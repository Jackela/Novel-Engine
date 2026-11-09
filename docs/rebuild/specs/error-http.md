# 错误契约 · HTTP 信封 · 分页协议 规格

本文件是重建时 `contracts/errors.ts`、`contracts/http-envelope.ts`、`contracts/cursor.ts` 的唯一输入。
所有条目均来自旧代码实测，格式为 `file:line`，路径相对仓库根 `/Users/jackela/Documents/GitHub/Novel-Engine`。**行号引用约定**：跨行调用的区间取 `throw` 首行至 `);`，且区间内必须包含支撑结论的那个 token——否则读者按区间核对时看不到证据，会直接推翻结论（例：`job_store_part.ts:289`–`:294` 的 `1` 在 `:293`，区间若截止到 `:292` 就把「带延迟」的唯一证据漏在括号外）。

旧代码的三处 SSOT：

| 关注点 | 唯一来源 |
| --- | --- |
| 错误码集合 | `server/src/shared/domain/error_codes.ts:5` |
| 码 → HTTP 状态 | `server/src/shared/interface/http/error_envelope.ts:13` |
| 人类可读目录 | `docs/agents/error-codes.md:17` |

三者由 `server/scripts/qa/check_error_codes.mjs:121` 做双向集合 + 状态码 lockstep 校验（注释在 `:5`）。
重建后应保留同等强度的门禁：`ERROR_CODES` 与 `ERROR_HTTP_STATUS` 用 `satisfies` 编译期闭合（`error_envelope.ts:36`），markdown 目录用脚本对齐。

---

## 1. 错误码全表

共 **22 条**，与 `ERROR_CODES`（`server/src/shared/domain/error_codes.ts:6`–`:27`）逐条一一对应，不省略。
`是否可重试` 一列取自 `docs/agents/error-codes.md:19` 的 agent 指引语义，记录的是「agent 是否存在可行补救路径」——**含换一个请求再试**。它与 §6.1 的 `retryable`（严格定义：原样重试同一请求）不是同一维度，差异见 §6.1 开头，不要直接照抄本列。

| # | code | HTTP status | 触发条件 | 用户可见文案 | 是否可重试 |
| --- | --- | --- | --- | --- | --- |
| 1 | `UNAUTHORIZED` | 401 | 无 / 过期 / 非法 session cookie。`principalGuard` 解析 principal 为 null 时抛出，`requirePrincipal` 兜底再抛一次 | `Owner session required.`（`auth_guard.ts:52`、`:94`） | 是（重新登录后带 cookie 重试） |
| 2 | `FORBIDDEN` | 403 | 已认证但无权限：非 owner 访问 owner-only 面（provider catalog、legacy import），或 `POST /api/setup` 的 Origin/Referer 非同源 | `Owner session required.`（`provider_routes.ts:45`）／`This operation requires the local Owner.`（`import_routes.ts:62`）／同源说明长文案（`auth_routes.ts:178`） | 否（换身份或改客户端来源） |
| 3 | `SETUP_TOKEN_INVALID` | 403 | `POST /api/setup` 来自非 loopback 对端且 `x-setup-token` 缺失或不等；缺失、畸形、不匹配三者不可区分 | 长文案，指向 `first-start setup token` 日志行与 `.setup-token` 文件（`auth_routes.ts:196`） | 是（补上正确 header 后重试一次） |
| 4 | `CSRF_TOKEN_MISSING` | 403 | 写方法（POST/PUT/PATCH/DELETE）且路径不在 `FIRST_CONTACT_PATHS`，cookie 或 header 之一为空 | 模板文案，含 cookie/header 名与豁免路径列表（`auth_guard.ts:68`） | 是（回显 cookie 到 header） |
| 5 | `CSRF_TOKEN_INVALID` | 403 | 两个 token 均存在但 `timingSafeEqual` 不等 | 模板文案，指示重新登录取新对（`auth_guard.ts:75`） | 是（重登后重试） |
| 6 | `RATE_LIMIT_EXCEEDED` | 429 | 首触点路径（`/api/setup`、`/api/session/login`）按 `ip:method:path` 计数超限；`details.retry_after_seconds` 与 `Retry-After` 头同值 | `Rate limit exceeded.`（`auth_routes.ts:121`） | 是（等待 hint 秒数） |
| 7 | `NOT_FOUND` | 404 | 资源在寻址范围内不存在，或存在于别的 project（二者刻意不可区分）。同时用于未知路由 | `<Resource> not found: <id>.`（如 `studio_query_helpers.ts:45` `Project not found: ...`）；未知路由为 `Route <method> <url> is not known to this API.`（`error_envelope.ts:200`） | 否（核对 id / 路径） |
| 8 | `INVALID_OPERATION` | 422 | 请求格式合法但域拒绝：前置条件不满足、非法取值、作业状态不可重试、登录凭据错（常量时间路径，不区分用户不存在与密码错） | 透传域异常 message（`studio_error_mapping.ts:200`） | 否（改输入或推进状态） |
| 9 | `PROVIDER_NOT_CONFIGURED` | 422 | 所选生成 provider 在服务端无可用凭据（dashscope 缺 `DASHSCOPE_API_KEY`、openai_compatible 缺 `LLM_API_KEY`）；不会回退 mock | 透传 `ProviderNotConfiguredError.message`（`studio_error_mapping.ts:191`） | 否（补 key 并重启） |
| 10 | `EXPORT_CAPACITY_EXCEEDED` | 422 | 新导出超过固定 source-document / source-byte / artifact-byte 预算。`details` 仅含 `resource`、`limit`、`observed`（`observed` 饱和到 `limit+1`） | 固定字面量 `Export capacity exceeded.`（`export_capacity_schemas.ts:14`，映射处 `studio_error_mapping.ts:180`） | 否（预算永久固定） |
| 11 | `GENERATION_CAPACITY_EXCEEDED` | 422 | 完整 Provider prompt 超过 8 MiB UTF-8 预算（`generation_capacity_policy.ts:2`），或 lore 抽取片段超码点预算 | 固定字面量 `Generation capacity exceeded.`（`generation_capacity_schemas.ts:20`） | 否（同 key 会重放同一拒绝） |
| 12 | `IMPORT_CAPACITY_EXCEEDED` | 422 | 旧 workspace 超过固定 inspection 预算（story/chapter/total byte、章节数、目录项数） | 固定字面量 `Legacy import capacity exceeded.`（`studio_error_mapping.ts:35`，本码无专属 schema） | 否 |
| 13 | `STRUCTURE_CAPACITY_EXCEEDED` | 422 | 受门控的结构写入将超过固定闭集预算（`structure_capacity.ts:15`：project_documents 2500、project_volumes 100、volume_chapters 2000、project_settings_bytes 16384、document_metadata_bytes 16384、outline_beats 5000） | 固定字面量 `Authoring structure capacity exceeded.`（`structure_capacity_schemas.ts:20`） | 否（无 retry hint、无 override） |
| 14 | `VALIDATION_ERROR` | 422 | AJV schema 校验失败、游标解码失败、PATCH 原始键守卫失败、无 body 契约却带 body | 固定字面量 `Request validation failed.`（`error_envelope.ts:172`、`canonical_cursor.ts:14`、`project_update_raw_keys.ts:15`） | 是（按 `details.errors` 改一次） |
| 15 | `REVISION_CONFLICT` | 409 | 乐观并发：保存基于的 revision 已非当前 revision，未发生写入。`details.current_revision_id` 给出赢家。`base_revision_id: null` **不是「强制覆盖」**——文档恒有 current revision，`null !== <id>` 必然 409（`document_revision_writes.ts:57`） | `Document changed since the requested base revision.`（`exceptions.ts:34`，透传于 `studio_error_mapping.ts:117`） | 是（用新 base 重放） |
| 16 | `VOLUME_CONFLICT` | 409 | 同 project 内 volume 标题重复 | `A volume titled "<title>" already exists in this project.`（`exceptions.ts:202`） | 否（换标题） |
| 17 | `SNAPSHOT_CONFLICT` | 409 | 不可变 export snapshot 仍引用该 document，删除被拒 | 固定字面量 `Document is referenced by an immutable snapshot.`（`exceptions.ts:43`，schema enum 于 `studio_schemas.ts:233`） | 否（永久） |
| 18 | `DOCUMENT_CONFLICT` | 409 | 同 `(project, kind, title)` 身份的 document 已存在 | `A <kind> document titled "<title>" already exists in this project.`（`exceptions.ts:190`） | 否（换标题） |
| 19 | `OPERATION_IN_FLIGHT` | 409 | 同一 pipeline 操作（generation/review/export/retry）已在跑；或 project 删除持有 project-wide 转换窗口（`document_id: null`） | `The <operation> operation is already running for this project\|document.`（`exceptions.ts:239`）；带可选 `Retry-After`（`studio_error_mapping.ts:151`） | 否（轮询 jobs；删除场景等清理完成，404 即完成） |
| 20 | `OPERATION_CAPACITY_EXCEEDED` | 503 | app 级或 project 级昂贵工作流配额已满。`details.scope`（`project`\|`application`）、`limit`、`in_flight`、`project_id`、`retry_after_seconds`；同值写 `Retry-After` | 固定字面量 `Studio operation capacity is exhausted.`（`studio_schemas.ts:150`） | 有条件（等 hint 秒后由 Owner 决定，不自动重试） |
| 21 | `SERVICE_UNAVAILABLE` | 503 | 持久层未配置（无数据库实例、API-only 启动、缺 data directory），或 diagnostics 面未装配 | `The persistence layer is not configured.`（`auth_guard.ts:44`、`auth_routes.ts:75`、`project_routes.ts:51`、`import_routes.ts:100`）／`The diagnostics surface is not configured.`（`diagnostics_routes.ts:106`） | 否（同一实例无意义） |
| 22 | `INTERNAL_ERROR` | 500 | 未捕获异常；stack 只进日志不进响应。`details.error_id` 等于请求 id（即 `x-request-id` 头） | `An internal error occurred.`（`error_envelope.ts:190`） | 否（读 `error_id` 报问题） |

