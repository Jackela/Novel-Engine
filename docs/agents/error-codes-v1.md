# 错误码（v1）

本表与 `server/src/contracts/errors.ts` 一一对应。核对基线：`22c53b8ffc2c`（`sha256` 前 12 位）。契约变更必须与本文档同一次提交。

文案指纹：`52a6eb27181b`

门禁有两项，都过才算通过：

- **四列比对**：22 条的 `code` / `status` / `retry` / `remedy`，连码序一起核对。不符即失败。
- **文案指纹**：即上面单独那一行。语料是 22 条 `CODE|defaultMessage`，按契约文件声明顺序、`\n` 连接、无尾随换行、不做 Unicode 规范化，UTF-8 取 `sha256` 前 12 位。不符即失败。

**判定顺序固定：先 diff 四列，再核指纹。** 四列不符说明契约形状变了，先改表；四列相符而指纹不符，说明只改了文案，此时重读 §5 的对照再更新本节——不重读就会留下一张描述旧文案的表。

指纹只覆盖 `defaultMessage`，不覆盖 `message`（抛出点插值，不可枚举），也不覆盖注释与类型；`status` / `retry` / `remedy` 由四列比对负责，指纹不重复覆盖，否则失败信息会失去定位力。

判定本文是否过期，**比的是值，不是文件字节**。哈希不同只说明文件被动过（加注释、加类型都会改哈希），不代表本表失效；值不符时哈希相同也不能免责。

表中所有条目的 `status`、`defaultMessage`、`retry`、`remedy` 都以该文件为准，本文只做解释，不新增码、不改语义；任何一处不一致，以代码为准并视为本文缺陷。`Retry-After` 头不在契约表内按码声明，它的有无取决于抛出点（见 §1 末尾）。`defaultMessage` 是**兜底句**而非必然输出：有 8 个码的 `message` 由抛出点强制提供（见 §5 第 6 条）。

## 0. 怎么用这份表

**两类码，两种通道。** 错误码不是一个平面清单，而是两条互不重叠的通道：

- **HTTP 信封码**（22 条，§1）：失败发生在响应提交之前，服务端能给出非 200 的 `status`，body 是 `{error:{...}}` 信封。`status` 是必有的。
- **SSE 帧码**（1 条，§2）：失败发生在响应提交之后。此时 HTTP 状态已经是 `200`、`content-type: text/event-stream`、响应头已上线，服务端无法再改状态，只能往流里推一个 `{type:"error"}` 帧。这类码**没有** `status`，也不出现在 `ERROR_CATALOG` 里，它在 `FRAME_ERROR_CODES` 中。

判断入口因此是两个：拿到状态码 → 查 §1；流已经建立、正在收 `delta` 帧 → 查 §2。不要把帧码当 HTTP 码匹配，也不要用 HTTP 状态判断流内失败。

**`retry` 回答「原样重试能否成功」，三个值：**

| 值 | 含义 |
| --- | --- |
| `yes` | 同一请求可以立即重放，不做任何修改。当前 22 条里没有码取此值，它是表结构的一部分，留给未来的纯瞬时故障。 |
| `after-delay` | 必须等一段延迟再重放：有 `Retry-After` 就按它，没有就用自身退避。立即重放只会重复命中。 |
| `no` | 原样重放必然再次失败。必须先改变某个东西，而「改变什么」由 `remedy` 指路。 |

**`remedy` 回答「要改什么」，五个值：**

| 值 | 含义 |
| --- | --- |
| `reauth` | 重建身份凭据：重新登录、换用 Owner 身份、刷新 CSRF 配对。 |
| `fix-request` | 改请求本身：修字段、补 header、缩小输入、换标题。 |
| `reread` | 改请求所依据的状态：重新读取资源，用新的版本标识重建请求。 |
| `configure` | 改服务端配置：装 provider 凭据、补 data directory，通常需要重启。 |
| `none` | 没有可改的东西。要么等（配合 `after-delay`），要么就此停下。 |

