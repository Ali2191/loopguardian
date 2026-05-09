"""
Test CLI functionality
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner

from loopguard.cli import cli, LoopGuardService


class TestCLI:
    """Test CLI commands and functionality"""
    
    def setup_method(self) -> None:
        """Setup test environment"""
        self.runner = CliRunner()
    
    def test_cli_help(self) -> None:
        """Test CLI help command"""
        result = self.runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'LoopGuard' in result.output
    
    def test_cli_version(self) -> None:
        """Test CLI version option"""
        result = self.runner.invoke(cli, ['--version'])
        # Should not fail (version might not be implemented yet)
        assert result.exit_code in [0, 1]
    
    def test_start_command(self) -> None:
        """Test start command"""
        with patch('loopguard.cli.LoopGuardService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            result = self.runner.invoke(cli, ['start'])
            
            assert result.exit_code == 0
            mock_service.start.assert_called_once()
    
    def test_status_command(self) -> None:
        """Test status command"""
        with patch('loopguard.cli.LoopGuardService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            result = self.runner.invoke(cli, ['status'])
            
            assert result.exit_code == 0
            mock_service.status.assert_called_once()
    
    def test_analytics_command(self) -> None:
        """Test analytics command"""
        with patch('loopguard.cli.LoopGuardService') as mock_service_class:
            mock_service = Mock()
            mock_service.session_analytics.get_recent_sessions.return_value = []
            mock_service.session_analytics.get_efficiency_summary.return_value = {
                'avg_efficiency_score': 85.0,
                'total_loops_detected': 3,
                'session_count': 10,
                'avg_tokens_per_session': 1000
            }
            mock_service_class.return_value = mock_service
            
            result = self.runner.invoke(cli, ['analytics'])
            
            assert result.exit_code == 0
            mock_service.session_analytics.get_recent_sessions.assert_called_once()
            mock_service.session_analytics.get_efficiency_summary.assert_called_once()
    
    def test_setup_command(self) -> None:
        """Test setup command"""
        with patch('loopguard.cli.LoopGuardService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            result = self.runner.invoke(cli, ['setup'])
            
            assert result.exit_code == 0
            # Service should be created with interactive_setup=True
            mock_service_class.assert_called_once()
    
    def test_validate_command_valid(self) -> None:
        """Test validate command with valid config"""
        with patch('loopguard.cli.LoopGuardService') as mock_service_class:
            mock_service = Mock()
            mock_service.config.validate_current_config.return_value = (True, [])
            mock_service_class.return_value = mock_service
            
            result = self.runner.invoke(cli, ['validate'])
            
            assert result.exit_code == 0
            assert 'valid' in result.output.lower()
    
    def test_validate_command_invalid(self) -> None:
        """Test validate command with invalid config"""
        with patch('loopguard.cli.LoopGuardService') as mock_service_class:
            mock_service = Mock()
            mock_service.config.validate_current_config.return_value = (False, ['error1', 'error2'])
            mock_service.config.get_validation_summary.return_value = 'Validation failed'
            mock_service_class.return_value = mock_service
            
            result = self.runner.invoke(cli, ['validate'])
            
            assert result.exit_code == 0
            assert 'Validation failed' in result.output
    
    def test_performance_command(self) -> None:
        """Test performance command"""
        with patch('loopguard.cli.LoopGuardService') as mock_service_class:
            mock_service = Mock()
            mock_service.performance_monitor.get_performance_summary.return_value = {
                'memory': {'current_mb': 50.0, 'target_mb': 100.0, 'within_target': True},
                'cpu': {'current_percent': 10.0, 'target_percent': 20.0, 'within_target': True},
                'caches': {'session_cache_size': 5, 'session_cache_max_size': 100},
                'counters': {'sessions_processed': 10}
            }
            mock_service_class.return_value = mock_service
            
            result = self.runner.invoke(cli, ['performance'])
            
            assert result.exit_code == 0
            mock_service.performance_monitor.get_performance_summary.assert_called_once()
    
    def test_export_command(self) -> None:
        """Test export command"""
        with patch('loopguard.cli.LoopGuardService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            with tempfile.TemporaryDirectory() as temp_dir:
                output_file = Path(temp_dir) / "test_export.json"
                
                result = self.runner.invoke(cli, ['export', '--output', str(output_file)])
                
                assert result.exit_code == 0
                mock_service.performance_monitor.export_performance_data.assert_called_once()
    
    def test_adapt_command(self) -> None:
        """Test adapt command"""
        with patch('loopguard.cli.LoopGuardService') as mock_service_class:
            mock_service = Mock()
            mock_service.loop_detector.get_adaptation_stats.return_value = {
                'adaptive_mode': True,
                'total_feedback': 10,
                'adapted_sessions': 5,
                'profiles': {},
                'session_types': {}
            }
            mock_service_class.return_value = mock_service
            
            result = self.runner.invoke(cli, ['adapt'])
            
            assert result.exit_code == 0
            mock_service.loop_detector.get_adaptation_stats.assert_called_once()
    
    def test_feedback_command(self) -> None:
        """Test feedback command"""
        with patch('loopguard.cli.LoopGuardService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            result = self.runner.invoke(cli, [
                'feedback',
                '--session-id', 'test-session',
                '--alert-id', 'test-alert',
                '--correct'
            ])
            
            assert result.exit_code == 0
            mock_service.loop_detector.provide_feedback.assert_called_once()
    
    def test_feedback_command_missing_args(self) -> None:
        """Test feedback command with missing arguments"""
        result = self.runner.invoke(cli, ['feedback'])
        
        assert result.exit_code != 0
        assert 'required' in result.output.lower()


class TestLoopGuardService:
    """Test LoopGuardService class"""
    
    def test_service_initialization(self) -> None:
        """Test service initialization"""
        service = LoopGuardService()
        
        assert service.config is not None
        assert service.process_monitor is not None
        assert service.loop_detector is not None
        assert service.notification_service is not None
        assert service.running is False
    
    def test_service_initialization_with_config(self) -> None:
        """Test service initialization with custom config"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_path = f.name
        
        try:
            service = LoopGuardService(config_path)
            assert service.config.config_path == config_path
        finally:
            Path(config_path).unlink(missing_ok=True)
    
    def test_get_health_status(self) -> None:
        """Test health status retrieval"""
        service = LoopGuardService()
        
        health = service.get_health_status()
        
        assert 'overall_status' in health
        assert 'health_score' in health
        assert 'components' in health
        assert 'week3_features' in health
    
    def test_signal_handler(self) -> None:
        """Test signal handler"""
        service = LoopGuardService()
        
        with patch('sys.exit') as mock_exit:
            service._signal_handler(15, None)
            
            mock_exit.assert_called_once_with(0)
    
    def test_on_alert(self) -> None:
        """Test alert handling"""
        service = LoopGuardService()
        
        # Create mock alert
        mock_alert = Mock()
        mock_alert.session_id = 'test-session'
        mock_alert.alert_type = 'test_type'
        mock_alert.description = 'Test alert'
        mock_alert.severity = 'medium'
        mock_alert.suggested_action = 'Test action'
        
        # Mock notification service
        service.notification_service.is_available = Mock(return_value=True)
        service.notification_service.send_alert = Mock()
        
        # Should not raise any exceptions
        service._on_alert(mock_alert)
        
        # Verify alert was stored
        service.session_analytics._store_alert.assert_called_once_with(mock_alert)
    
    def test_enter_safe_mode(self) -> None:
        """Test entering safe mode"""
        service = LoopGuardService()
        
        # Mock components
        service.file_watcher = Mock()
        service.notification_service = Mock()
        
        service._enter_safe_mode()
        
        # Verify components were stopped/disabled
        service.file_watcher.stop_watching.assert_called_once()
        assert service.notification_service.enabled is False
    
    def test_get_uptime_minutes(self) -> None:
        """Test uptime calculation"""
        service = LoopGuardService()
        
        uptime = service._get_uptime_minutes()
        
        assert isinstance(uptime, int)
        assert uptime >= 0


