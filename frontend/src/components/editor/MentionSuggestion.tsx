/**
 * MentionSuggestion - Tiptap Mention extension configuration for character suggestions.
 *
 * Why: Enables the @mention autocomplete experience in the editor. When users
 * type @ followed by text, this shows a dropdown of matching characters.
 * The key feature is the "Create New" option that appears for unmatched names,
 * enabling CHAR-038's quick character creation workflow.
 */
import { ReactRenderer } from '@tiptap/react';
import { forwardRef, useCallback, useEffect, useImperativeHandle, useState } from 'react';
import { UserPlus, User } from 'lucide-react';

import { cn } from '@/lib/utils';
import type { CharacterSummary } from '@/types/schemas';

/**
 * Suggestion item can be an existing character or a "create new" action.
 */
export interface SuggestionItem {
  type: 'character' | 'create-new';
  id: string;
  name: string;
  archetype?: string | null;
}

interface MentionListProps {
  items: SuggestionItem[];
  command: (item: SuggestionItem) => void;
}

interface MentionListRef {
  onKeyDown: (props: { event: KeyboardEvent }) => boolean;
}

/**
 * MentionList - Dropdown component for mention suggestions.
 *
 * Why: Provides keyboard-navigable list of matching characters with visual
 * distinction for the "Create New" option. Uses shadcn styling for consistency.
 */
export const MentionList = forwardRef<MentionListRef, MentionListProps>(
  ({ items, command }, ref) => {
    const [selectedIndex, setSelectedIndex] = useState(0);

    const selectItem = useCallback(
      (index: number) => {
        const item = items[index];
        if (item) {
          command(item);
        }
      },
      [items, command]
    );

    const upHandler = useCallback(() => {
      setSelectedIndex((prev) => (prev + items.length - 1) % items.length);
    }, [items.length]);

    const downHandler = useCallback(() => {
      setSelectedIndex((prev) => (prev + 1) % items.length);
    }, [items.length]);

    const enterHandler = useCallback(() => {
      selectItem(selectedIndex);
    }, [selectItem, selectedIndex]);

    useEffect(() => {
      setSelectedIndex(0);
    }, [items]);

    useImperativeHandle(ref, () => ({
      onKeyDown: ({ event }) => {
        if (event.key === 'ArrowUp') {
          upHandler();
          return true;
        }

        if (event.key === 'ArrowDown') {
          downHandler();
          return true;
        }

        if (event.key === 'Enter') {
          enterHandler();
          return true;
        }

        return false;
      },
    }));

    if (items.length === 0) {
      return null;
    }

    return (
      <div className="z-50 min-w-[200px] overflow-hidden rounded-md border border-border bg-popover p-1 shadow-md">
        {items.map((item, index) => (
          <button
            key={item.id}
            type="button"
            className={cn(
              'flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm outline-none',
              'hover:bg-accent hover:text-accent-foreground',
              index === selectedIndex && 'bg-accent text-accent-foreground'
            )}
            onClick={() => selectItem(index)}
          >
            {item.type === 'create-new' ? (
              <>
                <UserPlus className="h-4 w-4 text-primary" />
                <span className="font-medium text-primary">
                  Create &quot;{item.name}&quot;
                </span>
              </>
            ) : (
              <>
                <User className="h-4 w-4 text-muted-foreground" />
                <span>{item.name}</span>
                {item.archetype && (
                  <span className="ml-auto text-xs text-muted-foreground">
                    {item.archetype}
                  </span>
                )}
              </>
            )}
          </button>
        ))}
      </div>
    );
  }
);

MentionList.displayName = 'MentionList';

/**
 * Build suggestion items from character list and query string.
 *
 * Why: Shows matching characters first, then always adds a "Create New" option
 * at the bottom when the user has typed at least 2 characters. This enables
 * the quick-create workflow even when there are partial matches.
 */
