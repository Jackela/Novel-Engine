# M10 Observability & Security System Design

**Novel Engine Turn Orchestration - Enterprise Monitoring & Security Framework**

## Overview

M10 builds upon the sophisticated M9 Turn Orchestration system to add enterprise-grade observability and security capabilities. This system implements a comprehensive monitoring, tracing, and security framework that maintains performance while providing production-ready operational visibility and access control.

## Architecture Principles

### Core Design Philosophy
- **Performance-First**: <5% overhead with optimized middleware and instrumentation
- **Security-by-Design**: Zero-trust authentication with fine-grained authorization
- **Observability-Native**: Metrics and traces designed for production monitoring and debugging
- **Backward Compatible**: Non-intrusive integration preserving existing API contracts

### Integration Strategy
- **Incremental Enhancement**: Build on existing performance tracking without breaking changes
- **Middleware Stack**: Layered security and observability using FastAPI middleware patterns
- **Dependency Injection**: Leverage existing FastAPI Depends() for clean service orchestration
- **Event-Driven**: Integrate with Novel Engine's event architecture for comprehensive monitoring

## 📊 Component 1: Prometheus Metrics System

### Business Metrics Collection

**Primary KPIs**:
```python
# Core business metrics requested
novel_engine_llm_cost_per_request_dollars = Gauge(
    'novel_engine_llm_cost_per_request_dollars',
    'AI/LLM cost per turn execution request',
    ['phase', 'model_type', 'success']
)

novel_engine_turn_duration_seconds = Histogram(
    'novel_engine_turn_duration_seconds', 
    'Turn execution duration in seconds',
    ['phase', 'participants_count', 'ai_enabled'],
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 60.0, float('inf')]
)
```

**Extended Metrics Suite**:
```python
# Turn orchestration metrics
novel_engine_turns_total = Counter(
    'novel_engine_turns_total',
    'Total number of turn executions',
    ['status', 'participants_range']
)

novel_engine_turns_active = Gauge(
    'novel_engine_turns_active',
    'Number of currently executing turns'
)

# Phase-specific metrics  
novel_engine_phase_duration_seconds = Histogram(
    'novel_engine_phase_duration_seconds',
    'Phase execution duration',
    ['phase_type', 'success'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, float('inf')]
)

novel_engine_phase_events_processed_total = Counter(
    'novel_engine_phase_events_processed_total', 
    'Total events processed by phase',
    ['phase_type', 'event_type']
)

# AI integration metrics
novel_engine_ai_requests_total = Counter(
    'novel_engine_ai_requests_total',
    'Total AI/LLM requests made',
    ['provider', 'model', 'phase', 'status']
)

novel_engine_ai_token_usage_total = Counter(
    'novel_engine_ai_token_usage_total',
    'Total AI tokens consumed',
    ['provider', 'model', 'token_type']
)

# Saga pattern metrics
novel_engine_compensations_total = Counter(
    'novel_engine_compensations_total',
    'Total compensation actions executed', 
    ['compensation_type', 'success']
)

# Resource utilization
novel_engine_memory_usage_bytes = Gauge(
    'novel_engine_memory_usage_bytes',
    'Memory usage during turn execution'
)

novel_engine_concurrent_operations = Gauge(
    'novel_engine_concurrent_operations', 
    'Number of concurrent operations'
)
```

### Metrics Collection Integration

**Performance Tracker Enhancement**:
```python
# Enhanced PerformanceTracker with Prometheus integration
class EnhancedPerformanceTracker(PerformanceTracker):
    def __init__(self):
        super().__init__()
        self.prometheus_collector = PrometheusMetricsCollector()
        
    def track_turn_completion(self, turn: Turn, pipeline_result: PipelineResult):
        # Existing metrics collection
        performance_metrics = super().track_turn_completion(turn, pipeline_result)
        
        # Enhanced Prometheus metrics
        execution_time_seconds = performance_metrics['execution_time_ms'] / 1000
        
        novel_engine_turn_duration_seconds.labels(
            phase='complete',
            participants_count=self._get_participants_range(len(turn.participants)),
            ai_enabled=turn.configuration.ai_integration_enabled
        ).observe(execution_time_seconds)
        
        novel_engine_llm_cost_per_request_dollars.labels(
            phase='total',
            model_type='gpt-4',  # Derive from actual usage
            success=pipeline_result.was_fully_successful()
        ).set(float(performance_metrics['cost_analysis']['total_ai_cost']))
        
        return performance_metrics
```

### Metrics Endpoint Implementation
```python
# FastAPI /metrics endpoint
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
```

## 🔍 Component 2: OpenTelemetry Distributed Tracing

