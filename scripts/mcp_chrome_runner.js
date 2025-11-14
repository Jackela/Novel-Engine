#!/usr/bin/env node
/**
 * Lightweight Chrome DevTools (MCP) runner that launches a headless Chrome instance,
 * waits for key dashboard selectors, captures a screenshot, and emits a JSON summary
 * so docs/tests can reference real evidence rather than mock data.
 */
const { spawn } = require('child_process');
const net = require('net');
const os = require('os');
const CDP = require('chrome-remote-interface');
const fs = require('fs/promises');
const path = require('path');

const DEFAULT_URL = process.env.MCP_DASHBOARD_URL || 'http://127.0.0.1:3000/dashboard';
const DEFAULT_VIEWPORT = process.env.MCP_VIEWPORT || '1440x900';
const DEFAULT_OUT_DIR = path.join(__dirname, '..', 'tmp', 'mcp');
const DEFAULT_ASSET_DIR = path.join(__dirname, '..', 'docs', 'assets', 'dashboard');
const DEFAULT_SELECTORS = [
  '[data-testid="dashboard-layout"]',
  '[data-role="control-cluster"]',
  '[data-role="stream-feed"]',
  '[data-role="system-signals"]',
  '[data-role="pipeline"]',
];

function parseArgs() {
  const args = process.argv.slice(2);
  const options = {
    url: DEFAULT_URL,
    viewport: DEFAULT_VIEWPORT,
    selectors: [...DEFAULT_SELECTORS],
    timeout: Number(process.env.MCP_TIMEOUT || 40000),
    screenshot:
      process.env.MCP_SCREENSHOT ||
      path.join(
        DEFAULT_ASSET_DIR,
        `dashboard-flow-${new Date().toISOString().slice(0, 10)}.png`
      ),
    metadata:
      process.env.MCP_METADATA ||
      path.join(
        DEFAULT_OUT_DIR,
        `dashboard-flow-${Date.now()}.json`
      ),
  };

  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    const next = args[i + 1];
    switch (arg) {
      case '--url':
        options.url = next;
        i += 1;
        break;
      case '--viewport':
        options.viewport = next;
        i += 1;
        break;
      case '--screenshot':
        options.screenshot = next;
        i += 1;
        break;
      case '--metadata':
        options.metadata = next;
        i += 1;
        break;
      case '--timeout':
        options.timeout = Number(next);
        i += 1;
        break;
      case '--selector':
        if (next) {
          options.selectors.push(next);
          i += 1;
        }
        break;
      default:
        break;
    }
  }
  return options;
}

async function ensureDir(filePath) {
  const dir = path.dirname(filePath);
  await fs.mkdir(dir, { recursive: true });
}

function parseViewport(viewport) {
  const [widthStr, heightStr] = viewport.split('x');
  const width = Number(widthStr);
  const height = Number(heightStr);
  if (!width || !height) {
    throw new Error(`Invalid viewport "${viewport}". Expected format 1440x900.`);
  }
  return { width, height };
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function getFreePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.unref();
    server.on('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const { port } = server.address();
      server.close(() => resolve(port));
    });
  });
}

function getChromeExecutable() {
  if (process.env.CHROME_PATH) {
    return process.env.CHROME_PATH;
  }
  return 'google-chrome';
}

async function mkUserDataDir() {
  const tmpRoot = path.join(os.tmpdir(), 'mcp-chrome-');
  return fs.mkdtemp(tmpRoot);
}

async function waitForDebugger(port, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(`http://127.0.0.1:${port}/json/version`);
      if (res.ok) {
        return true;
      }
    } catch {
      // swallow until timeout
    }
    await delay(300);
  }
  throw new Error(`Chrome debugger not ready on port ${port}`);
}

async function waitForSelector(Runtime, selector, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const { result } = await Runtime.evaluate({
      expression: `document.querySelector('${selector.replace(/'/g, "\\'")}') !== null`,
      returnByValue: true,
    });
    if (result.value === true) {
      return true;
    }
    await delay(500);
  }
  throw new Error(`Timeout waiting for selector: ${selector}`);
}

async function attemptEnterDemo(Runtime) {
  const { result } = await Runtime.evaluate({
    expression: `(() => {
      const btn = document.querySelector('[data-testid="cta-demo"]');
      if (btn) {
        btn.click();
        return true;
      }
      return false;
    })();`,
    returnByValue: true,
  });
  return Boolean(result.value);
}

