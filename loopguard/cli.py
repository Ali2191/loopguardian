"""
Command-line interface for LoopGuard
"""

import sys
import signal
import time
import threading
from pathlib import Path

import click

from .config import Config
from .process_monitor import ProcessMonitor
from .file_watcher import FileWatcher
from .loop_detector import LoopDetector
from .notifications import NotificationService
from .session_analytics import SessionAnalytics
from .error_handler import ErrorHandler, LoopGuardError, ErrorCategory, ErrorSeverity
from .session_discovery import SessionDiscovery
from .performance_monitor import PerformanceMonitor


class LoopGuardService:
    """Enhanced LoopGuard service with Week 3 features"""
    
    def __init__(self, config_path: str = None, interactive_setup: bool = False):
        self.config = Config(config_path, interactive_setup=interactive_setup)
        self.process_monitor = ProcessMonitor(
            max_sessions=self.config.get('performance.max_sessions', 50)
        )
        self.loop_detector = LoopDetector(self.config)
        self.notification_service = NotificationService(
            self.config.get('notifications.enabled', True),
            config=self.config
        )
        self.file_watcher = FileWatcher(self.loop_detector, self._on_alert)
        self.session_analytics = SessionAnalytics()
        self.session_analytics.set_config(self.config)
        self.error_handler = ErrorHandler(self.notification_service)
        
        # Week 3 enhancements
        self.session_discovery = SessionDiscovery()
        self.performance_monitor = PerformanceMonitor(
            self.config.get('performance', {})
        )
        
        self.running = False
        self.monitor_thread = None
        self._last_discovery_update = 0
    
    def _on_alert(self, alert):
        """Handle loop detection alerts with error handling"""
        try:
            print(f"\n🚨 LOOP DETECTED: {alert.description}")
            print(f"   Session: {alert.session_id[:12]}...")
            print(f"   Severity: {alert.severity}")
            print(f"   Suggested: {alert.suggested_action}")
            
            # Store alert and update session analytics
            self.session_analytics._store_alert(alert)
            
            # Send desktop notification
            if self.notification_service.is_available():
                self.notification_service.send_alert(alert)
                
        except Exception as e:
            # Handle alert processing errors
            self.error_handler.handle_error(e, {
                'operation': 'alert_processing',
                'alert_type': alert.alert_type if hasattr(alert, 'alert_type') else 'unknown',
                'session_id': alert.session_id
            })
    
    def start(self):
        """Start enhanced LoopGuard service with Week 3 features"""
        try:
            print("🔍 Starting LoopGuard with enhanced features...")
            
            # Start performance monitoring
            self.performance_monitor.start_monitoring()
            
            # Check notification service with error handling
            try:
                if not self.notification_service.is_available():
                    print("⚠️  Desktop notifications not available")
                    print("   Install terminal-notifier: brew install terminal-notifier")
            except Exception as e:
                self.error_handler.handle_error(e, {
                    'operation': 'notification_check',
                    'component': 'notification_service'
                })
                print("⚠️  Notification check failed - continuing without notifications")
            
            # Start file watcher with enhanced discovery
            try:
                if not self.file_watcher.start_watching():
                    raise LoopGuardError(
                        "Failed to start file watching",
                        ErrorCategory.FILE_SYSTEM,
                        ErrorSeverity.HIGH
                    )
                print("✅ Enhanced file watching started successfully")
            except Exception as e:
                handled = self.error_handler.handle_error(e, {
                    'operation': 'start_file_watching',
                    'component': 'file_watcher'
                })
                if not handled:
                    print("❌ Failed to start file watching")
                    return False
                print("⚠️  File watching started with fallback mode")
            
            print("✅ LoopGuard is monitoring Claude Code sessions with enhanced features")
            print(f"   Config: {self.config.config_path}")
            print(f"   Notifications: {'enabled' if self.notification_service.is_available() else 'disabled'}")
            print(f"   Adaptive detection: {'enabled' if self.config.get('detection.adaptive_mode', True) else 'disabled'}")
            
            self.running = True
            
            # Start enhanced process monitoring in separate thread
            try:
                self.monitor_thread = threading.Thread(target=self._enhanced_monitor_loop, daemon=True)
                self.monitor_thread.start()
                print("✅ Enhanced process monitoring started")
            except Exception as e:
                self.error_handler.handle_error(e, {
                    'operation': 'start_process_monitoring',
                    'component': 'process_monitor'
                })
                print("⚠️  Process monitoring failed - using degraded mode")
            
            # Set up signal handlers for graceful shutdown
            try:
                signal.signal(signal.SIGINT, self._signal_handler)
                signal.signal(signal.SIGTERM, self._signal_handler)
            except Exception as e:
                self.error_handler.handle_error(e, {
                    'operation': 'setup_signal_handlers',
                    'component': 'system'
                })
            
            # Main thread waits for monitoring
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
            
            self.stop()
            
        except Exception as e:
            # Critical startup error
            self.error_handler.handle_error(e, {
                'operation': 'service_startup',
                'component': 'main_service',
                'fatal': True
            })
            print("❌ Critical startup error - LoopGuard cannot start")
            return False
    
    def stop(self):
        """Stop enhanced LoopGuard service with graceful shutdown"""
        try:
            print("\n🛑 Stopping LoopGuard...")
            self.running = False
            
            # Stop performance monitoring
            self.performance_monitor.stop_monitoring()
            
            # Stop components with error handling
            if self.file_watcher:
                try:
                    self.file_watcher.stop_watching()
                    print("✅ Enhanced file watching stopped")
                except Exception as e:
                    self.error_handler.handle_error(e, {
                        'operation': 'stop_file_watching',
                        'component': 'file_watcher'
                    })
            
            if self.monitor_thread and self.monitor_thread.is_alive():
                try:
                    self.monitor_thread.join(timeout=5)
                    print("✅ Enhanced process monitoring stopped")
                except Exception as e:
                    self.error_handler.handle_error(e, {
                        'operation': 'stop_process_monitoring',
                        'component': 'process_monitor'
                    })
            
            # Stop notification service
            if self.notification_service:
                try:
                    self.notification_service.stop()
                    print("✅ Notification service stopped")
                except Exception as e:
                    self.error_handler.handle_error(e, {
                        'operation': 'stop_notifications',
                        'component': 'notification_service'
                    })
            
            # Export final performance data
            try:
                perf_file = Path.home() / ".loopguard" / f"performance_data_{int(time.time())}.json"
                self.performance_monitor.export_performance_data(str(perf_file), hours=1)
            except Exception as e:
                print(f"⚠️  Could not export performance data: {e}")
            
            print("✅ LoopGuard stopped")
            
        except Exception as e:
            self.error_handler.handle_error(e, {
                'operation': 'service_shutdown',
                'component': 'main_service',
                'fatal': False
            })
            print("⚠️  LoopGuard stopped with errors")
    
    def _enhanced_monitor_loop(self):
        """Enhanced monitoring loop with Week 3 features"""
        consecutive_errors = 0
        max_consecutive_errors = 5
        last_discovery_update = 0
        discovery_interval = 30  # Update discovery every 30 seconds
        
        while self.running:
            try:
                # Check for new Claude Code processes
                new_sessions = self.process_monitor.detect_claude_processes()
                
                for session in new_sessions:
                    print(f"📝 Detected Claude Code session (PID: {session.pid}, Priority: {session.priority})")
                    
                    # Update performance counters
                    self.performance_monitor.update_counters(sessions_processed=1)
                
                # Synchronize with session discovery
                current_time = time.time()
                if current_time - last_discovery_update > discovery_interval:
                    self.file_watcher.continuous_discovery_update()
                    
                    # Synchronize processes with discovered sessions
                    active_sessions = self.process_monitor.get_active_sessions()
                    process_map = {f"{s.pid}": s for s in active_sessions}
                    self.file_watcher.synchronize_with_processes(process_map)
                    
                    last_discovery_update = current_time
                    
                    # Update performance counters
                    self.performance_monitor.update_counters(
                        files_processed=len(self.file_watcher.watched_sessions)
                    )
                
                # Check performance alerts
                performance_alerts = self.performance_monitor.check_performance_alerts()
                for alert in performance_alerts:
                    print(f"⚠️  Performance Alert: {alert.message}")
                    if alert.severity == 'high':
                        # Auto-optimize on high severity alerts
                        self.performance_monitor.optimize_memory(aggressive=True)
                
                # Clean up terminated sessions
                active_sessions = self.process_monitor.get_active_sessions()
                for session in active_sessions:
                    session_id = f"{session.pid}"
                    if not self.file_watcher.is_watching_session(session_id):
                        print(f"⚠️  Session {session_id} not being watched")
                
                # Reset error count on successful iteration
                consecutive_errors = 0
                time.sleep(2)  # Check every 2 seconds
                
            except Exception as e:
                consecutive_errors += 1
                
                # Handle monitoring error
                handled = self.error_handler.handle_error(e, {
                    'operation': 'enhanced_monitor_loop',
                    'component': 'process_monitor',
                    'consecutive_errors': consecutive_errors
                })
                
                # Too many consecutive errors - enter safe mode
                if consecutive_errors >= max_consecutive_errors:
                    print("⚠️  Too many monitoring errors - entering safe mode")
                    self._enter_safe_mode()
                    break
                
                # Wait longer after errors
                time.sleep(min(10, 2 * consecutive_errors))
    
    def _enter_safe_mode(self):
        """Enter safe mode with minimal functionality"""
        print("🛡️  Entering safe mode - minimal monitoring active")
        
        # Stop non-essential components
        try:
            if self.file_watcher:
                self.file_watcher.stop_watching()
            if self.notification_service:
                self.notification_service.enabled = False
        except Exception as e:
            self.error_handler.handle_error(e, {
                'operation': 'enter_safe_mode',
                'component': 'system'
            })
    
    def get_health_status(self):
        """Get comprehensive system health status with Week 3 features"""
        try:
            # Get error handler health
            error_health = self.error_handler.get_health_status()
            
            # Get performance metrics
            perf_summary = self.performance_monitor.get_performance_summary(minutes=10)
            
            # Get component status
            components = {
                'file_watcher': {
                    'active': self.file_watcher is not None,
                    'watching': self.file_watcher.is_watching() if self.file_watcher else False,
                    'discovery_stats': self.file_watcher.get_discovery_stats() if self.file_watcher else {}
                },
                'notification_service': {
                    'active': self.notification_service is not None,
                    'available': self.notification_service.is_available() if self.notification_service else False,
                    'queue_status': self.notification_service.get_queue_status() if self.notification_service else {}
                },
                'process_monitor': {
                    'active': self.process_monitor is not None,
                    'active_sessions': len(self.process_monitor.get_active_sessions()) if self.process_monitor else 0,
                    'resource_usage': self.process_monitor.get_resource_usage_summary() if self.process_monitor else {}
                },
                'session_analytics': {
                    'active': self.session_analytics is not None,
                    'database_path': str(self.session_analytics.db_path) if self.session_analytics else None
                },
                'performance_monitor': {
                    'active': self.performance_monitor.monitoring_active,
                    'metrics': perf_summary,
                    'cache_stats': self.performance_monitor.get_cache_stats()
                },
                'adaptive_detector': {
                    'active': self.config.get('detection.adaptive_mode', True),
                    'stats': self.loop_detector.get_adaptation_stats()
                }
            }
            
            # Calculate overall health score
            base_health = error_health['health_score']
            
            # Adjust based on performance
            if perf_summary.get('memory', {}).get('within_target', True):
                base_health = min(100, base_health + 5)
            else:
                base_health = max(0, base_health - 10)
            
            if perf_summary.get('cpu', {}).get('within_target', True):
                base_health = min(100, base_health + 5)
            else:
                base_health = max(0, base_health - 10)
            
            overall_health = base_health
            if overall_health >= 90:
                health_status = "Excellent"
            elif overall_health >= 75:
                health_status = "Good"
            elif overall_health >= 60:
                health_status = "Fair"
            elif overall_health >= 40:
                health_status = "Poor"
            else:
                health_status = "Critical"
            
            return {
                'overall_status': health_status,
                'health_score': overall_health,
                'service_running': self.running,
                'components': components,
                'error_metrics': error_health,
                'uptime_minutes': self._get_uptime_minutes(),
                'week3_features': {
                    'multi_process_support': True,
                    'automatic_discovery': True,
                    'adaptive_detection': self.config.get('detection.adaptive_mode', True),
                    'performance_monitoring': self.performance_monitor.monitoring_active,
                    'user_friendly_config': True
                }
            }
            
        except Exception as e:
            self.error_handler.handle_error(e, {
                'operation': 'get_health_status',
                'component': 'system'
            })
            return {
                'overall_status': 'Unknown',
                'health_score': 0,
                'error': str(e)
            }
    
    def _get_uptime_minutes(self) -> int:
        """Get service uptime in minutes"""
        # This would be implemented with actual startup time tracking
        # For now, return a placeholder
        return 0
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\nReceived signal {signum}")
        self.stop()
        sys.exit(0)
    
    def status(self):
        """Show enhanced LoopGuard status with health information"""
        try:
            health_status = self.get_health_status()
            
            print("📊 LoopGuard Status")
            print(f"   Overall Status: {health_status['overall_status']}")
            print(f"   Health Score: {health_status['health_score']}/100")
            print(f"   Service Running: {health_status['service_running']}")
            print(f"   Uptime: {health_status['uptime_minutes']} minutes")
            print(f"   Config: {self.config.config_path}")
            
            # Component status
            print("\n🔧 Components:")
            components = health_status['components']
            for comp_name, comp_status in components.items():
                if comp_status['active']:
                    status_icon = "✅"
                else:
                    status_icon = "❌"
                print(f"     {comp_name}: {status_icon} {comp_status}")
            
            # Error metrics
            error_metrics = health_status['error_metrics']
            if error_metrics['total_error_count'] > 0:
                print("\n⚠️  Error Metrics:")
                print(f"     Total Errors: {error_metrics['total_error_count']}")
                print(f"     Recent (1h): {len(error_metrics['recent_errors_1h'])}")
                if error_metrics['active_fallback_modes']:
                    print(f"     Fallback Modes: {', '.join(error_metrics['active_fallback_modes'].keys())}")
            
            # Show active sessions
            if components['process_monitor']['active_sessions'] > 0:
                print("\n📝 Active Sessions:")
                active_sessions = self.process_monitor.get_active_sessions()
                for session in active_sessions:
                    print(f"     PID {session.pid}: {' '.join(session.cmdline[:3])}...")
            
            # Show detection thresholds
            print("\n🎯 Detection Thresholds:")
            print(f"     Tool Call Repeats: {self.config.get('detection.tool_call_repeats', 3)}")
            print(f"     Error Repeats: {self.config.get('detection.error_repeats', 2)}")
            print(f"     Stagnation Minutes: {self.config.get('detection.stagnation_minutes', 5)}")
            
        except Exception as e:
            print(f"❌ Error getting status: {e}")
            self.error_handler.handle_error(e, {
                'operation': 'get_status',
                'component': 'cli'
            })
        print(f"     Tool call repeats: {self.config.get('detection.tool_call_repeats')}")
        print(f"     Error repeats: {self.config.get('detection.error_repeats')}")
        print(f"     Stagnation minutes: {self.config.get('detection.stagnation_minutes')}")


