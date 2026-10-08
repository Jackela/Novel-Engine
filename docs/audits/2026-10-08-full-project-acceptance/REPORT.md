# Novel-Engine 全面调查、ACP 接入与项目验收

**现有版本验收、历史整改复核和 0.9.0 发布准入均为 `fail`。** 本轮实现了通用 ACP 代理、Grok Provider、工作室工具观察与权限答复，以及 Review 正文和捕获版本修复；草稿补存、备份恢复、旧卷升级等既有问题按授权复现和报告，没有扩大为整仓整改。测试通过的能力与未完成的发布门槛分别记录。

调查实施时间为 2026-10-08 至 2026-10-09（Asia/Shanghai）。本报告是 Markdown 主稿；未进行发布、部署到生产或人工验收，也没有升级产品版本。

## 1. 三类结论与代码身份

| 对象 | 状态 | 判断依据 | 关闭条件 |
|---|---|---|---|
| 现有版本：固定基线及当前候选 | **fail** | 已复现草稿静默丢失、最旧备份恢复失败、旧卷升级失败；候选修复了本轮指定能力，但既有阻断仍在 | 分项修复 P1 问题，重放对应失败和恢复场景，并补齐下列平台／实际模型缺项 |
| 历史 48 DR、6 DEC 整改 | **fail** | 所有原始条目已入矩阵；账本有 47 个 DR 勾选和 1 个未勾选，与“48 项完成”汇总冲突；部分原验收未重新执行，且 DR002、DR031 有当前失败证据 | 按每条原验收补证，解决规格／已采纳整改冲突，修正汇总，保持人工决定独立 |
| 0.9.0 发布准入 | **fail** | 当前仍为未发布 0.8.0 候选；部分选区改写、默认 Proposal diff 缺项，作者访谈与留存验证按要求跳过；候选 CI、真实 Grok 权限请求及稳定性未通过全部验收 | 完成产品承诺、数据安全整改、实际平台验证、精确候选 CI 和 Owner 发布授权；不能以本次审计结束代替准入 |

| 权威对象 | 本轮实际状态 |
|---|---|
| 固定调查基线 | `066d923d8bb92a47c7d6a12d8352b2aa471cbd4b`，原 checkout 保持该状态 |
| 本轮产品代码提交 | `da025b7de90a6b2106892d5d8490bbdfd8628a20`，分支 `codex/acp-full-acceptance`，146 文件（首批0799ddf后追加连接取消、41项回归及UI忙碌状态修复）；后续提交只记录审计材料 |
| 产品版本来源 | `server/package.json`，仍为 **0.8.0**；新增能力是候选，不是已发布 0.9.0 |
| 远端 main | `490e19458e019641fb6394d33db1fe54ef032d28`；其 CI 成功仅属于这个 SHA |
| v0.8.0 Git 标签 | `520be9a8300957c3c5400bc3561b64d86bdc2333`；GitHub Release 为 Draft，未发布；最新已发布 Release 为 v0.7.0 |
| 现有 ghcr 0.8.0 镜像 | index digest `sha256:15df0fa2b7aca06b30fd412c5dce46a353f57d1de905a7aac1db29440f742c93`；实测旧 revision、UID 0、23 迁移，无当前首启令牌及 ACP |
| 本轮最终本机镜像 | `novel-engine-acp-audit:final`；实际 image ID `sha256:c3286465ec20b6c26d04f52c4b360dbda50b53a6d5539c8991526ea26201843e`；revision label 与产品代码提交一致，ARM64，本机没有推送镜像 |

[远端与检查快照](remote-state.json)记录查询时间、标签、Release 与 main 检查链接。[运维证据](operations-evidence.json)分别保留旧发布镜像、早期本机镜像与最终镜像的检查，三者不可互换。

原目录的 `.commandcode/`、`.zcode/` 保留原状。真实数据库、备份、秘密配置及项目禁区没有被读取或修改。实现使用独立 managed worktree，运行使用临时合成数据、资料和 Docker 卷。

## 2. 调查覆盖及证据解释

主代理固定基线、整合完整差异并复核关键发现；子代理最多三名并行，分轮覆盖规格／历史、写作／持久化、AI／任务、安全、前端、运维和产品承诺。主要分析与实现使用 gpt-6.1-sol high，独立安全复核使用 gpt-6-astra high；实际调用与任务写集分开，未让两个代理同时修改同一产品区域。

