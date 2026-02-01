/**
 * EditorComponent - Tiptap-based rich text editor for narrative writing.
 *
 * Why: Provides a WYSIWYG editing experience for story content, with a
 * toolbar for common formatting operations and shadcn/ui styling for
 * consistent design system integration. Supports streaming text insertion
 * from LLM generation via SSE. Also supports drag-and-drop character
 * mentions from the sidebar. CHAR-038: Supports @mention autocomplete
 * with quick character creation via typing @NewName.
 */
import { useEditor, EditorContent, type Editor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Mention from '@tiptap/extension-mention';
import { useDroppable } from '@dnd-kit/core';
import { Bold, Italic, Heading1, Heading2, Sparkles, Loader2, Square } from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { cn } from '@/lib/utils';
import { Toggle } from '@/components/ui/toggle';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';
import { useStoryStream, type StreamRequest } from '@/hooks/useStoryStream';
import { CharacterMention } from '@/components/editor/CharacterMention';
import { createMentionSuggestion, type SuggestionItem } from '@/components/editor/MentionSuggestion';
import { QuickCreateCharacterDialog } from '@/features/characters/components/QuickCreateCharacterDialog';
import type { CharacterSummary } from '@/types/schemas';

/**
 * Character mention insertion data.
 */
export interface CharacterMentionInsert {
  characterId: string;
  characterName: string;
}

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
  /** Whether a character is currently being dragged over */
  isDropTarget?: boolean | undefined;
  /** Pending character mention to insert (from drag-and-drop) */
  pendingMention?: CharacterMentionInsert | null | undefined;
  /** Called after mention is inserted */
  onMentionInserted?: (() => void) | undefined;
  /** List of characters for @mention suggestions (CHAR-038) */
  characters?: CharacterSummary[] | undefined;
  /** Called when a new character is created via quick-create (CHAR-038) */
  onCharacterCreated?: ((characterId: string, characterName: string) => void) | undefined;
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
  isDropTarget = false,
  pendingMention,
  onMentionInserted,
  characters = [],
  onCharacterCreated,
}: EditorComponentProps) {
  // Track the cursor position where we'll insert streamed text
  const insertPositionRef = useRef<number | null>(null);

  // CHAR-038: Quick-create dialog state
  const [quickCreateOpen, setQuickCreateOpen] = useState(false);
  const [quickCreateName, setQuickCreateName] = useState('');

  // Setup droppable zone for character drag-and-drop
  const { setNodeRef: setDroppableRef, isOver } = useDroppable({
    id: 'editor-drop-zone',
  });

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

  /**
   * CHAR-038: Handle request to create a new character from @mention.
   *
   * Why: When user types @NewName and no match is found, selecting
   * "Create New" opens the quick-create dialog with the name pre-filled.
   */
  const handleCreateNew = useCallback((name: string) => {
    setQuickCreateName(name);
    setQuickCreateOpen(true);
  }, []);

  /**
   * CHAR-038: Handle successful character creation from quick-create dialog.
   *
   * Why: After creating a character, we insert a mention of the new character
   * at the current cursor position, completing the flow without interruption.
   */
  const handleQuickCreateSuccess = useCallback(
    (characterId: string, characterName: string) => {
      // Insert the mention of the newly created character
      if (editorRef.current) {
        editorRef.current
          .chain()
          .focus()
          .insertCharacterMention({
            characterId,
            characterName,
          })
          .insertContent(' ')
          .run();
      }

      // Notify parent if callback provided
      onCharacterCreated?.(characterId, characterName);
    },
    [onCharacterCreated]
  );

  /**
   * CHAR-038: Create Mention extension with suggestion configuration.
   *
   * Why: The Mention extension provides @-trigger autocomplete with a
   * dropdown showing matching characters and a "Create New" option.
   */
  const mentionSuggestion = useMemo(
    () => createMentionSuggestion(characters, handleCreateNew),
    [characters, handleCreateNew]
  );

  /**
   * CHAR-038: Configure Mention extension to render character mentions.
   *
   * Why: When a character is selected from the dropdown, we need to insert
   * our custom CharacterMention node (which has hover cards) rather than
   * a generic mention node. We cast the command to bypass strict typing
   * since our items() returns SuggestionItems that get passed to command().
   */
  const MentionExtension = useMemo(
    () =>
      Mention.configure({
        HTMLAttributes: {
          class: 'character-mention',
        },
        suggestion: {
          ...mentionSuggestion,
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          command: ({ editor, range, props }: { editor: Editor; range: { from: number; to: number }; props: any }) => {
            const item = props as SuggestionItem;
            // Delete the @query text
            editor.chain().focus().deleteRange(range).run();

            // Insert our custom CharacterMention node
            editor
              .chain()
              .focus()
              .insertCharacterMention({
                characterId: item.id,
                characterName: item.name,
              })
              .insertContent(' ')
              .run();
          },
        },
      }),
    [mentionSuggestion]
  );

  const editor = useEditor({
    extensions: [StarterKit, CharacterMention, MentionExtension],
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
   * Insert character mention when pendingMention changes.
   *
   * Why: When a character is dropped on the editor, the parent component
   * sets pendingMention with the character data. This effect picks up
   * that data and inserts it as a mention node at the cursor position.
   */
  useEffect(() => {
    if (!pendingMention || !editor) return;

    // Insert the character mention at the current cursor position
    editor
      .chain()
      .focus()
      .insertCharacterMention({
        characterId: pendingMention.characterId,
        characterName: pendingMention.characterName,
      })
      .insertContent(' ') // Add space after mention
      .run();

    // Notify parent that mention was inserted
    onMentionInserted?.();
  }, [pendingMention, editor, onMentionInserted]);

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

  // Combine drop target state from props and local isOver
  const showDropIndicator = isDropTarget || isOver;

  return (
    <div
      ref={setDroppableRef}
      className={cn(
        'flex flex-col overflow-hidden rounded-md border border-input bg-background',
        'focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2',
        showDropIndicator && 'ring-2 ring-primary ring-offset-2',
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

      {/* Drop indicator */}
      {showDropIndicator && (
        <div
          className="flex items-center gap-2 border-b border-primary bg-primary/10 px-3 py-2 text-sm text-primary"
          data-testid="drop-indicator"
        >
          <span>Drop to insert @mention</span>
        </div>
      )}

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

      {/* CHAR-038: Quick Create Character Dialog */}
      <QuickCreateCharacterDialog
        open={quickCreateOpen}
        onClose={() => setQuickCreateOpen(false)}
        initialName={quickCreateName}
        onCharacterCreated={handleQuickCreateSuccess}
      />
    </div>
  );
}

export default EditorComponent;