**⚠ 上文表格记录的是旧实现的 wire；新契约的现值见 §6.4。** 旧实现里「用户可见文案」那一列就是实际输出。新契约把 8 个码的 `message` 改为**编译期必填**（`ErrorCodeRequiringMessage`，`contracts/errors.ts:210`–`:218`：`FORBIDDEN`、`NOT_FOUND`、`INVALID_OPERATION`、`PROVIDER_NOT_CONFIGURED`、`VOLUME_CONFLICT`、`DOCUMENT_CONFLICT`、`OPERATION_IN_FLIGHT`、`SERVICE_UNAVAILABLE`），表里那几句因此退化为**兜底句**：抛出点必须自带具体信息（资源 id、冲突标题、provider 名、哪个 store 未配置），`AppError` 的两组重载（`platform/http/error_envelope.ts:55`–`:59`）让「漏传」变成编译错误。其余 14 个码（`ErrorCodeWithDefaultMessage`，`contracts/errors.ts:221`）才可以回落到表里的句子。

一个易误判的例外：`REVISION_CONFLICT` **不在**必填组，它用通用句也不算丢信息——可操作的信息在 `details.current_revision_id`，不在 `message`。

**目录外的运输层码**：Fastify 自身抛出的 4xx（`FST_ERR_*`）以**原 code、原状态**透传同一信封，不入目录（`error_envelope.ts:177`–`:187`，`docs/agents/error-codes.md:48`）。判定条件是 `statusCode ∈ [400,500)` 且 `code.startsWith("FST_ERR")`（`:178`–`:184`）。实际可达的四个：

| 触发 | status | 线上 `code` | 说明 |
| --- | --- | --- | --- |
| 请求体超过 1 MiB，**且该路由声明了 body 契约** | **413** | `FST_ERR_CTP_BODY_TOO_LARGE` | 实例级 `bodyLimit: 1_048_576`（`apps/api/http_server_policy.ts:43`），**handler 之前**拒绝；测试断言 `server/tests/apps/api/inbound_request_lifetime.test.ts:274` |
| body 不是合法 JSON 但 content-type 声明为 JSON | 400 | `FST_ERR_CTP_INVALID_JSON_BODY` | 测试 `server/tests/api/error_envelope.test.ts:186` |
| 不支持的 content-type | 415 | `FST_ERR_CTP_INVALID_MEDIA_TYPE` | `fastify/lib/errors.js:111`–`:115` |
| body 长度与 `Content-Length` 不符 | 400 | `FST_ERR_CTP_INVALID_CONTENT_LENGTH` | `fastify/lib/errors.js:116`–`:120` |

这四条**都不产生 `details`**（`sendEnvelope` 只传 code+message），也**都不在 `ERROR_CODES` 里**。特别注意 413：`PAYLOAD_TOO_LARGE` 这个常见命名在本实现里**不存在**，客户端若按名字匹配会全部落空，必须按 `FST_ERR_CTP_BODY_TOO_LARGE` 或仅按 413 判断。

**关于下文引用的第三方行号**：`fastify/lib/route.js`、`fastify/lib/content-type-parser.js` 是 `node_modules` 里的实现内部行号，`pnpm` 升一个小版本就可能漂移，属**易腐证据**。之所以仍然引，是因为「onRequest 早于 body 解析」在本仓没有测试能证明（唯一相关用例只发了 32 字节，见下），只有源码能定论。结论本身是 Fastify 的**公开生命周期契约**（onRequest → preParsing → 解析），应作为长期依据；行号仅用于本次复核，重建时不必保留。

**413 与 422 `undeclared_body` 的优先级（易答反）**：`bodyLimit` 的检查发生在**内容类型解析阶段**（`fastify/lib/content-type-parser.js:250`–`:252`，`contentLength > limit` 即抛 413），而 `registerUndeclaredRequestBodyPolicy` 挂在 **`onRequest`**（`http_server_policy.ts:64`）。Fastify 的生命周期是 `onRequest` → `preParsing` → 内容解析（`fastify/lib/route.js:564`–`:566`，再 `:658`–`:659`），所以：

- 路由**有** `schema.body` 且体 > 1 MiB → **413** `FST_ERR_CTP_BODY_TOO_LARGE`
- 路由**无** `schema.body` 且体 > 0 → **422** `VALIDATION_ERROR`（`type: "undeclared_body"`，附 `connection: close`），**即使超过 1 MiB 也是 422**：钩子只判 `content-length > 0` / `transfer-encoding` 存在与否，与体大小无关，413 根本没有机会触发

现有测试只覆盖后者的小体情形（`inbound_request_lifetime.test.ts:160`–`:204`，`Content-Length: 32` 与 `Transfer-Encoding: chunked`），**没有 >1 MiB 的对照用例**。因机制与大小无关，预期仍是 422，但重建时应补一条 >1 MiB 的 bodyless 用例把优先级钉死——否则很容易被写成「超限一律 413」。

**目录外的流内码**：SSE 帧里的 `code` 是另一套词表，**不走 HTTP 信封、没有 status**，因此不能塞进 `ERROR_CODES`：

| code | 载体 | 位置 | 说明 |
| --- | --- | --- | --- |
| `PROVIDER_FAILED` | `{type:"error"}` SSE 帧 | `proposal_frame.ts:34`（schema 为 `Type.Literal`，**不是**自由字符串）；发出点 `proposal_pipeline.ts:200`、重放路径 `proposal_landing.ts:290` | 流已建立后的 provider 失败。此时 HTTP 状态早已是 200，客户端只能靠帧判断失败 |
| `PROPOSAL_STREAM_DRAIN_TIMEOUT` | **无载体** | `proposal_stream_response.ts:21` | 30 s 未 drain 的内部诊断码，`response.destroy(failure)`（`:140`）直接掐断连接，客户端只看到网络错误，收不到任何帧或信封 |

**顺带澄清一个容易凭空新增的状态：客户端永远看不到 502。** `502` 在本仓只作为**上游 provider 的可重试状态**出现（`contexts/ai/infrastructure/providers/provider_http.ts:15` 的 `RETRYABLE_HTTP_STATUSES = {429,500,502,503,504}`、`platform/text-generation/ports.ts:183`），是「我们收到」而非「我们发出」。provider 失败的两条对外路径都不会产出 502：

- 同步生成：失败落成 persisted failed job，HTTP 仍是 **200**（job payload 的 `status: "failed"`）；
- 流式：hijack 后发 `{type:"error", error:{code:"PROVIDER_FAILED"}}` 帧，HTTP 仍是 **200**。

所以若重建时为了"语义准确"给上游失败新增 502，那是**新增第 23 个对外状态/码**，不是还原旧行为——必须显式记录为破坏性变更，并同步 `docs-error-codes` 与本表。

failure kind（`platform/text-generation/ports.ts:158`–`:198`，`grep -c 'readonly kind: "'` = **12 个**，下表 12 个全覆盖）与对外形态的完整对应：

| failure kind | 对外表现 | 有 HTTP 码？ |
| --- | --- | --- |
| `unconfigured`（`:193`） | 422 `PROVIDER_NOT_CONFIGURED` | 有 |
| `timeout_first_byte` / `timeout_idle` / `timeout_deadline`（`:158`–`:162`）与 `protocol_not_json` / `protocol_missing_field` / `protocol_unknown_event` / `protocol_stream_truncated`（`:164`–`:179`） | 同步：200 + persisted failed job；流式：200 + `PROVIDER_FAILED` 帧 | **无**（本行按**对外形态**并列；provider 侧 `protocol_not_json` 可重试而其余三条不可，若将来按可重试性重排需拆行，并同步改「12 个」那句） |
| `transport_http_status`（`:181`，含上游 `status`，可能是 502）/ `transport_connect` / `transport_interrupted`（`:186`–`:188`） | 同上——**上游 502 在这里被吸收，不会转成我们的 502** | **无** |
| `content_not_prose`（`:198`） | 同上 | **无** |

