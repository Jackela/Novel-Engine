# Novel Engine 魔鬼代言人评审 · 修复清单（Fix Backlog）

- 评审日期：2026-10-01
- 评审基线：`main` @ `607a092e`（server `0.8.0`）；工作区当时仅有既存未跟踪目录 `.commandcode/`、`.zcode/`
- 方法：9 个并行 subagent —— 5 个角色评审（产品伪需求 / 用户可用性 / 架构工程 / 运维与安全 / 竞争与可持续）+ 4 个功能域审查（编辑器与写作核心 / AI 生成审阅 / 搜索导入导出 / 平台与规格符合性）。关键结论由编排者交叉复核；部分结论带实测证据（隔离 DB 与内存库复现、针对性 vitest、只读网络核验、容器只读演练）。
- 文件性质：本文件是**可执行的修复 backlog**，不是完整评审报告。它是给"清空上下文后的新 AI"逐条修复用的工作单；每条包含证据、修复方向、验收标准与验证命令。

> 行号基于评审基线 `607a092e`，代码演进后会漂移。若行号失配，请按条目中提到的符号/文件名重新定位，不要凭行号断言"问题不存在"。

---

## 0. 如何使用本文件（给执行修复的 AI）

1. **先读仓库规则**：根 `AGENTS.md`（架构契约、禁区、命名、验证入口）、`docs/agents/change-evidence.md`（证据标准）、`docs/agents/ci-gates.md`（门禁语义）。
2. **一次只做一条**：按 `DR-###` 编号领取；一条就是一个可独立提交的任务，不要顺手扩大范围（AGENTS.md：One task is one audit finding）。
3. **先复现，再修**：先按"验证"字段跑出现状（失败或行为证据），修复后同一命令必须通过；需要新增回归测试的条目已注明。
4. **遵守禁区**：不得修改 `.env*`、`config/env/*`、`data/*.sqlite3`、`data/backups/*`、`AUDIT_REPORT_Linus.md`、`Makefile`、`justfile`。迁移只能用 `pnpm --dir server db:generate --name <semantic-slug>`；改动 HTTP 路由后必须 `pnpm --dir server openapi:snapshot` 重新生成基线。
5. **收尾验证**：至少跑该条目"验证"中的命令 + `pnpm --dir server gates`；跨前后端的条目再加 `pnpm --dir frontend type-check && pnpm --dir frontend test:unit`。不得通过削弱断言来"修复"测试。
6. **交付记录**：完成后在本条目下追加一行 `- [x] <日期> <SHA> <命令与结果摘要>`，不要删除原始证据描述。

### 等级定义

| 等级 | 含义 | 处理要求 |
|---|---|---|
| **P0** | 数据丢失、安全漏洞、或"中文用户必然失败"的可信度问题 | 应立即修复，修完才做其他 |
| **P1** | 高频功能缺陷、规格承诺落空、运维/质量硬伤 | 按批次推进 |
| **P2** | 质量打磨、可见性、清理项 | 有空时清理 |
| **DEC** | 需要人工/产品决策，不是纯代码任务 | 由 Owner 决策后才可转为代码任务 |

### 状态图例

`- [ ] 未开始` / `- [~] 进行中` / `- [x] 已完成` / `- [!] 阻塞（写明原因）`

---

## 1. 汇总表

### P0（9 条）

| ID | 领域 | 一句话 | 主要证据锚点 |
|---|---|---|---|
| DR-001 | 前端保存 | 保存失败一次后自动保存永久熔断，无重试入口 → 静默丢字 | `frontend/src/features/studio/hooks/useDocumentDraftAutosave.ts:83-90` |
| DR-002 | 前端保存 | 切换文档/关闭页面会丢弃 1.5s 内的编辑，且无离开守卫 | 同上 `:92,149`；`beforeunload` 全仓 0 命中 |
| DR-003 | 搜索 | 中文全文搜索静默失效（FTS5 默认 unicode61，整段中文=1 token） | `server/drizzle/0000_init_persistence_core.sql:41`；实测"林黛玉"0 命中 |
| DR-004 | 搜索 | 无 FTS 重建/校验通道；doctor 查不出索引问题（DR-003 的前置依赖） | 全仓无 rebuild/integrity-check 路径 |
| DR-005 | 计数 | 中文字数按"标点分段"计（约 1/7 低估），污染统计、薄章阈值与 token 估算 | `server/src/contexts/studio/domain/revision_word_count.ts:3` |
| DR-006 | AI | 流式生成中途失败丢弃全部已生成文本且不重试（双端全损） | `server/.../streaming_generation.ts:209`；`useProposalStreamSession.ts:199-204` |
| DR-007 | AI | "生成整本"会静默覆盖手写/导入/恢复的章节并自动接受 | `frontend/src/features/studio/hooks/wholeBookPlan.ts:17-19`（注释自认） |
| DR-008 | 安全 | 公网/LAN 首启无 setup token，第一个访问者可抢占 Owner | `server/src/shared/interface/http/auth_routes.ts:128-155`；容器实测 201 |
| DR-009 | 安全 | 信任代理配置下 X-Forwarded-For 伪造使登录限速归零，可无限爆破 | `shared/infrastructure/rate_limit/client_identity.ts:160-170`；实测 16 次 0 次 429 |

### P1（30 条）

| ID | 领域 | 一句话 |
|---|---|---|
| DR-010 | AI/UX | 停止生成=全部丢弃；接受提案不可撤销；reject 后无法找回文本 |
| DR-011 | 编辑器 | 修订历史无法阅读正文、无 diff，"恢复"是不可预判的盲操作 |
| DR-012 | 编辑器 | 冲突解决只能整体丢弃/整体覆盖，无法查看对方版本 |
| DR-013 | 导出 | DOCX 无中文字体/首行缩进/分页/TOC，且章节标题重复出现 |
| DR-014 | 导出 | EPUB `dc:language=en`、缺 `dcterms:modified`、零 CSS，不合 EPUB 3 |
| DR-015 | 导出 | Markdown 导出丢失章节标题，且只有 chapter 入导出（笔记/设定/大纲拿不到） |
| DR-016 | 编辑器 | 无查找/替换、无 Ctrl+S、无快捷键，搜索结果不定位命中位置 |
| DR-017 | 结构 | 卷（Volume）后端齐全但 UI 零入口 → 多卷、放置、按卷导出全部不可达 |
| DR-018 | 项目 | 项目删除端点已有但 UI 无入口（API 死代码） |
| DR-019 | 认证 | 无密码确认字段、无修改密码入口、无"无法找回"提示（单账号永久锁死风险） |
| DR-020 | 会话 | 会话过期静默 401 跳转，无提示、丢草稿与位置 |
| DR-021 | i18n | 服务端错误消息英文直出（含内部标识符），中文用户无法自助 |
| DR-022 | AI/设置 | 未配置的 provider 可选且无提示；model 不可见；未配置报"不支持流式"误导 |
| DR-023 | AI | 提示词无语言跟随，mock 全英文、清理器只删英文模板 → "双语"实为"界面双语" |
| DR-024 | AI | Review 恒用 env 级 provider，而非项目所选 provider，UI 不标注 |
| DR-025 | AI | review 超时仅 30s，长稿审阅必超时并白烧重试 |
| DR-026 | AI | 180s 绝对截止会杀掉健康长流；无心跳帧；SSE 内错误帧被静默忽略 |
| DR-027 | AI | 生成端点无幂等键，重复提交=双份 job + 双份计费 |
| DR-028 | AI/用量 | usage 语义误导（instruction 词数当 prompt tokens）、`estimated_cost` 死列、无预算护栏 |
| DR-029 | 搜索 | 搜索 UI 无空态、无计数、无命中定位，结果硬截断 30 条 |
| DR-030 | 性能 | 8-token 长查询冻结事件循环 453–970ms（实测），搜索无输入上限 |
| DR-031 | 运维 | 每次启动写全量备份且永不清理；重启循环可撑爆磁盘 |
| DR-032 | 运维 | `doctor` 并非只读：会迁移/备份/取锁，且把错误消息塞进 quick_check 字段 |
| DR-033 | 运维 | `.env.example` 占位密钥可通过 production 守门；README 写 "sample value" 不一致 |
| DR-034 | 运维 | 反代三陷阱：无 trusted proxies 时登录 DoS；TLS 下 setup 403；trustProxy 缺失 |
| DR-035 | 运维 | 未认证暴露 `/openapi.json`（125KB 全量契约）与 `/version` 指纹 |
| DR-036 | 运维 | 备份边角：校验产生 `-shm/-wal` 残留、无备份后自检、明文未在 UI 说明 |
| DR-037 | 导入 | 导入 hash 含绝对路径 → 同一目录内容变更/搬家即重复建项目；标题丢失变 Chapter N；无前端入口 |
| DR-038 | 工程 | 关键回归缺失：autosave 失败路径、CJK 搜索、413 保存均无用例；i18n 测试把文案钉死 |
| DR-039 | 文档 | 文档-实现对齐：README 发布态过时、guides 宣称 diff/跳转命中/Move to volume 不成立、spec/CONTEXT 漂移 |

### P2（9 条）

| ID | 领域 | 一句话 |
|---|---|---|
| DR-040 | 运维 | dev 模式未配置密钥时每次重启轮换会话密钥，用户被静默登出 |
| DR-041 | 运维 | 容器以 root 运行、无只读根/能力收敛；无 `/metrics`、无 `LOG_LEVEL` |
| DR-042 | 编辑器 | 快照对用户不可见；审阅历史不可点开（端点已有）；文档被快照引用时的 409 无指引 |
| DR-043 | 编辑器 | Beat 关联是"背出标题"的自由文本；多 outline 文档时规则不可知 |
| DR-044 | 工程 | 死代码/未接线清理（同步提案端点、卷 API、未用导出、`estimated_cost` 列） |
| DR-045 | 统计 | "今日字数"按 UTC 分桶；统计表出现无法解释的负数（如 −364） |
| DR-046 | 前端 | 硬编码英文串未 i18n、日期/数字不随语言、无离线提示、编辑器 aria-label 语言陈旧 |
| DR-047 | 数据 | revision 无界增长：每次自动保存全量副本 + FTS 全量重写，无保留策略/正文预算 |
| DR-048 | 编辑器 | 1 MiB 请求体硬墙对超长中文章节不可保存且无提示（配合 DR-001 成死局） |

### DEC（非代码，需 Owner 决策）

| ID | 事项 |
|---|---|
| DEC-01 | 用户验证从未发生：10 场访谈 + 一次真实冷启动（TTFW）计时，建议作为 0.9.0 发布 gate |
| DEC-02 | 定位收敛：面向普通作者的文案 vs 实际 homelab/tinkerer 受众 |
| DEC-03 | v0.8.0 Release 仍为 draft（tag/镜像已可用）：正式发布或修正文案 |
| DEC-04 | LICENSE 署名（当前 Copyright 写的是项目名）与贡献者协议取舍 |
| DEC-05 | 0.9.0 方向：整本生成 vs 局部生成 + diff 的能力优先级重排 |
| DEC-06 | provider 抽象（约 30 个文件）瘦身评估 |

---

## 2. P0 详细条目

### DR-001 [P0] 自动保存失败熔断，无重试入口

- [x] 已完成（2026-10-01）
- **问题**：保存一旦进入 `error` 状态，autosave effect 直接 return，不再排任何定时器；继续输入的字不会触发保存，界面无"重试保存"按钮。
- **证据**：`frontend/src/features/studio/hooks/useDocumentDraftAutosave.ts:83-90`（熔断）、`:117-121`（置位）；`StudioEditorPane.tsx:125-152` 只为 conflict 渲染动作，error 态无按钮；`useDocumentDraft*.test.tsx` 无 500/网络失败用例。
- **影响**：静默数据丢失。红色 "Save failed" 后继续写作并切换文档/刷新 = 全部新增内容丢失。
- **修复方向**：把 `error` 从熔断改为"退避重试（如 5s/15s）+ 显式重试按钮"，复用 `retryOverwrite` 的 `persistDraft` 路径；`error` 与 `conflict` 共用同一保存状态机。
- **验收标准**：① 一次非 409 失败后，下一次输入会自动重试保存并最终成功；② UI 始终有一个可见的"重试保存"动作；③ 新增回归测试覆盖失败→重试→成功与失败→持续失败。
- **验证**：`pnpm --dir frontend exec vitest run src/features/studio/hooks/useDocumentDraft.test.tsx`（新增用例）；`pnpm --dir frontend type-check`。
- **备注**：这是全清单中成本最低的 P0（单一 hook + 一个按钮）。
- **交付记录**：2026-10-01 | 工作区（基线 `607a092e`，未提交） | 退避重试（5s/15s/30s，成功即复位）+ 错误面板"重试保存"按钮（`editor.action.retrySave`，en/zh）+ 保留击键恢复路径 | 验证：`pnpm --dir frontend test:unit` 131 文件/709 用例全绿；`type-check` / `biome check` / `format:check` / `pnpm --dir frontend build` / `pnpm --dir server gates` 全绿 | 新增回归 `useDocumentDraft.autosave-recovery.test.tsx`（自动重试、退避上限、击键恢复、手动重试）。

### DR-002 [P0] 草稿丢失窗口与离开守卫缺失

- [x] 已完成（2026-10-01）
- **问题**：切换文档或组件卸载会清掉待发的 1.5s 防抖定时器，未持久化编辑被丢弃；没有 `beforeunload`/路由守卫；当前测试把"丢弃"固化为期望行为。
- **证据**：`useDocumentDraftAutosave.ts:92,149`；`grep "beforeunload|pagehide|visibilitychange" frontend/src` = 0；`useDocumentDraft.selection.test.tsx:101`、`useDocumentDraft.lifecycle.test.tsx:197` 断言丢弃；`spec.md:1838-1884` 明确 Draft 仅在内存。
- **影响**：最常见的数据损失路径（写完一句立刻切章/关标签）。
- **修复方向**：① `beforeunload` 守卫（存在未持久化草稿时）；② 切换文档前 flush 或确认；③ 可选：最新草稿写 sessionStorage 作为崩溃恢复（需同步修改规格）。
- **验收标准**：切换/关闭时未保存内容不静默丢失；对应既有"丢弃"测试按新行为重写（不是掩盖）。
- **验证**：`pnpm --dir frontend exec vitest run src/features/studio/hooks/useDocumentDraft.selection.test.tsx src/features/studio/hooks/useDocumentDraft.lifecycle.test.tsx`；浏览器人工验证一次。
- **交付记录**：2026-10-01 | 工作区（基线 `607a092e`，未提交） | `beforeunload` 守卫（仅未持久化编辑触发）+ 切换文档/卸载时"救援写入"（新模块 `useDocumentDraftRescue.ts` 与 `documentDraftPersistence.ts`；与在途保存内容相同的写入会跳过，避免与其自身基线竞争） | 既有 5 处"切换即丢弃"用例按新语义重写（selection×2、lifecycle×1、external×1、reconciliation×1），未削弱断言语义 | 可选的 sessionStorage 崩溃恢复未做，保留为后续项 | 验证同 DR-001。

### DR-003 [P0] 中文全文搜索静默失效

- [x] 已完成（2026-10-02）
- **问题**：`document_search` 建表未指定 tokenizer（默认 unicode61），连续 CJK 字符被切成"整段一个 token"；查询侧 `buildFtsMatchQuery` 把中文包成短语做精确 token 匹配，导致日常中文查询几乎全部 0 命中。
- **证据**：`server/drizzle/0000_init_persistence_core.sql:41`；`server/src/contexts/studio/application/fts_match_query.ts:10,25`；实测（真实 Fastify inject）`q="林黛玉"/"黛玉"/"宝玉"` → `results=[]`，`q="葬花"` 命中；一篇三段中文小说命中率 4/14；`tests/api/studio_search.test.ts` CJK 用例数 = 0。
- **影响**：中文作者的核心检索能力事实上不存在；"搜索"是写作指南推荐功能，静默失败比缺失更伤信任。
- **修复方向**：写入 FTS 的 title/content 做 CJK 预分词，查询侧用同一分词器。两个实测选项：`Intl.Segmenter('zh',{granularity:'word'})`（零依赖，2 字词可命中，推荐）或 `tokenize='trigram'`（3 字起命中，**2 字词仍 0 命中**，单用不够）。同时把 snippet 窗口从"16 token"改为"16 字符 CJK / 16 token 拉丁"。
- **验收标准**：`"林黛玉"`、`"黛玉"`、`"宝玉"` 均命中断言进入 `studio_search.test.ts`；英文既有用例零回归；搜索头/查询构造在中文下不再整段成 token。
- **验证**：`pnpm --dir server exec vitest run tests/api/studio_search.test.ts`；新增 CJK 用例先在基线上复现 0 命中。
- **依赖**：**必须与 DR-004 同批交付**（换 tokenizer 需要全量重建索引）。
- **交付记录**：2026-10-02 | `eea6f3d4`（wave 2，与 DR-004 同批） | 共享分词模块 `server/src/contexts/studio/domain/fts_segmentation.ts`（索引侧 Han 字符单独成 token、查询侧 Han 串→引号字短语；Latin 行为不变）；标题/摘要经 `restoreFtsDisplayText` 还原；CJK 摘要窗口即 16 字符 | 复现：CJK 用例在基线上 0 命中（`林黛玉` → `[]`）；修复后 `tests/api/studio_search.test.ts` 10/10（林黛玉/黛玉/宝玉/黛/葬花 均命中，英文零回归） | 偏离：未采用 `Intl.Segmenter`（实测其把「林黛玉」保持为单一词，黛玉/宝玉子词仍 0 命中），改逐字符方案；无 schema 迁移 | 验证：`pnpm --dir server exec vitest run tests/api/studio_search.test.ts`、`server gates`、`type-check`、`lint`、`lint:types`、`arch`、`server test`（237 文件/1426 用例）、frontend 全套 + react-doctor(100) + `pnpm spec:validate` 全绿。

