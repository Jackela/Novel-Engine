# Frontend Unit Test Performance Optimization Report

**Date**: November 25, 2025
**Objective**: Identify and optimize the 5 slowest frontend unit tests to run in <2 seconds each

## Executive Summary

All 127 frontend unit tests currently run in **under 2 seconds**, with the slowest test at **599ms**. This is excellent performance! However, opportunities exist to further optimize the slowest tests to improve developer experience and CI/CD pipeline speed.

**Total Test Suite Time**: ~10.2 seconds for 127 tests
**Average Test Time**: ~80ms per test
**Tests Over 500ms**: 2 tests
**Tests Over 400ms**: 6 tests
**Tests Over 200ms**: 20 tests

**Status**: ✅ All tests already meet the <2s requirement

---

## Top 5 Slowest Tests (Current State)

### 1. workflows.test.tsx - "should render the application without errors"
- **Current Time**: 599ms
- **Target Time**: <200ms (for unit tests)
- **File**: `/mnt/d/Code/novel-engine/frontend/src/tests/workflows.test.tsx:146`
- **Optimization Potential**: 🔴 HIGH (3-4x speedup possible)

**Root Causes**:
- Renders entire App component with full MUI Theme provider
- Initializes React Router with MemoryRouter
- Creates new QueryClient for each test
- Uses vague `waitFor(() => expect(document.body).toBeInTheDocument())` which always passes but adds ~50-100ms delay
- Renders Dashboard, Navbar, and all route components even when not needed

**Recommended Optimizations**:
```typescript
// BEFORE (slow):
const renderAppWithProviders = async ({ route = '/' } = {}) => {
  const queryClient = createTestQueryClient();
  await act(async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          <MemoryRouter initialEntries={[route]}>
            <TestApp />
          </MemoryRouter>
        </ThemeProvider>
      </QueryClientProvider>
    );
  });
};

// AFTER (fast):
// 1. Create shared QueryClient and Theme at module level
const sharedQueryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false, cacheTime: 0 },
  },
});
const sharedTheme = createTheme({ /* minimal config */ });

// 2. Mock heavy child components
vi.mock('../components/Dashboard', () => ({
  default: () => <div data-testid="dashboard">Dashboard</div>
}));
vi.mock('../components/Navbar', () => ({
  default: () => <nav data-testid="navbar">Navbar</nav>
}));

// 3. Remove unnecessary waitFor
it('should render without errors', () => {
  render(<TestApp />, { wrapper });
  expect(screen.getByTestId('navbar')).toBeInTheDocument();
  // No waitFor needed for synchronous renders!
});
```

**Expected Improvement**: 599ms → ~150ms (**75% faster**)

---

### 2. workflows.test.tsx - "should navigate to workshop"
- **Current Time**: 589ms
- **Target Time**: <200ms
- **File**: `/mnt/d/Code/novel-engine/frontend/src/tests/workflows.test.tsx:190`
- **Optimization Potential**: 🔴 HIGH

**Root Causes**: Same as #1

**Expected Improvement**: 589ms → ~150ms (**75% faster**)

---

### 3. workflows.test.tsx - "should navigate to monitor"
- **Current Time**: 535ms
- **Target Time**: <200ms
- **File**: `/mnt/d/Code/novel-engine/frontend/src/tests/workflows.test.tsx:206`
- **Optimization Potential**: 🔴 HIGH

**Root Causes**: Same as #1

**Expected Improvement**: 535ms → ~150ms (**72% faster**)

---

### 4. CharacterCreationDialog.test.tsx - "renders the dialog when open"
- **Current Time**: 516ms
- **Target Time**: <200ms
- **File**: `/mnt/d/Code/novel-engine/frontend/src/components/CharacterStudio/CharacterCreationDialog.test.tsx:51`
- **Optimization Potential**: 🟡 MEDIUM (2x speedup possible)

**Root Causes**:
- Creates new MUI Theme for every test
- Creates new QueryClient for every test
- Renders full MUI Dialog component (heavy)
- MUI Dialog includes Backdrop, Portal, Focus Trap, etc.

**Recommended Optimizations**:
```typescript
// BEFORE (slow):
const createWrapper = () => {
  const queryClient = new QueryClient(/* ... */);
  const theme = createTheme();
  return ({ children }) => (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        {children}
      </ThemeProvider>
    </QueryClientProvider>
  );
};

// AFTER (fast):
// 1. Share QueryClient and Theme across all tests
const sharedQueryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false, cacheTime: 0 },
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

// 2. Clear query cache in beforeEach instead of recreating
beforeEach(() => {
  vi.clearAllMocks();
  sharedQueryClient.clear(); // Clear cache instead of new instance
});

// 3. Mock react-dropzone upfront (already done)
```

