import { type BrowserContext, expect, type Page, test } from "@playwright/test";

import { createProject } from "../content_acceptance_helpers";

// Placement contract: same as studio_diagnostics_export.spec.ts — this
// directory sorts after studio-ts.spec.ts under Playwright's localeCompare
// file order, so the owner-setup file always starts in the first worker
// wave and the login polling below cannot starve it (see #467 PR notes).

// #652 (T5.1) lorebook initialization wizard workflow: a pasted draft segment
// runs one extraction Job on the trial provider (deterministic placeholder
// candidates, each labeled as trial output), the merged candidates are
// toggled and confirmed through the existing creation-plus-alias-write path,
// and a routed alias-write failure reports created-with-failed-aliases with
// retry before the entries settle as drafts in the Navigator. A second run
// that is abandoned leaves the lorebook untouched — extraction Jobs are
// audit records, never Lore entries.

// Same fragment-assembled credential as studio-ts.spec.ts, which owns the
// one-time owner setup on the shared store this suite logs into.
const OWNER_PASSWORD = ["ts-e2e-owner", "password-1234"].join("-");

/** The trial (mock) provider's deterministic placeholder candidates, by title. */
const TRIAL_CANDIDATES = [
  {
    title: "Placeholder Character",
    kind: "Character",
    aliases: "Trial Candidate",
    summary:
      "Sample character suggestion. Built-in trial provider placeholder; connect a real provider to extract lore from your draft.",
  },
  {
    title: "Placeholder World",
    kind: "World",
    aliases: "Trial Setting",
    summary:
      "Sample world suggestion. Built-in trial provider placeholder; connect a real provider to extract lore from your draft.",
  },
] as const;

/** A trial-writing segment with identifiable names; content is inert to the mock provider. */
const FIRST_SEGMENT = [
  "Mira Voss steadied the lantern against the salt wind.",
  "Vellen Harbor had swallowed taller smugglers than her, and Old Bram, the lighthouse keeper, still counted every boat by name.",
  "She pressed the tin whistle into her coat and climbed.",
].join("\n\n");

