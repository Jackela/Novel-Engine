import { existsSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { inflateRawSync } from 'node:zlib';
import { DatabaseSync } from 'node:sqlite';

import { expect } from '@playwright/test';

/**
 * #276 content-level acceptance helpers. Two SSOT rules drive this module:
 *
 * 1. The prose contract is owned by the server sanitization module. Instead
 *    of forking the forbidden-phrase list into the frontend suite, the specs
 *    dynamically import the EMITTED server module (`pnpm --dir server build`
 *    is already a prerequisite of this Playwright project) and run its real
 *    guard plus its real phrase list against browser-visible content.
 * 2. DOCX/EPUB archives are unpacked with node:zlib only — no new frontend
 *    dependency; jszip stays a server-side writer concern.
 */

interface CompiledSanitizationModule {
  FORBIDDEN_PROSE_PHRASES?: unknown;
  isProposalMarkdownProse?: unknown;
}

/** The server-owned prose contract the e2e suite reuses, never forks. */
export interface ServerProseContract {
  readonly forbiddenPhrases: readonly string[];
  readonly isNarrativeProse: (markdown: string) => boolean;
}

let proseContractPromise: Promise<ServerProseContract> | undefined;

export function loadServerProseContract(): Promise<ServerProseContract> {
  proseContractPromise ??= importCompiledProseContract();
  return proseContractPromise;
}

async function importCompiledProseContract(): Promise<ServerProseContract> {
  const helpersDir = fileURLToPath(new URL('.', import.meta.url));
  const compiledModule = resolve(
    helpersDir,
    '../../../server/dist/contexts/studio/application/sanitization.js',
  );
  if (!existsSync(compiledModule)) {
    throw new Error(`Compiled server sanitization module not found at ${compiledModule}.`);
  }
  const module = (await import(compiledModule)) as CompiledSanitizationModule;
  const phrases = module.FORBIDDEN_PROSE_PHRASES;
  const guard = module.isProposalMarkdownProse;
  if (
    !Array.isArray(phrases) ||
    phrases.length === 0 ||
    phrases.some((phrase) => typeof phrase !== 'string') ||
    typeof guard !== 'function'
  ) {
    throw new Error('Compiled server sanitization module no longer exports the prose contract.');
  }
  return {
    forbiddenPhrases: phrases as readonly string[],
    isNarrativeProse: guard as (markdown: string) => boolean,
  };
}

/**
 * The #240 guard at e2e level: browser-visible prose must satisfy the
 * compiled server guard AND the suite's own invariants, so a weakened server
 * guard alone cannot green this acceptance.
 */
export async function assertNarrativeProse(markdown: string): Promise<void> {
  const prose = await loadServerProseContract();
  expect(prose.isNarrativeProse(markdown), 'compiled #240 guard accepts the content').toBe(true);
  expect(markdown.length).toBeGreaterThan(400);
  for (const phrase of prose.forbiddenPhrases) {
    expect(markdown.toLowerCase()).not.toContain(phrase.toLowerCase());
  }
  expect(markdown).not.toContain('[REDACTED]');
  expect(markdown).not.toContain('[BEGIN AUTHOR INSTRUCTION]');
  expect(markdown).not.toContain('[BEGIN UNTRUSTED MANUSCRIPT JSON]');
  expect(markdown).not.toContain('"echo"');
  expect(markdown).not.toContain('"result"');
}

/** The data directory pinned by playwright.ts.config.ts for this run. */
export function tsStackDataDirectory(): string {
  const dataDirectory = process.env.TS_E2E_DATA_DIR;
  if (!dataDirectory) {
    throw new Error('TS_E2E_DATA_DIR is unset; run through pnpm test:e2e:ts.');
  }
  return dataDirectory;
}

/** Fixed allowlist: table plus its project column — never user input. */
const PROJECT_ROW_TABLES: readonly (readonly [table: string, column: string])[] = [
  ['projects', 'id'],
  ['documents', 'project_id'],
  ['project_snapshots', 'project_id'],
  ['exports', 'project_id'],
  ['jobs', 'project_id'],
];

/**
 * Row counts per studio table for one project, read straight from the stack's
 * SQLite store through node:sqlite. Parameterized statements only.
 */
export function readStoreRowCounts(
  dataDirectory: string,
  projectId: string,
): Record<string, number> {
  const database = new DatabaseSync(join(dataDirectory, 'novel-engine.sqlite3'));
  try {
    const counts: Record<string, number> = {};
    for (const [table, column] of PROJECT_ROW_TABLES) {
      const row = database
        .prepare(`SELECT count(*) AS n FROM ${table} WHERE ${column} = ?`)
        .get(projectId);
      counts[table] = Number(row?.n ?? 0);
    }
    return counts;
  } finally {
    database.close();
  }
}

const END_OF_CENTRAL_DIRECTORY = 0x06054b50;
const CENTRAL_DIRECTORY_ENTRY = 0x02014b50;
const LOCAL_FILE_HEADER = 0x04034b50;
const MAXIMUM_COMMENT_SIZE = 0xffff;

function findEndOfCentralDirectory(archive: Buffer): number {
  const floor = Math.max(0, archive.length - 22 - MAXIMUM_COMMENT_SIZE);
  for (let index = archive.length - 22; index >= floor; index -= 1) {
    if (archive.readUInt32LE(index) === END_OF_CENTRAL_DIRECTORY) {
      return index;
    }
  }
  throw new Error('ZIP end-of-central-directory record not found.');
}

/**
 * Minimal central-directory ZIP reader (STORE + DEFLATE only) returning every
 * file entry by name. Structural violations — bad signatures, truncated
 * entries, size mismatches — throw instead of returning partial data.
 */
export function readZipEntries(archive: Buffer): Map<string, Buffer> {
  const endOfCentralDirectory = findEndOfCentralDirectory(archive);
  const entryCount = archive.readUInt16LE(endOfCentralDirectory + 10);
  let cursor = archive.readUInt32LE(endOfCentralDirectory + 16);
  const entries = new Map<string, Buffer>();
  for (let entry = 0; entry < entryCount; entry += 1) {
    if (cursor + 46 > archive.length || archive.readUInt32LE(cursor) !== CENTRAL_DIRECTORY_ENTRY) {
      throw new Error(`ZIP central-directory entry ${entry} is malformed.`);
    }
    const method = archive.readUInt16LE(cursor + 10);
    const compressedSize = archive.readUInt32LE(cursor + 20);
    const uncompressedSize = archive.readUInt32LE(cursor + 24);
    const nameLength = archive.readUInt16LE(cursor + 28);
    const extraLength = archive.readUInt16LE(cursor + 30);
    const commentLength = archive.readUInt16LE(cursor + 32);
    const localOffset = archive.readUInt32LE(cursor + 42);
    const name = archive.toString('utf8', cursor + 46, cursor + 46 + nameLength);
    cursor += 46 + nameLength + extraLength + commentLength;
    if (name.endsWith('/')) {
      continue;
    }
    const entryBuffer = readStoredEntry(archive, name, localOffset, compressedSize, method);
    if (entryBuffer.length !== uncompressedSize) {
      throw new Error(`ZIP entry ${name} declares ${uncompressedSize} bytes, inflated to other.`);
    }
    entries.set(name, entryBuffer);
  }
  return entries;
}

/** The EPUB OCF `mimetype` rule: first record, stored uncompressed. */
export function zipFirstEntryIsStoredMimetype(archive: Buffer, expected: string): boolean {
  if (archive.readUInt32LE(0) !== LOCAL_FILE_HEADER) {
    return false;
  }
  const method = archive.readUInt16LE(8);
  const compressedSize = archive.readUInt32LE(18);
  const uncompressedSize = archive.readUInt32LE(22);
  const nameLength = archive.readUInt16LE(26);
  const extraLength = archive.readUInt16LE(28);
  const dataStart = 30 + nameLength + extraLength;
  return (
    archive.toString('utf8', 30, 30 + nameLength) === 'mimetype' &&
    method === 0 &&
    compressedSize === expected.length &&
    uncompressedSize === expected.length &&
    archive.toString('utf8', dataStart, dataStart + expected.length) === expected
  );
}

function readStoredEntry(
  archive: Buffer,
  name: string,
  localOffset: number,
  compressedSize: number,
  method: number,
): Buffer {
  if (
    localOffset + 30 > archive.length ||
    archive.readUInt32LE(localOffset) !== LOCAL_FILE_HEADER
  ) {
    throw new Error(`ZIP local header for ${name} is malformed.`);
  }
  const localNameLength = archive.readUInt16LE(localOffset + 26);
  const localExtraLength = archive.readUInt16LE(localOffset + 28);
  const dataStart = localOffset + 30 + localNameLength + localExtraLength;
  const data = archive.subarray(dataStart, dataStart + compressedSize);
  if (method === 0) {
    return Buffer.from(data);
  }
  if (method !== 8) {
    throw new Error(`ZIP entry ${name} uses unsupported compression method ${method}.`);
  }
  return inflateRawSync(data);
}
