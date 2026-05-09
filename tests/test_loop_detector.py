"""
Test loop detection functionality
"""

import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

from loopguard.config import Config
from loopguard.loop_detector import LoopDetector
from loopguard.log_parser import LogEvent


def create_test_event(event_type: str, timestamp: datetime, content: dict) -> LogEvent:
    """Create a test log event"""
    return LogEvent(
        event_type=event_type,
        timestamp=timestamp,
        session_id="test-session",
        content=content,
        raw_data={}
    )


def test_tool_call_loop_detection():
    """Test detection of repeated tool calls"""
    print("Testing tool call loop detection...")
    
    config = Config()
    detector = LoopDetector(config)
    
    # Create events with repeated tool calls
    base_time = datetime.now()
    events = []
    
    for i in range(4):  # 4 identical tool calls (threshold is 3)
        event = create_test_event(
            event_type='assistant',
            timestamp=base_time + timedelta(minutes=i),
            content={
                'content': [
                    {
                        'type': 'tool_use',
                        'name': 'str_replace',
                        'input': {
                            'path': '/test/file.py',
                            'old_str': 'old code',
                            'new_str': 'new code'
                        }
                    }
                ]
            }
        )
        events.append(event)
    
    alerts = detector.analyze_events(events)
    
    # Debug: print all alerts to see what we're getting
    print(f"   Generated {len(alerts)} alerts: {[a.alert_type for a in alerts]}")
    
    tool_alerts = [a for a in alerts if a.alert_type == 'tool_call_loop']
    assert len(tool_alerts) >= 1, f"Expected at least 1 tool alert, got {len(tool_alerts)}"
    alert = tool_alerts[0]
    assert alert.alert_type == 'tool_call_loop'
    assert 'str_replace' in alert.description
    assert alert.session_id == 'test-session'
    
    print("✅ Tool call loop detection works")


def test_error_loop_detection():
    """Test detection of repeated errors"""
    print("Testing error loop detection...")
    
    config = Config()
    detector = LoopDetector(config)
    
    # Create events with repeated errors
    base_time = datetime.now()
    events = []
    
    for i in range(2):  # 2 identical errors (threshold is 2)
        event = create_test_event(
            event_type='assistant',
            timestamp=base_time + timedelta(minutes=i),
            content={
                'content': f'Error: Permission denied to read file /test/secret.py'
            }
        )
        events.append(event)
    
    alerts = detector.analyze_events(events)
    
    # Should detect error loop
    error_alerts = [a for a in alerts if a.alert_type == 'error_loop']
    assert len(error_alerts) >= 1, f"Expected at least 1 error alert, got {len(error_alerts)}"
    
    print("✅ Error loop detection works")


def test_stagnation_detection():
    """Test detection of stagnation"""
    print("Testing stagnation detection...")
    
    config = Config()
    detector = LoopDetector(config)
    
    # Create events with activity but no file changes
    base_time = datetime.now()
    events = []
    
    # Add many events but no file operations
    for i in range(15):
        event = create_test_event(
            event_type='assistant',
            timestamp=base_time + timedelta(minutes=i),
            content={
                'content': 'Thinking about the problem...'
            }
        )
        events.append(event)
    
    alerts = detector.analyze_events(events)
    
    # Should detect stagnation
    stagnation_alerts = [a for a in alerts if a.alert_type == 'stagnation']
    assert len(stagnation_alerts) >= 1, f"Expected at least 1 stagnation alert, got {len(stagnation_alerts)}"
    
    print("✅ Stagnation detection works")


def test_notification_throttling():
    """Test alert throttling"""
    print("Testing notification throttling...")
    
    config = Config()
    detector = LoopDetector(config)
    
    # Create identical events that should trigger alerts
    base_time = datetime.now()
    events = []
    
    # First set of tool calls (should trigger alert)
    for i in range(3):
        event = create_test_event(
            event_type='assistant',
            timestamp=base_time + timedelta(seconds=i*10),
            content={
                'content': [
                    {
                        'type': 'tool_use',
                        'name': 'str_replace',
                        'input': {'path': '/test/file.py'}
                    }
                ]
            }
        )
        events.append(event)
    
    alerts1 = detector.analyze_events(events)
    assert len(alerts1) == 1, "First set should trigger alert"
    
    # Second identical set soon after (should be throttled)
    events2 = []
    for i in range(3):
        event = create_test_event(
            event_type='assistant',
            timestamp=base_time + timedelta(seconds=i*10) + timedelta(seconds=10),
            content={
                'content': [
                    {
                        'type': 'tool_use',
                        'name': 'str_replace',
                        'input': {'path': '/test/file.py'}
                    }
                ]
            }
        )
        events2.append(event)
    
    alerts2 = detector.analyze_events(events2)
    # Should be throttled (no new alerts for same type)
    tool_alerts2 = [a for a in alerts2 if a.alert_type == 'tool_call_loop']
    assert len(tool_alerts2) == 0, "Second set should be throttled"
    
    print("✅ Notification throttling works")


if __name__ == '__main__':
    print("🧪 Running LoopGuard tests...")
    
    test_tool_call_loop_detection()
    test_error_loop_detection()
    test_stagnation_detection()
    test_notification_throttling()
    
    print("✅ All tests passed!")
