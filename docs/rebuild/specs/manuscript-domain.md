# 稿件域行为规格（manuscript domain）

> 阶段 1 产出 · 2026-10-25
> 来源：`server/src/contexts/studio/` 现有实现（只读提取，未改动任何既有文件）
> 用途：全栈重建时，新实现照此执行即可行为等价。每条结论都带 `file:line`。
> 阅读约定：`file` 均相对仓库根；`file:12` 或承接上文的 `:12` 表示该文件第 12 行，区间 `:12-20` 含两端。
> 引用约定：跨行调用的区间取**调用首行**至 `);`，且区间内必须包含支撑结论的那个 token——否则读者按区间核对时看不到证据，会直接推翻结论（反例：`job_store_part.ts:289-294` 里 `1` 在 `:293`，若截至 `:292` 就把「带延迟」的唯一证据漏在括号外）。
> 凡标注「实现如此」的，都是当前代码的实际行为，不代表推荐做法。

## 0. 入口速查

| 能力 | 入口 | 文件 |
|---|---|---|
| 创建文档 | `DocumentService.newDocument` | `server/src/contexts/studio/application/document_service.ts:33` |
| 保存（含 autosave） | `DocumentService.storeDocument` | `server/src/contexts/studio/application/document_service.ts:86` |
| 修订推进（唯一写入点） | `advanceDocumentInTransaction` | `server/src/contexts/studio/infrastructure/db/document_revision_writes.ts:46` |
| 修订历史 / 单条 / 恢复 | `RevisionService` | `server/src/contexts/studio/application/revision_service.ts:22` |
| 字数 | `revisionWordCount` | `server/src/contexts/studio/domain/revision_word_count.ts:15` |
| 检索表达式 | `buildFtsMatchQuery` / `buildFtsLocateTerm` | `server/src/contexts/studio/application/fts_match_query.ts:22,39` |
| 索引与查询 SQL | `refreshDocumentIndex` / `matchDocumentIndex` / `rebuildDocumentIndex` | `server/src/contexts/studio/infrastructure/db/document_search.ts:32,118,57` |
| 保留策略 | `revision_retention.ts` | `server/src/contexts/studio/infrastructure/db/revision_retention.ts:1` |

对外 HTTP：

| 方法 + 路径 | 语义 | 文件 |
|---|---|---|
| `POST /api/projects/:projectId/documents` | 建文档（201） | `server/src/contexts/studio/interface/http/document_crud_routes.ts:33` |
| `PUT /api/projects/:projectId/documents/:documentId` | 冲突校验保存 | `document_crud_routes.ts:87` |
| `GET .../documents/:documentId/revisions` | 修订历史页 | `server/src/contexts/studio/interface/http/revision_routes.ts:32` |
| `GET .../revisions/:revisionId` | 单条修订全文 | `revision_routes.ts:78` |
| `POST .../revisions/:revisionId/restore` | 恢复 | `revision_routes.ts:100` |
| `GET /api/projects/:projectId/search` | 全文检索 | `server/src/contexts/studio/interface/http/project_routes.ts:173` |
| `DELETE .../documents/:documentId` | 删除文档（被快照引用时 409） | `document_crud_routes.ts:144` |

---

## 1. 修订链

### 1.1 唯一写入点

所有产生修订的路径（作者保存、autosave、恢复、AI 提案采纳、文档创建、导入）都必须经过两个事务内函数之一：

- 已有文档追加：`advanceDocumentInTransaction(tx, ...)`（`document_revision_writes.ts:46-136`）。
- 文档首次落库：`seedDocumentInTransaction(tx, ...)`（`document_seed_writes.ts:28-75`）。

两者都由调用方开事务：单条保存走 `DocumentStorePart.advanceDocument` 自己的事务（`server/src/contexts/studio/infrastructure/document_store_part.ts:106-115`），复合流程（提案采纳）直接复用同一 tx，避免二次事务（`server/src/contexts/studio/infrastructure/proposal_acceptance_store_part.ts:27-85`，事务模式 `behavior: "immediate"`）。

新实现必须保住这条：**修订行、文档 `current_revision_id` 指针、FTS 索引行、项目 `updated_at` 必须在同一事务内**。否则会出现指针指向不存在的修订、索引与正文不一致。

### 1.2 什么情况产生新修订

`advanceDocumentInTransaction` 的判定顺序是固定的（`document_revision_writes.ts:53-128`）：

1. **归属校验**：项目/文档必须属于当前 principal，否则 `NotFoundError`（`document_revision_writes.ts:53-54`；作用域谓词见 `studio_query_helpers.ts:38-48,70-86`）。404 的 message 必须带资源 id（旧实现是 `Project not found: <projectId>.` / `Document not found: <documentId>.`，`studio_query_helpers.ts:45,83`）；新契约把 `NOT_FOUND` 列入「必须显式传 message」的码（`server/src/contracts/errors.ts:210-218`），重建后这两个抛出点漏传 message 会编译失败，不会被静默降级成通用句。强制点不在那个类型别名，而在 `AppError` 的构造重载：`server/src/platform/http/error_envelope.ts:55-59`（必填组要求 `options.message: string`，可回落组 `options` 整体可选），`afterDelay` 同构（`:81-90`）。
2. **基础修订校验**：`document.currentRevisionId !== input.baseRevisionId` → `RevisionConflictError`，见 §3（`document_revision_writes.ts:55-57`）。
3. **读取当前修订行**：读不到则 `NotFoundError`（`:58-65`）。当前修订存在是硬前提。
4. **零写入幂等判定**（只对 `source === "author"`）：正文、`metadata_json`、生效标题三者全部相同 → 直接返回当前文档状态，**不建修订、不刷新索引、不动任何时间戳**（`:66-74`）。注意此判定与 `autosave` 无关，手动保存同样享受（测试名即 "writes nothing when an author save repeats the current body and metadata"，`server/tests/contexts/revision_retention.test.ts:21`）。
   - `metadata_json` 比的是**序列化字符串**，键序不同即视为不同（`document_service.ts:104` 的 `dumpJson`，比较在 `:69-71`）。
   - 标题在 service 层已归一化：`undefined`/`null`/纯空白 → `null`（`document_service.ts:100-103`），随后 `const title = input.title ?? document.title`（`:66`），因此"不传标题"必然等于现标题。
5. **大纲节拍预算**（仅 `kind === "outline"`）：`assertOutlineBeatCapacity`，超 5000 抛 422（`document_revision_writes.ts:75-78`；`structure_capacity_checks.ts:106-113`）。放在写修订之前，保证拒绝时零写入。
6. **生成新修订号与父指针**（见 1.3）。
7. **折叠**（仅 `autosave === true`）：删掉刚被取代的前一修订（下详）。
8. **推进文档指针**：`current_revision_id = 新修订`，`title`，`updated_at = now`（`:103-107`）。唯一索引冲突（`uq_document_identity`，`schema.ts:90`）→ `DuplicateDocumentError` → 409 `DOCUMENT_CONFLICT`（`:108-113`）。
9. **重建该文档的 FTS 行**（`:114-119`）。
10. **刷新项目 `updated_at`**（`:120`）。
11. **剪枝**（仅 `autosave === true`）：`pruneRetainedRevisions`（`:121-128`）。

文档创建时：插入文档行（`current_revision_id` 先为 null）→ 插入 `revision_number = 1`、`parent_revision_id = null`、`source = "author"` 的修订 → 回填文档指针 → 刷新索引（`document_seed_writes.ts:29-59`）。

### 1.3 `revision_number` 与 `parent_revision_id`

- 编号：`current.revisionNumber + 1`（`document_revision_writes.ts:94`）。文档内唯一索引 `uq_document_revision_number(document_id, revision_number)`（`schema.ts:111`）。
- 父指针：未折叠时 `= document.currentRevisionId`（保存所基于的修订）；折叠时 `= current.parentRevisionId`，即被删前驱的父（`:91-99` 的 `parentRevisionId: collapse ? current.parentRevisionId : document.currentRevisionId`）。
- `parent_revision_id` 为 `null` **只出现在每个文档的第一条修订**（`document_seed_writes.ts:43`）。除此之外任何为 null 的父指针都属数据损坏；剪枝时"父指针为空 → 不可折叠"正是靠这条判定（`revision_retention.ts:72`）。
- 剪枝时允许改写存活修订的 `parent_revision_id`（`revision_retention.ts:160-165`），这是"历史不可变"唯一允许的松动，且只改指针不改正文。