**两者不是一回事，不要合并。** `retry: "no"` 不代表「没有出路」，只代表「这个请求重发没用」。`UNAUTHORIZED` 是 `no` + `reauth`：重新登录后发出的**是另一个请求**（带新 cookie），不是原请求的重放。`VALIDATION_ERROR` 是 `no` + `fix-request`：改完字段后发出的也是另一个请求。把这两种情况读成「可重试」正是客户端在 401 上打出热循环的原因。

## 1. HTTP 错误码（22 条）

顺序与 `ERROR_CATALOG` 一致。

| code | status | retry | remedy | 触发条件 | 客户端该做什么 |
| --- | --- | --- | --- | --- | --- |
| `UNAUTHORIZED` | 401 | `no` | `reauth` | 请求缺 session cookie，或 cookie 已过期 / 不可解析，guard 解析出的 principal 为 `null`。 | 重新登录取新 session，带上 cookie jar 再发新请求。 |
| `FORBIDDEN` | 403 | `no` | `reauth` | 已认证但身份不允许：非 Owner 访问 Owner-only 面（provider catalog、legacy import），或 `POST /api/setup` 的 `Origin` / `Referer` 非同源。 | 换用 Owner 身份，或改用同源 / 无 `Origin` 的对端发起。 |
| `SETUP_TOKEN_INVALID` | 403 | `no` | `fix-request` | `POST /api/setup` 来自非 loopback 对端，且 `x-setup-token` 缺失或与一次性 token 不等；缺失、畸形、不匹配三者不可区分。 | 从 `first-start setup token` 日志行或 `.setup-token` 文件取 token，补 header 后重发。 |
| `CSRF_TOKEN_MISSING` | 403 | `no` | `reauth` | 写方法（POST/PUT/PATCH/DELETE）且路径不在首触点豁免集内，CSRF cookie 与 `x-csrf-token` 头之一为空。 | 把 `novel_engine_csrf` cookie 的值回显到 `x-csrf-token` 头。 |
| `CSRF_TOKEN_INVALID` | 403 | `no` | `reauth` | 两个 token 都存在但值不相等（配对过期，或 cookie 与 header 来自不同会话）。 | 重新登录取一对新 token，再发写请求。 |
| `RATE_LIMIT_EXCEEDED` | 429 | `after-delay` | `none` | 首触点路径（`/api/setup`、`/api/session/login`）按 `ip:method:path` 计数超出窗口配额。 | 等 `Retry-After` 秒，只重发一次。 |
| `NOT_FOUND` | 404 | `no` | `none` | 资源在寻址范围内不存在，或存在于另一个 project（两者刻意不可区分）；未知路由也归此码。 | 核对 id 与 project 路径，停止换 id 试探。 |
| `INVALID_OPERATION` | 422 | `no` | `reread` | 格式合法但域拒绝：前置条件未满足（导出无章节、接受未完成的提案）、取值非法、作业状态不可重试、登录凭据错误。 | 读 message 定位被拒的前置条件，重读资源状态后重建请求。 |
| `PROVIDER_NOT_CONFIGURED` | 422 | `no` | `configure` | 所选生成 provider 在服务端无可用凭据（dashscope 缺 `DASHSCOPE_API_KEY`、openai_compatible 缺 `LLM_API_KEY`）；不会回退 mock。 | 在服务端环境补上缺的 key 并重启，或把项目切到 `mock`。 |
| `EXPORT_CAPACITY_EXCEEDED` | 422 | `no` | `fix-request` | 一次全新导出超过固定预算：源文档数、源字节、产物字节三者之一越界。 | 缩减导出来源或项目规模到 `details.limit` 以下。 |
| `GENERATION_CAPACITY_EXCEEDED` | 422 | `no` | `fix-request` | 完整 provider prompt 超过 8 MiB UTF-8 预算，或 lore 抽取片段超过码点预算。 | 裁掉稿件或参考上下文后，用新幂等键重发。 |
| `IMPORT_CAPACITY_EXCEEDED` | 422 | `no` | `fix-request` | legacy workspace 超过固定 inspection 预算：story / chapter / 总字节、章节数、目录项数。 | 拆分或精简待导入的 workspace 后再导入。 |
| `STRUCTURE_CAPACITY_EXCEEDED` | 422 | `no` | `fix-request` | 受门控的结构写入将越过固定上限：`project_documents` 2500、`project_volumes` 100、`volume_chapters` 2000、`project_settings_bytes` 16384、`document_metadata_bytes` 16384、`outline_beats` 5000。 | 先删结构或缩小 settings / metadata / outline，再提交。 |
| `VALIDATION_ERROR` | 422 | `no` | `fix-request` | AJV schema 校验失败、游标解码失败、PATCH 未知键或空对象、路由无 body 契约却带 body、`idempotency-key` 不合规。 | 按 `details.errors` 逐条改字段后重发一次。 |
| `REVISION_CONFLICT` | 409 | `no` | `reread` | 提交的 `base_revision_id` 与文档当前修订不符，本次未写入。`null` 不表示强制覆盖：文档恒有当前修订，必然冲突。 | 用 `details.current_revision_id` 作新 base 重放变更。 |
| `VOLUME_CONFLICT` | 409 | `no` | `fix-request` | 同 project 内已有同名卷，本次创建与既有标题冲突。 | 换一个卷标题；message 会引用冲突的那个标题。 |
| `SNAPSHOT_CONFLICT` | 409 | `no` | `none` | 目标文档仍被某个 review 或 export 快照引用，删除或改写被拒绝。 | 停下：这条是永久引用，先让引用它的 review / export 不存在，重试无意义。 |
| `DOCUMENT_CONFLICT` | 409 | `no` | `fix-request` | 同 `(project, kind, title)` 身份的 document 已存在，与本次写入的身份冲突。 | 换一个标题，或改为更新既有文档。 |
| `OPERATION_IN_FLIGHT` | 409 | `after-delay` | `none` | 同一 pipeline 操作（generation / review / export / retry）已在运行；或项目删除正持有 project 级转换与清理窗口。 | 轮询 `GET /api/projects/{projectId}/jobs`，不要重复提交；`details.operation` 在重试面是 `retry (<jobId>)` 模板串，不要当操作名匹配。 |
| `OPERATION_CAPACITY_EXCEEDED` | 503 | `after-delay` | `none` | 应用级或项目级昂贵工作流配额已满，`details.scope` 指明是哪一级。 | 等 `Retry-After` 秒后刷新作业历史，由 Owner 决定是否再提交。 |
| `SERVICE_UNAVAILABLE` | 503 | `no` | `none` | 持久层未配置（无数据库实例、API-only 启动、缺 data directory），或 diagnostics 面未装配。 | 停下，让运维补配置并重启，同一个实例上重试无意义。 |
| `INTERNAL_ERROR` | 500 | `no` | `none` | 未捕获异常；stack 只进日志，不进响应。 | 取 `details.error_id`（等于 `x-request-id` 头）报缺陷，不要解析 message。 |

