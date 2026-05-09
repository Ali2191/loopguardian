"""
Adaptive loop detection with machine learning-inspired threshold tuning
"""

import time
import json
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
import statistics
import hashlib

from .types import LoopAlert
from .log_parser import LogEvent
from .config import Config


@dataclass
class DetectionMetrics:
    """Metrics for detection accuracy and performance"""
    true_positives: int = 0
    false_positives: int = 0
    true_negatives: int = 0
    false_negatives: int = 0
    total_detections: int = 0
    feedback_history: deque = field(default_factory=lambda: deque(maxlen=100))
    
    @property
    def precision(self) -> float:
        """Detection precision: TP / (TP + FP)"""
        if self.true_positives + self.false_positives == 0:
            return 1.0
        return self.true_positives / (self.true_positives + self.false_positives)
    
    @property
    def recall(self) -> float:
        """Detection recall: TP / (TP + FN)"""
        if self.true_positives + self.false_negatives == 0:
            return 1.0
        return self.true_positives / (self.true_positives + self.false_negatives)
    
    @property
    def f1_score(self) -> float:
        """F1 score: harmonic mean of precision and recall"""
        if self.precision + self.recall == 0:
            return 0.0
        return 2 * (self.precision * self.recall) / (self.precision + self.recall)
    
    @property
    def false_positive_rate(self) -> float:
        """False positive rate per hour"""
        return self.false_positives / max(1, self.total_detections / 60)  # Assuming detections per minute


@dataclass
class SessionTypeProfile:
    """Profile for different session types (debugging, development, testing)"""
    session_type: str  # 'debugging', 'development', 'testing'
    tool_call_threshold: float = 3.0
    error_threshold: float = 2.0
    stagnation_threshold: float = 5.0
    confidence_threshold: float = 0.7
    adaptation_rate: float = 0.1
    
    def adjust_thresholds(self, metrics: DetectionMetrics) -> None:
        """Adjust thresholds based on performance metrics"""
        # Adjust tool call threshold
        if metrics.false_positive_rate > 0.125:  # > 1 FP per 8 hours
            self.tool_call_threshold += self.adaptation_rate
        elif metrics.false_positive_rate < 0.02 and metrics.recall < 0.8:
            self.tool_call_threshold -= self.adaptation_rate * 0.5
        
        # Adjust error threshold
        if metrics.false_positives > 0 and metrics.precision < 0.8:
            self.error_threshold += self.adaptation_rate
        elif metrics.recall < 0.7:
            self.error_threshold -= self.adaptation_rate * 0.3
        
        # Ensure thresholds stay within reasonable bounds
        self.tool_call_threshold = max(2.0, min(10.0, self.tool_call_threshold))
        self.error_threshold = max(1.0, min(8.0, self.error_threshold))
        self.stagnation_threshold = max(2.0, min(15.0, self.stagnation_threshold))


