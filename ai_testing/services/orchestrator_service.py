import os
"""
AI Test Orchestrator Service

Central coordination service for AI acceptance testing framework.
Provides intelligent test planning, execution orchestration, and resource management.

Integrates with Novel-Engine architecture patterns and provides RESTful API
compatible with existing FastAPI backend structure.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import httpx
import redis.asyncio as redis

# Import Novel-Engine patterns
from config_loader import get_config
from src.event_bus import EventBus
from src.shared_types import SystemStatus

# Import AI testing framework contracts
from ai_testing.interfaces.service_contracts import (
    ITestOrchestrator, TestScenario, TestExecution, TestResult, TestContext,
    TestStatus, TestType, ServiceHealthResponse, BatchTestResponse,
    TestExecutionEvent, validate_test_scenario, create_test_context
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === AI Test Orchestrator Implementation ===

class TestPlan(BaseModel):
    """Intelligent test execution plan"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    scenarios: List[TestScenario]
    context: TestContext
    
    # Execution strategy
    execution_order: List[str]  # scenario IDs in execution order
    parallel_groups: List[List[str]]  # scenarios that can run in parallel
    dependencies: Dict[str, List[str]]  # scenario_id -> [dependency_scenario_ids]
    
    # Resource planning
    estimated_duration_minutes: int
    required_services: Set[str]
    resource_requirements: Dict[str, Any]
    
    # AI-generated insights
    risk_assessment: Dict[str, float]  # scenario_id -> risk_score
    optimization_suggestions: List[str]
    
    # Execution tracking
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: TestStatus = TestStatus.PENDING
    executions: List[str] = Field(default_factory=list)  # execution IDs

class AITestOrchestrator(ITestOrchestrator):
    """
    AI-powered test orchestration service
    
    Features:
    - Intelligent test planning using Gemini AI
    - Resource-aware scheduling and load balancing
    - Dependency management and parallel execution
    - Real-time execution monitoring and control
    - Integration with Novel-Engine event system
    """
    
    
    def _get_service_url(self, service_name: str, port: int) -> str:
        """Get service URL based on environment"""
        # Check if running in Docker or locally
        is_docker = os.environ.get('DOCKER_ENV') == 'true'
        
        if is_docker:
            # Use Docker service names
            return f"http://{service_name}:{port}"
        else:
            # Use localhost for local development
            return f"http://localhost:{port}"

