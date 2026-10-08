# ACP 代理与 Grok 接入

本功能在当前未发布的 0.8.0 候选中实现。旧的 `ghcr.io/jackela/novel-engine:0.8.0` 镜像不包含本功能；应先从本候选构建。ACP 是 Agent Client Protocol，WebSocket 是本代理的自定义传输，不代表官方通用 WebSocket 服务。

## 本机运行

先安装、登录 Grok CLI。本轮实际验证版本为 1.0.46；不要把登录凭据复制到 Novel Engine 容器。代理令牌与工作室登录、Grok 登录分别管理。

```sh
pnpm --dir server build
node server/dist/apps/cli/main.js acp serve --token-file "$HOME/.local/share/novel-engine/acp-token"
```

首次运行创建 0600 令牌文件，后续读取同一文件；不在日志打印令牌。默认监听 `127.0.0.1:8710`，连接路径 `/acp`。连接在 WebSocket 升级前提交 `Authorization: Bearer …`。不接受 URL 查询令牌或浏览器 Origin。持有令牌的客户端可以启动本人的命令：该服务只供本人信任的 ACP 客户端使用。

建立专用小说资料目录，放入允许工具修改的工作副本。不要把仓库、Studio 数据目录、SQLite、备份、秘密配置或后台登记的导出原件放入该目录。需要参考导出内容时，复制一份到资料目录。

Grok 使用自定义 `novel-engine` 沙箱，而非可能在初始化失败后降级的内置 profile。在该资料目录的 `.grok/sandbox.toml` 中配置，例如：

```toml
[profiles.novel-engine]
extends = "strict"
restrict_network = true
deny = ["/absolute/host/path/to/studio-data", "**/.env", "**/.env.*", "**/*.sqlite3", "**/*.db", "**/*.pem", "**/*.key"]
```

`studio-data` 必须替换成宿主机上真实的数据根，覆盖数据库、备份和登记的导出原件。禁止规则应覆盖宿主机真实路径，而非只填写容器内路径。不要用同名用户全局 profile 覆盖这份规则；启动前检查本人的 Grok 配置、MCP 和已有权限规则。自定义沙箱不存在或不能应用时，Grok 会拒绝启动。本服务仍信任配置的 CLI 和本人配置的 profile；不会把 ACP capabilities 当作原生工具的操作系统隔离，也不会验证任意用户全局配置的全部安全性。

在启动工作室的进程环境中设置：

```sh
export ACP_PROXY_TOKEN_FILE="$HOME/.local/share/novel-engine/acp-token"
export ACP_WORKSPACE_ROOT="/absolute/path/to/novel-materials"
export ACP_AGENT_COMMAND="/absolute/path/to/grok"
pnpm --dir server cli serve
```

工作室的项目设置只选择 `acp` Provider。命令、参数、工作目录和模型由后端配置，不接受浏览器请求注入。首次运行先用合成内容验证实际工具访问范围。

| 设置 | 默认或含义 |
|---|---|
| `ACP_PROXY_URL` | `ws://127.0.0.1:8710/acp`；远程连接需受保护的网络或 TLS/SSH 隧道 |
| `ACP_PROXY_TOKEN_FILE` | 必填；只含独立代理令牌的文件 |
| `ACP_WORKSPACE_ROOT` | 必填；绝对路径、已存在的专用资料目录，与 Studio 数据根不得交叠 |
| `ACP_AGENT_COMMAND` | `grok`；直接启动可执行文件，不解释 Shell 字符串 |
| `ACP_AGENT_ARGS` | JSON 字符串数组；默认 `["--no-auto-update","--sandbox","novel-engine","agent","--no-leader","stdio"]` |
| `ACP_MODEL` | 可选；通过实际 session config 选择并确认，不能用 `LLM_MODEL` 伪造模型事实 |

默认握手 30 秒、执行 180 秒、权限等待 120 秒、总操作 600 秒。等待权限暂停执行计时，总操作上限仍适用。每个连接单独拥有子进程；断线或退出会清理进程组。单消息上限 1 MiB、缓冲上限 8 MiB。Review 先按共享 8 MiB 正文输入预算拒绝超限；ACP 还检查实际编码后的 prompt 是否适合 1 MiB 消息，超限在启动模型或工具前明确拒绝，不截断章节。Windows 的进程清理实现存在，但本轮没有 Windows 执行证据。

