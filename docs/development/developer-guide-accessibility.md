# Developer Guide - Accessibility & Performance

## Quick Start

### Setting Up

```bash
# Install dependencies (one time)
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
(cd frontend && npm install)

# Start both stacks in the background (non-blocking)
npm run dev:daemon

# Run tests
(cd frontend && npm test)

# Accessibility-only suite
(cd frontend && npm test -- accessibility)

# Size + type checks
(cd frontend && npm run size && npm run type-check)

# Stop dev environment after auditing
npm run dev:stop
```

## Accessible Component Development

### Rule 1: Always Use Semantic HTML

```tsx
// ✅ GOOD - Semantic HTML
<button onClick={handleClick} disabled={isLoading}>
  Submit
</button>

// ❌ BAD - Non-semantic div
<div onClick={handleClick} className="button">
  Submit
</div>
```

### Rule 2: Provide Keyboard Navigation

```tsx
// ✅ GOOD - Keyboard accessible
<div
  role="button"
  tabIndex={0}
  onClick={handleClick}
  onKeyDown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleClick();
    }
  }}
>
  Custom Button
</div>

// ❌ BAD - Mouse only
<div onClick={handleClick}>Custom Button</div>
```

### Rule 3: Add ARIA Labels

```tsx
// ✅ GOOD - Descriptive ARIA label
<button
  onClick={handleDelete}
  aria-label={`Delete character ${characterName}`}
>
  <DeleteIcon />
</button>

// ❌ BAD - No context for screen readers
<button onClick={handleDelete}>
  <DeleteIcon />
</button>
```

### Rule 4: Use Live Regions for Dynamic Content

```tsx
// ✅ GOOD - Screen reader announces changes
<div
  role="status"
  aria-live="polite"
  aria-atomic="true"
>
  {selectedCharacters.length} characters selected
</div>

// ❌ BAD - Silent updates
<div>{selectedCharacters.length} characters selected</div>
```

## Performance Optimization Patterns

### Pattern 1: React.memo for Expensive Components

```tsx
import React from 'react';

interface CharacterCardProps {
  character: string;
  isSelected: boolean;
  onSelect: (character: string) => void;
}

// ✅ GOOD - Prevents unnecessary re-renders
export const CharacterCard = React.memo<CharacterCardProps>(
  ({ character, isSelected, onSelect }) => {
    return (
      <div
        className={`character-card ${isSelected ? 'selected' : ''}`}
        onClick={() => onSelect(character)}
      >
        {character}
      </div>
    );
  }
);

CharacterCard.displayName = 'CharacterCard';
```

### Pattern 2: useCallback for Stable Function References

```tsx
import React, { useCallback } from 'react';

const ParentComponent: React.FC = () => {
  // ✅ GOOD - Stable function reference
  const handleSelect = useCallback((characterName: string) => {
    setSelectedCharacters(prev => 
      prev.includes(characterName)
        ? prev.filter(name => name !== characterName)
        : [...prev, characterName]
    );
  }, []);

  return (
    <>
      {characters.map(char => (
        <CharacterCard
          key={char}
          character={char}
          onSelect={handleSelect} // Same reference on every render
        />
      ))}
    </>
  );
};
```

### Pattern 3: useMemo for Expensive Computations

```tsx
import React, { useMemo } from 'react';

const CharacterList: React.FC = () => {
  // ✅ GOOD - Memoized computation
  const filteredCharacters = useMemo(() => {
    return characters
      .filter(char => char.includes(searchTerm))
      .sort((a, b) => a.localeCompare(b));
  }, [characters, searchTerm]);

  // ✅ GOOD - Set for O(1) lookup
  const selectedSet = useMemo(() => {
    return new Set(selectedCharacters);
  }, [selectedCharacters]);

  const isSelected = useCallback((character: string) => {
    return selectedSet.has(character); // O(1) vs array.includes() O(n)
  }, [selectedSet]);

  return (
    <>
      {filteredCharacters.map(char => (
        <CharacterCard
          key={char}
          character={char}
          isSelected={isSelected(char)}
        />
      ))}
    </>
  );
};
```

### Pattern 4: Code Splitting with React.lazy

```tsx
import React, { Suspense, lazy } from 'react';
import { SkeletonDashboard } from './components/loading';

// ✅ GOOD - Lazy load heavy components
const Dashboard = lazy(() => import('./components/Dashboard'));

const App: React.FC = () => {
  return (
    <Suspense fallback={<SkeletonDashboard />}>
      <Dashboard />
    </Suspense>
  );
};
```

## Custom Hooks

### useFocusTrap Hook

```tsx
import { useEffect, RefObject } from 'react';

export function useFocusTrap(
  elementRef: RefObject<HTMLElement>,
  isActive: boolean
) {
  useEffect(() => {
    if (!isActive || !elementRef.current) return;

    const element = elementRef.current;
    const focusableElements = element.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    
    const firstElement = focusableElements[0] as HTMLElement;
    const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;

      if (e.shiftKey) {
        if (document.activeElement === firstElement) {
          e.preventDefault();
          lastElement?.focus();
        }
      } else {
        if (document.activeElement === lastElement) {
          e.preventDefault();
          firstElement?.focus();
        }
      }
    };

    element.addEventListener('keydown', handleKeyDown);
    firstElement?.focus();

    return () => {
      element.removeEventListener('keydown', handleKeyDown);
    };
  }, [elementRef, isActive]);
}
```

### usePerformance Hook

