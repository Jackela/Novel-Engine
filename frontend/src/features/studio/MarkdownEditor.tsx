import { Bold, Heading1, Italic } from "lucide-react";
import { useEffect, useRef } from "react";

import { useTranslation } from "@/app/i18n/useTranslation";

import { searchPhrases, useCodeMirrorEditor } from "./hooks/useCodeMirrorEditor";
import { type MarkdownFormatCommand, runMarkdownFormat } from "./runMarkdownFormat";

interface MarkdownEditorProps {
  value: string;
  onChange: (value: string) => void;
  /** DR-029: locate one search hit (term + monotonic token) in the body. */
  reveal?: { readonly term: string; readonly token: number } | null;
}

const FORMAT_BUTTONS = [
  { command: "bold", Icon: Bold, labelKey: "editor.format.bold" },
  { command: "italic", Icon: Italic, labelKey: "editor.format.italic" },
  { command: "heading", Icon: Heading1, labelKey: "editor.format.heading" },
] as const;

export function MarkdownEditor({ value, onChange, reveal = null }: MarkdownEditorProps) {
  const { t } = useTranslation();
  const { failed, parent, ready, runtime, view } = useCodeMirrorEditor(value, onChange);
  /** The last consumed reveal token; repeated clicks mint fresh tokens (DR-029). */
  const handledRevealRef = useRef(0);

  // DR-029: a clicked search result arrives as a locate intent; after the
  // target body loads, pre-fill the editor's find query and jump to the first
  // match. The guard reads the controlled body (`value`) so the intent is
  // re-checked when the target body arrives, the token guard keeps one reveal
  // from re-running on every keystroke, and a term that never appears in the
  // body (a title-only hit) leaves the selection alone instead of fabricating
  // a jump.
  useEffect(() => {
    const editor = view.current;
    const codeMirror = runtime.current;
    if (!ready || editor === null || codeMirror === null || reveal === null) return;
    if (handledRevealRef.current === reveal.token) return;
    if (!value.toLowerCase().includes(reveal.term.toLowerCase())) return;
    handledRevealRef.current = reveal.token;
    editor.dispatch({
      effects: codeMirror.search.setSearchQuery.of(
        new codeMirror.search.SearchQuery({ search: reveal.term }),
      ),
    });
    codeMirror.search.findNext(editor);
    // The view and runtime refs are stable, so listing them keeps the
    // effect honest without ever re-running it.
  }, [reveal, ready, value, runtime, view]);

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
    // Stable refs again: listed for the linter, inert for timing.
  }, [t, parent, runtime, view]);

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