**`Retry-After` 不按码声明。** 契约里没有「这个码一定带头」的字段：头的有无由抛出点决定，不由码决定。`RATE_LIMIT_EXCEEDED` 与 `OPERATION_CAPACITY_EXCEEDED` 的抛出点知道具体秒数，所以带值；`OPERATION_IN_FLIGHT` 有六个构造点，只有重试面那两处知道是 1 秒，生成 / 评审 / 导出 / 提案的准入 409 不知道，因而不带。统一读法只有一种：**头在就按值等，头不在就用自己的退避**（对 409 取 1 秒轮询作业状态）。把「必有 hint」写成断言，会在准入 409 上永久卡住；反过来假定「一定没有」，会丢掉重试面已经给出并测过的 1 秒提示。

这属于**无法声明**，不是本文漏写：没有任何一处契约值可供比对，所以也不存在「本文声明与代码不符」这种缺陷。要把它做成可校验的，得先在实现对每个抛出点定下口径（哪些该带、哪些不该带），再谈声明。

## 2. SSE 帧错误码（1 条）

| code | retry | remedy | 触发条件 |
| --- | --- | --- | --- |
| `PROVIDER_FAILED` | `no` | `reread` | 流已经以 `200` 建立并开始推送后，provider 在生成中途失败（上游报错、连接中断、流被截断）。 |

