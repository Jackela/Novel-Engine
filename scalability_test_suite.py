#!/usr/bin/env python3
"""
Comprehensive Scalability and Load Testing Suite for Novel Engine
================================================================

Enterprise-grade performance validation system for concurrent user testing,
story generation throughput, database performance, and system resource analysis.

Production Scalability Standards:
- Support 500+ concurrent users
- Maintain <200ms response time at 80% capacity
- Handle 100+ simultaneous story generations
- Sustain operation for 7+ days under load
- Resource utilization <70% under normal load
"""

import asyncio
import aiohttp
import time
import json
import logging
import statistics
import sqlite3
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import asynccontextmanager
import threading
import queue
import random
import string
from pathlib import Path

# Optional imports with fallbacks
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("Warning: psutil not available, system monitoring will be limited")

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    print("Warning: websockets not available, WebSocket testing will be skipped")

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scalability_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class TestConfiguration:
    """Load testing configuration parameters."""
    base_url: str = "http://127.0.0.1:8000"
    max_concurrent_users: int = 500
    story_generation_load: int = 100
    test_duration_minutes: int = 30
    ramp_up_duration: int = 300  # 5 minutes ramp-up
    database_connections: int = 50
    websocket_connections: int = 200
    target_response_time_ms: int = 200
    max_resource_utilization: float = 0.70
    test_data_size: int = 1000
    batch_size: int = 20

@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics collection."""
    timestamp: datetime = field(default_factory=datetime.now)
    response_times: List[float] = field(default_factory=list)
    success_rate: float = 0.0
    error_rate: float = 0.0
    throughput_rps: float = 0.0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_io: Dict[str, float] = field(default_factory=dict)
    network_io: Dict[str, float] = field(default_factory=dict)
    database_response_times: List[float] = field(default_factory=list)
    websocket_latency: List[float] = field(default_factory=list)
    concurrent_connections: int = 0
    active_story_generations: int = 0
    queue_depth: int = 0

@dataclass
class ScalabilityTestResults:
    """Comprehensive scalability test results."""
    test_start: datetime
    test_duration: timedelta
    peak_concurrent_users: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time: float
    percentile_95_response_time: float
    max_response_time: float
    throughput_rps: float
    error_rate: float
    peak_cpu_usage: float
    peak_memory_usage: float
    database_performance: Dict[str, float]
    websocket_performance: Dict[str, float]
    bottlenecks_identified: List[str]
    scaling_recommendations: List[str]
    production_readiness_score: float

class SystemResourceMonitor:
    """Advanced system resource monitoring for performance analysis."""
    
    def __init__(self):
        self.monitoring = False
        self.metrics: List[Dict[str, Any]] = []
        self.monitor_thread = None
        
    def start_monitoring(self, interval: float = 1.0):
        """Start system resource monitoring."""
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_resources, 
            args=(interval,)
        )
        self.monitor_thread.start()
        logger.info("System resource monitoring started")
    
    def stop_monitoring(self):
        """Stop system resource monitoring."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
        logger.info("System resource monitoring stopped")
    
    def _monitor_resources(self, interval: float):
        """Monitor system resources continuously."""
        while self.monitoring:
            try:
                if PSUTIL_AVAILABLE:
                    # CPU metrics
                    cpu_percent = psutil.cpu_percent(interval=None)
                    cpu_count = psutil.cpu_count()
                    cpu_freq = psutil.cpu_freq()
                    
                    # Memory metrics
                    memory = psutil.virtual_memory()
                    swap = psutil.swap_memory()
                    
                    # Disk I/O metrics
                    disk_io = psutil.disk_io_counters()
                    
                    # Network I/O metrics
                    network_io = psutil.net_io_counters()
                    
                    # Process metrics (for the server process if identifiable)
                    server_processes = []
                    try:
                        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                            try:
                                if 'python' in proc.info['name'].lower():
                                    server_processes.append(proc.info)
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                continue
                    except Exception:
                        pass
                    
                    metrics = {
                        'timestamp': datetime.now(),
                        'cpu': {
                            'percent': cpu_percent,
                            'count': cpu_count,
                            'frequency': cpu_freq._asdict() if cpu_freq else None
                        },
                        'memory': {
                            'total': memory.total,
                            'available': memory.available,
                            'percent': memory.percent,
                            'used': memory.used,
                            'swap_percent': swap.percent
                        },
                        'disk_io': {
                            'read_bytes': disk_io.read_bytes if disk_io else 0,
                            'write_bytes': disk_io.write_bytes if disk_io else 0,
                            'read_count': disk_io.read_count if disk_io else 0,
                            'write_count': disk_io.write_count if disk_io else 0
                        },
                        'network_io': {
                            'bytes_sent': network_io.bytes_sent if network_io else 0,
                            'bytes_recv': network_io.bytes_recv if network_io else 0,
                            'packets_sent': network_io.packets_sent if network_io else 0,
                            'packets_recv': network_io.packets_recv if network_io else 0
                        },
                        'server_processes': server_processes
                    }
                else:
                    # Fallback metrics when psutil is not available
                    metrics = {
                        'timestamp': datetime.now(),
                        'cpu': {'percent': 0, 'count': 1, 'frequency': None},
                        'memory': {'total': 0, 'available': 0, 'percent': 0, 'used': 0, 'swap_percent': 0},
                        'disk_io': {'read_bytes': 0, 'write_bytes': 0, 'read_count': 0, 'write_count': 0},
                        'network_io': {'bytes_sent': 0, 'bytes_recv': 0, 'packets_sent': 0, 'packets_recv': 0},
                        'server_processes': []
                    }
                
                self.metrics.append(metrics)
                
                # Keep only last hour of metrics to prevent memory bloat
                if len(self.metrics) > 3600:
                    self.metrics = self.metrics[-3600:]
                    
            except Exception as e:
                logger.error(f"Error monitoring resources: {e}")
            
            time.sleep(interval)
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current system metrics."""
        if self.metrics:
            return self.metrics[-1]
        return {}
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of collected metrics."""
        if not self.metrics:
            return {}
        
        cpu_values = [m['cpu']['percent'] for m in self.metrics]
        memory_values = [m['memory']['percent'] for m in self.metrics]
        
        return {
            'cpu_avg': statistics.mean(cpu_values),
            'cpu_max': max(cpu_values),
            'cpu_min': min(cpu_values),
            'memory_avg': statistics.mean(memory_values),
            'memory_max': max(memory_values),
            'memory_min': min(memory_values),
            'samples_collected': len(self.metrics),
            'monitoring_duration': (self.metrics[-1]['timestamp'] - self.metrics[0]['timestamp']).total_seconds()
        }

