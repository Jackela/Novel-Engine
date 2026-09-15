# Provider setup

Novel Engine 通过 **provider** 生成文字——provider 就是把你的指令变成提案
的 AI 服务。本指南讲解如何用 Docker Compose 配置一个 provider，并给出
DashScope 和任意 OpenAI 兼容接口（以 DeepSeek 为例）的精确环境变量示例。

如果你只是想先试试这个工作室，暂时不需要本页：内置的试用 provider
（`mock`）不需要 API key、不需要在任何地方注册账号，就能写出真实、确定的
文字，而且每一个功能——Copilot、整本书生成、评审——都能用它跑通。

## How providers are selected

每个项目在项目**设置**面板里选择自己的 provider（界面中标注为「生成服
务」）。面板会列出所有 provider
类型——`mock`、DashScope 和 OpenAI 兼容——但只有服务器已经拿到其 API key
的那几个（见下文）才能成功生成；选了一个未配置的 provider 会让每次生成
都失败。在你配置好 key 之前，让项目保持在内置的试用 provider（`mock`）
上。

## How configuration reaches the container

工作室容器从环境变量读取配置。用 Docker Compose 时，最简单的设置方式是
`compose.yaml` 旁边的 `.env` 文件：Compose 会自动读取这个文件，并把
provider 设置透传给容器，所以只要把 key 写进 `.env`，再跑一次
`docker compose up -d` 就完成了。这个文件由你编辑，不属于工作室代码的一
部分，因此[升级](upgrading.md)永远不会覆盖它。

在包含 `compose.yaml` 的文件夹里新建一个名为 `.env` 的文件（全新下载只带
一个 `.env.example` 模板；如果已有 `.env`，继续用它），把设置写成普通的
`NAME=value` 行：

```bash
LLM_PROVIDER=dashscope
DASHSCOPE_API_KEY=sk-your-key-here
```

然后应用更改：

```bash
docker compose up -d
```

`up -d` 会用新的环境变量重建容器；改完文件只做普通的 restart 是不够的。

也可以在 `compose.yaml` 旁边放一个 `compose.override.yaml`——Compose 会把
它合并到主文件之上，适合需要改端口这类结构性调整的场合。设置写进
`environment` 块：

```yaml
services:
  novel-engine:
    environment:
      LLM_PROVIDER: dashscope
      DASHSCOPE_API_KEY: sk-your-key-here
```

注意：

- 在 shell 里导出的设置（`export DASHSCOPE_API_KEY=...`）优先于 `.env`
  文件；两者通过同一条透传通道进入容器。
- 这些值永远不会被回显进日志或错误信息。

## DashScope

DashScope 是阿里云的模型服务（通义千问 Qwen 模型家族）。

1. 登录 DashScope 控制台（百炼 / Model Studio）：
   `https://bailian.console.aliyun.com/`——国际用户：
   `https://modelstudio.console.alibabacloud.com/`。如果提示开通模型服务，
   按提示开通（计费按 token 量付费）。
2. 在控制台打开 **API-KEY** 管理，创建一个 key 并复制。
3. 把 key 放进 `compose.yaml` 旁边的 `.env` 文件：

   ```bash
   LLM_PROVIDER=dashscope
   DASHSCOPE_API_KEY=sk-your-key-here
   ```

4. 运行 `docker compose up -d`，然后打开项目的**设置**，选择
   **DashScope**。

可选的补充项：

| 变量 | 用途 |
|---|---|
| `DASHSCOPE_MODEL` | 生成模型。默认 `qwen3.5-flash`。 |
| `DASHSCOPE_REVIEW_MODEL` | 评审（AI review）专用的另一个模型；缺省回退到生成模型。 |
| `DASHSCOPE_API_BASE` | 自定义 API base URL，只用于镜像 DashScope API 的网关。 |
| `DASHSCOPE_TRANSPORT_MODE` | `multimodal_generation`（默认）、`text_generation` 或 `responses`。 |

## OpenAI-compatible endpoints (DeepSeek as the example)

任何讲 OpenAI chat-completions API 的服务都能通过 `openai_compatible`
provider 接入。你需要从服务商那里拿三个值：API base URL、API key 和模型
名。

### DeepSeek, step by step

1. 登录 `https://platform.deepseek.com/`，充一点额度（计费按 token 量
   付费）。
2. 在左侧菜单打开 **API keys**，按 **Create new API key**，复制 key（之后
   再也看不到它了）。
3. 把这些值放进 `compose.yaml` 旁边的 `.env` 文件：

   ```bash
   LLM_PROVIDER=openai_compatible
   OPENAI_API_KEY=sk-your-deepseek-key
   OPENAI_API_BASE=https://api.deepseek.com/v1
   OPENAI_COMPATIBLE_MODEL=deepseek-chat
   ```

4. 运行 `docker compose up -d`，然后打开项目的**设置**，选择
   **OpenAI 兼容**。

### Other OpenAI-compatible services

同样的三个变量适用于任何兼容接口——工作室把 `LLM_API_KEY` /
`LLM_API_BASE` 作为规范名，同时接受 `OPENAI_API_KEY` /
`OPENAI_API_BASE` 作为别名（两种写法都行）：

```bash
LLM_PROVIDER=openai_compatible
LLM_API_KEY=sk-your-key
LLM_API_BASE=https://api.openai.com/v1
OPENAI_COMPATIBLE_MODEL=gpt-4o-mini
```

模型名必须是该接口真实提供的；如果不填，工作室回退到 `gpt-4o-mini`
（设置了 `LLM_MODEL` 时则用它）。

## Checking that it works

1. 打开一个项目，在**设置**里选好 provider，新建或打开一章，跑一次
   Copilot 的**继续**。一段流式提案就是 key、base URL、模型全部正常工
   作的端到端证明。
2. 如果生成失败，看服务器日志里具体的 provider 错误：

   ```bash
   docker compose logs novel-engine
   ```

   常见原因：复制 key 时带了多余的空格、改完 `.env` 后没跑 `up -d`、模型
   名在该接口不存在，或者账户欠费。
3. 想要一份更深入的数据库与配置健康报告，可以在容器里运行 `doctor` 命令
   ——它需要先停掉工作室；精确的停止/运行/启动顺序见
   [backup and restore](backup-and-restore.md#running-cli-commands-in-docker)。

## Back to trial mode

在 `.env` 里设置 `LLM_PROVIDER=mock`（或删掉 `LLM_PROVIDER` 这一行），然后
运行 `docker compose up -d`。项目就会回到试用 provider 上；无论怎么切，
你的手稿都不受影响。
