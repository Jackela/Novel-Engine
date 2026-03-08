# VP Agent 1 - 工作说明书

**项目编号**: NE-2024-001  
**项目名称**: 核心模块测试覆盖率提升项目  
**汇报对象**: CTO Office

---

## 任命书

你被任命为 **Project A** 的 VP Agent（测试覆盖率提升负责人）。

你的使命是组建并领导开发团队，在2周内完成核心模块的测试覆盖率提升目标。

---

## 接收包

### 需求文档
- [项目需求文档](docs/requirements.md) - 完整的需求规范
- [验收模板](templates/acceptance_template.md) - 验收标准清单

### 目标模块
```
src/caching/              (0% → 80%)
src/contexts/ai/          (0% → 80%)
src/contexts/interactions/ (0% → 80%)
src/contexts/orchestration/ (0% → 80%)
src/core/                 (7% → 60%)
```

### 当前状态
```bash
# 查看当前覆盖率
pytest --cov=src.caching --cov=src.contexts.ai \
       --cov=src.contexts.interactions --cov=src.contexts.orchestration \
       --cov=src.core tests/ -v --cov-report=term-missing
```

---

## 职责范围

### 核心职责
1. **团队组建**: 招募2-3名开发人员组成测试团队
2. **计划制定**: 制定详细的测试开发计划（每日任务分解）
3. **执行监督**: 跟踪进度，确保按时交付
4. **质量保证**: 确保测试代码质量符合标准
5. **风险管控**: 识别风险并及时上报CTO Office
6. **最终交付**: 组织验收并提交交付物

### 决策权限
- ✅ 测试策略决策
- ✅ 任务优先级调整
- ✅ 代码审查标准
- ⚠️ 需求变更需CTO审批
- ❌ 预算/时间调整需CTO审批

---

## 交付物要求

| 交付物 | 路径 | 截止时间 |
|--------|------|----------|
| 测试计划 | `deliverables/test_plan.md` | Day 2 |
| 测试用例代码 | `deliverables/test_cases/` | Day 8 |
| 覆盖率报告 | `deliverables/coverage_report.md` | Day 9 |
| 交接文档 | `deliverables/handover_doc.md` | Day 10 |

---

## 验收标准

### 覆盖率达标
```bash
# 必须全部通过
pytest --cov=src.caching tests/          # ≥ 80%
pytest --cov=src.contexts.ai tests/      # ≥ 80%
pytest --cov=src.contexts.interactions tests/  # ≥ 80%
pytest --cov=src.contexts.orchestration tests/ # ≥ 80%
pytest --cov=src.core tests/             # ≥ 60%
```

### 质量检查
- 所有测试通过 (`pytest -v` 无失败)
- 无测试代码异味
- 代码审查通过

### 回归验收
- 现有功能无破坏
- 集成测试通过

---

## 时间线

```
Week 1 (Day 1-5)
├── Day 1: 团队组建，熟悉代码
├── Day 2: 提交测试计划
├── Day 3-5: 第一轮测试开发 (caching, contexts/ai)

Week 2 (Day 6-10)
├── Day 6-8: 第二轮测试开发 (interactions, orchestration, core)
├── Day 9: 覆盖率验证，生成报告
└── Day 10: 最终验收，文档交付
```

---

## 报告要求

### 每日报告 (Day 1-10, 18:00前)
发送简短状态更新到CTO Office:
```
Project A - Day X 状态:
- 完成: [今日完成内容]
- 进度: [X%]
- 风险: [如有]
- 明日计划: [计划]
```

### 周报告 (Day 5, Day 10)
更新 `status.md` 包含:
- 完成百分比
- 已完成模块清单
- 遇到的阻碍
- 下周/剩余工作计划

---

## 成功标准

项目成功的定义：
1. ✅ 所有目标模块达到规定覆盖率
2. ✅ 所有交付物按时提交
3. ✅ 验收报告签字确认
4. ✅ 无重大回归缺陷

---

## 授权

VP Agent 1 被授权：
- 访问所有相关代码库
- 指派开发任务给团队成员
- 代表团队与CTO Office沟通
- 在授权范围内做技术决策

---

**任命日期**: 2024-03-04  
**任命人**: CTO Office  
**接受确认**: [VP Agent 1 签字]
