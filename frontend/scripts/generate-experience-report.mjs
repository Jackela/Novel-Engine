#!/usr/bin/env node
import { promises as fs } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import MarkdownIt from 'markdown-it';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FRONTEND_ROOT = path.resolve(__dirname, '..');
const REPORT_DIR = path.join(FRONTEND_ROOT, 'reports');
const TEST_RESULTS_PATH = path.join(FRONTEND_ROOT, 'test-results.json');
const REPORT_RETENTION_COUNT = Number(process.env.EXPERIENCE_REPORT_RETENTION ?? '10');

const md = new MarkdownIt();

function formatSection(title, lines = []) {
  return `## ${title}\n\n${lines.join('\n')}\n`;
}

async function readJson(file) {
  try {
    const raw = await fs.readFile(file, 'utf8');
    return JSON.parse(raw);
  } catch (error) {
    console.warn(`⚠️ Unable to read ${file}:`, error.message);
    return null;
  }
}

function walkSpecs(data) {
  const specs = [];
  if (!data) return specs;
  const queue = [...(data.suites || [])];
  while (queue.length) {
    const suite = queue.shift();
    if (suite?.suites?.length) queue.push(...suite.suites);
    if (suite?.specs?.length) specs.push(...suite.specs);
  }
  return specs;
}

function findSpecByTag(data, tag) {
  return walkSpecs(data).find(spec =>
    spec?.title?.includes(tag) ||
    spec?.tests?.some(test =>
      test?.annotations?.some(annotation => annotation?.description?.includes(tag) || annotation?.type === tag)
    )
  );
}

function summarizeResult(spec) {
  if (!spec?.tests?.length) return { status: 'unknown', duration: 0 };
  const result = spec.tests[0]?.results?.[0];
  return {
    status: result?.status || 'unknown',
    duration: result?.duration || 0,
    attachments: result?.attachments || [],
  };
}

async function writeFileSafe(filePath, content) {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await fs.writeFile(filePath, content, 'utf8');
  return filePath;
}

