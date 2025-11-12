1. [ ] Extend `BentoGrid`/dashboard CSS with a four-tier breakpoint map (≥1440, 1200–1439, 900–1199, 600–899, <600) and expose utility classes so tiles can declare `tile-xl`, `tile-lg`, etc.
2. [ ] Update the dashboard header + action bar spacing rules so padding, typography, and wrapping adjust per breakpoint (e.g., 2x2 action grid on tablets, single column on narrow phones).
3. [ ] Implement tile elevation + animation tokens (hover/focus scale, optional fade-in) and ensure world map/timeline/performance tiles adopt the new classes without breaking existing data-testid hooks.
4. [ ] Re-run `npm run lint` and the quick Playwright smoke spec to verify layout still renders end-to-end.
