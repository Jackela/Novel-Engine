# AI Context

## Overview
The AI Context serves as the central gateway for all Large Language Model (LLM) interactions within the Novel Engine platform. It provides a unified abstraction layer over multiple AI providers while enforcing policies for caching, rate limiting, cost tracking, and retry logic.

This context handles AI model provider management, request orchestration, and intelligent routing across different LLM backends (OpenAI, Anthropic, Ollama, etc.).

## Domain

### Aggregates
- **None**: This context is primarily service-oriented and does not maintain traditional aggregates.

### Entities
- **None**: Uses value objects for identity management.

### Value Objects
- **ProviderId**: Uniquely identifies LLM providers with support for official providers (OpenAI, Anthropic, Google, etc.) and custom providers
  - Encapsulates provider name, type, API version, and region
  - Validates provider naming conventions and region codes (ISO 3166-1 alpha-2)
  - Factory methods: `create_openai()`, `create_anthropic()`, `create_custom()`
  
- **ModelId**: Represents specific AI models within providers
  - Tracks capabilities, token limits, and pricing
  - Supports capability checking: `supports_capability()`, `can_handle_context()`
  - Cost estimation: `estimate_cost(input_tokens, output_tokens)`
  - Factory methods: `create_gpt4()`, `create_claude()`
  
- **TokenBudget**: Manages token allocation and consumption tracking
  - Supports hierarchical budgets with rollover policies
  - Tracks consumed, reserved tokens and accumulated costs
  - Enforces budget constraints: `can_reserve_tokens()`, `can_afford_cost()`
  - Factory methods: `create_daily_budget()`, `create_project_budget()`

### Domain Events
- **None currently defined**: Events are typically raised by application services and propagated through the event bus.

## Application

### Services
- **ExecuteLLMService**: Main orchestration service for LLM execution
  - `execute_async(request, budget, config)` - Execute LLM request with full policy enforcement
    - Input: `LLMRequest`, optional `TokenBudget`, optional `LLMExecutionConfig`
    - Output: `LLMExecutionResult` with response, metrics, and cost data
    - Errors: Rate limit exceeded, budget exceeded, provider unavailable
  - `execute_stream_async(request, budget, config)` - Execute with streaming response
    - Yields response chunks for real-time UI updates
  - `get_execution_stats_async()` - Get comprehensive execution statistics
  - Provider management: `register_provider(provider)`

- **ProviderRouter**: Intelligent provider selection and routing
  - Health checking and performance-based selection
  - Fallback provider support
  - Model capability matching

### Ports (Interfaces)
- **ICacheService**: Caching abstraction for LLM responses
- **IRateLimiter**: Rate limiting enforcement
- **ICostTracker**: Cost tracking and budget enforcement
- **IRetryPolicy**: Retry logic with exponential backoff

### Commands
- **None explicitly defined**: Commands are handled directly through service methods.

### Queries
- **None explicitly defined**: Query capabilities provided through service methods.

## Infrastructure

### Repositories
- **None**: This context is stateless regarding persistence; configuration is injected.

### External Services
- **OllamaProvider**: Local LLM inference via Ollama
- **OpenAIProvider**: OpenAI API integration (GPT models)
- **Caching Policy**: Redis-based response caching with TTL
- **Cost Tracking Policy**: Budget enforcement and cost accumulation
- **Rate Limiting Policy**: Token bucket algorithm for request throttling
- **Retry/Fallback Policy**: Exponential backoff with circuit breaker pattern

## API

### REST Endpoints
None directly exposed. This context is consumed by other contexts via dependency injection.

### WebSocket Events
None directly exposed.

## Testing

### Running Tests
```bash
# Unit tests
pytest tests/contexts/ai/unit/ -v

# Integration tests
pytest tests/contexts/ai/integration/ -v

# All context tests
pytest tests/contexts/ai/ -v
```

### Test Coverage
Current coverage: To be measured
Target coverage: 80%

## Architecture Decision Records
- ADR-001: Multi-provider LLM abstraction layer
- ADR-002: Token-based budgeting for cost control

## Integration Points

### Inbound
- Events consumed from other contexts:
  - None (service calls only)

### Outbound
- Events published:
  - Cost threshold alerts
  - Rate limit warnings

### Dependencies
- **Domain**: None (pure domain)
- **Application**: Other contexts via dependency injection
- **Infrastructure**: LLM APIs, Redis (optional), Monitoring systems

## Development Guide

### Adding New Features
1. Add new provider support in `infrastructure/providers/`
2. Implement port interface for new capabilities
3. Update ExecuteLLMService to utilize new features
4. Add configuration options to `LLMExecutionConfig`
5. Write tests for new provider/policy

### Common Tasks
- **Adding a new LLM provider**: 
  - Implement `ILLMProvider` interface
  - Add factory method to `ProviderId`
  - Register in service initialization
  
- **Adding a new policy**: 
  - Create port interface in `application/ports/`
  - Implement in `infrastructure/policies/`
  - Wire into `ExecuteLLMService`

## Maintainer
Team: @ai-team
Contact: ai-team@example.com
