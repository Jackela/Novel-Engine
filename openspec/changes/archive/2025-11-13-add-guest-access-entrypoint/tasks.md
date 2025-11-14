## Task List

1. **Landing & Routing**
   - [x] Add a `/` landing route with copy + CTA buttons, ensuring router defaults no longer bounce straight to `/dashboard`.
   - [x] Wire the “View Demo” button to trigger guest auth (when enabled) and navigate to `/dashboard`.
2. **Guest UX Surface**
   - [x] Add a guest badge/banner in the dashboard header with a dismiss action stored per session.
3. **Testing & Docs**
   - [x] Update/extend Playwright smoke test to click the demo CTA and assert dashboard zones render.
   - [x] Run regression commands (`npm run lint`, `npm run type-check`, `npm test -- --run`, Playwright suite) and document results.