处理方式：

1. **保留已收到的文本。** 已经落地的 `delta` 帧是有效内容，连接异常不使它们失效；丢弃它们等于重付一次生成成本。
2. **不要重放同一个请求。** 帧码的 `retry` 是 `no`：原样重发会打到同一个失败的 provider。`remedy` 是 `reread`——重新读取文档与上下文，必要时换一个 provider 再发起新的流。
3. **区分阶段。** 首帧之前的失败走普通信封，按性质分三种：provider 无可用凭据 → `PROVIDER_NOT_CONFIGURED`（422，`configure`）；provider 不具备流式生成能力 → `INVALID_OPERATION`（422，message 指名该 provider，`reread`）；其余 provider 运行期失败 → `INTERNAL_ERROR`（500，只给 `error_id`，不转述上游文案与状态码）。首帧之后状态码已锁定 200，失败一律以本帧码出现——收到 `{type:"error"}` 就不要再去找状态码。

   注意这三种不是「按 provider 分类」，而是「按失败发生的时点与性质分类」：前两种根本不会开始生成，所以永远不会出现 `delta` 帧；第三种已经尝试调用、失败于首帧之前。

**上游故障不映射为任何信封码。** provider 的 HTTP 5xx、超时、连接中断、坏 JSON 都不会变成 `ERROR_CATALOG` 里的条目——表里没有代表上游故障的码，这是设计而非遗漏。它们本身只有三种可见形态：首帧之前是 `INTERNAL_ERROR`（500），首帧之后是 `PROVIDER_FAILED` 帧或一条 `status: "failed"` 的作业记录。因此不要写「上游 429 时客户端会收到 429」——上游的状态码从不进入我们的状态位；客户端主动断流属于取消，不是失败，不产生任何码。

**`PROPOSAL_STREAM_DRAIN_TIMEOUT` 不是契约码。** 它只用于 `destroy` 响应路径，客户端既收不到帧也收不到信封，属于日志与诊断信号。本表不收录，也不要为它写客户端分支。

## 3. 信封形状

**成功响应是裸对象，没有 `{data: ...}` 包装。** 单资源直接返回该资源；列表返回具名字段数组加游标，例如 `{ projects: [...], next_cursor: string | null }`、`{ jobs, next_cursor }`。`204` 的 body 为 `null`。是否成功只看状态码，不要去找 `data` 键。

**失败响应只有一种形状：**

```json
{ "error": { "code": "STABLE_CODE", "message": "human-readable", "details": {} } }
```

`code` 与 `message` 恒有；`details` 只在有值时才出现，没有该键即表示无附加信息。信封是封闭对象，除这三个键外没有别的字段——请求关联 id 不在信封顶层，它只以 `details.error_id` 的形式出现在 `INTERNAL_ERROR` 上。

按状态看 `details` 的可能字段：

| status | code | `details` 字段 |
| --- | --- | --- |
| 404 | `NOT_FOUND` | 无。资源类型与 id 只写在 message 里。 |
| 409 | `REVISION_CONFLICT` | `current_revision_id: string \| null`，必填键、恒存在（值可为 `null`）。 |
| 409 | `VOLUME_CONFLICT` / `SNAPSHOT_CONFLICT` / `DOCUMENT_CONFLICT` | 无。 |
| 409 | `OPERATION_IN_FLIGHT` | `project_id: string`、`document_id: string \| null`、`operation: string`。重试面的 `operation` 是 `retry (<原 jobId>)` 模板串而非操作名，且那里 `document_id` 恒为 `null`；不要拿 `operation` 当枚举匹配。 |
| 422 | `VALIDATION_ERROR` | `errors: [{ field: string, message: string, type: string }]`；游标失败固定为 `field: "cursor"`。 |
| 422 | `INVALID_OPERATION` / `PROVIDER_NOT_CONFIGURED` | 无。缺的凭据名、被拒的前置条件只写在 message 里。 |
| 422 | 四个 `*_CAPACITY_EXCEEDED` | `resource`、`limit`、`observed`；`observed` 饱和到 `limit + 1`。 |
| 429 | `RATE_LIMIT_EXCEEDED` | `retry_after_seconds`，与 `Retry-After` 头同值。 |
| 503 | `OPERATION_CAPACITY_EXCEEDED` | `scope: "project" \| "application"`、`limit`、`in_flight`、`project_id`、`retry_after_seconds`，同时发 `Retry-After`。 |
| 503 | `SERVICE_UNAVAILABLE` | 无，且不发 `Retry-After`。 |

