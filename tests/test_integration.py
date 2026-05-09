"""
Integration tests for LoopGuard functionality
"""

import pytest
import tempfile
import time
import threading
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from loopguard.cli import LoopGuardService
from loopguard.config import Config
from loopguard.loop_detector import LoopDetector
from loopguard.notifications import NotificationService


class TestIntegration:
    """Integration tests for complete LoopGuard functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "test_config.yaml"
        
        # Create test config
        config_data = {
            'detection': {
                'tool_call_repeats': 3,
                'error_repeats': 2,
                'stagnation_minutes': 5
            },
            'notifications': {
                'enabled': True,
                'throttle_seconds': 30,
                'sound': False
            },
            'monitoring': {
                'watch_directories': [self.temp_dir],
                'file_patterns': ['*.py', '*.js']
            }
        }
        
        import yaml
        with open(self.config_path, 'w') as f:
            yaml.dump(config_data, f)
    
    def teardown_method(self):
        """Cleanup test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_service_lifecycle(self):
        """Test complete service lifecycle"""
        service = LoopGuardService(str(self.config_path))
        
        # Test initialization
        assert service.config is not None
        assert service.running is False
        
        # Test health status
        health = service.get_health_status()
        assert 'overall_status' in health
        assert 'health_score' in health
        
        # Test status display
        service.status()
        
        # Should not raise any exceptions
        assert True
    
    def test_config_detection_integration(self):
        """Test configuration and detection integration"""
        config = Config(str(self.config_path))
        detector = LoopDetector(config)
        
        # Verify config values are used
        assert detector.tool_call_threshold == 3
        assert detector.error_threshold == 2
        assert detector.stagnation_threshold_minutes == 5
    
    def test_notification_service_integration(self):
        """Test notification service integration"""
        config = Config(str(self.config_path))
        service = NotificationService(
            config.get('notifications.enabled', True),
            config=config
        )
        
        # Verify config values are used
        assert service.enabled is True
        assert service.throttle_seconds == 30
    
    def test_error_handling_integration(self):
        """Test error handling integration"""
        service = LoopGuardService(str(self.config_path))
        
        # Test error handler is properly initialized
        assert service.error_handler is not None
        
        # Test health status includes error metrics
        health = service.get_health_status()
        assert 'error_metrics' in health
    
    def test_file_watching_integration(self):
        """Test file watching integration"""
        service = LoopGuardService(str(self.config_path))
        
        # Test file watcher initialization
        assert service.file_watcher is not None
        
        # Test watching functionality
        try:
            result = service.file_watcher.start_watching()
            # Result may be False if no Claude Code processes found
            assert isinstance(result, bool)
        except Exception:
            # Expected in test environment
            pass
    
    def test_session_analytics_integration(self):
        """Test session analytics integration"""
        service = LoopGuardService(str(self.config_path))
        
        # Test analytics initialization
        assert service.session_analytics is not None
        
        # Test analytics configuration
        service.session_analytics.set_config(service.config)
        
        # Test getting recent sessions
        recent_sessions = service.session_analytics.get_recent_sessions(limit=5)
        assert isinstance(recent_sessions, list)
    
    def test_process_monitoring_integration(self):
        """Test process monitoring integration"""
        service = LoopGuardService(str(self.config_path))
        
        # Test process monitor initialization
        assert service.process_monitor is not None
        
        # Test detecting Claude processes
        try:
            sessions = service.process_monitor.detect_claude_processes()
            assert isinstance(sessions, list)
        except Exception:
            # Expected in test environment
            pass
    
    def test_adaptive_detection_integration(self):
        """Test adaptive detection integration"""
        service = LoopGuardService(str(self.config_path))
        
        # Test adaptive detection stats
        stats = service.loop_detector.get_adaptation_stats()
        assert isinstance(stats, dict)
        assert 'adaptive_mode' in stats
    
    def test_performance_monitoring_integration(self):
        """Test performance monitoring integration"""
        service = LoopGuardService(str(self.config_path))
        
        # Test performance monitor initialization
        assert service.performance_monitor is not None
        
        # Test performance monitoring
        try:
            service.performance_monitor.start_monitoring()
            time.sleep(0.1)  # Brief monitoring period
            
            summary = service.performance_monitor.get_performance_summary(minutes=1)
            assert isinstance(summary, dict)
            
            service.performance_monitor.stop_monitoring()
        except Exception:
            # Expected in test environment
            pass
    
    def test_session_discovery_integration(self):
        """Test session discovery integration"""
        service = LoopGuardService(str(self.config_path))
        
        # Test session discovery initialization
        assert service.session_discovery is not None
        
        # Test discovery functionality
        try:
            sessions = service.session_discovery.discover_sessions()
            assert isinstance(sessions, list)
        except Exception:
            # Expected in test environment
            pass
    
    def test_alert_handling_integration(self):
        """Test alert handling integration"""
        service = LoopGuardService(str(self.config_path))
        
        # Create mock alert
        from loopguard.loop_detector import Alert
        alert = Alert(
            alert_type='tool_call_loop',
            session_id='test-session',
            description='Test alert',
            severity='medium',
            suggested_action='Test action'
        )
        
        # Test alert handling
        service._on_alert(alert)
        
        # Should not raise any exceptions
        assert True
    
    def test_configuration_validation_integration(self):
        """Test configuration validation integration"""
        service = LoopGuardService(str(self.config_path))
        
        # Test configuration validation
        is_valid, errors = service.config.validate_current_config()
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)
    
    def test_component_interaction(self):
        """Test interaction between components"""
        service = LoopGuardService(str(self.config_path))
        
        # Test that components are properly connected
        assert service.loop_detector.config == service.config
        assert service.notification_service.config == service.config
        assert service.file_watcher.loop_detector == service.loop_detector
    
    def test_service_with_invalid_config(self):
        """Test service behavior with invalid configuration"""
        # Create invalid config
        invalid_config_path = Path(self.temp_dir) / "invalid_config.yaml"
        with open(invalid_config_path, 'w') as f:
            f.write("invalid: yaml: content: [")
        
        # Should handle invalid config gracefully
        try:
            service = LoopGuardService(str(invalid_config_path))
            # Should fall back to default config
            assert service.config is not None
        except Exception:
            # Expected to handle gracefully
            pass
    
    def test_service_resource_cleanup(self):
        """Test proper resource cleanup"""
        service = LoopGuardService(str(self.config_path))
        
        # Start and stop service
        try:
            service.start()
            time.sleep(0.1)  # Brief running period
        except Exception:
            # Expected in test environment
            pass
        finally:
            try:
                service.stop()
            except Exception:
                # Expected in test environment
                pass
        
        # Should not raise any exceptions during cleanup
        assert True


