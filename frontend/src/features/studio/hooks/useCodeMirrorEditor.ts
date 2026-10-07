import { useEffect, useRef, useState } from "react";

import { translateActive } from "@/app/i18n/translate";

import { markdownEditorTheme } from "../markdownEditorTheme";
import { type MarkdownCommandRuntime, runMarkdownFormat } from "../runMarkdownFormat";

/** Search-panel labels for the active language (CodeMirror phrase keys). */
export function searchPhrases(): Record<string, string> {
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

interface CodeMirrorRuntime extends MarkdownCommandRuntime {
  readonly Transaction: typeof import("@codemirror/state").Transaction;
  readonly EditorState: typeof import("@codemirror/state").EditorState;
  /** Reconfigures the search-panel phrases when the language switches. */
  readonly phrases: import("@codemirror/state").Compartment;
  /** DR-029: the find-query machinery the locate intent drives. */
  readonly search: typeof import("@codemirror/search");
}

/**
 * The CodeMirror writing surface behind MarkdownEditor: the
 * lazy-loaded view (loader failures surface through `failed`
 * instead of leaving the editor silently unset), the
 * controlled-value sync that preserves the selection across
 * programmatic updates, and the refs the toolbar, the reveal
 * intent, and the language sync drive. The view is created
 * once, so a language switch cannot flow through re-created
 * extensions or content attributes; the caller syncs both
 * directly.
 */
export function useCodeMirrorEditor(value: string, onChange: (value: string) => void) {
  const parent = useRef<HTMLDivElement>(null);
  const view = useRef<import("@codemirror/view").EditorView | null>(null);
  const runtime = useRef<CodeMirrorRuntime | null>(null);
  const latestValueRef = useRef(value);
  const onChangeRef = useRef(onChange);
  const [failed, setFailed] = useState(false);
  const [ready, setReady] = useState(false);

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
            editorView.EditorView.theme(markdownEditorTheme()),
          ],
        }),
      });
      mountedView = nextView;
      runtime.current = {
        EditorSelection: state.EditorSelection,
        Transaction: state.Transaction,
        EditorState: state.EditorState,
        phrases,
        search,
      };
      view.current = nextView;
      setReady(true);
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

  return { failed, parent, ready, runtime, view };
}
