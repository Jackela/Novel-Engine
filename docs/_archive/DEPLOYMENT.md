# Codex: Deployment & Operations (DEPLOYMENT.md)
*Document Version: 1.2*
*Last Updated: 2025-08-11*

This document provides instructions for deploying and operating the Novel Engine.

## 1. Environment Baseline

-   **Python:** 3.9+
-   **Dependencies:** See `requirements.txt`. Key dependencies include `fastapi`, `uvicorn`, `pydantic`, `faiss-cpu`, `sentence-transformers`.
-   **OS:** Linux-based OS recommended for production deployments.
-   **Resources:** Minimum 2 CPU cores, 4GB RAM. GPU is optional but recommended for local Knowledge Base embedding.

## 2. Configuration (`settings.yaml`)

The `settings.yaml` file is the central configuration point for the Engine.

-   **`mode`:** `neutral` | `fan` | `empty`. Determines the operational mode and knowledge source.
-   **`policy`:**
    -   `monetization`: Must be `disabled`.
    -   `allow_trademarks`: Must be `false` for CI/public builds.
    -   `fan_mode_requires_local_registry`: Must be `true`.
-   **`kb`:**
    -   `neutral_dir`, `private_dir`, `index_dir`: Paths to knowledge base content and indexes.
    -   `model`: The Sentence Transformers model to use for embeddings.
-   **`guard`:**
    -   `banned_terms`: A list of strings and regex patterns forbidden in the codebase.

**Sensitive Configurations:**
-   API keys (e.g., for an external LLM) should **not** be stored in `settings.yaml`. Use environment variables (e.g., `LLM_API_KEY`).

## 3. Startup Procedures

### 3.1. Building the Knowledge Base
Before the first run, the Knowledge Base index must be built.
```bash
# For neutral mode (default)
python scripts/build_kb.py

# For fan mode (local only)
# First, ensure your private/registry.yaml is compliant.
# Then, run the ingestion script.
python scripts/ingest_local_assets.py
# Finally, build the index.
python scripts/build_kb.py --mode fan
```

### 3.2. Running the API Server
The server is a standard FastAPI application.
```bash
# For development with auto-reload
uvicorn src.api.main:app --reload

# For production
gunicorn -w 4 -k uvicorn.workers.UvicornWorker src.api.main:app
```

### 3.3. Startup Guards
The application includes startup guards to ensure compliant operation. If conditions are not met, the server will exit with a descriptive error message.
-   **`fan` mode:** Will fail if `private/registry.yaml` is missing or its `compliance` section is invalid.
-   **`monetization`:** Will fail if `policy.monetization` is not `disabled`.

## 4. Logging and Observability

-   **Application Logs:** Standard application logs are output to `stdout`/`stderr` and should be collected by your logging agent (e.g., Fluentd, Logstash).
-   **Replay Logs:** Detailed run data for replay and evaluation is stored in `runs/{run_id}/`. Each turn's data is a separate JSON file.
-   **Health Check:** The `GET /meta/policy` endpoint serves as a basic health and policy check.

## 5. Containerization (Docker)

A `Dockerfile` is provided for building a production-ready container image.

**Build Command:**
```bash
docker build -t novel-engine:latest .
```

**Run Command (`neutral` mode):**
```bash
docker run -p 8000:8000 -e LLM_API_KEY="your_key" novel-engine:latest
```

**Run Command (`fan` mode):**
This requires mounting the local `private` directory into the container.
```bash
docker run -p 8000:8000 \
  -v /path/to/your/local/private:/app/private \
  -e LLM_API_KEY="your_key" \
  novel-engine:latest --mode fan
```

**Important:** The Docker image **does not** contain the `private/` directory or any third-party assets.

## 6. Release & Versioning Strategy

-   The project follows Semantic Versioning (SemVer).
-   Releases are managed via Git tags and GitHub Releases.
-   Each release is accompanied by a `CHANGELOG.md` detailing updates.
-   The CI/CD pipeline automatically builds and tests new tags, but deployment to production is a manual step.

```