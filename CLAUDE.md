# Novel Engine - AI 开发指南

## 快速开始

### 技术栈
- **后端**: Python 3.11+, FastAPI, Pydantic
- **前端**: TypeScript, React, Vite
- **AI**: Google Gemini 2.0 Flash
- **架构**: DDD (Domain-Driven Design)

### 构建命令
```bash
# 后端
python -m src.api.main_api_server

# 前端
cd frontend && npm run dev

# 测试
pytest tests/
npm run test
```

### 测试命令
```bash
# Python 单元测试
pytest tests/unit/

# Python 集成测试
pytest tests/integration/

# E2E 测试
npm run test:e2e
```

## Ralph Loop（迭代操作手册）
目标：最小化试错，确保每轮变更都可追踪、可验证、可复现。

## Contract-First Protocol

- When modifying APIs, always update Pydantic models first, regenerate `docs/api/openapi.json`, then update frontend Zod schemas.
- Frontend: Use `npm run type-check` for validation.
- Backend: Use `pytest`.

### R - Read（阅读与上下文）
- 读取 `CLAUDE.md`、`AGENTS.md`（若存在）与关键 ADR
- 扫描变更区域：`rg -n "关键词" src/ tests/ docs/`
- 明确 SSoT（单一真相来源），避免重复实现

### A - Align（对齐目标）
- 明确本轮目标、边界、完成标准
- 识别必须跑的验证命令（测试、lint、build）
- 如果涉及 API/Schema/契约，先更新对应模型与文档

### L - Locate（定位改动）
- 锁定要改的模块、入口与导出路径
- 核对 `__init__.py` 导出与公共 API 面
- 标记潜在影响的测试与文档

### P - Patch（小步修补）
- 小步提交可读的改动（必要时拆分文件）
- 改动与文档/配置同步更新
- 避免引入重复逻辑或新的遗留入口

### H - Harden（验证闭环）
- 后端：`pytest tests/` + `flake8`
- 前端：`cd frontend && npm run type-check && npm run lint:all`
- 全量：`scripts/validate_ci_locally.sh`
- 确保控制台输出无警告/报错，必要时补充注释与说明

## 项目结构

### 核心目录
```
src/
├── api/              # FastAPI 路由和端点
├── contexts/         # DDD 领域模块（已集中）
├── core/             # 核心基础设施
├── agents/           # Agent 实现
│   ├── persona_agent/    # 角色 Agent
│   └── director_agent/   # 导演 Agent
└── director_components/  # 导演组件（已模块化）
```

### 领域模块（src/contexts/）
- **narratives/** - 叙事生成领域（持续扩展）
- **character/** - 角色管理领域（已落地）
- **orchestration/** - 编排领域（已落地）
- **interactions/** - 互动协商领域
- **knowledge/** - 知识管理领域
- **subjective/** - 主观视角领域
- **world/** - 世界状态领域

## 代码风格

### Python
- 遵循 PEP 8
- 使用类型注解 (Type Hints)
- Pydantic 用于数据验证
- 异步优先 (async/await)

### TypeScript
- 严格模式 (strict: true)
- React Hooks
- Zustand 状态管理
- TanStack Query 数据获取

## 导入规范

> [!IMPORTANT]
> Strictly enforce boundaries via `import-linter`. **Do not import `src.api` inside `src.contexts`.**


### 推荐导入路径
```python
# ✅ 推荐：从模块化组件导入
from src.director_components.turn_execution import TurnOrchestrator
from src.agents.persona_agent.agent import PersonaAgent

# ❌ 避免：从遗留根目录导入
from src.core.turn_orchestrator import TurnOrchestrator  # 已废弃
from src.persona_agent import PersonaAgent          # 已移除       
```

## 架构决策记录 (ADR)

关键架构决策请参考：
- `docs/adr/001-ddd-migration.md`
- `docs/adr/002-api-standardization.md`

## 当前重构状态

**Wave 3 完成**:
- ✅ API 路由标准化
- ✅ 配置文件迁移至 config/

**进行中**:
- 🔄 遗留代码清理
- 🔄 DDD 领域模块完善

**规划中**:
- 📋 PersonaAgent 统一重构
- 📋 完整的 DDD 分层架构




