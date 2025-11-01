# Character Selection Component - Test Suite Documentation

## Overview

This directory contains comprehensive Playwright tests for the Character Selection Component, designed to ensure robust functionality, accessibility, and user experience. The tests are written to guide implementation and provide confidence in the component's behavior across different scenarios.

## Test Structure

### Main Test File
- **`CharacterSelection.spec.js`** - Primary test suite with comprehensive coverage

### Supporting Files
- **`test-utils.js`** - Helper functions, constants, and utilities
- **`README.md`** - This documentation file

### Configuration Files
- **`../playwright.config.js`** - Playwright configuration
- **`../tests/global-setup.js`** - Global test setup
- **`../tests/global-teardown.js`** - Global test cleanup

## Test Coverage Areas

### 1. Initial State Tests
Tests the component's loading behavior and API integration:

- ✅ Component renders with loading state initially
- ✅ Makes API call to GET /characters endpoint on mount
- ✅ Displays character cards after successful API response
- ✅ Handles API errors gracefully (404, 500, network failures)
- ✅ Shows appropriate loading indicators
- ✅ Provides retry functionality after failures

### 2. Selection Logic Tests
Tests character selection and deselection functionality:

- ✅ Clicking a character card selects it (adds selected visual state)
- ✅ Clicking a selected character card deselects it (removes selected state)
- ✅ Selection state persists correctly across interactions
- ✅ Visual feedback for selected vs unselected states
- ✅ Multiple character selection functionality
- ✅ Hover effects and interactive feedback

### 3. Validation Logic Tests
Tests selection constraints and validation rules:

- ✅ Cannot proceed with less than 2 characters (minimum requirement)
- ✅ Cannot select more than 6 characters maximum
- ✅ Attempt to select 7th character should fail with error message
- ✅ Proper error messaging for validation failures
- ✅ Confirm Selection button behavior based on validation
- ✅ Color-coded selection counter (red/green based on validity)

### 4. Accessibility Tests
Tests keyboard navigation and screen reader support:

- ✅ Full keyboard navigation support
- ✅ Proper ARIA labels and roles
- ✅ Focus management and visual indicators
- ✅ Color contrast compliance
- ✅ Screen reader announcements

### 5. Error Recovery Tests
Tests error handling and recovery mechanisms:

- ✅ Retry functionality after API failures
- ✅ Loading states during retry attempts
- ✅ Graceful degradation when API is unavailable

### 6. Integration Tests
Tests component integration with broader application:

- ✅ Integration with simulation workflow
- ✅ Proper data formatting for API calls
- ✅ Confirmation dialog functionality (if implemented)

## Test Data and Mocking

### Mock API Responses
The tests use comprehensive mock data that mirrors the expected API structure:

```javascript
// Basic characters list
{
  "characters": ["krieg", "ork", "test"]
}

// Character detail structure
{
  "character_name": "krieg",
  "narrative_context": "Trooper 86 of the Death Korps...",
  "structured_data": {
    "name": "Trooper 86",
    "factions": ["Astra Militarum", "Death Korps of Krieg"],
    "personality_traits": ["Fatalistic", "Grim", "Loyal to the Emperor"]
  },
  "file_count": { "md": 1, "yaml": 1 }
}
```

### API Endpoints Tested
- `GET /characters` - Fetch available characters
- `GET /characters/{name}` - Fetch character details (optional)
- `POST /simulation/start` - Start simulation with selected characters

## Component Requirements (Based on UI Spec)

### Required Data Attributes
The component must implement the following `data-testid` attributes for testing:

#### Loading States
- `data-testid="loading-spinner"` - Loading indicator
- `data-testid="character-grid"` - Main character grid container

#### Character Cards
- `data-testid="character-card"` - Generic character card
- `data-testid="character-card-{name}"` - Specific character card (e.g., "character-card-krieg")
- `data-testid="selection-checkmark-{name}"` - Selection indicator for character

#### UI Elements
- `data-testid="selection-counter"` - Selection count display
- `data-testid="confirm-selection-button"` - Main action button
- `data-testid="retry-button"` - Retry button for failed API calls

#### Error States
- `data-testid="error-message"` - General error message container
- `data-testid="validation-error"` - Validation-specific error messages

#### Dialogs (Optional)
- `data-testid="confirmation-dialog"` - Confirmation dialog
- `data-testid="confirm-dialog-yes"` - Dialog confirmation button
- `data-testid="confirm-dialog-no"` - Dialog cancellation button

### Required CSS Classes
- `.selected` - Applied to selected character cards
- Hover effects with `transform: scale(1.02)`
- Color coding: `#CC0000` (red) for errors, `#228B22` (green) for success

