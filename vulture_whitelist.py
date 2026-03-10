# Vulture Whitelist File
# This file contains legitimate uses that vulture may flag as dead code

# Context manager __exit__ parameters - required by Python interface
# These are standard Python context manager interface parameters
exc_type  # noqa: F821
exc_val  # noqa: F821
exc_tb  # noqa: F821
tb  # noqa: F821

# FastAPI dependency injection parameters - used for validation/docs
request_params  # noqa: F821

# Protocol/Interface method parameters - required by contract
goals  # noqa: F821
limit  # noqa: F821
query  # noqa: F821
prompt  # noqa: F821
context  # noqa: F821
agent_id  # noqa: F821
default  # noqa: F821
trait_name  # noqa: F821
character_id  # noqa: F821
character  # noqa: F821
event  # noqa: F821


# TYPE_CHECKING imports - used for type hints only
def TYPE_CHECKING_imports():
    from src.agents.persona_core import PersonaCore  # noqa
    from src.agents.context_manager import CharacterContextManager  # noqa


# Protocol method parameters - required by interface
def protocol_placeholders():
    # CharacterDataManagerProtocol
    character_id = ""  # noqa
    trait_name = ""  # noqa
    default = None  # noqa

    # DecisionEngineProtocol
    character = None  # noqa
    event = None  # noqa

    # WorldInterpretationProtocol
    limit = 0  # noqa

    # MemoryManagerProtocol
    query = ""  # noqa

    # LLMIntegrationProtocol
    prompt = ""  # noqa
    context = {}  # noqa

    # AgentStateManagerProtocol
    agent_id = ""  # noqa

    # RecommendationEngineProtocol
    user_ids = []  # noqa
