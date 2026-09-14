# Writing guide

本页按你写作时会遇到的样子走一遍工作室：项目列表、编辑器及其侧栏、
Copilot 提案、整本书生成、设定、评审和历史。它解释每个界面能为作为作者
的你做什么——不是一份功能清单。

## The project library

登录之后你落在项目列表页。每一部小说是一个**项目**：在**新建项目**下输
入书名创建。列表会展示你的项目；点开一个就能进入，右上角的控制可以退出
登录。项目标题和它使用的 AI provider 之后在项目的**设置**区块里修改。

## The workspace at a glance

打开一个项目，看到的是写作工作台：

- **左侧导航**在各个区块之间切换（Manuscript、Outline、Characters、
  World、Notes），可以搜索项目；在手稿界面上，它还承载整本书生成器和按
  分卷归组的章节列表。
- **中间编辑器**是一个自动保存的 Markdown 编辑器。标题附近的状态指示器
  显示保存状态；你停止打字片刻后，文字就会被存下来。
- **右侧 Inspector** 是工具标签页：**Copilot**、**Review**、**History**、
  **Export**、**Jobs** 和 **Usage**。选中的标签页跟随页面地址，所以你可以
  随时收藏或刷新而不丢位置。

项目标题和它使用的 provider 在**设置**区块里修改。

## Sections: what lives where

用导航里每组旁边的 **Add** 按钮创建内容：

| 分组 | 用它来放 |
|---|---|
| **Manuscript** | 章节——书本身，按阅读顺序。 |
| **Outline** | 节拍文档：场景速写、你据以写作的结构笔记。 |
| **Characters** | 人物卡：他是谁、他怎么说话。 |
| **World** | 地点、魔法体系、阵营、历史——关于这个世界为真的一切。 |
| **Notes** | 其他任何东西：调研碎片、TODO、名字点子。 |

章节和大纲文档可以用每行上的 **Move** 按钮重新排序。章节还可以用行上的
**Move to volume…** 选择器归入分卷；导航会把章节按每卷一个标题、按阅读
顺序归组（只有两级：项目，然后是卷）。

每一章可以关联一个大纲节拍：打开章节，在 Copilot 标签页里的节拍控件中输
入大纲文档的标题，或者清除关联。这样章节就带着自己的写作计划，正文和大
纲始终保持联系。

## Copilot: propose, then accept

Copilot 是 Inspector 里的起草助手。规则很简单：**在你接受一份提案之前，
Copilot 绝不会改动手稿。**

1. 点进指令框，说你想要什么，例如 "Continue this scene with a quieter,
   more ominous tone"。
2. 按 **Continue** 续写本章，或按 **Rewrite** 从头重写。提案会以流式预览
   的形式出现——此时什么都没有被应用。
3. **Accept** 把提案应用到手稿（并创建一条你可以回退的历史修订），
   **Reject** 把它丢掉。提案流式传输时你可以 **Stop**；被停掉的提案不留
   任何痕迹。

Copilot 起草时能看到你的章节、大纲以及相关的人物卡和世界设定——如何控
制它知道什么，见下文
[lore](#lore-your-characters-and-world-feed-the-ai)。

## The whole-book generator

章节列表下方是整本书控制。按下 **Generate whole book** 会严格按阅读顺序
起草并自动接受每一个还没有被接受的 AI 修订的章节——每一章都是在读过前面
章节之后写的，所以全书连贯地生长。进度显示 "Generating chapter 3 of
12…"，**Stop generating** 会在当前这一章写完后停下；已经接受的章节原样
保留。之后再启动，它会从第一处还缺被接受修订的章节继续。

整本生成会逐章消耗 provider 的 token；如果你的套餐按量计费，请盯着
**Usage** 标签页。

## Lore: your characters and world feed the AI

没有一套需要单独维护的 lore 系统——你的 **Characters** 和 **World** 文档
*就是* lore。当 Copilot 起草一章时，标题或别名出现在正文中的条目会被注
入提示词，AI 因此能记住名字、性格和世界细节。

两个控制点很重要：

- **标题**：条目的标题就是它的触发键，所以人物卡和世界设定的标题要与正
  文中的叫法一字不差（写 "Yan Shuang"，不要写 "我的主角"）。
- **生命周期状态**：每个条目是 `draft`、`stable` 或 `deprecated`。只有
  **stable** 且非空的条目才会给 AI 看。新条目从 draft 开始；等你信得过
  它了再切成 stable。状态控件在条目打开时位于 Copilot 标签页下。

标题之外的触发名（别名）底层 API 支持，但工作室里还没有界面；今天可靠的
路径是标题。

如果 AI 老是和你的设定打架，原因多半是一张内容太薄或还处于 draft 状态的
世界设定：把它填满，标成 stable。

## Review: a second pair of eyes

右侧 Inspector 的 **Review** 标签页对当前手稿跑一次 AI 评审。按
**Run review**；发现的问题会按严重程度分组返回——连贯性瑕疵、节奏建议、
与你的设定冲突之处——并且以与手稿状态绑定的快照保存，所以改过文字之后，
过去的评审依然可读。评审与生成使用同一个 provider（DashScope 可以用专门
的评审模型，见 [provider setup](provider-setup.md#dashscope)）。

## History: every version is kept

**History** 标签页列出当前打开文档的修订链。保存、被接受的提案、恢复操作
都会产生修订——没有任何东西会被覆盖。**Restore** 会把旧版本作为*一条新*
修订带回来，所以恢复本身也是可撤销的。把它当作大改时的安全网：先接受
Copilot 那个大胆的版本，写过火了再对照历史回退。

## Jobs, usage, and search

- **Jobs** 显示后台工作——生成任务、导出、重试——及其状态，失败的任务可
  以一键重试。
- **Usage** 按模型汇总项目消耗的 token，带一个滚动 30 天窗口，按量计费的
  套餐不会有意外。
- **Search**（导航顶部）在项目的全部文档里找文字，直接跳到命中处。

## When the editor disagrees with the server

如果你开了两个标签页同时编辑，或者一次保存发生冲突，工作室绝不悄悄丢字：
它会给你 **Load latest**（采用服务器版本，放弃本地）或 **Keep local and
retry**（把你的文字叠在最新修订之上重新提交）两个选择。你的文字，是工作
室最不愿意丢的东西。
