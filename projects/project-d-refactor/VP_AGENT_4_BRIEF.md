# VP Agent 4 - 工作说明书

**项目编号**: NE-2024-004  
**项目名称**: 技术债务清理与架构优化  
**汇报对象**: CTO Office

---

## 任命书

你被任命为 **Project D** 的 VP Agent（重构优化负责人）。

你的使命是组建并领导开发团队，在1周内完成技术债务清理。

---

## 接收包

### 需求文档
- [项目需求文档](docs/requirements.md) - 完整的需求规范
- [验收模板](templates/acceptance_template.md) - 验收标准清单

### 目标清单

#### 目标1: 拆分 oversized 文件
```bash
# 检查超大文件
find src -name "*.py" -exec wc -l {} + | awk '$1 > 1000 {print $1, $2}'

# 目标文件:
# - src/contexts/orchestration/engine.py (~1,247行)
# - src/services/agent_service.py (~1,156行)
```

#### 目标2: 清理 ai_intelligence/ 死代码
```bash
# 检查死代码
vulture src/ai_intelligence/ --min-confidence 80
```

#### 目标3: 替换阻塞I/O
```bash
# 查找requests使用
grep -r "import requests" src/ --include="*.py"
# 替换为 httpx
```

---

## 职责范围

### 核心职责
1. **团队组建**: 招募1-2名开发人员
2. **影响分析**: 分析重构影响范围
3. **执行监督**: 确保重构不改变行为
4. **质量控制**: 严格的回归测试
5. **风险管控**: 识别高风险变更
6. **最终交付**: 组织验收并提交交付物

### 决策权限
- ✅ 拆分策略决策
- ✅ 删除确认决策
- ⚠️ 影响API的变更需CTO审批
- ❌ 不能修改业务逻辑行为

---

## 交付物要求

| 交付物 | 路径 | 截止时间 |
|--------|------|----------|
| 重构计划 | `deliverables/refactor_plan.md` | Day 1 |
| 重构后代码 | `deliverables/refactored_code/` | Day 5 |
| 性能报告 | `deliverables/performance_report.md` | Day 6 |
| 清理报告 | `deliverables/cleanup_report.md` | Day 7 |

---

## 验收标准

### 代码结构验收
```bash
# 超大文件检查
find src -name "*.py" -exec wc -l {} + | awk '$1 > 1000 {print $1, $2}'
# 必须返回空

# 死代码检查
vulture src/ai_intelligence/ --min-confidence 80
# 死代码 < 5处

# requests检查
grep -r "import requests" src/ --include="*.py" | grep -v "compat"
# 必须返回空
```

### 性能验收
- 并发HTTP请求吞吐量提升 ≥ 30%
- 基准测试通过

### 回归验收
- 所有测试通过
- 无行为变更
- 公共API向后兼容

---

## 时间线

```
Week 1 (Day 1-7)
├── Day 1: 影响分析，提交重构计划
├── Day 2-3: 文件拆分
├── Day 4: 死代码清理
├── Day 5: 阻塞I/O替换
├── Day 6: 性能测试，Bug修复
└── Day 7: 最终验收，文档交付
```

---

## 重构原则

### 黄金法则
1. **不改变行为**: 重构前后外部行为完全一致
2. **小步提交**: 每次变更一个职责，单独提交
3. **自动化验证**: 每次提交必须通过全部测试

### 文件拆分策略
```python
# 策略: 垂直拆分
src/contexts/orchestration/
├── __init__.py          # 保持兼容导入
├── engine.py            # 精简后的核心
├── coordinator.py       # 协调逻辑
├── executor.py          # 执行逻辑
└── models.py            # 数据模型
```

### 死代码清理流程
1. 使用 `vulture` 识别候选
2. 使用 `grep` 确认无引用
3. Git历史中确认非临时注释
4. 删除并记录

---

## 报告要求

### 每日报告 (Day 1-7, 18:00前)
```
Project D - Day X 状态:
- 今日完成:
  - [重构内容]
- 进度:
  - 文件拆分: [X/Y]
  - 死代码清理: [X/Y]
  - I/O替换: [X/Y]
- 风险: [如有]
- 测试状态: [全部通过/有失败]
```

---

## 成功标准

项目成功的定义：
1. ✅ 无文件 > 1000行
2. ✅ requests 完全替换为 httpx
3. ✅ 性能提升 ≥ 30%
4. ✅ 零回归缺陷
5. ✅ 所有测试通过

---

**任命日期**: 2024-03-04  
**任命人**: CTO Office  
**接受确认**: [VP Agent 4 签字]
