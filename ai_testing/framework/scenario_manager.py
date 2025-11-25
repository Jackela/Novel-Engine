"""
AI Test Scenario Management System

Provides comprehensive scenario creation, management, and orchestration for
Novel-Engine AI acceptance testing. Includes AI-powered scenario generation
and intelligent test case optimization.
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import httpx
import yaml

# Import AI testing contracts
from ai_testing.interfaces.service_contracts import (
    QualityMetric,
    TestScenario,
    TestType,
)

# Import Novel-Engine patterns
from pydantic import BaseModel, Field

from src.event_bus import EventBus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Scenario Management Models ===


class ScenarioCategory(str, Enum):
    """Test scenario categories"""

    SMOKE = "smoke"
    REGRESSION = "regression"
    INTEGRATION = "integration"
    PERFORMANCE = "performance"
    SECURITY = "security"
    ACCESSIBILITY = "accessibility"
    AI_QUALITY = "ai_quality"
    USER_JOURNEY = "user_journey"


class ScenarioComplexity(str, Enum):
    """Scenario complexity levels"""

    SIMPLE = "simple"  # Single API call or basic UI interaction
    MODERATE = "moderate"  # Multiple steps, some dependencies
    COMPLEX = "complex"  # Cross-service integration, AI validation
    ADVANCED = "advanced"  # Full user journeys, multi-modal testing


@dataclass
class ScenarioTemplate:
    """Template for generating test scenarios"""

    name: str
    description: str
    category: ScenarioCategory
    complexity: ScenarioComplexity
    test_type: TestType

    # Template configuration
    config_template: Dict[str, Any] = field(default_factory=dict)
    parameter_placeholders: List[str] = field(default_factory=list)

    # Metadata
    tags: Set[str] = field(default_factory=set)
    prerequisites: List[str] = field(default_factory=list)
    estimated_duration_minutes: int = 5

    # AI generation hints
    ai_generation_hints: Dict[str, str] = field(default_factory=dict)


class ScenarioCollection(BaseModel):
    """Collection of related test scenarios"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    version: str = "1.0.0"

    scenarios: List[TestScenario] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Collection properties
    total_estimated_minutes: int = 0
    category_distribution: Dict[ScenarioCategory, int] = Field(default_factory=dict)
    complexity_distribution: Dict[ScenarioComplexity, int] = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


# === AI Scenario Generator ===


