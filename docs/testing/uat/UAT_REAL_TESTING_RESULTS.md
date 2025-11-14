# ✅ UAT 回归报告 – Flow-based Dashboard Condensed Fold (2025-11-15)

## 测试环境
- **时间**：2025-11-15 00:00–00:45 AEST（WSL2）
- **启动方式**：始终使用 `npm run dev:daemon` 启动 FastAPI + Vite，`npm run dev:stop` 关闭
- **Playwright / UAT 统一参数**：`SKIP_DASHBOARD_VERIFY=true PLAYWRIGHT_BASE_URL=http://127.0.0.1:3000`
- **日志目录**：`tmp/dev_env/*.log`（后台服务） + `frontend/test-results/*`（Playwright 追踪） + `tmp/act-frontend.log` / `tmp/act-ci.log` / `tmp/lhci.log`

## 自动化结果总览
| 套件/工具 | 命令 | 结果 | 佐证 |
| --- | --- | --- | --- |
| Lint | `cd frontend && npm run lint` | ✅ 通过 | 无新增 warning |
| Type Check | `cd frontend && npm run type-check` | ✅ 通过 | 无 TS 错误 |
| Vitest | `cd frontend && npm test -- --run` | ✅ 通过 | 仅保留既有 React/Router warning |
| Playwright · Core UAT | `npx playwright test tests/e2e/dashboard-core-uat.spec.ts --project=chromium-desktop` | ✅ 通过 | `frontend/test-results/dashboard-core-uat-*` |
| Playwright · Extended UAT | `npx playwright test tests/e2e/dashboard-extended-uat.spec.ts --project=chromium-desktop` | ✅ 通过 | 同上 |
| Playwright · Interactions | `npx playwright test tests/e2e/dashboard-interactions.spec.ts --project=chromium-desktop` | ✅ 通过 | 同上 |
| Playwright · Cross Browser | `npx playwright test tests/e2e/dashboard-cross-browser-uat.spec.ts` | ✅ 通过（Safari/Firefox 依旧 skipped） | 同上 |
| Playwright · Accessibility | `npx playwright test tests/e2e/accessibility.spec.ts --project=chromium-desktop` | ✅ 通过 | Skip-link & live region 断言稳定 |
| Playwright · Login CTA | `npx playwright test tests/e2e/login-flow.spec.ts --project=chromium-desktop` | ✅ 通过 | 同上 |
| Backend Pytest | `pytest tests/test_security_framework.py tests/test_quality_framework.py` | ✅ 通过 | 68+ 用例，全绿 |
| CI Parity | `./scripts/validate_ci_locally.sh` | ✅ 通过（前一次运行结果复用） | `.venv-ci` 自动创建，Black/Isort/Flake8/Mypy + pytest 完整输出 |
| GitHub Actions (frontend) | `act --pull=false -W .github/workflows/frontend-ci.yml -j build-and-test` | ✅ 通过 | `tmp/act-frontend.log` |
| GitHub Actions (backend) | `act --pull=false -W .github/workflows/ci.yml -j tests` | ✅ 通过 | `tmp/act-ci.log` |
| Lighthouse | `cd frontend && CHROME_PATH=/usr/bin/google-chrome npx @lhci/cli@0.14.0 autorun` | ✅ 通过 | `tmp/lhci.log` 含报告 URL |
| MCP 证据 | `node scripts/mcp_chrome_runner.js --viewport 1440x900 ...` | ✅ 通过（无需重新采集，沿用 11-14 版本） | `docs/assets/dashboard/dashboard-flow-2025-11-14-condensed.*` |

## 关键截图（MCP 自动采集）
![Flow dashboard condensed](../../assets/dashboard/dashboard-flow-2025-11-14-condensed.png)

## 主要结论
- 控制带、活动流、管线在首屏的密度与 11-14 版本一致，Playwright 核心场景稳定（管线 Phase 5 仍属于 mock、耗时 ~24s）。
- 所有 UAT/Accessibility 套件均在 daemon 化环境下通过；CI parity (`act`) 与 LHCI 运行成功，日志已归档。
- README、Coding Standards 与 UAT 文档已指向最新命令与证据路径。

## 残余风险 & 后续
1. Narrative Integration 阶段依旧模拟完成；真实 API 接入后需重新校准 Phase 5 断言。
2. `@monogrid/gainmap-js` 对 `three@>=0.159` 的 peer warning 仍存在，暂未影响构建。
3. Cross-browser 套件仍跳过 Safari/Firefox（CI 同策略）；若需要真实 WebKit/Gecko 支持，需在远端运行器补测。

凭借以上结果，11-15 的回归验证确认文档更新未影响功能，可继续推进后续提交流程。EOF
