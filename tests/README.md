# LoopGuard Week 2 Alpha Test Suite

This directory contains comprehensive test scenarios for LoopGuard Week 2 features.

## Test Coverage

### Enhanced Desktop Notifications
- **Severity Levels**: Test low, medium, and high severity notification handling
- **Actionable Content**: Verify notifications include file paths, line numbers, and specific suggestions
- **Notification Actions**: Test dismiss, snooze, stop session, and view details actions
- **Sound Customization**: Test different sounds for different severity levels
- **Quiet Hours**: Test notification suppression during configured hours

### Session Efficiency Scoring
- **Efficiency Calculation**: Test the enhanced efficiency scoring algorithm
- **End-of-Session Reports**: Verify comprehensive summary generation
- **Token Usage Estimation**: Test improved token usage calculations
- **Progress Indicators**: Test detection of meaningful progress markers
- **Time Wasted Estimation**: Verify calculation of wasted time in loops

### Smart Notification Throttling
- **Per-Project Settings**: Test project-specific notification configurations
- **Adaptive Throttling**: Verify different throttle times for different severities
- **Context-Aware Batching**: Test intelligent notification grouping
- **User Feedback Integration**: Test threshold adjustment based on user behavior

### Error Handling & Graceful Degradation
- **Automatic Recovery**: Test recovery mechanisms for different error types
- **Fallback Modes**: Verify service continues in degraded mode
- **Health Monitoring**: Test comprehensive system health reporting
- **Error Categorization**: Test proper classification of different error types
- **Safe Mode**: Test minimal functionality during critical errors

## Running Tests

### Quick Test
```bash
cd tests
python test_scenarios.py
```

### Detailed Test with Coverage Report
```bash
cd tests
python -m unittest test_scenarios.py -v
```

### Performance Testing
```bash
cd tests
python -c "
from test_scenarios import TestScenarios
import unittest

# Create test suite
suite = unittest.TestLoader().loadTestsFromTestCase(TestScenarios)
runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)

# Performance requirements verification
print(f'Performance Requirements Met: {result.wasSuccessful()}')
"
```

## Test Scenarios

### 1. Real-World Simulation
- Simulate actual Claude Code session patterns
- Test with various file types and operations
- Verify loop detection in complex scenarios

### 2. Edge Case Testing
- Test with malformed log files
- Verify behavior with missing dependencies
- Test resource exhaustion scenarios

### 3. Performance Testing
- Memory usage validation (< 50MB)
- CPU usage monitoring (< 2%)
- Notification response time (< 1 second)

### 4. Integration Testing
- Test all components working together
- Verify configuration loading and validation
- Test graceful shutdown and restart

## Expected Results

### Success Criteria
- All tests pass with > 95% success rate
- Performance requirements met:
  - Memory usage < 50MB during monitoring
  - CPU usage < 2% during active monitoring
  - Notification response time < 1 second from loop detection
  - Session database queries < 100ms response time
- Error handling demonstrates graceful degradation
- No critical failures in core functionality

### Beta Readiness
- Comprehensive test coverage of all Week 2 features
- Performance benchmarks met consistently
- Error recovery mechanisms validated
- User experience scenarios tested
- Documentation and onboarding materials prepared

## Troubleshooting

### Common Test Failures
1. **terminal-notifier not found**: Install with `brew install terminal-notifier`
2. **Permission errors**: Ensure proper file permissions for test directories
3. **Database locks**: Clear test databases between runs
4. **Memory issues**: Monitor system resources during testing

### Debug Mode
Set environment variable for detailed debugging:
```bash
export LOOPGUARD_DEBUG=1
python test_scenarios.py
```

## Next Steps

After successful alpha testing:
1. Review test results and fix any failures
2. Update documentation based on findings
3. Prepare beta user onboarding materials
4. Set up user feedback collection mechanism
5. Deploy to beta testers from r/ClaudeAI community
