"""
Test LoopGuard with real Claude Code session data
"""

import tempfile
import shutil
from pathlib import Path

from loopguard.config import Config
from loopguard.log_parser import LogParser
from loopguard.loop_detector import LoopDetector
from loopguard.notifications import NotificationService


def test_with_sample_session():
    """Test loop detection with sample Claude Code session"""
    print("Testing with sample Claude Code session...")
    
    # Create temporary Claude Code directory structure
    with tempfile.TemporaryDirectory() as temp_dir:
        claude_dir = Path(temp_dir) / ".claude" / "projects" / "test-project" / "sessions"
        claude_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy simple session file
        sample_file = Path(__file__).parent / "simple_session.jsonl"
        session_file = claude_dir / "test-loop-session-123.jsonl"
        shutil.copy(sample_file, session_file)
        
        # Initialize components
        config = Config()
        detector = LoopDetector(config)
        parser = LogParser()
        notification_service = NotificationService(enabled=True)
        
        # Parse the session
        events = list(parser.parse_session_file(session_file))
        print(f"   Parsed {len(events)} events from session")
        
        # Analyze for loops
        alerts = detector.analyze_events(events)
        print(f"   Detected {len(alerts)} loops")
        
        # Display alerts
        for alert in alerts:
            print(f"\n🚨 {alert.alert_type.upper()}:")
            print(f"   Description: {alert.description}")
            print(f"   Severity: {alert.severity}")
            print(f"   Suggested: {alert.suggested_action}")
            
            # Test notification
            if notification_service.is_available():
                print("   📱 Sending desktop notification...")
                success = notification_service.send_alert(alert)
                print(f"   {'✅ Sent' if success else '❌ Failed'}")
        
        # Verify we detected the expected loop
        tool_loops = [a for a in alerts if a.alert_type == 'tool_call_loop']
        assert len(tool_loops) >= 1, "Should have detected tool call loop"
        
        print("✅ Real session test completed successfully")


if __name__ == '__main__':
    test_with_sample_session()
