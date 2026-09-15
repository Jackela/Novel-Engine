# Troubleshooting

针对 Docker 部署的按症状排查。绝大多数问题是这三种之一：端口被占用、浏
览器怪癖，或者 provider 配置没有真正到达容器。

## The studio does not open on localhost:8000

**症状：** `docker compose up -d` 跑完了，但浏览器连不上，或者容器不停重
启。

端口 8000 可能已被另一个应用占用。把工作室挪到 8001：在 `compose.yaml`
旁边创建一个 `compose.override.yaml`，内容为：

```yaml
services:
  novel-engine:
    ports: !override
      - "8001:8000"
```

然后运行 `docker compose up -d`，打开 `http://localhost:8001`。（
`!override` 标记需要 Docker Compose v2.24+，当前的 Docker Desktop 自带该
版本；也可以直接编辑 `compose.yaml`，把 `8000:8000` 改成 `8001:8000`。）

还是不行？看看容器在说什么：

```bash
docker compose logs novel-engine
```

并在你实际映射的宿主机端口上检查健康端点——比如改端口后的
`http://localhost:8001/health/ready`，或默认安装的
`http://localhost:8000/health/ready`。那里能返回 JSON 就说明服务器本身没
问题，问题出在浏览器与端口之间。

## I created my account but cannot use the studio (Safari)

Safari 能显示工作室，但在磨砂玻璃视觉风格下有一个已知的渲染缺陷，而
Safari 特有的登录问题是最常见的反馈。请用 **Chrome 或 Firefox**。你的账
户和手稿不受所用浏览器的影响。

## Generation fails with a provider error

**症状：** Copilot 或整本书生成一开始就报错，
`docker compose logs novel-engine` 里显示 provider 失败。

按这张清单逐项检查：

1. 改完 `.env`（或 `compose.override.yaml`）之后，你跑过
   `docker compose up -d` **了吗**？光 restart 不会应用新的环境变量；容器
   必须被重建。
2. API key 是否完整——没有被截断、没有混进空格——并且在服务商控制台里仍
   然有效？
3. 模型名在那个接口上存在吗（DeepSeek 用 `deepseek-chat`，DashScope 用
   `qwen3.5-flash`）？
4. provider 账户还有额度或配额吗？
5. 想在排查期间继续写作，就在设置里把项目的 provider 切回
   **Mock（试用 — 无需 API key）**；它永远可用。

完整的配置清单见 [provider setup](provider-setup.md)。

## "The data directory is already owned by another Novel Engine process."

**症状：** `backup`、`restore` 或 `doctor` 命令拒绝运行。

正在运行的工作室以独占方式持有数据目录。先停掉它，再跑命令，然后启动回
来——精确顺序见
[backup and restore](backup-and-restore.md#running-cli-commands-in-docker)。
这个拒绝是刻意设计的：正是它防止两个进程同时写你的手稿数据库。

## I can't find my novels on disk

它们不在应用文件夹里——它们在 Docker volume `novel-engine-data` 里（见
[where your data lives](backup-and-restore.md#where-your-data-physically-lives)）。
用这条命令确认它存在：

```bash
docker volume inspect novel-engine-data
```

命令有输出，你的手稿就在那里。`docker compose down`（千万别 `down -v`）
是安全的；volume 会留下来。

## The first start takes forever

只此一次，属正常现象：应用镜像在第一次启动时要从源码构建，耗时几分钟不
等，取决于机器和网络。之后的启动复用镜像，几秒即开；一次版本
[升级](upgrading.md)会重建，于是又慢这一次。

## The container restarts endlessly with a secret error

**症状：** 容器永远起不来，
`docker compose logs novel-engine` 反复出现
`entrypoint: /app/data/.secret is empty; remove it or set SECURITY_SECRET_KEY`。

数据 volume 里自动生成的会话密钥存在但内容为空（可能 volume 被不完整地
恢复过）。要么删掉这个坏文件，让下次启动生成一个新的：

```bash
docker compose stop novel-engine
docker run --rm -v novel-engine-data:/data alpine rm /data/.secret
docker compose up -d
```

要么在 `.env`（或 `compose.override.yaml`）里把 `SECURITY_SECRET_KEY` 设
成一个足够长的随机值，然后运行 `docker compose up -d`。一个相关的拒绝：
显式设置但长度不足的密钥会在启动时被拒绝，报
`SECURITY_SECRET_KEY must be at least 16 characters long`——换一个更长的
值。（设置密钥视为一次主动登出：重启后请重新登录。）

## Before you ask for help: export diagnostics

如果以上都没解决、你准备求助，先去项目的**设置**区块：**导出诊断信息**会
在你的电脑上保存一个 JSON 文件，其中包含版本、运行环境、配置状态、近期错
误摘要与数据库健康状态——不含你写的任何内容，也不含 API key。Novel Engine
绝不会把这个文件发送到任何地方；是否分享由你自行决定。

## Anything else

1. `docker compose logs novel-engine` —— 服务器日志会指出是哪个组件在失
   败。
2. `http://localhost:8000/health/ready` —— 服务器能连上自己的数据库时，
   这里会返回 JSON。
3. `doctor` 命令以 JSON 报告版本、数据库完整性和账户状态；它需要先停掉
   工作室
   （[顺序见此](backup-and-restore.md#running-cli-commands-in-docker)）。
4. 求助时附上诊断导出——见
   [export diagnostics before asking for
   help](#before-you-ask-for-help-export-diagnostics)。
