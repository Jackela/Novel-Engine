# FAQ

自托管作者最常问的问题，给最短的回答。更深入的页面：
[getting started](getting-started.md)、
[provider setup](provider-setup.md)、
[writing guide](writing-guide.md)、
[backup and restore](backup-and-restore.md)。

## Where are my manuscripts stored?

在你机器上的一个 SQLite 文件里，位于 Docker volume `novel-engine-data`
之中。没有任何东西存在外部服务器上。你可以复制这个文件、备份它，或者把
项目导出成 Markdown/DOCX/EPUB，把写作带到任何地方——见
[backup and restore](backup-and-restore.md#where-your-data-physically-lives)。

## Can I change the AI model?

可以。provider 及其模型通过环境变量设置，并在设置里按项目选择。支持
DashScope（通义千问模型）和任何 OpenAI 兼容接口（DeepSeek、OpenAI 等）；
精确的变量见 [provider setup](provider-setup.md)。每个项目可以用不同的
provider。

## Does it work offline?

可以，用内置的试用 provider（`mock`）：它不需要 key，也不需要联网，所有
功能都能用它跑通。真实的 provider（DashScope、DeepSeek 等）需要联网，因
为它们本来就是外部服务。

## Do I need an API key? What does it cost?

试用不需要：试用 provider 免费且功能完整。要用真实模型生成，你需要那个
服务商的 key，服务商按用量计费（对整本小说级别的实验通常花销很小；盯住
工作室的**用量**标签页）。

## Who can read my drafts?

只有你。工作室在你的机器上运行，只有一个所有者账户，不向任何地方汇报。
唯一的例外是 AI 生成所固有的：你随生成请求发出的文字，会按该服务商的条
款传到你配置的那个 AI 服务商那里。用试用 provider 时，什么都不会离开你
的机器。

## How do I move my writing to a new computer?

备份、复制备份文件、恢复：[backup and restore](backup-and-restore.md)。
在新电脑上装好 Docker Desktop 和 Novel Engine，然后在那里恢复备份——项
目、章节和历史装在同一个文件里一起过来。

## I stopped the container / restarted my computer — is my writing safe?

安全。你打字的同时手稿就在写入数据库（自动保存），数据 volume 在停止、
崩溃、重启和升级之后都留存。容器被配置为自动回来（
`restart: unless-stopped`）；在你主动 `docker compose stop` 之后，用
`docker compose up -d` 再次启动。

## Can several people write together?

不能。Novel Engine 刻意做成只有一个所有者账户的单人工作室。要加第二位作
者，请在另一台机器或另一个端口上跑第二个实例——各自拥有自己的数据
volume。
