"""
Validator
=========

Advanced validation system for PersonaAgent data and operations.
Provides comprehensive validation for character data, actions, and system integrity.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import re
import json

from ..protocols import WorldEvent, ThreatLevel


class ValidationType(Enum):
    """Types of validation that can be performed."""
    CHARACTER_DATA = "character_data"
    ACTION = "action"
    WORLD_EVENT = "world_event"
    SYSTEM_STATE = "system_state"
    CONFIGURATION = "configuration"
    MEMORY = "memory"
    GOAL = "goal"


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    """Represents a validation issue."""
    severity: ValidationSeverity
    message: str
    field: Optional[str] = None
    code: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of validation operation."""
    is_valid: bool
    validation_type: ValidationType
    issues: List[ValidationIssue]
    score: float = 1.0  # 0.0 to 1.0, where 1.0 is perfect
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def has_critical_issues(self) -> bool:
        """Check if validation has critical issues."""
        return any(issue.severity == ValidationSeverity.CRITICAL for issue in self.issues)
    
    def has_errors(self) -> bool:
        """Check if validation has errors or critical issues."""
        return any(issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL] 
                  for issue in self.issues)
    
    def get_issues_by_severity(self, severity: ValidationSeverity) -> List[ValidationIssue]:
        """Get issues of specific severity."""
        return [issue for issue in self.issues if issue.severity == severity]


