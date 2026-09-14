import type { enShared } from "./en.shared";

/** Chinese counterpart of `en.shared.ts`; keys must match it exactly. */
export const zhShared = {
  "common.action.tryAgain": "重试",
  "common.action.tryingAgain": "正在重试...",
  "common.action.saving": "正在保存…",
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

  "provider.mock": "Mock（试用 — 无需 API key）",
  "provider.dashscope": "DashScope",
  "provider.openaiCompatible": "OpenAI 兼容",

  "noun.chapter": "章",
  "noun.chapters": "章",
  "noun.finding": "条发现",
  "noun.findings": "条发现",
  "noun.word": "字",
  "noun.words": "字",
} satisfies Record<keyof typeof enShared, string>;