### DR-004 [P0] FTS 索引重建通道与 doctor 对账缺失

- [x] 已完成（2026-10-02）
- **问题**：全仓无 FTS `rebuild`/`integrity-check` 代码路径；`document_search` 是自含内容表，FTS5 内置 rebuild 指令不可用；`doctor` 只报 4 项、不查索引。
- **证据**：`grep -rn "rebuild|fts5vocab|integrity-check" server/src` 仅命中无关代码；`apps/cli/main.ts:210-239`；`sqlite_diagnostics_health.ts:20-42`。
- **影响**：换机（手工拷 DB）、索引损坏、或 DR-003 换 tokenizer 时无重建手段；用户完全不可见不可修。
- **修复方向**：新增 `novel-engine reindex` 子命令（从 `documents.current_revision_id` + `document_revisions.content_markdown` 重灌索引）；`doctor` 增加"索引行数 vs 文档数"对账项。
- **验收标准**：reindex 在有/无漂移库上均幂等；doctor 能报告漂移；CLI 测试覆盖。
- **验证**：`pnpm --dir server exec vitest run tests/apps/cli/cli.test.ts`（新增用例）；`pnpm --dir server exec vitest run tests/api/studio_search.test.ts`。
- **交付记录**：2026-10-02 | `eea6f3d4`（wave 2，与 DR-003 同批） | 新增 `novel-engine reindex`（`server/src/apps/cli/reindex_command.ts`：单事务全量重建、幂等、复用 `refreshDocumentIndex` 写入路径；与 backup 同数据目录独占，服务器运行中拒绝执行）；`doctor` 新增 `document_index: {documents, indexed, drifted}` 对账项（CLI 报告字段；HTTP diagnostics 载荷未变动，未触发 OpenAPI 基线变更） | 测试：漂移库（2 文档/1 孤儿行）→ doctor 报 `drifted:true` → 连续两次 `reindex` 幂等 → `黛玉`/`葬花` MATCH 命中、孤儿行清除；损坏库 `document_index: null` | 升级提示：旧库需一次性执行 `reindex` 后 CJK 搜索才生效（doctor 计数对账不检测"格式陈旧"行）。

### DR-005 [P0] 中文字数口径错误（跨产品面）

- [x] 已完成（2026-10-02）
- **问题**：字数按 `[\p{L}\p{N}_'-]+` 匹配"词"，中文连续文本被按标点分段计数（约 1/7 低估），但 UI 在中文下把它当"字"显示，英文下当 "words"。
- **证据**：`server/src/contexts/studio/domain/revision_word_count.ts:3`；测试钉死 `"你好世界"→1`（`tests/contexts/revision_word_count.test.ts:15-18`）；实测 31 汉字 → 4；UI `zh.shared.ts:30-31`、`StudioStatusbar.tsx:41-44`、`StudioHistoryPanel.tsx:89-90`；下游 `THIN_CHAPTER_WORDS=250`（`review_rules.ts:84`）导致中文约 1700–2000 字前一直报"章节过薄"；usage 缺失回退也复用该函数（`proposal_landing.ts:114-118`）。
- **影响**：连载作者的心跳数字失真；同时污染评审阈值、统计与成本估算。
- **修复方向**：改为按脚本分量计数（CJK 逐字符 + 拉丁按词），或中文场景直接用字符数口径；同步 zh 文案、`THIN_CHAPTER_WORDS`、usage 回退与规格中的计数定义。
- **验收标准**：CJK 用例（如 31 汉字）计数符合新定义；既有英文用例不回归；规格补充"word"定义条目。
- **验证**：`pnpm --dir server exec vitest run tests/contexts/revision_word_count.test.ts tests/api/studio_writing_stats.test.ts`；`pnpm --dir server gates`（若涉及 spec 改动则含 `pnpm spec:validate`）。
- **备注**：涉及 `docs/agents/error-codes.md` 之外的文档无需门禁；改动面横跨 domain/UI/测试/规格，按 AGENTS.md 一次性完成。
- **交付记录**：2026-10-02 | `8e59e9b6` | 统一口径：汉字符逐字计数 + 非 Han 字母/数字/下划线/撇号/连字符 run 按词，混排求和（`domain/revision_word_count.ts`，JSDoc 与 spec 同文）；`reconcileRevisionWordCounts` 从"仅补 NULL"升级为"keyset 分批全量重算、仅在存储值≠重算值时写入"（启动时自动修正旧口径存量计数，幂等零写入，`RevisionWordCountInvariantError` 语义保留）；`THIN_CHAPTER_WORDS` 维持 250 并文档化（中文即 250 字符下限，语言差异化阈值属产品决策）；`proposal_landing` 回退注释注明 CJK ≈1 token/字；前端文案经核查无需改（纯中文"字"、纯英文 words、混排伞形口径） | 复现：31 汉字段落旧口径计 1（应 31）、`"你好世界"` 1（应 4）、`"hello，世界！"` 2（应 3）；修复后对应 31/4/3 | spec 新增 "Stale counts ... recomputed" 场景 + 逐字计数断言 | 验证：`pnpm --dir server exec vitest run tests/contexts/revision_word_count.test.ts tests/api/studio_writing_stats.test.ts tests/db/revision_word_count_reconciliation.test.ts tests/contexts/project_shell_store.test.ts`（27 用例）、`server gates`/`type-check`/`lint`/`lint:types`/`arch`/`test`（237 文件/1432 用例）、frontend 全套 + react-doctor(100)、`pnpm spec:validate` 全绿 | 设计代价（有意）：启动对账每次 open 全量重算 revision（keyset 256/批、可中断续跑、一致库零写入）；未跑：全量套件由 integrator 于屏障执行（已执行）

### DR-006 [P0] 流式生成失败不可恢复（重试 + 保命）

- [x] 已完成（2026-10-02）
- **问题**：唯一在用的生成路径是 SSE；流一旦失败（瞬时 429/5xx/idle 超时）不回退重试，且已生成正文在服务端置空、前端 `finally` 清空预览——双端全损，只能重新生成、再次计费。
- **证据**：`server/src/contexts/studio/infrastructure/streaming_generation.ts:209-212`（"A stream is never retried"）；`proposal_pipeline.ts:216-223`；`frontend/.../useProposalStreamSession.ts:199-204`；`tests/api/studio_proposals_stream.test.ts` 把"不伪造文本"固化为期望。
- **影响**：长章一次生成失败 = 全部作废 + token 双倍成本。
- **修复方向**：① 首个 delta 之前的失败复用 `runWithRetryPolicy`；② 中途失败把已累积的 sanitized 文本持久化为 failed job 的 `result_json.partial_markdown`，前端保留预览并支持"另存为提案/复制"。
- **验收标准**：首 delta 前失败自动重试且不产生重复 usage；中途失败后 job 记录含 partial 文本、前端可保留；新增两条回归测试。
- **验证**：`pnpm --dir server exec vitest run tests/api/studio_proposals_stream.test.ts`；`pnpm --dir frontend exec vitest run src/app/proposalStream.lifecycle.test.ts`。
- **交付记录**：2026-10-02 | `3771724e` | 首帧前失败经 `runWithRetryPolicy` 重试（重试只在首帧未进入 extractor 前发生，避免重放增量解包状态；失败即关闭帧迭代器）；中途失败把已累积的 sanitized 文本写入 failed job 的 `result_json.partial_markdown`（完成流 drain 后不保留 partial）；前端保留中断预览（`streamingInterrupted` 贯穿 hook→页面模型→面板），Stop 替换为"复制"（zh/en 文案、无障碍保留） | 复现：基线 `studio_proposals_stream.test.ts` 将"失败即清空"固化为期望；新用例先红后绿 | 回归：`studio_proposals_stream_retry.test.ts`（429→重试→单 job、单 usage、tokens 21/34）、`provider_streaming_retry.test.ts`（首帧前重试 / 耗尽 3 次 / 首 delta 后不重试）、`StudioCopilotPanel.streaming.test.tsx`；integrator 修复重试引入的 4 个定时预算用例（显式单次尝试隔离，断言不变）与 3 处格式化 | 验证：`server 239 文件/1436 用例`、`frontend 134 文件/723 用例`、gates/type-check/lint/lint:types/arch/react-doctor(100)/`pnpm spec:validate` 全绿

### DR-007 [P0] 整本生成静默覆盖手写章节

- [x] 已完成（2026-10-02）
- **问题**：整本循环的 `needsGeneration` 规则是"当前修订不是 ai-accepted 就重生成"，手写/导入/restore 的章节全部会被重新起草并自动接受；UI 仅一句 "still missing an AI revision"，无确认。
- **证据**：`frontend/src/features/studio/hooks/wholeBookPlan.ts:8-19`（注释自认 seeded/hand-written/imported/restored 都会被重生成）；`useWholeBookChapterRun.ts:108-140` 自动接受；`en.studio.ts:215-216` 文案。
- **影响**：一键顶替手稿（只能逐条 restore 找回），违反 CONTEXT.md"仅作者显式接受才应用"的产品承诺。
- **修复方向**：默认只生成"空章节/从未有 ai-accepted 的章节"；对非空作者文本逐章确认（或先 dry-run 列表）；UI 明确列出将被覆盖的章节。
- **验收标准**：含手写章节的项目启动整本生成时不静默覆盖；回归测试覆盖 needsGeneration 与确认路径。
- **验证**：`pnpm --dir frontend exec vitest run src/features/studio/hooks/useWholeBookLoop.run.test.tsx`；`pnpm --dir server exec vitest run tests/api/studio_proposals.test.ts`。
- **交付记录**：2026-10-02 | `3771724e` | `wholeBookPlan` 拆为安全集（空正文 `word_count===0`，自动生成）与确认集（非空作者/导入/恢复文本）；`useWholeBookChapterRun.start(plan, {replaceOccupied})` 仅在显式确认时触碰确认集（调用方+执行器双防线）；`StudioWholeBookControl` 新增 dry-run 章节清单 +「仅生成 N 个空章」/「替换 M 章」/取消（Esc、焦点进入/归还），Start 不再静默替换；停止或刷新后重跑对未确认章节重新要求确认；`wholeBook.hint` 与两个 e2e 规格同步新交互 | 复现：探针显示手写章节被列入计划并自动接受（proposal/accept 各 2 次）；新用例先红后绿 | 回归：`useWholeBookLoop.confirm.test.tsx`（4）、`StudioWholeBookControl.confirm.test.tsx`（6）、`wholeBookPlan.test.ts`、resume/stop/unknown 用例适配（旧"无差别重生成"断言逐条点名更新） | spec："Whole-book generation loop" 需求与场景改确认门控（integrator 补写）；integrator 修复 react-doctor 链式迭代告警（单遍循环） | 验证：同 DR-006（全绿）

### DR-008 [P0] 首启 Owner 抢占（无 setup token）

- [x] 已完成（2026-10-02）
- **问题**：`POST /api/setup` 的唯一门是 same-origin 校验；不带 Origin/Referer 的非浏览器客户端被直接放行。任何扫描器/首个访问者可在作者之前创建 Owner；第二次 setup 被单 Owner 不变式拒绝 → 作者被永久锁死，且无 CLI 自助恢复。
- **证据**：`server/src/shared/interface/http/auth_routes.ts:128-155`（注释自认）、`auth_store.ts:55-72`；容器实测：无 Origin 的 `POST /api/setup` → 201，真实作者随后 → 422；两个 compose 文件默认发布 `0.0.0.0:8000`。
- **影响**：正常部署直接变成"实例被接管且无法自救"（恢复只能删库，等于丢内容）。
- **修复方向**：① 首启生成一次性 setup token（写入卷内 `.setup-token` 0600 + 打印到日志），`POST /api/setup` 校验 `x-setup-token`；或 setup 仅允许 loopback；② 补 `cli owner reset`（持数据目录锁，正确处理 FK/session cascade）。
- **验收标准**：带外网地址的无 token setup 被拒；容器首启流程文档化；`cli owner reset` 有测试且不破坏既有会话语义。
- **验证**：`pnpm --dir server exec vitest run tests/api/auth_setup.test.ts`（新增 token 用例）；`pnpm --dir server exec vitest run tests/apps/cli/cli.test.ts`。
- **备注**：与 DR-033/DR-034 同属"部署安全第一公里"，建议同批规划、分条提交。
- **交付记录**：2026-10-02 | `b10e02c6` | 首启一次性 setup token：无 Owner 时生成 32B base64url、写 `data/.setup-token`(0600)、日志打印一次（重启复用未用 token）；`POST /api/setup` 对非 loopback 原始 socket 对等方强制 `x-setup-token`（timingSafeEqual；成功后失效并删档；已有 Owner 时启动清理残留文件；路径失败一律 fail-closed，loopback 不受影响；403 `SETUP_TOKEN_INVALID`），loopback 保留原 origin 校验流程；新增 `novel-engine owner reset`（与 backup 同数据目录独占锁；单事务删 owners+sessions，输出 `{owners_deleted, sessions_deleted, username}`；spec 明确"无邮件找回，reset 即恢复路径"） | 复现：`remoteAddress: 203.0.113.7`、无 Origin、无 token 的 setup 基线 201 → 修复后 403 且无 Owner | 回归：`auth_setup.test.ts`（17：缺/错/正确 token、loopback、残留文件、并发单 Owner）、`owner_reset_cli.test.ts`（4）、`setup_token.test.ts`（4） | 联动：新错误码 SETUP_TOKEN_INVALID 同步 `error-codes.md` + `ERROR_HTTP_STATUS`；README/deploy README 首启流程（docker logs 取 token + curl 示例）；spec 新增 "First-boot setup token gate" 需求与 5 场景 | 已知后续项：浏览器 setup 页尚未提供 token 输入框（当前 Docker 首启需一次 curl），已并入 DR-019 的 setup UX 范围 | 验证：定向 78 用例 + server 241 文件/1457 用例 + frontend 全套 + react-doctor(100) + `pnpm spec:validate` 全绿

### DR-009 [P0] XFF 伪造使登录限速失效

- [x] 已完成（2026-10-02）
- **问题**：当 peer 命中 `SECURITY_TRUSTED_PROXIES` 时，限速键取 `X-Forwarded-For` 首段（客户端可控）；每请求换一个伪造 IP 即每请求一个新桶，登录限速永不上限。信任列表一旦过宽（含直连网段/CIDR），爆破无阻。
- **证据**：`shared/infrastructure/rate_limit/client_identity.ts:160-170`；`apps/api/auth_registration.ts:51-57`；实测：无信任代理时第 5 次 429；`SECURITY_TRUSTED_PROXIES=127.0.0.1` 后连续 16 次恶意登录零 429。bcrypt cost 12 每次约 0.21s，持续爆破同时打满 CPU。
- **影响**：README 的 "5/minute" 抗爆破承诺失效，登录面可被 DoS。
- **修复方向**：只接受具体代理 IP（拒绝 CIDR 覆盖客户端）；取"最右侧未受信跳"作为客户端身份；`trustedProxies` 推导 Fastify `trustProxy`；文档补反例警告。
- **验收标准**：信任代理场景下伪造 XFF 不再绕过限速；新增回归测试覆盖"多跳 + 伪造首段"。
- **验证**：`pnpm --dir server exec vitest run tests/apps/api/`（限速/身份相关文件）；`pnpm --dir server gates`。
- **交付记录**：2026-10-02 | `b10e02c6` | 限速身份改为转发链"最右未受信跳"（peer 必须仍为受信代理；全部受信时回退 peer 共桶）；信任条目仅接受具体地址/主机，网络范围在配置加载即拒绝（`ConfigurationError` 指名 `SECURITY_TRUSTED_PROXIES`），匹配器也永不匹配范围（`isTrustedProxyRange` 防程序化绕过）；Fastify `trustProxy` 由同一列表推导（`http_server_policy.ts`，空列表保持 false），`app.ts` 单次解析供两处共用 | 复现：受信代理下 16 次轮换伪造 XFF 登录基线 0 次 429 → 修复后第 6 次起 429（共桶于最右未受信跳） | 回归：`auth_rate_limit.test.ts`（伪造首段共桶 / 多跳取右最未受信跳 / 范围条目失效）、`client_identity.test.ts`（11）、`server_config.test.ts`（范围启动拒绝）、`inbound_request_lifetime.test.ts`（XFP 仅在受信 peer 下生效） | 文档：README 配置行为 + deploy README（范围拒绝、代理须追加 XFF 的反例警告）；spec 限速需求与场景同步 | 行为变更提示：`SECURITY_TRUSTED_PROXIES` 使用 CIDR 的部署将启动失败，需改为枚举具体代理地址 | 验证：同 DR-008（全绿）

---

## 3. P1 详细条目

### DR-010 [P1] 停止/接受/拒绝的恢复性

