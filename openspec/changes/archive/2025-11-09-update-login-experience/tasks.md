## Task List

1. **Audit current login UI via MCP snapshot**
   - [x] Capture latest `/login` snapshot & screenshot for baseline (already stored under `tmp/snapshots`, re-run if needed).
2. **Implement responsive split layout**
   - [x] Update `LoginPage.tsx` styles/components to introduce hero panel, include breakpoint-aware layout logic, and ensure mobile stacking works.
3. **Enhance form UX**
   - [x] Add inline validation helper text, password visibility toggle, remember-me checkbox, and improved loading state on the submit button.
4. **Add contextual help + demo messaging**
   - [x] Surface demo mode credentials/info when `appConfig.demoMode` is true, otherwise render support CTA + documentation link.
5. **Polish + test**
   - [x] Add regression tests (React Testing Library) covering helper text, demo/support messaging, and new controls.
   - [x] Re-run MCP snapshot & screenshot to verify visual/layout changes and archive under `tmp/snapshots`.
