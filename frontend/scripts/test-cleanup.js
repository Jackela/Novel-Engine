/**
 * Test Cleanup Script for Novel Engine Frontend
 * Ensures proper cleanup of test processes and handles
 */

import { execFileSync } from 'child_process';
import fs from 'fs';
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
        const output = execFileSync('netstat', ['-ano'], { encoding: 'utf8' });
        const pids = new Set();
        output.split(/\r?\n/).forEach(line => {
          if (!line.includes(`:${port}`)) return;
          const parts = line.trim().split(/\s+/);
          const pid = parts[parts.length - 1];
          if (pid && /^\d+$/.test(pid)) {
            pids.add(pid);
          }
        });
        for (const pid of pids) {
          execFileSync('taskkill', ['/f', '/pid', pid], { stdio: 'pipe' });
        }
      } else {
        const output = execFileSync('lsof', ['-ti', `:${port}`], { encoding: 'utf8' }).trim();
        if (output) {
          output.split(/\r?\n/).forEach(pid => {
            if (/^\d+$/.test(pid)) {
              try {
                process.kill(Number(pid), 'SIGKILL');
              } catch {
                // Process already terminated
              }
            }
          });
        }
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
      const output = execFileSync(
        'wmic',
        ['process', 'where', 'name="node.exe"', 'get', 'ProcessId,CommandLine', '/value'],
        { encoding: 'utf8' }
      );
      const entries = output.split(/\r?\n\r?\n/);
      entries.forEach(block => {
        const lines = block.split(/\r?\n/);
        const commandLine = lines.find(line => line.startsWith('CommandLine='))?.slice('CommandLine='.length) || '';
        const pidLine = lines.find(line => line.startsWith('ProcessId=')) || '';
        const pid = pidLine.split('=')[1];
        if (pid && commandLine.includes(currentDir)) {
          try {
            execFileSync('taskkill', ['/f', '/pid', pid], { stdio: 'pipe' });
            console.log(`✅ Killed process ${pid}`);
          } catch {
            // Process already terminated
          }
        }
      });
    } else {
      const output = execFileSync('ps', ['-eo', 'pid=,command='], { encoding: 'utf8' });
      output.split(/\r?\n/).forEach(line => {
        const trimmed = line.trim();
        if (!trimmed) return;
        const [pidPart, ...commandParts] = trimmed.split(/\s+/);
        const command = commandParts.join(' ');
        if (!pidPart || !/^\d+$/.test(pidPart)) return;
        if (command.includes('node') && command.includes(currentDir)) {
          try {
            process.kill(Number(pidPart), 'SIGKILL');
            console.log(`✅ Killed process ${pidPart}`);
          } catch {
            // Process already terminated
          }
        }
      });
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
        fs.rmSync(fullPath, { recursive: true, force: true });
        console.log(`✅ Cleaned up ${dir}`);
      } catch {
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
