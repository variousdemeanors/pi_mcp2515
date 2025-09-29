"""
CAN Bus Diagnostics and Configuration Module
Provides real-time monitoring, benchmarking, and configuration for wireless CAN connections
"""

import time
import json
import requests
import logging
from datetime import datetime, timedelta
from collections import defaultdict, deque
import threading

logger = logging.getLogger(__name__)

class CANDiagnostics:
    """Real-time CAN bus diagnostics and performance monitoring."""
    
    def __init__(self, config):
        self.config = config
        self.connection_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'average_response_time': 0.0,
            'pids_per_second': 0.0,
            'last_update': None,
            'connection_quality': 'Unknown'
        }
        
        # Rolling window for performance metrics
        self.response_times = deque(maxlen=100)  # Last 100 responses
        self.pid_timestamps = deque(maxlen=50)   # Last 50 PID readings
        
        # PID-specific statistics
        self.pid_stats = defaultdict(lambda: {
            'count': 0,
            'last_value': None,
            'last_timestamp': None,
            'avg_response_time': 0.0,
            'success_rate': 0.0
        })
        
        self.is_monitoring = False
        self.monitor_thread = None
        
    def start_monitoring(self):
        """Start continuous monitoring of CAN performance."""
        if not self.is_monitoring:
            self.is_monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            logger.info("🔍 Started CAN diagnostics monitoring")
    
    def stop_monitoring(self):
        """Stop continuous monitoring."""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        logger.info("⏹️ Stopped CAN diagnostics monitoring")
    
    def _monitor_loop(self):
        """Background monitoring loop."""
        while self.is_monitoring:
            try:
                self._update_connection_stats()
                time.sleep(1)  # Update every second
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                time.sleep(5)
    
    def _update_connection_stats(self):
        """Update real-time connection statistics."""
        conn_config = self.config.get('network', {}).get('obd_connection', {})
        
        if conn_config.get('type') == 'wireless_can':
            self._test_wireless_connection()
        
        # Calculate PIDs per second
        now = time.time()
        recent_pids = [ts for ts in self.pid_timestamps if now - ts < 10]  # Last 10 seconds
        self.connection_stats['pids_per_second'] = len(recent_pids) / 10.0
        
        # Calculate average response time
        if self.response_times:
            self.connection_stats['average_response_time'] = sum(self.response_times) / len(self.response_times)
        
        # Determine connection quality
        pps = self.connection_stats['pids_per_second']
        avg_time = self.connection_stats['average_response_time']
        
        if pps >= 15 and avg_time <= 0.1:
            quality = 'Excellent'
        elif pps >= 10 and avg_time <= 0.2:
            quality = 'Good'
        elif pps >= 5 and avg_time <= 0.5:
            quality = 'Fair'
        else:
            quality = 'Poor'
        
        self.connection_stats['connection_quality'] = quality
        self.connection_stats['last_update'] = datetime.now()
    
    def _test_wireless_connection(self):
        """Test wireless CAN connection performance."""
        wireless_config = self.config.get('network', {}).get('obd_connection', {}).get('wireless_can', {})
        esp32_ip = wireless_config.get('esp32_ip', '192.168.4.1')
        esp32_port = wireless_config.get('esp32_port', 5000)
        
        start_time = time.time()
        try:
            response = requests.get(f"http://{esp32_ip}:{esp32_port}/obd_data", timeout=2)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                self.connection_stats['successful_requests'] += 1
                self.response_times.append(response_time)
                self.pid_timestamps.append(time.time())
                
                # Parse response for PID-specific stats
                try:
                    data = response.json()
                    self._update_pid_stats(data, response_time)
                except:
                    pass
            else:
                self.connection_stats['failed_requests'] += 1
                
        except Exception as e:
            self.connection_stats['failed_requests'] += 1
            logger.debug(f"Connection test failed: {e}")
        
        self.connection_stats['total_requests'] += 1
    
    def _update_pid_stats(self, data, response_time):
        """Update statistics for individual PIDs."""
        current_time = time.time()
        
        for pid_name, value in data.items():
            if pid_name in ['timestamp', 'data_valid']:
                continue
                
            stats = self.pid_stats[pid_name]
            stats['count'] += 1
            stats['last_value'] = value
            stats['last_timestamp'] = current_time
            
            # Update rolling average response time
            if stats['avg_response_time'] == 0:
                stats['avg_response_time'] = response_time
            else:
                # Exponential moving average
                stats['avg_response_time'] = 0.8 * stats['avg_response_time'] + 0.2 * response_time
    
    def benchmark_connection(self, duration_seconds=30):
        """Run a comprehensive benchmark test."""
        logger.info(f"🏁 Starting {duration_seconds}s CAN benchmark...")
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        initial_stats = self.connection_stats.copy()
        pid_counts = defaultdict(int)
        response_times = []
        errors = []
        
        conn_config = self.config.get('network', {}).get('obd_connection', {})
        
        if conn_config.get('type') != 'wireless_can':
            return {'error': 'Benchmark only supports wireless CAN connections'}
        
        wireless_config = conn_config.get('wireless_can', {})
        esp32_ip = wireless_config.get('esp32_ip', '192.168.4.1')
        esp32_port = wireless_config.get('esp32_port', 5000)
        
        while time.time() < end_time:
            test_start = time.time()
            try:
                response = requests.get(f"http://{esp32_ip}:{esp32_port}/obd_data", timeout=1)
                response_time = time.time() - test_start
                
                if response.status_code == 200:
                    response_times.append(response_time)
                    
                    try:
                        data = response.json()
                        for pid_name, value in data.items():
                            if pid_name not in ['timestamp', 'data_valid']:
                                pid_counts[pid_name] += 1
                    except:
                        pass
                else:
                    errors.append(f"HTTP {response.status_code}")
                    
            except Exception as e:
                errors.append(str(e))
                response_times.append(999)  # Max penalty for failed requests
            
            time.sleep(0.05)  # 50ms between requests (20Hz max)
        
        # Calculate benchmark results
        actual_duration = time.time() - start_time
        total_requests = len(response_times)
        successful_requests = len([rt for rt in response_times if rt < 10])
        
        results = {
            'duration': actual_duration,
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'failed_requests': len(errors),
            'success_rate': (successful_requests / total_requests * 100) if total_requests > 0 else 0,
            'requests_per_second': total_requests / actual_duration,
            'successful_rps': successful_requests / actual_duration,
            'average_response_time': sum(response_times) / len(response_times) if response_times else 0,
            'min_response_time': min(response_times) if response_times else 0,
            'max_response_time': max([rt for rt in response_times if rt < 10]) if response_times else 0,
            'pid_counts': dict(pid_counts),
            'total_pids': sum(pid_counts.values()),
            'pids_per_second': sum(pid_counts.values()) / actual_duration,
            'errors': errors[:10],  # First 10 errors
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"✅ Benchmark complete: {results['successful_rps']:.1f} RPS, {results['pids_per_second']:.1f} PID/s")
        return results
    
    def get_current_status(self):
        """Get current connection status and statistics."""
        conn_config = self.config.get('network', {}).get('obd_connection', {})
        
        status = {
            'connection_type': conn_config.get('type', 'Unknown'),
            'connection_configured': bool(conn_config),
            'monitoring_active': self.is_monitoring,
            'stats': self.connection_stats.copy(),
            'pid_stats': dict(self.pid_stats),
            'timestamp': datetime.now().isoformat()
        }
        
        if conn_config.get('type') == 'wireless_can':
            wireless_config = conn_config.get('wireless_can', {})
            status['wireless_config'] = {
                'esp32_ip': wireless_config.get('esp32_ip'),
                'esp32_port': wireless_config.get('esp32_port'),
                'timeout': wireless_config.get('timeout'),
                'endpoint': wireless_config.get('endpoint')
            }
            
            # Test current connection
            esp32_ip = wireless_config.get('esp32_ip', '192.168.4.1')
            esp32_port = wireless_config.get('esp32_port', 5000)
            
            try:
                response = requests.get(f"http://{esp32_ip}:{esp32_port}/status", timeout=2)
                status['esp32_status'] = 'Online' if response.status_code == 200 else f'Error {response.status_code}'
            except:
                status['esp32_status'] = 'Offline'
        
        return status
    
    def get_performance_recommendations(self):
        """Get recommendations for improving CAN performance."""
        recommendations = []
        
        pps = self.connection_stats['pids_per_second']
        avg_time = self.connection_stats['average_response_time']
        success_rate = (self.connection_stats['successful_requests'] / 
                       max(1, self.connection_stats['total_requests']) * 100)
        
        if pps < 10:
            recommendations.append({
                'severity': 'warning',
                'issue': 'Low PID Rate',
                'description': f'Only {pps:.1f} PIDs/second. Target: >10 PID/s',
                'suggestions': [
                    'Check WiFi signal strength',
                    'Reduce ESP32 request interval',
                    'Optimize network latency'
                ]
            })
        
        if avg_time > 0.2:
            recommendations.append({
                'severity': 'warning',
                'issue': 'High Response Time',
                'description': f'Average response: {avg_time*1000:.0f}ms. Target: <200ms',
                'suggestions': [
                    'Move ESP32 closer to RPi4',
                    'Check for network interference',
                    'Reduce ESP32 HTTP timeout'
                ]
            })
        
        if success_rate < 95:
            recommendations.append({
                'severity': 'error',
                'issue': 'Connection Reliability',
                'description': f'Success rate: {success_rate:.1f}%. Target: >95%',
                'suggestions': [
                    'Check ESP32 power supply',
                    'Verify CAN bus wiring',
                    'Test with vehicle running'
                ]
            })
        
        if not recommendations:
            recommendations.append({
                'severity': 'success',
                'issue': 'Performance Optimal',
                'description': 'CAN connection is performing excellently',
                'suggestions': ['No optimizations needed']
            })
        
        return recommendations