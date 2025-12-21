# Change: Add authenticated character creation and simulation API

## Why
Real users cannot create characters or run simulations with their own data because `/api/characters` rejects POST and `/simulations` depend on pre-seeded names. We need authenticated endpoints so users can onboard characters and generate narrative from live inputs.

## What Changes
- Add an authenticated character API to create and list user characters (and enforce validation).
- Allow simulations to accept user-created characters and politely handle missing/invalid names.
- Wire CORS/auth so the frontend can call these endpoints from the dashboard/login flow.

## Impact
- Affected specs: character-service (new)
- Affected code: `secure_main_api.py` (or `api_server.py` equivalent), character domain models, auth/CORS config, frontend service hooks.
