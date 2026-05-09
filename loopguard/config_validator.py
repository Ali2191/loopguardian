"""
User-friendly configuration validation with helpful error messages
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from jsonschema import validate, ValidationError, Draft7Validator
import os
import re


class ConfigValidationError:
    """Represents a configuration validation error with helpful context"""
    
    def __init__(self, path: str, message: str, value: Any = None, 
                 suggestion: str = None, documentation_url: str = None):
        self.path = path
        self.message = message
        self.value = value
        self.suggestion = suggestion
        self.documentation_url = documentation_url
    
    def to_dict(self) -> Dict:
        return {
            'path': self.path,
            'message': self.message,
            'value': self.value,
            'suggestion': self.suggestion,
            'documentation_url': self.documentation_url
        }
    
    def format_error(self) -> str:
        """Format error message for user display"""
        msg = f"❌ {self.path}: {self.message}"
        if self.value is not None:
            msg += f"\n   Current value: {repr(self.value)}"
        if self.suggestion:
            msg += f"\n   💡 Suggestion: {self.suggestion}"
        if self.documentation_url:
            msg += f"\n   📚 Documentation: {self.documentation_url}"
        return msg


class UserFriendlyConfigValidator:
    """Enhanced configuration validator with user-friendly error messages"""
    
    def __init__(self):
        self.documentation_base = "https://github.com/loopguard/loopguard/docs"
        self.common_errors = self._init_common_error_patterns()
        self.validators = self._init_custom_validators()
    
    def validate_config(self, config: Dict, config_path: str = None) -> Tuple[bool, List[ConfigValidationError]]:
        """Validate configuration with user-friendly error messages"""
        errors = []
        
        # Schema validation first
        try:
            from .config import CONFIG_SCHEMA
            validate(instance=config, schema=CONFIG_SCHEMA)
        except ValidationError as e:
            errors.append(self._format_schema_error(e))
        
        # Custom validation for better user experience
        errors.extend(self._validate_detection_settings(config))
        errors.extend(self._validate_notification_settings(config))
        errors.extend(self._validate_performance_settings(config))
        errors.extend(self._validate_paths_and_permissions(config))
        errors.extend(self._validate_logical_constraints(config))
        
        # Check for common configuration mistakes
        errors.extend(self._check_common_mistakes(config))
        
        return len(errors) == 0, errors
    
    def get_validation_summary(self, errors: List[ConfigValidationError]) -> str:
        """Get user-friendly validation summary"""
        if not errors:
            return "✅ Configuration is valid!"
        
        summary = f"❌ Found {len(errors)} configuration issue{'s' if len(errors) != 1 else ''}:\n\n"
        
        for i, error in enumerate(errors, 1):
            summary += f"{i}. {error.format_error()}\n\n"
        
        summary += "💡 Need help? Visit: {}\n".format(self.documentation_base)
        return summary
    
    def suggest_fixes(self, errors: List[ConfigValidationError]) -> Dict[str, Any]:
        """Generate suggested configuration fixes"""
        fixes = {}
        
        for error in errors:
            if error.path in fixes:
                continue
            
            if error.suggestion:
                # Try to parse suggestion into a concrete fix
                fix = self._parse_suggestion_to_fix(error)
                if fix:
                    fixes[error.path] = fix
        
        return fixes
    
    def interactive_setup_wizard(self) -> Dict[str, Any]:
        """Guide user through interactive configuration setup"""
        config = {}
        
        print("🧙 LoopGuard Configuration Wizard")
        print("=" * 40)
        print("Let's set up your LoopGuard configuration step by step.\n")
        
        # Detection settings
        print("🔍 Detection Settings")
        print("-" * 20)
        
        config['detection'] = {}
        
        tool_repeats = self._ask_numeric(
            "Tool call repeats before alert (default: 3)",
            default=3, min_val=2, max_val=10,
            help_text="How many identical tool calls before considering it a loop?"
        )
        config['detection']['tool_call_repeats'] = tool_repeats
        
        error_repeats = self._ask_numeric(
            "Error repeats before alert (default: 2)",
            default=2, min_val=1, max_val=8,
            help_text="How many identical errors before considering it a loop?"
        )
        config['detection']['error_repeats'] = error_repeats
        
        stagnation_minutes = self._ask_numeric(
            "Stagnation minutes before alert (default: 5)",
            default=5, min_val=1, max_val=30,
            help_text="Minutes of activity without file changes before alert?"
        )
        config['detection']['stagnation_minutes'] = stagnation_minutes
        
        # Adaptive mode
        adaptive_mode = self._ask_yes_no(
            "Enable adaptive detection (recommended)",
            default=True,
            help_text="Automatically adjust thresholds based on your usage patterns?"
        )
        config['detection']['adaptive_mode'] = adaptive_mode
        
        # Notification settings
        print("\n🔔 Notification Settings")
        print("-" * 25)
        
        config['notifications'] = {}
        
        notifications_enabled = self._ask_yes_no(
            "Enable desktop notifications",
            default=True,
            help_text="Show desktop alerts when loops are detected?"
        )
        config['notifications']['enabled'] = notifications_enabled
        
        if notifications_enabled:
            throttle_seconds = self._ask_numeric(
                "Notification throttle seconds (default: 30)",
                default=30, min_val=10, max_val=300,
                help_text="Minimum seconds between notifications for the same session?"
            )
            config['notifications']['throttle_seconds'] = throttle_seconds
            
            sound_enabled = self._ask_yes_no(
                "Enable notification sounds",
                default=True,
                help_text="Play sound with notifications?"
            )
            config['notifications']['sound_enabled'] = sound_enabled
        
        # Claude Code directory discovery
        print("\n📁 Claude Code Setup")
        print("-" * 22)
        
        claude_path = self._discover_claude_directory()
        if claude_path:
            print(f"✅ Found Claude Code directory: {claude_path}")
            config['claude_code_path'] = str(claude_path)
        else:
            print("⚠️  Could not find Claude Code directory automatically")
            custom_path = input("Enter Claude Code projects path (or press Enter to skip): ").strip()
            if custom_path and Path(custom_path).exists():
                config['claude_code_path'] = custom_path
        
        print("\n✨ Configuration setup complete!")
        return config
    
    def _validate_detection_settings(self, config: Dict) -> List[ConfigValidationError]:
        """Validate detection-specific settings"""
        errors = []
        detection = config.get('detection', {})
        
        # Tool call repeats validation
        tool_repeats = detection.get('tool_call_repeats')
        if tool_repeats is not None:
            if not isinstance(tool_repeats, int) or tool_repeats < 2:
                errors.append(ConfigValidationError(
                    'detection.tool_call_repeats',
                    'Must be an integer >= 2',
                    tool_repeats,
                    'Set to 3 for balanced detection',
                    f'{self.documentation_base}/detection#tool-call-repeats'
                ))
            elif tool_repeats > 10:
                errors.append(ConfigValidationError(
                    'detection.tool_call_repeats',
                    'Value too high may miss actual loops',
                    tool_repeats,
                    'Consider values between 2-5 for better detection',
                    f'{self.documentation_base}/detection#tool-call-repeats'
                ))
        
        # Error repeats validation
        error_repeats = detection.get('error_repeats')
        if error_repeats is not None:
            if not isinstance(error_repeats, int) or error_repeats < 1:
                errors.append(ConfigValidationError(
                    'detection.error_repeats',
                    'Must be an integer >= 1',
                    error_repeats,
                    'Set to 2 for typical error loop detection',
                    f'{self.documentation_base}/detection#error-repeats'
                ))
        
        # Stagnation minutes validation
        stagnation = detection.get('stagnation_minutes')
        if stagnation is not None:
            if not isinstance(stagnation, int) or stagnation < 1:
                errors.append(ConfigValidationError(
                    'detection.stagnation_minutes',
                    'Must be an integer >= 1',
                    stagnation,
                    'Set to 5 for balanced stagnation detection',
                    f'{self.documentation_base}/detection#stagnation'
                ))
            elif stagnation > 60:
                errors.append(ConfigValidationError(
                    'detection.stagnation_minutes',
                    'Very high value may delay important alerts',
                    stagnation,
                    'Consider values between 3-15 minutes',
                    f'{self.documentation_base}/detection#stagnation'
                ))
        
        return errors
    
    def _validate_notification_settings(self, config: Dict) -> List[ConfigValidationError]:
        """Validate notification-specific settings"""
        errors = []
        notifications = config.get('notifications', {})
        
        # Throttle seconds validation
        throttle = notifications.get('throttle_seconds')
        if throttle is not None:
            if not isinstance(throttle, int) or throttle < 10:
                errors.append(ConfigValidationError(
                    'notifications.throttle_seconds',
                    'Must be an integer >= 10 seconds',
                    throttle,
                    'Set to 30 seconds to avoid notification spam',
                    f'{self.documentation_base}/notifications#throttling'
                ))
            elif throttle > 600:  # 10 minutes
                errors.append(ConfigValidationError(
                    'notifications.throttle_seconds',
                    'Very high throttle may delay important alerts',
                    throttle,
                    'Consider values between 30-120 seconds',
                    f'{self.documentation_base}/notifications#throttling'
                ))
        
        # Quiet hours validation
        quiet_hours = notifications.get('quiet_hours', {})
        if quiet_hours.get('enabled', False):
            start_hour = quiet_hours.get('start_hour')
            end_hour = quiet_hours.get('end_hour')
            
            if start_hour is not None and (not isinstance(start_hour, int) or not (0 <= start_hour <= 23)):
                errors.append(ConfigValidationError(
                    'notifications.quiet_hours.start_hour',
                    'Must be an integer between 0-23',
                    start_hour,
                    'Use 22 (10 PM) for typical quiet hours start',
                    f'{self.documentation_base}/notifications#quiet-hours'
                ))
            
            if end_hour is not None and (not isinstance(end_hour, int) or not (0 <= end_hour <= 23)):
                errors.append(ConfigValidationError(
                    'notifications.quiet_hours.end_hour',
                    'Must be an integer between 0-23',
                    end_hour,
                    'Use 7 (7 AM) for typical quiet hours end',
                    f'{self.documentation_base}/notifications#quiet-hours'
                ))
        
        return errors
    
    def _validate_performance_settings(self, config: Dict) -> List[ConfigValidationError]:
        """Validate performance-related settings"""
        errors = []
        
        # Check for potentially problematic performance settings
        max_sessions = config.get('performance', {}).get('max_sessions')
        if max_sessions is not None:
            if not isinstance(max_sessions, int) or max_sessions < 1:
                errors.append(ConfigValidationError(
                    'performance.max_sessions',
                    'Must be a positive integer',
                    max_sessions,
                    'Set to 10 for balanced performance',
                    f'{self.documentation_base}/performance#max-sessions'
                ))
            elif max_sessions > 100:
                errors.append(ConfigValidationError(
                    'performance.max_sessions',
                    'Very high value may impact system performance',
                    max_sessions,
                    'Consider values between 5-20 for most systems',
                    f'{self.documentation_base}/performance#max-sessions'
                ))
        
        return errors
    
    def _validate_paths_and_permissions(self, config: Dict) -> List[ConfigValidationError]:
        """Validate file paths and permissions"""
        errors = []
        
        # Check Claude Code path if specified
        claude_path = config.get('claude_code_path')
        if claude_path:
            path = Path(claude_path)
            if not path.exists():
                errors.append(ConfigValidationError(
                    'claude_code_path',
                    'Path does not exist',
                    claude_path,
                    'Install Claude Code or provide correct path',
                    f'{self.documentation_base}/setup#claude-code-path'
                ))
            elif not os.access(path, os.R_OK):
                errors.append(ConfigValidationError(
                    'claude_code_path',
                    'Path is not readable',
                    claude_path,
                    'Check file permissions for this directory',
                    f'{self.documentation_base}/setup#permissions'
                ))
        
        return errors
    
    def _validate_logical_constraints(self, config: Dict) -> List[ConfigValidationError]:
        """Validate logical constraints between settings"""
        errors = []
        detection = config.get('detection', {})
        notifications = config.get('notifications', {})
        
        # Check for contradictory settings
        adaptive_mode = detection.get('adaptive_mode', False)
        if adaptive_mode:
            # If adaptive mode is enabled, manual thresholds should be reasonable
            tool_repeats = detection.get('tool_call_repeats', 3)
            if tool_repeats > 8:
                errors.append(ConfigValidationError(
                    'detection.tool_call_repeats',
                    'High threshold conflicts with adaptive mode',
                    tool_repeats,
                    'Lower to 3-5 when using adaptive mode',
                    f'{self.documentation_base}/detection#adaptive-mode'
                ))
        
        # Check notification settings consistency
        if notifications.get('enabled', True):
            throttle = notifications.get('throttle_seconds', 30)
            if throttle > 300:  # 5 minutes
                errors.append(ConfigValidationError(
                    'notifications.throttle_seconds',
                    'High throttle may defeat notification purpose',
                    throttle,
                    'Use 30-120 seconds for responsive alerts',
                    f'{self.documentation_base}/notifications#throttling'
                ))
        
        return errors
    
    def _check_common_mistakes(self, config: Dict) -> List[ConfigValidationError]:
        """Check for common configuration mistakes"""
        errors = []
        
        # Check for typos in common keys
        common_typos = {
            'detection.tool_repeat': 'detection.tool_call_repeats',
            'detection.error_repeat': 'detection.error_repeats',
            'notification.enabled': 'notifications.enabled',
            'notificatons.enabled': 'notifications.enabled'
        }
        
        for typo, correct in common_typos.items():
            if self._get_nested_value(config, typo) is not None:
                errors.append(ConfigValidationError(
                    typo,
                    f'Possible typo - did you mean "{correct}"?',
                    self._get_nested_value(config, typo),
                    f'Change key to "{correct}"',
                    f'{self.documentation_base}/common-issues#typos'
                ))
        
        # Check for deprecated settings
        deprecated_settings = {
            'detection.loop_sensitivity': 'Removed in v0.2.0 - use adaptive_mode instead',
            'notifications.popup_enabled': 'Use enabled instead'
        }
        
        for deprecated, message in deprecated_settings.items():
            if self._get_nested_value(config, deprecated) is not None:
                errors.append(ConfigValidationError(
                    deprecated,
                    f'Deprecated setting: {message}',
                    self._get_nested_value(config, deprecated),
                    'Remove this setting from configuration',
                    f'{self.documentation_base}/migration#deprecated-settings'
                ))
        
        return errors
    
    def _format_schema_error(self, error: ValidationError) -> ConfigValidationError:
        """Format JSON schema validation error"""
        path = '.'.join(str(p) for p in error.absolute_path) if error.absolute_path else 'root'
        
        suggestions = {
            'type': 'Check the data type - should be {}'.format(error.validator_value),
            'minimum': 'Value must be >= {}'.format(error.validator_value),
            'maximum': 'Value must be <= {}'.format(error.validator_value),
            'required': 'This field is required',
            'additionalProperties': 'Unknown property - remove or check spelling'
        }
        
        suggestion = suggestions.get(error.validator, 'Check configuration format')
        
        return ConfigValidationError(
            path,
            error.message,
            error.instance,
            suggestion,
            f'{self.documentation_base}/schema#{error.validator}'
        )
    
    def _get_nested_value(self, config: Dict, path: str) -> Any:
        """Get nested value from config using dot notation"""
        keys = path.split('.')
        value = config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value
    
    def _parse_suggestion_to_fix(self, error: ConfigValidationError) -> Any:
        """Parse suggestion into a concrete configuration fix"""
        suggestion = error.suggestion
        if not suggestion:
            return None
        
        # Extract numeric values from suggestions
        if 'set to' in suggestion.lower():
            match = re.search(r'set to (\d+)', suggestion.lower())
            if match:
                return int(match.group(1))
        
        # Extract boolean values
        if 'enable' in suggestion.lower():
            return True
        elif 'disable' in suggestion.lower():
            return False
        
        return None
    
    def _ask_numeric(self, question: str, default: int, min_val: int, max_val: int, help_text: str = None) -> int:
        """Ask user for numeric input with validation"""
        while True:
            if help_text:
                print(f"💡 {help_text}")
            
            response = input(f"{question} [{default}]: ").strip()
            
            if not response:
                return default
            
            try:
                value = int(response)
                if min_val <= value <= max_val:
                    return value
                else:
                    print(f"⚠️  Please enter a value between {min_val} and {max_val}")
            except ValueError:
                print("⚠️  Please enter a valid number")
    
    def _ask_yes_no(self, question: str, default: bool, help_text: str = None) -> bool:
        """Ask user for yes/no input"""
        while True:
            if help_text:
                print(f"💡 {help_text}")
            
            response = input(f"{question} [{'Y' if default else 'N'}]: ").strip().lower()
            
            if not response:
                return default
            
            if response in ['y', 'yes', 'true', '1']:
                return True
            elif response in ['n', 'no', 'false', '0']:
                return False
            else:
                print("⚠️  Please enter Y/yes or N/no")
    
    def _discover_claude_directory(self) -> Optional[Path]:
        """Automatically discover Claude Code directory"""
        possible_paths = [
            Path.home() / ".claude" / "projects",
            Path.home() / ".config" / "claude" / "projects",
            Path("/usr/local/share/claude/projects"),
            Path("/opt/claude/projects")
        ]
        
        for path in possible_paths:
            if path.exists() and path.is_dir():
                return path
        
        return None
    
    def _init_common_error_patterns(self) -> Dict[str, str]:
        """Initialize common error patterns and their solutions"""
        return {
            'permission_denied': 'Check file permissions and run with appropriate access',
            'file_not_found': 'Verify file paths and ensure directories exist',
            'invalid_json': 'Check JSON syntax - use linter or validator',
            'schema_violation': 'Review configuration schema documentation'
        }
    
    def _init_custom_validators(self) -> Dict[str, callable]:
        """Initialize custom validation functions"""
        return {
            'validate_threshold': lambda x: isinstance(x, int) and x > 0,
            'validate_path': lambda x: Path(x).exists() if isinstance(x, str) else False,
            'validate_time_range': lambda x: isinstance(x, int) and 0 <= x <= 23
        }
