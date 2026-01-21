# Writing Fast Frontend Tests: Best Practices Guide

This guide provides actionable patterns for writing fast, reliable frontend unit tests based on optimizations applied to the Novel Engine frontend test suite.

---

## Quick Reference

| Pattern | Time Impact | Difficulty | When to Use |
|---------|-------------|------------|-------------|
| Share providers across tests | 🟢🟢🟢 High (100-200ms/file) | Easy | Always |
| Remove unnecessary `waitFor` | 🟢🟢 Medium (50-100ms/test) | Easy | Synchronous operations |
| Mock heavy child components | 🟢🟢🟢 High (50-150ms/component) | Easy | Integration tests |
| Use fake timers | 🟢🟢🟢 Very High (seconds) | Medium | Tests with delays |
| Test in isolation | 🟢🟢 Medium (100-300ms/test) | Medium | Unit tests |

---

## Pattern 1: Share Providers Across Tests

### ❌ SLOW (recreates on every test)
```typescript
// CharacterCreationDialog.test.tsx
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  const theme = createTheme();

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        {children}
      </ThemeProvider>
    </QueryClientProvider>
  );
};

describe('Component', () => {
  it('test 1', () => {
    render(<Component />, { wrapper: createWrapper() }); // New instances
  });

  it('test 2', () => {
    render(<Component />, { wrapper: createWrapper() }); // New instances again
  });
});
```

**Cost**: 100-200ms per test (creating QueryClient + Theme)

### ✅ FAST (shares instances, clears state)
```typescript
// Create once at module level
const sharedQueryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false, cacheTime: 0 },
    mutations: { retry: false },
  },
});

const sharedTheme = createTheme();

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={sharedQueryClient}>
    <ThemeProvider theme={sharedTheme}>
      {children}
    </ThemeProvider>
  </QueryClientProvider>
);

describe('Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sharedQueryClient.clear(); // Clear cache, not recreate!
  });

  it('test 1', () => {
    render(<Component />, { wrapper }); // Reuses instances
  });

  it('test 2', () => {
    render(<Component />, { wrapper }); // Reuses instances
  });
});
```

**Savings**: 100-200ms per test
**Why it works**: Object creation is expensive, clearing state is cheap

---

## Pattern 2: Remove Unnecessary `waitFor`

### ❌ SLOW (waits for synchronous operation)
```typescript
it('validates required fields', async () => {
  render(<CharacterCreationDialog {...mockProps} />);

  const submitButton = screen.getByRole('button', { name: /create/i });
  fireEvent.click(submitButton); // Synchronous!

  await waitFor(() => {
    expect(screen.getByText('Name is required')).toBeInTheDocument();
  });
});
```

**Cost**: 50-100ms (unnecessary async polling)

### ✅ FAST (synchronous assertion)
```typescript
it('validates required fields', () => {
  render(<CharacterCreationDialog {...mockProps} />);

  const submitButton = screen.getByRole('button', { name: /create/i });
  fireEvent.click(submitButton); // Synchronous validation

  // No waitFor needed - validation is immediate!
  expect(screen.getByText('Name is required')).toBeInTheDocument();
});
```

**Savings**: 50-100ms per test
**Why it works**: `fireEvent` and `userEvent` are synchronous unless they trigger async effects

### When to use `waitFor`:
```typescript
// ✅ CORRECT: Waiting for async data fetch
await waitFor(() => {
  expect(screen.getByText('Data loaded')).toBeInTheDocument();
});

// ✅ CORRECT: Waiting for animation/transition
await waitFor(() => {
  expect(screen.getByTestId('modal')).toHaveClass('visible');
});

// ❌ WRONG: Synchronous DOM update
fireEvent.click(button);
await waitFor(() => {
  expect(handler).toHaveBeenCalled(); // handler is called sync!
});
```

---

## Pattern 3: Mock Heavy Child Components

