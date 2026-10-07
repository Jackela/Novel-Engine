/**
 * CodeMirror theme spec for the markdown writing surface.
 * Colors resolve from base.css tokens (ADR-0009) — CodeMirror's
 * own light/dark base themes cannot see them — while the content
 * width and centering live in styles/editor.css (SSOT).
 */
export function markdownEditorTheme() {
  return {
    "&": { height: "100%", backgroundColor: "var(--surface)" },
    ".cm-scroller": {
      fontFamily: 'ui-serif, Georgia, Cambria, "Times New Roman", Times, serif',
      fontSize: "19px",
      lineHeight: "1.8",
      padding: "clamp(24px, 4vw, 34px) clamp(20px, 6vw, 54px) 80px",
    },
    /* content width + centering live in styles/editor.css (SSOT) */
    ".cm-content": {
      caretColor: "var(--teal-strong)",
    },
    "&.cm-focused": {
      outline: "3px solid var(--teal-strong)",
      outlineOffset: "-3px",
    },
    ".cm-gutters": { display: "none" },
    ".cm-activeLine": { backgroundColor: "transparent" },
    /* The search panel follows the shell tokens, including dark
       mode (CM's own light/dark base theme cannot see our tokens). */
    ".cm-panel.cm-search": {
      backgroundColor: "var(--surface-muted)",
      borderBottom: "1px solid var(--line)",
      color: "var(--ink)",
    },
    ".cm-panel.cm-search input": {
      backgroundColor: "var(--surface)",
      border: "1px solid var(--line)",
      borderRadius: "4px",
      color: "var(--ink)",
    },
    ".cm-panel.cm-search button": {
      backgroundColor: "var(--surface-glass-strong)",
      border: "1px solid var(--glass-border)",
      borderRadius: "4px",
      color: "var(--ink-soft)",
    },
    "&.cm-focused > .cm-scroller > .cm-selectionLayer .cm-selectionBackground": {
      backgroundColor: "var(--focus-ring)",
    },
  };
}
