"""
Performance monitoring and optimization for LoopGuard
"""

import time
import threading
import psutil
import gc
from pathlib import Path
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from collections import deque, defaultdict
from datetime import datetime, timezone, timedelta
import json
import weakref


@dataclass
class PerformanceMetrics:
    """Real-time performance metrics"""
    timestamp: float
    memory_mb: float
    cpu_percent: float
    disk_io_mb: float
    network_io_mb: float
    active_sessions: int
    watched_files: int
    alerts_per_minute: float
    gc_collections: int


@dataclass
class PerformanceAlert:
    """Performance alert when thresholds are exceeded"""
    alert_type: str  # 'memory', 'cpu', 'disk', 'network'
    severity: str  # 'low', 'medium', 'high'
    message: str
    current_value: float
    threshold_value: float
    timestamp: datetime
    suggested_action: str


class BoundedCache:
    """Memory-efficient bounded cache with automatic cleanup"""
    
    def __init__(self, max_size: int = 1000, cleanup_ratio: float = 0.8):
        self.max_size = max_size
        self.cleanup_ratio = cleanup_ratio
        self.cache = {}
        self.access_order = deque()
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[any]:
        with self._lock:
            if key in self.cache:
                # Move to end (most recently used)
                self.access_order.remove(key)
                self.access_order.append(key)
                return self.cache[key]
            return None
    
    def put(self, key: str, value: any):
        with self._lock:
            if key in self.cache:
                self.access_order.remove(key)
            elif len(self.cache) >= self.max_size:
                self._cleanup()
            
            self.cache[key] = value
            self.access_order.append(key)
    
    def remove(self, key: str):
        with self._lock:
            if key in self.cache:
                del self.cache[key]
                self.access_order.remove(key)
    
    def clear(self):
        with self._lock:
            self.cache.clear()
            self.access_order.clear()
    
    def _cleanup(self):
        """Remove least recently used items"""
        items_to_remove = int(self.max_size * (1 - self.cleanup_ratio))
        for _ in range(items_to_remove):
            if self.access_order:
                oldest_key = self.access_order.popleft()
                if oldest_key in self.cache:
                    del self.cache[oldest_key]
    
    def size(self) -> int:
        with self._lock:
            return len(self.cache)


