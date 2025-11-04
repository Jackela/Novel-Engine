# Codex: API Contract (API.md)
*Document Version: 1.2*
*Last Updated: 2025-08-11*
*API Version: v1*

This document provides a detailed specification for the Novel Engine's v1 RESTful API.

## 1. Versioning & Stability

The v1 API is considered stable. The base path for this version is `/api/v1/`. Any breaking changes will result in a new version (e.g., `/api/v2/`). Non-breaking changes (e.g., adding optional fields to a response) may be made to v1.

## 2. Endpoints

### 2.1 Get Policy
-   **Route:** `GET /meta/policy`
-   **Description:** Returns the current operational policy of the Engine, including its mode and compliance status.
-   **Request Body:** None.
-   **Response Model (200 OK):**
    ```json
    {
      "mode": "neutral",
      "monetization": "disabled",
      "provenance_required": true
    }
    ```
-   **Error Codes:** None.

### 2.2 Run Simulation
-   **Route:** `POST /simulations/run`
-   **Description:** Initiates a new simulation run from a predefined seed scenario.
-   **Request Body:**
    ```json
    {
      "seed_id": "string", // ID of the seed scenario to run
      "steps": "integer"   // Number of turns to execute
    }
    ```
-   **Response Model (202 Accepted):**
    ```json
    {
      "run_id": "string" // A unique ID for this simulation run
    }
    ```
-   **Error Codes:**
    -   `400 Bad Request`: The request body is malformed or `steps` is out of range.
    -   `404 Not Found`: The specified `seed_id` does not exist.

### 2.3 Execute Turn
-   **Route:** `POST /simulations/{run_id}/turn`
-   **Description:** Submits a set of character actions for a specific turn and advances the simulation.
-   **Request Body:** `List[CharacterAction]` (Refer to `SCHEMAS.md`)
-   **Response Model (200 OK):**
    ```json
    {
      "world": {}, // The new WorldState object after the turn
      "log_id": "string" // The ID of the log entry for this turn
    }
    ```
-   **Error Codes:**
    -   `422 Unprocessable Entity`: The request body does not conform to the `CharacterAction` schema.
    -   `409 Conflict`: The Adjudicator rejected one or more actions. The response body will contain details of the adjudication failure with specific error codes:
        -   `E001_RESOURCE_NEGATIVE`: Action would result in negative resource values (violates Iron Law 1)
        -   `E002_TARGET_INVALID`: Action targets an entity not visible to the actor (violates Iron Law 2) 
        -   `E003_ACTION_IMPOSSIBLE`: Action type not permitted for current entity state (violates Iron Law 3)
        -   `E004_LOGIC_VIOLATION`: Action contradicts established world rules (violates Iron Law 4)
        -   `E005_CANON_BREACH`: Action would violate canonical source material constraints (violates Iron Law 5)
    -   `404 Not Found`: The specified `run_id` does not exist.

### 2.4 List Characters
-   **Route:** `GET /characters`
-   **Description:** Retrieves a list of all available `PersonaCardV2` definitions in the active Knowledge Base.
-   **Request Body:** None.
-   **Response Model (200 OK):** `List[PersonaCardV2]` (Refer to `SCHEMAS.md`)
-   **Error Codes:** None.

### 2.5 Generate Chronicle
-   **Route:** `POST /chronicle`
-   **Description:** Requests the generation of a narrative chronicle from a completed simulation run.
-   **Request Body:**
    ```json
    {
      "run_id": "string"
    }
    ```
-   **Response Model (200 OK):** `ChronicleSpec` (Refer to `SCHEMAS.md`)
-   **Error Codes:**
    -   `404 Not Found`: The specified `run_id` does not exist or is not yet complete.

## 3. Error Code Reference

### 3.1 Adjudication Error Codes

The following error codes are returned when the Iron Adjudicator rejects character actions (HTTP 409 Conflict):

| Code | Description | Iron Law Violated |
|------|-------------|-------------------|
| `E001_RESOURCE_NEGATIVE` | Action would result in negative resource values | Iron Law 1: Resource Conservation |
| `E002_TARGET_INVALID` | Action targets an entity not visible to the actor | Iron Law 2: Information Limit |
| `E003_ACTION_IMPOSSIBLE` | Action type not permitted for current entity state | Iron Law 3: State Consistency |
| `E004_LOGIC_VIOLATION` | Action contradicts established world rules | Iron Law 4: Rule Adherence |
| `E005_CANON_BREACH` | Action would violate canonical source material constraints | Iron Law 5: Canon Preservation |

### 3.2 Error Response Format

When the Adjudicator rejects actions, the response includes:

```json
{
  "error": "adjudication_failed",
  "details": {
    "rejected_actions": [
      {
        "action_index": 0,
        "error_code": "E001_RESOURCE_NEGATIVE",
        "message": "Action would reduce health to -5 (minimum: 0)",
        "repair_suggestion": "Limit damage to current health value"
      }
    ],
    "repaired_actions": [...] // Optional: Auto-repaired actions if applicable
  }
}