- [x] 已完成（2026-10-02）
- **问题**：① 点"停止"后已生成的全部 delta 被清空，预览只读、无复制/保留；② 接受提案后没有 undo，只能走"历史 → 恢复修订"；③ reject 无记录，文本永久丢失。
- **证据**：`useProposalStreamSession.ts:199-231`；`StudioCopilotPanel.tsx:168,183-208`；全前端 `grep -i undo` 零命中；无 reject 路由（`revision_routes.ts` 仅 list/restore）。
- **修复方向**：停止时保留已收文本（可复制/另存为提案）；Accept 后出一次性"撤销"提示条；reject 的文本存入 job/proposal 记录可回看。
- **验收**：三条路径各有回归测试；UI 文案（zh/en）同步。
- **验证**：`pnpm --dir frontend exec vitest run src/features/studio/`（相关组件）。
- **交付记录**：2026-10-02 | `2baed8a9` | ① 停止生成：新增 `streamingStopped` 状态保留已收文本并提供"复制"（与 DR-006 的 interrupted 并列、不伪造失败；面板 Stop→Copy 切换）；② 一次性撤销：接受时记录 base revision，页面模型经 `buildProposalUndo` 组合 `{onUndo}` 走 History 同款恢复路径；consume-first 保证第二次点击无效；③ 被放弃提案的文本可在任务面板按行懒加载（`api.job(projectId, jobId)` → 既有单任务 GET，无新路由）阅读/复制 | 复现：停止后预览清空、接受后无出口、拒绝后无从找回；三条新回归先红后绿（`useStudioProposal.test.tsx` 停止保留、`useStudioPageModel.proposal-undo.test.tsx`、`StudioJobsPanel.proposal-text.test.tsx`） | 过程修正：撤销提议曾被文件刷新引起的瞬时 owner 切换清空 → 清理移至项目级 effect；`activeDocumentIdRef` 渲染期写改为 effect 同步（react-doctor 归零） | 已知取舍：撤销提议在切换文档后仍保留（派生逻辑只在所属文档显示；切换项目即清除） | 验证：frontend 138 文件/745 用例、server 241 文件/1459 用例、gates/arch/react-doctor(100)/`pnpm spec:validate` 全绿

### DR-011 [P1] 修订历史预览与 diff

- [x] 已完成（2026-10-02）
- **问题**：历史列表只有 source/时间/词数/id 前缀；无正文预览端点、无 diff；restore 无二次确认，是"盲恢复"。
- **证据**：`StudioHistoryPanel.tsx:85-96`；`revision_routes.ts:26-99` 无单条正文 GET；`grep "\bdiff\b"` 前端零命中；`openwiki/guides/writing-guide.md:161` 宣称可 "diff against history"（文档说谎）。
- **修复方向**：新增只读 `GET .../revisions/:revisionId`（正文）；历史行可点开预览 + 与当前版本 diff 高亮；restore 前确认并说明"当前内容仍保留在历史"。
- **验收**：可查看任一历史正文；diff 至少覆盖"行级"对比；restore 有确认。
- **验证**：`pnpm --dir server exec vitest run tests/api/studio_revisions.test.ts`（新增正文端点用例）；`pnpm --dir frontend exec vitest run src/features/studio/components/StudioHistoryPanel.restore.test.tsx`。
- **交付记录**：2026-10-02 | `2baed8a9` | 新增只读 `GET /api/projects/:projectId/documents/:documentId/revisions/:revisionId`（正文 + source + word_count + created_at；owner/作用域校验与既有修订路由一致；读取不产生修订）；历史行可展开懒加载预览（打开一次、缓存、失败可重试）；行级 LCS diff（`historyLineDiff.ts`：删除/新增/上下文标记、确定性、超 25 万格预算退化为块替换）对比当前正文；恢复前确认并说明"当前内容仍保留在历史" | 复现：历史仅摘要、无正文端点/预览/diff；新用例先红后绿（server `studio_revisions.test.ts` 8 用例含"previews an ancestor revision body without creating a revision"、`StudioHistoryPanel.preview.test.tsx` 5 用例、restore 6 用例） | 联动：路由变更 → `openapi:snapshot` + `gen:api-types` 再生成（gate:openapi 与 drift 检查均绿）；历史/预览文案入 en/zh 字典 | 验证：同 DR-010（全绿）

### DR-012 [P1] 冲突解决可查看服务器版本

- [x] 已完成（2026-10-02）
- **问题**：冲突的两个动作都是破坏性的（整体丢弃/整体覆盖），无法查看对方文本同时保留自己草稿；被覆盖文本只能靠 restore 阅读（而 restore 又整体覆盖）。
- **证据**：`useDocumentDraftActions.ts`（loadLatest/retryOverwrite）；`StudioEditorPane.tsx:129-150`；依赖 DR-011 的正文端点。
- **修复方向**：冲突面板加"查看服务器版本（只读）"；覆盖前列出将覆盖的 revision 号；可选三选一（保留本地/加载最新/预览后决定）。
- **验收**：冲突下可只读查看服务器文本；测试覆盖"查看不改变本地草稿"。
- **验证**：`pnpm --dir frontend exec vitest run src/features/studio/hooks/useDocumentDraft.conflict.test.tsx`。
- **依赖**：DR-011。
- **交付记录**：2026-10-02 | `2baed8a9` | 冲突面板新增"查看服务器版本（只读）"：经 DR-011 端点读取当前服务器修订正文并标注将被覆盖的修订号，保留三选一（保留本地 / 加载最新 / 预览后决定）；查看纯读，不改草稿、不写项目/修订缓存，关闭冲突面板即收起，过期响应按请求序号丢弃 | 复现：冲突下两个动作均为破坏性、无法对照对方文本；`useDocumentDraft.conflict.test.tsx` 新增"viewing does not change the local draft"先红后绿（原有用例保留） | 验证：同 DR-010（全绿）

### DR-013 [P1] DOCX 中文排版

- [x] 已完成（2026-10-02）
- **问题**：DOCX 只有 TITLE + HEADING_1 + 裸段落；无 `w:rFonts eastAsia`、无 2 字符首行缩进、无章前分页、无 TOC 域；正文首行与章节标题重复（H1 被 plainText 去标记后与标题行重复）。
- **证据**：`server/src/contexts/studio/infrastructure/bounded_export_rendering.ts:86-101`；grep `rFonts|eastAsia|indent|pageBreak` 零命中；实测 styles.xml 空 `<w:rPrDefault/>`。
- **修复方向**：显式东文字体（宋体/思源宋体）+ 首行缩进 2 字符 + 章前分页 + TOC；跳过与章节标题重复的首行；补结构断言测试。
- **验收**：导出 DOCX 在 Word/WPS 打开即具备中文段落样式；标题不重复；测试覆盖字体与缩进标记。
- **验证**：`pnpm --dir server test`（导出相关）；人工打开一次产物。
- **交付记录**：2026-10-02 | `238a1cab` | 新模块 `docx_manuscript.ts`（纯 docx API，无原始 OOXML 逃逸）：docDefaults + 每个 run 显式 `w:rFonts eastAsia="SimSun"` + Latin Times New Roman + `w:hint="eastAsia"`；正文段落 2 字符首行缩进（`w:firstLineChars="200"` 且 `w:firstLine="480"` twips），Title/Heading1 覆盖为 0 保持标题齐头；每章标题 `w:pageBreakBefore`；TOC 经库的 `TableOfContents`（`w:sdt` + `TOC \h \o "1-1"`）+ `settings.xml` `w:updateFields` 让 Word/WPS 打开时重建；跳过与章节标题重复的首行（H1 或普通重复行，复用 `stripRepeatedTitleLine`） | 复现：结构断言先红（无 eastAsia、无 ind、无 pageBreak、标题重复、无 CSS/语言被写死等 9 条）；修复后全绿 | 测试：`export_artifact_docx_layout.test.ts`（6 条结构断言） | 人工 gate：Word/WPS 打开一次待 Owner（OOXML 标记已解包断言并留存 dump） | 验证：导出套件 30 文件/137 用例 + 全套（server 244/1472、frontend 138/745、gates/arch/react-doctor(100)/spec 全绿）

### DR-014 [P1] EPUB 合规与中文 CSS

- [x] 已完成（2026-10-02）
- **问题**：`<dc:language>en</dc:language>` 硬编码；缺 `<meta property="dcterms:modified">`（EPUB 3 必需）；无任何 CSS（无缩进/行高/字体）；图片与代码块被整段删除。
- **证据**：`epub_xml.ts:113,29-37,62-68`；解包实测（mimetype 合规、缺 dcterms:modified）。
- **修复方向**：语言可配置或按内容/项目语言推断；补 dcterms:modified（用导出时间 ISO-8601）；内置中文阅读 CSS；明确图片策略。
- **验收**：EPUBCheck 类校验通过（或结构断言等价）；中文书语言正确。
- **验证**：`pnpm --dir server test`（导出相关）；有条件时跑 EPUBCheck。
- **交付记录**：2026-10-02 | `238a1cab` | `dc:language` 按正文推断（Han→zh、假名占比≥20% 判 ja、Hangul→ko、Cyrillic→ru、Latin→en；代码块/URL/链接目标排除在统计外；无法识别时回退 en）；`<meta property="dcterms:modified">` 取导出时间 ISO-8601 UTC（`ArtifactWriteRequest.capturedAt` 由 `ExportSource.capturedAt` 注入，测试断言快照时间抵达网关）；内置 `OEBPS/styles/reading.css`（宋体/思源宋体栈、`text-indent: 2em`、行高 1.75）在 OPF manifest 声明并由每章链接，章节带 `xml:lang`；围栏代码输出 `<pre><code>`；图片保留为可见占位 `[image: alt] src`（快照仅含 markdown 文本、远端抓取超出容量边界，已在代码注释说明策略） | 复现：结构断言先红（4 条：缺 CSS、语言写死、缺 dcterms:modified、代码块丢失）；修复后全绿 | 测试：`export_artifact_epub_package.test.ts`（4 条：mimetype/container/OPF/manifest/CSS/chapter 标记） | 跳过：EPUBCheck 本地不可用（以等价结构断言替代，记录为环境跳过） | 验证：同 DR-013

### DR-015 [P1] Markdown 导出丢标题与导出范围

- [x] 已完成（2026-10-02）
- **问题**：Markdown 只拼 `chapter.contentMarkdown`，丢 `chapter.title`；且所有格式只含 chapter，character/world/outline/note 与 lore 字段只留在 SQLite；指南称 Markdown 是"无损副本"（不成立）。
- **证据**：`bounded_export_rendering.ts:73-84`；`export_artifact_service.ts:155-157`；实测输出无章节标题。
- **修复方向**：Markdown 每章输出 `## {title}`；决策并实现"全量归档导出"（含非章节文档）或修正文档承诺。
- **验收**：Markdown 含章节标题；导出范围与文档一致。
- **验证**：`pnpm --dir server test`（导出相关）。
- **交付记录**：2026-10-02 | `238a1cab` | `markdownChapterSegment`：每章输出 `## {title}` + 去除与标题重复的首行后的正文（空正文仍保留标题，章节不消失；顺序与 `\n\n` 分隔、单结尾换行的既有确定性不变）；方向决策＝文档对齐（不做全量归档新功能）：`openwiki/guides/exporting.md` 与 zh 镜像改为精确范围（仅章节文档；notes/characters/world/outline/lore 留在数据库；**full-archive export 未实现**，全量请备份数据库），删去 "lossless/future-proof/无损副本" 承诺 | 复现：新用例先红（标题缺失、空正文章节塌缩为空行）；修复后 `export_artifact_markdown.test.ts` 3/3；`export_artifact_files.test.ts` 的 byte-stable 期望按新输出更新（原期望固化的是无标题旧行为） | 验证：`pnpm --dir server exec vitest run tests/contexts/export`（30 文件/137 用例）+ 全套同 DR-013（全绿）

### DR-016 [P1] 查找/替换与快捷键

- [x] 已完成（2026-10-02）
- **问题**：编辑器无查找/替换（未装 `@codemirror/search`）；全前端无 metaKey/ctrlKey 处理，Ctrl+S 触发浏览器"保存网页"；工具条无可点击格式按钮；搜索不定位命中。
- **证据**：`frontend/package.json`；`MarkdownEditor.tsx:49-50`；grep 零命中；`StudioNavigatorSearch.tsx:64`。
- **修复方向**：接入 CodeMirror search（Ctrl+F/Ctrl+H）；全局拦截 Ctrl/Cmd+S 触发保存 + toast；最小格式按钮（B/I/H）；搜索返回偏移以支持定位高亮（可拆 DR-029）。
- **验收**：Ctrl+F/Ctrl+H/Ctrl+S 行为正确；组件测试覆盖快捷键处理。
- **验证**：`pnpm --dir frontend exec vitest run src/features/studio/`；人工浏览器验证。
- **交付记录**：2026-10-02 | `2baed8a9` | 接入 `@codemirror/search`（授权范围内，lockfile 同步）：Ctrl+F/Ctrl+H 打开查找/替换面板（Mod-h 聚焦替换栏；面板文案随语言切换、跟随外壳主题令牌含暗色）；Ctrl/Cmd+S 经 `flushDraftNow` 取消防抖并走既有保存路径（冲突态/在途/无改动时安全 no-op，错误态委托 `retrySave` 保持 DR-001 语义，不触发浏览器"保存网页"）；Bold/Italic/Heading 命令（`runMarkdownFormat.ts`：选区包裹/去包裹、行级 `# ` 前缀切换，含空选区插入与多行处理）+ 最小工具条；新增 en/zh.editor 字典分块 | 复现：无 search 扩展/无快捷键拦截/无格式命令；`MarkdownEditor.test.tsx`（6 用例）与 `StudioEditorPane.test.tsx`（10 用例）先红后绿 | 范围说明：搜索命中定位（导航搜索偏移）仍按 backlog 拆分至 DR-029；人工浏览器验证待 Owner（已记录为人工 gate） | 验证：frontend build（含新依赖）通过；其余同 DR-010（全绿）

### DR-017 [P1] 卷功能 UI 可达性（或规格降级）

- [x] 已完成（2026-10-02）
- **问题**：卷 CRUD/reorder API 与前端 client 方法存在但零调用者；项目只创建一个默认卷 → "Move to volume" 控件永不渲染；多卷、按卷导出在 UI 不可达，规格却以多卷为前提。
- **证据**：`frontend/src/app/api.ts:79-86`（零调用者）；`StudioNavigatorRowActions.tsx:88-123`；E2E 自述 `studio_reorder.spec.ts:11-13`；`project_store_part.ts:60,178`。
- **修复方向**：二选一（需 Owner 拍板，可并入 DEC-05）：A. 补最小卷管理 UI（新建/改名/删除/排序 + 放置）；B. 承认单卷并同步降级 spec/guide，删除死代码。
- **验收**：所选方向落地；不再存在"文档教用户使用不存在入口"。
- **验证**：`pnpm --dir server exec vitest run tests/api/studio_volumes.test.ts`；前端相关测试。
- **交付记录**：2026-10-02 | `aa551e01` | 方向 A 落地（Owner 已拍板）：navigator 新增卷管理三件套——`StudioNavigatorVolumeList`（按卷分组 + 头簇）、`StudioNavigatorVolumeCreate`（行内新建表单）、`StudioNavigatorVolumeHeader`（改名/删除确认/上下移，复用文档重排模式而非新拖拽系统）；`useStudioVolumeActions` 接线既有 `api.createVolume/renameVolume/deleteVolume/reorderVolumes`（单飞、owner 守卫、行内错误、失败态保留），`moveDocument` 的"移至卷"入口随多卷可达（原第 2 卷起才渲染的菜单项现在真正有卷可选） | 复现：单卷项目下无任何卷控件、多卷不可达（新用例先红后绿）；修复前既有 E2E 自述该缺口 | 回归：`StudioNavigator.volumes.test.tsx`（13：新建/改名/删除+服务端拒绝/重排+边缘禁用/单卷守卫）、`useStudioPageModel.volumes.test.tsx`（5：含"新建后放置入口可达"与删除合并章节/拒绝保留）；`studio_volumes.test.ts` 7 用例无回归 | 过程修正：react-doctor 4 条（完成态 effect 改为渲染期调节 + 事件侧 ref 标志；scope 循环改单遍）；E2E 消歧 2 处（未运行，CI 负责） | 验证：frontend 141 文件/767 用例、server 244/1472、gates/arch/react-doctor(100)/spec 全绿

### DR-018 [P1] 项目删除入口

- [x] 已完成（2026-10-02）
- **问题**：`DELETE /api/projects/:id` 已实现，`api.deleteProject` 零调用者（历史审计 0.3.0 的同类问题以"有后端无 UI"形态存活）。
- **证据**：`frontend/src/app/api.ts:170`；`server/.../project_routes.ts:195`；项目库 UI 无删除。
- **修复方向**：项目库/设置加删除（二次确认，明示导出文件与快照的处理）。
- **验收**：UI 可删除项目并有确认；测试覆盖。
- **验证**：`pnpm --dir frontend exec vitest run src/features/`（项目库相关）；`pnpm --dir server exec vitest run tests/api/`（项目相关）。
- **交付记录**：2026-10-02 | `aa551e01` | 项目库每行新增删除入口：`ProjectCatalogRow`（行内确认条，Escape 取消、焦点进入确认/取消后回触发器）+ `useProjectLibraryDeletion`（单飞、经既有 `api.deleteProject`、成功后刷新目录并播报、失败按行留存）+ 确认文案明示移除范围（项目及其文档/修订/导出/快照；备份不受影响）；删除成功后行移除且焦点按既有约定回落标题 | 复现：`ProjectLibraryPage.deletion.test.tsx` 4 用例先红（渲染行仅打开按钮）；修复后全绿（确认前不发请求/取消零副作用/确认一次并刷新/失败不刷新） | 既有 lifecycle/pagination 用例的宽松正则消歧（`/Title/`→`/^Title/`，未削弱断言）；E2E 同型消歧 1 处（未运行，CI 负责） | 说明：删除入口落在项目库页面（任务锚点）；打开中项目的设置面板入口未加（属可选后续，已记录） | 验证：server 项目删除相关 3 文件/11 用例无回归；其余同 DR-017（全绿）

