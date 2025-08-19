#!/usr/bin/env python3
"""
Enterprise CQRS Command Bus Implementation

This module provides a production-ready command bus for handling write operations
in a CQRS architecture, with support for:
- Command validation and authorization
- Event sourcing integration
- Saga pattern for complex workflows
- Circuit breaker and retry mechanisms
- Audit logging and compliance
"""

import asyncio
import logging
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Type, TypeVar, Generic, Union
from enum import Enum
from uuid import uuid4
from abc import ABC, abstractmethod

from ..events.event_bus import EventBus, Event, EventPriority
from ..events.event_registry import EventType

logger = logging.getLogger(__name__)

T = TypeVar('T')

class CommandStatus(Enum):
    """Command execution status."""
    CREATED = "created"
    VALIDATED = "validated"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"

class CommandType(Enum):
    """Standard command types in the Novel Engine."""
    
    # Character Commands
    CREATE_CHARACTER = "create_character"
    UPDATE_CHARACTER = "update_character"
    DELETE_CHARACTER = "delete_character"
    CHANGE_CHARACTER_STATE = "change_character_state"
    ADD_CHARACTER_MEMORY = "add_character_memory"
    UPDATE_CHARACTER_RELATIONSHIP = "update_character_relationship"
    
    # Story Commands
    START_STORY = "start_story"
    UPDATE_STORY = "update_story"
    COMPLETE_STORY = "complete_story"
    CREATE_STORY_BRANCH = "create_story_branch"
    MAKE_STORY_CHOICE = "make_story_choice"
    
    # Interaction Commands
    START_INTERACTION = "start_interaction"
    EXECUTE_DIALOGUE = "execute_dialogue"
    PERFORM_COMBAT_ACTION = "perform_combat_action"
    EXECUTE_TRADE = "execute_trade"
    
    # Equipment Commands
    ACQUIRE_EQUIPMENT = "acquire_equipment"
    USE_EQUIPMENT = "use_equipment"
    REPAIR_EQUIPMENT = "repair_equipment"
    TRANSFER_EQUIPMENT = "transfer_equipment"
    
    # System Commands
    REGISTER_AGENT = "register_agent"
    DEREGISTER_AGENT = "deregister_agent"
    BACKUP_SYSTEM = "backup_system"
    RESTORE_SYSTEM = "restore_system"

@dataclass
class CommandResult:
    """Result of command execution."""
    success: bool
    command_id: str
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    events_generated: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0
    compensation_commands: List['Command'] = field(default_factory=list)

@dataclass
class Command:
    """
    Base command class for CQRS operations.
    
    Represents an intention to change system state.
    """
    command_id: str = field(default_factory=lambda: str(uuid4()))
    command_type: Union[CommandType, str] = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    status: CommandStatus = CommandStatus.CREATED
    version: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 30
    retry_count: int = 0
    max_retries: int = 3
    idempotency_key: Optional[str] = None
    authorization_context: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate command structure."""
        if not self.command_type:
            raise ValueError("Command type is required")
        if not self.source:
            raise ValueError("Command source is required")
        
        # Generate correlation ID if not provided
        if not self.correlation_id:
            self.correlation_id = str(uuid4())
        
        # Generate idempotency key if not provided
        if not self.idempotency_key:
            self.idempotency_key = f"{self.command_type}_{self.correlation_id}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize command to dictionary."""
        return {
            'command_id': self.command_id,
            'command_type': self.command_type.value if isinstance(self.command_type, CommandType) else self.command_type,
            'payload': self.payload,
            'source': self.source,
            'user_id': self.user_id,
            'correlation_id': self.correlation_id,
            'causation_id': self.causation_id,
            'timestamp': self.timestamp.isoformat(),
            'status': self.status.value,
            'version': self.version,
            'metadata': self.metadata,
            'timeout_seconds': self.timeout_seconds,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'idempotency_key': self.idempotency_key,
            'authorization_context': self.authorization_context
        }

