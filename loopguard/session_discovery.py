"""
Automatic session discovery for Claude Code sessions
"""

import os
import json
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import glob

from .process_monitor import ClaudeSession


@dataclass
class DiscoveredSession:
    """Represents a discovered Claude Code session from file system"""
    session_id: str
    project_id: str
    file_path: Path
    last_modified: float
    size_bytes: int
    is_active: bool = False
    associated_pid: Optional[int] = None
    metadata: Dict = field(default_factory=dict)


class SessionDiscovery:
    """Automatic discovery of Claude Code sessions with dual-approach detection"""
    
    def __init__(self, claude_base_path: Optional[Path] = None):
        self.claude_base_path = claude_base_path or (Path.home() / ".claude" / "projects")
        self.discovered_sessions: Dict[str, DiscoveredSession] = {}
        self.project_sessions: Dict[str, Set[str]] = {}  # project_id -> session_ids
        self._lock = threading.RLock()
        self._last_scan_time = 0
        self._scan_interval = 30  # seconds
        
    def discover_existing_sessions(self) -> Dict[str, DiscoveredSession]:
        """Immediate scan of existing Claude Code sessions on startup"""
        with self._lock:
            discovered: Dict[str, DiscoveredSession] = {}
            
            if not self.claude_base_path.exists():
                print(f"Claude Code directory not found: {self.claude_base_path}")
                return discovered
            
            # Scan all project directories for session files
            for project_dir in self.claude_base_path.iterdir():
                if not project_dir.is_dir():
                    continue
                
                project_id = project_dir.name
                sessions = self._scan_project_sessions(project_dir, project_id)
                discovered.update(sessions)
            
            self.discovered_sessions = discovered
            self._update_project_mappings()
            self._last_scan_time = time.time()
            
            print(f"🔍 Discovered {len(discovered)} existing sessions across {len(self.project_sessions)} projects")
            return discovered
    
    def continuous_discovery(self) -> List[DiscoveredSession]:
        """Continuous discovery integration with process monitoring"""
        with self._lock:
            current_time = time.time()
            
            # Throttle scans to avoid excessive filesystem access
            if current_time - self._last_scan_time < self._scan_interval:
                return []
            
            new_sessions = []
            current_discovered = set()
            
            # Re-scan for new sessions
            for project_dir in self.claude_base_path.iterdir():
                if not project_dir.is_dir():
                    continue
                
                project_id = project_dir.name
                sessions = self._scan_project_sessions(project_dir, project_id)
                
                for session_id, session in sessions.items():
                    current_discovered.add(session_id)
                    
                    if session_id not in self.discovered_sessions:
                        new_sessions.append(session)
                        self.discovered_sessions[session_id] = session
                    else:
                        # Update existing session metadata
                        self.discovered_sessions[session_id].last_modified = session.last_modified
                        self.discovered_sessions[session_id].size_bytes = session.size_bytes
                        self.discovered_sessions[session_id].is_active = session.is_active
            
            # Clean up sessions that no longer exist
            removed_sessions = set(self.discovered_sessions.keys()) - current_discovered
            for session_id in removed_sessions:
                del self.discovered_sessions[session_id]
            
            self._update_project_mappings()
            self._last_scan_time = current_time
            
            return new_sessions
    
    def synchronize_with_processes(self, active_processes: List[ClaudeSession]) -> Dict[str, ClaudeSession]:
        """Reconcile discovered sessions with active processes"""
        with self._lock:
            session_map = {}
            
            for process in active_processes:
                # Try to match process with discovered session
                matching_session = self._find_matching_session(process)
                
                if matching_session:
                    session_id = matching_session.session_id
                    matching_session.is_active = True
                    matching_session.associated_pid = process.pid
                    session_map[session_id] = process
                else:
                    # Create session entry for process without discovered file
                    session_id = self._generate_session_id_from_process(process)
                    session_map[session_id] = process
            
            # Mark unmatched discovered sessions as inactive
            for session in self.discovered_sessions.values():
                if session.session_id not in session_map:
                    session.is_active = False
                    session.associated_pid = None
            
            return session_map
    
    def get_session_file_path(self, session_id: str) -> Optional[Path]:
        """Get file path for a discovered session"""
        with self._lock:
            session = self.discovered_sessions.get(session_id)
            return session.file_path if session else None
    
    def get_project_sessions(self, project_id: str) -> List[DiscoveredSession]:
        """Get all sessions for a specific project"""
        with self._lock:
            session_ids = self.project_sessions.get(project_id, set())
            return [self.discovered_sessions[sid] for sid in session_ids if sid in self.discovered_sessions]
    
    def get_active_discovered_sessions(self) -> List[DiscoveredSession]:
        """Get all discovered sessions that are currently active"""
        with self._lock:
            return [s for s in self.discovered_sessions.values() if s.is_active]
    
    def reconstruct_session_state(self, session_id: str) -> Optional[Dict]:
        """Reconstruct session state from historical log files"""
        with self._lock:
            session = self.discovered_sessions.get(session_id)
            if not session or not session.file_path.exists():
                return None
            
            try:
                # Read last few entries to understand session state
                state = {
                    'session_id': session_id,
                    'project_id': session.project_id,
                    'last_activity': session.last_modified,
                    'file_size': session.size_bytes,
                    'recent_entries': []
                }
                
                # Read last 10 lines to understand recent activity
                with open(session.file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[-10:]
                    
                for i, line in enumerate(lines):
                    try:
                        entry = json.loads(line.strip())
                        state['recent_entries'].append({
                            'line_number': len(lines) - 10 + i + 1,
                            'timestamp': entry.get('timestamp', ''),
                            'type': entry.get('type', ''),
                            'preview': str(entry.get('message', ''))[:100]
                        })
                    except json.JSONDecodeError:
                        continue
                
                return state
                
            except (IOError, UnicodeDecodeError) as e:
                print(f"Error reconstructing session state for {session_id}: {e}")
                return None
    
    def _scan_project_sessions(self, project_dir: Path, project_id: str) -> Dict[str, DiscoveredSession]:
        """Scan a single project directory for session files"""
        sessions = {}
        sessions_dir = project_dir / "sessions"
        
        if not sessions_dir.exists():
            return sessions
        
        # Look for .jsonl session files
        pattern = str(sessions_dir / "*.jsonl")
        for file_path in glob.glob(pattern):
            file_path = Path(file_path)
            
            try:
                stat = file_path.stat()
                session_id = file_path.stem
                
                # Extract metadata from file name if it follows naming convention
                metadata = self._extract_session_metadata(file_path)
                
                session = DiscoveredSession(
                    session_id=session_id,
                    project_id=project_id,
                    file_path=file_path,
                    last_modified=stat.st_mtime,
                    size_bytes=stat.st_size,
                    metadata=metadata
                )
                
                sessions[session_id] = session
                
            except OSError as e:
                print(f"Error scanning session file {file_path}: {e}")
                continue
        
        return sessions
    
    def _extract_session_metadata(self, file_path: Path) -> Dict:
        """Extract metadata from session file path and content"""
        metadata = {}
        
        # Extract from filename pattern
        filename = file_path.stem
        if '_' in filename:
            parts = filename.split('_')
            if len(parts) >= 2 and parts[-1].isdigit():
                metadata['timestamp'] = int(parts[-1])
        
        # Try to read first line for additional metadata
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                if first_line:
                    try:
                        entry = json.loads(first_line)
                        metadata['first_entry'] = entry.get('timestamp', '')
                        metadata['session_type'] = entry.get('type', '')
                    except json.JSONDecodeError:
                        pass
        except (IOError, UnicodeDecodeError):
            pass
        
        return metadata
    
    def _find_matching_session(self, process: ClaudeSession) -> Optional[DiscoveredSession]:
        """Find discovered session that matches a process"""
        # Try multiple matching strategies
        
        # Strategy 1: Direct session ID match
        if process.session_id:
            session = self.discovered_sessions.get(process.session_id)
            if session:
                return session
        
        # Strategy 2: Project path matching
        process_path = process.project_path
        if process_path:
            for session in self.discovered_sessions.values():
                if session.project_id in process_path:
                    return session
        
        # Strategy 3: Timestamp matching (within 5 minutes)
        process_time = process.start_time
        for session in self.discovered_sessions.values():
            if abs(session.last_modified - process_time) < 300:  # 5 minutes
                return session
        
        return None
    
    def _generate_session_id_from_process(self, process: ClaudeSession) -> str:
        """Generate session ID from process when no file discovered"""
        import hashlib
        data = f"{process.pid}_{process.start_time}_{process.cmdline}"
        return hashlib.md5(data.encode()).hexdigest()[:12]
    
    def _update_project_mappings(self):
        """Update project to session mappings"""
        self.project_sessions.clear()
        
        for session_id, session in self.discovered_sessions.items():
            project_id = session.project_id
            if project_id not in self.project_sessions:
                self.project_sessions[project_id] = set()
            self.project_sessions[project_id].add(session_id)
    
    def get_discovery_stats(self) -> Dict:
        """Get discovery statistics"""
        with self._lock:
            active_count = sum(1 for s in self.discovered_sessions.values() if s.is_active)
            total_size = sum(s.size_bytes for s in self.discovered_sessions.values())
            
            return {
                'total_sessions': len(self.discovered_sessions),
                'active_sessions': active_count,
                'total_projects': len(self.project_sessions),
                'total_size_mb': total_size / 1024 / 1024,
                'last_scan_time': self._last_scan_time,
                'scan_interval': self._scan_interval
            }
