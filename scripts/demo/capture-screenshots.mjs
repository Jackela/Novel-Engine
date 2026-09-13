#!/usr/bin/env node
/**
 * Manual screenshot capture for the Novel Engine demo flow.
 *
 * Captures the key product screens (entry/login, project library, Studio with
 * the Copilot drafting a proposal, and the Export panel) against a RUNNING
 * Novel Engine instance and writes PNGs to `docs/screenshots/`.
 *
 * Operating constraints — enforced by convention, please keep them:
 * - Run by hand only. Never wire this into CI: it drives a real instance and
 *   leaves a demo project behind.
 * - Never run two captures against the same instance concurrently; the script
 *   creates its own project and racing captures would interleave UI sessions.
 * - Point it at a throwaway/demo instance, never at data you care about.
 *
 * Configuration (environment variables):
 * - DEMO_BASE_URL   Base URL of the running instance (default: http://localhost:8000).
 * - DEMO_USERNAME   Owner username; when unset the login form's stored default is used.
 * - DEMO_PASSWORD   Owner password; REQUIRED — no default is ever assumed.
 *
 * Dependencies resolve from the `frontend` workspace (`playwright` is already
 * its devDependency); no additional install is needed beyond
 * `pnpm --dir frontend install` and `pnpm --dir frontend exec playwright install`.
 *
 * Usage: `node scripts/demo/capture-screenshots.mjs`
 */

import { mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = fileURLToPath(new URL("../..", import.meta.url));
const outputDirectory = join(repoRoot, "docs", "screenshots");
const baseUrl = (process.env.DEMO_BASE_URL ?? "http://localhost:8000").replace(/\/+$/, "");
const username = process.env.DEMO_USERNAME;
const password = process.env.DEMO_PASSWORD;

/** Resolve Playwright from the frontend workspace without a root dependency. */
function loadPlaywright() {
  const requireFromFrontend = createRequire(new URL("../frontend/package.json", import.meta.url));
  return requireFromFrontend("playwright");
}

function fail(message) {
  console.error(`[capture-screenshots] ${message}`);
  process.exit(1);
}

async function capture(browser) {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
  });
  const page = await context.newPage();
  const shots = [];

  const shoot = async (name) => {
    const path = join(outputDirectory, name);
    await page.screenshot({ path });
    shots.push(path);
    console.log(`captured ${path}`);
  };

  // Entry page: wait generously — the target server may still be starting up.
  await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { name: "Open your writing studio" }).waitFor({
    timeout: 60_000,
  });
  if (await page.getByRole("button", { name: "Create owner" }).isVisible()) {
    throw new Error(
      "This instance has no owner yet. Complete the first-run setup in a browser first (see examples/demo-workspace/README.md), then rerun.",
    );
  }
  await shoot("01-login.png");

  // Sign in and land on the project library.
  await page.getByLabel("Password").fill(password);
  if (username !== undefined) {
    await page.getByLabel("Username").fill(username);
  }
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL(/\/projects$/, { timeout: 30_000 });
  await shoot("02-project-library.png");

  // A dedicated throwaway project keeps the capture off real user data.
  await page.getByLabel("Title").fill("Screenshot Demo — safe to delete");
  await page.getByRole("button", { name: /create project/i }).click();
  await page.waitForURL(/\/projects\/[^/]+\/manuscript/, { timeout: 30_000 });

  // Seed a line of prose so the Copilot demo shows a real editing session.
  const editor = page.locator(".cm-content");
  await editor.click();
  await page.keyboard.press("ControlOrMeta+a");
  await page.keyboard.type("# Chapter 1\n\nThe lighthouse keeper counted her debts aloud.");
  await page
    .locator(".studio-editor .editor__save-state")
    .waitFor({ state: "visible", timeout: 15_000 });

  // Copilot: fire the proposal and catch the generating state. The mock
  // provider settles in seconds — if it finishes before the frame lands, the
  // streamed preview is captured instead, which demonstrates the same step.
  await page.getByLabel("Proposal instruction").fill("Continue with the storm arriving early.");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  try {
    await page.getByRole("button", { name: "Generating…" }).waitFor({ timeout: 2_000 });
  } catch {
    // Generation already finished; the proposal preview below is the fallback shot.
  }
  await page.getByText("Proposed Markdown").waitFor({ timeout: 60_000 });
  await shoot("03-studio-copilot.png");

  await page.getByRole("button", { name: "Accept" }).click();
  await page.getByText("Proposed Markdown").waitFor({ state: "detached", timeout: 30_000 });

  // Export panel with the completed revision available for download.
  await page.getByRole("tab", { name: "Export" }).click();
  await page.waitForURL(/\/export$/, { timeout: 30_000 });
  await page.locator(".export-panel").waitFor({ timeout: 30_000 });
  await shoot("04-export-panel.png");

  await context.close();
  return shots;
}

async function main() {
  if (password === undefined || password === "") {
    fail("DEMO_PASSWORD is required (owner password of the target instance).");
  }
  mkdirSync(outputDirectory, { recursive: true });
  const { chromium } = loadPlaywright();
  const browser = await chromium.launch();
  try {
    const shots = await capture(browser);
    console.log(`[capture-screenshots] done: ${shots.length} screenshots in ${outputDirectory}`);
  } catch (error) {
    throw error instanceof Error ? error : new Error(String(error));
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error("[capture-screenshots] failed:", error instanceof Error ? error.message : error);
  process.exit(1);
});
