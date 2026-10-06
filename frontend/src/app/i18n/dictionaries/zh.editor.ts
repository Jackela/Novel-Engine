import type { enEditor } from "./en.editor";

/** Chinese counterpart of `en.editor.ts`; keys must match it exactly. */
export const zhEditor = {
  "editor.format.toolbar": "格式",
  "editor.format.bold": "加粗",
  "editor.format.italic": "斜体",
  "editor.format.heading": "标题",
  "editor.search.find": "查找",
  "editor.search.replace": "替换",
  "editor.search.next": "下一个",
  "editor.search.previous": "上一个",
  "editor.search.all": "全部",
  "editor.search.matchCase": "区分大小写",
  "editor.search.regexp": "正则表达式",
  "editor.search.byWord": "全词匹配",
  "editor.search.replaceAction": "替换",
  "editor.search.replaceAll": "全部替换",
  "editor.search.close": "关闭",
} satisfies Record<keyof typeof enEditor, string>;
