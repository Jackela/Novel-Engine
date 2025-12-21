# Novel Engine（AI 叙事引擎）

语言/Languages: [English](README.en.md) | 简体中文

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![React 18+](https://img.shields.io/badge/react-18+-blue.svg)](https://react.dev/)

面向生产的 AI 驱动叙事生成与多智能体模拟平台，支持前后端协作、可观测性与持续交付。

本仓库采用单仓（monorepo）结构。本文件是 GitHub 展示和项目说明的唯一权威 README 版本；
子目录中的 README 仅用于该子模块的本地说明，不作为项目首页展示的候选。

---

## 亮点特性

- 多智能体架构：`DirectorAgent`、`PersonaAgent`、`ChroniclerAgent` 等组件协作
- 真实 AI 集成：支持 LLM/外部 API，失效时提供优雅降级策略
- 配置统一：`config.yaml` + 环境变量覆盖，线程安全的全局配置访问
- 生产友好：并发安全、丰富日志、缓存与重试、错误处理与可观测性
- 前端支持：独立的 `frontend/`（React 18），设计系统与质量门禁集成

![Flow-based dashboard view](docs/assets/dashboard/dashboard-flow-2025-11-14-condensed.png)

---

## 理论基础

本项目的理论基础源于罗兰·巴特 1967 年提出的《作者之死》。核心观点：文本意义并非由作者单一意图决定，而是由语言系统与读者共同生成。语言先于作者存在，作者不再是意义中心，系统的任务是对“人类书写系统（Human Writing System）”中的语义资源进行检索与编排。

- 命题与位移：系统中的“作者”退位为“编排者（Orchestrator）”；引擎不“创造意义”，而是在语义网络中“生成路径”。
- 价值主张：重在组合逻辑、语义约束与可复现性，而非语言表层的创造性。
- 核心假设与约束：
  - 语言是封闭系统内的开放演算（closed world, open composition）：仅在既有语义分布内组合，不越出人类语言的统计边界。
  - 创作即约束（composition as constraint）：生成需满足逻辑一致性、语义连贯性与来源溯源。
  - 原创性是稀有路径（originality as rare recombination）：原创对应语义图谱中的低概率新路径。
- 工程化落地：
  - 路径多样化搜索（path diversification）
  - 熵平衡控制（entropy-balanced generation）
  - 验证驱动编排（validation-driven orchestration）
  - 检索（retrieval）机制与权重可解释性（traceable weighting）

详见：`docs/FOUNDATIONS.md`

---

## 仓库结构（摘录）

- `src/`：核心后端源代码与服务
- `frontend/`：前端应用与设计系统
- `docs/`：架构、API、指南与 ADR 文档
- `tests/`：测试代码与质量门禁
- `scripts/`：本地验证、质量与迁移脚本
- `.github/workflows/`：CI/CD 工作流

更多目录请见仓库根目录清单与 `docs/index.md`。

---

## 快速开始

前置依赖：Python 3.11+、Node.js 18+、npm

后端（示例）

```
python -m venv .venv
./.venv/Scripts/activate  # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -U pip
pip install -r requirements.txt
pytest -q  # 可选：快速运行测试
python api_server.py  # 或运行其他入口，如 production_api_server.py
```

前/后端一键启动（非阻塞）

1. 创建虚拟环境并安装依赖：
   ```bash
   python -m venv .venv
   . .venv/bin/activate  # Windows 请使用 .venv\\Scripts\\activate
   pip install -r requirements.txt
   (cd frontend && npm install)
   ```
2. 运行统一脚本（后台启动 + 健康检查）：
   ```bash
   npm run dev:daemon
   ```
   - 后端默认监听 `http://127.0.0.1:8000/health`
   - 前端默认监听 `http://127.0.0.1:3000`
   - 日志写入 `tmp/dev_env.log`，PID 写入 `tmp/dev_env/`
3. 停止后台进程：
   ```bash
   npm run dev:stop
   ```
4. 如需单独运行某端，可进入对应目录执行传统命令，但 README 以后将以脚本为准。

### 统一开发脚本（前后端同步启动）

为避免 Vite/uvicorn 阻塞或悬挂，**必须通过封装脚本启动/停止本地环境**：

| 命令 | 说明 |
| --- | --- |
| `npm run dev:daemon` | 调用 `scripts/dev_env.sh start --detach`，同时拉起 FastAPI（127.0.0.1:8000）与 Vite（127.0.0.1:3000），非阻塞运行 |
| `npm run dev:stop` | 对应 `scripts/dev_env.sh stop`，优雅停止两个进程 |
| `npm run dev:status` | 显示当前进程 PID；若发现僵尸 `uvicorn`/`vite`，请先执行此命令再决定是否手动 kill |

日志归档在 `tmp/dev_env/backend.log` 与 `tmp/dev_env/frontend.log`，便于 Playwright 或 MCP 快照分析。所有本地 UAT/Playwright 测试需要显式指定：

```bash
SKIP_DASHBOARD_VERIFY=true PLAYWRIGHT_BASE_URL=http://127.0.0.1:3000 npx playwright test …
```

## 编码规范与质量门禁

- **前端**：进入 `frontend/` 后运行 `npm run lint`、`npm run type-check`、`npm test -- --run`。仪表盘相关改动必须使用上述环境变量运行全部 Playwright 套件（Core / Extended / Interactions / Cross-browser / Accessibility / Login）。`data-role` 与 `data-testid` 标签是自动化和 MCP 的硬性要求。
- **后端**：执行 `bash scripts/validate_ci_locally.sh` 以获得 Black、Isort、Flake8、Mypy 以及 pytest coverage 的完整输出；若仅需冒烟可运行 `pytest tests/test_security_framework.py tests/test_quality_framework.py`。
- **CI 对齐**：使用 `act --pull=false -W .github/workflows/frontend-ci.yml -j build-and-test` 与 `act --pull=false -W .github/workflows/ci.yml -j tests` 模拟 GitHub Actions，日志保存在 `tmp/act-frontend.log` 与 `tmp/act-ci.log`。
- **Mock/Stub 控制**：默认会失败而非静默使用 mock。仅在测试时使用环境变量开启：`ALLOW_MOCK_REDIS`, `ALLOW_MOCK_GEOIP`, `ALLOW_MOCK_USER_AGENTS`, `CONTEXT7_ALLOW_MOCK`。详细见 `docs/ENVIRONMENT_FLAGS.md`。
- **Lighthouse / MCP 证据**：`CHROME_PATH=/usr/bin/google-chrome npx @lhci/cli@0.14.0 autorun` 生成性能报告；`node scripts/mcp_chrome_runner.js --viewport WIDTHxHEIGHT …` 采集真实 UI 截图与 metadata（存放在 `docs/assets/dashboard/` 并在 README/UX 报告中引用）。
- 详细约定、命令表与文档更新流程请参阅 [`docs/coding-standards.md`](docs/coding-standards.md)。

### Flow-based Dashboard（2025-11）

`/dashboard` 现以语义区域为核心构建流式布局：

- `data-role="summary-strip"`：最上方的摘要带显示编排状态、当前阶段与最后一次数据刷新时间
- `data-role="control-cluster"`：Quick Actions + 连接指示灯；所有按钮保持 ≥44px 点击区
- `data-role="pipeline-monitor"`：Turn Pipeline 运行态信息，可滚动查看步骤，阶段变化会同步到控制区
- `data-role="stream-feed"`：Real-time Activity 与 Narrative Timeline 并排显示（窄屏合并为选项卡）
- `data-role="system-signals"`：Performance Metrics + Event Cascade，内部滚动避免挤压下方卡片
- `data-role="persona-ops"` / `data-role="analytics-insights"`：角色网络与分析面板

桌面端使用 `repeat(auto-fit, minmax(320px, 1fr)) + grid-auto-flow: dense`，控制/管线区域优先占两列；平板收敛为 2 列，移动端交由 `MobileTabbedDashboard` 控制一次只展开一个高密度面板。

![Flow-based dashboard screenshot](docs/assets/dashboard/dashboard-flow-2025-11-14-condensed.png)

> 捕获最新截图：  
> `node scripts/mcp_chrome_runner.js --url http://127.0.0.1:3000/dashboard --viewport 1440x900 --screenshot docs/assets/dashboard/dashboard-flow-2025-11-14-condensed.png --metadata docs/assets/dashboard/dashboard-flow-2025-11-14-condensed.json`  
> 脚本会自动点击 Demo CTA、等待 `data-role="control-cluster"` 渲染，随后将 PNG+JSON 存入 `docs/assets/dashboard/`，用于 README/UX 报告取证。

---

## 测试与质量

- Python 测试：`pytest`（配置见 `pytest.ini` / `.coveragerc`）
- 本地 CI 对齐：`scripts/validate_ci_locally.sh`（Windows 可用 `scripts/validate_ci_locally.ps1`）。默认只跑相关文件，可通过 `RUN_LINT=1` / `RUN_MYPY=1` / `RUN_TESTS=1` 扩展到遗留模块（注意其中仍有 lint/mypy 技债）。
- 前端质量门禁：`npm run type-check`、`npm run lint:all`、`npm run tokens:check`
- 完整 UAT：使用 `npm run dev:daemon` 启动后执行 Playwright 套件（核心 UAT、扩展 UAT、跨浏览器、无障碍）。

**最后一次本地验证**（2025-11-14，commit `bf1406c`）

| 范畴 | 覆盖命令 |
| --- | --- |
| 前端 Lint/Type | `npm run lint`、`npm run type-check` |
| 前端单测 | `VITEST_MAX_THREADS=6 VITEST_MIN_THREADS=3 npx vitest run --reporter=dot` |
| Playwright | `npx playwright test tests/e2e/dashboard-core-uat.spec.ts --project=chromium-desktop`<br>`npx playwright test tests/e2e/dashboard-extended-uat.spec.ts --project=chromium-desktop`<br>`npx playwright test tests/e2e/dashboard-cross-browser-uat.spec.ts --project=chromium-desktop`<br>`npx playwright test tests/e2e/dashboard-interactions.spec.ts --project=chromium-desktop`<br>`npx playwright test tests/e2e/accessibility.spec.ts --project=chromium-desktop`<br>`npx playwright test tests/e2e/login-flow.spec.ts --project=chromium-desktop` |
| 后端测试 | `pytest tests/test_security_framework.py tests/test_quality_framework.py` |
| CI Parity | `scripts/validate_ci_locally.sh`、`act --pull=false -W .github/workflows/frontend-ci.yml -j build-and-test`、`act --pull=false -W .github/workflows/ci.yml -j tests` |

如需快速复现，可执行 `scripts/dev_env_daemon.sh` 启动环境后运行以上命令；验证输出会被追加到 `tmp/dev_env.log` 与 `reports/test-results/`。

### Demo CTA & Offline 模式指南

- **运行 Demo CTA 流程**  
  1. 在 `frontend/` 中执行 `npm install && npm run dev`；  
  2. 打开 `http://127.0.0.1:3000/`，点击 “View Demo (cta-demo)” 按钮；  
  3. 确认跳转到 `/dashboard`，看到 Demo banner（`data-testid="guest-mode-banner"`）与 Summary Strip 的 Demo/Live 指示。

- **模拟离线状态**  
  - 在本地 DevTools Network 面板选择 “Offline”，或在 Playwright 里使用 `page.context().setOffline(true)`；  
  - 仪表盘右上角的 Connection 指示器会变为 `OFFLINE`，恢复网络后自动返回 `ONLINE/LIVE` 并在控制台输出 `[connection-indicator]` 日志。

- **Playwright 验证与 Experience Report**  
  - `npm run test:e2e:smoke`（<1 分钟）仅覆盖 Demo CTA + Offline 场景；  
  - `npm run test:e2e` 运行完整套件；  
  - 每次 Playwright 运行结束都会在 `frontend/reports/experience-report-*.md/.html` 生成报告，CI 不仅上传为构建工件，还会在 GitHub Job Summary 中渲染 CTA/Offline 状态表格（无需下载即可查看）。

- **全局变量**  
  - `PLAYWRIGHT_VERIFY_ATTEMPTS` / `PLAYWRIGHT_VERIFY_RETRY_DELAY`：控制全局 setup 在验证 `/dashboard` 之前的重试次数与间隔，调试不稳定环境时可在命令行导出：  
    ```bash
    PLAYWRIGHT_VERIFY_ATTEMPTS=5 PLAYWRIGHT_VERIFY_RETRY_DELAY=8000 npm run test:e2e:smoke
    ```

---

## 文档与导航

- 文档主页：`docs/index.md`
- 架构：`docs/architecture/INDEX.md`
- API：`docs/api/INDEX.md`
- 指南：`docs/guides/INDEX.md`

---

## 贡献

欢迎 Issue 与 PR。请在提交前运行本地验证脚本与测试，确保通过质量门禁。

---

## 许可证

本项目基于 MIT 许可证发布，详见 `LICENSE`。

---

## LEGAL DISCLAIMER

This software is not affiliated with or endorsed by any commercial entity, publisher, or rights holder of any intellectual property (including, but not limited to, Games Workshop Group PLC). This is an independent, non-commercial project developed for educational and research purposes. See `LEGAL.md`.