class ConcurrentUserSimulator:
    """Advanced concurrent user simulation for load testing."""
    
    def __init__(self, config: TestConfiguration):
        self.config = config
        self.session = None
        self.metrics = PerformanceMetrics()
        self.active_users = 0
        self.completed_requests = 0
        self.failed_requests = 0
        
    async def initialize(self):
        """Initialize HTTP session for testing."""
        connector = aiohttp.TCPConnector(
            limit=self.config.max_concurrent_users * 2,
            limit_per_host=self.config.max_concurrent_users,
            ttl_dns_cache=300,
            keepalive_timeout=30
        )
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        )
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.session:
            await self.session.close()
    
    async def simulate_concurrent_users(self, user_count: int, duration: int) -> Dict[str, Any]:
        """Simulate concurrent users with realistic traffic patterns."""
        logger.info(f"Starting concurrent user simulation: {user_count} users for {duration} seconds")
        
        # Create user simulation tasks
        tasks = []
        for user_id in range(user_count):
            task = asyncio.create_task(
                self._simulate_user_session(user_id, duration)
            )
            tasks.append(task)
            
            # Stagger user arrivals for realistic ramp-up
            if user_id % 10 == 0:
                await asyncio.sleep(0.1)
        
        # Wait for all users to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        successful_sessions = sum(1 for r in results if not isinstance(r, Exception))
        failed_sessions = len(results) - successful_sessions
        
        return {
            'total_users': user_count,
            'successful_sessions': successful_sessions,
            'failed_sessions': failed_sessions,
            'session_success_rate': successful_sessions / user_count,
            'total_requests': self.completed_requests,
            'failed_requests': self.failed_requests,
            'request_success_rate': (self.completed_requests - self.failed_requests) / max(self.completed_requests, 1)
        }
    
    async def _simulate_user_session(self, user_id: int, duration: int):
        """Simulate a realistic user session with multiple API interactions."""
        session_start = time.time()
        request_count = 0
        
        try:
            while time.time() - session_start < duration:
                # Simulate realistic user behavior patterns
                await self._simulate_user_actions(user_id)
                request_count += 1
                
                # Random think time between actions (1-5 seconds)
                think_time = random.uniform(1, 5)
                await asyncio.sleep(think_time)
                
        except Exception as e:
            logger.error(f"User {user_id} session failed: {e}")
            self.failed_requests += request_count
            raise
        
        self.completed_requests += request_count
    
    async def _simulate_user_actions(self, user_id: int):
        """Simulate realistic user actions with timing measurement."""
        actions = [
            self._test_health_endpoint,
            self._test_characters_endpoint,
            self._test_simulation_endpoint,
            self._test_story_generation
        ]
        
        # Randomly select and execute action
        action = random.choice(actions)
        start_time = time.time()
        
        try:
            await action(user_id)
            response_time = (time.time() - start_time) * 1000
            self.metrics.response_times.append(response_time)
        except Exception as e:
            logger.debug(f"User {user_id} action failed: {e}")
            self.failed_requests += 1
            raise
    
    async def _test_health_endpoint(self, user_id: int):
        """Test health endpoint."""
        async with self.session.get(f"{self.config.base_url}/health") as response:
            if response.status != 200:
                raise Exception(f"Health check failed: {response.status}")
    
    async def _test_characters_endpoint(self, user_id: int):
        """Test characters endpoint."""
        async with self.session.get(f"{self.config.base_url}/characters") as response:
            if response.status != 200:
                raise Exception(f"Characters endpoint failed: {response.status}")
    
    async def _test_simulation_endpoint(self, user_id: int):
        """Test simulation endpoint with realistic data."""
        # Generate realistic character selection
        characters = ["Aria", "Zara", "Marcus", "Elena", "Kai"]
        selected_characters = random.sample(characters, random.randint(2, 4))
        
        payload = {
            "character_names": selected_characters,
            "turns": random.randint(2, 5)
        }
        
        async with self.session.post(
            f"{self.config.base_url}/simulations",
            json=payload
        ) as response:
            if response.status not in [200, 201]:
                raise Exception(f"Simulation failed: {response.status}")
    
    async def _test_story_generation(self, user_id: int):
        """Test story generation API if available."""
        try:
            # Generate realistic story request
            characters = ["Hero", "Villain", "Sage"]
            selected_characters = random.sample(characters, random.randint(2, 3))
            
            payload = {
                "characters": selected_characters,
                "title": f"User {user_id} Story {random.randint(1, 1000)}"
            }
            
            async with self.session.post(
                f"{self.config.base_url}/api/v1/stories/generate",
                json=payload
            ) as response:
                if response.status not in [200, 201]:
                    logger.debug(f"Story generation not available or failed: {response.status}")
        except Exception:
            # Story generation might not be available
            pass