### Trace Architecture

**Root Span Strategy**:
```python
# Turn orchestration root span covering entire run_turn flow
@trace_async_operation("novel_engine.turn_execution")
async def execute_turn(self, participants: List[str], configuration: TurnConfiguration, turn_id: TurnId):
    with trace_context("turn_orchestration") as root_span:
        root_span.set_attribute("turn.id", str(turn_id.turn_uuid))
        root_span.set_attribute("turn.participants.count", len(participants))
        root_span.set_attribute("turn.ai_enabled", configuration.ai_integration_enabled)
        root_span.set_attribute("turn.narrative_depth", configuration.narrative_analysis_depth)
        
        # Execute 5-phase pipeline with nested spans
        pipeline_result = await self._execute_turn_pipeline(turn, root_span)
        
        # Set result attributes
        root_span.set_attribute("turn.success", pipeline_result.was_fully_successful())
        root_span.set_attribute("turn.completion_percentage", pipeline_result.get_completion_percentage())
        root_span.set_attribute("turn.total_cost", float(pipeline_result.total_ai_cost))
        
        return pipeline_result
```

**Phase-Level Spans**:
```python
# Individual phase spans as children of turn execution
async def _execute_turn_pipeline(self, turn: Turn, parent_span):
    phases = [
        ('world_update', self._execute_world_update_phase),
        ('subjective_brief', self._execute_subjective_brief_phase), 
        ('interaction_orchestration', self._execute_interaction_phase),
        ('event_integration', self._execute_event_integration_phase),
        ('narrative_integration', self._execute_narrative_integration_phase)
    ]
    
    for phase_name, phase_executor in phases:
        with trace_async_operation(f"novel_engine.phase.{phase_name}", parent=parent_span) as phase_span:
            phase_span.set_attribute("phase.order", len([p for p in phases if p[0] <= phase_name]))
            phase_span.set_attribute("turn.id", str(turn.turn_id))
            
            try:
                phase_result = await phase_executor(turn, phase_span)
                
                # Phase result attributes
                phase_span.set_attribute("phase.success", phase_result.was_successful())
                phase_span.set_attribute("phase.events_processed", len(phase_result.events_consumed))
                phase_span.set_attribute("phase.events_generated", len(phase_result.events_generated))
                phase_span.set_attribute("phase.ai_cost", float(phase_result.get_ai_cost()))
                
                if phase_result.error_details:
                    phase_span.set_attribute("phase.error", phase_result.error_details)
                    phase_span.set_status(trace.status.Status(trace.status.StatusCode.ERROR))
                
            except Exception as e:
                phase_span.record_exception(e)
                phase_span.set_status(trace.status.Status(trace.status.StatusCode.ERROR, str(e)))
                raise
```

### Cross-Context Trace Propagation
```python
# AI Gateway integration with trace context
class AIGatewayClient:
    async def generate_subjective_brief(self, agent_context, trace_context=None):
        with trace_async_operation("ai_gateway.subjective_brief", parent=trace_context) as span:
            span.set_attribute("ai.model", self.model_name)
            span.set_attribute("ai.agent", agent_context.agent_id)
            span.set_attribute("ai.prompt_length", len(agent_context.prompt))
            
            # Propagate trace context to external AI service
            headers = {'traceparent': span.get_trace_header()}
            response = await self.client.post('/generate', headers=headers, json=request_data)
            
            span.set_attribute("ai.tokens_used", response.json().get('token_usage', 0))
            span.set_attribute("ai.cost", response.json().get('cost', 0))
            
            return response.json()
```

### Trace Sampling Strategy
```python
# Intelligent sampling configuration
trace_config = TraceConfig(
    sampler=CompositeSampler([
        # Always sample errors and slow operations
        TraceBasedSampler(lambda trace: trace.has_error() or trace.duration > 10.0, 1.0),
        # Sample 10% of successful fast operations  
        TraceBasedSampler(lambda trace: not trace.has_error() and trace.duration <= 10.0, 0.1),
        # Sample 50% of operations with high AI cost
        TraceBasedSampler(lambda trace: trace.get_attribute('turn.total_cost', 0) > 1.0, 0.5)
    ])
)
```

## 🔐 Component 3: JWT Authentication Framework

### Token Structure
```python
# JWT payload structure for Novel Engine authentication
@dataclass
class NovelEngineJWTPayload:
    user_id: UUID
    username: str
    email: str
    roles: List[str]
    permissions: List[str]
    campaign_access: Dict[UUID, List[str]]  # campaign_id -> permissions
    iat: int  # Issued at
    exp: int  # Expiration
    aud: str = "novel-engine"  # Audience
    iss: str = "novel-engine-auth"  # Issuer
```