class CommandHandler(ABC, Generic[T]):
    """Abstract base class for command handlers."""
    
    @abstractmethod
    async def handle(self, command: T) -> CommandResult:
        """
        Handle a command.
        
        Args:
            command: Command to handle
            
        Returns:
            CommandResult with execution outcome
        """
        pass
    
    @property
    @abstractmethod
    def handled_command_types(self) -> List[Union[CommandType, str]]:
        """List of command types this handler can process."""
        pass
    
    @property
    def handler_id(self) -> str:
        """Unique identifier for this handler."""
        return f"{self.__class__.__module__}.{self.__class__.__name__}"
    
    async def validate(self, command: T) -> bool:
        """
        Validate command before execution.
        
        Args:
            command: Command to validate
            
        Returns:
            True if valid, False otherwise
        """
        return True
    
    async def authorize(self, command: T) -> bool:
        """
        Authorize command execution.
        
        Args:
            command: Command to authorize
            
        Returns:
            True if authorized, False otherwise
        """
        return True
    
    async def compensate(self, command: T, original_result: CommandResult) -> CommandResult:
        """
        Compensate for a command (undo its effects).
        
        Args:
            command: Original command to compensate
            original_result: Result of original command execution
            
        Returns:
            CommandResult of compensation
        """
        return CommandResult(
            success=True,
            command_id=command.command_id,
            result_data={"compensation": "not_implemented"}
        )

class CommandValidationError(Exception):
    """Raised when command validation fails."""
    pass

class CommandAuthorizationError(Exception):
    """Raised when command authorization fails."""
    pass

class CommandExecutionError(Exception):
    """Raised when command execution fails."""
    pass

@dataclass
class CommandBusConfig:
    """Configuration for the command bus."""
    max_concurrent_commands: int = 50
    enable_event_sourcing: bool = True
    enable_audit_log: bool = True
    enable_idempotency: bool = True
    enable_saga_support: bool = True
    default_timeout: int = 30
    circuit_breaker_enabled: bool = True
    retry_enabled: bool = True

class IdempotencyManager:
    """Manages command idempotency to prevent duplicate execution."""
    
    def __init__(self):
        self._executed_commands: Dict[str, CommandResult] = {}
        self._command_timestamps: Dict[str, datetime] = {}
    
    async def is_duplicate(self, command: Command) -> bool:
        """Check if command has already been executed."""
        if not command.idempotency_key:
            return False
        
        return command.idempotency_key in self._executed_commands
    
    async def get_existing_result(self, command: Command) -> Optional[CommandResult]:
        """Get result of previously executed command."""
        if command.idempotency_key:
            return self._executed_commands.get(command.idempotency_key)
        return None
    
    async def record_execution(self, command: Command, result: CommandResult):
        """Record command execution for idempotency checking."""
        if command.idempotency_key:
            self._executed_commands[command.idempotency_key] = result
            self._command_timestamps[command.idempotency_key] = datetime.now()
    
    async def cleanup_old_records(self, max_age_hours: int = 24):
        """Clean up old idempotency records."""
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        
        expired_keys = [
            key for key, timestamp in self._command_timestamps.items()
            if timestamp.timestamp() < cutoff_time
        ]
        
        for key in expired_keys:
            self._executed_commands.pop(key, None)
            self._command_timestamps.pop(key, None)

class SagaManager:
    """Manages saga pattern for complex multi-command workflows."""
    
    def __init__(self):
        self._active_sagas: Dict[str, List[Command]] = {}
        self._saga_results: Dict[str, List[CommandResult]] = {}
    
    async def start_saga(self, saga_id: str, commands: List[Command]):
        """Start a new saga with a series of commands."""
        self._active_sagas[saga_id] = commands
        self._saga_results[saga_id] = []
        logger.info(f"Started saga {saga_id} with {len(commands)} commands")
    
    async def record_command_result(self, saga_id: str, result: CommandResult):
        """Record the result of a command in a saga."""
        if saga_id in self._saga_results:
            self._saga_results[saga_id].append(result)
    
    async def should_compensate(self, saga_id: str) -> bool:
        """Check if saga should trigger compensation."""
        if saga_id not in self._saga_results:
            return False
        
        results = self._saga_results[saga_id]
        return any(not result.success for result in results)
    
    async def get_compensation_commands(self, saga_id: str) -> List[Command]:
        """Get compensation commands for a failed saga."""
        if saga_id not in self._saga_results:
            return []
        
        compensation_commands = []
        results = self._saga_results[saga_id]
        
        # Compensate in reverse order
        for result in reversed(results):
            if result.success and result.compensation_commands:
                compensation_commands.extend(result.compensation_commands)
        
        return compensation_commands