### DR-019 [P1] 密码体验（确认/修改/无找回提示）

- [x] 已完成（2026-10-03）
- **问题**：密码框无确认字段（打错即永久锁死）；全仓无"忘记密码/重置"路径；只有 setup 与 login。
- **证据**：`EntryPage.tsx:105-117`；`grep "忘记密码|reset.*password|forgot"` 全仓零命中。
- **修复方向**：setup 加二次确认；`cli owner` 提供改密/重置（与 DR-008 的 reset 合并设计）；首登提示"本工具无邮件找回，请妥善保存密码"。
- **验收**：setup 两次输入一致才通过；有文档化的重置路径。
- **验证**：`pnpm --dir server exec vitest run tests/api/auth_setup.test.ts`；`pnpm --dir frontend exec vitest run src/features/studio/EntryPage.lifecycle.test.tsx`。
- **交付记录**：2026-10-03 | `5795feb9` | setup 新增确认密码字段（不一致时阻止提交并内联报错；`EntrySetupFields.tsx`）；并按 DR-008 遗留项补上"首启 setup token"输入（`api.setupOwner(u,p,token?)` 非空时发送 `x-setup-token` 头，`SETUP_TOKEN_INVALID`/403 显示可操作中文提示：从日志或 `.setup-token` 读取、loopback 无需）；setup 与首登表单常驻"无邮箱找回，请保存密码；恢复路径为停止服务器后 `novel-engine owner reset`（书稿不受影响）"提示（对齐 README） | 复现：6 个新用例先红（无确认框、无 token 头、提示缺失）；修复后全绿 | 改动面：EntryPage/EntrySetupFields/api/httpClient(postJson 支持可选 init)/entrySubmitMessage/字典/entry.css；README 与 deploy README 的"setup 界面无法发送 token"表述同步修正 | 改密端点未新增（recovery 即 DR-008 的 owner reset，文档化） | 测试：EntryPage 套件 + api.test（30 用例）、`auth_setup.test.ts` 17 用例无回归 | 验证：frontend 145 文件/805 用例、server 244/1472、gates/arch/react-doctor(100)/spec 全绿

### DR-020 [P1] 会话过期体验

- [x] 已完成（2026-10-03）
- **问题**：任一 401 直接 `navigate("/", {replace:true})`，无提示、丢草稿与当前位置；登录后固定回 `/projects`。
- **证据**：`useStudioPageNavigation.ts:31-34`、`useProjectShellState.ts:120-123`、`useCurrentDocument.ts:139-141`；dictionaries 无 session-expired 文案。
- **修复方向**：入口页显示"会话已过期"；保留来源路由（`state.from`），登录后回跳；配合 DR-002 降低草稿损失。
- **验收**：过期→提示→登录→回到原文档路径；测试覆盖。
- **验证**：`pnpm --dir frontend exec vitest run src/features/studio/EntryPage.lifecycle.test.tsx`。
- **交付记录**：2026-10-03 | `5795feb9` | 新增 `app/sessionExpiry.ts`：401 强制返回时写入 history state `{from, reason:"session-expired"}`（replace 语义，防止后退弹回过期页），入口页据此渲染本地化"会话已过期"提示（`EntrySessionNotice`，主动登出/首次访问不带标记、不显示）；登录成功后回跳被保留的站内路由（`from` 经形状校验，拒绝非站内/协议相对路径），无来源时回落 `/projects`；受影响路径统一改走 `useSessionExpiredRedirect`（导航/项目壳/当前文档） | 复现：5 个新用例先红（无提示、无回跳）；修复后全绿（含"自愿访问无提示""非法来源忽略"） | 测试拆分：`EntryPage.test-helpers.tsx`（共享挂载/夹具）消除复制，`EntryPage.session-expiry.test.tsx` 承载 DR-020 用例，lifecycle 文件回落到 300 行内 | 验证：同 DR-019（全绿）

### DR-021 [P1] 错误文案中文化

- [x] 已完成（2026-10-03）
- **问题**：服务端英文 message 直出，且夹带内部标识符（如 `project_settings_bytes`、`provider returned HTTP 401`、`Owner session required.`）；契约层 `Invalid <label>.<key>` 21 处。
- **证据**：`frontend/src/app/toErrorMessage.ts:28-36`；`httpClient.ts:41-44`；`zh.errors.ts:44` 与 `structure_capacity.ts:69` 拼出中英混句。
- **修复方向**：按 `error.code` 前端映射中文文案；provider 原始消息降为"技术详情"折叠区；契约错误改为用户可读。
- **验收**：中文界面常见错误（401/413/422/限速/容量）不再出现英文；测试覆盖映射表。
- **验证**：`pnpm --dir frontend exec vitest run src/app/`（错误处理相关）。
- **交付记录**：2026-10-03 | `5795feb9` | 新增 `app/localizeError.ts`：按信封稳定 `error.code` 映射双语消息（23 码 = 服务端 21 目录码 + 流末帧 `PROVIDER_FAILED` + Fastify 413 传输码；`localizeError.test.ts` 读取服务端目录并在漂移时失败，名称锁步 `docs/agents/error-codes.md`）；`toErrorMessage` 改为经 `localizeError` 归约——有码错误返回本地化消息，原始服务端/provider 英文与内部标识符不再作为主文案，改经诊断通道（`reportUnexpectedError`）保留为"技术详情"（`StudioJobsPanel` 的 `<details>` 折叠 + 失败行） ；契约层 `Invalid <label>.<key>` 归约为可读文案（apiContract/apiWorkflowContract/diagnosticsContract/loreExtractContract/proposalStream 同步走本地化）；未知码降级为通用可读消息且原始文本仅进技术详情 | 复现：`localizeError.test.ts`（21 用例）与 toErrorMessage（7）先红（英文直出/标识符泄漏）；修复后全绿 | 验证：frontend 145 文件/805 用例（含 zh 渲染断言）、`error_codes_gate` 无回归、gates/react-doctor(100)/spec 全绿

### DR-022 [P1] provider 配置可见性与错误语义

- [x] 已完成（2026-10-03）
- **问题**：设置页渲染全部 provider，未配置不禁用不标注；`/api/providers` 已返回 `model/configured/is_default` 但前端不读；未配置时生成报 `Provider '<x>' does not support streaming generation.`（掩盖缺 key 的真实原因）。
- **证据**：`StudioSettingsPanel.tsx:94-118`；`model_resolution.ts:74-80`；`proposal_pipeline.ts:186-191`；`provider-setup.md` 自认"选未配置 provider 会让所有生成失败"。
- **修复方向**：未配置项置灰 + 标注"（未配置 API key）"+ 链接指南；显示当前 model；未配置错误改为明确的凭证缺失 code/message。
- **验收**：未配置 provider 不可选；错误消息指向缺失凭证；测试覆盖。
- **验证**：`pnpm --dir server exec vitest run tests/api/provider_catalog.test.ts tests/api/studio_proposals_stream.test.ts`。
- **交付记录**：2026-10-03 | `b1151803`（wave 10a，与 DR-023 同批） | 新 `StudioProviderField`：按服务端目录（`configured/model/is_default`）渲染——未配置项禁用并在选项中标注"（未配置，缺少 API key）"，选中未配置项显示指向 provider 设置指南的警示，并展示解析后的 model；内置回退目录不含凭证事实，保持可选（禁用/标注只属于服务端目录路径） | 未配置生成：新增错误码 `PROVIDER_NOT_CONFIGURED`（`UnconfiguredTextProvider` 现在也提供 streaming 方法，在首帧前抛凭证错误；同步 `error-codes.md`/`ERROR_HTTP_STATUS`/前端 `localizeError` 映射）；SSE 与同步提案端点返回该码并带 `provider-setup` 指引，不再报"不支持流式" | 复现：`provider_catalog`/`studio_proposals_stream`/settings 用例先红（目录事实被忽略、错误码是能力文案）；修复后全绿（`studio_proposals_stream_unconfigured.test.ts` 独立承载新契约） | 测试拆分：`generation_capacity_api` 的 422 目录断言同步加入新码；`text_generation` 拆出 stream-budgets 与 helpers（行数门禁） | 验证：server 249 文件/1496 用例、frontend 145/808、gates/arch/react-doctor(100)/spec 全绿

### DR-023 [P1] 生成语言跟随（"双语"的最后一公里）

- [x] 已完成（2026-10-03）
- **问题**：任务无 locale、SYSTEM_PROMPT 无语言要求；mock provider 全英文且 revision 不引用作者正文；清理器只删英文模板前缀（"好的，以下是……"不会被剥离）。
- **证据**：`ports/text_generation.ts:53-58`；`proposal_prompts.ts:19-28`；`deterministic_story_provider.ts:88,94-116`；`sanitization.ts:4-25`。
- **修复方向**：项目级"写作语言"（默认取 UI 语言/大纲语言）注入 prompt；zh trial 模板与占位候选；清理器补中文模板前缀。
- **验收**：zh 项目用中文指令生成中文正文（mock 可断言）；清理器覆盖中文前缀用例。
- **验证**：`pnpm --dir server exec vitest run tests/contexts/`（prompt/sanitization 相关）。
- **交付记录**：2026-10-03 | `b1151803`（wave 10a，与 DR-022 同批） | 新 `application/writing_language.ts`：由项目大纲/正文推断写作语言（Han 为主→zh，否则 en；无迁移/无新设置字段），随 `TextGenerationTask` 携带（`deterministic_task_language.ts` 归一化）；prompt 层（`proposal_prompts.ts`）与 review 服务把语言写进 system/instruction，zh 项目请求中文正文、en 项目请求英文 | mock provider 拆分出 `deterministic_story_content.ts`/`deterministic_review_content.ts`：zh 任务产出确定性中文散文（仍引用章节号与标题、步骤语义不变），英文任务保持原行为 | `sanitization.ts` 增补中文模板前缀剥离（"好的，以下是…"等），合法正文不受影响 | 复现：`proposal_writing_language`/`deterministic_story_language`/`studio_proposals_language`/`review_service`（语言入 review 任务）/`sanitization` 中文用例先红后绿；`text_generation.test.ts` 的英文固定断言按语言分流更新并点名 | 验证：同 DR-022（全绿）

### DR-024 [P1] Review 归属 provider

- [x] 已完成（2026-10-03）
- **问题**：项目选 dashscope 时生成走 dashscope，但 Review 恒用 `LLM_PROVIDER`（默认 mock）；UI 不标注 → 用户以为在用真模型审稿。
- **证据**：`review_routes.ts:41-62`（拒绝客户端字段）；`studio_services_assembly.ts:110-113`；`review_service.ts:112`。
- **修复方向**：review provider 随项目设置（或显式标注当前 provider/model + "用其他 provider 重审"）。
- **验收**：review 的 provider 可见且可预期；测试覆盖。
- **验证**：`pnpm --dir server exec vitest run tests/api/review_app_wiring.test.ts tests/api/studio_reviews.test.ts`。
- **交付记录**：2026-10-03 | `dcbb42dd`（wave 10b，与 DR-025 同批） | Review 改为按项目设置解析 provider（`ReviewService.providerNameForProject`：目录内取值优先，未知存量值回落 env 默认；`review_routes` 继续拒绝客户端自选字段）；实际运行的 provider 随评估与任务落库（`review_outcome_store`/`review_store_part` 读项目 provider + 结果 provenance），失败任务按记录 provider 重试 | UI：评审面板在最新发现上方标注"由 {provider} · {model} 审阅"（en/zh 文案 + `StudioReviewPanel` 用例） | 复现：`review_service`（项目 provider 生效/未知值回落）、`review_app_wiring`（与 env 默认不一致时保持项目选择、失败任务按项目 provider 重试）先红后绿 | 验证：server 250 文件/1500 用例、frontend 145/809、gates/arch/react-doctor(100)/spec 全绿

### DR-025 [P1] review 超时下限

- [x] 已完成（2026-10-03）
- **问题**：`chapter_draft/chapter_revision` 有 180s 地板，但 `editorial_review` 走默认 30s 且重试 3 次 → 长稿送审必超时并白烧 3 次调用。
- **证据**：`provider_http.ts:12,221`；`provider_http.test.ts:163`（明确断言 30s）；`review_service.ts:118`。
- **修复方向**：给 `editorial_review`（及 `lore_extract`）设置独立超时下限（≥180s 或独立 env）；超时消息写入 job.error 供 UI 展示。
- **验收**：review 超时可配置且默认足够长；测试更新。
- **验证**：`pnpm --dir server exec vitest run tests/contexts/provider_http.test.ts`。
- **交付记录**：2026-10-03 | `dcbb42dd`（wave 10b，与 DR-024 同批） | `effectiveTimeoutSeconds` 改为按显式"长文步骤"集合套用 `LONG_FORM_TIMEOUT_FLOOR_SECONDS=180`（chapter_draft/chapter_revision/editorial_review/lore_extract；未来短步骤不会被误套地板），沿用既有 `LLM_TIMEOUT` 之上取 max、未新增 env；超时错误照常写入 job.error（UI 已有的失败行）| 复现：`dashscope_provider` 原断言"非章节步骤保持 30s"被 DR-025 契约替换（更新并点名），新增 `dashscope_provider_timeout_floor.test.ts`（章节 180s 地板 + review 180s 地板替代 30s 基线，含 179,999ms 不触发、180,000ms 触发断言）与 `review_app_wiring` "reports the editorial review's floored timeout in the job error" | 测试拆分：dashscope 测试拆出 helpers/floor 文件（行数门禁） | 验证：同 DR-024（全绿）

### DR-026 [P1] 流式时限与诊断

- [x] 已完成（2026-10-03）
- **问题**：180s 是从 dispatch 起算的绝对截止（不随帧重置），健康长流会被斩；SSE 无心跳帧、首个 delta 前不写 header；provider 在 200 的 SSE 里回错误负载被静默忽略（最终报 JSON contract 错）；客户端 30s 不读即 destroy（笔记本休眠即失去生成）。
- **证据**：`streaming_generation.ts:212-232`；`provider_response_lifecycle.ts:39-47`；`proposal_stream_response.ts:6-11,13,110-120,155-158`；`dashscope_extractors.ts:74-96`。
- **修复方向**：区分"绝对上限"与"静默预算"（或按 step 放宽并暴露设置）；补 `:` 心跳；识别 SSE 内错误帧并透出稳定 code；drain 超时区分客户端卡死与可续传。
- **验收**：长流不再被静默周期杀；错误帧有可读诊断；测试覆盖。
- **验证**：`pnpm --dir server exec vitest run tests/contexts/provider_streaming_deadline.test.ts tests/api/proposal_stream_response.test.ts`。
- **交付记录**：2026-10-03 | `301db695` + `2c8393b0`（wave 10c + 补齐 10c2） | ① 心跳与诊断（301db695）：服务端在等待下一帧期间每 15s 发 `: heartbeat` 注释帧（首个 delta 前仍不写 header，保留 pre-stream 错误信封；写失败走同一 monitor）；客户端墙钟看门狗（静默 90s 默认，0 关闭）→ `ProposalStreamStalledError` 中止 + `[proposal-stream]` 异常日志，容忍注释帧，EOF/中断报告"已收 N delta 帧/M 字节"。② 补齐（2c8393b0）：`ProviderResponseDeadline` 增加 `rearm()`，每收到一帧即重置绝对预算——dispatch+首帧仍受绝对上限，之后由逐帧静默预算（首字节/空闲）治理，健康长流不再被 180s 静默斩（旧钉子 "does not reset the absolute deadline while a stream keeps dripping frames" 被具名替换为两条：健康长流存活 + 超静默仍中止）；DashScope 与 OpenAI 兼容适配器识别 200 SSE 内的错误负载（`error.message`/原生 `code`+`message`）→ 归一化 `PROVIDER_FAILED` 携带 provider message+code，不再退化为 JSON contract 错 | 复现：长流在绝对预算处被拒 / 错误帧静默成功或报 contract 错（原始输出在 `$COMMANDCODE_SCRATCHPAD/gap-repro.txt`）| 回归：`provider_streaming_timeouts`（11）、`provider_streaming_failures`（4）、`provider_streaming_deadline/retry`、`provider_sse_boundaries`、`provider_http`（22）等 20 文件 144 用例；API 级 `studio_provider_failure_diagnostics`、`proposal_stream_stall_reason`（job.error 逐字含 stall 原因）| 已知边界（后续条目候选）：适配器仍把"无终止帧的 EOF"当正常结束；客户端主动中止与 job 完成间的语义维持 DR-006 约定 | 验证：server 255 文件/1517 用例、frontend 148/819、gates/arch/react-doctor(100)/spec 全绿

### DR-027 [P1] 生成端点幂等键

