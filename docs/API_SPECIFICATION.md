# Novel Engine API Specification

**Version**: 1.0.0  
**Base URL**: `http://localhost:8000`  
**Content Type**: `application/json`  
**Date**: 2025-08-12

## Overview

The Novel Engine API provides a RESTful interface for managing characters, running story simulations, and monitoring system health. This API powers an AI-driven multi-agent story creation platform designed for creative professionals.

## Authentication

Currently, the API operates without authentication. Future versions will implement JWT-based authentication.

## Rate Limiting

- **Default**: 100 requests per minute per IP
- **Burst**: 200 requests in 5-minute window
- **Story Generation**: 5 concurrent simulations per user

## Core Endpoints

### System Health & Status

#### `GET /health`
System health check for monitoring and load balancers.

**Response**:
```json
{
  "api": "healthy" | "degraded" | "error",
  "config": "loaded" | "error",
  "version": "1.0.0",
  "timestamp": "2025-08-12T10:30:00Z",
  "uptime_seconds": 3600
}
```

**Status Codes**:
- `200` - System healthy
- `503` - System degraded/unavailable

#### `GET /meta/system-status`
Detailed system metrics and performance data.

**Response**:
```json
{
  "api": "healthy",
  "config": "loaded", 
  "version": "1.0.0",
  "performance": {
    "avg_response_time_ms": 150,
    "cache_hit_rate": 0.89,
    "active_connections": 12,
    "memory_usage_mb": 512,
    "cpu_usage_percent": 25.6
  },
  "features": {
    "character_generation": true,
    "story_simulation": true,
    "caching_enabled": true,
    "budget_management": true
  }
}
```

### Character Management

#### `GET /characters`
Retrieve all character names in the system.

**Response**:
```json
{
  "characters": ["krieg", "isabella_varr", "ork_warboss", "test_character"],
  "count": 4,
  "timestamp": "2025-08-12T10:30:00Z"
}
```

#### `GET /characters/{character_name}`
Get detailed character information.

**Parameters**:
- `character_name` (string, required) - URL-encoded character name

**Response**:
```json
{
  "character_name": "krieg",
  "narrative_context": "A battle-hardened soldier from the Death Korps of Krieg...",
  "structured_data": {
    "combat_stats": {
      "strength": 8,
      "dexterity": 6,
      "intelligence": 7,
      "perception": 9,
      "leadership": 5
    },
    "equipment": {
      "primary_weapon": "Lasgun",
      "armor": "Flak Armor",
      "special_gear": ["Bayonet", "Field Kit", "Gas Mask"]
    },
    "psychological_profile": {
      "loyalty": 10,
      "morale": 8,
      "fear_response": 2
    }
  },
  "creation_date": "2025-08-10T15:20:00Z",
  "last_modified": "2025-08-12T09:15:00Z"
}
```

**Status Codes**:
- `200` - Character found
- `404` - Character not found
- `400` - Invalid character name

#### `GET /characters/{character_name}/enhanced`
Get enhanced character data with AI analysis (optional endpoint).

**Response**:
```json
{
  "character_id": "krieg",
  "name": "Krieg Guardsman",
  "faction": "Death Korps of Krieg",
  "ai_personality": {
    "role": "Veteran Guardsman",
    "traits": ["Disciplined", "Fatalistic", "Loyal"],
    "speech_patterns": "Formal military jargon"
  },
  "stats": {
    "strength": 8,
    "dexterity": 6,
    "intelligence": 7,
    "willpower": 9,
    "perception": 8,
    "charisma": 4
  },
  "equipment": [
    {
      "name": "Lasgun",
      "equipment_type": "weapon",
      "condition": 0.95,
      "properties": {
        "range": "300m",
        "damage": "medium",
        "reliability": "high"
      }
    }
  ],
  "relationships": [],
  "background_analysis": "Psychological profile indicates...",
  "story_potential": 0.87
}
```

#### `POST /characters`
Create a new character with multipart form data.

**Content-Type**: `multipart/form-data`

**Form Fields**:
- `name` (string, required) - Character name (3-50 characters)
- `description` (string, required) - Character description (10-2000 characters)
- `files` (file[], optional) - Supporting character files

**Validation Rules**:
- Character names must be unique
- Description must contain meaningful character information
- Maximum 5 files per character, 10MB total size
- Allowed file types: .txt, .md, .json, .yaml

**Response**:
```json
{
  "success": true,
  "character": {
    "name": "new_character",
    "creation_status": "processing" | "completed" | "failed",
    "estimated_completion": "2025-08-12T10:35:00Z"
  },
  "message": "Character creation initiated successfully"
}
```

**Status Codes**:
- `201` - Character creation started
- `400` - Invalid input data
- `409` - Character name already exists
- `413` - File size too large

### Story Simulation

#### `POST /simulations`
Run a story simulation with specified characters.