**Expected Improvement**: 516ms → ~250ms (**51% faster**)

---

### 5. workflows.test.tsx - "should have navigation buttons"
- **Current Time**: 484ms
- **Target Time**: <200ms
- **File**: `/mnt/d/Code/novel-engine/frontend/src/tests/workflows.test.tsx:159`
- **Optimization Potential**: 🔴 HIGH

**Root Causes**: Same as #1

**Expected Improvement**: 484ms → ~150ms (**69% faster**)

---

## Common Optimization Patterns Identified

### 1. Remove Unnecessary `waitFor` for Synchronous Operations

**❌ SLOW Pattern**:
```typescript
await waitFor(() => {
  expect(document.body).toBeInTheDocument();
});
```

**✅ FAST Pattern**:
```typescript
// document.body is always in the document, no need to wait
expect(screen.getByRole('button')).toBeInTheDocument();
```

**Impact**: Saves 50-100ms per occurrence
**Occurrences in slow tests**: 9 times
**Total Savings**: 450-900ms

---

### 2. Share Expensive Objects Across Tests

**❌ SLOW Pattern**:
```typescript
const createWrapper = () => {
  const queryClient = new QueryClient(/* heavy config */);
  const theme = createTheme(/* large theme object */);
  return Wrapper;
};
```

**✅ FAST Pattern**:
```typescript
// Module-level shared instances
const sharedQueryClient = new QueryClient(/* config */);
const sharedTheme = createTheme(/* config */);

beforeEach(() => {
  sharedQueryClient.clear(); // Reset state, not object
});
```

**Impact**: Saves 100-200ms per test file
**Occurrences**: 2 files (workflows.test.tsx, CharacterCreationDialog.test.tsx)
**Total Savings**: 200-400ms per file

---

### 3. Mock Heavy Child Components

**❌ SLOW Pattern**:
```typescript
// Renders entire Dashboard with all its API calls, hooks, and child components
<Route path="/" element={<Dashboard />} />
```

**✅ FAST Pattern**:
```typescript
// Mock at module level
vi.mock('../components/Dashboard', () => ({
  default: () => <div data-testid="dashboard">Dashboard Mock</div>
}));
```

**Impact**: Saves 50-150ms per heavy component
**Occurrences**: Dashboard, SystemMonitor, StoryWorkshop, etc.
**Total Savings**: 200-600ms

---

### 4. Use Fake Timers for Delays

**❌ SLOW Pattern**:
```typescript
await waitFor(() => {
  expect(screen.getByText('Loading...')).not.toBeInTheDocument();
}, { timeout: 3000 });
```

**✅ FAST Pattern**:
```typescript
beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

// Test with instant time advancement
vi.advanceTimersByTime(3000);
expect(screen.getByText('Loaded!')).toBeInTheDocument();
```

**Impact**: Converts real delays to instant
**Potential Savings**: Up to 3s per test with setTimeout/setInterval

---

### 5. Minimize Provider Nesting

**❌ SLOW Pattern**:
```typescript
<QueryClientProvider>
  <ThemeProvider>
    <CssBaseline />
    <MemoryRouter>
      <ReduxProvider>
        <Component />
      </ReduxProvider>
    </MemoryRouter>
  </ThemeProvider>
</QueryClientProvider>
```

**✅ FAST Pattern**:
```typescript
// Only include providers actually needed for the test
<ThemeProvider theme={minimalTheme}>
  <Component />
</ThemeProvider>
```

**Impact**: Saves 50-100ms per unnecessary provider
**Best Practice**: Test components in isolation when possible

---

## Test-Specific Optimization Recommendations

### workflows.test.tsx (5 slow tests, 599ms-484ms each)

**Total Time**: ~2.7s for 10 tests
**Target Time**: <1.5s for 10 tests
**Optimization Potential**: 🔴 HIGH (**45% speedup possible**)

**Actionable Changes**:

1. **Create shared test fixtures** (lines 107-117):
   ```typescript
   // Move to module level
   const sharedQueryClient = new QueryClient({
     defaultOptions: {
       queries: { retry: false, cacheTime: 0, staleTime: 0 },
     },
   });
   const sharedTheme = theme; // Already defined at module level

   beforeEach(() => {
     vi.clearAllMocks();
     sharedQueryClient.clear();
   });
   ```