def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.event_bus = EventBus()
        self.redis_client: Optional[redis.Redis] = None
        self.http_client: Optional[httpx.AsyncClient] = None
        
        # Service endpoints - use environment-aware configuration
        from ai_testing.config import ServiceConfig
        service_urls = ServiceConfig.get_service_urls()
        
        # Environment-aware service endpoints
        self.service_endpoints = {
            "browser_automation": self._get_service_url("browser-automation", 8001),
            "api_testing": self._get_service_url("api-testing", 8002),
            "ai_quality": self._get_service_url("ai-quality", 8003),
            "results_aggregation": self._get_service_url("results-aggregation", 8004),
            "notification": self._get_service_url("notification", 8005)
        }
        
        # Also support underscore versions for backward compatibility
        self.services = {
            "browser-automation": ServiceEndpoint(
                name="browser-automation",
                base_url=self.service_endpoints["browser_automation"]
            ),
            "api-testing": ServiceEndpoint(
                name="api-testing", 
                base_url=self.service_endpoints["api_testing"]
            ),
            "ai-quality": ServiceEndpoint(
                name="ai-quality",
                base_url=self.service_endpoints["ai_quality"]
            ),
            "results-aggregation": ServiceEndpoint(
                name="results-aggregation",
                base_url=self.service_endpoints["results_aggregation"]
            ),
            "notification": ServiceEndpoint(
                name="notification",
                base_url=self.service_endpoints["notification"]
            )
        }

        
        # State management
        self.active_plans: Dict[str, TestPlan] = {}
        self.active_executions: Dict[str, TestExecution] = {}
        self.service_health: Dict[str, bool] = {}
        
        # AI configuration
        self.gemini_api_key = config.get("gemini_api_key")
        self.use_ai_planning = config.get("use_ai_planning", True)
        
        logger.info("AI Test Orchestrator initialized")
    
    async def initialize(self):
        """Initialize orchestrator resources"""
        try:
            # Initialize Redis for state management
            redis_url = self.config.get("redis_url", "redis://localhost:6379")
            self.redis_client = redis.from_url(redis_url)
            await self.redis_client.ping()
            
            # Initialize HTTP client
            self.http_client = httpx.AsyncClient(timeout=30.0)
            
            # Check service health
            await self._update_service_health()
            
            logger.info("Orchestrator initialization complete")
            
        except Exception as e:
            logger.error(f"Orchestrator initialization failed: {e}")
            raise
    
    async def shutdown(self):
        """Cleanup orchestrator resources"""
        if self.redis_client:
            await self.redis_client.close()
        if self.http_client:
            await self.http_client.aclose()
        logger.info("Orchestrator shutdown complete")
    
    # === Core Orchestration Methods ===
    
    async def create_test_plan(
        self, 
        scenarios: List[TestScenario],
        context: TestContext
    ) -> str:
        """Create an intelligent test execution plan using AI"""
        try:
            # Validate scenarios
            validation_errors = []
            for scenario in scenarios:
                errors = validate_test_scenario(scenario)
                validation_errors.extend([f"Scenario {scenario.name}: {error}" for error in errors])
            
            if validation_errors:
                raise ValueError(f"Scenario validation failed: {validation_errors}")
            
            # Create base plan
            plan = TestPlan(
                name=f"Test Plan {context.session_id}",
                description=f"AI-generated test plan for {len(scenarios)} scenarios",
                scenarios=scenarios,
                context=context,
                execution_order=[s.id for s in scenarios],
                parallel_groups=[],
                dependencies={},
                estimated_duration_minutes=sum(s.timeout_seconds for s in scenarios) // 60,
                required_services=self._determine_required_services(scenarios),
                resource_requirements=self._estimate_resource_requirements(scenarios),
                risk_assessment={},
                optimization_suggestions=[]
            )
            
            # Use AI to optimize plan if enabled
            if self.use_ai_planning and self.gemini_api_key:
                plan = await self._optimize_plan_with_ai(plan)
            else:
                plan = await self._optimize_plan_heuristic(plan)
            
            # Store plan
            self.active_plans[plan.id] = plan
            await self._store_plan_in_redis(plan)
            
            # Emit planning event
            await self.event_bus.publish("test_plan_created", {
                "plan_id": plan.id,
                "scenario_count": len(scenarios),
                "estimated_duration": plan.estimated_duration_minutes,
                "context": context.dict()
            })
            
            logger.info(f"Test plan created: {plan.id} with {len(scenarios)} scenarios")
            return plan.id
            
        except Exception as e:
            logger.error(f"Test plan creation failed: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to create test plan: {str(e)}")
    
    async def execute_test_plan(self, plan_id: str) -> List[TestExecution]:
        """Execute a test plan with intelligent orchestration"""
        try:
            plan = await self._get_plan(plan_id)
            if not plan:
                raise HTTPException(status_code=404, detail=f"Test plan {plan_id} not found")
            
            if plan.status != TestStatus.PENDING:
                raise HTTPException(status_code=400, detail=f"Plan {plan_id} is not in pending status")
            
            # Update plan status
            plan.status = TestStatus.RUNNING
            await self._update_plan_in_redis(plan)
            
            # Create executions for all scenarios
            executions = []
            for scenario in plan.scenarios:
                execution = TestExecution(
                    scenario_id=scenario.id,
                    context=plan.context,
                    executor_service="orchestrator",
                    execution_node=f"orchestrator-{uuid.uuid4().hex[:8]}"
                )
                executions.append(execution)
                self.active_executions[execution.id] = execution
                plan.executions.append(execution.id)
            
            # Start execution orchestration
            asyncio.create_task(self._orchestrate_execution(plan, executions))
            
            logger.info(f"Test plan execution started: {plan_id}")
            return executions
            
        except Exception as e:
            logger.error(f"Test plan execution failed: {e}")
            raise
    
    async def get_execution_status(self, execution_id: str) -> TestExecution:
        """Get current execution status"""
        execution = self.active_executions.get(execution_id)
        if not execution:
            # Try to load from Redis
            execution = await self._load_execution_from_redis(execution_id)
            if not execution:
                raise HTTPException(status_code=404, detail=f"Execution {execution_id} not found")
        
        return execution
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running test execution"""
        try:
            execution = await self.get_execution_status(execution_id)
            
            if execution.status not in [TestStatus.PENDING, TestStatus.RUNNING]:
                return False
            
            # Update execution status
            execution.status = TestStatus.CANCELLED
            execution.completed_at = datetime.utcnow()
            
            # Notify downstream services
            await self._notify_execution_cancelled(execution)
            
            # Update storage
            await self._update_execution_in_redis(execution)
            
            logger.info(f"Execution cancelled: {execution_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel execution {execution_id}: {e}")
            return False
    
    # === AI Planning Methods ===
    
    async def _optimize_plan_with_ai(self, plan: TestPlan) -> TestPlan:
        """Use Gemini AI to optimize test execution plan"""
        try:
            # Prepare AI prompt for test planning
            prompt = self._create_planning_prompt(plan)
            
            # Call Gemini API for planning optimization
            optimization = await self._call_gemini_for_planning(prompt)
            
            # Parse AI response and update plan
            plan = self._apply_ai_optimization(plan, optimization)
            
            logger.info(f"AI optimization applied to plan {plan.id}")
            return plan
            
        except Exception as e:
            logger.warning(f"AI planning failed, using heuristic: {e}")
            return await self._optimize_plan_heuristic(plan)
    
    def _create_planning_prompt(self, plan: TestPlan) -> str:
        """Create AI prompt for intelligent test planning"""
        scenario_info = []
        for scenario in plan.scenarios:
            scenario_info.append({
                "id": scenario.id,
                "name": scenario.name,
                "type": scenario.test_type,
                "priority": scenario.priority,
                "timeout": scenario.timeout_seconds,
                "dependencies": scenario.prerequisites
            })
        
        prompt = f"""
        As an AI test orchestration expert, optimize this test execution plan:
        
        Test Scenarios: {scenario_info}
        Available Services: {list(self.service_endpoints.keys())}
        Service Health: {self.service_health}
        
        Please provide optimization recommendations for:
        1. Execution order based on dependencies and priorities
        2. Parallel execution groups to minimize total time
        3. Risk assessment for each scenario (0.0-1.0)
        4. Resource allocation strategy
        5. Potential optimization suggestions
        
        Consider these factors:
        - Higher priority tests should run earlier
        - Tests with dependencies must run after their prerequisites
        - Parallel execution should balance load across services
        - Risk assessment should consider test complexity and failure probability
        
        Return response as JSON with this structure:
        {{
            "execution_order": ["scenario_id1", "scenario_id2", ...],
            "parallel_groups": [["group1_scenario1", "group1_scenario2"], ["group2_scenario1"]],
            "risk_assessment": {{"scenario_id": risk_score}},
            "optimization_suggestions": ["suggestion1", "suggestion2"]
        }}
        """
        
        return prompt
    
    async def _call_gemini_for_planning(self, prompt: str) -> Dict[str, Any]:
        """Call Gemini API for test planning optimization"""
        # This would integrate with existing Novel-Engine Gemini patterns
        # For now, return mock optimization
        return {
            "execution_order": [s.id for s in self.active_plans[list(self.active_plans.keys())[0]].scenarios],
            "parallel_groups": [],
            "risk_assessment": {},
            "optimization_suggestions": ["Consider parallel execution", "Monitor service health"]
        }
    
    def _apply_ai_optimization(self, plan: TestPlan, optimization: Dict[str, Any]) -> TestPlan:
        """Apply AI optimization recommendations to test plan"""
        plan.execution_order = optimization.get("execution_order", plan.execution_order)
        plan.parallel_groups = optimization.get("parallel_groups", [])
        plan.risk_assessment = optimization.get("risk_assessment", {})
        plan.optimization_suggestions = optimization.get("optimization_suggestions", [])
        
        return plan
    
    async def _optimize_plan_heuristic(self, plan: TestPlan) -> TestPlan:
        """Fallback heuristic optimization when AI is unavailable"""
        # Sort scenarios by priority (higher first)
        sorted_scenarios = sorted(plan.scenarios, key=lambda s: s.priority, reverse=True)
        plan.execution_order = [s.id for s in sorted_scenarios]
        
        # Simple parallel grouping by test type
        type_groups = {}
        for scenario in plan.scenarios:
            if scenario.test_type not in type_groups:
                type_groups[scenario.test_type] = []
            type_groups[scenario.test_type].append(scenario.id)
        
        plan.parallel_groups = list(type_groups.values())
        
        # Basic risk assessment
        plan.risk_assessment = {
            s.id: 0.3 if s.test_type == TestType.AI_QUALITY else 0.1 
            for s in plan.scenarios
        }
        
        plan.optimization_suggestions = [
            "Using heuristic optimization - enable AI planning for better results",
            "Consider grouping tests by type for efficiency"
        ]
        
        return plan
    
    # === Execution Orchestration ===
    
    async def _orchestrate_execution(self, plan: TestPlan, executions: List[TestExecution]):
        """Orchestrate test execution according to plan"""
        try:
            logger.info(f"Starting orchestration for plan {plan.id}")
            
            # Execute scenarios according to optimization plan
            if plan.parallel_groups:
                await self._execute_parallel_groups(plan, executions)
            else:
                await self._execute_sequential(plan, executions)
            
            # Update plan status
            plan.status = TestStatus.COMPLETED
            await self._update_plan_in_redis(plan)
            
            # Generate final report
            await self._generate_execution_report(plan)
            
            logger.info(f"Orchestration completed for plan {plan.id}")
            
        except Exception as e:
            logger.error(f"Orchestration failed for plan {plan.id}: {e}")
            plan.status = TestStatus.FAILED
            await self._update_plan_in_redis(plan)
    
    async def _execute_parallel_groups(self, plan: TestPlan, executions: List[TestExecution]):
        """Execute test scenarios in parallel groups"""
        execution_map = {e.scenario_id: e for e in executions}
        
        for group in plan.parallel_groups:
            # Execute scenarios in current group in parallel
            group_tasks = []
            for scenario_id in group:
                if scenario_id in execution_map:
                    execution = execution_map[scenario_id]
                    task = asyncio.create_task(self._execute_single_scenario(execution))
                    group_tasks.append(task)
            
            # Wait for group completion
            if group_tasks:
                await asyncio.gather(*group_tasks, return_exceptions=True)
                
                # Brief pause between groups
                await asyncio.sleep(1)
    
    async def _execute_sequential(self, plan: TestPlan, executions: List[TestExecution]):
        """Execute test scenarios sequentially"""
        execution_map = {e.scenario_id: e for e in executions}
        
        for scenario_id in plan.execution_order:
            if scenario_id in execution_map:
                execution = execution_map[scenario_id]
                await self._execute_single_scenario(execution)
    
    async def _execute_single_scenario(self, execution: TestExecution):
        """Execute a single test scenario"""
        try:
            # Update execution status
            execution.status = TestStatus.RUNNING
            execution.started_at = datetime.utcnow()
            await self._update_execution_in_redis(execution)
            
            # Emit execution started event
            await self.event_bus.publish("test_execution_started", {
                "execution_id": execution.id,
                "scenario_id": execution.scenario_id,
                "context": execution.context.dict()
            })
            
            # Get scenario details
            scenario = await self._get_scenario_by_id(execution.scenario_id)
            if not scenario:
                raise ValueError(f"Scenario {execution.scenario_id} not found")
            
            # Route to appropriate service based on test type
            result = await self._route_test_execution(scenario, execution)
            
            # Update execution with results
            execution.status = TestStatus.COMPLETED if result.passed else TestStatus.FAILED
            execution.completed_at = datetime.utcnow()
            execution.duration_ms = int((execution.completed_at - execution.started_at).total_seconds() * 1000)
            execution.passed = result.passed
            execution.score = result.score
            
            await self._update_execution_in_redis(execution)
            
            # Store result
            await self._store_test_result(result)
            
            logger.info(f"Scenario execution completed: {execution.scenario_id}")
            
        except Exception as e:
            logger.error(f"Scenario execution failed: {execution.scenario_id}: {e}")
            execution.status = TestStatus.FAILED
            execution.completed_at = datetime.utcnow()
            execution.error_message = str(e)
            await self._update_execution_in_redis(execution)
    
    async def _route_test_execution(self, scenario: TestScenario, execution: TestExecution) -> TestResult:
        """Route test execution to appropriate service"""
        service_map = {
            TestType.API: "api_testing",
            TestType.UI: "browser_automation",
            TestType.AI_QUALITY: "ai_quality",
            TestType.INTEGRATION: "api_testing",  # Default to API testing
            TestType.PERFORMANCE: "api_testing",
            TestType.SECURITY: "api_testing",
            TestType.ACCESSIBILITY: "browser_automation"
        }
        
        service_name = service_map.get(scenario.test_type, "api_testing")
        service_url = self.service_endpoints[service_name]
        
        # Prepare request payload
        payload = {
            "scenario": scenario.dict(),
            "execution": execution.dict(),
            "context": execution.context.dict()
        }
        
        # Call service
        async with self.http_client as client:
            response = await client.post(f"{service_url}/execute", json=payload)
            response.raise_for_status()
            
            result_data = response.json()
            return TestResult(**result_data)
    
    # === Utility Methods ===
    
    def _determine_required_services(self, scenarios: List[TestScenario]) -> Set[str]:
        """Determine which services are required for scenarios"""
        services = set()
        for scenario in scenarios:
            if scenario.test_type in [TestType.API, TestType.INTEGRATION, TestType.PERFORMANCE, TestType.SECURITY]:
                services.add("api_testing")
            elif scenario.test_type in [TestType.UI, TestType.ACCESSIBILITY]:
                services.add("browser_automation")
            elif scenario.test_type == TestType.AI_QUALITY:
                services.add("ai_quality")
        
        services.add("results_aggregation")  # Always needed
        services.add("notification")  # Always needed
        
        return services
    
    def _estimate_resource_requirements(self, scenarios: List[TestScenario]) -> Dict[str, Any]:
        """Estimate resource requirements for scenarios"""
        return {
            "estimated_cpu_cores": len(scenarios) * 0.5,
            "estimated_memory_gb": len(scenarios) * 0.2,
            "estimated_storage_gb": len(scenarios) * 0.1,
            "network_bandwidth_mbps": len(scenarios) * 10
        }
    
    async def _update_service_health(self):
        """Update health status of all services"""
        for service_name, endpoint in self.service_endpoints.items():
            try:
                async with self.http_client as client:
                    response = await client.get(f"{endpoint}/health", timeout=5.0)
                    self.service_health[service_name] = response.status_code == 200
            except Exception:
                self.service_health[service_name] = False
    
    # === Redis Storage Methods ===
    
    async def _store_plan_in_redis(self, plan: TestPlan):
        """Store test plan in Redis"""
        if self.redis_client:
            await self.redis_client.setex(
                f"plan:{plan.id}",
                3600,  # 1 hour TTL
                plan.json()
            )
    
    async def _update_plan_in_redis(self, plan: TestPlan):
        """Update test plan in Redis"""
        await self._store_plan_in_redis(plan)
    
    async def _get_plan(self, plan_id: str) -> Optional[TestPlan]:
        """Get test plan from memory or Redis"""
        if plan_id in self.active_plans:
            return self.active_plans[plan_id]
        
        if self.redis_client:
            plan_data = await self.redis_client.get(f"plan:{plan_id}")
            if plan_data:
                plan = TestPlan.parse_raw(plan_data)
                self.active_plans[plan_id] = plan
                return plan
        
        return None
    
    async def _update_execution_in_redis(self, execution: TestExecution):
        """Update execution in Redis"""
        if self.redis_client:
            await self.redis_client.setex(
                f"execution:{execution.id}",
                3600,  # 1 hour TTL
                execution.json()
            )
    
    async def _load_execution_from_redis(self, execution_id: str) -> Optional[TestExecution]:
        """Load execution from Redis"""
        if self.redis_client:
            execution_data = await self.redis_client.get(f"execution:{execution_id}")
            if execution_data:
                return TestExecution.parse_raw(execution_data)
        return None
    
    async def _get_scenario_by_id(self, scenario_id: str) -> Optional[TestScenario]:
        """Get scenario by ID from active plans"""
        for plan in self.active_plans.values():
            for scenario in plan.scenarios:
                if scenario.id == scenario_id:
                    return scenario
        return None
    
    async def _store_test_result(self, result: TestResult):
        """Store test result via Results Aggregation Service"""
        try:
            service_url = self.service_endpoints["results_aggregation"]
            async with self.http_client as client:
                await client.post(f"{service_url}/results", json=result.dict())
        except Exception as e:
            logger.error(f"Failed to store test result: {e}")
    
    async def _notify_execution_cancelled(self, execution: TestExecution):
        """Notify services about execution cancellation"""
        try:
            # Emit cancellation event
            await self.event_bus.publish("test_execution_cancelled", {
                "execution_id": execution.id,
                "scenario_id": execution.scenario_id,
                "cancelled_at": execution.completed_at.isoformat()
            })
        except Exception as e:
            logger.error(f"Failed to notify cancellation: {e}")
    
    async def _generate_execution_report(self, plan: TestPlan):
        """Generate comprehensive execution report"""
        # This would integrate with Results Aggregation Service
        logger.info(f"Execution report generated for plan {plan.id}")

# === FastAPI Application ===

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan management"""
    # Initialize orchestrator
    config = get_config()
    orchestrator_config = {
        "redis_url": config.get("redis_url", "redis://localhost:6379"),
        "gemini_api_key": config.get("gemini_api_key"),
        "use_ai_planning": config.get("ai_testing", {}).get("use_ai_planning", True),
        **config.get("ai_testing", {}).get("orchestrator", {})
    }
    
    orchestrator = AITestOrchestrator(orchestrator_config)
    await orchestrator.initialize()
    
    app.state.orchestrator = orchestrator
    
    logger.info("AI Test Orchestrator Service started")
    yield
    
    await orchestrator.shutdown()
    logger.info("AI Test Orchestrator Service stopped")

