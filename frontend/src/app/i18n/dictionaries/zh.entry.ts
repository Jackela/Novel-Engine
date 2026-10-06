import type { enEntry } from "./en.entry";

/** Chinese counterpart of `en.entry.ts`; keys must match it exactly. */
export const zhEntry = {
  "entry.heading.signedIn": "打开你的写作工作室",
  "entry.heading.createOwner": "创建本地所有者",
  "entry.heading.unavailable": "无法打开你的写作工作室",
  "entry.heading.loading": "正在打开你的写作工作室",
  "entry.intro.selfHosted": "你的项目、Markdown 修订、评审与导出都保存在这个自托管实例中。",
  "entry.intro.trialProvider":
    "没有 API key？生成会先跑在内置的试用 provider 上 — 准备就绪后，随时可以在项目的设置里接入正式 provider。",
  "entry.notice.sessionExpired": "会话已过期，请重新登录以回到之前的位置。",
  "entry.field.username": "用户名",
  "entry.field.password": "密码",
  "entry.field.confirmPassword": "确认密码",
  "entry.field.setupToken": "首启 setup token",
  "entry.hint.setupToken":
    "可选 — 仅 Docker 等非 loopback 地址的首启需要：请把服务器日志里的（或数据目录下 .setup-token 文件中的）一次性 token 粘贴到此处；loopback 首启留空即可。",
  "entry.hint.noRecovery":
    "本工具出于设计不提供邮箱找回。请务必保存好这个密码：一旦遗忘，请先停止服务器，再运行 novel-engine owner reset 重新创建所有者。书稿内容不会受影响。",
  "entry.action.signIn": "登录",
  "entry.action.signingIn": "正在登录...",
  "entry.action.createOwner": "创建所有者",
  "entry.action.creatingOwner": "正在创建所有者...",
  "entry.status.checkingSession": "正在检查你的会话...",
  "entry.error.unableToContinue": "无法继续。",
  "entry.error.unableToCheckOwner": "无法检查本地所有者。",
  "entry.error.passwordMismatch": "两次输入的密码不一致。",
  "entry.error.invalidCredentials": "用户名或密码不正确。",
  "entry.error.setupTokenInvalid":
    "这次首启来自非 loopback 地址，需要一次性 setup token：请从服务器日志（或数据目录下的 .setup-token 文件）中读取并填入上方输入框。loopback 首启无需 token。",
} satisfies Record<keyof typeof enEntry, string>;