容量类（`OPERATION_CAPACITY_EXCEEDED` 等）仍走 422 / 503。一句话：**provider 的 failure kind 映射到「运行结果」，不映射到 HTTP 响应；HTTP 错误码只覆盖「请求本身不成立」。** 这条边界一旦被跨过，用量表会少掉 failed job 行、客户端轮询指引也要改。

结论：错误码不是「一个平面清单」，而是**两个通道**（HTTP 信封 / SSE 帧）+ 一个不可达的内部诊断码。新契约必须显式区分通道，否则 `PROVIDER_FAILED` 会被硬塞进 HTTP 状态表并被迫编造一个状态。详见 §2.5、§6.1。

---

## 2. 信封形状

### 2.1 成功响应：无包装

成功响应是**裸对象**，没有 `{data: ...}` 外层。列表直接返回具名字段数组加 `next_cursor`：

- `/api/projects` → `{ projects: [...], next_cursor: string \| null }`（`project_routes.ts:92`–`:95`）
- `/api/projects/:id/revisions` → `{ revisions: [...], next_cursor }`（`revision_routes.ts:66`–`:73`）
- `/api/projects/:id/jobs` → `{ jobs, next_cursor }`（`job_routes.ts:94`–`:97`）
- `/api/projects/:id/exports` → `{ exports, next_cursor }`（`export_routes.ts:151`–`:154`）
- `/api/projects/:id/reviews` → `{ reviews, next_cursor }`（`review_routes.ts:125`–`:128`）
- `/api/projects/:id/search` → `{ results, total, next_offset }`（`studio_schemas.ts:52`–`:58`）

单个资源同样裸返回（`project_routes.ts:163`–`:170` 直接返回 `.payload`）。
204 响应 body 为 `null`，schema 声明 `{ type: "null" }`（`project_routes.ts:207`、`auth_routes.ts:255`）。

新契约决策点：保留裸对象（成本低、与 OpenAPI 已发布一致），还是引入 `{data}`。若引入，必须同时改所有 payload schema，不建议。

### 2.2 错误响应字段

唯一形状（`error_envelope.ts:117`–`:121`）：

```
{ "error": { "code": string, "message": string, "details"?: object } }
```

- `code`：必填，来自 `ERROR_CODES`（OpenAPI 里声明为开放 string，以放行 `FST_ERR_*`，`error_envelope.ts:89`）
- `message`：必填
- `details`：可选，仅在有值时出现（`error_envelope.ts:118` 的 `if (details !== undefined)`）
- `request_id`：**信封中没有这个字段**。请求关联 id 只以 `details.error_id` 出现在 `INTERNAL_ERROR`（`error_envelope.ts:190`–`:192`），值等于 `request.id`，而 `request.id` 被回写为 `x-request-id` 响应头。rebuild 若想让每个错误都可追踪，需要新增 `error.request_id`——这是一处**有意的契约扩展**，必须与 `x-request-id` 同值，否则会分裂出两套追踪标识。
- `additionalProperties: false`（`error_envelope.ts:83`、`:86`）：信封是封闭对象，多一个字段即违反 schema。
- **运输层错误（`FST_ERR_*`）只有 `code` + `message`**，永不带 `details`（`error_envelope.ts:185` 只传三个位置参数中的前三个），且 `code` 不来自目录，`message` 是 Fastify 原文。这是信封里唯一「`code` 非闭集」的合法情形。

### 2.3 校验失败形状

触发点：AJV（`error_envelope.ts:167`）、裸 body 策略（`http_server_policy.ts:70`）、PATCH 原始键守卫（`project_update_raw_keys.ts:36`）、游标解码（`canonical_cursor.ts:11`）。

```
{ "error": { "code": "VALIDATION_ERROR", "message": "Request validation failed.",
             "details": { "errors": [ { "field": string, "message": string, "type": string } ] } } }
```

- `field`：`instancePath` 去掉前导 `/`，空则 `"(root)"`（`error_envelope.ts:138`）
- `message`：AJV 原文，缺省 `"value is invalid"`
- `type`：AJV `keyword`，缺省 `"invalid"`
- schema 声明三者全部 required（`unprocessable_entity_schemas.ts:55`–`:66`）
- 游标失败固定写 `field: "cursor"`、`message: "value is invalid"`、`type: "invalid"`（`canonical_cursor.ts:16`）
- 三处语义化特例：`additionalProperties` + `"unknown field is not allowed"`（`project_update_raw_keys.ts:49`）、`minProperties` + `"at least one field is required"`（`:52`）、`type: "undeclared_body"`（`http_server_policy.ts:74`–`:78`）

**旧实现的统一性（新建时别丢）**：无论失败来自 AJV、手写守卫还是游标解码，旧代码产出的 `VALIDATION_ERROR` **形状一致**——message 恒为 `Request validation failed.`，细节一律进 `details.errors[]`，每项齐备 `field` / `message` / `type`。这让 `docs/agents/error-codes.md:34` 能对 agent 说一句「按 `details.errors` 里列的字段改」。重建后一度分裂成两种形状（分页走自定义 message + 扁平 details），现已在 `pagination.ts:71`–`:81` 收复：`invalid(field, message)` 固定产出 `message: "Request validation failed."` + `details: { errors: [{ field, message, type: "invalid" }] }`，与 AJV 路径同构，且注释明写「an agent told to 'read details.errors' must not hit a second layout here」。新增校验代码必须走这个工厂，不要自己 `new AppError`。

### 2.4 404 / 409 / 422 / 503 的额外字段

| 状态 | 码 | `details` 额外字段 | 额外头 |
| --- | --- | --- | --- |
| 404 | `NOT_FOUND` | 无（走通用 `ErrorEnvelope` 引用，`error_envelope.ts:100`） | 无 |
| 409 | `REVISION_CONFLICT` | `current_revision_id: string \| null`（required，`studio_schemas.ts:72`–`:77`） | 无 |
| 409 | `DOCUMENT_CONFLICT` | 无（`studio_schemas.ts:85`–`:99`） | 无 |
| 409 | `VOLUME_CONFLICT` | 无（`volume_routes.ts:23`） | 无 |
| 409 | `SNAPSHOT_CONFLICT` | 无，且 `message` 被 schema 锁成固定 enum（`studio_schemas.ts:230`–`:235`） | 无 |
| 409 | `OPERATION_IN_FLIGHT` | `project_id: string`、`document_id: string \| null`、`operation: string`（全 required，`additionalProperties: false`，`studio_schemas.ts:113`–`:122`） | **条件性**：仅当构造时传了 `retryAfterSeconds` 才发（`studio_error_mapping.ts:151`–`:153`）。实测只有 keyed retry 路径传 `1`（`job_history_service.ts:233`），准入路径不传（`operation_in_flight.ts:82`）→ **不发**。详见 §2.6 |
| 422 | `INVALID_OPERATION` | 无（`unprocessable_entity_schemas.ts:3`–`:18`，仅 code+message） | 无 |
| 422 | `VALIDATION_ERROR` | `errors[]`（见 2.3） | 无 |
| 422 | `PROVIDER_NOT_CONFIGURED` | 无（`unprocessable_entity_schemas.ts:24`–`:39`，缺的凭据名只写在 message 里） | 无 |
| 422 | `*_CAPACITY_EXCEEDED`（4 个） | `resource`（闭集 enum）、`limit`（int ≥0）、`observed`（int ≥1，饱和到 `limit+1`）（`export_capacity_schemas.ts:27`–`:36`、`structure_capacity_schemas.ts:32`–`:41`、`generation_capacity_schemas.ts:41`–`:50`） | 无 |
| 503 | `OPERATION_CAPACITY_EXCEEDED` | `scope: "project"\|"application"`、`limit`、`in_flight`、`project_id`、`retry_after_seconds`（全 required，`studio_schemas.ts:165`–`:176`） | **有** `Retry-After`（`studio_error_mapping.ts:170`） |
| 503 | `SERVICE_UNAVAILABLE` | 无（`studio_schemas.ts:184`–`:200`，`details` 开放但实际不发） | **无** `Retry-After`（注释明示，`studio_schemas.ts:202`） |
| 429 | `RATE_LIMIT_EXCEEDED` | `retry_after_seconds: number`（`auth_routes.ts:122`） | **有** `Retry-After`（`auth_routes.ts:117`，**全仓唯一直接 `reply.header` 的一处**）。重建动作项：必须改走 `AppError.afterDelay`，否则统一信封后该头静默丢失、客户端立刻重试 |

关键区分：**503 两种码靠 `Retry-After` 是否出现来判别可重试性**，同一状态码下语义相反。新契约必须把这点写进 `retryable`，不能只看 status。

### 2.5 流式响应与信封的边界

只有一条路由是流式的：`POST /api/projects/:projectId/documents/:documentId/ai-proposals/stream`（`proposal_routes.ts:84`）。它的契约分两段，分界点是 `reply.hijack()`：