- [x] 已完成（2026-10-03）
- **问题**：in-flight guard 只挡"同 target 的并发同请求"且是进程内的；顺序重复提交（网络抖动后重发）必然产生第二份 job 与 usage（双份计费）。retry 端点强制 Idempotency-Key，形成不对称契约。
- **证据**：`operation_in_flight.ts:17,44-98`（自认 process-local）；`job_routes.ts:104-140`。
- **修复方向**：生成端点接受可选 `Idempotency-Key`，命中已存在 job 时返回同一 job（复用 retry 幂等机制）。
- **验收**：同 key 重放不产生新 job/usage；测试覆盖。
- **验证**：`pnpm --dir server exec vitest run tests/api/studio_proposals.test.ts tests/api/job_retry_idempotency_contract.test.ts`。
- **交付记录**：2026-10-03 | `04ab5d74`（wave 10d） | 两个生成端点（同步 + SSE）接受可选 `Idempotency-Key`（16–128 字符、与 retry 同格式），经 `job_request_claim.ts` 复用 retry claim 模式：`jobs.request_idempotency_key` 列 + `(project_id, request_idempotency_key)` 部分唯一索引（迁移 `0023`，经 `db:generate` 生成）——重复请求要么等待并加入赢家（并发插入经唯一冲突回归），要么重放已存 job/usage/终帧；服务端不重复调用 provider、不写第二条 usage。客户端在 `useProposalStreamSession`/`useWholeBookChapterRun` 各生成点铸造"每逻辑生成一个"键（sessionStorage 按 project+document+operation 作用域），未知结果保留（重发即重放），成功或确定性失败清除。重做说明：初版曾实现进程内 guard（`request_idempotency.ts`），因遮蔽持久 claim 的重放路径且违背"复用 retry 幂等机制"被整体替换（guard 与测试已删除，`proposal_retry_replay_boundaries` 原样恢复通过）。范围：仅提案生成端点；review/lore/export 的 job 创建维持既有 in-flight + 容量准入。 | 复现：同 key 连发两次在基线产生两条 job（修复后同 id、单次 provider 调用、单条 usage）；并发同 key 先查后插竞态回归赢家 | 回归：`proposal_generation_idempotency`（8：同步重放、流式 done/失败重放、竞态、异 key/跨项目独立、无 key 不变 + 键格式校验）、`proposal_generation_idempotency_contract`（OpenAPI：生成键可选、retry 键必需）、`restart_persistence`（jobs 列清单含新列）| 联动：OpenAPI 基线 + 前端生成类型更新；README 无过时幂等承诺（已核对） | 验证：server 255 文件/1517 用例、frontend 148/819（新增 `proposalStream.idempotency`、`useStudioProposal.idempotency`、`retryAttemptRegistry` 生成作用域用例）、gates/arch/react-doctor(100)/spec 全绿

### DR-028 [P1] usage 语义与成本

- [x] 已完成（2026-10-03）
- **问题**：provider 未报 usage 时 `prompt_tokens` 被写成 instruction 词数（通常 0–5）、completion 写 proposal 词数；usage 只在"完成"时落库，重试/超时/失败的真实消耗不可见；`estimated_cost` 是只存在于 schema 的死列；无任何预算/告警护栏。
- **证据**：`proposal_landing.ts:114-118,205-213`；`job_usage_tables.ts:66-69,81`；全仓 grep 仅 migration 命中 estimated_cost。
- **修复方向**：usage 增加 `attempt/outcome` 与"provider 未报 usage"标记；决策 `estimated_cost`（实现价格表或从 schema 删除）；项目级预算/告警。
- **验收**：用量面板数字不再误导；失败/重试可见；决策落地。
- **验证**：`pnpm --dir server exec vitest run tests/api/studio_usage.test.ts`；`pnpm --dir frontend exec vitest run`（用量组件）。
- **交付记录**：2026-10-03 | `2630cc7f`（wave 10e） | `usage_events` 增 `outcome`（completed/failed，CHECK 约束）与 `token_source`（provider/estimated/unreported）：provider 上报→`provider`；未上报走词数回退→显式 `estimated`（不再冒充 provider 数字）；每个到达 provider 的失败尝试→零 token `unreported` 行（review/export 等不记 usage 的 kind 除外），重试链上的原失败与新结果各留一行。聚合/API/前端类型新增 `failed_attempt_count`、`estimated_requests`（含 per-model `failed_attempts`/`estimated_requests`）；用量面板增"失败调用"卡 + 两条披露（失败不并入 token 合计、估算来源说明，zh/en 文案）。决策落地：删除 `estimated_cost` 死列（迁移 `0024`/`0025` 重建表，已核对全仓仅 schema/写入处引用）。 | 复现：修复前 provider 未报 usage 时 prompt_tokens=instruction 词数（0–5）且失败尝试零行；修复后语义见上 | 回归：`studio_usage_provenance`（估算 vs provider 标记、失败行）、`job_store_transactions`（失败 job+usage 同事务、回滚不孤儿）、`safe_usage_persistence`、用量 API/写入面板/契约测试；13 个既有 API 测试文件按新账本契约具名更新（失败尝试改为显式断言 failed/unreported 行、重试链索引后移、payload 增字段），无断言弱化 | 联动：OpenAPI 基线 + 前端生成类型 + 写作统计解析器（statsContract）字段补齐 | 范围说明：修复方向中的"项目级预算/告警"不在验收内，未实现（候选后续条目） | 验证：server 256 文件/1520 用例、frontend 148/819、gates/arch/react-doctor(100)/spec 全绿

### DR-029 [P1] 搜索 UI

- [x] 已完成（2026-10-03）
- **问题**：零结果不渲染任何提示；结果点击只切文档不定位命中；硬编码 `LIMIT 30`、无 cursor/总数；无排序选项。
- **证据**：`StudioNavigatorSearch.tsx:58-72`；`useStudioPageModel.ts:207`；`db/document_search.ts:14-15,61`。
- **修复方向**：空态文案 + 结果计数；返回 `total`/cursor；结果带偏移支持跳转高亮。
- **验收**：0 结果有提示；>30 有"更多"；点击可定位。
- **验证**：`pnpm --dir frontend exec vitest run src/features/studio/`（搜索相关）；`pnpm --dir server exec vitest run tests/api/studio_search.test.ts`。
- **依赖**：DR-003（分词修复先落地，否则中文仍无结果可展示）。
- **交付记录**：2026-10-03 | `636fc7b5`（wave 11） | 服务端搜索页：`matchDocumentIndex` 返回 `total`（同项目同 MATCH 的诚实 `COUNT(*)`，非页大小）与 `next_offset` 游标；排序键补 `document_id ASC` 保证 LIMIT/OFFSET 分页不重不漏；每命中附 `match_term`（首个归约元素的显示形态，供定位）。前端：零结果提示、结果计数（单复数）、"更多"分页（hasMoreResults/isLoadingMore）、点击结果 → 打开文档 + 经 `useSearchReveal` 把 term 交给编辑器（`@codemirror/search` setSearchQuery + findNext，token 去重；仅对当前活动文档生效；标题命中而正文无该词时不伪造跳转，仅打开文档）；请求 schema `q` 增加 maxLength，输入框 maxLength=200 | 复现：修复前零结果无提示、>30 无入口、点击不定位 | 回归：`studio_search_pagination`（跨页不重不漏/总数）、`StudioNavigatorSearch.test`（提示/计数/更多/跳转意图）、`useStudioSearchJobs.test` 更新为分页契约、`StudioNavigator`/`StudioEditorPane` 用例 | 过程修复：payload guard/导航 fixture 补 `match_term`、`apiContract.ts` 拆出 `searchContract.ts`、`useStudioPageModel` 抽出 `studioSearchModel` 助手、navigator 布尔 props 归并为 `searchState`（react-doctor）| 验证：server 258 文件/1525 用例、frontend 149/826、gates/arch/react-doctor(100)/spec 全绿。（"排序选项"未含在验收内，未实现）

### DR-030 [P1] 事件循环冻结（搜索路径）

- [x] 已完成（2026-10-03）
- **问题**：搜索 handler 同步执行；`q` 无长度/token 上限；8-token 停用词串要求 bm25 对全匹配集打分（LIMIT 不能剪枝）→ 实测 453–970ms 进程级冻结（SSE delta 无法 flush、healthcheck 迟到）。
- **证据**：`server/src/contexts/studio/interface/http/project_routes.ts:173`；`studio_request_schemas.ts:141-144`；`fts_match_query.ts:12`；`document_search.ts:59-61`；实测（200 章/6.16MiB 语料）452.9ms@8 tokens。
- **修复方向**：`MAX_MATCH_TOKENS` 8→3（实测压到 ~71ms）；高频词短路（document frequency 超阈值降级 OR/不参与 rank）；`q` 加 `maxLength`。
- **验收**：最坏查询工作集显著下降；有界输入；测试覆盖上限行为。
- **验证**：`pnpm --dir server exec vitest run tests/api/studio_search.test.ts tests/contexts/`（match query 相关）。
- **备注**：与 DR-003 相邻但独立：先测量再隔离，不要为此引入 worker thread。
- **交付记录**：2026-10-03 | `636fc7b5`（wave 11） | `MAX_MATCH_ELEMENTS` 8→3（JSDoc 注明实测 453–970ms → ~71ms 的动因；归约/引号/AND 语义与恶意输入防护不变）；`q` 增加 maxLength 使最坏输入有界；新增 `studio_search_bounds` + `fts_match_query` 上限用例（5 元素归约到 3 的语义、超长 q 拒绝、恶意查询仍被引号包裹）| 复现：8 元素对抗查询在 6.16MiB 语料上同步 452.9ms 冻结事件循环 | 备注落实：未实现"高频词短路"（不在验收内，保留候选）、未引入 worker thread（遵备注）| 验证：见 DR-029 行（全绿）

### DR-031 [P1] 启动备份策略

- [x] 已完成（2026-10-03）
- **问题**：每次启动（含崩溃重启循环）都写一份等于库大小的备份，永不清理；restore 还需约 2×库大小的空闲空间 → 磁盘耗尽后连恢复都做不了。
- **证据**：`startup.ts:56-64`；`backup.ts:22-32`；`compose.yaml:4`（restart: unless-stopped）；实测 boot2/boot3 各增一份 `.bak`。
- **修复方向**：仅当 schema 变化或显式请求时备份；保留 N 份/按时间轮转；备份前检查剩余空间并给出明确错误。
- **验收**：连续重启不再线性增长备份；空间不足时消息可读；CLI 测试覆盖。
- **验证**：`pnpm --dir server exec vitest run tests/apps/cli/`。
- **交付记录**：2026-10-03 | `90e5f271`（wave 12a） | 启动备份改为"仅在确有迁移待执行时"：新增 `pending_migrations.ts`（镜像 drizzle 判定：journal 最新 `when` vs `__drizzle_migrations` 最新 `created_at`；缺表=待迁移；探测不了则保守备份）；保留最新 3 份（只清理本模块命名的文件族）；写前 `statfs` 剩余空间检查（不足报 required/available 字节与建议、零写入）；写后 `quick_check` 自检，失败即删产物（含 sidecar）。未改 `compose.yaml`（部署行为需另行授权，且不在验收内）。 | 复现：连续三次启动 → 0/1/2 份备份线性增长；修复后无待迁移 0/0/0，待迁移恰好 1 份 | 回归：`backup_policy`（保留/清理/自检/低空间注入探针可读报错零写入）、`backup_policy_cli`（首启备份 1 次、二次不增、坏备份 exit 1 且删文件）、`startup_pipeline`/`cli.test.ts` 两处旧断言具名更新（正向覆盖保留在新用例）| 验证：见 §10

### DR-032 [P1] doctor 只读化与迁移分离

- [x] 已完成（2026-10-03）
- **问题**：`doctor` 实际会取排他锁、执行迁移与数据对账、写备份；服务器在跑时 exit 1 且把错误消息塞进 `quick_check` 字段，易被误判为数据库损坏。
- **证据**：`apps/cli/main.ts:210-228,88`（help 未提写入副作用）；`reconciled_studio_database.ts:26-40`；实测 doctor 前后 backups 计数 +1。
- **修复方向**：doctor 默认 readonly（不迁移/不备份/不取写锁）；迁移独立为 `cli migrate`；错误字段与消息修正。
- **验收**：doctor 对副本零写入；运行中可安全执行（或明确拒绝并给出正确原因）。
- **验证**：`pnpm --dir server exec vitest run tests/apps/cli/`。
- **交付记录**：2026-10-03 | `82aaa64f`（wave 12b） | doctor 改为只读（`doctor_command.ts`）：干净副本以 `query_only=ON` 打开（关闭时清理自身瞬态 sidecar，目录/字节/mtime 前后一致——实测覆盖），存在 WAL sidecar（服务器运行中/非正常退出）时 `readonly:true` 附着不改写；报告 `quick_check/journal_mode/foreign_keys/owner/document_index/migrations{applied,pending}/error`；锁与权威冲突改由 `error` 字段承载（不再污染 `quick_check`），`timeout:0` 保证锁冲突立即以正确原因报错；新增 `migrate_command.ts`（`novel-engine migrate`：排他锁→DR-031 条件备份→迁移→导出对账→作业恢复，打印 `{database, migrations}`）；USAGE 明示 doctor 只读与 migrate 写入路径 | 复现：doctor 在待迁移副本上 +1 备份并迁移、服务器运行中 exit 1 且把 "already owned" 塞进 quick_check；修复后 doctor 零写入（含运行中 exit 0），migrate applied 26 且恰好 1 份备份 | 回归：`doctor_readonly_cli`（6：零写入/无迁移行/运行中只读/锁库正确原因/缺库不建/USAGE）、`migrate_cli`（3）；`cli.test.ts`/`cli_database_authority`/`cli_export_recovery` 三处旧断言具名更新（语义变更，无弱化）| 验证：见 §10

### DR-033 [P1] 占位密钥守门

- [x] 已完成（2026-10-03）
- **问题**：`.env.example` 的 `change-me-to-a-long-random-local-secret` 能通过 production 守门（只拒绝空值、哨兵、<16 字符）；README 表格写默认 "sample value"，与代码不一致。
- **证据**：`server_config.ts:27,178-186`；`.env.example:9`；实测该值 START ALLOWED。
- **修复方向**：`.env.example` 留空或与哨兵同值；production 拒绝 `change-me*` 前缀；README 同步。
- **验收**：占位值在 production 下被拒；文档与代码一致。
- **验证**：`pnpm --dir server exec vitest run tests/`（config 相关）。
- **交付记录**：2026-10-03 | `a06df731`（wave 12c） | production 守门拒绝 `change-me*` 前缀（`PLACEHOLDER_SECRET_PREFIX` + 守卫旁 JSDoc 说明；精确哨兵值在非生产仍经 `secretFrom` 归零）；README/README.zh-CN 密钥与 CORS/代理表措辞与代码一致；`server/vitest.config.ts` 固定 `NODE_ENV=test` 消除宿主环境漂移（本机 shell 为 production）。偏离说明：`.env.example` 属禁区未改——代码侧拒绝已使示例值在生产 fail fast，满足验收。 | 复现：该占位值基线 START ALLOWED；修复后拒绝 | 回归：`server_config.test`（17：dev 允许占位/生产拒绝/空 CORS 拒绝）与拆分出的 `server_config_production.test`（9）| 验证：见 §10

### DR-034 [P1] 反向代理配置陷阱

- [x] 已完成（2026-10-03）
- **问题**：A. 前置代理但未设 trusted proxies → 所有客户端共用一个限速桶，匿名者可让作者长期 429（登录 DoS）；B. TLS 终止后 `trustProxy` 未启用，浏览器 setup 的 Origin 校验只能靠 CORS 列表兜底，沿用占位 origin 时 setup 403（而 curl 反而成功）；C. compose 默认带占位 `https://app.example.com`。
- **证据**：`client_identity.ts:166-170`；`auth_registration.ts:51-57`；`origin_validation.ts`；`http_server_policy.ts:23-40`；`compose.yaml:12`、`deploy/compose.yaml:18`；实测 Origin 组合。
- **修复方向**：由 `trustedProxies` 推导 `trustProxy`；setup 的 expected origin 支持受信 `X-Forwarded-Proto`；compose 不提供占位 origin（缺省即 fail fast）；文档补部署 checklist。
- **验收**：反代 + 默认配置下 setup 可用、限速按真实客户端隔离；测试/文档覆盖。
- **验证**：`pnpm --dir server exec vitest run tests/apps/api/`；`pnpm --dir server gates`。
- **交付记录**：2026-10-03 | `a06df731`（wave 12c） | 两 compose 删除占位 `https://app.example.com`（`SECURITY_CORS_ORIGINS` 缺省为空 → 生产 fail fast）并透传 `SECURITY_TRUSTED_PROXIES`；`check_compose_passthrough.mjs` 扩展为可机检该契约（占位默认/丢失透传即失败，含负例）；setup 的受信 `X-Forwarded-Proto` 行为（DR-009 的 trustProxy 推导使其生效）以 `setup_proxy_origin` 固化（受信代 → HTTPS origin 通过；不受信 peer 的转发头被忽略 403）；`deploy/README.md` 增反代 checklist（5 条 + 示例）；getting-started（EN/ZH）与 quickstart 补本地 Docker 需显式配置（`.env` + `compose.override.yaml` 开发模式）的说明。A 项（未设代理时的共桶风险）以文档 checklist 覆盖（DR-009 已实现按真实客户端隔离的机制）| 复现：`docker compose config` 解析出假 origin 且 compose 不透传可信代理 | 回归：`compose_passthrough_gate`（6）、`cors_contract`（4）、`setup_proxy_origin`（2）| 验证：见 §10

