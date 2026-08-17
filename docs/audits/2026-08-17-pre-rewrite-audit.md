# Novel Engine 重写前全面审计（Pre-Rewrite Audit）

- 日期：2026-08-17
- 性质：只读审计。本报告是 ADR-0001（TS 绿地重写）前置 blocking 步骤的输入，
  供下一场 wayfinder 开图使用；本会话不重构、不改产品代码。
- 关联：ADR `docs/adr/0001-typescript-greenfield-rewrite.md`、issue #233、
  产品规范 SSOT `openspec/specs/novel-studio/spec.md`（实为 **18 条** Requirement，
  此前口径 17 条，以本报告为准）。
- 方法：门禁基线实测留证 → 六维只读审查（分层契约 / 规范-实现漂移 / 测试缺口 /
  尺寸复杂度 / 死代码 / 前端与依赖，并行子代理）→ 隐性需求盘点 → 高价值疑点人工复核。
  mimosa 深度安全扫描 2026-08-17 已完成且 clean（`EntryPage.tsx:94` 的 HIGH 为
  `autoComplete='current-password'` 误报，不再列入）。
- 基线 commit：`14c141d5`（main，worktree clean）。

## 0. 执行摘要

**门禁全绿，代码库健康度高；但"spec 作为重写验收契约"目前是空洞的——这是最大的重写风险。**

1. **无 P0**：未发现新的安全漏洞（mimosa clean、bandit 0、脱敏/消毒/认证逻辑均有实现有测试）。
2. **一个 P1 功能缺陷**：API `operation` 枚举与 deterministic (mock) provider 的 step
   词汇表错配——默认 provider（project settings 默认 `mock`）下所有 AI 提案内容是
   provider 的 echo JSON，而非有效的小说续写文本。e2e 只断言流程不断言内容，全部门禁
   因此未拦截（详见 F-1）。
3. **隐性需求约 62 条**只存在于代码、不在 spec 的 18 条 Requirement 里，其中约 2/3
   无测试锁定。绿地重写若只按 spec 验收，将静默丢失 FTS5 搜索、CSRF 机制形状、错误
   响应契约、review 规则、导出布局、并发模型等完整子系统（详见第 4 节）。
4. **测试金标准缺口集中在持久层**：repository 10 个模块（约 1562 行）零直接测试；
   `reorder` / `update_project` / `restore` 三条链路全仓零测试引用。重写对齐无从比对。
5. **依赖债已冻结**：dependabot 已禁用（PR #238），此前 10+ 个大组升级 PR 全部因
   lockfile/specifier 失配在 install 阶段失败——升级从未被真正验证过。
6. 死代码量小而干净：2 个 Python 模块、4 条死路由、6 个依赖可直接不迁移；
   `novel_studio_*` cookie 名是活跃前后端契约，改名需迁移。

## 1. 门禁基线（全绿，2026-08-17 实测）

| Gate | 结果 |
|---|---|
| `uv run python -m pytest -q --ignore=tests/e2e --ignore=tests/performance` | **272 passed, 1 skipped**（skip 为 DashScope contract 测试，需 `ENABLE_DASHSCOPE_TESTS=1`；`tests/performance` 目录实际不存在，ignore 无害） |
| `uv run mypy src tests` | Success：176 文件零问题 |
| `uv run ruff format --check src tests scripts` | 184 文件已格式化 |
| `uv run ruff check src tests scripts` | 全过 |
| `uv run bandit -r src` | 0 issue（全严重度/置信度） |
| `uv run lint-imports` | **6 contracts kept, 0 broken**（166 文件 502 依赖边） |
| `scripts/qa/check_file_sizes.py` | clean：246 文件，limit 300，legacy baselines 0 |
| `scripts/qa/check_openapi_snapshot.py` | 快照最新（`docs/api/openapi.current.json`） |
| `scripts/qa/check_repo_hygiene.py` | clean |
| `scripts/qa/check_ssot.py` | Novel Engine 0.3.1 aligned |
| `pnpm spec:validate` | 1 passed, 0 failed |
| `pnpm --dir frontend lint` | clean（`--max-warnings=0`） |
| `pnpm --dir frontend type-check` | clean |
| `pnpm --dir frontend test:unit` | 16 文件 57 用例全过 |
| `pnpm --dir frontend build` | 成功 |

结论：当前基线可作为重写对照的起点快照。

## 2. Findings 分级

分级口径：P0 = 安全漏洞/数据丢失；P1 = 功能缺陷、重写必然丢失的行为、契约金标准缺失、
架构决策悬空；P2 = 观察项、技术债、低风险漂移。

### P0

无。（mimosa 深扫 clean；本次六维审查未发现新的安全问题。）

### P1

