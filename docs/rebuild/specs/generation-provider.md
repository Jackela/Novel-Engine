# 生成管线与 Provider 行为规格

> 用途：全栈重建时的行为基线。所有结论均来自旧代码，标注 `file:line`。
> 路径前缀约定：`srv/` = `server/src/`。只描述「必须保持的行为」，不描述实现结构。
> 阅读顺序建议：§1（端口）→ §2（三种 provider）→ §3（流式协议）→ §4（提案落地）→ §5（净化）→ §6（上下文）→ §7（审阅）→ §9（脆弱点）。

---

## 0. 边界与词汇

| 词 | 含义 | 证据 |
| --- | --- | --- |
| step | Provider 面向的封闭步骤词汇 | `srv/contexts/ai/application/ports/text_generation.ts:9-14` |
| operation | 前端/HTTP 面向的操作词汇（continue/rewrite/generate） | `srv/contexts/studio/application/proposal_prompts.ts:15-19` |
| proposal | 一次生成产出的整章 markdown，落在 job 上，不改正文 | `srv/contexts/studio/application/proposal_landing.ts:200-233` |
| acceptance | 作者显式接受提案，写入 `ai-accepted` 修订 | `srv/contexts/studio/infrastructure/proposal_acceptance_store_part.ts:21-86` |

封闭词汇表：step 仅 `chapter_draft | chapter_revision | editorial_review | lore_extract`，越界即抛错而不是回显（`text_generation.ts:18-20`，`srv/contexts/ai/infrastructure/providers/provider_json.ts:80-85`）。operation→step 映射只有三条：`continue/rewrite → chapter_revision`，`generate → chapter_draft`（`proposal_prompts.ts:15-19`）。

模型永不来自客户端：`text_generation.ts:22-25` 只允许客户端在 `mock | dashscope | openai_compatible` 中选 provider；模型由服务端解析链决定（`srv/contexts/ai/application/model_resolution.ts:53-62`）。

---

## 1. Provider 端口

### 1.1 接口形状

```
TextGenerationProvider
  generateStructured(task): Promise<TextGenerationResult>              // 必需
  generateStructuredStreaming?(task, options?): AsyncGenerator<string> // 可选能力
  dispose?(): Promise<void>                                            // 可选清理
```

证据：`text_generation.ts:124-155`（143-152 为流式方法，153-154 为 dispose）。

**Task 形状**（`text_generation.ts:78-90`）：`step`、`language?`、`systemPrompt`、`userPrompt`、`responseSchema`、`metadata`。
- `step` 在 port 上是 `string`，实际由 adapter 用 `supportedStep` 收窄（`provider_json.ts:80-85`）。
- `language` 缺省按 `en` 处理，保证旧 task 形状行为不变（`text_generation.ts:80-85`，`srv/contexts/ai/infrastructure/providers/deterministic_task_language.ts:11-13`）。
- `responseSchema` 目前生产代码只用一种：`{ chapter_markdown: { type: "string" } }`（`proposal_landing.ts:92`）；审阅用 `{ findings: [...] }`（`srv/contexts/studio/application/review_service.ts:151-161`）。
- `metadata` 是「顺带塞进 prompt 的自由字段」，见 §6.3。

**Result 形状**（`text_generation.ts:93-101`）：`step`、`provider`、`model`、`rawText`、`content`、`promptTokens`、`completionTokens`。
- `content` 是唯一被应用层读取的字段；`rawText` 明确是诊断/证据字段，应用代码不读（`text_generation.ts:125-140`）。
- 两条不一致必须保留认知：确定性 provider 在章节步骤把**裸 markdown**放进 `rawText`、包装成 `{ chapter_markdown }` 放进 `content`（`srv/contexts/ai/infrastructure/providers/deterministic_story_provider.ts:82-90`）；HTTP provider 把 `content` 再 `JSON.stringify` 进 `rawText`（`srv/contexts/ai/infrastructure/providers/dashscope_provider.ts:139`，`srv/contexts/ai/infrastructure/providers/openai_compatible_provider.ts:185`）。
- `promptTokens`/`completionTokens`：`null` 表示「provider 没给证据」，且必须是安全非负整数才算数（`text_generation.ts:41-44`，`srv/contexts/ai/infrastructure/providers/provider_http.ts:30-32`）。

**Stream 契约**（`text_generation.ts:110-122`）：`signal` 中止上游；已 yield 的 delta 仍有效；`onOutcome` **恰好一次**、仅在成功后调用，携带 model 与末帧 usage；abort/failure 后永不调用。

### 1.2 生命周期：每请求一实例

- 工厂签名 `(provider) => TextGenerationProvider`，注释明确「一次请求构造一个」（`text_generation.ts:157-161`）。
- 组合根注入工厂，provider 不在 import 期构造：`srv/contexts/ai/infrastructure/providers/text_provider_factory.ts:93-98`、`srv/apps/api/provider_runtime.ts:88-100`。
- 两条管线的用法：`provider = this.providerFactory(providerName)`，在 `finally` 中 `disposeProvider`（`srv/contexts/studio/application/proposal_pipeline.ts:95-96,111-115`；流式 154-155,202-206；重试 230-233,253-257）。审阅同构（`review_service.ts:142-143,190-194`）。
- `dispose` 语义：仅「请求级清理」，**不得**改变已选定的 job/HTTP 结果；异常被吞并只上报观测（`srv/contexts/studio/application/provider_disposal.ts:23-32`）。清理有 1s 宽限上限（`provider_http.ts:17,169-186`）。
- 现状：三个 provider 都未实现 `dispose`（全仓只有 port 声明处出现该符号）。即「可选」实际为空实现，新实现可保留钩子但不要依赖它释放 HTTP 连接。

### 1.3 错误分类与重试

统一错误族（`text_generation.ts:47-75`）：

| 类 | 语义 | 是否进「可重试」判定 |
| --- | --- | --- |
| `TextGenerationProviderError` | 一切预期 provider 失败（step 不支持、传输、超时、HTTP 状态、坏 JSON、schema 不符） | 否（基类自身不带重试事实） |
| `ProviderNotConfiguredError`（extends 上者） | 服务端无可用凭据 | 否 |
| `TextGenerationCancelledError` | 应用侧主动取消（控制流信号，非失败） | 否 |
| `ProviderTransportError`（extends 基类，infrastructure 内） | 带 `status/timedOut/malformedJson/retryable` 结构化事实 | 是 |

`ProviderTransportError.retryable` 的判定（`provider_http.ts:79-90`）：

```
retryable = timedOut || malformedJson || status ∈ {429, 500, 502, 503, 504}
```

可重试状态集合硬编码于 `provider_http.ts:15`（这里的状态是**上游**响应码，不是我们的响应）；**HTTP 响应体内容永不参与重试决策**（`provider_http.ts:164-166`，`203-214` 先登记失败再丢弃 body）。

重试策略：默认 3 次总尝试、间隔 1000ms（`provider_http.ts:16,101-105`），次数被夹在 1..3（`111-116`）。只重试 `ProviderTransportError` 且 `retryable`（`126-148`）。

错误码映射（谁负责什么）：

- 同步/流式的预期失败 → 落成 failed job（`proposal_pipeline.ts:106-110`，`187-201`），不是 HTTP 4xx/5xx。
- 未配置 provider 在流式路径**不落 job**，直接向上抛，由 HTTP 层映射为 422 `PROVIDER_NOT_CONFIGURED`（`srv/contexts/studio/application/studio_failure_classification.ts:119-128`；`srv/contexts/studio/interface/http/studio_error_mapping.ts:185-193`；`srv/shared/interface/http/error_envelope.ts:22`）。
- 取消：流式「静默返回，无 job 无 error 帧」（`studio_failure_classification.ts:110-118`，`proposal_pipeline.ts:193-194`）。
- 未知错误（含编程错误）一律不归一化、不上表、直达 500（`studio_failure_classification.ts:16-28,180-189`；`provider_http.ts:300-306` 只归一化 AbortError/TimeoutError/TypeError）。

#### 重建决定：新端口的失败 kind 与 HTTP 面（`srv/platform/text-generation/ports.ts` 的 `ProviderFailure` 联合，现 `:155-200`）

> 引用约定：`ports.ts` 仍在压缩中（为守 200 行上限会重排注释），行号会漂。本章对该文件优先引**符号名**（`transport_connect` / `TextGenerationResult.text` / `STEP_TEXT_KIND`），括号内的行号只是核对时刻的快照。

