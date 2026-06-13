import { useEffect, useRef } from 'react';
import { markdown } from '@codemirror/lang-markdown';
import { EditorState } from '@codemirror/state';
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
            '.cm-selectionBackground': { backgroundColor: '#ccfbf1 !important' },
          }),
        ],
      }),
    });
    view.current = nextView;
    return () => nextView.destroy();
  }, []);

  useEffect(() => {
    const editor = view.current;
    if (!editor || editor.state.doc.toString() === value) return;
    editor.dispatch({
      changes: { from: 0, to: editor.state.doc.length, insert: value },
    });
  }, [value]);

  return <div className="markdown-editor" ref={parent} />;
}