### ❌ SLOW (renders entire component tree)
```typescript
// workflows.test.tsx
const TestApp = () => (
  <Box>
    <Navbar /> {/* Renders Drawer, Menu, AppBar, etc. */}
    <Routes>
      <Route path="/" element={<Dashboard />} /> {/* Renders charts, SSE, queries */}
      <Route path="/monitor" element={<SystemMonitor />} /> {/* Renders WebSocket, metrics */}
      <Route path="/workshop" element={<StoryWorkshop />} /> {/* Heavy form component */}
    </Routes>
  </Box>
);

it('should render app', async () => {
  render(<TestApp />); // Renders EVERYTHING!
  await waitFor(() => expect(document.body).toBeInTheDocument());
});
```

**Cost**: 200-600ms (rendering heavy components + all their hooks/queries)

### ✅ FAST (mocks child components)
```typescript
// Mock heavy components at module level
vi.mock('../components/Dashboard', () => ({
  default: () => <div data-testid="dashboard">Dashboard Mock</div>
}));

vi.mock('../components/SystemMonitor', () => ({
  default: () => <div data-testid="monitor">Monitor Mock</div>
}));

vi.mock('../components/StoryWorkshop', () => ({
  default: () => <div data-testid="workshop">Workshop Mock</div>
}));

vi.mock('../components/Navbar', () => ({
  default: () => <nav data-testid="navbar">Navbar Mock</nav>
}));

// Same TestApp definition, but uses mocks
it('should render app', () => {
  render(<TestApp />);
  expect(screen.getByTestId('navbar')).toBeInTheDocument();
  // No waitFor, mocks are lightweight!
});
```

**Savings**: 200-600ms per test
**Why it works**: Mocks bypass complex rendering, hooks, and API calls

### When to mock:
- ✅ Components with heavy rendering (charts, 3D graphics)
- ✅ Components with async effects (SSE, WebSocket)
- ✅ Components making API calls
- ✅ Third-party components (react-dropzone, react-beautiful-dnd)

### When NOT to mock:
- ❌ Components you're actually testing
- ❌ Leaf components (buttons, inputs) - they're fast
- ❌ Integration tests where you need full behavior

---

## Pattern 4: Use Fake Timers

### ❌ SLOW (real delay)
```typescript
it('shows loading state then content', async () => {
  render(<AsyncComponent />);

  expect(screen.getByText('Loading...')).toBeInTheDocument();

  // Wait for real 2 second delay
  await waitFor(() => {
    expect(screen.getByText('Content loaded!')).toBeInTheDocument();
  }, { timeout: 3000 });
});
```

**Cost**: 2000ms+ (real time delay)

### ✅ FAST (fake timers)
```typescript
describe('AsyncComponent', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('shows loading state then content', async () => {
    render(<AsyncComponent />);

    expect(screen.getByText('Loading...')).toBeInTheDocument();

    // Instantly fast-forward 2 seconds
    act(() => {
      vi.advanceTimersByTime(2000);
    });

    expect(screen.getByText('Content loaded!')).toBeInTheDocument();
  });
});
```

**Savings**: Seconds per test
**Why it works**: Fake timers run instantly, no real waiting

### Common scenarios:
```typescript
// Debounced input
act(() => {
  vi.advanceTimersByTime(500); // Skip 500ms debounce
});

// Polling interval
act(() => {
  vi.advanceTimersByTime(1000); // Trigger next poll
});

// Timeout
act(() => {
  vi.advanceTimersByTime(5000); // Skip to timeout
});

// Run all pending timers
act(() => {
  vi.runAllTimers();
});
```

---

## Pattern 5: Test Components in Isolation

### ❌ SLOW (integration test as unit test)
```typescript
// Testing navigation by rendering entire app
it('should navigate to character studio', async () => {
  render(
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <MemoryRouter>
          <App /> {/* Entire app with all routes! */}
        </MemoryRouter>
      </ThemeProvider>
    </QueryClientProvider>
  );

  fireEvent.click(screen.getByRole('button', { name: /characters/i }));

  await waitFor(() => {
    expect(screen.getByText('Character Studio')).toBeInTheDocument();
  });
});
```

**Cost**: 400-600ms (full app render + navigation)

### ✅ FAST (unit test in isolation)
```typescript
// Test Navbar navigation logic in isolation
it('calls onNavigate when character button clicked', () => {
  const mockOnNavigate = vi.fn();

  render(<Navbar onNavigate={mockOnNavigate} />);

  fireEvent.click(screen.getByRole('button', { name: /characters/i }));

  expect(mockOnNavigate).toHaveBeenCalledWith('/characters');
});

// Separate integration test (in e2e or integration suite)
it('end-to-end navigation', async () => {
  // Full app test goes here
});
```