- **hijack 之前 → 普通 JSON 信封**。`writeProposalStreamResponse` 先拉第一帧（`proposal_stream_response.ts:197`），**只在第一帧成功拿到之后**才 `hijack()` + `writeHead(200, SSE_HEADERS)`（`:199`–`:201`）。所以「入参非法 / 文档不存在 / 409 `OPERATION_IN_FLIGHT` / provider 无流式能力 / `PROVIDER_NOT_CONFIGURED`」全部以标准信封 + 标准状态码返回，响应头仍是 `application/json`。
  第一帧的拉取被 `withAsyncStudioErrors` 包住（`proposal_routes.ts:137`），这是「hijack 前的域异常仍能映射成信封」的机制：异常在 `:213` 被捕获、`:249` 重新抛出，此时 hijack 未执行，Fastify 仍可直接写响应。
- **hijack 之后 → 只有 SSE 帧，永远不会有信封**。写过头之后 `reply.raw` 已被接管，任何失败只能降级为 `{type:"error"}` 帧，或直接 `destroy()`。

流的三帧词表（`proposal_frame.ts:13`–`:47`，`additionalProperties: false`，由 TypeBox SSOT 与漂移门禁锁定）：
`{type:"delta", text}` ／ `{type:"done", job}`（job 复用 `jobPayloadSchema`，与同步落地同一 SSOT）／ `{type:"error", error:{code:"PROVIDER_FAILED", message}}`。

配套细节：
- 心跳是 SSE **注释帧** `": heartbeat\n\n"`（`proposal_stream_response.ts:17`），15 s 一次（`:15`），无 `data:` 字段；`heartbeatMs <= 0` 可关闭（`:168`）。其写返回值被**刻意忽略**（`:175`，注释 `:172`–`:174`）——心跳不受背压保护，只有 `data:` 帧做 drain 握手（`:203`–`:207`）。
- 背压：`write` 返回 false 时等 `drain`，30 s 超时（`:13`）抛 `ProposalStreamDrainTimeoutError` 并 `destroy`（`:136`–`:141`）。路由声明的 `200` 是 `text/event-stream`（`proposal_routes.ts:25`–`:30`），其余状态码仍是 JSON 信封（`:92`–`:97`）。

**对新契约的含义**：信封 schema 与帧 schema 必须是两套独立的判别联合，不能共用一个 `code` 枚举；`ErrorEnvelope` 只能描述非 200 的 JSON 响应。

### 2.6 幂等键

写路径的第三次重试保护，与 `OPERATION_IN_FLIGHT`、`OPERATION_CAPACITY_EXCEEDED` 直接相邻，所以必须写在错误契约里。

- **头名** `idempotency-key`（HTTP 头大小写不敏感，Fastify 已归一为小写键；线上客户端可写 `Idempotency-Key`）。两种 schema：可选版（`job_schemas.ts:45`–`:53`，16–128 字符、`^[A-Za-z0-9._~-]+$`）用于两个提案生成路由（`proposal_routes.ts:50`、`:90`）；必填版（`job_schemas.ts:29`–`:38`，键在 `:33`）用于 keyed retry（`job_routes.ts:159`）。
- **违反即 422 `VALIDATION_ERROR`**，`field` 为 `"idempotency-key"`（AJV `additionalProperties: false` 下未知头不报错，只有该头本身不合规才报）。
- **落库与唯一性**：列 `request_idempotency_key`（`job_usage_tables.ts:29`），配 `(project_id, request_idempotency_key)` 的**部分**唯一索引（`:42`–`:43`，`where isNotNull`）。冲突靠唯一约束错误文本判定（`job_request_claim.ts:11`），查回落在 `:33`。
- **重放语义**：重放在任何工作之前发生（`proposal_pipeline.ts:77`–`:79`、`:132`–`:137`），幂等键相同的第二次提交直接回放已存 job，不花第二次生成成本；流式重放**只产出一帧**（`done` 或 `error`，`proposal_landing.ts:287`–`:293`），不会重放 `delta` 序列。
- **仍有两处 409 会先于重放命中，但两者的头不一样**：
  - **同键的 retry 仍在跑** → 409 且**带**固定 `Retry-After: 1`：`job_history_service.ts:233` 与 `job_store_part.ts:289`–`:294` 都以**第 4 个参数 `1`** 构造异常，测试 `job_retry_idempotency_contract.test.ts:97` 断言 `retry-after === "1"`——不是只有 schema 声明。
  - **准入路径的 409** → 同 code 同 status 但**不带**：`acquire()` 只传 3 参（`operation_in_flight.ts:82`，另见 `:66`、`:123`、`:130`），映射处条件展开不写头。故 **6 个抛出点里 4 个无头、2 个带 `1`**——同一个码在 wire 上时有时无，任何「按码断定有没有头」的客户端逻辑都会错。**错判的上界**：客户端多等 N 秒后重试仍会失败，只增延迟、不改错误类型（`unchecked.md` 第 1 条的失效上界）。码上留「需要先等」的类别、抛出点给具体秒数，两层并存，见 §6.1 的两层表。

**对新契约的含义**：`retryable: true` 只对**幂等写**成立。若新契约把 `retryable` 当全局建议，而没有「该路由是否接受幂等键」这一维，客户端会对无键的写做盲目重试。建议在错误定义或路由契约里加 `idempotentReplay: boolean`。

---

## 3. 错误映射

### 3.1 domain 异常 → 错误码（`studio_error_mapping.ts:80`–`:203`，共 **14** 条）

表是有序数组，`matches` 用 `instanceof`，**顺序即优先级**；先命中先渲染，子类会被更早的父类规则吞掉。

| # | 域异常（定义处） | → code | status 写法 | details |
| --- | --- | --- | --- | --- |
| 1 | `InvalidProjectUpdateError`（`studio/domain/exceptions.ts:19`） | `VALIDATION_ERROR` | `ERROR_HTTP_STATUS[...]`（`:85`） | `errors: [{ field: "title", type: "minLength", message: error.message }]`（`:89`） |
| 2 | `NotFoundError`（`:11`） | `NOT_FOUND` | 字面量 `404`（`:97`） | 无 |
| 3 | `DuplicateVolumeError`（`:198`） | `VOLUME_CONFLICT` | 字面量 `409`（`:106`） | 无 |
| 4 | `RevisionConflictError`（`:30`） | `REVISION_CONFLICT` | 字面量 `409`（`:115`） | `current_revision_id`（`:118`） |
| 5 | `SnapshotConflict`（`:41`） | `SNAPSHOT_CONFLICT` | 字面量 `409`（`:125`） | 无 |
| 6 | `DuplicateDocumentError`（`:185`） | `DOCUMENT_CONFLICT` | 字面量 `409`（`:134`） | 无 |
| 7 | `OperationInFlightError`（`:226`） | `OPERATION_IN_FLIGHT` | 字面量 `409`（`:143`） | `project_id`、`document_id`、`operation` + 条件 `Retry-After`（`:146`–`:153`） |
| 8 | `OperationCapacityExceededError`（`:254`） | `OPERATION_CAPACITY_EXCEEDED` | `ERROR_HTTP_STATUS[...]`（`:160`） | `scope`、`limit`、`in_flight`、`project_id`、`retry_after_seconds` + `Retry-After`（`:163`–`:170`） |
| 9 | `ImportCapacityExceededError`（`:162`） | `IMPORT_CAPACITY_EXCEEDED` | 经 `capacityEnvelope` → `ERROR_HTTP_STATUS`（`:72`） | `resource`、`limit`、`observed`（`:75`） |
| 10 | `StructureCapacityExceededError`（`studio/domain/structure_capacity.ts:36`） | `STRUCTURE_CAPACITY_EXCEEDED` | 同上（`:177`） | 同上 |
| 11 | `ExportCapacityExceededError`（`studio/domain/exceptions.ts:91`） | `EXPORT_CAPACITY_EXCEEDED` | 同上（`:180`） | 同上 |
| 12 | `GenerationCapacityExceededError`（`:127`） | `GENERATION_CAPACITY_EXCEEDED` | 同上（`:183`） | 同上 |
| 13 | `ProviderNotConfiguredError`（`ai/application/ports/text_generation.ts`） | `PROVIDER_NOT_CONFIGURED` | `ERROR_HTTP_STATUS[...]`（`:189`） | 无 |
| 14 | `InvalidOperationError`（`shared/domain/exceptions.ts:6`） | `INVALID_OPERATION` | `INVALID_OPERATION_STATUS_CODE`（`:198`，间接来自 `ERROR_HTTP_STATUS`） | 无 |

承接函数有两个，且都只做「未知异常原样抛出」：同步 `withStudioErrors`（`:220`）与异步 `withAsyncStudioErrors`（`:233`）。未知异常继续冒泡到 500（注释 `:205`–`:208`）。

**未映射的域异常（会变 500）**，重建时需显式决策：
`InvalidJobTransitionError`（`exceptions.ts:209`）、`ReviewSourceInvalidatedError`（`:49`）、`ExportSourceInvalidatedError`（`:57`）、`ExportArtifactWriteError`（`:65`）。

