"""
Test configuration management functionality
"""

import pytest
import tempfile
import yaml
import json
from pathlib import Path

from loopguard.config import Config


class TestConfig:
    """Test configuration management"""
    
    def test_default_config_creation(self):
        """Test creating default configuration"""
        config = Config()
        
        assert config.get('detection.tool_call_repeats') == 3
        assert config.get('detection.error_repeats') == 2
        assert config.get('detection.stagnation_minutes') == 5
        assert config.get('notifications.enabled') is True
        assert config.get('notifications.throttle_seconds') == 30
    
    def test_config_from_file(self):
        """Test loading configuration from file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_data = {
                'detection': {
                    'tool_call_repeats': 5,
                    'error_repeats': 3,
                    'stagnation_minutes': 10
                },
                'notifications': {
                    'enabled': False,
                    'throttle_seconds': 60
                }
            }
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            config = Config(config_path)
            
            assert config.get('detection.tool_call_repeats') == 5
            assert config.get('detection.error_repeats') == 3
            assert config.get('detection.stagnation_minutes') == 10
            assert config.get('notifications.enabled') is False
            assert config.get('notifications.throttle_seconds') == 60
        finally:
            Path(config_path).unlink(missing_ok=True)
    
    def test_config_from_json(self):
        """Test loading configuration from JSON file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_data = {
                'detection': {
                    'tool_call_repeats': 4,
                    'error_repeats': 2,
                    'stagnation_minutes': 7
                }
            }
            json.dump(config_data, f)
            config_path = f.name
        
        try:
            config = Config(config_path)
            
            assert config.get('detection.tool_call_repeats') == 4
            assert config.get('detection.error_repeats') == 2
            assert config.get('detection.stagnation_minutes') == 7
        finally:
            Path(config_path).unlink(missing_ok=True)
    
    def test_config_validation(self):
        """Test configuration validation"""
        config = Config()
        
        # Valid configuration
        is_valid, errors = config.validate_current_config()
        assert is_valid is True
        assert len(errors) == 0
        
        # Invalid configuration
        config.set('detection.tool_call_repeats', -1)
        config.set('notifications.throttle_seconds', -5)
        
        is_valid, errors = config.validate_current_config()
        assert is_valid is False
        assert len(errors) > 0
    
    def test_config_set_get(self):
        """Test setting and getting configuration values"""
        config = Config()
        
        # Test setting values
        config.set('detection.tool_call_repeats', 10)
        config.set('notifications.enabled', False)
        
        # Test getting values
        assert config.get('detection.tool_call_repeats') == 10
        assert config.get('notifications.enabled') is False
        
        # Test default values
        assert config.get('nonexistent.key', 'default') == 'default'
        assert config.get('nonexistent.key') is None
    
    def test_config_save(self):
        """Test saving configuration to file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.yaml"
            
            config = Config()
            config.set('detection.tool_call_repeats', 8)
            config.set('test.value', 'test_data')
            
            config.save(str(config_path))
            
            # Load and verify
            new_config = Config(str(config_path))
            assert new_config.get('detection.tool_call_repeats') == 8
            assert new_config.get('test.value') == 'test_data'
    
    def test_interactive_setup(self):
        """Test interactive configuration setup"""
        config = Config()
        
        # Test that interactive setup doesn't crash
        try:
            config.interactive_setup()
        except (KeyboardInterrupt, EOFError):
            # Expected when running in non-interactive environment
            pass
    
    def test_config_merge(self):
        """Test configuration merging"""
        config = Config()
        
        # Merge partial configuration
        merge_data = {
            'detection': {
                'tool_call_repeats': 7
            },
            'new_section': {
                'new_value': 'test'
            }
        }
        
        config.merge(merge_data)
        
        assert config.get('detection.tool_call_repeats') == 7
        assert config.get('new_section.new_value') == 'test'
        # Other values should remain
        assert config.get('detection.error_repeats') == 2
    
    def test_config_environment_override(self):
        """Test environment variable overrides"""
        import os
        
        try:
            # Set environment variable
            os.environ['LOOPGUARD_DETECTION_TOOL_CALL_REPEATS'] = '15'
            
            config = Config()
            # Should use environment override
            assert config.get('detection.tool_call_repeats') == 15
            
        finally:
            # Clean up
            os.environ.pop('LOOPGUARD_DETECTION_TOOL_CALL_REPEATS', None)
    
    def test_config_type_validation(self):
        """Test type validation for configuration values"""
        config = Config()
        
        # Valid types
        config.set('detection.tool_call_repeats', 5)  # int
        config.set('notifications.enabled', True)     # bool
        config.set('test.string', 'test')             # str
        
        # Invalid types should be converted or rejected
        config.set('detection.tool_call_repeats', '10')  # string to int
        assert config.get('detection.tool_call_repeats') == 10
        
        config.set('notifications.enabled', 'true')     # string to bool
        assert config.get('notifications.enabled') is True
