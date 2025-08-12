#!/usr/bin/env python3
"""
Novel Engine State Hashing System
==================================

Comprehensive state hashing system for consistency validation,
caching optimization, and state change detection.

This system provides:
1. Deterministic hash generation for all game state components
2. Incremental hash updates for performance optimization
3. State consistency validation across simulation turns
4. Cache key generation for semantic caching
5. Change detection for efficient delta processing

Architecture Reference:
- docs/IMPLEMENTATION.md - Caching and performance systems
- Work Order PR-08.1 - State Hashing System Implementation

Development Phase: Work Order PR-08.1 - State Hashing Implementation
"""

import hashlib
import json
import time
from typing import Dict, List, Optional, Any, Union, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import logging

# Import Novel Engine types
try:
    from src.shared_types import (
        CharacterData, CharacterStats, CharacterResources, ResourceValue,
        Position, ActionType, ProposedAction, ActionParameters,
        ValidationStatus, IronLawsReport
    )
    SHARED_TYPES_AVAILABLE = True
except ImportError:
    SHARED_TYPES_AVAILABLE = False
    logging.warning("Shared types not available - using fallback hashing")

logger = logging.getLogger(__name__)

@dataclass
class StateHash:
    """Represents a computed state hash with metadata."""
    
    hash_value: str
    timestamp: datetime
    component_type: str
    component_id: Optional[str] = None
    version: int = 1
    dependencies: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "hash_value": self.hash_value,
            "timestamp": self.timestamp.isoformat(),
            "component_type": self.component_type,
            "component_id": self.component_id,
            "version": self.version,
            "dependencies": self.dependencies
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StateHash':
        """Create from dictionary."""
        return cls(
            hash_value=data["hash_value"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            component_type=data["component_type"],
            component_id=data.get("component_id"),
            version=data.get("version", 1),
            dependencies=data.get("dependencies", [])
        )

@dataclass
class HashingConfig:
    """Configuration for state hashing system."""
    
    # Hash algorithm settings
    algorithm: str = "sha256"
    encoding: str = "utf-8"
    
    # Performance settings
    enable_incremental_hashing: bool = True
    cache_intermediate_results: bool = True
    max_cache_size: int = 1000
    
    # Validation settings
    enable_consistency_checking: bool = True
    strict_ordering: bool = True
    include_timestamps: bool = False
    
    # Component-specific settings
    hash_character_positions: bool = True
    hash_resource_values: bool = True
    hash_equipment_order: bool = False
    hash_memory_contents: bool = True
    
    # Debug settings
    enable_debug_logging: bool = False
    save_hash_breakdown: bool = False

class StateHasher:
    """Core state hashing engine for Novel Engine components."""
    
    def __init__(self, config: Optional[HashingConfig] = None):
        """
        Initialize state hasher with configuration.
        
        Args:
            config: Hashing configuration, uses defaults if None
        """
        self.config = config or HashingConfig()
        self.hash_cache: Dict[str, StateHash] = {}
        self.dependency_graph: Dict[str, Set[str]] = {}
        
        # Initialize hash algorithm
        self.hasher_class = getattr(hashlib, self.config.algorithm, hashlib.sha256)
        
        logger.info(f"🔐 StateHasher initialized with {self.config.algorithm} algorithm")
    
    def hash_world_state(self, world_state: Dict[str, Any]) -> StateHash:
        """
        Generate comprehensive hash for world state.
        
        Args:
            world_state: Complete world state dictionary
            
        Returns:
            StateHash with world state hash and metadata
        """
        try:
            # Create ordered, normalized representation
            normalized_state = self._normalize_world_state(world_state)
            
            # Generate hash
            hash_value = self._compute_hash(normalized_state)
            
            # Create dependencies list
            dependencies = self._extract_world_dependencies(world_state)
            
            state_hash = StateHash(
                hash_value=hash_value,
                timestamp=datetime.now(),
                component_type="world_state",
                component_id="global",
                dependencies=dependencies
            )
            
            # Cache result
            if self.config.cache_intermediate_results:
                self._cache_hash("world_state_global", state_hash)
            
            if self.config.enable_debug_logging:
                logger.debug(f"🌍 World state hash: {hash_value[:16]}...")
            
            return state_hash
            
        except Exception as e:
            logger.error(f"❌ World state hashing failed: {e}")
            raise
    
    def hash_character_state(self, character_data: Dict[str, Any]) -> StateHash:
        """
        Generate hash for character state.
        
        Args:
            character_data: Character data dictionary
            
        Returns:
            StateHash with character state hash
        """
        try:
            character_id = character_data.get('character_id', 'unknown')
            
            # Normalize character data based on configuration
            normalized_data = self._normalize_character_data(character_data)
            
            # Generate hash
            hash_value = self._compute_hash(normalized_data)
            
            # Extract dependencies
            dependencies = self._extract_character_dependencies(character_data)
            
            state_hash = StateHash(
                hash_value=hash_value,
                timestamp=datetime.now(),
                component_type="character_state",
                component_id=character_id,
                dependencies=dependencies
            )
            
            # Cache result
            if self.config.cache_intermediate_results:
                self._cache_hash(f"character_{character_id}", state_hash)
            
            if self.config.enable_debug_logging:
                logger.debug(f"👤 Character {character_id} hash: {hash_value[:16]}...")
            
            return state_hash
            
        except Exception as e:
            logger.error(f"❌ Character state hashing failed: {e}")
            raise
    
    def hash_action_sequence(self, actions: List[Dict[str, Any]]) -> StateHash:
        """
        Generate hash for sequence of actions.
        
        Args:
            actions: List of action dictionaries
            
        Returns:
            StateHash with action sequence hash
        """
        try:
            # Normalize action sequence
            normalized_actions = []
            
            for action in actions:
                normalized_action = self._normalize_action(action)
                normalized_actions.append(normalized_action)
            
            # Generate hash from sequence
            if self.config.strict_ordering:
                # Order-dependent hashing
                hash_input = {
                    "actions": normalized_actions,
                    "sequence_length": len(normalized_actions),
                    "ordered": True
                }
            else:
                # Order-independent hashing (sort by action ID)
                sorted_actions = sorted(normalized_actions, 
                                      key=lambda x: x.get('action_id', ''))
                hash_input = {
                    "actions": sorted_actions,
                    "sequence_length": len(normalized_actions),
                    "ordered": False
                }
            
            hash_value = self._compute_hash(hash_input)
            
            # Extract dependencies from all actions
            dependencies = []
            for action in actions:
                action_deps = self._extract_action_dependencies(action)
                dependencies.extend(action_deps)
            
            state_hash = StateHash(
                hash_value=hash_value,
                timestamp=datetime.now(),
                component_type="action_sequence",
                component_id=f"sequence_{len(actions)}",
                dependencies=list(set(dependencies))  # Remove duplicates
            )
            
            if self.config.enable_debug_logging:
                logger.debug(f"⚡ Action sequence hash: {hash_value[:16]}...")
            
            return state_hash
            
        except Exception as e:
            logger.error(f"❌ Action sequence hashing failed: {e}")
            raise
    
    def hash_iron_laws_state(self, iron_laws_report: Dict[str, Any]) -> StateHash:
        """
        Generate hash for Iron Laws validation state.
        
        Args:
            iron_laws_report: Iron Laws report dictionary
            
        Returns:
            StateHash with Iron Laws state hash
        """
        try:
            # Normalize Iron Laws report
            normalized_report = self._normalize_iron_laws_report(iron_laws_report)
            
            hash_value = self._compute_hash(normalized_report)
            
            # Dependencies based on validated actions and characters
            dependencies = []
            if 'validated_actions' in iron_laws_report:
                for action in iron_laws_report['validated_actions']:
                    if 'character_id' in action:
                        dependencies.append(f"character_{action['character_id']}")
                    if 'action_id' in action:
                        dependencies.append(f"action_{action['action_id']}")
            
            state_hash = StateHash(
                hash_value=hash_value,
                timestamp=datetime.now(),
                component_type="iron_laws_state",
                component_id="validation_report",
                dependencies=dependencies
            )
            
            if self.config.enable_debug_logging:
                logger.debug(f"🛡️ Iron Laws hash: {hash_value[:16]}...")
            
            return state_hash
            
        except Exception as e:
            logger.error(f"❌ Iron Laws hashing failed: {e}")
            raise
    
    def compute_composite_hash(self, component_hashes: List[StateHash]) -> StateHash:
        """
        Compute composite hash from multiple component hashes.
        
        Args:
            component_hashes: List of component StateHash objects
            
        Returns:
            StateHash representing the composite state
        """
        try:
            # Sort hashes by component type and ID for consistency
            sorted_hashes = sorted(component_hashes, 
                                 key=lambda h: (h.component_type, h.component_id or ''))
            
            # Create composite hash input
            hash_input = {
                "component_hashes": [h.hash_value for h in sorted_hashes],
                "component_count": len(sorted_hashes),
                "component_types": [h.component_type for h in sorted_hashes]
            }
            
            if not self.config.include_timestamps:
                # For consistency, don't include timestamps in composite
                pass
            else:
                hash_input["latest_timestamp"] = max(h.timestamp for h in sorted_hashes).isoformat()
            
            composite_hash_value = self._compute_hash(hash_input)
            
            # Combine all dependencies
            all_dependencies = []
            for h in component_hashes:
                all_dependencies.extend(h.dependencies)
            
            composite_hash = StateHash(
                hash_value=composite_hash_value,
                timestamp=datetime.now(),
                component_type="composite_state",
                component_id=f"composite_{len(component_hashes)}",
                dependencies=list(set(all_dependencies))
            )
            
            if self.config.enable_debug_logging:
                logger.debug(f"🔗 Composite hash: {composite_hash_value[:16]}...")
            
            return composite_hash
            
        except Exception as e:
            logger.error(f"❌ Composite hashing failed: {e}")
            raise
    
    def validate_state_consistency(self, 
                                 current_hashes: Dict[str, StateHash],
                                 previous_hashes: Dict[str, StateHash]) -> Dict[str, Any]:
        """
        Validate state consistency between hash snapshots.
        
        Args:
            current_hashes: Current state hashes
            previous_hashes: Previous state hashes
            
        Returns:
            Validation report with consistency analysis
        """
        try:
            validation_report = {
                "timestamp": datetime.now().isoformat(),
                "consistency_status": "unknown",
                "changed_components": [],
                "new_components": [],
                "removed_components": [],
                "hash_comparisons": {},
                "dependency_changes": []
            }
            
            # Find component changes
            current_keys = set(current_hashes.keys())
            previous_keys = set(previous_hashes.keys())
            
            validation_report["new_components"] = list(current_keys - previous_keys)
            validation_report["removed_components"] = list(previous_keys - current_keys)
            
            # Compare hash values for common components
            common_keys = current_keys & previous_keys
            
            for key in common_keys:
                current_hash = current_hashes[key]
                previous_hash = previous_hashes[key]
                
                comparison = {
                    "component": key,
                    "hash_changed": current_hash.hash_value != previous_hash.hash_value,
                    "current_hash": current_hash.hash_value,
                    "previous_hash": previous_hash.hash_value,
                    "version_changed": current_hash.version != previous_hash.version
                }
                
                if comparison["hash_changed"]:
                    validation_report["changed_components"].append(key)
                
                # Check dependency changes
                current_deps = set(current_hash.dependencies)
                previous_deps = set(previous_hash.dependencies)
                
                if current_deps != previous_deps:
                    validation_report["dependency_changes"].append({
                        "component": key,
                        "added_dependencies": list(current_deps - previous_deps),
                        "removed_dependencies": list(previous_deps - current_deps)
                    })
                
                validation_report["hash_comparisons"][key] = comparison
            
            # Determine overall consistency status
            has_changes = (len(validation_report["changed_components"]) > 0 or
                          len(validation_report["new_components"]) > 0 or
                          len(validation_report["removed_components"]) > 0)
            
            validation_report["consistency_status"] = "changed" if has_changes else "consistent"
            
            if self.config.enable_debug_logging:
                logger.debug(f"🔍 State consistency: {validation_report['consistency_status']}")
            
            return validation_report
            
        except Exception as e:
            logger.error(f"❌ State consistency validation failed: {e}")
            raise
    
    def get_cache_key(self, component_type: str, component_data: Dict[str, Any]) -> str:
        """
        Generate cache key from component data.
        
        Args:
            component_type: Type of component (character, world, action, etc.)
            component_data: Component data dictionary
            
        Returns:
            Cache key string suitable for semantic caching
        """
        try:
            # Generate hash for the component
            if component_type == "character":
                state_hash = self.hash_character_state(component_data)
            elif component_type == "world":
                state_hash = self.hash_world_state(component_data)
            elif component_type == "action":
                state_hash = self.hash_action_sequence([component_data])
            elif component_type == "iron_laws":
                state_hash = self.hash_iron_laws_state(component_data)
            else:
                # Generic hashing
                normalized_data = self._normalize_generic(component_data)
                hash_value = self._compute_hash(normalized_data)
                state_hash = StateHash(
                    hash_value=hash_value,
                    timestamp=datetime.now(),
                    component_type=component_type
                )
            
            # Create cache key with component type prefix
            cache_key = f"{component_type}:{state_hash.hash_value}"
            
            return cache_key
            
        except Exception as e:
            logger.error(f"❌ Cache key generation failed: {e}")
            raise
    
    def _normalize_world_state(self, world_state: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize world state for consistent hashing."""
        normalized = {}
        
        # Include core world state components
        if 'locations' in world_state:
            normalized['locations'] = self._normalize_locations(world_state['locations'])
        
        if 'objects' in world_state:
            normalized['objects'] = self._normalize_objects(world_state['objects'])
        
        if 'environment' in world_state:
            normalized['environment'] = self._normalize_environment(world_state['environment'])
        
        if 'characters' in world_state:
            # Only include character IDs and positions if configured
            if self.config.hash_character_positions:
                char_positions = {}
                for char_id, char_data in world_state['characters'].items():
                    if 'position' in char_data:
                        char_positions[char_id] = char_data['position']
                normalized['character_positions'] = char_positions
        
        return normalized
    
    def _normalize_character_data(self, character_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize character data for consistent hashing."""
        normalized = {}
        
        # Always include core identity
        if 'character_id' in character_data:
            normalized['character_id'] = character_data['character_id']
        
        if 'name' in character_data:
            normalized['name'] = character_data['name']
        
        # Include stats and resources based on configuration
        if self.config.hash_resource_values:
            if 'stats' in character_data:
                normalized['stats'] = self._normalize_stats(character_data['stats'])
            
            if 'resources' in character_data:
                normalized['resources'] = self._normalize_resources(character_data['resources'])
        
        # Include position if configured
        if self.config.hash_character_positions and 'position' in character_data:
            normalized['position'] = self._normalize_position(character_data['position'])
        
        # Include equipment based on configuration
        if 'equipment' in character_data:
            if self.config.hash_equipment_order:
                normalized['equipment'] = character_data['equipment']
            else:
                # Sort equipment for order-independent hashing
                normalized['equipment'] = sorted(character_data['equipment'])
        
        # Include memory if configured
        if self.config.hash_memory_contents and 'memory' in character_data:
            normalized['memory'] = self._normalize_memory(character_data['memory'])
        
        return normalized
    
    def _normalize_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize action for consistent hashing."""
        normalized = {}
        
        # Include core action components
        for key in ['action_id', 'character_id', 'action_type', 'parameters']:
            if key in action:
                normalized[key] = action[key]
        
        # Normalize parameters if present
        if 'parameters' in normalized and isinstance(normalized['parameters'], dict):
            # Sort parameters for consistency
            normalized['parameters'] = dict(sorted(normalized['parameters'].items()))
        
        return normalized
    
    def _normalize_iron_laws_report(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Iron Laws report for consistent hashing."""
        normalized = {}
        
        # Include validation results
        if 'validation_results' in report:
            normalized['validation_results'] = report['validation_results']
        
        if 'violations_found' in report:
            # Sort violations for consistency
            violations = report['violations_found']
            if isinstance(violations, list):
                normalized['violations_found'] = sorted(violations, 
                                                      key=lambda v: v.get('law_code', ''))
            else:
                normalized['violations_found'] = violations
        
        if 'repair_attempts' in report:
            normalized['repair_attempts'] = report['repair_attempts']
        
        return normalized
    
    def _normalize_stats(self, stats: Any) -> Dict[str, Any]:
        """Normalize character stats for hashing."""
        if SHARED_TYPES_AVAILABLE and hasattr(stats, '__dict__'):
            # Handle Pydantic model
            return dict(sorted(stats.__dict__.items()))
        elif isinstance(stats, dict):
            return dict(sorted(stats.items()))
        else:
            return {"stats_hash": str(hash(str(stats)))}
    
    def _normalize_resources(self, resources: Any) -> Dict[str, Any]:
        """Normalize character resources for hashing."""
        if SHARED_TYPES_AVAILABLE and hasattr(resources, '__dict__'):
            # Handle Pydantic model
            return dict(sorted(resources.__dict__.items()))
        elif isinstance(resources, dict):
            return dict(sorted(resources.items()))
        else:
            return {"resources_hash": str(hash(str(resources)))}
    
    def _normalize_position(self, position: Any) -> Dict[str, Any]:
        """Normalize position for hashing."""
        if SHARED_TYPES_AVAILABLE and hasattr(position, '__dict__'):
            return dict(sorted(position.__dict__.items()))
        elif isinstance(position, dict):
            return dict(sorted(position.items()))
        else:
            return {"position_hash": str(hash(str(position)))}
    
    def _normalize_locations(self, locations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize locations for hashing."""
        normalized = []
        for location in locations:
            norm_loc = dict(sorted(location.items()))
            normalized.append(norm_loc)
        return sorted(normalized, key=lambda x: x.get('id', ''))
    
    def _normalize_objects(self, objects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize objects for hashing."""
        normalized = []
        for obj in objects:
            norm_obj = dict(sorted(obj.items()))
            normalized.append(norm_obj)
        return sorted(normalized, key=lambda x: x.get('id', ''))
    
    def _normalize_environment(self, environment: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize environment for hashing."""
        return dict(sorted(environment.items()))
    
    def _normalize_memory(self, memory: Any) -> Dict[str, Any]:
        """Normalize memory contents for hashing."""
        if isinstance(memory, dict):
            return dict(sorted(memory.items()))
        else:
            return {"memory_hash": str(hash(str(memory)))}
    
    def _normalize_generic(self, data: Any) -> Dict[str, Any]:
        """Generic normalization for unknown data types."""
        if isinstance(data, dict):
            return dict(sorted(data.items()))
        elif isinstance(data, list):
            return {"list_items": sorted([str(item) for item in data])}
        else:
            return {"data_hash": str(hash(str(data)))}
    
    def _compute_hash(self, data: Dict[str, Any]) -> str:
        """Compute hash from normalized data."""
        try:
            # Convert to stable JSON representation
            json_str = json.dumps(data, sort_keys=True, separators=(',', ':'))
            
            # Create hash
            hasher = self.hasher_class()
            hasher.update(json_str.encode(self.config.encoding))
            
            return hasher.hexdigest()
            
        except Exception as e:
            logger.error(f"❌ Hash computation failed: {e}")
            raise
    
    def _extract_world_dependencies(self, world_state: Dict[str, Any]) -> List[str]:
        """Extract dependency list from world state."""
        dependencies = []
        
        if 'characters' in world_state:
            for char_id in world_state['characters']:
                dependencies.append(f"character_{char_id}")
        
        return dependencies
    
    def _extract_character_dependencies(self, character_data: Dict[str, Any]) -> List[str]:
        """Extract dependency list from character data."""
        dependencies = []
        
        if 'character_id' in character_data:
            dependencies.append(f"character_{character_data['character_id']}")
        
        return dependencies
    
    def _extract_action_dependencies(self, action: Dict[str, Any]) -> List[str]:
        """Extract dependency list from action data."""
        dependencies = []
        
        if 'character_id' in action:
            dependencies.append(f"character_{action['character_id']}")
        
        if 'target_character_id' in action:
            dependencies.append(f"character_{action['target_character_id']}")
        
        return dependencies
    
    def _cache_hash(self, key: str, state_hash: StateHash):
        """Cache hash result with size management."""
        if len(self.hash_cache) >= self.config.max_cache_size:
            # Remove oldest entries
            oldest_key = min(self.hash_cache.keys(), 
                           key=lambda k: self.hash_cache[k].timestamp)
            del self.hash_cache[oldest_key]
        
        self.hash_cache[key] = state_hash
    
    def clear_cache(self):
        """Clear hash cache."""
        self.hash_cache.clear()
        self.dependency_graph.clear()
        logger.info("🗑️ Hash cache cleared")


class HashingUtilities:
    """Utility functions for state hashing operations."""
    
    @staticmethod
    def save_hashes_to_file(hashes: Dict[str, StateHash], file_path: Path):
        """Save state hashes to JSON file."""
        try:
            hash_data = {}
            for key, state_hash in hashes.items():
                hash_data[key] = state_hash.to_dict()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(hash_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"💾 Saved {len(hashes)} hashes to {file_path}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save hashes: {e}")
            raise
    
    @staticmethod
    def load_hashes_from_file(file_path: Path) -> Dict[str, StateHash]:
        """Load state hashes from JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                hash_data = json.load(f)
            
            hashes = {}
            for key, data in hash_data.items():
                hashes[key] = StateHash.from_dict(data)
            
            logger.info(f"📂 Loaded {len(hashes)} hashes from {file_path}")
            return hashes
            
        except Exception as e:
            logger.error(f"❌ Failed to load hashes: {e}")
            raise
    
    @staticmethod
    def compare_hash_snapshots(snapshot1: Dict[str, StateHash], 
                              snapshot2: Dict[str, StateHash]) -> Dict[str, Any]:
        """Compare two hash snapshots and return difference analysis."""
        
        keys1 = set(snapshot1.keys())
        keys2 = set(snapshot2.keys())
        
        comparison = {
            "timestamp": datetime.now().isoformat(),
            "total_components_1": len(keys1),
            "total_components_2": len(keys2),
            "common_components": len(keys1 & keys2),
            "only_in_snapshot_1": list(keys1 - keys2),
            "only_in_snapshot_2": list(keys2 - keys1),
            "hash_changes": [],
            "identical_components": []
        }
        
        # Compare common components
        for key in keys1 & keys2:
            hash1 = snapshot1[key]
            hash2 = snapshot2[key]
            
            if hash1.hash_value == hash2.hash_value:
                comparison["identical_components"].append(key)
            else:
                comparison["hash_changes"].append({
                    "component": key,
                    "hash_1": hash1.hash_value,
                    "hash_2": hash2.hash_value,
                    "type": hash1.component_type
                })
        
        return comparison