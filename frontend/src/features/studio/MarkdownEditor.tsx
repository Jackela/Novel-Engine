import { useEffect, useRef } from 'react';
import { markdown } from '@codemirror/lang-markdown';
import { EditorSelection, EditorState, Transaction } from '@codemirror/state';
import { EditorView, keymap } from '@codemirror/view';
import { defaultKeymap, history, historyKeymap } from '@codemirror/commands';

interface MarkdownEditorProps {
  value: string;
  onChange: (value: string) => void;
}

export function MarkdownEditor({ value, onChange }: MarkdownEditorProps) {
  const parent = useRef<HTMLDivElement>(null);
  const view = useRef<EditorView | null>(null);
  const onChangeRef = useRef(onChange);

  useEffect(() => {
    onChangeRef.current = onChange;
  }, [onChange]);

  useEffect(() => {
    // Editor is created once per mount; subsequent external value changes are
    // applied in a separate effect below to avoid recreating the editor and
    // losing editor state (cursor, undo history).
    if (!parent.current) return;
    const nextView = new EditorView({
      parent: parent.current,
      state: EditorState.create({
        doc: value,
        extensions: [
          history(),
          keymap.of([...defaultKeymap, ...historyKeymap]),
          markdown(),
          EditorView.lineWrapping,
          EditorView.updateListener.of((update) => {
            if (update.docChanged) onChangeRef.current(update.state.doc.toString());
          }),
          EditorView.theme({
            '&': { height: '100%', backgroundColor: '#fff' },
            '.cm-scroller': {
              fontFamily: '"Source Serif 4", Georgia, serif',
              fontSize: '19px',
              lineHeight: '1.8',
              padding: '34px 54px 80px',
            },
            '.cm-content': { maxWidth: '780px', margin: '0 auto', caretColor: '#0f766e' },
            '.cm-focused': { outline: 'none' },
            '.cm-gutters': { display: 'none' },
            '.cm-activeLine': { backgroundColor: 'transparent' },
            '&.cm-focused > .cm-scroller > .cm-selectionLayer .cm-selectionBackground': {
              backgroundColor: '#ccfbf1',
            },
          }),
        ],
      }),
    });
    view.current = nextView;
    return () => nextView.destroy();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- Editor instance created once per mount; external value changes handled by the effect below.
  }, []);

  useEffect(() => {
    const editor = view.current;
    if (!editor || editor.state.doc.toString() === value) return;

    const currentSelection = editor.state.selection;
    const newLength = value.length;
    const ranges = currentSelection.ranges.map((range) => {
      const from = Math.min(range.from, newLength);
      const to = Math.min(range.to, newLength);
      return EditorSelection.range(from, to);
    });

    editor.dispatch({
      changes: { from: 0, to: editor.state.doc.length, insert: value },
      selection: EditorSelection.create(ranges, currentSelection.mainIndex),
      annotations: Transaction.addToHistory.of(false),
    });
  }, [value]);

  return (
    <div
      className="markdown-editor"
      ref={parent}
      role="textbox"
      aria-label="Markdown editor"
      aria-multiline="true"
    />
  );
}