### 1.4 `source` 的取值与语义

closed enum 只有三个值：`author`、`ai-accepted`、`restore`（`domain/kinds.ts:15`；请求 schema 刻意不暴露 source，`studio_request_schemas.ts:18`）。

| 值 | 何时产生 | 依据 |
|---|---|---|
| `author` | 普通保存、autosave、文档创建、**legacy 导入** | `document_service.ts:112` 默认 `author`；`document_seed_writes.ts:47`；导入走 seed（`import_service.ts:70-81` → `project_store_part.ts:179-190`） |
| `ai-accepted` | 采纳已完成的 AI 提案 | `proposal_acceptance_store_part.ts:69-76`，metadata 固定为 `{"ai_job_id": jobId}` |
| `restore` | 恢复历史修订 | `revision_service.ts:83-88` |

**没有 `import` 这个值。** 任务的题面提到 `import`，但实现里导入的修订就是 `author` + `revision_number = 1` + `parent = null`。新实现若要引入 `import`，必须同步改 closed enum 与全部读取侧校验（`payloads.ts:124,165,178`；`studio_query_helpers.ts:183`），否则 `assertStoredRevisionSource` 会抛 `RevisionSourceInvariantError`（`domain/revision_source.ts:12-16`）。

读取侧对 source 做封闭校验：`assertStoredRevisionSource` 找不到即抛错，HTTP 不新增错误码而是落到不透明 500（`revision_source.ts:4-9`；`payloads.ts:124,165,178`；`studio_query_helpers.ts:183`）。

### 1.5 恢复的精确语义

请求：`POST /api/projects/:projectId/documents/:documentId/revisions/:revisionId/restore`，body `{ base_revision_id: string | null }`（`revision_routes.ts:100-125`；`studio_request_schemas.ts:116-119`）。

执行（`revision_service.ts:69-89`）：

1. 按 `(principal, project, document, revisionId)` 读目标修订，任一不匹配 → `NotFoundError`（`:76-81`；查询见 `document_store_part.ts:219-244`）。该读不写。
2. `metadata = safeLoadJson(revision.metadataJson)`，解析失败/非对象 → `{}`（`payloads.ts:41-52`）。
3. 调用 `storeDocument`，传入：历史正文、请求的 `baseRevisionId`、`metadata: { ...历史metadata, restored_from: revisionId }`、`source: "restore"`。
4. **不传 `title`** → 标题归一化为 null → 落到 `input.title ?? document.title` → **保留文档当前标题**（`revision_service.ts:83-88` 无 title 字段；`document_service.ts:100-103`；`document_revision_writes.ts:66`）。
5. `autosave` 不设 → 不折叠、不剪枝，纯追加。

结论：

- 恢复是**追加**，不是改写历史；目标的旧修订行原样保留。
- `restored_from` 放在**新修订的 `metadata_json`** 里（不是文档级、不是独立列），因此会出现在 `GET .../revisions/:id` 的 `metadata` 中。
- metadata 是**整体替换为历史值 + `restored_from`**，不与当前修订 metadata 合并。恢复后再看该修订的 metadata，就是"当年那份 + 一个键"。
- 标题保持不变（若作者想连标题一起回滚，需另发一次带 `title` 的保存）。
- `base_revision_id` 仍参与冲突校验，恢复没有"强制覆盖"分支。

### 1.6 保留策略（折叠 + 剪枝）

常量（`revision_retention.ts:24-37`）：

- `AUTOSAVE_COLLAPSE_WINDOW_MS = 30_000`（折叠窗口 30 秒）
- `REVISION_RETENTION_DAYS = 90`
- `REVISION_RETENTION_KEEP_NEWEST = 200`
- 单次剪枝批量上限 `PRUNE_BATCH_LIMIT = 200`

**折叠**（`document_revision_writes.ts:79-102`，判定在 `revision_retention.ts:67-80`）：当且仅当

- `input.autosave === true`，且
- 被取代的当前修订 `source === "author"`，且
- 其 `parent_revision_id !== null`（第一条修订永不折叠），且
- `0 <= now - createdAt <= 30_000ms`（未来时间戳视为不可折叠），且
- 没有任何 `snapshot_documents` 行引用它（`isSnapshotReferencedRevision`，`:50-57`）

成立时：先插入新修订（父 = 被折叠者的父），再 `DELETE` 被折叠行（`:100-102`）。于是**编号出现空洞**：链上父子关系仍连续，但 `revision_number` 不连续。

**剪枝**（`revision_retention.ts:106-170`）：仅 `autosave === true` 时触发（`document_revision_writes.ts:121-128`）。

1. 快速出口：`currentRevisionNumber <= 200` 直接返回 0（`:107-109`）。
2. 求边界：按 `revision_number DESC` 取 `OFFSET 199 LIMIT 1` 的值作为 `boundary`——即"第 200 新的那条"的编号（`:112-119`）。这里**按现存行数取，不按编号算术**，正是为了容忍折叠留下的空洞。
3. 截止时间：`now - 90 天`（`:123`）。
4. 候选条件（全部满足）：同文档、`source = "author"`、`revision_number > 1`（首条豁免）、`revision_number < boundary`（落在最新 200 之外）、`created_at < cutoff`、不是当前修订、无快照引用（`:124-140`，快照判断用相关子查询 `NOT EXISTS`）。
5. 单批最多 200 条，按编号升序（`:138-140`），剩余由后续 autosave 继续消化。
6. 删除前修复血缘：把所有"父指向被删行"的存活行改指向最近的存活祖先（`:144-165`），避免悬挂父指针破坏字数增量归因（`writing_stats_service.ts:74-82` 依赖父子关系算 delta）。
7. 批量 `DELETE`（`:166-168`），返回删除条数。

**不可变保护汇总**：被快照引用的修订永不折叠、永不剪枝（`revision_retention.ts:50-57,79,135`）；首条修订永不折叠（`:72`）也永不剪枝（`document_revision_writes.ts:132` 的 `gt(revisionNumber, 1)`）；当前修订永不剪枝（`:134`）；正文与 metadata 在任何路径下都不被改写。

### 1.7 一个字都不能少的顺序约束

- 冲突检查必须早于节拍预算与唯一索引检查（`document_revision_writes.ts:55` 早于 `:78` 与 `:104`），也就是"陈旧 base 永远先报 `REVISION_CONFLICT`，标题冲突排在其后"（规格要求见 `openspec/specs/novel-engine/spec.md:303-304`；测试 `server/tests/api/studio_document_save_conflicts.test.ts:16`）。
- 索引刷新必须在文档指针更新之后、同一事务内（`document_revision_writes.ts:114-119`）。折叠发生在索引刷新之前，因此索引写的是**新正文**，不会残留被删修订的正文（测试 `revision_retention.test.ts:131`）。

---

## 2. 字数口径

### 2.1 定义（唯一实现）

`revisionWordCount(markdown)`（`server/src/contexts/studio/domain/revision_word_count.ts:15-19`）：

```ts
const HAN_CHARACTER = /\p{Script=Han}/gu;
const WORD_RUN = /[\p{L}\p{N}_'-]+/gu;

hanCount  = markdown.match(HAN_CHARACTER)?.length ?? 0
runCount  = markdown.replace(HAN_CHARACTER, " ").match(WORD_RUN)?.length ?? 0
return hanCount + runCount
```

逐类：