| # | Finding | 证据 | 影响 |
|---|---|---|---|
| F-1 | **operation 枚举错配（功能缺陷）**：API 允许 `operation ∈ {continue, rewrite, generate}`，直接透传为 `TextGenerationTask.step`；deterministic provider 只识别 `chapter_draft/chapter_revision/editorial_review`，未识别的 step 返回 `{"result":"ok","step":...,"echo":...}`；`ai_service` 取不到 `chapter_markdown` 后回退 `raw_text`，即把 echo JSON 字符串当提案落盘 | `src/contexts/studio/interface/http/schemas.py:55`；`src/contexts/studio/application/services/ai_service.py`（`step=operation` 透传与 `content.get("chapter_markdown") or result.raw_text` 回退）；`src/contexts/ai/infrastructure/providers/deterministic_text_generation_provider.py:39-47` | 项目 settings 默认 `{"provider":"mock"}`，默认配置下 AI 提案功能实质产出垃圾内容。e2e（`frontend/tests/e2e/studio.spec.ts:61`）只断言接受流程成功、不断言提案内容，故门禁全绿未拦截。重写时必须先决定 mock provider 的语义 |
| F-2 | **隐性需求未入 spec（约 62 条，见第 4 节）**：FTS5 搜索是完整子系统但 spec 零覆盖；CSRF 双提交机制、cookie 形状、错误响应双形状、review 规则、导出布局与生命周期、jobs 并发模型、限流、CORS、配置守卫等全部只存在于代码 | 见第 4 节逐条 file:line | spec 是重写验收契约（ADR-0001），按 18 条 Requirement 验收 = 大量功能静默丢失。wayfinder 开图第一优先级：把高价值隐性需求升格进 spec |
| F-3 | **repository 持久层零直接测试**：10 个模块约 1562 行（common/document/project/job/snapshot/review/auth/export/document_revisions/document_search）仅经 facade/API 集成路过；IntegrityError/rollback 等错误路径无断言；唯一并发测试是 `tests/apps/api/test_csrf.py:103` | `src/contexts/studio/infrastructure/repository/` vs `tests/`（逐模块引用核对） | 重写时持久层无金标准可比对；SQL 语义（RESTRICT、FTS5、scope 过滤）只能靠人读代码 |
| F-4 | **三条链路全仓零测试引用**：`reorder_documents`（service+repo+HTTP 端点）、`update_project`（service+repo+PATCH 端点）、`restore_revision`（service+HTTP 端点） | `document_service.py:127`、`repository/document.py:229`、`project_router.py:110`；`project_service.py:65`、`repository/project.py:161`、`project_router.py:55`；`revision_service.py:44`、`project_router.py:193` | 这三个行为只由 OpenAPI 快照间接锁形状、无行为锁定；重写对齐无从验证（前端仅有 `useStudioActions.test.tsx:191` 与 mock 测过 reorder 语义） |
| F-5 | **导出产物无生命周期管理**：无任何保留/清理策略；项目删除只删 DB 记录、导出文件残留磁盘 | `export_service.py:101-112,191-211`；`repository/project.py:189-217`（无文件删除） | 磁盘泄漏随使用增长；重写要么复刻此语义（显式接受）要么设计清理——目前是"未决策"状态 |
| F-6 | **studio→ai 上下文耦合无契约保护**：studio 的 AI port 直接以 ai 的类型为签名（`ports/ai_provider.py:7-24`），`service_common.py:23-26` 扇出再导出，infra 层再适配（`infrastructure/ai_provider.py:5-11`）；import-linter 无 context 独立性契约。ai 实为"ports + provider adapters"模块（`ai/domain/**` 全空） | 同左 | 重写必须先决策：ai 是共享内核还是独立 context、TS 中 factory 接口归属；既成事实无契约固化，容易在重写中变形 |
| F-7 | **AI provider 注入双轨**：API 走 `runtime.py:43-47` 内联闭包（注入 settings）；CLI 走 `create_studio_text_generation_provider`（内部调全局 `get_settings()`）——同一 port 两条构造路径、settings 获取语义不同 | `src/apps/api/runtime.py:43-47`；`src/contexts/studio/infrastructure/ai_provider.py:12,20`；`src/apps/cli/novel_engine.py:47` | TS 组合根设计需统一此路径；两条轨道的配置漂移风险已被双测试面掩盖 |
| F-8 | **.importlinter interface 契约缺口**：契约 5 只禁 `src.contexts.*.infrastructure`，漏 `src.shared.infrastructure`——AGENTS.md 措辞与 linter 覆盖不一致 | `.importlinter:37-44` | 未来 router 可"合法"import shared infra；AGENTS 声明与可执行政策漂移 |
| F-9 | **前端类型三处人工同步、无 codegen**：`types/studio.ts` 手写类型 + `apiContract.ts`/`apiWorkflowContract.ts` 手写 runtime parser + 后端 OpenAPI 快照，三者间无自动对比；幸而零 `as any`/`@ts-ignore` | `frontend/src/app/types/studio.ts`、`frontend/src/app/apiContract.ts`、`scripts/qa/check_openapi_snapshot.py` | ADR 已选 TS 全栈；codegen（或 schema-first）是重写最大工程化收益点，现状是纯手工三处同步 |
| F-10 | **依赖升级债冻结**：dependabot 已禁用（#238）；此前 frontend-maintenance 大组 PR（#214–#236，2026-06-28 起 ≥10 个）全部因 `pnpm install --frozen-lockfile` 下 manifest/lockfile specifier 失配失败——升级从未被真正验证；TypeScript 6.0.3 vs 最新 7.0.2（落后一个大版本）、jsdom 29 被 `undici <8` override 锁死、vite/codemirror/lucide 各落后数个 minor | `pnpm-workspace.yaml`（`undici: >=7.29.0 <8`）；CI `.github/workflows/ci.yml:52`；已核实 npm 最新版本 2026-08-17 | 对重写的影响：不是"要追版本"，而是 TS 工具链选型（7.x）与锁死约束（undici/jsdom）要作为栈决策输入 |

### P2