```tsx
import { usePerformance } from '../hooks/usePerformance';

const MyComponent: React.FC = () => {
  const { getRenderCount, measureInteraction } = usePerformance({
    onMetric: (metric) => {
      console.log(`${metric.name}: ${metric.value}ms (${metric.rating})`);
    },
  });

  const handleClick = () => {
    measureInteraction('button_click', () => {
      // Expensive operation
      processData();
    });
  };

  // Log render count in development
  useEffect(() => {
    if (import.meta.env.DEV) {
      console.log(`Component rendered ${getRenderCount()} times`);
    }
  });

  return <button onClick={handleClick}>Click Me</button>;
};
```

## Performance Profiling

### Measuring Component Re-renders

```tsx
import React, { Profiler } from 'react';

const onRenderCallback = (
  id: string,
  phase: 'mount' | 'update',
  actualDuration: number,
  baseDuration: number,
  startTime: number,
  commitTime: number
) => {
  console.log({
    id,
    phase,
    actualDuration,
    baseDuration,
    startTime,
    commitTime,
  });
};

const App: React.FC = () => {
  return (
    <Profiler id="character-selection" onRender={onRenderCallback}>
      <CharacterSelection />
    </Profiler>
  );
};
```

### Chrome DevTools Performance

1. Open Chrome DevTools → Performance tab
2. Click Record
3. Interact with the application
4. Stop recording
5. Analyze flame graph for slow operations

### React DevTools Profiler

1. Install React DevTools extension
2. Open DevTools → Profiler tab
3. Click Record
4. Interact with the application
5. Stop recording
6. Review component render times

## Testing

### Accessibility Testing with jest-axe

```tsx
import { render } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import { CharacterCard } from './CharacterCard';

expect.extend(toHaveNoViolations);

test('CharacterCard should have no accessibility violations', async () => {
  const { container } = render(
    <CharacterCard
      character="Aragorn"
      isSelected={false}
      onSelect={jest.fn()}
    />
  );

  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

### Keyboard Navigation Testing

```tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CharacterCard } from './CharacterCard';

test('CharacterCard should be selectable via keyboard', async () => {
  const onSelect = jest.fn();
  const user = userEvent.setup();

  render(
    <CharacterCard
      character="Aragorn"
      isSelected={false}
      onSelect={onSelect}
    />
  );

  const card = screen.getByRole('button');
  
  // Tab to focus
  await user.tab();
  expect(card).toHaveFocus();

  // Press Enter to select
  await user.keyboard('{Enter}');
  expect(onSelect).toHaveBeenCalledWith('Aragorn');
});
```

### Performance Testing

```tsx
import React from 'react';
import { render } from '@testing-library/react';
import { CharacterCard } from './CharacterCard';

test('CharacterCard should NOT re-render when props unchanged', () => {
  let renderCount = 0;

  const RenderTracker: React.FC = (props) => {
    renderCount++;
    return <CharacterCard {...props} />;
  };

  const { rerender } = render(
    <RenderTracker
      character="Aragorn"
      isSelected={false}
      onSelect={jest.fn()}
    />
  );

  expect(renderCount).toBe(1);

  // Re-render with same props
  rerender(
    <RenderTracker
      character="Aragorn"
      isSelected={false}
      onSelect={jest.fn()}
    />
  );

  // Should re-render because onSelect is new function
  // To prevent this, wrap onSelect with useCallback in parent
  expect(renderCount).toBe(2);
});
```

## Common Pitfalls

### ❌ Creating New Functions in Render

```tsx
// BAD - Creates new function on every render
{characters.map(char => (
  <CharacterCard
    key={char}
    character={char}
    onSelect={() => handleSelect(char)} // New function every render!
  />
))}

// GOOD - Use data attributes instead
const handleCardSelect = useCallback((e: React.MouseEvent) => {
  const character = e.currentTarget.dataset.character;
  if (character) handleSelect(character);
}, [handleSelect]);

{characters.map(char => (
  <CharacterCard
    key={char}
    character={char}
    data-character={char}
    onClick={handleCardSelect} // Same function reference
  />
))}
```

### ❌ Missing Dependency Arrays

```tsx
// BAD - Missing dependencies
const filteredCharacters = useMemo(() => {
  return characters.filter(char => char.includes(searchTerm));
}, []); // Missing dependencies!

// GOOD - Correct dependencies
const filteredCharacters = useMemo(() => {
  return characters.filter(char => char.includes(searchTerm));
}, [characters, searchTerm]);
```

### ❌ Inaccessible Custom Components

```tsx
// BAD - No keyboard support
<div className="button" onClick={handleClick}>
  Click Me
</div>

// GOOD - Keyboard accessible
<div
  role="button"
  tabIndex={0}
  onClick={handleClick}
  onKeyDown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleClick();
    }
  }}
  aria-label="Click me button"
>
  Click Me
</div>

// BETTER - Use semantic HTML
<button onClick={handleClick}>Click Me</button>
```

## CI/CD Integration

### Pre-commit Hooks

```json
// package.json
{
  "husky": {
    "hooks": {
      "pre-commit": "npm run lint && npm run type-check",
      "pre-push": "npm test"
    }
  }
}
```

### GitHub Actions

See `.github/workflows/lighthouse-ci.yml` for automated Lighthouse audits on every PR.

## Resources

- **Internal Docs**: `/docs/accessibility.md`
- **Custom Hooks**: `/frontend/src/hooks/`
- **Test Examples**: `/frontend/tests/`
- **Performance Guide**: Web Vitals dashboard in production

## Support

For questions or issues:
- Review `/docs/accessibility.md`
- Check existing components for patterns
- Run `npm test -- accessibility` for automated checks
- Use Chrome Lighthouse for performance audits