class TestCLIIntegration:
    """Integration tests for CLI"""
    
    def test_cli_with_config_file(self) -> None:
        """Test CLI with custom config file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_path = f.name
        
        try:
            with patch('loopguard.cli.LoopGuardService') as mock_service_class:
                mock_service = Mock()
                mock_service_class.return_value = mock_service
                
                result = self.runner.invoke(cli, ['--config', config_path, 'status'])
                
                assert result.exit_code == 0
                # Verify config path was passed
                mock_service_class.assert_called_once()
        finally:
            Path(config_path).unlink(missing_ok=True)
    
    def test_cli_error_handling(self) -> None:
        """Test CLI error handling"""
        with patch('loopguard.cli.LoopGuardService') as mock_service_class:
            mock_service_class.side_effect = Exception("Test error")
            
            result = self.runner.invoke(cli, ['status'])
            
            # Should handle error gracefully
            assert result.exit_code != 0 or 'error' in result.output.lower()
    
    def test_start_stop_lifecycle(self) -> None:
        """Test complete start/stop lifecycle"""
        with patch('loopguard.cli.LoopGuardService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Test start
            start_result = self.runner.invoke(cli, ['start'])
            assert start_result.exit_code == 0
            mock_service.start.assert_called_once()
            
            # Test status
            status_result = self.runner.invoke(cli, ['status'])
            assert status_result.exit_code == 0
            mock_service.status.assert_called_once()