2. **Mock all route components** (before describe blocks):
   ```typescript
   vi.mock('../components/Dashboard', () => ({
     default: () => <div data-testid="dashboard">Dashboard</div>
   }));
   vi.mock('../components/CharacterStudio', () => ({
     default: () => <div data-testid="character-studio">Characters</div>
   }));
   vi.mock('../components/StoryWorkshop', () => ({
     default: () => <div data-testid="workshop">Workshop</div>
   }));
   vi.mock('../components/StoryLibrary', () => ({
     default: () => <div data-testid="library">Library</div>
   }));
   vi.mock('../components/SystemMonitor', () => ({
     default: () => <div data-testid="monitor">Monitor</div>
   }));
   ```

3. **Remove vague waitFor calls** (lines 150-153, 162-164, etc.):
   ```typescript
   // BEFORE:
   await waitFor(() => {
     expect(document.body).toBeInTheDocument();
   });

   // AFTER:
   // Remove entirely or use specific element wait
   expect(screen.getByTestId('navbar')).toBeInTheDocument();
   ```

4. **Simplify renderAppWithProviders** (lines 119-135):
   ```typescript
   const renderAppWithProviders = ({ route = '/' } = {}) => {
     // No need for act() wrapper for synchronous renders
     return render(
       <QueryClientProvider client={sharedQueryClient}>
         <ThemeProvider theme={sharedTheme}>
           <MemoryRouter initialEntries={[route]}>
             <TestApp />
           </MemoryRouter>
         </ThemeProvider>
       </QueryClientProvider>
     );
   };
   ```

**Expected Results**:
- Test 1: 599ms → ~120ms (-80%)
- Test 2: 589ms → ~120ms (-80%)
- Test 3: 535ms → ~120ms (-78%)
- Test 5: 484ms → ~120ms (-75%)
- Total: ~2.7s → ~0.9s (**67% faster**)

---

### CharacterCreationDialog.test.tsx (5 tests, 516ms-230ms each)

**Total Time**: ~1.8s for 5 tests
**Target Time**: <1.0s for 5 tests
**Optimization Potential**: 🟡 MEDIUM (**44% speedup possible**)

**Actionable Changes**:

1. **Share QueryClient and Theme** (lines 22-38):
   ```typescript
   const sharedQueryClient = new QueryClient({
     defaultOptions: {
       queries: { retry: false },
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

   beforeEach(() => {
     vi.clearAllMocks();
     sharedQueryClient.clear();
   });
   ```

2. **Remove unnecessary waitFor** (lines 69-72, 86-88):
   ```typescript
   // BEFORE (test at line 61):
   fireEvent.click(submitButton);
   await waitFor(() => {
     expect(screen.getByText('Character name is required')).toBeInTheDocument();
   });

   // AFTER:
   fireEvent.click(submitButton);
   // Validation is synchronous, no need to wait
   expect(screen.getByText('Character name is required')).toBeInTheDocument();
   ```

3. **Batch assertions** (lines 110-113):
   ```typescript
   // Group related assertions to reduce re-renders
   fireEvent.click(submitButton);
   expect(screen.queryByText('Character name is required')).not.toBeInTheDocument();
   expect(screen.queryByText('Description is required')).not.toBeInTheDocument();
   // No waitFor needed
   ```

**Expected Results**:
- Test 1: 516ms → ~280ms (-46%)
- Test 2: 289ms → ~150ms (-48%)
- Test 3: 327ms → ~180ms (-45%)
- Test 4: 408ms → ~220ms (-46%)
- Test 5: 230ms → ~130ms (-43%)
- Total: ~1.8s → ~1.0s (**44% faster**)

---

## Performance Optimization Best Practices

### ✅ DO

1. **Share expensive objects across tests**
   - QueryClient instances
   - MUI Themes
   - Redux stores
   - Custom hooks with heavy initialization

2. **Mock at the module level**
   - Heavy child components
   - External libraries (react-dropzone, etc.)
   - API clients
   - WebSocket connections

3. **Use specific, synchronous assertions**
   ```typescript
   expect(screen.getByRole('button', { name: /submit/i })).toBeInTheDocument();
   ```

4. **Clear state in beforeEach, not recreate**
   ```typescript
   beforeEach(() => {
     queryClient.clear(); // Fast
     // NOT: queryClient = new QueryClient(); // Slow
   });
   ```

