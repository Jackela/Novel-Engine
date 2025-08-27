#!/usr/bin/env python3
"""
World Context Database Models

SQLAlchemy models for persisting World domain entities.
These models map domain aggregates to database tables.
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, String, DateTime, Integer, Text, JSON, Index, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core_platform.persistence.models import FullAuditModel


class WorldStateModel(FullAuditModel):
    """
    SQLAlchemy model for WorldState aggregate persistence.
    
    This model provides the persistence layer for WorldState aggregates,
    mapping domain objects to database tables with proper indexing,
    constraints, and performance optimizations.
    """
    
    __tablename__ = 'world_states'
    
    # Core world properties
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default='initializing', index=True)
    
    # World time and versioning
    world_time = Column(DateTime(timezone=True), nullable=False, default=func.now())
    version = Column(Integer, nullable=False, default=1, index=True)
    
    # Configuration
    max_entities = Column(Integer, nullable=False, default=10000)
    spatial_grid_size = Column(Float, nullable=False, default=100.0)
    
    # JSON storage for complex data
    entities = Column(JSON, nullable=False, default=dict)  # Stores all entities
    environment = Column(JSON, nullable=False, default=dict)  # Environment properties
    spatial_index = Column(JSON, nullable=False, default=dict)  # Spatial grid index
    metadata = Column(JSON, nullable=False, default=dict)  # Additional metadata
    
    # Performance indexes
    __table_args__ = (
        Index('idx_world_states_name_status', 'name', 'status'),
        Index('idx_world_states_world_time', 'world_time'),
        Index('idx_world_states_version', 'version'),
        Index('idx_world_states_created_at', 'created_at'),
        Index('idx_world_states_updated_at', 'updated_at'),
        Index('idx_world_states_is_deleted', 'is_deleted'),
    )
    
    def to_domain_aggregate(self):
        """
        Convert database model to domain aggregate.
        
        Returns:
            WorldState domain aggregate
        """
        from ...domain.aggregates.world_state import WorldState, WorldStatus, EntityType, WorldEntity
        from ...domain.value_objects.coordinates import Coordinates
        
        # Parse entities from JSON storage
        domain_entities = {}
        if self.entities:
            for entity_id, entity_data in self.entities.items():
                if entity_data:  # Skip None/empty entities
                    coordinates = Coordinates.from_dict(entity_data['coordinates'])
                    entity_type = EntityType(entity_data['entity_type'])
                    
                    world_entity = WorldEntity(
                        id=entity_data['id'],
                        entity_type=entity_type,
                        name=entity_data['name'],
                        coordinates=coordinates,
                        properties=entity_data.get('properties', {}),
                        metadata=entity_data.get('metadata', {}),
                        created_at=datetime.fromisoformat(entity_data['created_at']) if entity_data.get('created_at') else datetime.now(),
                        updated_at=datetime.fromisoformat(entity_data['updated_at']) if entity_data.get('updated_at') else datetime.now()
                    )
                    domain_entities[entity_id] = world_entity
        
        # Create domain aggregate
        world_state = WorldState(
            id=str(self.id),
            name=self.name,
            description=self.description,
            status=WorldStatus(self.status),
            world_time=self.world_time,
            entities=domain_entities,
            environment=self.environment or {},
            spatial_index=self.spatial_index or {},
            metadata=self.metadata or {},
            max_entities=self.max_entities,
            spatial_grid_size=self.spatial_grid_size,
            created_at=self.created_at,
            updated_at=self.updated_at,
            version=self.version
        )
        
        return world_state
    
    @classmethod
    def from_domain_aggregate(cls, world_state):
        """
        Create database model from domain aggregate.
        
        Args:
            world_state: WorldState domain aggregate
            
        Returns:
            WorldStateModel instance
        """
        # Serialize entities to JSON
        serialized_entities = {}
        for entity_id, entity in world_state.entities.items():
            serialized_entities[entity_id] = entity.to_dict()
        
        return cls(
            id=uuid.UUID(world_state.id) if isinstance(world_state.id, str) else world_state.id,
            name=world_state.name,
            description=world_state.description,
            status=world_state.status.value,
            world_time=world_state.world_time,
            entities=serialized_entities,
            environment=world_state.environment,
            spatial_index=world_state.spatial_index,
            metadata=world_state.metadata,
            max_entities=world_state.max_entities,
            spatial_grid_size=world_state.spatial_grid_size,
            version=world_state.version,
            created_at=world_state.created_at,
            updated_at=world_state.updated_at
        )
    
    def update_from_domain_aggregate(self, world_state):
        """
        Update database model from domain aggregate.
        
        Args:
            world_state: WorldState domain aggregate
        """
        # Serialize entities to JSON
        serialized_entities = {}
        for entity_id, entity in world_state.entities.items():
            serialized_entities[entity_id] = entity.to_dict()
        
        self.name = world_state.name
        self.description = world_state.description
        self.status = world_state.status.value
        self.world_time = world_state.world_time
        self.entities = serialized_entities
        self.environment = world_state.environment
        self.spatial_index = world_state.spatial_index
        self.metadata = world_state.metadata
        self.max_entities = world_state.max_entities
        self.spatial_grid_size = world_state.spatial_grid_size
        self.version = world_state.version
        self.updated_at = world_state.updated_at
    
    def validate(self) -> List[str]:
        """Validate the model instance."""
        errors = super().validate()
        
        if not self.name or not self.name.strip():
            errors.append("World name cannot be empty")
        
        if self.version < 1:
            errors.append("World version must be positive")
        
        if self.max_entities < 1:
            errors.append("Max entities must be positive")
        
        if self.spatial_grid_size <= 0:
            errors.append("Spatial grid size must be positive")
        
        # Validate JSON fields are valid JSON
        try:
            if self.entities and not isinstance(self.entities, dict):
                errors.append("Entities must be a valid JSON object")
        except (ValueError, TypeError):
            errors.append("Entities contains invalid JSON")
        
        try:
            if self.environment and not isinstance(self.environment, dict):
                errors.append("Environment must be a valid JSON object")
        except (ValueError, TypeError):
            errors.append("Environment contains invalid JSON")
        
        return errors
    
    def get_entity_count(self) -> int:
        """Get the number of entities in this world."""
        return len(self.entities) if self.entities else 0
    
    def get_entity_types_summary(self) -> Dict[str, int]:
        """Get summary of entity types and counts."""
        summary = {}
        if self.entities:
            for entity_data in self.entities.values():
                if entity_data and 'entity_type' in entity_data:
                    entity_type = entity_data['entity_type']
                    summary[entity_type] = summary.get(entity_type, 0) + 1
        return summary
    
    def __repr__(self) -> str:
        return f"<WorldStateModel(id={self.id}, name='{self.name}', status='{self.status}', entities={self.get_entity_count()})>"


class WorldStateSnapshotModel(FullAuditModel):
    """
    SQLAlchemy model for WorldState snapshots.
    
    This model stores point-in-time snapshots of world states
    for backup, recovery, and historical analysis purposes.
    """
    
    __tablename__ = 'world_state_snapshots'
    
    # Reference to parent world state
    world_state_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Snapshot metadata
    snapshot_name = Column(String(255), nullable=False)
    snapshot_reason = Column(Text, nullable=False)
    world_version_at_snapshot = Column(Integer, nullable=False)
    
    # Snapshot data (complete world state at time of snapshot)
    snapshot_data = Column(JSON, nullable=False)
    
    # Snapshot statistics
    entity_count = Column(Integer, nullable=False, default=0)
    data_size_bytes = Column(Integer, nullable=False, default=0)
    
    # Performance indexes
    __table_args__ = (
        Index('idx_world_snapshots_world_id', 'world_state_id'),
        Index('idx_world_snapshots_name', 'snapshot_name'),
        Index('idx_world_snapshots_created_at', 'created_at'),
        Index('idx_world_snapshots_version', 'world_version_at_snapshot'),
    )
    
    def validate(self) -> List[str]:
        """Validate the snapshot model."""
        errors = super().validate()
        
        if not self.world_state_id:
            errors.append("World state ID is required")
        
        if not self.snapshot_name or not self.snapshot_name.strip():
            errors.append("Snapshot name cannot be empty")
        
        if not self.snapshot_reason or not self.snapshot_reason.strip():
            errors.append("Snapshot reason cannot be empty")
        
        if self.world_version_at_snapshot < 1:
            errors.append("World version at snapshot must be positive")
        
        if not self.snapshot_data:
            errors.append("Snapshot data is required")
        
        return errors
    
    def __repr__(self) -> str:
        return f"<WorldStateSnapshotModel(id={self.id}, world_id={self.world_state_id}, name='{self.snapshot_name}')>"


class WorldStateVersionModel(FullAuditModel):
    """
    SQLAlchemy model for WorldState version history.
    
    This model tracks version history for optimistic concurrency control
    and provides the ability to query historical versions of world states.
    """
    
    __tablename__ = 'world_state_versions'
    
    # Reference to parent world state
    world_state_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Version information
    version_number = Column(Integer, nullable=False, index=True)
    previous_version = Column(Integer, nullable=True)
    
    # Version metadata
    change_reason = Column(Text, nullable=True)
    change_summary = Column(String(500), nullable=True)
    changed_by = Column(UUID(as_uuid=True), nullable=True)
    
    # Version data (complete world state at this version)
    version_data = Column(JSON, nullable=False)
    
    # Change statistics
    entities_added = Column(Integer, nullable=False, default=0)
    entities_removed = Column(Integer, nullable=False, default=0)
    entities_modified = Column(Integer, nullable=False, default=0)
    environment_changed = Column(Boolean, nullable=False, default=False)
    
    # Performance indexes
    __table_args__ = (
        Index('idx_world_versions_world_id_version', 'world_state_id', 'version_number'),
        Index('idx_world_versions_created_at', 'created_at'),
        Index('idx_world_versions_changed_by', 'changed_by'),
    )
    
    def validate(self) -> List[str]:
        """Validate the version model."""
        errors = super().validate()
        
        if not self.world_state_id:
            errors.append("World state ID is required")
        
        if self.version_number < 1:
            errors.append("Version number must be positive")
        
        if self.previous_version is not None and self.previous_version >= self.version_number:
            errors.append("Previous version must be less than current version")
        
        if not self.version_data:
            errors.append("Version data is required")
        
        return errors
    
    def __repr__(self) -> str:
        return f"<WorldStateVersionModel(id={self.id}, world_id={self.world_state_id}, version={self.version_number})>"