# LoopGuard Quick Start Guide

Get LoopGuard up and running in 5 minutes! 🚀

## ⚡ 5-Minute Setup

### Step 1: Install LoopGuard (1 minute)

```bash
# Download and run the installer
curl -fsSL https://raw.githubusercontent.com/loopguard/loopguard/main/install.sh | bash
```

The installer will automatically:
- ✅ Check system requirements
- ✅ Install dependencies  
- ✅ Set up the background service
- ✅ Create default configuration
- ✅ Test the installation

### Step 2: Verify Installation (30 seconds)

```bash
# Check that LoopGuard is working
loopguard --version
loopguard status
```

You should see version information and service status.

### Step 3: Test Notifications (30 seconds)

```bash
# Test desktop notifications
loopguard test
```

You should see a test notification on your screen.

### Step 4: Start Using Claude Code (2 minutes)

Simply start using Claude Code as you normally would. LoopGuard will automatically:

- 🔍 Monitor your sessions in the background
- 🚨 Alert you if it detects loops or issues
- 📊 Track your productivity patterns
- 💾 Log activity for analysis

### Step 5: Customize (Optional, 1 minute)

If you want to adjust settings:

```bash
# View current settings
loopguard config show

# Adjust detection sensitivity
loopguard config set detection.tool_call_repeats 5

# Enable/disable notifications
loopguard config set notifications.enabled true
```

## 🎯 You're All Set!

LoopGuard is now protecting your Claude Code sessions. You'll receive notifications if:

- 🔄 Claude gets stuck in repetitive tool calls
- ❌ Error patterns emerge in your session  
- ⏸️ Your session becomes stagnant
- 📊 Resource usage becomes excessive

## 📋 Essential Commands

```bash
# Check status
loopguard status

# Test notifications
loopguard test

# View recent activity
loopguard activity

# View logs
loopguard logs

# Configure settings
loopguard config show
loopguard config set <key> <value>
```

## 🔧 Common Customizations

### Adjust Detection Sensitivity

```bash
# More sensitive (detects loops faster)
loopguard config set detection.tool_call_repeats 2

# Less sensitive (fewer false alarms)
loopguard config set detection.tool_call_repeats 5
```

### Change Notification Settings

```bash
# Disable notifications temporarily
loopguard config set notifications.enabled false

# Increase time between notifications
loopguard config set notifications.throttle_seconds 60
```

### Monitor Specific Directories

```bash
# Add a project directory to monitor
loopguard config set monitoring.watch_directories '["~/Desktop", "~/Documents", "~/MyProject"]'
```

## 🚨 What to Do When Alerted

When LoopGuard detects an issue:

1. **Review the notification** - It will tell you what type of issue was detected
2. **Check your session** - Look for repetitive patterns or stuck processes
3. **Take corrective action**:
   - For loops: Restart the task or try a different approach
   - For errors: Review the error messages and adjust your approach
   - For stagnation: Take a break or refocus the session

## 📊 Understanding Your Sessions

LoopGuard tracks several metrics:

- **Session Duration**: How long you've been working
- **Tool Call Diversity**: Variety of tools being used
- **Error Rate**: Frequency of errors in the session
- **Progress Indicators**: File changes and successful operations

View detailed analytics:

```bash
# Session summary
loopguard activity --summary

# Detailed metrics
loopguard activity --detailed
```

## 🆘 Quick Troubleshooting

### No Notifications?

```bash
# Test notification system
loopguard test notification

# Check if service is running
launchctl list | grep loopguard

# Restart service if needed
launchctl stop com.loopguard.agent
launchctl start com.loopguard.agent
```

### Too Many False Alarms?

```bash
# Make detection less sensitive
loopguard config set detection.tool_call_repeats 5
loopguard config set detection.stagnation_minutes 10
```

### Service Not Running?

```bash
# Start manually
loopguard monitor start

# Check logs for errors
tail -f ~/.loopguard/logs/loopguard.error.log
```

## 📁 Important File Locations

- **Configuration**: `~/.loopguard/config/config.yaml`
- **Logs**: `~/.loopguard/logs/`
- **Installation**: `~/.loopguard/`

## 🔄 Daily Workflow

1. **Start your day** - LoopGuard is already running in the background
2. **Work with Claude Code** - Use it normally, no changes needed
3. **Receive alerts** - Take action when LoopGuard notifies you
4. **End of day** - Check your session summary with `loopguard activity`

## 🎉 Success!

You've successfully set up LoopGuard! Here's what you can expect:

- ✅ **Automatic monitoring** - No manual intervention needed
- ✅ **Intelligent alerts** - Only notified when necessary
- ✅ **Productivity insights** - Understand your coding patterns
- ✅ **Minimal overhead** - Lightweight background service

## 📚 Next Steps

- **Read the full User Guide**: `docs/USER_GUIDE.md`
- **Explore advanced features**: Configuration, custom rules, integrations
- **Join the community**: GitHub discussions, Discord server
- **Report issues**: Help us improve LoopGuard

## 🛡️ Need Help?

- **Documentation**: https://loopguard.readthedocs.io/
- **Issues**: https://github.com/loopguard/loopguard/issues
- **Community**: https://discord.gg/loopguard

---

**Congratulations! 🎉** You're now protected by LoopGuard. Enjoy more productive and frustration-free Claude Code sessions!
