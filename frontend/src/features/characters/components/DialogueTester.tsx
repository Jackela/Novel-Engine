/**
 * DialogueTester - AI Voice/Dialogue Testing Interface
 *
 * A chat-like interface where users can test how a character speaks.
 * Sends context prompts to the dialogue generation API and displays
 * character responses with tone, internal thoughts, and body language.
 */
import { useState, useRef, useEffect } from 'react';
import { Button } from '@/shared/components/ui/Button';
import { Card, CardContent } from '@/shared/components/ui/Card';
import { Input } from '@/shared/components/ui/Input';
import { Label } from '@/shared/components/ui/Label';
import { Badge } from '@/shared/components/ui/Badge';
import { generateDialogue } from '@/lib/api';
import type { DialogueGenerationResponse, CharacterDetail } from '@/types/schemas';

/**
 * Message in the conversation history.
 */
interface Message {
  id: string;
  type: 'user' | 'character';
  content: string;
  timestamp: Date;
  // Character response metadata
  tone?: string;
  internalThought?: string | null;
  bodyLanguage?: string | null;
  error?: string | null;
}

interface Props {
  characterId: string;
  characterName: string;
  characterData?: CharacterDetail | null;
}

const MOOD_OPTIONS = [
  { value: '', label: 'Default' },
  { value: 'happy', label: 'Happy' },
  { value: 'angry', label: 'Angry' },
  { value: 'sad', label: 'Sad' },
  { value: 'fearful', label: 'Fearful' },
  { value: 'excited', label: 'Excited' },
  { value: 'cautious', label: 'Cautious' },
  { value: 'melancholic', label: 'Melancholic' },
];

const EXAMPLE_CONTEXTS = [
  'A stranger asks for directions',
  'Their rival insults them',
  'A merchant offers a suspiciously good deal',
  'An old friend appears unexpectedly',
  'They discover a hidden treasure',
  'Someone asks about their past',
];

export default function DialogueTester({
  characterId,
  characterName,
  characterData,
}: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [contextInput, setContextInput] = useState('');
  const [mood, setMood] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const trimmedContext = contextInput.trim();
    if (!trimmedContext) return;

    // Add user message
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      type: 'user',
      content: trimmedContext,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setContextInput('');
    setIsLoading(true);

    try {
      const response: DialogueGenerationResponse = await generateDialogue({
        character_id: characterId,
        context: trimmedContext,
        mood: mood || undefined,
        // If we have character data, we could pass overrides here
        psychology_override: characterData?.psychology ?? undefined,
      });

      // Add character response
      const characterMessage: Message = {
        id: `char-${Date.now()}`,
        type: 'character',
        content: response.dialogue,
        timestamp: new Date(),
        tone: response.tone,
        internalThought: response.internal_thought ?? null,
        bodyLanguage: response.body_language ?? null,
        error: response.error ?? null,
      };
      setMessages((prev) => [...prev, characterMessage]);
    } catch (error) {
      // Add error message
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        type: 'character',
        content: '...',
        timestamp: new Date(),
        error: error instanceof Error ? error.message : 'Failed to generate dialogue',
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleExampleClick = (context: string) => {
    setContextInput(context);
  };

  const handleClear = () => {
    setMessages([]);
  };

  return (
    <div className="flex h-full max-h-[600px] flex-col">
      {/* Header with character info */}
      <div className="flex items-center justify-between border-b p-4">
        <div>
          <h3 className="text-lg font-semibold">{characterName}</h3>
          <p className="text-sm text-muted-foreground">
            Voice Tester - Chat as this character
          </p>
        </div>
        {messages.length > 0 && (
          <Button variant="outline" size="sm" onClick={handleClear}>
            Clear Chat
          </Button>
        )}
      </div>

      {/* Mood selector */}
      <div className="border-b bg-muted/30 px-4 py-2">
        <div className="flex items-center gap-4">
          <Label htmlFor="mood-select" className="text-sm font-medium">
            Current Mood:
          </Label>
          <select
            id="mood-select"
            value={mood}
            onChange={(e) => setMood(e.target.value)}
            className="h-8 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          >
            {MOOD_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Messages area */}
      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        {messages.length === 0 ? (
          <div className="py-8 text-center text-muted-foreground">
            <p className="mb-4">No messages yet. Start a conversation!</p>
            <div className="space-y-2">
              <p className="text-sm font-medium">Try one of these prompts:</p>
              <div className="flex flex-wrap justify-center gap-2">
                {EXAMPLE_CONTEXTS.map((context) => (
                  <Button
                    key={context}
                    variant="outline"
                    size="sm"
                    onClick={() => handleExampleClick(context)}
                    className="text-xs"
                  >
                    {context}
                  </Button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <Card
                className={`max-w-[80%] ${
                  message.type === 'user'
                    ? 'bg-primary text-primary-foreground'
                    : message.error
                      ? 'border-destructive bg-destructive/10'
                      : 'bg-muted'
                }`}
              >
                <CardContent className="p-3">
                  {message.type === 'user' ? (
                    <>
                      <p className="mb-1 text-xs opacity-70">Context:</p>
                      <p>{message.content}</p>
                    </>
                  ) : (
                    <>
                      {message.error ? (
                        <p className="text-sm text-destructive">
                          Error: {message.error}
                        </p>
                      ) : (
                        <>
                          <div className="mb-2 flex items-center gap-2">
                            <span className="text-sm font-medium">
                              {characterName}:
                            </span>
                            {message.tone && (
                              <Badge variant="secondary" className="text-xs">
                                {message.tone}
                              </Badge>
                            )}
                          </div>
                          <p className="italic">&quot;{message.content}&quot;</p>

                          {/* Body language */}
                          {message.bodyLanguage && (
                            <p className="mt-2 text-xs text-muted-foreground">
                              *{message.bodyLanguage}*
                            </p>
                          )}

                          {/* Internal thought */}
                          {message.internalThought && (
                            <div className="mt-2 border-t border-border/50 pt-2">
                              <p className="text-xs text-muted-foreground">
                                <span className="font-medium">Thinks:</span>{' '}
                                <span className="italic">
                                  {message.internalThought}
                                </span>
                              </p>
                            </div>
                          )}
                        </>
                      )}
                    </>
                  )}
                </CardContent>
              </Card>
            </div>
          ))
        )}

        {/* Loading indicator */}
        {isLoading && (
          <div className="flex justify-start">
            <Card className="bg-muted">
              <CardContent className="p-3">
                <div className="flex items-center gap-2">
                  <div className="flex gap-1">
                    <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground" />
                    <span
                      className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground"
                      style={{ animationDelay: '0.1s' }}
                    />
                    <span
                      className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground"
                      style={{ animationDelay: '0.2s' }}
                    />
                  </div>
                  <span className="text-sm text-muted-foreground">
                    {characterName} is thinking...
                  </span>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <form onSubmit={handleSubmit} className="border-t bg-background p-4">
        <div className="flex gap-2">
          <Input
            value={contextInput}
            onChange={(e) => setContextInput(e.target.value)}
            placeholder="Describe the situation... (e.g., 'Someone asks about their past')"
            disabled={isLoading}
            className="flex-1"
          />
          <Button type="submit" disabled={isLoading || !contextInput.trim()}>
            {isLoading ? 'Generating...' : 'Send'}
          </Button>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          Enter a context or situation to see how {characterName} would respond.
        </p>
      </form>
    </div>
  );
}
