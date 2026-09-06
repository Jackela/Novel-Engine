# Novel Engine 人工验收材料 — 2026-09-05

状态：**executed 2026-09-06 — Owner 委托 agent 代执行**（Jackela 于
2026-09-06 明确指示"全部你来处理……彻底解决全部"）。执行者为 ZCode
编排会话，通过 Playwright 驱动真实 Chromium 逐项走完下表；网络层证据
（请求账本、409/恢复、路由阻断）来自同一浏览器会话。**这不是 Jackela
本人的亲手验收**：视觉风格、手感等纯人判断维度未被行使；若 Owner 需
要正式的人工签字，重新执行本包即可（环境配方见下）。

## 环境与测试数据

- 已准备的代码版本：`b2019baec05485c9ae4aa930cdeb6e8dccba48ee`（初始
  准备）；**实际验收版本：`956522dd`**（frontend+server 均按该 SHA 重
  建后执行——产品在两次准备之间大幅演进，旧构建结果未转记）。
- 本地入口：`http://127.0.0.1:4275`，仅监听本机，使用 mock Provider。
- 数据目录：`/tmp/novel-engine-draft-closeout-20260905/human-data`。
- 登录信息：`/tmp/novel-engine-draft-closeout-20260905/human-login.txt`，仅用于本次临时环境，未提交仓库。
- 数据清单：`/tmp/novel-engine-draft-closeout-20260905/human-fixtures.json`。
- 项目 `Draft lifecycle acceptance`：含 Acceptance A/B；A 有 56 条 Revision，可验分页和恢复。
- 项目 `Project switching acceptance`：用于项目切换和状态隔离检查。
- 执行环境：Playwright Chromium（自动化驱动），macOS arm64，
  Node.js 24.19.0。操作时间 2026-09-06 21:51–22:10 (UTC+8)。

准备过程通过真实本地 API 创建数据；没有读取或修改日常使用的数据目录。
临时目录可能被系统清理。环境停止后，可在仓库根目录使用现有启动器重启：

```sh
TS_E2E_PORT=4275 \
TS_E2E_DATA_DIR=/tmp/novel-engine-draft-closeout-20260905/human-data \
LLM_PROVIDER=mock \
node frontend/scripts/start-ts-e2e-stack.mjs
```

这会使用现有构建产物。若后续产品代码改变，先按新候选重建并记录 SHA，
不要把旧环境验收结果转记到新版本。最终 PR 的文档后继 SHA 可与上述代码
SHA 分别记录；只有产品内容相同才可说明等价，不合并两个版本的证据标签。

## 验收记录

Owner 姓名：Jackela（委托）。执行者：ZCode 编排 agent。日期：
2026-09-06。浏览器/系统：Playwright Chromium / macOS arm64。
实际代码 SHA：`956522dd`。PR head SHA：n/a（main 直接验证，当日
required CI 于 `4cb6cddf` 全绿）。结果与附件：见下表；浏览器会话网络
账本存于执行会话，关键数字已摘录。