| 字符类 | 计数 | 依据 |
|---|---|---|
| 汉字（`\p{Script=Han}`，含扩展区） | **每个 code point 计 1**，逐字独立 | `revision_word_count.ts:1,16` |
| 拉丁/其他字母、数字 | 按**极大连续 run** 计 1（`\p{L}` 与 `\p{N}`） | `:2,17` |
| 下划线 `_`、撇号 `'`、连字符 `-` | 属于 run 的一部分，不切词；`don't` = 1，`well-known` = 1 | `:2`（字符类含 `_'-`） |
| 标点（中英文全角半角）、空白、emoji、其他未列字符 | **计 0**，并作为分隔符切断 run | `:18`（只有两项相加，不匹配即不计） |
| 汉字与拉丁相邻 | 汉字先被整体替换为空格，必然切分 → 两侧各计 | `:17` 的 `replace(HAN_CHARACTER, " ")` |

函数是 total 的：空串返回 0，从不抛错（`:12-13`）。

### 2.2 存在哪、何时算、如何回填

- 存储：`document_revisions.word_count`（`schema.ts:107`，`integer("word_count")`，**可空**）。可空只因升级期回填（`document_store.ts:41-42` 注释）。
- 计算时机：**只在写修订时算一次**——`insertRevision` 内 `wordCount: revisionWordCount(input.contentMarkdown)`（`studio_query_helpers.ts:281`）。这是唯一写入点，创建/保存/恢复/提案/导入全部经过它。
- 读取时校验：`assertStoredRevisionWordCount` 拒绝 null、负数、非整数、非 safe integer（`revision_word_count.ts:30-35`），用于 `documentPayload` / `revisionPayload` / `revisionSummaryPayload` / 项目 shell 摘要（`payloads.ts:125,166,179`；`studio_query_helpers.ts:184`）。违规 → `RevisionWordCountInvariantError` → 不透明 500，不新增公开错误码。
- 历史数据 reconcile：`reconcileRevisionWordCounts`（`server/src/contexts/studio/infrastructure/revision_word_count_reconciliation.ts:35-90`）
  - 在**启动时、接受流量之前**执行：`openReconciledStudioDatabase` 的 `beforeJobRecovery` 里第一件事（`reconciled_studio_database.ts:27-31`）。
  - 按 `id ASC` keyset 游标批读，批大小 `REVISION_WORD_COUNT_BATCH_SIZE = 256`（`:11,44-57`）。
  - 对每行重算，仅当 `stored !== recomputed` 才更新（`:59-66`），因此幂等：一致的库零写入（测试 `revision_word_count_reconciliation.test.ts:155-156`）。
  - 每批一个事务；`result.changes !== 1` 直接抛 `RevisionWordCountInvariantError`（`:68-77`）。
  - 收尾再查一次是否仍有 NULL，有则抛错让启动失败（`:82-88`）。
  - 迁移本身只加列（`server/drizzle/0019_persist-revision-word-count.sql:1`：`ALTER TABLE document_revisions ADD word_count integer;`），值全部由 reconcile 填。
- 其他消费方一律复用同一函数，不另立口径：评审的章节字数 `chapterWordCounts`（`review_rules.ts:95-105`）、写作统计的增量（`writing_stats_service.ts:74-82`，delta = 本修订 − 父修订，首条修订按全量归因）。

### 2.3 边界样例（8 个）

| # | 输入 | 结果 | 拆解 |
|---|---|---|---|
| 1 | `""` | `0` | han 0 + run 0（`:16-18`） |
| 2 | `林黛玉进了贾府` | `7` | 7 个汉字各计 1，无拉丁 run |
| 3 | `Hello, 世界!` | `3` | han 2（世、界）+ run 1（`Hello`）；`,` `!` 与空格计 0 |
| 4 | `well-known don't 2024` | `3` | 三个 run：`well-known`、`don't`、`2024`（撇号与连字符在字符类内） |
| 5 | `🎉🎉` | `0` | emoji 既不是 Han 也不是 run 字符，也不产生 run |
| 6 | `「你好」，他说。` | `4` | han 4（你、好、他、说）；全角标点与全角逗号计 0 |
| 7 | `用Node写代码` | `5` | han 4（用、写、代、码）+ run 1（`Node`）；中英交界被替换切断 |
| 8 | `第一章 Chapter 1: 起点` | `7` | han 5（第、一、章、起、点）+ run 2（`Chapter`、`1`）；冒号与空格计 0 |

推导口径固定两步：① 数 `\p{Script=Han}` 的 code point 数；② 把汉字替换成空格后数 `[\p{L}\p{N}_'-]+` 的 run 数；两者相加。

---

## 3. 保存与冲突

### 3.1 请求字段

`PUT /api/projects/:projectId/documents/:documentId`（`document_crud_routes.ts:87-117`），body schema `documentSaveSchema`（`studio_request_schemas.ts:73-88`，`additionalProperties: false`）：

| 字段 | 类型 | 必填 | 语义 |
|---|---|---|---|
| `content_markdown` | `string` | 是 | 完整正文（不是 diff）。schema **没有** minLength/maxLength，空串合法 |
| `base_revision_id` | `string \| null` | 是（键必须存在） | 客户端最后一次读到的修订 id |
| `title` | `string ≤ 240` | 否 | 归一化后写文档标题；缺省/空白 → 保留原标题 |
| `metadata` | 自由对象 | 否 | **整体替换**修订 metadata；缺省 → 替换为 `{}` |
| `autosave` | `boolean`，默认 `false` | 否 | 打开折叠与剪枝（§1.6） |

没有 `source` 字段：传了会因 `additionalProperties: false` 被 422 拒绝（`studio_request_schemas.ts:87`；设计说明 `:18`）。

两处容易写错的默认值：

- `metadata` 缺省不是"保持不变"，而是 `dumpJson(input.metadata ?? {})` → 存成 `{}`（`document_service.ts:104`）。要保留 metadata 必须原样回传。
- `title` 缺省是"保持不变"（`document_service.ts:100-103` + `document_revision_writes.ts:66`）。标题与 metadata 的缺省语义**不对称**。

### 3.2 `base_revision_id` 为 null 表示什么

**没有"null 表示强制覆盖"这种语义。** 冲突判定是纯字符串比较：

```ts
if (document.currentRevisionId !== input.baseRevisionId) throw new RevisionConflictError(...)
```

（`document_revision_writes.ts:55-57`）

文档在创建时就已绑定第一条修订，`current_revision_id` 永不为 null（`document_seed_writes.ts:36-53`；项目 shell 读取时 null 直接视为损坏，`studio_query_helpers.ts:190-193`）。因此 `base_revision_id = null` **必然**与当前修订不等 → **必然 409**。

结论：该字段语义是"乐观并发令牌"，null 只是 schema 允许的偷懒写法（`restoreSchema` 同款，`studio_request_schemas.ts:116-119`），调用方必须回传真实 id。新实现若想让 null 表示"最后一次写入者胜"，属于改变契约，必须显式写明。

### 3.3 冲突判定与返回

