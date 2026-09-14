# Getting started (Docker)

本指南带你从零开始，用 Docker Desktop 写出第一个有 AI 参与的章节。它是为
作者写的，不是为系统管理员写的：每一步都发生在你自己的电脑上，每一步都可
以撤销。

先说一件最重要的事：Novel Engine 是**自托管**的。你的稿子就是你机器上的
一个数据库文件——不是别人云服务器里的几行数据。没有任何外部服务器存储、
读取或掌控你的写作，也不需要任何订阅。你随时可以备份或导出作品，带着它
离开。

## What you need

- **Docker Desktop**（Windows、macOS 或 Linux），已安装并正在运行。下载地址：
  `https://www.docker.com/products/docker-desktop/`。
- 浏览器用 **Chrome 或 Firefox**，两者都完全支持。Safari 能打开工作室，但
  在磨砂玻璃视觉风格下有一个已知的渲染缺陷，不建议使用。
- 预留大约 10 分钟做首次启动。第一次启动要构建应用镜像，可能需要几分钟；
  之后的每次启动都很快。

## Step 1: Get the code

两种方式任选其一：

- 装有 Git 的话，直接**克隆**仓库：

  ```bash
  git clone https://github.com/Jackela/Novel-Engine.git
  cd Novel-Engine
  ```

- 没有 Git 就**下载**：在仓库的 GitHub 页面上点绿色的 **Code** 按钮，再点
  **Download ZIP**，然后解压。在解压出来的文件夹里打开一个终端——就是那
  个装着 `compose.yaml` 的文件夹。

## Step 2: Start the studio

在包含 `compose.yaml` 的文件夹里运行：

```bash
docker compose up -d
```

第一次运行会构建应用镜像，可能需要几分钟。等命令提示符回来，工作室就已
经作为一个后台服务在运行了——崩溃或重启电脑之后，Docker 会自动把它拉起来
（除非是你自己停掉的）。

想看启动进度，运行 `docker compose logs -f novel-engine`；按 Ctrl+C 停止
查看（这不会停掉工作室）。

## Step 3: Open the studio and create your account

在 Chrome 或 Firefox 里打开 `http://localhost:8000`。第一屏是初始化页面：
选一个用户名和密码，创建本地的**所有者（Owner）**账户，然后登录。所有者
账户有且只有一个——Novel Engine 是单人工作室，这个账户只存在于你的电脑
上。

如果页面打不开，见
[troubleshooting](troubleshooting.md#the-studio-does-not-open-on-localhost8000)。

## Step 4: Write your first chapter with AI help

工作室自带一个内置的**试用 provider**（`mock`）：不需要任何 API key 就能
写出真实、确定的文字，所以你可以在向任何人付费之前，先试用每一个功能。

1. 在项目列表页的**新建项目**下输入一个书名，按**创建项目**。
2. 在左侧导航里，点 **Manuscript** 旁边的 **Add** 新建一章，在编辑器里打
   几句话。文字会自动保存。
3. 在右侧的 **Copilot** 面板里输入一句指令，比如
   "Continue this scene with a quieter, more ominous tone"，然后按
   **Continue**。一段提案会以流式预览的形式出现。
4. 按 **Accept** 应用到手稿，或按 **Reject** 丢弃。在你按下 Accept 之前，
   Copilot 绝不会改动你的文字。

编辑器的完整导览见 [writing guide](writing-guide.md)。

## Where your data lives

你写的一切——项目、章节、修订、设置——都存在你机器上一个名为
`novel-engine-data` 的 Docker **named volume** 里的一个 SQLite 文件中。
停止或升级工作室都不会碰它；只有显式执行 `docker compose down -v` 才会删
掉它（别这么做）。要把作品从容器里复制出来，见
[backup and restore](backup-and-restore.md)。

## Day-to-day: stopping and starting

```bash
docker compose stop      # stop the studio (data is kept)
docker compose up -d     # start it again
```

`stop` 之后，在同一个文件夹里再跑一次 `docker compose up -d` 就能把工作
室带回来。你的手稿和登录状态在重启之后都还在。

## Next steps

- [Provider setup](provider-setup.md)：当试用 provider 不够用时，接一个真
  正的 AI 服务，比如 DashScope 或 DeepSeek。
- [Writing guide](writing-guide.md)：完整的写作流程，包括整本书生成。
- [Exporting](exporting.md)：把项目变成 Markdown、DOCX 或 EPUB。
- [FAQ](faq.md)：常见问题的简短回答。