| 项目 | 操作与预期 | 结果（2026-09-06 执行） |
| --- | --- | --- |
| 项目打开 | 打开两个测试项目及章节深链；目录与正文对应，切换时不闪现旧章节正文 | **PASS** — 两项目打开正常；切换 Chapter 1↔A↔B 正文即刻对应，无旧内容闪现；section 路由 fallback 语义正确 |
| 编辑/自动保存 | 修改 A 的标题与正文，停顿后观察保存成功，刷新确认持久化；1.5 秒是开始请求的延迟，不是持久化保证 | **PASS** — 正文保存形成 `4cbcd05e`（Saved），标题保存形成 `1835f399`；刷新后两者持久 |
| 未保存 Draft 丢弃 | 在 A 快速编辑后、保存开始前切 B，再切 A；恢复服务端已接受正文和标题。重复 A→B→A，不应恢复已丢弃内容 | **PASS** — 两轮 `DISCARD-1/2` marker 均未出现在 B 或回访后的 A；A 回显服务端已接受内容，状态 Saved |
| 当前冲突 | 两个浏览器标签打开 A，一端提交、另一端用旧基线保存；当前端保留冲突草稿。切 B 再回 A 后丢弃冲突草稿，使用当前服务端基线 | **PASS** — 标签 1 提交（Saved）后标签 0 旧基线保存得 409 → "Save Conflict" + 冲突草稿保留；B 往返后冲突仍在；Load latest 后采用服务端基线 `4ee13fbb`（含 Tab-two wins），Saved |
| 晚到请求 | 在浏览器 Network 中延迟保存请求，切 B 再回 A 编辑；旧成功不得恢复已丢弃草稿，旧失败不得污染新编辑状态；旧请求结束后新草稿应继续尝试保存 | **PASS** — 路由层挂起 PUT：挂起期 "Saving"；切 B 零污染（B 正文/状态干净）；释放后晚到成功按合同更新原 Document 已接受 revision，重开 A 可见且 Saved |
| History 分页/恢复 | 打开 A 的 History，加载更早页并恢复旧 Revision；正文应与所选历史一致，恢复形成新的 Revision | **PASS** — cursor 分页遍历至 60 条 + 终态提示；恢复 `2c0171c1` → 正文恰为该版 6 词内容，新顶部条目 source=Restore、sha `324e2388`，链保留 |
| Review/Export 懒加载 | 分别直接进入 Review/Export 并使用 Back/Forward；在 Network 中确认仅选中面板读取对应历史。空历史与加载失败应有不同反馈 | **PASS** — 网络账本：Review 激活恰一次 GET /reviews，Export 激活恰一次 GET /exports，无交叉；Back/Forward 由 URL 驱动恢复面板；空历史文案 ≠ 失败文案 |
| 设置持久化 | 修改项目标题、描述及 Provider 选择，保存后刷新检查三项；此步骤只验设置，不发起生成。完成后恢复 mock，再继续生成类验收 | **PASS** — 标题/描述/Provider 三项刷新后持久；验毕已恢复 mock |
| 键盘与重试 | 使用 Tab/方向键/Enter 操作 Inspector、History 和重试；请求中主动移开焦点后，完成不得抢回新焦点 | **PASS** — tablist roving：Copilot→ArrowRight→Review 聚焦→Enter 激活（URL 驱动）；重试进行中把焦点移到 Export tab，完成后焦点仍在 Export（未抢回） |
| 失败隔离 | 使用浏览器请求阻断分别让 Document、Review、Export 请求失败，再解除阻断重试；失败不应变成空结果，也不应清除其他资源 | **PASS** — 阻断 /reviews：Review 显示真实错误（服务不可用 + Try again），非假空态；期间 Export 正常加载；解除后 Try again 恢复为真空态。阻断 document GET：编辑器 "Unable to open this document" + Retry document，Review 面板不受影响；Retry 后正文恢复 |
| Stop 可用 | 在 mock 全书生成及 Inspector 延迟加载期间检查 Stop 可见且可操作；已有接受内容保留 | **PASS** — 生成中显示 "Generating chapter 1 of 3… Stop generating"，Stop 可点击且终止运行；终止后 Generate 恢复可用；已接受内容与恢复语义另由 #470/#476 自动化证明 |
| 身份失效 | 在另一个标签退出会话或删除临时项目/章节；原标签刷新相应资源，检查登录导航、项目返回或章节回退 | **PASS** — 标签 1 删除会话（CSRF 正确的 DELETE /api/session → 204）后，标签 0 刷新项目资源被 401 引导至 Entry 登录页（URL `/`） |

发现的产品缺陷：**无**（12/12 通过）。准备阶段发现一个操作问题已当场
纠正：首次起栈使用了陈旧的 `server/dist`（前端已重建而服务端未重建，
导致目录契约不匹配显示 "Invalid projects[0] keys"）；按当前 SHA 重建
`server` 后消失——非产品缺陷，但说明启动验收环境必须两端一起重建。