**Savings**: 300-500ms per test
**Why it works**: Tests only what's necessary, avoids heavy providers

### Guidelines:
- **Unit tests**: Test single component, minimal providers
- **Integration tests**: Test component interactions, necessary providers only
- **E2E tests**: Full app with all providers (use Playwright, not Vitest)

---

## Pattern 6: Avoid Vague `waitFor` Conditions

### ❌ SLOW (always-true condition)
```typescript
it('renders app', async () => {
  render(<App />);

  await waitFor(() => {
    expect(document.body).toBeInTheDocument(); // Always true!
  });

  expect(screen.getByText('Welcome')).toBeInTheDocument();
});
```

**Cost**: 50-100ms (pointless polling loop)

### ✅ FAST (specific assertion)
```typescript
it('renders app', () => {
  render(<App />);

  // Test specific element, no waiting
  expect(screen.getByText('Welcome')).toBeInTheDocument();
});
```

**Savings**: 50-100ms per test

### Good `waitFor` conditions:
```typescript
// ✅ GOOD: Waiting for specific state change
await waitFor(() => {
  expect(screen.getByText('Data loaded')).toBeInTheDocument();
});

// ✅ GOOD: Waiting for element to disappear
await waitFor(() => {
  expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
});

// ❌ BAD: Vague/always-true
await waitFor(() => {
  expect(document.body).toBeInTheDocument();
});

// ❌ BAD: Testing implementation details
await waitFor(() => {
  expect(component.state.loaded).toBe(true);
});
```

---

## Pattern 7: Minimize Provider Nesting

### ❌ SLOW (unnecessary providers)
```typescript
it('tests button click', () => {
  render(
    <QueryClientProvider client={queryClient}>
      <StoreProvider store={store}>
        <ThemeProvider theme={theme}>
          <MemoryRouter>
            <SimpleButton onClick={handler}>Click me</SimpleButton>
          </MemoryRouter>
        </ThemeProvider>
      </StoreProvider>
    </QueryClientProvider>
  );

  fireEvent.click(screen.getByText('Click me'));
  expect(handler).toHaveBeenCalled();
});
```

**Cost**: 100-200ms (provider initialization)

### ✅ FAST (minimal providers)
```typescript
it('tests button click', () => {
  // Button doesn't need routing, store, or queries!
  render(
    <ThemeProvider theme={theme}>
      <SimpleButton onClick={handler}>Click me</SimpleButton>
    </ThemeProvider>
  );

  fireEvent.click(screen.getByText('Click me'));
  expect(handler).toHaveBeenCalled();
});

// Or even simpler:
it('tests button click', () => {
  render(<SimpleButton onClick={handler}>Click me</SimpleButton>);

  fireEvent.click(screen.getByText('Click me'));
  expect(handler).toHaveBeenCalled();
});
```

**Savings**: 50-150ms per test
**Why it works**: Only pay for what you use

### Provider checklist:
- ❓ Does component use routing? → Need `MemoryRouter`
- ❓ Does component use a shared store? → Add provider if required by your store setup
- ❓ Does component use queries? → Need `QueryClientProvider`
- ❓ Does component rely on a theme provider? → Add the provider if required

If NO to all → Don't add any providers!

---

## Pattern 8: Batch Related Assertions

### ❌ SLOW (multiple renders)
```typescript
it('validates form', () => {
  render(<Form />);

  fireEvent.click(submitButton);

  expect(screen.getByText('Name required')).toBeInTheDocument();

  // Component re-renders to clear error
  fireEvent.change(nameInput, { target: { value: 'John' } });

  expect(screen.queryByText('Name required')).not.toBeInTheDocument();

  // Another re-render
  fireEvent.change(emailInput, { target: { value: 'invalid' } });

  expect(screen.getByText('Invalid email')).toBeInTheDocument();
});
```

**Cost**: Multiple re-renders can add up (30-50ms each)

