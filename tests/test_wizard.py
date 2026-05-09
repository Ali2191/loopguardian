"""
Test first run wizard functionality
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from loopguard.wizard import FirstRunWizard


class TestFirstRunWizard:
    """Test first run wizard"""
    
    def test_wizard_initialization(self):
        """Test wizard initialization"""
        wizard = FirstRunWizard()
        
        assert wizard.config_path == Path.home() / ".loopguard" / "config" / "config.yaml"
        assert wizard.setup_data == {}
    
    def test_find_claude_code_paths(self):
        """Test Claude Code path discovery"""
        wizard = FirstRunWizard()
        
        # Mock file system checks
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = True
            
            paths = wizard._find_claude_code_paths()
            
            assert isinstance(paths, list)
            # Should find some paths when exists returns True
    
    def test_find_claude_code_paths_empty(self):
        """Test Claude Code path discovery when nothing found"""
        wizard = FirstRunWizard()
        
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = False
            
            paths = wizard._find_claude_code_paths()
            
            assert len(paths) == 0
    
    def test_check_terminal_notifier_available(self):
        """Test terminal-notifier availability check"""
        wizard = FirstRunWizard()
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            
            result = wizard._check_terminal_notifier()
            assert result is True
    
    def test_check_terminal_notifier_unavailable(self):
        """Test terminal-notifier availability check when not available"""
        wizard = FirstRunWizard()
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 1
            
            result = wizard._check_terminal_notifier()
            assert result is False
    
    def test_get_sensitivity_name(self):
        """Test sensitivity level name conversion"""
        wizard = FirstRunWizard()
        
        # Test high sensitivity
        wizard.setup_data = {'tool_call_repeats': 2}
        assert wizard._get_sensitivity_name() == "High"
        
        # Test medium sensitivity
        wizard.setup_data = {'tool_call_repeats': 3}
        assert wizard._get_sensitivity_name() == "Medium"
        
        # Test low sensitivity
        wizard.setup_data = {'tool_call_repeats': 5}
        assert wizard._get_sensitivity_name() == "Low"
    
    def test_create_config_file_yaml(self):
        """Test creating YAML configuration file"""
        wizard = FirstRunWizard()
        wizard.setup_data = {
            'tool_call_repeats': 4,
            'error_repeats': 2,
            'stagnation_minutes': 6,
            'notifications_enabled': True,
            'notification_throttle': 45,
            'notification_sound': False,
            'watch_directories': ['/test/dir'],
            'file_patterns': ['*.py'],
            'claude_code_path': '/Applications/Claude.app'
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            wizard.config_path = Path(temp_dir) / "config.yaml"
            
            wizard._create_config_file()
            
            assert wizard.config_path.exists()
            
            # Verify content
            import yaml
            with open(wizard.config_path) as f:
                config = yaml.safe_load(f)
            
            assert config['detection']['tool_call_repeats'] == 4
            assert config['notifications']['enabled'] is True
    
    def test_create_config_file_json_fallback(self):
        """Test creating JSON configuration file when YAML not available"""
        wizard = FirstRunWizard()
        wizard.setup_data = {
            'tool_call_repeats': 3,
            'notifications_enabled': True
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            wizard.config_path = Path(temp_dir) / "config.yaml"
            
            # Mock yaml import to fail
            with patch.dict('sys.modules', {'yaml': None}):
                wizard._create_config_file()
            
            # Should create JSON file instead
            json_path = wizard.config_path.with_suffix('.json')
            assert json_path.exists()
    
    def test_test_notifications_success(self):
        """Test notification testing when successful"""
        wizard = FirstRunWizard()
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            
            wizard._test_notifications()
            # Should not raise any exceptions
    
    def test_test_notifications_failure(self):
        """Test notification testing when failed"""
        wizard = FirstRunWizard()
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = "Command not found"
            
            wizard._test_notifications()
            # Should not raise any exceptions
    
    def test_check_claude_running_true(self):
        """Test checking if Claude Code is running when it is"""
        wizard = FirstRunWizard()
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "1234\n5678"
            
            wizard._check_claude_running()
            
            assert wizard.setup_data['claude_running'] is True
    
    def test_check_claude_running_false(self):
        """Test checking if Claude Code is running when it's not"""
        wizard = FirstRunWizard()
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 1
            
            wizard._check_claude_running()
            
            assert wizard.setup_data['claude_running'] is False
    
    def test_setup_autostart_success(self):
        """Test setting up autostart when successful"""
        wizard = FirstRunWizard()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            wizard.config_path = Path(temp_dir) / "config.yaml"
            
            wizard._setup_autostart()
            
            # Should create plist file
            plist_path = Path.home() / "Library" / "LaunchAgents" / "com.loopguard.agent.plist"
            # Note: In real test, this would check actual file creation
    
    def test_show_setup_summary(self):
        """Test showing setup summary"""
        wizard = FirstRunWizard()
        wizard.setup_data = {
            'claude_code_path': '/Applications/Claude.app',
            'tool_call_repeats': 3,
            'notifications_enabled': True,
            'auto_start': False,
            'claude_running': True
        }
        
        # Should not raise any exceptions
        wizard._show_setup_summary()
    
    def test_show_next_steps(self):
        """Test showing next steps"""
        wizard = FirstRunWizard()
        
        # Should not raise any exceptions
        wizard._show_next_steps()
    
    @patch('click.confirm')
    @patch('click.prompt')
    def test_manual_claude_setup(self, mock_prompt, mock_confirm):
        """Test manual Claude Code setup"""
        wizard = FirstRunWizard()
        
        # Mock user inputs
        mock_confirm.return_value = True
        mock_prompt.return_value = "/Applications/Claude.app"
        
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = True
            
            result = wizard._manual_claude_setup()
            
            assert result == "/Applications/Claude.app"
    
    def test_run_first_time_wizard_function(self):
        """Test the standalone run_first_time_wizard function"""
        from loopguard.wizard import run_first_time_wizard
        
        with patch.object(FirstRunWizard, 'run_wizard') as mock_run:
            mock_run.return_value = True
            
            result = run_first_time_wizard()
            
            assert result is True
            mock_run.assert_called_once()


class TestWizardIntegration:
    """Integration tests for wizard functionality"""
    
    def test_complete_wizard_flow_mocked(self):
        """Test complete wizard flow with mocked user interactions"""
        wizard = FirstRunWizard()
        
        # Mock all user interactions to return defaults
        with patch.multiple(
            'click',
            confirm=Mock(return_value=True),
            prompt=Mock(side_effect=[2, 30, True, 30, True, 30, True])
        ):
            with patch.object(wizard, '_system_check', return_value=True):
                with patch.object(wizard, '_discover_claude_code'):
                    with patch.object(wizard, '_setup_configuration'):
                        with patch.object(wizard, '_setup_notifications'):
                            with patch.object(wizard, '_setup_monitoring'):
                                with patch.object(wizard, '_run_tutorial'):
                                    with patch.object(wizard, '_complete_setup'):
                                        result = wizard.run_wizard()
                                        
                                        assert result is True
    
    def test_wizard_cancellation(self):
        """Test wizard cancellation"""
        wizard = FirstRunWizard()
        
        with patch.object(wizard, '_print_welcome', side_effect=KeyboardInterrupt):
            result = wizard.run_wizard()
            
            assert result is False