### Authentication Middleware
```python
class JWTAuthenticationMiddleware:
    def __init__(self, app: FastAPI, secret_key: str, algorithm: str = "HS256"):
        self.app = app
        self.secret_key = secret_key
        self.algorithm = algorithm
        
    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
            
        request = Request(scope, receive)
        
        # Skip authentication for public endpoints
        if self._is_public_endpoint(request.url.path):
            await self.app(scope, receive, send)
            return
            
        try:
            token = self._extract_token(request)
            payload = self._verify_token(token)
            user_info = UserInfo.from_jwt_payload(payload)
            
            # Add user context to request scope
            scope["user"] = user_info
            
            # Add authentication trace attributes
            if hasattr(scope, 'trace_context'):
                scope['trace_context'].set_attribute("auth.user_id", str(user_info.user_id))
                scope['trace_context'].set_attribute("auth.roles", user_info.roles)
            
            await self.app(scope, receive, send)
            
        except AuthenticationError as e:
            # Record authentication failure metric
            authentication_failures_total.labels(reason=e.reason).inc()
            
            response = JSONResponse(
                status_code=401,
                content={"detail": "Authentication failed", "error": str(e)}
            )
            await response(scope, receive, send)
```

### User Context Dependency
```python
# FastAPI dependency for user authentication
async def get_current_user(request: Request) -> UserInfo:
    """Extract current user from authenticated request."""
    if "user" not in request.scope:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
    return request.scope["user"]

async def get_optional_user(request: Request) -> Optional[UserInfo]:
    """Extract current user if authenticated, None otherwise.""" 
    return request.scope.get("user")
```

## 🛡️ Component 4: RBAC Authorization System

### Permission Model
```python
# Novel Engine permission structure
class Permission:
    STORY_READ = "story.read"
    STORY_EXECUTE = "story.execute" 
    STORY_ADMIN = "story.admin"
    
    TURN_VIEW = "orchestration.turn.view"
    TURN_EXECUTE = "orchestration.turn.execute"
    TURN_CANCEL = "orchestration.turn.cancel"
    TURN_DEBUG = "orchestration.turn.debug"
    
    CAMPAIGN_READ = "campaign.read"
    CAMPAIGN_WRITE = "campaign.write"
    CAMPAIGN_ADMIN = "campaign.admin"
    
    METRICS_VIEW = "metrics.view"
    METRICS_ADMIN = "metrics.admin"

# Role definitions
class Role:
    PLAYER = "player"
    STORY_MASTER = "story_master" 
    ADMIN = "admin"
    DEVELOPER = "developer"

ROLE_PERMISSIONS = {
    Role.PLAYER: [
        Permission.STORY_READ,
        Permission.TURN_VIEW
    ],
    Role.STORY_MASTER: [
        Permission.STORY_READ, Permission.STORY_EXECUTE,
        Permission.TURN_VIEW, Permission.TURN_EXECUTE, Permission.TURN_CANCEL,
        Permission.CAMPAIGN_READ, Permission.CAMPAIGN_WRITE
    ],
    Role.ADMIN: [
        # All permissions
        *[perm for perm in Permission.__dict__.values() if isinstance(perm, str)]
    ],
    Role.DEVELOPER: [
        Permission.STORY_READ, Permission.TURN_VIEW, Permission.TURN_DEBUG,
        Permission.METRICS_VIEW, Permission.METRICS_ADMIN
    ]
}
```

### RBAC Decorators and Dependencies
```python
# Permission requirement decorator
def require_permission(permission: str, campaign_id: str = None):
    """Decorator to require specific permission for endpoint access."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user from FastAPI dependency
            current_user: UserInfo = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(status_code=401, detail="Authentication required")
                
            # Check permission
            if not current_user.has_permission(permission, campaign_id):
                # Record authorization failure
                authorization_failures_total.labels(
                    permission=permission,
                    user_role=current_user.primary_role
                ).inc()
                
                raise HTTPException(
                    status_code=403, 
                    detail=f"Permission '{permission}' required"
                )
                
            # Add authorization trace attributes
            if 'trace_context' in kwargs:
                kwargs['trace_context'].set_attribute("authz.permission", permission)
                kwargs['trace_context'].set_attribute("authz.granted", True)
                
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# FastAPI dependency for permission checking
def require_permissions(*permissions: str):
    """FastAPI dependency factory for permission requirements."""
    async def permission_dependency(
        current_user: UserInfo = Depends(get_current_user)
    ) -> UserInfo:
        missing_permissions = [
            perm for perm in permissions 
            if not current_user.has_permission(perm)
        ]
        
        if missing_permissions:
            raise HTTPException(
                status_code=403,
                detail=f"Missing required permissions: {missing_permissions}"
            )
            
        return current_user
    
    return permission_dependency
```