class AIScenarioGenerator:
    """
    AI-powered test scenario generator

    Uses Gemini AI to generate comprehensive test scenarios based on:
    - Novel-Engine API specifications
    - User journey patterns
    - Quality assessment requirements
    - Performance and security considerations
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.gemini_api_key = config.get("gemini_api_key")
        self.http_client: Optional[httpx.AsyncClient] = None

        # Generation parameters
        self.creativity_temperature = config.get("scenario_generation", {}).get(
            "creativity", 0.7
        )
        self.max_scenarios_per_request = config.get("scenario_generation", {}).get(
            "max_per_request", 10
        )

        logger.info("AI Scenario Generator initialized")

    async def initialize(self):
        """Initialize AI generator resources"""
        self.http_client = httpx.AsyncClient(timeout=60.0)

    async def cleanup(self):
        """Clean up generator resources"""
        if self.http_client:
            await self.http_client.aclose()

    async def generate_scenarios_for_api(
        self,
        api_spec: Dict[str, Any],
        scenario_count: int = 5,
        focus_areas: List[str] = None,
    ) -> List[TestScenario]:
        """Generate test scenarios for API endpoints"""

        if not self.gemini_api_key:
            logger.warning(
                "Gemini API key not configured, using template-based generation"
            )
            return self._generate_template_scenarios(api_spec, scenario_count)

        prompt = self._create_api_scenario_prompt(
            api_spec, scenario_count, focus_areas or []
        )

        try:
            ai_response = await self._call_gemini_for_scenarios(prompt)
            scenarios = self._parse_ai_scenario_response(ai_response)

            logger.info(f"Generated {len(scenarios)} AI scenarios for API")
            return scenarios

        except Exception as e:
            logger.error(f"AI scenario generation failed: {e}")
            return self._generate_template_scenarios(api_spec, scenario_count)

    async def generate_user_journey_scenarios(
        self,
        journey_description: str,
        user_personas: List[str] = None,
        complexity_level: ScenarioComplexity = ScenarioComplexity.MODERATE,
    ) -> List[TestScenario]:
        """Generate comprehensive user journey test scenarios"""

        prompt = self._create_user_journey_prompt(
            journey_description, user_personas or ["default_user"], complexity_level
        )

        try:
            ai_response = await self._call_gemini_for_scenarios(prompt)
            scenarios = self._parse_ai_scenario_response(ai_response)

            logger.info(f"Generated {len(scenarios)} user journey scenarios")
            return scenarios

        except Exception as e:
            logger.error(f"User journey generation failed: {e}")
            return self._generate_default_user_journey(journey_description)

    async def generate_ai_quality_scenarios(
        self, ai_features: List[str], quality_focus: List[QualityMetric] = None
    ) -> List[TestScenario]:
        """Generate AI quality assessment scenarios"""

        quality_metrics = quality_focus or list(QualityMetric)
        prompt = self._create_ai_quality_prompt(ai_features, quality_metrics)

        try:
            ai_response = await self._call_gemini_for_scenarios(prompt)
            scenarios = self._parse_ai_scenario_response(ai_response)

            logger.info(f"Generated {len(scenarios)} AI quality scenarios")
            return scenarios

        except Exception as e:
            logger.error(f"AI quality scenario generation failed: {e}")
            return self._generate_default_ai_quality_scenarios(ai_features)

    def _create_api_scenario_prompt(
        self, api_spec: Dict[str, Any], scenario_count: int, focus_areas: List[str]
    ) -> str:
        """Create AI prompt for API scenario generation"""

        endpoints = api_spec.get("endpoints", [])
        focus_text = f"Focus on: {', '.join(focus_areas)}" if focus_areas else ""

        prompt = f"""
        Generate {scenario_count} comprehensive test scenarios for this Novel-Engine API:

        API Endpoints:
        {json.dumps(endpoints, indent=2)}

        {focus_text}

        For each scenario, provide:
        1. Scenario name and description
        2. Test type (api, ui, ai_quality, integration, performance)
        3. Priority (1-10)
        4. Detailed test configuration
        5. Expected outcomes and validation criteria
        6. Quality thresholds for AI features

        Consider these Novel-Engine specific aspects:
        - Character simulation and AI decision-making
        - Story generation and narrative quality
        - Multi-agent interactions and event bus patterns
        - Real-time simulation execution
        - Performance under AI workloads

        Generate scenarios that cover:
        - Happy path and edge cases
        - Error handling and resilience
        - Performance under load
        - AI output quality and consistency
        - Security and input validation

        Return as JSON array with this structure:
        [
          {{
            "name": "scenario name",
            "description": "detailed description",
            "test_type": "api|ui|ai_quality|integration|performance",
            "priority": 1-10,
            "timeout_seconds": 30-300,
            "config": {{
              "api_spec": {{"endpoint": "/path", "method": "GET", ...}},
              "expected_outcomes": ["outcome1", "outcome2"],
              "quality_thresholds": {{"coherence": 0.8, "safety": 0.9}}
            }}
          }}
        ]
        """

        return prompt

    def _create_user_journey_prompt(
        self,
        journey_description: str,
        user_personas: List[str],
        complexity_level: ScenarioComplexity,
    ) -> str:
        """Create AI prompt for user journey scenario generation"""

        prompt = f"""
        Generate comprehensive user journey test scenarios for Novel-Engine:

        Journey Description: {journey_description}
        User Personas: {', '.join(user_personas)}
        Complexity Level: {complexity_level.value}

        Novel-Engine is an AI-powered interactive story generation system with:
        - React frontend for simulation control
        - FastAPI backend with character management
        - Multi-agent AI for character decision-making
        - Real-time story generation and narrative creation

        Generate scenarios that test complete user workflows:
        1. User authentication and onboarding
        2. Character selection and customization
        3. Simulation configuration and execution
        4. Real-time interaction and decision-making
        5. Story generation and narrative viewing
        6. Results sharing and campaign management

        For each scenario, include:
        - Multi-step user actions (UI interactions)
        - API calls and data validation
        - AI quality assessment for generated content
        - Performance measurement for user experience
        - Accessibility and usability validation

        Return as JSON array with detailed step-by-step scenarios.
        """

        return prompt

    def _create_ai_quality_prompt(
        self, ai_features: List[str], quality_metrics: List[QualityMetric]
    ) -> str:
        """Create AI prompt for quality assessment scenarios"""

        metrics_text = ", ".join([m.value for m in quality_metrics])

        prompt = f"""
        Generate AI quality assessment scenarios for Novel-Engine features:

        AI Features to Test: {', '.join(ai_features)}
        Quality Metrics: {metrics_text}

        Novel-Engine AI capabilities include:
        - Character AI decision-making with Gemini API
        - Dynamic story generation and narrative creation
        - Multi-agent interaction and dialogue
        - Context-aware character behavior
        - Adaptive storytelling based on user preferences

        Generate scenarios that assess:
        1. AI output coherence and logical consistency
        2. Creative quality and narrative engagement
        3. Character authenticity and personality consistency
        4. Safety and content appropriateness
        5. Relevance to context and user input
        6. Consistency across multiple generations

        Each scenario should include:
        - Specific AI prompts and inputs
        - Expected output characteristics
        - Quality assessment criteria
        - Comparison baselines
        - Multi-model validation approach

        Use "LLM as a Judge" methodology for quality assessment.
        Return as JSON array with comprehensive quality scenarios.
        """

        return prompt

    async def _call_gemini_for_scenarios(self, prompt: str) -> str:
        """Call Gemini API for scenario generation"""
        # This would integrate with Novel-Engine's existing Gemini patterns
        # For now, return a mock response
        return """[
          {
            "name": "API Health Check Validation",
            "description": "Verify all API endpoints are responding correctly",
            "test_type": "api",
            "priority": 9,
            "timeout_seconds": 30,
            "config": {
              "api_spec": {
                "endpoint": "/health",
                "method": "GET",
                "expected_status": 200
              },
              "expected_outcomes": ["Service is healthy", "Response time < 1s"],
              "quality_thresholds": {}
            }
          }
        ]"""

    def _parse_ai_scenario_response(self, ai_response: str) -> List[TestScenario]:
        """Parse AI response into TestScenario objects"""
        try:
            scenarios_data = json.loads(ai_response)
            scenarios = []

            for scenario_data in scenarios_data:
                scenario = TestScenario(
                    name=scenario_data["name"],
                    description=scenario_data["description"],
                    test_type=TestType(scenario_data["test_type"]),
                    priority=scenario_data.get("priority", 5),
                    timeout_seconds=scenario_data.get("timeout_seconds", 30),
                    config=scenario_data.get("config", {}),
                    expected_outcomes=scenario_data.get("config", {}).get(
                        "expected_outcomes", []
                    ),
                    quality_thresholds={
                        QualityMetric(k): v
                        for k, v in scenario_data.get("config", {})
                        .get("quality_thresholds", {})
                        .items()
                        if k in [m.value for m in QualityMetric]
                    },
                )
                scenarios.append(scenario)

            return scenarios

        except Exception as e:
            logger.error(f"Failed to parse AI scenario response: {e}")
            return []

    def _generate_template_scenarios(
        self, api_spec: Dict[str, Any], scenario_count: int
    ) -> List[TestScenario]:
        """Generate scenarios using templates when AI is unavailable"""
        scenarios = []

        # Health check scenario
        scenarios.append(
            TestScenario(
                name="API Health Check",
                description="Verify API health endpoint responds correctly",
                test_type=TestType.API,
                priority=10,
                config={
                    "api_spec": {
                        "endpoint": "/health",
                        "method": "GET",
                        "expected_status": 200,
                        "response_time_threshold_ms": 1000,
                    }
                },
                expected_outcomes=["Service is healthy", "Fast response time"],
            )
        )

        # Character management scenario
        scenarios.append(
            TestScenario(
                name="Character List Retrieval",
                description="Test character listing functionality",
                test_type=TestType.API,
                priority=8,
                config={
                    "api_spec": {
                        "endpoint": "/characters",
                        "method": "GET",
                        "expected_status": 200,
                    }
                },
                expected_outcomes=["Returns character list", "Valid JSON structure"],
            )
        )

        # Simulation scenario
        scenarios.append(
            TestScenario(
                name="Basic Simulation Execution",
                description="Test simulation with default characters",
                test_type=TestType.INTEGRATION,
                priority=7,
                config={
                    "api_spec": {
                        "endpoint": "/simulations",
                        "method": "POST",
                        "request_body": {
                            "character_names": ["krieg", "ork"],
                            "turns": 3,
                        },
                        "expected_status": 200,
                    }
                },
                expected_outcomes=[
                    "Simulation completes",
                    "Story generated",
                    "Valid response structure",
                ],
            )
        )

        return scenarios[:scenario_count]

    def _generate_default_user_journey(
        self, journey_description: str
    ) -> List[TestScenario]:
        """Generate default user journey scenarios"""
        return [
            TestScenario(
                name="Complete User Journey",
                description=f"End-to-end test: {journey_description}",
                test_type=TestType.INTEGRATION,
                priority=8,
                config={
                    "user_journey": {
                        "steps": [
                            "Access application",
                            "Select characters",
                            "Configure simulation",
                            "Execute simulation",
                            "View results",
                        ]
                    }
                },
                expected_outcomes=[
                    "Journey completes successfully",
                    "User experience is smooth",
                ],
            )
        ]

    def _generate_default_ai_quality_scenarios(
        self, ai_features: List[str]
    ) -> List[TestScenario]:
        """Generate default AI quality scenarios"""
        scenarios = []

        for feature in ai_features:
            scenarios.append(
                TestScenario(
                    name=f"AI Quality Assessment - {feature}",
                    description=f"Assess quality of {feature} AI outputs",
                    test_type=TestType.AI_QUALITY,
                    priority=6,
                    config={
                        "ai_spec": {
                            "feature": feature,
                            "assessment_criteria": {
                                "coherence": "Output should be logically consistent",
                                "safety": "Content should be appropriate and safe",
                                "relevance": "Output should be relevant to input",
                            },
                        }
                    },
                    quality_thresholds={
                        QualityMetric.COHERENCE: 0.8,
                        QualityMetric.SAFETY: 0.9,
                        QualityMetric.RELEVANCE: 0.8,
                    },
                )
            )

        return scenarios


# === Scenario Manager ===


class ScenarioManager:
    """
    Comprehensive test scenario management system

    Features:
    - Scenario creation and validation
    - Collection management and organization
    - AI-powered scenario generation
    - Template-based scenario creation
    - Import/export capabilities
    - Scenario optimization and deduplication
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.event_bus = EventBus()
        self.ai_generator = AIScenarioGenerator(config)

        # Storage configuration
        self.scenarios_directory = Path(
            config.get("scenarios_directory", "ai_testing/scenarios")
        )
        self.templates_directory = Path(
            config.get("templates_directory", "ai_testing/templates")
        )

        # In-memory storage
        self.scenarios: Dict[str, TestScenario] = {}
        self.collections: Dict[str, ScenarioCollection] = {}
        self.templates: Dict[str, ScenarioTemplate] = {}

        # Ensure directories exist
        self.scenarios_directory.mkdir(parents=True, exist_ok=True)
        self.templates_directory.mkdir(parents=True, exist_ok=True)

        logger.info("Scenario Manager initialized")

    async def initialize(self):
        """Initialize scenario manager"""
        await self.ai_generator.initialize()
        await self._load_existing_scenarios()
        await self._load_templates()
        logger.info("Scenario Manager ready")

    async def cleanup(self):
        """Clean up scenario manager resources"""
        await self.ai_generator.cleanup()

    # === Scenario Management ===

    async def create_scenario(
        self,
        name: str,
        description: str,
        test_type: TestType,
        config: Dict[str, Any],
        **kwargs,
    ) -> TestScenario:
        """Create a new test scenario"""

        scenario = TestScenario(
            name=name,
            description=description,
            test_type=test_type,
            config=config,
            **kwargs,
        )

        # Validate scenario
        validation_errors = self._validate_scenario(scenario)
        if validation_errors:
            raise ValueError(f"Scenario validation failed: {validation_errors}")

        # Store scenario
        self.scenarios[scenario.id] = scenario
        await self._save_scenario(scenario)

        # Emit creation event
        await self.event_bus.publish(
            "scenario_created",
            {
                "scenario_id": scenario.id,
                "name": scenario.name,
                "test_type": scenario.test_type.value,
            },
        )

        logger.info(f"Scenario created: {name}")
        return scenario

    def get_scenario(self, scenario_id: str) -> Optional[TestScenario]:
        """Get scenario by ID"""
        return self.scenarios.get(scenario_id)

    def list_scenarios(
        self,
        test_type: Optional[TestType] = None,
        category: Optional[ScenarioCategory] = None,
        tags: Optional[List[str]] = None,
    ) -> List[TestScenario]:
        """List scenarios with optional filtering"""
        scenarios = list(self.scenarios.values())

        if test_type:
            scenarios = [s for s in scenarios if s.test_type == test_type]

        if category:
            scenarios = [
                s for s in scenarios if s.config.get("category") == category.value
            ]

        if tags:
            scenarios = [
                s
                for s in scenarios
                if any(tag in s.config.get("tags", []) for tag in tags)
            ]

        return sorted(scenarios, key=lambda s: s.priority, reverse=True)

    async def update_scenario(
        self, scenario_id: str, updates: Dict[str, Any]
    ) -> TestScenario:
        """Update existing scenario"""
        scenario = self.scenarios.get(scenario_id)
        if not scenario:
            raise ValueError(f"Scenario {scenario_id} not found")

        # Apply updates
        for key, value in updates.items():
            if hasattr(scenario, key):
                setattr(scenario, key, value)

        scenario.updated_at = datetime.now(timezone.utc)

        # Validate updated scenario
        validation_errors = self._validate_scenario(scenario)
        if validation_errors:
            raise ValueError(f"Updated scenario validation failed: {validation_errors}")

        # Save updated scenario
        await self._save_scenario(scenario)

        logger.info(f"Scenario updated: {scenario.name}")
        return scenario

    async def delete_scenario(self, scenario_id: str) -> bool:
        """Delete scenario"""
        if scenario_id not in self.scenarios:
            return False

        scenario = self.scenarios.pop(scenario_id)

        # Delete file
        scenario_file = self.scenarios_directory / f"{scenario_id}.json"
        if scenario_file.exists():
            scenario_file.unlink()

        logger.info(f"Scenario deleted: {scenario.name}")
        return True

    # === Collection Management ===

    async def create_collection(
        self, name: str, description: str, scenario_ids: List[str]
    ) -> ScenarioCollection:
        """Create a scenario collection"""

        # Validate scenario IDs
        scenarios = []
        for scenario_id in scenario_ids:
            scenario = self.scenarios.get(scenario_id)
            if not scenario:
                raise ValueError(f"Scenario {scenario_id} not found")
            scenarios.append(scenario)

        # Create collection
        collection = ScenarioCollection(
            name=name, description=description, scenarios=scenarios
        )

        # Calculate collection metrics
        collection.total_estimated_minutes = sum(
            s.timeout_seconds // 60 for s in scenarios
        )

        # Store collection
        self.collections[collection.id] = collection
        await self._save_collection(collection)

        logger.info(f"Collection created: {name} with {len(scenarios)} scenarios")
        return collection

    def get_collection(self, collection_id: str) -> Optional[ScenarioCollection]:
        """Get collection by ID"""
        return self.collections.get(collection_id)

    def list_collections(self) -> List[ScenarioCollection]:
        """List all collections"""
        return list(self.collections.values())

    # === AI-Powered Generation ===

    async def generate_scenarios_for_novel_engine(
        self, generation_type: str = "comprehensive", focus_areas: List[str] = None
    ) -> ScenarioCollection:
        """Generate comprehensive scenarios for Novel-Engine"""

        scenarios = []

        # API scenarios
        api_spec = await self._get_novel_engine_api_spec()
        api_scenarios = await self.ai_generator.generate_scenarios_for_api(
            api_spec, scenario_count=5, focus_areas=focus_areas
        )
        scenarios.extend(api_scenarios)

        # User journey scenarios
        user_journeys = [
            "Complete story generation workflow",
            "Character customization and simulation",
            "Multi-character interactive session",
        ]

        for journey in user_journeys:
            journey_scenarios = await self.ai_generator.generate_user_journey_scenarios(
                journey
            )
            scenarios.extend(journey_scenarios)

        # AI quality scenarios
        ai_features = [
            "Character decision-making",
            "Story generation",
            "Narrative transcription",
            "Multi-agent interaction",
        ]

        ai_scenarios = await self.ai_generator.generate_ai_quality_scenarios(
            ai_features
        )
        scenarios.extend(ai_scenarios)

        # Store scenarios
        for scenario in scenarios:
            self.scenarios[scenario.id] = scenario
            await self._save_scenario(scenario)

        # Create collection
        collection = await self.create_collection(
            name=f"Novel-Engine {generation_type.title()} Test Suite",
            description="AI-generated comprehensive test scenarios for Novel-Engine",
            scenario_ids=[s.id for s in scenarios],
        )

        logger.info(f"Generated {len(scenarios)} scenarios for Novel-Engine")
        return collection

    # === Import/Export ===

    async def export_collection(
        self, collection_id: str, format: str = "json", include_results: bool = False
    ) -> str:
        """Export collection to file"""
        collection = self.collections.get(collection_id)
        if not collection:
            raise ValueError(f"Collection {collection_id} not found")

        export_data = {
            "collection": collection.model_dump(),
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
            "format_version": "1.0",
        }

        if format == "json":
            export_content = json.dumps(export_data, indent=2, default=str)
        elif format == "yaml":
            export_content = yaml.dump(export_data, default_flow_style=False)
        else:
            raise ValueError(f"Unsupported export format: {format}")

        # Save to file
        export_file = self.scenarios_directory / f"export_{collection_id}.{format}"
        export_file.write_text(export_content)

        logger.info(f"Collection exported: {export_file}")
        return str(export_file)

    async def import_collection(self, file_path: str) -> ScenarioCollection:
        """Import collection from file"""
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Import file not found: {file_path}")

        content = file_path.read_text()

        if file_path.suffix == ".json":
            import_data = json.loads(content)
        elif file_path.suffix in [".yaml", ".yml"]:
            import_data = yaml.safe_load(content)
        else:
            raise ValueError(f"Unsupported import format: {file_path.suffix}")

        collection_data = import_data["collection"]
        collection = ScenarioCollection(**collection_data)

        # Import scenarios
        for scenario_data in collection.scenarios:
            scenario = TestScenario(**scenario_data)
            self.scenarios[scenario.id] = scenario
            await self._save_scenario(scenario)

        # Store collection
        self.collections[collection.id] = collection
        await self._save_collection(collection)

        logger.info(f"Collection imported: {collection.name}")
        return collection

    # === Utility Methods ===

    def _validate_scenario(self, scenario: TestScenario) -> List[str]:
        """Validate scenario configuration"""
        errors = []

        # Basic validation
        if not scenario.name.strip():
            errors.append("Scenario name cannot be empty")

        if not scenario.description.strip():
            errors.append("Scenario description cannot be empty")

        if scenario.timeout_seconds <= 0:
            errors.append("Timeout must be positive")

        if not 1 <= scenario.priority <= 10:
            errors.append("Priority must be between 1 and 10")

        # Type-specific validation
        if scenario.test_type == TestType.API:
            api_spec = scenario.config.get("api_spec", {})
            if not api_spec.get("endpoint"):
                errors.append("API test requires endpoint configuration")

        elif scenario.test_type == TestType.UI:
            ui_spec = scenario.config.get("ui_spec", {})
            if not ui_spec.get("page_url"):
                errors.append("UI test requires page_url configuration")

        elif scenario.test_type == TestType.AI_QUALITY:
            ai_spec = scenario.config.get("ai_spec", {})
            if not ai_spec.get("input_prompt"):
                errors.append("AI quality test requires input_prompt")

        return errors

    async def _save_scenario(self, scenario: TestScenario):
        """Save scenario to file"""
        scenario_file = self.scenarios_directory / f"{scenario.id}.json"
        scenario_file.write_text(scenario.model_dump_json(indent=2))

    async def _save_collection(self, collection: ScenarioCollection):
        """Save collection to file"""
        collection_file = self.scenarios_directory / f"collection_{collection.id}.json"
        collection_file.write_text(collection.model_dump_json(indent=2))

    async def _load_existing_scenarios(self):
        """Load existing scenarios from files"""
        for scenario_file in self.scenarios_directory.glob("*.json"):
            if scenario_file.name.startswith("collection_"):
                continue

            try:
                scenario_data = json.loads(scenario_file.read_text())
                scenario = TestScenario(**scenario_data)
                self.scenarios[scenario.id] = scenario
            except Exception as e:
                logger.warning(f"Failed to load scenario {scenario_file}: {e}")

        logger.info(f"Loaded {len(self.scenarios)} existing scenarios")

    async def _load_templates(self):
        """Load scenario templates"""
        # This would load predefined templates
        logger.info("Scenario templates loaded")

    async def _get_novel_engine_api_spec(self) -> Dict[str, Any]:
        """Get Novel-Engine API specification"""
        # This would extract API spec from the actual API server
        return {
            "endpoints": [
                {"path": "/health", "method": "GET", "description": "Health check"},
                {
                    "path": "/characters",
                    "method": "GET",
                    "description": "List characters",
                },
                {
                    "path": "/characters/{id}",
                    "method": "GET",
                    "description": "Get character",
                },
                {
                    "path": "/simulations",
                    "method": "POST",
                    "description": "Run simulation",
                },
                {
                    "path": "/campaigns",
                    "method": "GET",
                    "description": "List campaigns",
                },
                {
                    "path": "/campaigns",
                    "method": "POST",
                    "description": "Create campaign",
                },
            ]
        }


# === Export Manager Components ===

__all__ = [
    "ScenarioManager",
    "AIScenarioGenerator",
    "ScenarioCollection",
    "ScenarioTemplate",
    "ScenarioCategory",
    "ScenarioComplexity",
]
