# Observability Baseline — 2025-10-29

| Metric | Current Value | Target | Notes |
|--------|---------------|--------|-------|
| Simulation turn p95 latency | 1.8s | ≤ 2.0s | Measured via staging workload (10 campaigns). |
| Persona decision p95 latency | 620ms | ≤ 700ms | Gemini API cache hit rate ~82%. |
| StoryForge API availability (last 7d) | 99.4% | ≥ 99.9% | Two brief outages linked to rate-limit misconfiguration. |
| RED Errors per minute | 4.2 | ≤ 2.0 | Spikes during contract regression tests; investigate after refactor. |
| USE CPU utilization | 58% | ≤ 70% | Stable under daily workload. |

**Next Steps**
- Instrument new spans and logs per bounded context to improve error attribution.
- Align rate-limit configuration with security controls charter.
- Re-run baseline after implementing refactor documentation to set revised targets.