class PerformanceMonitor:
    """Real-time performance monitoring with optimization"""
    
    def __init__(self, config: dict):
        self.config = config
        self.process = psutil.Process()
        self.monitoring_active = False
        self.metrics_history = deque(maxlen=1000)  # Last 1000 data points
        self.alerts_history = deque(maxlen=100)  # Last 100 alerts
        
        # Performance targets from Week 3 plan
        self.targets = {
            'max_memory_mb': config.get('memory_limit_mb', 40),
            'max_cpu_percent': config.get('cpu_limit_percent', 1.5),
            'max_disk_io_mb_per_sec': 10.0,
            'max_network_io_mb_per_sec': 5.0,
            'max_sessions': config.get('max_sessions', 50)
        }
        
        # Bounded caches for memory management
        self.session_cache = BoundedCache(max_size=500)
        self.event_cache = BoundedCache(max_size=2000)
        self.alert_cache = BoundedCache(max_size=100)
        
        # Performance optimization state
        self.optimization_level = 0  # 0=normal, 1=moderate, 2=aggressive
        self.last_gc_time = time.time()
        self.gc_interval = 300  # GC every 5 minutes
        
        # Monitoring thread
        self._monitor_thread = None
        self._stop_event = threading.Event()
        self._callbacks = defaultdict(list)
        
        # Performance counters
        self.counters = {
            'alerts_processed': 0,
            'sessions_processed': 0,
            'files_processed': 0,
            'gc_runs': 0,
            'optimizations_applied': 0
        }
    
    def start_monitoring(self):
        """Start performance monitoring in background thread"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self._stop_event.clear()
        
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        
        print("📊 Performance monitoring started")
        print(f"   Targets: <{self.targets['max_memory_mb']}MB memory, <{self.targets['max_cpu_percent']}% CPU")
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        self._stop_event.set()
        
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)
        
        print("📊 Performance monitoring stopped")
    
    def register_callback(self, event_type: str, callback: Callable):
        """Register callback for performance events"""
        self._callbacks[event_type].append(callback)
    
    def get_current_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics"""
        try:
            # Memory usage
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            # CPU usage
            cpu_percent = self.process.cpu_percent()
            
            # Disk I/O
            io_counters = self.process.io_counters()
            disk_io_mb = (io_counters.read_bytes + io_counters.write_bytes) / 1024 / 1024
            
            # Network I/O
            try:
                net_io = psutil.net_io_counters()
                network_io_mb = (net_io.bytes_sent + net_io.bytes_recv) / 1024 / 1024
            except (AttributeError, OSError):
                network_io_mb = 0
            
            return PerformanceMetrics(
                timestamp=time.time(),
                memory_mb=memory_mb,
                cpu_percent=cpu_percent,
                disk_io_mb=disk_io_mb,
                network_io_mb=network_io_mb,
                active_sessions=self.counters['sessions_processed'],
                watched_files=self.counters['files_processed'],
                alerts_per_minute=self._get_alerts_rate(),
                gc_collections=self.counters['gc_runs']
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return PerformanceMetrics(
                timestamp=time.time(),
                memory_mb=0, cpu_percent=0, disk_io_mb=0,
                network_io_mb=0, active_sessions=0,
                watched_files=0, alerts_per_minute=0, gc_collections=0
            )
    
    def get_performance_summary(self, minutes: int = 60) -> Dict:
        """Get performance summary for specified time period"""
        cutoff_time = time.time() - (minutes * 60)
        recent_metrics = [m for m in self.metrics_history if m.timestamp > cutoff_time]
        
        if not recent_metrics:
            return {'error': 'No recent metrics available'}
        
        # Calculate statistics
        memory_values = [m.memory_mb for m in recent_metrics]
        cpu_values = [m.cpu_percent for m in recent_metrics]
        
        return {
            'time_period_minutes': minutes,
            'sample_count': len(recent_metrics),
            'memory': {
                'current_mb': memory_values[-1] if memory_values else 0,
                'average_mb': sum(memory_values) / len(memory_values),
                'peak_mb': max(memory_values),
                'target_mb': self.targets['max_memory_mb'],
                'within_target': max(memory_values) <= self.targets['max_memory_mb']
            },
            'cpu': {
                'current_percent': cpu_values[-1] if cpu_values else 0,
                'average_percent': sum(cpu_values) / len(cpu_values),
                'peak_percent': max(cpu_values),
                'target_percent': self.targets['max_cpu_percent'],
                'within_target': max(cpu_values) <= self.targets['max_cpu_percent']
            },
            'caches': {
                'session_cache_size': self.session_cache.size(),
                'event_cache_size': self.event_cache.size(),
                'alert_cache_size': self.alert_cache.size()
            },
            'counters': dict(self.counters),
            'optimization_level': self.optimization_level
        }
    
    def optimize_memory(self, aggressive: bool = False):
        """Apply memory optimization techniques"""
        original_memory = self.get_current_metrics().memory_mb
        
        # Clear caches
        cleared_items = 0
        cleared_items += self.session_cache.size()
        self.session_cache.clear()
        
        cleared_items += self.event_cache.size()
        self.event_cache.clear()
        
        cleared_items += self.alert_cache.size()
        self.alert_cache.clear()
        
        # Force garbage collection
        gc.collect()
        self.counters['gc_runs'] += 1
        
        # Update optimization level
        if aggressive:
            self.optimization_level = 2
        elif original_memory > self.targets['max_memory_mb'] * 0.8:
            self.optimization_level = 1
        else:
            self.optimization_level = 0
        
        new_memory = self.get_current_metrics().memory_mb
        memory_freed = original_memory - new_memory
        
        self.counters['optimizations_applied'] += 1
        
        print(f"🧹 Memory optimization: freed {memory_freed:.1f}MB, cleared {cleared_items} cache items")
        
        # Trigger callbacks
        self._trigger_callbacks('memory_optimized', {
            'memory_freed_mb': memory_freed,
            'items_cleared': cleared_items,
            'optimization_level': self.optimization_level
        })
        
        return memory_freed
    
    def check_performance_alerts(self) -> List[PerformanceAlert]:
        """Check for performance threshold violations"""
        alerts = []
        current = self.get_current_metrics()
        
        # Memory alert
        if current.memory_mb > self.targets['max_memory_mb']:
            severity = 'high' if current.memory_mb > self.targets['max_memory_mb'] * 1.2 else 'medium'
            alerts.append(PerformanceAlert(
                alert_type='memory',
                severity=severity,
                message=f"Memory usage ({current.memory_mb:.1f}MB) exceeds target ({self.targets['max_memory_mb']}MB)",
                current_value=current.memory_mb,
                threshold_value=self.targets['max_memory_mb'],
                timestamp=datetime.now(timezone.utc),
                suggested_action="Consider reducing session limits or enabling aggressive optimization"
            ))
        
        # CPU alert
        if current.cpu_percent > self.targets['max_cpu_percent']:
            severity = 'high' if current.cpu_percent > self.targets['max_cpu_percent'] * 1.5 else 'medium'
            alerts.append(PerformanceAlert(
                alert_type='cpu',
                severity=severity,
                message=f"CPU usage ({current.cpu_percent:.1f}%) exceeds target ({self.targets['max_cpu_percent']}%)",
                current_value=current.cpu_percent,
                threshold_value=self.targets['max_cpu_percent'],
                timestamp=datetime.now(timezone.utc),
                suggested_action="Check for infinite loops or reduce monitoring frequency"
            ))
        
        # Session limit alert
        if current.active_sessions > self.targets['max_sessions']:
            alerts.append(PerformanceAlert(
                alert_type='sessions',
                severity='medium',
                message=f"Active sessions ({current.active_sessions}) exceed limit ({self.targets['max_sessions']})",
                current_value=current.active_sessions,
                threshold_value=self.targets['max_sessions'],
                timestamp=datetime.now(timezone.utc),
                suggested_action="Enable session prioritization or increase limits"
            ))
        
        # Store alerts
        for alert in alerts:
            self.alerts_history.append(alert)
            self._trigger_callbacks('performance_alert', alert)
        
        return alerts
    
    def update_counters(self, **kwargs):
        """Update performance counters"""
        for key, value in kwargs.items():
            if key in self.counters:
                self.counters[key] += value
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        return {
            'session_cache': {
                'size': self.session_cache.size(),
                'max_size': self.session_cache.max_size,
                'utilization': self.session_cache.size() / self.session_cache.max_size
            },
            'event_cache': {
                'size': self.event_cache.size(),
                'max_size': self.event_cache.max_size,
                'utilization': self.event_cache.size() / self.event_cache.max_size
            },
            'alert_cache': {
                'size': self.alert_cache.size(),
                'max_size': self.alert_cache.max_size,
                'utilization': self.alert_cache.size() / self.alert_cache.max_size
            }
        }
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        last_io_check = time.time()
        last_disk_io = 0
        last_network_io = 0
        
        while not self._stop_event.is_set():
            try:
                # Get current metrics
                metrics = self.get_current_metrics()
                self.metrics_history.append(metrics)
                
                # Check for performance alerts
                alerts = self.check_performance_alerts()
                
                # Periodic memory optimization
                current_time = time.time()
                if current_time - self.last_gc_time > self.gc_interval:
                    if metrics.memory_mb > self.targets['max_memory_mb'] * 0.8:
                        self.optimize_memory(aggressive=(metrics.memory_mb > self.targets['max_memory_mb']))
                    self.last_gc_time = current_time
                
                # Trigger periodic callbacks
                self._trigger_callbacks('metrics_update', metrics)
                
                # Sleep for monitoring interval
                self._stop_event.wait(5.0)  # Monitor every 5 seconds
                
            except Exception as e:
                print(f"⚠️  Performance monitoring error: {e}")
                self._stop_event.wait(10.0)  # Wait longer on error
    
    def _get_alerts_rate(self) -> float:
        """Calculate alerts per minute rate"""
        if not self.alerts_history:
            return 0.0
        
        one_minute_ago = time.time() - 60
        recent_alerts = [a for a in self.alerts_history 
                        if a.timestamp.timestamp() > one_minute_ago]
        return len(recent_alerts)
    
    def _trigger_callbacks(self, event_type: str, data: any):
        """Trigger registered callbacks for event type"""
        for callback in self._callbacks.get(event_type, []):
            try:
                callback(data)
            except Exception as e:
                print(f"⚠️  Callback error for {event_type}: {e}")
    
    def export_performance_data(self, file_path: str, hours: int = 24):
        """Export performance data to JSON file"""
        cutoff_time = time.time() - (hours * 3600)
        recent_metrics = [m for m in self.metrics_history if m.timestamp > cutoff_time]
        
        data = {
            'export_time': datetime.now(timezone.utc).isoformat(),
            'time_period_hours': hours,
            'metrics': [
                {
                    'timestamp': m.timestamp,
                    'memory_mb': m.memory_mb,
                    'cpu_percent': m.cpu_percent,
                    'disk_io_mb': m.disk_io_mb,
                    'network_io_mb': m.network_io_mb,
                    'active_sessions': m.active_sessions,
                    'watched_files': m.watched_files,
                    'alerts_per_minute': m.alerts_per_minute
                }
                for m in recent_metrics
            ],
            'summary': self.get_performance_summary(hours * 60),
            'targets': self.targets,
            'counters': dict(self.counters)
        }
        
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"📊 Performance data exported to {file_path}")
        except Exception as e:
            print(f"❌ Error exporting performance data: {e}")
