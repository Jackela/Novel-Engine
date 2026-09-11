import { expect, type Locator, type Page, test } from "@playwright/test";

/**
 * Theme workflow acceptance (ADR-0010 / openspec 2026-09-11-dark-mode T3.1):
 * OS emulation decides while unlocked, an explicit lock wins over the OS and
 * survives reload through the pre-paint inline script (no first-frame flash),
 * and returning to system resumes live OS-following. Token assertions read
 * the computed `:root` values from base.css — the same values the unit
 * drift/contrast guards pin, here proven through the built SPA against the
 * TS backend.
 */

// Same owner as the other specs; created by studio-ts.spec.ts on the shared
// fresh store, so the login form may lag the start of this file.
const OWNER_PASSWORD = ["ts-e2e-owner", "password-1234"].join("-");

const DARK = {
  colorScheme: "dark",
  canvas: "rgb(16, 20, 21)",
  surface: "#15191a",
};
const LIGHT = {
  colorScheme: "light",
  canvas: "rgb(247, 248, 248)",
  surface: "#fff",
};

interface ThemeSnapshot {
  readonly dataTheme: string | null;
  readonly colorScheme: string;
  readonly canvas: string;
  readonly surface: string;
}

async function themeSnapshot(page: Page): Promise<ThemeSnapshot> {
  return page.evaluate(() => ({
    dataTheme: document.documentElement.dataset.theme ?? null,
    colorScheme: getComputedStyle(document.documentElement).colorScheme,
    canvas: getComputedStyle(document.documentElement).backgroundColor,
    surface: getComputedStyle(document.documentElement).getPropertyValue("--surface").trim(),
  }));
}

async function assertTokens(page: Page, theme: typeof DARK | typeof LIGHT): Promise<void> {
  const snapshot = await themeSnapshot(page);
  expect(snapshot.colorScheme, "color-scheme follows the active theme").toBe(theme.colorScheme);
  expect(snapshot.canvas, "canvas composite follows the active theme").toBe(theme.canvas);
  expect(snapshot.surface, "--surface follows the active theme").toBe(theme.surface);
}

/** The visible option label; radios are invisible (focusable via labels). */
function themeOption(page: Page, label: string): Locator {
  return page.locator(".ui-theme-switch__option").filter({
    has: page.getByText(label, { exact: true }),
  });
}

async function storedPreference(page: Page): Promise<string | null> {
  return page.evaluate(() => localStorage.getItem("novel_engine_theme"));
}

async function login(page: Page): Promise<void> {
  // Owner-creation precedence: in a full suite run studio-ts.spec.ts creates
  // the owner and its first test asserts the setup form, so this spec waits
  // for the login form and never touches the setup path there. The fallback
  // below only runs when the login form never appears (standalone filtered
  // runs of this file against a fresh store).
  try {
    await expect(async () => {
      await page.goto("/");
      await expect(page.getByRole("heading", { name: "Open your writing studio" })).toBeVisible();
    }).toPass({ timeout: 45_000 });
  } catch {
    await expect(async () => {
      await page.goto("/");
      await expect(page.getByRole("heading", { name: "Create the local owner" })).toBeVisible();
      await page.getByLabel("Password").fill(OWNER_PASSWORD);
      await page.getByRole("button", { name: "Create owner" }).click();
      await expect(page).toHaveURL(/\/projects$/);
    }).toPass({ timeout: 30_000 });
    return;
  }
  await page.getByLabel("Password").fill(OWNER_PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/projects$/);
}