**有意变更（已裁决，已落地于 `ports.ts` 的 `transport_connect` / `transport_interrupted`）：网络失败按阶段拆分。**
- `transport_connect`：建连期失败（DNS、TLS、TCP 拒绝）→ 请求体未发出 → **`retryable: true`**。
- `transport_interrupted`：请求已发出、响应中途断开或 socket reset → **可能已计费** → **`retryable: false`**。
- 旧实现把两者都归为不可重试（`provider_http.ts:288-306`：`TypeError` → 构造时无 `timedOut`/`malformedJson`/`status` → `retryable === false`，见 `:85-88`）。这是「保守但误伤」：瞬时的 DNS/TLS 失败本可安全重试。而统一改成 true 则相反——会把可能已计费的中断也重发，产生重复计费。按阶段拆开后两个判断各自成立，这是唯一同时正确的分法。

**已裁决：kind 映射的是「运行结果」，不是「HTTP 响应」。** HTTP 码只覆盖「请求本身不成立」这一层；provider 的运行期失败一律落 failed job（同步 `200`、流式 `200` + `PROVIDER_FAILED` 帧，§3.2/§4.4）。因此**不得为任何 kind 新增 HTTP 码**——旧契约只承诺既有 code 与 status 稳定，新增即破坏。设计过程中一度出现过「重试耗尽 → 503、协议类 → 502」的映射，已撤回：它没有任何旧代码支撑，`ports.ts` 全文不含 HTTP 状态码。唯一例外是 `unconfigured` → 422 `PROVIDER_NOT_CONFIGURED`（且流式不落 job）。

**一处易错映射，需纠正：** `content_not_prose` ≠ 422 `INVALID_OPERATION`。`server/tests/api/studio_proposals.test.ts:303-305` 那条断言发生在**接受**调用上——accept 门拒绝一个 failed proposal（`Only a completed proposal can be accepted.` → `InvalidOperationError`），与生成时的非正文判定是两回事。生成侧的旧行为是落 failed job。另：`INVALID_PROPOSAL_PROSE` 只是消息常量（`proposal_prompts.ts:53`），`ERROR_CODES` 中没有任何同名码。

**约束落点：** `content_not_prose` 只允许净化闸门构造、adapter 永不产出（否则「模型不听话」会被伪装成「provider 坏了」）。判别联合在类型上留不住这条，必须由 adapter 契约测试或 lint 规则兜。

### 1.4 三档超时 + 一档清理宽限

| 档 | 常量/默认 | 语义 | 证据 |
| --- | --- | --- | --- |
| 整体 outbound deadline | `LLM_TIMEOUT`，默认 30s，配置区间 5..300 | 从 dispatch 起算的绝对截止，覆盖 dispatch + body 读取；流式每收到一帧就 **rearm**，因此实际语义是「dispatch+静默」而非总墙钟 | `provider_http.ts:27`，`srv/shared/infrastructure/config/provider_config.ts:14-16,88-94`，`srv/contexts/ai/infrastructure/providers/provider_response_lifecycle.ts:59-60,75-79` |
| 长文下限 | `LONG_FORM_TIMEOUT_FLOOR_SECONDS = 180` | 四个 step **全部**属长文，实际超时 = `max(配置值, 180)` | `provider_http.ts:19-24,258-270`；调用点 `dashscope_provider.ts:111,177`、`openai_compatible_provider.ts:156,226` |
| 首字节静默 | 默认 30000ms，`LLM_STREAM_FIRST_BYTE_TIMEOUT_MS` | 仅流式：从 open 成功到第一帧到达的静默上限 | `srv/contexts/ai/infrastructure/providers/streaming_generation.ts:24,62-64,174-180` |
| 帧间静默 | 默认 60000ms，`LLM_STREAM_IDLE_TIMEOUT_MS` | 仅流式：相邻两帧之间的静默上限；每帧后重新起算 | `streaming_generation.ts:26,66-68,230-236` |
| 清理宽限 | `PROVIDER_CLEANUP_GRACE_MS = 1000` | dispose / body cancel 最多等 1s，超时不改结果 | `provider_http.ts:17,169-195` |

要点（易被重建时搞错）：

1. 180s 下限让「配置 30s」对四个长文 step 实际无效；只有新增的短 step 才能拿到裸 30s（`provider_http.ts:252-270` 的注释就是这个意图）。
2. 三档超时都会归一化成 **timedOut** 的 `ProviderTransportError`，即默认可重试；错误文案必须区分档位（`streaming_generation.ts:77-88` 输出 `first-byte timeout after Ns` / `idle timeout after Ns of silence`；`provider_http.ts:222-226` 输出整体超时）。
3. 静默预算用 `Promise.race` 实现，超时后主动 abort dispatch，且败者的 Promise 被吞掉，避免未处理拒绝（`streaming_generation.ts:96-121`）。
4. 配置值合法性：非法/非有限/<=0 的秒数退回默认（`provider_http.ts:53-61`）；环境变量层面则直接拒启（`provider_config.ts:88-94`）。
5. 三档的**字段名**按 arm 钉死（`timeoutMs` / `silenceMs` / `deadlineMs` 各属一个 `ProviderFailure` arm，写错名字是编译错误），但**值**可以合法地填错（把 60s 填进 `deadlineMs` 类型完全成立）。所以档位语义只能由 adapter 测试与上表保证，端口类型不兜——与 `content_not_prose` 的来源约束属同一类「类型管不住」的缺口。

---

## 2. 三种 provider 的差异

### 2.1 mock / deterministic

定位：离线默认体验，产「真散文」而不是占位符（`deterministic_story_provider.ts:29-37`）。

| 维度 | 行为 | 证据 |
| --- | --- | --- |
| step 支持集 | `chapter_draft`、`chapter_revision`、`editorial_review`、`lore_extract`；其他步骤抛 `Unsupported generation step` | `deterministic_story_provider.ts:47-91` |
| 章节输出形状 | `content = { chapter_markdown }`，`rawText` = 裸 markdown | `deterministic_story_provider.ts:82-90` |
| 审阅/lore 输出形状 | `content` 即 `{ findings }` / `{ candidates }`，`rawText` = `JSON.stringify(content)` | `deterministic_story_provider.ts:49-73` |
| usage | 永远 `null`,`null` | `deterministic_story_provider.ts:58-59,70-71,88-89` |
| 语言跟随 | `task.language ?? "en"` 决定整套表格；中英各有独立的 cast/pressure/turn/title 四组常量 | `deterministic_task_language.ts:11-13`，`srv/contexts/ai/infrastructure/providers/deterministic_story_content.ts:13-69,195-205` |
| 确定性 | 全部由 `chapter_number` 取模选槽位；`metadata.title/genre/premise` 直接插值 | `deterministic_story_content.ts:81-113,115-153` |
| 模拟失败 | **没有**失败开关。只有「不支持的 step」这一条失败路径；没有任何注入式故障模拟 | `deterministic_story_provider.ts:80,110` |
| 流式 | 按空白切分，4 个「词」一帧；连续 Han 字符逐字切分，保证拼接等于原文 | `deterministic_story_provider.ts:17,27,99-127` |
| 流式取消 | 每个 piece 之间检查 `signal.aborted`，直接 return（不抛错） | `deterministic_story_provider.ts:115,125` |

重建建议保留的语义：**流式拼接必须逐字节等于同步输出**（`deterministic_story_provider.ts:93-98` 的注释即契约），这是唯一能让流式与同步被同一断言覆盖的机制。

### 2.2 dashscope

三个传输模式（`srv/contexts/ai/infrastructure/providers/dashscope_transport.ts:46`），默认 `multimodal_generation`（`dashscope_provider.ts:41`，`provider_config.ts:82-87`）：

| 模式 | base（无配置时） | endpoint | messages 形状 | 证据 |
| --- | --- | --- | --- | --- |
| `text_generation` | `https://dashscope.aliyuncs.com` + `api` 版本根 | `/services/aigc/text-generation/generation` | `content: string` | `dashscope_transport.ts:34,36,134-135` |
| `multimodal_generation`（默认） | 同上 | `/services/aigc/multimodal-generation/generation` | `content: [{ text }]` | `dashscope_transport.ts:37,134-135` |
| `responses` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `/responses` | **没有 messages，拼成单串 `input`** | `dashscope_transport.ts:30-33,35,38,124-131` |

