"""
File watching service for Claude Code session logs
"""

import os
import time
from pathlib import Path
from typing import Set, Callable, Optional, Dict, Any
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

from .log_parser import LogParser, LogEvent
from .loop_detector import LoopDetector, LoopAlert
from .session_discovery import SessionDiscovery, DiscoveredSession


class SessionFileHandler(FileSystemEventHandler):
    """Handles file system events for Claude Code session files"""
    
    def __init__(self, callback: Callable[[str, list[LogEvent]], None]):
        self.callback = callback
        self.log_parser = LogParser()
        self._file_positions = {}  # Track file positions for incremental reading
    
    def on_modified(self, event):
        """Handle file modification events"""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        # Only process .jsonl files in sessions directories
        if (not file_path.name.endswith('.jsonl') or
            'sessions' not in str(file_path)):
            return
        
        try:
            # Read only new content from the file
            new_events = self._read_new_content(file_path)
            if new_events:
                session_id = self._extract_session_id(file_path)
                self.callback(session_id, new_events)
        except Exception as e:
            print(f"Error processing file {file_path}: {e}")
    
    def _read_new_content(self, file_path: Path) -> list[LogEvent]:
        """Read only new content from a file"""
        file_key = str(file_path)
        current_size = file_path.stat().st_size
        
        # Get last read position
        last_position = self._file_positions.get(file_key, 0)
        
        if current_size <= last_position:
            return []  # No new content
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                f.seek(last_position)
                new_content = f.read()
                
                # Parse new lines
                new_events = []
                for line in new_content.strip().split('\n'):
                    if line.strip():
                        event = self.log_parser._parse_log_entry(
                            {'timestamp': '', 'type': 'assistant', 'message': {}}, 
                            file_path
                        )
                        if event:
                            new_events.append(event)
                
                # Update position
                self._file_positions[file_key] = current_size
                return new_events
                
        except (IOError, UnicodeDecodeError) as e:
            print(f"Error reading file {file_path}: {e}")
            return []
    
    def _extract_session_id(self, file_path: Path) -> str:
        """Extract session ID from file path"""
        # Expected path: ~/.claude/projects/<project>/sessions/<session-id>.jsonl
        parts = file_path.parts
        
        session_idx = -2  # Second to last part should be 'sessions'
        project_idx = -3   # Third to last part should be project name
        
        if (len(parts) >= abs(session_idx) and 
            parts[session_idx] == 'sessions'):
            
            session_id = file_path.stem
            project_name = parts[project_idx]
            return f"{project_name}:{session_id}"
        
        return file_path.stem


