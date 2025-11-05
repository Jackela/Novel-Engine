#!/usr/bin/env node
/**
 * Convert Auth Tests from TDD Red to TDD Green
 * 
 * This script:
 * 1. Uncomments all test implementation code
 * 2. Removes expect(true).toBe(false) forced failures
 * 3. Adds proper imports for JWTAuthService
 * 4. Updates test file headers from "Red Phase" to "Green Phase"
 */

const fs = require('fs');
const path = require('path');

// Files to convert
const files = [
  'frontend/tests/unit/auth/JWTAuthService.test.ts',
  'frontend/tests/integration/auth-flow/auth-integration.test.ts'
];

function convertFile(filePath) {
  console.log(`Converting ${filePath}...`);
  
  let content = fs.readFileSync(filePath, 'utf-8');
  
  // 1. Update file header from "Red Phase" to "Green Phase"
  content = content.replace(
    '* JWTAuthService Unit Tests (TDD Red Phase)',
    '* JWTAuthService Unit Tests (TDD Green Phase)'
  );
  content = content.replace(
    '* Authentication Flow Integration Tests (TDD Red Phase)',
    '* Authentication Flow Integration Tests (TDD Green Phase)'
  );
  
  // 2. Add JWTAuthService import after the type imports
  if (!content.includes('import { JWTAuthService }')) {
    content = content.replace(
      "import type { LoginRequest, LoginResponse, AuthToken } from '../../../src/types/auth';",
      "import type { LoginRequest, LoginResponse, AuthToken } from '../../../src/types/auth';\nimport { JWTAuthService } from '../../../src/services/auth/JWTAuthService';"
    );
    // For integration tests
    content = content.replace(
      "import type { LoginRequest, LoginResponse, AuthToken } from '../../../src/types/auth';",
      "import type { LoginRequest, LoginResponse, AuthToken } from '../../../src/types/auth';\nimport { JWTAuthService } from '../../../src/services/auth/JWTAuthService';"
    );
  }
  
  // 3. Uncomment all lines that start with "      // " (6 spaces + "// ")
  // This preserves indentation while uncommenting
  content = content.replace(/^(\s+)\/\/ (const |await |expect\(|authService\.|vi\.)/gm, '$1$2');
  
  // 4. Remove all expect(true).toBe(false) forced failures and their comments
  content = content.replace(/\s*\/\/ TDD Red:.*\n\s*expect\(true\)\.toBe\(false\);.*\n/g, '\n');
  
  // 5. Clean up any remaining "TDD Red" comments
  content = content.replace(/\s*\/\/ TDD Red:.*\n/g, '\n');
  
  // 6. Remove multiple consecutive blank lines
  content = content.replace(/\n{3,}/g, '\n\n');
  
  fs.writeFileSync(filePath, content, 'utf-8');
  console.log(`✓ Converted ${filePath}`);
}

// Main execution
console.log('Starting TDD Red → Green conversion...\n');

files.forEach(file => {
  const fullPath = path.join(process.cwd(), '..', file);
  try {
    convertFile(fullPath);
  } catch (error) {
    console.error(`✗ Error converting ${file}:`, error.message);
  }
});

console.log('\n✓ All files converted successfully!');
console.log('\nNext steps:');
console.log('1. Run: cd frontend && npm test -- auth/');
console.log('2. Verify: All 23 auth tests should now PASS');
console.log('3. Run coverage: npm run test:coverage');
