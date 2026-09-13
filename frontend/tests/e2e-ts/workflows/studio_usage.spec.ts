import { expect, type Page, test } from "@playwright/test";

import type { ProjectUsage } from "../../../src/app/types/studio";
import { createProject, typeChapter } from "../project_document_helpers";

const OWNER_PASSWORD = ["ts-e2e-owner", "password-1234"].join("-");

type UsagePayload = Omit<ProjectUsage, "daily"> & {
  daily: NonNullable<ProjectUsage["daily"]>;
};

async function usageResponse(page: Page, projectId: string): Promise<UsagePayload> {
  const responsePromise = page.waitForResponse(
    (response) =>
      response.request().method() === "GET" &&
      new URL(response.url()).pathname === `/api/projects/${projectId}/usage`,
  );
  await page.getByRole("tab", { name: "Usage" }).click();
  const response = await responsePromise;
  expect(response.status(), await response.text()).toBe(200);
  return (await response.json()) as UsagePayload;
}

async function generateUsage(page: Page): Promise<void> {
  await page.getByPlaceholder("Describe the change or direction...").fill("Add a quiet storm.");
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.getByRole("button", { name: "Accept" })).toBeVisible();
  await page.getByRole("button", { name: "Accept" }).click();
  await expect(page.getByText("Proposed Markdown")).toHaveCount(0);
  await expect(page.locator(".studio-editor .editor__save-state")).toHaveText(/saved/i);
}

function totalTokens(
  usage: UsagePayload["per_model"][number] | UsagePayload["daily"][number],
): number {
  return usage.prompt_tokens + usage.completion_tokens;
}

async function assertUsageView(page: Page, usage: UsagePayload): Promise<void> {
  await expect(
    page.getByLabel(`Requests: ${usage.request_count.toLocaleString("en-US")}`),
  ).toBeVisible();
  await expect(
    page.getByLabel(`Prompt tokens: ${usage.prompt_tokens.toLocaleString("en-US")}`),
  ).toBeVisible();
  await expect(
    page.getByLabel(`Completion tokens: ${usage.completion_tokens.toLocaleString("en-US")}`),
  ).toBeVisible();
  const rows = page.locator(".usage__daily-row");
  await expect(rows).toHaveCount(usage.daily.some((bucket) => bucket.request_count > 0) ? 30 : 0);
  if (usage.daily.some((bucket) => bucket.request_count > 0)) {
    await expect(rows.locator(".usage__daily-date")).toHaveText(
      usage.daily.map((bucket) => bucket.date),
    );
    await expect(rows.locator(".usage__daily-count")).toHaveText(
      usage.daily.map((bucket) => totalTokens(bucket).toLocaleString("en-US")),
    );
  }
  const modelRows = page.getByRole("table", { name: "Usage per model" }).locator("tbody tr");
  await expect(modelRows).toHaveCount(usage.per_model.length);
  for (const [index, row] of usage.per_model.entries())
    await expect(modelRows.nth(index).locator("th, td")).toHaveText([
      row.model,
      row.requests.toLocaleString("en-US"),
      row.prompt_tokens.toLocaleString("en-US"),
      row.completion_tokens.toLocaleString("en-US"),
    ]);
}

async function assertZeroUsageView(page: Page): Promise<void> {
  await expect(page.getByLabel("Requests: 0")).toBeVisible();
  await expect(page.getByLabel("Prompt tokens: 0")).toBeVisible();
  await expect(page.getByLabel("Completion tokens: 0")).toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0);
  await expect(page.getByRole("region", { name: "Daily usage, last 30 days" })).toHaveCount(0);
  await expect(page.getByRole("table", { name: "Usage per model" })).toHaveCount(0);
}

