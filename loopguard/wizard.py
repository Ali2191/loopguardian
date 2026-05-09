"""
First Run Wizard with Claude Code auto-discovery and enhanced user onboarding
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import click

from .config import Config
from .notifications import NotificationService
from .session_discovery import SessionDiscovery


class FirstRunWizard:
    """Enhanced first run wizard with Claude Code auto-discovery"""
    
    def __init__(self) -> None:
        self.config_path = Path.home() / ".loopguard" / "config" / "config.yaml"
        self.session_discovery = SessionDiscovery()
        self.notification_service = NotificationService()
        self.setup_data = {}
        
    def run_wizard(self) -> bool:
        """Run the complete first run wizard"""
        try:
            self._print_welcome()
            
            # Step 1: System check
            if not self._system_check():
                return False
                
            # Step 2: Claude Code discovery
            self._discover_claude_code()
            
            # Step 3: Configuration setup
            self._setup_configuration()
            
            # Step 4: Notification setup
            self._setup_notifications()
            
            # Step 5: Monitoring setup
            self._setup_monitoring()
            
            # Step 6: Tutorial mode
            self._run_tutorial()
            
            # Step 7: Final setup
            self._complete_setup()
            
            return True
            
        except KeyboardInterrupt:
            click.echo("\n\n❌ Setup cancelled by user")
            return False
        except Exception as e:
            click.echo(f"\n❌ Setup failed: {e}")
            return False
    
    def _print_welcome(self) -> None:
        """Print welcome message"""
        click.echo("=" * 60)
        click.echo("🛡️  Welcome to LoopGuard - First Run Setup")
        click.echo("=" * 60)
        click.echo()
        click.echo("LoopGuard protects your Claude Code sessions from")
        click.echo("getting stuck in loops and unproductive patterns.")
        click.echo()
        click.echo("This wizard will guide you through the initial setup")
        click.echo("and automatically detect your Claude Code installation.")
        click.echo()
        click.echo("⏱️  Setup takes approximately 2-3 minutes")
        click.echo()
    
    def _system_check(self) -> bool:
        """Perform system requirements check"""
        click.echo("🔍 Checking system requirements...")
        
        checks_passed = 0
        total_checks = 5
        
        # Check Python version
        python_version = sys.version_info
        if python_version >= (3, 8):
            click.echo(f"   ✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
            checks_passed += 1
        else:
            click.echo(f"   ❌ Python {python_version.major}.{python_version.minor}.{python_version.micro} (requires 3.8+)")
            click.echo("      Please upgrade Python: https://python.org")
            return False
        
        # Check operating system
        if sys.platform == "darwin":
            import platform
            macos_version = platform.mac_ver()[0]
            click.echo(f"   ✅ macOS {macos_version}")
            checks_passed += 1
        else:
            click.echo(f"   ⚠️  {sys.platform} (LoopGuard optimized for macOS)")
            checks_passed += 0.5  # Partial credit
        
        # Check available memory
        try:
            import psutil
            memory_gb = psutil.virtual_memory().total / (1024**3)
            if memory_gb >= 4:
                click.echo(f"   ✅ {memory_gb:.1f}GB RAM available")
                checks_passed += 1
            else:
                click.echo(f"   ⚠️  {memory_gb:.1f}GB RAM (4GB+ recommended)")
                checks_passed += 0.5
        except ImportError:
            click.echo("   ⚠️  Could not check memory (psutil not available)")
            checks_passed += 0.5
        
        # Check disk space
        try:
            home_path = Path.home()
            disk_usage = psutil.disk_usage(str(home_path))
            free_gb = disk_usage.free / (1024**3)
            if free_gb >= 1:
                click.echo(f"   ✅ {free_gb:.1f}GB free disk space")
                checks_passed += 1
            else:
                click.echo(f"   ⚠️  {free_gb:.1f}GB free disk space (1GB+ recommended)")
                checks_passed += 0.5
        except:
            click.echo("   ⚠️  Could not check disk space")
            checks_passed += 0.5
        
        # Check permissions
        config_dir = Path.home() / ".loopguard"
        try:
            config_dir.mkdir(exist_ok=True)
            test_file = config_dir / ".permission_test"
            test_file.touch()
            test_file.unlink()
            click.echo("   ✅ File permissions OK")
            checks_passed += 1
        except PermissionError:
            click.echo("   ❌ Insufficient file permissions")
            click.echo("      Check permissions for home directory")
            return False
        
        click.echo()
        if checks_passed >= total_checks * 0.8:
            click.echo("✅ System requirements met")
            return True
        else:
            click.echo("⚠️  Some requirements not met, but you can continue")
            return click.confirm("Continue with setup anyway?", default=True)
    
    def _discover_claude_code(self) -> None:
        """Auto-discover Claude Code installations"""
        click.echo("🔍 Discovering Claude Code installation...")
        
        # Search for Claude Code
        claude_paths = self._find_claude_code_paths()
        
        if claude_paths:
            click.echo(f"   ✅ Found {len(claude_paths)} Claude Code installation(s):")
            for i, path in enumerate(claude_paths, 1):
                click.echo(f"      {i}. {path}")
            
            # Select primary path
            if len(claude_paths) == 1:
                selected_path = claude_paths[0]
                click.echo(f"   📍 Using: {selected_path}")
            else:
                click.echo()
                selected_path = self._select_claude_path(claude_paths)
        else:
            click.echo("   ❌ Claude Code not found")
            click.echo("      LoopGuard can still work, but you'll need to")
            click.echo("      specify the Claude Code path manually.")
            selected_path = self._manual_claude_setup()
        
        self.setup_data['claude_code_path'] = selected_path
        
        # Check if Claude Code is running
        self._check_claude_running()
    
    def _find_claude_code_paths(self) -> List[str]:
        """Find all Claude Code installations"""
        potential_paths = [
            "/Applications/Claude.app",
            f"{Path.home()}/Applications/Claude.app",
            "/Applications/Claude Code.app",
            f"{Path.home()}/Applications/Claude Code.app",
            "/usr/local/bin/claude",
            f"{Path.home()}/.local/bin/claude",
            "/opt/homebrew/bin/claude",
            "/usr/local/Caskroom/claude/latest/Claude.app",
        ]
        
        found_paths = []
        for path in potential_paths:
            if os.path.exists(path):
                found_paths.append(path)
        
        # Also search common directories
        search_dirs = [
            "/Applications",
            f"{Path.home()}/Applications",
            "/usr/local/bin",
            f"{Path.home()}/.local/bin",
        ]
        
        for search_dir in search_dirs:
            if os.path.exists(search_dir):
                try:
                    for item in os.listdir(search_dir):
                        if "claude" in item.lower() and not item.startswith('.'):
                            full_path = os.path.join(search_dir, item)
                            if os.path.exists(full_path):
                                found_paths.append(full_path)
                except PermissionError:
                    continue
        
        # Remove duplicates and sort
        found_paths = list(set(found_paths))
        found_paths.sort()
        
        return found_paths
    
    def _select_claude_path(self, paths: List[str]) -> str:
        """Let user select Claude Code path"""
        click.echo()
        click.echo("Please select the Claude Code installation to use:")
        
        for i, path in enumerate(paths, 1):
            click.echo(f"   {i}) {path}")
        
        while True:
            try:
                choice = click.prompt("Enter your choice", type=int)
                if 1 <= choice <= len(paths):
                    return paths[choice - 1]
                else:
                    click.echo("   Please enter a valid number")
            except click.Abort:
                return self._manual_claude_setup()
    
    def _manual_claude_setup(self) -> str:
        """Manual Claude Code path setup"""
        click.echo()
        click.echo("Manual Claude Code Setup")
        click.echo("-" * 25)
        
        # Provide guidance
        click.echo("Common Claude Code locations:")
        click.echo("   • /Applications/Claude.app")
        click.echo("   • ~/Applications/Claude.app")
        click.echo("   • /usr/local/bin/claude (if installed via Homebrew)")
        click.echo()
        
        # Try to find with command
        try:
            result = subprocess.run(['which', 'claude'], capture_output=True, text=True)
            if result.returncode == 0:
                click.echo(f"   Found 'claude' command at: {result.stdout.strip()}")
                if click.confirm("Use this path?", default=True):
                    return result.stdout.strip()
        except:
            pass
        
        # Manual input
        while True:
            path = click.prompt("Enter Claude Code path")
            if os.path.exists(path):
                click.echo(f"   ✅ Using: {path}")
                return path
            else:
                click.echo("   ❌ Path does not exist")
                if not click.confirm("Try another path?", default=True):
                    break
        
        # Fallback
        click.echo("   ⚠️  Using default path - you can change this later")
        return "/Applications/Claude.app"
    
    def _check_claude_running(self) -> None:
        """Check if Claude Code is currently running"""
        try:
            result = subprocess.run(['pgrep', '-f', 'Claude'], capture_output=True, text=True)
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                click.echo(f"   🟢 Claude Code is running (PIDs: {', '.join(pids[:3])}{'...' if len(pids) > 3 else ''})")
                self.setup_data['claude_running'] = True
            else:
                click.echo("   ⚪ Claude Code is not currently running")
                self.setup_data['claude_running'] = False
        except:
            click.echo("   ❓ Could not check if Claude Code is running")
            self.setup_data['claude_running'] = None
    
    def _setup_configuration(self) -> None:
        """Setup configuration with user preferences"""
        click.echo()
        click.echo("⚙️  Configuration Setup")
        click.echo("-" * 25)
        
        # Detection settings
        click.echo("Loop Detection Sensitivity:")
        click.echo("   1) High - Detect loops quickly (may have false positives)")
        click.echo("   2) Medium - Balanced detection (recommended)")
        click.echo("   3) Low - Only detect obvious loops")
        
        sensitivity_map = {
            1: {'tool_call_repeats': 2, 'error_repeats': 1, 'stagnation_minutes': 3},
            2: {'tool_call_repeats': 3, 'error_repeats': 2, 'stagnation_minutes': 5},
            3: {'tool_call_repeats': 5, 'error_repeats': 3, 'stagnation_minutes': 10}
        }
        
        while True:
            try:
                sensitivity = click.prompt("Choose sensitivity (1-3)", default=2, type=int)
                if 1 <= sensitivity <= 3:
                    self.setup_data.update(sensitivity_map[sensitivity])
                    break
                else:
                    click.echo("   Please enter 1, 2, or 3")
            except click.Abort:
                self.setup_data.update(sensitivity_map[2])
                break
        
        # Monitoring directories
        click.echo()
        click.echo("Directories to Monitor:")
        default_dirs = [
            str(Path.home() / "Desktop"),
            str(Path.home() / "Documents"),
            str(Path.home() / "Downloads")
        ]
        
        self.setup_data['watch_directories'] = default_dirs
        click.echo(f"   Default: {', '.join(default_dirs)}")
        
        if click.confirm("Add additional directories?", default=False):
            additional_dirs = []
            while True:
                dir_path = click.prompt("Enter directory path (or press Enter to finish)", default="", show_default=False)
                if not dir_path:
                    break
                if os.path.exists(dir_path):
                    additional_dirs.append(dir_path)
                    click.echo(f"   ✅ Added: {dir_path}")
                else:
                    click.echo(f"   ❌ Directory not found: {dir_path}")
            
            self.setup_data['watch_directories'].extend(additional_dirs)
        
        # File patterns
        click.echo()
        default_patterns = ["*.py", "*.js", "*.ts", "*.jsx", "*.tsx", "*.md"]
        self.setup_data['file_patterns'] = default_patterns
        
        if click.confirm("Customize file patterns?", default=False):
            click.echo(f"Current patterns: {', '.join(default_patterns)}")
            custom_patterns = click.prompt("Enter patterns (comma-separated)", default="", show_default=False)
            if custom_patterns:
                patterns = [p.strip() for p in custom_patterns.split(',')]
                self.setup_data['file_patterns'] = patterns
    
    def _setup_notifications(self) -> None:
        """Setup notification preferences"""
        click.echo()
        click.echo("🔔 Notification Setup")
        click.echo("-" * 22)
        
        # Check terminal-notifier
        terminal_notifier_available = self._check_terminal_notifier()
        
        if terminal_notifier_available:
            click.echo("   ✅ Desktop notifications available")
            notifications_enabled = click.confirm("Enable desktop notifications?", default=True)
        else:
            click.echo("   ❌ Desktop notifications not available")
            click.echo("      Install with: brew install terminal-notifier")
            notifications_enabled = False
        
        self.setup_data['notifications_enabled'] = notifications_enabled
        
        if notifications_enabled:
            # Notification throttling
            throttle_seconds = click.prompt("Minimum seconds between notifications", default=30, type=int)
            self.setup_data['notification_throttle'] = max(10, throttle_seconds)
            
            # Sound
            sound_enabled = click.confirm("Enable notification sound?", default=True)
            self.setup_data['notification_sound'] = sound_enabled
        
        # Test notifications
        if notifications_enabled and click.confirm("Test notifications now?", default=True):
            self._test_notifications()
    
    def _check_terminal_notifier(self) -> bool:
        """Check if terminal-notifier is available"""
        try:
            result = subprocess.run(['which', 'terminal-notifier'], capture_output=True)
            return result.returncode == 0
        except:
            return False
    
    def _test_notifications(self) -> None:
        """Test notification system"""
        click.echo("   🧪 Testing notifications...")
        
        try:
            result = subprocess.run([
                'terminal-notifier',
                '-title', 'LoopGuard',
                '-message', 'Test notification - LoopGuard is working!',
                '-sound', 'default'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                click.echo("   ✅ Test notification sent successfully")
            else:
                click.echo(f"   ❌ Test failed: {result.stderr}")
        except Exception as e:
            click.echo(f"   ❌ Test failed: {e}")
    
    def _setup_monitoring(self) -> None:
        """Setup monitoring preferences"""
        click.echo()
        click.echo("👁️  Monitoring Setup")
        click.echo("-" * 23)
        
        # Auto-start
        auto_start = click.confirm("Start LoopGuard automatically on login?", default=True)
        self.setup_data['auto_start'] = auto_start
        
        # Session timeout
        timeout_minutes = click.prompt("Maximum session duration (minutes)", default=30, type=int)
        self.setup_data['session_timeout'] = max(5, timeout_minutes)
        
        # Performance monitoring
        perf_monitoring = click.confirm("Enable performance monitoring?", default=True)
        self.setup_data['performance_monitoring'] = perf_monitoring
        
        if perf_monitoring:
            click.echo("   This will track resource usage and optimize performance")
    
    def _run_tutorial(self) -> None:
        """Run interactive tutorial"""
        click.echo()
        click.echo("📚 Quick Tutorial")
        click.echo("-" * 18)
        
        if not click.confirm("Run interactive tutorial?", default=True):
            return
        
        click.echo()
        click.echo("LoopGuard monitors your Claude Code sessions for:")
        click.echo()
        
        # Tutorial step 1
        click.echo("🔄 1. Repetitive Tool Calls")
        click.echo("   Detects when Claude uses the same tool repeatedly")
        click.echo("   Example: Reading the same file multiple times")
        
        if click.confirm("See an example?", default=True):
            click.echo("   Example: read_file -> read_file -> read_file")
            click.echo("   🚨 Alert: 'Possible loop detected in file reading'")
        
        # Tutorial step 2
        click.echo()
        click.echo("❌ 2. Error Patterns")
        click.echo("   Detects repeated errors or failed operations")
        click.echo("   Example: Same API call failing multiple times")
        
        if click.confirm("See an example?", default=True):
            click.echo("   Example: api_call(error) -> api_call(error) -> api_call(error)")
            click.echo("   🚨 Alert: 'Repeated errors detected'")
        
        # Tutorial step 3
        click.echo()
        click.echo("⏸️  3. Session Stagnation")
        click.echo("   Detects when no meaningful progress is made")
        click.echo("   Example: Long periods without file changes")
        
        # Tutorial step 4
        click.echo()
        click.echo("🔧 4. What to do when alerted")
        click.echo("   • Review the suggested action")
        click.echo("   • Try a different approach")
        click.echo("   • Take a break and refocus")
        click.echo("   • Provide feedback to improve detection")
        
        click.echo()
        click.echo("✅ Tutorial complete! You're ready to use LoopGuard.")
    
    def _complete_setup(self) -> None:
        """Complete the setup process"""
        click.echo()
        click.echo("🎯 Finalizing Setup")
        click.echo("-" * 20)
        
        # Create configuration
        self._create_config_file()
        
        # Setup auto-start if requested
        if self.setup_data.get('auto_start', False):
            self._setup_autostart()
        
        # Show summary
        self._show_setup_summary()
        
        # Next steps
        self._show_next_steps()
    
    def _create_config_file(self) -> None:
        """Create the configuration file"""
        config_dir = self.config_path.parent
        config_dir.mkdir(parents=True, exist_ok=True)
        
        config_content = {
            'detection': {
                'tool_call_repeats': self.setup_data.get('tool_call_repeats', 3),
                'error_repeats': self.setup_data.get('error_repeats', 2),
                'stagnation_minutes': self.setup_data.get('stagnation_minutes', 5),
                'session_timeout_minutes': self.setup_data.get('session_timeout', 30)
            },
            'monitoring': {
                'claude_code_path': self.setup_data.get('claude_code_path', '/Applications/Claude.app'),
                'watch_directories': self.setup_data.get('watch_directories', []),
                'file_patterns': self.setup_data.get('file_patterns', [])
            },
            'notifications': {
                'enabled': self.setup_data.get('notifications_enabled', True),
                'throttle_seconds': self.setup_data.get('notification_throttle', 30),
                'sound': self.setup_data.get('notification_sound', True),
                'desktop': self.setup_data.get('notifications_enabled', True)
            },
            'performance': {
                'monitoring_enabled': self.setup_data.get('performance_monitoring', True),
                'max_memory_mb': 512,
                'max_cpu_percent': 20
            },
            'logging': {
                'level': 'INFO',
                'max_file_size_mb': 10,
                'backup_count': 5
            }
        }
        
        try:
            import yaml
            with open(self.config_path, 'w') as f:
                yaml.dump(config_content, f, default_flow_style=False, indent=2)
            click.echo(f"   ✅ Configuration saved to {self.config_path}")
        except ImportError:
            # Fallback to JSON if YAML not available
            json_path = self.config_path.with_suffix('.json')
            with open(json_path, 'w') as f:
                json.dump(config_content, f, indent=2)
            click.echo(f"   ✅ Configuration saved to {json_path}")
            self.config_path = json_path
    
    def _setup_autostart(self) -> None:
        """Setup automatic startup"""
        try:
            plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.loopguard.agent</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/loopguard</string>
        <string>monitor</string>
        <string>--config</string>
        <string>{self.config_path}</string>
        <string>--daemon</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>{Path.home()}</string>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
        <key>NetworkState</key>
        <true/>
    </dict>
    
    <key>StandardOutPath</key>
    <string>{Path.home()}/.loopguard/logs/loopguard.log</string>
    
    <key>StandardErrorPath</key>
    <string>{Path.home()}/.loopguard/logs/loopguard.error.log</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>LOOPGUARD_HOME</key>
        <string>{Path.home()}/.loopguard</string>
    </dict>
    
    <key>ProcessType</key>
    <string>Background</string>
</dict>
</plist>"""
            
            # Create logs directory
            logs_dir = Path.home() / ".loopguard" / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            
            # Write plist file
            plist_path = Path.home() / "Library" / "LaunchAgents" / "com.loopguard.agent.plist"
            with open(plist_path, 'w') as f:
                f.write(plist_content)
            
            click.echo(f"   ✅ Auto-start configured: {plist_path}")
            
        except Exception as e:
            click.echo(f"   ⚠️  Auto-start setup failed: {e}")
            click.echo("      You can enable it manually with: launchctl load ~/Library/LaunchAgents/com.loopguard.agent.plist")
    
    def _show_setup_summary(self) -> None:
        """Show setup summary"""
        click.echo()
        click.echo("📋 Setup Summary")
        click.echo("-" * 18)
        
        click.echo(f"   Claude Code: {self.setup_data.get('claude_code_path', 'Not found')}")
        click.echo(f"   Sensitivity: {self._get_sensitivity_name()}")
        click.echo(f"   Notifications: {'Enabled' if self.setup_data.get('notifications_enabled', False) else 'Disabled'}")
        click.echo(f"   Auto-start: {'Enabled' if self.setup_data.get('auto_start', False) else 'Disabled'}")
        click.echo(f"   Config: {self.config_path}")
        
        if self.setup_data.get('claude_running'):
            click.echo("   🟢 Claude Code is currently running")
        else:
            click.echo("   ⚪ Claude Code is not running")
    
    def _get_sensitivity_name(self) -> str:
        """Get sensitivity level name"""
        repeats = self.setup_data.get('tool_call_repeats', 3)
        if repeats <= 2:
            return "High"
        elif repeats <= 3:
            return "Medium"
        else:
            return "Low"
    
    def _show_next_steps(self) -> None:
        """Show next steps"""
        click.echo()
        click.echo("🚀 Next Steps")
        click.echo("-" * 15)
        
        click.echo("1. Start using Claude Code as normal")
        click.echo("2. LoopGuard will monitor in the background")
        click.echo("3. Receive alerts if loops are detected")
        click.echo()
        
        click.echo("Useful commands:")
        click.echo(f"   loopguard status     - Check LoopGuard status")
        click.echo(f"   loopguard test       - Test notifications")
        click.echo(f"   loopguard config     - View configuration")
        click.echo(f"   loopguard activity   - View session activity")
        click.echo()
        
        if self.setup_data.get('auto_start', False):
            click.echo("LoopGuard will start automatically when you log in.")
        else:
            click.echo("Start LoopGuard manually with: loopguard start")
        
        click.echo()
        click.echo("🎉 Setup complete! LoopGuard is now protecting your Claude Code sessions.")
        click.echo()
        click.echo("Need help? Visit: https://loopguard.readthedocs.io/")


def run_first_time_wizard() -> bool:
    """Run the first-time setup wizard"""
    wizard = FirstRunWizard()
    return wizard.run_wizard()