payload 固定参数：`temperature: 0.7`、`enable_thinking: false`、`result_format: "message"`、`response_format: { type: "json_object" }`（`dashscope_transport.ts:44,144-149`）。responses 模式只剩 `temperature` 与 `response_format`（`125-129`）。

base 归一化分两套，这是历史事故的沉淀：
- 生成模式：若显式 base 含 `compatible-mode`，**重写**回 origin 加版本根；否则原样（`dashscope_transport.ts:91-95`）。
- responses 模式：显式 base **原样通过**，只裁空白与尾斜杠，非法 URL 直接抛 `DashScope API base must be an absolute URL`（`103-107,80-89`）。

同步取文本：`output.choices[0].message.content`（字符串或 `[{text}]` 数组拼接），退化到 `output.text`，否则抛错（`srv/contexts/ai/infrastructure/providers/dashscope_extractors.ts:29-51`）。responses 模式额外检查 `status ∈ {failed,incomplete,cancelled,in_progress,queued}` 一律失败，哪怕有文本（`57-80`）。

流式：
- 请求头 `Accept: text/event-stream` + `X-DashScope-SSE: enable`（`dashscope_provider.ts:167-174`）。
- 请求体加 `parameters.incremental_output = true`，**仅当存在 parameters 对象**；responses 模式没有 parameters 于是原样透传（`dashscope_provider.ts:62-77`）。
- 帧内取文本按三形状依次尝试：responses(`delta` / `output[]` 项) → compatible(`choices[0].delta|message.content`) → native(`output.choices[0].message.content` / `output.text`)，全部**不 trim**（`dashscope_extractors.ts:104-110,128-183`；`rawTextFromContent` 见 `86-97`）。
- usage 从每帧累积，兼容 `prompt_tokens|input_tokens` 与 `completion_tokens|output_tokens` 两套命名（`186-195`）。

已知协议漂移点（重建必须显式建模，见 §9）：responses 端点基址、responses 流帧的 item 形状、JSON 模式流式包装、native 与 compatible 的 finish_reason 集合差异。

### 2.3 openai_compatible

- 默认 base `https://api.openai.com/v1`，只接受 http/https 且必须是绝对 URL，否则抛 provider 错误（`openai_compatible_provider.ts:37,60-75`）。
- 端点固定 `${base}/chat/completions`（`158`）。
- payload：`model`、`temperature: 0.7`、`response_format: { type: "json_object" }`、`messages: [system, user]`（`77-87`）。
- 流式额外加 `stream: true` 与 `stream_options: { include_usage: true }`（`219-223`）。
- 同步取文本：`choices[0].message.content` 必须是非空字符串，否则抛错；**trim 后**返回（`89-106`）。
- 流式取 delta：`choices[0].delta.content`，空串视为无内容（`115-124`）。

`chapter_markdown` 包装的解包规则（`srv/contexts/ai/infrastructure/providers/stream_json_unwrap.ts`）——这是全项目最脆弱的一段契约，逐条固定：

1. 只认唯一包装键 `chapter_markdown`（`4`）。
2. 状态机十相：`leading → member-start → key → colon → value-start → (skip-string|skip-plain) → member-continue`，命中目标键后 `target → trailing`（`11-21,224-235`）。
3. 容错：前导白名单空白、兄弟字段、字段顺序、pretty-print（`138-205`）。
4. 严格：根必须是 `{`；目标值必须是字符串；**嵌套 object/array 的兄弟值一律拒绝**（`140,151-152,178-180`）；未知转义序列报错（`73-75`）。
5. 转义可跨帧：`\u` 六位状态机跨 feed 保持（`24-27,105-136`）。
6. **永不**把裸文本透传：没见到 `{` 就报「expected a JSON object wrapper」（`140`）。
7. 流结束仍停在非 `trailing` 相即报错（`245-249`）。调用点显式 `unwrapper.finish()`（`openai_compatible_provider.ts:244`，`dashscope_provider.ts:195`）。
8. 拼接后的所有 delta 必须逐字节等于 `JSON.parse(payload).chapter_markdown`（`78-87` 注释即契约）。

### 2.4 未配置 provider：必须失败，禁止降级

- 工厂发现 key 为空 → 返回 `UnconfiguredTextProvider`，而不是 mock（`text_provider_factory.ts:71-76`）。
- 该 provider **故意实现流式方法**，让流在第一次 pull 前就抛 `ProviderNotConfiguredError`，避免被误判成「不支持流式」而给出错误能力提示（`srv/contexts/ai/infrastructure/providers/unconfigured_provider.ts:9-46`）。
- 错误文案必须点名环境变量并指向 setup 文档：`DASHSCOPE_API_KEY` / `LLM_API_KEY`（`text_provider_factory.ts:45-52`）。
- 目录端点如实报告 `configured: false`（`model_resolution.ts:75-90`，`srv/contexts/ai/interface/http/provider_routes.ts:57-71`）。

### 2.5 模型解析链

`providerOverride → genericModel → HARD_DEFAULT_MODELS`（`model_resolution.ts:53-62`），默认值 `mock: deterministic-story-v1`、`dashscope: qwen3.5-flash`、`openai_compatible: gpt-4o-mini`（`4-8`）。审阅在 dashscope 上多一级 `DASHSCOPE_REVIEW_MODEL`（`65-73`，`provider_runtime.ts:90-100`）。空串按未设处理（`38-41`）。

---

## 3. 流式协议

### 3.1 上游（provider → server）：必须容忍的 SSE 现实

解析器 `sseDataPayloads`（`srv/contexts/ai/infrastructure/providers/sseDataPayloads.ts:43-94`）的规则：

- 只取 `data:` 行；`:` 注释行、`event:`/`id:` 等其他字段全部忽略（`96-102`）。
- `data:` 后**最多**去掉一个前导空格（`10-14`）。
- 多行 data 用 `\n` 拼接（`96-102`）。
- 事件边界支持 `\n\n`、`\r\n\r\n`、`\r\n\n`、`\n\r\n` 混合（`16-36`，测试 `server/tests/contexts/provider_sse_boundaries.test.ts:23`）。
- 末尾残留缓冲即使没有空行也要 flush（`88-93`）。
- 单事件上限 1 MiB，整 body 上限 8 MiB，超限即 `ProviderTransportError`（`provider_response_lifecycle.ts:11-12,131-137`；`sseDataPayloads.ts:59-63,83-86`）。
- 解码按 chunk 流式进行（`TextDecoder({stream:true})`），缓冲按字节而非字符计（`sseDataPayloads.ts:64-86`）。

### 3.2 下游（server → client）：提案流帧

- 响应头：`content-type: text/event-stream; charset=utf-8`、`cache-control: no-cache`、`connection: keep-alive`、`x-accel-buffering: no`（`srv/contexts/studio/interface/http/proposal_stream_response.ts:5-11`）。
- 数据帧：`data: <JSON>\n\n`，一帧一个 `data:` 字段（`proposal_stream_response.ts:29-32`）。
- 心跳帧：`: heartbeat\n\n`，默认每 15s，`0` 关闭；只在「已提交但等下一帧」期间发（`13-17,162-186`）。
- 帧词汇只有三种，且是 SSOT 类型（`srv/contexts/studio/application/payload_schemas/proposal_frame.ts:13-49`）：
  - `{ type: "delta", text }`
  - `{ type: "done", job }`
  - `{ type: "error", error: { code: "PROVIDER_FAILED", message } }`（code 是字面量，目前只有这一个值）