class Validator:
    """
    Advanced validation system for PersonaAgent.
    
    Responsibilities:
    - Validate character data structure and content
    - Validate actions and decisions for consistency
    - Validate world events and interpretations
    - Validate system state and configuration
    - Provide detailed validation reports with suggestions
    - Support custom validation rules and schemas
    """
    
    def __init__(self, character_id: str, logger: Optional[logging.Logger] = None):
        self.character_id = character_id
        self.logger = logger or logging.getLogger(__name__)
        
        # Validation rules and schemas
        self._character_data_schema = self._initialize_character_schema()
        self._action_schema = self._initialize_action_schema()
        self._world_event_schema = self._initialize_world_event_schema()
        
        # Custom validation rules
        self._custom_rules: Dict[str, callable] = {}
        
        # Validation statistics
        self._stats = {
            "total_validations": 0,
            "successful_validations": 0,
            "failed_validations": 0,
            "issues_by_type": {vt.value: 0 for vt in ValidationType},
            "issues_by_severity": {vs.value: 0 for vs in ValidationSeverity}
        }
        
        # Common patterns for validation
        self._patterns = {
            "name": re.compile(r"^[a-zA-Z\s\-'\.]{2,50}$"),
            "faction": re.compile(r"^[a-zA-Z\s\-']{2,30}$"),
            "location": re.compile(r"^[a-zA-Z\s\-'\.0-9]{2,50}$"),
            "id": re.compile(r"^[a-zA-Z0-9_\-]{3,50}$"),
            "percentage": re.compile(r"^[0-9]{1,3}%$"),
            "float_0_1": lambda x: isinstance(x, (int, float)) and 0.0 <= x <= 1.0,
            "positive_int": lambda x: isinstance(x, int) and x > 0
        }
    
    async def validate_character_data(self, character_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate character data structure and content.
        
        Args:
            character_data: Character data to validate
            
        Returns:
            ValidationResult: Comprehensive validation results
        """
        try:
            self.logger.debug("Validating character data")
            issues = []
            
            # Schema validation
            schema_issues = await self._validate_against_schema(
                character_data, self._character_data_schema, "character_data"
            )
            issues.extend(schema_issues)
            
            # Required sections validation
            required_sections = ["basic_info", "personality", "attributes"]
            for section in required_sections:
                if section not in character_data:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message=f"Missing required section: {section}",
                        field=section,
                        code="MISSING_REQUIRED_SECTION"
                    ))
            
            # Basic info validation
            if "basic_info" in character_data:
                basic_info_issues = await self._validate_basic_info(character_data["basic_info"])
                issues.extend(basic_info_issues)
            
            # Personality validation
            if "personality" in character_data:
                personality_issues = await self._validate_personality(character_data["personality"])
                issues.extend(personality_issues)
            
            # Attributes validation
            if "attributes" in character_data:
                attributes_issues = await self._validate_attributes(character_data["attributes"])
                issues.extend(attributes_issues)
            
            # Faction info validation
            if "faction_info" in character_data:
                faction_issues = await self._validate_faction_info(character_data["faction_info"])
                issues.extend(faction_issues)
            
            # Goals validation
            if "goals" in character_data:
                goals_issues = await self._validate_goals(character_data["goals"])
                issues.extend(goals_issues)
            
            # Decision weights validation
            if "decision_weights" in character_data:
                weights_issues = await self._validate_decision_weights(character_data["decision_weights"])
                issues.extend(weights_issues)
            
            # Calculate validation score
            score = await self._calculate_validation_score(issues)
            
            # Create result
            result = ValidationResult(
                is_valid=not any(issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL] 
                               for issue in issues),
                validation_type=ValidationType.CHARACTER_DATA,
                issues=issues,
                score=score,
                metadata={
                    "sections_validated": len([s for s in required_sections if s in character_data]),
                    "total_fields": len(self._flatten_dict(character_data)),
                    "validation_timestamp": datetime.now().isoformat()
                }
            )
            
            await self._update_validation_stats(result)
            return result
            
        except Exception as e:
            self.logger.error(f"Character data validation failed: {e}")
            return ValidationResult(
                is_valid=False,
                validation_type=ValidationType.CHARACTER_DATA,
                issues=[ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Validation system error: {str(e)}",
                    code="VALIDATION_SYSTEM_ERROR"
                )]
            )
    
    async def validate_action(self, action: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Validate character action for consistency and feasibility.
        
        Args:
            action: Action to validate
            context: Optional context for validation
            
        Returns:
            ValidationResult: Action validation results
        """
        try:
            self.logger.debug(f"Validating action: {action.get('action_type', 'unknown')}")
            issues = []
            
            # Schema validation
            schema_issues = await self._validate_against_schema(
                action, self._action_schema, "action"
            )
            issues.extend(schema_issues)
            
            # Required fields
            required_fields = ["action_type"]
            for field in required_fields:
                if field not in action:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message=f"Missing required action field: {field}",
                        field=field,
                        code="MISSING_ACTION_FIELD"
                    ))
            
            # Action type validation
            if "action_type" in action:
                action_type_issues = await self._validate_action_type(action["action_type"])
                issues.extend(action_type_issues)
            
            # Priority validation
            if "priority" in action:
                priority_issues = await self._validate_priority(action["priority"])
                issues.extend(priority_issues)
            
            # Parameters validation
            if "parameters" in action:
                params_issues = await self._validate_action_parameters(
                    action["parameters"], action.get("action_type")
                )
                issues.extend(params_issues)
            
            # Context validation
            if context:
                context_issues = await self._validate_action_context(action, context)
                issues.extend(context_issues)
            
            # Feasibility check
            feasibility_issues = await self._validate_action_feasibility(action, context)
            issues.extend(feasibility_issues)
            
            # Calculate score
            score = await self._calculate_validation_score(issues)
            
            result = ValidationResult(
                is_valid=not any(issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL] 
                               for issue in issues),
                validation_type=ValidationType.ACTION,
                issues=issues,
                score=score,
                metadata={
                    "action_type": action.get("action_type"),
                    "has_context": context is not None,
                    "validation_timestamp": datetime.now().isoformat()
                }
            )
            
            await self._update_validation_stats(result)
            return result
            
        except Exception as e:
            self.logger.error(f"Action validation failed: {e}")
            return ValidationResult(
                is_valid=False,
                validation_type=ValidationType.ACTION,
                issues=[ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Action validation error: {str(e)}",
                    code="ACTION_VALIDATION_ERROR"
                )]
            )
    
    async def validate_world_event(self, event: WorldEvent) -> ValidationResult:
        """
        Validate world event structure and content.
        
        Args:
            event: World event to validate
            
        Returns:
            ValidationResult: Event validation results
        """
        try:
            self.logger.debug(f"Validating world event: {event.event_id}")
            issues = []
            
            # Event ID validation
            if not event.event_id or not self._patterns["id"].match(event.event_id):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message="Invalid event ID format",
                    field="event_id",
                    code="INVALID_EVENT_ID"
                ))
            
            # Event type validation
            if not event.event_type or len(event.event_type.strip()) == 0:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message="Event type cannot be empty",
                    field="event_type",
                    code="EMPTY_EVENT_TYPE"
                ))
            
            # Source validation
            if not event.source or not self._patterns["id"].match(event.source):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message="Event source should follow ID format",
                    field="source",
                    code="INVALID_SOURCE_FORMAT",
                    suggestion="Use alphanumeric characters, underscores, and hyphens only"
                ))
            
            # Affected entities validation
            if not event.affected_entities:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message="Event has no affected entities",
                    field="affected_entities",
                    code="NO_AFFECTED_ENTITIES",
                    suggestion="Consider adding affected entity IDs"
                ))
            else:
                for entity in event.affected_entities:
                    if not self._patterns["id"].match(entity):
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            message=f"Entity ID '{entity}' should follow ID format",
                            field="affected_entities",
                            code="INVALID_ENTITY_ID"
                        ))
            
            # Location validation
            if event.location and not self._patterns["location"].match(event.location):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message="Location format may be invalid",
                    field="location",
                    code="INVALID_LOCATION_FORMAT"
                ))
            
            # Timestamp validation
            if event.timestamp <= 0:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message="Invalid timestamp",
                    field="timestamp",
                    code="INVALID_TIMESTAMP"
                ))
            
            # Data validation
            if event.data:
                data_issues = await self._validate_event_data(event.data)
                issues.extend(data_issues)
            
            score = await self._calculate_validation_score(issues)
            
            result = ValidationResult(
                is_valid=not any(issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL] 
                               for issue in issues),
                validation_type=ValidationType.WORLD_EVENT,
                issues=issues,
                score=score,
                metadata={
                    "event_type": event.event_type,
                    "affected_entities_count": len(event.affected_entities),
                    "has_location": event.location is not None,
                    "has_data": bool(event.data),
                    "validation_timestamp": datetime.now().isoformat()
                }
            )
            
            await self._update_validation_stats(result)
            return result
            
        except Exception as e:
            self.logger.error(f"World event validation failed: {e}")
            return ValidationResult(
                is_valid=False,
                validation_type=ValidationType.WORLD_EVENT,
                issues=[ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Event validation error: {str(e)}",
                    code="EVENT_VALIDATION_ERROR"
                )]
            )
    
    async def validate_system_state(self, state: Dict[str, Any]) -> ValidationResult:
        """
        Validate system state for integrity and consistency.
        
        Args:
            state: System state to validate
            
        Returns:
            ValidationResult: System state validation results
        """
        try:
            self.logger.debug("Validating system state")
            issues = []
            
            # Memory system validation
            if "memory_system" in state:
                memory_issues = await self._validate_memory_system(state["memory_system"])
                issues.extend(memory_issues)
            
            # Goal system validation
            if "goal_system" in state:
                goal_issues = await self._validate_goal_system(state["goal_system"])
                issues.extend(goal_issues)
            
            # Decision system validation
            if "decision_system" in state:
                decision_issues = await self._validate_decision_system(state["decision_system"])
                issues.extend(decision_issues)
            
            # World interpretation validation
            if "world_interpretation" in state:
                interpretation_issues = await self._validate_world_interpretation(state["world_interpretation"])
                issues.extend(interpretation_issues)
            
            # LLM integration validation
            if "llm_integration" in state:
                llm_issues = await self._validate_llm_integration(state["llm_integration"])
                issues.extend(llm_issues)
            
            score = await self._calculate_validation_score(issues)
            
            result = ValidationResult(
                is_valid=not any(issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL] 
                               for issue in issues),
                validation_type=ValidationType.SYSTEM_STATE,
                issues=issues,
                score=score,
                metadata={
                    "subsystems_validated": len([k for k in state.keys() if k.endswith("_system")]),
                    "validation_timestamp": datetime.now().isoformat()
                }
            )
            
            await self._update_validation_stats(result)
            return result
            
        except Exception as e:
            self.logger.error(f"System state validation failed: {e}")
            return ValidationResult(
                is_valid=False,
                validation_type=ValidationType.SYSTEM_STATE,
                issues=[ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    message=f"System state validation error: {str(e)}",
                    code="SYSTEM_STATE_ERROR"
                )]
            )
    
    async def add_custom_rule(self, rule_name: str, rule_function: callable) -> None:
        """
        Add custom validation rule.
        
        Args:
            rule_name: Name of the rule
            rule_function: Function that takes data and returns (is_valid, issues)
        """
        try:
            self._custom_rules[rule_name] = rule_function
            self.logger.info(f"Added custom validation rule: {rule_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to add custom rule {rule_name}: {e}")
    
    async def get_validation_statistics(self) -> Dict[str, Any]:
        """Get comprehensive validation statistics."""
        try:
            total = self._stats["total_validations"]
            success_rate = (self._stats["successful_validations"] / total) if total > 0 else 0.0
            
            return {
                "total_validations": total,
                "successful_validations": self._stats["successful_validations"],
                "failed_validations": self._stats["failed_validations"],
                "success_rate": success_rate,
                "issues_by_type": self._stats["issues_by_type"].copy(),
                "issues_by_severity": self._stats["issues_by_severity"].copy(),
                "custom_rules_count": len(self._custom_rules)
            }
            
        except Exception as e:
            self.logger.error(f"Statistics calculation failed: {e}")
            return {"error": str(e)}
    
    # Private validation methods
    
    async def _validate_basic_info(self, basic_info: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate basic character information."""
        issues = []
        
        # Name validation
        if "name" not in basic_info:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message="Character name is required",
                field="basic_info.name",
                code="MISSING_NAME"
            ))
        elif not self._patterns["name"].match(str(basic_info["name"])):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                message="Character name format may be invalid",
                field="basic_info.name",
                code="INVALID_NAME_FORMAT",
                suggestion="Use only letters, spaces, hyphens, apostrophes, and periods"
            ))
        
        # Age validation (if present)
        if "age" in basic_info:
            try:
                age = int(basic_info["age"])
                if age < 1 or age > 1000:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        message="Age seems unrealistic",
                        field="basic_info.age",
                        code="UNREALISTIC_AGE"
                    ))
            except (ValueError, TypeError):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message="Age must be a valid number",
                    field="basic_info.age",
                    code="INVALID_AGE_TYPE"
                ))
        
        return issues
    
    async def _validate_personality(self, personality: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate personality traits."""
        issues = []
        
        if not isinstance(personality, dict):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message="Personality must be a dictionary",
                field="personality",
                code="INVALID_PERSONALITY_TYPE"
            ))
            return issues
        
        # Validate trait values
        for trait, value in personality.items():
            if isinstance(value, (int, float)):
                if not self._patterns["float_0_1"](value):
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        message=f"Personality trait '{trait}' should be between 0.0 and 1.0",
                        field=f"personality.{trait}",
                        code="TRAIT_OUT_OF_RANGE",
                        suggestion="Use values between 0.0 and 1.0"
                    ))
        
        # Check for common traits
        common_traits = ["aggression", "intelligence", "loyalty", "charisma"]
        missing_traits = [trait for trait in common_traits if trait not in personality]
        
        if missing_traits:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                message=f"Consider adding common traits: {', '.join(missing_traits)}",
                field="personality",
                code="MISSING_COMMON_TRAITS"
            ))
        
        return issues
    
    async def _validate_attributes(self, attributes: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate character attributes."""
        issues = []
        
        # Similar validation to personality
        for attr, value in attributes.items():
            if isinstance(value, (int, float)):
                if not self._patterns["float_0_1"](value):
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        message=f"Attribute '{attr}' should be between 0.0 and 1.0",
                        field=f"attributes.{attr}",
                        code="ATTRIBUTE_OUT_OF_RANGE"
                    ))
        
        return issues
    
    async def _validate_faction_info(self, faction_info: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate faction information."""
        issues = []
        
        if "faction" in faction_info:
            if not self._patterns["faction"].match(str(faction_info["faction"])):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message="Faction name format may be invalid",
                    field="faction_info.faction",
                    code="INVALID_FACTION_FORMAT"
                ))
        
        return issues
    
    async def _validate_goals(self, goals: List[Dict[str, Any]]) -> List[ValidationIssue]:
        """Validate character goals."""
        issues = []
        
        if not isinstance(goals, list):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message="Goals must be a list",
                field="goals",
                code="INVALID_GOALS_TYPE"
            ))
            return issues
        
        for i, goal in enumerate(goals):
            if not isinstance(goal, dict):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Goal {i} must be a dictionary",
                    field=f"goals[{i}]",
                    code="INVALID_GOAL_TYPE"
                ))
                continue
            
            # Check required goal fields
            if "description" not in goal and "title" not in goal:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message=f"Goal {i} should have description or title",
                    field=f"goals[{i}]",
                    code="MISSING_GOAL_DESCRIPTION"
                ))
        
        return issues
    
    async def _validate_decision_weights(self, weights: Dict[str, float]) -> List[ValidationIssue]:
        """Validate decision weights."""
        issues = []
        
        for weight_name, value in weights.items():
            if not isinstance(value, (int, float)):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Decision weight '{weight_name}' must be a number",
                    field=f"decision_weights.{weight_name}",
                    code="INVALID_WEIGHT_TYPE"
                ))
            elif not -1.0 <= value <= 1.0:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message=f"Decision weight '{weight_name}' should be between -1.0 and 1.0",
                    field=f"decision_weights.{weight_name}",
                    code="WEIGHT_OUT_OF_RANGE"
                ))
        
        return issues
    
    async def _validate_action_type(self, action_type: str) -> List[ValidationIssue]:
        """Validate action type."""
        issues = []
        
        valid_action_types = [
            "attack", "defend", "move", "communicate", "explore", "wait", 
            "negotiate", "trade", "heal", "craft", "observe", "retreat"
        ]
        
        if action_type not in valid_action_types:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                message=f"Unknown action type: {action_type}",
                field="action_type",
                code="UNKNOWN_ACTION_TYPE",
                suggestion=f"Consider using: {', '.join(valid_action_types[:5])}"
            ))
        
        return issues
    
    async def _validate_priority(self, priority: str) -> List[ValidationIssue]:
        """Validate action priority."""
        issues = []
        
        valid_priorities = ["critical", "high", "medium", "low"]
        
        if priority not in valid_priorities:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                message=f"Invalid priority: {priority}",
                field="priority",
                code="INVALID_PRIORITY",
                suggestion=f"Use: {', '.join(valid_priorities)}"
            ))
        
        return issues
    
    # Schema and utility methods
    
    def _initialize_character_schema(self) -> Dict[str, Any]:
        """Initialize character data validation schema."""
        return {
            "type": "object",
            "required": ["basic_info"],
            "properties": {
                "basic_info": {
                    "type": "object",
                    "required": ["name"],
                    "properties": {
                        "name": {"type": "string", "minLength": 2, "maxLength": 50},
                        "age": {"type": "integer", "minimum": 1, "maximum": 1000}
                    }
                },
                "personality": {
                    "type": "object"
                },
                "attributes": {
                    "type": "object"
                }
            }
        }
    
    def _initialize_action_schema(self) -> Dict[str, Any]:
        """Initialize action validation schema."""
        return {
            "type": "object",
            "required": ["action_type"],
            "properties": {
                "action_type": {"type": "string", "minLength": 1},
                "priority": {"type": "string"},
                "parameters": {"type": "object"}
            }
        }
    
    def _initialize_world_event_schema(self) -> Dict[str, Any]:
        """Initialize world event validation schema."""
        return {
            "type": "object",
            "required": ["event_id", "event_type", "source"],
            "properties": {
                "event_id": {"type": "string", "minLength": 3},
                "event_type": {"type": "string", "minLength": 1},
                "source": {"type": "string", "minLength": 1}
            }
        }
    
    async def _validate_against_schema(self, data: Dict[str, Any], schema: Dict[str, Any], 
                                     context: str) -> List[ValidationIssue]:
        """Validate data against JSON schema."""
        # This is a simplified schema validation
        # In a production system, you might use jsonschema library
        issues = []
        
        try:
            # Basic type checking
            if schema.get("type") == "object" and not isinstance(data, dict):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"{context} must be an object/dictionary",
                    code="INVALID_TYPE"
                ))
                return issues
            
            # Required fields checking
            required_fields = schema.get("required", [])
            for field in required_fields:
                if field not in data:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message=f"Required field '{field}' is missing",
                        field=field,
                        code="MISSING_REQUIRED_FIELD"
                    ))
            
        except Exception as e:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"Schema validation error: {str(e)}",
                code="SCHEMA_VALIDATION_ERROR"
            ))
        
        return issues
    
    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """Flatten nested dictionary for counting fields."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)
    
    async def _calculate_validation_score(self, issues: List[ValidationIssue]) -> float:
        """Calculate validation score based on issues."""
        if not issues:
            return 1.0
        
        # Weight issues by severity
        severity_weights = {
            ValidationSeverity.CRITICAL: -0.5,
            ValidationSeverity.ERROR: -0.3,
            ValidationSeverity.WARNING: -0.1,
            ValidationSeverity.INFO: -0.05
        }
        
        score = 1.0
        for issue in issues:
            score += severity_weights.get(issue.severity, -0.1)
        
        return max(0.0, min(1.0, score))
    
    async def _update_validation_stats(self, result: ValidationResult) -> None:
        """Update validation statistics."""
        try:
            self._stats["total_validations"] += 1
            
            if result.is_valid:
                self._stats["successful_validations"] += 1
            else:
                self._stats["failed_validations"] += 1
            
            self._stats["issues_by_type"][result.validation_type.value] += len(result.issues)
            
            for issue in result.issues:
                self._stats["issues_by_severity"][issue.severity.value] += 1
                
        except Exception as e:
            self.logger.debug(f"Statistics update failed: {e}")
    
    # Placeholder methods for system validation
    
    async def _validate_memory_system(self, memory_state: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate memory system state.""" 
        return []  # Placeholder
    
    async def _validate_goal_system(self, goal_state: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate goal system state."""
        return []  # Placeholder
    
    async def _validate_decision_system(self, decision_state: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate decision system state."""
        return []  # Placeholder
    
    async def _validate_world_interpretation(self, interpretation_state: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate world interpretation system state."""
        return []  # Placeholder
    
    async def _validate_llm_integration(self, llm_state: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate LLM integration system state."""
        return []  # Placeholder
    
    async def _validate_action_parameters(self, parameters: Dict[str, Any], action_type: Optional[str]) -> List[ValidationIssue]:
        """Validate action parameters."""
        return []  # Placeholder
    
    async def _validate_action_context(self, action: Dict[str, Any], context: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate action within context."""
        return []  # Placeholder
    
    async def _validate_action_feasibility(self, action: Dict[str, Any], context: Optional[Dict[str, Any]]) -> List[ValidationIssue]:
        """Validate action feasibility."""
        return []  # Placeholder
    
    async def _validate_event_data(self, data: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate event data."""
        return []  # Placeholder