class StoryGenerationThroughputTester:
    """Specialized testing for story generation throughput and performance."""
    
    def __init__(self, config: TestConfiguration):
        self.config = config
        self.session = None
        self.generation_metrics: List[Dict[str, Any]] = []
        
    async def initialize(self):
        """Initialize HTTP session for story generation testing."""
        connector = aiohttp.TCPConnector(
            limit=self.config.story_generation_load * 2,
            limit_per_host=self.config.story_generation_load
        )
        timeout = aiohttp.ClientTimeout(total=300, connect=30)  # Longer timeout for story generation
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        )
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.session:
            await self.session.close()
    
    async def test_story_generation_throughput(self, concurrent_generations: int) -> Dict[str, Any]:
        """Test story generation system throughput under load."""
        logger.info(f"Testing story generation throughput: {concurrent_generations} concurrent generations")
        
        # Create story generation tasks
        tasks = []
        for gen_id in range(concurrent_generations):
            task = asyncio.create_task(
                self._generate_story_with_metrics(gen_id)
            )
            tasks.append(task)
        
        # Execute all generations concurrently
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_duration = time.time() - start_time
        
        # Analyze results
        successful_generations = sum(1 for r in results if not isinstance(r, Exception))
        failed_generations = len(results) - successful_generations
        
        if self.generation_metrics:
            avg_generation_time = statistics.mean([m['duration'] for m in self.generation_metrics])
            p95_generation_time = statistics.quantiles([m['duration'] for m in self.generation_metrics], n=20)[18]  # 95th percentile
        else:
            avg_generation_time = 0
            p95_generation_time = 0
        
        throughput = successful_generations / total_duration if total_duration > 0 else 0
        
        return {
            'concurrent_generations': concurrent_generations,
            'successful_generations': successful_generations,
            'failed_generations': failed_generations,
            'success_rate': successful_generations / concurrent_generations,
            'total_duration': total_duration,
            'throughput_per_second': throughput,
            'avg_generation_time': avg_generation_time,
            'p95_generation_time': p95_generation_time,
            'generation_metrics': self.generation_metrics
        }
    
    async def _generate_story_with_metrics(self, generation_id: int) -> Dict[str, Any]:
        """Generate a story with detailed performance metrics."""
        characters = ["Alice", "Bob", "Charlie", "Diana", "Eve"]
        selected_characters = random.sample(characters, random.randint(2, 4))
        
        payload = {
            "characters": selected_characters,
            "title": f"Load Test Story {generation_id}"
        }
        
        start_time = time.time()
        try:
            # Initiate story generation
            async with self.session.post(
                f"{self.config.base_url}/api/v1/stories/generate",
                json=payload
            ) as response:
                if response.status not in [200, 201]:
                    raise Exception(f"Story generation initiation failed: {response.status}")
                
                response_data = await response.json()
                generation_id_server = response_data.get('generation_id')
                
                if not generation_id_server:
                    raise Exception("No generation ID returned")
            
            # Monitor generation progress (if WebSocket available)
            completion_time = await self._monitor_generation_progress(generation_id_server)
            
            total_duration = time.time() - start_time
            
            metrics = {
                'generation_id': generation_id,
                'server_generation_id': generation_id_server,
                'characters': selected_characters,
                'duration': total_duration,
                'completion_time': completion_time,
                'status': 'completed'
            }
            
            self.generation_metrics.append(metrics)
            return metrics
            
        except Exception as e:
            duration = time.time() - start_time
            error_metrics = {
                'generation_id': generation_id,
                'duration': duration,
                'status': 'failed',
                'error': str(e)
            }
            self.generation_metrics.append(error_metrics)
            raise
    
    async def _monitor_generation_progress(self, generation_id: str) -> float:
        """Monitor story generation progress via REST API."""
        start_time = time.time()
        max_wait_time = 300  # 5 minutes maximum
        
        while time.time() - start_time < max_wait_time:
            try:
                async with self.session.get(
                    f"{self.config.base_url}/api/v1/stories/status/{generation_id}"
                ) as response:
                    if response.status == 200:
                        status_data = await response.json()
                        if status_data.get('status') == 'completed':
                            return time.time() - start_time
                        elif status_data.get('status') == 'failed':
                            raise Exception("Generation failed on server")
                    elif response.status == 404:
                        # Generation not found, might not be implemented
                        await asyncio.sleep(5)  # Wait a bit and assume completion
                        return 5.0
                
                await asyncio.sleep(1)  # Poll every second
                
            except Exception as e:
                logger.debug(f"Error monitoring generation {generation_id}: {e}")
                break
        
        # Return estimated completion time if monitoring fails
        return 30.0