### DR-035 [P1] 未认证暴露面收口

- [x] 已完成（2026-10-03）
- **问题**：production 下 `/openapi.json`（125KB 全量契约）、`/version`（含 build/environment 指纹）、`/health*`、`/api/setup` 探针均可匿名访问。
- **证据**：`apps/api/app.ts:211`；`health_routes.ts:70,100,110`；`version_route.ts:29`；实测 200。
- **修复方向**：生产把 `/openapi.json` 收到 owner 门后或加开关；`/version` 去掉 runtime/build 指纹。
- **验收**：生产匿名不再获得完整契约与构建指纹；测试覆盖。
- **验证**：`pnpm --dir server exec vitest run tests/api/`；`pnpm --dir server gates`（涉及路由需 openapi:snapshot）。
- **交付记录**：2026-10-03 | `a06df731`（wave 12c） | production 下 `/openapi.json` 走 owner 门（匿名 401；无持久层 503 fail-closed；dev/test 保持开放）；`/version` 生产仅回 `{name, version}`（runtime/environment/build 指纹移除；dev/test 全量）；`/health*` 维持匿名但字段面经用例固化（无路径/运行时/构建/环境泄漏）；`/api/setup` 维持 DR-008 首启语义（不在本项范围）。 | 复现：基线匿名即得全量契约与 build/runtime 指纹（新增用例先红）| 回归：`version.test.ts` +4（生产裁剪/开发全量/匿名 401 与 owner 200/无持久层 503）、`health.test.ts` +1 | 联动：OpenAPI 基线零漂移（`gate:openapi` 通过），前端契约未变 | 验证：见 §10

### DR-036 [P1] 备份边角

- [ ] 未开始
- **问题**：restore 校验会打开 `.bak` 从而在 backups/ 留下 `-shm/-wal` 残留；备份命令本身不做 quick_check 自检；备份为明文且未在 UI/指南中提示。
- **证据**：实测 `restore.ts:51-56` 后出现 sidecar；`backup.ts:22-37` 无自检。
- **修复方向**：校验后清理 sidecar；备份后自检 `quick_check`，失败删除半成品；文档说明备份明文。
- **验收**：backups/ 无 sidecar 残留；坏备份不会静默留下。
- **验证**：`pnpm --dir server exec vitest run tests/apps/cli/restore_cli.test.ts`。
- **交付记录**：2026-10-03 | `90e5f271`（wave 12a） | 校验拆分为 `verifyRestoreInput`（无论成败都清理输入 sidecar `-wal/-shm/-journal`；清理失败与校验失败以 AggregateError 并存）+ `assertRestoreInput`（原语义不变）；备份写后 `quick_check` 自检失败即删产物（与 DR-031 同批交付）；CLI USAGE 增"备份为明文 SQLite 文件，须仅限操作者可读"。 | 复现：restore 校验后 backups/ 出现 `.bak-shm`/`.bak-wal` 残留、坏备份可静默留下 | 回归：`restore_cli` 新增"校验后无 sidecar"用例、`backup_policy` 断言产物可过 quick_check 且自检失败删文件 | 验证：见 §10

### DR-037 [P1] 导入修复

- [x] 已完成（2026-10-03）
- **问题**：source hash 含目录绝对路径与内容 → 同目录改名/改一章内容即重复建项目；导入丢弃源章节标题全部变 `Chapter N`；无前端入口（仅 preview + CLI）。
- **证据**：`fs_legacy_workspace_reader.ts:93,137-147`；`import_service.ts:60-68`；`project_store_part.ts:185-199`；`import_routes.ts:60-65`。
- **修复方向**：hash 去根路径（相对路径+内容）；从首行标题/文件名推断章节名；决策 Web 导入向导或明确文档标注 CLI-only（可并入 DEC-05）。
- **验收**：重复导入行为可预期（显式提示或幂等）；标题保留。
- **验证**：`pnpm --dir server exec vitest run tests/contexts/legacy_import_service.test.ts`（或对应文件）。
- **交付记录**：2026-10-03 | `d61b9b37`（wave 13） | source hash 改为"相对路径 + 原始字节"（去根路径）：同内容换目录不再重复建项目，改一章内容仍可检出；章节标题从源首行标题/文件名推断并随 workspace 保留（不再 `Chapter N`）；重复导入按幂等行为处理并测试钉住；文档明确导入为 CLI-only（不做 Web 向导，方向记录归 DEC-05）。 | 复现：改名目录 → 新 sourceHash 重复建项目、标题全丢；修复前新用例先红 | 回归：`legacy_import_service`/`legacy_import_demo_workspace`/`studio_imports` 14 用例 + `legacy_workspace_reader`（`title` 字段与"根无关 hash"两处旧契约具名更新为 DR-037 语义）| 验证：见 §10

### DR-038 [P1] 关键回归与测试模式收敛

- [x] 已完成（2026-10-03）
- **问题**：① autosave 失败路径（DR-001）、CJK 搜索（DR-003）、413 保存（DR-048）都没有用例；② `frontend/src/app/i18n/dictionaries/dictionaries.test.ts` 把英文文案按字节钉死，导致改一句 UI 文案要动三处（字典+断言+e2e）。
- **证据**：`dictionaries.test.ts:27`；各域报告"测试盲区"节。
- **修复方向**：补三类回归；把字典测试改为"键对齐 + 非空 + 关键锚点白名单"，不再全量钉文案。
- **验收**：新增用例在修复前失败、修复后通过；字典测试只锁必要契约。
- **验证**：`pnpm --dir server test && pnpm --dir frontend test:unit`。
- **进展**：autosave 失败/恢复路径已随 DR-001/DR-002 交付回归覆盖（2026-10-01）；CJK 搜索用例已随 DR-003 交付（2026-10-02）；413 用例仍待 DR-048。
- **交付记录**：2026-10-03 | `d61b9b37`（wave 13） | 字典测试收敛为"双向键对齐 + 非空 + 锚点白名单"：白名单逐条对照 `frontend/tests/e2e-ts` 定位器与按文案定位的单测核实（删除两处孤儿锚点），普通文案改动不再需要同步测试；autosave 失败回归（DR-001/002）与 CJK 搜索回归（DR-003）确认已存在；413 保存用例明确随 DR-048 交付（本项未重复实现，见"进展"注记）。 | 复现：基线字典测试全量钉死英文文案、改一句需动三处 | 回归：`dictionaries.test.ts`（4：parity 双向/非空/锚点）| 验证：见 §10

### DR-039 [P1] 文档-实现对齐

- [x] 已完成（2026-10-03）
- **问题**：① README/deploy 反复写 "Once v0.8.0 is published"，但 tag/raw URL/GHCR 镜像均已可用（实测）；② guides 宣称 diff（`writing-guide.md:161`）、搜索"跳到命中"（`:169-171`）、"Move to volume…"（`:48-49`）均不成立；③ CONTEXT.md/CONTEXT 的 Review/Snapshot、rolling summary、Job 措辞与实现不符；④ spec 路由清单/命令数/`note` 类型滞后。
- **证据**：各域报告的"规格宣称 vs 实现落差"与"③ 跨界发现"节。
- **修复方向**：逐条修正；对"未来能力"的文案改为明确"未实现/规划中"表述；规格补 `note` kind、路由前缀、CLI 命令数、字数定义（DR-005）。
- **验收**：文档不再承诺不存在的功能；`pnpm spec:validate` 通过。
- **验证**：`pnpm spec:validate`；`pnpm --dir server gates`（llms-txt/hygiene）。
- **交付记录**：2026-10-03 | `d61b9b37`（wave 13） | 逐条对齐：README/README.zh-CN/deploy README 的发布态与配置文案、openwiki guides（writing/backup/upgrading，EN+ZH）、architecture 与 studio-workspace 文档、quickstart、CONTEXT.md 术语（Review/Snapshot/rolling summary/Job）、openspec 规格补 `note` kind/路由前缀/CLI 命令数（含 reindex/migrate/owner）/DR-005 字数定义；未实现能力明确标注"未实现/规划中"。 | 复现：guides 宣称的 diff / "跳到命中" / "Move to volume" 在基线不成立（前序波次已实现，本次按现实改文）；README "Once v0.8.0 is published" 与 tag/GHCR 现实不符 | 回归：`pnpm spec:validate`（strict）与 `server gates`（llms-txt/hygiene/ssot）全绿 | 验证：见 §10

---

## 4. P2 详细条目（简式）

### DR-040 [P2] dev 模式会话密钥持久化

- [x] 已完成（2026-10-03）
- **问题**：非 Docker、未配置 `SECURITY_SECRET_KEY` 时每进程随机生成，重启即全体登出。
- **证据**：`apps/api/app.ts:170-176`；`auth_service.ts:115`。
- **修复方向**：非容器环境也把随机 secret 持久化到 `data/.secret`（0600）。
- **验证**：`pnpm --dir server exec vitest run tests/api/auth_session.test.ts`。
- **交付记录**：2026-10-03 | `206c8dbe`（wave 14a） | 无配置 secret 的非生产启动把生成的 secret 持久化到数据目录 `data/.secret`（0600，一次生成、复用），会话跨重启保留；env secret 优先、生产守门行为不变。 | 复现：基线每次非生产重启生成新 secret → 全员登出；`config_startup` 旧断言（401）按新契约改为"重启保留（200）+ 删除 `.secret` 后失效（401）" | 回归：`auth_session_secret`（重启保留/0600/env 优先）、`auth_session`、`config_startup` | 验证：见 §10

### DR-041 [P2] 容器加固与可观测性

- [x] 已完成（2026-10-03）
- **问题**：容器以 root 运行、无 `read_only`/`cap_drop`/资源限制；无 `/metrics`、无 `LOG_LEVEL`；日志本身未泄露敏感信息（此项是好的）。
- **证据**：容器实测 `id -u=0`；grep `LOG_LEVEL` 零命中。
- **修复方向**：`USER node` + 只读根 + tmpfs；可选内网 `/metrics`；`LOG_LEVEL` 环境变量。
- **验证**：`docker build` + compose 启动人工验证；`pnpm --dir server gates`。
- **交付记录**：2026-10-03 | `206c8dbe`（wave 14a） | Dockerfile/compose：非 root `node` 运行 + 只读根 + tmpfs + `cap_drop: [ALL]` + `no-new-privileges` + 资源限制；新增内网 `GET /metrics`（Prometheus 文本：进程/uptime/任务/用量类指标；loopback 或受信 peer 或 owner 会话可读，路由与门禁同步）；`LOG_LEVEL` 由 `log_level.ts` 驱动 logger，写入 README 并经 compose 透传（passthrough 锚点同步）。 | 复现：容器 `id -u`=0、无加固、无 metrics/LOG_LEVEL | 回归：`metrics_route`（4：loopback 匿名、非 loopback 需 owner、内容面）、`compose_passthrough_gate`、`server_config*`；`docker compose config -q` 双文件通过；`docker build` 的完整容器冒烟由 CI 容器任务拥有（本地按可用性执行并在交付报告注明） | 验证：见 §10

### DR-042 [P2] 快照/审阅可见性与删除指引

- [x] 已完成（2026-10-03）
- **问题**：`project_snapshots` 用户永远看不到；审阅历史列表不可点开（详情端点已存在）；被快照引用的文档删除 409 无用户可读的解法。
- **证据**：`useReviewHistory.ts:92-123`；`StudioReviewHistoryList.tsx:68-82`；`document_store_part.ts:139-146`。
- **修复方向**：审阅行接详情；快照给出可读名字；删除失败时给出指引。
- **验证**：`pnpm --dir frontend exec vitest run`（审阅组件）；`pnpm --dir server exec vitest run tests/api/`（review 相关）。
- **交付记录**：2026-10-03 | `c3a9674c`（wave 14b） | 审阅历史行改为按钮：点击选中该行详情（`useReviewHistory` 以 `selectedReviewId` 驱动详情读取，空选回退最新），`aria-pressed` 标记选中；审阅 provenance 显示快照短名（`shortSnapshotId`，`review.snapshotLabel`）；导出历史行同样显示快照短名（`export.history.snapshotLabel`）；`errors.codeSnapshotConflict`（zh/en）补可读解法"先删除引用该文档的导出快照/导出，再删除文档"。 | 复现：基线列表行为不可点开的静态文本、快照 id 不可见、409 仅一句英文冲突描述 | 回归：`StudioReviewPanel`（5：选中态/点击回调/快照短名）、`StudioReviewHistoryList`（选中样式与 aria）、`useReviewHistory`、`dictionaries`（键对齐）、`localizeError` 快照冲突文案 | 验证：见 §10

### DR-043 [P2] Beat 候选与规则明示

- [x] 已完成（2026-10-03）
- **问题**：beat 关联要求精确记住 outline 标题；多 outline 文档时只有第一个生效且无提示。
- **证据**：`StudioBeatPanel.tsx:92-99`；`beat_association_service.ts:46-54,76-84`。
- **修复方向**：服务端返回候选列表，UI 改下拉；多 outline 时明示规则或报错。
- **验证**：`pnpm --dir server exec vitest run tests/api/studio_beats.test.ts`。
- **交付记录**：2026-10-03 | `aa559112`（wave 14c） | 章节 beat 视图携带候选目录与"权威 outline"（`BeatOutlineAuthority`：文档 id/标题/outline 数量），服务端仍以阅读顺序第一个 outline 为权威但**显式披露**且链接仍只接受该 outline 的 beat；`StudioBeatPanel` 改为下拉选择（`useBeatCandidates` 懒加载 + 刷新按钮 + 错误态），多 outline 时显示"本项目有 N 个 outline，beats 来自「X」"提示；既有的"背标题"输入路径退役 | 复现：基线只有自由文本输入，多 outline 时静默取第一个 | 回归：`studio_beat_candidates`（2：候选目录顺序；多 outline 披露计数 + 非权威 outline 的 beat 一律 422）、`studio_beats`（11，共享 `studio_beat_helpers`）、`StudioBeatPanel`（11：下拉选择/多 outline 提示/刷新） | 过程修复：契约拆出 `beatContract.ts`、测试拆分为 `studio_beats` + `studio_beat_candidates`、共享 helper 模块（行数门禁） | 验证：见 §10

### DR-044 [P2] 死代码与未接线清理

- [x] 已完成（2026-10-03）
- **问题**：同步提案端点无调用者；卷 API 方法零调用者（若 DR-017 选降级则删除）；`estimated_cost` 死列（随 DR-028 决策）；若干仅测试引用的导出。
- **证据**：`frontend/src/app/api.ts:79-86,170`；`job_usage_tables.ts:81`；架构报告"死代码/无引用导出"节。
- **修复方向**：按 DEC-05/DR-017/DR-028 决策删除或接线；删除前确认 react-doctor 的 `unused-export` 零容忍不受影响。
- **验证**：`pnpm --dir server gates && pnpm --dir frontend type-check`。
- **交付记录**：2026-10-03 | `52011933`（wave 14d） | 逐候选核验后清理：删除 `api.proposal`（同步客户端方法，运行期零调用——真实路径为 `streamProposal` + `api.acceptProposal`，仅 3 个测试 mock 覆盖行引用，一并删除）；删除零引用类型 `DictionaryChunk`、`LoreExtractRequest`/`LoreExtractRequestBody`、`LorebookWizardModel`；保留（有真实引用）：服务端 `/ai-proposals` 同步路由（服务端测试 + OpenAPI 快照引用）、卷 API 方法（DR-017 已接线）、test-only 导出（harness/factories/针脚，删除会破坏或削弱测试）。`estimated_cost` 核验：当前 schema 已无该列（仅历史迁移产物与一句说明注释），无需动作。 | 复现：全仓引用清单（556 个导出脚本化核验；`api.proposal` 仅测试 mock 引用） | 回归：`api*`/`useWholeBookLoop.*`/`useLorebookWizard.*` 用例全绿；react-doctor 0 诊断（unused-export 零容忍不受影响）| 验证：见 §10

### DR-045 [P2] 统计时区与负数解释

- [x] 已完成（2026-10-03）
- **问题**："今日字数"按 UTC 日分桶（UTC+8 作者 0–8 点看到昨天）；统计表出现 `已采纳 −364` 无解释。
- **证据**：`writing_stats_service.ts:15-18,49-55,66-78`；`StudioWritingStatsPanel.tsx:44,95-105`；截图 `writing-stats-zh.png`。
- **修复方向**：按浏览器时区分桶（或明确标注 UTC）；负数来源加解释文案。
- **验证**：`pnpm --dir server exec vitest run tests/contexts/writing_stats_calendar.test.ts`。
- **交付记录**：2026-10-03 | `206c8dbe`（wave 14a） | 统计按浏览器时区分桶：前端 `browserTimezone.ts` 上传 `tz_offset_minutes`，服务端按该偏移切日桶并在响应回显 `tz_offset_minutes`；面板显示时区提示与"负数来自恢复/回滚抵消"的解释文案（zh/en）。 | 复现：UTC 分桶下 UTC+8 作者 0–8 点看到昨天；`已采纳 −364` 无解释 | 回归：`writing_stats_calendar`、`studio_writing_stats`、`apiStatsContract`、`StudioWritingStatsPanel`（+tz 字段与提示）| 验证：见 §10