### Campaign-Level Access Control
```python
# Campaign-scoped authorization
class CampaignAccessControl:
    def __init__(self, campaign_repository: CampaignRepository):
        self.campaign_repo = campaign_repository
        
    async def check_campaign_access(
        self, 
        user: UserInfo, 
        campaign_id: UUID, 
        required_permission: str
    ) -> bool:
        """Check if user has permission for specific campaign."""
        
        # Check global permissions first
        if user.has_permission(Permission.CAMPAIGN_ADMIN):
            return True
            
        # Check campaign-specific permissions
        campaign_permissions = user.campaign_access.get(campaign_id, [])
        return required_permission in campaign_permissions

def require_campaign_permission(permission: str):
    """Decorator for campaign-scoped permissions.""" 
    async def campaign_permission_dependency(
        campaign_id: UUID,
        current_user: UserInfo = Depends(get_current_user),
        access_control: CampaignAccessControl = Depends()
    ) -> UserInfo:
        has_access = await access_control.check_campaign_access(
            current_user, campaign_id, permission
        )
        
        if not has_access:
            raise HTTPException(
                status_code=403,
                detail=f"Campaign access denied: {permission}"
            )
            
        return current_user
    
    return campaign_permission_dependency
```

## 🔗 Integration Architecture

### FastAPI Application Enhancement
```python
# Complete middleware stack for M10
def create_m10_enhanced_app() -> FastAPI:
    app = FastAPI(
        title="Novel Engine Turn Orchestration API",
        description="M10 Enhanced with Observability & Security",
        version="2.0.0"
    )
    
    # Middleware stack (order matters - last added = first executed)
    app.add_middleware(
        PrometheusMiddleware,
        app_name="novel_engine_orchestration",
        group_paths=True
    )
    
    app.add_middleware(
        OpenTelemetryMiddleware,
        excluded_urls=["/health", "/metrics"]
    )
    
    app.add_middleware(
        SecurityHeadersMiddleware,
        force_https=True,
        hsts_max_age=31536000
    )
    
    app.add_middleware(
        RateLimitingMiddleware,
        calls=100,
        period=60  # 100 calls per minute
    )
    
    app.add_middleware(
        JWTAuthenticationMiddleware,
        secret_key=settings.jwt_secret_key,
        algorithm="HS256"
    )
    
    # Include routers with enhanced security
    app.include_router(
        turns_router,
        prefix="/v1/turns",
        tags=["Turn Orchestration"]
    )
    
    app.include_router(
        monitoring_router,
        prefix="/v1/monitoring", 
        tags=["Observability"]
    )
    
    return app
```

### Enhanced API Endpoints
```python
# Turn execution with full M10 integration
@router.post("/v1/turns:run")
@require_permission(Permission.TURN_EXECUTE)
async def execute_turn(
    request: TurnExecutionRequest,
    current_user: UserInfo = Depends(get_current_user),
    trace_context: TraceContext = Depends(get_trace_context)
) -> TurnExecutionResponse:
    """Execute turn with comprehensive observability and security."""
    
    # Metrics collection
    with turn_execution_duration.time():
        with trace_async_operation("api.turns.execute", parent=trace_context) as span:
            # Set trace attributes
            span.set_attribute("api.endpoint", "/v1/turns:run")
            span.set_attribute("api.method", "POST")
            span.set_attribute("user.id", str(current_user.user_id))
            span.set_attribute("user.role", current_user.primary_role)
            
            try:
                # Validate campaign access if specified
                if request.campaign_id:
                    await validate_campaign_access(current_user, request.campaign_id)
                
                # Execute turn orchestration
                orchestrator = get_turn_orchestrator()
                result = await orchestrator.execute_turn(
                    participants=request.participants,
                    configuration=request.configuration,
                    user_context=current_user,
                    trace_context=span
                )
                
                # Success metrics
                turns_executed_total.labels(
                    status="success",
                    user_role=current_user.primary_role,
                    participants_count=len(request.participants)
                ).inc()
                
                return TurnExecutionResponse.from_result(result)
                
            except Exception as e:
                # Error metrics and tracing
                turns_executed_total.labels(
                    status="error",
                    user_role=current_user.primary_role,
                    participants_count=len(request.participants)
                ).inc()
                
                span.record_exception(e)
                span.set_status(trace.status.Status(trace.status.StatusCode.ERROR, str(e)))
                
                raise HTTPException(
                    status_code=500,
                    detail=f"Turn execution failed: {str(e)}"
                )

# Metrics endpoint with security
@router.get("/metrics")
async def get_metrics(
    current_user: UserInfo = Depends(require_permissions(Permission.METRICS_VIEW))
):
    """Prometheus metrics endpoint with access control."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
```