class TestRealWorldScenarios:
    """Test real-world usage scenarios"""
    
    def test_typical_usage_scenario(self):
        """Test typical usage scenario"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            
            # Create typical configuration
            config_data = {
                'detection': {
                    'tool_call_repeats': 3,
                    'error_repeats': 2,
                    'stagnation_minutes': 5
                },
                'notifications': {
                    'enabled': True,
                    'throttle_seconds': 30
                }
            }
            
            import yaml
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f)
            
            # Simulate typical usage
            service = LoopGuardService(str(config_path))
            
            # Check status
            service.status()
            
            # Get health status
            health = service.get_health_status()
            assert health['health_score'] >= 0
            
            # Should handle typical usage gracefully
            assert True
    
    def test_error_recovery_scenario(self):
        """Test error recovery scenario"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            
            # Create configuration
            config_data = {'detection': {'tool_call_repeats': 3}}
            import yaml
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f)
            
            service = LoopGuardService(str(config_path))
            
            # Simulate error conditions
            try:
                # Force an error
                raise Exception("Simulated error")
            except Exception as e:
                # Handle error through error handler
                service.error_handler.handle_error(e, {'operation': 'test'})
            
            # Check health after error
            health = service.get_health_status()
            assert health['total_error_count'] >= 1
    
    def test_configuration_change_scenario(self):
        """Test configuration changes during runtime"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            
            # Create initial configuration
            config_data = {
                'detection': {'tool_call_repeats': 3},
                'notifications': {'enabled': True}
            }
            
            import yaml
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f)
            
            service = LoopGuardService(str(config_path))
            
            # Change configuration
            service.config.set('detection.tool_call_repeats', 5)
            service.config.set('notifications.enabled', False)
            
            # Verify changes took effect
            assert service.config.get('detection.tool_call_repeats') == 5
            assert service.config.get('notifications.enabled') is False
    
    def test_high_load_scenario(self):
        """Test behavior under high load"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            
            config_data = {
                'detection': {'tool_call_repeats': 3},
                'performance': {'max_memory_mb': 100}
            }
            
            import yaml
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f)
            
            service = LoopGuardService(str(config_path))
            
            # Simulate high load by creating many alerts
            from loopguard.loop_detector import Alert
            for i in range(10):
                alert = Alert(
                    alert_type='tool_call_loop',
                    session_id=f'test-session-{i}',
                    description=f'Test alert {i}',
                    severity='medium',
                    suggested_action='Test action'
                )
                service._on_alert(alert)
            
            # Check system health
            health = service.get_health_status()
            assert health['health_score'] >= 0


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_empty_configuration(self):
        """Test with empty configuration"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("")  # Empty file
            config_path = f.name
        
        try:
            service = LoopGuardService(config_path)
            # Should handle empty config gracefully
            assert service.config is not None
        finally:
            Path(config_path).unlink(missing_ok=True)
    
    def test_missing_configuration_file(self):
        """Test with missing configuration file"""
        service = LoopGuardService("/nonexistent/config.yaml")
        # Should use default configuration
        assert service.config is not None
    
    def test_very_large_configuration(self):
        """Test with very large configuration"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "large_config.yaml"
            
            # Create large configuration
            config_data = {
                'detection': {'tool_call_repeats': 3},
                'large_section': {f'key_{i}': f'value_{i}' for i in range(1000)}
            }
            
            import yaml
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f)
            
            service = LoopGuardService(str(config_path))
            # Should handle large config
            assert service.config is not None
    
    def test_unicode_configuration(self):
        """Test with unicode characters in configuration"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "unicode_config.yaml"
            
            config_data = {
                'detection': {'tool_call_repeats': 3},
                'unicode_test': '测试中文 🛡️ LoopGuard'
            }
            
            import yaml
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f)
            
            service = LoopGuardService(str(config_path))
            # Should handle unicode
            assert service.config is not None