| # | Finding | 证据 |
|---|---|---|
| P2-1 | .importlinter 其余缺口：`src.shared→src.apps` 未声明、infrastructure→interface 未声明（当前均未发生） | `.importlinter` |
| P2-2 | health 端点越层直调 `store.repository.health_check()`，绕过 application service | `src/apps/api/health.py:51-53` |
| P2-3 | 同一 store 挂双 `app.state` 通道（`studio_runtime.store` / `studio_store`） | `runtime.py:62`、`dependencies.py:15` |
| P2-4 | `StudioStore` 三 mixin 菱形继承同一 `StudioServiceRegistry`，`__init__` 非 cooperative（无 `super().__init__()`），mixin 不可独立扩展 | `facade.py:29`、`facade_base.py:25-39` |
| P2-5 | 空壳脚手架：`src/contexts/shared/**`、`src/contexts/ai/domain/**` 全 0 字节；`contexts/ai/__init__.py:3` 包级导出 application 层 | 同左 |
| P2-6 | `novel_engine.py:80` uvicorn 字符串工厂引用绕过静态 import 图（`src.apps.api.main:create_application`） | 同左 |
| P2-7 | 存量红线违例：12 个 Python 函数 >50 行（最长 `_build_chapter_payload` 107 行，`deterministic_text_generation_provider.py:49`；`create_review` 82、`export_project` 81）；4 个非测试前端文件 >200 行（`useDocumentDraft.ts` 303、`apiContract.ts` 253、`api.ts` 248、`useStudioPageModel.ts` 222）；组件目录无一超 200（最大 `StudioNavigator.tsx` 176），`StudioPage.tsx` 仅 21 行 | 第 3.4 节 |
| P2-8 | 四组 HTTP 端点无 HTTP 级测试：`GET /projects/{id}/jobs`、`POST .../jobs/{id}/retry`、`POST /ai-proposals/{job_id}/accept`（拒绝路径仅 service 级）、`POST /api/imports`（仅 preview 有） | `workflow_router.py:81-99,91,70,179` |
| P2-9 | 五个应用层服务无直接单测：`auth_service.py`（HMAC/会话仅集成路过）、`import_service.py`、`export_service.py`、`ai_job_persistence.py`、`service_payloads.py` | `src/contexts/studio/application/services/` |
| P2-10 | `src/shared/infrastructure/logging/config.py`（159 行）全测试树零引用 | 同左 |
| P2-11 | Web 导入 symlink 拒绝已实现但零专项测试；CLI import 路径（`import_service.py`）无 symlink 检查（spec 允许 CLI 显式路径，但语义边界值得显式化） | `workflow_router.py:40`；`import_service.py:36` |
| P2-12 | 死代码（高置信，可直接不迁移）：`src/shared/domain/types.py` + `exceptions.py`（525 行，仅自身测试引用；studio 有独立在用的体系）；4 条前端与测试均不调用的路由（`GET/POST /projects/{id}/snapshots`、`POST /api/imports`、`GET /documents/{id}` 单文档）；依赖 `jinja2`、`python-multipart`、`aiosqlite`、`click`(dev)、**`httpx2`（`pyproject.toml:71`，笔误依赖，httpx 已声明两次）**、docs extras（mkdocs 三件套无配置）；6 个空包 | 第 3.5 节 |
| P2-13 | `novel_studio_session` / `novel_studio_csrf` cookie 名是活跃前后端契约（后端 `service_common.py:66-67`、前端 `api.ts:42` 正则匹配）；TS 重写改名 = 全部会话失效，需兼容迁移或保留 | 同左 |
| P2-14 | hooks 编排约定灰区：studio 主链路严格经 hooks（components 零 api 调用），但 `EntryPage.tsx`（5 处）与 `ProjectLibraryPage.tsx`（4 处）页面级组件直接调 `api.*` | `EntryPage.tsx:18,24,46,48,61`、`ProjectLibraryPage.tsx:18,34,43` |
| P2-15 | 前端无测试源文件热点：`useDocumentDraftAutosave.ts`(162)、`useStudioPageModel.ts`(222)、`MarkdownEditor.tsx`(110)、`StudioInspectorPanels.tsx`(175)、`EntryPage.tsx`、`ProjectLibraryPage.tsx` 等 | 第 3.3 节 |
| P2-16 | spec 两条 implemented-untested：SPA deep-link 托管（`main.py:156-183`）与响应式 821–949px/44px 规则（`index.css:1017-1111`）均无自动化测试；docx/epub 导出内容无逐字断言（仅 markdown 断言） | 同左 |
| P2-17 | `tests/unit/INFRASTRUCTURE_TESTS_REPORT.md` 引用的 character/world 测试文件已不存在（陈旧报告）；每小时 guest 清理调度循环无测试 | 同左 |
| P2-18 | mock provider 词汇表陈旧：deterministic provider 的 chapter_draft 等语义来自旧设计，metadata（chapter_number/genre 等）当前调用方从不传（F-1 的根因面） | `deterministic_text_generation_provider.py:49-107` |

**已核伪的疑点（不要在重写规划中重复上报）**：
- "Studio 不报版本"为误报——`EntryPage.tsx:115`、`StudioStatusbar.tsx:37` 渲染
  `__APP_VERSION__`（`vite.config.ts:13` define），Requirement 1 满足。
- "execution lease 机制"不存在——无 lease 字段/时长/并发限制，实现就是启动时把
  `running` 全部标记 `interrupted`（`database.py:129-150`）。不要在重写中虚构 lease。
- "draft localStorage 持久化"不存在——草稿仅在 React 内存，切换文档即丢
  （`useDocumentDraft.ts:41-43`）。

## 3. 六维详查

### 3.1 分层契约

- AGENTS.md 六条契约 grep 全量 import 图**全部实测通过**；lint-imports 6 kept。
  动态导入为零；唯一运行时加载是 CLI 的 uvicorn 字符串工厂（P2-6）。
- `.importlinter` 无任何 ignore/exclude（零豁免，优点）。漂移点是结构性缺口：
  契约 5 漏 `src.shared.infrastructure`（F-8）；无 context 独立性契约（F-6）。
- studio→ai 单向耦合三层：port 签名（`ports/ai_provider.py:7-24`）→
  `service_common.py:23-26` 再导出扇出 → `infrastructure/ai_provider.py:5-11` 适配；
  ai 对 studio 零 import。组合根在 `src/apps`（唯一 root，无循环）。
