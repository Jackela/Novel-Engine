# 技术债务清理与架构优化 - 重构计划

> **项目编号**: NE-2024-004  
> **角色**: VP of Engineering / Tech Lead  
> **日期**: 2026-03-04

---

## 执行策略

**执行方式**: Subagent-Driven Development  
**所需技能**: `superpowers:subagent-driven-development`

---

## 项目概览

### 目标
清理技术债务，优化架构，修复阻塞 I/O，提升代码可维护性。

### 关键指标
- 所有文件 < 1000 行
- 无阻塞 I/O (requests → httpx)
- ai_intelligence/ 清理完成
- 性能基准通过
- 所有测试通过
- 无架构违规

---

## Task 1: 拆分 structure.py (P0)

**当前状态**: 2,810 行  
**目标**: 拆分为多个 < 1000 行的模块

**文件**: `src/api/routers/structure.py`

### 分析结果

从代码分析，structure.py 包含以下功能模块：

1. **Story 管理** (行 150-300)
   - 创建、读取、更新、删除 Story
   - 响应转换函数: `_story_to_response`

2. **Chapter 管理** (行 300-600)
   - Chapter CRUD 操作
   - Chapter 分析、健康检查
   - 响应转换: `_chapter_to_response`

3. **Scene 管理** (行 600-1000)
   - Scene CRUD 操作
   - Scene 节拍、 critique
   - 响应转换: `_scene_to_response`

4. **Beat 管理** (行 1000-1400)
   - Beat CRUD 操作
   - Beat 重新排序
   - 响应转换: `_beat_to_response`

5. **Conflict 管理** (行 1640-1800)
   - Conflict CRUD
   - 响应转换: `_conflict_to_response`

6. **Plotline 管理** (行 1947-2100)
   - Plotline CRUD
   - Scene 关联
   - 响应转换: `_plotline_to_response`

7. **Foreshadowing 管理** (行 2027-2200)
   - Foreshadowing CRUD
   - Payoff 链接
   - 响应转换: `_foreshadowing_to_response`

8. **共享工具函数** (分散在各处)
   - `_parse_uuid`
   - 存储辅助函数

### 拆分方案

```
src/api/routers/structure/
├── __init__.py          # 聚合所有路由
├── common.py            # 共享工具函数 (200行)
├── stories.py           # Story 路由 (300行)
├── chapters.py          # Chapter 路由 (400行)
├── scenes.py            # Scene 路由 (500行)
├── beats.py             # Beat 路由 (400行)
├── conflicts.py         # Conflict 路由 (300行)
├── plotlines.py         # Plotline 路由 (350行)
└── foreshadowing.py     # Foreshadowing 路由 (300行)
```

### 实施步骤

**Step 1: 创建目录结构**
```bash
mkdir -p src/api/routers/structure
```

**Step 2: 提取共享工具函数到 common.py**
- 提取 `_parse_uuid`
- 提取所有 `_store_*` 辅助函数
- 提取所有 `_get_*` 辅助函数
- 提取响应转换函数

**Step 3: 逐个拆分路由模块**
每个模块遵循相同模式：
1. 复制相关路由函数
2. 更新 imports
3. 从原文件删除
4. 运行测试验证

**Step 4: 更新主路由文件**
创建新的 `structure/__init__.py`：
```python
from fastapi import APIRouter

from . import beats, chapters, conflicts, foreshadowing, plotlines, scenes, stories

router = APIRouter()
router.include_router(stories.router, prefix="/stories")
router.include_router(chapters.router, prefix="/chapters")
router.include_router(scenes.router, prefix="/scenes")
router.include_router(beats.router, prefix="/beats")
router.include_router(conflicts.router, prefix="/conflicts")
router.include_router(plotlines.router, prefix="/plotlines")
router.include_router(foreshadowing.router, prefix="/foreshadowing")
```

**Step 5: 更新 import 路径**
搜索并替换所有对 `structure.py` 的导入

**Step 6: 运行测试**
```bash
pytest tests/ -x -v
```

**Step 7: 提交**
```bash
git add src/api/routers/structure/
git commit -m "refactor: split structure.py into modular routers"
```

