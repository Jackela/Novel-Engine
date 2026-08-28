# mimosa 误报复核豁免登记（2026-08-28）

- 日期：2026-08-28
- 性质：只读豁免登记。mimosa deep 扫描（2026-08-28）报告的 5 条 MEDIUM
  经逐条代码复核全部为静态分析误报（0 条真实可利用）；本文照录 #332
  决议的豁免措辞与 finding ids，供后续扫描基线对照。不改产品代码。
- 关联：决议 issue #332（map #329）、分诊票 #348、
  `docs/audits/2026-08-17-pre-rewrite-audit.md`。

## 扫描信息与证据边界

| 项 | 值 |
|---|---|
| scanId | `scan-2026-08-28T16-07-14.424Z-c775f9c5d516` |
| 封印 digest | `sha256:8e74f73ab70a3a2aed01c94fa03a593d91af88929775e3e640905a74cc5a50f1` |
| 证据边界 | `static_only_no_runtime_execution`（纯静态证据，无运行时执行） |
| 覆盖 | 源码 258/258 全解析；completeness `partial`（扫描器自报调用图因动态派发部分不完整，属已知工具限制） |
| 结论 | HIGH 0 / MEDIUM 5 / LOW 0 / INFO 0；5 条 MEDIUM 全部误报；依赖扫描 9 包 0 命中 advisory |

## 豁免一：类级（M1/M2/M3）— DELETE 路由 preHandler guard 覆盖缺口

单 owner 自托管产品授权模型为「会话存在即 owner」，无角色体系，不存在也不应
有 route 级角色注解；三条 DELETE 路由均 `preHandler: [principalGuard(authService)]`
（无会话 401、写方法 CSRF double-submit 403），guard 以 Fastify preHandler 数组
注册，未被静态分析识别为授权约束属工具覆盖缺口。

- M1：`server/src/contexts/studio/interface/http/document_routes.ts:147-168`
  finding `business:70eb0dfbcb081a16c3af`（inconclusive/candidate/verdictEffect: none）
- M2：`server/src/contexts/studio/interface/http/project_routes.ts:106-117`
  finding `business:7816d64f0a881baed6b0`（inconclusive/candidate/verdictEffect: none）
- M3：`server/src/contexts/studio/interface/http/volume_routes.ts:107-118`
  finding `business:03b053230af132e6145c`（inconclusive/candidate/verdictEffect: none）

## 豁免二：M4 — POST /api/setup 首启引导

`server/src/shared/interface/http/auth_routes.ts:120-148` 为设计上的首启引导面：
same-origin 校验 403 + FIRST_CONTACT_PATHS per-IP 限流 429 + owner 唯一性事务校验
（已配置后永久拒绝，无接管窗口）+ 密码策略 10–72 字节。四层防护齐全，
配置后端点等效失效。

- finding `business:1736d58891e285df50f4`

## 豁免三：M5 — DELETE /api/session 登出非敏感

`server/src/shared/interface/http/auth_routes.ts:170-181` 为登出端点，行 173 带
`preHandler: [guard]`；终止自身会话非特权敏感操作。

- finding `business:da3f6e14ebcf2b210694`

## 重新评估条件

若未来引入真正的多用户/RBAC，需重新评估全部豁免（上述 5 处）的有效性。