另一张独立表 `studio_failure_classification.ts:113`–`:172` 有 8 条 `failureRule`，但它决定的是**作业落库 vs 抛出的处置**，与 HTTP 信封无关（注释 `:24`–`:26` 明确「does not consume this registry」）。重建时不要与 `contracts/errors.ts` 合并。

### 3.2 直接 `new AppError` 绕过映射的路由

| 位置 | code / status | 场景 |
| --- | --- | --- |
| `shared/interface/http/auth_guard.ts:41` | `SERVICE_UNAVAILABLE` / 503 | guard 拿到 undefined AuthService |
| `auth_guard.ts:49` | `UNAUTHORIZED` / 401 | principal 解析为 null |
| `auth_guard.ts:65` | `CSRF_TOKEN_MISSING` / 403 | cookie 或 header 为空 |
| `auth_guard.ts:72` | `CSRF_TOKEN_INVALID` / 403 | 两 token 不等 |
| `auth_guard.ts:91` | `UNAUTHORIZED` / 401 | `requirePrincipal` 兜底 |
| `shared/interface/http/auth_routes.ts:72` | `SERVICE_UNAVAILABLE` / 503 | `requireService` |
| `auth_routes.ts:118` | `RATE_LIMIT_EXCEEDED` / 429 | onRequest 限流 |
| `auth_routes.ts:175` | `FORBIDDEN` / 403 | setup 非同源 |
| `auth_routes.ts:193` | `SETUP_TOKEN_INVALID` / 403 | 非 loopback 缺 token |
| `shared/interface/http/canonical_cursor.ts:11` | `VALIDATION_ERROR` / 422 | 任意非法游标 |
| `studio/interface/http/project_update_raw_keys.ts:12` | `VALIDATION_ERROR` / 422 | PATCH 未知键 / 空对象 / 类型错 |
| `apps/api/http_server_policy.ts:70` | `VALIDATION_ERROR` / 422 | 路由无 body 契约却带 body |
| `ai/interface/http/provider_routes.ts:42` | `FORBIDDEN` / 403 | 非 owner 读 provider catalog |
| `studio/interface/http/project_routes.ts:48` | `SERVICE_UNAVAILABLE` / 503 | `requireServices` |
| `studio/interface/http/import_routes.ts:59` | `FORBIDDEN` / 403 | 非 local owner 做 legacy 预览 |
| `import_routes.ts:97` | `SERVICE_UNAVAILABLE` / 503 | 缺 dataDirectory |
| `studio/interface/http/diagnostics_routes.ts:103` | `SERVICE_UNAVAILABLE` / 503 | diagnostics 未装配 |
| `studio/interface/http/review_routes.ts:45` | `VALIDATION_ERROR` / 422 | review 创建 body 含客户端可控字段 |

这 18 处全部在 handler/preHandler/hook 里直接构造，不经 `withStudioErrors`。合理性：它们都是「框架/装配/鉴权层」失败，不来自 domain。重建时应把这些统一收敛到一个 `httpFailures` 工厂，避免 18 处重复的字面量。

### 3.3 硬编码状态码字面量（未走 `ERROR_HTTP_STATUS`）

共 21 处。重建时必须全部改为 `ERROR_HTTP_STATUS[code]`，否则码表与状态映射会二次漂移。

| 位置 | 字面量 |
| --- | --- |
| `shared/interface/http/auth_guard.ts:42` / `:50` / `:66` / `:73` / `:92` | 503 / 401 / 403 / 403 / 401 |
| `shared/interface/http/auth_routes.ts:73` / `:119` / `:176` / `:194` | 503 / 429 / 403 / 403 |
| `shared/interface/http/error_envelope.ts:170`（校验）/ `:190`（500）/ `:198`（404） | 422 / 500 / 404 |
| `contexts/ai/interface/http/provider_routes.ts:43` | 403 |
| `contexts/studio/interface/http/review_routes.ts:46` | 422 |
| `contexts/studio/interface/http/import_routes.ts:60` / `:98` | 403 / 503 |
| `contexts/studio/interface/http/project_routes.ts:49` | 503 |
| `contexts/studio/interface/http/diagnostics_routes.ts:104` | 503 |
| `contexts/studio/interface/http/studio_error_mapping.ts:97` / `:106` / `:115` / `:125` / `:134` / `:143` | 404 / 409 ×5 |

`error_envelope.ts` 自身的三处可以接受（它就是映射表本体），其余 18 处应消灭。

---

## 4. 分页协议

### 4.1 游标编码

统一编解码器 `makeKeysetCursor`（`shared/interface/http/canonical_cursor.ts:87`–`:152`）。

- **载体**：`base64url`（无 padding），内容是 JSON 数组：`[version, ...scopes, numberField, id]`（`:138`，文档 `:84`）
- **规范形式（canonical）**：解码后必须能原样重编码成同一个字符串，否则拒绝（`:47`）。这条同时挡掉 padding 变体、非最短 base64、非规范 JSON 空白
- **UTF-8 严格解码**：`new TextDecoder("utf-8", { fatal: true })`（`:7`、`:43`）
- **长度与字符集**：1–1024 字符，`^[A-Za-z0-9_-]+$`（`:5`–`:6`、`:35`）；同样的约束在四个 query schema 里重复了一遍（`studio_request_schemas.ts:124`–`:128`、`:138`–`:142`、`job_schemas.ts:15`–`:21`、`export_routes.ts:37`–`:43`、`review_schemas.ts:15`–`:21`）
- **签名**：**无签名、无 HMAC、不加密**。安全性全部来自三点：规范形式自校验、scope 与路由绑定（`:118`–`:120`）、数值域校验（`:104`–`:112`，`minNumber`、`Number.isSafeInteger`、`id.length ≤ idMaxLength`）
- **失败形状**：单一出口，即 422 `VALIDATION_ERROR` + `field: "cursor"`（`:11`–`:18`）
- **encode 失败**：抛普通 `Error`（`:136`），**不是** `AppError`；若真的触发会落到 500。它是「不可信输入不得编码」的断言，正常路径不触发

### 4.2 五个游标的逐字段对比

| 维度 | jobs | exports | reviews | revisions | project catalog |
| --- | --- | --- | --- | --- | --- |
| 文件 | `job_cursor.ts:4` | `export_cursor.ts:4` | `review_cursor.ts:4` | `revision_cursor.ts:4` | `project_catalog_cursor.ts:4` |
| `version` | 1 | 1 | 1 | 1 | 1 |
| `scopeCount` | 1 | 1 | 1 | **2** | 1 |
| scope 含义 | `projectId` | `projectId` | `projectId` | `projectId` + `documentId` | **`ownerId`** |
| `numberField` | `createdAtMs` | `createdAtMs` | `createdAtMs` | **`revisionNumber`** | **`updatedAtMs`** |
| `minNumber` | 0 | 0 | 0 | **1** | 0 |
| `idMaxLength` | 128 | 128 | 128 | 128 | 128 |
| `label`（错误消息用） | `"job"` | `"export"` | `"review"` | `"revision"` | `"project catalog"` |
| 线上元组长度 | 4 | 4 | 4 | **5** | 4 |
| 路由 | `job_routes.ts:83`–`:85` | `export_routes.ts:138`–`:140` | `review_routes.ts:114`–`:116` | `revision_routes.ts:49`–`:56` | `project_routes.ts:83`–`:86` |
| 解码时机 | 在 `withStudioErrors` **外** | 同 | 同 | 同 | 同 |

差异只有 4 个维度：`scopeCount`（1 vs 2）、scope 承载对象（project vs **owner**）、排序字段（时间戳 vs 序号）、`minNumber`（0 vs 1）。其余完全一致。

第四个（project catalog）是唯一的**非 project 作用域**：它绑定 owner，因为路由没有 `:projectId` 参数（`project_catalog_cursor.ts:14`–`:17` 注释说明）。

### 4.3 limit

| 参数 | 默认 | 下界 | 上界 | 来源 |
| --- | --- | --- | --- | --- |
| 5 个游标列表的 `limit` | 50 | 1 | 100 | `studio_request_schemas.ts:122`、`:136`、`job_schemas.ts:15`、`export_routes.ts:37`、`review_schemas.ts:15` |
| `search` 的 `limit` | **30** | 1 | 100 | `studio_request_schemas.ts:157` |
| `search` 的 `offset` | 0 | 0 | 10 000 | `studio_request_schemas.ts:158` |

