#!/usr/bin/env python3
"""
Scalability Framework for Novel Engine - Iteration 2.

This module implements horizontal scaling capabilities, load balancing preparation,
stateless operation patterns, container orchestration readiness, and distributed
system foundations for production deployment.
"""

import asyncio
import base64
import hashlib
import json
import logging
import pickle
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

import yaml

logger = logging.getLogger(__name__)


class ScalingMode(Enum):
    """Scaling operation modes."""

    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    AUTO = "auto"


class NodeStatus(Enum):
    """Node status in the cluster."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAINING = "draining"
    FAILED = "failed"


class LoadBalancingStrategy(Enum):
    """Load balancing strategies."""

    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    CONSISTENT_HASH = "consistent_hash"
    RANDOM = "random"


@dataclass
class NodeInfo:
    """Information about a cluster node."""

    node_id: str
    host: str
    port: int
    status: NodeStatus = NodeStatus.ACTIVE
    weight: float = 1.0
    current_connections: int = 0
    max_connections: int = 1000
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    last_heartbeat: float = field(default_factory=time.time)
    capabilities: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def load_factor(self) -> float:
        """Calculate current load factor (0.0 to 1.0)."""
        connection_load = self.current_connections / max(self.max_connections, 1)
        cpu_load = self.cpu_usage / 100.0
        memory_load = self.memory_usage / 100.0
        return (connection_load + cpu_load + memory_load) / 3.0

    @property
    def is_healthy(self) -> bool:
        """Check if node is healthy."""
        return (
            self.status == NodeStatus.ACTIVE
            and time.time() - self.last_heartbeat < 60.0
            and self.load_factor < 0.9
        )


@dataclass
class ScalingPolicy:
    """Scaling policy configuration."""

    name: str
    metric_name: str
    scale_up_threshold: float
    scale_down_threshold: float
    min_instances: int = 1
    max_instances: int = 10
    scale_up_step: int = 1
    scale_down_step: int = 1
    cooldown_period: int = 300  # seconds
    evaluation_period: int = 60  # seconds
    enabled: bool = True


@dataclass
class StatelessSession:
    """Stateless session container for distributed processing."""

    session_id: str
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    accessed_at: float = field(default_factory=time.time)
    ttl: float = 3600.0  # 1 hour default

    def is_expired(self) -> bool:
        """Check if session has expired."""
        return time.time() - self.accessed_at > self.ttl

    def touch(self):
        """Update access time."""
        self.accessed_at = time.time()


class ConsistentHashRing:
    """Consistent hash ring for distributed load balancing."""

    def __init__(self, replicas: int = 160):
        self.replicas = replicas
        self.ring = {}
        self.sorted_keys = []

    def add_node(self, node_id: str):
        """Add a node to the hash ring."""
        for i in range(self.replicas):
            key = self._hash(f"{node_id}:{i}")
            self.ring[key] = node_id

        self._update_sorted_keys()
        logger.debug(f"Added node {node_id} to hash ring")

    def remove_node(self, node_id: str):
        """Remove a node from the hash ring."""
        for i in range(self.replicas):
            key = self._hash(f"{node_id}:{i}")
            self.ring.pop(key, None)

        self._update_sorted_keys()
        logger.debug(f"Removed node {node_id} from hash ring")

    def get_node(self, key: str) -> Optional[str]:
        """Get the node responsible for a given key."""
        if not self.ring:
            return None

        hash_key = self._hash(key)

        # Find the first node clockwise from the hash
        for ring_key in self.sorted_keys:
            if ring_key >= hash_key:
                return self.ring[ring_key]

        # Wrap around to the first node
        return self.ring[self.sorted_keys[0]]

    def get_nodes(self, key: str, count: int = 1) -> List[str]:
        """Get multiple nodes for redundancy."""
        if not self.ring or count <= 0:
            return []

        hash_key = self._hash(key)
        nodes = []
        seen_nodes = set()

        # Start from the primary node and move clockwise
        start_idx = 0
        for i, ring_key in enumerate(self.sorted_keys):
            if ring_key >= hash_key:
                start_idx = i
                break

        # Collect unique nodes
        for i in range(len(self.sorted_keys)):
            idx = (start_idx + i) % len(self.sorted_keys)
            node = self.ring[self.sorted_keys[idx]]

            if node not in seen_nodes:
                nodes.append(node)
                seen_nodes.add(node)

                if len(nodes) >= count:
                    break

        return nodes

    def _hash(self, key: str) -> int:
        """Hash function for the ring."""
        return int(hashlib.md5(key.encode()).hexdigest(), 16)

    def _update_sorted_keys(self):
        """Update the sorted keys list."""
        self.sorted_keys = sorted(self.ring.keys())


class LoadBalancer:
    """Advanced load balancer with multiple strategies."""

    def __init__(
        self, strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN
    ):
        self.strategy = strategy
        self.nodes = {}
        self.current_index = 0
        self.hash_ring = ConsistentHashRing()
        self.request_counts = defaultdict(int)
        self.lock = threading.RLock()

    def add_node(self, node: NodeInfo):
        """Add a node to the load balancer."""
        with self.lock:
            self.nodes[node.node_id] = node
            if self.strategy == LoadBalancingStrategy.CONSISTENT_HASH:
                self.hash_ring.add_node(node.node_id)
            logger.info(f"Added node {node.node_id} to load balancer")

    def remove_node(self, node_id: str):
        """Remove a node from the load balancer."""
        with self.lock:
            if node_id in self.nodes:
                del self.nodes[node_id]
                if self.strategy == LoadBalancingStrategy.CONSISTENT_HASH:
                    self.hash_ring.remove_node(node_id)
                logger.info(f"Removed node {node_id} from load balancer")

    def get_node(self, session_key: Optional[str] = None) -> Optional[NodeInfo]:
        """Get a node based on the load balancing strategy."""
        with self.lock:
            healthy_nodes = [node for node in self.nodes.values() if node.is_healthy]

            if not healthy_nodes:
                return None

            if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
                return self._round_robin(healthy_nodes)
            elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
                return self._least_connections(healthy_nodes)
            elif self.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
                return self._weighted_round_robin(healthy_nodes)
            elif self.strategy == LoadBalancingStrategy.CONSISTENT_HASH:
                return self._consistent_hash(session_key or str(uuid.uuid4()))
            elif self.strategy == LoadBalancingStrategy.RANDOM:
                return self._random(healthy_nodes)
            else:
                return healthy_nodes[0] if healthy_nodes else None

    def _round_robin(self, nodes: List[NodeInfo]) -> NodeInfo:
        """Round-robin load balancing."""
        node = nodes[self.current_index % len(nodes)]
        self.current_index += 1
        return node

    def _least_connections(self, nodes: List[NodeInfo]) -> NodeInfo:
        """Least connections load balancing."""
        return min(nodes, key=lambda n: n.current_connections)

    def _weighted_round_robin(self, nodes: List[NodeInfo]) -> NodeInfo:
        """Weighted round-robin load balancing."""
        # Simple weighted selection based on inverse load factor
        weights = [1.0 / max(node.load_factor, 0.1) for node in nodes]
        total_weight = sum(weights)

        target = (self.current_index % int(total_weight * 100)) / 100.0
        cumulative = 0.0

        for i, weight in enumerate(weights):
            cumulative += weight
            if cumulative >= target:
                self.current_index += 1
                return nodes[i]

        return nodes[0]

    def _consistent_hash(self, key: str) -> Optional[NodeInfo]:
        """Consistent hash load balancing."""
        node_id = self.hash_ring.get_node(key)
        return self.nodes.get(node_id) if node_id else None

    def _random(self, nodes: List[NodeInfo]) -> NodeInfo:
        """Random load balancing."""
        import random

        return random.choice(nodes)

    def update_node_stats(
        self, node_id: str, connections: int, cpu_usage: float, memory_usage: float
    ):
        """Update node statistics."""
        with self.lock:
            if node_id in self.nodes:
                node = self.nodes[node_id]
                node.current_connections = connections
                node.cpu_usage = cpu_usage
                node.memory_usage = memory_usage
                node.last_heartbeat = time.time()

    def get_stats(self) -> Dict[str, Any]:
        """Get load balancer statistics."""
        with self.lock:
            total_nodes = len(self.nodes)
            healthy_nodes = sum(1 for node in self.nodes.values() if node.is_healthy)
            total_connections = sum(
                node.current_connections for node in self.nodes.values()
            )
            avg_load = sum(node.load_factor for node in self.nodes.values()) / max(
                total_nodes, 1
            )

            return {
                "strategy": self.strategy.value,
                "total_nodes": total_nodes,
                "healthy_nodes": healthy_nodes,
                "total_connections": total_connections,
                "average_load": avg_load,
                "nodes": {
                    node_id: asdict(node) for node_id, node in self.nodes.items()
                },
            }


class DistributedSessionManager:
    """Manages stateless sessions for distributed processing."""

    def __init__(self, default_ttl: float = 3600.0):
        self.default_ttl = default_ttl
        self.sessions = {}
        self.lock = asyncio.Lock()
        self.cleanup_task = None

    async def start(self):
        """Start the session manager."""
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Distributed session manager started")

    async def stop(self):
        """Stop the session manager."""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Distributed session manager stopped")

    async def create_session(
        self, session_id: Optional[str] = None, ttl: Optional[float] = None
    ) -> str:
        """Create a new stateless session."""
        if session_id is None:
            session_id = str(uuid.uuid4())

        session = StatelessSession(session_id=session_id, ttl=ttl or self.default_ttl)

        async with self.lock:
            self.sessions[session_id] = session

        logger.debug(f"Created session {session_id}")
        return session_id

    async def get_session(self, session_id: str) -> Optional[StatelessSession]:
        """Get a session by ID."""
        async with self.lock:
            session = self.sessions.get(session_id)
            if session and not session.is_expired():
                session.touch()
                return session
            elif session:
                # Remove expired session
                del self.sessions[session_id]
            return None

    async def update_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """Update session data."""
        async with self.lock:
            session = self.sessions.get(session_id)
            if session and not session.is_expired():
                session.data.update(data)
                session.touch()
                return True
            return False

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        async with self.lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                logger.debug(f"Deleted session {session_id}")
                return True
            return False

    async def serialize_session(self, session_id: str) -> Optional[str]:
        """Serialize a session for distribution."""
        session = await self.get_session(session_id)
        if session:
            serialized = pickle.dumps(asdict(session))
            return base64.b64encode(serialized).decode()
        return None

    async def deserialize_session(self, serialized_data: str) -> Optional[str]:
        """Deserialize a session from another node."""
        try:
            data = base64.b64decode(serialized_data.encode())
            session_data = pickle.loads(data)
            session = StatelessSession(**session_data)

            async with self.lock:
                self.sessions[session.session_id] = session

            return session.session_id
        except Exception as e:
            logger.error(f"Error deserializing session: {e}")
            return None

    async def _cleanup_loop(self):
        """Background cleanup of expired sessions."""
        while True:
            try:
                expired_sessions = []
                time.time()

                async with self.lock:
                    for session_id, session in list(self.sessions.items()):
                        if session.is_expired():
                            expired_sessions.append(session_id)

                    for session_id in expired_sessions:
                        del self.sessions[session_id]

                if expired_sessions:
                    logger.debug(f"Cleaned up {len(expired_sessions)} expired sessions")

                await asyncio.sleep(60)  # Cleanup every minute

            except Exception as e:
                logger.error(f"Session cleanup error: {e}")
                await asyncio.sleep(60)


class AutoScaler:
    """Automatic scaling system based on metrics and policies."""

    def __init__(self, load_balancer: LoadBalancer):
        self.load_balancer = load_balancer
        self.policies = {}
        self.metrics_history = defaultdict(lambda: deque(maxlen=100))
        self.last_scaling_action = {}
        self.scaling_active = False
        self.scaling_task = None

    async def start(self):
        """Start the auto-scaler."""
        if self.scaling_active:
            return

        self.scaling_active = True
        self.scaling_task = asyncio.create_task(self._scaling_loop())
        logger.info("Auto-scaler started")

    async def stop(self):
        """Stop the auto-scaler."""
        self.scaling_active = False
        if self.scaling_task:
            self.scaling_task.cancel()
            try:
                await self.scaling_task
            except asyncio.CancelledError:
                pass
        logger.info("Auto-scaler stopped")

    def add_policy(self, policy: ScalingPolicy):
        """Add a scaling policy."""
        self.policies[policy.name] = policy
        logger.info(f"Added scaling policy: {policy.name}")

    def remove_policy(self, policy_name: str):
        """Remove a scaling policy."""
        self.policies.pop(policy_name, None)
        logger.info(f"Removed scaling policy: {policy_name}")

    def record_metric(self, metric_name: str, value: float):
        """Record a metric value for scaling decisions."""
        self.metrics_history[metric_name].append(
            {"value": value, "timestamp": time.time()}
        )

    async def _scaling_loop(self):
        """Main scaling evaluation loop."""
        while self.scaling_active:
            try:
                for policy in self.policies.values():
                    if policy.enabled:
                        await self._evaluate_policy(policy)

                await asyncio.sleep(10)  # Evaluate every 10 seconds

            except Exception as e:
                logger.error(f"Scaling loop error: {e}")
                await asyncio.sleep(10)

    async def _evaluate_policy(self, policy: ScalingPolicy):
        """Evaluate a scaling policy and take action if needed."""
        # Check cooldown period
        last_action_time = self.last_scaling_action.get(policy.name, 0)
        if time.time() - last_action_time < policy.cooldown_period:
            return

        # Get recent metric values
        recent_metrics = self._get_recent_metrics(
            policy.metric_name, policy.evaluation_period
        )
        if not recent_metrics:
            return

        # Calculate average value
        avg_value = sum(m["value"] for m in recent_metrics) / len(recent_metrics)

        # Get current instance count
        current_instances = len(
            [n for n in self.load_balancer.nodes.values() if n.is_healthy]
        )

        # Scale up decision
        if (
            avg_value > policy.scale_up_threshold
            and current_instances < policy.max_instances
        ):

            await self._scale_up(policy, current_instances)

        # Scale down decision
        elif (
            avg_value < policy.scale_down_threshold
            and current_instances > policy.min_instances
        ):

            await self._scale_down(policy, current_instances)

    def _get_recent_metrics(
        self, metric_name: str, duration_seconds: int
    ) -> List[Dict[str, Any]]:
        """Get recent metric values within the specified duration."""
        cutoff_time = time.time() - duration_seconds
        return [
            m
            for m in self.metrics_history[metric_name]
            if m["timestamp"] >= cutoff_time
        ]

    async def _scale_up(self, policy: ScalingPolicy, current_instances: int):
        """Scale up the cluster."""
        target_instances = min(
            current_instances + policy.scale_up_step, policy.max_instances
        )

        logger.info(
            f"Scaling up {policy.name}: {current_instances} -> {target_instances}"
        )

        # In a real implementation, this would trigger container orchestration
        # For now, we'll simulate by adding placeholder nodes
        for i in range(target_instances - current_instances):
            node_id = f"auto_scaled_node_{uuid.uuid4().hex[:8]}"
            node = NodeInfo(
                node_id=node_id,
                host="auto-scaled-host",
                port=8000 + i,
                status=NodeStatus.ACTIVE,
                capabilities={"auto_scaled"},
            )
            self.load_balancer.add_node(node)

        self.last_scaling_action[policy.name] = time.time()

    async def _scale_down(self, policy: ScalingPolicy, current_instances: int):
        """Scale down the cluster."""
        target_instances = max(
            current_instances - policy.scale_down_step, policy.min_instances
        )

        logger.info(
            f"Scaling down {policy.name}: {current_instances} -> {target_instances}"
        )

        # Remove auto-scaled nodes first
        nodes_to_remove = []
        for node in self.load_balancer.nodes.values():
            if "auto_scaled" in node.capabilities and len(nodes_to_remove) < (
                current_instances - target_instances
            ):
                nodes_to_remove.append(node.node_id)

        for node_id in nodes_to_remove:
            self.load_balancer.remove_node(node_id)

        self.last_scaling_action[policy.name] = time.time()


class ContainerOrchestrationConfig:
    """Configuration for container orchestration deployment."""

    def __init__(self, app_name: str = "novel-engine"):
        self.app_name = app_name

    def generate_docker_compose(self) -> str:
        """Generate Docker Compose configuration."""
        config = {
            "version": "3.8",
            "services": {
                "novel-engine-api": {
                    "build": ".",
                    "ports": ["8000:8000"],
                    "environment": [
                        "NODE_ENV=production",
                        "DATABASE_URL=postgresql://user:pass@postgres:5432/novelengine",
                        "REDIS_URL=redis://redis:6379",
                    ],
                    "depends_on": ["postgres", "redis"],
                    "restart": "unless-stopped",
                    "healthcheck": {
                        "test": ["CMD", "curl", "-f", "http://localhost:8000/health"],
                        "interval": "30s",
                        "timeout": "10s",
                        "retries": 3,
                    },
                },
                "postgres": {
                    "image": "postgres:14",
                    "environment": [
                        "POSTGRES_DB=novelengine",
                        "POSTGRES_USER=user",
                        "POSTGRES_PASSWORD=pass",
                    ],
                    "volumes": ["postgres_data:/var/lib/postgresql/data"],
                    "restart": "unless-stopped",
                },
                "redis": {
                    "image": "redis:7-alpine",
                    "restart": "unless-stopped",
                    "volumes": ["redis_data:/data"],
                },
                "nginx": {
                    "image": "nginx:alpine",
                    "ports": ["80:80", "443:443"],
                    "volumes": [
                        "./nginx.conf:/etc/nginx/nginx.conf",
                        "./ssl:/etc/ssl/certs",
                    ],
                    "depends_on": ["novel-engine-api"],
                    "restart": "unless-stopped",
                },
            },
            "volumes": {"postgres_data": {}, "redis_data": {}},
        }

        return yaml.dump(config, default_flow_style=False)

    def generate_kubernetes_manifests(self) -> Dict[str, str]:
        """Generate Kubernetes deployment manifests."""
        manifests = {}

        # Deployment
        deployment = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": f"{self.app_name}-api",
                "labels": {"app": self.app_name},
            },
            "spec": {
                "replicas": 3,
                "selector": {"matchLabels": {"app": self.app_name}},
                "template": {
                    "metadata": {"labels": {"app": self.app_name}},
                    "spec": {
                        "containers": [
                            {
                                "name": self.app_name,
                                "image": f"{self.app_name}:latest",
                                "ports": [{"containerPort": 8000}],
                                "env": [
                                    {"name": "NODE_ENV", "value": "production"},
                                    {
                                        "name": "DATABASE_URL",
                                        "valueFrom": {
                                            "secretKeyRef": {
                                                "name": f"{self.app_name}-secrets",
                                                "key": "database-url",
                                            }
                                        },
                                    },
                                ],
                                "livenessProbe": {
                                    "httpGet": {"path": "/health", "port": 8000},
                                    "initialDelaySeconds": 30,
                                    "periodSeconds": 10,
                                },
                                "readinessProbe": {
                                    "httpGet": {"path": "/health", "port": 8000},
                                    "initialDelaySeconds": 5,
                                    "periodSeconds": 5,
                                },
                                "resources": {
                                    "requests": {"memory": "256Mi", "cpu": "100m"},
                                    "limits": {"memory": "512Mi", "cpu": "500m"},
                                },
                            }
                        ]
                    },
                },
            },
        }
        manifests["deployment.yaml"] = yaml.dump(deployment)

        # Service
        service = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {"name": f"{self.app_name}-service"},
            "spec": {
                "selector": {"app": self.app_name},
                "ports": [{"port": 80, "targetPort": 8000}],
                "type": "ClusterIP",
            },
        }
        manifests["service.yaml"] = yaml.dump(service)

        # HorizontalPodAutoscaler
        hpa = {
            "apiVersion": "autoscaling/v2",
            "kind": "HorizontalPodAutoscaler",
            "metadata": {"name": f"{self.app_name}-hpa"},
            "spec": {
                "scaleTargetRef": {
                    "apiVersion": "apps/v1",
                    "kind": "Deployment",
                    "name": f"{self.app_name}-api",
                },
                "minReplicas": 2,
                "maxReplicas": 10,
                "metrics": [
                    {
                        "type": "Resource",
                        "resource": {
                            "name": "cpu",
                            "target": {"type": "Utilization", "averageUtilization": 70},
                        },
                    },
                    {
                        "type": "Resource",
                        "resource": {
                            "name": "memory",
                            "target": {"type": "Utilization", "averageUtilization": 80},
                        },
                    },
                ],
            },
        }
        manifests["hpa.yaml"] = yaml.dump(hpa)

        return manifests

    def generate_dockerfile(self) -> str:
        """Generate optimized Dockerfile."""
        dockerfile = """# Multi-stage build for optimal image size