@click.group()
@click.option('--config', '-c', help='Path to configuration file')
@click.pass_context
def cli(ctx, config):
    """LoopGuard - Real-time AI coding agent loop detector"""
    ctx.ensure_object(dict)
    ctx.obj['config_path'] = config


@cli.command()
@click.pass_context
def start(ctx):
    """Start LoopGuard service"""
    service = LoopGuardService(ctx.obj.get('config_path'))
    service.start()


@cli.command()
@click.pass_context  
def status(ctx):
    """Show LoopGuard status"""
    service = LoopGuardService(ctx.obj.get('config_path'))
    service.status()


@cli.command()
@click.pass_context
def analytics(ctx):
    """Show session analytics and efficiency reports"""
    service = LoopGuardService(ctx.obj.get('config_path'))
    
    # Get recent sessions with metrics
    recent_sessions = service.session_analytics.get_recent_sessions(limit=10)
    
    if not recent_sessions:
        print("📊 No session data available")
        return
    
    print("📈 Session Analytics (Last 10 sessions)")
    print("-" * 60)
    
    for session in recent_sessions:
        duration = f"{session.duration_minutes}m" if session.duration_minutes else "Active"
        efficiency_color = "🟢" if session.efficiency_score >= 80 else "🟡" if session.efficiency_score >= 60 else "🔴"
        
        print(f"Session: {session.session_id[:12]}...")
        print(f"  Duration: {duration}")
        print(f"  Efficiency: {efficiency_color} {session.efficiency_score:.1f}%")
        print(f"  Events: {session.total_events} ({session.tool_calls} tools, {session.file_operations} files)")
        print(f"  Loops: {session.loops_detected}")
        print(f"  Tokens: ~{session.estimated_tokens_used}")
        print()
    
    # Get efficiency summary
    summary = service.session_analytics.get_efficiency_summary(days=7)
    print("📈 7-Day Efficiency Summary")
    print("-" * 60)
    print(f"  Avg Efficiency: {summary['avg_efficiency_score']:.1f}%")
    print(f"  Total Loops: {summary['total_loops_detected']}")
    print(f"  Sessions: {summary['session_count']}")
    print(f"  Avg Tokens/Session: {summary['avg_tokens_per_session']:.0f}")


