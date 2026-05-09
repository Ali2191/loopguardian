"""
Session analytics and efficiency scoring for LoopGuard
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import statistics
from enum import Enum

from .log_parser import LogEvent
from .types import LoopAlert


class SessionState(Enum):
    """Session lifecycle states"""
    STARTING = "starting"
    ACTIVE = "active"
    IDLE = "idle"
    ENDING = "ending"
    COMPLETED = "completed"


class EfficiencyLevel(Enum):
    """Session efficiency levels"""
    EXCELLENT = "excellent"  # 90-100
    GOOD = "good"           # 75-89
    FAIR = "fair"           # 60-74
    POOR = "poor"           # 40-59
    CRITICAL = "critical"    # 0-39


@dataclass
class SessionMetrics:
    """Metrics for a Claude Code session"""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime]
    total_events: int
    tool_calls: int
    file_operations: int
    loops_detected: int
    efficiency_score: float
    estimated_tokens_used: int
    duration_minutes: Optional[int] = None
    session_state: SessionState = SessionState.ACTIVE
    efficiency_level: Optional[EfficiencyLevel] = None
    productive_turns: int = 0
    loop_turns: int = 0
    unique_files_modified: int = 0
    error_count: int = 0
    stagnation_periods: int = 0
    progress_indicators: List[str] = None
    
    def __post_init__(self):
        if self.progress_indicators is None:
            self.progress_indicators = []
        if self.efficiency_score is not None:
            self.efficiency_level = self._calculate_efficiency_level()
    
    def _calculate_efficiency_level(self) -> EfficiencyLevel:
        """Calculate efficiency level based on score"""
        if self.efficiency_score >= 90:
            return EfficiencyLevel.EXCELLENT
        elif self.efficiency_score >= 75:
            return EfficiencyLevel.GOOD
        elif self.efficiency_score >= 60:
            return EfficiencyLevel.FAIR
        elif self.efficiency_score >= 40:
            return EfficiencyLevel.POOR
        else:
            return EfficiencyLevel.CRITICAL


@dataclass
class SessionSummary:
    """End-of-session summary report"""
    session_id: str
    duration_minutes: int
    efficiency_score: float
    efficiency_level: EfficiencyLevel
    total_events: int
    productive_turns: int
    loop_turns: int
    estimated_tokens_used: int
    unique_files_modified: int
    loops_detected: int
    key_insights: List[str]
    recommendations: List[str]
    progress_made: str
    time_wasted_estimate: int  # minutes wasted in loops
    cost_savings: float  # estimated cost savings from loop prevention


class SessionAnalytics:
    """Tracks and analyzes session efficiency"""
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            self.db_path = Path.home() / ".loopguard" / "sessions.db"
        else:
            self.db_path = Path(db_path)
        
        self.config = None  # Will be set by LoopGuardService
        self._init_database()
    
    def set_config(self, config):
        """Set configuration for analytics"""
        self.config = config
    
    def _init_database(self):
        """Initialize SQLite database for session analytics with enhanced schema"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            # Enhanced sessions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    start_time TEXT,
                    end_time TEXT,
                    total_events INTEGER,
                    tool_calls INTEGER,
                    file_operations INTEGER,
                    loops_detected INTEGER,
                    efficiency_score REAL,
                    estimated_tokens_used INTEGER,
                    duration_minutes INTEGER,
                    session_state TEXT,
                    efficiency_level TEXT,
                    productive_turns INTEGER,
                    loop_turns INTEGER,
                    unique_files_modified INTEGER,
                    error_count INTEGER,
                    stagnation_periods INTEGER,
                    progress_indicators TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Enhanced alerts table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    alert_type TEXT,
                    severity TEXT,
                    description TEXT,
                    suggested_action TEXT,
                    evidence TEXT,
                    timestamp TEXT,
                    action_taken TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # New session summaries table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS session_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE,
                    summary_data TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # File activity tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_activity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    file_path TEXT,
                    operation_type TEXT,
                    timestamp TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
    
    def start_session(self, session_id: str):
        """Start tracking a new session with enhanced metrics"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO sessions 
                (session_id, start_time, total_events, tool_calls, file_operations, loops_detected, 
                 efficiency_score, session_state, productive_turns, loop_turns, unique_files_modified,
                 error_count, stagnation_periods, progress_indicators)
                VALUES (?, ?, 0, 0, 0, 0, 100.0, ?, 0, 0, 0, 0, 0, ?)
            """, (
                session_id, 
                datetime.now().isoformat(),
                SessionState.ACTIVE.value,
                json.dumps([])
            ))
            conn.commit()
    
    def track_file_activity(self, session_id: str, file_path: str, operation_type: str):
        """Track file activity for a session"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO file_activity (session_id, file_path, operation_type, timestamp)
                VALUES (?, ?, ?, ?)
            """, (
                session_id,
                file_path,
                operation_type,
                datetime.now().isoformat()
            ))
            conn.commit()
    
    def update_session_state(self, session_id: str, state: SessionState):
        """Update session state"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE sessions SET session_state = ? WHERE session_id = ?
            """, (state.value, session_id))
            conn.commit()
    
    def update_session(self, session_id: str, events: List[LogEvent], alerts: List[LoopAlert]):
        """Update session metrics with enhanced efficiency calculation"""
        if not events:
            return
        
        # Calculate enhanced metrics
        total_events = len(events)
        tool_calls = self._count_tool_calls(events)
        file_operations = self._count_file_operations(events)
        loops_detected = len(alerts)
        
        # Enhanced efficiency calculation
        productive_turns = self._count_productive_turns(events)
        loop_turns = self._count_loop_turns(events, alerts)
        unique_files_modified = self._count_unique_files(events, session_id)
        error_count = self._count_errors(events)
        stagnation_periods = self._count_stagnation_periods(alerts)
        progress_indicators = self._identify_progress_indicators(events)
        
        # Calculate efficiency score with enhanced algorithm
        efficiency_score = self._calculate_enhanced_efficiency_score(
            total_events, tool_calls, file_operations, loops_detected,
            productive_turns, loop_turns, unique_files_modified, error_count
        )
        
        # Estimate token usage with better accuracy
        estimated_tokens = self._estimate_enhanced_token_usage(events)
        
        # Calculate duration
        start_time = datetime.fromisoformat(events[0].timestamp.replace('Z', '+00:00'))
        end_time = datetime.now()
        duration_minutes = int((end_time - start_time).total_seconds() / 60)
        
        # Update database with enhanced metrics
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE sessions SET
                    end_time = ?, total_events = ?, tool_calls = ?, 
                    file_operations = ?, loops_detected = ?, efficiency_score = ?,
                    estimated_tokens_used = ?, duration_minutes = ?, session_state = ?,
                    productive_turns = ?, loop_turns = ?, unique_files_modified = ?,
                    error_count = ?, stagnation_periods = ?, progress_indicators = ?
                WHERE session_id = ?
            """, (
                end_time.isoformat(),
                total_events,
                tool_calls,
                file_operations,
                loops_detected,
                efficiency_score,
                estimated_tokens,
                duration_minutes,
                SessionState.ACTIVE.value,
                productive_turns,
                loop_turns,
                unique_files_modified,
                error_count,
                stagnation_periods,
                json.dumps(progress_indicators),
                session_id
            ))
            conn.commit()
        
        # Store alerts with action tracking
        for alert in alerts:
            self._store_alert(alert)
        
        # Track file activity
        self._track_file_activities(session_id, events)
    
    def _count_productive_turns(self, events: List[LogEvent]) -> int:
        """Count productive turns (those that result in file changes or progress)"""
        productive_turns = 0
        for event in events:
            if event.event_type == 'assistant':
                content = str(event.content)
                # Check for productive operations
                if any(op in content.lower() for op in 
                       ['str_replace', 'write_to_file', 'edit', 'create_file', 'multi_edit']):
                    productive_turns += 1
        return productive_turns
    
    def _count_loop_turns(self, events: List[LogEvent], alerts: List[LoopAlert]) -> int:
        """Count turns that are part of detected loops"""
        loop_turns = 0
        for alert in alerts:
            if alert.alert_type in ['tool_call_loop', 'error_loop']:
                loop_turns += alert.evidence.get('count', 0)
        return loop_turns
    
    def _count_unique_files(self, events: List[LogEvent], session_id: str) -> int:
        """Count unique files modified in this session"""
        unique_files = set()
        for event in events:
            if event.event_type == 'assistant':
                content = str(event.content)
                # Extract file paths from content
                if 'file_path' in content.lower():
                    # Simple extraction - in real implementation would be more sophisticated
                    lines = content.split('\n')
                    for line in lines:
                        if 'file_path' in line.lower() and ':' in line:
                            try:
                                file_path = line.split(':')[1].strip().strip('"\'')
                                unique_files.add(file_path)
                            except:
                                pass
        
        return len(unique_files)
    
    def _count_errors(self, events: List[LogEvent]) -> int:
        """Count error messages in events"""
        error_count = 0
        for event in events:
            if event.event_type == 'assistant':
                content = str(event.content)
                if any(error in content.lower() for error in 
                       ['error', 'failed', 'exception', 'traceback']):
                    error_count += 1
        return error_count
    
    def _count_stagnation_periods(self, alerts: List[LoopAlert]) -> int:
        """Count stagnation alerts"""
        return sum(1 for alert in alerts if alert.alert_type == 'stagnation')
    
    def _identify_progress_indicators(self, events: List[LogEvent]) -> List[str]:
        """Identify indicators of progress in the session"""
        indicators = []
        for event in events:
            if event.event_type == 'assistant':
                content = str(event.content)
                if 'test' in content.lower() and 'pass' in content.lower():
                    indicators.append('Tests passing')
                elif 'build' in content.lower() and 'success' in content.lower():
                    indicators.append('Build successful')
                elif 'deploy' in content.lower():
                    indicators.append('Deployment activity')
                elif 'commit' in content.lower():
                    indicators.append('Git commit made')
        return list(set(indicators))  # Remove duplicates
    
    def _track_file_activities(self, session_id: str, events: List[LogEvent]):
        """Track individual file activities for detailed analysis"""
        for event in events:
            if event.event_type == 'assistant':
                content = str(event.content)
                # Detect file operations
                if 'str_replace' in content.lower():
                    file_path = self._extract_file_path_from_content(content)
                    if file_path:
                        self.track_file_activity(session_id, file_path, 'edit')
                elif 'write_to_file' in content.lower() or 'create_file' in content.lower():
                    file_path = self._extract_file_path_from_content(content)
                    if file_path:
                        self.track_file_activity(session_id, file_path, 'create')
                elif 'read_file' in content.lower():
                    file_path = self._extract_file_path_from_content(content)
                    if file_path:
                        self.track_file_activity(session_id, file_path, 'read')
    
    def _extract_file_path_from_content(self, content: str) -> Optional[str]:
        """Extract file path from content"""
        lines = content.split('\n')
        for line in lines:
            if 'file_path' in line.lower() and ':' in line:
                try:
                    file_path = line.split(':')[1].strip().strip('"\'')
                    if file_path and file_path != 'unknown':
                        return file_path
                except:
                    pass
        return None
    
    def _count_tool_calls(self, events: List[LogEvent]) -> int:
        """Count tool usage events"""
        tool_calls = 0
        for event in events:
            if event.event_type == 'assistant':
                content = event.content
                if isinstance(content, dict):
                    content_list = content.get('content', [])
                    if isinstance(content_list, list):
                        tool_calls += sum(1 for item in content_list 
                                           if isinstance(item, dict) and 
                                           item.get('type') == 'tool_use')
        return tool_calls
    
    def _count_file_operations(self, events: List[LogEvent]) -> int:
        """Count file modification operations"""
        file_ops = 0
        for event in events:
            if event.event_type == 'assistant':
                content = str(event.content)
                if any(op in content.lower() for op in 
                       ['str_replace', 'write_to_file', 'edit', 'read_file']):
                    file_ops += 1
        return file_ops
    
    def _calculate_enhanced_efficiency_score(self, total_events: int, tool_calls: int, 
                                        file_ops: int, loops: int, productive_turns: int,
                                        loop_turns: int, unique_files: int, errors: int) -> float:
        """Calculate enhanced session efficiency score (0-100)"""
        if total_events == 0:
            return 100.0
        
        # Base productivity score (40% weight)
        productivity_score = min(40, (productive_turns / max(1, total_events)) * 40)
        
        # Tool usage effectiveness (20% weight)
        tool_effectiveness = min(20, (tool_calls / max(1, total_events)) * 20)
        
        # File operations score (15% weight)
        file_score = min(15, (file_ops / max(1, total_events)) * 15)
        
        # Unique files diversity (10% weight)
        diversity_score = min(10, unique_files * 2)
        
        # Penalties
        loop_penalty = min(30, (loop_turns / max(1, total_events)) * 30)
        error_penalty = min(15, (errors / max(1, total_events)) * 15)
        
        # Calculate final score
        raw_score = (productivity_score + tool_effectiveness + file_score + 
                    diversity_score - loop_penalty - error_penalty)
        
        return max(0, min(100, raw_score))
    
    def _estimate_enhanced_token_usage(self, events: List[LogEvent]) -> int:
        """Enhanced token usage estimation"""
        total_tokens = 0
        
        for event in events:
            if event.event_type == 'assistant':
                content_str = str(event.content)
                # More accurate token estimation
                total_tokens += len(content_str) // 4  # ~1 token per 4 characters
                
                # Add tokens for tool calls (more accurate)
                if 'tool_use' in content_str:
                    # Count actual tool calls
                    tool_call_count = content_str.count('tool_use')
                    total_tokens += tool_call_count * 75  # More realistic estimate
                
                # Add tokens for file operations
                if any(op in content_str.lower() for op in 
                       ['str_replace', 'write_to_file', 'edit']):
                    total_tokens += 25  # File operation overhead
        
        return total_tokens
    
    def _calculate_efficiency_score(self, tool_calls: int, file_ops: int, 
                               loops: int, total_events: int) -> float:
        """Calculate session efficiency score (0-100)"""
        if total_events == 0:
            return 100.0
        
        # Base score on productive work
        productive_score = min(100, (tool_calls + file_ops) * 10)
        
        # Penalty for loops
        loop_penalty = loops * 20
        
        # Penalty for low activity
        activity_penalty = max(0, (total_events - tool_calls - file_ops) * 5)
        
        raw_score = productive_score - loop_penalty - activity_penalty
        return max(0, min(100, raw_score))
    
    def generate_session_summary(self, session_id: str) -> Optional[SessionSummary]:
        """Generate end-of-session summary report"""
        metrics = self.get_session_metrics(session_id)
        if not metrics:
            return None
        
        # Calculate time wasted in loops
        time_wasted = self._estimate_time_wasted(metrics)
        
        # Calculate cost savings
        cost_savings = self._calculate_cost_savings(metrics)
        
        # Generate insights
        key_insights = self._generate_key_insights(metrics)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(metrics)
        
        # Summarize progress
        progress_made = self._summarize_progress(metrics)
        
        return SessionSummary(
            session_id=session_id,
            duration_minutes=metrics.duration_minutes or 0,
            efficiency_score=metrics.efficiency_score,
            efficiency_level=metrics.efficiency_level or EfficiencyLevel.FAIR,
            total_events=metrics.total_events,
            productive_turns=metrics.productive_turns,
            loop_turns=metrics.loop_turns,
            estimated_tokens_used=metrics.estimated_tokens_used,
            unique_files_modified=metrics.unique_files_modified,
            loops_detected=metrics.loops_detected,
            key_insights=key_insights,
            recommendations=recommendations,
            progress_made=progress_made,
            time_wasted_estimate=time_wasted,
            cost_savings=cost_savings
        )
    
    def _estimate_time_wasted(self, metrics: SessionMetrics) -> int:
        """Estimate minutes wasted in loops"""
        if metrics.duration_minutes == 0:
            return 0
        
        # Estimate that loop turns consume 2x more time than productive turns
        loop_ratio = metrics.loop_turns / max(1, metrics.total_events)
        estimated_wasted_minutes = int(metrics.duration_minutes * loop_ratio * 0.5)
        return min(estimated_wasted_minutes, metrics.duration_minutes)
    
    def _calculate_cost_savings(self, metrics: SessionMetrics) -> float:
        """Calculate estimated cost savings from loop prevention"""
        # Rough estimate: $0.01 per 1K tokens, loops waste 50% more tokens
        wasted_tokens = metrics.estimated_tokens_used * (metrics.loop_turns / max(1, metrics.total_events)) * 0.5
        return round(wasted_tokens * 0.01 / 1000, 2)
    
    def _generate_key_insights(self, metrics: SessionMetrics) -> List[str]:
        """Generate key insights from session metrics"""
        insights = []
        
        if metrics.efficiency_score >= 90:
            insights.append("Excellent session efficiency - highly productive work")
        elif metrics.efficiency_score >= 75:
            insights.append("Good session efficiency with solid progress")
        elif metrics.efficiency_score < 50:
            insights.append("Low efficiency - significant optimization opportunities")
        
        if metrics.loops_detected > 0:
            insights.append(f"{metrics.loops_detected} loop(s) detected and prevented")
        
        if metrics.unique_files_modified > 10:
            insights.append(f"High file diversity - worked on {metrics.unique_files_modified} files")
        
        if metrics.productive_turns > metrics.loop_turns * 3:
            insights.append("Strong productive vs. loop turn ratio")
        
        return insights
    
    def _generate_recommendations(self, metrics: SessionMetrics) -> List[str]:
        """Generate recommendations based on session metrics"""
        recommendations = []
        
        if metrics.loops_detected > 2:
            recommendations.append("Consider breaking down complex tasks into smaller steps")
        
        if metrics.error_count > metrics.total_events * 0.2:
            recommendations.append("Review error patterns - consider validation steps")
        
        if metrics.stagnation_periods > 1:
            recommendations.append("Take breaks during long sessions to maintain focus")
        
        if metrics.efficiency_score < 60:
            recommendations.append("Consider using more specific prompts and file targeting")
        
        return recommendations
    
    def _summarize_progress(self, metrics: SessionMetrics) -> str:
        """Summarize progress made in the session"""
        if metrics.efficiency_score >= 80:
            return "Significant progress made with high efficiency"
        elif metrics.efficiency_score >= 60:
            return "Good progress with room for optimization"
        elif metrics.productive_turns > metrics.loop_turns:
            return "Moderate progress - more productive than loop activity"
        else:
            return "Limited progress due to repeated patterns"
    
    def save_session_summary(self, summary: SessionSummary):
        """Save session summary to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO session_summaries (session_id, summary_data)
                VALUES (?, ?)
            """, (
                summary.session_id,
                json.dumps(asdict(summary), default=str)
            ))
            conn.commit()
    
    def _store_alert(self, alert: LoopAlert):
        """Store alert in database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO alerts 
                (session_id, alert_type, severity, description, suggested_action, evidence, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                alert.session_id,
                alert.alert_type,
                alert.severity,
                alert.description,
                alert.suggested_action,
                json.dumps(alert.evidence),
                alert.timestamp.isoformat()
            ))
            conn.commit()
    
    def get_session_metrics(self, session_id: str) -> Optional[SessionMetrics]:
        """Get metrics for a specific session"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("""
                SELECT * FROM sessions WHERE session_id = ?
            """, (session_id,)).fetchone()
            
            if row:
                return SessionMetrics(
                    session_id=row['session_id'],
                    start_time=datetime.fromisoformat(row['start_time']),
                    end_time=datetime.fromisoformat(row['end_time']) if row['end_time'] else None,
                    total_events=row['total_events'],
                    tool_calls=row['tool_calls'],
                    file_operations=row['file_operations'],
                    loops_detected=row['loops_detected'],
                    efficiency_score=row['efficiency_score'],
                    estimated_tokens_used=row['estimated_tokens_used'],
                    duration_minutes=row['duration_minutes']
                )
        
        return None
    
    def get_recent_sessions(self, limit: int = 10) -> List[SessionMetrics]:
        """Get recent sessions with their metrics"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM sessions 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (limit,)).fetchall()
            
            return [SessionMetrics(
                session_id=row['session_id'],
                start_time=datetime.fromisoformat(row['start_time']),
                end_time=datetime.fromisoformat(row['end_time']) if row['end_time'] else None,
                total_events=row['total_events'],
                tool_calls=row['tool_calls'],
                file_operations=row['file_operations'],
                loops_detected=row['loops_detected'],
                efficiency_score=row['efficiency_score'],
                estimated_tokens_used=row['estimated_tokens_used'],
                duration_minutes=row['duration_minutes']
            ) for row in rows]
    
    def get_efficiency_summary(self, days: int = 7) -> Dict:
        """Get efficiency summary for recent days"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Get recent sessions
            cutoff_date = datetime.now() - timedelta(days=days)
            rows = conn.execute("""
                SELECT AVG(efficiency_score) as avg_efficiency,
                       SUM(loops_detected) as total_loops,
                       COUNT(*) as session_count,
                       AVG(estimated_tokens_used) as avg_tokens
                FROM sessions 
                WHERE created_at > ?
            """, (cutoff_date.isoformat(),)).fetchone()
            
            return {
                'avg_efficiency_score': rows['avg_efficiency'] or 0,
                'total_loops_detected': rows['total_loops'] or 0,
                'session_count': rows['session_count'] or 0,
                'avg_tokens_per_session': rows['avg_tokens'] or 0,
                'period_days': days
            }
