/**
 * ChatInterface - Floating chat widget for AI assistant
 *
 * BRAIN-037B-01: Chat UI - Floating Widget
 *
 * Why: Provides a floating, collapsible chat interface for interacting
 * with the AI assistant. Positioned fixed bottom-right and collapses when not in use.
 *
 * OPT-004: Added virtualization using react-window VariableSizeList
 * to handle 100+ messages efficiently with dynamic-height support.
 *
 * OPT-008: Added Markdown rendering for assistant messages with syntax
 * highlighting for code blocks using highlight.js. User messages remain
 * plain text.
 */

import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { MessageSquare, X, Send, Minimize2, Maximize2 } from 'lucide-react';
import { VariableSizeList as List } from 'react-window';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Markdown, PlainText } from '@/components/ui/markdown';
import { cn } from '@/lib/utils';
import { brainSettingsApi, type ChatMessage, type ChatChunk } from '@/features/routing/api/brainSettingsApi';

interface ChatInterfaceProps {
  /** Optional initial session ID for conversation tracking */
  sessionId?: string;
}

/**
 * Estimate message height based on content length
 * Used for initial virtual list sizing before actual measurement
 */
function estimateMessageHeight(content: string): number {
  const lines = Math.ceil(content.length / 50); // Approx 50 chars per line
  const minHeight = 44; // Base padding + single line
  const lineHeight = 20; // Approx line height
  return Math.min(minHeight + lines * lineHeight, 200); // Cap at 200px
}

/**
 * MessageRow - Individual message component for virtualized list
 */
interface MessageRowProps {
  index: number;
  style: React.CSSProperties;
  data: {
    messages: ChatMessage[];
    streamingContent: string;
    isStreaming: boolean;
  };
}

function MessageRow({ index, style, data }: MessageRowProps) {
  const { messages, streamingContent, isStreaming } = data;

  // Check if this is the streaming indicator row (last row when streaming)
  const isStreamingRow = isStreaming && index === messages.length;

  if (isStreamingRow) {
    return (
      <div style={style} className="px-4 py-1">
        <div className="mr-auto max-w-[80%] rounded-lg bg-muted px-3 py-2">
          <PlainText
            content={streamingContent + '▊'}
            className="text-sm"
          />
          <span className="inline-block animate-pulse" />
        </div>
      </div>
    );
  }

  const message = messages[index];
  if (!message) return null;

  return (
    <div style={style} className="px-4 py-1">
      <div
        className={cn(
          'max-w-[80%] rounded-lg px-3 py-2',
          message.role === 'user'
            ? 'ml-auto bg-primary text-primary-foreground'
            : 'mr-auto bg-muted',
        )}
      >
        {message.role === 'assistant' ? (
          <Markdown content={message.content} />
        ) : (
          <PlainText content={message.content} />
        )}
      </div>
    </div>
  );
}

/**
 * Custom outer element to maintain scroll styling with react-window
 */
const OuterElementType = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>((props, ref) => {
  return (
    <div
      ref={ref}
      className="h-full overflow-y-auto overflow-x-hidden"
      {...props}
    />
  );
});
OuterElementType.displayName = 'OuterElementType';

/**
 * ChatInterface provides a floating chat widget with:
 * - Fixed positioning (bottom-right)
 * - Collapsible when not in use
 * - Streaming message responses
 * - Auto-scroll to latest message
 * - Virtualized message list for 100+ messages
 */