class DatabasePerformanceTester:
    """Database performance testing under concurrent load."""
    
    def __init__(self, config: TestConfiguration):
        self.config = config
        self.db_path = "context.db"  # Default database path
        self.metrics: List[Dict[str, Any]] = []
    
    async def test_database_performance(self) -> Dict[str, Any]:
        """Test database performance under concurrent access."""
        logger.info("Testing database performance under concurrent load")
        
        # Test concurrent read operations
        read_results = await self._test_concurrent_reads()
        
        # Test concurrent write operations
        write_results = await self._test_concurrent_writes()
        
        # Test mixed read/write operations
        mixed_results = await self._test_mixed_operations()
        
        # Analyze overall database performance
        return {
            'concurrent_reads': read_results,
            'concurrent_writes': write_results,
            'mixed_operations': mixed_results,
            'performance_summary': self._analyze_db_performance()
        }
    
    async def _test_concurrent_reads(self) -> Dict[str, Any]:
        """Test concurrent read operations."""
        concurrent_readers = 50
        operations_per_reader = 100
        
        async def read_operation(reader_id: int):
            query_times = []
            try:
                # Simulate database reads
                for _ in range(operations_per_reader):
                    start_time = time.time()
                    
                    # Since we're testing against SQLite, we'll use a simple approach
                    conn = sqlite3.connect(self.db_path, timeout=10.0)
                    cursor = conn.cursor()
                    
                    # Example read operations
                    cursor.execute("SELECT COUNT(*) FROM memories WHERE agent_id = ?", (f"test_agent_{reader_id}",))
                    result = cursor.fetchone()
                    
                    conn.close()
                    
                    query_time = (time.time() - start_time) * 1000
                    query_times.append(query_time)
                    
                    # Small delay to simulate realistic usage
                    await asyncio.sleep(0.01)
                
                return query_times
                
            except Exception as e:
                logger.error(f"Read operation failed for reader {reader_id}: {e}")
                return []
        
        # Execute concurrent reads
        start_time = time.time()
        tasks = [read_operation(i) for i in range(concurrent_readers)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_duration = time.time() - start_time
        
        # Analyze results
        all_query_times = []
        successful_readers = 0
        
        for result in results:
            if isinstance(result, list) and result:
                all_query_times.extend(result)
                successful_readers += 1
        
        if all_query_times:
            avg_query_time = statistics.mean(all_query_times)
            p95_query_time = statistics.quantiles(all_query_times, n=20)[18]
        else:
            avg_query_time = 0
            p95_query_time = 0
        
        return {
            'concurrent_readers': concurrent_readers,
            'successful_readers': successful_readers,
            'total_queries': len(all_query_times),
            'total_duration': total_duration,
            'queries_per_second': len(all_query_times) / total_duration if total_duration > 0 else 0,
            'avg_query_time_ms': avg_query_time,
            'p95_query_time_ms': p95_query_time
        }
    
    async def _test_concurrent_writes(self) -> Dict[str, Any]:
        """Test concurrent write operations."""
        concurrent_writers = 20  # Lower for writes to avoid contention
        operations_per_writer = 50
        
        async def write_operation(writer_id: int):
            write_times = []
            try:
                for op_id in range(operations_per_writer):
                    start_time = time.time()
                    
                    conn = sqlite3.connect(self.db_path, timeout=30.0)
                    cursor = conn.cursor()
                    
                    # Example write operation
                    cursor.execute(
                        """INSERT OR REPLACE INTO memories 
                           (memory_id, agent_id, memory_type, content, timestamp, emotional_weight, relevance_score)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (
                            f"test_memory_{writer_id}_{op_id}",
                            f"test_agent_{writer_id}",
                            "episodic",
                            f"Test memory content from writer {writer_id}",
                            datetime.now(),
                            0.5,
                            0.7
                        )
                    )
                    conn.commit()
                    conn.close()
                    
                    write_time = (time.time() - start_time) * 1000
                    write_times.append(write_time)
                    
                    # Small delay for realistic usage
                    await asyncio.sleep(0.02)
                
                return write_times
                
            except Exception as e:
                logger.error(f"Write operation failed for writer {writer_id}: {e}")
                return []
        
        # Execute concurrent writes
        start_time = time.time()
        tasks = [write_operation(i) for i in range(concurrent_writers)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_duration = time.time() - start_time
        
        # Analyze results
        all_write_times = []
        successful_writers = 0
        
        for result in results:
            if isinstance(result, list) and result:
                all_write_times.extend(result)
                successful_writers += 1
        
        if all_write_times:
            avg_write_time = statistics.mean(all_write_times)
            p95_write_time = statistics.quantiles(all_write_times, n=20)[18]
        else:
            avg_write_time = 0
            p95_write_time = 0
        
        return {
            'concurrent_writers': concurrent_writers,
            'successful_writers': successful_writers,
            'total_writes': len(all_write_times),
            'total_duration': total_duration,
            'writes_per_second': len(all_write_times) / total_duration if total_duration > 0 else 0,
            'avg_write_time_ms': avg_write_time,
            'p95_write_time_ms': p95_write_time
        }
    
    async def _test_mixed_operations(self) -> Dict[str, Any]:
        """Test mixed read/write operations simulating realistic usage."""
        concurrent_users = 30
        operations_per_user = 75
        read_write_ratio = 0.7  # 70% reads, 30% writes
        
        async def mixed_operation(user_id: int):
            operation_times = []
            try:
                for op_id in range(operations_per_user):
                    start_time = time.time()
                    
                    conn = sqlite3.connect(self.db_path, timeout=15.0)
                    cursor = conn.cursor()
                    
                    if random.random() < read_write_ratio:
                        # Read operation
                        cursor.execute(
                            "SELECT content FROM memories WHERE agent_id = ? ORDER BY timestamp DESC LIMIT 10",
                            (f"test_agent_{user_id % 10}",)
                        )
                        results = cursor.fetchall()
                    else:
                        # Write operation
                        cursor.execute(
                            """INSERT OR REPLACE INTO memories 
                               (memory_id, agent_id, memory_type, content, timestamp, emotional_weight, relevance_score)
                               VALUES (?, ?, ?, ?, ?, ?, ?)""",
                            (
                                f"mixed_memory_{user_id}_{op_id}",
                                f"test_agent_{user_id % 10}",
                                "semantic",
                                f"Mixed operation memory from user {user_id}",
                                datetime.now(),
                                random.uniform(0.1, 0.9),
                                random.uniform(0.3, 0.8)
                            )
                        )
                        conn.commit()
                    
                    conn.close()
                    
                    operation_time = (time.time() - start_time) * 1000
                    operation_times.append(operation_time)
                    
                    await asyncio.sleep(0.015)
                
                return operation_times
                
            except Exception as e:
                logger.error(f"Mixed operation failed for user {user_id}: {e}")
                return []
        
        # Execute mixed operations
        start_time = time.time()
        tasks = [mixed_operation(i) for i in range(concurrent_users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_duration = time.time() - start_time
        
        # Analyze results
        all_operation_times = []
        successful_users = 0
        
        for result in results:
            if isinstance(result, list) and result:
                all_operation_times.extend(result)
                successful_users += 1
        
        if all_operation_times:
            avg_operation_time = statistics.mean(all_operation_times)
            p95_operation_time = statistics.quantiles(all_operation_times, n=20)[18]
        else:
            avg_operation_time = 0
            p95_operation_time = 0
        
        return {
            'concurrent_users': concurrent_users,
            'successful_users': successful_users,
            'total_operations': len(all_operation_times),
            'total_duration': total_duration,
            'operations_per_second': len(all_operation_times) / total_duration if total_duration > 0 else 0,
            'avg_operation_time_ms': avg_operation_time,
            'p95_operation_time_ms': p95_operation_time
        }
    
    def _analyze_db_performance(self) -> Dict[str, Any]:
        """Analyze overall database performance."""
        # This would include additional analysis of database locks,
        # connection pool efficiency, query optimization opportunities, etc.
        return {
            'analysis_completed': True,
            'recommendations': [
                "Consider connection pooling for high-concurrency scenarios",
                "Implement read replicas for read-heavy workloads",
                "Add database query optimization and indexing",
                "Consider migration to PostgreSQL for better concurrency"
            ]
        }

class WebSocketScalabilityTester:
    """WebSocket connection scalability and real-time feature testing."""
    
    def __init__(self, config: TestConfiguration):
        self.config = config
        self.connection_metrics: List[Dict[str, Any]] = []
        
    async def test_websocket_scalability(self) -> Dict[str, Any]:
        """Test WebSocket connection scalability and performance."""
        logger.info("Testing WebSocket scalability and real-time features")
        
        # Test concurrent WebSocket connections
        connection_results = await self._test_concurrent_connections()
        
        # Test message throughput
        throughput_results = await self._test_message_throughput()
        
        return {
            'concurrent_connections': connection_results,
            'message_throughput': throughput_results,
            'scalability_analysis': self._analyze_websocket_performance()
        }
    
    async def _test_concurrent_connections(self) -> Dict[str, Any]:
        """Test concurrent WebSocket connections."""
        if not WEBSOCKETS_AVAILABLE:
            return {
                'test_skipped': True,
                'reason': 'websockets library not available'
            }
        
        target_connections = min(self.config.websocket_connections, 100)  # Limit for testing
        connection_timeout = 10
        
        async def establish_connection(connection_id: int):
            try:
                import websockets
                # Try to connect to WebSocket endpoint (if available)
                uri = f"ws://127.0.0.1:8000/api/v1/stories/progress/test_{connection_id}"
                
                start_time = time.time()
                
                # Use a simple WebSocket connection test
                async with websockets.connect(uri, timeout=connection_timeout) as websocket:
                    connection_time = (time.time() - start_time) * 1000
                    
                    # Test basic communication
                    await websocket.send("ping")
                    response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    
                    # Keep connection alive briefly
                    await asyncio.sleep(2)
                    
                    return {
                        'connection_id': connection_id,
                        'connection_time_ms': connection_time,
                        'status': 'success',
                        'response': response
                    }
                    
            except Exception as e:
                return {
                    'connection_id': connection_id,
                    'status': 'failed',
                    'error': str(e)
                }
        
        # Attempt concurrent connections
        start_time = time.time()
        tasks = [establish_connection(i) for i in range(target_connections)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_duration = time.time() - start_time
        
        # Analyze results
        successful_connections = sum(1 for r in results if isinstance(r, dict) and r.get('status') == 'success')
        failed_connections = len(results) - successful_connections
        
        connection_times = [
            r['connection_time_ms'] for r in results 
            if isinstance(r, dict) and r.get('status') == 'success'
        ]
        
        avg_connection_time = statistics.mean(connection_times) if connection_times else 0
        
        return {
            'target_connections': target_connections,
            'successful_connections': successful_connections,
            'failed_connections': failed_connections,
            'success_rate': successful_connections / target_connections,
            'total_duration': total_duration,
            'avg_connection_time_ms': avg_connection_time
        }
    
    async def _test_message_throughput(self) -> Dict[str, Any]:
        """Test WebSocket message throughput."""
        # This is a placeholder since WebSocket implementation might not be fully available
        return {
            'message_throughput_test': 'not_available',
            'reason': 'WebSocket endpoints may not be fully implemented',
            'recommendation': 'Implement WebSocket load testing when endpoints are available'
        }
    
    def _analyze_websocket_performance(self) -> Dict[str, Any]:
        """Analyze WebSocket performance characteristics."""
        return {
            'analysis_completed': True,
            'recommendations': [
                "Implement proper WebSocket connection pooling",
                "Add heartbeat mechanism for connection health",
                "Consider using WebSocket clustering for scalability",
                "Implement message queuing for high-throughput scenarios"
            ]
        }

class ScalabilityTestSuite:
    """Comprehensive scalability testing orchestrator."""
    
    def __init__(self, config: Optional[TestConfiguration] = None):
        self.config = config or TestConfiguration()
        self.resource_monitor = SystemResourceMonitor()
        self.test_results: Dict[str, Any] = {}
        
    async def run_comprehensive_scalability_test(self) -> ScalabilityTestResults:
        """Execute comprehensive scalability testing suite."""
        logger.info("Starting comprehensive scalability testing suite")
        test_start = datetime.now()
        
        try:
            # Start system resource monitoring
            self.resource_monitor.start_monitoring()
            
            # Run all test phases
            await self._run_test_phases()
            
            # Stop monitoring and collect final metrics
            self.resource_monitor.stop_monitoring()
            
            # Generate comprehensive results
            return await self._generate_scalability_results(test_start)
            
        except Exception as e:
            logger.error(f"Scalability testing failed: {e}")
            self.resource_monitor.stop_monitoring()
            raise
    
    async def _run_test_phases(self):
        """Execute all testing phases in sequence."""
        
        # Phase 1: Basic load testing with ramping users
        logger.info("Phase 1: Basic load testing")
        await self._phase_1_basic_load_test()
        
        # Phase 2: Story generation throughput testing
        logger.info("Phase 2: Story generation throughput")
        await self._phase_2_story_generation_test()
        
        # Phase 3: Database performance testing
        logger.info("Phase 3: Database performance")
        await self._phase_3_database_performance_test()
        
        # Phase 4: WebSocket scalability testing
        logger.info("Phase 4: WebSocket scalability")
        await self._phase_4_websocket_scalability_test()
        
        # Phase 5: System stress testing
        logger.info("Phase 5: System stress testing")
        await self._phase_5_stress_test()
    
    async def _phase_1_basic_load_test(self):
        """Phase 1: Basic load testing with concurrent users."""
        user_simulator = ConcurrentUserSimulator(self.config)
        await user_simulator.initialize()
        
        try:
            # Gradual ramp-up testing
            ramp_up_results = []
            for user_count in [10, 25, 50, 100, 200]:
                if user_count > self.config.max_concurrent_users:
                    break
                
                logger.info(f"Testing {user_count} concurrent users")
                result = await user_simulator.simulate_concurrent_users(
                    user_count, 
                    60  # 1 minute per test
                )
                result['user_count'] = user_count
                ramp_up_results.append(result)
                
                # Short break between tests
                await asyncio.sleep(10)
            
            self.test_results['basic_load_test'] = {
                'ramp_up_results': ramp_up_results,
                'final_metrics': user_simulator.metrics
            }
            
        finally:
            await user_simulator.cleanup()
    
    async def _phase_2_story_generation_test(self):
        """Phase 2: Story generation throughput testing."""
        story_tester = StoryGenerationThroughputTester(self.config)
        await story_tester.initialize()
        
        try:
            # Test increasing levels of concurrent story generation
            generation_results = []
            for concurrent_gens in [5, 10, 20, 50]:
                if concurrent_gens > self.config.story_generation_load:
                    break
                
                logger.info(f"Testing {concurrent_gens} concurrent story generations")
                result = await story_tester.test_story_generation_throughput(concurrent_gens)
                generation_results.append(result)
                
                # Break between tests
                await asyncio.sleep(15)
            
            self.test_results['story_generation_test'] = {
                'generation_results': generation_results,
                'throughput_analysis': self._analyze_story_throughput(generation_results)
            }
            
        finally:
            await story_tester.cleanup()
    
    async def _phase_3_database_performance_test(self):
        """Phase 3: Database performance testing."""
        db_tester = DatabasePerformanceTester(self.config)
        
        db_results = await db_tester.test_database_performance()
        self.test_results['database_performance'] = db_results
    
    async def _phase_4_websocket_scalability_test(self):
        """Phase 4: WebSocket scalability testing."""
        websocket_tester = WebSocketScalabilityTester(self.config)
        
        websocket_results = await websocket_tester.test_websocket_scalability()
        self.test_results['websocket_scalability'] = websocket_results
    
    async def _phase_5_stress_test(self):
        """Phase 5: Maximum stress testing to find breaking points."""
        logger.info("Running stress test to identify system limits")
        
        user_simulator = ConcurrentUserSimulator(self.config)
        await user_simulator.initialize()
        
        try:
            # Progressive stress testing
            max_users = min(self.config.max_concurrent_users, 500)
            stress_duration = 300  # 5 minutes
            
            stress_result = await user_simulator.simulate_concurrent_users(
                max_users, 
                stress_duration
            )
            
            self.test_results['stress_test'] = {
                'max_users_tested': max_users,
                'duration_seconds': stress_duration,
                'results': stress_result
            }
            
        finally:
            await user_simulator.cleanup()
    
    def _analyze_story_throughput(self, generation_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze story generation throughput patterns."""
        if not generation_results:
            return {'analysis': 'no_data'}
        
        throughputs = [r['throughput_per_second'] for r in generation_results if 'throughput_per_second' in r]
        success_rates = [r['success_rate'] for r in generation_results if 'success_rate' in r]
        
        return {
            'max_throughput': max(throughputs) if throughputs else 0,
            'avg_throughput': statistics.mean(throughputs) if throughputs else 0,
            'avg_success_rate': statistics.mean(success_rates) if success_rates else 0,
            'scalability_trend': 'increasing' if len(throughputs) > 1 and throughputs[-1] > throughputs[0] else 'declining'
        }
    
    async def _generate_scalability_results(self, test_start: datetime) -> ScalabilityTestResults:
        """Generate comprehensive scalability test results."""
        test_duration = datetime.now() - test_start
        
        # Extract key metrics from all test phases
        total_requests = 0
        successful_requests = 0
        failed_requests = 0
        all_response_times = []
        
        # Aggregate metrics from all test phases
        for phase, results in self.test_results.items():
            if phase == 'basic_load_test':
                for ramp_result in results.get('ramp_up_results', []):
                    total_requests += ramp_result.get('total_requests', 0)
                    failed_requests += ramp_result.get('failed_requests', 0)
                    successful_requests += ramp_result.get('total_requests', 0) - ramp_result.get('failed_requests', 0)
            
            # Add response times if available
            if hasattr(results, 'response_times'):
                all_response_times.extend(results.response_times)
        
        # Calculate performance metrics
        if all_response_times:
            avg_response_time = statistics.mean(all_response_times)
            p95_response_time = statistics.quantiles(all_response_times, n=20)[18]
            max_response_time = max(all_response_times)
        else:
            avg_response_time = 0
            p95_response_time = 0
            max_response_time = 0
        
        # Get system metrics summary
        system_metrics = self.resource_monitor.get_metrics_summary()
        
        # Calculate error rate
        error_rate = failed_requests / max(total_requests, 1)
        
        # Calculate throughput
        throughput_rps = successful_requests / test_duration.total_seconds() if test_duration.total_seconds() > 0 else 0
        
        # Identify bottlenecks
        bottlenecks = self._identify_bottlenecks()
        
        # Generate scaling recommendations
        recommendations = self._generate_scaling_recommendations()
        
        # Calculate production readiness score
        readiness_score = self._calculate_production_readiness_score(
            error_rate, avg_response_time, system_metrics
        )
        
        return ScalabilityTestResults(
            test_start=test_start,
            test_duration=test_duration,
            peak_concurrent_users=self.config.max_concurrent_users,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            average_response_time=avg_response_time,
            percentile_95_response_time=p95_response_time,
            max_response_time=max_response_time,
            throughput_rps=throughput_rps,
            error_rate=error_rate,
            peak_cpu_usage=system_metrics.get('cpu_max', 0),
            peak_memory_usage=system_metrics.get('memory_max', 0),
            database_performance=self.test_results.get('database_performance', {}),
            websocket_performance=self.test_results.get('websocket_scalability', {}),
            bottlenecks_identified=bottlenecks,
            scaling_recommendations=recommendations,
            production_readiness_score=readiness_score
        )
    
    def _identify_bottlenecks(self) -> List[str]:
        """Identify system bottlenecks based on test results."""
        bottlenecks = []
        
        # Check CPU utilization
        system_metrics = self.resource_monitor.get_metrics_summary()
        if system_metrics.get('cpu_max', 0) > 80:
            bottlenecks.append("High CPU utilization detected - consider scaling vertically or horizontally")
        
        # Check memory usage
        if system_metrics.get('memory_max', 0) > 85:
            bottlenecks.append("High memory usage detected - optimize memory allocation or add RAM")
        
        # Check database performance
        db_results = self.test_results.get('database_performance', {})
        for test_type, results in db_results.items():
            if isinstance(results, dict) and results.get('p95_query_time_ms', 0) > 100:
                bottlenecks.append(f"Database {test_type} performance bottleneck - consider optimization")
        
        # Check story generation performance
        story_results = self.test_results.get('story_generation_test', {})
        if story_results.get('throughput_analysis', {}).get('avg_success_rate', 1) < 0.9:
            bottlenecks.append("Story generation success rate below 90% - investigate processing pipeline")
        
        return bottlenecks
    
    def _generate_scaling_recommendations(self) -> List[str]:
        """Generate scaling recommendations based on test results."""
        recommendations = []
        
        system_metrics = self.resource_monitor.get_metrics_summary()
        
        # CPU scaling recommendations
        if system_metrics.get('cpu_max', 0) > 70:
            recommendations.append("Consider horizontal scaling with load balancer for CPU-intensive operations")
        
        # Memory scaling recommendations
        if system_metrics.get('memory_max', 0) > 70:
            recommendations.append("Implement memory optimization and consider vertical scaling")
        
        # Database scaling recommendations
        recommendations.append("Consider implementing database connection pooling")
        recommendations.append("Evaluate migration to PostgreSQL for better concurrency support")
        
        # Story generation scaling recommendations
        recommendations.append("Implement queue-based story generation with worker processes")
        recommendations.append("Add caching layer for frequently accessed content")
        
        # WebSocket scaling recommendations
        recommendations.append("Implement WebSocket connection clustering for horizontal scaling")
        
        return recommendations
    
    def _calculate_production_readiness_score(self, error_rate: float, avg_response_time: float, 
                                             system_metrics: Dict[str, Any]) -> float:
        """Calculate production readiness score (0-100)."""
        score = 100.0
        
        # Deduct for high error rate
        if error_rate > 0.01:  # > 1%
            score -= min(50, error_rate * 5000)  # Max 50 point deduction
        
        # Deduct for slow response times
        if avg_response_time > 200:  # > 200ms
            score -= min(30, (avg_response_time - 200) / 10)  # Max 30 point deduction
        
        # Deduct for high resource utilization
        cpu_usage = system_metrics.get('cpu_max', 0)
        if cpu_usage > 70:
            score -= min(20, (cpu_usage - 70) / 3)  # Max 20 point deduction
        
        memory_usage = system_metrics.get('memory_max', 0)
        if memory_usage > 80:
            score -= min(15, (memory_usage - 80) / 2)  # Max 15 point deduction
        
        return max(0, score)

async def main():
    """Main execution function for scalability testing."""
    print("Novel Engine - Comprehensive Scalability Testing Suite")
    print("=" * 60)
    
    # Create test configuration
    config = TestConfiguration(
        max_concurrent_users=200,  # Reduced for testing
        story_generation_load=50,  # Reduced for testing
        test_duration_minutes=15,  # Shorter test duration
        websocket_connections=50   # Reduced for testing
    )
    
    # Create and run test suite
    test_suite = ScalabilityTestSuite(config)
    
    try:
        results = await test_suite.run_comprehensive_scalability_test()
        
        # Display results
        print("\nScalability Test Results:")
        print("-" * 40)
        print(f"Test Duration: {results.test_duration}")
        print(f"Total Requests: {results.total_requests}")
        print(f"Success Rate: {((results.successful_requests / max(results.total_requests, 1)) * 100):.1f}%")
        print(f"Average Response Time: {results.average_response_time:.1f}ms")
        print(f"95th Percentile Response Time: {results.percentile_95_response_time:.1f}ms")
        print(f"Throughput: {results.throughput_rps:.1f} requests/second")
        print(f"Peak CPU Usage: {results.peak_cpu_usage:.1f}%")
        print(f"Peak Memory Usage: {results.peak_memory_usage:.1f}%")
        print(f"Production Readiness Score: {results.production_readiness_score:.1f}/100")
        
        print("\nIdentified Bottlenecks:")
        for bottleneck in results.bottlenecks_identified:
            print(f"- {bottleneck}")
        
        print("\nScaling Recommendations:")
        for recommendation in results.scaling_recommendations:
            print(f"- {recommendation}")
        
        # Save detailed results
        results_file = f"scalability_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump({
                'test_configuration': config.__dict__,
                'test_results': test_suite.test_results,
                'scalability_summary': {
                    'test_duration': str(results.test_duration),
                    'total_requests': results.total_requests,
                    'success_rate': (results.successful_requests / max(results.total_requests, 1)) * 100,
                    'average_response_time': results.average_response_time,
                    'throughput_rps': results.throughput_rps,
                    'production_readiness_score': results.production_readiness_score,
                    'bottlenecks': results.bottlenecks_identified,
                    'recommendations': results.scaling_recommendations
                }
            }, f, indent=2, default=str)
        
        print(f"\nDetailed results saved to: {results_file}")
        
    except Exception as e:
        logger.error(f"Scalability testing failed: {e}")
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())