### ✅ FAST (grouped interactions)
```typescript
it('validates form', () => {
  render(<Form />);

  // Test all validation errors at once
  fireEvent.click(submitButton);

  expect(screen.getByText('Name required')).toBeInTheDocument();
  expect(screen.getByText('Email required')).toBeInTheDocument();

  // Fix all at once
  fireEvent.change(nameInput, { target: { value: 'John' } });
  fireEvent.change(emailInput, { target: { value: 'john@example.com' } });

  expect(screen.queryByText('Name required')).not.toBeInTheDocument();
  expect(screen.queryByText('Email required')).not.toBeInTheDocument();
});
```

**Savings**: 20-40ms per test
**Why it works**: Fewer renders, assertions run immediately

---

## Pattern 9: Use userEvent Over fireEvent (Carefully)

### ⚠️ SLOWER (but more realistic)
```typescript
import userEvent from '@testing-library/user-event';

it('types in input', async () => {
  const user = userEvent.setup();
  render(<SearchInput />);

  // Simulates real typing (slower but accurate)
  await user.type(screen.getByRole('textbox'), 'search query');

  expect(screen.getByRole('textbox')).toHaveValue('search query');
});
```

**Cost**: +30-50ms (but more realistic)

### ⚡ FASTER (but less realistic)
```typescript
it('types in input', () => {
  render(<SearchInput />);

  // Instant change (fast but less realistic)
  fireEvent.change(screen.getByRole('textbox'), {
    target: { value: 'search query' }
  });

  expect(screen.getByRole('textbox')).toHaveValue('search query');
});
```

**Savings**: 30-50ms per interaction

### When to use each:
- `fireEvent`: Unit tests, simple interactions, speed priority
- `userEvent`: Integration tests, complex interactions, accuracy priority

---

## Pattern 10: Profile and Optimize Hot Paths

### Find slow tests:
```bash
# Run tests with timing
npm test -- --run --reporter=verbose 2>&1 | tee test-output.log

# Extract slowest tests
grep "✓.*ms" test-output.log | \
  sed 's/\x1b\[[0-9;]*m//g' | \
  sort -t' ' -k$(NF) -rn | \
  head -20
```

### Optimize in order:
1. **First**: Tests >500ms (biggest impact)
2. **Second**: Tests 200-500ms (medium impact)
3. **Last**: Tests <200ms (usually fast enough)

### Measure impact:
```bash
# Before optimization
npm test -- --run | grep "Tests.*passed"

# After optimization
npm test -- --run | grep "Tests.*passed"

# Compare times
```

---

## Checklist: Writing a Fast Test

✅ **Before writing:**
- [ ] Is this a unit test? → Minimal providers
- [ ] Does it need full app? → Probably an E2E test
- [ ] What's the smallest testable unit?

✅ **While writing:**
- [ ] Shared providers at module level?
- [ ] Mocked heavy child components?
- [ ] Using specific assertions (no `document.body`)?
- [ ] Only necessary providers?

✅ **After writing:**
- [ ] Removed unnecessary `await waitFor`?
- [ ] Used fake timers for delays?
- [ ] Test runs in <200ms for unit tests?
- [ ] Test runs in <500ms for integration tests?

✅ **Before committing:**
- [ ] All tests pass?
- [ ] No performance regression?
- [ ] CI will run in reasonable time?

---

## Example: Refactoring a Slow Test

### BEFORE: 516ms
```typescript
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  const theme = createTheme();

  return ({ children }) => (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        {children}
      </ThemeProvider>
    </QueryClientProvider>
  );
};

it('renders dialog', async () => {
  render(<CharacterCreationDialog open onClose={vi.fn()} />, {
    wrapper: createWrapper(), // New instances every time!
  });

  await waitFor(() => {
    expect(screen.getByText('Create Character')).toBeInTheDocument();
  });
});
```