@cli.command()
@click.pass_context
def setup(ctx):
    """Run interactive configuration setup wizard"""
    service = LoopGuardService(ctx.obj.get('config_path'), interactive_setup=True)



@cli.command()
@click.pass_context
def validate(ctx):
    """Validate current configuration with user-friendly error messages"""
    service = LoopGuardService(ctx.obj.get('config_path'))
    
    is_valid, errors = service.config.validate_current_config()
    
    if is_valid:
        print("✅ Configuration is valid!")
    else:
        print(service.config.get_validation_summary())
        
        # Ask if user wants to auto-fix
        if click.confirm("\n🔧 Attempt to auto-fix configuration issues?"):
            service.config.interactive_setup()



@cli.command()
@click.pass_context
def performance(ctx):
    """Show performance monitoring statistics"""
    service = LoopGuardService(ctx.obj.get('config_path'))
    
    # Get performance summary
    perf_summary = service.performance_monitor.get_performance_summary(minutes=60)
    
    if 'error' in perf_summary:
        print(f"❌ Error getting performance data: {perf_summary['error']}")
        return
    
    print("� Performance Monitoring (Last 60 minutes)")
    print("-" * 50)
    
    # Memory stats
    memory = perf_summary['memory']
    memory_status = "✅" if memory['within_target'] else "⚠️"
    print(f"Memory: {memory_status} {memory['current_mb']:.1f}MB / {memory['target_mb']}MB")
    print(f"  Average: {memory['average_mb']:.1f}MB, Peak: {memory['peak_mb']:.1f}MB")
    
    # CPU stats
    cpu = perf_summary['cpu']
    cpu_status = "✅" if cpu['within_target'] else "⚠️"
    print(f"CPU: {cpu_status} {cpu['current_percent']:.1f}% / {cpu['target_percent']}%")
    print(f"  Average: {cpu['average_percent']:.1f}%, Peak: {cpu['peak_percent']:.1f}%")
    
    # Cache stats
    caches = perf_summary['caches']
    print(f"\nCache Usage:")
    print(f"  Sessions: {caches['session_cache_size']} / {caches['session_cache_max_size']} ({caches['session_cache_utilization']:.1%})")
    print(f"  Events: {caches['event_cache_size']} / {caches['event_cache_max_size']} ({caches['event_cache_utilization']:.1%})")
    print(f"  Alerts: {caches['alert_cache_size']} / {caches['alert_cache_max_size']} ({caches['alert_cache_utilization']:.1%})")
    
    # Counters
    counters = perf_summary['counters']
    print(f"\nCounters:")
    print(f"  Sessions processed: {counters['sessions_processed']}")
    print(f"  Files processed: {counters['files_processed']}")
    print(f"  Alerts processed: {counters['alerts_processed']}")
    print(f"  GC runs: {counters['gc_runs']}")
    print(f"  Optimizations applied: {counters['optimizations_applied']}")



