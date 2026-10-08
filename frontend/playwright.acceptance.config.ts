import { defineConfig, devices } from "@playwright/test";
import standard from "./playwright.ts.config";

/** Cross-engine audit keeps the same isolated TS runtime and workflow assertions. */
export default defineConfig({
  ...standard,
  workers: 2,
  projects: [
    { name: "firefox", use: { ...devices["Desktop Firefox"] } },
    { name: "webkit", use: { ...devices["Desktop Safari"] } },
  ],
});
