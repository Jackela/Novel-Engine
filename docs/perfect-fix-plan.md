# Novel Engine 深度治理基线

本文档取代早期的“零缺陷到完美架构”草案。早期草案中的 MyPy 错误数、覆盖率数字和缺失 Adapter 清单已经不再代表当前分支状态。

## 当前事实

- 后端静态质量门禁：Ruff、MyPy、import-linter 均为必跑门禁。
- 后端行为门禁：`uv run pytest -q`。
- 后端平台基础设施覆盖率门禁：auth、config、health、persistence 模块保持 80% 以上。
- 后端横切基础设施覆盖率门禁：circuit breaker、shared middleware、API middleware 模块保持 80% 以上。
- API 合同门禁：OpenAPI 快照检查和 public API audit 必须保持绿色。
- 前端门禁：TypeScript、Vitest platform coverage、production build、dependency audit、exports audit、Playwright smoke/full-audit。
- 外部服务测试：DashScope、Honcho、Chroma、PostgreSQL live 测试保持 opt-in 或独立 CI job，不进入默认本地门禁。

## 治理重点

1. 平台基础设施优先：健康检查、配置加载、JWT/auth、错误处理中间件、日志/correlation id、metrics、circuit breaker、persistence repository 和 unit-of-work。
2. 覆盖率防退化：后端平台基础设施和横切基础设施 coverage floor 均为 80%；前端 coverage floor 覆盖 app/auth/shared/components/lib 等平台壳层模块，故事工作台产品流由 focused unit tests 和 Playwright E2E 覆盖。
3. 合同稳定：业务 API 不为测试漂移做兼容 shim；OpenAPI snapshot 只随真实合同变化更新。
4. 文档同步：README、CI 和 Makefile 中的命令必须与实际门禁保持一致。

## 本阶段完成标准

- `make test` 与 CI backend-tests 使用同一组行为测试、平台 coverage 命令和 circuit/middleware coverage 命令。
- MyPy 配置没有过期 override 提示。
- Knip exports audit 没有冗余配置提示。
- 平台基础设施和横切 middleware/circuit breaker 新增失败路径和边界行为测试。
- README 描述的本地验证命令能直接复现 CI 的关键门禁。
