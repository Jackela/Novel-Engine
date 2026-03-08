# 全面合规修复 - 分包工作计划

**目标：** B+ (73/100) → A+ (95+/100)  
**方法：** 13个分包并行执行  
**预计时间：** 1周（并行）  
**资源：** 13个Subagent同时工作

---

## 📦 分包结构

### MyPy错误修复分包 (4个)

#### 分包1.1: agents/ - 430个错误
- **范围：** `src/agents/` 所有Python文件
- **错误类型：** no-untyped-def, attr-defined, arg-type
- **文件数：** ~19个
- **预计减少：** 400-430个错误
- **Agent：** MyPy修复专员-A

#### 分包1.2: contexts/knowledge/ - 281个错误
- **范围：** `src/contexts/knowledge/` 所有Python文件
- **错误类型：** assignment, return-value, union-attr
- **文件数：** ~47个
- **预计减少：** 250-280个错误
- **Agent：** MyPy修复专员-B

#### 分包1.3: contexts/narratives/ - 421个错误
- **范围：** `src/contexts/narratives/` 所有Python文件
- **错误类型：** attr-defined, union-attr, var-annotated
- **文件数：** ~35个
- **预计减少：** 380-420个错误
- **Agent：** MyPy修复专员-C

#### 分包1.4: interactions/ + orchestration/ - 490个错误
- **范围：**
  - `src/contexts/interactions/` (86错误)
  - `src/contexts/orchestration/` (404错误)
- **错误类型：** arg-type, return-value, no-untyped-def
- **文件数：** ~60个
- **预计减少：** 450-490个错误
- **Agent：** MyPy修复专员-D

**MyPy合计：** 4,200 → ~2,500 (-1,700)

---

### 测试覆盖分包 (3个)

#### 分包2.1: agents/ - 0% → 70%
- **范围：** `src/agents/` 所有模块
- **当前：** 0%覆盖
- **目标：** 70%覆盖
- **测试数：** 150+ 测试用例
- **关键文件：**
  - persona_core.py
  - agent_coordinator.py
  - agent_factory.py
  - task_scheduler.py
- **Agent：** 测试专员-A

#### 分包2.2: contexts/narratives/ - 0% → 70%
- **范围：** `src/contexts/narratives/` 所有模块
- **当前：** 0%覆盖
- **目标：** 70%覆盖
- **测试数：** 180+ 测试用例
- **关键文件：**
  - narrative_flow_service.py
  - story_arc_service.py
  - plot_manager.py
  - narrative_generation_service.py
- **Agent：** 测试专员-B

#### 分包2.3: contexts/orchestration/ + interactions/ - 0% → 70%
- **范围：**
  - `src/contexts/orchestration/` 
  - `src/contexts/interactions/`
- **当前：** 0%覆盖
- **目标：** 70%覆盖
- **测试数：** 200+ 测试用例
- **关键文件：**
  - turn_orchestrator.py
  - saga_coordinator.py
  - interaction_engine.py
  - negotiation_service.py
- **Agent：** 测试专员-C

**测试覆盖合计：** 25% → 50% (+25%)

---

### Result[T,E]模式分包 (2个)

#### 分包3.1: contexts/knowledge/ - 24个服务
- **范围：** `src/contexts/knowledge/application/services/`
- **当前：** 0%采用
- **目标：** 80%采用
- **服务数：** 24个服务
- **方法数：** ~200个方法
- **关键服务：**
  - KnowledgeIngestionService
  - RetrievalService
  - BM25Retriever
  - EmbeddingService
  - DocumentProcessor
- **Agent：** 错误处理专员-A

#### 分包3.2: contexts/narrative/ + world/ - 25个服务
- **范围：**
  - `src/contexts/narrative/application/services/`
  - `src/contexts/world/application/services/`
- **当前：** <10%采用
- **目标：** 80%采用
- **服务数：** 25个服务
- **方法数：** ~220个方法
- **关键服务：**
  - NarrativeGenerationService
  - StoryService
  - WorldService
  - EventService
  - LocationService
- **Agent：** 错误处理专员-B

**Result模式合计：** 15% → 55% (+40%)

---

### StructLog分包 (2个)

#### 分包4.1: agents/ + core/ - 67个文件
- **范围：**
  - `src/agents/` (19文件)
  - `src/core/` (48文件)
- **当前：** 0-20%采用
- **目标：** 80%采用
- **文件数：** 67个
- **Agent：** 日志专员-A

#### 分包4.2: contexts/ + interactions/ - 100+文件
- **范围：**
  - `src/contexts/knowledge/` (76文件)
  - `src/contexts/narratives/` (50文件)
  - `src/contexts/interactions/` (52文件)
- **当前：** 30-40%采用
- **目标：** 80%采用
- **文件数：** 100+
- **Agent：** 日志专员-B

**StructLog合计：** 42% → 75% (+33%)

---

### E2E测试分包 (1个)

#### 分包5: 端到端测试
- **范围：** 关键用户旅程
- **当前：** 0.1%
- **目标：** 10%
- **测试数：** 20个E2E测试
- **场景：**
  - 用户注册/登录流程
  - 创建角色完整流程
  - 开始故事会话流程
  - 知识库上传和检索流程
  - 多人协商流程
- **Agent：** E2E测试专员

---

## 📊 执行计划

### 阶段1: 启动所有分包 (Day 1)
同时派遣13个agents:
- 4个 MyPy修复agents
- 3个 测试覆盖agents
- 2个 Result模式agents
- 2个 StructLogagents
- 1个 E2E测试agent
- 1个 协调员agent (监控进度)

### 阶段2: 中期检查 (Day 3)
- 每个agent汇报进度
- 解决阻塞问题
- 调整资源分配

### 阶段3: 完成和验证 (Day 5-7)
- 所有分包完成
- 集成测试
- 最终验证

---

## 🎯 预期结果

| 指标 | 当前 | 目标 | 变化 |
|------|------|------|------|
| MyPy错误 | 4,200 | <1,500 | -2,700 |
| 测试覆盖 | 25% | 50% | +25% |
| Result模式 | 15% | 55% | +40% |
| StructLog | 42% | 75% | +33% |
| E2E测试 | 0.1% | 10% | +9.9% |
| **总分** | **73** | **95+** | **+22** |

---

## 🔧 Subagent任务模板

每个subagent将收到：
1. 明确的任务范围（具体文件/目录）
2. 可量化的目标（错误数/覆盖率）
3. 详细的技术规范
4. 验收标准
5. 提交格式要求

---

## ✅ 成功标准

每个分包的验收标准：
- [ ] 代码通过所有现有测试
- [ ] 新代码有对应测试
- [ ] 通过mypy检查（对应分包）
- [ ] 通过lint检查
- [ ] 文档已更新
