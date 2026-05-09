"""
Test notification service functionality
"""

import pytest
import tempfile
import time
from unittest.mock import Mock, patch, MagicMock

from loopguard.notifications import NotificationService
from loopguard.loop_detector import Alert


class TestNotificationService:
    """Test notification service"""
    
    def test_notification_service_init(self):
        """Test notification service initialization"""
        service = NotificationService()
        
        assert service.enabled is True
        assert service.throttle_seconds == 30
        assert service.last_notification_time == {}
    
    def test_notification_service_disabled(self):
        """Test notification service when disabled"""
        service = NotificationService(enabled=False)
        
        assert service.enabled is False
        assert service.is_available() is False
    
    def test_notification_availability(self):
        """Test notification availability check"""
        service = NotificationService()
        
        # Mock terminal-notifier check
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            assert service.is_available() is True
            
            mock_run.return_value.returncode = 1
            assert service.is_available() is False
    
    def test_send_alert(self):
        """Test sending alert notifications"""
        service = NotificationService()
        
        # Create test alert
        alert = Alert(
            alert_type='tool_call_loop',
            session_id='test-session',
            description='Test alert',
            severity='medium',
            suggested_action='Try a different approach'
        )
        
        # Mock subprocess call
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            result = service.send_alert(alert)
            
            assert result is True
            mock_run.assert_called_once()
    
    def test_send_alert_disabled(self):
        """Test sending alert when notifications disabled"""
        service = NotificationService(enabled=False)
        
        alert = Alert(
            alert_type='tool_call_loop',
            session_id='test-session',
            description='Test alert',
            severity='medium',
            suggested_action='Try a different approach'
        )
        
        result = service.send_alert(alert)
        assert result is False
    
    def test_notification_throttling(self):
        """Test notification throttling"""
        service = NotificationService(throttle_seconds=1)
        
        alert = Alert(
            alert_type='tool_call_loop',
            session_id='test-session',
            description='Test alert',
            severity='medium',
            suggested_action='Try a different approach'
        )
        
        # Mock subprocess call
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            
            # First notification should succeed
            result1 = service.send_alert(alert)
            assert result1 is True
            assert mock_run.call_count == 1
            
            # Second notification immediately should be throttled
            result2 = service.send_alert(alert)
            assert result2 is False
            assert mock_run.call_count == 1  # No additional call
            
            # Wait for throttle period
            time.sleep(1.1)
            
            # Third notification should succeed
            result3 = service.send_alert(alert)
            assert result3 is True
            assert mock_run.call_count == 2
    
    def test_different_alert_types_not_throttled(self):
        """Test that different alert types are not throttled together"""
        service = NotificationService(throttle_seconds=1)
        
        alert1 = Alert(
            alert_type='tool_call_loop',
            session_id='test-session',
            description='Test alert 1',
            severity='medium',
            suggested_action='Try a different approach'
        )
        
        alert2 = Alert(
            alert_type='error_loop',
            session_id='test-session',
            description='Test alert 2',
            severity='high',
            suggested_action='Check permissions'
        )
        
        # Mock subprocess call
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            
            # Both notifications should succeed (different types)
            result1 = service.send_alert(alert1)
            result2 = service.send_alert(alert2)
            
            assert result1 is True
            assert result2 is True
            assert mock_run.call_count == 2
    
    def test_notification_error_handling(self):
        """Test notification error handling"""
        service = NotificationService()
        
        alert = Alert(
            alert_type='tool_call_loop',
            session_id='test-session',
            description='Test alert',
            severity='medium',
            suggested_action='Try a different approach'
        )
        
        # Mock subprocess call to raise exception
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = Exception("Command failed")
            
            result = service.send_alert(alert)
            assert result is False
    
    def test_custom_notification_message(self):
        """Test custom notification messages"""
        service = NotificationService()
        
        alert = Alert(
            alert_type='tool_call_loop',
            session_id='test-session',
            description='Test alert',
            severity='medium',
            suggested_action='Try a different approach'
        )
        
        # Mock subprocess call
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            
            service.send_alert(alert)
            
            # Check that the notification contains expected elements
            call_args = mock_run.call_args[0][0]
            assert 'LoopGuard' in call_args
            assert 'Test alert' in call_args
    
    def test_notification_sound_option(self):
        """Test notification sound option"""
        service = NotificationService(sound_enabled=True)
        
        alert = Alert(
            alert_type='tool_call_loop',
            session_id='test-session',
            description='Test alert',
            severity='medium',
            suggested_action='Try a different approach'
        )
        
        # Mock subprocess call
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            
            service.send_alert(alert)
            
            # Check that sound is included
            call_args = mock_run.call_args[0][0]
            assert '-sound' in call_args or 'default' in call_args
    
    def test_notification_without_sound(self):
        """Test notification without sound"""
        service = NotificationService(sound_enabled=False)
        
        alert = Alert(
            alert_type='tool_call_loop',
            session_id='test-session',
            description='Test alert',
            severity='medium',
            suggested_action='Try a different approach'
        )
        
        # Mock subprocess call
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            
            service.send_alert(alert)
            
            # Check that sound is not included
            call_args = mock_run.call_args[0][0]
            assert '-sound' not in call_args
    
    def test_queue_status(self):
        """Test notification queue status"""
        service = NotificationService()
        
        status = service.get_queue_status()
        
        assert 'last_notifications' in status
        assert 'throttle_seconds' in status
        assert 'enabled' in status
    
    def test_stop_service(self):
        """Test stopping notification service"""
        service = NotificationService()
        
        # Should not raise any exceptions
        service.stop()
        assert service.enabled is False