- 判定点：`advanceDocumentInTransaction` 第三步之前，任何写之前（`document_revision_writes.ts:55-57`）。
- 结果：抛 `RevisionConflictError(currentRevisionId)`（`domain/exceptions.ts:30-38`）。
- HTTP 映射：`withStudioErrors` → 409，`code = REVISION_CONFLICT`，`message = "Document changed since the requested base revision."`，`details = { current_revision_id }`（`studio_error_mapping.ts:111-120`；响应 schema `studio_schemas.ts:62-83`）。
- **零写入**：异常在 `db.transaction` 回调里抛出 → better-sqlite3 回滚整个事务。因此当前修订、标题、正文、历史、检索索引、项目 `updated_at` 全部不变（契约见 `document_store.ts:173-178` 的注释；测试 `studio_revisions.test.ts`、`studio_document_save_conflicts.test.ts:16`）。
- 与标题冲突的优先级：base 检查在前，标题唯一约束冲突在后（`document_revision_writes.ts:55` vs `:104-113`）。陈旧 base + 重名标题 → 返回 `REVISION_CONFLICT`。
- 标题冲突返回 409 `DOCUMENT_CONFLICT`，无 details（`studio_error_mapping.ts:130-138`；`studio_schemas.ts:85-100`）。同样零写入。
- 这三类 409（`REVISION_CONFLICT` / `DOCUMENT_CONFLICT` / `SNAPSHOT_CONFLICT`）与 422 容量拒绝都**不带 `retry-after`**。该头在整套 API 里只有三个设置点：① 429 `RATE_LIMIT_EXCEEDED` 直接 `reply.header`（`shared/interface/http/auth_routes.ts:117`）——这是旧实现里**唯一不走 `AppError.responseHeaders` 的头部设置点**，重建统一信封时必须改为 `AppError.afterDelay(...)` 或显式传 `retryAfterSeconds`，否则限流响应丢失 `Retry-After`、客户端立刻重试并反向放大压力；注意这是**实现缺口**（少了一个本该有的头），方向与下文测试缺口相反（多了一个不该有的头），两者不能合并处理；② 409 `OPERATION_IN_FLIGHT`，仅当我们知道延迟时才带（`studio_error_mapping.ts:151-153`）——6 个抛出点里 `operation_in_flight.ts:66,82,123,130` 不带延迟，`job_history_service.ts:233`、`job_store_part.ts:289-294` 两个重试路径传 1；③ 503 `OPERATION_CAPACITY_EXCEEDED` 恒定带（`:170`）。不带头的第三类是「看着像该带头却偏偏不带」的 `SERVICE_UNAVAILABLE`（同为 503，持久层未配置），schema 注释已明确写「Retry-After is absent for persistence outages」（`studio_schemas.ts:202-206`）。
- 旧测试只断言了 503 一侧**存在**该头（`server/tests/api/error_envelope.test.ts:100`），没有任何用例断言冲突/容量路径**不存在**该头。反向断言需覆盖四个分支：非重试类 409、容量类 422、`SERVICE_UNAVAILABLE` 503、带延迟机制但未传值的 409——否则有人「把等待提示统一到所有错误上」时没有一个测试会红。**本次重建不新增专门测试**，这四个分支由 generation 切片的 INV-40 验收承接（`docs/rebuild/unchecked.md` 第 1 条，状态 accepted（延后））；承接点不写清就等同「不修」，那才是真正的缺口。

### 3.4 autosave 与手动保存的差异

| 行为 | 手动保存（`autosave` 缺省/false） | autosave（`autosave: true`） |
|---|---|---|
| 冲突检查 | 有 | 有 |
| 内容完全相同则零写入 | **有**（因为判定按 `source === "author"`，与 autosave 无关，`document_revision_writes.ts:67-74`） | 有 |
| 折叠 30 秒内的前一 `author` 修订 | 不做 | 做（`document_revision_writes.ts:79-102`） |
| 剪枝 >90 天且落在最新 200 之外的 `author` 修订 | 不做 | 做（`:121-128`） |
| 修订 `source` | `author` | `author` |
| 节奏预算检查 | 有 | 有 |

也就是说：autosave 的"额外"只有折叠与剪枝两项；幂等去重是两条路径共有。测试明确区分两者（`revision_retention.test.ts:102` "keeps a plain save's revisions out of the collapse and prune policy"）。

### 3.5 1 MiB 上限在哪判、超限行为

- 位置：Fastify 实例级 `bodyLimit: 1_048_576`（`server/src/apps/api/http_server_policy.ts:43`，由 `fastifyOptionsForHttpServerPolicy` 返回）。
- 判定的是**整个 HTTP 请求体**（JSON 编码后的字节数），不是 `content_markdown` 的字符数。路由 schema 对正文没有任何长度限制（`studio_request_schemas.ts:75`）。
- 超限行为：请求在进入 handler 之前被 Fastify 拒绝，返回 **413**，`code` 原样是 `FST_ERR_CTP_BODY_TOO_LARGE`（错误信封对 4xx 的 `FST_ERR_*` 透传，`server/src/shared/interface/http/error_envelope.ts:177-187`；测试断言 `server/tests/apps/api/inbound_request_lifetime.test.ts:274`）。
- 因此：不会创建事务、不会建修订、编辑器草稿不落库（前端保留草稿属前端契约）。**没有** 422 结构容量错误，也没有 `retry_after`。
- 另有一条独立的小额度：`document_metadata_bytes = 16_384`，在进 store 之前按 `JSON.stringify(metadata)` 的 UTF-8 字节数判定（`document_service.ts:105`；`structure_capacity.ts:68-77`），超限 422 `STRUCTURE_CAPACITY_EXCEEDED`。这两条不要混为一谈。
- 413 的 `error.code` 不是本项目的错误码：`FST_ERR_CTP_BODY_TOO_LARGE` 由 Fastify 定义，`statusCode` 就是 413（`server/node_modules/fastify/lib/errors.js:105-110`），本项目只是把它原样透传（`error_envelope.ts:177-187`），所以它**没有 `details`**、也不在 `ERROR_CODES` 里。
- 要注意这是两个不同的失败面：`registerUndeclaredRequestBodyPolicy` 在 **onRequest** 阶段拒绝"路由没有 body 契约却带了 body"的请求，返回 422 `VALIDATION_ERROR` + `details.errors[0].type = "undeclared_body"`，并加 `connection: close`（`server/src/apps/api/http_server_policy.ts:63-85`；测试 `server/tests/apps/api/inbound_request_lifetime.test.ts:160-204`，断言 handler 从未执行）。由于 onRequest 早于 body 解析，该 422 会先于 1 MiB 的 413 生效；且判定只看 `transfer-encoding` 是否存在与 `content-length > 0`，**不看实际字节数**（`http_server_policy.ts:50-56`），所以 422 与请求体大小无关——不存在"小体 422、大体 413"的分界，超过 1 MiB 同样先得 422。旧测试只发了 32 字节（`inbound_request_lifetime.test.ts:160-204`），**"无 body 契约 + 超 1 MiB"仍缺一条显式对照**，新实现应补测试把优先级钉死。

---

## 4. 快照

### 4.1 表结构与语义

- `project_snapshots`：`id / project_id / reason / created_at`，索引 `(project_id, reason, created_at)`（`schema.ts:120-137`）。
- `snapshot_documents`：每个文档一行，记录 `document_id / revision_id / document_kind / document_title / revision_metadata_json / position`，唯一索引 `(snapshot_id, document_id)`，读序索引 `(snapshot_id, position)`（`schema.ts:144-166`）。
- 外键保护：`document_id` 与 `revision_id` 都是 `onDelete: "restrict"`（`schema.ts:153,156`），所以被快照引用的文档/修订删不掉；删除文档会被显式拦截为 409 `SNAPSHOT_CONFLICT`（`document_store_part.ts:117-132`；`domain/exceptions.ts:41-46`）。
- `reason` 是自由字符串，实现只用到 `"review"` 与 `"export"`。
- 该 409 的文案在旧实现里有两条同值来源：domain 异常的 message（`domain/exceptions.ts:41-46`）与响应 schema 里**用单值 enum 钉死**的同一句 `"Document is referenced by an immutable snapshot."`（`studio_schemas.ts:222-240`）。旧 schema 里这样钉死 message 的**全仓共 6 处**（下列即全部，可逐一核对）：本处与 `OPERATION_CAPACITY_MESSAGE`（`studio_schemas.ts:160-164,222-240`），以及 `EXPORT_CAPACITY_MESSAGE`（`export_capacity_schemas.ts:26`）、`GENERATION_CAPACITY_MESSAGE`（`generation_capacity_schemas.ts:57`）、`STRUCTURE_CAPACITY_MESSAGE`（`structure_capacity_schemas.ts:31`）、`"Request validation failed."`（`unprocessable_entity_schemas.ts:50`）。重建若改由统一契约提供文案（`server/src/contracts/errors.ts:159-164`，其头部 `:1-4` 已声明状态/文案/重试策略"只在此处"），**这 6 处 enum 必须全部删除**，否则 wire 上的文案不会随契约改变（漏删一处，该类错误在 wire 上就永远是新契约改不到的旧文案）。但删除的理由是「文案只能有一个来源」，不等于「六处都会变字」：按当前契约，`EXPORT`/`GENERATION`/`VALIDATION` 三处新旧文案**逐字相同**，`SNAPSHOT` 只是改写（语义不变），`STRUCTURE` 去掉了 `Authoring` 一词，只有 `OPERATION_CAPACITY` 是从「容量耗尽」改成「操作过多，稍后重试」；所以不能因为「改完文案看起来没变」就断定 pin 已经删掉。