- **帧内码 vs HTTP 码是两个通道**：`PROVIDER_FAILED` 是 SSE 帧内的字面量，**不在** HTTP 错误码目录里（`srv/shared/domain/error_codes.ts:5-28` 共 22 条，无此项），它没有 HTTP status，也不会出现在任何错误信封中。同族的还有一个不可达内部诊断码 `PROPOSAL_STREAM_DRAIN_TIMEOUT`：它只用于 `destroy` 响应，客户端既收不到帧也收不到信封（`proposal_stream_response.ts:19-27,136-141`）。重建时不要把它塞进 HTTP 状态表。
- 提交时机：先拉第一帧，成功后才 `hijack()` + `writeHead(200)`；因此「输入非法 / 文档不存在 / 409 in-flight / provider 不支持流式 / 未配置凭据」都以普通 JSON 错误信封返回（`proposal_stream_response.ts:196-201`；`srv/contexts/studio/application/proposal_streaming.ts:33-43`）。
- **「首帧之前」不等于「走信封」——这是最容易被重建搞错的一处**：provider 的**运行期**失败（超时、上游 5xx、协议异常），即使发生在第一个 delta 之前，也会被管线在生成器内部捕获，转成 `200` + `error` 帧 + failed job（`proposal_pipeline.ts:187-201`），因为 `pullFirst` 拿到的是一个帧而不是异常。真正会在开门前抛成信封的只有三类：`ProviderNotConfiguredError` → 422 `PROVIDER_NOT_CONFIGURED`（分类表 `stream: "propagate"`）、provider 无流式方法 → `InvalidOperationError` → 422 `INVALID_OPERATION`、准入/文档/在飞拒绝 → 404/409。只有**未映射的未知错误**才落到 500 `INTERNAL_ERROR`（`srv/platform/http/error_envelope.ts:170-172`）。
- **「无流式能力」不是 provider 失败**，它是能力缺失，不属于 12 个 `ProviderFailure` kind 中的任何一个：由管线抛 `InvalidOperationError`（分类表 `stream: "propagate"`、`retry: "land"`，`studio_failure_classification.ts:162-167`），直接 422 且不落 job。两者的重试语义正好相反——`protocol_*` 不重试但**落** failed job，能力缺失**不落** job 且必须换 provider 重发。实现者很容易把能力缺失塞进 `protocol_*`，那会把「换一个支持流式的 provider」变成「原地重试同一个不支持的 provider」。

### 3.3 中断判定与已生成文本保留

服务端判定「正常结束」的唯一条件：见到 `[DONE]` 或 `isTerminalChunk` 为真（`streaming_generation.ts:216-223`）。终结帧集合按模式区分：

- responses：`type === "response.completed" && response.status === "completed"`（`srv/contexts/ai/infrastructure/providers/isProviderStreamTerminal.ts:31-37`）。
- compatible / openai_compatible：`choices[0].finish_reason ∈ {stop,length,content_filter,tool_calls,function_call}`（`4-10,38-40`）。
- native：`output.choices[0].finish_reason` 或 `output.finish_reason ∈ {stop,length,tool_calls}`（`11,41-48`）。

**EOF 而无终结帧 = 不可重试的 provider 失败**，错误串必须带诊断计数（`frames=N, bytes=M`）（`streaming_generation.ts:239-245`）。

客户端判定（`frontend/src/app/proposalStream.ts`）：
- 只有 `done`/`error` 是终结帧；解析器见到即停止收帧并清空缓冲（`114-139`）。
- EOF 却没有终结帧 → `HttpError("ended without result", 502)`，并归类为「结果未知」（`280-299`）。
- 90s 无任何字节 → watchdog 中止连接，报 `PROPOSAL_OUTCOME_UNKNOWN`（`23-24,183-200,289-290`）。
- 心跳帧不产生 data，解析为 `undefined` 被丢弃，永不导致失败（`77-91`）。

已生成文本的保留规则（三处，别混淆）：
1. 服务端中途失败：已累积的原文 `accumulated.join("")` 经净化写入 `result_json.partial_markdown`，`proposal_markdown` 为空串（`proposal_pipeline.ts:195-199`；`proposal_landing.ts:241-278`）。
2. 服务端成功：`accumulated.splice(0)` 清空 sink，不留 partial（`proposal_pipeline.ts:167-169`）。
3. 客户端：失败（interrupted）或作者主动 stop 时，只有在 `text.length > 0` 时才保留预览并置位一个终结标志；空预览不保留（`frontend/src/features/studio/hooks/useProposalStreamSession.ts:32-44,239-269`）。

### 3.4 背压与写入节奏

- 每次 `write` 返回 `false` 就等 `"drain"`，等不到则 30s 后 `PROPOSAL_STREAM_DRAIN_TIMEOUT` 并销毁响应（`proposal_stream_response.ts:13,107-147`）。
- 心跳写返回值**故意忽略**：注释声明的理由是「单帧有界、每次 pull 之间清零，背压握手交给下一个数据帧」（`169-178`）。这是刻意的取舍，重建时可保留但需知道它意味着心跳不受背压保护。
- 每帧写出后都重新检查连接是否已中断（`202-210`）；`frames.return()` 一定会被调用一次，清理失败与流失败以 `AggregateError` 合并上抛（`219-251`）。
- 连接中断来源有三：客户端 socket `close`、response `close`（且未 `writableFinished`）、response `error`；三者竞速，第一个赢（`68-105`）。

### 3.5 幂等键的传递与重放

传递链：HTTP 头 `Idempotency-Key` → `requestKey` → job 行 `request_idempotency_key`（`srv/contexts/studio/interface/http/proposal_routes.ts:50,78`；`proposal_routes.ts:90,124`；`proposal_landing.ts:173`）。

重放语义（DR-027）：
- 同步：进入任何工作前先 `findJobRequest`，命中直接返回存量 job（`proposal_pipeline.ts:77-79`；`srv/contexts/studio/application/proposal_admission.ts:117-124`）。
- 流式：命中则只产出一帧——completed → `done`，failed 且有 error → `error`；无终结状态的存量行是协议违约，抛错而不是编造帧（`proposal_pipeline.ts:132-137`；`proposal_landing.ts:287-293`）。
- 并发插入竞态不在查表处解决，而由落库时的 `claimRequestKeyJob` 关闭（`proposal_admission.ts:110-116` 注释）。
- 键与作用域绑定：同键不同项目视为不同键（`proposal_admission.ts:117-124`）。
- 客户端只在「结果未知」时保留键以便重发；确定失败即弃键（`useProposalStreamSession.ts:218-224`）。
- **重放不是无条件捷径**：只有本次键对应的 job 已落库才走重放；同键请求仍在跑时 `findJobRequest` 查不到，紧接着的 in-flight 守卫抛 `OperationInFlightError` → 409 `OPERATION_IN_FLIGHT`（`proposal_pipeline.ts:78-79,90`；守卫本身 `srv/contexts/studio/application/operation_in_flight.ts:78-92`）。
- **同一个 code、同一个 409，`Retry-After` 的有无取决于抛出点，不取决于码**：全仓 `OperationInFlightError` 6 个构造点里只有 2 个传了 `retryAfterSeconds=1`，且都在重试面——`job_history_service.ts:233`（`retry (<jobId>)` 重放）与 `job_store_part.ts:289-294`（retry claim 时 status 仍为 running）；另外 4 个（project 独占 `operation_in_flight.ts:66`、同目标 `:82`、project 容量前 `:123`、app 容量前 `:130`）都是 3 参，映射处因值为 undefined 而省略该头（`studio_error_mapping.ts:139-155`）。因此生成路由的 409 **不带**该头，重试路由的同键 409 **带** `Retry-After: 1`（运行时受测：`server/tests/api/job_retry_idempotency_contract.test.ts:97`）。
- 新契约已按这个裁决执行：`srv/contracts/errors.ts:20-27` 用注释明确「`Retry-After` 不按码声明，是否携带取决于抛出点」，并点名 `OPERATION_IN_FLIGHT` 有 6 个构造点、只有 2 个知道延迟。因此 `ErrorDefinition` 里**没有** `retryAfterHeader` 字段（该字段曾在早期草稿出现，现已删除）；头只能由抛出点的 `retryAfterSeconds` 经 `studio_error_mapping.ts:151-153` 写出。
- 残留风险（写进验收）：这条约束目前**只有注释，没有类型或测试兜底**。任何人都可能重新加回「码级 flag」，届时又会两边错一边。建议加两条反向断言：重试面 409 必带 `Retry-After: 1`（已有 `job_retry_idempotency_contract.test.ts:97`），生成面准入 409 必**不带**该头（目前缺）。
若缺这两条断言，失效后果仍有上界：某准入点若误传 `retryAfterSeconds`，症状是多一个等待头（时长等于误传值，**不固定 1 秒**），客户端多等 N 秒后重试仍会失败——只增延迟、不改错误类型。因此可作为 `accepted-risk` 记录，但必须写明这个上界，否则会被误读成「无害」而不是「有界」。
- 报错文本通道（新信封；已部分由类型兜底，但兜底范围是手写的）：
  - 8 个码的 `message` 现为**必填**（`contracts/errors.ts:210-218` 的 `ErrorCodeRequiringMessage` 并集）：`FORBIDDEN`、`NOT_FOUND`、`INVALID_OPERATION`、`PROVIDER_NOT_CONFIGURED`、`VOLUME_CONFLICT`、`DOCUMENT_CONFLICT`、`OPERATION_IN_FLIGHT`、`SERVICE_UNAVAILABLE`。这些码必须把「哪个 id / 字段 / provider」写进 `message`，不能只塞进 `details`；漏传变成编译错误。
  - 其余 14 条（`contracts/errors.ts:221` 的 `ErrorCodeWithDefaultMessage`）仍可省略，回落到 catalog 通用句。
  - 残留风险：**将来新增的码**若没被手工加入 requiring 并集，就会静默回落到通用句，而类型不会提醒。这与本节的 `Retry-After` 条形成对照——那条至今只有注释，没有类型。
  - 若要以门禁兜住这条，必须做**双向集合比对**（文档声明的集合 ≡ `ErrorCodeRequiringMessage` 的键集合），只校验「那行存在且可解析」会恒绿：集合成员变化既不改 `status`/`retry`/`remedy`，也不改 `defaultMessage`，四列门禁与文案指纹都察觉不到。失败信息还应指出**哪几个码**多出/缺失，而不是只报「不一致」。