- `StudioServiceRegistry`（`facade_base.py:24-65`）构造 11 个 service 的依赖图；
  `job_service` 聚合 ai+review+export，`import_service` 聚合 project+document。

### 3.2 规范-实现漂移（18 条 Requirement 逐条）

结论：**硬漂移 0 条；implemented-untested 2 条（SPA deep-link、响应式 CSS，P2-16）；
其余 16 条 implemented+tested。** 验收契约骨架是真实可信的。

抽样证据（实现 → 测试）：
- 冲突保存 409/不可变 revision：`repository/document.py:186-222` →
  `test_services.py:65-93`、`test_studio.py:39-51`
- proposal accept 校验（非 completed/空 Markdown 拒绝）：`ai_service.py:211-258` →
  `test_ai_service.py:130-159`
- 三格式同快照导出：`export_service.py:60-98` → `test_services.py:128-169`
- job 恢复+retry 限 failed/interrupted：`database.py:129-150`、`job_service.py:52-107` →
  `test_services.py:188-217`、`test_job_service.py:157`
- guest 24h + 启动/每小时清理：`service_common.py:65`、`runtime.py:74-77,115` →
  `test_services.py:172-185`
- HMAC + registry 注入 + 轮换：`domain/utils.py:46-58`、`facade_base.py:31-43` →
  `test_services.py:96-125`、`test_csrf.py:46-75`
- FTS5 严格 token 归约（casefold、`\w+`、去重、≤8 token、引号 AND、拦截操作符）：
  `service_common.py:101-116` → `test_document_service.py:99`、`test_studio.py:138`
- 日志脱敏白名单：`error_handler.py:99-112,154-195` → `test_error_handler.py:124-175`
- untrusted JSON 边界（`\u005b` 转义防伪造定界符）：`service_common.py:196-214`、
  `ai_service.py:81-98` → `test_ai_sanitization.py:128-193`
- 删除保护 RESTRICT→409：`models.py:210-212`、`errors.py:36-40` →
  `test_studio.py:177-219`

弱覆盖注记：accept 拒绝路径无 HTTP 级测试（P2-8）；docx/epub 无内容级断言（P2-16）；
版本 Requirement 实际满足（见"已核伪"）。

### 3.3 测试缺口

- 规模：src/ 119 个 .py（11296 行），非平凡约 83 个；tests/ 33 文件 254 用例
  （后端）+ 前端 vitest 16 文件 57 用例 + Playwright 1 文件 2 用例。
- 后端 e2e：`tests/e2e/test_studio_workflow.py`（1 用例 guest 全流程）；
  前端 e2e：`frontend/tests/e2e/studio.spec.ts`（2 用例：guest 写作→提案→历史→
  导出 + 保存冲突恢复；多视口布局断言）。CI 只跑该 smoke 文件。
- 核心缺口：repository 全层（F-3）、三条零引用链路（F-4）、四组 HTTP 端点（P2-8）、
  五个 service（P2-9）、logging config（P2-10）。
- 覆盖相对好的面：ai providers 错误归一化（DashScope 5 + OpenAI 7 + factory 14 用例）、
  CSRF/cookie（13 用例）、shared middleware/rate_limit/token_bucket、settings。
- 前端：hooks 12/15 有测试；组件 4/17；无测试热点见 P2-15。

### 3.4 尺寸复杂度

- file-size gate 干净（246 文件 0 超限，0 豁免）。注意口径：gate 数"非空非注释行"，
  `useDocumentDraft.ts` 总行 303 但 code 280 未超限。
- 贴线文件（code ≥240）：`scripts/ai/regression_check.py` 299、`useDocumentDraft.ts`
  280、`service_common.py` 251、`job_service.py` 247、`ai_service.py` 245、
  `settings.py` 240、`shared/domain/exceptions.py` 240（后者是死代码，见 P2-12）。
- 巨型文件清单（总行）：`settings.py` 299、`session_router.py` 272、
  `error_handler.py` 257、repository `common/document/project` 各 250+；
  facade 系列全部 <135；`StudioPage.tsx` 21（编排已成功下沉 hooks）。

### 3.5 死代码与遗留

高置信净清单（重写可直接不迁移）：`src/shared/domain/` 两模块（525 行）、6 个空包、
4 条死路由、依赖 jinja2 / python-multipart / aiosqlite / click(dev) / httpx2 /
docs extras。低置信（契约测试持有，迁移前确认）：`POST /api/imports/preview`
（前端不调但 tests+OpenAPI 在）、`GET /version`、`GET /health`（`/health/live`
被 e2e 栈用、`/health/ready` 被 compose healthcheck 用——这两个必须保留）。
旧名残留：alembic 迁移 ID（持久契约，不可改）、`openapi.current.json` 的
"Novel Studio Session" 标题（重新生成即消）；TODO/FIXME/deprecated 全仓 0。

### 3.6 前端与依赖

- `api.ts` 唯一 HTTP 出口 **100% 守住**（全前端仅 2 处 `fetch(`，均在 `api.ts`）；
  CSRF 注入/credentials/abort+超时/错误归一化语义完整（`api.ts:38-103,124-126`）。
- 契约层 `apiContract.ts`/`apiWorkflowContract.ts` 是手写 runtime parser（抛
  `ApiContractError`），只被 `api.ts` 消费——合法层，但属 F-9 的人工同步面。
- hooks 编排：`useStudioPageModel.ts` 是唯一编排根（组合 10 个领域 hook 产出
  viewProps）；components 零 api 调用；灰区仅 P2-14 两页面。
- 依赖：见 F-10。当前 pin 组（`pnpm-workspace.yaml`：undici/brace-expansion/
  fast-uri/nanoid/postcss）与 dependabot manifest-only 更新相冲突是失败根因。