**Request Body**:
```json
{
  "character_names": ["krieg", "ork_warboss"],
  "turns": 5,
  "narrative_style": "action" | "dialogue" | "balanced" | "descriptive",
  "scenario": "optional scenario description",
  "constraints": {
    "max_words_per_turn": 200,
    "tone": "dark" | "heroic" | "comedy" | "neutral",
    "perspective": "third_person" | "first_person"
  }
}
```

**Validation Rules**:
- 2-6 characters per simulation
- 3-20 turns maximum
- All characters must exist in system
- Estimated generation time: 30-180 seconds

**Response**:
```json
{
  "simulation_id": "sim_1234567890",
  "status": "completed" | "processing" | "failed",
  "participants": ["krieg", "ork_warboss"],
  "turns_executed": 5,
  "story": "The battlefield stretched endlessly before them...",
  "metadata": {
    "word_count": 1247,
    "generation_time_seconds": 45.2,
    "quality_score": 0.87,
    "narrative_coherence": 0.92
  },
  "performance": {
    "cache_hits": 3,
    "tokens_used": 2847,
    "api_calls": 12
  },
  "created_at": "2025-08-12T10:30:00Z",
  "completed_at": "2025-08-12T10:30:45Z"
}
```

**Status Codes**:
- `201` - Simulation started successfully
- `400` - Invalid parameters
- `404` - Character not found
- `429` - Rate limit exceeded
- `503` - System overloaded

#### `GET /simulations/{simulation_id}`
Get simulation status and results.

**Response**:
```json
{
  "simulation_id": "sim_1234567890",
  "status": "completed",
  "progress": 100,
  "estimated_remaining_seconds": 0,
  "story": "...",
  "error": null
}
```

### Campaign Management

#### `GET /campaigns`
List all campaigns (story collections).

**Response**:
```json
{
  "campaigns": ["default", "Novel Engine_40k", "custom_scenario"],
  "count": 3
}
```

#### `POST /campaigns`
Create a new campaign.

**Request Body**:
```json
{
  "campaign_name": "my_campaign",
  "description": "Campaign description"
}
```

**Response**:
```json
{
  "success": true,
  "campaign": {
    "name": "my_campaign",
    "created_at": "2025-08-12T10:30:00Z"
  }
}
```

## Data Models

### Character Stats Schema
```json
{
  "strength": 1-10,      // Physical power
  "dexterity": 1-10,     // Agility and coordination  
  "intelligence": 1-10,   // Mental acuity
  "willpower": 1-10,     // Mental fortitude
  "perception": 1-10,    // Awareness and intuition
  "charisma": 1-10       // Social influence
}
```

### Equipment Schema
```json
{
  "id": "unique_identifier",
  "name": "Equipment Name",
  "type": "weapon" | "armor" | "tool" | "special",
  "description": "Equipment description",
  "condition": 0.0-1.0,  // 0 = broken, 1 = perfect
  "properties": {}       // Type-specific properties
}
```

## Error Responses

All errors follow this format:
```json
{
  "error": true,
  "error_code": "VALIDATION_ERROR",
  "message": "Human-readable error message",
  "details": {
    "field": "specific field with error",
    "received": "actual value received",
    "expected": "expected format or constraint"
  },
  "timestamp": "2025-08-12T10:30:00Z",
  "request_id": "req_1234567890"
}
```

### Error Codes
- `VALIDATION_ERROR` - Input validation failed
- `RESOURCE_NOT_FOUND` - Requested resource doesn't exist
- `RATE_LIMIT_EXCEEDED` - Too many requests
- `SYSTEM_UNAVAILABLE` - Service temporarily unavailable
- `INTERNAL_ERROR` - Unexpected server error

## Performance Guidelines

### Response Times
- Health checks: < 50ms
- Character queries: < 200ms
- Story generation: 30-180 seconds
- System status: < 500ms

### Caching
- Character data cached for 5 minutes
- System status cached for 30 seconds
- Story results cached for 24 hours

### Timeouts
- Client timeout: 30 seconds for regular operations
- Story generation timeout: 5 minutes
- Health check timeout: 5 seconds

## Security Considerations

### Input Validation
- All user input sanitized and validated
- File uploads scanned for malicious content
- SQL injection prevention through parameterized queries
- XSS protection through output encoding

### Data Protection
- No personal data stored without consent
- Character data anonymized in logs
- Temporary files cleaned up after processing

## Development Integration

### Frontend Integration
The API is designed to work seamlessly with the React/TypeScript frontend:
- Type-safe interfaces provided
- Error states handled gracefully  
- Real-time updates via polling (WebSocket support planned)

### Testing
- Comprehensive test suite with 95%+ coverage
- Integration tests for all critical paths
- Performance tests for story generation
- Load testing for concurrent users

## Changelog

### Version 1.0.0 (2025-08-12)
- Initial API specification
- Core character management endpoints
- Story simulation functionality
- System health monitoring
- Campaign management basics

---

**Contact**: Development Team  
**Repository**: Novel Engine  
**License**: MIT