async function run() {
  const options = parseArgs();
  const { width, height } = parseViewport(options.viewport);
  await ensureDir(options.screenshot);
  await ensureDir(options.metadata);

  let chromeProcess;
  let client;
  let userDataDir;
  try {
    userDataDir = await mkUserDataDir();
    const debuggerPort = await getFreePort();
    const chromeArgs = [
      '--headless=new',
      '--disable-gpu',
      '--disable-dev-shm-usage',
      '--no-sandbox',
      '--hide-scrollbars',
      '--mute-audio',
      `--window-size=${width},${height}`,
      `--remote-debugging-port=${debuggerPort}`,
      `--user-data-dir=${userDataDir}`,
      'about:blank',
    ];

    chromeProcess = spawn(getChromeExecutable(), chromeArgs, { stdio: 'ignore' });

    chromeProcess.on('exit', (code) => {
      if (code !== 0) {
        console.error('[mcp] Chrome exited unexpectedly with code', code);
      }
    });

    await waitForDebugger(debuggerPort, options.timeout);

    client = await CDP({ port: debuggerPort });
    const { Page, Runtime, Network } = client;
    await Promise.all([Page.enable(), Runtime.enable(), Network.enable()]);

    await Page.navigate({ url: options.url });
    await Page.loadEventFired();

    // Ensure we are past the landing page by clicking the demo CTA if needed.
    const layoutSelector = options.selectors.find((sel) => sel.includes('dashboard-layout'));
    const layoutDeadline = Date.now() + options.timeout;
    if (layoutSelector) {
      let layoutReady = false;
      while (Date.now() < layoutDeadline) {
        const { result } = await Runtime.evaluate({
          expression: `document.querySelector('${layoutSelector.replace(/'/g, "\\'")}') !== null`,
          returnByValue: true,
        });
        if (result.value === true) {
          layoutReady = true;
          break;
        }
        const clicked = await attemptEnterDemo(Runtime);
        if (clicked) {
          await delay(800);
        } else {
          await delay(400);
        }
      }
      if (!layoutReady) {
        throw new Error('Dashboard layout never rendered (CTA click may have failed)');
      }
    }

    for (const selector of options.selectors) {
      await waitForSelector(Runtime, selector, options.timeout);
    }

    const metrics = await Page.getLayoutMetrics();
    const screenshot = await Page.captureScreenshot({
      format: 'png',
      clip: {
        x: 0,
        y: 0,
        width: metrics.contentSize.width,
        height: metrics.contentSize.height,
        scale: 1,
      },
    });
    await fs.writeFile(options.screenshot, Buffer.from(screenshot.data, 'base64'));

    const { result } = await Runtime.evaluate({
      expression: `(() => {
        const connection = document.querySelector('[data-testid="connection-status"]');
        const liveIndicator = document.querySelector('[data-testid="live-indicator"]');
        const pipeline = document.querySelector('[data-role="pipeline"] [data-status]');
        return {
          title: document.title,
          url: location.href,
          connectionStatus: connection ? connection.getAttribute('data-status') : null,
          liveIndicator: liveIndicator ? liveIndicator.textContent?.trim() : null,
          pipelinePhase: pipeline ? pipeline.getAttribute('data-phase') : null,
          timestamp: new Date().toISOString(),
        };
      })();`,
      returnByValue: true,
    });

    const summary = {
      ...result.value,
      screenshot: path.relative(process.cwd(), options.screenshot),
      selectors: options.selectors,
      viewport: { width, height },
    };
    await fs.writeFile(options.metadata, `${JSON.stringify(summary, null, 2)}\n`);

    console.log(`[mcp] Screenshot saved → ${summary.screenshot}`);
    console.log(`[mcp] Metadata saved → ${path.relative(process.cwd(), options.metadata)}`);
    console.log(`[mcp] Connection status: ${summary.connectionStatus}, pipeline phase: ${summary.pipelinePhase}`);
  } catch (error) {
    console.error('[mcp] Failed to capture dashboard snapshot:', error.message);
    process.exitCode = 1;
  } finally {
    if (client) {
      await client.close();
    }
    if (chromeProcess && chromeProcess.kill) {
      chromeProcess.kill('SIGTERM');
      await delay(250);
    }
    if (userDataDir) {
      await fs.rm(userDataDir, { recursive: true, force: true });
    }
  }
}

run();
