import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';

import { expect, test, type BrowserContext, type Page } from '@playwright/test';

import {
  assertNarrativeProse,
  readStoreRowCounts,
  readZipEntries,
  tsStackDataDirectory,
  zipFirstEntryIsStoredMimetype,
} from './content_acceptance_helpers';

/**
 * #276 content-level acceptance against the TS stack: green must mean
 * correct, not just responsive. The flows of studio-ts.spec.ts (#274) stay
 * the interaction surface; this suite pins the CONTENT contracts — the F-1
 * prose guarantee after a proposal accept, byte-faithful markdown plus
 * structurally valid DOCX/EPUB downloads, operator-safe FTS5 reduction, the
 * unified 409/CSRF envelopes, and export-directory plus row removal on
 * project deletion. Prose invariants reuse the compiled server guard (see
 * content_acceptance_helpers) instead of forking the phrase list.
 */

interface ChapterDocument {
  id: string;
  kind: string;
  title: string;
  position: number;
  current_revision_id: string;
  content_markdown: string;
}

interface EnvelopeBody {
  error: { code: string; message: string; details: Record<string, unknown> };
}

test.describe.serial('#276 content acceptance', () => {
  test.setTimeout(120_000);

  // Same fragment-assembled credential as studio-ts.spec.ts: that suite owns
  // the one-time owner setup on the shared store, so this suite waits for the
  // login form and signs in as the owner.
  const OWNER_PASSWORD = ['ts-e2e-owner', 'password-1234'].join('-');

  let studioContext: BrowserContext;
  let studio: Page;
  let csrfToken: string;

  test.beforeAll(async ({ browser }) => {
    studioContext = await browser.newContext();
    studio = await studioContext.newPage();
    // The entry page probes setup once on mount, so poll by reloading until
    // the sibling suite's one-time owner setup has flipped the heading.
    await expect(async () => {
      await studio.goto('/');
      await expect(studio.getByRole('heading', { name: 'Open your writing studio' })).toBeVisible();
    }).toPass({ timeout: 60_000 });
    await studio.getByLabel('Password').fill(OWNER_PASSWORD);
    await studio.getByRole('button', { name: 'Sign in' }).click();
    await expect(studio).toHaveURL(/\/projects$/);

    // Cookie contract restated for this suite's session: the double-submit
    // pair is novel_engine_* and no legacy cookie survives.
    const cookieNames = (await studioContext.cookies()).map((cookie) => cookie.name);
    expect(cookieNames).toContain('novel_engine_session');
    expect(cookieNames).not.toContain('novel_studio_csrf');
    csrfToken =
      (await studioContext.cookies()).find((cookie) => cookie.name === 'novel_engine_csrf')
        ?.value ?? '';
    expect(csrfToken).not.toBe('');
  });

  test.afterAll(async () => {
    await studioContext.close();
  });

  test('accepted proposal leaves narrative prose in the editor and the saved document', async () => {
    const projectId = await createProject(studio, 'Prose Harbor');
    await typeChapter(studio, '# Chapter 1\n\nThe harbor bell rang twice.');

    await studio.getByPlaceholder('Describe the change or direction...').fill('Deepen the storm.');
    await studio.getByRole('button', { name: 'Continue' }).click();
    await expect(studio.getByText('Proposed Markdown')).toBeVisible();

    const preview = (await studio.locator('.proposal pre').textContent()) ?? '';
    await assertNarrativeProse(preview);

    await studio.getByRole('button', { name: 'Accept' }).click();
    await expect(studio.getByText('Proposed Markdown')).toHaveCount(0);
    await expect(studio.locator('.studio-editor .save-state')).toHaveText(/saved/i);
    await expect(studio.locator('.cm-content')).toContainText('The Debt in the Rain');

    // The accepted revision must be exactly the prose the author saw.
    const saved = (await studioChapters(studio, projectId))[0]?.content_markdown ?? '';
    expect(saved).toBe(preview);
    await assertNarrativeProse(saved);
  });

  test('exports download as byte-faithful markdown and structurally valid docx and epub', async () => {
    const title = 'Fidelity Ledger';
    const projectId = await createProject(studio, title);
    await typeChapter(studio, '# Chapter 1\n\nThe harbor bell rang twice.');
    await studio.getByRole('button', { name: 'Add Manuscript' }).click();
    await expect(studio.getByRole('textbox', { name: 'Document title' })).toHaveValue('Chapter 2');
    await typeChapter(studio, '# Chapter 2\n\nThe ledger named its next cost before midnight.');

    await studio.getByRole('tab', { name: 'Export' }).click();

    // The store must hold exactly the authored chapters before fidelity is
    // judged, so a lost autosave fails loudly instead of weakening it.
    await expect
      .poll(async () =>
        (await studioChapters(studio, projectId)).map((chapter) => chapter.content_markdown),
      )
      .toEqual([
        '# Chapter 1\n\nThe harbor bell rang twice.',
        '# Chapter 2\n\nThe ledger named its next cost before midnight.',
      ]);
    const chapters = await studioChapters(studio, projectId);

    const markdownBytes = await exportThroughUi(studio, 'Markdown', `${title}.md`);
    const docxBytes = await exportThroughUi(studio, 'Word document', `${title}.docx`);
    const epubBytes = await exportThroughUi(studio, 'EPUB', `${title}.epub`);
    await expect(studio.locator('.export-row')).toHaveCount(3);

    // Byte fidelity (#294): the file is exactly the saved chapters under the
    // project title — reconstructed from the store, not from typed constants.
    const expectedMarkdown = Buffer.from(
      `# ${title}\n\n${chapters.map((chapter) => chapter.content_markdown.trim()).join('\n\n')}\n`,
      'utf8',
    );
    expect(markdownBytes.equals(expectedMarkdown)).toBe(true);

    const docxEntries = readZipEntries(docxBytes);
    const documentXml = docxEntries.get('word/document.xml')?.toString('utf8') ?? '';
    expect(docxEntries.has('[Content_Types].xml')).toBe(true);
    expect(documentXml).toContain('<w:body>');
    expect(documentXml).toContain(title);
    expect(documentXml).toContain('The harbor bell rang twice.');
    expect(documentXml).toContain('The ledger named its next cost before midnight.');

    const epubEntries = readZipEntries(epubBytes);
    expect(epubEntries.get('mimetype')?.toString('utf8')).toBe('application/epub+zip');
    expect(zipFirstEntryIsStoredMimetype(epubBytes, 'application/epub+zip')).toBe(true);
    expect(epubEntries.get('META-INF/container.xml')?.toString('utf8')).toContain(
      'OEBPS/content.opf',
    );
    const navigation = epubEntries.get('OEBPS/nav.xhtml')?.toString('utf8') ?? '';
    const toc = epubEntries.get('OEBPS/toc.ncx')?.toString('utf8') ?? '';
    const opf = epubEntries.get('OEBPS/content.opf')?.toString('utf8') ?? '';
    expect(navigation).toContain('chapter-001.xhtml');
    expect(navigation).toContain('chapter-002.xhtml');
    expect(toc).toContain('<navMap>');
    expect(toc).toContain('Chapter 2');
    expect(opf).toContain('properties="nav"');
    expect(opf).toContain('<itemref idref="chapter-1"/>');
    expect(opf).toContain('<itemref idref="chapter-2"/>');
    const chapterOne = epubEntries.get('OEBPS/chapter-001.xhtml')?.toString('utf8') ?? '';
    expect(chapterOne).toContain('<h1>Chapter 1</h1>');
    expect(chapterOne).toContain('<p>The harbor bell rang twice.</p>');
    expect(epubEntries.get('OEBPS/chapter-002.xhtml')?.toString('utf8')).toContain(
      '<p>The ledger named its next cost before midnight.</p>',
    );
  });

  test('deleting a project removes its export directory and every store row', async () => {
    const projectId = await createProject(studio, 'Doomed Ledger');
    await typeChapter(studio, '# Chapter 1\n\nThe bell named its last keeper.');
    const created = await studio.request.post(`/api/projects/${projectId}/exports`, {
      data: { format: 'markdown' },
      headers: { 'x-csrf-token': csrfToken },
    });
    expect(created.status()).toBe(201);
    expect(((await created.json()) as { status: string }).status).toBe('completed');

    const catalog = (await (
      await studio.request.get(`/api/projects/${projectId}/exports`)
    ).json()) as { exports: Array<{ id: string; download_url: string; size_bytes: number }> };
    expect(catalog.exports).toHaveLength(1);
    const artifact = catalog.exports[0] ?? { id: '', download_url: '', size_bytes: 0 };
    const delivered = await studio.request.get(artifact.download_url);
    expect(delivered.ok()).toBe(true);
    expect((await delivered.body()).length).toBe(artifact.size_bytes);

    const exportDirectory = join(tsStackDataDirectory(), 'exports', projectId);
    expect(existsSync(exportDirectory)).toBe(true);
    expect(readdirSync(exportDirectory).length).toBeGreaterThan(0);
    expect(readStoreRowCounts(tsStackDataDirectory(), projectId)).toEqual({
      projects: 1,
      documents: 1,
      project_snapshots: 1,
      exports: 1,
      jobs: 1,
    });

    const removal = await studio.request.delete(`/api/projects/${projectId}`, {
      headers: { 'x-csrf-token': csrfToken },
    });
    expect(removal.status()).toBe(204);
    expect(existsSync(exportDirectory)).toBe(false);
    expect(readStoreRowCounts(tsStackDataDirectory(), projectId)).toEqual({
      projects: 0,
      documents: 0,
      project_snapshots: 0,
      exports: 0,
      jobs: 0,
    });

    const missing = await studio.request.get(`/api/projects/${projectId}`);
    expect(missing.status()).toBe(404);
    expect(((await missing.json()) as EnvelopeBody).error.code).toBe('NOT_FOUND');
    const undeliverable = await studio.request.get(artifact.download_url);
    expect(undeliverable.status()).toBe(404);
  });

  test('search reduces operators to literals; conflicts and csrf answer the unified envelope', async () => {
    const projectId = await createProject(studio, 'Signal Ledger');
    await typeChapter(
      studio,
      '# Chapter 1\n\nThe harbor bell rang twice. Nobody answered the second time.',
    );

    // Punctuation-separated terms all exist in the chapter: a hit through
    // both the API and the browser flow.
    const punctuated = await studio.request.get(
      `/api/projects/${projectId}/search?q=${encodeURIComponent('harbor.bell,twice')}`,
    );
    const punctuatedBody = (await punctuated.json()) as {
      results: Array<{ document_id: string; title: string }>;
    };
    expect(punctuatedBody.results).toHaveLength(1);
    expect(punctuatedBody.results[0]?.title).toBe('Chapter 1');
    const searchBox = studio.getByLabel('Search project');
    await searchBox.fill('harbor.bell,twice');
    await searchBox.press('Enter');
    await expect(studio.getByLabel('Search results')).toBeVisible();

    // FTS5 operators become literal quoted tokens: "harbor OR bell" reduces
    // to harbor AND or AND bell, and the chapter has no standalone "or" — so
    // raw operator passthrough would have matched, the reduction must not.
    const operated = await studio.request.get(
      `/api/projects/${projectId}/search?q=${encodeURIComponent('harbor OR bell')}`,
    );
    expect(((await operated.json()) as { results: unknown[] }).results).toHaveLength(0);
    await searchBox.fill('harbor OR bell');
    await searchBox.press('Enter');
    // The previous query's results are still on screen, so this auto-retry
    // assertion cannot pass early: the section must first disappear once the
    // safely-reduced query returns its empty result set.
    await expect(studio.getByLabel('Search results')).toHaveCount(0);

    // Stale base revision: 409 with the unified envelope and the winner.
    const chapter = (await studioChapters(studio, projectId))[0];
    const history = (await (
      await studio.request.get(`/api/projects/${projectId}/documents/${chapter?.id}/revisions`)
    ).json()) as { revisions: Array<{ id: string }> };
    const conflict = await studio.request.put(
      `/api/projects/${projectId}/documents/${chapter?.id}`,
      {
        data: { content_markdown: 'Stale tab write.', base_revision_id: history.revisions[0]?.id },
        headers: { 'x-csrf-token': csrfToken },
      },
    );
    expect(conflict.status()).toBe(409);
    const conflictBody = (await conflict.json()) as EnvelopeBody;
    expect(conflictBody.error.code).toBe('REVISION_CONFLICT');
    expect(typeof conflictBody.error.message).toBe('string');
    expect(conflictBody.error.details.current_revision_id).toBe(chapter?.current_revision_id);

    // CSRF double-submit: a session-authenticated write without the header is
    // rejected, and a tampered token is rejected separately.
    const missingToken = await studio.request.post('/api/projects', {
      data: { title: 'No token ledger' },
    });
    expect(missingToken.status()).toBe(403);
    expect(((await missingToken.json()) as EnvelopeBody).error.code).toBe('CSRF_TOKEN_MISSING');
    const tamperedToken = await studio.request.post('/api/projects', {
      data: { title: 'Tampered token ledger' },
      headers: { 'x-csrf-token': `${csrfToken}-tampered` },
    });
    expect(tamperedToken.status()).toBe(403);
    expect(((await tamperedToken.json()) as EnvelopeBody).error.code).toBe('CSRF_TOKEN_INVALID');
  });
});

