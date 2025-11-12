# Documentation Archive

This directory contains superseded or deprecated documentation files that have been replaced by newer, consolidated versions.

## Archived Files

### Architecture Documentation (Archived 2024-11-04)
- **Architecture_Blueprint.md** → Consolidated into `docs/architecture/SYSTEM_ARCHITECTURE.md`
  - Original: Detailed multi-agent system blueprint
  - Reason: Merged with overview for comprehensive architecture doc

- **ARCHITECTURE_OVERVIEW.md** → Consolidated into `docs/architecture/SYSTEM_ARCHITECTURE.md`
  - Original: High-level system architecture overview
  - Reason: Merged with blueprint to eliminate duplication

### Deployment Documentation (Archived 2024-11-04)
- **DEPLOYMENT.md** → Consolidated into `docs/deployment/DEPLOYMENT_GUIDE.md`
  - Original: Deployment and operations guide (v1.2)
  - Reason: Merged with deployment guide for comprehensive reference

- **DEPLOYMENT_GUIDE.md** → Consolidated into `docs/deployment/DEPLOYMENT_GUIDE.md`
  - Original: Production deployment guide (v1.0)
  - Reason: Merged with deployment docs to eliminate duplication

### API Documentation (Archived 2024-11-04)
- **API.md** → Consolidated into `docs/api/API_REFERENCE.md`
  - Original: REST API Contract (v1 endpoints)
  - Reason: Merged with other API docs for single source of truth
  
- **API_DOCUMENTATION.md** → Consolidated into `docs/api/API_REFERENCE.md`
  - Original: Python Framework API documentation
  - Reason: Merged with REST API for comprehensive reference
  
- **API_SPECIFICATION.md** → Consolidated into `docs/api/API_REFERENCE.md`
  - Original: HTTP REST API Specification
  - Reason: Merged with other API docs to eliminate duplication

## Why Archive?

Files are archived rather than deleted to:
1. Preserve historical context
2. Allow recovery if needed
3. Maintain git history references
4. Support rollback if consolidation causes issues

## Retention Policy

Archived files are retained for:
- **6 months** for general documentation
- **1 year** for architectural decisions
- **Indefinitely** for legal/compliance documents

## Accessing Archived Files

These files are kept in git history and can be accessed via:
```bash
git log -- docs/_archive/FILENAME.md
git show COMMIT:docs/_archive/FILENAME.md
```

---

**Last Updated**: 2024-11-04  
**Maintained by**: Documentation Team