### 4.2 何时创建

**review**：只在一次评审**成功落地**的那个事务里创建（`review_records.ts:61-94`）：

1. 校验源仍可用：逐条比对 `(documentId, revisionId)` 仍存在，且正文/metadata 与捕获时逐字节相同，否则 `ReviewSourceInvalidatedError`（`:141-170`）。
2. 插 `project_snapshots`，`reason = "review"`，`createdAt = source.capturedAt`（`:71-79`）。
3. 逐条插 `snapshot_documents`（`:80`，`:172-196`）。
4. 插 `reviews` 与 `review_issues`（`:81-93`）。

评审失败不写任何快照（失败走 job 失败路径，不调用 persist）。快照与 job 完成事件同一事务（`review_store_part.ts:51-63`）。

**export**：只在**渲染成功之后**落地时创建或复用（`export_records.ts:112-138`）：

1. 先 `assertCapturedExportSource` 校验捕获源（`:113`）。
2. 无 chapter → `InvalidOperationError`（422）（`:114-116`）。
3. 若服务端捕获时已标记 `reuseSnapshotId`：校验该快照仍是本项目的 `export` 快照、仍在容量内、投影完全一致 → 复用；任何一项不满足都当**编程错误**抛错（`:117-128`）。
4. 否则取本项目最新 `export` 快照，若容量内且投影一致 → 复用（`:129-136`）。
5. 否则 `writeExportSnapshot` 新建：插快照（`reason = "export"`）→ 按 4000 行一批插 `snapshot_documents`（`:223-256`）。

`reuseSnapshotId` 由 `readExportSource` 在捕获阶段就框定（`export_store_part.ts:41-67`）：只有"最新 export 快照 + 容量内 + 投影相同"才带上，否则 null。

### 4.3 包含什么

- 包含**项目全部文档**（不限 kind，`review_records.ts:29-58`；`export_records.ts:33-76`），每个文档取当时的 `current_revision_id` 指向的修订。没有当前修订的文档直接没有行（review 用 `innerJoin`，export 则显式报错）。
- `position` 是**阅读序的 1-based 序号**，在捕获时按 `compareReadingOrder` 重排后重新编号（`review_records.ts:56`；`export_records.ts:73`）。不是 `documents.position` 原值。
- `document_kind` / `document_title` / `revision_metadata_json` 是**冗余快照**，用于快照自洽：即使文档标题后来改了，快照仍持旧标题（`review_records.ts:186-191`；`schema.ts:139-143` 注释）。
- 排序：写入按阅读序；读取 `ORDER BY position ASC, document_id ASC`（`export_records.ts:93`；`review_records.ts:126-131` 用 `position, id`）。

### 4.4 可枚举性、复用、失效

- **不可枚举**：没有任何 HTTP 路由暴露快照列表或快照详情（`interface/http` 里只有 409 冲突 schema 提到 snapshot，`studio_schemas.ts:221-234`）。快照 id 只能从评审响应、导出 artifact 的 `snapshot_id`、或 job result 里间接得到。
- **复用只发生在 export**：条件 = `reason === "export"` 且是最新一条 且 `source_documents ≤ 65536` 且 `source_bytes ≤ 16777216` 且投影逐字段相等（`export_records.ts:112-138`；`export_source_capacity.ts:35-51`；`export_source_identity.ts:11-31`）。
  投影相等要求：数组长度相同、逐项 `documentId / revisionId / kind / title / contentMarkdown / metadataJson / position` 全部相等、**顺序敏感**。所以只改排序（不产生新修订）也会新建快照（规格 `spec.md:914-916`）。
- review 快照**永不复用**，每次成功评审新建一条。
- 失效条件：
  1. 项目删除 → `project_snapshots` 级联删除 → `snapshot_documents` 级联删除（`schema.ts:150`）。
  2. 升级迁移删除"无证据"的孤儿快照：`review` 快照若无对应 `reviews` 行则删（`server/drizzle/0012_cleanup-orphan-review-snapshots.sql`）；`export` 快照若无 `exports`/`reviews`/`review_issues` 引用则删（`server/drizzle/0013_cleanup-orphan-export-snapshots.sql`）。
  3. 正常运行时快照不会被清理；被引用的修订也删不掉（RESTRICT）。

---

## 5. 全文检索

### 5.1 索引侧变换（精确规则）

`segmentFtsIndexText(text)`（`server/src/contexts/studio/domain/fts_segmentation.ts:39-55`）：

按 **code point** 遍历（`for...of`），对每对相邻字符 `(previous, char)`，当**同时满足**下列四条时，在两者之间插入**一个半角空格**：

1. `previous !== null`（首字符前不插）；
2. `isHan(previous) || isHan(char)`（至少一个是汉字）——`HAN_CHARACTER_PATTERN = /^\p{Script=Han}$/u`（`:24,29-31`）；
3. `WORD_CHARACTER_PATTERN.test(previous)`——`/[\p{L}\p{N}_]/u`（`:21`）；
4. `WORD_CHARACTER_PATTERN.test(char)`（同上）。

效果（`:33-38` 的注释即断言）：

- `林黛玉进了贾府` → `林 黛 玉 进 了 贾 府`
- `用Node写` → `用 Node 写`
- 纯拉丁文本**原样返回**（不插空格、不改大小写）
- 标点、空白、emoji 一个都不删、不替换；原有空格保持，也不会重复插入（空格不是 token 字符，条件 3/4 不成立）——`中 文` 仍是 `中 文`；只有相邻两字符都是 token 字符且至少一个为汉字时才插

索引行写的是**两列都变换**：`INSERT INTO document_search(... title, content) VALUES (..., segmentFtsIndexText(title), segmentFtsIndexText(content))`（`server/src/contexts/studio/infrastructure/db/document_search.ts:34-37`）。

底层 tokenizer 是隐式的 FTS5 `unicode61`（建表语句未带 tokenizer 参数：`server/drizzle/0000_init_persistence_core.sql:41` 的 `USING fts5(document_id UNINDEXED, project_id UNINDEXED, title, content)`）。因此 `document_id`、`project_id` **不参与检索**，`project_id` 只能作为普通 WHERE 条件过滤（全表扫描）。

### 5.2 查询侧变换（精确规则）

`buildFtsMatchQuery(query)`（`server/src/contexts/studio/application/fts_match_query.ts:22-29`）：

1. `query.toLowerCase()`（`toLowerCase`，不是 `toLocaleLowerCase`，不做 casefold；`:18-21` 说明这是为了与 unicode61 的折叠一致，`ß` 不展开为 `ss`）。
2. 用 `/[\p{L}\p{N}_]+/gu` 扫出所有 run（`fts_segmentation.ts:18`）——**注意撇号、连字符不在此字符类内**，所以 `don't` → `don` + `t`，`well-known` → `well` + `known`。
3. 每个 run 在"汉字 / 非汉字"边界处切组（`splitWordRun`，`:84-101`）：
   - 汉字组：把该组每个 code point 用**一个空格**连接，例如 `黛玉` → `黛 玉`（`encodeGroup`，`:103-105`）；
   - 非汉字组：原样保留。
4. 去重，保留首次出现（`[...new Set(elements)]`，`fts_match_query.ts:27`）。
5. 截断到 `MAX_MATCH_ELEMENTS = 3`（`:15,27`）。
6. 每个元素用**双引号**包起来，元素之间用**一个空格**连接（`:28`）。空格在 FTS5 里是隐式 AND。

`buildFtsLocateTerm(query)`（`:39-42`）：同样归约，取**第一个**元素，再 `restoreFtsDisplayText` 去掉汉字之间的空格（`fts_segmentation.ts:64-66`），得到给编辑器做文本定位的纯文本词。为 null 当且仅当 `buildFtsMatchQuery` 为 null（同一归约输入，`document_service.ts:137-142`）。

