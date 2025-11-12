# process-management Specification

## Purpose
TBD - created by archiving change audit-user-flow-with-devtools. Update Purpose after archive.
## Requirements
### Requirement: Support Multiple Process Management Methods
The system MUST provide scripts to start frontend and backend services as background processes using at least three different methods: PM2, Docker Compose detached mode, and tmux sessions.

#### Scenario: Developer starts services with PM2
```
GIVEN the developer has PM2 installed globally
WHEN they run `npm run pm2:start` from the project root
THEN the backend FastAPI server starts on port 8000
AND the frontend Vite dev server starts on port 3000
AND both processes run in the background without blocking the terminal
AND PM2 logs are accessible via `pm2 logs`
```

#### Scenario: Developer starts services with Docker Compose
```
GIVEN Docker and Docker Compose are installed
WHEN the developer runs `docker compose -f docker/docker-compose.dev.yml up -d`
THEN all services (backend, frontend, redis) start in detached mode
AND the developer can continue using the terminal
AND services are accessible on their configured ports
AND logs can be viewed with `docker compose logs -f`
```

#### Scenario: Developer starts services with tmux
```
GIVEN tmux is installed
WHEN the developer runs `scripts/start-dev-tmux.sh`
THEN a new tmux session named "novel-engine-dev" is created
AND the backend runs in window 0
AND the frontend runs in window 1
AND the developer can attach to the session with `tmux attach -t novel-engine-dev`
AND the developer can detach and keep processes running
```

### Requirement: Health Check Endpoints
The backend MUST expose a `/health` endpoint that returns service readiness status. The frontend MUST respond with HTTP 200 when the Vite dev server is ready.

#### Scenario: Backend health check returns ready status
```
GIVEN the backend server has fully initialized
AND database connections are established
WHEN a client sends GET /health
THEN the response status is 200 OK
AND the response body includes {"status": "healthy", "timestamp": "<ISO-8601>"}
```

#### Scenario: Backend health check returns not ready
```
GIVEN the backend server is still initializing
WHEN a client sends GET /health
THEN the response status is 503 Service Unavailable
AND the response body includes {"status": "initializing"}
```

#### Scenario: Frontend responds when Vite dev server is ready
```
GIVEN the Vite dev server has completed initialization
WHEN a client sends GET http://localhost:3000
THEN the response status is 200 OK
AND the response includes HTML content
```

### Requirement: Service Startup Wait Script
The system MUST provide a script that waits for both frontend and backend services to become healthy before proceeding.

#### Scenario: Wait script succeeds when services are ready
```
GIVEN services are starting in the background
WHEN the developer runs `scripts/wait-for-services.sh --timeout 60`
THEN the script polls /health endpoints every 2 seconds
AND the script exits with code 0 when both services return 200
AND the script prints "Services ready" to stdout
```

#### Scenario: Wait script times out if services don't start
```
GIVEN services fail to start within the timeout period
WHEN the developer runs `scripts/wait-for-services.sh --timeout 10`
THEN the script polls for 10 seconds
AND the script exits with code 1
AND the script prints "Timeout waiting for services" to stderr
```

### Requirement: Service Cleanup Script
The system MUST provide a cleanup script that properly terminates all background processes without leaving orphaned processes.

#### Scenario: Cleanup script stops PM2 processes
```
GIVEN services are running via PM2
WHEN the developer runs `npm run pm2:stop`
THEN all PM2-managed processes for this project are stopped
AND PM2 confirms "stopped 2 processes"
AND no orphaned node/python processes remain
```

#### Scenario: Cleanup script stops Docker Compose services
```
GIVEN services are running via Docker Compose
WHEN the developer runs `docker compose -f docker/docker-compose.dev.yml down`
THEN all containers are stopped and removed
AND networks are cleaned up
AND volumes persist unless --volumes flag is used
```

#### Scenario: Cleanup script kills tmux session
```
GIVEN services are running in tmux session "novel-engine-dev"
WHEN the developer runs `scripts/stop-dev-tmux.sh`
THEN the tmux session is killed
AND all processes in the session are terminated
AND `tmux ls` no longer shows "novel-engine-dev"
```

### Requirement: Configuration for Port and Host Settings
Process management scripts MUST read port and host configuration from environment variables or config files.

#### Scenario: Backend port is configurable
```
GIVEN the environment variable API_PORT=8080 is set
WHEN the backend starts via any process manager
THEN the FastAPI server listens on port 8080
AND the health check is accessible at http://localhost:8080/health
```

#### Scenario: Frontend port is configurable
```
GIVEN the environment variable VITE_PORT=3001 is set
WHEN the frontend starts via any process manager
THEN the Vite dev server listens on port 3001
AND the UI is accessible at http://localhost:3001
```

### Requirement: Process Monitoring and Restart
For PM2 and Docker Compose methods, processes MUST automatically restart on crash.

#### Scenario: PM2 restarts crashed backend
```
GIVEN the backend is running via PM2
WHEN the backend process crashes
THEN PM2 automatically restarts the process within 5 seconds
AND the restart is logged in PM2 logs
AND the health check returns 200 after reinitialization
```

#### Scenario: Docker Compose restarts crashed container
```
GIVEN services are running with restart policy "unless-stopped"
WHEN the backend container crashes
THEN Docker Compose restarts the container
AND the container logs show the restart event
AND the service becomes healthy again
```