export function ChatInterface({ sessionId = 'default' }: ChatInterfaceProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');

  const listRef = useRef<List>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Cache for item sizes to avoid recalculation
  const itemSizeCache = useRef<Map<number, number>>(new Map());

  // Reset caches when messages change significantly
  useEffect(() => {
    if (messages.length === 0) {
      itemSizeCache.current.clear();
    }
  }, [messages.length]);

  /**
   * Get item size for virtual list
   * Uses cache to avoid recalculating heights
   */
  const getItemSize = useCallback((index: number) => {
    // Check cache first
    if (itemSizeCache.current.has(index)) {
      return itemSizeCache.current.get(index)!;
    }

    // Streaming indicator row
    if (isStreaming && index === messages.length) {
      const height = estimateMessageHeight(streamingContent) + 16;
      itemSizeCache.current.set(index, height);
      return height;
    }

    const message = messages[index];
    if (!message) {
      return 60; // Default fallback
    }

    const height = estimateMessageHeight(message.content) + 16;
    itemSizeCache.current.set(index, height);
    return height;
  }, [messages, isStreaming, streamingContent]);

  /**
   * Reset item size cache when streaming content changes
   * This ensures the streaming row resizes properly
   */
  useEffect(() => {
    if (isStreaming) {
      itemSizeCache.current.delete(messages.length);
      listRef.current?.resetAfterIndex(messages.length);
    }
  }, [streamingContent, isStreaming, messages.length]);

  // Calculate total item count (messages + optional streaming indicator)
  // Must be defined before useEffects that use it
  const itemCount = messages.length + (isStreaming ? 1 : 0);

  /**
   * Auto-scroll to bottom when new messages arrive
   * Always scrolls to latest message for better chat UX
   */
  useEffect(() => {
    if (!listRef.current) return;

    // Scroll to the last item
    const lastIndex = Math.max(0, itemCount - 1);
    listRef.current.scrollToItem(lastIndex, 'end');
  }, [itemCount]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
      abortControllerRef.current = null;
    };
  }, []);

  const handleSend = useCallback(async () => {
    const trimmedInput = input.trim();
    if (!trimmedInput || isStreaming) return;

    // Add user message
    const userMessage: ChatMessage = { role: 'user', content: trimmedInput };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsStreaming(true);
    setStreamingContent('');

    // Clear size cache for new index
    itemSizeCache.current.delete(messages.length);

    // Prepare messages for API
    const chatHistory = messages.map((msg) => ({
      role: msg.role as 'user' | 'assistant',
      content: msg.content,
    }));

    try {
      await brainSettingsApi.chat(
        {
          query: trimmedInput,
          chat_history: chatHistory,
          session_id: sessionId,
        },
        (chunk: ChatChunk) => {
          if (chunk.done) {
            // Final chunk - add complete assistant message
            const assistantMessage: ChatMessage = { role: 'assistant', content: streamingContent + chunk.delta };
            setMessages((prev) => {
              itemSizeCache.current.delete(prev.length + 1);
              return [...prev, assistantMessage];
            });
            setStreamingContent('');
            setIsStreaming(false);
          } else {
            // Streaming chunk - accumulate content
            setStreamingContent((prev) => prev + chunk.delta);
          }
        },
        (error: Error) => {
          console.error('Chat error:', error);
          setMessages((prev) => [
            ...prev,
            { role: 'assistant', content: `Error: ${error.message}` },
          ]);
          setStreamingContent('');
          setIsStreaming(false);
        },
      );
    } catch (error) {
      console.error('Chat error:', error);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `Error: ${(error as Error).message}` },
      ]);
      setIsStreaming(false);
    }
  }, [input, isStreaming, messages, sessionId, streamingContent]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  // Memoize list data to avoid unnecessary re-renders
  const listData = useMemo(
    () => ({ messages, streamingContent, isStreaming }),
    [messages, streamingContent, isStreaming],
  );

  // Toggle button - always visible
  if (!isOpen) {
    return (
      <div className="fixed bottom-4 right-4 z-50">
        <Button
          onClick={() => setIsOpen(true)}
          size="lg"
          className="h-14 w-14 rounded-full shadow-lg"
          aria-label="Open chat"
        >
          <MessageSquare className="h-6 w-6" />
        </Button>
      </div>
    );
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col items-end gap-2">
      {/* Main chat panel */}
      <Card
        className={cn(
          'w-80 sm:w-96 shadow-lg transition-all duration-200',
          isMinimized ? 'h-14' : 'h-[500px]',
        )}
      >
        {/* Header */}
        <CardHeader className="flex flex-row items-center justify-between border-b p-4">
          <CardTitle className="text-sm font-medium">AI Assistant</CardTitle>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => setIsMinimized(!isMinimized)}
              aria-label={isMinimized ? 'Expand' : 'Minimize'}
            >
              {isMinimized ? (
                <Maximize2 className="h-4 w-4" />
              ) : (
                <Minimize2 className="h-4 w-4" />
              )}
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => setIsOpen(false)}
              aria-label="Close chat"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>

        {/* Messages area - hidden when minimized */}
        {!isMinimized && (
          <>
            <CardContent className="flex-1 p-0">
              <div className="h-[380px]">
                {messages.length === 0 && !isStreaming ? (
                  <div className="flex h-full items-center justify-center px-4">
                    <p className="text-center text-sm text-muted-foreground">
                      Ask me anything about your story, characters, or world building.
                    </p>
                  </div>
                ) : (
                  <List
                    ref={listRef}
                    outerElementType={OuterElementType}
                    itemCount={itemCount}
                    itemSize={getItemSize}
                    width="100%"
                    height={380}
                    itemData={listData}
                  >
                    {MessageRow}
                  </List>
                )}
              </div>
            </CardContent>

            {/* Input area */}
            <div className="border-t p-3">
              <div className="flex gap-2">
                <Input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask a question..."
                  disabled={isStreaming}
                  className="flex-1"
                />
                <Button
                  onClick={handleSend}
                  disabled={isStreaming || !input.trim()}
                  size="icon"
                  className="shrink-0"
                  aria-label="Send message"
                >
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </>
        )}
      </Card>
    </div>
  );
}

export default ChatInterface;