class AdaptiveLoopDetector:
    """Enhanced loop detector with adaptive threshold tuning"""
    
    def __init__(self, config: Config):
        self.config = config
        self.session_profiles: Dict[str, SessionTypeProfile] = {}
        self.session_metrics: Dict[str, DetectionMetrics] = defaultdict(DetectionMetrics)
        self.session_types: Dict[str, str] = {}  # session_id -> session_type
        self.feedback_data: Dict[str, List[Dict]] = defaultdict(list)
        self._lock = threading.RLock()
        
        # Initialize default session profiles
        self._init_default_profiles()
        
        # Load historical data
        self._load_historical_data()
        
        # Performance targets from Week 3 plan
        self.targets = {
            'max_false_positives_per_8h': 1.0,
            'min_precision': 0.95,
            'min_recall': 0.80,
            'target_f1_score': 0.87
        }
    
    def analyze_events_adaptive(self, events: List[LogEvent]) -> List[LoopAlert]:
        """Analyze events with adaptive thresholds based on session type"""
        alerts = []
        
        for event in events:
            session_id = event.session_id
            
            # Determine session type if not already classified
            if session_id not in self.session_types:
                self.session_types[session_id] = self._classify_session_type(event)
            
            session_type = self.session_types[session_id]
            profile = self.session_profiles[session_type]
            
            # Apply context-aware detection
            context_alerts = self._detect_with_context(event, profile)
            
            # Filter alerts based on confidence threshold
            for alert in context_alerts:
                confidence = self._calculate_alert_confidence(alert, event, profile)
                if confidence >= profile.confidence_threshold:
                    alert.suggested_action = self._get_contextual_suggestion(alert, session_type)
                    alerts.append(alert)
        
        return alerts
    
    def provide_feedback(self, session_id: str, alert_id: str, was_correct: bool, feedback_type: str = "user") -> None:
        """Provide feedback for detected loops to improve accuracy"""
        with self._lock:
            timestamp = datetime.now(timezone.utc).isoformat()
            
            feedback_entry = {
                'timestamp': timestamp,
                'alert_id': alert_id,
                'was_correct': was_correct,
                'feedback_type': feedback_type,
                'session_type': self.session_types.get(session_id, 'unknown')
            }
            
            self.feedback_data[session_id].append(feedback_entry)
            
            # Update metrics
            metrics = self.session_metrics[session_id]
            if was_correct:
                metrics.true_positives += 1
            else:
                metrics.false_positives += 1
            
            metrics.feedback_history.append(feedback_entry)
            
            # Adapt thresholds based on feedback
            self._adapt_thresholds(session_id, metrics)
            
            # Save feedback data periodically
            if len(self.feedback_data[session_id]) % 10 == 0:
                self._save_feedback_data()
    
    def get_session_profile(self, session_id: str) -> Optional[SessionTypeProfile]:
        """Get the adaptive profile for a session"""
        session_type = self.session_types.get(session_id)
        if session_type:
            return self.session_profiles[session_type]
        return None
    
    def get_adaptation_stats(self) -> Dict:
        """Get statistics about threshold adaptation"""
        with self._lock:
            stats = {
                'session_types': dict(self.session_types),
                'total_feedback': sum(len(feedback) for feedback in self.feedback_data.values()),
                'adapted_sessions': len([s for s in self.session_metrics.values() if s.total_detections > 0]),
                'average_precision': statistics.mean([m.precision for m in self.session_metrics.values() if m.total_detections > 0]) if self.session_metrics else 0,
                'average_recall': statistics.mean([m.recall for m in self.session_metrics.values() if m.total_detections > 0]) if self.session_metrics else 0,
                'profiles': {}
            }
            
            for session_type, profile in self.session_profiles.items():
                stats['profiles'][session_type] = {
                    'tool_call_threshold': profile.tool_call_threshold,
                    'error_threshold': profile.error_threshold,
                    'stagnation_threshold': profile.stagnation_threshold,
                    'confidence_threshold': profile.confidence_threshold
                }
            
            return stats
    
    def _init_default_profiles(self) -> None:
        """Initialize default session type profiles"""
        self.session_profiles['debugging'] = SessionTypeProfile(
            session_type='debugging',
            tool_call_threshold=4.0,  # Higher threshold for debugging (more retries expected)
            error_threshold=3.0,      # Higher error tolerance in debugging
            stagnation_threshold=8.0,   # Longer stagnation allowed
            confidence_threshold=0.8,
            adaptation_rate=0.15
        )
        
        self.session_profiles['development'] = SessionTypeProfile(
            session_type='development',
            tool_call_threshold=3.0,  # Standard thresholds
            error_threshold=2.0,
            stagnation_threshold=5.0,
            confidence_threshold=0.7,
            adaptation_rate=0.1
        )
        
        self.session_profiles['testing'] = SessionTypeProfile(
            session_type='testing',
            tool_call_threshold=2.5,  # Lower threshold (loops more problematic in testing)
            error_threshold=1.5,
            stagnation_threshold=3.0,
            confidence_threshold=0.6,
            adaptation_rate=0.2
        )
        
        self.session_profiles['unknown'] = SessionTypeProfile(
            session_type='unknown',
            tool_call_threshold=3.0,
            error_threshold=2.0,
            stagnation_threshold=5.0,
            confidence_threshold=0.7,
            adaptation_rate=0.1
        )
    
    def _classify_session_type(self, event: LogEvent) -> str:
        """Classify session type based on event content and patterns"""
        content = str(event.content).lower()
        
        # Debugging indicators
        debug_keywords = ['debug', 'error', 'exception', 'traceback', 'fix', 'bug', 'test', 'assert']
        debug_score = sum(1 for keyword in debug_keywords if keyword in content)
        
        # Development indicators
        dev_keywords = ['feature', 'implement', 'create', 'add', 'build', 'develop', 'function', 'class']
        dev_score = sum(1 for keyword in dev_keywords if keyword in content)
        
        # Testing indicators
        test_keywords = ['test', 'spec', 'unit', 'integration', 'assert', 'mock', 'fixture']
        test_score = sum(1 for keyword in test_keywords if keyword in content)
        
        # Determine session type based on scores
        if debug_score >= 3:
            return 'debugging'
        elif test_score >= 2:
            return 'testing'
        elif dev_score >= 2:
            return 'development'
        else:
            return 'unknown'
    
    def _detect_with_context(self, event: LogEvent, profile: SessionTypeProfile) -> List[LoopAlert]:
        """Detect loops with context-aware thresholds"""
        # This would integrate with the existing LoopDetector but use adaptive thresholds
        # For now, return empty list - integration would be done in the main LoopDetector
        return []
    
    def _calculate_alert_confidence(self, alert: LoopAlert, event: LogEvent, profile: SessionTypeProfile) -> float:
        """Calculate confidence score for an alert"""
        base_confidence = 0.5
        
        # Adjust based on alert type and session profile
        if alert.alert_type == 'tool_call_loop':
            base_confidence = min(1.0, alert.evidence.get('count', 1) / profile.tool_call_threshold)
        elif alert.alert_type == 'error_loop':
            base_confidence = min(1.0, alert.evidence.get('count', 1) / profile.error_threshold)
        elif alert.alert_type == 'stagnation':
            base_confidence = min(1.0, alert.evidence.get('time_window_minutes', 1) / profile.stagnation_threshold)
        
        # Adjust based on recent feedback for this session type
        session_type = profile.session_type
        recent_feedback = [f for feedback_list in self.feedback_data.values() 
                         for f in feedback_list 
                         if f.get('session_type') == session_type and 
                         (datetime.now(timezone.utc) - datetime.fromisoformat(f['timestamp'].replace('Z', '+00:00'))).total_seconds() < 3600]
        
        if recent_feedback:
            accuracy = sum(1 for f in recent_feedback if f['was_correct']) / len(recent_feedback)
            base_confidence *= accuracy
        
        return base_confidence
    
    def _get_contextual_suggestion(self, alert: LoopAlert, session_type: str) -> str:
        """Get contextual suggestion based on session type"""
        suggestions = {
            'debugging': {
                'tool_call_loop': "Debug tool call parameters and consider adding debug logging",
                'error_loop': "Check error conditions and add defensive programming",
                'stagnation': "Review debugging strategy and consider different approach"
            },
            'development': {
                'tool_call_loop': "Review tool parameters and consider alternative implementation",
                'error_loop': "Fix underlying issue causing repeated errors",
                'stagnation': "Break down task into smaller, achievable steps"
            },
            'testing': {
                'tool_call_loop': "Check test setup and mock configurations",
                'error_loop': "Fix test environment and dependencies",
                'stagnation': "Review test strategy and consider test isolation"
            }
        }
        
        return suggestions.get(session_type, {}).get(alert.alert_type, alert.suggested_action)
    
    def _adapt_thresholds(self, session_id: str, metrics: DetectionMetrics) -> None:
        """Adapt thresholds based on session metrics"""
        session_type = self.session_types.get(session_id, 'unknown')
        profile = self.session_profiles[session_type]
        
        # Check if we have enough data to adapt
        if metrics.total_detections < 5:
            return
        
        # Adapt thresholds based on performance
        profile.adjust_thresholds(metrics)
        
        try:
            with open(data_file, 'r') as f:
                data = json.load(f)
            
            # Load session types
            self.session_types.update(data.get('session_types', {}))
            
            # Load feedback data
            for session_id, feedback_list in data.get('feedback_data', {}).items():
                self.feedback_data[session_id].extend(feedback_list)
            
            # Load adapted profiles
            profiles_data = data.get('session_profiles', {})
            for session_type, profile_data in profiles_data.items():
                if session_type in self.session_profiles:
                    profile = self.session_profiles[session_type]
                    profile.tool_call_threshold = profile_data.get('tool_call_threshold', profile.tool_call_threshold)
                    profile.error_threshold = profile_data.get('error_threshold', profile.error_threshold)
                    profile.stagnation_threshold = profile_data.get('stagnation_threshold', profile.stagnation_threshold)
                    profile.confidence_threshold = profile_data.get('confidence_threshold', profile.confidence_threshold)
            
            print(f"📊 Loaded historical adaptation data for {len(self.session_types)} sessions")
            
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  Error loading historical data: {e}")
    
    def _save_feedback_data(self):
        """Save feedback and adaptation data"""
        data_file = Path.home() / ".loopguard" / "adaptive_data.json"
        data_file.parent.mkdir(exist_ok=True)
        
        try:
            data = {
                'session_types': self.session_types,
                'feedback_data': dict(self.feedback_data),
                'session_profiles': {
                    session_type: {
                        'tool_call_threshold': profile.tool_call_threshold,
                        'error_threshold': profile.error_threshold,
                        'stagnation_threshold': profile.stagnation_threshold,
                        'confidence_threshold': profile.confidence_threshold
                    }
                    for session_type, profile in self.session_profiles.items()
                },
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
            with open(data_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except IOError as e:
            print(f"⚠️  Error saving adaptation data: {e}")