### DR-046 [P2] 前端本地化与离线

- [x] 已完成（2026-10-03）
- **问题**：硬编码英文串（`main.tsx`、`router.tsx`、`httpClient.ts`、`networkError.ts`、`proposalStream.ts`、契约层）；日期/数字不随语言；无离线提示；编辑器 aria-label 切换语言后不更新。
- **证据**：各域报告 i18n 节。
- **修复方向**：补 i18n 键；统一 Intl formatter 走 `getActiveLanguage()`；离线横幅 + 恢复重试。
- **验证**：`pnpm --dir frontend test:unit && pnpm --dir frontend lint`。
- **交付记录**：2026-10-03 | `52011933`（wave 14d） | 本地化收尾：外壳崩溃面板（`AppCrashFallback`）、HTTP 客户端、网络错误、提案流文案全部改走 `translateActive`（EN 值与旧字面量逐字节一致；新增 `errors.transport.*`/`errors.proposalStream.*`、`shell.error.*`、`shell.offline.notice` 键）；新增 `i18n/format.ts`（`formatCount/formatDateTime/formatDate`，按 `getActiveLanguage()` 每次调用解析、formatter 模块级预建）替换 5 处内联 `toLocaleString("en-US")` 与 5 处裸 `toLocale*`（Intl 此前全仓 0 使用）；`StudioOfflineNotice` 监听 online/offline 事件在 Studio 外壳显示离线横幅（zh/en）；编辑器 aria-label 经核验已在前序波次修复。 | 复现：断网无提示、语言切换不影响日期/数字、崩溃面板硬编码英文 | 回归：`format`（3）、`StudioOfflineNotice`（3：离线显示/恢复隐藏/清理）、`AppCrashFallback`（2）、`networkError`（2）+ 既有组件用例（语言切换后格式化跟随）| 验证：见 §10

### DR-047 [P2] revision 增长与保留策略

- [x] 已完成（2026-10-03）
- **问题**：每次自动保存插入整篇副本 + FTS 全量重写；无历史保留/合并策略；无正文体积预算（隐藏上限是 1 MiB HTTP body，见 DR-048）。
- **证据**：`document_revision_writes.ts:38-52`；`document_search.ts:26-32`；`grep "prune|retention" server/src` = 0；`structure_capacity.ts:15-22` 无正文预算。
- **修复方向**：相邻 autosave 合并（同秒/内容未变跳过）；保留策略（按时间/数量折叠）；规格补正文预算并与 DR-048 对齐。
- **验证**：`pnpm --dir server exec vitest run tests/contexts/revision_store_pagination.test.ts`（新增策略用例）。
- **交付记录**：2026-10-03 | `206c8dbe`（wave 14a） | 写入路径：内容未变跳过（不写 revision、不重写 FTS）；相邻窗口内的 autosave 折叠（删除无引用的前驱并插入新行；被快照/任务/提案引用者永不删除；最新行始终保留）；`revision_retention.ts` 清理超出保留窗口的旧无引用 autosave；保存载荷新增 `autosave: true`（9 处旧精确断言具名补字段）；规格保留策略条目（正文预算条目由 DR-048 补齐）。 | 复现：每次保存插入整篇副本 + FTS 全量重写、零保留策略 | 回归：`revision_retention`（未变写入 0、窗口折叠、引用保护、最新保护）、`revision_retention_prune`、`revision_store_pagination`、`document_revision_writes` 相关 | 验证：见 §10

### DR-048 [P2] 1 MiB 请求体与 413 体验

- [x] 已完成（2026-10-03）
- **问题**：`bodyLimit: 1_048_576` 对约 35 万汉字的章节直接 413，编辑界面无体积提示；与 DR-001 叠加成"永久保存失败"死局。
- **证据**：`http_server_policy.ts:36`；`error_envelope.ts:180-186`。
- **修复方向**：编辑器显示字数/字节进度与软上限；或提高上限并写进 capacity 规格；413 给出可读指引。
- **验证**：`pnpm --dir server exec vitest run tests/apps/api/`（新增 413 用例）。
- **交付记录**：2026-10-03 | `aa559112`（wave 14c） | 保留 1 MiB 为文档化软上限（不提高）：新增 `bodyBudget.ts`（UTF-8 字节精确测量、90% 进入 near、与服务端一致的字数口径）与 `StudioBodyBudget` 指示器（编辑器头显示"草稿 {used}/{limit} · {words}"，near/over 给出拆分指引）；`errors.codePayloadTooLarge`（zh/en）改为可读解法"拆分为更小的章节——草稿仍在编辑器里"（验证草稿保留路径已有断言）；规格 "Authoring structure capacity" 增补正文预算段落与"超限 413 且不丢草稿"场景 | 复现：基线无任何体积提示，413 只有一句"请求体过大" | 回归：`StudioBodyBudget`（4：尺寸格式化/阈值/超限文案）、`StudioEditorPane`（草稿预算渲染 + 保存失败保持草稿）、`localizeError`（413 文案） | 联动：`pnpm spec:validate` 通过 | 验证：见 §10

---

## 5. 决策与验证事项（非代码，DEC）

### DEC-01 用户验证从未发生（最高战略风险）

- [!] 阻塞（需 Owner 执行，2026-10-03）
- **事实**：`docs/research/interview-kit.md` 明文"本文档只准备材料，全部访谈由 Owner 本人执行"，成功判据"留存候选 ≥ 3"；仓库内没有任何已执行访谈记录；TTFW（首次价值时间）从未实测（历史记录多次 "recorded skip"）。公开仓库 6 star / 0 watcher。
- **决策建议**：把"10 场访谈 + 一次真实冷启动计时"作为 0.9.0 发布 gate；若留存候选 < 3，收敛 writer-facing 定位（见 DEC-02）。
- **完成定义**：访谈记录归档 + TTFW 计时有一份可复现记录 + 留存候选结论。
- **交付记录**：2026-10-03 | 决策落地（可由 agent 完成的部分）：发布 gate（10 场访谈 + 一次冷启动计时，留存候选 ≥ 3）已采纳并写入 `docs/roadmap.md`；访谈材料就绪（`docs/research/interview-kit.md`）。**阻塞原因**：访谈与 TTFW 计时必须由 Owner 对真实用户执行，仓库侧无等价替代动作。**所需决策/动作**：Owner 安排访谈与计时，完成后把记录与结论归档到 `docs/research/`。

### DEC-02 定位收敛

- [x] 已决策（2026-10-03）
- **事实**：README 第一屏对"普通作者"说话（"no development involved"），实际路径要求 Docker/终端/端口/环境变量；指南 FAQ 自述 "self-hosting authors"；访谈筛选把"不会装 Docker 的人"当作信号而非淘汰线。
- **决策建议**：二选一——A. 面向 homelab/tinkerer 的窄口径产品文档与能力取舍；B. 为普通作者补"零终端"路径（托管/一键安装包）。文案现状与任一方向都要一致。
- **交付记录**：2026-10-03 | 选择方向 A（self-hosting/homelab 窄口径）：README "For Writers" 重写——明确"跑在自己机器上、需要 Docker 与一个环境变量、无托管或零终端版本"，删除 "no development involved" 的宽口径暗示；中文 README 与各指南（self-hosting authors）本就一致，无需改动；零终端托管路径不再作为承诺（如需转向，等同于方向 B 的新决策）。

### DEC-03 v0.8.0 Release 状态

- [x] 已决策（2026-10-03）
- **事实**：tag `v0.8.0`、GHCR 多架构镜像（`0.8.0/0.8/latest` 匿名可拉）、raw compose URL 均已可用；GitHub Release 仍为 draft，外部发布动作处于冻结。
- **决策建议**：正式发布或同步修正 README/deploy 文案（文案部分已包含在 DR-039）。
- **交付记录**：2026-10-03 | 文案与事实一致（DR-039 落地）：英文 README 只陈述 "tag 已推送、镜像可拉"，中文 README 与 deploy README 如实标注 "GitHub Release 仍为 draft"；正式发布（把 GitHub Release 从 draft 转为 published）保留为 **Owner 外部动作**，agent 不代办（发布是对外且不可撤回的一步，需 Owner 显式执行）。

### DEC-04 LICENSE 署名与贡献协议

- [x] 已决策（2026-10-03）
- **事实**：MIT，`Copyright (c) 2024 Novel Engine`（署名是项目名而非自然人或实体；年份与仓库创建时间不一致）；无 CLA；CONTRIBUTING 的流程实际为 agent 集群设计，外部人类贡献成本高。
- **决策建议**：修正署名；决定是否需要 DCO/CLA；如实说明外部贡献门槛。
- **交付记录**：2026-10-03 | LICENSE 署名修正为 `Copyright (c) 2024-2026 Jackela`（仓库所有者身份；如需替换为法务姓名，Owner 可再改一行）；决定**不引入** CLA/DCO（MIT 已覆盖贡献授权）；CONTRIBUTING 新增 "External contributions" 一节，如实说明 agent 集群工作流与外部贡献门槛。

### DEC-05 0.9.0 方向：局部生成 + diff 优先

- [x] 已决策（2026-10-03）
- **事实**：评审一致结论——"整章/整本盲签"是当前最贵且体验最差的路径（无 diff、不可局部生成、整本循环有覆盖风险），而不可变修订 + snapshot 是唯一竞品无对应物的承重卖点，却在用户端不可感知（看不到历史正文/无 diff）。
- **决策建议**：把"局部生成（选区/段落）+ 接受前 diff + 一键撤销"作为 0.9.0 主题；整本生成默认改为逐章确认（与 DR-007 配套）。
- **交付记录**：2026-10-03 | 方向落档 `docs/roadmap.md`（0.9.0 主题：局部生成 + 接受前 diff + 一键撤销）；其中"接受前 diff"（DR-011/DR-042 已交付的预览与行级 diff）与"一次性撤销"（DR-010 已交付）已在本轮实现，"整本逐章确认"已随 DR-007 成为默认；"局部生成"为 0.9.0 的未开工主题（已登记）。

### DEC-06 provider 抽象瘦身评估

- [x] 已决策（2026-10-03）
- **事实**：约 30 个文件维护多 provider 抽象与厂商中立 payload，但真实并发上限 4、真实用户 1；同时 DashScope 协议已发生过两次真实断裂（历史记录）。
- **决策建议**：评估"保留两家 + 明确文档"或"收敛适配层厚度"，避免为不存在的市场维护抽象。
- **交付记录**：2026-10-03 | 决策：**保留** DashScope + OpenAI-compatible + trial `mock` 三家与现有适配层厚度，不扩张为插件生态、不为不存在的 provider 增加抽象；评估与理由写入 `docs/roadmap.md` 的 "Provider policy" 节（真实并发上限 4、DashScope 两次协议断裂的历史）。若未来出现第二个真实付费用户群，再按该节的标准重新评估。

---

## 6. 保护清单（已验证良好，勿在修复中重写/删除）

- **架构门禁真实生效**：`pnpm --dir server arch` 0 违规（273 模块/1252 依赖，2.5s）；四层边界、`ai` 隔离规则实际执行。
- **文件粒度**：全仓生产文件 ≤331 行（300 代码行预算 + 零豁免）；这是罕见的正面资产。
- **测试体系主干**：234 个 server 测试文件/1421 用例（184s）全过；断言可执行、无快照仪式、无 skip/only；增量维护问题只收敛"字节钉死文案"这一种模式（DR-038）。
- **备份/恢复主干**：WAL 在线备份一致性、restore 的三重拒绝路径（空文件/异种库/坏路径均不改动现库）、SIGKILL 后数据完好——实测通过；DR-031/036 只是策略与边角。
- **部署链**：GHCR 镜像真实可拉可跑、首启 secret bootstrap 生效、会话跨重启有效、healthcheck 工作。
- **i18n 键完整度**：EN/zh 359 键完全对齐；无障碍（APG tabs、aria-live、焦点管理）基础扎实。
- **错误处理**：无吞错模式、无 TODO/FIXME 标记债；日志不打印密码/密钥/cookie。

---

## 7. 附录：评审角色与交叉发现摘要

- 5 个角色：产品伪需求 / 用户可用性 / 架构工程 / 运维安全 / 竞争可持续；4 个功能域：编辑器与写作核心 / AI 生成审阅 / 搜索导入导出 / 平台与规格符合性。
- **交叉印证**（多角色独立命中同一事实）：中文搜索失效（用户+功能域+产品）、字数口径（用户+功能域+统计）、卷不可达（产品+功能域）、保存/取消的不可恢复（用户+功能域）、setup 抢占与限流绕过（运维实测）、"非线性产品投入"（架构 46% 提交非功能 + 市场 60% 非功能 + 产品 33/48 change 为加固）。
- **正交结论**（单一角色独有）：运维实测的事件循环冻结（架构域独立复测）、EPUB/DOCX 产物结构缺陷（功能域实测）、竞品矩阵与 bus factor=1/验证缺失（市场域）、429/201 等安全实测（运维域）。
- **最大交叉张力**：不可变修订 + snapshot 被市场域判为"唯一承重卖点"，但产品域判其"用户不可见"，功能域确认"连历史正文都读不了"——三者合起来指向同一修复主题：**让版本能力对用户可见/可用（DR-010/011/012）**，这比新增功能更有价值。

---

## 8. 执行计划（波次推进）

- 配套背景：评审发现记录见 [2026-10-01-devil-advocate-review-report.md](./2026-10-01-devil-advocate-review-report.md)。
- 原则：**一次一条、独立提交、先复现后修复**；同一波次内条目可并行，但写集（文件）不得重叠；跨波次存在依赖的条目按"准入条件"推进。
- 每完成一条：运行条目验证命令 + `pnpm --dir server gates`，并在第 10 节与条目内更新状态。

| 波次 | 条目 | 主题 | 准入条件 |
|---|---|---|---|
| Wave 1 | DR-001、DR-002 | 保存止血（熔断重试 + 离开守卫） | 无 |
| Wave 2 | DR-003 + DR-004 | 中文搜索分词 + 索引重建（**必须同批**） | Wave 1 完成（避免同区域冲突） |
| Wave 3 | DR-005 | 中文字数口径（跨域，改动面最大的一条） | 无（建议独占一批） |
| Wave 4 | DR-006、DR-007 | 流式保命 + 整本防覆盖 | 无 |
| Wave 5 | DR-008、DR-009 | 部署安全（setup token、XFF） | 无（建议与 DEC-03 联动） |
| Wave 6 | DR-010、DR-011、DR-012、DR-016 | 版本可见性三件套 + 编辑器 UX | DR-011 提供正文端点后再接 DR-012 |
| Wave 7 | DR-013、DR-014、DR-015 | 导出质量三件套 | 无 |
| Wave 8 | DR-017、DR-018 | 结构/项目入口 | DR-017 需 DEC-05 先拍板方向 |
| Wave 9 | DR-019、DR-020、DR-021 | 认证/会话/错误文案 | 无 |
| Wave 10 | DR-022 至 DR-028 | AI 设置、韧性、用量 | 无 |
| Wave 11 | DR-029、DR-030 | 搜索 UI 与性能 | Wave 2 完成 |
| Wave 12 | DR-031 至 DR-036 | 运维批次 | 无 |
| Wave 13 | DR-037 至 DR-039 | 导入、测试模式、文档对齐 | 无 |
| Wave 14 | DR-040 至 DR-048 | P2 收尾 | 各前置 |

---

## 9. 执行 Prompt（复制给清空上下文后的执行 AI）

**单条模式（推荐）**：

```text
你是在 Novel Engine 仓库执行「魔鬼代言人评审修复清单」的执行 AI。你的上下文可能已清空，按以下流程工作。

仓库：/Users/jackela/Documents/GitHub/Novel-Engine（main 分支）。
资料：
- 工作单：docs/audits/2026-10-01-devil-advocate-fix-backlog.md（每个条目含：问题/证据/修复方向/验收标准/验证命令）
- 评审背景（可选）：docs/audits/2026-10-01-devil-advocate-review-report.md
- 规则：AGENTS.md、docs/agents/change-evidence.md、docs/agents/ci-gates.md

任务：修复 <DR-XXX>（一次只做这一条，不要顺带扩大范围）。

流程：
1) 通读该条目；按条目中的证据锚点（file:line，以符号为准）确认问题仍存在。
2) 先复现：运行条目"验证"命令，或先写一个失败用例并记录复现输出。
3) 最小范围修复；遵守禁区（.env*、config/env/*、data/*.sqlite3、data/backups/*、AUDIT_REPORT_Linus.md、Makefile、justfile 不得修改）；迁移只用 pnpm --dir server db:generate --name <semantic-slug>；改动 HTTP 路由后必须运行 pnpm --dir server openapi:snapshot 更新基线。
4) 运行：条目验证命令；然后 pnpm --dir server gates；涉及前端再加 pnpm --dir frontend type-check、pnpm --dir frontend test:unit；涉及规格再加 pnpm spec:validate。
5) 在 backlog 该条目下追加交付记录：`- [x] <日期> <SHA> <命令与结果摘要>`；若阻塞改标 `- [!]` 并写明原因与所需决策。
6) 不要执行 git commit（除非用户明确要求）；不要为了通过检查而削弱测试断言。

输出：①问题复现证据 ②修改文件清单 ③实际运行的命令与结果（含失败/跳过） ④未完成项与阻塞。
```

