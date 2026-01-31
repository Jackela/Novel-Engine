/**
 * EditorComponent - Tiptap-based rich text editor for narrative writing.
 *
 * Why: Provides a WYSIWYG editing experience for story content, with a
 * toolbar for common formatting operations and shadcn/ui styling for
 * consistent design system integration.
 */
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { Bold, Italic, Heading1, Heading2 } from 'lucide-react';

import { cn } from '@/lib/utils';
import { Toggle } from '@/components/ui/toggle';
import { Separator } from '@/components/ui/separator';

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
 * EditorToolbar - Formatting toolbar for the Tiptap editor.
 *
 * Why: Provides accessible formatting controls using shadcn Toggle
 * components that sync with editor state for visual feedback.
 */
function EditorToolbar({
  editor,
}: {
  editor: ReturnType<typeof useEditor>;
}) {
  if (!editor) {
    return null;
  }

  return (
    <div
      className="flex items-center gap-1 border-b border-border bg-muted/50 px-2 py-1.5"
      role="toolbar"
      aria-label="Text formatting"
      data-testid="editor-toolbar"
    >
      {/* Bold toggle */}
      <Toggle
        size="sm"
        pressed={editor.isActive('bold')}
        onPressedChange={() => editor.chain().focus().toggleBold().run()}
        aria-label="Bold"
        data-testid="toolbar-bold"
      >
        <Bold className="h-4 w-4" />
      </Toggle>

      {/* Italic toggle */}
      <Toggle
        size="sm"
        pressed={editor.isActive('italic')}
        onPressedChange={() => editor.chain().focus().toggleItalic().run()}
        aria-label="Italic"
        data-testid="toolbar-italic"
      >
        <Italic className="h-4 w-4" />
      </Toggle>

      <Separator orientation="vertical" className="mx-1 h-6" />

      {/* Heading 1 toggle */}
      <Toggle
        size="sm"
        pressed={editor.isActive('heading', { level: 1 })}
        onPressedChange={() =>
          editor.chain().focus().toggleHeading({ level: 1 }).run()
        }
        aria-label="Heading 1"
        data-testid="toolbar-h1"
      >
        <Heading1 className="h-4 w-4" />
      </Toggle>

      {/* Heading 2 toggle */}
      <Toggle
        size="sm"
        pressed={editor.isActive('heading', { level: 2 })}
        onPressedChange={() =>
          editor.chain().focus().toggleHeading({ level: 2 }).run()
        }
        aria-label="Heading 2"
        data-testid="toolbar-h2"
      >
        <Heading2 className="h-4 w-4" />
      </Toggle>
    </div>
  );
}

/**
 * A Tiptap editor component with formatting toolbar for narrative writing.
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
    editorProps: {
      attributes: {
        class:
          'prose prose-sm dark:prose-invert max-w-none focus:outline-none min-h-[200px]',
      },
    },
  });

  return (
    <div
      className={cn(
        'flex flex-col overflow-hidden rounded-md border border-input bg-background',
        'focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2',
        className
      )}
      data-testid="narrative-editor"
    >
      {/* Toolbar */}
      <EditorToolbar editor={editor} />

      {/* Editor content */}
      <div className="flex-1 overflow-auto p-4">
        <EditorContent editor={editor} />
      </div>
    </div>
  );
}

export default EditorComponent;
