# VP Agent 3 - 工作说明书

**项目编号**: NE-2024-003  
**项目名称**: Events & Rumors 系统扩展  
**汇报对象**: CTO Office

---

## 任命书

你被任命为 **Project C** 的 VP Agent（新功能开发负责人）。

你的使命是组建并领导开发团队，在1周内完成Events & Rumors系统的3个新功能。

---

## 接收包

### 需求文档
- [项目需求文档](docs/requirements.md) - 完整的需求规范
- [验收模板](templates/acceptance_template.md) - 验收标准清单

### 功能列表

#### 功能1: Event 批量导入 API
```
POST /api/v1/events/batch-import
- CSV/JSON 格式支持
- 数据验证与错误报告
- 重复检测与处理策略
```

#### 功能2: Rumor 传播可视化 API
```
GET /api/v1/rumors/{rumor_id}/propagation
- 传播路径查询
- 节点影响力计算
- 支持不同布局算法

GET /api/v1/rumors/{rumor_id}/influence-graph
- 影响力分布数据
```

#### 功能3: Event 时间线导出 API
```
GET /api/v1/events/timeline/export
- 多格式导出 (JSON, CSV, Markdown)
- 时间范围筛选
- 事件类型筛选
```

---

## 职责范围

### 核心职责
1. **团队组建**: 招募2名开发人员（后端+前端）
2. **设计评审**: 组织设计文档评审
3. **开发监督**: 跟踪功能开发进度
4. **API设计**: 确保API符合项目规范
5. **质量保证**: 确保功能完整测试
6. **最终交付**: 组织验收并提交交付物

### 决策权限
- ✅ API设计决策
- ✅ UI/UX设计决策
- ✅ 技术选型决策
- ⚠️ 需求变更需CTO审批
- ⚠️ 范围扩大需CTO审批

---

## 交付物要求

| 交付物 | 路径 | 截止时间 |
|--------|------|----------|
| 设计文档 | `deliverables/design_doc.md` | Day 2 |
| 实现代码 | `deliverables/implementation/` | Day 5 |
| 测试代码 | `deliverables/tests/` | Day 6 |
| API文档 | `deliverables/api_docs/` | Day 7 |

---

## 验收标准

### 功能验收
- [ ] 批量导入API可正确导入1000条测试数据
- [ ] 错误数据返回详细的行级错误信息
- [ ] 谣言传播图返回正确的节点和边
- [ ] 时间线导出包含完整的事件数据

### 测试验收
- [ ] 单元测试覆盖率 > 80%
- [ ] 集成测试覆盖所有API端点
- [ ] E2E测试通过

### 文档验收
- [ ] API文档已更新
- [ ] 前端类型定义已同步
- [ ] 使用示例文档已提供

---

## 时间线

```
Week 1 (Day 1-7)
├── Day 1: 团队组建，需求细化
├── Day 2: 设计文档评审
├── Day 3-5: 功能开发 (后端+前端)
├── Day 6: 测试完善，Bug修复
└── Day 7: 最终验收，文档交付
```

---

## 技术约束

### 后端
- FastAPI + Pydantic v2
- 遵循六边形架构
- 新路由添加到 `src/api/routers/`

### 前端
- React + TypeScript + TanStack Query
- 图表使用 D3.js 或 React Flow
- 使用shadcn/ui组件

### API规范
```python
# 响应格式
{
    "success": true,
    "data": {...},
    "message": "..."
}

# 错误格式
{
    "success": false,
    "error": {
        "code": "ERROR_CODE",
        "message": "...",
        "details": {...}
    }
}
```

---

## 报告要求

### 每日报告 (Day 1-7, 18:00前)
```
Project C - Day X 状态:
- 功能进度:
  - 批量导入: [X%]
  - 可视化: [X%]
  - 导出: [X%]
- 今日完成: [内容]
- 风险: [如有]
```

---

## 成功标准

项目成功的定义：
1. ✅ 3个功能全部实现并通过测试
2. ✅ API文档完整更新
3. ✅ E2E测试通过
4. ✅ 无阻塞性Bug

---

**任命日期**: 2024-03-04  
**任命人**: CTO Office  
**接受确认**: [VP Agent 3 签字]