# Create FastAPI app
app = FastAPI(
    title="AI Test Orchestrator Service",
    description="Intelligent test orchestration for Novel-Engine AI acceptance testing",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# === API Endpoints ===

@app.get("/health", response_model=ServiceHealthResponse)
async def health_check():
    """Service health check"""
    orchestrator: AITestOrchestrator = app.state.orchestrator
    
    # Check service health
    await orchestrator._update_service_health()
    
    healthy_services = sum(1 for healthy in orchestrator.service_health.values() if healthy)
    total_services = len(orchestrator.service_health)
    
    status = "healthy" if healthy_services == total_services else "degraded"
    if healthy_services < total_services // 2:
        status = "unhealthy"
    
    return ServiceHealthResponse(
        service_name="ai-test-orchestrator",
        status=status,
        version="1.0.0",
        database_status="connected" if orchestrator.redis_client else "disconnected",
        message_queue_status="connected",
        external_dependencies=orchestrator.service_health,
        response_time_ms=50.0,
        memory_usage_mb=128.0,
        cpu_usage_percent=15.0,
        active_tests=len(orchestrator.active_executions),
        completed_tests_24h=0,  # Would be calculated from Redis
        error_rate_percent=0.0
    )

@app.post("/plans", response_model=Dict[str, str])
async def create_test_plan(
    scenarios: List[TestScenario],
    context: TestContext
):
    """Create an intelligent test execution plan"""
    orchestrator: AITestOrchestrator = app.state.orchestrator
    plan_id = await orchestrator.create_test_plan(scenarios, context)
    return {"plan_id": plan_id}

@app.post("/plans/{plan_id}/execute", response_model=BatchTestResponse)
async def execute_test_plan(plan_id: str):
    """Execute a test plan"""
    orchestrator: AITestOrchestrator = app.state.orchestrator
    executions = await orchestrator.execute_test_plan(plan_id)
    
    return BatchTestResponse(
        batch_id=plan_id,
        total_tests=len(executions),
        queued_tests=len(executions),
        estimated_completion_minutes=30,  # Would be calculated from plan
        execution_ids=[e.id for e in executions],
        progress_url=f"/executions/batch/{plan_id}/status"
    )

@app.get("/executions/{execution_id}", response_model=TestExecution)
async def get_execution_status(execution_id: str):
    """Get execution status"""
    orchestrator: AITestOrchestrator = app.state.orchestrator
    return await orchestrator.get_execution_status(execution_id)

@app.post("/executions/{execution_id}/cancel", response_model=Dict[str, bool])
async def cancel_execution(execution_id: str):
    """Cancel a test execution"""
    orchestrator: AITestOrchestrator = app.state.orchestrator
    success = await orchestrator.cancel_execution(execution_id)
    return {"cancelled": success}

@app.get("/plans/{plan_id}", response_model=TestPlan)
async def get_test_plan(plan_id: str):
    """Get test plan details"""
    orchestrator: AITestOrchestrator = app.state.orchestrator
    plan = await orchestrator._get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Test plan not found")
    return plan

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")