同一个 `503` 下两种码语义相反：`OPERATION_CAPACITY_EXCEEDED` 是可等的容量问题，`SERVICE_UNAVAILABLE` 是配置缺失、等不来。判别依据是码本身与 `Retry-After` 是否出现，不是状态码。

`INTERNAL_ERROR` 同时是「故意不设码」的兜底出口：修订 source 与字数不变量被破坏这类内部损坏不会产生新码，只落成 500 + `error_id`。看到 500 时能做的只有把 `error_id` 交出去。

## 4. 重试决策表

按 `retry × remedy` 组合决定动作。当前表内的实际分布如下。

| retry | remedy | 动作 | 命中的码 |
| --- | --- | --- | --- |
| `after-delay` | `none` | 有 `Retry-After` 就按值等，没有就按 1 s 轮询；然后原样重发。 | `RATE_LIMIT_EXCEEDED`、`OPERATION_IN_FLIGHT`、`OPERATION_CAPACITY_EXCEEDED` |
| `no` | `reauth` | 重新登录或换身份，然后发**新**请求；绝不重发原请求。 | `UNAUTHORIZED`、`FORBIDDEN`、`CSRF_TOKEN_MISSING`、`CSRF_TOKEN_INVALID` |
| `no` | `fix-request` | 改请求本身（字段、header、规模、标题）后重发。 | `SETUP_TOKEN_INVALID`、`VALIDATION_ERROR`、四个 `*_CAPACITY_EXCEEDED`、`DOCUMENT_CONFLICT`、`VOLUME_CONFLICT` |
| `no` | `reread` | 先重新读取资源拿到最新版本，再构造新请求。 | `INVALID_OPERATION`、`REVISION_CONFLICT` |
| `no` | `configure` | 改服务端配置并重启，之后重发。 | `PROVIDER_NOT_CONFIGURED` |
| `no` | `none` | 停止重试：核对寻址、移除外部引用，或上报缺陷。 | `NOT_FOUND`、`SNAPSHOT_CONFLICT`、`SERVICE_UNAVAILABLE`、`INTERNAL_ERROR` |

三条容易踩错的边界：

- `after-delay` 只对**幂等**写成立。没有幂等键的写操作在等待后重投，可能造成第二次执行；先在响应里确认操作未发生，再决定是否重投。
- `no` + `reread` 不是「等一下再重试」。资源没有变化之前，重发必然再拿到同一个 409。
- 任何组合下都不要对 `message` 做字符串匹配来决定分支。文案会变，`code` 不会。

## 5. 相对旧契约的破坏性变更

变化全在文案层：`code` 与 `status` 一律未变，旧客户端的按码分支、按状态分支不受影响。受影响的是把 `defaultMessage` 当成固定字面量去匹配的客户端。

**以下文案为切换后目标值；切换前旧 wire 仍返回旧文案，`code` 与 `status` 两期不变。** 也就是说，本节的每一项都描述「切换后你会看到什么」，而不是「现在线上返回什么」——现阶段按 `code` 分支的客户端无需任何改动，按 message 匹配的客户端则必须在本节列出的每一项落地之前就改掉。

