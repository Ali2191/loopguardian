"""
JSONL log parser for Claude Code sessions
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Iterator
from datetime import datetime, timezone
from dataclasses import dataclass, asdict


@dataclass
class ToolCall:
    """Represents a tool call in Claude Code"""
    tool_name: str
    parameters: Dict[str, Any]
    timestamp: datetime
    session_id: str
    file_path: Optional[str] = None
    error_message: Optional[str] = None


@dataclass 
class LogEvent:
    """Represents a single log event"""
    event_type: str  # 'user', 'assistant', 'tool_call', 'error'
    timestamp: datetime
    session_id: str
    content: Dict[str, Any]
    raw_data: Dict[str, Any]


class LogParser:
    """Parses Claude Code JSONL session logs"""
    
    def __init__(self):
        self.claude_dir = Path.home() / ".claude"
        self.sessions_dir = self.claude_dir / "projects"
    
    def discover_session_files(self) -> Dict[str, Path]:
        """Discover all Claude Code session files"""
        session_files = {}
        
        if not self.sessions_dir.exists():
            return session_files
        
        for project_dir in self.sessions_dir.iterdir():
            if not project_dir.is_dir():
                continue
            
            sessions_path = project_dir / "sessions"
            if not sessions_path.exists():
                continue
            
            for session_file in sessions_path.glob("*.jsonl"):
                session_id = session_file.stem
                project_path = project_dir.name
                full_session_id = f"{project_path}:{session_id}"
                session_files[full_session_id] = session_file
        
        return session_files
    
    def parse_session_file(self, session_file: Path) -> Iterator[LogEvent]:
        """Parse a single session JSONL file"""
        if not session_file.exists():
            return
        
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        data = json.loads(line)
                        event = self._parse_log_entry(data, session_file)
                        if event:
                            yield event
                    except json.JSONDecodeError as e:
                        print(f"JSON decode error in {session_file}:{line_num}: {e}")
                        continue
        except IOError as e:
            print(f"Error reading session file {session_file}: {e}")
    
    def _parse_log_entry(self, data: Dict[str, Any], session_file: Path) -> Optional[LogEvent]:
        """Parse a single log entry"""
        try:
            timestamp_str = data.get('timestamp')
            if timestamp_str:
                # Parse ISO 8601 timestamp
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            else:
                timestamp = datetime.now(timezone.utc)
            
            session_id = data.get('sessionId', session_file.stem)
            event_type = data.get('type', 'unknown')
            
            return LogEvent(
                event_type=event_type,
                timestamp=timestamp,
                session_id=session_id,
                content=data.get('message', {}),
                raw_data=data
            )
        except (ValueError, KeyError) as e:
            print(f"Error parsing log entry: {e}")
            return None
    
    def extract_tool_calls(self, events: List[LogEvent]) -> List[ToolCall]:
        """Extract tool calls from log events"""
        tool_calls = []
        
        for event in events:
            if event.event_type != 'assistant':
                continue
            
            message = event.content
            if not isinstance(message, dict):
                continue
            
            content = message.get('content', [])
            if not isinstance(content, list):
                continue
            
            for content_item in content:
                if isinstance(content_item, dict) and content_item.get('type') == 'tool_use':
                    tool_call = self._parse_tool_call(content_item, event)
                    if tool_call:
                        tool_calls.append(tool_call)
        
        return tool_calls
    
    def _parse_tool_call(self, tool_use: Dict[str, Any], event: LogEvent) -> Optional[ToolCall]:
        """Parse a single tool call"""
        try:
            tool_name = tool_use.get('name', '')
            if not tool_name:
                return None
            
            parameters = tool_use.get('input', {})
            file_path = None
            error_message = None
            
            # Extract file path for common tools
            if tool_name in ['str_replace', 'edit', 'write_to_file', 'read_file']:
                file_path = parameters.get('path') or parameters.get('file_path')
            
            # Check for errors in subsequent events
            error_message = self._find_tool_error(tool_use, event.session_id)
            
            return ToolCall(
                tool_name=tool_name,
                parameters=parameters,
                timestamp=event.timestamp,
                session_id=event.session_id,
                file_path=file_path,
                error_message=error_message
            )
        except (KeyError, ValueError):
            return None
    
    def _find_tool_error(self, tool_use: Dict[str, Any], session_id: str) -> Optional[str]:
        """Find error message for a tool call (simplified for MVP)"""
        # This would need more sophisticated logic to match tool calls with their results
        # For MVP, we'll extract errors from assistant message content
        return None
    
    def get_session_info(self, session_file: Path) -> Dict[str, Any]:
        """Get basic session information"""
        try:
            stat = session_file.stat()
            return {
                'file_path': str(session_file),
                'size_bytes': stat.st_size,
                'modified_time': datetime.fromtimestamp(stat.st_mtime),
                'session_id': session_file.stem
            }
        except OSError:
            return {}