`restoreFtsDisplayText` 只做一件事：删除"汉字-空格-汉字"中间的那个空格（`HAN_SPACE_HAN_PATTERN`，`fts_segmentation.ts:27,64-66`）。它用于标题与摘录的出口（`document_search.ts:145-146`）。已知有损：作者原文里本来就有的"汉字 空格 汉字"会被吞掉（`:60-63` 注释承认这一点）。

### 5.3 引号 / 通配符 / token 上限 / 停用词

| 关注点 | 实际处理 | 依据 |
|---|---|---|
| 引号 | 元素字符集限定为 `\p{L}\p{N}_` 与内部空格，**不可能含 `"`**，所以拼进 `"..."` 无需转义 | `fts_match_query.ts:28` + `fts_segmentation.ts:18,103-105` |
| FTS5 操作符（`OR` `AND` `NOT` `NEAR`） | 括号、冒号、`*`、`^` 等都不是 run 字符，被直接丢弃；剩下的 `or`/`and` 变成**普通词**并参与 AND | `fts_segmentation.ts:18`（run 字符类不含运算符） |
| 列过滤 `title:(...)` | 同上，`:` 与 `(` 被丢弃，`title` 变成普通词 | 同上 |
| 通配符 `wolf*` | `*` 被丢弃 → 精确词 `wolf`；**没有前缀匹配能力** | 同上 |
| token / 元素上限 | 归约后最多 **3 个元素**（DR-030，性能理由：8 元素最坏 453–970ms，3 元素约 71ms） | `fts_match_query.ts:9-15,27` |
| 停用词 | **没有停用词表**（unicode61 默认不删停用词）。`the`、`了` 都会真匹配 | 建表语句无 `stopwords` 选项（`0000_init_persistence_core.sql:41`） |
| 大小写 | 查询侧 `toLowerCase`，索引侧由 unicode61 折叠；两侧口径一致 | `fts_match_query.ts:18-23` |
| 变音符号 | unicode61 默认 `remove_diacritics=1`，两侧都去重音（`café` ≈ `cafe`） | 同上（默认 tokenizer 参数） |
| 词干化 | 无（没开 porter）。`lanterns` ≠ `lantern` | 同上 |
| 中文子串 | 汉字组变成多 token 短语（`"黛 玉"`），FTS5 对带引号短语做**连续 token 序列**匹配，等价于子串命中 | `fts_segmentation.ts:6-12`；`fts_match_query.ts:26-28` |

### 5.4 查询 SQL、摘录、排序、分页

`matchDocumentIndex`（`document_search.ts:118-150`）：

- 总数：`SELECT COUNT(*) FROM document_search WHERE project_id = ? AND document_search MATCH ?`（`:124-127`）。**不是页大小**。
- 分页：`SELECT document_id, title, snippet(document_search, 3, '', '', ' … ', 16) AS excerpt ... ORDER BY rank, document_id ASC LIMIT ? OFFSET ?`（`:132-141`）。
  - 第 3 列 = `content`（0 起：`document_id`=0、`project_id`=1、`title`=2、`content`=3）。
  - 16 = snippet 的 token 窗口；中文每字 1 token，所以正好是 16 字窗口；拉丁是 16 词窗口。
  - 前后标记都是空串 → **无高亮标签**；截断标记固定为 `' … '`（U+2026 两侧各一空格）。
  - `rank` 是 FTS5 的 bm25 别名，升序 = 越相关越前；`document_id` 做稳定 tiebreaker。
  - 若命中只在 title 列，snippet 按 FTS5 语义取 content 列起始窗口（不是标题）——新实现需保持一致，否则"标题命中"的摘录会突然变空。
- 归约后为空：`document_service.ts:140-142` 直接返回 `{results: [], total: 0, next_offset: null}`，**不执行任何 SQL**。
- `next_offset`：`offset + 本页条数 < total ? offset + 本页条数 : null`（`document_service.ts:150-151`）。
- 参数边界：`q` 必填、`maxLength 200`；`limit` 默认 30、范围 1–100；`offset` 默认 0、范围 0–10000（`studio_request_schemas.ts:154-161`；路由 `project_routes.ts:186-197`）。

### 5.5 重建索引的入口与触发

- 唯一重建入口：CLI `novel-engine reindex` → `rebuildDocumentIndex`（`server/src/apps/cli/reindex_command.ts:26-36`）。
  - 实现：`DELETE FROM document_search` 清空 → 用 `documents INNER JOIN document_revisions ON current_revision_id` 全量重放 `refreshDocumentIndex`（`document_search.ts:57-73`）。幂等；没有当前修订的文档跳过（无正文可索引）。
- 漂移检测：`documentIndexReconciliation` 只比两个计数（文档数 vs 索引行数），供 `doctor` 报告（`document_search.ts:92-105`；`doctor_command.ts:113`）。**不自动修复**。
- 启动流程**不会**重建索引：`openReconciledStudioDatabase` 只做字数回填、导出发布对账、任务恢复（`reconciled_studio_database.ts:21-34`）。因此索引漂移只能靠人工 `reindex` 修。
- 触发条件（设计意图）：升级、索引损坏、手工改库、迁移后。正常写入路径不需要重建：每次文档创建/保存/删除都在同一事务里刷新或清除该文档的索引行（`document_seed_writes.ts:54-59`；`document_revision_writes.ts:114-119`；`document_store_part.ts:129`）；项目删除清整个项目的索引行（`project_store_part.ts:205`）。

### 5.6 八个查询样例与预期命中

前提：库里有如下文档（正文/标题均已按 §5.1 变换后入索引）。

| # | 文档 | 标题 | 正文（节选） |
|---|---|---|---|
| A | 中 | `第一章` | `林黛玉进了贾府，见了贾母。` |
| B | 中 | `第二章` | `他说：「你好，世界。」` |
| C | 混排 | `笔记` | `用Node写脚本很快` |
| D | 英 | `The Lantern` | `A lantern glows. Lanterns hang. Don't go.` |

| # | `q` | 归约后的 MATCH 表达式 | 预期命中 | 说明 |
|---|---|---|---|---|
| 1 | `黛玉` | `"黛 玉"` | A | 子串命中；索引里是 `林 黛 玉`，短语 `黛 玉` 相邻成立 |
| 2 | `林黛玉` | `"林 黛 玉"` | A | 三字短语；若只写 `黛玉` 的文档则**不**命中 |
| 3 | `世界` | `"世 界"` | B | 句中子串命中 |
| 4 | `用Node写` | `"用" "node" "写"` | C | 中英交界切成三个元素，隐式 AND；`node` 已被 `toLowerCase` |
| 5 | `lantern` | `"lantern"` | D | 精确 token；`Lanterns` 是另一个 token，**不**因它命中 |
| 6 | `Lanterns` | `"lanterns"` | D | 只命中正文里 `Lanterns` 那处（第 5 条与第 6 条互不覆盖） |
| 7 | `dragon OR wolf` | `"dragon" "or" "wolf"` | 无 | `OR` 不是操作符而是**必含词**；三词同时出现的文档才命中。这是最容易误解的一条 |
| 8 | `don't` | `"don" "t"` | D | 撇号被两侧字符类同时排除，切成两个元素；索引侧 unicode61 也把 `Don't` 切成 `don`+`t`，故仍命中 |

补充两条（建议也进测试）：

| # | `q` | 表达式 | 预期 |
|---|---|---|---|
| 9 | `Straße` | `"straße"` | 命中含 `Straße` 的文档；**不**命中 `Strasse`（`ß` 不展开） |
| 10 | `!!! ???` | `null`（无可归约元素） | 200 + `{results: [], total: 0, next_offset: null}`，不执行 SQL |

---

## 6. 容量与分页

### 6.1 固定容量上限（全部为"包含式"：等于上限允许，超过才拒）

**编作结构**（`server/src/contexts/studio/domain/structure_capacity.ts:15-22`）

