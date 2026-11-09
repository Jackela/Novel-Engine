# 重建工作区

Novel Engine 全栈重建的阶段产出与约定。计划本体在 `.workbuddy/plans/stellar-aurora-babbage-xquKyuqB.md`，这里只放"做的时候需要随手查"的东西。

## 现在在哪

阶段 0（冻结行为）完成，阶段 1（walking skeleton）进行中。

| 已落地 | 位置 | 状态 |
|---|---|---|
| 错误契约 | `server/src/contracts/errors.ts` | 冻结，`22c53b8ffc2c` |
| 项目 / 文档契约 | `server/src/contracts/{projects,documents}.ts` | 编译通过 |
| 错误信封 | `server/src/platform/http/error_envelope.ts` | 编译通过 |
| 分页编解码 | `server/src/platform/http/pagination.ts` | 13 测试 |
| 运行时注入 | `server/src/platform/kernel/` | 编译通过 |
| 数据层 | `server/src/platform/db/schema/`（6 文件 17 表） | 编译通过 |
| provider 端口 | `server/src/platform/text-generation/ports.ts` | 编译通过 |
| 行为契约 | `docs/rebuild/invariants.md`（44 条） | — |
| 需求映射 | `docs/rebuild/requirements-matrix.md`（114 条） | — |
| 测试分诊 | `docs/rebuild/test-triage.md`（508 文件） | — |

九道门全绿，含新增的 `error-codes-v1`。

另外两份清单分工不同：`invariants.md` 列**必须成立的行为**（44 条，每条要有会红的用例）；`unchecked.md` 列**类型与门禁都兜不住的约束**（5 条，区分「已知缺口」与「待办」）。后者存在的意义是交付时不被误判——把缺口当待办会被判未完成，把待办当缺口则漏洞永远留着。

## 四份规格各管什么

| 文档 | 什么时候读 |
|---|---|
| `specs/manuscript-domain.md` | 写 authoring / library 切片时。修订链、字数口径、快照、检索、容量的唯一依据 |
| `specs/generation-provider.md` | 写 generation 切片与 provider 适配时。12 个失败 kind、SSE 协议、净化规则 |
| `specs/error-http.md` | 写任何路由时。信封形状、22 条码的触发条件、分页协议 |
| `../agents/error-codes-v1.md` | 给 agent 读的错误码表；与契约由门禁绑定 |

规格里标注「规格与实现不一致」的条目，是实现时的决策点，不是障碍。

## 协作约定

这一轮所有跨人分歧最后都靠三样东西收敛：**源码行号、可复算的数值、以及"如果没人发现它会怎么坏"**。凡是能说清后者的争议，收敛都很快；说不清的（例如"该不该新增 502"）只能靠裁决，而裁决往往出错——那一轮确实错了一次。

所以提变更时先回答一句：**如果没人发现，它会静默坏在哪？**

答不出来，说明这个变更还没有证据支撑，先别提。

## 三条容易踩的工具约定

**Node 版本。** 系统 node 是 22，项目要求 ≥24。所有命令前面加 `PATH="/Users/jackela/.local/bin:$PATH"`。

**pnpm 调用形态。** `pnpm --dir server vitest` 无效，要 `cd server && pnpm exec vitest`。

**引用新代码用符号名，不用行号。** 旧代码是冻结的，行号可靠；新代码在压缩与重排，行号会在几十分钟内失效——本轮 `ports.ts` 被三个人看过、改过两次，行号漂了两次，导致一次误判。规格与注释引用新代码时写符号名（`ProviderFailure.transport_connect`、`TextGenerationResult.text`），行号只作为"核对时刻"的附注。

## 门禁里与新代码有关的两个

- `check_error_codes.mjs`：旧的三面 lockstep，保护仍在跑的老代码。
- `check_error_codes_v1.mjs`：新的双轨，比对 `contracts/errors.ts` ↔ `error-codes-v1.md` 的 code / status / retry / remedy 四列，外加一条**文案指纹**（`52a6eb27181b`）。指纹是变更探测器而不是副本：文案改了它才响，指向「重读 §5」，不是「改表」。

切换阶段删旧门禁，新门禁升为唯一。
