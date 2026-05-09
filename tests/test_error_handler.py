"""
Test error handler functionality
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from loopguard.error_handler import ErrorHandler, LoopGuardError, ErrorCategory, ErrorSeverity


class TestErrorHandler:
    """Test error handler functionality"""
    
    def test_error_handler_initialization(self):
        """Test error handler initialization"""
        mock_notification_service = Mock()
        handler = ErrorHandler(mock_notification_service)
        
        assert handler.notification_service == mock_notification_service
        assert len(handler.error_history) == 0
        assert len(handler.active_fallback_modes) == 0
    
    def test_handle_error_with_notification(self):
        """Test handling error with notification"""
        mock_notification_service = Mock()
        handler = ErrorHandler(mock_notification_service)
        
        error = Exception("Test error")
        context = {'operation': 'test_operation', 'component': 'test_component'}
        
        result = handler.handle_error(error, context)
        
        assert result is True
        assert len(handler.error_history) == 1
        
        # Should send notification for critical errors
        mock_notification_service.send_alert.assert_called()
    
    def test_handle_error_without_notification(self):
        """Test handling error without notification"""
        mock_notification_service = Mock()
        handler = ErrorHandler(mock_notification_service)
        
        error = Exception("Test error")
        context = {'operation': 'test_operation', 'component': 'test_component'}
        
        result = handler.handle_error(error, context, notify=False)
        
        assert result is True
        assert len(handler.error_history) == 1
        
        # Should not send notification
        mock_notification_service.send_alert.assert_not_called()
    
    def test_handle_loop_guard_error(self):
        """Test handling LoopGuard specific errors"""
        mock_notification_service = Mock()
        handler = ErrorHandler(mock_notification_service)
        
        error = LoopGuardError(
            "Test LoopGuard error",
            ErrorCategory.FILE_SYSTEM,
            ErrorSeverity.HIGH
        )
        context = {'operation': 'file_operation'}
        
        result = handler.handle_error(error, context)
        
        assert result is True
        assert len(handler.error_history) == 1
        
        # Should handle LoopGuard errors appropriately
        mock_notification_service.send_alert.assert_called()
    
    def test_consecutive_error_handling(self):
        """Test handling consecutive errors"""
        mock_notification_service = Mock()
        handler = ErrorHandler(mock_notification_service)
        
        error = Exception("Test error")
        context = {'operation': 'test_operation'}
        
        # Handle multiple errors
        for i in range(3):
            handler.handle_error(error, context)
        
        assert len(handler.error_history) == 3
        
        # Should activate fallback mode after consecutive errors
        assert len(handler.active_fallback_modes) > 0
    
    def test_get_health_status(self):
        """Test health status calculation"""
        mock_notification_service = Mock()
        handler = ErrorHandler(mock_notification_service)
        
        # Add some errors
        handler.handle_error(Exception("Test error"), {'operation': 'test'})
        handler.handle_error(Exception("Test error"), {'operation': 'test'})
        
        health = handler.get_health_status()
        
        assert 'health_score' in health
        assert 'total_error_count' in health
        assert 'recent_errors_1h' in health
        assert 'active_fallback_modes' in health
        assert health['total_error_count'] == 2
    
    def test_get_health_status_no_errors(self):
        """Test health status with no errors"""
        mock_notification_service = Mock()
        handler = ErrorHandler(mock_notification_service)
        
        health = handler.get_health_status()
        
        assert health['health_score'] == 100
        assert health['total_error_count'] == 0
        assert len(health['recent_errors_1h']) == 0
        assert len(health['active_fallback_modes']) == 0
    
    def test_fallback_mode_activation(self):
        """Test fallback mode activation"""
        mock_notification_service = Mock()
        handler = ErrorHandler(mock_notification_service)
        
        error = Exception("Test error")
        context = {'operation': 'test_operation', 'component': 'test_component'}
        
        # Trigger fallback mode
        for i in range(5):  # Enough to trigger fallback
            handler.handle_error(error, context)
        
        assert len(handler.active_fallback_modes) > 0
        
        # Check fallback mode details
        fallback_modes = list(handler.active_fallback_modes.keys())
        assert any('test_component' in mode for mode in fallback_modes)
    
    def test_error_categorization(self):
        """Test automatic error categorization"""
        mock_notification_service = Mock()
        handler = ErrorHandler(mock_notification_service)
        
        # Test different error types
        file_error = FileNotFoundError("File not found")
        permission_error = PermissionError("Permission denied")
        network_error = ConnectionError("Network error")
        
        handler.handle_error(file_error, {'operation': 'file_read'})
        handler.handle_error(permission_error, {'operation': 'file_write'})
        handler.handle_error(network_error, {'operation': 'api_call'})
        
        assert len(handler.error_history) == 3
        
        # Check categorization
        file_error_entry = handler.error_history[0]
        assert file_error_entry['category'] == ErrorCategory.FILE_SYSTEM
        
        permission_error_entry = handler.error_history[1]
        assert permission_error_entry['category'] == ErrorCategory.PERMISSIONS
        
        network_error_entry = handler.error_history[2]
        assert network_error_entry['category'] == ErrorCategory.NETWORK
    
    def test_error_severity_assignment(self):
        """Test error severity assignment"""
        mock_notification_service = Mock()
        handler = ErrorHandler(mock_notification_service)
        
        # Test different severities
        critical_error = LoopGuardError("Critical error", ErrorCategory.SYSTEM, ErrorSeverity.CRITICAL)
        high_error = LoopGuardError("High severity error", ErrorCategory.FILE_SYSTEM, ErrorSeverity.HIGH)
        low_error = Exception("Low severity error")
        
        handler.handle_error(critical_error, {'operation': 'system_op'})
        handler.handle_error(high_error, {'operation': 'file_op'})
        handler.handle_error(low_error, {'operation': 'minor_op'})
        
        assert len(handler.error_history) == 3
        
        # Check severity assignment
        critical_entry = handler.error_history[0]
        assert critical_entry['severity'] == ErrorSeverity.CRITICAL
        
        high_entry = handler.error_history[1]
        assert high_entry['severity'] == ErrorSeverity.HIGH
        
        low_entry = handler.error_history[2]
        assert low_entry['severity'] == ErrorSeverity.LOW
    
    def test_recent_errors_filtering(self):
        """Test filtering of recent errors"""
        mock_notification_service = Mock()
        handler = ErrorHandler(mock_notification_service)
        
        # Add errors with different timestamps
        import time
        from datetime import datetime, timedelta
        
        now = datetime.now()
        old_time = now - timedelta(hours=2)
        
        # Mock timestamp for first error
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = old_time
            handler.handle_error(Exception("Old error"), {'operation': 'test'})
        
        # Add recent error
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = now
            handler.handle_error(Exception("Recent error"), {'operation': 'test'})
        
        health = handler.get_health_status()
        
        # Should only count recent error
        assert len(health['recent_errors_1h']) == 1
    
    def test_error_context_validation(self):
        """Test error context validation"""
        mock_notification_service = Mock()
        handler = ErrorHandler(mock_notification_service)
        
        error = Exception("Test error")
        
        # Test with valid context
        valid_context = {'operation': 'test_op', 'component': 'test_comp'}
        result = handler.handle_error(error, valid_context)
        assert result is True
        
        # Test with invalid context (missing required fields)
        invalid_context = {}
        result = handler.handle_error(error, invalid_context)
        assert result is True  # Should still handle, just with default context
    
    def test_notification_error_handling(self):
        """Test handling errors in notification sending"""
        mock_notification_service = Mock()
        mock_notification_service.send_alert.side_effect = Exception("Notification failed")
        
        handler = ErrorHandler(mock_notification_service)
        
        error = LoopGuardError("Test error", ErrorCategory.SYSTEM, ErrorSeverity.HIGH)
        result = handler.handle_error(error, {'operation': 'test'})
        
        # Should still handle the error even if notification fails
        assert result is True
        assert len(handler.error_history) == 1


class TestLoopGuardError:
    """Test LoopGuard error class"""
    
    def test_loop_guard_error_creation(self):
        """Test LoopGuard error creation"""
        error = LoopGuardError(
            "Test message",
            ErrorCategory.FILE_SYSTEM,
            ErrorSeverity.HIGH
        )
        
        assert str(error) == "Test message"
        assert error.category == ErrorCategory.FILE_SYSTEM
        assert error.severity == ErrorSeverity.HIGH
    
    def test_loop_guard_error_with_context(self):
        """Test LoopGuard error with additional context"""
        error = LoopGuardError(
            "Test message",
            ErrorCategory.NETWORK,
            ErrorSeverity.MEDIUM,
            context={'retry_count': 3, 'timeout': 30}
        )
        
        assert error.context['retry_count'] == 3
        assert error.context['timeout'] == 30
    
    def test_loop_guard_error_inheritance(self):
        """Test that LoopGuardError inherits from Exception"""
        error = LoopGuardError("Test", ErrorCategory.SYSTEM, ErrorSeverity.LOW)
        
        assert isinstance(error, Exception)
        assert isinstance(error, BaseException)
