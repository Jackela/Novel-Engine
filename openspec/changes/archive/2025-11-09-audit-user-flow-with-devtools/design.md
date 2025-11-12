# Design: Chrome DevTools Audit with Process Management

## Architecture Overview

This change introduces two interconnected capabilities:

1. **Process Management**: Infrastructure to run frontend/backend as background services
2. **DevTools Audit Workflow**: Automated user flow testing via Chrome DevTools Protocol

### Component Relationships

```
┌─────────────────────────────────────────────────────────────┐
│                   Audit Orchestrator                        │
│  (scripts/audit-user-flow.sh or .py)                       │
└────────────┬────────────────────────────────┬───────────────┘
             │                                │
             v                                v
   ┌─────────────────┐              ┌──────────────────┐
   │ Process Manager │              │ DevTools Client  │
   │  (Start/Stop)   │              │  (CDP Protocol)  │
   └────────┬────────┘              └────────┬─────────┘
            │                                │
            v                                v
   ┌─────────────────┐              ┌──────────────────┐
   │ Health Checker  │              │ Chrome Browser   │
   │ (Wait Ready)    │──polls───────>│ (Headless/UI)   │
   └─────────────────┘              └──────────────────┘
            │
            v
   ┌──────────────────────────────────────────┐
   │  Backend (FastAPI) + Frontend (Vite)     │
   │  Running in background via:              │
   │  - tmux sessions                         │
   │  - nohup + disown                        │
   │  - PM2 process manager                   │
   │  - systemd --user services               │
   │  - Docker Compose (detached)             │
   └──────────────────────────────────────────┘
```

## Process Management Design

### Approach Comparison

| Method | Pros | Cons | Best For |
|--------|------|------|----------|
| **tmux** | Session persistence, easy debugging | Requires tmux install | Development, debugging |
| **nohup + disown** | No dependencies, portable | Manual PID tracking | CI/CD, simple scripts |
| **PM2** | Node-native, logs, clustering | Node-specific, extra dependency | Node-heavy stacks |
| **systemd --user** | System integration, auto-restart | Linux-only, config complexity | Production-like local env |
| **Docker Compose** | Isolation, reproducibility | Overhead, image build time | Integration testing |

### Recommended Implementation Priority

1. **PM2** (Phase 1): Easiest for this Node/Python stack, built-in logging
2. **Docker Compose** (Phase 1): Already configured, production parity
3. **tmux** (Phase 2): Developer convenience for interactive debugging
4. **nohup** (Phase 3): Fallback for minimal environments
5. **systemd** (Optional): Advanced users only

### Health Check Strategy

```python
# Pseudo-code for readiness check
def wait_for_services(timeout=60):
    start = time.time()
    while time.time() - start < timeout:
        backend_ready = check_http("http://localhost:8000/health")
        frontend_ready = check_http("http://localhost:3000")
        if backend_ready and frontend_ready:
            return True
        time.sleep(2)
    raise TimeoutError("Services did not become ready")
```

**Backend Health Endpoint** (`/health`):
- Return 200 if database connections are alive
- Return 503 if still initializing

**Frontend Health Check**:
- Poll `http://localhost:3000` until it responds with 200
- Vite dev server returns HTML immediately when ready

## DevTools Audit Design

### Audit Workflow Sequence

```
1. Start Services (via process manager)
2. Wait for Health (poll /health endpoints)
3. Launch Chrome (headless or UI mode)
4. Connect via CDP (Chrome DevTools Protocol)
5. Execute User Flow:
   a. Navigate to /login
   b. Fill credentials (from config/env)
   c. Submit and wait for redirect
   d. Navigate to /dashboard
   e. Interact with key UI elements
   f. Trigger API calls (click buttons, load data)
6. Collect Metrics:
   - Performance (Lighthouse or Web Vitals)
   - Accessibility (axe-core)
   - Network (timing, errors)
   - Console (warnings, errors)
7. Generate Reports (JSON + HTML)
8. Stop Services (cleanup)
```

### Technology Choices

**Option A: Playwright** (Recommended)
- Already in `package.json` dependencies
- High-level API for user interactions
- Built-in CDP access
- Lighthouse integration via `playwright-lighthouse`

**Option B: Puppeteer**
- Lower-level CDP control
- Slightly more complex for common tasks

**Option C: Direct CDP**
- Maximum control
- Steep learning curve

**Decision**: Use **Playwright** for productivity and existing project presence.

### Audit Script Structure

```python
# scripts/audit_user_flow.py (Python + Playwright)
import asyncio
from playwright.async_api import async_playwright

async def run_audit():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # Enable CDP session for advanced metrics
        cdp = await context.new_cdp_session(page)

        # Start performance monitoring
        await cdp.send('Performance.enable')

        # User flow
        await page.goto('http://localhost:3000/login')
        await page.fill('input[name="username"]', 'demo')
        await page.fill('input[name="password"]', 'demo123')
        await page.click('button[type="submit"]')
        await page.wait_for_url('**/dashboard')

        # Capture metrics
        metrics = await cdp.send('Performance.getMetrics')

        # Accessibility audit
        await page.evaluate('axe.run()')

        # Generate report
        await browser.close()
```

### Report Format

**JSON Output** (`audit-results.json`):
```json
{
  "timestamp": "2025-11-09T12:00:00Z",
  "environment": {
    "backend": "http://localhost:8000",
    "frontend": "http://localhost:3000"
  },
  "performance": {
    "lcp": 1234,
    "fid": 56,
    "cls": 0.12
  },
  "accessibility": {
    "violations": [],
    "passes": 42
  },
  "network": {
    "requests": 15,
    "errors": 0,
    "slowest": "/api/dashboard (234ms)"
  }
}
```

**HTML Report**: Generated via template or Lighthouse HTML reporter.

## Integration Points

- **CI/CD**: Audit can run as GitHub Actions job (using Docker Compose + headless Chrome)
- **Pre-commit**: Optional fast audit on localhost before push
- **Monitoring**: Compare audit results over time to detect regressions

## Risk Mitigation

1. **Port Conflicts**: Health checker should detect if ports 3000/8000 are already in use
2. **Zombie Processes**: Cleanup script must kill by PID file or process group
3. **Timing Issues**: Add configurable timeouts and retries for flaky networks
4. **Credential Security**: Store test credentials in `.env.test`, never commit

## Trade-offs

| Decision | Pro | Con |
|----------|-----|-----|
| Multiple process managers | Flexibility for different envs | Increased maintenance |
| Playwright over Puppeteer | Easier API, already installed | Slightly heavier |
| Python audit script | Consistent with backend stack | Could use Node (already has Playwright) |
| Docker Compose as default | Production parity | Slower startup than native processes |

## Future Enhancements

- Visual regression testing (screenshot comparison)
- Multi-browser testing (Firefox, Safari)
- Synthetic monitoring (run audits on schedule)
- Integration with external monitoring services (DataDog, New Relic)
