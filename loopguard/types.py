"""
Shared types and dataclasses for LoopGuard
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class LoopAlert:
    """Represents a detected loop"""
    alert_type: str  # 'tool_call_loop', 'error_loop', 'stagnation'
    session_id: str
    timestamp: datetime
    description: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    suggested_action: str
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary"""
        return {
            'alert_type': self.alert_type,
            'session_id': self.session_id,
            'timestamp': self.timestamp.isoformat(),
            'description': self.description,
            'severity': self.severity,
            'suggested_action': self.suggested_action,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LoopAlert':
        """Create alert from dictionary"""
        return cls(
            alert_type=data['alert_type'],
            session_id=data['session_id'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            description=data['description'],
            severity=data['severity'],
            suggested_action=data['suggested_action'],
            metadata=data['metadata']
        )


@dataclass
class Alert:
    """Represents a detected loop (alias for LoopAlert)"""
    alert_type: str
    session_id: str
    description: str
    severity: str
    suggested_action: str