FROM python:3.11-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    g++ \\
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

# Create non-root user
RUN groupadd -r novelengine && useradd -r -g novelengine novelengine

# Copy dependencies from builder stage
COPY --from=builder /root/.local /home/novelengine/.local

# Set environment variables
ENV PATH=/home/novelengine/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=novelengine:novelengine . .

# Switch to non-root user
USER novelengine

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \\
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=10)"

# Expose port
EXPOSE 8000

# Start application
CMD ["python", "-m", "uvicorn", "async_api_server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
"""
        return dockerfile


class ScalabilityFramework:
    """Main scalability framework coordinator."""

    def __init__(self):
        self.load_balancer = LoadBalancer()
        self.session_manager = DistributedSessionManager()
        self.auto_scaler = AutoScaler(self.load_balancer)
        self.orchestration_config = ContainerOrchestrationConfig()
        self.framework_active = False

    async def start(self):
        """Start the scalability framework."""
        if self.framework_active:
            return

        await self.session_manager.start()
        await self.auto_scaler.start()

        # Setup default scaling policies
        self._setup_default_policies()

        # Register sample nodes (in production, these would be discovered)
        self._register_sample_nodes()

        self.framework_active = True
        logger.info("Scalability framework started")

    async def stop(self):
        """Stop the scalability framework."""
        if not self.framework_active:
            return

        await self.auto_scaler.stop()
        await self.session_manager.stop()

        self.framework_active = False
        logger.info("Scalability framework stopped")

    def _setup_default_policies(self):
        """Setup default auto-scaling policies."""
        policies = [
            ScalingPolicy(
                name="cpu_scaling",
                metric_name="avg_cpu_usage",
                scale_up_threshold=70.0,
                scale_down_threshold=30.0,
                min_instances=2,
                max_instances=10,
                cooldown_period=300,
            ),
            ScalingPolicy(
                name="memory_scaling",
                metric_name="avg_memory_usage",
                scale_up_threshold=80.0,
                scale_down_threshold=40.0,
                min_instances=2,
                max_instances=8,
                cooldown_period=600,
            ),
            ScalingPolicy(
                name="request_rate_scaling",
                metric_name="requests_per_second",
                scale_up_threshold=100.0,
                scale_down_threshold=20.0,
                min_instances=1,
                max_instances=15,
                cooldown_period=180,
            ),
        ]

        for policy in policies:
            self.auto_scaler.add_policy(policy)

    def _register_sample_nodes(self):
        """Register sample nodes for demonstration."""
        sample_nodes = [
            NodeInfo(
                node_id="node_1",
                host="localhost",
                port=8001,
                weight=1.0,
                capabilities={"api", "simulation"},
            ),
            NodeInfo(
                node_id="node_2",
                host="localhost",
                port=8002,
                weight=1.5,
                capabilities={"api", "simulation", "storage"},
            ),
        ]

        for node in sample_nodes:
            self.load_balancer.add_node(node)

    def get_framework_status(self) -> Dict[str, Any]:
        """Get comprehensive framework status."""
        return {
            "active": self.framework_active,
            "load_balancer": self.load_balancer.get_stats(),
            "session_count": len(self.session_manager.sessions),
            "scaling_policies": list(self.auto_scaler.policies.keys()),
            "timestamp": datetime.now().isoformat(),
        }


# Global scalability framework instance
scalability_framework = ScalabilityFramework()


# Helper functions for integration
async def setup_scalability():
    """Setup the scalability framework."""
    await scalability_framework.start()
    logger.info("Scalability framework initialized")


async def shutdown_scalability():
    """Shutdown the scalability framework."""
    await scalability_framework.stop()
    logger.info("Scalability framework shutdown")


if __name__ == "__main__":
    # Example usage and testing
    async def test_scalability_framework():
        """Test the scalability framework."""
        await setup_scalability()

        # Test load balancing
        print("Testing load balancing...")
        for i in range(10):
            node = scalability_framework.load_balancer.get_node()
            if node:
                print(f"Request {i} -> Node {node.node_id}")

        # Test session management
        print("\nTesting session management...")
        session_id = await scalability_framework.session_manager.create_session()
        await scalability_framework.session_manager.update_session(
            session_id, {"user_id": "test_user"}
        )

        session = await scalability_framework.session_manager.get_session(session_id)
        print(f"Session data: {session.data if session else 'Not found'}")

        # Test auto-scaling metrics
        print("\nTesting auto-scaling...")
        for i in range(5):
            scalability_framework.auto_scaler.record_metric(
                "avg_cpu_usage", 75.0 + i * 5
            )
            scalability_framework.auto_scaler.record_metric(
                "requests_per_second", 50.0 + i * 20
            )
            await asyncio.sleep(1)

        # Wait for scaling evaluation
        await asyncio.sleep(5)

        # Get status
        status = scalability_framework.get_framework_status()
        print(f"\nFramework status: {json.dumps(status, indent=2, default=str)}")

        # Generate container configurations
        print("\nGenerating container configurations...")
        (
            scalability_framework.orchestration_config.generate_docker_compose()
        )
        print("Docker Compose generated")

        k8s_manifests = (
            scalability_framework.orchestration_config.generate_kubernetes_manifests()
        )
        print(f"Kubernetes manifests generated: {list(k8s_manifests.keys())}")

        await shutdown_scalability()

    # Run the test
    asyncio.run(test_scalability_framework())
