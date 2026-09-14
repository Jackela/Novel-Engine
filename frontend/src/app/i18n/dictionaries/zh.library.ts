import type { enLibrary } from "./en.library";

/** Chinese counterpart of `en.library.ts`; keys must match it exactly. */
export const zhLibrary = {
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
} satisfies Record<keyof typeof enLibrary, string>;
