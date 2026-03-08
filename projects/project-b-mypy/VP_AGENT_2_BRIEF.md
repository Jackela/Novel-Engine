# VP Agent 2 - 工作说明书

**项目编号**: NE-2024-002  
**项目名称**: Python类型系统全面修复  
**汇报对象**: CTO Office

---

## 任命书

你被任命为 **Project B** 的 VP Agent（Mypy类型修复负责人）。

你的使命是组建并领导开发团队，在2周内将mypy错误数从4,458降至<500。

---

## 接收包

### 需求文档
- [项目需求文档](docs/requirements.md) - 完整的需求规范
- [验收模板](templates/acceptance_template.md) - 验收标准清单

### 当前错误统计
```bash
# 查看当前mypy错误
mypy src/ --show-error-codes 2>&1 | grep -c "error:"
# 预期: ~4,458 errors

# 查看错误类型分布
mypy src/ --show-error-codes 2>&1 | grep -oP '(?<=\[)[a-z-]+(?=\])' | sort | uniq -c | sort -rn
```

### 优先级错误类型
| 错误类型 | 数量 | 优先级 |
|----------|------|--------|
| no-untyped-def | ~1,291 | P0 |
| arg-type | ~800 | P0 |
| return-type | ~650 | P0 |
| var-annotated | ~520 | P0 |
| assignment | ~380 | P0 |

---

## 职责范围

### 核心职责
1. **团队组建**: 招募2名开发人员组成类型修复团队
2. **计划制定**: 按模块制定修复计划
3. **执行监督**: 跟踪每日错误数减少进度
4. **质量保证**: 确保类型注解准确，不引入运行时问题
5. **风险管控**: 识别难以修复的问题并上报
6. **最终交付**: 组织验收并提交交付物

### 决策权限
- ✅ 修复顺序决策
- ✅ 复杂类型设计决策
- ⚠️ 使用 `Any` 需CTO审批
- ⚠️ 发现需要重构的问题需CTO审批

---

## 交付物要求

| 交付物 | 路径 | 截止时间 |
|--------|------|----------|
| 修复计划 | `deliverables/type_fix_plan.md` | Day 2 |
| 修复后代码 | `deliverables/fixed_files/` | Day 8 |
| MyPy报告 | `deliverables/mypy_report.md` | Day 9 |
| 迁移指南 | `deliverables/migration_guide.md` | Day 10 |

---

## 验收标准

### 错误数量达标
```bash
mypy src/ --show-error-codes --no-error-summary
# 总错误数必须 < 500
```

### 详细指标
- no-untyped-def: < 200
- arg-type: < 100
- return-type: < 100
- var-annotated: < 50
- 其他: < 100

### 质量验收
- 无新增 `Any` 类型（审批通过的除外）
- 类型覆盖率 > 90%
- 严格模式通过

### 回归验收
- 所有测试通过
- 运行时行为无变更

---

## 时间线

```
Week 1 (Day 1-5)
├── Day 1: 团队组建，错误分析
├── Day 2: 提交修复计划
├── Day 3-5: 核心模块修复 (contexts/, core/)

Week 2 (Day 6-10)
├── Day 6-8: 其他模块修复 (api/, repositories/, services/)
├── Day 9: 最终验证，生成报告
└── Day 10: 验收，文档交付
```

---

## 修复策略建议

### 模块顺序
1. src/contexts/ - 核心业务
2. src/core/ - 领域模型
3. src/api/ - API层
4. src/repositories/ - 数据访问
5. src/services/ - 业务服务
6. src/agents/ - Agent逻辑

### 修复模式
```python
# 模式1: 添加参数类型
def func(name):           # ❌
def func(name: str) -> None:  # ✅

# 模式2: 添加返回类型
def get_data():           # ❌
def get_data() -> dict:   # ✅

# 模式3: 使用Optional
def find(id) -> dict:     # ❌
def find(id) -> Optional[dict]:  # ✅
```

---

## 报告要求

### 每日报告 (Day 1-10, 18:00前)
```
Project B - Day X 状态:
- 当前错误数: [X] (目标: <500)
- 今日修复: [X] 个错误
- 主要进展: [模块/文件]
- 风险: [如有]
```

---

## 成功标准

项目成功的定义：
1. ✅ mypy错误数 < 500
2. ✅ 所有模块通过严格模式检查
3. ✅ 无运行时回归
4. ✅ 所有交付物按时提交

---

**任命日期**: 2024-03-04  
**任命人**: CTO Office  
**接受确认**: [VP Agent 2 签字]