- **校验失败行为**：AJV 层直接 422 `VALIDATION_ERROR`，`field` 为 `"limit"` / `"offset"`。默认值由 AJV `useDefaults` 注入，所以 handler 里 `request.query.limit ?? 50`（如 `job_routes.ts:91`）是**冗余兜底**，永真
- **应用层二次校验**：`pageLimit<T>`（`ports/page_limit.ts:26`–`:32`）做整数 + 区间断言，失败抛 `RangeError`（文案被 5 个端口各自 pin：如 `Export page limit must be an integer from 1 through 100.`）。**RangeError 不在映射表内**，若触发会变 500 `INTERNAL_ERROR`。HTTP 路径上 AJV 已先拦，所以这是纯防御；重建时若保留双层校验，必须把 RangeError 也映射成 422，否则契约里存在一个「理论可 500」的洞
- **五个端口各自的 brand 与区间**：revision 1–100（`ports/document_store.ts:58`–`:67`）、match 1–100（`:101`–`:110`）、export 1–100（`ports/export_store.ts:41`–`:51`）、job 1–100（`ports/job_records.ts:56`–`:66`）、project 1–100（`ports/project_catalog_store.ts:19`–`:29`）、review 1–100（`ports/review_outcome_store.ts:78`–`:88`）。**6 个 brand 的类型与区间完全相同**，只有名义 brand 不同——重建时这是可以合并的第一处

### 4.4 稳定排序键

所有列表**降序**（最新在前），并都采用 `limit + 1` 探测决定 `next_cursor`（`job_store_part.ts:194`–`:206`、`project_store_part.ts:87`–`:98`、`document_store_part.ts:199`–`:213`、`review_store_part.ts:103`–`:118`、`export_records.ts:174`–`:183`）。

| 列表 | 排序键 | 键集比较 | 索引 |
| --- | --- | --- | --- |
| jobs | `created_at DESC, id DESC` | 行值元组 `(created_at, id) < (?, ?)`（`job_page_queries.ts:11`、`:29`） | — |
| exports | `createdAt DESC, id DESC` | 行值元组（`export_page_queries.ts:12`、`:26`） | `idx_exports_project_created_id`（`schema.ts:238`） |
| reviews | `createdAt DESC, id DESC` | 行值元组（`review_page_queries.ts:12`、`:25`） | `idx_reviews_project_created_id`（`schema.ts:189`） |
| projects | `updated_at DESC, id DESC` | 行值元组（`project_page_queries.ts:17`、`:28`） | `idx_projects_owner_updated_id`（`schema.ts:33`） |
| revisions | `revision_number DESC, id DESC` | 展开为 `(rn < ?) OR (rn = ? AND id < ?)`（`revision_page_queries.ts:26`–`:32`、`:35`） | — |
| search | `rank, document_id ASC`（唯一全序） | 不用游标 | `document_search.ts:110`、`:140` |

`next_cursor` 只有 `rows.length > limit` 时才非 null（否则为 null，表示到末页）。这是「先多取一行再丢弃」的标准实现。

**search 是第六个分页面，但不是游标分页**：它用 limit + offset，返回 `total` 与 `next_offset`（`studio_schemas.ts:52`–`:58`）。新契约若统一成 `CursorPage<T>`，search 必须保留 offset 语义或迁移成 rank-based 游标——这是一个明确的迁移工作量，不能靠「加个 `next_cursor`」蒙过去。

---

## 5. 响应组合子

`studio/interface/http/route_responses.ts`。

| 组合子 | 覆盖状态码 | 定义 |
| --- | --- | --- |
| `READ_ERROR_RESPONSE_BASE` | 401、404、503 | `route_responses.ts:19`–`:23` |
| `WRITE_ERROR_RESPONSE_BASE` | 401、403、404、503 | `:26`–`:29`（在 READ 基础上加 403） |
| `authedReadResponses(extra)` | 上述 + `extra` | `:36`–`:38` |
| `authedWriteResponses(extra)` | 上述 + `extra` | `:46`–`:48` |

语义：401 = guard 失败；404 = 域内父资源缺失或跨 project；403 = CSRF 双提交拒绝（**仅写**）；503 = store 不可用。`extra` 由路由声明，并可**覆盖**同名状态码（如 `422: structureCapacity422ResponseSchema` 覆盖基线的通用信封）——合并是浅展开 `{...base, ...extra}`。

使用面：约 40 处（`volume_routes.ts:55`、`document_crud_routes.ts:40`、`proposal_routes.ts:52`、`beat_routes.ts:48`、`lore_routes.ts:33`、`writing_stats_routes.ts:126` 等）。

**不能复用的例外，及原因**：

| 路由 | 原因 | 位置 |
| --- | --- | --- |
| `GET /api/projects` | 非 project 作用域，基线 404 永不可能发生；若复用会凭空声明一个不可能的响应 | `project_routes.ts:63`–`:78`（注释 `:70`–`:72`） |
| `POST /api/projects` | 创建父资源，同样没有 404；内联 401/403/422/503 + 201 | `project_routes.ts:125`–`:139`（注释 `:131`–`:132`） |
| `GET /api/projects/:id/exports/:exportId/download` | 二进制 `produces`，错误必须包成 JSON 信封否则 content-type 冲突；用自己的 `exportJsonErrorResponseSchema` | `export_routes.ts:170`–`:178`、`export_capacity_schemas.ts:46` |
| `/api/setup`、`/api/session*` | 首触点面，无 404 语义，另有 429 | `auth_routes.ts:127`–`:267` |
| `GET /api/providers` | owner-only + 403，无 project 作用域 | `provider_routes.ts:57`–`:70` |
| `GET /health/*` | 明确**不**走统一信封，503 返回 `{status, reason}` 裸对象 | `health_routes.ts:116`–`:133` |

health 是唯一公开的、刻意违反信封的接口（供编排系统探针消费）。重建时要么保留这条例外并写进契约，要么改成信封并同步改探针——不能默认忘掉。

---

## 6. 新契约的设计输入

### 6.1 `contracts/errors.ts`

```ts
// 已落地于 contracts/errors.ts —— 下面是现行形状，不是提议
export type RetryPolicy = "yes" | "after-delay" | "no";
export type Remedy = "reauth" | "fix-request" | "reread" | "configure" | "none";

export const ERROR_CATALOG = {
  UNAUTHORIZED:        { status: 401, defaultMessage: "Owner session required.", retry: "no",          remedy: "reauth" },
  OPERATION_IN_FLIGHT: { status: 409, defaultMessage: "An identical operation is already running.", retry: "after-delay", remedy: "none" },
  RATE_LIMIT_EXCEEDED: { status: 429, defaultMessage: "Too many attempts…", retry: "after-delay", remedy: "none" },
  // ... 其余 19 条
} as const satisfies Record<string, ErrorDefinition>;

// 帧内码独立成表，不共享 status
export const FRAME_ERROR_CODES = { PROVIDER_FAILED: { … } } as const;
```

两张表 + 两个枚举。`retry` 与 `remedy` 拆开是**必须**的：`retry` 只回答「原样重放会不会成功」（因此 22 条里 **0 条 `"yes"`、3 条 `"after-delay"`、19 条 `"no"`**；三处 `after-delay` 在 `contracts/errors.ts:96`、`:174`、`:180`。注意这是**策略列**的计数，与「响应有没有 `Retry-After`」是两列——`OPERATION_IN_FLIGHT` 策略上是 `after-delay`，但 4/6 的抛出点给不出秒数，见 §6.4 第 6 条），`remedy` 回答「该改什么」（重登 / 改请求 / 重读 / 配 provider / 无）。若合成一个 `retryable: boolean`，`UNAUTHORIZED`（重新登录）、`CSRF_TOKEN_*`（回显或重登）、`VALIDATION_ERROR`（改字段）都会被误标成「可重试」，客户端照做只会拿到完全相同的失败。

**`Retry-After` 不能声明在码上，只能由抛出点携带**——这是本契约最容易做错的一处。`OPERATION_IN_FLIGHT` 有 6 个构造点，只有 2 个（keyed retry 的 `job_history_service.ts:233`、`job_store_part.ts:289`）知道该等 1 秒；准入路径 4 个给不出值。所以：

| 层次 | 声明什么 | 例 |
| --- | --- | --- |
| 码级（目录） | `retry` 的**类别**：能否原样重放、是否需要先等 | `OPERATION_IN_FLIGHT → "after-delay"` |
| 抛出点级（`AppError`） | 具体**秒数**，经 `retryAfterSeconds` 携带（`platform/http/error_envelope.ts:27`、`:114`–`:115`） | keyed retry 传 `1`；准入路径不传 → 无头 |

两者必须并存。只做码级 → `"after-delay"` 变成无值的承诺（客户端瞎猜延迟）；只做抛出点级 → 客户端没法在收到 409 时预判「该等还是该改」。**并且约束是双向的**：「不要在码上声明头」只是禁令，还必须配一条正向规则——**一个码的每个抛出点都必须能回答「等多久」；答不出的抛出点不该走 `after-delay`，而应改用 `retry: "no"` 或让该路径换一个语义更准的码**。否则读者只知道不能加字段，不知道「同一码有时要等、有时不用等」该怎么表达。**不要**再加 `retryAfterHeader?: boolean` 这类码级开关（早期骨架有、现已删除，全仓 0 命中）：它既表达不了 4/6 场景的无值，又会让实现者以为「声明了就会发」。

