# LoopGuard Troubleshooting Guide

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [Service Problems](#service-problems)
3. [Notification Issues](#notification-issues)
4. [Detection Problems](#detection-problems)
5. [Performance Issues](#performance-issues)
6. [Configuration Issues](#configuration-issues)
7. [Log Analysis](#log-analysis)
8. [Advanced Debugging](#advanced-debugging)
9. [Common Error Messages](#common-error-messages)
10. [Getting Help](#getting-help)

## Installation Issues

### "Python 3 not found" Error

**Problem**: Installer fails with "Python 3 is required but not installed"

**Solutions**:
```bash
# Install Python 3 using Homebrew
brew install python3

# Or download from python.org
# https://www.python.org/downloads/macos/

# Verify installation
python3 --version
```

### "Permission denied" during Installation

**Problem**: Installer fails with permission errors

**Solutions**:
```bash
# Install to user directory instead of system directory
./install.sh
# Choose installation directory when prompted

# Or run with sudo (not recommended)
sudo ./install.sh
```

### "pip3 not found" Error

**Problem**: pip3 is not available

**Solutions**:
```bash
# Install pip3
python3 -m ensurepip --upgrade

# Or use Python 3's built-in pip
python3 -m pip --version
```

### Homebrew Installation Fails

**Problem**: Cannot install Homebrew for terminal-notifier

**Solutions**:
```bash
# Skip terminal-notifier installation
./install.sh
# Choose "n" when prompted about terminal-notifier

# Or install Homebrew manually
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

## Service Problems

### Service Not Running

**Problem**: LoopGuard service not found in process list

**Diagnosis**:
```bash
# Check if service is loaded
launchctl list | grep loopguard

# Check service status
loopguard status
```

**Solutions**:
```bash
# Load the service manually
launchctl load ~/Library/LaunchAgents/com.loopguard.agent.plist

# Start the service
launchctl start com.loopguard.agent

# Restart the service
launchctl stop com.loopguard.agent
launchctl start com.loopguard.agent
```

### Service Crashes on Startup

**Problem**: Service starts but immediately crashes

**Diagnosis**:
```bash
# Check error logs
tail -f ~/.loopguard/logs/loopguard.error.log

# Look for specific error messages
grep -i error ~/.loopguard/logs/loopguard.error.log
```

**Solutions**:
```bash
# Check Python environment
source ~/.loopguard/venv/bin/activate
python -c "import loopguard"

# Reinstall dependencies
source ~/.loopguard/venv/bin/activate
pip install --upgrade -r requirements.txt

# Reset configuration
loopguard config reset
```

### Service Won't Stop

**Problem**: Cannot stop the LoopGuard service

**Solutions**:
```bash
# Force stop
launchctl stop com.loopguard.agent

# Kill process manually
pkill -f loopguard

# Remove and reload service
launchctl unload ~/Library/LaunchAgents/com.loopguard.agent.plist
launchctl load ~/Library/LaunchAgents/com.loopguard.agent.plist
```

## Notification Issues

### No Desktop Notifications

**Problem**: LoopGuard is running but no notifications appear

**Diagnosis**:
```bash
# Test notification system
loopguard test notification

# Check terminal-notifier
which terminal-notifier
terminal-notifier -help
```

**Solutions**:
```bash
# Install terminal-notifier
brew install terminal-notifier

# Check notification permissions
# Go to System Preferences > Security & Privacy > Notifications
# Find Terminal in the list and enable notifications

# Test manually
terminal-notifier -title "Test" -message "This is a test"
```

### Too Many Notifications

**Problem**: Receiving excessive notifications

**Solutions**:
```bash
# Increase throttling
loopguard config set notifications.throttle_seconds 60

# Make detection less sensitive
loopguard config set detection.tool_call_repeats 5
loopguard config set detection.error_repeats 3

# Disable specific notification types
loopguard config set notifications.enabled false
```

### Notification Sound Not Working

**Problem**: Notifications appear but no sound plays

**Solutions**:
```bash
# Check system sound settings
# Go to System Preferences > Sound > Sound Effects

# Test sound manually
terminal-notifier -title "Test" -message "Sound test" -sound default

# Disable sound if not working
loopguard config set notifications.sound false
```

## Detection Problems

### False Positives

**Problem**: LoopGuard alerts for normal activity

**Solutions**:
```bash
# Adjust detection thresholds
loopguard config set detection.tool_call_repeats 5
loopguard config set detection.stagnation_minutes 10

# Exclude certain directories
loopguard config set monitoring.watch_directories '["~/Desktop"]'

# Add custom rules to ignore specific patterns
```

### Missing Detections

**Problem**: LoopGuard doesn't detect obvious loops

**Solutions**:
```bash
# Make detection more sensitive
loopguard config set detection.tool_call_repeats 2
loopguard config set detection.error_repeats 1

# Enable debug logging
loopguard config set logging.level DEBUG

# Check what's being monitored
loopguard status --verbose
```

### Claude Code Not Detected

**Problem**: LoopGuard doesn't find Claude Code sessions

**Diagnosis**:
```bash
# Check Claude Code path
loopguard config show monitoring.claude_code_path

# Verify Claude Code installation
ls -la "/Applications/Claude.app"
```

**Solutions**:
```bash
# Set correct Claude Code path
loopguard config set monitoring.claude_code_path "/Applications/Claude.app"

# Add alternative paths
loopguard config set monitoring.claude_code_paths '["/Applications/Claude.app", "~/Applications/Claude.app"]'
```

## Performance Issues

### High CPU Usage

**Problem**: LoopGuard consuming excessive CPU

**Diagnosis**:
```bash
# Check resource usage
loopguard status --resources

# Monitor process activity
top -pid $(pgrep -f loopguard)
```

**Solutions**:
```bash
# Reduce monitoring frequency
loopguard config set monitoring.check_interval_seconds 30

# Exclude large directories
loopguard config set monitoring.watch_directories '["~/Desktop"]'

# Limit file patterns
loopguard config set monitoring.file_patterns '["*.py", "*.js"]'
```

### High Memory Usage

**Problem**: LoopGuard using too much memory

**Solutions**:
```bash
# Reduce log retention
loopguard config set logging.max_file_size_mb 5
loopguard config set logging.backup_count 2

# Clear old logs
rm ~/.loopguard/logs/*.old

# Restart service
launchctl stop com.loopguard.agent
launchctl start com.loopguard.agent
```

### Slow System Response

**Problem**: System becomes slow when LoopGuard is running

**Solutions**:
```bash
# Disable real-time monitoring
loopguard config set monitoring.real_time false

# Increase check intervals
loopguard config set monitoring.check_interval_seconds 60

# Monitor fewer directories
loopguard config set monitoring.watch_directories '["~/Desktop"]'
```

## Configuration Issues

### Invalid Configuration

**Problem**: Configuration file contains errors

**Diagnosis**:
```bash
# Validate configuration
loopguard config validate

# Check syntax
python -c "import yaml; yaml.safe_load(open('~/.loopguard/config/config.yaml'))"
```

**Solutions**:
```bash
# Reset to defaults
loopguard config reset

# Edit manually with validation
nano ~/.loopguard/config/config.yaml

# Test specific sections
loopguard config show detection
```

### Configuration Not Applied

**Problem**: Changes to config don't take effect

**Solutions**:
```bash
# Restart service after config change
launchctl stop com.loopguard.agent
launchctl start com.loopguard.agent

# Verify config is being read
loopguard config show

# Check for syntax errors in config file
grep -n "error" ~/.loopguard/logs/loopguard.error.log
```

### Missing Configuration File

**Problem**: Config file doesn't exist

**Solutions**:
```bash
# Create default config
mkdir -p ~/.loopguard/config
loopguard config reset

# Or create manually
cat > ~/.loopguard/config/config.yaml << EOF
detection:
  tool_call_repeats: 3
  error_repeats: 2
  stagnation_minutes: 5

notifications:
  enabled: true
  throttle_seconds: 30
EOF
```

## Log Analysis

### Viewing Logs

```bash
# Recent logs
loopguard logs --tail 50

# Live monitoring
tail -f ~/.loopguard/logs/loopguard.log

# Error logs only
tail -f ~/.loopguard/logs/loopguard.error.log

# Filter by level
loopguard logs --level ERROR
loopguard logs --level DEBUG
```

### Searching Logs

```bash
# Search for specific patterns
loopguard logs --grep "loop_detected"
loopguard logs --grep "error"

# Search by time
grep "2024-01-01" ~/.loopguard/logs/loopguard.log

# Count occurrences
grep -c "notification" ~/.loopguard/logs/loopguard.log
```

### Exporting Logs

```bash
# Export for support
loopguard logs --export ~/loopguard-logs.zip

# Manual export
zip -r ~/loopguard-support.zip ~/.loopguard/logs/ ~/.loopguard/config/
```

## Advanced Debugging

### Debug Mode

```bash
# Enable debug logging
loopguard config set logging.level DEBUG

# Run in foreground
loopguard monitor start --foreground --debug

# Monitor debug output
tail -f ~/.loopguard/logs/loopguard.log | grep DEBUG
```

### Manual Testing

```bash
# Test individual components
loopguard test detection
loopguard test notification
loopguard test config

# Test with custom config
loopguard monitor start --config /path/to/test-config.yaml
```

### Performance Profiling

```bash
# Profile resource usage
python -m cProfile -o ~/.loopguard/profile.stats -m loopguard.cli status

# Analyze profile
python -c "
import pstats
p = pstats.Stats('~/.loopguard/profile.stats')
p.sort_stats('cumulative').print_stats(20)
"
```

## Common Error Messages

### "Permission denied"

**Cause**: Trying to write to protected directories

**Solution**: Check file permissions, use user directories

### "ModuleNotFoundError: No module named 'loopguard'"

**Cause**: Python path issues or incomplete installation

**Solution**: Reinstall LoopGuard, check virtual environment

### "launchctl: Could not find service"

**Cause**: Service not properly loaded

**Solution**: Load service manually, check plist file

### "Connection refused"

**Cause**: Service not running or network issues

**Solution**: Start service, check firewall settings

### "Configuration validation failed"

**Cause**: Invalid YAML or missing required fields

**Solution**: Validate config, reset to defaults

## Getting Help

### Automated Diagnostics

```bash
# Run diagnostic tool
loopguard diagnostics

# Generate support bundle
loopguard support-bundle
```

### Collecting Information for Support

When reporting issues, include:

1. **System Information**:
   ```bash
   loopguard --version
   sw_vers
   python3 --version
   ```

2. **Configuration**:
   ```bash
   loopguard config show
   ```

3. **Recent Logs**:
   ```bash
   loopguard logs --tail 100
   ```

4. **Service Status**:
   ```bash
   launchctl list | grep loopguard
   loopguard status
   ```

### Community Support

- **GitHub Issues**: https://github.com/loopguard/loopguard/issues
- **Discussions**: https://github.com/loopguard/loopguard/discussions
- **Discord**: https://discord.gg/loopguard

### Creating a Support Bundle

```bash
# Generate complete support package
loopguard support-bundle --output ~/loopguard-support.zip

# Include additional context
loopguard support-bundle --include logs,config,system
```

## Recovery Procedures

### Complete Reset

```bash
# Stop service
launchctl stop com.loopguard.agent

# Backup config
cp ~/.loopguard/config/config.yaml ~/loopguard-config-backup.yaml

# Reset everything
loopguard config reset
rm ~/.loopguard/logs/*

# Restart
launchctl start com.loopguard.agent
```

### Clean Reinstall

```bash
# Uninstall completely
./uninstall.sh

# Reinstall fresh
./install.sh

# Restore custom config if needed
cp ~/loopguard-config-backup.yaml ~/.loopguard/config/config.yaml
```

---

This troubleshooting guide should help resolve most common issues with LoopGuard. If you continue to experience problems, please reach out to our support channels with the diagnostic information collected above.