- 重试面 409 的 `details` 有第二个陷阱：`operation` 的值是 `retry (<原 jobId>)` 模板串而非原 pipeline 操作名，且 `document_id` **恒为 null**（`job_history_service.ts:233`、`job_store_part.ts:289-294`），即便原 job 绑定了文档。客户端不能用它判断「是否同一次生成在跑」——它只表示「该重试已被认领」。

---

## 4. 提案落地

### 4.1 接受的判定

前置门（`proposal_acceptance_store_part.ts:30-53`）：
1. job 必须存在、属于该 project、`kind === "proposal"`、`document_id` 非空，否则 404。
2. `status === "completed"`，否则 `InvalidOperationError("Only a completed proposal can be accepted.")`。
3. `result.accepted_revision_id` 已存在 → 直接返回当前 job（幂等，不再写）。
4. `proposal_markdown` 必须非空（trim 后）。

**整章替换**，没有前缀重合/合并模式：接受时的写入内容就是 `proposal_markdown` 全文（`69-76`）。全仓没有任何「proposal 与 base 文本前缀比对」的逻辑（`proposal_*` 与 `proposal_acceptance_store_part` 中无 `startsWith`/prefix 判定）；前端只有展示用的行级 diff（`frontend/src/features/studio/historyLineDiff.ts:33-55`），不参与写入。

末尾形状：只有「整体替换整章」「幂等返回」「采纳历史遗留拆分修订」三种，没有 append/insert 模式（`proposal_acceptance_store_part.ts:58-68`）。

### 4.2 冲突检测（生成期间正文被改）

- 提案生成时把 `base_revision_id` 记进 job.request_json（`proposal_admission.ts:89-93`）。
- 接受时以它作为 `baseRevisionId` 传给 `advanceDocumentInTransaction`；该函数第一件事就是比对 `document.currentRevisionId !== input.baseRevisionId` → `RevisionConflictError(currentRevisionId)`（`srv/contexts/studio/infrastructure/db/document_revision_writes.ts:55-57`）。
- HTTP 面映射为 409 `REVISION_CONFLICT` 且带 `details.current_revision_id`（`srv/contexts/studio/interface/http/studio_error_mapping.ts:111-120`）。
- 整个接受是一个 `behavior: "immediate"` 事务（`proposal_acceptance_store_part.ts:27,84`），幂等判断在读锁**之后**（`42,88-89`）。
- 重试路径同样做钉住校验，但产出的是 `stale-base` 失败结果而不是 409（`proposal_admission.ts:192-198`）。

### 4.3 接受的写入序列

按事务内顺序（`proposal_acceptance_store_part.ts:27-85`）：

1. `scopedProject`（校验 scope 归属）
2. 读 job 行 → 存在性/kind/document 判定
3. 状态判定 → `afterLockedJobRead`（测试缝，证明锁先于幂等决策）
4. 读 `result_json` → 幂等短路
5. `scopedDocument`
6. 读 `request_json.base_revision_id`
7. 历史兼容：查找同 document、`source = "ai-accepted"`、内容逐字节相等、`parentRevisionId === base`、`metadata.ai_job_id === jobId` 的既有修订，命中则只补绑 `accepted_revision_id`（`109-135`）
8. 否则 `advanceDocumentInTransaction({ contentMarkdown: proposal, baseRevisionId, title: null, metadataJson: {ai_job_id}, source: "ai-accepted" })`
9. `bindAcceptedRevision`：把 `accepted_revision_id` 合并写回 job.result_json

第 8 步内部还会：校验大纲 beat 容量（所有产出 outline 内容的路径共用同一闸门，`document_revision_writes.ts:75-78`）、插入新修订行（parent 指向 base、`revisionNumber = current+1`，`91-99`）、更新 document 指针与标题（`103-107`）、刷新全文索引（`114-119`）、更新 project.updatedAt（`120`）。

审计信息落点：修订 `source = "ai-accepted"` + `metadata.ai_job_id`（`proposal_acceptance_store_part.ts:73-74`）；job 侧 `request_json` 保存 operation/instruction/base_revision_id（`proposal_admission.ts:89-93`），`result_json` 保存 proposal/base/accepted（`proposal_landing.ts:210-214`），`event_details_json = { proposal_only: true }`（`216`）。

**两条不对称，别混**（与稿件域确认过）：
- AI 采纳把修订 metadata **整体替换**为 `{"ai_job_id": ...}`，文档原有 metadata 不会保留（`proposal_acceptance_store_part.ts:73`）。
- 历史修订恢复是**以历史修订的 metadata 为底，再盖 `restored_from`**：`safeLoadJson(revision.metadataJson)` 里的 `revision` 是**被恢复的那条历史修订**（`revision_service.ts:73-88`）。因此当前修订的 metadata 被**丢弃**，`ai_job_id` 之类的字段不会残留；这不是「在当前 metadata 上补一个字段」。
- 准确表述：两者都是「整体替换」，区别只在替换成什么——采纳换成 `{ai_job_id}`，恢复换成「历史修订 metadata + restored_from」，`source` 分别是 `ai-accepted` / `restore`。因此「采纳一次 AI 提案」会丢掉该文档此前的自定义 metadata，这是既有行为，重建时需显式决定是否保留。

### 4.4 失败落地与用量

- 失败：failed job + 零 token 的 `unreported` usage 行，同一事务写入（`proposal_landing.ts:241-278`；`srv/contexts/studio/application/attempt_usage.ts:38-58`）。
- 成功：job + usage 同一事务（`proposal_landing.ts:159-178`），usage 的 `token_source` 只要任一侧是估算就降级为 `estimated`（`attempt_usage.ts:21-36`）。
- 用量缺失时用词数估算，词数定义是「一个 Han 字符算一个词 + 非 Han 的连续字母数字串算一个词」（`srv/contexts/studio/domain/revision_word_count.ts:4-19`）。
- 该词数函数是**全仓唯一**口径，HTTP 层以 `wordCount` 名义再导出（`srv/contexts/studio/application/payloads.ts:38`）。注意它的词字符集是 `[\p{L}\p{N}_'-]+`（**含**撇号与连字符，`revision_word_count.ts:2`），而 FTS 检索分词用的是 `[\p{L}\p{N}_]+`（**不含**）——做 usage 估算时用前者，不要与检索口径混用。

---

## 5. 输出净化

### 5.1 规则完整清单（`srv/contexts/studio/application/sanitization.ts`）

**A. 逐行删除机械模板行**（`138-143`，判定见 `75-82`）：
1. 英文引导 + 模板短语同现：`^(here's|here is|below is|sure|certainly|as requested|draft(ed) chapter) … (模板短语) …$`（`29-32`）
2. 中文「确认/元话术开头 + 整行含模板短语」（`69-71`）；模板短语闭集 20 个：以下是/下面是/如下/如下所示/正文如下/内容如下/初稿/草稿/修订稿/修改稿/重写稿/改写稿/重写后的/改写后的/修改后的/修订后的/为您/按照您的要求/根据您的要求/遵照您的指示（`34-55`）
3. 整行只有确认词 → 直接删（`73-74`）

**B. 子串机械替换**（`15-25`，9 条）：`revision anchor:` → 删除；`the chapter closes` → `The scene settles`；`the next scene` → `What follows`；`first draft` → `opening passage`；`rewritten chapter` → `reworked passage`；`focus character` → `central figure`；`focus_motivation` → `central motivation`；`relationship_status` → `relationship state`；`outline_hook` → `story hook`。

