import { Bold, Heading1, Italic } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { translateActive } from "@/app/i18n/translate";
import { useTranslation } from "@/app/i18n/useTranslation";

import {
  type MarkdownCommandRuntime,
  type MarkdownFormatCommand,
  runMarkdownFormat,
} from "./runMarkdownFormat";

interface MarkdownEditorProps {
  value: string;
  onChange: (value: string) => void;
}

interface CodeMirrorRuntime extends MarkdownCommandRuntime {
  readonly Transaction: typeof import("@codemirror/state").Transaction;
  readonly EditorState: typeof import("@codemirror/state").EditorState;
  /** Reconfigures the search-panel phrases when the language switches. */
  readonly phrases: import("@codemirror/state").Compartment;
}

const FORMAT_BUTTONS = [
  { command: "bold", Icon: Bold, labelKey: "editor.format.bold" },
  { command: "italic", Icon: Italic, labelKey: "editor.format.italic" },
  { command: "heading", Icon: Heading1, labelKey: "editor.format.heading" },
] as const;

/** Search-panel labels for the active language (CodeMirror phrase keys). */
function searchPhrases(): Record<string, string> {
  return {
    Find: translateActive("editor.search.find"),
    Replace: translateActive("editor.search.replace"),
    next: translateActive("editor.search.next"),
    previous: translateActive("editor.search.previous"),
    all: translateActive("editor.search.all"),
    "match case": translateActive("editor.search.matchCase"),
    regexp: translateActive("editor.search.regexp"),
    "by word": translateActive("editor.search.byWord"),
    replace: translateActive("editor.search.replaceAction"),
    "replace all": translateActive("editor.search.replaceAll"),
    close: translateActive("editor.search.close"),
  };
}

export function MarkdownEditor({ value, onChange }: MarkdownEditorProps) {
  const { t } = useTranslation();
  const parent = useRef<HTMLDivElement>(null);
  const view = useRef<import("@codemirror/view").EditorView | null>(null);
  const runtime = useRef<CodeMirrorRuntime | null>(null);
  const latestValueRef = useRef(value);
  const onChangeRef = useRef(onChange);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    onChangeRef.current = onChange;
  }, [onChange]);

  useEffect(() => {
    latestValueRef.current = value;
  }, [value]);

  useEffect(() => {
    let mountedView: import("@codemirror/view").EditorView | null = null;
    let cancelled = false;

    const promise = Promise.all([
      import("@codemirror/lang-markdown"),
      import("@codemirror/state"),
      import("@codemirror/view"),
      import("@codemirror/commands"),
      import("@codemirror/search"),
    ]).then(([language, state, editorView, commands, search]) => {
      if (cancelled || !parent.current) return;
      const commandRuntime: MarkdownCommandRuntime = { EditorSelection: state.EditorSelection };
      const phrases = new state.Compartment();
      // Ctrl+H opens the same panel focused on its replace field.
      const openReplacePanel = (target: import("@codemirror/view").EditorView): boolean => {
        const opened = search.openSearchPanel(target);
        queueMicrotask(() =>
          target.dom.querySelector<HTMLInputElement>('input[name="replace"]')?.focus(),
        );
        return opened;
      };
      const nextView = new editorView.EditorView({
        parent: parent.current,
        state: state.EditorState.create({
          doc: latestValueRef.current,
          extensions: [
            commands.history(),
            editorView.keymap.of([
              ...search.searchKeymap,
              { key: "Mod-h", run: openReplacePanel },
              { key: "Ctrl-h", run: openReplacePanel },
              { key: "Mod-b", run: (target) => runMarkdownFormat(target, "bold", commandRuntime) },
              {
                key: "Mod-i",
                run: (target) => runMarkdownFormat(target, "italic", commandRuntime),
              },
              ...commands.defaultKeymap,
              ...commands.historyKeymap,
            ]),
            search.search({ top: true }),
            phrases.of(state.EditorState.phrases.of(searchPhrases())),
            language.markdown(),
            editorView.EditorView.lineWrapping,
            editorView.EditorView.contentAttributes.of({
              "aria-label": translateActive("editor.field.markdownEditor"),
              "aria-multiline": "true",
            }),
            editorView.EditorView.updateListener.of((update) => {
              if (update.docChanged) onChangeRef.current(update.state.doc.toString());
            }),
            editorView.EditorView.theme({
              /* colors resolve from base.css tokens (ADR-0009) */
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
            }),
          ],
        }),
      });
      mountedView = nextView;
      runtime.current = {
        EditorSelection: state.EditorSelection,
        Transaction: state.Transaction,
        EditorState: state.EditorState,
        phrases,
      };
      view.current = nextView;
    });

    // Surface loader failures instead of leaving the editor silently unset;
    // the error stays visible through the component's failed state.
    promise.catch((error: unknown) => {
      if (cancelled) return;
      setFailed(true);
      console.error("Markdown editor failed to load", error);
    });

    return () => {
      cancelled = true;
      mountedView?.destroy();
      if (view.current === mountedView) view.current = null;
    };
  }, []);

  useEffect(() => {
    const editor = view.current;
    const codeMirror = runtime.current;
    if (!editor || !codeMirror || editor.state.doc.toString() === value) return;

    const currentSelection = editor.state.selection;
    const newLength = value.length;
    const ranges = currentSelection.ranges.map((range) => {
      const from = Math.min(range.from, newLength);
      const to = Math.min(range.to, newLength);
      return codeMirror.EditorSelection.range(from, to);
    });

    editor.dispatch({
      changes: { from: 0, to: editor.state.doc.length, insert: value },
      selection: codeMirror.EditorSelection.create(ranges, currentSelection.mainIndex),
      annotations: codeMirror.Transaction.addToHistory.of(false),
    });
  }, [value]);

  // The CodeMirror view is created once, so a language switch cannot flow
  // through re-created extensions or content attributes; sync both directly.
  useEffect(() => {
    const editor = view.current;
    const codeMirror = runtime.current;
    if (editor && codeMirror) {
      editor.dispatch({
        effects: codeMirror.phrases.reconfigure(codeMirror.EditorState.phrases.of(searchPhrases())),
      });
    }
    const content = parent.current?.querySelector(".cm-content");
    if (content) content.setAttribute("aria-label", t("editor.field.markdownEditor"));
  }, [t]);

  /** Runs one format command over the current selection and keeps focus. */
  const formatCommand = (command: MarkdownFormatCommand) => {
    const editor = view.current;
    const codeMirror = runtime.current;
    if (!editor || !codeMirror) return;
    runMarkdownFormat(editor, command, codeMirror);
    editor.focus();
  };

  return (
    <>
      <div aria-label={t("editor.format.toolbar")} className="editor__format" role="toolbar">
        {FORMAT_BUTTONS.map(({ command, Icon, labelKey }) => (
          <button
            aria-label={t(labelKey)}
            className="ui-command ui-command--icon"
            disabled={failed}
            key={command}
            onClick={() => formatCommand(command)}
            type="button"
          >
            <Icon aria-hidden="true" />
          </button>
        ))}
      </div>
      <div className="editor__markdown" ref={parent}>
        {failed ? <p className="ui-form-error">{t("editor.error.markdownFailed")}</p> : null}
      </div>
    </>
  );
}
