/**
 * Safe Test Runner for Novel Engine Frontend
 * Runs tests with proper cleanup and timeout handling
 */

import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';
import { runCleanup } from './test-cleanup.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Test configuration
const CONFIG = {
  TEST_TIMEOUT: 300000, // 5 minutes
  CLEANUP_TIMEOUT: 30000, // 30 seconds
  MAX_RETRIES: 2
};

// Handle cleanup on exit
function setupCleanupHandlers() {
  const cleanup = () => {
    console.log('\n🛑 Test interrupted, cleaning up...');
    runCleanup();
    process.exit(1);
  };

  process.on('SIGINT', cleanup);
  process.on('SIGTERM', cleanup);
  process.on('exit', () => {
    runCleanup();
  });
}

// Run tests with timeout and cleanup
async function runTestsWithCleanup(testArgs = []) {
  let attempt = 1;
  
  while (attempt <= CONFIG.MAX_RETRIES) {
    console.log(`\n🧪 Test attempt ${attempt}/${CONFIG.MAX_RETRIES}`);
    
    // Pre-test cleanup
    console.log('🧹 Pre-test cleanup...');
    runCleanup();
    
    // Wait a moment for cleanup to complete
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    try {
      const testResult = await runVitest(testArgs);
      
      if (testResult.success) {
        console.log('✅ Tests completed successfully!');
        return true;
      } else {
        console.log(`❌ Tests failed on attempt ${attempt}`);
        if (attempt < CONFIG.MAX_RETRIES) {
          console.log('🔄 Retrying after cleanup...');
          await new Promise(resolve => setTimeout(resolve, 3000));
        }
      }
    } catch (error) {
      console.error(`💥 Test execution error on attempt ${attempt}:`, error.message);
      if (attempt < CONFIG.MAX_RETRIES) {
        console.log('🔄 Retrying after cleanup...');
        await new Promise(resolve => setTimeout(resolve, 3000));
      }
    }
    
    // Post-test cleanup
    runCleanup();
    attempt++;
  }
  
  console.log('❌ All test attempts failed');
  return false;
}

// Run vitest with proper timeout handling
function runVitest(args) {
  return new Promise((resolve) => {
    const vitestArgs = ['vitest', '--run', '--reporter=verbose', ...args];
    
    console.log(`🚀 Running: npm ${vitestArgs.join(' ')}`);
    
    const testProcess = spawn('npm', vitestArgs, {
      stdio: 'inherit',
      cwd: process.cwd(),
      env: {
        ...process.env,
        NODE_ENV: 'test',
        CI: '1'
      }
    });
    
    // Set timeout for the entire test run
    const timeout = setTimeout(() => {
      console.log('⏰ Test timeout reached, killing process...');
      testProcess.kill('SIGTERM');
      
      // Force kill after 5 seconds if graceful kill doesn't work
      setTimeout(() => {
        testProcess.kill('SIGKILL');
      }, 5000);
      
      resolve({ success: false, reason: 'timeout' });
    }, CONFIG.TEST_TIMEOUT);
    
    testProcess.on('close', (code) => {
      clearTimeout(timeout);
      resolve({ 
        success: code === 0, 
        code,
        reason: code === 0 ? 'success' : 'test-failure'
      });
    });
    
    testProcess.on('error', (error) => {
      clearTimeout(timeout);
      resolve({ 
        success: false, 
        error: error.message,
        reason: 'spawn-error'
      });
    });
  });
}

// Parse command line arguments
function parseArgs() {
  const args = process.argv.slice(2);
  return args;
}

// Main function
async function main() {
  console.log('🚀 Novel Engine Frontend - Safe Test Runner');
  console.log('==========================================');
  
  setupCleanupHandlers();
  
  const testArgs = parseArgs();
  
  console.log('📋 Configuration:');
  console.log(`   Test Timeout: ${CONFIG.TEST_TIMEOUT / 1000}s`);
  console.log(`   Max Retries: ${CONFIG.MAX_RETRIES}`);
  console.log(`   Test Args: ${testArgs.join(' ') || 'none'}`);
  
  const success = await runTestsWithCleanup(testArgs);
  
  if (success) {
    console.log('\n🎉 All tests completed successfully!');
    process.exit(0);
  } else {
    console.log('\n💥 Tests failed after all attempts');
    process.exit(1);
  }
}

// Run if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch(error => {
    console.error('💥 Fatal error:', error);
    runCleanup();
    process.exit(1);
  });
}

export {
  runTestsWithCleanup,
  runVitest,
  CONFIG
};