### 风险缓解
- 保持原有 API 路径不变
- 保持函数签名不变
- 小步提交，每次拆分一个模块

---

## Task 2: 拆分 brain_settings.py (P0)

**当前状态**: 2,230 行  
**目标**: 拆分为多个 < 1000 行的模块

**文件**: `src/api/routers/brain_settings.py`

### 分析结果

brain_settings.py 包含以下功能：

1. **API Keys 管理** (行 359-554)
   - 获取/更新 API Keys
   - 加密/解密逻辑

2. **RAG 配置** (行 440-500)
   - RAG 配置获取/更新

3. **Token 使用分析** (行 626-1036)
   - 使用统计
   - 导出功能
   - 实时流

4. **Ingestion Jobs** (行 1325-1740)
   - 知识库摄取任务
   - 任务状态查询

5. **Chat 功能** (行 1876-2230)
   - Chat 会话管理
   - 消息处理

### 拆分方案

```
src/api/routers/brain/
├── __init__.py          # 聚合所有路由
├── common.py            # 共享工具 (加密、仓库获取)
├── api_keys.py          # API Keys 路由 (200行)
├── rag_config.py        # RAG 配置路由 (150行)
├── token_usage.py       # Token 使用分析 (350行)
├── ingestion.py         # Ingestion jobs (400行)
└── chat.py              # Chat 功能 (450行)
```

### 实施步骤

与 Task 1 类似，逐个提取模块并测试。

---

## Task 3: 拆分 chunking_strategy_adapters.py (P0)

**当前状态**: 2,531 行  
**目标**: 使用策略模式重构

**文件**: `src/contexts/knowledge/infrastructure/adapters/chunking_strategy_adapters.py`

### 分析结果

包含 7 个 Chunking 策略类：

1. `CoherenceScore` - 评分工具
2. `ChunkCoherenceAnalyzer` - 连贯性分析器
3. `FixedChunkingStrategy` - 固定大小分块
4. `SentenceChunkingStrategy` - 句子分块
5. `ParagraphChunkingStrategy` - 段落分块
6. `SemanticChunkingStrategy` - 语义分块
7. `NarrativeFlowChunkingStrategy` - 叙事流分块
8. `AutoChunkingStrategy` - 自动选择策略

### 拆分方案

```
src/contexts/knowledge/infrastructure/adapters/chunking/
├── __init__.py                    # 导出所有策略
├── base.py                        # 抽象基类/接口
├── coherence.py                   # CoherenceScore, ChunkCoherenceAnalyzer
├── fixed_strategy.py              # FixedChunkingStrategy
├── sentence_strategy.py           # SentenceChunkingStrategy
├── paragraph_strategy.py          # ParagraphChunkingStrategy
├── semantic_strategy.py           # SemanticChunkingStrategy
├── narrative_flow_strategy.py     # NarrativeFlowChunkingStrategy
└── auto_strategy.py               # AutoChunkingStrategy
```

### 实施步骤

**Step 1: 创建基类**
定义 `ChunkingStrategy` 抽象基类

**Step 2: 逐个迁移策略类**
每个策略类独立成文件

**Step 3: 更新 imports**
确保所有引用更新

---

## Task 4: 修复阻塞 I/O - 迁移到 httpx.AsyncClient (P0)

**目标**: 将所有 sync requests.post 替换为 async httpx.AsyncClient

### 受影响文件

| 文件 | 位置 | 当前代码 |
|------|------|----------|
| `src/api/services/prompt_router_service.py` | 779, 848, 915, 977 | `requests.post()` |
| `src/contexts/world/infrastructure/generators/llm_world_generator.py` | 260 | `requests.post()` |
| `src/contexts/world/infrastructure/generators/character_profile_generator.py` | 441 | `requests.post()` |
| `src/contexts/character/infrastructure/generators/llm_character_generator.py` | 94 | `requests.post()` |
| `src/contexts/story/infrastructure/generators/llm_scene_generator.py` | 112 | `requests.post()` |

### 迁移模式

**Before:**
```python
import requests

def call_llm(endpoint, data):
    response = requests.post(endpoint, json=data, timeout=120)
    return response.json()
```