另外 2 个字段建议纳入契约但旧代码里是隐式的：
- `detailsShape?: "none" | "validation" | "capacity" | "revision" | "in-flight" | "capacity-503" | "internal"`：把 §2.4 那张表变成类型
- `idempotentReplay?: boolean`：该错误是否发生在幂等重放路径上（见 §2.6）；决定客户端能否安全重投同一 `idempotency-key`

`message` 已由类型系统解决：8 个需插值的码走 `ErrorCodeRequiringMessage`，`AppError` 的构造函数重载强制传值（`error_envelope.ts:58`–`:61`），漏传是编译错误。详见 §6.4 第 8 条（已关闭）。

### 6.2 统一分页协议

```ts
export interface CursorPage<T> {
  readonly items: readonly T[];
  readonly nextCursor: string | null;
}

export interface CursorCodec<Scope extends readonly unknown[], Key extends string> {
  encode(scope: Scope, position: { readonly [K in Key]: number } & { readonly id: string } | null): string | null;
  decode(token: string, scope: Scope): { readonly [K in Key]: number } & { readonly id: string };
}
```

`encode`/`decode` 的实现直接沿用 `canonical_cursor.ts` 的四个不变量，**一个字节都不要改**：base64url 无 padding、严格 UTF-8、重编码自校验、1–1024 字符 + `^[A-Za-z0-9_-]+$`。这四点已经在生产里被宽严两端的输入打磨过，重写等于重新引入 padding/非规范 JSON 的绕过面。

wire 保持 `[version, ...scopes, key, id]` 的位置元组（不用对象），理由：长度稳定、scope 顺序天然可校验、`minNumber` 校验位置固定。若改成 `{v, s, k, i}` 对象，会多出一个「字段缺失 vs 字段为 null」的歧义面。

### 6.3 合并 5 个游标为 1 个时必须保留的语义

不能为了「一个 codec」而丢掉的 5 件事：

1. **排序键的可变性（最关键）**。`revisionNumber` 是每 document 单调递增、**永不变化**的序号；`createdAtMs` 是插入时间，**不可变但非唯一**（同毫秒批量插入很常见）；`updatedAtMs` 是 `projects` 的**可变**排序键——分页过程中任何项目被更新，它在全序中的位置就变了，keyset 会漏项或重项。统一 codec 若不把这个差异暴露到类型上，调用方会把 `updatedAt` 当成稳定键，从而产出「翻页时项目消失」的静默错误。旧代码用 `(updated_at, id)` 行值比较只是让边界确定，并不消除漂移。这一条必须在契约层显式标注 `sortKeyMutability: "immutable" | "mutable"`，并在 projects 列表上接受漂移、或改成 `created_at` 排序。
2. **scope 的个数与承载对象**。1 个 scope 绑 projectId、1 个绑 ownerId、2 个绑 projectId+documentId。合并后必须支持变长 scope 且**校验顺序**，否则跨 project 的 revision 游标可以被拿去解另一个 document（越权探测面）。
3. **`minNumber` 的域**。时间戳允许 0（epoch），`revisionNumber` 允许 1（1-based）。统一成 `minNumber: 0` 会让 `revisionNumber = 0` 的伪造游标通过，查询退化成全表首行。
4. **`version` 的独立演化**。5 个游标今天都是 `version: 1`，但它们各自演化。合并成一个 codec 后必须保留「按资源分 version」的能力，否则任一资源的 wire 变更会强制其它 4 个一起 bump，已发出的游标全部失效。
5. **label 只影响错误消息**。`Cannot encode an invalid ${label} cursor position.`（`canonical_cursor.ts:136`）是唯一的 500 级诊断线索。合并时若丢 label，线上定位 encode 失败会失去「哪个资源」的信息。

次要但值得保留的：decode 在 `withStudioErrors` 之外执行（5 个路由一致），意味着游标失败**永远**是 422 而不会被域映射改写；以及 `next_cursor` 的 `null` 表示末页，不是 `""`。

### 6.4 与已落地骨架的对齐检查

仓库里已有重建骨架：`server/src/contracts/errors.ts`、`server/src/platform/http/error_envelope.ts`、`server/src/platform/http/pagination.ts`、`server/tests/rebuild/pagination.test.ts`。

**未决计数（截至本轮核对）：原 8 项全部关闭（#1–#6、#8、#9 逐条验证通过）；#7 部分关闭——7a（注释与实现矛盾）已修，7b 已登记为 `docs/rebuild/unchecked.md` 第 1 条、状态 **accepted（延后）**：本次重建不新增专门测试，反向**四分支**由 generation 切片的 INV-40 验收承接。**

| # | 位置 | 现象 | 与旧契约的差异 | 建议 |
| --- | --- | --- | --- | --- |
| 1 **（已关闭）** | `pagination.ts:83`–`:93`（throw `:87`–`:90`） | 原问题：`normalizeLimit` **夹取**越界值（`0→1`、`10000→100`、`25.9→25`），与「非法输入必须 422」冲突 | — | **已改**：非整数或越界即 `throw invalid("limit", …)` → 422 `VALIDATION_ERROR`；不再夹取。注释写明 `Clamp-free limit normalization: an out-of-range limit is a client bug` |
| 2 **（已关闭）** | `pagination.ts:153`–`:160` | 原问题：游标 `key` 是无条件 string，无 `Number.isSafeInteger`、无 `minKey` 域、无 `idMaxLength` | — | **已改**：`key` 必须 `number` + 安全整数 + `>= minKey`；`id` 必须非空且 `<= maxIdLength`（默认 128）。模块头注释 `:15`–`:17` 说明「never a string：SQL 列是整数，SQLite 按存储类比较」——正是原风险点 |
| 3 **（已关闭）** | `pagination.ts:138`–`:152`（另有 `:49`、`:57`、`:99`） | 原问题：游标不含 scope 也不含 version，跨 scope 复用会静默返回错位一页 | — | **已改**：wire 为 `[version, ...scope, key, id]`（`:107`），decode 逐项校验元组长度、version 相等、scope 顺序相等。**另超出原建议**：导出 `SortKeyMutability`（`:49`）并接入 codec（`:57`、`:99`），把「可变排序键会漂移」从注释升级为类型契约 |
| 4 **（已关闭）** | `pagination.ts:113`–`:128` | 原问题：无长度上限、无字符集白名单、无规范重编码校验（超长游标先全量解码再拒绝） | — | **已改**：1–1024 字符（`:113`）、`^[A-Za-z0-9_-]+$`（`:116`）都在 `Buffer.from` **之前**；随后要求「重编码等于原 token」（`:126`）。无界工作量与 base64 多拼写绕过面同时消除 |
| 5 **（已关闭）** | `pagination.ts:76`–`:81`、`:111`–`:162` | 原问题：`InvalidCursorError` 是普通 `Error`，调用点漏 catch 即 500 | — | **已改**：`InvalidCursorError` 已删除，`decode` 全部经 `invalid()` 工厂直接抛 `AppError("VALIDATION_ERROR")`，未 catch 也是 422 |
| 6 **（已关闭）** | `contracts/errors.ts:171`–`:176` | `OPERATION_IN_FLIGHT.retry = "after-delay"`，但响应通常**没有** `Retry-After` | 该文件把 `"after-delay"` 定义为「必须等 `retryAfter` 再重试」。而 6 个构造点里只有 2 个能给出 1 秒（`job_history_service.ts:233`、`job_store_part.ts:289`），准入路径（`operation_in_flight.ts:66/82/123/130`）给不出值 → 头不发。`"after-delay"` 在 4/6 的场景里是**无值的承诺** | 语义本身没错，文件头 `:22`–`:27` 已写明「头按抛出点、无头则由调用方退回自己的 backoff」。但这条规则**必须同步进面向 agent 的文档**，否则会被写成「409 一定带 Retry-After」。另建议加测试钉住「重试路径 = 1、准入路径 = 无头」。**现状态**：`retryAfterHeader` 与 `sendsRetryAfter` 已从契约删除（全仓 0 命中），并新增 `AppError.afterDelay(code, seconds, options)`（`platform/http/error_envelope.ts:57`–`:63`）——「知道延迟的抛出点」不再需要手写字段，该风险基本消解 |
| 7 **（部分关闭）** | `error_envelope.ts:29`–`:38`、`:114`–`:115` | 原问题：注释写「on 429/503」，实现不判状态 | 已一致；且「删掉 `retryAfterSeconds !== undefined` 判断」会被 `job_retry_idempotency_contract.test.ts:97`（409 + `1`）抓红 | **7a 已关**。**7b 未关，且是跨域缺口**：`retry-after` 只有正向断言，反向**零覆盖**（`grep -rn 'retry-after' server/tests` 与 `not\|undefined\|toBeNull` 交叉命中 = 0）。若有人把等待提示「统一」到所有错误上，`REVISION_CONFLICT` / `DOCUMENT_CONFLICT` / `SNAPSHOT_CONFLICT` 会开始劝客户端重试——而冲突正是重试必然再失败的一类——**且没有任何测试会红**。重建时补一条「非重试类 409/422 响应不含 `retry-after`」即可关闭；同款缺口亦见 `manuscript-domain.md` §3.3。若长期不补，按 `accepted-risk` 记账——**症状是准入 409 多一个等待头，客户端多等 N 秒后重试、仍会失败，只增延迟不增错误类型**，所以可接受但应记录 |
| 8 **（已关闭）** | `contracts/errors.ts:210`–`:221`、`platform/http/error_envelope.ts:55`–`:59` | 原风险：`defaultMessage` 是通用短句且 `message` 可选 → 漏传即静默丢掉资源 id，类型系统不报错 | 现状态：8 个需插值的码被 `ErrorCodeRequiringMessage` 收进必填组，其余 14 个走 `ErrorCodeWithDefaultMessage`；`AppError` 用**构造函数重载**强制——漏传 message 是编译错误，不是运行期降级 | 无需再改。若要更保守，可加一条 lint：禁止对必填组传 `message: ERROR_CATALOG[...].defaultMessage`（等价于没传）。`REVISION_CONFLICT` 不需进必填组，其可操作信息在 `details.current_revision_id` |
| 9 **（已关闭）** | `pagination.ts:71`–`:81` vs `error_envelope.ts:128`–`:133`、`:161` | 原风险：`VALIDATION_ERROR` 有两种形状——AJV 走固定句 + `details.errors[]`，分页走自定义 message + 扁平 `details` 或**无 details** | 旧实现三种来源（游标 / PATCH 原始键 / 裸 body）形状统一，`error-codes.md:34` 才敢教 agent「按 `details.errors` 改」 | **已改**：`invalid(field, message)` 现在产出 `message: "Request validation failed."` + `details: { errors: [{ field, message, type: "invalid" }] }`（`:76`–`:81`），与 AJV 路径同构。注释 `:71`–`:75` 明确写下理由：「an agent told to 'read details.errors' must not hit a second layout here」 |

