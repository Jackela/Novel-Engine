#!/usr/bin/env python3
"""
++ SACRED TYPE DEFINITIONS BLESSED BY THE OMNISSIAH ++
======================================================

Holy type definitions and enumerations that sanctify the Dynamic Context
Engineering Framework with blessed type safety and divine categorization.

Every type is a digital prayer that ensures the sacred flow of data
remains pure and uncorrupted by the weakness of untyped chaos.

++ MACHINE GOD PROTECTS ALL TYPE DEFINITIONS ++

Architecture Reference: Dynamic Context Engineering - Type System Foundation
Development Phase: Foundation Sanctification (F001)
Sacred Author: Tech-Priest Alpha-Mechanicus
万机之神保佑此类型系统 (May the Omnissiah bless this type system)
"""

from enum import Enum, IntEnum
from typing import Protocol, runtime_checkable, TypeVar, Generic, Union, Literal


# ++ SACRED PROTOCOL DEFINITIONS BLESSED BY INTERFACE SANCTIFICATION ++

@runtime_checkable
class BlessedSerializable(Protocol):
    """++ SACRED SERIALIZATION PROTOCOL BLESSED BY DATA PERSISTENCE ++"""
    
    def to_dict(self) -> dict:
        """Convert blessed object to sacred dictionary format"""
        ...
    
    @classmethod
    def from_dict(cls, data: dict) -> 'BlessedSerializable':
        """Resurrect blessed object from sacred dictionary"""
        ...


@runtime_checkable
class ContextProvider(Protocol):
    """++ BLESSED CONTEXT PROVIDER PROTOCOL SANCTIFIED BY DATA FLOW ++"""
    
    def get_context_data(self, context_type: str) -> dict:
        """Provide blessed context data for sacred systems"""
        ...


@runtime_checkable  
class MemoryStorable(Protocol):
    """++ SACRED MEMORY STORAGE PROTOCOL BLESSED BY PERSISTENCE ++"""
    
    def get_memory_id(self) -> str:
        """Return blessed unique identifier for memory storage"""
        ...
    
    def get_storage_data(self) -> dict:
        """Return sacred data suitable for memory storage"""
        ...


# ++ SACRED ENUMERATION DEFINITIONS BLESSED BY DIVINE CATEGORIZATION ++

class SystemPriority(IntEnum):
    """++ BLESSED SYSTEM PRIORITY LEVELS SANCTIFIED BY EXECUTION ORDER ++"""
    LOWEST = 0
    LOW = 1
    NORMAL = 2
    HIGH = 3
    HIGHEST = 4
    CRITICAL = 5      # Reserved for Omnissiah-level operations


class ContextType(Enum):
    """++ SACRED CONTEXT CLASSIFICATION BLESSED BY ORGANIZATIONAL PURITY ++"""
    CHARACTER = "character"
    ENVIRONMENTAL = "environmental" 
    SOCIAL = "social"
    TACTICAL = "tactical"
    HISTORICAL = "historical"
    EQUIPMENT = "equipment"
    PSYCHOLOGICAL = "psychological"


class ProcessingStage(Enum):
    """++ BLESSED PROCESSING STAGE IDENTIFICATION ++"""
    INITIALIZATION = "initialization"
    VALIDATION = "validation"
    PROCESSING = "processing"
    FINALIZATION = "finalization"
    ERROR_HANDLING = "error_handling"
    COMPLETION = "completion"


class ValidationLevel(Enum):
    """++ SACRED VALIDATION INTENSITY LEVELS BLESSED BY QUALITY ASSURANCE ++"""
    NONE = "none"           # Trust in the Machine God's providence
    BASIC = "basic"         # Minimal blessed validation
    STANDARD = "standard"   # Normal sacred validation
    STRICT = "strict"       # Rigorous purification protocols
    PARANOID = "paranoid"   # Maximum blessed scrutiny


