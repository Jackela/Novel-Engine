import type { Dictionary } from "./en";

/**
 * Simplified-Chinese dictionary. The `Dictionary` annotation makes a
 * missing or misspelled key a compile error, so `zh` can never silently
 * drift from the English key set. Proper nouns the product already treats
 * as opaque (Markdown, SQLite, DashScope, API key) keep their Latin form.
 */
export const zh: Dictionary = {
  "common.action.tryAgain": "重试",
  "common.action.tryingAgain": "正在重试...",
  "common.field.title": "标题",
  "common.field.description": "描述",

  "theme.legend": "主题",
  "theme.option.system": "跟随系统",
  "theme.option.systemLight": "跟随系统（浅色）",
  "theme.option.systemDark": "跟随系统（深色）",
  "theme.option.light": "浅色",
  "theme.option.dark": "深色",

  "language.legend": "语言",
  "language.option.en": "English",
  "language.option.zh": "中文",

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

  "library.action.signOut": "退出登录",
  "library.heading.projects": "项目",
  "library.intro": "打开一部手稿，或者开始一部新小说。",
  "library.create.newProject": "新建项目",
  "library.create.premise": "故事前提",
  "library.action.create": "创建项目",
  "library.action.creating": "正在创建项目...",
  "library.status.loading": "正在加载项目...",
  "library.error.unableToCreate": "无法创建项目。",
  "library.error.unableToSignOut": "无法退出登录。",
  "library.error.unableToLoad": "无法加载项目。",
  "library.error.unableToLoadOlder": "无法加载更早的项目。",
  "library.catalog.noPremise": "暂无故事前提",
  "library.catalog.end": "项目目录到此为止。",
  "library.action.loadOlder": "加载更早的项目",
  "library.action.loadingOlder": "正在加载更早的项目...",

  "settings.heading": "项目设置",
  "settings.field.provider": "生成服务",
  "settings.field.storage": "存储",
  "settings.field.documentSyntax": "文档语法",
  "settings.value.sqlite": "SQLite",
  "settings.value.markdown": "Markdown",
  "settings.action.save": "保存设置",
  "settings.action.saving": "正在保存…",
  "settings.status.saving": "正在保存项目设置。",

  "shell.action.backToProjects": "返回项目列表",

  "provider.mock": "Mock（试用 — 无需 API key）",
  "provider.dashscope": "DashScope",
  "provider.openaiCompatible": "OpenAI 兼容",
};