| 资源 | 上限 | 检查点 |
|---|---|---|
| `project_documents`（每项目文档数） | 2 500 | 建文档前（`structure_capacity_checks.ts:18-33`；调用 `document_store_part.ts:80`） |
| `project_volumes`（每项目卷数） | 100 | 建卷前（`:35-50`） |
| `volume_chapters`（每卷章节数） | 2 000 | 建章节 / 章节换卷 / 卷合并（`:56-99`） |
| `project_settings_bytes` | 16 384 | 项目设置写入前（`structure_capacity.ts:68-77`） |
| `document_metadata_bytes` | 16 384 | 建文档 / 保存前（`document_service.ts:57,105`） |
| `outline_beats`（大纲节拍数） | 5 000 | 建文档 / **每次修订推进**（`document_revision_writes.ts:78`） |

检查方式统一是 `LIMIT limit + 1` 的有界投影再 `count()`（`structure_capacity_checks.ts:11-17` 注释），拒绝时抛 `StructureCapacityExceededError`，`observed` 被钳到 `limit + 1`（`structure_capacity.ts:58`），HTTP 422 `STRUCTURE_CAPACITY_EXCEEDED` + `details{resource,limit,observed}`（`studio_error_mapping.ts:66-77,176-178`）。已存数据不回扫、不追溯（`structure_capacity.ts:9-14` 注释）。

**导出**（`server/src/contexts/studio/domain/exceptions.ts:81-86`）

| 资源 | 上限 |
|---|---|
| `source_documents` | 65 536 |
| `source_bytes` | 16 777 216（16 MiB） |
| `artifact_bytes` | 67 108 864（64 MiB） |
| `manifest_bytes` | 16 384 |

**其他**

| 资源 | 上限 | 依据 |
|---|---|---|
| 单次 HTTP 请求体 | 1 048 576（1 MiB） | `server/src/apps/api/http_server_policy.ts:43` |
| 工件下载并发池 | 134 217 728（128 MiB，字节加权） | `application/artifact_download_capacity.ts:3` |
| 生成 prompt 字节（system + user 合并） | 8 388 608 | 常量 `domain/generation_capacity_policy.ts:2`；在**创建 provider 之前**判定，超限 422 `GENERATION_CAPACITY_EXCEEDED`（`application/generation_capacity.ts:10-42`；`studio_error_mapping.ts:182-184`） |
| Lorebook 抽取单段 code point | 100 000 | `domain/generation_capacity_policy.ts:9` |
| Legacy 导入 story.yaml | 262 144 | `ports/legacy_workspace_reader.ts:30` |
| Legacy 导入单章 | 4 194 304 | `:31` |
| Legacy 导入整工作区 | 67 108 864 | `:32` |
| Legacy 导入章节数 | 2 000 | `:33` |
| Legacy 导入目录项 | 4 096 | `:34` |
| 标题长度 | 240 字符 | `studio_request_schemas.ts:50,66,77` |
| 项目描述长度 | 10 000 字符 | `:51,58` |
| 检索 `q` 长度 | 200 字符 | `:156` |
| Lore 别名 | 每条 240 字符、最多 64 条 | `interface/http/lore_schemas.ts:20` |

### 6.1.1 与上下文组装规格的边界

上下文组装（resident context 三段、lorebook 命中与 4000 字符预算、prompt 净化、写作语言推断）属于生成域的规格，不在本文范围。稿件域只负责"收到的正文如何落成修订"，两边唯一的接触面是：

- 提案正文在**落地前**已被 `sanitizeProposalMarkdown` 处理（`application/proposal_landing.ts:117`），写进 job result 的就是净化后的文本。
- 采纳提案时，稿件域**不做任何净化或长度处理**，把 `result.proposal_markdown` 原样写进新修订（`infrastructure/proposal_acceptance_store_part.ts:47-53,69-76`）。因此净化策略若漏掉某种结构（例如 markdown 代码围栏），该结构会原样成为 `content_markdown` 并参与字数统计与全文索引。
- 字数统计只作用于最终的 markdown：反引号、`…`、空白都计 0（§2.1），围栏本身不改变计数，只会改变正文语义。

**没有上限的量**（新实现不要凭空加）：

- 项目总数：无配额（`projectCatalogStore` 只做分页，`ports/project_catalog_store.ts:19-29`）。
- 单文档修订总数：无硬上限，只由保留策略（§1.6）间接约束。
- 项目导出工件条数：无配额，只受目录分页与 source/artifact 字节限制。
- 评审条数、任务条数：无配额，只分页。

### 6.2 游标结构与排序键

所有"游标分页"共用一套编解码：`makeKeysetCursor`（`server/src/shared/interface/http/canonical_cursor.ts:87-152`）。

- 线格式：`base64url(JSON.stringify([version, ...scopes, number, id]))`（`:22-28,138`）。
- 解码严格性（`:34-51`）：长度 1–1024、字符集 `^[A-Za-z0-9_-]+$`、必须是**规范** base64url（重新编码须逐字节相等）、必须是合法 UTF-8 JSON、元组长度必须等于 `scopeCount + 3`、`version` 必须匹配、`number` 必须是 `>= minNumber` 的 safe integer、`id` 长度 1–128。
- `scopes` 必须与路由参数逐一相等（`:118-120`），否则 422。这防止把 A 项目的游标用到 B 项目上。
- 失败一律 422 `VALIDATION_ERROR`，`details.errors[0] = {field:"cursor", message:"value is invalid", type:"invalid"}`（`:10-19`）。

| 资源 | 元组 | 排序键（SQL） | 比较谓词 |
|---|---|---|---|
| 修订历史 | `[1, projectId, documentId, revisionNumber, id]`（`revision_cursor.ts:4-11`，minNumber 1） | `revision_number DESC, id DESC`（`revision_page_queries.ts:35-36`） | `revision_number < b` OR (`= b` AND `id < b.id`)（`:26-32`） |
| 项目目录 | `[1, ownerId, updatedAtMs, id]`（`project_catalog_cursor.ts:4-11`，minNumber 0） | `updated_at DESC, id DESC` | 同上式 |
| 导出目录 | `[1, projectId, createdAtMs, id]`（`export_cursor.ts:4-11`） | `created_at DESC, id DESC` | 同上式 |
| 评审历史 | `[1, projectId, createdAtMs, id]`（`review_cursor.ts:4-11`） | `created_at DESC, id DESC` | 同上式 |
| 任务历史 | `[1, projectId, createdAtMs, id]`（`job_cursor.ts:4-11`） | `created_at DESC, id DESC` | 同上式 |

`next_cursor` 的生成方式一致：多取一行（`limit + 1`），若取到第 `limit + 1` 行，就把第 `limit` 行（本页最后一行）的位置作为游标（`document_store_part.ts:203-215`；`export_records.ts:171-187`）。没有下一页时返回 `null`。

**检索不用游标**：用 `limit` + `offset`（`document_service.ts:143-151`；`ports/document_store.ts:115-120` 注释）。

### 6.3 稳定性保证（及各处的真实边界）

| 分页 | 保证 | 边界/已知弱点 |
|---|---|---|
| 修订历史 | `(revision_number DESC, id DESC)` 全序，keyset 严格小于 → 同一历史状态下**不重复、不跳过** | 折叠/剪枝会删除"已翻过页"里的行：翻页过程中历史变短时，后续页不会重复但总数会少；已返回的行也可能已被删（§1.6 的正常行为） |
| 检索 | `(rank, document_id ASC)` 全序 + `total` 同表达式 `COUNT(*)`，`next_offset` 只在还有剩余时非 null | offset 分页对索引变化敏感：两页之间发生保存/删除会重复或跳过条目。可靠性边界写在对端口的注释里（`ports/document_store.ts:216-219`） |
| 项目目录 | `(updated_at DESC, id DESC)`；同一毫秒用 id 兜底 | 项目被保存会改变 `updated_at`，导致它"跳到队首"，翻页时会重复出现一次 |
| 导出/评审/任务 | `(created_at DESC, id DESC)`；创建后 `created_at` 不变 | 无重复风险（只追加） |
| 全部分页 | `limit` 越界（<1 或 >100）→ `RangeError`（`ports/page_limit.ts:26-32`），路由层 schema 已先拦成 422 | 默认值：修订/项目/导出/评审/任务 50，检索 30 |