**文案变更范围需要更正**（早前版本的说法已过期）：`defaultMessage` 与旧 wire 原文**相同**的是 `EXPORT_CAPACITY_EXCEEDED`（`Export capacity exceeded.`）、`GENERATION_CAPACITY_EXCEEDED`（`Generation capacity exceeded.`）、`VALIDATION_ERROR`、`INTERNAL_ERROR`、`UNAUTHORIZED`；**变了**的是 `IMPORT_`（去掉 `Legacy`）、`STRUCTURE_`（去掉 `Authoring`），以及全部 8 条原本靠插值的码（`NOT_FOUND`、`FORBIDDEN`、`INVALID_OPERATION`、`PROVIDER_NOT_CONFIGURED`、`VOLUME_CONFLICT`、`DOCUMENT_CONFLICT`、`OPERATION_IN_FLIGHT`、`SERVICE_UNAVAILABLE`）与 `RATE_LIMIT_EXCEEDED`、`REVISION_CONFLICT`、`SNAPSHOT_CONFLICT`、`OPERATION_CAPACITY_EXCEEDED`。

其中 `SNAPSHOT_CONFLICT` 曾出现三份文档三种写法，现已被修正并由 v1 门禁锁住：`defaultMessage: "The snapshot is referenced by a review or an export."`、`retry: "no"`、`remedy: "none"`（`contracts/errors.ts:159`–`:164`；文档侧 `docs/agents/error-codes-v1.md:71`）。本文件 §1 第 17 行写的是**旧** wire 原文（`"Document is referenced by an immutable snapshot."`），作为历史事实保留、不是新值。

骨架做对且应保留：`AppError` 不再自带 `statusCode`、从目录派生（`error_envelope.ts:44`–`:46`），消灭了 §3.3 列出的 21 处字面量漂移；`buildPageInfo` 的 `limit+1` 探测与旧实现一致（`pagination.ts:167`–`:171` 对应 `job_store_part.ts:203`）。仍缺两处：`InvalidOperationError` 的全局兜底分支（旧 `error_envelope.ts:163`–`:166`，现只靠调用点包 `withStudioErrors`）；health 探针刻意不走信封（`health_routes.ts:116`–`:133`）。

**契约表达力的边界（⚠ 无机器校验）**：下列**三**件事行为已正确、但当前没有任何门禁或测试能拦住回退（v1 门禁已覆盖其余项，见 §6.5）：

- **`Retry-After` 不该出现的场合**：反向零覆盖（=7b，`unchecked.md` 第 1 条，accepted 延后）→ 补**四分支**：非重试类 409、容量 422、`SERVICE_UNAVAILABLE` 503 不含该头；外加「带延迟机制但未传值的 409」——它不是「不该带」，而是**同一个码有时带有时不带**（别按码推断）。
- **`defaultMessage` 是否仍等于旧 wire 原文**：`checkFingerprint` 只能发现「冻结后又被改动」，无法判断「新文案是否等于旧文案」——该等价性只能人工比对本表。
- **`message` 必填组的抛出点不得从 catalog 取串**：类型只看「传没传」，不看「传了什么」→ lint 禁止 `ERROR_CATALOG[...]`（spec-manuscript 的收紧版：取串即说明该抛出点不知道要报告哪个 id）。

按检查类型可分两类，区别在**维护成本**而非重要性：**第 2 条是「对应类」**——断言两处必须一致，需随两侧演进，应尽量改写成派生校验，否则对照表本身就是第二份真相；**第 1、3 条是「缺席类」**——「不存在」是稳定命题，写成即几乎无需维护，应优先自动化。一句话：**凡「值」都有类型保护，凡「值的来源与场合」都只有测试能保护**。

### 6.5 门禁

**已实现，不是待办。** 新契约有独立门禁 `server/scripts/qa/check_error_codes_v1.mjs`（`package.json:31` 的 `gate:error-codes-v1`，并列于 `:30` 的 `gates` 聚合）。实测输出 `[error-codes-v1] clean: 22 codes match across server/src/contracts/errors.ts and docs/agents/error-codes-v1.md`。

它由**四个函数**覆盖**五类检查**（`compare` 一行同时管码集合与四列，故函数数比检查面少一），且实现方式比「公式化清单」更硬：

| 检查 | 实现 | 关键设计 |
| --- | --- | --- |
| 码集合 + 四列（status / retry / remedy / 文案）逐条一致 | `compare`（`:116`） | 双向比对，两侧任一多一条都报 |
| 文案指纹 | `checkFingerprint`（`:272`） | 冻结基线；只能发现「冻结后又改」，不能判断「是否等于旧 wire」 |
| 帧内码与 HTTP 码键集互不相交 | `checkChannelDisjoint`（`:222`） | 挡「把 `PROVIDER_FAILED` 挪进 `ERROR_CATALOG`」 |
| 必填 message 码集合 == `ErrorCodeRequiringMessage` 键集 | `checkRequiredSet`（`:169`） | **取数源是类型、不是文档**（`:157` 注释：否则会退化成文档自我背书）；双向报错并区分方向（漏声明→加进文档；多声明→从文档删）；另有数量自比（`:199`–`:202`） |

实测有效性：从文档删掉 `VOLUME_CONFLICT` 会同时触发两条（数量 7≠8、漏声明 `VOLUME_CONFLICT`），说明「数量单独比对」那一层真的在生效，不是设计意图。

**仍需注意的两件事**：

1. **旧门禁尚未退役**。`package.json:26` 的 `gate:error-codes` 仍跑 `check_error_codes.mjs`，其 `:17`–`:19` 硬编码三个旧来源（`docs/agents/error-codes.md`、`shared/domain/error_codes.ts`、`shared/interface/http/error_envelope.ts`）。这在**旧代码仍存在时是正确的**——旧文档必须继续与旧代码同步；但它必须与 `docs/agents/error-codes.md` 和 `shared/domain/error_codes.ts` **同批退役**：先删旧代码会留僵尸门禁（fail-closed 后有人为了让 CI 绿而删门禁），先删门禁会留无人校验的旧文档，两条路都比现状糟。另注意**命名在起反作用**——`error-codes-v1.md` 的 `-v1` 后缀天然读作「候选稿」，且旧文档开头没有一行指向它；退役时该后缀应一并改为正式名，否则下一个人会继续以旧文档为准。
2. **格式脆弱点**：`CATALOG_ROW` 同款正则要求行首严格为 `` | `CODE` | NNN | ``，`code` 必须反引号包裹、第一列必须是 code、第二列必须是三位状态码。实测当前 `error-codes-v1.md` 命中 22 行、去重 22 个，`details` 表与文案表不会被误吞，**对齐空格不影响**。一旦有人给 code 加粗或调换列序，行数会从 22 掉到 0，脚本报 `contains no catalog table rows` 并 fail-closed。

结论：**契约侧的机器校验已经到位**；§6.4 那三条 ⚠ 是它覆盖不到的残余（两句「不得出现」与一句「是否等价」），加上 7b 的测试缺口。
