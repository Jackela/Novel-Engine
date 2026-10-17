import { expect, test } from "@playwright/test";

import { createProject } from "../project_document_helpers";

/**
 * The owner-setup flow in studio-ts.spec.ts runs before workflow files.
 * This regression exercises the built navigation with two volumes: its
 * command targets must remain below a readable, clickable document title.
 */
test("navigation preserves title space and keyboard commands across widths and themes", async ({
  page,
}) => {
  test.setTimeout(120_000);
  await expect(async () => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Open your writing studio" })).toBeVisible();
  }).toPass({ timeout: 60_000 });
  await page.getByLabel("Password").fill(["ts-e2e-owner", "password-1234"].join("-"));
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/projects$/);

  const projectId = await createProject(page, "Navigation Layout Ledger");
  const csrf = (await page.context().cookies()).find(
    (cookie) => cookie.name === "novel_engine_csrf",
  );
  expect(csrf).toBeDefined();
  const headers = { "x-csrf-token": csrf?.value ?? "" };
  const title = "第二章 The harbor bell rings again";
  const chapter = await page.request.post(`/api/projects/${projectId}/documents`, {
    headers,
    data: { kind: "chapter", title, content_markdown: "港口的钟响了两下。The bell rang twice." },
  });
  expect(chapter.status(), await chapter.text()).toBe(201);
  const volume = await page.request.post(`/api/projects/${projectId}/volumes`, {
    headers,
    data: { title: "第二卷 Volume Two" },
  });
  expect(volume.status(), await volume.text()).toBe(201);
  await page.reload();

  for (const [language, theme] of [
    ["en", "light"],
    ["zh", "dark"],
  ] as const) {
    await page
      .locator(".ui-language-switch__option")
      .filter({
        has: page.locator(`input[value="${language}"]`),
      })
      .click();
    await page
      .locator(".ui-theme-switch__option")
      .filter({
        has: page.locator(`input[value="${theme}"]`),
      })
      .click();
    for (const width of [1440, 1050, 390]) {
      await page.setViewportSize({ width, height: 900 });
      const document = page.getByRole("button", { name: title, exact: true });
      const row = page.locator(".document-row__wrap").filter({ has: document });
      await row.hover();
      const dimensions = await row.evaluate((element) => {
        const button = element.querySelector(".document-row");
        const commands = element.querySelectorAll(
          ".document-row__order button, .document-row__actions button",
        );
        if (!(button instanceof HTMLElement)) throw new Error("Document title is missing.");
        const bounds = element.getBoundingClientRect();
        const titleBounds = button.getBoundingClientRect();
        return {
          rowWidth: bounds.width,
          titleWidth: titleBounds.width,
          titleBottom: titleBounds.bottom,
          commandBounds: Array.from(commands, (command) => {
            const rect = command.getBoundingClientRect();
            return {
              x: rect.x,
              right: rect.right,
              top: rect.top,
              width: rect.width,
              height: rect.height,
            };
          }),
          left: bounds.left,
          right: bounds.right,
        };
      });
      expect(dimensions.titleWidth, `${width}px ${language} ${theme} title width`).toBeGreaterThan(
        dimensions.rowWidth * 0.95,
      );
      for (const command of dimensions.commandBounds) {
        expect(command.top).toBeGreaterThanOrEqual(dimensions.titleBottom);
        expect(command.width).toBeGreaterThanOrEqual(44);
        expect(command.height).toBeGreaterThanOrEqual(44);
        expect(command.x).toBeGreaterThanOrEqual(dimensions.left);
        expect(command.right).toBeLessThanOrEqual(dimensions.right + 1);
      }
      await document.click();
      await expect(page.locator(".editor__title")).toHaveValue(title);
      await document.focus();
      await page.keyboard.press("Tab");
      await expect(row.locator(".document-row__order button").first()).toBeFocused();
    }
  }
});
