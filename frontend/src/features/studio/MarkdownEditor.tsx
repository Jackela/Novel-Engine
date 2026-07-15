import { useEffect, useRef } from 'react';

interface MarkdownEditorProps {
  value: string;
  onChange: (value: string) => void;
}

interface CodeMirrorRuntime {
  readonly EditorSelection: typeof import('@codemirror/state').EditorSelection;
  readonly Transaction: typeof import('@codemirror/state').Transaction;
}

export function MarkdownEditor({ value, onChange }: MarkdownEditorProps) {
  const parent = useRef<HTMLDivElement>(null);
  const view = useRef<import('@codemirror/view').EditorView | null>(null);
  const runtime = useRef<CodeMirrorRuntime | null>(null);
  const latestValueRef = useRef(value);
  const onChangeRef = useRef(onChange);

  useEffect(() => {
    onChangeRef.current = onChange;
  }, [onChange]);

  useEffect(() => {
    latestValueRef.current = value;
  }, [value]);

  useEffect(() => {
    let mountedView: import('@codemirror/view').EditorView | null = null;
    let cancelled = false;

    void Promise.all([
      import('@codemirror/lang-markdown'),
      import('@codemirror/state'),
      import('@codemirror/view'),
      import('@codemirror/commands'),
    ]).then(([language, state, editorView, commands]) => {
      if (cancelled || !parent.current) return;
      const nextView = new editorView.EditorView({
        parent: parent.current,
        state: state.EditorState.create({
          doc: latestValueRef.current,
          extensions: [
            commands.history(),
            editorView.keymap.of([...commands.defaultKeymap, ...commands.historyKeymap]),
            language.markdown(),
            editorView.EditorView.lineWrapping,
            editorView.EditorView.contentAttributes.of({
              'aria-label': 'Markdown editor',
              'aria-multiline': 'true',
            }),
            editorView.EditorView.updateListener.of((update) => {
              if (update.docChanged) onChangeRef.current(update.state.doc.toString());
            }),
            editorView.EditorView.theme({
              '&': { height: '100%', backgroundColor: '#fff' },
              '.cm-scroller': {
                fontFamily: 'ui-serif, Georgia, Cambria, "Times New Roman", Times, serif',
                fontSize: '19px',
                lineHeight: '1.8',
                padding: 'clamp(24px, 4vw, 34px) clamp(20px, 6vw, 54px) 80px',
              },
              '.cm-content': { maxWidth: '72ch', margin: '0 auto', caretColor: '#0f766e' },
              '&.cm-focused': { outline: '3px solid #0f766e', outlineOffset: '-3px' },
              '.cm-gutters': { display: 'none' },
              '.cm-activeLine': { backgroundColor: 'transparent' },
              '&.cm-focused > .cm-scroller > .cm-selectionLayer .cm-selectionBackground': {
                backgroundColor: '#ccfbf1',
              },
            }),
          ],
        }),
      });
      mountedView = nextView;
      runtime.current = {
        EditorSelection: state.EditorSelection,
        Transaction: state.Transaction,
      };
      view.current = nextView;
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

  return <div className="markdown-editor" ref={parent} />;
}
