# Implementation Plan: Frontend Quality Improvements

**Branch**: `001-frontend-quality` | **Date**: 2025-11-05 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/001-frontend-quality/spec.md`

## Summary

This feature addresses six critical frontend quality gaps identified in code review: production-ready error handling, structured logging to replace 265 console.log statements, complete authentication flow without bypasses, WebSocket decision (complete or remove), comprehensive test coverage (60-80%), and type safety improvements. The technical approach focuses on React 18 ecosystem with TypeScript strict mode, implementing error boundaries at root and route levels, environment-aware logging service with automatic sanitization, JWT/session-based authentication, and systematic test coverage improvements using Vitest.

## Technical Context

**Language/Version**: TypeScript 5.x with ES2020 target, React 18, Node.js 18+  
**Primary Dependencies**: React 18, Vite 5.x, Material-UI v5, Redux Toolkit, React Query v3, Vitest 4.x, Playwright  
**Storage**: Browser sessionStorage/httpOnly cookies for auth tokens (no database changes)  
**Testing**: Vitest 4.x with @vitest/coverage-v8, Playwright for E2E, React Testing Library  
**Target Platform**: Modern browsers (ES2020+ support), responsive web application  
**Project Type**: Web application (frontend-only changes in `/frontend` directory)  
**Performance Goals**: <3s load time on 3G, <500KB initial bundle, <100ms logging overhead, 60fps UI  
**Constraints**: Zero production console.log via Terser, <50KB bundle increase, 99% auth token refresh success  
**Scale/Scope**: 93 TypeScript files, 39 existing tests, target 60%+ coverage, eliminate 265 console.log statements

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Article I - Domain-Driven Design (DDD)**: 
  - Bounded contexts: Frontend UI domain (error handling, logging infrastructure), Authentication domain (auth state management)
  - Domain model purity: Error boundaries are pure UI concern; logging service is infrastructure layer; auth tokens are application state
  - Infrastructure dependencies: Logging adapts to environment (dev vs production); auth integrates with backend API via axios adapter

- **Article II - Ports & Adapters**: 
  - Ports: ILogger interface (logging abstraction), IErrorReporter interface (error tracking), IAuthenticationService interface (auth operations), IWebSocketClient interface (if implementing WebSocket)
  - Adapters: ConsoleLogger (development), SentryLogger (production), JWTAuthService (backend integration), WebSocketAdapter (connection management)
  - Dependency inversion: React components depend on ILogger abstraction, not ConsoleLogger directly; auth components use IAuthenticationService interface

- **Article III - Test-Driven Development (TDD)**: 
  - Red-Green-Refactor plan: Write failing ErrorBoundary tests → implement boundaries → refactor for reusability; write logging sanitization tests → implement sanitizer → refactor
  - Failing tests to write first: ErrorBoundary rendering test, logging environment filtering test, auth redirect test, token refresh test
  - Test coverage targets: 60% overall, 70% core components (Dashboard, CharacterStudio, StoryWorkshop), 80% custom hooks (useWebSocket, usePerformanceOptimizer)

- **Article IV - Single Source of Truth (SSOT)**: 
  - No database schema changes required (frontend-only feature)
  - Authentication tokens: httpOnly cookies are authoritative (if backend supports), sessionStorage fallback
  - Logging configuration: centralized LoggerConfig in logging service is SSOT for log levels and sanitization rules
  - Error boundary state: React component state is authoritative for error display

- **Article V - SOLID Principles**: 
  - SRP: Logging service handles only logging; error boundaries handle only error display; auth service handles only authentication
  - OCP: Logging service open for extension (add new LogDestination) but closed for modification
  - LSP: Different logger implementations (ConsoleLogger, SentryLogger) substitutable via ILogger interface
  - ISP: Separate ILogger, IErrorReporter, IAuthenticationService interfaces rather than monolithic IFrontendService
  - DIP: Components depend on ILogger abstraction, not concrete ConsoleLogger; auth components depend on IAuthenticationService interface

- **Article VI - Event-Driven Architecture (EDA)**: 
  - Domain events: ErrorOccurred (error boundary triggered), UserAuthenticationFailed (auth error), LogEntryCreated (new log)
  - Event subscriptions: Error monitoring service subscribes to ErrorOccurred for analytics
  - No Kafka integration needed (frontend-only changes, no cross-context communication)
  - Event bus: Frontend event bus for error boundary → error monitoring communication (local only)

- **Article VII - Observability**: 
  - Structured logging: All logs include timestamp, level, component name, user action, session ID
  - Metrics: Error boundary trigger rate (errors/hour), authentication failure rate (failures/login attempts), log volume by level (debug/info/warn/error)
  - OpenTelemetry tracing: Error boundaries emit traces for error propagation paths; auth service traces token refresh flow
  - Performance monitoring: Log service performance metrics (<100ms overhead), error boundary render performance

- Constitution Compliance Review Date: 2025-11-05
- Constitution Compliance Review Completion: 2025-11-05 (Feature 001 implementation complete, all articles validated)

**GATE STATUS**: ✅ PASS - No violations identified

## Project Structure

### Documentation (this feature)

```text
specs/001-frontend-quality/
├── plan.md              # This file (/speckit.plan output)
├── research.md          # Phase 0 output (technology decisions)
├── data-model.md        # Phase 1 output (state models)
├── quickstart.md        # Phase 1 output (implementation guide)
├── contracts/           # Phase 1 output (interfaces)
│   ├── ILogger.ts       # Logging interface
│   ├── IErrorReporter.ts # Error tracking interface
│   └── IAuthenticationService.ts # Auth interface
└── tasks.md             # Phase 2 output (/speckit.tasks - NOT created yet)
```

### Source Code (repository root)

```text
frontend/
├── src/
│   ├── components/
│   │   ├── admin/           # Existing admin components
│   │   ├── error-boundaries/ # NEW: Error boundary components
│   │   │   ├── RootErrorBoundary.tsx
│   │   │   └── RouteErrorBoundary.tsx
│   │   └── ...
│   ├── services/
│   │   ├── api/             # Existing API services
│   │   ├── logging/         # NEW: Logging service
│   │   │   ├── ILogger.ts
│   │   │   ├── ConsoleLogger.ts
│   │   │   ├── SentryLogger.ts
│   │   │   ├── LoggerFactory.ts
│   │   │   └── Sanitizer.ts
│   │   ├── auth/            # NEW or ENHANCED: Auth service
│   │   │   ├── IAuthenticationService.ts
│   │   │   ├── JWTAuthService.ts
│   │   │   └── TokenStorage.ts
│   │   └── error-reporting/ # NEW: Error reporting
│   │       ├── IErrorReporter.ts
│   │       └── SentryReporter.ts
│   ├── hooks/
│   │   ├── useLogger.ts     # NEW: Logger hook
│   │   └── useAuth.ts       # ENHANCED: Auth hook with refresh
│   ├── types/
│   │   ├── logging.ts       # NEW: Logging types
│   │   └── auth.ts          # ENHANCED: Auth types
│   └── test/
│       └── setup.ts         # ENHANCED: Test setup with cleanup
└── tests/
    ├── unit/
    │   ├── error-boundaries/ # NEW: Error boundary tests
    │   ├── logging/         # NEW: Logging tests
    │   └── auth/            # NEW: Auth tests
    ├── integration/
    │   ├── auth-flow/       # NEW: Auth integration tests
    │   └── logging/         # NEW: Logging integration tests
    └── e2e/                 # Existing E2E tests (may add auth scenarios)
```

**Structure Decision**: Web application structure with frontend-only changes. All new code resides in `/frontend/src/` directory following existing React + TypeScript conventions. New services follow ports & adapters pattern with interfaces in `/services/{domain}/I*.ts` and implementations as sibling files. Error boundaries follow React 18 patterns with dedicated `/components/error-boundaries/` directory.

## Complexity Tracking

> No Constitution violations detected. This section remains empty.