本节是本文唯一依赖 `defaultMessage` 现行值的地方，因此也是唯一会被文案变更单独打穿的地方。维护次序与开头一致：**先 diff 四列，再核文案指纹**；四列相符而指纹变了，改动就在这里，逐条重读本节的旧值/新值对照，而不是去动 §1 的表。

1. **四个 capacity 码的默认文案已改。** 旧 wire 文案与新的 `defaultMessage` 不再逐字相同：

   | code | 旧文案 | 新 `defaultMessage` |
   | --- | --- | --- |
   | `EXPORT_CAPACITY_EXCEEDED` | `Export capacity exceeded.` | `Export capacity exceeded.` |
   | `GENERATION_CAPACITY_EXCEEDED` | `Generation capacity exceeded.` | `Generation capacity exceeded.` |
   | `IMPORT_CAPACITY_EXCEEDED` | `Legacy import capacity exceeded.` | `Import capacity exceeded.` |
   | `STRUCTURE_CAPACITY_EXCEEDED` | `Authoring structure capacity exceeded.` | `Structure capacity exceeded.` |

   `IMPORT_` 与 `STRUCTURE_` 两条的字符串确实变了，`EXPORT_` 与 `GENERATION_` 两条只是从「实现里拼的字面量」升格为「目录里的 `defaultMessage`」。四条都必须当作不可匹配的文本处理。

   同族还有一条：`OPERATION_CAPACITY_EXCEEDED` 的旧 wire 是 `Studio operation capacity is exhausted.`，新 `defaultMessage` 是 `Too many operations are running; retry shortly.`。

2. **`VOLUME_CONFLICT` 的默认文案已改。** 旧 wire 文案是 `A volume titled "<title>" already exists in this project.`，新 `defaultMessage` 是 `A volume with this title already exists.`。语义未变，都是同项目重名；变的是不再把标题插进那句模板里——所以任何按 `A volume titled "` 前缀切字符串取标题的写法都会失效，标题要么从请求里来，要么不用。

3. **`SNAPSHOT_CONFLICT` 的默认文案已改。** 旧 wire 文案是 `Document is referenced by an immutable snapshot.`，新 `defaultMessage` 是 `The snapshot is referenced by a review or an export.`。语义同样未变：文档被引用因而不可删。变的是把「不可变快照」这个笼统说法换成引用方的实际类型，客户端若曾 grep `immutable snapshot` 来识别此码，需改为按 `code` 分支。

4. **`UNAUTHORIZED` 的默认文案已改。** 由 `Authentication is required.` 改为 `Owner session required.`。语义口径随之收紧：这条码只表示缺少 Owner 会话，不表示泛化的「未认证」。

5. **上述文案曾被 pin 成 OpenAPI `enum`。** 旧 schema 把 `message` 锁成单值闭集，因此「改文案」在当时等同于「改 schema」。全仓共 **6 处**，重建时必须全部删除：

   | 位置 | 钉住的文案 |
   | --- | --- |
   | `studio_schemas.ts:233` | `Document is referenced by an immutable snapshot.`（`SNAPSHOT_CONFLICT`） |
   | `studio_schemas.ts:163` | `Studio operation capacity is exhausted.` |
   | `export_capacity_schemas.ts:26` | `Export capacity exceeded.` |
   | `generation_capacity_schemas.ts:57` | `Generation capacity exceeded.` |
   | `structure_capacity_schemas.ts:31` | `Authoring structure capacity exceeded.` |
   | `unprocessable_entity_schemas.ts:50` | `Request validation failed.`（`VALIDATION_ERROR`） |

   复核命令（应输出 6 行）：

   ```sh
   grep -rn "message: {" -A 4 server/src | grep -E "enum: \["
   ```

   注意前两处是 `message: {` 换行后才写 `enum` 的多行写法，用单行 grep 只能抓到 4 处。新契约声明状态、默认文案、重试策略「只在此处」（`contracts/errors.ts:1-4`），响应 schema 里再出现 `message` 的单值 `enum` 即违约。**漏删任何一处，那一类错误在 wire 上就永远是契约改不到的旧文案**；在这些删除落地之前，本节的变更尚不可观测。

   **但这 6 处并非都会变字，验收时不要以「文案没变」判定 pin 没删：**

   | 位置 | 与旧 pin 的字面比较 |
   | --- | --- |
   | `studio_schemas.ts:233` | 改写（`…immutable snapshot.` → `The snapshot is referenced by a review or an export.`） |
   | `studio_schemas.ts:163` | 语气与信息量都变，并新增重试提示 |
   | `structure_capacity_schemas.ts:31` | 去掉 `Authoring` 一词 |
   | `export_capacity_schemas.ts:26` | **逐字相同** |
   | `generation_capacity_schemas.ts:57` | **逐字相同** |
   | `unprocessable_entity_schemas.ts:50` | **逐字相同** |

   后三处删与不删，当前 wire 输出一模一样。删除理由是「文案只能有一个来源」，不是「这六处现在都不同」——凭「响应看起来没变」回滚删除，等于把未来所有的文案修改权重新锁死。

