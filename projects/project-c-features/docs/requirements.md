# 项目需求文档

## 项目信息
- **项目编号**: NE-2024-003
- **项目名称**: Events & Rumors 系统扩展
- **预算**: 2个开发团队周
- **交付期限**: 1周
- **优先级**: P1

---

## 1. 项目背景

Novel-Engine的Events & Rumors系统是叙事引擎的核心组件，用户需要更强大的功能来：
- 批量管理事件数据
- 可视化谣言传播路径
- 导出时间线数据用于外部分析

本扩展将显著提升内容创作者的工作效率。

---

## 2. 功能需求

### 2.1 必须实现 (P0)

#### 2.1.1 Event 批量导入 API
- [ ] 支持 CSV/JSON 格式批量导入
- [ ] 数据验证与错误报告
- [ ] 重复检测与处理策略
- [ ] 导入进度反馈
- [ ] 事务性导入（全部成功或回滚）

**API端点**:
```
POST /api/v1/events/batch-import
Content-Type: multipart/form-data

参数:
- file: 导入文件
- format: csv | json
- duplicate_strategy: skip | update | error
```

#### 2.1.2 Rumor 传播可视化 API
- [ ] 谣言传播路径查询
- [ ] 节点影响力计算
- [ ] 时间维度传播数据
- [ ] 支持不同布局算法

**API端点**:
```
GET /api/v1/rumors/{rumor_id}/propagation
  - 返回: 节点列表 + 边列表 + 元数据

GET /api/v1/rumors/{rumor_id}/influence-graph
  - 返回: 影响力分布数据
```

#### 2.1.3 Event 时间线导出 API
- [ ] 支持多种导出格式 (JSON, CSV, Markdown)
- [ ] 时间范围筛选
- [ ] 事件类型筛选
- [ ] 关联实体包含选项

**API端点**:
```
GET /api/v1/events/timeline/export
  参数:
  - format: json | csv | markdown
  - start_date: ISO8601
  - end_date: ISO8601
  - event_types: 逗号分隔
  - include_related: bool
```

### 2.2 应该实现 (P1)
- [ ] 导入模板下载端点
- [ ] 导出任务异步处理（大文件）
- [ ] 可视化数据缓存

---

## 3. 非功能需求

### 3.1 性能要求
- 批量导入: 支持 10,000 条记录 < 30秒
- 可视化查询: < 500ms (节点数 < 1000)
- 导出API: 支持流式响应

### 3.2 安全要求
- 文件上传大小限制: 10MB
- 文件类型白名单验证
- 用户权限验证（基于现有RBAC）

### 3.3 质量要求
- API符合OpenAPI 3.0规范
- 输入严格验证（Pydantic v2）
- 错误信息清晰友好

---

## 4. 验收标准

### 4.1 功能验收
- [ ] 批量导入API可正确导入1000条测试数据
- [ ] 错误数据返回详细的行级错误信息
- [ ] 重复检测按策略正确处理
- [ ] 谣言传播图返回正确的节点和边
- [ ] 时间线导出包含完整的事件数据

### 4.2 测试验收
- [ ] 单元测试覆盖率 > 80%
- [ ] 集成测试覆盖所有API端点
- [ ] E2E测试通过（关键路径）

### 4.3 文档验收
- [ ] API文档已更新（OpenAPI spec）
- [ ] 前端类型定义已同步
- [ ] 使用示例文档已提供

---

## 5. 交付物清单

| 序号 | 交付物 | 路径 | 说明 |
|------|--------|------|------|
| 1 | 设计文档 | `deliverables/design_doc.md` | 架构设计与API设计 |
| 2 | 实现代码 | `deliverables/implementation/` | 后端+前端代码 |
| 3 | 测试代码 | `deliverables/tests/` | 单元+集成测试 |
| 4 | API文档 | `deliverables/api_docs/` | OpenAPI规范+示例 |

---

## 6. 技术约束

### 6.1 架构约束
- 遵循六边形架构（Hexagonal Architecture）
- 新API路由添加到 `src/api/routers/`
- 业务逻辑放在 `src/services/`
- 数据访问放在 `src/repositories/`

### 6.2 技术栈
- 后端: FastAPI + Pydantic v2
- 前端: React + TypeScript + TanStack Query
- 图表: D3.js 或 React Flow
- 导出: 标准库 csv/json

### 6.3 代码规范
- 遵循项目现有代码风格
- 所有新函数必须有docstring
- 使用依赖注入模式

---

## 7. 风险与应对

| 风险 | 可能性 | 影响 | 应对措施 |
|------|--------|------|----------|
| 大文件处理超时 | 中 | 高 | 实现异步任务队列 |
| 复杂图算法性能 | 中 | 中 | 实现分页和懒加载 |
| 第三方库兼容 | 低 | 中 | 提前进行技术选型验证 |

---

**文档版本**: v1.0  
**创建日期**: 2024-03-04  
**审批人**: CTO Office
