#!/usr/bin/env node

/**
 * Analyze Vitest test timings from verbose output
 * Usage: npm test -- --run --reporter=verbose 2>&1 | node scripts/analyze-test-timing.js
 */

const fs = require('fs');
const path = require('path');

// Read from stdin or file
let input = '';

if (process.stdin.isTTY) {
  // Read from file if provided
  const filePath = process.argv[2];
  if (filePath && fs.existsSync(filePath)) {
    input = fs.readFileSync(filePath, 'utf8');
  } else {
    console.error('Usage: npm test -- --run --reporter=verbose 2>&1 | node scripts/analyze-test-timing.js');
    console.error('   or: node scripts/analyze-test-timing.js <log-file>');
    process.exit(1);
  }
} else {
  // Read from stdin
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', chunk => {
    input += chunk;
  });

  process.stdin.on('end', () => {
    analyzeTimings(input);
  });
}

if (input) {
  analyzeTimings(input);
}

function analyzeTimings(input) {
  // Strip ANSI color codes first (including ESC sequences)
  const strippedInput = input.replace(/\x1b\[[0-9;]*m|\[\d+m/g, '');

  // Parse test timing lines from verbose output
  // Format: ✓ tests/path/to/test.tsx > Suite > Test name 123ms
  const timingRegex = /✓\s+([^\s]+\.test\.tsx(?:x)?)\s+>\s+(.+?)\s+(\d+)ms/g;

  const tests = [];
  let match;

  while ((match = timingRegex.exec(strippedInput)) !== null) {
    const [, file, testPath, time] = match;
    tests.push({
      file,
      testPath,
      time: parseInt(time, 10)
    });
  }

  if (tests.length === 0) {
    console.error('No test timings found in input');
    process.exit(1);
  }

  // Sort by time descending
  tests.sort((a, b) => b.time - a.time);

  // Output top 10 slowest tests
  console.log('\n=== TOP 20 SLOWEST TESTS ===\n');
  tests.slice(0, 20).forEach((test, index) => {
    console.log(`${index + 1}. ${test.time}ms - ${test.file}`);
    console.log(`   ${test.testPath}`);
    console.log('');
  });

  // Output summary stats
  console.log('\n=== SUMMARY ===\n');
  console.log(`Total tests analyzed: ${tests.length}`);
  console.log(`Slowest test: ${tests[0].time}ms`);
  console.log(`Fastest test: ${tests[tests.length - 1].time}ms`);

  const totalTime = tests.reduce((sum, t) => sum + t.time, 0);
  const avgTime = totalTime / tests.length;
  console.log(`Average time: ${Math.round(avgTime)}ms`);
  console.log(`Total time: ${totalTime}ms (${(totalTime / 1000).toFixed(2)}s)`);

  // Tests over 2 seconds
  const slowTests = tests.filter(t => t.time > 2000);
  console.log(`\nTests over 2s: ${slowTests.length}`);

  // Tests over 1 second
  const slowishTests = tests.filter(t => t.time > 1000);
  console.log(`Tests over 1s: ${slowishTests.length}`);
}