test.describe
  .serial("studio usage browser contract", () => {
    test.setTimeout(150_000);
    let studio: Page;

    test.beforeAll(async ({ browser }) => {
      const context = await browser.newContext();
      studio = await context.newPage();
      await expect(async () => {
        await studio.goto("/");
        await expect(
          studio.getByRole("heading", { name: "Open your writing studio" }),
        ).toBeVisible();
      }).toPass({ timeout: 60_000 });
      await studio.getByLabel("Password").fill(OWNER_PASSWORD);
      await studio.getByRole("button", { name: "Sign in" }).click();
      await expect(studio).toHaveURL(/\/projects$/);
    });

    test.afterAll(async () => {
      await studio.context().close();
    });

    test("renders empty usage, then mirrors generated server totals and daily rows", async () => {
      const projectId = await createProject(studio, "Usage Mirror Ledger");
      await typeChapter(studio, "# Chapter 1\n\nA quiet harbor waited.");

      const empty = await usageResponse(studio, projectId);
      expect(empty).toMatchObject({
        project_id: projectId,
        request_count: 0,
        prompt_tokens: 0,
        completion_tokens: 0,
        per_model: [],
      });
      expect(empty.daily).toHaveLength(30);
      await expect(studio.getByText("No usage recorded yet.")).toBeVisible();
      await expect(studio.getByRole("region", { name: "Daily usage, last 30 days" })).toHaveCount(
        0,
      );
      await expect(studio.getByRole("table", { name: "Usage per model" })).toHaveCount(0);

      await studio.getByRole("tab", { name: "Copilot" }).click();
      await generateUsage(studio);
      await studio.getByRole("tab", { name: "Usage" }).click();
      const refreshResponse = studio.waitForResponse(
        (response) =>
          response.request().method() === "GET" &&
          new URL(response.url()).pathname === `/api/projects/${projectId}/usage`,
      );
      await studio.getByRole("button", { name: "Refresh usage" }).click();
      const generated = (await (await refreshResponse).json()) as UsagePayload;

      expect(generated.project_id).toBe(projectId);
      expect(generated.request_count).toBe(1);
      expect(generated.prompt_tokens + generated.completion_tokens).toBeGreaterThan(0);
      expect(generated.daily).toHaveLength(30);
      expect(
        generated.daily.every(
          (bucket, index) => index === 0 || generated.daily[index - 1]?.date < bucket.date,
        ),
      ).toBe(true);
      expect(generated.daily.reduce((sum, bucket) => sum + bucket.request_count, 0)).toBe(
        generated.request_count,
      );
      expect(generated.per_model.reduce((sum, row) => sum + row.requests, 0)).toBe(
        generated.request_count,
      );
      expect(generated.per_model.reduce((sum, row) => sum + totalTokens(row), 0)).toBe(
        generated.prompt_tokens + generated.completion_tokens,
      );

      await assertUsageView(studio, generated);
      const dailyRows = studio.locator(".usage__daily-row");
      expect(
        await dailyRows
          .filter({
            hasText: generated.daily.find((bucket) => bucket.request_count > 0)?.date ?? "",
          })
          .locator(".usage__daily-bar")
          .evaluate(
            (bar) =>
              bar instanceof HTMLElement &&
              Number.parseFloat(bar.style.width) > 0 &&
              bar.getBoundingClientRect().width > 0,
          ),
      ).toBe(true);
    });

    test("keeps prior usage through a 503 and restores refresh focus after recovery", async () => {
      const projectId = await createProject(studio, "Usage Recovery Ledger");
      await typeChapter(studio, "# Chapter 1\n\nThe signal returned.");
      await generateUsage(studio);
      const loaded = await usageResponse(studio, projectId);
      const refresh = studio.getByRole("button", { name: "Refresh usage" });
      let failNext = true;
      await studio.route(`**/api/projects/${projectId}/usage`, async (route) => {
        if (failNext) {
          failNext = false;
          await route.fulfill({
            status: 503,
            contentType: "application/json",
            body: JSON.stringify({
              error: { code: "SERVICE_UNAVAILABLE", message: "Usage is down." },
            }),
          });
          return;
        }
        await route.continue();
      });
      const failed = studio.waitForResponse(
        (response) =>
          response.request().method() === "GET" &&
          new URL(response.url()).pathname === `/api/projects/${projectId}/usage` &&
          response.status() === 503,
      );
      try {
        await refresh.click();
        await failed;
        await expect(studio.getByRole("alert")).toContainText("Usage is down.");
        await assertUsageView(studio, loaded);
        await expect(refresh).toBeEnabled();
        await expect(refresh).toBeFocused();
        await studio.unroute(`**/api/projects/${projectId}/usage`);
        const recovered = studio.waitForResponse(
          (response) =>
            response.request().method() === "GET" &&
            new URL(response.url()).pathname === `/api/projects/${projectId}/usage` &&
            response.status() === 200,
        );
        await refresh.click();
        const recoveredPayload = (await (await recovered).json()) as UsagePayload;
        expect(recoveredPayload.project_id).toBe(loaded.project_id);
        expect(recoveredPayload.request_count).toBe(loaded.request_count);
        expect(recoveredPayload.prompt_tokens).toBe(loaded.prompt_tokens);
        expect(recoveredPayload.completion_tokens).toBe(loaded.completion_tokens);
        expect(recoveredPayload.per_model).toEqual(loaded.per_model);
        await expect(studio.getByRole("alert")).toHaveCount(0);
        await assertUsageView(studio, recoveredPayload);
        await expect(refresh).toBeFocused();
      } finally {
        await studio.unroute(`**/api/projects/${projectId}/usage`);
      }
    });

    test("drops stale project A usage while navigating to zero-usage project B", async () => {
      const projectA = await createProject(studio, "Usage A");
      await typeChapter(studio, "# Chapter 1\n\nA has usage.");
      await generateUsage(studio);
      await usageResponse(studio, projectA);
      await studio.getByRole("button", { name: "Back to projects" }).click();
      await expect(studio.getByRole("heading", { name: "Projects" })).toBeVisible();
      const projectB = await createProject(studio, "Usage B");
      await expect(studio).toHaveURL(new RegExp(`/projects/${projectB}/manuscript`));
      await studio.goto(`/projects/${projectA}/manuscript?inspector=usage`);
      await expect(studio.getByRole("tab", { name: "Usage" })).toHaveAttribute(
        "aria-selected",
        "true",
      );
      await expect(studio.getByLabel(/Requests:/)).toBeVisible();

      let releaseA: (() => void) | undefined;
      const heldA = new Promise<void>((resolve) => {
        releaseA = resolve;
      });
      let handlerCompleted: (() => void) | undefined;
      const completed = new Promise<void>((resolve) => {
        handlerCompleted = resolve;
      });
      let responseFetched: (() => void) | undefined;
      let fetched = false;
      const started = new Promise<void>((resolve) => {
        responseFetched = resolve;
      });
      await studio.route(`**/api/projects/${projectA}/usage`, async (route) => {
        const response = await route.fetch();
        fetched = true;
        responseFetched?.();
        await heldA;
        try {
          await route.fulfill({ response });
        } finally {
          handlerCompleted?.();
        }
      });
      const refresh = studio.getByRole("button", { name: "Refresh usage" });
      try {
        await refresh.click();
        await expect(studio.locator('[aria-label="Refreshing usage"]')).toBeVisible();
        await started;
        await studio.getByRole("button", { name: "Back to projects" }).click();
        await expect(studio.getByRole("heading", { name: "Projects" })).toBeVisible();
        await studio.getByRole("button", { name: "Usage B" }).click();
        await expect(studio).toHaveURL(new RegExp(`/projects/${projectB}/manuscript`));
        const emptyB = await usageResponse(studio, projectB);
        expect(emptyB).toMatchObject({
          project_id: projectB,
          request_count: 0,
          prompt_tokens: 0,
          completion_tokens: 0,
          per_model: [],
        });
        expect(emptyB.daily).toHaveLength(30);
        await assertZeroUsageView(studio);
        await expect(studio.getByText("No usage recorded yet.")).toBeVisible();
        releaseA?.();
        await completed;
        await expect(studio).toHaveURL(new RegExp(`/projects/${projectB}/manuscript`));
        await assertZeroUsageView(studio);
      } finally {
        releaseA?.();
        if (fetched) await completed;
        await studio.unroute(`**/api/projects/${projectA}/usage`);
      }
    });
  });
