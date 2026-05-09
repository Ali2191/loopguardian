# LoopGuard User Guide

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Configuration](#configuration)
5. [Monitoring](#monitoring)
6. [Notifications](#notifications)
7. [CLI Reference](#cli-reference)
8. [Troubleshooting](#troubleshooting)
9. [Advanced Usage](#advanced-usage)
10. [Uninstallation](#uninstallation)

## Introduction

LoopGuard is a real-time monitoring tool designed to detect and alert you when Claude Code gets stuck in repetitive loops or unproductive patterns. It runs silently in the background and provides intelligent notifications when potential issues are detected.

### Key Features

- **Real-time Loop Detection**: Monitors Claude Code sessions for repetitive tool calls and error patterns
- **Intelligent Notifications**: Desktop alerts with configurable throttling and sound options
- **Session Monitoring**: Tracks session duration, tool call patterns, and productivity metrics
- **Auto-start Service**: Runs automatically on system startup with minimal resource usage
- **Configurable Detection**: Adjustable sensitivity for different work patterns
- **Comprehensive Logging**: Detailed logs for debugging and analysis

### System Requirements

- **Operating System**: macOS 10.15+ (Catalina or later)
- **Python**: Version 3.8 or higher
- **Memory**: Minimum 100MB available memory
- **Storage**: 50MB free disk space
- **Optional**: Homebrew for desktop notifications

## Installation

### Method 1: Automated Installer (Recommended)

The easiest way to install LoopGuard is using the provided installer script:

```bash
# Download and run the installer
curl -fsSL https://raw.githubusercontent.com/loopguard/loopguard/main/install.sh | bash

# Or if you have the source code:
./install.sh
```

The installer will:
- Check system requirements
- Detect Claude Code installation
- Create a Python virtual environment
- Install required dependencies
- Set up the launchd service
- Create default configuration
- Test the installation

### Method 2: Manual Installation

If you prefer manual installation:

```bash
# 1. Clone the repository
git clone https://github.com/loopguard/loopguard.git
cd loopguard

# 2. Create virtual environment
python3 -m venv ~/.loopguard/venv
source ~/.loopguard/venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
pip install -e .

# 4. Create configuration directory
mkdir -p ~/.loopguard/{config,logs}

# 5. Copy launchd plist
cp loopguard/templates/com.loopguard.agent.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.loopguard.agent.plist
```

### Post-Installation Verification

After installation, verify everything is working:

```bash
# Check if LoopGuard command is available
loopguard --version

# Check service status
launchctl list | grep loopguard

# Test notifications
loopguard test
```

## Quick Start

### 5-Minute Setup

1. **Install LoopGuard** using the automated installer
2. **Start a Claude Code session** and work normally
3. **Receive notifications** when loops are detected
4. **Configure settings** if needed (see Configuration section)

### Basic Usage

```bash
# Check current status
loopguard status

# Test notifications
loopguard test

# View recent activity
loopguard activity

# Start monitoring manually (if auto-start is disabled)
loopguard monitor start

# Stop monitoring
loopguard monitor stop
```

## Configuration

LoopGuard uses a YAML configuration file located at `~/.loopguard/config/config.yaml`. The installer creates a default configuration that you can customize.

### Configuration Structure

```yaml
# LoopGuard Configuration
detection:
  tool_call_repeats: 3          # Number of repeated tool calls to flag
  error_repeats: 2               # Number of repeated errors to flag
  stagnation_minutes: 5          # Minutes of inactivity to flag
  session_timeout_minutes: 30    # Maximum session duration

monitoring:
  claude_code_path: "/Applications/Claude.app"  # Path to Claude Code
  watch_directories:                              # Directories to monitor
    - "~/Desktop"
    - "~/Documents"
    - "~/Downloads"
  file_patterns:                                   # File patterns to watch
    - "*.py"
    - "*.js"
    - "*.ts"
    - "*.jsx"
    - "*.tsx"
    - "*.md"

notifications:
  enabled: true                 # Enable desktop notifications
  throttle_seconds: 30         # Minimum seconds between notifications
  sound: true                  # Play notification sound
  desktop: true                # Show desktop alerts

logging:
  level: INFO                  # Log level (DEBUG, INFO, WARNING, ERROR)
  max_file_size_mb: 10        # Maximum log file size
  backup_count: 5             # Number of log backups to keep
```

### Detection Settings

- **tool_call_repeats**: How many times the same tool call must be repeated before triggering an alert
- **error_repeats**: Number of repeated error patterns before alerting
- **stagnation_minutes**: Minutes of no meaningful activity before considering a session stagnant
- **session_timeout_minutes**: Maximum recommended session duration

### Monitoring Settings

- **claude_code_path**: Path to your Claude Code installation
- **watch_directories**: Directories where Claude Code might be working
- **file_patterns**: File extensions to monitor for activity

### Notification Settings

- **enabled**: Master switch for notifications
- **throttle_seconds**: Prevent notification spam
- **sound**: Play system notification sound
- **desktop**: Show desktop notification bubbles

## Monitoring

### What LoopGuard Monitors

LoopGuard tracks several patterns in Claude Code sessions:

1. **Repetitive Tool Calls**: Same function called multiple times with similar parameters
2. **Error Loops**: Repeated error messages or failed operations
3. **Session Stagnation**: Long periods without meaningful progress
4. **Resource Usage**: Excessive memory or CPU consumption
5. **File Activity Patterns**: Unusual file access patterns

### Session Analysis

LoopGuard analyzes sessions for productivity patterns:

- **Tool Call Diversity**: Variety of tools being used
- **Progress Indicators**: File changes, successful operations
- **Error Recovery**: How errors are being handled
- **Session Duration**: Total time spent in active development

### Real-time Alerts

When issues are detected, LoopGuard provides:

- **Desktop Notifications**: System-level alerts with detailed messages
- **Log Entries**: Detailed information in log files
- **Session Summaries**: End-of-session reports with recommendations

## Notifications

### Desktop Notifications

LoopGuard uses macOS notification system to provide real-time alerts:

```bash
# Test notification system
loopguard test

# Check notification settings
loopguard config --show notifications
```

### Notification Types

1. **Loop Detection**: "Claude Code may be in a repetitive loop"
2. **Error Pattern**: "Repeated errors detected in session"
3. **Session Stagnation**: "Session appears to be stagnant"
4. **Resource Warning**: "High resource usage detected"
5. **Session Summary**: "Session completed - view summary"

### Customizing Notifications

Edit the notification section in your config file:

```yaml
notifications:
  enabled: true
  throttle_seconds: 30
  sound: true
  desktop: true
  custom_messages:
    loop_detected: "🔄 Claude Code seems stuck in a loop"
    error_pattern: "❌ Repeated errors detected"
    session_stagnant: "⏸️ Session has been inactive"
```

## CLI Reference

### Basic Commands

```bash
# Version information
loopguard --version
loopguard -v

# Help documentation
loopguard --help
loopguard -h

# Status and monitoring
loopguard status
loopguard activity
loopguard logs

# Configuration
loopguard config --show
loopguard config --set detection.tool_call_repeats 5
loopguard config --reset
```

### Monitor Commands

```bash
# Start monitoring
loopguard monitor start
loopguard monitor start --config /path/to/config.yaml

# Stop monitoring
loopguard monitor stop

# Restart monitoring
loopguard monitor restart

# Check monitor status
loopguard monitor status
```

### Test Commands

```bash
# Test notification system
loopguard test
loopguard test notification

# Test detection system
loopguard test detection

# Test configuration
loopguard test config
```

### Configuration Commands

```bash
# Show current configuration
loopguard config show

# Show specific section
loopguard config show detection
loopguard config show notifications

# Set configuration value
loopguard config set detection.tool_call_repeats 4
loopguard config set notifications.enabled false

# Reset configuration to defaults
loopguard config reset

# Validate configuration
loopguard config validate
```

## Troubleshooting

### Common Issues

#### LoopGuard Not Starting

**Symptoms**: No notifications, service not running

**Solutions**:
```bash
# Check if service is loaded
launchctl list | grep loopguard

# Load service manually
launchctl load ~/Library/LaunchAgents/com.loopguard.agent.plist

# Start service manually
launchctl start com.loopguard.agent

# Check logs for errors
tail -f ~/.loopguard/logs/loopguard.error.log
```

#### Notifications Not Working

**Symptoms**: Service running but no desktop notifications

**Solutions**:
```bash
# Test notification system
loopguard test notification

# Check terminal-notifier installation
which terminal-notifier
brew install terminal-notifier

# Check notification permissions
# Go to System Preferences > Security & Privacy > Notifications
```

#### False Positives

**Symptoms**: Too many notifications for normal activity

**Solutions**:
```bash
# Adjust detection sensitivity
loopguard config set detection.tool_call_repeats 5
loopguard config set detection.stagnation_minutes 10

# Increase notification throttling
loopguard config set notifications.throttle_seconds 60
```

#### High Resource Usage

**Symptoms**: LoopGuard consuming too much CPU/memory

**Solutions**:
```bash
# Check current resource usage
loopguard status

# Reduce monitoring frequency
loopguard config set monitoring.check_interval_seconds 30

# Exclude large directories from monitoring
loopguard config set monitoring.watch_directories '["~/Desktop"]'
```

### Debug Mode

Enable debug logging for troubleshooting:

```bash
# Enable debug mode
loopguard config set logging.level DEBUG

# Monitor debug logs
tail -f ~/.loopguard/logs/loopguard.log

# Run in foreground for debugging
loopguard monitor start --foreground --debug
```

### Log Analysis

```bash
# View recent logs
loopguard logs --tail 50

# Filter logs by level
loopguard logs --level ERROR

# Search logs for patterns
loopguard logs --grep "loop_detected"

# Export logs for support
loopguard logs --export ~/loopguard-logs.zip
```

## Advanced Usage

### Custom Detection Rules

Create custom detection patterns:

```yaml
# In config.yaml
detection:
  custom_rules:
    - name: "file_creation_loop"
      pattern: "create_file.*same_name"
      threshold: 3
      action: "notify"
    
    - name: "api_call_timeout"
      pattern: "timeout.*api_call"
      threshold: 2
      action: "terminate_session"
```

### Integration with IDEs

LoopGuard can be integrated with IDE development workflows:

```bash
# IDE-specific configuration
loopguard config set monitoring.ide "vscode"
loopguard config set monitoring.project_detection true
```

### Session Automation

Automate session management:

```yaml
# Auto-session settings
automation:
  auto_terminate_stagnant: true
  auto_save_progress: true
  auto_generate_reports: true
```

### Performance Monitoring

Monitor LoopGuard's own performance:

```bash
# Performance metrics
loopguard metrics
loopguard metrics --detailed

# Resource usage
loopguard status --resources
```

## Uninstallation

### Automated Uninstaller

Use the provided uninstall script for complete removal:

```bash
# Run the uninstaller
./uninstall.sh

# Or download and run directly
curl -fsSL https://raw.githubusercontent.com/loopguard/loopguard/main/uninstall.sh | bash
```

The uninstaller will:
- Stop and remove the launchd service
- Remove command wrappers
- Delete installation directory
- Clean up PATH modifications
- Create configuration backup (optional)

### Manual Uninstallation

If you prefer manual removal:

```bash
# 1. Stop and remove service
launchctl stop com.loopguard.agent
launchctl unload ~/Library/LaunchAgents/com.loopguard.agent.plist
rm ~/Library/LaunchAgents/com.loopguard.agent.plist

# 2. Remove commands
rm -f /usr/local/bin/loopguard
rm -f ~/.local/bin/loopguard

# 3. Remove installation directory
rm -rf ~/.loopguard

# 4. Clean up PATH
# Remove loopguard lines from ~/.zshrc and ~/.bash_profile
```

### Backup Before Uninstall

The uninstaller offers to backup your configuration:

```bash
# Manual backup
cp -r ~/.loopguard ~/loopguard-backup-$(date +%Y%m%d)

# Restore after reinstall
cp -r ~/loopguard-backup-YYYYMMDD/* ~/.loopguard/
```

## Support and Community

### Getting Help

- **Documentation**: https://loopguard.readthedocs.io/
- **Issues**: https://github.com/loopguard/loopguard/issues
- **Discussions**: https://github.com/loopguard/loopguard/discussions
- **Community**: https://discord.gg/loopguard

### Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

### Reporting Issues

When reporting issues, please include:

1. LoopGuard version (`loopguard --version`)
2. macOS version
3. Python version
4. Error logs from `~/.loopguard/logs/`
5. Steps to reproduce
6. Expected vs actual behavior

---

Thank you for using LoopGuard! We hope it helps you have more productive sessions with Claude Code. 🛡️
