"""
Configuration management for LoopGuard
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from jsonschema import validate, ValidationError

from .config_validator import UserFriendlyConfigValidator, ConfigValidationError


DEFAULT_CONFIG = {
    "detection": {
        "tool_call_repeats": 3,
        "error_repeats": 2,
        "stagnation_minutes": 5,
        "adaptive_mode": True
    },
    "notifications": {
        "enabled": True,
        "throttle_seconds": 30,
        "quiet_hours": {
            "enabled": False,
            "start_hour": 22,
            "end_hour": 7
        },
        "sound_enabled": True,
        "severity_thresholds": {
            "low": 300,    # 5 minutes
            "medium": 120,  # 2 minutes  
            "high": 30      # 30 seconds
        },
        "project_settings": {}
    },
    "performance": {
        "max_sessions": 50,
        "memory_limit_mb": 40,
        "cpu_limit_percent": 1.5
    }
}

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "detection": {
            "type": "object",
            "properties": {
                "tool_call_repeats": {"type": "integer", "minimum": 2, "maximum": 10},
                "error_repeats": {"type": "integer", "minimum": 1, "maximum": 8},
                "stagnation_minutes": {"type": "integer", "minimum": 1, "maximum": 60},
                "adaptive_mode": {"type": "boolean"}
            },
            "required": ["tool_call_repeats", "error_repeats", "stagnation_minutes"]
        },
        "notifications": {
            "type": "object",
            "properties": {
                "enabled": {"type": "boolean"},
                "throttle_seconds": {"type": "integer", "minimum": 10, "maximum": 600},
                "quiet_hours": {
                    "type": "object",
                    "properties": {
                        "enabled": {"type": "boolean"},
                        "start_hour": {"type": "integer", "minimum": 0, "maximum": 23},
                        "end_hour": {"type": "integer", "minimum": 0, "maximum": 23}
                    },
                    "required": ["enabled", "start_hour", "end_hour"]
                },
                "sound_enabled": {"type": "boolean"},
                "severity_thresholds": {
                    "type": "object",
                    "properties": {
                        "low": {"type": "integer", "minimum": 60},
                        "medium": {"type": "integer", "minimum": 30},
                        "high": {"type": "integer", "minimum": 10}
                    },
                    "required": ["low", "medium", "high"]
                },
                "project_settings": {
                    "type": "object",
                    "patternProperties": {
                        ".*": {
                            "type": "object",
                            "properties": {
                                "muted": {"type": "boolean"},
                                "custom_throttle_seconds": {"type": "integer", "minimum": 10},
                                "severity_override": {"type": "string", "enum": ["low", "medium", "high"]}
                            }
                        }
                    }
                }
            },
            "required": ["enabled", "throttle_seconds"]
        },
        "performance": {
            "type": "object",
            "properties": {
                "max_sessions": {"type": "integer", "minimum": 1, "maximum": 100},
                "memory_limit_mb": {"type": "integer", "minimum": 20, "maximum": 200},
                "cpu_limit_percent": {"type": "number", "minimum": 0.5, "maximum": 10.0}
            }
        }
    },
    "required": ["detection", "notifications"]
}


class Config:
    """Enhanced configuration manager with user-friendly validation"""
    
    def __init__(self, config_path: Optional[str] = None, interactive_setup: bool = False):
        self.validator = UserFriendlyConfigValidator()
        
        if interactive_setup:
            # Run interactive setup wizard
            self._config = self.validator.interactive_setup_wizard()
            self.config_path = Path.home() / ".loopguard" / "config.json"
            self._save_config()
            return
        
        if config_path is None:
            # Look for config in current directory first, then home directory
            current_dir = Path.cwd() / "loopguard.config.json"
            home_dir = Path.home() / ".loopguard" / "config.json"
            
            if current_dir.exists():
                self.config_path = current_dir
            elif home_dir.exists():
                self.config_path = home_dir
            else:
                # Create default config in home directory
                home_dir.parent.mkdir(exist_ok=True)
                self.config_path = home_dir
                self._save_default_config()
        else:
            self.config_path = Path(config_path)
        
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration with user-friendly validation"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    
                    # Validate with user-friendly error messages
                    is_valid, errors = self.validator.validate_config(config, str(self.config_path))
                    
                    if not is_valid:
                        print("\n⚠️  Configuration Validation Issues Found:")
                        print(self.validator.get_validation_summary(errors))
                        
                        # Try to auto-fix common issues
                        fixes = self.validator.suggest_fixes(errors)
                        if fixes:
                            print("\n🔧 Attempting to auto-fix common issues...")
                            for path, fix in fixes.items():
                                self._set_nested_value(config, path, fix)
                                print(f"   Fixed: {path} = {fix}")
                            
                            # Re-validate after fixes
                            is_valid, errors = self.validator.validate_config(config, str(self.config_path))
                            if is_valid:
                                print("✅ Auto-fix successful!")
                                self._save_config()
                            else:
                                print("⚠️  Some issues remain - using default values for problematic settings")
                        
                        # Fall back to defaults for invalid settings
                        if not is_valid:
                            config = self._merge_with_defaults(config)
                    
                    return config
            else:
                self._save_default_config()
                return DEFAULT_CONFIG.copy()
        except (ValidationError, json.JSONDecodeError) as e:
            print(f"\n❌ Invalid config file {self.config_path}: {e}")
            print("💡 Using default configuration and creating new config file.")
            self._save_default_config()
            return DEFAULT_CONFIG.copy()
        except Exception as e:
            print(f"\n⚠️  Error loading config: {e}")
            print("💡 Using default configuration.")
            return DEFAULT_CONFIG.copy()
    
    def _save_default_config(self):
        """Save default configuration to file"""
        with open(self.config_path, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
    
    def get(self, key_path: str, default=None):
        """Get configuration value by dot-separated path"""
        keys = key_path.split('.')
        value = self._config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, key_path: str, value):
        """Set configuration value by dot-separated path"""
        keys = key_path.split('.')
        config = self._config
        
        # Navigate to the parent of the target key
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        # Set the final value
        config[keys[-1]] = value
    
    def get_project_settings(self, project_path: str) -> dict:
        """Get settings for a specific project"""
        project_settings = self.get('notifications.project_settings', {})
        return project_settings.get(project_path, {})
    
    def set_project_settings(self, project_path: str, settings: dict):
        """Set settings for a specific project"""
        project_settings = self.get('notifications.project_settings', {})
        project_settings[project_path] = settings
        self.set('notifications.project_settings', project_settings)
        self._save_config()
    
    def get_throttle_seconds(self, severity: str, project_path: str = None) -> int:
        """Get throttle seconds for a specific severity and project"""
        # Check project-specific override first
        if project_path:
            project_settings = self.get_project_settings(project_path)
            if 'custom_throttle_seconds' in project_settings:
                return project_settings['custom_throttle_seconds']
        
        # Use severity-based thresholds
        return self.get(f'notifications.severity_thresholds.{severity}', 120)
    
    def is_project_muted(self, project_path: str) -> bool:
        """Check if a project is muted"""
        if not project_path:
            return False
        
        project_settings = self.get_project_settings(project_path)
        return project_settings.get('muted', False)
    
    def get_severity_override(self, project_path: str) -> Optional[str]:
        """Get severity override for a project"""
        if not project_path:
            return None
        
        project_settings = self.get_project_settings(project_path)
        return project_settings.get('severity_override')
    
    def validate_current_config(self) -> Tuple[bool, List[ConfigValidationError]]:
        """Validate current configuration and return errors"""
        return self.validator.validate_config(self._config, str(self.config_path))
    
    def get_validation_summary(self) -> str:
        """Get user-friendly validation summary for current config"""
        is_valid, errors = self.validate_current_config()
        return self.validator.get_validation_summary(errors)
    
    def interactive_setup(self):
        """Run interactive configuration setup wizard"""
        print("🧙 Starting interactive configuration setup...\n")
        new_config = self.validator.interactive_setup_wizard()
        self._config = new_config
        self._save_config()
        print("\n✅ Configuration updated successfully!")
    
    def _merge_with_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge invalid config with defaults, fixing problematic values"""
        merged = DEFAULT_CONFIG.copy()
        
        def merge_recursive(default: dict, user: dict):
            for key, value in user.items():
                if key in default:
                    if isinstance(value, dict) and isinstance(default[key], dict):
                        merge_recursive(default[key], value)
                    else:
                        # Validate the value before merging
                        try:
                            # Simple validation - if it fails, use default
                            if key in ['tool_call_repeats', 'error_repeats', 'stagnation_minutes']:
                                if isinstance(value, int) and value > 0:
                                    default[key] = value
                            elif key in ['enabled', 'sound_enabled', 'adaptive_mode']:
                                if isinstance(value, bool):
                                    default[key] = value
                            else:
                                default[key] = value
                        except:
                            pass  # Keep default value
                else:
                    default[key] = value
        
        merge_recursive(merged, config)
        return merged
    
    def _set_nested_value(self, config: Dict, path: str, value: Any):
        """Set nested value using dot notation"""
        keys = path.split('.')
        current = config
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    def _save_config(self):
        """Save current configuration to file"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(self._config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def reload(self):
        """Reload configuration from file"""
        self._config = self._load_config()