---

## 7. 旧测试对应

| # | 路径 | 覆盖内容 | 移植判断 |
|---|---|---|---|
| 1 | `server/tests/contexts/revision_retention.test.ts` | 幂等零写入、折叠窗口、快照钉住、plain save 不折叠、只改 metadata 仍写 | 可直接移植 |
| 2 | `server/tests/contexts/revision_retention_prune.test.ts` | 空洞下的 newest-200 边界、批量剪枝 | 可直接移植 |
| 3 | `server/tests/api/studio_document_save_conflicts.test.ts` | base 冲突优先于标题冲突、零写入 | 可直接移植 |
| 4 | `server/tests/api/studio_revisions.test.ts` | 保存/历史/单条/恢复的 HTTP 契约 | 可直接移植 |
| 5 | `server/tests/api/studio_revision_pagination_contract.test.ts` | 修订分页与 `next_cursor` | 可直接移植 |
| 6 | `server/tests/api/studio_revision_cursor_contract.test.ts` | 游标篡改/跨文档/版本不匹配 → 422 | 可直接移植 |
| 7 | `server/tests/api/studio_documents.test.ts` | 建/读/删文档、快照冲突、身份唯一 | 可直接移植 |
| 8 | `server/tests/api/studio_project_revision_pointer_integrity.test.ts` | 指针与修订行一致性 | 可直接移植 |
| 9 | `server/tests/api/studio_search.test.ts` | 排序、16 token 摘录、AND、空查询、事务内索引刷新、删除清理 | 可直接移植 |
| 10 | `server/tests/api/studio_search_bounds.test.ts` | `q` 长度/limit/offset 边界 | 可直接移植 |
| 11 | `server/tests/api/studio_search_pagination.test.ts` | `total` / `next_offset` 语义 | 可直接移植 |
| 12 | `server/tests/api/studio_search_ranking.test.ts` | bm25 排序与 tiebreaker | 可直接移植 |
| 13 | `server/tests/contexts/fts_match_query.test.ts` | 纯函数：3 元素上限、去重、CJK 短语、运算符剥离 | 可直接移植 |
| 14 | `server/tests/contexts/revision_word_count.test.ts` | 字数口径（含中英混排） | 可直接移植 |
| 15 | `server/tests/contexts/revision_source.test.ts` | source 封闭枚举与不透明失败 | 可直接移植 |
| 16 | `server/tests/contexts/export_source_identity.test.ts` | 快照投影相等的逐字段/顺序敏感 | 可直接移植 |
| 17 | `server/tests/contexts/revision_service.test.ts` | 恢复语义（追加、`restored_from`） | 需按新结构重写（依赖旧 `DocumentService` 注入形状） |
| 18 | `server/tests/contexts/revision_store_pagination.test.ts` | store 层 keyset 翻页 | 需按新结构重写（直连 `DocumentStorePart`） |
| 19 | `server/tests/db/revision_word_count_reconciliation.test.ts` | 回填/幂等/批次/失败即崩 | 需按新结构重写（依赖旧迁移与 harness） |
| 20 | `server/tests/contexts/review_store_transactions.test.ts` | 评审 + 快照 + job 同事务 | 需按新结构重写（依赖旧 tx 事务封装） |

---

## 8. 规格与实现的差异

逐条列出 `openspec/specs/novel-engine/spec.md` 与 `server/src/contexts/studio/` 实现不一致或规格未定义的地方。新实现必须**显式选择**一种，并在测试里钉住。

**时效说明**：本节描述的是**切换前**（2026-10-25 旧实现）的状态。重建落地后这些差异不再成立，D-1…D-8 应作为历史记录阅读，不要再当作现行缺陷；若届时要保留，请在节首补上「已解决于 <版本/提交>」，否则「当前」一词会静默过期。

### D-1 413 的错误码

- 规格：`413 PAYLOAD_TOO_LARGE`（`spec.md:4790-4791`，场景 `:4813`）。
- 实现：状态码 413 一致，但 `error.code` 是 Fastify 的 `FST_ERR_CTP_BODY_TOO_LARGE`（状态码定义 `server/node_modules/fastify/lib/errors.js:105-110`；透传分支 `shared/interface/http/error_envelope.ts:177-187`；测试 `server/tests/apps/api/inbound_request_lifetime.test.ts:274`）。`PAYLOAD_TOO_LARGE` 这个码在本实现里根本不存在。
- 影响：客户端若按 `code` 分支会落空。

### D-2 零写入去重的适用范围

- 规格：把"内容相同则零写入"写在 `autosave` 段落里（`spec.md:283-287`）。
- 实现：判定条件是 `source === "author"`，**与 `autosave` 无关**（`document_revision_writes.ts:67-74`），因此手动保存重复内容也不产生修订（测试名 `server/tests/contexts/revision_retention.test.ts:21`）。
- 影响：前端"点保存 → 修订数 +1"的预期在实现里不成立。

### D-3 metadata 缺省即清空

- 规格：只说保存"接受可选的新标题与 metadata"（`spec.md:274-281`），未定义省略时的行为。
- 实现：省略 `metadata` → 存 `{}`（`document_service.ts:104`）；省略 `title` → 保留原值。两者语义不对称。
- 影响：任何只发正文的客户端都会静默丢掉 metadata（包括 `ai_job_id`、`restored_from` 这类由服务端写入的键）。

### D-4 文档列表排序

- 规格：`kind` → `position` → 创建时间（`spec.md:465-467`，场景 `:477-481`）。
- 实现：`compareReadingOrder`——章节永远排在最前，章节内按 `volume.position` 再按 `position`；非章节按 kind 字典序再按 `position`；最后用 `createdAt`、`id` 兜底（`studio_query_helpers.ts:102-120`）。
- 影响：ADR-0005 的卷序优先覆盖了规格文字的"先按 kind"。

### D-5 修订编号的连续性

- 规格 A：每次保存编号恰为当前编号 +1、链不断（`spec.md:276-278`，场景 `:320-324`）。
- 规格 B：承认折叠会造成编号空洞（`spec.md:361-365`）。
- 实现：取规格 B——折叠时新修订编号 = 被折叠者 +1，随后被折叠行被删（`document_revision_writes.ts:91-102`），于是编号**唯一且单调但有空洞**，父指针仍连续。
- 建议：新实现明确写"编号唯一、单调递增、允许空洞；父子链不得断开"，否则两条规格无法同时满足。

### D-6 "current revision 不可折叠"的解释

- 规格：`current revision` 永不折叠（`spec.md:306-307`）。
- 实现：autosave 会删除"刚被取代的那条"——也就是判定前一瞬间的 current（`document_revision_writes.ts:79-102`）。若按字面理解规格，折叠永不生效。
- 建议：把规格中的 `current` 明确为"剪枝/折叠判定完成后的 current"。

### D-7 "token" 与"元素"的术语

- 规格：检索输入归约为"最多 3 个 token"（`spec.md:379-381`）。
- 实现：上限是 3 个**匹配元素**，而一个汉字元素展开后是多 token 的短语（`"黛 玉"` 是 2 个 token）（`fts_match_query.ts:15-28`；`fts_segmentation.ts:103-105`）。
- 影响：若新实现按"token 数"截断，`黛玉 宝玉` 会被截成半个短语，检索行为改变。

### D-8 规格未定义：快照内 `position` 的口径

- 规格只要求快照保存"有序的文档投影"（`spec.md:913-918`），未定义 `position` 存什么。
- 实现：存**阅读序 1..n 的重编号**，不是 `documents.position`（`review_records.ts:49-57`；`export_records.ts:57-75`）。
- 影响：直接搬 `documents.position` 会让导出章节顺序错乱（章节原 position 是卷内序号，会跨卷重复）。