export function buildSuggestionItems(
  characters: CharacterSummary[],
  query: string
): SuggestionItem[] {
  const items: SuggestionItem[] = [];

  // Filter existing characters by name match
  const queryLower = query.toLowerCase();
  const matchingCharacters = characters
    .filter((c) => c.name.toLowerCase().includes(queryLower))
    .slice(0, 5) // Limit to 5 matches
    .map((c) => ({
      type: 'character' as const,
      id: c.agent_id,
      name: c.name,
      archetype: c.archetype ?? null,
    }));

  items.push(...matchingCharacters);

  // Add "Create New" option if query has at least 2 characters
  // and doesn't exactly match an existing character
  if (query.length >= 2) {
    const exactMatch = characters.some(
      (c) => c.name.toLowerCase() === queryLower
    );
    if (!exactMatch) {
      items.push({
        type: 'create-new',
        id: `create-${query}`,
        name: query,
      });
    }
  }

  return items;
}

/**
 * Popup element manager for mention suggestions.
 */
class PopupManager {
  private popup: HTMLDivElement | null = null;

  create(content: Element, rect: DOMRect) {
    this.destroy();

    this.popup = document.createElement('div');
    this.popup.style.position = 'fixed';
    this.popup.style.left = `${rect.left}px`;
    this.popup.style.top = `${rect.bottom + 4}px`;
    this.popup.style.zIndex = '50';

    this.popup.appendChild(content);
    document.body.appendChild(this.popup);
  }

  update(rect: DOMRect) {
    if (this.popup) {
      this.popup.style.left = `${rect.left}px`;
      this.popup.style.top = `${rect.bottom + 4}px`;
    }
  }

  destroy() {
    if (this.popup) {
      this.popup.remove();
      this.popup = null;
    }
  }
}

/**
 * Create suggestion configuration for Tiptap Mention extension.
 *
 * Why: Configures how mentions are triggered, displayed, and inserted.
 * The key integration point is onSelect which can trigger either character
 * mention insertion or the quick-create dialog.
 *
 * @param characters - List of existing characters for suggestions
 * @param onCreateNew - Callback when "Create New" is selected with the typed name
 */
export function createMentionSuggestion(
  characters: CharacterSummary[],
  onCreateNew: (name: string) => void
) {
  return {
    char: '@',
    allowSpaces: false,
    allowedPrefixes: [' ', '\n'], // Allow @ at start of line/sentence
    startOfLine: false,

    items: ({ query }: { query: string }) => {
      return buildSuggestionItems(characters, query);
    },

    render: () => {
      let component: ReactRenderer<MentionListRef> | null = null;
      const popup = new PopupManager();

      return {
        onStart: (props: {
          clientRect?: (() => DOMRect | null) | null;
          items: SuggestionItem[];
          command: (item: SuggestionItem) => void;
        }) => {
          component = new ReactRenderer(MentionList, {
            props: {
              items: props.items,
              command: (item: SuggestionItem) => {
                if (item.type === 'create-new') {
                  // Trigger the create dialog, don't insert mention yet
                  onCreateNew(item.name);
                  popup.destroy();
                } else {
                  // Insert the character mention
                  props.command(item);
                }
              },
            },
            editor: null as never, // Not needed for our component
          });

          const rect = props.clientRect?.();
          if (rect) {
            popup.create(component.element, rect);
          }
        },

        onUpdate(props: {
          clientRect?: (() => DOMRect | null) | null;
          items: SuggestionItem[];
          command: (item: SuggestionItem) => void;
        }) {
          component?.updateProps({
            items: props.items,
            command: (item: SuggestionItem) => {
              if (item.type === 'create-new') {
                onCreateNew(item.name);
                popup.destroy();
              } else {
                props.command(item);
              }
            },
          });

          const rect = props.clientRect?.();
          if (rect) {
            popup.update(rect);
          }
        },

        onKeyDown(props: { event: KeyboardEvent }) {
          if (props.event.key === 'Escape') {
            popup.destroy();
            return true;
          }

          return component?.ref?.onKeyDown(props) ?? false;
        },

        onExit() {
          popup.destroy();
          component?.destroy();
        },
      };
    },
  };
}

export default MentionList;