### AFTER: ~250ms (51% faster!)
```typescript
// Module-level shared instances
const sharedQueryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false },
    mutations: { retry: false },
  },
});
const sharedTheme = createTheme();

const wrapper = ({ children }) => (
  <QueryClientProvider client={sharedQueryClient}>
    <ThemeProvider theme={sharedTheme}>
      {children}
    </ThemeProvider>
  </QueryClientProvider>
);

beforeEach(() => {
  sharedQueryClient.clear(); // Clear, don't recreate
});

it('renders dialog', () => {
  render(<CharacterCreationDialog open onClose={vi.fn()} />, {
    wrapper, // Reused instances!
  });

  // Synchronous render, no waitFor needed
  expect(screen.getByText('Create Character')).toBeInTheDocument();
});
```

**Changes made**:
1. ✅ Shared QueryClient and Theme
2. ✅ Removed unnecessary `waitFor`
3. ✅ Clear state in `beforeEach` instead of recreating

**Result**: 516ms → 250ms (**51% faster**)

---

## Common Anti-Patterns to Avoid

### 1. Creating new mocks in every test
```typescript
// ❌ BAD
it('test', () => {
  const mockFn = vi.fn();
  // ...
});

// ✅ GOOD (if used across tests)
const mockFn = vi.fn();
beforeEach(() => {
  mockFn.mockClear();
});
```

### 2. Not cleaning up after tests
```typescript
// ❌ BAD
it('test with SSE', () => {
  const eventSource = new EventSource('/events');
  // ... test ...
  // EventSource not closed! Leaks!
});

// ✅ GOOD
it('test with SSE', () => {
  const eventSource = new EventSource('/events');
  // ... test ...
  eventSource.close(); // Clean up
});
```

### 3. Testing implementation details
```typescript
// ❌ BAD
expect(component.state.loading).toBe(true);

// ✅ GOOD
expect(screen.getByText('Loading...')).toBeInTheDocument();
```

### 4. Over-mocking
```typescript
// ❌ BAD (mocking everything makes test useless)
vi.mock('./Button');
vi.mock('./Input');
vi.mock('./Form');
// ... test nothing but mocks

// ✅ GOOD (mock external dependencies, test your code)
vi.mock('axios');
// Test Form with real Button and Input
```

---

## Performance Budget

**Unit Test Performance Budget**:
- 🟢 **Target**: <200ms per test
- 🟡 **Acceptable**: 200-500ms per test
- 🔴 **Needs Optimization**: >500ms per test

**Integration Test Performance Budget**:
- 🟢 **Target**: <500ms per test
- 🟡 **Acceptable**: 500-1000ms per test
- 🔴 **Needs Optimization**: >1000ms per test

**Full Test Suite Performance Budget**:
- 🟢 **Target**: <10s for 100+ tests
- 🟡 **Acceptable**: 10-30s for 100+ tests
- 🔴 **Needs Optimization**: >30s for 100+ tests

---

## Tools and Commands

### Run tests with timing
```bash
npm test -- --run --reporter=verbose
```

### Find slow tests
```bash
npm test -- --run --reporter=verbose 2>&1 | \
  grep "✓.*ms" | \
  sed 's/\x1b\[[0-9;]*m//g' | \
  sort -rn | \
  head -20
```

### Profile a specific test
```bash
npm test -- --run path/to/test.test.tsx
```

### Run only slow tests
```bash
# Tag slow tests
it.skip('slow test', () => { /* ... */ });

# Or use grep filter
npm test -- --run --grep "slow"
```

---

## Summary

**Key Takeaways**:
1. ✅ Share expensive objects (QueryClient, Theme, Store)
2. ✅ Remove unnecessary `waitFor` for sync operations
3. ✅ Mock heavy child components in integration tests
4. ✅ Use fake timers for delays
5. ✅ Test components in isolation when possible
6. ✅ Minimize provider nesting
7. ✅ Profile and optimize hot paths first
8. ✅ Use specific, synchronous assertions

**Impact**:
- **High Priority** patterns save 100-600ms per test
- **Medium Priority** patterns save 50-100ms per test
- **Low Priority** patterns save 20-50ms per test

**When in Doubt**:
1. Can I remove this `waitFor`? (Usually yes if synchronous)
2. Can I mock this heavy component? (Usually yes for integration tests)
3. Can I share this provider? (Almost always yes)

Happy testing! 🚀

---

**Last Updated**: November 25, 2025
**Test Framework**: Vitest + React Testing Library
**Based On**: Novel Engine frontend test suite optimization
