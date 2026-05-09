"""
Process monitoring for Claude Code detection
"""

import psutil
import time
import threading
from typing import Optional, Set, Dict, List, Any
from dataclasses import dataclass, field
from collections import defaultdict
import os
from pathlib import Path


@dataclass
class ClaudeSession:
    """Represents a detected Claude Code session"""
    pid: int
    cmdline: list
    start_time: float
    project_path: Optional[str] = None
    session_id: Optional[str] = None
    resource_usage: Dict[str, float] = field(default_factory=dict)
    priority: int = 1  # 1=normal, 2=high, 0=low
    last_activity: float = field(default_factory=time.time)


class ProcessMonitor:
    """Enhanced multi-process Claude Code monitor with resource management"""
    
    def __init__(self, max_sessions: int = 10):
        self._claude_processes: Set[int] = set()
        self._sessions: Dict[int, ClaudeSession] = {}
        self._session_priorities: Dict[str, int] = defaultdict(lambda: 1)
        self._resource_limits = {
            'max_memory_mb': 100,
            'max_cpu_percent': 5.0
        }
        self._max_sessions = max_sessions
        self._lock = threading.RLock()
        self._monitoring_active = False
    
    def detect_claude_processes(self) -> List[ClaudeSession]:
        """Detect running Claude Code processes with enhanced multi-process support"""
        with self._lock:
            current_pids = set()
            new_sessions = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time', 'memory_info', 'cpu_percent']):
                try:
                    proc_info = proc.info
                    cmdline = proc_info.get('cmdline', [])
                    
                    if self._is_claude_process(cmdline):
                        pid = proc_info['pid']
                        current_pids.add(pid)
                        
                        if pid not in self._claude_processes:
                            # New Claude Code process detected
                            session = ClaudeSession(
                                pid=pid,
                                cmdline=cmdline,
                                start_time=proc_info['create_time'],
                                session_id=self._generate_session_id(pid, cmdline),
                                resource_usage=self._get_resource_usage(proc),
                                priority=self._calculate_session_priority(cmdline)
                            )
                            self._sessions[pid] = session
                            new_sessions.append(session)
                            
                            # Apply resource management if too many sessions
                            if len(self._sessions) > self._max_sessions:
                                self._apply_session_prioritization()
                        else:
                            # Update resource usage for existing session
                            if pid in self._sessions:
                                self._sessions[pid].resource_usage = self._get_resource_usage(proc)
                                self._sessions[pid].last_activity = time.time()
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Clean up terminated processes
            terminated_pids = self._claude_processes - current_pids
            for pid in terminated_pids:
                if pid in self._sessions:
                    del self._sessions[pid]
            
            self._claude_processes = current_pids
            return new_sessions
    
    def _is_claude_process(self, cmdline: list) -> bool:
        """Check if process is Claude Code"""
        if not cmdline:
            return False
        
        cmdline_str = ' '.join(cmdline).lower()
        
        # Check for common Claude Code patterns
        claude_patterns = [
            'claude',
            'claude-code',
            '/usr/local/bin/claude',
            'node.*claude'  # Node-based Claude Code
        ]
        
        for pattern in claude_patterns:
            if pattern in cmdline_str:
                # Exclude false positives like claude-api libraries
                if 'node_modules' not in cmdline_str and 'pip' not in cmdline_str:
                    return True
        
        return False
    
    def get_active_sessions(self) -> List[ClaudeSession]:
        """Get all active Claude Code sessions sorted by priority"""
        with self._lock:
            sessions = list(self._sessions.values())
            return sorted(sessions, key=lambda s: s.priority, reverse=True)
    
    def is_session_active(self, pid: int) -> bool:
        """Check if a specific session is still active"""
        with self._lock:
            return pid in self._claude_processes
    
    def get_session_by_id(self, session_id: str) -> Optional[ClaudeSession]:
        """Get session by session ID"""
        with self._lock:
            for session in self._sessions.values():
                if session.session_id == session_id:
                    return session
        return None
    
    def get_high_priority_sessions(self) -> List[ClaudeSession]:
        """Get high priority sessions for resource allocation"""
        with self._lock:
            return [s for s in self._sessions.values() if s.priority >= 2]
    
    def update_session_priority(self, session_id: str, priority: int) -> None:
        """Update session priority for resource management"""
        with self._lock:
            for session in self._sessions.values():
                if session.session_id == session_id:
                    session.priority = priority
                    break
    
    def get_resource_usage_summary(self) -> Dict[str, float]:
        """Get total resource usage across all sessions"""
        with self._lock:
            total_memory = sum(s.resource_usage.get('memory_mb', 0) for s in self._sessions.values())
            total_cpu = sum(s.resource_usage.get('cpu_percent', 0) for s in self._sessions.values())
            return {
                'total_memory_mb': total_memory,
                'total_cpu_percent': total_cpu,
                'session_count': len(self._sessions),
                'avg_memory_per_session': total_memory / max(1, len(self._sessions))
            }
    
    def _generate_session_id(self, pid: int, cmdline: list) -> str:
        """Generate unique session ID from PID and command line"""
        import hashlib
        cmd_str = ' '.join(cmdline)
        return hashlib.md5(f"{pid}{cmd_str}".encode()).hexdigest()[:12]
    
    def _get_resource_usage(self, proc: Any) -> Dict[str, float]:
        """Get resource usage for a process"""
        try:
            memory_info = proc.memory_info()
            return {
                'memory_mb': memory_info.rss / 1024 / 1024,
                'cpu_percent': proc.cpu_percent(),
                'num_threads': proc.num_threads()
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return {'memory_mb': 0, 'cpu_percent': 0, 'num_threads': 0}
    
    def _calculate_session_priority(self, cmdline: list) -> int:
        """Calculate session priority based on command line characteristics"""
        cmd_str = ' '.join(cmdline).lower()
        
        # Higher priority for interactive sessions
        if 'interactive' in cmd_str or 'tty' in cmd_str:
            return 2
        
        # Lower priority for background/automated sessions
        if 'background' in cmd_str or 'batch' in cmd_str:
            return 0
        
        return 1  # Normal priority
    
    def _apply_session_prioritization(self) -> None:
        """Apply resource management when too many sessions"""
        sessions = sorted(self._sessions.values(), key=lambda s: s.priority)
        
        # Mark lower priority sessions for reduced monitoring
        for i, session in enumerate(sessions):
            if i < len(sessions) - self._max_sessions:
                session.priority = 0  # Low priority - minimal monitoring
