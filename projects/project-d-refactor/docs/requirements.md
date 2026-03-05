# 项目需求文档

## 项目信息
- **项目编号**: NE-2024-004
- **项目名称**: 技术债务清理与架构优化
- **预算**: 2个开发团队周
- **交付期限**: 1周
- **优先级**: P1

---

## 1. 项目背景

Novel-Engine平台经过多年发展，累积了以下技术债务：
- 部分文件过大（>1000行），违反单一职责原则
- `ai_intelligence/` 目录存在大量死代码
- 使用阻塞I/O（requests）影响异步性能

本项目旨在清理技术债务，提升代码质量和性能。

---

## 2. 功能需求

### 2.1 必须实现 (P0)

#### 2.1.1 拆分 oversized 文件
识别并拆分超过1000行的文件：

| 文件路径 | 当前行数 | 拆分策略 |
|----------|----------|----------|
| src/contexts/orchestration/engine.py | ~1,247 | 拆分为 engine/, coordinator.py, executor.py |
| src/services/agent_service.py | ~1,156 | 拆分为 agent_service/, handlers/, utils/ |
| src/repositories/event_repository.py | ~983 | 提取查询构建器 |

拆分原则：
- [ ] 保持公共API向后兼容
- [ ] 按职责垂直拆分
- [ ] 每个新文件 < 500行
- [ ] 添加 `__init__.py` 保持导入兼容

#### 2.1.2 清理 ai_intelligence/ 死代码
- [ ] 识别未引用函数/类
- [ ] 识别重复实现
- [ ] 安全删除死代码
- [ ] 更新导入引用

**清理清单**:
```
src/ai_intelligence/
├── legacy_prompts.py      [待评估]
├── deprecated_models.py   [待删除]
├── unused_utils.py        [待删除]
└── duplicated_logic.py    [待合并]
```

#### 2.1.3 替换阻塞I/O (requests → httpx)
- [ ] 识别所有 `requests` 使用点
- [ ] 替换为 `httpx.AsyncClient`（异步上下文）
- [ ] 替换为 `httpx.Client`（同步上下文必须保留时）
- [ ] 更新测试mock

**替换范围**:
- `src/contexts/ai/clients/`
- `src/services/external/`
- `src/infrastructure/http/`

### 2.2 应该实现 (P1)
- [ ] 引入代码复杂度检查（radon/mccabe）
- [ ] 添加循环导入检测
- [ ] 统一异常层次结构

---

## 3. 非功能需求

### 3.1 性能要求
- HTTP客户端替换后，并发请求吞吐量提升 ≥ 30%
- 文件拆分后，导入时间不变或缩短
- 整体包大小减少 ≥ 5%

### 3.2 质量要求
- 零行为变更（重构前后功能完全一致）
- 所有公共API保持向后兼容
- 测试覆盖率不降低

### 3.3 安全要求
- 删除代码前必须经过静态分析确认无引用
- 保留重要历史代码的Git历史记录

---

## 4. 验收标准

### 4.1 代码结构验收
- [ ] `find src -name "*.py" -exec wc -l {} + | awk '$1 > 1000'` 返回空
- [ ] `vulture src/ai_intelligence/` 报告死代码 < 5处
- [ ] `grep -r "import requests" src/` 返回空（除了兼容层）

### 4.2 性能验收
- [ ] 基准测试通过（对比重构前后）
- [ ] 并发HTTP请求吞吐量提升 ≥ 30%

### 4.3 回归验收
- [ ] 所有单元测试通过
- [ ] 所有集成测试通过
- [ ] E2E测试通过
- [ ] 手动冒烟测试通过

---

## 5. 交付物清单

| 序号 | 交付物 | 路径 | 说明 |
|------|--------|------|------|
| 1 | 重构计划 | `deliverables/refactor_plan.md` | 详细重构方案 |
| 2 | 重构后代码 | `deliverables/refactored_code/` | 变更文件清单 |
| 3 | 性能报告 | `deliverables/performance_report.md` | 前后对比数据 |
| 4 | 清理报告 | `deliverables/cleanup_report.md` | 删除/修改统计 |

---

## 6. 技术约束

### 6.1 重构原则
- **不改变行为**: 重构前后外部行为完全一致
- **小步提交**: 每次变更一个职责，单独提交
- **自动化验证**: 每次提交必须通过全部测试

### 6.2 工具链
```bash
# 代码分析
vulture src/ --min-confidence 80
radon cc src/ -a -nc
mypy src/ --strict

# 性能测试
pytest tests/benchmarks/ -v
```

### 6.3 禁止事项
- 禁止在重构中"顺手"修复bug（单独提交）
- 禁止添加新功能
- 禁止修改测试断言（除非测试本身错误）

---

## 7. 风险与应对

| 风险 | 可能性 | 影响 | 应对措施 |
|------|--------|------|----------|
| 意外删除有用代码 | 中 | 高 | 双重确认 + 代码审查 |
| 拆分导致导入循环 | 中 | 中 | 依赖分析后重构 |
| httpx兼容性问题 | 低 | 高 | 详细测试 + 回滚计划 |

---

**文档版本**: v1.0  
**创建日期**: 2024-03-04  
**审批人**: CTO Office
