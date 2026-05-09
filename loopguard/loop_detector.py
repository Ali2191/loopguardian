"""
Loop detection algorithms for Claude Code sessions
"""

import os
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Set, Any
from dataclasses import dataclass
import hashlib

from .log_parser import ToolCall, LogEvent
from .config import Config
from .types import LoopAlert
from .adaptive_detector import AdaptiveLoopDetector, SessionTypeProfile




class LoopDetector:
    """Enhanced loop detector with adaptive threshold tuning"""
    
    def __init__(self, config: Config):
        self.config: Config = config
        self.tool_call_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=50))
        self.error_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=20))
        self.file_activity: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10))
        self.session_activity: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.last_alerts: Dict[str, deque] = defaultdict(lambda: deque(maxlen=5))
        self.processed_events: Set[str] = set()  # Avoid duplicate processing
        
        # Initialize adaptive detector
        self.adaptive_detector = AdaptiveLoopDetector(config)
        self.adaptive_mode = config.get('detection.adaptive_mode', True)
    
    def analyze_events(self, events: List[LogEvent]) -> List[LoopAlert]:
        """Analyze log events for loop patterns with adaptive detection"""
        alerts: List[LoopAlert] = []
        
        for event in events:
            event_id = self._get_event_id(event)
            if event_id in self.processed_events:
                continue
            
            self.processed_events.add(event_id)
            self.session_activity[event.session_id].append(event)
            
            # Use adaptive detection if enabled
            if self.adaptive_mode:
                adaptive_alerts = self.adaptive_detector.analyze_events_adaptive([event])
                alerts.extend(adaptive_alerts)
            else:
                # Use traditional detection
                # Detect different types of loops
                if event.event_type == 'assistant':
                    tool_alerts = self._detect_tool_call_loops(event)
                    alerts.extend(tool_alerts)
                
                # Check for error patterns
                error_alerts = self._detect_error_loops(event)
                alerts.extend(error_alerts)
            
            # Check for stagnation (periodic check)
            stagnation_alerts = self._detect_stagnation(event.session_id)
            alerts.extend(stagnation_alerts)
        
        return self._filter_alerts(alerts)
    
    def _detect_tool_call_loops(self, event: LogEvent) -> List[LoopAlert]:
        """Detect repeated tool calls with adaptive thresholds"""
        alerts: List[LoopAlert] = []
        
        if not isinstance(event.content.get('content'), list):
            return alerts
        
        # Get adaptive threshold if available
        session_profile = None
        if self.adaptive_mode:
            session_profile = self.adaptive_detector.get_session_profile(event.session_id)
        
        for content_item in event.content['content']:
            if (isinstance(content_item, dict) and 
                content_item.get('type') == 'tool_use'):
                
                tool_call = self._normalize_tool_call(content_item, event)
                if not tool_call:
                    continue
                
                session_history = self.tool_call_history[event.session_id]
                session_history.append(tool_call)
                
                # Use adaptive threshold or fallback to config
                if session_profile:
                    threshold = session_profile.tool_call_threshold
                else:
                    threshold = self.config.get('detection.tool_call_repeats', 3)
                
                recent_calls = list(session_history)[-int(threshold):]
                
                if len(recent_calls) >= threshold:
                    if self._are_tool_calls_identical(recent_calls[-int(threshold):]):
                        alert = LoopAlert(
                            alert_type='tool_call_loop',
                            session_id=event.session_id,
                            description=f"Tool '{tool_call['name']}' repeated {threshold} times",
                            severity='medium',
                            timestamp=event.timestamp,
                            evidence={
                                'tool_name': tool_call['name'],
                                'parameters': tool_call['parameters'],
                                'count': threshold,
                                'file_path': tool_call.get('file_path'),
                                'adaptive_threshold': session_profile is not None
                            },
                            suggested_action="Interrupt session and provide more specific context"
                        )
                        alerts.append(alert)
        
        return alerts
    
    def _detect_error_loops(self, event: LogEvent) -> List[LoopAlert]:
        """Detect repeated error messages with adaptive thresholds"""
        alerts: List[LoopAlert] = []
        
        # Extract error messages from event content
        error_message = self._extract_error_message(event)
        if not error_message:
            return alerts
        
        # Get adaptive threshold if available
        session_profile = None
        if self.adaptive_mode:
            session_profile = self.adaptive_detector.get_session_profile(event.session_id)
        
        session_errors = self.error_history[event.session_id]
        session_errors.append({
            'message': error_message,
            'timestamp': event.timestamp,
            'event_id': self._get_event_id(event)
        })
        
        # Use adaptive threshold or fallback to config
        if session_profile:
            threshold = session_profile.error_threshold
        else:
            threshold = self.config.get('detection.error_repeats', 2)
        
        recent_errors = [e for e in session_errors 
                      if e['timestamp'] > event.timestamp - timedelta(minutes=10)]
        
        identical_errors = [e for e in recent_errors 
                        if e['message'] == error_message]
        
        if len(identical_errors) >= threshold:
            alert = LoopAlert(
                alert_type='error_loop',
                session_id=event.session_id,
                description=f"Error repeated {threshold} times: {error_message[:100]}...",
                severity='high',
                timestamp=event.timestamp,
                evidence={
                    'error_message': error_message,
                    'count': len(identical_errors),
                    'recent_occurrences': [e['timestamp'] for e in identical_errors],
                    'adaptive_threshold': session_profile is not None
                },
                suggested_action="Check file permissions or syntax and retry with corrected approach"
            )
            alerts.append(alert)
        
        return alerts
    
    def _detect_stagnation(self, session_id: str) -> List[LoopAlert]:
        """Detect sessions with no meaningful progress using adaptive thresholds"""
        alerts: List[LoopAlert] = []
        
        activity = self.session_activity[session_id]
        if not activity:
            return alerts
        
        # Get adaptive threshold if available
        session_profile = None
        if self.adaptive_mode:
            session_profile = self.adaptive_detector.get_session_profile(session_id)
        
        last_event = activity[-1]
        
        # Use adaptive threshold or fallback to config
        if session_profile:
            stagnation_minutes = session_profile.stagnation_threshold
        else:
            stagnation_minutes = self.config.get('detection.stagnation_minutes', 5)
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=stagnation_minutes)
        
        # Check if session is active but no progress
        if (last_event.timestamp.replace(tzinfo=None) > cutoff_time.replace(tzinfo=None) and 
            len(activity) > 10):  # Must have some activity
            
            # Check for file changes in recent activity
            recent_activity = [e for e in activity 
                           if e.timestamp.replace(tzinfo=None) > cutoff_time.replace(tzinfo=None)]
            file_changes = self._count_file_changes(recent_activity)
            
            if file_changes == 0:
                alert = LoopAlert(
                    alert_type='stagnation',
                    session_id=session_id,
                    description=f"No file changes in {stagnation_minutes} minutes of activity",
                    severity='medium',
                    timestamp=last_event.timestamp,
                    evidence={
                        'activity_count': len(recent_activity),
                        'time_window_minutes': stagnation_minutes,
                        'last_activity': last_event.timestamp,
                        'adaptive_threshold': session_profile is not None
                    },
                    suggested_action="Check if agent is stuck in a loop and restart session if needed"
                )
                alerts.append(alert)
        
        return alerts
    
    def _normalize_tool_call(self, tool_use: dict, event: LogEvent) -> Optional[dict]:
        """Normalize tool call for comparison"""
        try:
            name = tool_use.get('name', '')
            if not name:
                return None
            
            parameters = tool_use.get('input', {})
            
            # Normalize file paths for comparison
            normalized_params = {}
            for key, value in parameters.items():
                if key in ['path', 'file_path'] and isinstance(value, str):
                    # Normalize path separators and resolve relative paths
                    normalized_params[key] = os.path.normpath(value)
                else:
                    normalized_params[key] = value
            
            return {
                'name': name,
                'parameters': normalized_params,
                'timestamp': event.timestamp
            }
        except (KeyError, ValueError):
            return None
    
    def _are_tool_calls_identical(self, tool_calls: List[dict]) -> bool:
        """Check if tool calls are identical"""
        if len(tool_calls) < 2:
            return True
        
        first_call = tool_calls[0]
        
        for call in tool_calls[1:]:
            if (call['name'] != first_call['name'] or 
                call['parameters'] != first_call['parameters']):
                return False
        
        return True
    
    def _extract_error_message(self, event: LogEvent) -> Optional[str]:
        """Extract error message from event"""
        content = event.content
        
        # Look for error messages in different formats
        if isinstance(content, dict):
            # Check for error in message content
            message_text = content.get('content', '')
            if isinstance(message_text, str) and 'error' in message_text.lower():
                return message_text
            
            # Check for tool result errors
            if 'tool_result' in str(content):
                return self._extract_tool_result_error(content)
        
        return None
    
    def _extract_tool_result_error(self, content: dict) -> Optional[str]:
        """Extract error from tool result"""
        # This would need to be implemented based on actual log format
        # For now, return a generic error extraction
        if 'error' in str(content).lower():
            return str(content)[:200]  # Truncate long errors
        return None
    
    def _count_file_changes(self, events: List[LogEvent]) -> int:
        """Count file modification events"""
        file_changes = 0
        
        for event in events:
            if event.event_type == 'assistant':
                content = event.content
                if isinstance(content, dict):
                    # Look for file operations
                    message_str = str(content.get('content', ''))
                    if any(op in message_str.lower() 
                           for op in ['write_to_file', 'str_replace', 'edit']):
                        file_changes += 1
        
        return file_changes
    
    def _get_event_id(self, event: LogEvent) -> str:
        """Generate unique ID for event to avoid duplicates"""
        content_str = str(event.content)
        timestamp_str = event.timestamp.isoformat()
        return hashlib.md5(f"{event.session_id}{timestamp_str}{content_str}".encode()).hexdigest()
    
    def _filter_alerts(self, alerts: List[LoopAlert]) -> List[LoopAlert]:
        """Filter alerts based on throttling and deduplication"""
        filtered_alerts = []
        throttle_seconds = self.config.get('notifications.throttle_seconds', 30)
        
        for alert in alerts:
            alert_key = f"{alert.session_id}:{alert.alert_type}"
            
            # Check throttling
            last_alert_time = self.last_alerts.get(alert_key)
            if (last_alert_time and 
                alert.timestamp - last_alert_time < timedelta(seconds=throttle_seconds)):
                continue
            
            filtered_alerts.append(alert)
            self.last_alerts[alert_key] = alert.timestamp
        
        return filtered_alerts
    
    def clear_session_history(self, session_id: str) -> None:
        """Clear history for a session (when session ends)"""
        if session_id in self.tool_call_history:
            del self.tool_call_history[session_id]
        if session_id in self.error_history:
            del self.error_history[session_id]
        if session_id in self.file_activity:
            del self.file_activity[session_id]
        if session_id in self.session_activity:
            del self.session_activity[session_id]
    
    def provide_feedback(self, session_id: str, alert_id: str, was_correct: bool, feedback_type: str = "user") -> None:
        """Provide feedback for detected loops to improve adaptive accuracy"""
        if self.adaptive_mode:
            self.adaptive_detector.provide_feedback(session_id, alert_id, was_correct, feedback_type)
    
    def get_adaptation_stats(self) -> Dict[str, Any]:
        """Get statistics about adaptive threshold tuning"""
        if self.adaptive_mode:
            return self.adaptive_detector.get_adaptation_stats()
        return {'adaptive_mode': False}
    
    def toggle_adaptive_mode(self, enabled: bool) -> None:
        """Toggle adaptive detection mode"""
        self.adaptive_mode = enabled
        print(f"🎯 Adaptive detection {'enabled' if enabled else 'disabled'}")