test.describe
  .serial("#652 lorebook initialization wizard workflow", () => {
    test.setTimeout(150_000);

    let studioContext: BrowserContext;
    let studio: Page;

    test.beforeAll(async ({ browser }) => {
      studioContext = await browser.newContext();
      studio = await studioContext.newPage();
      // In the full suite the owner setup is owned by studio-ts.spec.ts, which
      // starts in the first worker wave; this file only logs in. Run
      // standalone (`-- lorebook_wizard`) against the same fresh store, no
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

    test("confirmed candidates land as draft lore entries after a routed alias-write failure retries clean", async () => {
      const projectId = await createProject(studio, "Lorebook Wizard Ledger");

      // Deep link activates the lore tab; an empty lorebook hosts the wizard
      // as the onboarding moment, and the trial provider carries the #615
      // trial-mode wording family.
      await studio.goto(`/projects/${projectId}/manuscript?inspector=lore`);
      await expect(studio.getByRole("tab", { name: "Lore" })).toHaveAttribute(
        "aria-selected",
        "true",
      );
      await expect(
        studio.getByRole("heading", { name: "Lorebook wizard", exact: true }),
      ).toBeVisible();
      await expect(
        studio.getByText(
          "This project has no lore entries yet. Feed it a draft and confirm the suggestions to build your lorebook.",
        ),
      ).toBeVisible();
      await expect(
        studio.getByText(
          "Extraction runs on the built-in trial provider — connect a real one in Settings for real extraction.",
        ),
      ).toBeVisible();

      // One pasted segment becomes one extraction segment; the mock provider
      // answers with the fixed placeholder set, so the segment completes with
      // exactly two suggestions.
      await studio.getByRole("textbox", { name: "Paste a draft segment" }).fill(FIRST_SEGMENT);
      await studio.getByRole("button", { name: "Extract segment" }).click();
      const segments = studio.getByRole("list", { name: "Extraction segments" });
      await expect(segments.getByText("Pasted text")).toBeVisible();
      await expect(segments.getByText("2 suggestions")).toBeVisible();

      // The merged candidate list carries both mock candidates, selected by
      // default with their suggested aliases; the summary preview labels the
      // trial output as such.
      const candidates = studio.getByRole("region", { name: "Suggested lore entries" });
      await expect(
        candidates.getByText(
          "Suggestions stay in this session — nothing is saved until you confirm.",
        ),
      ).toBeVisible();
      for (const candidate of TRIAL_CANDIDATES) {
        const row = candidates.locator("li").filter({ hasText: candidate.title });
        await expect(row.getByRole("checkbox", { name: candidate.title })).toBeChecked();
        await expect(row.getByText(candidate.kind, { exact: true })).toBeVisible();
        await expect(
          studio.getByLabel(`Aliases (comma-separated) — ${candidate.title}`),
        ).toHaveValue(candidate.aliases);
        await row.locator("summary").click();
        await expect(row.getByText(candidate.summary)).toBeVisible();
      }

      // Toggling a candidate drives the confirm command's count; it goes back
      // in for a full two-entry confirmation.
      await candidates
        .locator("li")
        .filter({ hasText: TRIAL_CANDIDATES[0].title })
        .getByRole("checkbox", { name: TRIAL_CANDIDATES[0].title })
        .uncheck();
      await expect(
        studio.getByRole("button", { name: "Add 1 selected to lorebook" }),
      ).toBeVisible();
      await candidates
        .locator("li")
        .filter({ hasText: TRIAL_CANDIDATES[0].title })
        .getByRole("checkbox", { name: TRIAL_CANDIDATES[0].title })
        .check();
      const confirm = studio.getByRole("button", { name: "Add 2 selected to lorebook" });
      await expect(confirm).toBeVisible();

      // Routed alias-write failure: both candidates are created through the
      // ordinary document-creation call, but every alias write fails, so each
      // result reports created-with-failed-aliases and keeps its aliases.
      await studio.route(`**/api/projects/${projectId}/documents/*/aliases`, async (route) => {
        await route.fulfill({
          status: 503,
          contentType: "application/json",
          body: JSON.stringify({
            error: { code: "SERVICE_UNAVAILABLE", message: "Alias write is down." },
          }),
        });
      });
      await confirm.click();
      const results = studio.getByRole("region", { name: "Confirmation results" });
      for (const candidate of TRIAL_CANDIDATES) {
        const row = results.locator("li").filter({ hasText: candidate.title });
        await expect(row.getByText("Created — alias write failed")).toBeVisible();
        await expect(row.getByRole("alert")).toHaveText("Alias write is down.");
        await expect(row.getByText(`Aliases kept for retry: ${candidate.aliases}`)).toBeVisible();
      }

      // Retry after recovery re-issues only the alias write; both outcomes
      // settle as plain created drafts with the error surface cleared.
      await studio.unroute(`**/api/projects/${projectId}/documents/*/aliases`);
      for (const candidate of TRIAL_CANDIDATES) {
        await results
          .locator("li")
          .filter({ hasText: candidate.title })
          .getByRole("button", { name: "Retry alias write" })
          .click();
        await expect(
          results.locator("li").filter({ hasText: candidate.title }).getByText("Created as draft"),
        ).toBeVisible();
      }
      await expect(results.getByRole("alert")).toHaveCount(0);

      // Confirmation used the existing creation path: after a shell reload
      // the Navigator's Characters and World sections carry the entries as
      // draft lore rows, and the populated lorebook keeps the wizard with its
      // persistent-entry hint.
      await studio.reload();
      await studio.getByRole("button", { name: "Characters", exact: true }).click();
      await expect(
        studio.getByRole("button", { name: "Placeholder Character — draft" }),
      ).toBeVisible();
      await studio.getByRole("button", { name: "World", exact: true }).click();
      await expect(studio.getByRole("button", { name: "Placeholder World — draft" })).toBeVisible();
      await studio.goto(`/projects/${projectId}/manuscript?inspector=lore`);
      await expect(
        studio.getByText(
          "Extract more suggestions from draft material; confirmed entries land as drafts like any new entry.",
        ),
      ).toBeVisible();
    });

    test("abandoning a second run discards its candidates and leaves the lorebook unchanged", async () => {
      const projectId = await createProject(studio, "Lorebook Wizard Abandon Ledger");
      await studio.goto(`/projects/${projectId}/manuscript?inspector=lore`);
      await expect(
        studio.getByRole("heading", { name: "Lorebook wizard", exact: true }),
      ).toBeVisible();

      // A fresh segment extracts session-only candidates again.
      await studio
        .getByRole("textbox", { name: "Paste a draft segment" })
        .fill(
          "The ferryman Ilse counted fares in old coins below the Vellen breakwater; nobody remembered when the bell tower flooded, only that it stayed silent after.",
        );
      await studio.getByRole("button", { name: "Extract segment" }).click();
      await expect(
        studio.getByRole("list", { name: "Extraction segments" }).getByText("2 suggestions"),
      ).toBeVisible();
      await expect(studio.getByRole("region", { name: "Suggested lore entries" })).toBeVisible();

      await studio.getByRole("button", { name: "Discard suggestions" }).click();

      // The whole wizard session is gone — no candidates, no segments — and
      // the paste box is back to its empty, extract-disabled resting state.
      await expect(studio.getByRole("region", { name: "Suggested lore entries" })).toHaveCount(0);
      await expect(studio.getByRole("list", { name: "Extraction segments" })).toHaveCount(0);
      await expect(studio.getByRole("textbox", { name: "Paste a draft segment" })).toHaveValue("");
      await expect(studio.getByRole("button", { name: "Extract segment" })).toBeDisabled();

      // Abandonment persisted nothing: the project shell still carries no
      // character or world documents — the extraction Job is audit-only.
      const shellResponse = await studio.request.get(`/api/projects/${projectId}`);
      expect(shellResponse.ok()).toBe(true);
      const shell = (await shellResponse.json()) as { documents: ReadonlyArray<{ kind: string }> };
      expect(
        shell.documents.filter(
          (document) => document.kind === "character" || document.kind === "world",
        ),
      ).toEqual([]);
    });
  });