function htmlLayout({ title, sections }) {
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>${title}</title>
  <style>
    body { font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 2rem; line-height: 1.6; }
    .badge { display: inline-block; padding: 0.2rem 0.6rem; border-radius: 999px; color: #fff; font-size: 0.8rem; }
    .badge.pass { background: #2d9d78; }
    .badge.fail { background: #d14343; }
    .card { border: 1px solid #ddd; border-radius: 8px; padding: 1rem; margin-bottom: 1.5rem; box-shadow: 0 2px 4px rgba(0,0,0,0.05);}    table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
    th, td { border: 1px solid #eee; padding: 0.5rem; text-align: left; }
  </style>
</head>
<body>
  <h1>${title}</h1>
  ${sections.join('\n')}
</body>
</html>`;
}

function htmlSection({ heading, status, duration, description }) {
  const badgeClass = status === 'passed' ? 'pass' : status === 'failed' ? 'fail' : '';
  const badgeLabel = badgeClass ? status.toUpperCase() : status;
  return `<div class="card">
    <h2>${heading} <span class="badge ${badgeClass}">${badgeLabel}</span></h2>
    <p><strong>Duration:</strong> ${(duration / 1000).toFixed(2)}s</p>
    <p>${description}</p>
  </div>`;
}

function statusBadge(status) {
  if (status === 'passed') return '✅ Passed';
  if (status === 'failed') return '❌ Failed';
  return status ?? 'Unknown';
}

function buildSummaryTable(rows) {
  const lines = [
    '| Scenario | Status | Duration |',
    '| --- | --- | --- |',
    ...rows.map(({ label, summary }) =>
      `| ${label} | ${statusBadge(summary.status)} | ${(summary.duration / 1000).toFixed(2)}s |`
    ),
  ];
  return lines.join('\n');
}

(async () => {
  const testResults = await readJson(TEST_RESULTS_PATH);

  const reportMeta = [
    `- Generated: ${new Date().toISOString()}`,
    `- Source: frontend/test-results.json`
  ];

  const demoSpec = findSpecByTag(testResults, '@experience-cta');
  const demoSummary = summarizeResult(demoSpec);
  const demoSection = formatSection('Demo CTA Flow', [
    `- Status: ${demoSummary.status}`,
    `- Duration: ${(demoSummary.duration / 1000).toFixed(2)}s`
  ]);

  const offlineSpec = findSpecByTag(testResults, '@experience-offline');
  const offlineSummary = summarizeResult(offlineSpec);
  const offlineSection = formatSection('Connection Indicator Behaviour', [
    `- Status: ${offlineSummary.status}`,
    `- Duration: ${(offlineSummary.duration / 1000).toFixed(2)}s`
  ]);

  const markdown = [
    formatSection('Experience Report Summary', reportMeta),
    demoSection,
    offlineSection,
  ].join('\n');

  const htmlSections = [
    htmlSection({
      heading: 'Demo CTA Flow',
      status: demoSummary.status,
      duration: demoSummary.duration,
      description: 'Validates landing CTA → dashboard routing and guest banner visibility.'
    }),
    htmlSection({
      heading: 'Connection Indicator',
      status: offlineSummary.status,
      duration: offlineSummary.duration,
      description: 'Simulates offline mode to ensure indicator + telemetry behave as expected.'
    })
  ];
  const htmlReport = htmlLayout({ title: 'Experience Report', sections: htmlSections });

  const timestamp = Date.now();
  const mdPath = path.join(REPORT_DIR, `experience-report-${timestamp}.md`);
  const htmlPath = path.join(REPORT_DIR, `experience-report-${timestamp}.html`);
  const jsonPath = path.join(REPORT_DIR, `experience-report-${timestamp}.json`);

  await Promise.all([
    writeFileSafe(mdPath, markdown),
    writeFileSafe(htmlPath, htmlReport),
    writeFileSafe(jsonPath, JSON.stringify({ demoSummary, offlineSummary, generatedAt: new Date().toISOString() }, null, 2))
  ]);
  await pruneOldReports(REPORT_RETENTION_COUNT);

  const summaryTable = buildSummaryTable([
    { label: 'Demo CTA', summary: demoSummary },
    { label: 'Offline Recovery', summary: offlineSummary },
  ]);

  console.log('📝 Experience Summary\n');
  console.log(summaryTable);
  console.log(`\nFull report (HTML): ${path.relative(process.cwd(), htmlPath)}`);
  console.log(`Full report (Markdown): ${path.relative(process.cwd(), mdPath)}`);

  const jobSummary = process.env.GITHUB_STEP_SUMMARY;
  if (jobSummary) {
    const summaryBlock = `${summaryTable}\n\n- Full HTML: ${path.basename(htmlPath)}\n- Full Markdown: ${path.basename(mdPath)}\n`;
    try {
      await fs.appendFile(jobSummary, `${summaryBlock}\n`);
      console.log('📎 Experience summary appended to GitHub job summary');
    } catch (error) {
      console.warn('⚠️ Failed appending to job summary:', error.message);
    }
  }

  console.log(`\n📝 Experience reports written to ${mdPath} + ${htmlPath}`);
})();

async function pruneOldReports(maxCount) {
  if (maxCount <= 0) {
    return;
  }
  try {
    const files = await fs.readdir(REPORT_DIR);
    const reportFiles = files
      .filter(name => /^experience-report-\d+\.(md|html|json)$/.test(name))
      .map(name => ({
        name,
        fullPath: path.join(REPORT_DIR, name),
        timestamp: Number(name.match(/^experience-report-(\d+)\./)?.[1] || 0),
        extension: path.extname(name),
      }));
    const grouped = reportFiles.reduce((acc, file) => {
      acc[file.timestamp] = acc[file.timestamp] || [];
      acc[file.timestamp].push(file);
      return acc;
    }, {});
    const timestamps = Object.keys(grouped).map(Number).sort((a, b) => b - a);
    const rowsToKeep = timestamps.slice(0, maxCount);
    const rowsToDelete = timestamps.slice(maxCount);
    for (const ts of rowsToDelete) {
      for (const file of grouped[ts]) {
        await fs.unlink(file.fullPath).catch(() => {});
      }
    }
    if (rowsToDelete.length) {
      console.log(`🧹 Pruned ${rowsToDelete.length} old report batches (retention=${maxCount}).`);
    }
  } catch (error) {
    console.warn('⚠️ Unable to prune old reports:', error.message);
  }
}