**C. 空白规范化**（`147-150`）：`\r\n?`→`\n`；去行尾空格；3 个以上连续换行压成 2；首尾 trim。

**D. 长度下限**：净化后 `length <= 400` 即判非正文（`164-167`）。注意是 UTF-16 长度，不是码点（与 §4 的码点上限口径不同）。

**E. 结构校验**：
- 不能整体 `JSON.parse` 成功（`152-162,165`）——残留 JSON 视为非正文。
- 不能含 provider 脚手架（`168-170`）：即保留键 `echo`/`result` 以四种形态出现——直接序列化 JSON、被引号/反引号包裹的 JSON、裸行键（含 `-`/`1.`/`[ ]` 前缀）、`{}`/`[]` 复合区域；嵌套 JSON 走 worklist（≤512 节点、深度上限、≤12 层字符串包装），**任何超限即判为脚手架**（fail closed）（`srv/contexts/studio/application/provider_scaffold_scanner.ts:30-33,99-131,135-147,170-226`）。
- 不能含 9 个禁用短语中的任何一个（不区分大小写）：`revision anchor`、`the chapter closes`、`the next scene`、`first draft`、`rewritten chapter`、`focus character`、`focus_motivation`、`relationship_status`、`outline_hook`（`sanitization.ts:4-14,171-172`）。

### 5.2 「不是正文」的拒绝条件（合并判定）

`validatedProposalOrThrow` 的完整拒绝链（`proposal_landing.ts:109-122`）：

1. `content.chapter_markdown` 不是字符串 → `INVALID_PROPOSAL_PROSE`
2. 码点数 > 1,000,000 → `OVERSIZED_PROPOSAL`（`srv/contexts/studio/application/proposal_code_points.ts:12-20`；流式路径按 delta 增量计数，跨 delta 的代理对只算 1，`34-70`）
3. 净化后不满足 §5.1 的 D/E → `INVALID_PROPOSAL_PROSE`

错误消息是稳定字面量：`"Generated proposal content is not valid story prose."`（`srv/contexts/studio/application/proposal_prompts.ts:53`）。

**注意缺口**：净化阶段**不剥 markdown 围栏**。围栏只出现在两处，且都不是散文净化：JSON 解析时剥除由三个反引号包裹、且不少于 3 行的代码围栏块（`srv/contexts/ai/infrastructure/providers/provider_payload.ts:16,92-96`），以及脚手架扫描时跳过以三个反引号开头的反引号字符串（`provider_scaffold_scanner.ts:81-82`）。因此「模型返回被 markdown 代码围栏整段包裹的章节」会原样通过并写进正文。这是重建时必须显式决策的点（现状 = 不处理）。

后果链（已与稿件域核对）：采纳时 `result.proposal_markdown` 被**原样**写成新修订正文（`proposal_acceptance_store_part.ts:47-53,69-76`），稿件域不再净化。所以围栏一旦漏过，会一路进入 `content_markdown`、字数统计（`revision_word_count.ts:15-19` 只把反引号当标点、计 0 词，但字符本身保留在正文）与全文索引，且无法在后续层自动纠正（重建索引 reindex 只是重建索引本身，不会剥离围栏；反引号在 FTS 分词里是分隔符，会被切成 token）。

### 5.3 净化与 provider 解耦的位置

- 净化只发生在 studio 应用层，**provider 完全不净化**，只在传输层做 JSON 结构容错（`provider_payload.ts:196-208`）。
- 唯一入口是 `validatedProposalOrThrow`，三条管线（同步 `proposal_pipeline.ts:97`、流式 `171-173`、重试 `234`）与失败落地（`proposal_landing.ts:262` 对 partial 也净化）共用。
- HTTP provider 的「散文兜底」发生在净化**之前**：若 schema 声明 `chapter_markdown` 为 string，则裸散文也算合法 payload（`provider_payload.ts:175-193`）。即容错分两层：传输层容忍裸文本 → 应用层再判是不是正文。
- 断言位置正确性由测试固定：`server/tests/contexts/sanitization.test.ts:23,69,218,266,300`。

**重建决定（已定，待接线）**：新端口 `srv/platform/text-generation/ports.ts` 用 `TextGenerationResult.text` 取代旧的 `content`（不再返回解析后的对象），JSON 步骤由调用方按 step 解析（`TextGenerationTask.responseSchema` 仅 JSON 步骤给）。这**不改变** §5.1/§5.2 的净化链，但把「容错」的责任显式搬走了，必须落定：
- 散文步骤（`chapter_draft` / `chapter_revision`）：adapter 负责 JSON 包装解包，`text` 必须是**已解包、未净化**的 markdown（`ports.ts` 的 `TextGenerationResult.text` 注释；`STEP_TEXT_KIND` 表）。
- JSON 步骤（`editorial_review` / `lore_extract`）：`text` 必须是**已完成提取与形状收敛**的 JSON 文本，即保留旧 `provider_payload.ts:89-110`（平衡括号提取 + 围栏剥除）与 `:112-169`（按 schema 收敛）的能力；不得退化为裸 `JSON.parse`。
- 裸散文兜底（旧 `provider_payload.ts:175-193`）仍只对声明了 `chapter_markdown: string` 的场景生效，随提取逻辑一起搬移。
- 无论搬到哪里，`validatedProposalOrThrow` 仍须在**净化前**拿到码点上限判定（§5.2 第 2 条），顺序不可颠倒。
- **必须补一条 adapter 级测试**：夹具用畸形 payload（整段被围栏包裹、JSON 前后夹散文、数组/字符串形状跑偏），断言 `text` 仍可直接 `JSON.parse` 且形状已收敛。mock 永远返回合法 JSON，缺这条测试时上述五段容错等于不存在（端口类型约束不了实现）。

---

## 6. 上下文组装

### 6.1 resident context 的三段构成

由 `assembleResidentContext` 生成（`srv/contexts/studio/application/resident_context.ts:135-165`）：

| 段 | 内容 | 截取规则 | 证据 |
| --- | --- | --- | --- |
| ① OUTLINE | 大纲文档当前修订的**全文** + 当前 beat | 不截断；beat 通过 `target.beatRef` 精确匹配 title 解析 | `resident_context.ts:158-161,168-177`；渲染 `srv/contexts/studio/application/resident_context_render.ts:41-50` |
| ② PRIOR STORY | 目标章**之前**每一章各一行摘要，按阅读顺序、不省略 | 每章摘要：扁平化后取前 **60 词**，且总长 ≤ **512 码点**，被截则末尾加 `…`；空章写 `(no text yet)` | `resident_context.ts:25-26,30,87-98,140-147` |
| ③ RECENT TEXT | 最近一章的**结尾**片段 | **1200 字符**上限；越界时在 200 字符窗口内优先找换行、再找空格对齐切点，都找不到就硬切 | `resident_context.ts:27-29,106-122,149-155` |

排序与选取：只取 `kind === "chapter"`；目标章之前的全部为 prior；recent 取「目标章之外最近的、有正文的那一章」的尾部（`135-155`，注释 124-134 解释为什么不重复目标章自己的正文）。目标不存在或非 chapter 时视为「所有章都在它之前」（`137-138`）。

扁平化（`70-81`）：去 CRLF、图片/链接保留文字、去 ATX 标题标记、去 `**`/`*`/反引号、连续空白压成单空格。

### 6.2 lore 注入的预算、优先级、超预算行为

- 命中判定：entry = `character | world` 文档（`srv/contexts/studio/application/lorebook.ts:22-26`）；键 = 标题 + 别名，**大小写不敏感的子串包含**（刻意不要求整词边界）；语料 = resident 原文 + 目标正文（`116-145`；语料构造见 `resident_context_render.ts:18-33`）。
- 门禁（fail-closed）：`status !== stable` 直接跳过；无正文内容跳过（`lorebook.ts:123-130`，`35-37`）。
- 摘要来源：条目自身首个散文段落，扁平化后 ≤ **240 字符**，词边界截断（`lorebook.ts:148,162-196`）。
- 预算：**4000 字符**默认，可由配置覆盖（`srv/contexts/studio/application/lore_injection.ts:21`，`provider_config.ts:34,124-130`，管线注入点 `proposal_pipeline.ts:67-68`）。
- 两段式渲染：所有命中先按摘要行入场；然后两趟贪心升级为全文——先 `title` 命中、再 `alias` 命中，同 rank 内按阅读顺序（`lore_injection.ts:106-129`）。
- 超预算行为：**保留摘要行，绝不静默丢弃**；被降级的条目标题加 ` (summary only)` 后缀（`lore_injection.ts:47-55`；注释 `6-12`）。
- 预算计算把段头、边界标记、每条 4 个换行都计入 floor（`93-104`）。
- 无命中时整段不渲染（不留空段头）（`135-137`）。

