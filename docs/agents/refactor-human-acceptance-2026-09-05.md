# Novel Engine 人工验收材料 — 2026-09-05

状态：**not run，等待 Owner 操作与判断**。以下准备和自动化结果不算人工验收。

## 环境与测试数据

- 已准备的代码版本：`b2019baec05485c9ae4aa930cdeb6e8dccba48ee`。
- 本地入口：`http://127.0.0.1:4275`，仅监听本机，使用 mock Provider。
- 数据目录：`/tmp/novel-engine-draft-closeout-20260905/human-data`。
- 登录信息：`/tmp/novel-engine-draft-closeout-20260905/human-login.txt`，仅用于本次临时环境，未提交仓库。
- 数据清单：`/tmp/novel-engine-draft-closeout-20260905/human-fixtures.json`。
- 项目 `Draft lifecycle acceptance`：含 Acceptance A/B；A 有 56 条 Revision，可验分页和恢复。
- 项目 `Project switching acceptance`：用于项目切换和状态隔离检查。

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
