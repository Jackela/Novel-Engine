#!/usr/bin/env python3
"""
ADVANCED MICROSERVICES ARCHITECTURE PATTERNS
==================================================

Enterprise-grade microservices patterns for Novel Engine scalability.
Implements service decomposition, API gateways, and distributed patterns.

Architecture Patterns:
- Service Discovery and Registration
- API Gateway with Load Balancing
- Circuit Breaker for Resilience
- Event-Driven Communication
- Distributed Caching Strategy
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import aiohttp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ServiceStatus(str, Enum):
    """Service health status enumeration"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class CircuitState(str, Enum):
    """Circuit breaker state enumeration"""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Circuit broken, failing fast
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class ServiceMetrics:
    """Service performance and health metrics"""

    request_count: int = 0
    error_count: int = 0
    average_response_time: float = 0.0
    last_health_check: Optional[datetime] = None
    status: ServiceStatus = ServiceStatus.UNKNOWN

    @property
    def error_rate(self) -> float:
        """Calculate error rate percentage"""
        return (self.error_count / max(self.request_count, 1)) * 100

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        return 100.0 - self.error_rate


@dataclass
class ServiceInstance:
    """Represents a service instance in the registry"""

    service_name: str
    instance_id: str
    host: str
    port: int
    health_endpoint: str = "/health"
    metadata: Dict[str, Any] = field(default_factory=dict)
    metrics: ServiceMetrics = field(default_factory=ServiceMetrics)
    registered_at: datetime = field(default_factory=datetime.now)

    @property
    def base_url(self) -> str:
        """Get the base URL for this service instance"""
        return f"http://{self.host}:{self.port}"

    @property
    def health_url(self) -> str:
        """Get the health check URL for this service instance"""
        return f"{self.base_url}{self.health_endpoint}"


class ServiceRegistry:
    """
    Service discovery and registration system
    Manages service instances and their health status
    """

    def __init__(self):
        self._services: Dict[str, List[ServiceInstance]] = {}
        self._health_check_interval = 30  # seconds
        self._health_check_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    async def register_service(self, service: ServiceInstance) -> bool:
        """Register a new service instance"""
        async with self._lock:
            if service.service_name not in self._services:
                self._services[service.service_name] = []

            # Check if instance already registered
            existing = self._find_instance(service.service_name, service.instance_id)
            if existing:
                # Update existing instance
                existing.host = service.host
                existing.port = service.port
                existing.metadata = service.metadata
                logger.info(
                    f"Updated service instance: {service.service_name}:{service.instance_id}"
                )
            else:
                # Add new instance
                self._services[service.service_name].append(service)
                logger.info(
                    f"Registered new service instance: {service.service_name}:{service.instance_id}"
                )

            # Start health checking if not already running
            if not self._health_check_task:
                self._health_check_task = asyncio.create_task(self._health_check_loop())

            return True

    async def deregister_service(self, service_name: str, instance_id: str) -> bool:
        """Deregister a service instance"""
        async with self._lock:
            if service_name in self._services:
                self._services[service_name] = [
                    s
                    for s in self._services[service_name]
                    if s.instance_id != instance_id
                ]
                # Remove service if no instances left
                if not self._services[service_name]:
                    del self._services[service_name]

                logger.info(
                    f"Deregistered service instance: {service_name}:{instance_id}"
                )
                return True
        return False

    def get_service_instances(self, service_name: str) -> List[ServiceInstance]:
        """Get all healthy instances of a service"""
        if service_name not in self._services:
            return []

        return [
            instance
            for instance in self._services[service_name]
            if instance.metrics.status == ServiceStatus.HEALTHY
        ]

    def get_service_instance(
        self, service_name: str, load_balancing: str = "round_robin"
    ) -> Optional[ServiceInstance]:
        """Get a single service instance using load balancing"""
        instances = self.get_service_instances(service_name)
        if not instances:
            return None

        if load_balancing == "round_robin":
            # Simple round-robin (stateless for now)
            return instances[int(time.time()) % len(instances)]
        elif load_balancing == "least_connections":
            # Return instance with lowest request count
            return min(instances, key=lambda x: x.metrics.request_count)
        else:
            # Default to first available
            return instances[0]

    def _find_instance(
        self, service_name: str, instance_id: str
    ) -> Optional[ServiceInstance]:
        """Find a specific service instance"""
        if service_name not in self._services:
            return None

        for instance in self._services[service_name]:
            if instance.instance_id == instance_id:
                return instance
        return None

    async def _health_check_loop(self):
        """Continuous health checking for all registered services"""
        while True:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self._health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(5)  # Short delay on error

    async def _perform_health_checks(self):
        """Perform health checks on all registered services"""
        tasks = []
        async with self._lock:
            for service_name, instances in self._services.items():
                for instance in instances:
                    task = asyncio.create_task(self._check_instance_health(instance))
                    tasks.append(task)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _check_instance_health(self, instance: ServiceInstance):
        """Check health of a single service instance"""
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=5)
            ) as session:
                start_time = time.time()
                async with session.get(instance.health_url) as response:
                    response_time = time.time() - start_time

                    if response.status == 200:
                        instance.metrics.status = ServiceStatus.HEALTHY
                        instance.metrics.average_response_time = response_time
                    else:
                        instance.metrics.status = ServiceStatus.DEGRADED

                    instance.metrics.last_health_check = datetime.now()

        except Exception as e:
            instance.metrics.status = ServiceStatus.UNHEALTHY
            instance.metrics.last_health_check = datetime.now()
            logger.warning(
                f"Health check failed for {instance.service_name}:{instance.instance_id}: {e}"
            )


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for resilience
    Prevents cascading failures by failing fast when service is down
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        expected_exception: type = Exception,
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

        self._lock = asyncio.Lock()

    async def call(self, func: Callable, *args, **kwargs):
        """Execute a function call through the circuit breaker"""
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    logger.info("Circuit breaker moving to HALF_OPEN state")
                else:
                    raise Exception("Circuit breaker is OPEN - failing fast")

        try:
            result = (
                await func(*args, **kwargs)
                if asyncio.iscoroutinefunction(func)
                else func(*args, **kwargs)
            )
            await self._on_success()
            return result

        except self.expected_exception as e:
            await self._on_failure()
            raise e

    async def _on_success(self):
        """Handle successful call"""
        async with self._lock:
            self.failure_count = 0
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                logger.info("Circuit breaker reset to CLOSED state")

    async def _on_failure(self):
        """Handle failed call"""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(
                    f"Circuit breaker OPENED after {self.failure_count} failures"
                )

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        return (time.time() - self.last_failure_time) >= self.timeout


