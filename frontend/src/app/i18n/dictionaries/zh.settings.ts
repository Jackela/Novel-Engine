import type { enSettings } from "./en.settings";

/** Chinese counterpart of `en.settings.ts`; keys must match it exactly. */
export const zhSettings = {
  "settings.heading": "项目设置",
  "settings.error.unableToUpdate": "无法更新项目。",
  "settings.field.provider": "生成服务",
  "settings.field.storage": "存储",
  "settings.field.documentSyntax": "文档语法",
  "settings.value.sqlite": "SQLite",
  "settings.value.markdown": "Markdown",
  "settings.action.save": "保存设置",
  "settings.action.saving": "正在保存…",
  "settings.status.saving": "正在保存项目设置。",

  "shell.action.backToProjects": "返回项目列表",
} satisfies Record<keyof typeof enSettings, string>;