- 测试栈无 `@testing-library/react`，用 `@testing-library/dom` 手写 render——
  重写时测试栈选型不受既有约束。

## 4. ★ 隐性需求盘点（spec 外行为，重写会悄悄丢的东西）

口径：行为存在于代码、未被 spec 18 条 Requirement 覆盖。约 62 条；"测试锁定"指有
直接断言该行为的测试。**建议进 spec 的高价值条目加粗**。wayfinder 开图时应把这批
分批升格进 openspec，或显式决策"接受丢失"。

### 4.1 安全与认证（12 条）

| # | 行为 | 证据 | 测试 | 建议 |
|---|---|---|---|---|
| A1 | 登录恒定时序 dummy bcrypt（用户名不存在也跑一次） | `auth_service.py:69-77`、`service_common.py:69-72` | 无 | **进 spec** |
| A2 | Owner 密码策略：username strip 非空、密码 10–72 UTF-8 字节；重复 setup 422 | `auth_service.py:46-54` | 弱 | **进 spec** |
| A3 | 并发 setup 用 `BEGIN IMMEDIATE` 只建一个 owner | `repository/auth.py:58-61` | `test_csrf.py:103` | 重写注意 |
| A4 | **CSRF 双提交**：`novel_studio_csrf` cookie（非 HttpOnly）+ `X-CSRF-Token` compare_digest；写方法全量校验；豁免 setup/login/guest | `session_router.py:58-63,135-151`、`api.ts:69-78` | `test_csrf.py` 6 用例 | **进 spec（形状契约）** |
| A5 | **Cookie 形状**：session=HttpOnly/SameSite=Lax/path=/，Secure 仅 prod/staging；owner 30 天、guest 24h | `session_router.py:22-55,207-230` | `test_csrf.py:26,121` | **进 spec** |
| A6 | Setup 同源校验（Origin/Referer、localhost 5173/4173/8000 白名单、拒 "null"/userinfo） | `session_router.py:63-121` | `test_csrf.py:77,92` | **进 spec** |
| A7 | 会话惰性过期（验证时过期即删+401）；`last_seen_at` 刷新 | `auth_service.py:113-127` | 无 | **进 spec** |
| A8 | 登出 = 删会话行 + 双 cookie 删除，204 | `session_router.py:239-254` | 有 | 进 spec |
| A9 | **认证端点限流**：setup/login/guest 按 IP（代理信任链 X-Forwarded-For+CIDR）令牌桶 5/min，429+Retry-After | `rate_limit_middleware.py:27-61,93-109` | 8 用例 | **进 spec** |
| A10 | **生产配置守卫**：prod 必须非默认 secret、强制 sqlite、CORS 禁 `*` | `settings.py:177-200` | 有 | **进 spec** |
| A11 | CORS 细节：默认 3 localhost origin、通配展开、credentials=true、允许 X-CSRF-Token | `cors.py:22-53` | 4 用例 | **进 spec** |
| A12 | **错误响应双形状**：`{"detail":...}` vs `{"error":{code,message,details}}`；409 嵌 `{message,current_revision_id}` | `error_handler.py:148-180,225-234`、`errors.py:24-44` | 有 | **进 spec（API 语义冻结）** |

### 4.2 API 面（15 条）

| # | 行为 | 证据 | 测试 | 建议 |
|---|---|---|---|---|
| B1 | **FTS5 全文搜索**：虚表+保存/删除同步刷新；严格 token 归约；snippet 16 词、rank 排序、LIMIT 30；excerpt 无 `<mark>` | `project_router.py:213-221`、`service_common.py:101-116`、`document_search.py:31-73`、`database.py:120-126` | 有 | **进 spec（最高优先级遗漏）** |
| B2 | 项目删除：手动绕过 RESTRICT 先删 FTS/snapshot_documents/snapshots 再删 project，级联 jobs/reviews/exports | `project_router.py:72-85`、`repository/project.py:189-217` | `test_studio.py:113,149` | **进 spec** |
| B3 | 文档重排序：`document_ids` 必须恰等于全文档集合（否则 422），position 重编号 | `project_router.py:110-124`、`repository/document.py:246-252` | 后端无 | **进 spec** |
| B4 | 修订恢复：以 `base_revision_id` 存新修订，`source="restore"`+`metadata.restored_from` | `project_router.py:192-210`、`revision_service.py:44-70` | 后端无 | **进 spec** |
| B5 | 手动快照端点（reason 1–48 字符，默认 "manual"） | `project_router.py:224-249` | 无 | 决策（前端不用，可弃） |
| B6 | 会话/provider 端点全集：setup(4)/session(4)/providers(1) | `session_router.py:170-272` | 部分 | **进 spec** |
| B7 | Job 列表（含 events 倒序）；无单 job 详情端点；retry 限 failed/interrupted | `workflow_router.py:81-99`、`job_service.py:65-66` | service 级 | **进 spec** |
| B8 | 导出下载：FileResponse + 相对路径根逃逸防护 | `workflow_router.py:153-162`、`export_service.py:138-155` | e2e | **进 spec** |
| B9 | 健康端点：`/health`(DB component)、`/health/live`、`/health/ready`(503)、`/version`(python_version/environment/BUILD_SHA) | `health.py:64-106` | 3 用例 | **进 spec（infra 契约）** |
| B10 | SPA 服务细节：`/assets` 挂载；catch-all 对 api/health/metrics/docs/openapi 前缀回 JSON；未构建时提示 JSON | `main.py:156-183` | 无 | 重写注意 |
| B11 | OpenAPI 定制：cookieAuth scheme、公开端点 security:[]、Swagger UI CDN 锁 5.32.6+SRI；快照 CI 冻结 | `main.py:40-99`、`swagger_ui.py:14-25` | 有 | 重写注意（契约来源） |
| B12 | 请求 schema 约束：title 1–240、instruction ≤10000、import source 1–240 等 | `schemas.py:10-73` | 快照间接 | 已随 OpenAPI 冻结 |
| B13 | Web 导入源限制：拒 `.`/`..`/斜杠/反斜杠，迭代比对目录名、拒 symlink、resolve 须在 `data/imports` 内；仅 owner 可用 | `workflow_router.py:23-28,31-45` | 部分（symlink 无） | spec 覆盖大方向 |
| B14 | Legacy workspace 契约：必须 `story.yaml`；`manuscript/chapters/chapter-*.md` 排序；source hash=路径+内容 sha256；章节命名 `Chapter N` | `import_service.py:36-56,84-96,110-119` | 有 | **进 spec** |
| B15 | 导入幂等按 owner/guest scope（同 workspace 不同 guest 各建一份） | `import_service.py:64-69` | 间接 | 重写注意 |

