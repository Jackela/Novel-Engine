import { describe, expect, it } from "vitest";

import { buildApp } from "../../src/apps/api/app.js";
import { loadServerConfig } from "../../src/shared/infrastructure/config/server_config.js";
import { fixtureApiKey } from "../credential_fixtures.js";
import {
  cookieHeader,
  cookieJar,
  loginOwner,
  makeDataDirectory,
  setupOwner,
  TEST_SESSION_SECRET,
} from "./auth_helpers.js";

function providerConfig(directory: string) {
  return loadServerConfig({
    envFile: null,
    workingDirectory: directory,
    env: {
      APP_ENVIRONMENT: "testing",
      SECURITY_SECRET_KEY: TEST_SESSION_SECRET,
      DB_URL: "sqlite:///./novel-engine.sqlite3",
      LLM_PROVIDER: "dashscope",
      DASHSCOPE_API_KEY: fixtureApiKey("test", "dashscope-catalog-credential"),
      DASHSCOPE_API_BASE: "https://dashscope.catalog.example.test/v1",
      DASHSCOPE_MODEL: "catalog-qwen-model",
      LLM_API_KEY: fixtureApiKey("test", "compatible-catalog-credential"),
      LLM_API_BASE: "https://compatible.catalog.example.test/v1",
      OPENAI_COMPATIBLE_MODEL: "catalog-compatible-model",
    },
  });
}

describe("provider catalog API", () => {
  it("requires an owner and returns only resolved provider facts", async () => {
    const directory = await makeDataDirectory();
    const config = providerConfig(directory);
    const app = await buildApp({ logger: false, config });
    try {
      const anonymous = await app.inject({ method: "GET", url: "/api/providers" });
      expect(anonymous.statusCode).toBe(401);
      expect(anonymous.json()).toMatchObject({ error: { code: "UNAUTHORIZED" } });

      await setupOwner(app);
      const login = await loginOwner(app);
      const response = await app.inject({
        method: "GET",
        url: "/api/providers",
        headers: { cookie: cookieHeader(cookieJar(login)) },
      });

      expect(response.statusCode).toBe(200);
      expect(response.json()).toEqual({
        providers: [
          {
            provider: "mock",
            configured: true,
            model: "deterministic-story-v1",
            is_default: false,
          },
          {
            provider: "dashscope",
            configured: true,
            model: "catalog-qwen-model",
            is_default: true,
          },
          {
            provider: "openai_compatible",
            configured: true,
            model: "catalog-compatible-model",
            is_default: false,
          },
        ],
      });
      expect(response.body).not.toContain("test-dashscope-catalog-credential");
      expect(response.body).not.toContain("test-compatible-catalog-credential");
      expect(response.body).not.toContain("dashscope.catalog.example.test");
      expect(response.body).not.toContain("compatible.catalog.example.test");
    } finally {
      await app.close();
    }
  });
});
