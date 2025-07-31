# Package.json Updates Required for Playwright Testing

## Dependencies to Add

To run the Playwright tests for the Character Selection Component, you'll need to add the following dependencies to your `package.json`:

### Development Dependencies

```json
{
  "devDependencies": {
    "@playwright/test": "^1.40.0"
  }
}
```

### Updated Scripts Section

Add these scripts to the `scripts` section of your `package.json`:

```json
{
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "lint": "eslint .",
    "preview": "vite preview",
    "test": "playwright test",
    "test:headed": "playwright test --headed",
    "test:debug": "playwright test --debug",
    "test:report": "playwright show-report",
    "test:ui": "playwright test --ui"
  }
}
```

## Installation Commands

Run these commands to install Playwright and set up the testing environment:

```bash
# Install Playwright test framework
npm install -D @playwright/test

# Install browser binaries
npx playwright install

# Install system dependencies (Linux/WSL only)
npx playwright install-deps
```

## Complete Updated package.json

Here's how your complete `package.json` should look after adding Playwright support:

```json
{
  "name": "frontend",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "lint": "eslint .",
    "preview": "vite preview",
    "test": "playwright test",
    "test:headed": "playwright test --headed",
    "test:debug": "playwright test --debug",
    "test:report": "playwright show-report",
    "test:ui": "playwright test --ui"
  },
  "dependencies": {
    "axios": "^1.11.0",
    "react": "^19.1.0",
    "react-dom": "^19.1.0"
  },
  "devDependencies": {
    "@eslint/js": "^9.30.1",
    "@playwright/test": "^1.40.0",
    "@types/react": "^19.1.8",
    "@types/react-dom": "^19.1.6",
    "@vitejs/plugin-react": "^4.6.0",
    "eslint": "^9.30.1",
    "eslint-plugin-react-hooks": "^5.2.0",
    "eslint-plugin-react-refresh": "^0.4.20",
    "globals": "^16.3.0",
    "vite": "^7.0.4"
  }
}
```

## Post-Installation Setup

After installing Playwright, you may want to run the configuration wizard:

```bash
# Initialize Playwright configuration (optional)
npx playwright install
```

## Verification

To verify the installation is working correctly:

```bash
# Run a simple test to verify setup
npx playwright test --list

# Run the Character Selection tests (will fail until component is implemented)
npx playwright test CharacterSelection.spec.js
```

## Notes

- The tests are designed to **fail initially** since the Character Selection Component hasn't been implemented yet
- Tests serve as implementation guidance and acceptance criteria
- Once the component is implemented with the required `data-testid` attributes, tests should pass
- The test configuration assumes the Vite dev server runs on `http://localhost:5173`
- API mocking is used extensively, so the backend doesn't need to be running for most tests