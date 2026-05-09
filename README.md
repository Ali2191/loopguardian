# LoopGuard

Real-time AI coding agent loop detector for Claude Code that prevents wasted tokens and costs by alerting you when agents get stuck in repetitive loops.

## The Problem

AI coding agents get stuck in repetitive loops — editing the same file over and over, hitting the same error repeatedly, hallucinating tool calls — burning your token quota and costing real money before you even notice.

LoopGuard monitors your Claude Code sessions in real-time and sends desktop notifications when it detects the agent is looping.

## Features

- **Real-time Monitoring**: Background service that auto-detects Claude Code sessions
- **Loop Detection**: Identifies three types of loops:
  - Repeated identical tool calls (same tool + parameters)
  - Repeated identical error messages  
  - No meaningful file changes during activity
- **Desktop Alerts**: Native macOS notifications with actionable information
- **Configurable Thresholds**: Customize detection sensitivity per project
- **Zero Friction**: Install once, runs automatically on login

## Quick Start

### Installation

```bash
pip install loopguardian
```

### Dependencies

```bash
# Install terminal-notifier for desktop notifications
brew install terminal-notifier
```

### Usage

```bash
# Start LoopGuard service
loopguardian start

# Check status
loopguardian status

# Test notifications
loopguardian test
```

## Configuration

Create a `loopguardian.config.json` file in your project root or `~/.loopguardian/config.json`:

```json
{
  "detection": {
    "tool_call_repeats": 3,
    "error_repeats": 2,
    "stagnation_minutes": 5
  },
  "notifications": {
    "enabled": true,
    "throttle_seconds": 30
  }
}
```

### Detection Settings

- **tool_call_repeats**: Number of identical tool calls before alerting (default: 3)
- **error_repeats**: Number of identical errors before alerting (default: 2)  
- **stagnation_minutes**: Minutes of activity without file changes before alerting (default: 5)

### Notification Settings

- **enabled**: Enable/disable desktop notifications (default: true)
- **throttle_seconds**: Minimum seconds between identical alerts (default: 30)

## How It Works

1. **Process Detection**: LoopGuard monitors for Claude Code processes starting up
2. **Log Monitoring**: When Claude Code is detected, LoopGuard starts watching the session log files
3. **Pattern Analysis**: Real-time analysis detects loop patterns using configurable thresholds
4. **Desktop Alerts**: Immediate notifications when loops are detected with suggested actions

## Example Alerts

```
🚨 LOOP DETECTED: Tool 'str_replace' repeated 3 times on auth.py.
   Session: a1b2c3d4e5f6...
   Severity: medium  
   Suggested: Interrupt the session and provide more specific context
```

## Architecture

- **Process Monitor**: Detects Claude Code startup via process monitoring
- **Log Monitor**: File watching service for Claude Code session logs
- **Loop Detector**: Pattern recognition engine with configurable thresholds
- **Notification Service**: macOS desktop notification system
- **Configuration Manager**: Handles settings and user preferences

## Development

```bash
# Install development dependencies
pip install -r requirements.txt

# Run in development mode
python -m loopguard.cli start
```

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions welcome! Please read the contributing guidelines and submit pull requests to the GitHub repository.
