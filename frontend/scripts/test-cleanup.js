/**
 * Test Cleanup Script for Novel Engine Frontend
 * Ensures proper cleanup of test processes and handles
 */

import { execSync } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Common ports used by the frontend
const PORTS_TO_KILL = [3000, 5173, 8000, 9229];

// Kill processes on specific ports
function killPortProcesses() {
  console.log('🧹 Cleaning up test ports...');
  
  for (const port of PORTS_TO_KILL) {
    try {
      if (process.platform === 'win32') {
        // Windows
        execSync(`netstat -ano | findstr :${port}`, { stdio: 'pipe' });
        execSync(`for /f "tokens=5" %a in ('netstat -ano ^| findstr :${port}') do taskkill /f /pid %a`, { stdio: 'pipe' });
      } else {
        // Unix-like systems
        execSync(`lsof -ti:${port} | xargs kill -9`, { stdio: 'pipe' });
      }
      console.log(`✅ Cleaned up port ${port}`);
    } catch (error) {
      // Port not in use or already cleaned
    }
  }
}

// Kill Node.js processes in current directory
function killNodeProcesses() {
  console.log('🧹 Cleaning up Node.js test processes...');
  
  try {
    const currentDir = process.cwd();
    
    if (process.platform === 'win32') {
      // Windows - kill node processes in current directory
      const cmd = `wmic process where "name='node.exe' and commandline like '%${currentDir.replace(/\\/g, '\\\\')}%'" get processid /value`;
      const output = execSync(cmd, { encoding: 'utf8', stdio: 'pipe' });
      
      const pids = output.match(/ProcessId=(\d+)/g);
      if (pids) {
        pids.forEach(pidMatch => {
          const pid = pidMatch.split('=')[1];
          try {
            execSync(`taskkill /f /pid ${pid}`, { stdio: 'pipe' });
            console.log(`✅ Killed process ${pid}`);
          } catch (err) {
            // Process already terminated
          }
        });
      }
    } else {
      // Unix-like systems
      execSync(`pkill -f "node.*${currentDir}"`, { stdio: 'pipe' });
      console.log('✅ Cleaned up Node.js processes');
    }
  } catch (error) {
    // No processes found or already cleaned
  }
}

// Clear temporary test files
function clearTempFiles() {
  console.log('🧹 Cleaning up temporary test files...');
  
  try {
    const tempDirs = [
      'test-results',
      'coverage',
      'playwright-report',
      '.vitest'
    ];
    
    tempDirs.forEach(dir => {
      try {
        const fullPath = path.join(process.cwd(), dir);
        if (process.platform === 'win32') {
          execSync(`if exist "${fullPath}" rmdir /s /q "${fullPath}"`, { stdio: 'pipe' });
        } else {
          execSync(`rm -rf "${fullPath}"`, { stdio: 'pipe' });
        }
        console.log(`✅ Cleaned up ${dir}`);
      } catch (err) {
        // Directory doesn't exist or already cleaned
      }
    });
  } catch (error) {
    console.warn('⚠️ Some temp files could not be cleaned:', error.message);
  }
}

// Main cleanup function
function runCleanup() {
  console.log('🚀 Starting test environment cleanup...');
  
  killPortProcesses();
  killNodeProcesses();
  clearTempFiles();
  
  console.log('✅ Test environment cleanup complete!');
}

// Run cleanup if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
  runCleanup();
}

export {
  runCleanup,
  killPortProcesses,
  killNodeProcesses,
  clearTempFiles
};