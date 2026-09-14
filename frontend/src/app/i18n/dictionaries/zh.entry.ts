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
  "entry.field.username": "用户名",
  "entry.field.password": "密码",
  "entry.action.signIn": "登录",
  "entry.action.signingIn": "正在登录...",
  "entry.action.createOwner": "创建所有者",
  "entry.action.creatingOwner": "正在创建所有者...",
  "entry.status.checkingSession": "正在检查你的会话...",
  "entry.error.unableToContinue": "无法继续。",
  "entry.error.unableToCheckOwner": "无法检查本地所有者。",
} satisfies Record<keyof typeof enEntry, string>;
