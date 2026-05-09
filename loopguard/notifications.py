"""
Desktop notification system for LoopGuard
"""

import subprocess
import time
import json
from typing import Optional, Dict, List, Any
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import threading
import queue

from .types import LoopAlert


class NotificationSeverity(Enum):
    """Notification severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class NotificationAction(Enum):
    """Available notification actions"""
    DISMISS = "dismiss"
    SNOOZE = "snooze"
    STOP_SESSION = "stop_session"
    VIEW_DETAILS = "view_details"
    OPEN_SESSION = "open_session"


@dataclass
class NotificationHistory:
    """Represents a notification history entry"""
    id: str
    alert_type: str
    severity: str
    message: str
    timestamp: datetime
    action_taken: Optional[str] = None
    retry_count: int = 0


@dataclass
class NotificationQueue:
    """Notification queue management"""
    notifications: queue.Queue
    max_size: int = 100
    retry_delay: int = 60  # seconds
    max_retries: int = 3


class NotificationService:
    """Handles desktop notifications for LoopGuard"""
    
    def __init__(self, enabled: bool = True, config: Any = None):
        self.enabled = enabled
        self.config = config
        self._terminal_notifier_path = self._find_terminal_notifier()
        self._notification_queue = NotificationQueue(queue.Queue())
        self._notification_history: List[NotificationHistory] = []
        self._last_notifications: Dict[str, datetime] = {}  # For throttling
        self._snoozed_alerts: Dict[str, datetime] = {}  # Snoozed alerts
        self._project_settings: Dict[str, Dict] = {}  # Per-project settings
        self._lock = threading.Lock()
        self._worker_thread: Optional[threading.Thread] = None
        self._running = False
        
        # Initialize settings from config
        self._load_settings_from_config()
        self._start_worker_thread()
    
    def _load_settings_from_config(self) -> None:
        """Load notification settings from configuration"""
        if not self.config:
            return
        
        # Load quiet hours
        quiet_hours = self.config.get('notifications.quiet_hours', {})
        if quiet_hours.get('enabled', False):
            self._quiet_hours_start = quiet_hours.get('start_hour', 22)
            self._quiet_hours_end = quiet_hours.get('end_hour', 7)
        else:
            self._quiet_hours_start = None
            self._quiet_hours_end = None
        
        # Load sound setting
        self._sound_enabled = self.config.get('notifications.sound_enabled', True)
        
        # Load project settings
        project_settings = self.config.get('notifications.project_settings', {})
        self._project_settings = project_settings.copy()
    
    def _start_worker_thread(self) -> None:
        """Start the background worker thread for notification processing"""
        if not self._running:
            self._running = True
            self._worker_thread = threading.Thread(target=self._notification_worker, daemon=True)
            self._worker_thread.start()
    
    def _notification_worker(self) -> None:
        """Background worker to process notification queue"""
        while self._running:
            try:
                # Process notifications from queue
                try:
                    notification_data = self._notification_queue.notifications.get(timeout=1)
                    self._process_queued_notification(notification_data)
                    self._notification_queue.notifications.task_done()
                except queue.Empty:
                    continue
                
                # Check for snoozed alerts that need to be re-sent
                self._check_snoozed_alerts()
                
                time.sleep(0.1)  # Prevent busy waiting
            except Exception as e:
                print(f"Notification worker error: {e}")
    
    def _process_queued_notification(self, notification_data: Dict[str, Any]) -> None:
        """Process a notification from the queue"""
        try:
            alert = notification_data['alert']
            retry_count = notification_data.get('retry_count', 0)
            
            if self._should_send_notification(alert):
                success = self._send_notification_internal(alert)
                
                if not success and retry_count < self._notification_queue.max_retries:
                    # Retry later
                    notification_data['retry_count'] = retry_count + 1
                    time.sleep(self._notification_queue.retry_delay)
                    self._notification_queue.notifications.put(notification_data)
                elif success:
                    # Record in history
                    self._add_to_history(alert)
        except Exception as e:
            print(f"Error processing queued notification: {e}")
    
    def _check_snoozed_alerts(self):
        """Check if any snoozed alerts should be re-sent"""
        current_time = datetime.now()
        alerts_to_remove = []
        
        for alert_key, snooze_time in self._snoozed_alerts.items():
            if current_time >= snooze_time:
                # Snooze period expired, re-send
                alerts_to_remove.append(alert_key)
                # Re-queue the alert
                # Note: In a real implementation, we'd need to reconstruct the alert
                # For now, just remove from snoozed list
        
        for alert_key in alerts_to_remove:
            del self._snoozed_alerts[alert_key]
    
    def _should_send_notification(self, alert: LoopAlert) -> bool:
        """Check if notification should be sent based on various conditions"""
        if not self.enabled or not self._terminal_notifier_path:
            return False
        
        current_time = datetime.now()
        
        # Check quiet hours
        if self._is_quiet_hours():
            return False
        
        # Check if snoozed
        alert_key = f"{alert.session_id}:{alert.alert_type}"
        if alert_key in self._snoozed_alerts:
            return False
        
        # Check throttling
        if self._is_throttled(alert):
            return False
        
        # Check project-specific settings
        project_path = alert.evidence.get('file_path', '')
        if self._is_project_muted(project_path):
            return False
        
        return True
    
    def _is_quiet_hours(self) -> bool:
        """Check if current time is within quiet hours"""
        if self._quiet_hours_start is None or self._quiet_hours_end is None:
            return False
        
        current_hour = datetime.now().hour
        
        if self._quiet_hours_start <= self._quiet_hours_end:
            # Normal range (e.g., 22:00 to 07:00 doesn't cross midnight)
            return self._quiet_hours_start <= current_hour <= self._quiet_hours_end
        else:
            # Crosses midnight (e.g., 22:00 to 07:00)
            return current_hour >= self._quiet_hours_start or current_hour <= self._quiet_hours_end
    
    def _is_throttled(self, alert: LoopAlert) -> bool:
        """Check if alert is throttled"""
        alert_key = f"{alert.session_id}:{alert.alert_type}"
        last_sent = self._last_notifications.get(alert_key)
        
        if last_sent:
            throttle_seconds = self._get_throttle_seconds(alert)
            if (datetime.now() - last_sent).total_seconds() < throttle_seconds:
                return True
        
        return False
    
    def _get_throttle_seconds(self, alert: LoopAlert) -> int:
        """Get throttle seconds based on alert severity and project settings"""
        project_path = alert.evidence.get('file_path', '')
        
        # Check for project-specific throttle override
        if self.config and project_path:
            project_dir = str(Path(project_path).parent)
            custom_throttle = self.config.get_throttle_seconds(alert.severity, project_dir)
            if custom_throttle:
                return custom_throttle
        
        # Use configuration-based throttling
        if self.config:
            return self.config.get_throttle_seconds(alert.severity)
        
        # Fallback to defaults
        base_throttle = {
            NotificationSeverity.LOW.value: 300,    # 5 minutes
            NotificationSeverity.MEDIUM.value: 120,  # 2 minutes
            NotificationSeverity.HIGH.value: 30      # 30 seconds
        }
        
        return base_throttle.get(alert.severity, 120)
    
    def _is_project_muted(self, project_path: str) -> bool:
        """Check if project is muted"""
        if not project_path:
            return False
        
        # Use config if available
        if self.config:
            project_dir = str(Path(project_path).parent)
            return self.config.is_project_muted(project_dir)
        
        # Fallback to internal settings
        project_dir = Path(project_path).parent
        for proj_path, settings in self._project_settings.items():
            if project_dir.samefile(Path(proj_path)) and settings.get('muted', False):
                return True
        
        return False
    
    def _should_send_notification(self, alert: LoopAlert) -> bool:
        """Check if notification should be sent based on various conditions"""
        if not self.enabled or not self._terminal_notifier_path:
            return False
        
        current_time = datetime.now()
        
        # Check quiet hours
        if self._is_quiet_hours():
            return False
        
        # Check if snoozed
        alert_key = f"{alert.session_id}:{alert.alert_type}"
        if alert_key in self._snoozed_alerts:
            return False
        
        # Check throttling
        if self._is_throttled(alert):
            return False
        
        # Check project-specific settings
        project_path = alert.evidence.get('file_path', '')
        if self._is_project_muted(project_path):
            return False
        
        # Check severity override
        if self.config and project_path:
            project_dir = str(Path(project_path).parent)
            severity_override = self.config.get_severity_override(project_dir)
            if severity_override:
                # Apply severity override logic here if needed
                pass
        
        return True
    
    def _add_to_history(self, alert: LoopAlert, action: Optional[str] = None):
        """Add notification to history"""
        with self._lock:
            history_entry = NotificationHistory(
                id=f"{alert.session_id}:{alert.timestamp.isoformat()}",
                alert_type=alert.alert_type,
                severity=alert.severity,
                message=self._format_alert_message(alert),
                timestamp=alert.timestamp,
                action_taken=action
            )
            self._notification_history.append(history_entry)
            
            # Keep only last 1000 entries
            if len(self._notification_history) > 1000:
                self._notification_history = self._notification_history[-1000:]
    
    def _find_terminal_notifier(self) -> Optional[str]:
        """Find terminal-notifier executable"""
        try:
            # Check common locations
            paths = [
                '/usr/local/bin/terminal-notifier',
                '/opt/homebrew/bin/terminal-notifier',
                '~/.brew/bin/terminal-notifier'
            ]
            
            for path in paths:
                expanded_path = Path(path).expanduser()
                if expanded_path.exists():
                    return str(expanded_path)
            
            # Try to find in PATH
            result = subprocess.run(['which', 'terminal-notifier'], 
                              capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
            
            return None
        except Exception:
            return None
    
    def send_alert(self, alert: LoopAlert) -> bool:
        """Send a loop alert as desktop notification (queues for async processing)"""
        if not self.enabled or not self._terminal_notifier_path:
            return False
        
        try:
            # Queue notification for async processing
            notification_data = {
                'alert': alert,
                'retry_count': 0,
                'queued_at': datetime.now()
            }
            
            # Check queue size
            if self._notification_queue.notifications.qsize() >= self._notification_queue.max_size:
                # Remove oldest notification to make room
                try:
                    self._notification_queue.notifications.get_nowait()
                except queue.Empty:
                    pass
            
            self._notification_queue.notifications.put(notification_data)
            
            # Update last notification time for throttling
            alert_key = f"{alert.session_id}:{alert.alert_type}"
            self._last_notifications[alert_key] = datetime.now()
            
            return True
                
        except Exception as e:
            print(f"❌ Error queuing notification: {e}")
            return False
    
    def _send_notification_internal(self, alert: LoopAlert) -> bool:
        """Internal method to actually send the notification"""
        try:
            title = self._get_notification_title(alert)
            message = self._format_alert_message(alert)
            subtitle = f"Session: {alert.session_id[:8]}..."
            
            # Build terminal-notifier command with enhanced options
            cmd = [
                self._terminal_notifier_path,
                '-title', title,
                '-message', message,
                '-subtitle', subtitle,
                '-timeout', '10'  # Auto-dismiss after 10 seconds
            ]
            
            # Add sound if enabled
            if self._sound_enabled:
                sound = self._get_sound_for_severity(alert.severity)
                cmd.extend(['-sound', sound])
            
            # Add severity-specific styling and actions
            actions = self._get_actions_for_alert(alert)
            if actions:
                cmd.extend(['-actions', ','.join(actions)])
            
            # Add app icon based on severity
            icon_path = self._get_icon_for_severity(alert.severity)
            if icon_path:
                cmd.extend(['-appIcon', icon_path])
            
            # Execute notification
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ Alert sent: {alert.alert_type}")
                print(f"   Session: {alert.session_id[:12]}...")
                print(f"   Severity: {alert.severity}")
                return True
            else:
                print(f"❌ Notification failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error sending notification: {e}")
            return False
    
    def _get_notification_title(self, alert: LoopAlert) -> str:
        """Get notification title based on alert type and severity"""
        severity_emoji = {
            NotificationSeverity.LOW.value: "🔵",
            NotificationSeverity.MEDIUM.value: "🟡",
            NotificationSeverity.HIGH.value: "🔴"
        }
        
        emoji = severity_emoji.get(alert.severity, "🔄")
        
        if alert.alert_type == 'tool_call_loop':
            return f"{emoji} LoopGuard: Tool Loop Detected"
        elif alert.alert_type == 'error_loop':
            return f"{emoji} LoopGuard: Error Loop Detected"
        elif alert.alert_type == 'stagnation':
            return f"{emoji} LoopGuard: Session Stagnation"
        else:
            return f"{emoji} LoopGuard Alert"
    
    def _get_sound_for_severity(self, severity: str) -> str:
        """Get sound based on alert severity"""
        if severity == NotificationSeverity.HIGH.value:
            return 'Basso'
        elif severity == NotificationSeverity.MEDIUM.value:
            return 'Glass'
        else:
            return 'default'
    
    def _get_actions_for_alert(self, alert: LoopAlert) -> List[str]:
        """Get available actions for an alert"""
        base_actions = ['Dismiss']
        
        if alert.severity == NotificationSeverity.HIGH.value:
            base_actions.extend(['Stop Session', 'Open Session'])
        elif alert.severity == NotificationSeverity.MEDIUM.value:
            base_actions.extend(['Snooze', 'View Details'])
        else:
            base_actions.append('Snooze')
        
        return base_actions
    
    def _get_icon_for_severity(self, severity: str) -> Optional[str]:
        """Get icon path based on severity"""
        # In a real implementation, these would be actual icon files
        # For now, return None to use default
        return None
    
    def _format_alert_message(self, alert: LoopAlert) -> str:
        """Format alert message for display with enhanced context"""
        if alert.alert_type == 'tool_call_loop':
            evidence = alert.evidence
            file_path = evidence.get('file_path', 'unknown')
            file_name = Path(file_path).name
            tool_name = evidence.get('tool_name', 'unknown')
            count = evidence.get('count', 0)
            
            # Enhanced message with specific file paths and line numbers
            if file_path != 'unknown':
                line_info = self._extract_line_info(evidence)
                return (f"🔄 Tool Loop: '{tool_name}' repeated {count} times\n"
                       f"📁 File: {file_name}{line_info}\n"
                       f"💡 Action: {alert.suggested_action}\n"
                       f"🔧 Suggestion: Agent may be stuck - consider different approach")
            else:
                return (f"🔄 Tool Loop: '{tool_name}' repeated {count} times\n"
                       f"💡 Action: {alert.suggested_action}")
        
        elif alert.alert_type == 'error_loop':
            evidence = alert.evidence
            error_msg = evidence.get('error_message', 'Unknown error')
            count = evidence.get('count', 0)
            file_path = evidence.get('file_path', '')
            
            # Truncate very long error messages
            if len(error_msg) > 100:
                error_msg = error_msg[:97] + "..."
            
            file_info = f"\n📁 File: {Path(file_path).name}" if file_path else ""
            
            return (f"❌ Error Loop: '{error_msg}' repeated {count} times{file_info}\n"
                   f"💡 Action: {alert.suggested_action}\n"
                   f"🔧 Suggestion: Check file permissions or syntax errors")
        
        elif alert.alert_type == 'stagnation':
            evidence = alert.evidence
            minutes = evidence.get('time_window_minutes', 0)
            activity_count = evidence.get('activity_count', 0)
            last_activity = evidence.get('last_activity', 'Unknown')
            
            return (f"⏸️ Stagnation: No file changes for {minutes} minutes\n"
                   f"📊 Activity: {activity_count} operations without progress\n"
                   f"🕐 Last activity: {last_activity}\n"
                   f"💡 Action: {alert.suggested_action}\n"
                   f"🔧 Suggestion: Agent may be stuck - consider restarting session")
        
        else:
            return f"🚨 {alert.description}"
    
    def _extract_line_info(self, evidence: Dict) -> str:
        """Extract line number information from evidence"""
        line_info = evidence.get('line_number')
        if line_info:
            return f" (line {line_info})"
        return ""
    
    # Configuration and management methods
    def set_quiet_hours(self, start_hour: int, end_hour: int):
        """Set quiet hours for notifications (24-hour format)"""
        self._quiet_hours_start = start_hour
        self._quiet_hours_end = end_hour
    
    def enable_sound(self, enabled: bool):
        """Enable or disable notification sounds"""
        self._sound_enabled = enabled
    
    def snooze_alert(self, session_id: str, alert_type: str, minutes: int = 30):
        """Snooze alerts for a specific session and alert type"""
        alert_key = f"{session_id}:{alert_type}"
        snooze_until = datetime.now() + timedelta(minutes=minutes)
        self._snoozed_alerts[alert_key] = snooze_until
    
    def set_project_settings(self, project_path: str, settings: Dict[str, Any]):
        """Set notification settings for a specific project"""
        self._project_settings[project_path] = settings
    
    def get_notification_history(self, limit: int = 50) -> List[NotificationHistory]:
        """Get recent notification history"""
        with self._lock:
            return self._notification_history[-limit:]
    
    def clear_history(self):
        """Clear notification history"""
        with self._lock:
            self._notification_history.clear()
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        return {
            'queue_size': self._notification_queue.notifications.qsize(),
            'max_size': self._notification_queue.max_size,
            'snoozed_alerts': len(self._snoozed_alerts),
            'throttled_alerts': len(self._last_notifications)
        }
    
    def send_test_notification(self) -> bool:
        """Send a test notification with enhanced features"""
        if not self._terminal_notifier_path:
            print("terminal-notifier not found")
            return False
        
        try:
            cmd = [
                self._terminal_notifier_path,
                '-title', '🔵 LoopGuard Test',
                '-message', 'LoopGuard is working correctly!\nEnhanced notifications are active.',
                '-subtitle', 'Test Notification',
                '-sound', 'Glass',
                '-timeout', '5'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
            
        except Exception as e:
            print(f"Test notification failed: {e}")
            return False
    
    def stop(self) -> None:
        """Stop the notification worker thread"""
        self._running = False
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2)
    
    def is_available(self) -> bool:
        """Check if notification service is available"""
        return self.enabled and self._terminal_notifier_path is not None
    
    def get_status(self) -> dict:
        """Get notification service status"""
        return {
            'enabled': self.enabled,
            'available': self._terminal_notifier_path is not None,
            'terminal_notifier_path': self._terminal_notifier_path,
            'quiet_hours': {
                'start': self._quiet_hours_start,
                'end': self._quiet_hours_end
            },
            'sound_enabled': self._sound_enabled,
            'queue_status': self.get_queue_status()
        }
