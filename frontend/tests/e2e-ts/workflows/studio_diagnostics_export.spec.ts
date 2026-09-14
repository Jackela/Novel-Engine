import { readFileSync } from "node:fs";

import { type BrowserContext, expect, type Page, test } from "@playwright/test";

import { createProject } from "../content_acceptance_helpers";

// Placement contract: same as studio_review_export.spec.ts — this directory
// sorts after studio-ts.spec.ts under Playwright's localeCompare file order,
// so the owner-setup file always starts in the first worker wave and the
// login polling below cannot starve it (see #467 PR notes).

// #654 (T4.1) diagnostics export workflow: the Settings action downloads the
// project-scoped summary as a client-named local JSON file. The workflow
// asserts the product identity and database-health fields are present, the
// recent-error summary carries its explicit empty state, and the two secrets
// the e2e stack configures — the session secret and a seeded DashScope key —
// are reported as booleans only and never occur as values in the file.

// Same fragment-assembled credential as studio-ts.spec.ts, which owns the
// one-time owner setup on the shared store this suite logs into.
const OWNER_PASSWORD = ["ts-e2e-owner", "password-1234"].join("-");

// Known secret values of the e2e stack: start-ts-e2e-stack.mjs seeds these
// defaults unless the caller overrides the environment, so mirroring the
// same fallback here lets the absence assertions run against the exact
// values the served backend holds. Fragment-assembled so no literal is
// bound to a credential-shaped name (same rule as the owner password).
const SESSION_SECRET =
  process.env.SECURITY_SECRET_KEY ?? ["test-secret-key-for", "ts-playwright-1234567890"].join("-");
const DASHSCOPE_API_KEY =
  process.env.DASHSCOPE_API_KEY ?? ["ne-e2e-diagnostics", "redaction-dashscope-key"].join("-");

/** The wire shape of the diagnostics export (#654); snake_case at the route. */
interface DiagnosticsExport {
  readonly generated_at: string;
  readonly product: { readonly name: string; readonly version: string };
  readonly runtime: {
    readonly platform: string;
    readonly architecture: string;
    readonly node_version: string;
  };
  readonly configuration: {
    readonly provider: { readonly id: string; readonly configured: boolean };
    readonly keys: {
      readonly session_secret: boolean;
      readonly dashscope_api_key: boolean;
      readonly openai_compatible_api_key: boolean;
    };
  };
  readonly database: {
    readonly quick_check: string;
    readonly journal_mode: string;
    readonly foreign_keys: boolean;
    readonly owner_configured: boolean;
  };
  readonly recent_errors: ReadonlyArray<{
    readonly message: string;
    readonly occurred_at: string;
  }>;
}

test.describe
  .serial("#654 diagnostics export workflow", () => {
    test.setTimeout(120_000);

    let studioContext: BrowserContext;
    let studio: Page;

    test.beforeAll(async ({ browser }) => {
      studioContext = await browser.newContext();
      studio = await studioContext.newPage();
      // In the full suite the owner setup is owned by studio-ts.spec.ts, which
      // starts in the first worker wave; this file only logs in. Run
      // standalone (`-- diagnostics_export`) against the same fresh store, no
      // other file creates the owner, so after the grace period this spec
      // completes the one-time setup itself with the same credential. Each
      // poll reloads the entry page — the rendered form only reflects the
      // owner's existence after a fresh load. Either path ends signed in at
      // the projects list.
      let ownerConfigured = false;
      const deadline = Date.now() + 20_000;
      while (!ownerConfigured && Date.now() < deadline) {
        await studio.goto("/");
        ownerConfigured = await studio
          .getByRole("heading", { name: "Open your writing studio" })
          .isVisible();
        if (!ownerConfigured) {
          await studio.waitForTimeout(2_000);
        }
      }
      await studio.getByLabel("Password").fill(OWNER_PASSWORD);
      await studio
        .getByRole("button", { name: ownerConfigured ? "Sign in" : "Create owner" })
        .click();
      await expect(studio).toHaveURL(/\/projects$/);
    });

    test.afterAll(async () => {
      await studioContext.close();
    });

    test("Settings exports diagnostics as a local JSON file with every configured secret absent", async () => {
      const projectId = await createProject(studio, "Diagnostics Export Ledger");

      // Deep link selects the Settings panel; the privacy statement mounts
      // with the action, so the export contract is visible before firing.
      await studio.goto(`/projects/${projectId}/settings`);
      await expect(studio.getByRole("heading", { name: "Project settings" })).toBeVisible();
      await expect(studio.getByText(/nothing you wrote, no API keys/)).toBeVisible();

      const [download] = await Promise.all([
        studio.waitForEvent("download"),
        studio.getByRole("button", { name: "Export diagnostics" }).click(),
      ]);
      // Client-derived filename: novel-engine-diagnostics-<UTC date>.json.
      expect(download.suggestedFilename()).toMatch(
        /^novel-engine-diagnostics-\d{4}-\d{2}-\d{2}\.json$/,
      );

      const downloadPath = await download.path();
      if (!downloadPath) {
        throw new Error("The diagnostics export produced no downloaded file.");
      }
      const exportText = readFileSync(downloadPath, "utf8");
      const summary = JSON.parse(exportText) as DiagnosticsExport;

      // Structural silhouette: the export carries exactly the redacted
      // summary's fields — no additional surface can appear unnoticed.
      expect(Object.keys(summary).sort()).toEqual([
        "configuration",
        "database",
        "generated_at",
        "product",
        "recent_errors",
        "runtime",
      ]);
      expect(Number.isNaN(Date.parse(summary.generated_at))).toBe(false);

      // Product identity matches the /version authority the shell renders
      // (that response carries additional build fields; identity is the
      // shared name + version pair).
      const versionResponse = await studio.request.get("/version");
      expect(versionResponse.ok()).toBe(true);
      const identity = (await versionResponse.json()) as { name: string; version: string };
      expect(summary.product.name).toBe(identity.name);
      expect(summary.product.version).toBe(identity.version);

      // Runtime and configuration state: the deterministic default provider
      // is configured, and both stack secrets are reported as booleans.
      expect(summary.runtime.platform).not.toBe("");
      expect(summary.runtime.architecture).not.toBe("");
      expect(summary.runtime.node_version).not.toBe("");
      expect(summary.configuration.provider).toEqual({ id: "mock", configured: true });
      expect(summary.configuration.keys.session_secret).toBe(true);
      expect(summary.configuration.keys.dashscope_api_key).toBe(true);
      expect(typeof summary.configuration.keys.openai_compatible_api_key).toBe("boolean");

      // Database health: the doctor field family of a healthy WAL store.
      expect(summary.database).toEqual({
        quick_check: "ok",
        journal_mode: "wal",
        foreign_keys: true,
        owner_configured: true,
      });

      // A fresh project carries the explicit empty recent-error state.
      expect(summary.recent_errors).toEqual([]);

      // The redaction rule end to end: both secrets the stack configures are
      // present in the backend's environment yet never occur in the file.
      expect(exportText).not.toContain(SESSION_SECRET);
      expect(exportText).not.toContain(DASHSCOPE_API_KEY);
    });
  });