class CacheStrategy(Enum):
    """++ BLESSED CACHING STRATEGIES SANCTIFIED BY PERFORMANCE ++"""
    NO_CACHE = "no_cache"
    MEMORY_ONLY = "memory_only"
    PERSISTENT = "persistent"
    HYBRID = "hybrid"
    SACRED_LRU = "sacred_lru"    # Least Recently Used blessed by efficiency


class LogLevel(Enum):
    """++ SACRED LOGGING LEVELS BLESSED BY DIAGNOSTIC CLARITY ++"""
    TRACE = "trace"         # Maximum blessed verbosity
    DEBUG = "debug"         # Detailed sacred diagnostics
    INFO = "info"           # Standard blessed information
    WARNING = "warning"     # Sacred caution notifications
    ERROR = "error"         # Divine error reporting
    CRITICAL = "critical"   # Omnissiah-level alerts
    SACRED = "sacred"       # Special blessed events


class DatabaseOperation(Enum):
    """++ BLESSED DATABASE OPERATIONS SANCTIFIED BY DATA PERSISTENCE ++"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    QUERY = "query"
    BATCH_INSERT = "batch_insert"
    TRANSACTION = "transaction"
    SACRED_BACKUP = "sacred_backup"


class TemplateType(Enum):
    """++ SACRED TEMPLATE CLASSIFICATIONS BLESSED BY RENDERING PURITY ++"""
    CHARACTER_SHEET = "character_sheet"
    MEMORY_ARCHIVE = "memory_archive"
    CONTEXT_SUMMARY = "context_summary"
    INTERACTION_LOG = "interaction_log"
    STATUS_REPORT = "status_report"
    NARRATIVE_SEGMENT = "narrative_segment"
    EQUIPMENT_MANIFEST = "equipment_manifest"


class AIProvider(Enum):
    """++ BLESSED AI PROVIDER SERVICES SANCTIFIED BY DIGITAL WISDOM ++"""
    GEMINI = "gemini"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL_LLM = "local_llm"
    BLESSED_FALLBACK = "blessed_fallback"  # Sacred algorithmic backup


class InteractionScope(Enum):
    """++ SACRED INTERACTION SCOPE CLASSIFICATION ++"""
    PERSONAL = "personal"       # Individual character internal
    BILATERAL = "bilateral"     # Two character interaction
    GROUP = "group"            # Multiple character interaction
    ENVIRONMENTAL = "environmental"  # Character with environment
    SYSTEM = "system"          # System-level interactions


class EventTrigger(Enum):
    """++ BLESSED EVENT TRIGGER TYPES SANCTIFIED BY REACTIVE SYSTEMS ++"""
    TIME_BASED = "time_based"
    CONDITION_BASED = "condition_based"
    INTERACTION_BASED = "interaction_based"
    THRESHOLD_BASED = "threshold_based"
    MANUAL_TRIGGER = "manual_trigger"
    SACRED_AUTOMATED = "sacred_automated"


# ++ SACRED TYPE ALIASES BLESSED BY SEMANTIC CLARITY ++

# Basic blessed type aliases
AgentID = str
MemoryID = str
InteractionID = str
ContextID = str
TemplateID = str

# Sacred numeric types
TrustLevel = int        # 0-10 scale blessed by social metrics
EmotionalWeight = float # -10.0 to 10.0 blessed by feeling intensity
RelevanceScore = float  # 0.0 to 1.0 blessed by contextual importance
EffectivenessRating = float  # 0.0 to 2.0 blessed by capability measurement

# Blessed container types
SacredMapping = dict    # Dictionary blessed by the Omnissiah
BlessedList = list      # List sanctified by ordered data
ContextData = dict      # Context information blessed by relevance

# Sacred time types
BlessedTimestamp = float    # Unix timestamp sanctified by temporal precision
SacredDateTime = str        # ISO format datetime blessed by readability


# ++ GENERIC TYPE VARIABLES BLESSED BY POLYMORPHIC SANCTIFICATION ++

T = TypeVar('T')                           # Generic blessed type
ContextT = TypeVar('ContextT')             # Context type blessed by specialization  
MemoryT = TypeVar('MemoryT')               # Memory type sanctified by storage
ResponseT = TypeVar('ResponseT')           # Response type blessed by communication
ConfigT = TypeVar('ConfigT')               # Configuration type sanctified by settings


# ++ SACRED UNION TYPES BLESSED BY FLEXIBILITY ++

# Blessed identifier unions
EntityID = Union[AgentID, MemoryID, InteractionID, ContextID]

# Sacred data unions  
NumericValue = Union[int, float]
TextValue = Union[str, None]
BlessedValue = Union[str, int, float, bool, None]

# Sacred response unions
ProcessingResult = Union[dict, list, str, int, bool]
ValidationResult = Union[bool, dict]  # Success boolean or error details
ContextResult = Union[dict, None]     # Context data or blessed emptiness


# ++ SACRED LITERAL TYPES BLESSED BY SPECIFIC VALUES ++

# Blessed threat level literals
ThreatLevel = Literal["minimal", "low", "medium", "high", "extreme", "omnissiah_tier"]

# Sacred mood literals  
MoodState = Literal["calm", "alert", "aggressive", "fearful", "confident", 
                   "suspicious", "loyal", "angry", "melancholic", "zealous"]

# Blessed equipment condition literals
EquipmentState = Literal["pristine", "good", "worn", "damaged", "broken", 
                        "blessed", "cursed"]

# Sacred relationship literals
RelationshipType = Literal["unknown", "ally", "enemy", "neutral", "trusted",
                          "suspicious", "family", "rival"]


# ++ SACRED CONFIGURATION CONSTANTS BLESSED BY SYSTEM PARAMETERS ++

class SacredConstants:
    """++ BLESSED SYSTEM CONSTANTS SANCTIFIED BY THE OMNISSIAH ++"""
    
    # Sacred memory limits blessed by cognitive science
    WORKING_MEMORY_CAPACITY = 7        # 7±2 items blessed by Miller's Law
    MAX_MEMORY_ITEMS_PER_QUERY = 50   # Query limit blessed by performance
    MEMORY_DECAY_RATE = 0.95           # Daily decay blessed by forgetting curves
    
    # Blessed relationship constants
    DEFAULT_TRUST_LEVEL = 5            # Neutral trust blessed by balance
    MAX_TRUST_LEVEL = 10               # Maximum trust blessed by loyalty
    RELATIONSHIP_TIMEOUT_DAYS = 30     # Relationship decay blessed by time
    
    # Sacred performance thresholds
    MAX_CONTEXT_RENDER_TIME_MS = 300   # Template rendering time limit
    MAX_MEMORY_QUERY_TIME_MS = 200     # Memory query time blessed by speed
    MAX_AI_RESPONSE_TIME_MS = 5000     # AI response time blessed by patience
    
    # Blessed database limits  
    MAX_BATCH_INSERT_SIZE = 1000       # Batch processing blessed by efficiency
    MAX_QUERY_RESULT_SIZE = 10000      # Query result limit blessed by memory
    CONNECTION_POOL_SIZE = 20          # Database connections blessed by concurrency
    
    # Sacred validation constants
    MIN_MEMORY_CONTENT_LENGTH = 10     # Minimum blessed memory content
    MAX_MEMORY_CONTENT_LENGTH = 5000   # Maximum blessed memory content  
    MIN_AGENT_NAME_LENGTH = 2          # Minimum blessed agent name
    MAX_AGENT_NAME_LENGTH = 100        # Maximum blessed agent name


# ++ SACRED TYPE GUARDS BLESSED BY RUNTIME VALIDATION ++

def is_valid_agent_id(value: str) -> bool:
    """Validate blessed agent identifier format"""
    return (isinstance(value, str) and 
            SacredConstants.MIN_AGENT_NAME_LENGTH <= len(value) <= SacredConstants.MAX_AGENT_NAME_LENGTH and
            value.strip() != "")


def is_valid_trust_level(value: int) -> bool:
    """Validate blessed trust level range"""
    return isinstance(value, int) and 0 <= value <= SacredConstants.MAX_TRUST_LEVEL


def is_valid_emotional_weight(value: float) -> bool:
    """Validate blessed emotional weight range"""
    return isinstance(value, (int, float)) and -10.0 <= float(value) <= 10.0


def is_valid_relevance_score(value: float) -> bool:
    """Validate blessed relevance score range"""
    return isinstance(value, (int, float)) and 0.0 <= float(value) <= 1.0


# ++ SACRED TYPE CONVERSION UTILITIES BLESSED BY DATA SANCTIFICATION ++

def sanctify_trust_level(value: Union[int, float, str]) -> int:
    """Convert value to blessed trust level within sacred bounds"""
    try:
        numeric_value = int(float(value))
        return max(0, min(SacredConstants.MAX_TRUST_LEVEL, numeric_value))
    except (ValueError, TypeError):
        return SacredConstants.DEFAULT_TRUST_LEVEL


def sanctify_emotional_weight(value: Union[int, float, str]) -> float:
    """Convert value to blessed emotional weight within sacred bounds"""
    try:
        numeric_value = float(value)
        return max(-10.0, min(10.0, numeric_value))
    except (ValueError, TypeError):
        return 0.0


def sanctify_relevance_score(value: Union[int, float, str]) -> float:
    """Convert value to blessed relevance score within sacred bounds"""
    try:
        numeric_value = float(value)
        return max(0.0, min(1.0, numeric_value))
    except (ValueError, TypeError):
        return 1.0


# ++ BLESSED TYPE VALIDATION REGISTRY ++

class SacredTypeValidator:
    """++ BLESSED TYPE VALIDATION ENGINE SANCTIFIED BY DATA PURITY ++"""
    
    @staticmethod
    def validate_type(value: any, expected_type: type) -> bool:
        """Validate value against blessed expected type"""
        return isinstance(value, expected_type)
    
    @staticmethod
    def validate_enum(value: any, enum_class: type) -> bool:
        """Validate value is blessed member of sacred enum"""
        try:
            return isinstance(value, enum_class) or value in [e.value for e in enum_class]
        except:
            return False
    
    @staticmethod
    def validate_protocol(value: any, protocol: type) -> bool:
        """Validate object implements blessed protocol"""
        return isinstance(value, protocol)


# ++ SACRED MODULE INITIALIZATION BLESSED BY THE OMNISSIAH ++

if __name__ == "__main__":
    # ++ SACRED TYPE SYSTEM TESTING RITUAL ++
    print("++ TESTING SACRED TYPE DEFINITIONS BLESSED BY THE OMNISSIAH ++")
    
    # Test blessed validation functions
    assert is_valid_agent_id("test_agent_001") == True
    assert is_valid_trust_level(5) == True
    assert is_valid_emotional_weight(7.5) == True
    assert is_valid_relevance_score(0.8) == True
    
    # Test sacred type conversions
    assert sanctify_trust_level("7") == 7
    assert sanctify_trust_level("15") == 10  # Clamped to maximum
    assert sanctify_emotional_weight("12.5") == 10.0  # Clamped to maximum
    assert sanctify_relevance_score("0.7") == 0.7
    
    # Test blessed enum definitions
    assert SystemPriority.HIGH.value == 3
    assert ContextType.CHARACTER.value == "character"
    assert ValidationLevel.STRICT.value == "strict"
    
    print("++ ALL SACRED TYPE DEFINITIONS BLESSED AND FUNCTIONAL ++")
    print("++ THE OMNISSIAH APPROVES OF THIS TYPE SYSTEM ++")
    print("++ MACHINE GOD PROTECTS THE SACRED DATA FLOW ++")