### 4.3 数据模型（10 条）

| # | 行为 | 证据 | 测试 | 建议 |
|---|---|---|---|---|
| C1 | 唯一约束：`(project_id,kind,title)`、`(document_id,revision_number)`、`sessions.token_hash`、`projects.import_hash` | `models.py:110-111,141-147,63,92-94` | 迁移间接 | **进 spec** |
| C2 | sessions 列：kind/token_hash/csrf_token/expires_at/last_seen_at | `models.py:54-74` | 无 | **进 spec** |
| C3 | jobs 列 `retry_of_job_id`(SET NULL)、request/result/error JSON；`usage_events` 表（tokens/request_evidence/estimated_cost） | `workflow_models.py:20-58,150-173` | 无 | **进 spec** |
| C4 | exports 列：relative_path/size_bytes/checksum_sha256 | `workflow_models.py:128-147` | 无 | 进 spec |
| C5 | review_issues 按 (severity,code) 排序；reviews 固定 summary 文案 | `workflow_models.py:99-103` | 无 | 接受丢失可 |
| C6 | SQLite PRAGMA：foreign_keys=ON / WAL / synchronous=NORMAL（每连接） | `database.py:102-108` | 有 | **进 spec** |
| C7 | 启动/CLI 前在线备份（sqlite3 backup API → `data/backups/`）+ `alembic upgrade head` | `database.py:60-70`、`novel_engine.py:64-70` | 有 | **进 spec** |
| C8 | "lease" 真相：启动时 running→interrupted + JobEvent，无字段级 lease | `database.py:129-150` | 有 | **进 spec（防虚构）** |
| C9 | 迁移策略：0001=create_all 非增量；0002/0003 数据回填 | `alembic/versions/` | — | 重写注意（既有 DB 兼容） |
| C10 | FTS 表不在 SQLAlchemy 元数据（手写 SQL），删除需手动清 FTS 行 | `repository/document.py:165-168`、`project.py:199-202` | 有 | 重写注意 |

### 4.4 业务规则（14 条）

| # | 行为 | 证据 | 测试 | 建议 |
|---|---|---|---|---|
| D1 | 新项目自动播种 "Chapter 1" 文档；settings 默认 `{"provider":"mock"}` | `repository/project.py:94-121` | e2e 隐式 | **进 spec** |
| D2 | **Review 规则**：chapter <250 词→warning `thin_chapter`；空内容→blocker `empty_chapter`；非 chapter 跳过；每次 review 建 snapshot | `repository/review.py:86-123` | fake 镜像有 | **进 spec** |
| D3 | 导出快照复用条件（revision map 与 current 完全一致）；只导 chapter；无 chapter→422 | `export_service.py:60-100` | 无 | **进 spec** |
| D4 | 导出布局 `data/exports/<project_id>/<export_id>.{md,docx,epub}`，tmp+replace 原子写；无清理；项目删除残留文件 | `export_service.py:101-112,191-211` | 无 | **进 spec（显式决策）** |
| D5 | Markdown 导出格式：`# {title}`+章节 strip 后 `\n\n` 连接 | `export_service.py:157-170` | e2e | 进 spec |
| D6 | DOCX/EPUB 是"剥离 Markdown 的纯文本"而非富格式转换；EPUB 章节命名 `chapter-%03d.xhtml` | `service_common.py:79-85`、`docx_exporter.py`、`epub_exporter.py` | 无 | **进 spec（含库选型）** |
| D7 | 排序契约：项目 updated_at 倒序；文档 kind,position,created_at | `repository/project.py:133-141,153-158` | 无 | 进 spec |
| D8 | 保存语义：409 带 `current_revision_id`；同请求可改 title/metadata；revision_number 递增+parent 链；source ∈ author/ai-accepted/restore | `repository/document.py:186-227` 等 | 有 | 部分进 spec |
| D9 | proposal job JSON 形状；accept 幂等；accept 后 metadata 写 `ai_job_id` | `ai_job_persistence.py:132-153`、`ai_service.py:230-258` | 有 | **进 spec** |
| D10 | 输出消毒：9 组机械话术替换/删除、preamble 删除、空白归一 | `service_common.py:127-229` | 5 用例 | **进 spec** |
| D11 | 输入消毒：6 种 injection 模式→`[REDACTED]` + 指令包裹边界 | `service_common.py:164-193` | 有 | **进 spec** |
| D12 | token 计数回退：provider 无 usage 时按词数估算 | `ai_job_persistence.py:16-17` | 无 | 进 spec |
| D13 | usage_events 记账：proposal 完成与 retry 成功各一条 | `ai_job_persistence.py:82-102` | 无 | 进 spec |
| D14 | operation 枚举 vs provider step 词汇表错配（= F-1） | 见 F-1 | 无 | **重写前决策** |

