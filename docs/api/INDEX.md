# API Documentation

Comprehensive API documentation for Novel Engine M1 services and integrations.

## 🔌 API Overview

Novel Engine M1 provides a comprehensive API layer through the API Gateway, offering unified access to all system capabilities with consistent authentication, validation, and response patterns.

### API Architecture

```
Client Applications
        ↓
   API Gateway
   ↙    ↓    ↘
Story  Character  Campaign
Engine  Service   Manager
   ↘    ↓    ↙
  Platform Services
```

### Core API Principles

1. **RESTful Design**: Standard HTTP methods and resource-based URLs
2. **Consistent Responses**: Uniform response formats across all endpoints
3. **Authentication**: Secure authentication and authorization for all operations
4. **Versioning**: API versioning for backward compatibility
5. **Documentation**: Living API documentation with examples and integration guides

## 📚 API Reference

### Service APIs

#### [API Gateway](./api-gateway/)
- **Authentication & Authorization**: User authentication and access control
- **Request Routing**: Intelligent request routing and load balancing
- **Rate Limiting**: Request throttling and usage monitoring
- **API Versioning**: Version management and compatibility

#### [Story Engine API](./story-engine/)
- **Narrative Generation**: Dynamic story creation and narrative orchestration
- **Plot Management**: Story arc development and plot progression
- **Event Orchestration**: Event generation and narrative coherence
- **Story Validation**: Quality assurance and content validation

#### [Character Service API](./character-service/)
- **Character Management**: Character creation, configuration, and lifecycle
- **Persona Agents**: Agent deployment and coordination
- **Character Interactions**: Interaction processing and validation
- **Memory Management**: Character memory and development tracking

#### [Campaign Manager API](./campaign-manager/)
- **Campaign Management**: Campaign lifecycle and session orchestration
- **World State**: World state coordination and persistence
- **Session Management**: Session tracking and progression
- **Analytics**: Campaign analytics and reporting

#### [Memory Service API](./memory-service/)
- **Memory Storage**: Centralized memory storage and retrieval
- **Search & Retrieval**: Memory search and similarity matching
- **Cross-Service**: Memory coordination across services
- **Optimization**: Memory cleanup and optimization

### Platform APIs

#### [AI Services API](./platform/ai-services/)
- **LLM Integration**: Language model provider integration
- **Prompt Management**: Template and prompt engineering
- **AI Orchestration**: Model selection and request routing

#### [Security API](./platform/security/)
- **Authentication**: User and service authentication
- **Authorization**: Role-based access control
- **Compliance**: Security policy enforcement

## 🛠️ Integration Guides

### [Quick Start](./quick-start.md)
Get started with Novel Engine APIs in minutes

### [Authentication Guide](./authentication.md)
Complete authentication and authorization setup

### [SDK Documentation](./sdks/)
Official SDKs and client libraries

### [Integration Examples](./examples/)
Real-world integration examples and use cases

## 📊 API Standards

### Request/Response Format
```json
{
  "success": true,
  "data": { ... },
  "metadata": {
    "timestamp": "2025-08-26T...",
    "version": "1.0.0",
    "request_id": "..."
  }
}
```

### Error Handling
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "...",
    "details": { ... }
  }
}
```

### Status Codes
- **200**: Success
- **201**: Created
- **400**: Bad Request
- **401**: Unauthorized
- **403**: Forbidden
- **404**: Not Found
- **500**: Internal Server Error

---

This API documentation provides everything needed to integrate with and extend the Novel Engine M1 system.