## 🧪 Validation & Testing Strategy

### Metrics Validation Tests
```python
async def test_prometheus_metrics_collection():
    """Test that all required metrics are collected and exposed."""
    
    # Execute a turn and collect metrics
    client = TestClient(app)
    turn_response = client.post("/v1/turns:run", json=test_turn_request, headers=auth_headers)
    
    # Fetch metrics
    metrics_response = client.get("/metrics", headers=admin_headers)
    metrics_text = metrics_response.text
    
    # Validate required metrics are present
    assert "novel_engine_llm_cost_per_request_dollars" in metrics_text
    assert "novel_engine_turn_duration_seconds" in metrics_text
    assert "novel_engine_turns_total" in metrics_text
    
    # Validate metric values are reasonable
    cost_metric = extract_metric_value(metrics_text, "novel_engine_llm_cost_per_request_dollars")
    assert 0 <= cost_metric <= 10  # Reasonable cost range
    
    duration_metric = extract_metric_value(metrics_text, "novel_engine_turn_duration_seconds")
    assert 0 < duration_metric < 300  # Under 5 minutes
```

### Trace Validation Tests  
```python
async def test_opentelemetry_trace_coverage():
    """Test that turn execution generates proper trace spans."""
    
    # Setup trace collector
    trace_collector = InMemoryTraceCollector()
    
    # Execute turn
    result = await orchestrator.execute_turn(test_participants, test_config)
    
    # Validate trace structure
    traces = trace_collector.get_traces()
    assert len(traces) == 1
    
    root_span = traces[0].root_span
    assert root_span.name == "novel_engine.turn_execution"
    assert root_span.get_attribute("turn.participants.count") == len(test_participants)
    
    # Validate phase spans
    phase_spans = traces[0].get_spans_by_name_prefix("novel_engine.phase.")
    assert len(phase_spans) == 5  # All 5 phases covered
    
    phase_names = {span.name.split(".")[-1] for span in phase_spans}
    expected_phases = {"world_update", "subjective_brief", "interaction_orchestration", 
                      "event_integration", "narrative_integration"}
    assert phase_names == expected_phases
```

### Security Validation Tests
```python
async def test_jwt_authentication_enforcement():
    """Test that JWT authentication is properly enforced."""
    
    client = TestClient(app)
    
    # Test unauthenticated request
    response = client.post("/v1/turns:run", json=test_turn_request)
    assert response.status_code == 401
    
    # Test invalid token
    response = client.post("/v1/turns:run", json=test_turn_request, 
                          headers={"Authorization": "Bearer invalid_token"})
    assert response.status_code == 401
    
    # Test valid token
    valid_token = create_test_jwt_token(test_user_claims)
    response = client.post("/v1/turns:run", json=test_turn_request,
                          headers={"Authorization": f"Bearer {valid_token}"})
    assert response.status_code in [200, 202]

async def test_rbac_permission_enforcement():
    """Test that RBAC permissions are properly enforced."""
    
    # Test user without turn execution permission
    player_token = create_test_jwt_token({"roles": [Role.PLAYER]})
    response = client.post("/v1/turns:run", json=test_turn_request,
                          headers={"Authorization": f"Bearer {player_token}"})
    assert response.status_code == 403
    
    # Test user with turn execution permission
    sm_token = create_test_jwt_token({"roles": [Role.STORY_MASTER]})
    response = client.post("/v1/turns:run", json=test_turn_request,
                          headers={"Authorization": f"Bearer {sm_token}"})
    assert response.status_code in [200, 202]
```

## Performance Benchmarks

### Target Performance Metrics
- **Metrics Collection Overhead**: <1% additional latency
- **Trace Collection Overhead**: <3% additional latency  
- **Authentication Overhead**: <2% additional latency
- **Total M10 Overhead**: <5% additional latency vs M9 baseline

### Resource Utilization Targets
- **Memory Overhead**: <50MB additional memory usage
- **CPU Overhead**: <10% additional CPU usage during turn execution
- **Network Overhead**: <1KB additional request/response payload

This comprehensive design provides the technical foundation for implementing the M10 Observability & Security system with enterprise-grade monitoring, distributed tracing, and access control while maintaining the high performance standards of the Novel Engine platform.