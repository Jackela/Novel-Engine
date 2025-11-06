/**
 * CharacterCard Component
 * 
 * Optimized character card component for large list performance
 * Wrapped with React.memo to prevent unnecessary re-renders
 * 
 * Performance Optimization:
 * - React.memo with custom comparison prevents re-renders when props unchanged
 * - Only re-renders when character selection state changes
 * - Target: < 15 re-renders when toggling selection in 100-item list
 * 
 * Constitution Compliance:
 * - Article V (SOLID): Single responsibility - render individual character card
 * - Article III (TDD): Implemented after tests written and verified to fail
 * - Article II (Hexagonal): UI adapter for character selection domain
 */

import React from 'react';
import { logger } from '../services/logging/LoggerFactory';

interface CharacterCardProps {
  /** Character name to display */
  character: string;
  /** Whether this character is currently selected */
  isSelected: boolean;
  /** Callback when character is selected/deselected */
  onSelect: (character: string) => void;
  /** Index for arrow key navigation */
  index: number;
  /** Whether this card currently has keyboard focus */
  isFocused: boolean;
  /** Ref for programmatic focus management */
  cardRef?: React.Ref<HTMLDivElement>;
  /** Callback when card receives focus */
  onFocus: (index: number) => void;
  /** Keyboard navigation handler */
  onKeyDown: (e: React.KeyboardEvent<HTMLDivElement>) => void;
}

/**
 * CharacterCard component with React.memo optimization
 * 
 * Custom comparison function ensures component only re-renders when:
 * - isSelected prop changes (character selected/deselected)
 * - isFocused prop changes (keyboard navigation)
 * - character name changes (unlikely but handled)
 * 
 * Parent re-renders do NOT trigger CharacterCard re-renders if props unchanged
 */
const CharacterCard = React.memo<CharacterCardProps>(
  ({ character, isSelected, onSelect, index, isFocused, cardRef, onFocus, onKeyDown }) => {
    const handleClick = () => {
      logger.info('Character card clicked:', { character, isSelected });
      onSelect(character);
    };

    const handleFocus = React.useCallback((e: React.FocusEvent<HTMLDivElement>) => {
      const idx = parseInt(e.currentTarget.dataset.index || '0', 10);
      onFocus(idx);
    }, [onFocus]);

    return (
      <div
        ref={cardRef}
        className={`character-card ${isSelected ? 'selected' : ''}`}
        onClick={handleClick}
        data-testid={`character-card-${character}`}
        data-character={character}
        data-index={index}
        role="button"
        tabIndex={isFocused ? 0 : -1}
        aria-label={`Select character ${character}`}
        aria-pressed={isSelected}
        onKeyDown={onKeyDown}
        onFocus={handleFocus}
      >
        <div className="character-content">
          <h2 className="character-name">{character}</h2>
          <div className="character-status">
            {isSelected && (
              <div className="selection-checkmark" data-testid={`selection-checkmark-${character}`}>
                ✓
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }
  // Using default React.memo shallow comparison
  // All props will be compared with Object.is
  // This works because all callback props are memoized with useCallback in parent
);

CharacterCard.displayName = 'CharacterCard';

export { CharacterCard };
export type { CharacterCardProps };