| 覆盖对象 | 完整登记数量 | 验证边界 |
|---|---:|---|
| canonical Requirement | 105 | 逐条保留原正文、来源行、断言和证据，不因整套测试通过而自动通过每条 |
| canonical Scenario | 513 | 所有行已登记；未逐条获得对应 THEN 的运行证据者明确 `not run` |
| 基线活动 EOF 增量 | 1 Requirement / 7 Scenario | 保留为当前候选增量；Issue #674 的关闭与规格归档未执行 |
| 新 ACP 活动增量 | 8 Requirement 块 / 32 Scenario | 7 个新增块、1 个修改 Review 块；与 canonical 分开，尚未归档 |
| 历史整改与决定 | 48 DR / 6 DEC | 原始验收、历史交付自述、当前证据分别保存 |
| CodeQL 开放告警 | 14 | 每项按所在 SHA、原调用路径、反证与残余风险分类；未把扫描告警总数当成真实漏洞总数 |

完整内容见 [规格覆盖矩阵](spec-coverage.json)、[历史整改矩阵](historical-remediation.json)、[安全及告警复核](security-evidence.json)。矩阵的库存完整性已检查；canonical 为 24 pass、9 fail、480 not run，ACP 增量为 7 pass、25 not run，EOF 增量为 7 not run。48 DR 的当前原验收为 2 fail、46 not run；6 DEC 为 1 blocked、5 not run。“全部条目已登记”不等于“513 个场景已重新验收”。未执行项有原断言对应的关闭条件。用户要求跳过的作者访谈和留存验证仍为 `not run`。

所有验收行采用 `pass / fail / not run / blocked / not applicable`。`partial` 只作为证据范围说明，不能成为第五种结论之外的通过状态。每项检查绑定源提交、环境、操作、日志及原因，见 [最终证据登记](evidence-registry.json)。历史或中间实现日志保留其原范围，不被回填为最终代码的完整验证。

## 3. 已实现的 ACP 与 Review 行为

### 通用代理与 CLI

