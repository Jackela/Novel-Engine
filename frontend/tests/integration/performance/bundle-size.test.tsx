/**
 * Bundle Size Validation Test (T063)
 * 
 * TDD Approach: Write test FIRST, ensure it FAILS (RED phase)
 * Verifies production bundle sizes meet performance targets
 * 
 * Targets:
 * - Initial bundle: < 400KB (gzip)
 * - Route chunks: < 200KB (gzip) each
 * 
 * Run after production build: npm run build
 */

import { describe, test, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import zlib from 'zlib';

describe('Bundle Size Validation', () => {
  const distDir = path.join(__dirname, '../../../dist');

  /**
   * Helper: Get gzipped size of file in KB
   */
  const getGzipSize = (filePath: string): number => {
    if (!fs.existsSync(filePath)) {
      throw new Error(`File not found: ${filePath}`);
    }
    
    const fileContent = fs.readFileSync(filePath);
    const gzipped = zlib.gzipSync(fileContent);
    return gzipped.length / 1024; // Convert bytes to KB
  };

  /**
   * Helper: Find files matching pattern in dist directory
   */
  const findFiles = (pattern: RegExp): string[] => {
    if (!fs.existsSync(distDir)) {
      return [];
    }

    const files: string[] = [];
    const walk = (dir: string) => {
      const items = fs.readdirSync(dir);
      items.forEach(item => {
        const fullPath = path.join(dir, item);
        const stat = fs.statSync(fullPath);
        
        if (stat.isDirectory()) {
          walk(fullPath);
        } else if (pattern.test(item)) {
          files.push(fullPath);
        }
      });
    };

    walk(distDir);
    return files;
  };

  /**
   * Test 1: Verify initial bundle is < 400KB gzipped
   * Initial bundle includes vendor code (React, MUI) and app entry point
   */
  test.skip('should have initial bundle < 400KB gzipped', () => {
    // Find main entry bundle (typically index-[hash].js)
    const mainBundles = findFiles(/^index-[a-f0-9]+\.js$/);
    
    expect(mainBundles.length).toBeGreaterThan(0);

    mainBundles.forEach(bundlePath => {
      const size = getGzipSize(bundlePath);
      const fileName = path.basename(bundlePath);
      
      console.log(`Main bundle ${fileName}: ${size.toFixed(2)}KB (gzip)`);
      expect(size).toBeLessThan(400);
    });
  });

  /**
   * Test 2: Verify route chunks are < 200KB gzipped each
   * Route chunks are lazy-loaded components (Dashboard, CharacterSelection, etc.)
   */
  test.skip('should have route chunks < 200KB gzipped each', () => {
    // Find all JS chunks (excluding main bundle and vendor)
    const allChunks = findFiles(/^[a-zA-Z]+-[a-f0-9]+\.js$/);
    const routeChunks = allChunks.filter(f => {
      const name = path.basename(f);
      return !name.startsWith('index-') && !name.startsWith('vendor-');
    });

    expect(routeChunks.length).toBeGreaterThan(0);

    routeChunks.forEach(chunkPath => {
      const size = getGzipSize(chunkPath);
      const fileName = path.basename(chunkPath);
      
      console.log(`Route chunk ${fileName}: ${size.toFixed(2)}KB (gzip)`);
      expect(size).toBeLessThan(200);
    });
  });

  /**
   * Test 3: Verify vendor bundle separation
   * Vendor code (React, MUI, etc.) should be in separate chunk for better caching
   */
  test.skip('should have separate vendor bundle', () => {
    const vendorBundles = findFiles(/^vendor-[a-f0-9]+\.js$/);
    
    expect(vendorBundles.length).toBeGreaterThan(0);

    vendorBundles.forEach(bundlePath => {
      const size = getGzipSize(bundlePath);
      const fileName = path.basename(bundlePath);
      
      console.log(`Vendor bundle ${fileName}: ${size.toFixed(2)}KB (gzip)`);
      // Vendor bundle can be larger but should still be reasonable
      expect(size).toBeLessThan(500);
    });
  });

  /**
   * Test 4: Verify total bundle size is reasonable
   * Sum of all bundles should be < 1MB gzipped for good performance
   */
  test.skip('should have total bundle size < 1MB gzipped', () => {
    const allBundles = findFiles(/\.js$/);
    
    let totalSize = 0;
    allBundles.forEach(bundlePath => {
      totalSize += getGzipSize(bundlePath);
    });

    console.log(`Total bundle size: ${totalSize.toFixed(2)}KB (gzip)`);
    expect(totalSize).toBeLessThan(1024); // 1MB
  });

  /**
   * Test 5: Verify CSS bundle is optimized
   */
  test.skip('should have CSS bundle < 50KB gzipped', () => {
    const cssFiles = findFiles(/\.css$/);
    
    cssFiles.forEach(cssPath => {
      const size = getGzipSize(cssPath);
      const fileName = path.basename(cssPath);
      
      console.log(`CSS bundle ${fileName}: ${size.toFixed(2)}KB (gzip)`);
      expect(size).toBeLessThan(50);
    });
  });
});
