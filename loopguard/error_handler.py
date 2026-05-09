"""
Error handling and graceful degradation for LoopGuard
"""

import logging
import traceback
import sys
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable
from pathlib import Path
import json
from enum import Enum

from .notifications import NotificationService


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories"""
    FILE_SYSTEM = "file_system"
    NETWORK = "network"
    CONFIGURATION = "configuration"
    NOTIFICATION = "notification"
    DATABASE = "database"
    PROCESS_MONITORING = "process_monitoring"
    LOG_PARSING = "log_parsing"
    RESOURCE_EXHAUSTION = "resource_exhaustion"


class LoopGuardError(Exception):
    """Base exception for LoopGuard"""
    def __init__(self, message: str, category: ErrorCategory, 
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM, 
                 cause: Optional[Exception] = None):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.cause = cause
        self.timestamp = datetime.now()


class ErrorHandler:
    """Centralized error handling and recovery for LoopGuard"""
    
    def __init__(self, notification_service: Optional[NotificationService] = None):
        self.notification_service = notification_service
        self.error_counts: Dict[str, int] = {}
        self.last_errors: Dict[str, datetime] = {}
        self.recovery_actions: Dict[ErrorCategory, Callable] = {}
        self.fallback_modes: Dict[ErrorCategory, bool] = {}
        self.logger = self._setup_logger()
        
        # Initialize recovery actions
        self._setup_recovery_actions()
    
    def _setup_logger(self) -> logging.Logger:
        """Setup structured logging"""
        logger = logging.getLogger('loopguard')
        logger.setLevel(logging.INFO)
        
        # Create logs directory
        log_dir = Path.home() / ".loopguard" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # File handler with rotation
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_dir / "loopguard.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def _setup_recovery_actions(self) -> None:
        """Setup automatic recovery actions for different error types"""
        self.recovery_actions = {
            ErrorCategory.FILE_SYSTEM: self._recover_file_system,
            ErrorCategory.NETWORK: self._recover_network,
            ErrorCategory.CONFIGURATION: self._recover_configuration,
            ErrorCategory.NOTIFICATION: self._recover_notification,
            ErrorCategory.DATABASE: self._recover_database,
            ErrorCategory.PROCESS_MONITORING: self._recover_process_monitoring,
            ErrorCategory.LOG_PARSING: self._recover_log_parsing,
            ErrorCategory.RESOURCE_EXHAUSTION: self._recover_resource_exhaustion
        }
        
        # Initialize fallback modes
        self.fallback_modes = {
            category: False for category in ErrorCategory
        }
    
    def handle_error(self, error: Exception, context: Dict[str, Any] = None) -> bool:
        """
        Handle an error with appropriate recovery action
        
        Returns:
            bool: True if error was handled/recovered, False otherwise
        """
        if context is None:
            context = {}
        
        # Convert to LoopGuardError if needed
        if not isinstance(error, LoopGuardError):
            loopguard_error = LoopGuardError(
                message=str(error),
                category=self._categorize_error(error),
                severity=self._determine_severity(error),
                cause=error
            )
        else:
            loopguard_error = error
        
        # Log the error
        self._log_error(loopguard_error, context)
        
        # Update error tracking
        self._update_error_tracking(loopguard_error)
        
        # Attempt recovery
        recovery_success = self._attempt_recovery(loopguard_error, context)
        
        # Send notification if critical and notification service available
        if (loopguard_error.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL] 
            and self.notification_service):
            self._send_error_notification(loopguard_error, context)
        
        return recovery_success
    
    def _categorize_error(self, error: Exception) -> ErrorCategory:
        """Categorize error based on type and message"""
        error_msg = str(error).lower()
        error_type = type(error).__name__.lower()
        
        if any(keyword in error_msg for keyword in ['file', 'directory', 'path', 'permission']):
            return ErrorCategory.FILE_SYSTEM
        elif any(keyword in error_msg for keyword in ['network', 'connection', 'timeout', 'socket']):
            return ErrorCategory.NETWORK
        elif any(keyword in error_msg for keyword in ['config', 'json', 'schema']):
            return ErrorCategory.CONFIGURATION
        elif any(keyword in error_msg for keyword in ['notification', 'terminal-notifier']):
            return ErrorCategory.NOTIFICATION
        elif any(keyword in error_msg for keyword in ['database', 'sqlite', 'sql']):
            return ErrorCategory.DATABASE
        elif any(keyword in error_msg for keyword in ['process', 'pid', 'psutil']):
            return ErrorCategory.PROCESS_MONITORING
        elif any(keyword in error_msg for keyword in ['log', 'parse', 'event']):
            return ErrorCategory.LOG_PARSING
        elif any(keyword in error_msg for keyword in ['memory', 'disk', 'resource']):
            return ErrorCategory.RESOURCE_EXHAUSTION
        else:
            return ErrorCategory.FILE_SYSTEM  # Default
    
    def _determine_severity(self, error: Exception) -> ErrorSeverity:
        """Determine error severity based on type and context"""
        error_msg = str(error).lower()
        
        # Critical errors that should stop the service
        if any(keyword in error_msg for keyword in ['critical', 'fatal', 'corrupt']):
            return ErrorSeverity.CRITICAL
        
        # High severity errors
        if any(keyword in error_msg for keyword in ['failed', 'error', 'exception']):
            return ErrorSeverity.HIGH
        
        # Medium severity errors
        if any(keyword in error_msg for keyword in ['warning', 'timeout', 'retry']):
            return ErrorSeverity.MEDIUM
        
        # Low severity errors
        return ErrorSeverity.LOW
    
    def _log_error(self, error: LoopGuardError, context: Dict[str, Any]) -> None:
        """Log error with full context"""
        log_data = {
            'error_type': type(error.cause).__name__ if error.cause else 'LoopGuardError',
            'category': error.category.value,
            'severity': error.severity.value,
            'message': error.message,
            'context': context,
            'traceback': traceback.format_exc() if error.cause else None
        }
        
        if error.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            self.logger.error(f"Error: {json.dumps(log_data, default=str)}")
        elif error.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(f"Warning: {json.dumps(log_data, default=str)}")
        else:
            self.logger.info(f"Info: {json.dumps(log_data, default=str)}")
    
    def _update_error_tracking(self, error: LoopGuardError) -> None:
        """Update error tracking for rate limiting and analysis"""
        error_key = f"{error.category.value}:{type(error.cause).__name__ if error.cause else 'LoopGuardError'}"
        
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        self.last_errors[error_key] = error.timestamp
        
        # Clean old error records (keep last 100)
        if len(self.last_errors) > 100:
            oldest_key = min(self.last_errors.keys(), 
                          key=lambda k: self.last_errors[k])
            del self.last_errors[oldest_key]
    
    def _attempt_recovery(self, error: LoopGuardError, context: Dict[str, Any]) -> bool:
        """Attempt automatic recovery based on error category"""
        try:
            recovery_action = self.recovery_actions.get(error.category)
            if recovery_action:
                return recovery_action(error, context)
        except Exception as recovery_error:
            self.logger.error(f"Recovery failed: {recovery_error}")
            return False
        
        return False
    
    def _send_error_notification(self, error: LoopGuardError, context: Dict[str, Any]) -> None:
        """Send error notification if available"""
        if not self.notification_service:
            return
        
        try:
            # Create a mock alert for error notification
            from .types import LoopAlert
            from datetime import timezone
            
            error_alert = LoopAlert(
                alert_type='system_error',
                session_id='system',
                description=f"LoopGuard Error: {error.category.value}",
                severity=error.severity.value,
                timestamp=datetime.now(timezone.utc),
                evidence={'error_message': error.message, 'context': context},
                suggested_action="Check LoopGuard logs for details"
            )
            
            self.notification_service.send_alert(error_alert)
        except Exception as notify_error:
            self.logger.error(f"Failed to send error notification: {notify_error}")
    
    # Recovery actions for different error categories
    def _recover_file_system(self, error: LoopGuardError, context: Dict[str, Any]) -> bool:
        """Recover from file system errors"""
        self.logger.info("Attempting file system recovery")
        
        # Try to create missing directories
        if 'directory' in context:
            try:
                Path(context['directory']).mkdir(parents=True, exist_ok=True)
                self.logger.info(f"Created directory: {context['directory']}")
                return True
            except Exception:
                pass
        
        # Check permissions
        if 'file_path' in context:
            try:
                file_path = Path(context['file_path'])
                if not file_path.parent.exists():
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    self.logger.info(f"Created parent directory for: {file_path}")
                    return True
            except Exception:
                pass
        
        return False
    
    def _recover_network(self, error: LoopGuardError, context: Dict[str, Any]) -> bool:
        """Recover from network errors"""
        self.logger.info("Network error - will retry on next operation")
        # Network errors are typically transient, just log and continue
        return True
    
    def _recover_configuration(self, error: LoopGuardError, context: Dict[str, Any]) -> bool:
        """Recover from configuration errors"""
        self.logger.info("Configuration error - using defaults")
        
        # Reset to default configuration
        if 'config_path' in context:
            try:
                config_path = Path(context['config_path'])
                if config_path.exists():
                    backup_path = config_path.with_suffix('.backup.json')
                    config_path.rename(backup_path)
                    self.logger.info(f"Backed up config to: {backup_path}")
                return True
            except Exception:
                pass
        
        return False
    
    def _recover_notification(self, error: LoopGuardError, context: Dict[str, Any]) -> bool:
        """Recover from notification errors"""
        self.logger.info("Notification system error - disabling notifications temporarily")
        
        # Disable notifications temporarily
        if self.notification_service:
            self.fallback_modes[ErrorCategory.NOTIFICATION] = True
            self.logger.info("Notifications disabled - will retry in 10 minutes")
        
        # Schedule re-enable
        import threading
        def reenable_notifications() -> None:
            import time
            time.sleep(600)  # 10 minutes
            self.fallback_modes[ErrorCategory.NOTIFICATION] = False
            self.logger.info("Re-enabling notifications")
        
        threading.Thread(target=reenable_notifications, daemon=True).start()
        return True
    
    def _recover_database(self, error: LoopGuardError, context: Dict[str, Any]) -> bool:
        """Recover from database errors"""
        self.logger.info("Database error - attempting recovery")
        
        if 'db_path' in context:
            try:
                db_path = Path(context['db_path'])
                # Try to recreate database
                if db_path.exists():
                    backup_path = db_path.with_suffix('.backup.db')
                    db_path.rename(backup_path)
                    self.logger.info(f"Backed up database to: {backup_path}")
                
                # Database will be recreated on next access
                return True
            except Exception:
                pass
        
        return False
    
    def _recover_process_monitoring(self, error: LoopGuardError, context: Dict[str, Any]) -> bool:
        """Recover from process monitoring errors"""
        self.logger.info("Process monitoring error - resetting monitor")
        # Process monitoring will restart automatically
        return True
    
    def _recover_log_parsing(self, error: LoopGuardError, context: Dict[str, Any]) -> bool:
        """Recover from log parsing errors"""
        self.logger.info("Log parsing error - skipping problematic log entry")
        # Skip problematic log entry and continue
        return True
    
    def _recover_resource_exhaustion(self, error: LoopGuardError, context: Dict[str, Any]) -> bool:
        """Recover from resource exhaustion"""
        self.logger.warning("Resource exhaustion - attempting cleanup")
        
        # Force garbage collection
        import gc
        gc.collect()
        
        # Clear caches if available
        if hasattr(self, '_clear_caches'):
            self._clear_caches()
        
        return True
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get system health status"""
        now = datetime.now()
        
        # Recent errors (last hour)
        recent_errors = {
            key: count for key, count in self.error_counts.items()
            if key in self.last_errors and 
            (now - self.last_errors[key]).total_seconds() < 3600
        }
        
        # Active fallback modes
        active_fallbacks = {
            category.value: active for category, active in self.fallback_modes.items()
            if active
        }
        
        return {
            'error_counts_24h': dict(self.error_counts),
            'recent_errors_1h': recent_errors,
            'active_fallback_modes': active_fallbacks,
            'last_error_time': max(self.last_errors.values()) if self.last_errors else None,
            'total_error_count': sum(self.error_counts.values()),
            'health_score': self._calculate_health_score()
        }
    
    def _calculate_health_score(self) -> float:
        """Calculate overall system health score (0-100)"""
        if not self.error_counts:
            return 100.0
        
        total_errors = sum(self.error_counts.values())
        active_fallbacks = sum(1 for active in self.fallback_modes.values() if active)
        
        # Base score starts at 100
        score = 100.0
        
        # Penalty for errors (more recent errors = higher penalty)
        score -= min(30, total_errors * 2)
        
        # Penalty for active fallback modes
        score -= active_fallbacks * 15
        
        return max(0, score)
    
    def clear_error_history(self) -> None:
        """Clear error history for fresh start"""
        self.error_counts.clear()
        self.last_errors.clear()
        self.logger.info("Error history cleared")
