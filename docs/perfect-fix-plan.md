# Novel-Engine 完美修复计划

## 目标：从零缺陷到完美架构

**当前状态：**
- 架构成熟度：60%（已完成阶段1-3，但还有严重缺陷）
- 测试覆盖率：8.58%
- MyPy 错误：455个
- 缺失 Adapter：10+
- 缺失 DI 容器：是

**目标状态：**
- 架构成熟度：100%
- 测试覆盖率：>80%
- MyPy 错误：0
- 所有 Port 都有 Adapter
- 专业 DI 容器

---

## 阶段4：核心基础设施完善（Day 11-14）

### P0 - 阻塞性问题（必须修复）

#### Task 4.1: 实现所有缺失的 Repository Adapters
- **knowledge**: PostgresKnowledgeRepository, PostgresDocumentRepository
- **narrative**: PostgresStoryRepository, PostgresChapterRepository, PostgresSceneRepository
- **identity**: 已完成（阶段2）
- **world**: 已拆分（阶段3）

#### Task 4.2: 实现专业 DI 容器
- 引入 `dependency-injector` 库
- 实现生命周期管理（Singleton/Transient/Scoped）
- 实现自动依赖解析
- 实现循环依赖检测
- 替换现有的手动依赖创建

#### Task 4.3: 修复 Application 层对 Infrastructure 的直接依赖
- 创建 Domain 层的 Port 接口
- 移动基础设施依赖到 Adapter

### P1 - 高优先级（建议修复）

#### Task 4.4: 统一错误处理
- 创建统一的错误码体系
- 实现错误码到 HTTP 状态的自动映射
- 添加国际化支持（i18n）

#### Task 4.5: 完善 Domain 层
- 实现完整的 Domain Event 流程
- 添加 Aggregate 业务不变量验证
- 实现 Value Object 的不可变性

---

## 阶段5：类型安全完善（Day 15-17）

### Task 5.1: 修复 MyPy 错误
- 修复 455 个 mypy 错误
- 移除所有未使用的 `type: ignore`
- 修复 `callable` 类型
- 修复异步上下文管理器

### Task 5.2: 类型现代化
- 迁移 `Optional[X]` → `X | None`
- 迁移 `Dict/List` → `dict/list`
- 减少 `Any` 使用

### Task 5.3: 类型检查集成
- 在 CI 中强制 mypy 检查
- 配置严格的 mypy 规则

---

## 阶段6：测试完善（Day 18-22）

### Task 6.1: 提升单元测试覆盖率到 80%
- 为所有缺失的模块添加测试
- 为所有 Value Object 添加测试
- 为所有 Service 添加测试

### Task 6.2: 创建集成测试套件
- 数据库集成测试（使用 Testcontainers）
- 外部服务集成测试（Honcho、Kafka）
- 组件间集成测试

### Task 6.3: 创建 E2E 测试套件
- 用户注册/登录流程
- 世界创建流程
- 故事生成流程

### Task 6.4: 创建架构测试
- 使用 import-linter 验证分层
- 创建契约测试验证 Port/Adapter 兼容性

---

## 阶段7：横切关注点完善（Day 23-25）

### Task 7.1: 完善日志系统
- 统一使用 structlog
- 实现分布式链路追踪（Correlation ID）
- 实现日志分级和过滤

### Task 7.2: 完善监控指标
- 实现业务指标（Prometheus）
- 实现性能指标
- 实现健康检查指标

### Task 7.3: 完善配置管理
- 实现配置热重载
- 实现配置验证
- 实现配置加密（敏感信息）

---

## 执行策略

### Subagent 分配

**Group A - Port/Adapter 实现（4个 subagents）**
- SA1: knowledge Repository Adapters
- SA2: narrative Repository Adapters  
- SA3: world Repository Adapters 补充
- SA4: 验证所有 Adapter 实现

**Group B - DI 容器（2个 subagents）**
- SA5: 实现 DI Container 核心
- SA6: 迁移所有依赖到 DI Container

**Group C - 类型安全（3个 subagents）**
- SA7: 修复 mypy 错误（基础设施层）
- SA8: 修复 mypy 错误（领域层）
- SA9: 修复 mypy 错误（应用层）

**Group D - 测试（4个 subagents）**
- SA10: 单元测试（Domain 层）
- SA11: 单元测试（Application 层）
- SA12: 集成测试（基础设施）
- SA13: E2E 测试

**Group E - 横切关注点（2个 subagents）**
- SA14: 日志和链路追踪
- SA15: 监控和配置

---

## 完美标准

### 架构标准
- [ ] 所有 Port 都有对应的 Adapter
- [ ] 专业 DI 容器管理所有依赖
- [ ] 分层架构严格遵守（无反向依赖）
- [ ] 完整的 Domain Event 实现
- [ ] 所有 Value Object 不可变

### 类型安全标准
- [ ] MyPy 错误数为 0
- [ ] `type: ignore` 数量为 0
- [ ] 无 `Any` 类型滥用
- [ ] 所有函数都有类型注解

### 测试标准
- [ ] 单元测试覆盖率 >80%
- [ ] 集成测试覆盖所有 Repository
- [ ] E2E 测试覆盖核心流程
- [ ] 架构测试防止分层违规
- [ ] 并发测试覆盖关键路径

### 代码质量标准
- [ ] Ruff 检查无错误
- [ ] MyPy 检查无错误
- [ ] 所有文件 < 500 行
- [ ] 函数复杂度 < 10
- [ ] 无重复代码

### 文档标准
- [ ] 所有公共 API 有 docstring
- [ ] 架构决策记录（ADR）
- [ ] 完整的 README
- [ ] API 文档自动生成

---

## 最终验证清单

### 运行所有检查
```bash
# 1. 类型检查
mypy src --strict

# 2. 代码风格
ruff check src
ruff format --check src

# 3. 测试覆盖率
pytest --cov=src --cov-report=term-missing --cov-fail-under=80

# 4. 架构检查
import-linter

# 5. 安全检查
bandit -r src

# 6. 性能检查
# 所有测试在 5 分钟内完成
```

### 手动验证
- [ ] 系统可以正常启动
- [ ] 所有 API 端点可访问
- [ ] 数据库迁移可执行
- [ ] 健康检查返回 200
- [ ] JWT 认证正常工作

---

**开始执行完美修复！**