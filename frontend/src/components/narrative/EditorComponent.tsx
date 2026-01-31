/**
 * EditorComponent - Tiptap-based rich text editor for narrative writing.
 *
 * Why: Provides a WYSIWYG editing experience for story content, with a
 * toolbar for common formatting operations and shadcn/ui styling for
 * consistent design system integration. Supports streaming text insertion
 * from LLM generation via SSE.
 */
import { useEditor, EditorContent, type Editor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { Bold, Italic, Heading1, Heading2, Sparkles, Loader2, Square } from 'lucide-react';
import { useCallback, useEffect, useRef } from 'react';

import { cn } from '@/lib/utils';
import { Toggle } from '@/components/ui/toggle';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';
import { useStoryStream, type StreamRequest } from '@/hooks/useStoryStream';

interface EditorComponentProps {
  /** Initial content for the editor (HTML string) */
  initialContent?: string | undefined;
  /** Called when editor content changes */
  onChange?: ((html: string) => void) | undefined;
  /** Additional CSS classes for the container */
  className?: string | undefined;
  /** Whether the editor is read-only */
  editable?: boolean | undefined;
  /** Scene ID for streaming generation (optional) */
  sceneId?: string | undefined;
  /** Custom prompt for generation (optional) */
  prompt?: string | undefined;
  /** Context for generation (optional) */
  context?: string | undefined;
}

/**
 * EditorToolbar - Formatting toolbar for the Tiptap editor.
 *
 * Why: Provides accessible formatting controls using shadcn Toggle
 * components that sync with editor state for visual feedback. Includes
 * a Generate button for triggering LLM streaming.
 */
function EditorToolbar({
  editor,
  isStreaming,
  onGenerate,
  onStopGenerate,
}: {
  editor: Editor | null;
  isStreaming: boolean;
  onGenerate: () => void;
  onStopGenerate: () => void;
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
        disabled={isStreaming}
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
        disabled={isStreaming}
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
        disabled={isStreaming}
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
        disabled={isStreaming}
      >
        <Heading2 className="h-4 w-4" />
      </Toggle>

      <Separator orientation="vertical" className="mx-1 h-6" />

      {/* Generate / Stop button */}
      {isStreaming ? (
        <Button
          size="sm"
          variant="destructive"
          onClick={onStopGenerate}
          aria-label="Stop generating"
          data-testid="toolbar-stop-generate"
        >
          <Square className="mr-1 h-4 w-4" />
          Stop
        </Button>
      ) : (
        <Button
          size="sm"
          variant="secondary"
          onClick={onGenerate}
          aria-label="Generate content"
          data-testid="toolbar-generate"
        >
          <Sparkles className="mr-1 h-4 w-4" />
          Generate
        </Button>
      )}
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
  sceneId,
  prompt,
  context,
}: EditorComponentProps) {
  // Track the cursor position where we'll insert streamed text
  const insertPositionRef = useRef<number | null>(null);

  /**
   * Insert streamed content at the cursor position.
   *
   * Why: We need to insert text at a stable position even as content grows.
   * We save the cursor position when generation starts and append text there.
   */
  const handleChunk = useCallback((content: string, _sequence: number) => {
    if (!editorRef.current) return;
    const editor = editorRef.current;

    // Insert text at the saved position (or end if not set)
    const insertAt = insertPositionRef.current ?? editor.state.doc.content.size;

    // Insert the new content (add newline before if not first chunk)
    const textToInsert = insertPositionRef.current !== null && insertPositionRef.current !== insertAt
      ? `\n${content}`
      : content;

    editor
      .chain()
      .focus()
      .insertContentAt(insertAt, textToInsert)
      .run();

    // Update position for next chunk
    insertPositionRef.current = insertAt + textToInsert.length;
  }, []);

  /**
   * Handle stream completion.
   */
  const handleComplete = useCallback(() => {
    // Reset insert position
    insertPositionRef.current = null;
  }, []);

  /**
   * Handle stream error.
   */
  const handleError = useCallback((error: string) => {
    console.error('Stream error:', error);
    insertPositionRef.current = null;
  }, []);

  // Initialize streaming hook
  const {
    isStreaming,
    error: streamError,
    startStream,
    stopStream,
  } = useStoryStream({
    onChunk: handleChunk,
    onComplete: handleComplete,
    onError: handleError,
  });

  const editor = useEditor({
    extensions: [StarterKit],
    content: initialContent,
    editable: editable && !isStreaming, // Disable editing during streaming
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

  // Store editor reference for streaming callbacks
  const editorRef = useRef<Editor | null>(null);
  useEffect(() => {
    editorRef.current = editor;
  }, [editor]);

  /**
   * Start generation at current cursor position.
   *
   * Why: User expects text to appear where their cursor is,
   * creating an intuitive "AI typing" experience.
   */
  const handleGenerate = useCallback(() => {
    if (!editor) return;

    // Save cursor position for insertion
    const { from } = editor.state.selection;
    insertPositionRef.current = from;

    // Build stream request
    const request: StreamRequest = {
      scene_id: sceneId,
      prompt,
      context,
      max_tokens: 500,
    };

    startStream(request);
  }, [editor, sceneId, prompt, context, startStream]);

  /**
   * Stop current generation.
   */
  const handleStopGenerate = useCallback(() => {
    stopStream();
    insertPositionRef.current = null;
  }, [stopStream]);

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
      <EditorToolbar
        editor={editor}
        isStreaming={isStreaming}
        onGenerate={handleGenerate}
        onStopGenerate={handleStopGenerate}
      />

      {/* Generating indicator */}
      {isStreaming && (
        <div
          className="flex items-center gap-2 border-b border-border bg-primary/10 px-3 py-2 text-sm text-primary"
          data-testid="generating-indicator"
        >
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>Generating...</span>
        </div>
      )}

      {/* Stream error */}
      {streamError && (
        <div
          className="border-b border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive"
          data-testid="stream-error"
        >
          Error: {streamError}
        </div>
      )}

      {/* Editor content */}
      <div className="flex-1 overflow-auto p-4">
        <EditorContent editor={editor} />
      </div>
    </div>
  );
}

export default EditorComponent;