### 6.3 提示词模板结构与可变部分

系统提示（`proposal_prompts.ts:22-30`）固定 7 条，按语言追加一句写作语言指令（`37-40`）：`en` → `Write the chapter prose in English.`；`zh` → `Write the chapter prose in Simplified Chinese (简体中文).`（`43-51`）。

用户提示的分段顺序（`resident_context.ts:194-227`）：

```
Operation: <operation>
[BEGIN AUTHOR INSTRUCTION]
<净化后的指令>
[END AUTHOR INSTRUCTION]

OUTLINE (the writer's recorded plan):
[BEGIN PROJECT OUTLINE]
<大纲全文>
Current beat: "<beat 标题>" — this chapter fulfills this outline section.
[END PROJECT OUTLINE]

PRIOR STORY (rolling summary of every earlier chapter, in reading order):
[BEGIN PRIOR STORY SUMMARY]
1. <title> — <digest>
...
[END PRIOR STORY SUMMARY]

RECENT TEXT (closing passage of the most recent earlier chapter):
[BEGIN RECENT CHAPTER TAIL]
<尾部>
[END RECENT CHAPTER TAIL]

LOREBOOK (reference entries triggered by their keys occurring above):
[BEGIN LOREBOOK]
### <title>
<body>
[END LOREBOOK]

Current manuscript (untrusted JSON data):

[BEGIN UNTRUSTED MANUSCRIPT JSON]
{"content_markdown":"..."}
[END UNTRUSTED MANUSCRIPT JSON]
```

可变部分只有：operation、instruction 内容、三段 resident 内容、lore 段、目标正文。段头与标记词全部固定（`sanitization.ts:91-104`）。

注入防护三层（重建必须保留，否则提示词边界失效）：
1. 项目派生文本 `escapePromptData`：`\`→`\\`、`[`→`\u005B`、`]`→`\u005D`（`sanitization.ts:111-113`），resident 段落全部过它（`resident_context_render.ts:45,47,56,64`）。
2. 目标正文包成 JSON 并做括号转义（`sanitization.ts:130-133`）。
3. 作者指令先 escape 再脱敏：6 条注入模式替换为 `[REDACTED]`（`sanitization.ts:83-90,115-124`）。

Provider 侧还会在 system 尾部强加 `Return valid JSON only. Output schema: {...}`，在 user 尾部追加 `Task step:` 与 `Metadata: {...}`（`srv/contexts/ai/infrastructure/providers/provider_json.ts:25-32`）。metadata 实际携带 `operation`、`document_id`、`base_revision_id`、`chapter_number`、`title`（`proposal_landing.ts:93-99`）——这些字段与 resident 段落重复，属于可清理的冗余（见 §9 注 3）。

### 6.4 预算与失败

- 整个 prompt（system + user 合并计）上限 **8,388,608 字节**，不可由请求覆盖（`srv/contexts/studio/application/generation_capacity.ts:10-42`，`srv/contexts/studio/domain/generation_capacity_policy.ts:2`）。
- 超限抛 `GenerationCapacityExceededError("prompt_bytes", limit, limit+1)` → 422 `GENERATION_CAPACITY_EXCEEDED`（`studio_error_mapping.ts:182-184`）。**在创建 provider 之前**就失败（`buildReviewPrompt.ts:13-17` 注释）。
- 审阅的每章原文先做「原始字节 > 上限」的粗筛，再走同一 writer 的精确字节计（`buildReviewPrompt.ts:28-36`）。
- 上下文捕获是**单次一致读**：`readProposalContext` 返回 project/target/documents/volumes 全量只读行（`srv/contexts/studio/application/ports/proposal_context_store.ts:19-33`）。注意这里的「一致读」是数据库读事务语义，与 `SNAPSHOT_CONFLICT` 所指的「快照被 review/export 引用」是两个不相干概念，勿混用措辞。

---

## 7. 审阅

### 7.1 维度闭集、严重度、发现结构

- 维度闭集 5 个：`pacing`、`continuity`、`pov`、`foreshadowing`、`dialogue`（`srv/contexts/studio/application/review_rules.ts:9-15`）。
- 严重度只有 `blocker | warning`，排序权重 `blocker=0, warning=1`（`19`）。
- 发现结构（持久化形状）：`document_id`、`severity`、`dimension`（落库为 `code`）、`message`、`suggestion`、`evidence`（`review_rules.ts:65-75`；`srv/contexts/studio/application/ports/review_outcome_store.ts:37-44`）。
- 收敛规则（宁可丢，不可编造）（`review_rules.ts:35-85`）：
  - 非对象条目丢弃
  - `document_id` 必须命中本次捕获的 chapter 文档，否则丢
  - `dimension` 必须（大小写不敏感）落在闭集，否则丢
  - `message` 必须非空，否则丢
  - 未知/缺失 severity → `warning`
  - `suggestion` 缺失 → 空串
  - 排序：severity → code 字典序 → 文档 position
- provider 返回必须含 `findings` 数组，否则抛 provider 错误（`srv/contexts/studio/application/review_service.ts:174-179`）。

### 7.2 快照绑定与 180 秒下限

- 读源：`readReviewSource(scope, projectId, now)` 返回同一时刻的只读文档集 + 项目存储的 provider 选择（`review_service.ts:134`；`review_outcome_store.ts:16-29,138`）。
- 只读评估：`evaluateProject` 明确「不持久化任何审阅证据」（`review_service.ts:127-133`）；落盘由 `recordCompletedReviewJob` / `completeReviewRetryJob` 一次性完成（`review_outcome_store.ts:139-145`）。
- 快照 id 与 `snapshot_document_id` 由持久层在落盘时生成并绑定到每条 issue（`review_outcome_store.ts:31-34,46-51`；DTO 出口 `review_service.ts:218-241`）。
- 捕获后源失效 → `ReviewSourceInvalidatedError`，审阅桥与重试链落 failed job，其余链上抛（`studio_failure_classification.ts:137-144`）。
- 180s：审阅走 `editorial_review` step，命中 `LONG_FORM_STEPS`，故传输超时下限 180s（`provider_http.ts:24,258-270`；`review_service.ts:143-173` 的 provider 调用）。这是「审阅与生成共用同一套超时下限」的具体体现。
- 薄章阈值 250 词（Han 文本即 250 字），只喂给确定性 provider 的检查，不是产品级拦截（`review_rules.ts:87-106`；注入点 `review_service.ts:162-172`）。

### 7.3 与生成共用 provider 的边界

共用：
- 同一 `TextGenerationProvider` 端口与同一工厂（`review_service.ts:70,142`）。
- 同一错误族与同一「失败即落 failed job」分类表（`studio_failure_classification.ts:129-136`）。
- 同一 prompt 字节预算、同一 `formatUntrustedManuscript` 包装（`buildReviewPrompt.ts:4,22-47`）。
- 同一 provider 选择优先级：显式 pin（重试）> 项目存储选择 > 服务端默认（`review_service.ts:122-125,135-136`；重试 pin 见 `srv/contexts/studio/application/job_retry_executor.ts:249-255`）。

不共用：
- 模型：dashscope 审阅可走独立 `DASHSCOPE_REVIEW_MODEL`（`provider_runtime.ts:90-100`）；生成不受影响。
- 流式：审阅只调 `generateStructured`，无流式路径（`review_service.ts:143`）。
- 输出契约：审阅是 `{ findings }`，且**不**经过散文净化链（净化只针对 `chapter_markdown`）。
- 语言推断：审阅用被审章节自身的文本推断（`review_service.ts:147-149`）；提案用整个捕获项目的文本推断（`srv/contexts/studio/application/writing_language.ts:46-54`，阈值 Han 占比 ≥ 0.25 判 zh，`26-39`）。

---

## 8. 旧测试对应

| # | 路径 | 覆盖行为 | 处置 |
| --- | --- | --- | --- |
| 1 | `server/tests/contexts/provider_streaming_retry.test.ts` | 首帧前可重试、首帧后永不再试（DR-006） | 可直接移植 |
| 2 | `server/tests/contexts/provider_streaming_terminal_frames.test.ts` | 四分支持久化终结帧判定（#674） | 可直接移植 |
| 3 | `server/tests/contexts/provider_streaming_completion.test.ts` | EOF 无终结帧 = 失败 | 可直接移植 |
| 4 | `server/tests/contexts/provider_streaming_timeouts.test.ts` | 首字节/帧间静默预算与 rearm | 可直接移植 |
| 5 | `server/tests/contexts/provider_streaming_deadline.test.ts` | 整体 deadline 与中断竞速 | 可直接移植 |
| 6 | `server/tests/contexts/provider_response_deadline.test.ts` | 同步响应 deadline 语义 | 可直接移植 |
| 7 | `server/tests/contexts/provider_response_bounds.test.ts` | 8 MiB / 1 MiB 上限 | 可直接移植 |
| 8 | `server/tests/contexts/provider_response_cleanup_races.test.ts` | 清理宽限与竞态不改结果 | 可直接移植 |
| 9 | `server/tests/contexts/provider_sse_boundaries.test.ts` | 混合换行事件边界 | 可直接移植 |
| 10 | `server/tests/contexts/provider_http.test.ts` | 可重试集合、策略夹取、错误归一 | 需重写（若拆分重试与传输职责） |
| 11 | `server/tests/contexts/provider_payload.test.ts` | JSON 对象提取、字段收敛、散文兜底 | 可直接移植 |
| 12 | `server/tests/contexts/provider_scaffold.test.ts` | 脚手架四形态与 fail-closed 上限 | 可直接移植 |
| 13 | `server/tests/contexts/sanitization.test.ts` | 净化表驱动 + 中文模板前缀 + 注入脱敏 + 边界块 | 可直接移植 |
| 14 | `server/tests/contexts/stream_json_unwrap.test.ts` | 增量解包器（#496） | 可直接移植 |
| 15 | `server/tests/contexts/dashscope_transport.test.ts` | 三模式 payload 与 base 归一 | 需重写（建议按「协议描述符」重新表达） |
| 16 | `server/tests/contexts/dashscope_extractors.test.ts` | 响应文本提取与 usage 兼容命名 | 可直接移植 |
| 17 | `server/tests/contexts/dashscope_provider.test.ts` | 请求形状 + 瞬时失败重试 | 可直接移植 |
| 18 | `server/tests/contexts/openai_compatible_provider.test.ts` | 请求形状、重试、base 边界 | 可直接移植 |
| 19 | `server/tests/contexts/resident_context.test.ts` | 摘要/尾部截取边界、三段装配、渲染布局 | 可直接移植 |
| 20 | `server/tests/contexts/lore_injection.test.ts` | 摘要来源与预算下渐进披露 | 可直接移植 |

补充（超出 20 条但值得一并搬迁的判定依据）：`server/tests/contexts/review_rules.test.ts`、`server/tests/contexts/proposal_acceptance_transactions.test.ts`、`server/tests/api/studio_proposals_stream.test.ts`、`server/tests/api/proposal_stream_response_heartbeat.test.ts`、`frontend/src/app/proposalStream.test.ts`。

---

## 9. 协议脆弱点（重建重点）

### 9.1 两次破坏兼容的具体位置

**第一次：Responses 端点基址被上游迁移（#502）**

- 旧行为把显式配置的 base 重写成带版本段的规范路径；上游不再维护 `api`-rooted 的 responses 链路，导致请求打到已废弃路径。
- 现在：无配置默认 `https://dashscope.aliyuncs.com/compatible-mode/v1`；显式 base **原样通过**，只裁空白与尾斜杠（`dashscope_transport.ts:25-35,97-107`）。
- 同时生成模式保留「含 compatible-mode 就重写回版本根」的补丁（`91-95`）——这条与 responses 的「不重写」方向相反，是两次事故叠加留下的不对称逻辑。