**波次模式（批量推进时使用）**：

```text
按 docs/audits/2026-10-01-devil-advocate-fix-backlog.md 第 8 节执行 Wave <N>。
对波次内每条 DR 按"单条模式"流程逐条完成：先复现、最小修复、验证命令 + gates、更新交付记录。
同一波次内保持文件写集不重叠；若发现依赖未满足，记录阻塞并跳过该条，继续其余条目。
最后汇报：完成条目、失败/阻塞条目、每条的命令与结果。
```

---

## 10. 交付记录

（执行修复的 AI 在此追加：`Date | SHA | Item | Commands | Result`）

- 2026-10-01 | `607a092e` | 评审基线 | 9 个 subagent 评审 + 编排者复核 | 本文件生成
- 2026-10-01 | 工作区（基线 `607a092e`，未提交） | DR-001 | `pnpm --dir frontend test:unit`（131/709）、`type-check`、`biome check`、`format:check`、`pnpm --dir frontend build`、`pnpm --dir server gates` | 通过：退避重试 + 手动重试按钮 + 新回归
- 2026-10-01 | 工作区（基线 `607a092e`，未提交） | DR-002 | 同上 | 通过：beforeunload 守卫 + 切换/卸载救援写入；5 处旧"丢弃"用例按新语义重写
- 2026-10-02 | `eea6f3d4` | DR-003 + DR-004 | `pnpm --dir server exec vitest run tests/api/studio_search.test.ts tests/apps/cli/cli.test.ts`；`pnpm --dir server gates && pnpm --dir server type-check && pnpm --dir server lint && pnpm --dir server lint:types && pnpm --dir server arch && pnpm --dir server test`；frontend lint/lint:types/format:check/type-check/test:unit/build + react-doctor(100) + `pnpm spec:validate` | 通过：CJK 逐字分词（无迁移）+ 16 字符窗口 + `reindex`/doctor 对账；server 237 文件/1426 用例、frontend 131 文件/709 用例；升级提示：旧库需一次性 `reindex`
- 2026-10-02 | `8e59e9b6` | DR-005 | `pnpm --dir server exec vitest run tests/contexts/revision_word_count.test.ts tests/api/studio_writing_stats.test.ts tests/db/revision_word_count_reconciliation.test.ts tests/contexts/project_shell_store.test.ts`；`pnpm --dir server gates/type-check/lint/lint:types/arch/test`；frontend 全套 + react-doctor + `pnpm spec:validate` | 通过：统一字数口径（Han 逐字 + 拉丁按词）+ 启动对账自动修正旧口径存量；server 237 文件/1432 用例、frontend 131/709；spec 增"Stale counts recomputed"场景
- 2026-10-02 | `3771724e` | DR-006 + DR-007 | 定向：server `studio_proposals_stream*`、`provider_streaming_retry`、`provider_streaming_deadline`、`text_generation`；frontend copilot/whole-book 7 文件；全套：`server gates/type-check/lint/lint:types/arch/test`（239 文件/1436 用例）、frontend lint/lint:types/format/type-check/test:unit/build（134 文件/723 用例）+ react-doctor(100) + `pnpm spec:validate` | 通过；过程修复：重试引入的 4 个定时预算用例（显式单次尝试，断言不变）、3 处格式化、1 处 react-doctor 链式迭代告警；spec 与 2 个 e2e 规格同步新语义
- 2026-10-02 | `b10e02c6` | DR-008 + DR-009 | 定向 7 文件 78 用例；全套 `server gates/type-check/lint/lint:types/arch/test`（241 文件/1457 用例）、frontend lint/lint:types/format/type-check/test:unit/build（134 文件/723 用例）+ react-doctor(100) + `pnpm spec:validate` | 通过：首启 setup token + `owner reset`（DR-008）；XFF 最右未受信跳 + 范围拒绝 + trustProxy 推导（DR-009）；新错误码 SETUP_TOKEN_INVALID 锁步；README/deploy/spec 同步；已知后续：浏览器 setup token 输入并入 DR-019
- 2026-10-02 | `2baed8a9` | DR-010 + DR-011 + DR-012 + DR-016 | 定向：server `studio_revisions.test.ts`；frontend copilot/jobs/history/conflict/editor 相关 10 文件 52 用例；全套 `server gates/type-check/lint/lint:types/arch/test`（241 文件/1459 用例）、frontend lint/lint:types/format/type-check/test:unit/build（138 文件/745 用例）+ react-doctor(100) + `pnpm spec:validate` | 通过：修订正文端点 + 预览/diff + 恢复确认（DR-011）；冲突只读查看服务器版本（DR-012）；停止保留/一次性撤销/拒绝文本可回看（DR-010）；查找替换 + Ctrl/Cmd+S + 格式命令（DR-016，新增 `@codemirror/search`）；过程修复：文件行数拆分（字典 jobs 分块、proposalUndo 助手、测试 harness/拆分）、react-doctor/格式化/导出排序、撤销提议在瞬时 owner 切换被清空；人工浏览器验证待 Owner
- 2026-10-02 | `238a1cab` | DR-013 + DR-014 + DR-015 | 定向：`pnpm --dir server exec vitest run tests/contexts/export`（30 文件/137 用例）；全套 `server gates/type-check/lint/lint:types/arch/test`（244 文件/1472 用例）、frontend lint/lint:types/format/type-check/test:unit/build（138 文件/745 用例）+ react-doctor(100) + `pnpm spec:validate` | 通过：DOCX 东文字体/2 字符缩进/章前分页/TOC/去重标题（纯 docx API）；EPUB 语言推断 + dcterms:modified + 内置中文 CSS + 代码块/图片占位；Markdown `## {title}` + 导出范围文档对齐（全量归档标注未实现）；跳过：EPUBCheck（本地不可用，结构断言替代）、Word/WPS 人工打开（待 Owner）
- 2026-10-02 | `aa551e01` | DR-017 + DR-018 | 定向：frontend 卷 18 用例 + 项目删除 4 用例；server `studio_volumes`（7）+ 项目删除 3 文件（11）无回归；全套 `server gates/type-check/lint/lint:types/arch/test`（244 文件/1472 用例）、frontend lint/lint:types/format/type-check/test:unit/build（141 文件/767 用例）+ react-doctor(100) + `pnpm spec:validate` | 通过：卷新建/改名/删除确认/排序 + "移至卷"可达（DR-017）；项目库删除确认 + 刷新（DR-018）；过程修复：4 条 react-doctor（完成态 effect → 渲染期调节 + 事件侧 ref 标志）、1 处单遍循环重构、测试/E2E 正则消歧；人工浏览器验证待 Owner
- 2026-10-03 | `5795feb9` | DR-019 + DR-020 + DR-021 | 定向：EntryPage 系列 + `localizeError`/`toErrorMessage`/jobs 错误详情（12 文件/89 用例）、`auth_setup`（17）与 `error_codes_gate` 无回归；全套 `server gates/type-check/lint/lint:types/arch/test`（244 文件/1472 用例）、frontend lint/lint:types/format/type-check/test:unit/build（145 文件/805 用例）+ react-doctor(100) + `pnpm spec:validate` | 通过：setup 确认密码 + 首启 token 输入 + 无找回提示（DR-019）；401 过期提示 + 来源回跳（DR-020）；23 错误码双语映射 + 技术详情折叠（DR-021）；过程修复：EntryPage 测试拆分与共享 harness（行数门禁）；README/deploy 文案同步；人工浏览器验证待 Owner
- 2026-10-03 | `b1151803` | DR-022 + DR-023 | 定向：server `provider_catalog`/`studio_proposals_stream*`/语言与清理器 8 文件 96 用例、frontend settings/localizeError 35 用例；全套 `server gates/type-check/lint/lint:types/arch/test`（249 文件/1496 用例）、frontend（145 文件/808 用例）+ react-doctor(100) + `pnpm spec:validate` | 通过：provider 目录驱动设置（禁用/标注/model）+ `PROVIDER_NOT_CONFIGURED` 凭证错误（DR-022）；写作语言入 prompt/mock/清理器（DR-023）；过程修复：422 目录断言同步、3 个测试文件拆分（行数门禁）
- 2026-10-03 | `dcbb42dd` | DR-024 + DR-025 | 定向：review/provider 8 文件 53 用例 + 前端评审面板 3 用例；全套 `server gates/type-check/lint/lint:types/arch/test`（250 文件/1500 用例）、frontend（145 文件/809 用例）+ react-doctor(100) + `pnpm spec:validate` | 通过：review 随项目 provider（可见标注 + 失败按记录 provider 重试）（DR-024）；长文步骤（含 review/lore）180s 超时地板（DR-025）；过程修复：dashscope 测试拆分（行数门禁）
- 2026-10-03 | `301db695` | DR-026（主体） | 定向 5+3 文件（server 28、frontend 46 用例）；全套 `server gates/type-check/lint/lint:types/arch/test`（252 文件/1503 用例）、frontend（146 文件/812 用例）+ react-doctor(100) + `pnpm spec:validate` | 通过：SSE `: heartbeat`（15s）+ 客户端停摆看门狗（90s，可关）+ 中断诊断（帧数/字节 + 异常日志）；过程修复：oxlint mock 类型 + 格式化
- 2026-10-03 | `2c8393b0` | DR-026（补齐验收） | 定向 20 文件 144 用例 + API 诊断；全套 `server gates/type-check/lint/lint:types/arch/test`（255 文件/1517 用例）、frontend（148 文件/819 用例）+ react-doctor(100) + `pnpm spec:validate` | 通过：`rearm()` 逐帧重置绝对预算（健康长流不再被斩；超静默仍中止）；DashScope/OpenAI 兼容识别 200 SSE 内错误帧 → `PROVIDER_FAILED`(message+code)；旧行为钉子具名替换
- 2026-10-03 | `04ab5d74` | DR-027 | 定向：生成幂等（`proposal_generation_idempotency*` 9 用例 + retry 边界 + proposals/stream 回归）+ 前端幂等 3 文件 10 用例；全套同上一行口径（server 255/1517、frontend 148/819、react-doctor 100、spec 通过）| 通过：生成端点可选 `Idempotency-Key` + 持久 claim（迁移 0023，部分唯一索引）+ 流式/同步重放 + 竞态回归；客户端按逻辑生成铸造/保留/清除键；重做移除进程内 guard（恢复 retry 持久重放路径）
- 2026-10-03 | `2630cc7f` | DR-028 | 定向：`studio_usage_provenance`/`job_store_transactions`/`safe_usage_persistence` + 前端用量面板/契约 5 文件 34 用例；全套 `server gates/type-check/lint/lint:types/arch/test`（256 文件/1520 用例）、frontend lint/lint:types/format/type-check/test:unit/build（148 文件/819 用例）+ react-doctor(100) + `pnpm spec:validate` | 通过：token 来源标记（provider/estimated/unreported）+ 失败尝试可见 + 删 estimated_cost 死列（迁移 0024/0025）+ 面板披露；过程修复：openapi 基线漂移重生成、13 个旧契约测试具名更新、写作统计解析器与 4 处前端 fixture 补字段、`types/studio.ts` 拆分（行数门禁）；范围说明：预算/告警未含在验收，留候选
- 2026-10-03 | `636fc7b5` | DR-029 + DR-030 | 定向：server 搜索 7 文件 68 用例 + 前端搜索 4 文件 30 用例；全套 `server gates/type-check/lint/lint:types/arch/test`（258 文件/1525 用例）、frontend lint/lint:types/format/type-check/test:unit/build（149 文件/826 用例）+ react-doctor(100) + `pnpm spec:validate` | 通过：token 上限 8→3 + `q` maxLength（DR-030 事件循环冻结）；total/next_offset 分页 + match_term 定位 + 零结果提示/计数/"更多"（DR-029）；过程修复：payload guard fixture、`searchContract`/`studioSearchModel` 拆分（行数门禁）、navigator 布尔 props 归并为 `searchState`（react-doctor）；"排序选项/高频词短路"不在验收，留候选
- 2026-10-03 | `90e5f271` | DR-031 + DR-036 | 定向：`backup_policy`/`backup_policy_cli`/`startup_pipeline`/`restore_cli`/`tests/apps/cli` 13 文件 71 用例；全套 `server gates/type-check/lint/lint:types/arch/test`（260 文件/1533 用例）、frontend test:unit/build（149 文件/826 用例）+ react-doctor(100) + `pnpm spec:validate` | 通过：仅待迁移时备份 + 保留 3 份 + 空间检查 + quick_check 自检（DR-031）；restore 校验清理 sidecar + 明文提示（DR-036）；过程修复：两处旧断言具名更新（serve 重启备份、startup 计数），正向覆盖移入新用例
- 2026-10-03 | `82aaa64f` | DR-032 | 定向：`doctor_readonly_cli`（6）+`migrate_cli`（3）+`tests/apps/cli`（13 文件/64 用例）+`tests/infrastructure`+`tests/db`；全套 `server gates/type-check/lint/lint:types/arch/test`（262 文件/1542 用例）、frontend test:unit/build（149 文件/826 用例）+ react-doctor(100) + `pnpm spec:validate` | 通过：doctor 只读零写入（含运行中只读）+ `migrate` 独立写入路径 + `error` 字段承载锁/权威原因；CLI 重放（构建产物）实证；三处旧断言具名更新
- 2026-10-03 | `a06df731` | DR-033 + DR-034 + DR-035 | 定向：config/version/health/cors/setup-proxy/compose-gate 7 文件 57 用例 + 回归 sanity 11 文件 100 用例；全套 `server gates/type-check/lint/lint:types/arch/test`（264 文件/1554 用例）、frontend type-check/test:unit/build（149 文件/826 用例）+ react-doctor(100) + `pnpm spec:validate`；`docker compose config` 冒烟 | 通过：占位密钥生产拒绝（DR-033）、compose 去占位 + 可信代理透传 + 反代 checklist（DR-034）、生产暴露面收口（DR-035）；OpenAPI 零漂移；过程修复：`server_config` 测试拆分（行数门禁）、vitest NODE_ENV 固定
- 2026-10-03 | `d61b9b37` | DR-037 + DR-038 + DR-039 | 定向：import 14 用例 + 字典 4 用例；全套 `server gates/type-check/lint/lint:types/arch/test`（264 文件/1557 用例）、frontend lint/lint:types/format/type-check/test:unit/build（149 文件/826 用例）+ react-doctor(100) + `pnpm spec:validate` | 通过：导入根无关 hash + 标题保留 + CLI-only 文档（DR-037）；字典契约收敛（parity 双向/非空/锚点白名单）与回归确认（DR-038，413 随 DR-048）；文档/spec 对齐（DR-039）；过程修复：`legacy_workspace_reader` 两处旧契约具名更新、字典测试格式化
- 2026-10-03 | `206c8dbe` | DR-040 + DR-041 + DR-045 + DR-047 | 定向：auth/metrics/stats/retention 9 文件 64 用例 + 前端 stats 2 文件 11 用例；全套 `server gates/type-check/lint/lint:types/arch/test`（268 文件/1579 用例）、frontend lint/lint:types/format/type-check/test:unit/build（149 文件/826 用例）+ react-doctor(100) + `pnpm spec:validate`；`docker compose config` 双文件 | 通过：dev secret 持久化（DR-040）、容器加固 + `/metrics` + `LOG_LEVEL`（DR-041）、统计本地时区 + 负数解释（DR-045）、revision 去重/折叠/保留 + `autosave` 标志（DR-047）；过程修复：`config_startup` 旧契约具名更新、9 处 saveDocument 载荷断言补字段、导入排序、stats fixture 补 tz 字段
- 2026-10-03 | `c3a9674c` | DR-042 | 定向：审阅面板 5 用例 + 列表/历史 hook + 字典/本地化用例；frontend lint/lint:types/format/type-check 全绿、react-doctor(100) | 通过：审阅行可点开详情 + 选中态、快照短名（审阅/导出）、快照冲突可读解法；全套复验随 wave 14 收尾提交执行
- 2026-10-03 | `aa559112` | DR-043 + DR-048 | 定向：beat 候选 43 用例 + 前端 beat/budget/editor 25 用例；全套 `server gates/type-check/lint/lint:types/arch/test`（269 文件/1581 用例）、frontend lint/lint:types/format/type-check/test:unit/build + react-doctor(100) + `pnpm spec:validate` | 通过：beat 候选下拉 + 权威 outline 披露（DR-043）；草稿字节预算指示 + 413 拆分指引 + 规格正文预算（DR-048）；过程修复：契约拆出 `beatContract.ts`、`studio_beats` 拆分为两文件 + 共享 helper、StudioComponents fixture 抽出、`fireEvent.change` 的 no-floating-promises
- 2026-10-03 | `52011933` | DR-046 + DR-044 | 定向：23 文件 155 用例 + 主题/页面契约 4 文件 25 用例；全套 `server gates/type-check/lint/lint:types/arch/test`（269 文件/1581 用例）、frontend lint/lint:types/format/type-check/test:unit（154 文件/851 用例）/build + react-doctor(100) + `pnpm spec:validate` | 通过：Intl 本地化格式化 + 离线横幅 + 外壳/错误文案收口（DR-046）；死代码清理（同步客户端方法/3 个零引用类型；服务端路由与 test-only 导出保留）（DR-044）；过程修复：3 处 import 排序、Intl formatter 提升到模块作用域（js-hoist-intl）——**至此全部 48 条 DR 交付完毕**
