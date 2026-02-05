/**
 * ChatInterface - Floating chat widget for AI assistant
 *
 * BRAIN-037B-01: Chat UI - Floating Widget
 *
 * Why: Provides a floating, collapsible chat interface for interacting
 * with the AI assistant. Positioned fixed bottom-right and collapses when not in use.
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import { MessageSquare, X, Send, Minimize2, Maximize2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { brainSettingsApi, type ChatMessage, type ChatChunk } from '@/features/routing/api/brainSettingsApi';

interface ChatInterfaceProps {
  /** Optional initial session ID for conversation tracking */
  sessionId?: string;
}

/**
 * ChatInterface provides a floating chat widget with:
 * - Fixed positioning (bottom-right)
 * - Collapsible when not in use
 * - Streaming message responses
 * - Auto-scroll to latest message
 */
export function ChatInterface({ sessionId = 'default' }: ChatInterfaceProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');

  const scrollRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, streamingContent]);

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
            setMessages((prev) => [...prev, assistantMessage]);
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
              <ScrollArea className="h-[380px] px-4">
                <div ref={scrollRef} className="flex flex-col gap-3 py-4">
                  {messages.length === 0 && !streamingContent && (
                    <p className="text-center text-sm text-muted-foreground">
                      Ask me anything about your story, characters, or world building.
                    </p>
                  )}

                  {messages.map((message, index) => (
                    <div
                      key={index}
                      className={cn(
                        'max-w-[80%] rounded-lg px-3 py-2',
                        message.role === 'user'
                          ? 'ml-auto bg-primary text-primary-foreground'
                          : 'mr-auto bg-muted',
                      )}
                    >
                      <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                    </div>
                  ))}

                  {streamingContent && (
                    <div className="mr-auto max-w-[80%] rounded-lg bg-muted px-3 py-2">
                      <p className="text-sm whitespace-pre-wrap">
                        {streamingContent}
                        <span className="inline-block animate-pulse">▊</span>
                      </p>
                    </div>
                  )}
                </div>
              </ScrollArea>
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

// Helper function for className merging (copied from lib/utils)
function cn(...classes: (string | undefined | null | false)[]) {
  return classes.filter(Boolean).join(' ');
}

export default ChatInterface;