### 4.5 AI providers（6 条）

| # | 行为 | 证据 | 测试 | 建议 |
|---|---|---|---|---|
| E1 | 未配置 key 的 provider 抛错不回退 mock | `provider_factory.py:39-64` | 有 | **进 spec** |
| E2 | 默认模型链：dashscope→qwen3.5-flash、openai→gpt-4o-mini、mock→studio-copilot-v1 | `llm_settings.py:101-109` | 无 | **进 spec** |
| E3 | DashScope 细节：transport 三模式、retry 3 次（429/5xx/timeout/bad json）、180s 超时地板、schema coercion、非对象回退 | `dashscope_text_generation_provider.py:36-55,90-97,196-208` | 有 | **进 spec** |
| E4 | OpenAI 兼容：json_object 模式、system 尾拼 schema、错误归一化+重试 | `openai_compatible_*.py:63-81,96-121,193-221` | 7 用例 | **进 spec** |
| E5 | provider 每请求即时构造、finally aclose | `ai_service.py:106-123` | 无 | 重写注意 |
| E6 | provider 选择由前端传参+project settings 默认 mock | `useStudioProposal.ts:69-75`、`workflow_router.py:58-67` | 无 | **进 spec** |

### 4.6 jobs（3 条）

| # | 行为 | 证据 | 测试 | 建议 |
|---|---|---|---|---|
| F1 | **无后台执行器**：proposal/review/export 全部请求内同步执行 | `workflow_router.py:48-67`、`repository/job.py:74-75` | 无 | **进 spec（并发模型声明）** |
| F2 | retry=新建 job+`retry_of_job_id` 链+JobEvent 全记录；import 不可 retry | `job_service.py:52-107` | 有 | **进 spec** |
| F3 | job events 随 payload 返回 `{id,status,details,created_at}` | `service_payloads.py:145-153` | 有 | 已随 OpenAPI 冻结 |

### 4.7 前端（14 条）

| # | 行为 | 证据 | 测试 | 建议 |
|---|---|---|---|---|
| G1 | 路由：`/`、`/projects`、`/projects/:projectId/:section?`（默认 manuscript） | `router.tsx:12-20` | 无 | **进 spec** |
| G2 | **无 job 轮询**（仅切 tab 或操作后拉取） | `useStudioInspectorState.ts:61-72` | 无 | **进 spec（显式声明）** |
| G3 | 草稿仅内存 state，切文档即丢 | `useDocumentDraft.ts:19-57` | 有 | **进 spec（澄清 retain 范围）** |
| G4 | 自动保存状态机：idle/saving/saved/error/conflict；1.5s debounce；与已存快照逐字比较才触发；冲突挂起；防重入；409 自动拉 baseline | `useDocumentDraftAutosave.ts:62-108` | 有 | spec 覆盖 1.5s，余进 spec |
| G5 | 冲突二选一实现（loadLatest / retryOverwrite） | `useDocumentDraft.ts:197-254` | 有 | 已覆盖 |
| G6 | 导出成功即浏览器下载：blob+`{title}.{ext}`+100ms revoke | `useExportDownload.ts:24-36` | 有 | 进 spec |
| G7 | API 客户端：credentials include、写自动 CSRF、全局超时默认 **300000ms**、错误文案归一 | `api.ts:48-110`、`config.ts:3-4` | 有 | **进 spec（超时值）** |
| G8 | section→kind 过滤：outline/characters/world 只显示对应 kind | `useActiveDocument.ts:5-16` | 有 | 进 spec |
| G9 | section→Inspector 联动；settings 按项目快照隔离 | `useStudioInspectorState.ts:27-33,74-94` | 有 | 进 spec |
| G10 | 新文档命名 `Chapter N`/`{Label} N`；chapter 预填 `# Chapter N` | `useStudioActions.ts:70-78` | 有 | 进 spec |
| G11 | EntryPage 流程：有会话跳 /projects；未配置走 setup+login 一键；guest 按钮 | `EntryPage.tsx:17-60` | 无 | **进 spec** |
| G12 | 项目加载失败（401/404）静默 navigate('/') | `useStudioProject.ts:27-29` | 无 | 重写注意 |
| G13 | reorder UI：移动一格=前端全量重排后整集提交 | `useStudioActions.ts:92-126` | 有 | 进 spec |
| G14 | 修订缓存：模块级 Map+useSyncExternalStore+版本号防竞态 | `useRevisionCache.ts:7-83` | 有 | 可接受丢失 |

### 4.8 配置面（6 条）

| # | 行为 | 证据 | 测试 | 建议 |
|---|---|---|---|---|
| H1 | env 文件是 **`.env.local`**（非 .env） | `settings_base.py:9-20` | 无 | **进 spec** |
| H2 | env 前缀族 APP_/DB_/API_/SECURITY_/LLM_/LOG_/MONITORING_/HEALTH_；CORS 多别名 | `settings.py:30-155` | 有 | **进 spec** |
| H3 | 默认：DB `sqlite:///./data/novel-engine.sqlite3`（强制 sqlite）；host 0.0.0.0:8000；rate 5/min | `settings_sections.py:60-104,159` | 有 | **进 spec** |
| H4 | 非 prod 未设 secret 时每次启动随机生成（=每次重启全员登出） | `settings.py:201-212` | 无 | **进 spec** |
| H5 | 版本读取链：pyproject.toml→包元数据→"0.3.1" 兜底 | `settings_sections.py:34-42` | 无 | 重写注意 |
| H6 | 中间件栈（GZip/CORS/Logging/Metrics/Correlation/RateLimit 固定顺序）；Prometheus 独立端口 9090 默认关；X-Correlation-ID/X-Request-ID 回显 | `main.py:121-143`、`metrics_middleware.py` | 有 | 进 spec 或决策 |

