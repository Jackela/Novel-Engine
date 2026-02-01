/**
 * CharacterMention - Tiptap extension for @CharacterName mentions.
 *
 * Why: Enables inline character references in the narrative editor,
 * allowing writers to reference world entities that can later be used
 * for context injection or character tracking. Uses ReactNodeViewRenderer
 * to support interactive hover cards showing character details.
 */
import { Node, mergeAttributes } from '@tiptap/core';
import { ReactNodeViewRenderer } from '@tiptap/react';

import { CharacterMentionView } from './CharacterMentionView';

/**
 * Character mention attributes stored in the document.
 */
export interface CharacterMentionAttributes {
  /** Character's unique identifier for lookups */
  characterId: string;
  /** Display name shown in the editor */
  characterName: string;
}

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    characterMention: {
      /**
       * Insert a character mention at the current position.
       */
      insertCharacterMention: (attrs: CharacterMentionAttributes) => ReturnType;
    };
  }
}

/**
 * CharacterMention extension for Tiptap.
 *
 * Why: Custom extension using ReactNodeViewRenderer to enable interactive
 * hover cards on character mentions. The hover card shows character details
 * (avatar, name, archetype, description) with 300ms delay, providing context
 * without leaving the editor.
 */
export const CharacterMention = Node.create({
  name: 'characterMention',

  group: 'inline',

  inline: true,

  selectable: true,

  atom: true,

  addAttributes() {
    return {
      characterId: {
        default: null,
        parseHTML: (element) => element.getAttribute('data-character-id'),
        renderHTML: (attributes: Record<string, unknown>) => ({
          'data-character-id': attributes['characterId'] as string,
        }),
      },
      characterName: {
        default: null,
        parseHTML: (element) => element.getAttribute('data-character-name'),
        renderHTML: (attributes: Record<string, unknown>) => ({
          'data-character-name': attributes['characterName'] as string,
        }),
      },
    };
  },

  parseHTML() {
    return [
      {
        tag: 'span[data-character-mention]',
      },
    ];
  },

  renderHTML({ node, HTMLAttributes }) {
    // Fallback HTML for SSR/copy-paste - the React component handles interactive rendering
    return [
      'span',
      mergeAttributes(HTMLAttributes, {
        'data-character-mention': '',
        class: 'character-mention',
      }),
      `@${node.attrs['characterName']}`,
    ];
  },

  addNodeView() {
    return ReactNodeViewRenderer(CharacterMentionView);
  },

  addCommands() {
    return {
      insertCharacterMention:
        (attrs: CharacterMentionAttributes) =>
        ({ commands }) => {
          return commands.insertContent({
            type: this.name,
            attrs,
          });
        },
    };
  },
});

export default CharacterMention;