class FileWatcher:
    """Enhanced file watcher with multi-session support and automatic discovery"""
    
    def __init__(self, loop_detector: LoopDetector, alert_callback: Callable[[LoopAlert], None]):
        self.loop_detector = loop_detector
        self.alert_callback = alert_callback
        self.log_parser = LogParser()
        self.observer = None
        self.watched_sessions: Set[str] = set()
        self.session_discovery = SessionDiscovery()
        self.session_handlers: Dict[str, SessionFileHandler] = {}
        self._max_sessions = 50  # Limit concurrent session monitoring

    @property
    def is_watching(self) -> bool:
        """Return True if the file watcher is currently running."""
        return self.observer is not None and self.observer.is_alive()
    
    def start_watching(self):
        """Start watching Claude Code session directories with enhanced discovery"""
        claude_dir = Path.home() / ".claude" / "projects"
        
        if not claude_dir.exists():
            print(f"Claude Code directory not found: {claude_dir}")
            return False
        
        # Set up single file system observer for efficiency
        self.observer = Observer()
        
        # Create handler for session file events
        session_handler = SessionFileHandler(self._on_new_events)
        
        # Watch all projects directories with single observer
        for project_dir in claude_dir.iterdir():
            if not project_dir.is_dir():
                continue
            
            sessions_dir = project_dir / "sessions"
            if not sessions_dir.exists():
                continue
            
            self.observer.schedule(session_handler, str(sessions_dir), recursive=False)
            print(f"Watching sessions directory: {sessions_dir}")
        
        self.observer.start()
        
        # Discover and process existing sessions
        discovered_sessions = self.session_discovery.discover_existing_sessions()
        self._process_discovered_sessions(discovered_sessions)
        
        return True
    
    def stop_watching(self):
        """Stop watching files"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
    
    def _on_new_events(self, session_id: str, events: list[LogEvent]):
        """Handle new log events with session management"""
        # Check session limit
        if len(self.watched_sessions) >= self._max_sessions and session_id not in self.watched_sessions:
            print(f"⚠️  Session limit reached ({self._max_sessions}), skipping: {session_id}")
            return
        
        if session_id not in self.watched_sessions:
            self.watched_sessions.add(session_id)
            print(f"Started monitoring session: {session_id}")
        
        # Analyze events for loops
        alerts = self.loop_detector.analyze_events(events)
        
        # Send alerts
        for alert in alerts:
            self.alert_callback(alert)
    
    def _process_discovered_sessions(self, discovered_sessions: Dict[str, DiscoveredSession]):
        """Process sessions discovered during startup"""
        for session_id, discovered_session in discovered_sessions.items():
            print(f"Processing discovered session: {session_id} (Project: {discovered_session.project_id})")
            
            # Reconstruct session state and process recent events
            session_state = self.session_discovery.reconstruct_session_state(session_id)
            if session_state:
                print(f"  Reconstructed state: {len(session_state['recent_entries'])} recent entries")
            
            # Read recent events from existing files
            try:
                events = list(self.log_parser.parse_session_file(discovered_session.file_path))
                if events:
                    # Only process most recent events to avoid processing entire history
                    recent_events = events[-50:]  # Last 50 events
                    self._on_new_events(session_id, recent_events)
            except Exception as e:
                print(f"Error processing discovered session {session_id}: {e}")
    
    def continuous_discovery_update(self):
        """Update with continuous discovery integration"""
        new_sessions = self.session_discovery.continuous_discovery()
        
        for session in new_sessions:
            print(f"🆕 New session discovered: {session.session_id} (Project: {session.project_id})")
            
            # Process new session file
            try:
                events = list(self.log_parser.parse_session_file(session.file_path))
                if events:
                    recent_events = events[-20:]  # Last 20 events for new sessions
                    self._on_new_events(session.session_id, recent_events)
            except Exception as e:
                print(f"Error processing new session {session.session_id}: {e}")
    
    def synchronize_with_processes(self, process_session_map: Dict[str, any]):
        """Synchronize discovered sessions with active processes"""
        active_discovered = self.session_discovery.synchronize_with_processes(list(process_session_map.values()))
        
        # Update monitoring for active sessions
        for session_id, process in active_discovered.items():
            if session_id not in self.watched_sessions:
                print(f"🔄 Activated monitoring for session: {session_id} (PID: {process.pid})")
    
    def get_discovery_stats(self) -> Dict:
        """Get discovery and monitoring statistics"""
        stats = self.session_discovery.get_discovery_stats()
        stats.update({
            'watched_sessions': len(self.watched_sessions),
            'max_sessions': self._max_sessions,
            'observer_active': self.observer.is_alive() if self.observer else False
        })
        return stats
    
    def is_watching_session(self, session_id: str) -> bool:
        """Check if a session is being monitored"""
        return session_id in self.watched_sessions
    
    def remove_session(self, session_id: str):
        """Remove a session from monitoring"""
        if session_id in self.watched_sessions:
            self.watched_sessions.remove(session_id)
            self.loop_detector.clear_session_history(session_id)
            print(f"Stopped monitoring session: {session_id}")
    
    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Get detailed information about a session"""
        discovered_session = self.session_discovery.discovered_sessions.get(session_id)
        if not discovered_session:
            return None
        
        return {
            'session_id': session_id,
            'project_id': discovered_session.project_id,
            'file_path': str(discovered_session.file_path),
            'is_active': discovered_session.is_active,
            'associated_pid': discovered_session.associated_pid,
            'last_modified': discovered_session.last_modified,
            'size_bytes': discovered_session.size_bytes,
            'is_watched': session_id in self.watched_sessions
        }
