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

  "settings.diagnostics.privacy":
    "诊断信息包含版本、运行环境、配置状态、近期错误摘要与数据库健康状态——不含你写的任何内容，也不含 API key。它只会以文件形式保存在你的电脑上；Novel Engine 绝不会将它发送到任何地方。是否分享由你自行决定。",
  "settings.diagnostics.action.export": "导出诊断信息",
  "settings.diagnostics.action.exporting": "正在导出…",
  "settings.diagnostics.status.exporting": "正在导出诊断信息。",

  "shell.action.backToProjects": "返回项目列表",
} satisfies Record<keyof typeof enSettings, string>;