**After:**
```python
import httpx

async def call_llm(endpoint, data):
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(endpoint, json=data)
        response.raise_for_status()
        return response.json()
```

### 实施步骤

**Step 1: 检查依赖**
```bash
pip list | grep httpx
# 确保 httpx 已安装
```

**Step 2: 逐个文件迁移**

每个文件遵循以下步骤：
1. 将函数改为 `async def`
2. 替换 `requests.post` 为 `httpx.AsyncClient`
3. 在调用处添加 `await`
4. 更新调用链（可能需要将调用者改为 async）
5. 运行测试验证

**Step 3: 更新调用链**

如果函数 A 调用函数 B，且 B 改为 async：
- A 也必须改为 async
- A 的调用者也要相应修改
- 一直向上到 FastAPI 路由（天然支持 async）

**Step 4: 错误处理兼容**

确保 httpx 错误处理与 requests 兼容：
```python
# requests
try:
    response = requests.post(...)
    response.raise_for_status()
except requests.exceptions.RequestException as e:
    ...

# httpx
try:
    async with httpx.AsyncClient() as client:
        response = await client.post(...)
        response.raise_for_status()
except httpx.HTTPError as e:
    ...
```

**Step 5: 测试**
```bash
pytest tests/unit/ -x -v
pytest tests/integration/ -x -v
```

---

## Task 5: 清理 ai_intelligence/ 死代码 (P1)

**注意**: 经过检查，`src/**/ai_intelligence/` 目录不存在。此任务标记为已完成。

如果后续发现 ai_intelligence 代码，清理策略：

1. 分析每个文件的 imports
2. 如果有 active imports → 保留并标记
3. 如果无 imports 且无测试 → 删除
4. 如果是实验性代码 → 移动到 `experiments/`

---

## Task 6: 性能基准测试

### 运行基准测试

```bash
# 运行基准测试
pytest tests/benchmarks/ -v

# 生成报告
pytest tests/benchmarks/ --benchmark-json=.benchmarks/results.json
```

### 关键指标

- API 响应时间 (p50, p95, p99)
- LLM 调用延迟
- 内存使用率
- 并发处理能力

---

## 质量门禁

每个任务完成后必须运行：

```bash
# 1. 静态检查
mypy src/ --ignore-missing-imports
ruff check src/
import-linter

# 2. 单元测试
pytest tests/unit/ -x

# 3. 集成测试
pytest tests/integration/ -x

# 4. 架构检查
# - 无循环依赖
# - 符合 Hexagonal Architecture
```

---

## 交付物检查清单

- [x] refactor_plan.md (本文件)
- [ ] 所有 oversized 文件已拆分 (<1000行)
- [ ] 所有阻塞 I/O 已修复 (httpx)
- [ ] ai_intelligence/ 已清理 (如存在)
- [ ] performance_report.md (包含基准对比)
- [ ] cleanup_report.md (清理总结)
- [ ] 所有测试通过
- [ ] 代码审查完成

---

## 风险矩阵

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 重构引入回归 | 中 | 高 | 完整测试覆盖，小步提交 |
| httpx 不兼容 | 低 | 高 | 渐进式迁移，保留 fallback |
| 拆分破坏 import | 中 | 中 | 全局搜索替换，测试验证 |
| 性能未提升 | 低 | 中 | 基准测试对比，可回滚 |
| 调用链遗漏 | 中 | 高 | 类型检查，全面测试 |

---

## 执行顺序

```
Day 1-2: Task 1 (structure.py 拆分)
Day 3:   Task 2 (brain_settings.py 拆分)
Day 4:   Task 3 (chunking_strategy_adapters.py 拆分)
Day 5-6: Task 4 (阻塞 I/O 修复)
Day 7:   Task 6 (性能基准) + 文档编写
```

---

## 团队分派

### Refactor Team
- Task 1: structure.py 拆分
- Task 2: brain_settings.py 拆分
- Task 3: chunking_strategy_adapters.py 拆分
- Task 5: ai_intelligence/ 清理

### Performance Team
- Task 4: 阻塞 I/O 修复
- Task 6: 性能基准测试

---

*计划完成，准备分派子代理执行任务*