@cli.command()
@click.option('--minutes', default=60, help='Minutes of performance data to export')
@click.option('--output', '-o', help='Output file path')
@click.pass_context
def export(ctx, minutes, output):
    """Export performance data to JSON file"""
    service = LoopGuardService(ctx.obj.get('config_path'))
    
    if not output:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = f"loopguard_performance_{timestamp}.json"
    
    service.performance_monitor.export_performance_data(output, hours=minutes//60)
    print(f"📊 Performance data exported to {output}")



@cli.command()
@click.pass_context
def adapt(ctx):
    """Show adaptive detection statistics and controls"""
    service = LoopGuardService(ctx.obj.get('config_path'))
    
    stats = service.loop_detector.get_adaptation_stats()
    
    if not stats.get('adaptive_mode', False):
        print("⚠️  Adaptive detection is disabled")
        print("Enable with: loopguard config set detection.adaptive_mode true")
        return
    
    print("🎯 Adaptive Detection Statistics")
    print("-" * 40)
    print(f"Total feedback: {stats['total_feedback']}")
    print(f"Adapted sessions: {stats['adapted_sessions']}")
    print(f"Average precision: {stats['average_precision']:.3f}")
    print(f"Average recall: {stats['average_recall']:.3f}")
    
    print("\nSession Type Profiles:")
    for session_type, profile in stats['profiles'].items():
        print(f"  {session_type}:")
        print(f"    Tool calls: {profile['tool_call_threshold']:.1f}")
        print(f"    Errors: {profile['error_threshold']:.1f}")
        print(f"    Stagnation: {profile['stagnation_threshold']:.1f} min")
        print(f"    Confidence: {profile['confidence_threshold']:.1f}")
    
    print("\nSession Types Detected:")
    for session_type, count in stats['session_types'].items():
        print(f"  {session_type}: {count} sessions")



@cli.command()
@click.option('--session-id', help='Provide feedback for specific session')
@click.option('--alert-id', help='Alert ID to provide feedback for')
@click.option('--correct/--incorrect', default=True, help='Was the alert correct?')
@click.pass_context
def feedback(ctx, session_id, alert_id, correct):
    """Provide feedback for loop detection to improve accuracy"""
    service = LoopGuardService(ctx.obj.get('config_path'))
    
    if not session_id or not alert_id:
        print("❌ Both --session-id and --alert-id are required")
        print("Use 'loopguard status' to see recent sessions and alerts")
        return
    
    service.loop_detector.provide_feedback(
        session_id=session_id,
        alert_id=alert_id,
        was_correct=correct,
        feedback_type="user"
    )
    
    result = "✅" if correct else "❌"
    print(f"{result} Feedback recorded for alert {alert_id} in session {session_id}")
    print("This will help improve adaptive detection accuracy.")


def main():
    """Main entry point"""
    cli()


if __name__ == '__main__':
    main()
