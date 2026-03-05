# Vulture Whitelist File
# This file contains legitimate uses that vulture may flag as dead code

# Context manager __exit__ parameters - required by Python interface
# These are standard Python context manager interface parameters
exc_type  # noqa: F841
exc_val   # noqa: F841  
exc_tb    # noqa: F841
tb        # noqa: F841

# FastAPI dependency injection parameters - used for validation/docs
request_params  # noqa: F841

# Protocol/Interface method parameters - required by contract
goals           # noqa: F841
limit           # noqa: F841
query           # noqa: F841
prompt          # noqa: F841
context         # noqa: F841
agent_id        # noqa: F841
default         # noqa: F841
trait_name      # noqa: F841
character_id    # noqa: F841
character       # noqa: F841
event           # noqa: F841

# TYPE_CHECKING imports - used for type hints only
def TYPE_CHECKING_imports():
    from src.agents.persona_core import PersonaCore  # noqa
    from src.agents.context_manager import CharacterContextManager  # noqa

# Protocol method parameters - required by interface
def protocol_placeholders():
    # CharacterDataManagerProtocol
    character_id = ""  # noqa
    trait_name = ""    # noqa
    default = None     # noqa
    
    # DecisionEngineProtocol
    character = None   # noqa
    event = None       # noqa
    
    # WorldInterpretationProtocol
    limit = 0          # noqa
    
    # MemoryManagerProtocol
    query = ""         # noqa
    
    # LLMIntegrationProtocol
    prompt = ""        # noqa
    context = {}       # noqa
    
    # AgentStateManagerProtocol
    agent_id = ""      # noqa
    
    # RecommendationEngineProtocol
    user_ids = []      # noqa