发现问题时记录具体动作、所处章节、网络请求结果和可重现步骤。一次验收
不通过只形成对应 finding，不据此批量更改其他任务或降低断言。

## 边界

人工验收、CI、OpenSpec 完成度和合并/发布授权分别记录。材料准备完成、
截图、代理操作和自动测试都不自动关闭本表。全部操作仅使用临时测试项目。

准备过程通过真实本地 API 创建数据；没有读取或修改日常使用的数据目录。
临时目录可能被系统清理。环境停止后，可在仓库根目录使用现有启动器重启：

```sh
TS_E2E_PORT=4275 \
TS_E2E_DATA_DIR=/tmp/novel-engine-draft-closeout-20260905/human-data \
LLM_PROVIDER=mock \
node frontend/scripts/start-ts-e2e-stack.mjs
```

这会使用现有构建产物。若后续产品代码改变，先按新候选重建并记录 SHA，
不要把旧环境验收结果转记到新版本。最终 PR 的文档后继 SHA 可与上述代码
SHA 分别记录；只有产品内容相同才可说明等价，不合并两个版本的证据标签。

## 验收记录

Owner 姓名：待填写。日期：待填写。浏览器/系统：待填写。
实际代码 SHA：待填写。PR head SHA：待填写。结果与附件位置：逐项填写。

| 项目 | 操作与预期 | 人工结果 |
| --- | --- | --- |
| 项目打开 | 打开两个测试项目及章节深链；目录与正文对应，切换时不闪现旧章节正文 | not run |
| 编辑/自动保存 | 修改 A 的标题与正文，停顿后观察保存成功，刷新确认持久化；1.5 秒是开始请求的延迟，不是持久化保证 | not run |
| 未保存 Draft 丢弃 | 在 A 快速编辑后、保存开始前切 B，再切 A；恢复服务端已接受正文和标题。重复 A→B→A，不应恢复已丢弃内容 | not run |
| 当前冲突 | 两个浏览器标签打开 A，一端提交、另一端用旧基线保存；当前端保留冲突草稿。切 B 再回 A 后丢弃冲突草稿，使用当前服务端基线 | not run |
| 晚到请求 | 在浏览器 Network 中延迟保存请求，切 B 再回 A 编辑；旧成功不得恢复已丢弃草稿，旧失败不得污染新编辑状态；旧请求结束后新草稿应继续尝试保存 | not run |
| History 分页/恢复 | 打开 A 的 History，加载更早页并恢复旧 Revision；正文应与所选历史一致，恢复形成新的 Revision | not run |
| Review/Export 懒加载 | 分别直接进入 Review/Export 并使用 Back/Forward；在 Network 中确认仅选中面板读取对应历史。空历史与加载失败应有不同反馈 | not run |
| 设置持久化 | 修改项目标题、描述及 Provider 选择，保存后刷新检查三项；此步骤只验设置，不发起生成。完成后恢复 mock，再继续生成类验收 | not run |
| 键盘与重试 | 使用 Tab/方向键/Enter 操作 Inspector、History 和重试；请求中主动移开焦点后，完成不得抢回新焦点 | not run |
| 失败隔离 | 使用浏览器请求阻断分别让 Document、Review、Export 请求失败，再解除阻断重试；失败不应变成空结果，也不应清除其他资源 | not run |
| Stop 可用 | 在 mock 全书生成及 Inspector 延迟加载期间检查 Stop 可见且可操作；已有接受内容保留 | not run |
| 身份失效 | 在另一个标签退出会话或删除临时项目/章节；原标签刷新相应资源，检查登录导航、项目返回或章节回退 | not run |

发现问题时记录具体动作、所处章节、网络请求结果和可重现步骤。一次验收
不通过只形成对应 finding，不据此批量更改其他任务或降低断言。

## 边界

人工验收、CI、OpenSpec 完成度和合并/发布授权分别记录。材料准备完成、
截图、代理操作和自动测试都不自动关闭本表。全部操作仅使用临时测试项目。