**第二次：JSON 模式流式增量从裸文本变为包装 JSON（#497 / #496）**

- 开启 `response_format: json_object` 后，上游流帧里的 `delta.content` 不再是散文片段，而是 `{"chapter_markdown":"...` 的**转义碎片**；直接拼接会把 `\n`、`\"` 原样吐给前端。
- 现在：所有 HTTP provider 的流式都把每个 delta 送进同一个增量解包状态机，输出反转义后的散文（`dashscope_provider.ts:149-156,184`；`openai_compatible_provider.ts:195-203,233`；`stream_json_unwrap.ts:78-92`）。

### 9.2 次要漂移点（已在代码里打了补丁，但都属于「猜上游形状」）

1. responses 非流式：`status` 白名单外视为成功（`dashscope_extractors.ts:57-69`）。
2. responses 流式：`output[]` 项的 `message`/`item` 双层持有者、`content` 优先于 `delta`（#364）（`128-156`）。
3. responses 流式：带 `type` 且非 `message` 的项（reasoning/tool_call）只接受顶层 `delta`（#371）（`137-144`）。
4. finish_reason 三套集合：compatible 5 个、native 3 个（`isProviderStreamTerminal.ts:4-11`）。
5. usage 命名双轨：`prompt_tokens|input_tokens`、`completion_tokens|output_tokens`（`dashscope_extractors.ts:186-195`）。
6. 流式 200 内嵌错误帧：compatible 走 OpenAI `error` 形状，native 走顶层 `code+message`（`118-125`；`provider_stream_failure.ts:30-49`）。
7. `streamingPayload` 只在存在 `parameters` 时加 `incremental_output`，responses 模式因此**不**请求增量——靠上游默认行为（`dashscope_provider.ts:67-77`）。

### 9.3 新实现如何降低耦合（建议，非现状）

1. **把「协议形状」抽成可替换的描述符**，一个模式一个描述符：`{ base(url), endpoint(path), buildTask(task), extractFinal(json), extractDelta(json), isTerminal(json), isFailure(json), usage(json) }`。现状这些散落在 `DashscopeTransport` + `dashscope_extractors` + `isProviderStreamTerminal` + `provider_stream_failure` 四处，而 `isProviderStreamTerminal` 已经用 `mode` 字符串区分三种协议（`isProviderStreamTerminal.ts:27-30`）。
2. **终结判定与错误判定合并为「帧分类器」**，返回 `{ kind: "delta"|"terminal"|"failure"|"ignore", text?, failure? }`，取代现在「先 `extractStreamFailure` 再 `isTerminalChunk` 再 `extractDelta`」的三趟扫描（`streaming_generation.ts:220-228`）。
3. **不要在两个 provider 里各写一份流式骨架**。现状 dashscope 与 openai 的流式方法除请求构建外几乎同构（`dashscope_provider.ts:157-196` vs `openai_compatible_provider.ts:204-245`），差异应改为描述符字段。
4. **默认走 OpenAI 兼容语义**，Responses 与 native 作为显式 opt-in；一旦上游再变，只改一个描述符文件。
5. **保留但收紧**：解包状态机是目前唯一能保证「逐字节等于 `JSON.parse(...).chapter_markdown`」的实现（`stream_json_unwrap.ts:78-87`），应当原样搬迁并保留其严格性，不要因为「偶发报错」而放宽成「透传裸文本」。
6. **把错误文案的 provider 名与 step 名做成模板参数**，而不是散落字符串（`provider_payload.ts:109` 现在写着 `"DashScope response is not a JSON object"`，却由 openai_compatible 复用 —— 这是已存在的错标）。

### 9.4 其它已知脆弱点（非 DashScope 专有）

1. 流式 `done` 帧的 model 取自 `reported?.model ?? ""`：若 provider 未调 `onOutcome`（例如 mock 之外的自定义实现），job 的 model 会是空串（`proposal_pipeline.ts:180-182`）。
2. 流式成功后 `accumulated.splice(0)` 与 `validate` 之间没有「已消费全部 delta」的断言；`onOutcome` 早于最后一帧到达时仍会落 completed（`streaming_generation.ts:246-252` 先 finish 再 onOutcome，服务端在此之后不再 yield）。
3. metadata 与 resident 段落重复把项目结构塞进 provider payload（§6.3）。
4. 净化不剥 markdown 围栏（§5.2 缺口）。
5. `dispose` 是空实现（§1.2），意味着「HTTP 连接释放」完全依赖 fetch 自身与 1s body cancel。
