/**
 * EditorComponent - Tiptap-based rich text editor for narrative writing.
 *
 * Why: Provides a WYSIWYG editing experience for story content, with support
 * for streaming text insertion from LLM generation.
 */
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';

import { cn } from '@/lib/utils';

interface EditorComponentProps {
  /** Initial content for the editor (HTML string) */
  initialContent?: string;
  /** Called when editor content changes */
  onChange?: (html: string) => void;
  /** Additional CSS classes for the container */
  className?: string;
  /** Whether the editor is read-only */
  editable?: boolean;
}

/**
 * A minimal Tiptap editor component for narrative writing.
 *
 * Why: Tiptap provides a headless, extensible editor framework that
 * integrates well with React and allows programmatic content manipulation
 * needed for streaming text from LLM generation.
 */
export function EditorComponent({
  initialContent = '<p>Hello World</p>',
  onChange,
  className,
  editable = true,
}: EditorComponentProps) {
  const editor = useEditor({
    extensions: [StarterKit],
    content: initialContent,
    editable,
    onUpdate: ({ editor }) => {
      onChange?.(editor.getHTML());
    },
  });

  return (
    <div
      className={cn(
        'prose prose-sm max-w-none',
        'min-h-[200px] rounded-md border border-input bg-background p-4',
        'focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2',
        className
      )}
      data-testid="narrative-editor"
    >
      <EditorContent editor={editor} />
    </div>
  );
}

export default EditorComponent;
