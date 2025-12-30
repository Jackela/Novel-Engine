# Novel Engine（AI 叙事引擎）

语言/Languages: [English](README.en.md) | 简体中文

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![React 18+](https://img.shields.io/badge/react-18+-blue.svg)](https://react.dev/)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

面向生产的 AI 驱动叙事生成与多智能体模拟平台。本项目采用**模块化单体 (Modular Monolith)** 架构，结合**函数式核心与命令式外壳**设计原则，提供高内聚、低耦合的叙事编排能力。

---

## 🚀 核心特性

- **多智能体编排**：`DirectorAgent`（导演）、`PersonaAgent`（角色）、`ChroniclerAgent`（记录者）基于事件总线协作，而非硬编码调用。
- **访客优先架构**：无需注册数据库，基于**文件系统的工作空间 (Filesystem Workspaces)** 技术，支持零配置启动和即时演示。
- **实时流式交互**：后端 `/api/events/stream` (SSE) 配合前端 `useRealtimeEvents` 钩子，提供毫秒级叙事反馈。
- **统一 API 规范**：全站统一使用 `/api/*` 路由前缀，前端集成 SSOT（单一事实来源）API 客户端与自动错误处理。
- **生产级质量门禁**：
  - 前端：TypeScript 严格模式 + ESLint (SOLID 原则) + Vitest (80% 覆盖率要求)。
  - 后端：Mypy 类型检查 + Pytest 单元/集成测试。

![Dashboard Preview](docs/assets/dashboard/dashboard-flow-2025-11-14-condensed.png)

---

## 🏗️ 架构概览

本项目深受**领域驱动设计 (DDD)** 和 **“作者之死”** 叙事理论影响。

- **逻辑微服务**：虽然代码位于单一仓库 (`src/`)，但业务逻辑按领域严格隔离 (`contexts/characters`, `contexts/narratives`)。
- **文件即数据**：为了极致的可移植性与本地优先体验，所有角色卡、战役状态和会话记录均以 Markdown/YAML/JSON 格式存储在本地文件系统中。
- **API 优先**：前后端通过标准化的 REST API 通信，支持 OpenAPI (Swagger) 自动文档生成。

---

## 🛠️ 快速开始

### 环境要求
- Python 3.11+
- Node.js 18+ & npm

### 一键开发环境 (推荐)

我们提供统一的脚本来同时管理前后端进程：

1. **初始化依赖**：
   ```bash
   # 后端
   python -m venv .venv
   # Windows: .venv\Scripts\activate | Mac/Linux: source .venv/bin/activate
   pip install -r requirements.txt

   # 前端
   cd frontend
   npm install
   ```

2. **启动开发服务**：
   ```bash
   # 在根目录运行
   npm run dev:daemon
   ```
   - 后端 API: `http://127.0.0.1:8000`
   - 前端 UI: `http://127.0.0.1:3000`
   - 服务将在后台运行，日志输出至 `tmp/dev_env.log`。

3. **停止服务**：
   ```bash
   npm run dev:stop
   ```

---

## 📂 目录结构

```
Novel-Engine/
├── src/                  # 后端核心代码 (FastAPI + Agents)
│   ├── api/              # API 路由与应用工厂
│   ├── agents/           # 智能体逻辑 (Director, Persona)
│   ├── contexts/         # 领域边界 (DDD Contexts)
│   └── workspaces/       # 文件系统持久化层
├── frontend/             # 前端应用 (React + Vite)
│   ├── src/lib/api/      # SSOT API 客户端
│   ├── src/features/     # 业务功能模块
│   └── tests/            # Vitest & Playwright 测试
├── docs/                 # 架构文档与规范
├── openspec/             # 架构演进提案 (OpenSpec)
└── characters/           # 用户角色数据存储 (YAML/MD)
```

---

## 🧪 测试与质量

本项目强制执行严格的 TDD（测试驱动开发）流程。

- **后端测试**：
  ```bash
  pytest
  ```
- **前端测试**：
  ```bash
  cd frontend
  npm run test        # 单元测试 (Vitest)
  npm run lint        # 代码风格检查
  npm run type-check  # 类型检查
  ```
- **E2E 测试**：
  UI 变更必须通过 Playwright 验证：
  ```bash
  cd frontend
  npx playwright test
  ```

---

## 🤝 贡献指南

1. 遵循 `docs/coding-standards.md` 中的代码规范。
2. 提交前请运行本地验证脚本：`scripts/validate_ci_locally.sh`。
3. 重大架构变更需通过 `openspec` 提出提案。

---

## 📄 许可证

MIT License. See [LICENSE](LICENSE).

---

## LEGAL DISCLAIMER

**LEGAL DISCLAIMER**: Novel Engine is a fan-created, educational project and is not affiliated with Games Workshop or any other intellectual property holder. This work is intended for educational and research purposes only, and it operates independently of any commercial publishing efforts. While the project embraces stylistic inspirations from narrative-rich franchises, it does not represent or endorse their official lore.

For compliance, all fan-mode functionality is strictly documented and adheres to non-commercial use, local distribution, and content filtering expectations. If you build upon or share this work, please ensure that any redistribution follows those same principles and credit the original sources where appropriate.