6. **对客户端的统一要求。** 分支只认 `code`，容量类错误的数值只从 `details.resource` / `details.limit` / `details.observed` 取，任何依赖上述旧字符串的判断都要在升级时删掉。**不要把 `message` 当作 §1 表里那句 `defaultMessage` 的复制品。** 契约把 8 个码的 `message` 设为必填（`FORBIDDEN`、`NOT_FOUND`、`INVALID_OPERATION`、`PROVIDER_NOT_CONFIGURED`、`VOLUME_CONFLICT`、`DOCUMENT_CONFLICT`、`OPERATION_IN_FLIGHT`、`SERVICE_UNAVAILABLE`），强制点不在类型别名，而在 `AppError` 的构造重载上（`platform/http/error_envelope.ts:55-59`，`afterDelay` 同构 `:81-90`）：这 8 个码不传 `message` 是编译错误，其余 14 个码走另一个重载、可省略。实现体 `:61` 的 `options.message ?? ERROR_CATALOG[code].defaultMessage` 就是「兜底句」的确切含义。结论：需要细节时读 `message`，需要稳定判定时读 `code`，两者职责不重叠。

   由此可推：`REVISION_CONFLICT` 不在必填组，输出的是通用句，但它并不丢信息——赢家修订在 `details.current_revision_id` 里。这是有意的组合，不要为了「让 message 更有用」把它加进必填组：那只会得到一句需要再解析的自然语言，而 `details` 里的值本来就能直接用。

下面这一行是给门禁读的声明，不是重复叙述：同一组码在上一段按契约声明序列出、在这里按字典序列出，**顺序不同是刻意的**——集合没有顺序，而门禁需要一行可逐字符比对的形式。

必填 message 码（8）：`DOCUMENT_CONFLICT`, `FORBIDDEN`, `INVALID_OPERATION`, `NOT_FOUND`, `OPERATION_IN_FLIGHT`, `PROVIDER_NOT_CONFIGURED`, `SERVICE_UNAVAILABLE`, `VOLUME_CONFLICT`

**保持不变的部分：** 22 个 `code` 与各自的 `status` 一一对应、未增未删；信封形状 `{error:{code,message,details?}}` 未变；`details` 各字段名未变；`Retry-After` 的归属规则未变——仍是按抛出点给，不按码给。

**运输层错误不在本表，且永远不进本表。** 请求在到达 handler 之前就被拒绝时，Fastify 的原生码原样透传，仍用同一信封形状，但集合不受 `ERROR_CATALOG` 约束：413 `FST_ERR_CTP_BODY_TOO_LARGE`（1 MiB 文档体积上限）、415 `FST_ERR_CTP_INVALID_MEDIA_TYPE`、400 `FST_ERR_CTP_INVALID_JSON_BODY`、400 `FST_ERR_CTP_INVALID_CONTENT_LENGTH`。**没有 `PAYLOAD_TOO_LARGE` 这个码**，它只存在于旧文档的笔误里；把 413 归一化成它等于改掉客户端已在匹配的 wire code，契约不允许。