### Required ARIA Attributes
- `role="button"` on character cards
- `tabindex="0"` for keyboard navigation
- `aria-label` with descriptive text
- `aria-pressed` for selection state

## Running the Tests

### Prerequisites
1. Install Playwright dependencies:
```bash
npm install -D @playwright/test
npx playwright install
```

2. Ensure the development server is running:
```bash
npm run dev
```

3. (Optional) Start the API server for integration tests:
```bash
# From the root directory
python api_server.py
```

### Test Execution Commands

```bash
# Run all tests
npx playwright test

# Run tests in headed mode (with browser UI)
npx playwright test --headed

# Run specific test file
npx playwright test CharacterSelection.spec.js

# Run tests with specific browser
npx playwright test --project=chromium

# Run tests in debug mode
npx playwright test --debug

# Generate test report
npx playwright show-report
```

### Test Debugging

```bash
# Run with verbose output
npx playwright test --reporter=line

# Run single test in debug mode
npx playwright test --grep "should render with loading state" --debug

# Record test actions for debugging
npx playwright codegen http://localhost:5173/character-selection
```

## Expected Test Behavior

### Initial Test Run
**The tests are expected to FAIL initially** since the Character Selection Component hasn't been implemented yet. This is by design - the tests serve as:

1. **Implementation guidance** - They define exactly what the component should do
2. **Acceptance criteria** - They specify the behavior that must be implemented
3. **Regression prevention** - They ensure future changes don't break functionality

### Test-Driven Development Approach
1. **Red Phase** - Tests fail (component doesn't exist)
2. **Green Phase** - Implement component to make tests pass
3. **Refactor Phase** - Improve implementation while keeping tests green

## Performance Considerations

The tests include performance helpers for:
- Component load time measurement
- Selection response time testing
- Memory usage monitoring (via browser devtools)

### Performance Benchmarks
- Component should load within 2 seconds on a normal connection
- Character selection should respond within 100ms
- API calls should complete within 5 seconds (with timeout handling)

## Browser Compatibility

Tests are configured to run across multiple browsers:
- **Chromium** (Chrome/Edge)
- **Firefox**
- **WebKit** (Safari)
- **Mobile Chrome** (Pixel 5 simulation)
- **Mobile Safari** (iPhone 12 simulation)

## Accessibility Standards

Tests verify compliance with:
- **WCAG 2.1 AA** color contrast requirements
- **Section 508** keyboard navigation
- **ARIA 1.1** semantic markup
- Screen reader compatibility

## Error Scenarios Covered

### API Error Types
- **404 Not Found** - Characters directory missing
- **500 Internal Server Error** - Backend issues
- **Network Timeout** - Slow connections
- **Connection Refused** - Server not running

### Validation Errors
- **Minimum Selection** - Less than 2 characters
- **Maximum Selection** - More than 6 characters
- **Empty State** - No characters available

### User Interaction Errors
- **Rapid Clicking** - Multiple quick selections
- **Keyboard vs Mouse** - Mixed interaction methods
- **Focus Management** - Tab navigation edge cases

## Future Enhancements

Potential test additions for future development:
- **Visual Regression Testing** - Screenshots comparison
- **Load Testing** - Many characters performance
- **Internationalization** - Multi-language support
- **Touch Gestures** - Mobile-specific interactions
- **Animation Testing** - Transition and hover effects

## Contributing to Tests

When adding new functionality to the component:

1. **Update test specifications** first (TDD approach)
2. **Add corresponding test data** to `test-utils.js`
3. **Update selectors** if new elements are added
4. **Maintain accessibility standards** in new tests
5. **Document breaking changes** in this README

## Troubleshooting

### Common Issues

**Tests timeout waiting for elements:**
- Verify the component renders the expected `data-testid` attributes
- Check that API mocking is working correctly
- Ensure the development server is running

**API mocking not working:**
- Verify the API base URL matches the server configuration
- Check that route patterns match exactly
- Ensure mock data structure matches API specification

**Accessibility tests failing:**
- Verify ARIA attributes are implemented correctly
- Check that keyboard navigation works manually
- Ensure color contrast meets WCAG standards

### Debug Commands

```bash
# Debug specific test
npx playwright test --grep "should select character" --debug

# Run with browser console logs
npx playwright test --headed --reporter=line

# Generate trace for failed tests
npx playwright test --trace=on
npx playwright show-trace trace.zip
```

This comprehensive test suite ensures the Character Selection Component meets all requirements from the UI Design Specification and provides a robust, accessible user experience.