沿用原 CLI，新增 `acp serve` 与 `acp connect`。代理遵循 [ACP 传输规范](https://agentclientprotocol.com/protocol/v1/transports)所允许的自定义 WebSocket 传输，使用独立 Bearer 令牌，在升级连接前认证；默认监听本机，拒绝 URL token、Origin 和未授权启动。首个 `initialize` 的 `_meta["novel-engine/acp-proxy"]` 传入后端选择的 command、args、cwd；代理消费该扩展后转发 ACP，直接启动进程，不解析 shell 字符串。

每个连接拥有独立进程，限制消息及积压缓冲，支持分帧、请求标识、权限、会话、取消与 stdio shim。断线、超时、异常退出清理所属进程。令牌不进入启动参数 URL 或子进程环境。网关是 Owner 受信客户端工具；没有把它包装成面向不受信用户的隔离执行平台。

### Provider、工具与权限

新增 `acp` Provider，命令、参数、资料根目录和可选模型由后端配置，工作室选择 Provider。复用四个既有结构化步骤：续写、改写、Review、Lore 提取。只把模型文本作为业务输出；工具和思考消息不混入正式正文。Grok 的过程说明与其后单个合法 JSON 分开处理，继续使用结构和业务校验。任务语言明确传到 ACP；模型及 token 依据协议证据，不伪造缺失值。

四类操作及重试均使用请求范围的观察通道和权限答复，界面显示动作、目标及实际选项。事件读取要求 Owner 身份及对应项目，权限答复另需 CSRF；过期、异项目、异 operation、重复或错误 option 被拒绝。工作室先连接事件流再提交任务，避免早期确认不可见。取消和离开页面关闭本轮交互，权限控件不会留到另一项目。

明确配置的资料／工作副本允许工具读写。客户端文件访问限制为该根目录，拒绝路径逃逸、父目录符号链接及硬链接等边界，并记录其实际写入副作用。Grok 原生工具另受 Owner 的专用 sandbox profile 管理；内建 profile 不能直接作为本接入配置，未找到自定义 profile 时启动拒绝。实测 profile 拒绝读取本轮数据库目录 canary，仍可写本轮资料副本。SQLite、Revision、Snapshot 和登记的导出原件仍由原业务管理；生成不直接修改正式正文。

Job 保存已完成、失败和未知工具操作；第 101 个新工具超过证据上限时失败并保留未知状态。客户端写入即使没有模型工具通知也独立记录。Agent 请求提交后没有自动重放；失败后的人工重试显示外部副作用提醒。取消不宣称撤销已完成文件写入。

### Review

Review 输入包括捕获时阅读顺序中的章标题、全文、document ID 与 Revision ID；同标题、同字数、不同正文产生不同输入。共享输入预算和 ACP 消息预算明确拒绝超限，不截断后继续审阅。空章和薄章规则保留。

捕获版本以应用实例共享的临时 refcount pin 保留到结果原子落库，处理等待中的连续 autosave、保留期剪枝、并行评审、失败及回滚；不提前创建 Snapshot，也不阻止作者编辑。真实 Grok 等待期间两次 autosave 后，当前正文为新版本，评审 Snapshot 仍引用原版本。故意删除源章节的拒绝语义仍保留。

术语见根 `CONTEXT.md`；架构取舍见 [ADR-0011](../../adr/0011-owner-acp-proxy.md)。[ACP 使用说明](../../acp.md)包括本机及容器接入、profile、令牌、权限、用量、CLI 副本与隐私边界。README、双语界面、OpenAPI、API 类型及锁文件已同步。

另补测到连接尚未升级时取消的未处理 WebSocket 异常，已修复预取消守卫及该精确预期关闭错误；普通网络错误仍可见。原失败、真实 TCP 等待 upgrade 的 cancel／timeout 及独立 34 项检查保留。连接补丁提交为 `7c155bf4`；最后 `da025b7d` 仅将 ACP 重试的忙碌状态在 finally 无条件清理，并验证错误后按钮恢复。服务端源码／测试与7c155完全一致，前端以da025重新验证。

## 4. 实际验证结果

环境为 macOS 27.0 ARM64、Node 24.19.0、pnpm 11.6.0、Docker/Colima ARM64；本机 HTTP 和隔离卷，不涉及生产部署。Grok CLI 实测为 1.0.46，实际模型按成功 session 记录为 grok-4.7；不能把最早探测的 grok-4.6 或环境默认模型当作后续任务事实。

| 验证 | 状态 | 实际范围及证据 |
|---|---|---|
| 网关／shim／认证／分帧／生命周期 | pass | 假 ACP 子进程与真实 WS；31 个测试，最终安全定向复核也覆盖网关边界 |
| ACP 四类 API、权限、取消、错误、客户端写入、消息预算 | pass | 固定候选独立定向检查 17 文件／71 测试；新增权限与 side-effect 回归进入最终全量测试 |
| Review capture／autosave／retry／落库／释放／回滚 | pass | 14 文件／58 测试；独立原失败对照转绿、删除源 API 回归、真实 Grok 等待期间两次保存 |
| 类型、lint、架构、SSOT、OpenAPI、OpenSpec、API 类型漂移 | pass | [最终完整日志](evidence/contracts-final-candidate.log)，规格 3 项均有效，无漂移 |
| 前端完整覆盖率与构建 | pass | 163 文件／890 测试；statements 91.13%、branches 84.25%、functions 90.47%、lines 93.99%，阈值未降低 |
| 服务端完整覆盖率 | pass | 7c155：303文件／1,807测试；statements92.11%、branches83.86%、functions96.26%、lines93.76%，全部原门槛满足；da025的服务端源码与测试逐字一致 |
| React 静态诊断 | pass | 最终 React Doctor score 100、0 diagnostics |
| Chromium 最终完整写作旅程 | pass | 35／35；包括保存、冲突、接受、撤销、历史、Review、Export、错误恢复及统计 |
| ACP 最终浏览器权限与副作用旅程 | pass | 2／2；四步骤允许、拒绝／取消、导航清理，正式正文仅在接受后变化；取消保留已有操作证据 |
| Google Chrome 实际安装版 | pass | 最终da025实际安装版35／35，另有ACP四步骤权限／取消2／2 |
| WebKit 引擎 | pass | 35／35，中间候选；不是原生 Safari 的替代证据 |
| Firefox | blocked | runner 启动反复遇到 macOS sandbox extension／SWGL 错误；未关闭浏览器安全来制造通过 |
| 原生 Safari | blocked | WebDriver 返回 Remote Automation 未启用；未改用户设置 |
| 中文／长稿／键盘／主题／响应式 | pass | 限定自动化范围： 48,426 字符保存／重开核对、1440／768／375 无横向溢出、标签键盘、浅深及系统主题；程序化 composition 不代表真实 IME |
| 真实 Grok 四类任务 | fail | 0799固定候选并发Review保持原Snapshot通过；其后正确Review及四类独立回放均180秒超时。早期12次en/zh任务成功属于中间源，不能替代最终稳定性；最终后续仅另有连接取消与UI忙碌状态修复，真实云端完整回归未完成。 |
| 真实 Grok 原生允许／拒绝确认 | not run | 安装版本不支持 `--permission-mode ask`，按既有权限运行未产生 request_permission；允许／拒绝 UI/API 仅有假进程证据 |
| 生产依赖审计 | pass | 0 告警；全开发依赖检查另有 braces3.0.3 high 告警，见问题清单 |
| 工具已写入但后台硬终止的中间窗口 | not run | 实际SIGKILL只验证已保存正文／会话／DB；工具写入至结果落库之间的硬终止尚未重放，关闭条件见证据登记 |
| 最终镜像及实际 Compose | pass | 最终 9 项隔离检查：fresh setup、UID/26 migrations、完整性、restart/SIGKILL、备份恢复、三格式、容器到宿主 fake ACP；DOCX实读另保留0799实测范围 |
| DOCX 内容及 LibreOffice 实读 | pass | 0799导出、校验和、正文及中文字体，headless读入再输出HTML检查正文；其后export源码未变，da025三格式结构另重放 |
| WPS 正文视觉检查 | blocked | 文件能打开且未见修复提示，但窗口操作限制未取得完整正文视觉依据 |
| EPUB ZIP／OPF／XHTML | pass | 正文、顺序、语言及结构检查；独立 EPUB 阅读器、EPUBCheck 未完成，后者缺 JRE |
| 候选 required CI／CodeQL | not run | 本地提交未 push，main 的绿色记录不能替代；required contexts 为 Analyze、validate、container |
| 作者访谈／留存／真实输入法／屏幕阅读器／视觉接受 | not run | 访谈及留存按用户要求跳过；其余缺少实际人工验证，均保持门槛未完成 |

本轮共37项记录（26 fail、1 not run、10 pass），包含运行缺陷、规范／文档冲突、扫描告警和已修复项。

早期失败不被删除：默认前端全量曾有 1 个 5 秒超时，原断言限定 2 workers 重跑通过；服务端一次并发全量出现 4 个超时，原失败 3 文件／7 测试隔离复跑全部通过。最终完整重放见对应行。此后增加41项协议／超时／文件边界测试，不降低门槛。初期 Docker 类型编译失败、实现阶段 RED 测试及 OpenAPI 并发再生成导致的失败也按各自代码状态保存，没有降低断言来掩盖。

React诊断曾有1条warning，原“已通过”登记经核对纠正；保留91分／1诊断原JSON，最终da025组件测试、全量前端和诊断100分／0条全部通过。

真实模型对照 Review 两次超过 180 秒执行时限，failed Job 保留 `outcome_unknown=true`，无自动重放；它们属于实际失败验证，不能由早先成功样本覆盖。正确样本和实际模型质量判断须以最终回放记录逐项检查，不要求模型对正常但重复的文字必然给出空 findings。

## 5. 本轮识别的全部问题及修复项

清单包含运行缺陷、文档／规格冲突、扫描告警及本轮修复，不能把总行数直接称为漏洞数量。以下按原授权保留未修复项；每项的触发、影响、源码、日志、严重度、原 Issue 关联及关闭条件详见 [findings.json](findings.json)。Issue 关联注明背景或已关闭历史记录，不表示本轮已开单、重新打开或关闭 Issue。

| ID／级别 | 分类／状态 | 问题或修复 | 源码位置 | 触发与关闭条件 |
|---|---|---|---|---|
| FE-01 / P1 | confirmed_bug / **fail** | 应用内导航补存失败导致未保存草稿静默丢失 | [useDocumentDraftRescue.ts:66](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/frontend/src/features/studio/hooks/useDocumentDraftRescue.ts:66) | 1.5秒自动保存防抖内导航，唯一补存PUT返回500或503；导航失败保留可恢复Draft并明确提示；重放500/503并核对正文/Revision与关闭保护。 |
| OPS-UPGRADE-VOLUME-OWNERSHIP / P1 | confirmed_bug / **fail** | 旧发布数据卷无法直接升级到当前非root镜像 | [Dockerfile:50](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/Dockerfile:50)、[entrypoint.sh:18](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/docker/entrypoint.sh:18) | 0.8发布镜像创建的root-owned0600 .secret交给USER node候选；设计受支持的旧卷权限迁移或恢复流程，在旧镜像创建的卷副本上完成升级与回退。 |
| OPS-RESTORE-RETENTION / P1 | confirmed_bug / **fail** | 恢复最旧备份时安全备份剪枝删除恢复输入 | [restore.ts:52](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/server/src/shared/infrastructure/db/restore.ts:52)、[backup.ts](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/server/src/shared/infrastructure/db/backup.ts) | 管理目录已有3个备份，restore以最旧文件为输入；保护已验证的恢复输入跨越剪枝和复制，重放最旧输入/损坏输入/失败恢复。 |
| OPS-PUBLISHED-IMAGE-DRIFT / P1 | release_artifact_drift / **fail** | 发布镜像与当前加固和首启说明不一致 | [compose.yaml:9](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/deploy/compose.yaml:9)、[README.md:114](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/README.md:114)、[README.md:193](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/README.md:193) | 按当前文档拉取ghcr.io/jackela/novel-engine:0.8.0；由Owner批准发布新tag/digest并绑定验收源码；验证文档、首启、升级和回退，不用旧镜像冒充当前源码。 |
| BACKUP-PERMISSION / P2 | confirmed_bug / **fail** | 备份吞掉访问错误并返回无数据库结果 | [backup.ts:45](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/server/src/shared/infrastructure/db/backup.ts:45) | 存在DB但其父目录不可访问(EACCES)；仅ENOENT表示不存在；权限/IO错误保留并退出失败，复核启动备份与CLI语义。 |
| CSRF-UNICODE / P2 | confirmed_bug / **fail** | CSRF按字符长度比较引发UTF8长度异常 | [auth_guard.ts:24](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/server/src/shared/interface/http/auth_guard.ts:24) | 认证会话仍有效，CSRF header含é，JS字符长度等于cookie但编码字节不同；编码后先比较字节长度再timingSafeEqual；无效请求403、后续会话仍可用。 |
| FE-02 / P2 | confirmed_bug / **fail** | 接受成功但刷新失败后旧稿仍显示已保存 | [acceptProposalAndRefresh.ts:51](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/frontend/src/features/studio/hooks/acceptProposalAndRefresh.ts:51)、[useProposalAcceptance.ts:135](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/frontend/src/features/studio/hooks/useProposalAcceptance.ts:135) | accept200之后document GET503；明确展示已接受但刷新失败，保持可重新同步状态，不重复接受；验证Undo与网络恢复。 |
| FE-03 / P2 | confirmed_bug / **fail** | 导出按钮未应用控件样式 | [StudioExportPanel.tsx:78](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/frontend/src/features/studio/components/StudioExportPanel.tsx:78)、[DESIGN.md:134](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/DESIGN.md:134) | 375px屏幕打开Export；按已有tokens修复控件样式，验证44px、键盘、窄屏与三格式。 |
| DOC-UPGRADE-PROJECT / P2 | document_conflict / **fail** | ZIP升级改变Compose项目名可能挂载新空卷 | [upgrading.md:19](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/openwiki/guides/upgrading.md:19)、[README.md:221](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/deploy/README.md:221) | 解压新版本到另一文件夹后按文档启动；固定项目名/卷名并回放跨目录升级，保留旧卷与回退说明。 |
| DEV-DEPENDENCY-AUDIT / P2 | scanner_alert / **fail** | braces3.0.3开发工具链高风险告警 | [pnpm-lock.yaml](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/pnpm-lock.yaml) | 全依赖审计，包括OpenSpec和React Doctor；处理或明确批准开发依赖风险，并在候选锁文件重跑全审计。 |
| REVIEW-USAGE / P2 | confirmed_behavior_gap / **fail** | Review不进入Provider用量账本 | [attempt_usage.ts:13](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/server/src/contexts/studio/application/attempt_usage.ts:13)、[job_retry_executor.ts:211](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/server/src/contexts/studio/application/job_retry_executor.ts:211) | 运行真实中英四类任务共8个Job；统一全AI任务的用量范围或明确界面排除Review，保留provider/estimated/unreported来源并验证重试。 |
| HTTP-REVIEW-LANGUAGE / P2 | confirmed_static_gap / **not run** | 既有HTTP Provider没有使用Review任务language标记 | [provider_json.ts:19](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/server/src/contexts/ai/infrastructure/providers/provider_json.ts:19) | Review/lore系统提示为英文而task.language=zh；HTTP请求构造不携带language；在真实HTTP供应商合成稿上复现并修订语言通道；不能用mock中文输出替代供应商验证。 |
| DOC-PRIVACY / P2 | document_conflict / **fail** | 本地存储表述不足以说明云模型与CLI会话副本 | [README.zh-CN.md:3](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/README.zh-CN.md:3)、[faq.md](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/openwiki/guides/faq.md)、[faq.md](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/openwiki/guides/zh/faq.md) | 选择真实云模型或本机Grok；按Provider、CLI保留和配置说明内容去向与费用，核对双语FAQ/README。 |
| GROK-TIMEOUT / P1 | integration_validation_failure / **fail** | 最终真实Grok对照Review及后续任务超过执行时限 | [AcpTurnBudget.ts:38](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/server/src/contexts/ai/infrastructure/providers/AcpTurnBudget.ts:38)、[AcpTextProvider.ts](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/server/src/contexts/ai/infrastructure/providers/AcpTextProvider.ts) | 最终候选正确对照Review连续两次及后续真实Agent任务无及时进展，超过180秒执行预算；保留原失败，获取实际CLI/传输/外部服务诊断后，在同权限配置和合成对照上稳定完成四类任务；核查无自动重放、失败进程清理及未知操作结果。 |
| SPEC-001 / P2 | specification_conflict / **fail** | 修订版本不可变与合并、清理策略冲突 | [document_revision_writes.ts](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/server/src/contexts/studio/infrastructure/db/document_revision_writes.ts)、[revision_retention.ts](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/server/src/contexts/studio/infrastructure/db/revision_retention.ts) | R008要求前驱版本A仍可读；R009允许30秒内合并未被引用的作者版本、清理旧版本并改写父引用，需区分内容不可修改与保留规则；明确规范意图并以OpenSpec校正对应正文/场景；再验证具体断言。 |
| SPEC-002 / P2 | specification_conflict / **fail** | 禁止自动删除备份与保留三份策略冲突 | [backup.ts](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/server/src/shared/infrastructure/db/backup.ts) | R013禁止自动删除备份；DR031及当前代码自动剪枝，只保留三份管理目录备份；明确规范意图并以OpenSpec校正对应正文/场景；再验证具体断言。 |
| SPEC-003 / P2 | specification_conflict / **fail** | Markdown章节标题规范与当前导出不一致 | [bounded_export_rendering.ts](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/server/src/contexts/studio/infrastructure/bounded_export_rendering.ts) | R028要求项目标题后直接输出正文；DR015的当前导出增加二级章标题，并移除正文中的重复标题；明确规范意图并以OpenSpec校正对应正文/场景；再验证具体断言。 |
| SPEC-004 / P2 | specification_conflict / **fail** | 导入章节命名规范与保留原题规则冲突 | [fs_legacy_workspace_reader.ts](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/server/src/contexts/studio/infrastructure/fs_legacy_workspace_reader.ts) | R032要求Chapter N标题；DR037的导入逻辑保留正文或文件名中的原章节标题；明确规范意图并以OpenSpec校正对应正文/场景；再验证具体断言。 |
| SPEC-005 / P2 | specification_conflict / **fail** | 预估费用及用量结构规范与整改结果冲突 | [job_usage_tables.ts](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/server/src/contexts/studio/infrastructure/db/job_usage_tables.ts)、[attempt_usage.ts](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/server/src/contexts/studio/application/attempt_usage.ts) | R033要求estimated cost，R065要求成功结果结构不变；DR028已移除estimated_cost并增加来源、失败和预估计数；明确规范意图并以OpenSpec校正对应正文/场景；再验证具体断言。 |
| SPEC-006 / P2 | specification_conflict / **fail** | 开发环境重启登出与持久会话规则冲突 | [session_secret.ts](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/server/src/shared/infrastructure/config/session_secret.ts) | R041要求非生产重启后登出；DR040通过持久化.secret继续保留会话；明确规范意图并以OpenSpec校正对应正文/场景；再验证具体断言。 |
| SPEC-007 / P2 | specification_conflict / **fail** | 失败流禁止留存与部分正文、用量证据冲突 | [proposal_streaming.ts](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/server/src/contexts/studio/application/proposal_streaming.ts)、[proposal_landing.ts](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/server/src/contexts/studio/application/proposal_landing.ts) | R067和R070禁止失败流保留部分正文或用量；DR006、DR028及EOF增量保留partial_markdown和failed/unreported用量；明确规范意图并以OpenSpec校正对应正文/场景；再验证具体断言。 |
| SPEC-008 / P2 | specification_conflict / **fail** | 任务列表及详情的事件顺序表述冲突 | [job.ts](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/server/src/contexts/studio/application/payload_schemas/job.ts)、[job_history_service.ts](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/server/src/contexts/studio/application/job_history_service.ts) | R077正文不允许列表携带events，却要求列表事件按新到旧；R030和R100要求详情事件按旧到新；明确规范意图并以OpenSpec校正对应正文/场景；再验证具体断言。 |
| SPEC-009 / P2 | specification_conflict / **fail** | 禁止历史版本详情资源与已实现接口冲突 | [revision_routes.ts](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/server/src/contexts/studio/interface/http/revision_routes.ts) | R088禁止独立的历史版本详情资源；DR011已提供GET revisions/:revisionId，当前正文语义本身仍正确；明确规范意图并以OpenSpec校正对应正文/场景；再验证具体断言。 |
| SPEC-010 / P2 | specification_conflict / **fail** | 统计统一UTC要求与本地日期分桶冲突 | [writing_stats_service.ts](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/server/src/contexts/studio/application/writing_stats_service.ts) | R103要求写作日、周和连续天数按UTC且与用量一致；DR045写作统计采用客户端时区偏移，用量保持自己的分桶；明确规范意图并以OpenSpec校正对应正文/场景；再验证具体断言。 |
| SPEC-011 / P2 | specification_conflict / **fail** | 三类Provider步骤规范未覆盖Lore提取 | [text_generation.ts](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/server/src/contexts/ai/application/ports/text_generation.ts) | R017仅列三个步骤；R105及既有ProviderStep已有lore_extract，ACP没有新增第五种业务步骤；明确规范意图并以OpenSpec校正对应正文/场景；再验证具体断言。 |
| SPEC-012 / P1 | specification_conflict / **fail** | 草稿补存规范的静默失败与DR002不丢稿验收冲突 | [spec.md:2078](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/openspec/specs/novel-engine/spec.md:2078)、[2026-10-01-devil-advocate-fix-backlog.md:128](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/docs/audits/2026-10-01-devil-advocate-fix-backlog.md:128) | canonical R046S05要求补存失败不显示错误或恢复Draft，DR002要求切换/关闭不静默丢失未保存内容；明确失败离开时应保留可恢复草稿或阻止离开/明确提示，更新规范后回放500/503离开重开及Revision。 |
| DR-036-STATUS / P2 | record_conflict / **fail** | DR036状态与交付汇总不一致 | [2026-10-01-devil-advocate-fix-backlog.md](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/docs/audits/2026-10-01-devil-advocate-fix-backlog.md) | 47个DR已勾选，DR036未勾选，但交付和章节10声称48全部完成；核实代码与所列验收证据后由维护者一致更新记录，不因汇总自动勾选。 |
| ACP-SEC-01 / P2 | implemented_fix / **pass** | 目录alias保护 | [AcpWorkspace.ts](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/server/src/contexts/ai/infrastructure/providers/AcpWorkspace.ts) | 工作副本路径经过父目录符号链接，单独检查文件O_NOFOLLOW不能识别该目录别名；候选代码与最终回归一致；通用宿主profile内容和平台边界需目标环境独立验证。 |
| ACP-SEC-02 / P1 | implemented_fix / **pass** | 自定义沙箱启动拒绝降级 | [validateAcpWorkspace.ts](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/server/src/apps/api/validateAcpWorkspace.ts) | 使用内建sandbox profile或重复sandbox参数；未知profile可能产生与预期不同的运行约束；候选代码与最终回归一致；通用宿主profile内容和平台边界需目标环境独立验证。 |
| ACP-SEC-03 / P2 | implemented_fix / **pass** | 客户端文件写入独立记录 | [buildAcpClient.ts](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/server/src/contexts/ai/infrastructure/providers/buildAcpClient.ts) | Agent调用客户端fs/write_text_file但未发出原生tool_call通知，文件已改而工具证据缺失；候选代码与最终回归一致；通用宿主profile内容和平台边界需目标环境独立验证。 |
| ACP-SEC-04 / P2 | implemented_fix / **pass** | 工具记录上限保留未知结果 | [withAiExecution.ts](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/server/src/contexts/studio/interface/http/withAiExecution.ts) | 一次请求产生第101个不同工具记录，原证据截断可能误报结果已完全确定；候选代码与最终回归一致；通用宿主profile内容和平台边界需目标环境独立验证。 |
| ACP-NATIVE-JSON / P1 | implemented_fix / **pass** | Grok过程说明与结构化正文分离 | [AcpJsonResponse.ts](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/server/src/contexts/ai/infrastructure/providers/AcpJsonResponse.ts) | Grok先输出过程说明再输出JSON，直接解析全部文本会把成功模型结果判为无效；候选代码与最终回归一致；通用宿主profile内容和平台边界需目标环境独立验证。 |
| ACP-LANGUAGE / P2 | implemented_fix / **pass** | ACP中文Review和设定语言 | [buildAcpSystemContent.ts](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/server/src/contexts/ai/infrastructure/providers/buildAcpSystemContent.ts) | 中文Review任务的模型意见曾返回英文，ACP未明确传入任务语言；候选代码与最终回归一致；通用宿主profile内容和平台边界需目标环境独立验证。 |
| REVIEW-BODY / P1 | implemented_fix / **pass** | Review捕获完整正文与Revision | [review_service.ts](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/server/src/contexts/studio/application/review_service.ts) | Review模型输入只有标题和字数，无法区别同标题、同字数的不同正文；候选代码与最终回归一致；通用宿主profile内容和平台边界需目标环境独立验证。 |
| REVIEW-AUTOSAVE-RACE / P1 | implemented_fix / **pass** | Review等待期间捕获Revision被autosave删除 | [revision_retention.ts](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/server/src/contexts/studio/infrastructure/db/revision_retention.ts)、[review_records.ts:162](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/server/src/contexts/studio/infrastructure/db/review_records.ts:162) | Review捕获R2后连续autosave折叠删除R2；共享应用实例保护捕获Revision直到landing/失败finally，真实HTTP+autosave及释放/并发回归通过。 |
| ACP-CONNECTING-CANCEL / P1 | implemented_fix / **pass** | 升级连接前取消导致未处理WebSocket异常已修复 | [AcpWebSocket.ts:8](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/server/src/contexts/ai/infrastructure/providers/AcpWebSocket.ts:8)、[AcpTextProvider.ts:148](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/server/src/contexts/ai/infrastructure/providers/AcpTextProvider.ts:148) | 预先abort，或TCP已连接但WebSocket upgrade未完成时取消／超时；原预取消及真实TCP等待upgrade的cancel/timeout、普通拒绝连接回归已通过；最终fullcoverage与运行回归见registry。 |
| ACP-REACT-BUSY-GATE / P2 | implemented_gate_fix / **pass** | ACP重试忙碌标记的条件清理触发React诊断警告 | [StudioAcpJobActions.tsx:56](/Users/jackela/.codex/worktrees/acp-full-acceptance/Novel-Engine/frontend/src/features/studio/components/StudioAcpJobActions.tsx:56) | ReactDoctor no-loading-flag-reset-outside-finally 对条件嵌套清理报1条warning，CI要求零diagnostics；失败证据保留；组件测试明确失败读取后按钮enabled，最终全量/React零诊断和浏览器回归见registry。 |

P1 关闭前，使用当前源码或镜像不能获得项目整体通过结论。Unicode CSRF 已确认是错误状态码与异常处理问题，没有认证绕过或进程 DoS 证据。发布镜像漂移与 Release Draft 属于不同权威对象；旧卷升级失败也不能凭 fresh install 通过被关闭。DOC-UPGRADE-PROJECT 证明换目录可能挂载新卷，没有证明旧数据被删除。

12 组规格冲突包括草稿补存的静默失败策略，以及 Revision 保留、备份自动剪枝、标题和导入、费用／用量形态、开发会话 secret、失败流、事件顺序、历史资源、日期分桶和 Provider 步骤数。已采纳整改与老规范冲突时需要正式更新规范，不能为了旧文字自动撤销整改。另两项扫描出的契约差异分别是本轮授权的 ACP 扩展和 Lore 阶段解释，未计为运行缺陷。

14 个 CodeQL 告警分别检查了首次 setup 限流、正则测试代码、导出路径、遗留资源读写与删除。已有 confinement、O_NOFOLLOW、隔离清理等反证按项记录；恶意本机文件系统竞争仍未实测。告警保持远端原状态，最终候选没有新的 CodeQL 结果。

## 6. 产品准入、剩余责任与关闭顺序

| 门槛／剩余工作 | 当前状态 | 责任与关闭条件 |
|---|---|---|
| 草稿安全、备份恢复与旧卷升级 | fail | 项目维护者逐项形成小改动，重放本清单失败及最近恢复边界 |
| 规格／DR 台账协调 | fail | 维护者确定当前规范权威，补 Scenario 和原 DR 验收证据；DR036 状态单独纠正 |
| 真 Grok 稳定性及原生权限 | fail / not run | 维护者在实际支持的隔离权限策略上产生原生确认，验证允许／拒绝、断线未知副作用和四任务稳定完成；不可只延长时限后声称修复 |
| 0.9.0 选区改写与默认 Proposal diff | not run（能力缺项） | Owner 确认产品承诺，按 OpenSpec 实现并在真实写作旅程验收；现有整章及单次 Undo 不等于选区／默认 diff |
| 干净环境首次成功写作、作者访谈与留存 | not run | Owner 的十位作者访谈及至少三位候选留存等原门槛；本轮跳过不改变其状态 |
| Firefox／Safari／实际 IME／AT／阅读器 | blocked / not run | 在支持的普通环境或人工设备上重放；说明具体版本及实际用户动作 |
| 当前候选 CI、Issue 处置、合并、正式发布 | not run | 精确最终候选全部 required checks 成功，按 Issue 契约处置，由 Owner 执行接受、合并及发布授权 |

审计交付完成标准是来源与条目无遗漏、关键问题有可回放依据、未完成项有具体关闭条件；项目验收结果仍可失败。本轮达到的是审计与指定实现交付，不替代发布前后每项责任。

## 7. 回放与文件导航

- [最终证据登记](evidence-registry.json)：检查、状态、候选、环境、操作、日志与未完成原因。
- [规格矩阵](spec-coverage.json)及[历史整改矩阵](historical-remediation.json)：全部原始条目与断言，避免摘要漏项。
- [前端](frontend-evidence.json)、[安全](security-evidence.json)、[运维](operations-evidence.json)：专业复核的原范围及本轮追加验证。
- [回放说明与脚本](replay/README.md)：基线失败、工程检查、假 ACP／浏览器、真 Grok、隔离 Compose 的运行方法。
- [证据脱敏与哈希](evidence/curation-manifest.json)及[交付文件哈希](artifact-manifest.json)：临时原文件与持久副本的关系；合成 token/cookie 已脱敏，真实秘密及数据库未复制。
- [ACP 使用说明](../../acp.md)与[架构决定](../../adr/0011-owner-acp-proxy.md)：配置、客户端、Grok profile、工具权限、副作用、容器网络和隐私。

本报告、矩阵与日志的持久副本都位于本目录；临时路径保留为运行溯源，不是唯一证据来源。没有生成报告 Word/PDF，没有更改发布指针，也没有把测试通过描述为 Owner 已接受。