class EventBus:
    """
    Event-driven communication system for microservices
    Implements publish-subscribe pattern for loose coupling
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._event_history: List[Dict] = []
        self._max_history = 1000
        self._lock = asyncio.Lock()

    async def subscribe(self, event_type: str, handler: Callable):
        """Subscribe to an event type"""
        async with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []

            self._subscribers[event_type].append(handler)
            logger.info(f"Subscribed to event type: {event_type}")

    async def unsubscribe(self, event_type: str, handler: Callable):
        """Unsubscribe from an event type"""
        async with self._lock:
            if event_type in self._subscribers:
                try:
                    self._subscribers[event_type].remove(handler)
                    if not self._subscribers[event_type]:
                        del self._subscribers[event_type]
                except ValueError:
                    logger.debug(
                        "Handler already removed for event type %s", event_type
                    )

    async def publish(
        self, event_type: str, data: Any, metadata: Optional[Dict] = None
    ):
        """Publish an event to all subscribers"""
        event = {
            "type": event_type,
            "data": data,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
            "event_id": f"{event_type}_{int(time.time()*1000)}",
        }

        # Store in history
        async with self._lock:
            self._event_history.append(event)
            if len(self._event_history) > self._max_history:
                self._event_history.pop(0)

        # Notify subscribers
        if event_type in self._subscribers:
            tasks = []
            for handler in self._subscribers[event_type]:
                if asyncio.iscoroutinefunction(handler):
                    tasks.append(asyncio.create_task(handler(event)))
                else:
                    # Run sync handlers in thread pool
                    tasks.append(asyncio.create_task(asyncio.to_thread(handler, event)))

            if tasks:
                # Execute all handlers concurrently
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Log any errors
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(f"Event handler error for {event_type}: {result}")

        logger.debug(f"Published event: {event_type}")
        return event["event_id"]


class APIGateway:
    """
    API Gateway for microservices routing and load balancing
    Provides centralized request routing, authentication, and monitoring
    """

    def __init__(self, service_registry: ServiceRegistry):
        self.service_registry = service_registry
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.request_count = 0
        self.error_count = 0

    async def route_request(
        self,
        service_name: str,
        path: str,
        method: str = "GET",
        data: Any = None,
        headers: Optional[Dict] = None,
    ) -> Dict:
        """Route a request to appropriate service instance"""
        self.request_count += 1

        # Get service instance
        instance = self.service_registry.get_service_instance(service_name)
        if not instance:
            self.error_count += 1
            raise Exception(
                f"No healthy instances available for service: {service_name}"
            )

        # Get or create circuit breaker for this service
        circuit_breaker = self._get_circuit_breaker(service_name)

        try:
            # Route through circuit breaker
            result = await circuit_breaker.call(
                self._make_request, instance, path, method, data, headers
            )

            # Update metrics
            instance.metrics.request_count += 1
            return result

        except Exception as e:
            instance.metrics.error_count += 1
            self.error_count += 1
            raise e

    def _get_circuit_breaker(self, service_name: str) -> CircuitBreaker:
        """Get or create circuit breaker for service"""
        if service_name not in self.circuit_breakers:
            self.circuit_breakers[service_name] = CircuitBreaker(
                failure_threshold=3, timeout=30
            )
        return self.circuit_breakers[service_name]

    async def _make_request(
        self,
        instance: ServiceInstance,
        path: str,
        method: str,
        data: Any,
        headers: Optional[Dict],
    ) -> Dict:
        """Make HTTP request to service instance"""
        url = f"{instance.base_url}{path}"

        async with aiohttp.ClientSession() as session:
            kwargs = {
                "url": url,
                "headers": headers,
                "timeout": aiohttp.ClientTimeout(total=10),
            }

            if data:
                if isinstance(data, dict):
                    kwargs["json"] = data
                else:
                    kwargs["data"] = data

            async with getattr(session, method.lower())(**kwargs) as response:
                if response.content_type == "application/json":
                    return await response.json()
                else:
                    return {"status": response.status, "text": await response.text()}


# Novel Engine Service Implementations


class CharacterService:
    """Microservice for character management"""

    def __init__(self, service_registry: ServiceRegistry, event_bus: EventBus):
        self.service_registry = service_registry
        self.event_bus = event_bus
        self.characters = {}

    async def create_character(self, character_data: Dict) -> Dict:
        """Create a new character"""
        character_id = f"char_{len(self.characters) + 1}"
        character = {
            "id": character_id,
            "created_at": datetime.now().isoformat(),
            **character_data,
        }

        self.characters[character_id] = character

        # Publish event
        await self.event_bus.publish(
            "character.created",
            {"character_id": character_id, "character_data": character},
        )

        return character

    async def get_character(self, character_id: str) -> Optional[Dict]:
        """Get character by ID"""
        return self.characters.get(character_id)


class StoryService:
    """Microservice for story generation and management"""

    def __init__(self, service_registry: ServiceRegistry, event_bus: EventBus):
        self.service_registry = service_registry
        self.event_bus = event_bus
        self.stories = {}

    async def generate_story(self, characters: List[str], scenario: str) -> Dict:
        """Generate a new story"""
        story_id = f"story_{len(self.stories) + 1}"
        story = {
            "id": story_id,
            "characters": characters,
            "scenario": scenario,
            "created_at": datetime.now().isoformat(),
            "status": "generating",
        }

        self.stories[story_id] = story

        # Publish event
        await self.event_bus.publish(
            "story.generation_started",
            {"story_id": story_id, "characters": characters, "scenario": scenario},
        )

        return story


# Example usage and testing
async def main():
    """Demonstrate microservices architecture patterns"""
    logger.info("Starting Novel Engine Microservices Architecture Demo")

    # Initialize components
    service_registry = ServiceRegistry()
    event_bus = EventBus()
    APIGateway(service_registry)

    # Register services
    character_service_instance = ServiceInstance(
        service_name="character-service",
        instance_id="char-001",
        host="localhost",
        port=8001,
    )

    story_service_instance = ServiceInstance(
        service_name="story-service",
        instance_id="story-001",
        host="localhost",
        port=8002,
    )

    await service_registry.register_service(character_service_instance)
    await service_registry.register_service(story_service_instance)

    # Initialize service implementations
    character_service = CharacterService(service_registry, event_bus)
    story_service = StoryService(service_registry, event_bus)

    # Subscribe to events
    async def on_character_created(event):
        logger.info(
            f"Character created event received: {event['data']['character_id']}"
        )

    await event_bus.subscribe("character.created", on_character_created)

    # Demo operations
    logger.info("Creating character...")
    character = await character_service.create_character(
        {"name": "Marcus the Brave", "faction": "Imperial Guard", "role": "Sergeant"}
    )

    logger.info("Generating story...")
    await story_service.generate_story(
        characters=[character["id"]], scenario="Defense of Hive City"
    )

    # Display service registry status
    logger.info(f"Registered services: {len(service_registry._services)}")
    for service_name, instances in service_registry._services.items():
        logger.info(f"  {service_name}: {len(instances)} instances")

    logger.info("Microservices architecture demonstration complete")


if __name__ == "__main__":
    asyncio.run(main())