async function createProject(page: Page, title: string): Promise<string> {
  await page.goto('/');
  await page.getByLabel('Title').fill(title);
  await page.getByRole('button', { name: /create project/i }).click();
  await expect(page).toHaveURL(/\/projects\/([^/]+)\/manuscript/);
  return page.url().match(/\/projects\/([^/]+)\/manuscript/)?.[1] ?? '';
}

async function typeChapter(page: Page, markdown: string): Promise<void> {
  const editor = page.locator('.cm-content');
  await editor.click();
  // ControlOrMeta resolves to the platform's select-all chord: CodeMirror maps
  // Mod-A to selectAll, so the typed chapter REPLACES the seed content (a
  // plain Control+A on macOS only moves to the line start).
  await page.keyboard.press('ControlOrMeta+a');
  await page.keyboard.type(markdown);
  await expect(page.locator('.studio-editor .save-state')).toHaveText(/saved/i, {
    timeout: 15_000,
  });
}

async function studioChapters(page: Page, projectId: string): Promise<ChapterDocument[]> {
  // The project payload embeds its documents (#246 dropped the list route).
  const response = await page.request.get(`/api/projects/${projectId}`);
  expect(response.status(), await response.text()).toBe(200);
  const body = (await response.json()) as { documents: ChapterDocument[] };
  return body.documents
    .filter((document) => document.kind === 'chapter')
    .sort((left, right) => left.position - right.position);
}

async function exportThroughUi(page: Page, formatLabel: string, filename: string): Promise<Buffer> {
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('button', { name: new RegExp(formatLabel, 'i') }).click(),
  ]);
  const downloadPath = await download.path();
  if (!downloadPath) {
    throw new Error(`The ${formatLabel} export produced no downloaded file.`);
  }
  expect(download.suggestedFilename()).toBe(filename);
  return readFileSync(downloadPath);
}
