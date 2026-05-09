# Changelog

All notable changes to LoopGuard will be documented in this file.

## [0.1.0] - 2025-05-10

### Added
- Real-time Claude Code session monitoring
- Loop detection for repeated tool calls, errors, and stagnation
- macOS desktop notifications with terminal-notifier
- Configurable detection thresholds
- Background service with auto-start on login
- CLI interface with start/stop/status/test commands

### Features
- Process monitoring for Claude Code detection
- JSONL log file parsing and watching
- Three types of loop detection:
  - Tool call loops (same tool + parameters repeated N times)
  - Error loops (identical error messages repeated N times)  
  - Progress stagnation (no file changes during N minutes of activity)
- Desktop notifications with actionable alerts
- Configuration via `loopguard.config.json`

### Installation
- `pip install loopguard` for package installation
- `./install.sh` for complete macOS setup with launchd service
- Dependencies: watchdog, psutil, click, jsonschema, terminal-notifier

### Known Issues
- JSONL parsing requires properly formatted JSON lines
- Timezone comparisons fixed for datetime compatibility
- Background service requires manual launchd loading