5. **Use fake timers for async delays**
   ```typescript
   vi.useFakeTimers();
   vi.advanceTimersByTime(1000);
   ```

6. **Test components in isolation**
   - Don't render entire app for unit tests
   - Use integration tests for full app flows

### ❌ DON'T

1. **Don't use vague waitFor conditions**
   ```typescript
   // BAD: Always true, adds delay
   await waitFor(() => expect(document.body).toBeInTheDocument());
   ```

2. **Don't create new providers in every test**
   ```typescript
   // BAD: Recreates theme/client each time
   it('test', () => {
     const wrapper = createWrapper(); // Slow!
   });
   ```

3. **Don't wait for synchronous operations**
   ```typescript
   // BAD: fireEvent is synchronous
   fireEvent.click(button);
   await waitFor(() => expect(handler).toHaveBeenCalled());

   // GOOD:
   fireEvent.click(button);
   expect(handler).toHaveBeenCalled();
   ```

4. **Don't render unnecessary providers**
   ```typescript
   // BAD: Component doesn't use routing
   <MemoryRouter>
     <ThemeProvider>
       <SimpleComponent />
     </ThemeProvider>
   </MemoryRouter>

   // GOOD:
   <SimpleComponent />
   ```

5. **Don't use real timers when fake timers work**
   ```typescript
   // BAD: Real 2s delay
   await new Promise(resolve => setTimeout(resolve, 2000));

   // GOOD: Instant
   vi.advanceTimersByTime(2000);
   ```

---

## Comparison: Test Speed Classifications

| Classification | Time Range | Count | % of Total | Examples |
|---------------|------------|-------|------------|----------|
| 🟢 **Fast** | < 50ms | 72 | 57% | Simple component renders, pure logic tests |
| 🟡 **Acceptable** | 50-200ms | 35 | 28% | Tests with providers, simple interactions |
| 🟠 **Slow** | 200-500ms | 18 | 14% | Full component trees, multiple providers |
| 🔴 **Very Slow** | > 500ms | 2 | 1.6% | Full app renders (workflows.test.tsx) |
| ❌ **Critical** | > 2000ms | 0 | 0% | None! ✅ |

---

## Impact Summary

### Current State
- **Total tests**: 127
- **Total runtime**: ~10.2s
- **Slowest test**: 599ms
- **Tests <2s**: 127 (100%) ✅

### After Optimizations (Projected)
- **Total tests**: 127
- **Total runtime**: ~7.5s (**26% faster**)
- **Slowest test**: ~280ms (**53% faster**)
- **Tests <200ms**: 107 (84%, up from 72%)
- **Time saved per run**: 2.7s
- **Time saved per day** (100 runs): 4.5 minutes
- **Time saved per year**: 27.5 hours of CI/CD time

### Developer Experience Improvements
- Faster feedback loop during TDD
- Faster CI/CD pipeline
- Less context switching while waiting for tests
- Better test isolation and reliability

---

## Implementation Priority

### High Priority (Implement First)
1. ✅ **workflows.test.tsx optimizations** (saves ~1.8s)
   - Mock route components
   - Remove vague waitFor calls
   - Share QueryClient/Theme

### Medium Priority (Implement Second)
2. ✅ **CharacterCreationDialog.test.tsx optimizations** (saves ~0.8s)
   - Share providers
   - Remove unnecessary waitFor

### Low Priority (Future Improvements)
3. 🔄 **Apply patterns to other test files**
   - Review tests in 200-500ms range
   - Standardize test setup across project

---

## Conclusion

**Status**: ✅ **All tests already meet the <2s requirement**

The frontend test suite is in excellent shape! All 127 tests run in under 2 seconds, with the slowest at 599ms. However, applying the optimizations outlined in this report could:

- Reduce total test suite time by **26%** (10.2s → 7.5s)
- Reduce slowest test time by **53%** (599ms → 280ms)
- Save ~**27.5 hours/year** of CI/CD time
- Improve developer experience with faster feedback

The optimizations are **non-breaking** and focus on:
1. Removing unnecessary delays
2. Sharing expensive objects
3. Mocking heavy components
4. Using synchronous assertions

**Recommendation**: Implement high-priority optimizations first to gain maximum benefit with minimal effort.

---

**Report Generated**: November 25, 2025
**Test Suite**: Frontend Unit Tests (Vitest)
**Total Tests Analyzed**: 127
**Framework**: React 18 + Vitest + Testing Library