### 4.9 横切（7 条）

| # | 行为 | 证据 | 测试 | 建议 |
|---|---|---|---|---|
| I1 | 基础工具语义：`new_id`=uuid4；`_word_count` 正则 `\b[\w'-]+\b`（word_count、250 词阈值、token 回退共用） | `domain/utils.py:17-62` | 有 | **进 spec（word_count 定义）** |
| I2 | studio 四异常→404/409/409/422 映射；`src/shared/domain/exceptions.py` 大体系实际未被生产使用（死代码） | `domain/exceptions.py:6-27`、`errors.py:21-44` | 有 | 重写可弃 shared 体系 |
| I3 | principal scope：owner→owner_id、guest→session_id，全部查询强制 scope | `service_common.py:232-236` | 有 | **进 spec** |
| I4 | CLI 面：serve（backup+migrate）/import（--source+owner_principal 绕过 HTTP 认证）/backup/doctor（PRAGMA quick_check） | `novel_engine.py:73-156` | 8 用例 | doctor/backup 进 spec |
| I5 | lifespan：structlog、启动 guest 清理、每小时循环、shutdown dispose | `runtime.py:74-126` | 部分 | 已覆盖 |
| I6 | 导出 payload 内嵌相对 `download_url` 供前端直接用 | `service_payloads.py:157-167` | 快照 | 已冻结 |
| I7 | QA 脚本体系（OpenAPI/size/SSOT/hygiene/regression） | `scripts/qa/`、`scripts/ai/` | 有 | 重写时决定 TS 等价物 |

## 5. TS 绿地重写风险清单

### R1 验收契约空洞（最高风险）

spec 18 条只覆盖产品骨架；62 条隐性需求中约 2/3 无测试锁定。**"TS 实现 OpenSpec
验收通过" 目前不等于"功能等价"。** 缓解：开图后第一优先把加粗条目分批升格进
openspec（候选首批：B1 搜索、A4/A5/A12 契约形状、D2/D3/D4 业务规则、C6/C8、F1/G2、
I3）；对每条显式决策"进 spec / 接受丢失"。

### R2 冻结契约只有三份

OpenAPI 快照、`novel_studio_*` cookie 名、alembic 迁移链（+其背后的 DB schema：
C1–C5 的约束与列）。DB schema 的隐性约束无 spec 载体——重写若继续用既有
`data/*.sqlite3`，schema 兼容是硬约束（C9/C10：FTS 表在元数据之外、手写清理）。

### R3 行为语义容易被"过度设计"掉

jobs 同步执行、无 lease、无轮询、草稿内存态、provider 即用即关、导出无清理——
这些是有意或无意的现状选择。重写者若按"现代最佳实践"加后台队列/轮询/本地持久化，
就静默改变了产品语义（且可能违反 spec 已冻结的异步状态 Requirement）。开图时逐条
显式决策。

### R4 验收面太窄

ADR 的门禁是"Playwright e2e 通过"，但 e2e 现仅 1 文件 2 用例（CI smoke）。作为
cutover 唯一验收面不足；且 F-1 证明"流程通过≠内容正确"，e2e 需补内容级断言
（proposal 文本、docx/epub 内容、搜索结果）。

### R5 质量门禁的 TS 等价物未定义

mypy/import-linter/OpenAPI 快照/SSOT/file-size 五套门禁在 TS 侧无对应物
（ADR 已承诺"重新建立而非移植"）。input-linter 的 6 条契约可作为 TS 模块边界
（如 eslint boundaries / dependency-cruiser）的需求输入；F-6 的 ai 归属决策要先做。

### R6 可直接丢弃的死重（净清单）

`src/shared/domain/` 两模块（注意先迁移 `tests/shared/domain/` 的 62 个用例或随
模块一起删）、6 个空包、4 条死路由、6 个 Python 依赖（含 `httpx2` 笔误）、
`src/shared/domain/exceptions.py` 异常体系（I2）。低置信项（imports/preview、
/version、/health）迁移前确认外部消费者。

### R7 开图时的决策 ticket 候选（喂给 wayfinder）

1. mock provider 语义（修复 F-1 还是重写时重新设计 AI 测试双簧）
2. ai context 归属：共享内核 or 独立 context（F-6）
3. cookie 名：保留 `novel_studio_*` or 迁移（P2-13）
4. 导出文件生命周期（F-5/D4）
5. 数据迁移策略：沿用 sqlite schema or 新 schema+迁移工具（R2/C9）
6. TS 栈选型（runtime/framework/ORM/monorepo，ADR 已留白）+ TypeScript 7.x
   与 undici/jsdom 约束（F-10）
7. e2e 验收面扩充策略（R4）
8. 隐性需求升格 spec 的分批计划（R1）
9. 前端类型 codegen vs schema-first（F-9）
10. 质量门禁 TS 等价物清单（R5）

## 6. 方法与可复现性

- 基线命令与输出：第 1 节表格（2026-08-17，commit `14c141d5`）。
- 审查：6 个只读子代理（分层/漂移/测试/尺寸/死代码/前端）+ 1 个隐性需求专项；
  高价值疑点人工复核 4 项：F-1 枚举错配（读源码确认）、symlink 测试缺失（grep）、
  前端版本渲染（纠正子代理误报）、`httpx2` 依赖（pyproject 确认）。
- 已知排除：mimosa 深扫结果（2026-08-17，clean）不重复；`AUDIT_REPORT_Linus.md`
  为只读参考未纳入；`tests/performance` 不存在。
- 局限：子代理结论经交叉复核但未逐条重跑；62 条隐性需求的"测试锁定"状态按
  "存在直接断言"口径判定，间接覆盖未计入。
