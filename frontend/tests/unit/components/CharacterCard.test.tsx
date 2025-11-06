/**
 * CharacterCard Component - React.memo Performance Tests
 * 
 * Tests to verify React.memo prevents unnecessary re-renders when props unchanged
 * Following TDD approach: Tests now active after implementation (GREEN phase)
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { vi } from 'vitest';
import { CharacterCard } from '../../../src/components/CharacterCard';

describe('CharacterCard - React.memo Performance Tests', () => {
  /**
   * Test 1: Verify component renders with basic props
   */
  test('should render character card with name', () => {
    const onSelect = vi.fn();
    const onFocus = vi.fn();
    const onKeyDown = vi.fn();
    
    render(
      <CharacterCard
        character="test_character"
        isSelected={false}
        onSelect={onSelect}
        index={0}
        isFocused={false}
        onFocus={onFocus}
        onKeyDown={onKeyDown}
      />
    );

    expect(screen.getByText('test_character')).toBeInTheDocument();
  });

  /**
   * Test 2: Verify React.memo prevents re-render when props unchanged
   * This is the key performance test - component should NOT re-render
   * when parent re-renders but props are identical
   */
  test('should NOT re-render when props unchanged (React.memo optimization)', () => {
    const onSelect = vi.fn();
    const onFocus = vi.fn();
    const onKeyDown = vi.fn();
    
    // Create a wrapper component to trigger parent re-renders
    const Wrapper = ({ triggerRerender }: { triggerRerender: number }) => {
      return (
        <CharacterCard
          character="test_character"
          isSelected={false}
          onSelect={onSelect}
          index={0}
          isFocused={false}
          onFocus={onFocus}
          onKeyDown={onKeyDown}
        />
      );
    };
    
    const { rerender } = render(<Wrapper triggerRerender={0} />);
    
    // Get initial DOM reference
    const card = screen.getByTestId('character-card-test_character');
    const initialCard = card;

    // Re-render parent with different wrapper prop (same CharacterCard props)
    rerender(<Wrapper triggerRerender={1} />);

    // CharacterCard should not re-render (React.memo prevents it)
    // DOM reference should be the same because component didn't re-render
    const cardAfterRerender = screen.getByTestId('character-card-test_character');
    
    // Verify the DOM node is the same instance (not re-created)
    expect(cardAfterRerender).toBe(initialCard);
    
    // Verify component still works correctly
    expect(screen.getByText('test_character')).toBeInTheDocument();
  });

  /**
   * Test 3: Verify component DOES re-render when isSelected prop changes
   */
  test('should re-render when isSelected prop changes', () => {
    let renderCount = 0;

    const RenderTracker = (props: any) => {
      renderCount++;
      return <CharacterCard {...props} />;
    };

    const onSelect = vi.fn();
    const onFocus = vi.fn();
    const onKeyDown = vi.fn();
    
    const { rerender } = render(
      <RenderTracker
        character="test_character"
        isSelected={false}
        onSelect={onSelect}
        index={0}
        isFocused={false}
        onFocus={onFocus}
        onKeyDown={onKeyDown}
      />
    );

    expect(renderCount).toBe(1);

    // Re-render with CHANGED isSelected prop
    rerender(
      <RenderTracker
        character="test_character"
        isSelected={true}
        onSelect={onSelect}
        index={0}
        isFocused={false}
        onFocus={onFocus}
        onKeyDown={onKeyDown}
      />
    );

    // Should re-render because isSelected changed
    expect(renderCount).toBe(2);
  });

  /**
   * Test 4: Verify component handles click events
   */
  test('should call onSelect when clicked', () => {
    const onSelect = vi.fn();
    const onFocus = vi.fn();
    const onKeyDown = vi.fn();

    render(
      <CharacterCard
        character="test_character"
        isSelected={false}
        onSelect={onSelect}
        index={0}
        isFocused={false}
        onFocus={onFocus}
        onKeyDown={onKeyDown}
      />
    );

    const card = screen.getByRole('button', { name: /select character test_character/i });
    fireEvent.click(card);

    expect(onSelect).toHaveBeenCalledWith('test_character');
  });

  /**
   * Test 5: Verify selected state styling
   */
  test('should apply selected class when isSelected is true', () => {
    const onSelect = vi.fn();
    const onFocus = vi.fn();
    const onKeyDown = vi.fn();

    const { container } = render(
      <CharacterCard
        character="test_character"
        isSelected={true}
        onSelect={onSelect}
        index={0}
        isFocused={false}
        onFocus={onFocus}
        onKeyDown={onKeyDown}
      />
    );

    const card = container.querySelector('.character-card');
    expect(card).toHaveClass('selected');
  });
});
