# 回放说明

本目录是调查工具，不能代替候选 CI 或发布脚本。进入仓库根目录后设置 `NOVEL_ENGINE_REPLAY_ROOT` 为当前仓库绝对路径，设置 `NOVEL_ENGINE_REPLAY_EVIDENCE` 为新建的隔离输出目录。依赖、构建及 Playwright 浏览器需已安装。产品代码候选为 `da025b7de90a6b2106892d5d8490bbdfd8628a20`；后续审计文档提交不改变它。

## 固定基线的三个失败

```bash
export NOVEL_ENGINE_REPLAY_ROOT="$PWD"
export NOVEL_ENGINE_REPLAY_EVIDENCE="$(mktemp -d /tmp/ne-baseline-evidence-XXXXXX)"
python3 docs/audits/2026-10-08-full-project-acceptance/replay/baseline.py
```

该工具从 Git 归档固定基线，排除禁区，使用临时数据库。预期三项失败分别为 Unicode CSRF 500、备份 EACCES 被吞掉、最旧恢复输入被剪枝删除。失败断言代表验收缺陷；工具不会修改被调查源码，也不会连接真实数据库。可检查原始 [观测](../evidence/baseline-observations.json) 与 [日志](../evidence/baseline-reproductions.log)。

## 最终候选的工程检查

```bash
pnpm --dir server gates
pnpm --dir server type-check
pnpm --dir server lint
pnpm --dir server lint:types
pnpm --dir server arch
pnpm --dir server test:coverage
pnpm --dir server build
pnpm --dir frontend lint
pnpm --dir frontend lint:types
pnpm --dir frontend format:check
pnpm --dir frontend type-check
pnpm --dir frontend test:coverage --maxWorkers=2
pnpm --dir frontend build
pnpm --dir frontend check:api-types
pnpm --dir frontend exec react-doctor --json
pnpm spec:validate
pnpm audit --audit-level high --prod
pnpm audit --audit-level high
pnpm --dir frontend test:e2e:ts --workers=2
```

源码和文档差异可用 `git diff --check 066d923d HEAD -- . ":(exclude)docs/audits/2026-10-08-full-project-acceptance/evidence/**"` 检查。未排除证据时，原始终端日志的尾随空白和末尾空行会使检查返回非零；日志保留原貌，参见 `../evidence/delivery-verification.json`。

全依赖审计已知返回非零，因为开发工具链的 braces 告警仍未处理；生产依赖检查通过。覆盖率阈值和断言未降低。浏览器标准套件使用其自身新建的数据目录，禁用浏览器安全选项未使用。

## ACP 浏览器权限、取消及正式正文边界

新建输出目录后，在一个终端运行 `node docs/audits/2026-10-08-full-project-acceptance/replay/start-fake-stack.mjs`；它只监听本机 4381。另一终端执行：

```bash
NOVEL_ENGINE_ACP_E2E_URL=http://127.0.0.1:4381 \
NOVEL_ENGINE_ACP_E2E_MATERIALS_ROOT="$NOVEL_ENGINE_REPLAY_EVIDENCE/fake-materials" \
pnpm --dir frontend exec playwright test -c playwright.acp.config.ts
```

运行后以 Ctrl-C 关闭本轮服务。用于草稿补存与接受后刷新问题的 `ui-replay.mjs` 要在这两个测试创建合成 Owner 后运行；输出目录须已存在。它注入 500/503 并记录数据库/API/屏幕差异。`ui-boundaries.mjs`、`ui-controls.mjs`、`ui-unload.mjs` 分别重放长稿、主题、窄屏及原生关闭保护；程序化 composition 不是操作系统输入法验收。

## 真实 Grok

`frozen-grok.mjs` 包含 Review 等待期间的两次自动保存与 Snapshot 检查；`replay-grok-studio.mjs` 使用独立合成中文对照稿重放四种任务。它们会使用本机 Grok 的既有登录态、产生实际模型调用费用及 CLI 会话记录。默认路径为本机已核实的 `/Users/jackela/.grok/bin/grok`，可设置 `NOVEL_ENGINE_REPLAY_GROK`。每次必须使用新的输出目录。

```bash
node docs/audits/2026-10-08-full-project-acceptance/replay/replay-grok-studio.mjs
```

脚本只创建本轮资料、数据、0600 代理令牌和专用 `novel-engine` sandbox profile，不复制登录凭据。模型等待超时应保留失败 Job 与外部操作证据，再由操作者明确发起新的请求；不能把脚本重跑当成 Provider 自动重放。安装的 Grok 1.0.46 不支持 `--permission-mode ask`；真实原生权限请求未出现，假进程的允许／拒绝证据不能替代这一缺项。

## 容器与阅读器

`ops-harness.py` 支持 `candidate`、`release`、`cleanup`，使用本轮新建的 Compose 项目、卷、端口和数据。默认候选 tag 为 `novel-engine-acp-audit:final`，可设 `NOVEL_ENGINE_REPLAY_IMAGE`。运行前核实镜像 label 与候选 SHA；所有阶段须使用同一隔离输出目录，最后运行 `cleanup`。实际 Compose 参数继承产品文件，通过临时 override 仅选择本轮镜像、端口和合成环境。

容器到宿主 ACP 的网络地址依 Docker 环境不同；本轮 Colima 使用其宿主网关。不能把本轮 IP 固化为产品默认。阅读器验证要独立执行：ZIP/XML 校验通过不等于 EPUB 阅读器或 WPS 视觉验收通过。

## 证据解释

`../evidence/curation-manifest.json` 记录临时原文件与持久副本的 SHA256，以及合成 token/cookie 脱敏。未复制真实数据库、原始 Grok stderr、全局会话或用户秘密文件。早期实现和失败日志保留当时范围；最终候选证据以主报告及 evidence-registry.json 的绑定为准。

回放脚本记录执行时实际 Git HEAD；务必先构建该 checkout，并保留未提交变更及源文件哈希。原证据的 SHA 不因脚本在新提交重跑而改变。

矩阵库存、断言映射和当前源哈希可用 `python3 docs/audits/2026-10-08-full-project-acceptance/replay/validate-matrices.py` 检查。