class CommandBus:
    """
    Enterprise-grade command bus for CQRS architecture.
    
    Features:
    - Command validation and authorization
    - Event sourcing integration
    - Saga pattern support
    - Idempotency handling
    - Circuit breaker protection
    - Comprehensive audit logging
    """
    
    def __init__(self, event_bus: EventBus, config: Optional[CommandBusConfig] = None):
        self.config = config or CommandBusConfig()
        self.event_bus = event_bus
        self._handlers: Dict[str, CommandHandler] = {}
        self._processing_semaphore = asyncio.Semaphore(self.config.max_concurrent_commands)
        
        self.idempotency_manager = IdempotencyManager() if self.config.enable_idempotency else None
        self.saga_manager = SagaManager() if self.config.enable_saga_support else None
        
        self._command_history: List[Command] = []
        self._metrics = {
            'commands_processed': 0,
            'commands_failed': 0,
            'average_execution_time': 0.0,
            'start_time': time.time()
        }
        
        logger.info("CommandBus initialized with enterprise configuration")
    
    def register_handler(self, handler: CommandHandler):
        """Register a command handler."""
        for command_type in handler.handled_command_types:
            command_type_str = command_type.value if isinstance(command_type, CommandType) else command_type
            self._handlers[command_type_str] = handler
        
        logger.info(f"Registered handler {handler.handler_id} for command types: {handler.handled_command_types}")
    
    def unregister_handler(self, handler: CommandHandler):
        """Unregister a command handler."""
        for command_type in handler.handled_command_types:
            command_type_str = command_type.value if isinstance(command_type, CommandType) else command_type
            if command_type_str in self._handlers and self._handlers[command_type_str] == handler:
                del self._handlers[command_type_str]
        
        logger.info(f"Unregistered handler {handler.handler_id}")
    
    async def execute(self, command: Command) -> CommandResult:
        """
        Execute a command through the command bus.
        
        Args:
            command: Command to execute
            
        Returns:
            CommandResult with execution outcome
        """
        async with self._processing_semaphore:
            start_time = time.time()
            
            try:
                # Check idempotency
                if self.idempotency_manager and await self.idempotency_manager.is_duplicate(command):
                    existing_result = await self.idempotency_manager.get_existing_result(command)
                    if existing_result:
                        logger.info(f"Returning cached result for idempotent command {command.command_id}")
                        return existing_result
                
                # Get handler
                command_type_str = command.command_type.value if isinstance(command.command_type, CommandType) else command.command_type
                handler = self._handlers.get(command_type_str)
                
                if not handler:
                    raise CommandExecutionError(f"No handler registered for command type: {command_type_str}")
                
                # Validate command
                command.status = CommandStatus.VALIDATED
                if not await handler.validate(command):
                    raise CommandValidationError(f"Command validation failed: {command.command_id}")
                
                # Authorize command
                if not await handler.authorize(command):
                    raise CommandAuthorizationError(f"Command authorization failed: {command.command_id}")
                
                # Execute command
                command.status = CommandStatus.EXECUTING
                result = await asyncio.wait_for(
                    handler.handle(command),
                    timeout=command.timeout_seconds
                )
                
                command.status = CommandStatus.COMPLETED
                result.execution_time_ms = (time.time() - start_time) * 1000
                
                # Record for idempotency
                if self.idempotency_manager:
                    await self.idempotency_manager.record_execution(command, result)
                
                # Generate events if successful
                if result.success and self.config.enable_event_sourcing:
                    await self._generate_command_events(command, result)
                
                # Store in command history for audit
                if self.config.enable_audit_log:
                    self._command_history.append(command)
                
                # Update metrics
                self._update_metrics(result)
                
                logger.debug(f"Command {command.command_id} executed successfully in {result.execution_time_ms}ms")
                return result
                
            except asyncio.TimeoutError:
                command.status = CommandStatus.FAILED
                error_msg = f"Command {command.command_id} timed out after {command.timeout_seconds} seconds"
                logger.error(error_msg)
                
                result = CommandResult(
                    success=False,
                    command_id=command.command_id,
                    error_message=error_msg,
                    execution_time_ms=(time.time() - start_time) * 1000
                )
                
                self._update_metrics(result)
                return result
                
            except Exception as e:
                command.status = CommandStatus.FAILED
                error_msg = f"Command execution failed: {str(e)}"
                logger.error(f"Command {command.command_id} failed: {error_msg}")
                
                result = CommandResult(
                    success=False,
                    command_id=command.command_id,
                    error_message=error_msg,
                    execution_time_ms=(time.time() - start_time) * 1000
                )
                
                self._update_metrics(result)
                
                # Handle retry logic
                if self.config.retry_enabled and command.retry_count < command.max_retries:
                    await self._schedule_retry(command)
                
                return result
    
    async def execute_saga(self, saga_id: str, commands: List[Command]) -> List[CommandResult]:
        """
        Execute a saga (series of related commands with compensation).
        
        Args:
            saga_id: Unique identifier for the saga
            commands: List of commands to execute in order
            
        Returns:
            List of CommandResults
        """
        if not self.saga_manager:
            raise RuntimeError("Saga support is not enabled")
        
        await self.saga_manager.start_saga(saga_id, commands)
        results = []
        
        try:
            for command in commands:
                result = await self.execute(command)
                results.append(result)
                await self.saga_manager.record_command_result(saga_id, result)
                
                # If command failed, trigger compensation
                if not result.success:
                    logger.warning(f"Saga {saga_id} failed at command {command.command_id}, starting compensation")
                    await self._compensate_saga(saga_id)
                    break
            
            logger.info(f"Saga {saga_id} completed with {len(results)} commands")
            return results
            
        except Exception as e:
            logger.error(f"Saga {saga_id} failed with exception: {e}")
            await self._compensate_saga(saga_id)
            raise
    
    async def _compensate_saga(self, saga_id: str):
        """Execute compensation commands for a failed saga."""
        if not self.saga_manager:
            return
        
        compensation_commands = await self.saga_manager.get_compensation_commands(saga_id)
        
        for compensation_command in compensation_commands:
            try:
                await self.execute(compensation_command)
                logger.info(f"Executed compensation command for saga {saga_id}")
            except Exception as e:
                logger.error(f"Compensation command failed for saga {saga_id}: {e}")
    
    async def _generate_command_events(self, command: Command, result: CommandResult):
        """Generate events based on command execution."""
        # Create command executed event
        event = Event(
            event_type=f"command.{command.command_type.value if isinstance(command.command_type, CommandType) else command.command_type}.executed",
            payload={
                'command_id': command.command_id,
                'command_type': command.command_type.value if isinstance(command.command_type, CommandType) else command.command_type,
                'success': result.success,
                'execution_time_ms': result.execution_time_ms,
                'result_data': result.result_data
            },
            source="command_bus",
            correlation_id=command.correlation_id,
            causation_id=command.command_id,
            priority=EventPriority.NORMAL
        )
        
        event_id = await self.event_bus.publish(event)
        result.events_generated.append(event_id)
    
    async def _schedule_retry(self, command: Command):
        """Schedule command retry with exponential backoff."""
        command.retry_count += 1
        delay = min(2 ** command.retry_count, 60)  # Max 60 seconds
        
        logger.info(f"Scheduling retry for command {command.command_id} in {delay} seconds (attempt {command.retry_count})")
        
        async def retry_after_delay():
            await asyncio.sleep(delay)
            await self.execute(command)
        
        asyncio.create_task(retry_after_delay())
    
    def _update_metrics(self, result: CommandResult):
        """Update command bus metrics."""
        self._metrics['commands_processed'] += 1
        
        if not result.success:
            self._metrics['commands_failed'] += 1
        
        # Update average execution time
        current_avg = self._metrics['average_execution_time']
        total_commands = self._metrics['commands_processed']
        self._metrics['average_execution_time'] = (
            (current_avg * (total_commands - 1) + result.execution_time_ms) / total_commands
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get command bus metrics."""
        uptime = time.time() - self._metrics['start_time']
        
        return {
            'commands_processed': self._metrics['commands_processed'],
            'commands_failed': self._metrics['commands_failed'],
            'success_rate': (self._metrics['commands_processed'] - self._metrics['commands_failed']) / max(self._metrics['commands_processed'], 1),
            'failure_rate': self._metrics['commands_failed'] / max(self._metrics['commands_processed'], 1),
            'average_execution_time_ms': self._metrics['average_execution_time'],
            'commands_per_second': self._metrics['commands_processed'] / max(uptime, 1),
            'uptime_seconds': uptime,
            'active_handlers': len(self._handlers),
            'audit_log_size': len(self._command_history)
        }
    
    def get_command_history(self, limit: int = 100) -> List[Command]:
        """Get recent command history for audit purposes."""
        return self._command_history[-limit:]
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the command bus."""
        health = {
            'status': 'healthy',
            'handlers_registered': len(self._handlers),
            'idempotency_enabled': self.idempotency_manager is not None,
            'saga_support_enabled': self.saga_manager is not None,
            'event_bus_healthy': False
        }
        
        # Check event bus health
        try:
            event_bus_health = await self.event_bus.health_check()
            health['event_bus_healthy'] = event_bus_health.get('status') == 'healthy'
        except Exception:
            health['status'] = 'degraded'
            health['event_bus_healthy'] = False
        
        health['metrics'] = self.get_metrics()
        return health