test.describe
  .serial("theme selection workflow", () => {
    test("dark OS emulation renders every surface dark through entry, login, library, and studio", async ({
      page,
    }) => {
      await page.emulateMedia({ colorScheme: "dark" });
      await page.goto("/");

      // System path: no data-theme attribute (CSS decides), dark tokens.
      const entry = await themeSnapshot(page);
      expect(entry.dataTheme, "system mode stays unlocked").toBeNull();
      await assertTokens(page, DARK);
      await expect(page.locator(".ui-theme-switch__option")).toHaveCount(3);
      await expect(themeOption(page, "System (dark)")).toBeVisible();
      await expect(page.getByRole("radio", { name: "System (dark)", exact: true })).toBeChecked();

      // Library: dark glass fill through --surface-glass.
      await login(page);
      await expect(page.locator(".library__header")).toBeVisible();
      await assertTokens(page, DARK);
      expect(
        await page
          .locator(".library__header")
          .evaluate((el) => getComputedStyle(el).backgroundColor),
        "library header frost is the dark glass fill",
      ).toBe("rgba(16, 20, 21, 0.62)");

      // Studio: dark topbar glass, dark opaque editor, no blur on the editor.
      await page.getByLabel("Title").fill("Theme Probe Ledger");
      await page.getByRole("button", { name: /create project/i }).click();
      await expect(page).toHaveURL(/\/projects\/[^/]+\/manuscript/);
      await expect(page.locator(".studio-editor")).toBeVisible();
      await assertTokens(page, DARK);
      expect(
        await page.locator(".studio-topbar").evaluate((el) => getComputedStyle(el).backgroundColor),
        "topbar frost is the dark glass fill",
      ).toBe("rgba(16, 20, 21, 0.62)");
      const editor = await page.locator(".studio-editor").evaluate((el) => {
        const style = getComputedStyle(el);
        return {
          background: style.backgroundColor,
          backdropFilter: style.backdropFilter,
          webkitBackdropFilter: style.getPropertyValue("-webkit-backdrop-filter"),
        };
      });
      expect(editor.background, "editor surface is the opaque dark --surface").toBe(
        "rgb(21, 25, 26)",
      );
      expect(editor.backdropFilter, "editor stays blur-free (ADR-0009 exception)").toBe("none");
      // Engines that do not expose the prefixed alias report "" — also blur-free.
      expect(["none", ""], `prefixed blur: "${editor.webkitBackdropFilter}"`).toContain(
        editor.webkitBackdropFilter,
      );
    });

    test("dark lock wins over a light OS and survives reload", async ({ page }) => {
      await page.emulateMedia({ colorScheme: "light" });
      await page.goto("/");
      await expect(themeOption(page, "System (light)")).toBeVisible();

      await themeOption(page, "Dark").click();
      await expect(page.getByRole("radio", { name: "Dark", exact: true })).toBeChecked();
      expect(
        await page.evaluate(() => document.documentElement.dataset.theme),
        "lock is applied to <html> immediately",
      ).toBe("dark");
      expect(await storedPreference(page)).toBe("dark");
      await assertTokens(page, DARK);

      await page.reload();
      await expect(themeOption(page, "Dark")).toBeVisible();
      await expect(
        page.getByRole("radio", { name: "Dark", exact: true }),
        "switch state is reconstructed from storage",
      ).toBeChecked();
      expect(await storedPreference(page)).toBe("dark");
      expect(await themeSnapshot(page)).toMatchObject({ dataTheme: "dark" });
      await assertTokens(page, DARK);
    });

    test("light lock renders light under a dark OS with the attribute set before first paint", async ({
      page,
    }) => {
      await page.emulateMedia({ colorScheme: "dark" });
      await page.goto("/");
      await themeOption(page, "Light").click();
      await assertTokens(page, LIGHT);
      expect(await storedPreference(page)).toBe("light");

      // The probe records <html> inside the first animation frame, which runs
      // before the first painted frame: a late (post-paint) application would
      // be recorded as "(no-attribute)" — the flash this guard forbids.
      await page.addInitScript(() => {
        const probe = { theme: "(before-first-frame)" };
        (window as unknown as { __prePaintTheme: { theme: string } }).__prePaintTheme = probe;
        requestAnimationFrame(() => {
          probe.theme = document.documentElement?.dataset.theme ?? "(no-attribute)";
        });
      });
      await page.reload();

      const prePaint = await page.evaluate(
        () => (window as unknown as { __prePaintTheme: { theme: string } }).__prePaintTheme,
      );
      expect(prePaint.theme, "stored light lock precedes the first paint").toBe("light");
      expect(await themeSnapshot(page)).toMatchObject({ dataTheme: "light" });
      await assertTokens(page, LIGHT);
    });

    test("returning to system removes the lock and follows OS flips live", async ({ page }) => {
      await page.emulateMedia({ colorScheme: "dark" });
      await page.goto("/");
      await themeOption(page, "Dark").click();
      await assertTokens(page, DARK);

      await themeOption(page, "System (dark)").click();
      await expect(page.getByRole("radio", { name: "System (dark)", exact: true })).toBeChecked();
      expect(await storedPreference(page), "system is stored explicitly").toBe("system");
      expect(await themeSnapshot(page)).toMatchObject({ dataTheme: null });
      await assertTokens(page, DARK);

      // Live OS-follow without reload: with the lock removed the rendering
      // path is the pure-CSS media entry, and the matchMedia listener
      // refreshes the switch's system label to the new resolved target.
      await page.emulateMedia({ colorScheme: "light" });
      await expect(themeOption(page, "System (light)")).toBeVisible();
      await assertTokens(page, LIGHT);
      expect(await themeSnapshot(page)).toMatchObject({ dataTheme: null });

      await page.emulateMedia({ colorScheme: "dark" });
      await expect(themeOption(page, "System (dark)")).toBeVisible();
      await assertTokens(page, DARK);
    });
  });