## stdio 客户端连接工具

只支持 stdio 的 ACP 客户端可将下面的程序设置为 agent command：

```sh
node server/dist/apps/cli/main.js acp connect \
  --url ws://127.0.0.1:8710/acp \
  --token-file "$HOME/.local/share/novel-engine/acp-token" \
  --command /absolute/path/to/grok \
  --arg --no-auto-update --arg --sandbox --arg novel-engine \
  --arg agent --arg --no-leader --arg stdio \
  --cwd /absolute/path/to/novel-materials
```

每个 `--arg` 后跟一个参数，可包含以 `--` 开头的值。工具给首个 `initialize.params._meta["novel-engine/acp-proxy"]` 添加 `{command,args,cwd}`。代理只消费该启动字段，随后双向转发 JSON-RPC；权限、会话、工具和取消消息保留原来的请求标识。诊断走 stderr，stdout 保持协议数据。

## 容器连接宿主代理

两份 Compose 已传递 ACP 设置，仍需显式挂载令牌和资料目录。令牌只读挂载；资料目录在容器内与宿主机保持相同绝对路径，以支持受约束的文件回调。Grok 可执行文件和登录态保留在宿主机。

在隔离的 Compose override 中设置：

```yaml
services:
  novel-engine:
    environment:
      ACP_PROXY_URL: ws://host.docker.internal:8710/acp
      ACP_PROXY_TOKEN_FILE: /run/secrets/acp-token
      ACP_WORKSPACE_ROOT: /absolute/path/to/novel-materials
      ACP_AGENT_COMMAND: /absolute/host/path/to/grok
    volumes:
      - /absolute/host/path/to/acp-token:/run/secrets/acp-token:ro
      - /absolute/path/to/novel-materials:/absolute/path/to/novel-materials
```

宿主地址及访问方式取决于 Docker 环境。默认回环监听不保证容器可达；使用受保护的转发地址，或将代理绑定到明确的可达接口。不要将无 TLS 的 Bearer 连接暴露给不受信任网络。挂载路径、实际访问和宿主沙箱保护需要在目标环境验证。

## 工具、结果与恢复

续写、改写、Review、Lore 提取均先建立请求范围的观察通道，再提交 AI 请求。CLI 请求确认时，界面展示动作、资料目标和 CLI 提供的允许/拒绝选项。答复接口验证 Owner、项目、操作和一次性权限标识，并要求 CSRF；过期或重复答复拒绝。

工具信息与思考内容不写入正式正文。只有符合预期 schema 的单个 JSON 对象进入现有业务校验；可忽略有限的前导过程说明，但多对象、尾部杂讯、截断和非法结构不能成为成功结果。正式正文仍经接受提案或保存生成 Revision，Review 绑定捕获的正文、阅读顺序和 Revision 集合。

任务详情保存安全工具摘要与未知结果状态。已提交可能产生文件影响的 prompt 不自动重放；再次执行由作者明确操作。取消、拒绝、断线和失败不会撤销已经完成的工具文件写入。重新执行前检查工作副本，并查看任务的工具记录。

实际模型来自 ACP session/config 证据。CLI 未报告 token 时沿用现有带来源标识的估算；失败的 `unreported` 记录不是“零费用”。该账本不是供应商账单或费用限额。Grok 可保存本机会话记录，并向所用模型发送内容；其 MCP、插件、网络及保留策略由本人 CLI 配置和供应商政策决定。

参考：[ACP 传输](https://agentclientprotocol.com/protocol/v1/transports)、[Grok ACP](https://docs.x.ai/build/cli/headless-scripting)、[官方沙箱说明](https://github.com/xai-org/grok-build/blob/main/crates/codegen/xai-grok-pager/docs/user-guide/18-sandbox.md)、[ADR-0011](adr/0011-owner-acp-proxy.md)。
