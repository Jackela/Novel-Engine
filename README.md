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

更多目录请见仓库根目录清单与 `docs/INDEX.md`。

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

前端（示例）

```
cd frontend
npm ci
npm run build:tokens
npm run dev
```

---

## 测试与质量

- Python 测试：`pytest`（配置见 `pytest.ini` / `.coveragerc`）
- 本地 CI 对齐验证：`scripts/validate_ci_locally.sh`（Windows 可用 `scripts/validate_ci_locally.ps1`）
- 前端质量门禁：`npm run type-check`、`npm run lint:all`、`npm run tokens:check`

---

## 文档与导航

- 文档主页：`docs/INDEX.md`
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

This project is an independent work and is not affiliated with, endorsed by, or associated with any third-party rights holders, including but not limited to Games Workshop. All references, if any, are used strictly for educational and research purposes. Trademarks and copyrights belong to their respective owners.
