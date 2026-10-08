import { randomBytes } from "node:crypto";
import { writeFile } from "node:fs/promises";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import type { ServerConfig } from "../../src/shared/infrastructure/config/server_config.js";
import { locateWorkspaceRoot } from "../../src/shared/infrastructure/workspace_manifest.js";
import { fixtureApiKey } from "../credential_fixtures.js";
import { expectRejected, generatedSecret, load, makeWorkspace } from "./server_config_helpers.js";

describe("environment configuration surface", () => {
  it("applies the adjudicated defaults without configuration", async () => {
    const workspace = await makeWorkspace();
    const config = load({ workingDirectory: workspace }) as ServerConfig;

    expect(config.environment).toBe("development");
    expect(config.sessionSecret).toBeUndefined();
    expect(config.databaseUrl).toBe("sqlite:///./data/novel-engine.sqlite3");
    expect(config.databasePath).toBe(join(workspace, "data", "novel-engine.sqlite3"));
    expect(config.dataDirectory).toBe(join(workspace, "data"));
    expect(config.host).toBe("0.0.0.0");
    expect(config.port).toBe(8000);
    expect(config.corsOrigins).toEqual([
      "http://localhost:5173",
      "http://localhost:4173",
      "http://localhost:8000",
    ]);
    expect(config.trustedProxies).toEqual([]);
    expect(config.authRateLimitPerMinute).toBe(5);
  });

  it("resolves the structured logger level and refuses an unknown one (DR-041)", async () => {
    const workspace = await makeWorkspace();

    const unset = load({ workingDirectory: workspace }) as ServerConfig;
    expect(unset.logLevel).toBe("info");

    const explicit = load({
      workingDirectory: workspace,
      env: { LOG_LEVEL: "debug" },
    }) as ServerConfig;
    expect(explicit.logLevel).toBe("debug");

    const normalized = load({
      workingDirectory: workspace,
      env: { LOG_LEVEL: " WARN " },
    }) as ServerConfig;
    expect(normalized.logLevel).toBe("warn");

    const rejected = expectRejected(
      load({ workingDirectory: workspace, env: { LOG_LEVEL: "verbose" } }),
    );
    expect(rejected.message).toContain("LOG_LEVEL must be one of");
  });

  it("anchors default database paths to the workspace root, not the working directory", () => {
    const config = load({}) as ServerConfig;

    const workspaceRoot = locateWorkspaceRoot();
    expect(config.databasePath).toBe(join(workspaceRoot, "data", "novel-engine.sqlite3"));
    expect(config.dataDirectory).toBe(join(workspaceRoot, "data"));
  });

  it("gives process provider settings precedence over .env.local values", async () => {
    const workspace = await makeWorkspace();
    const envFile = join(workspace, ".env.local");
    await writeFile(
      envFile,
      [
        "LLM_PROVIDER=mock",
        "LLM_MODEL=file-model",
        "DASHSCOPE_API_KEY=file-dashscope-key",
        "DASHSCOPE_API_BASE=https://file-dashscope.example/v1",
        "DASHSCOPE_MODEL=file-dashscope-model",
        "DASHSCOPE_REVIEW_MODEL=file-review-model",
        "OPENAI_API_KEY=file-openai-key",
        "OPENAI_API_BASE=https://file-openai.example/v1",
        "OPENAI_COMPATIBLE_MODEL=file-openai-model",
        "DASHSCOPE_TRANSPORT_MODE=text_generation",
        "LLM_TIMEOUT=45",
        "LLM_RETRY_ATTEMPTS=2",
        "LLM_RETRY_DELAY=0.5",
      ].join("\n"),
    );

    const config = load({
      envFile,
      workingDirectory: workspace,
      env: {
        LLM_PROVIDER: "dashscope",
        LLM_MODEL: "env-model",
        DASHSCOPE_API_KEY: fixtureApiKey("env", "dashscope-key"),
        DASHSCOPE_API_BASE: "https://env-dashscope.example/v1",
        DASHSCOPE_MODEL: "env-dashscope-model",
        DASHSCOPE_REVIEW_MODEL: "env-review-model",
        LLM_API_KEY: fixtureApiKey("env", "openai-key"),
        LLM_API_BASE: "https://env-openai.example/v1",
        OPENAI_COMPATIBLE_MODEL: "env-openai-model",
        DASHSCOPE_TRANSPORT_MODE: "responses",
        LLM_TIMEOUT: "180",
        LLM_RETRY_ATTEMPTS: "3",
        LLM_RETRY_DELAY: "2.5",
        LLM_STREAM_FIRST_BYTE_TIMEOUT_MS: "45000",
        LLM_STREAM_IDLE_TIMEOUT_MS: "90000",
      },
    }) as ServerConfig;

    expect(config.llm).toEqual({
      acp: {
        proxyUrl: "ws://127.0.0.1:8710/acp",
        tokenFile: undefined,
        command: "grok",
        args: ["--no-auto-update", "--sandbox", "novel-engine", "agent", "--no-leader", "stdio"],
        workspaceRoot: undefined,
        model: undefined,
      },
      defaultProvider: "dashscope",
      genericModel: "env-model",
      dashscopeModel: "env-dashscope-model",
      dashscopeReviewModel: "env-review-model",
      openaiCompatibleModel: "env-openai-model",
      dashscopeApiKey: fixtureApiKey("env", "dashscope-key"),
      dashscopeApiBase: "https://env-dashscope.example/v1",
      openaiCompatibleApiKey: fixtureApiKey("env", "openai-key"),
      openaiCompatibleApiBase: "https://env-openai.example/v1",
      dashscopeTransportMode: "responses",
      timeoutSeconds: 180,
      retryAttempts: 3,
      retryDelayMs: 2_500,
      streamFirstByteTimeoutMs: 45_000,
      streamIdleTimeoutMs: 90_000,
      lorebookBudgetCharacters: 4_000,
    });
  });

  it("retains upper-bound provider validation without exposing credentials", () => {
    const credential = fixtureApiKey("test", "credential", "must-not-leak");
    const cases: readonly [Record<string, string>, string][] = [
      [{ LLM_TIMEOUT: "301", LLM_API_KEY: credential }, "LLM_TIMEOUT"],
      [{ LLM_RETRY_DELAY: "10.1", LLM_API_KEY: credential }, "LLM_RETRY_DELAY"],
      [
        { LLM_STREAM_FIRST_BYTE_TIMEOUT_MS: "300001", LLM_API_KEY: credential },
        "LLM_STREAM_FIRST_BYTE_TIMEOUT_MS",
      ],
      [
        { LLM_STREAM_IDLE_TIMEOUT_MS: "300001", LLM_API_KEY: credential },
        "LLM_STREAM_IDLE_TIMEOUT_MS",
      ],
    ];

    for (const [env, expectedSetting] of cases) {
      const rejected = expectRejected(load({ env }));
      expect(rejected.message).toContain(expectedSetting);
      expect(rejected.message).not.toContain(credential);
    }
  });

  it("reads settings from the .env.local file without shell exports", async () => {
    const workspace = await makeWorkspace();
    const envFile = join(workspace, ".env.local");
    await writeFile(envFile, "APP_ENVIRONMENT=testing\nSECURITY_TRUSTED_PROXIES=10.0.0.7\n");

    const config = load({ envFile, workingDirectory: workspace }) as ServerConfig;

    expect(config.environment).toBe("testing");
    expect(config.trustedProxies).toEqual(["10.0.0.7"]);
  });

  it("refuses trusted proxy network ranges at load time", () => {
    const rejected = expectRejected(
      load({ env: { SECURITY_TRUSTED_PROXIES: "10.0.0.0/8, 127.0.0.1" } }),
    );
    expect(rejected.message).toContain("SECURITY_TRUSTED_PROXIES");
    expect(rejected.message).toContain("10.0.0.0/8");
  });

  it("lets the process environment win over the .env.local file", async () => {
    const workspace = await makeWorkspace();
    const envFile = join(workspace, ".env.local");
    await writeFile(envFile, "APP_ENVIRONMENT=staging\n");

    const config = load({
      env: { APP_ENVIRONMENT: "testing" },
      envFile,
      workingDirectory: workspace,
    }) as ServerConfig;

    expect(config.environment).toBe("testing");
  });

  it("ignores retired CORS alias names", () => {
    const config = load({
      env: {
        CORS_ORIGINS: "https://retired-one.example",
        CORS_ALLOWED_ORIGINS: "https://retired-two.example",
      },
    }) as ServerConfig;

    expect(config.corsOrigins).toEqual([
      "http://localhost:5173",
      "http://localhost:4173",
      "http://localhost:8000",
    ]);
  });

  it("parses SECURITY_CORS_ORIGINS as the single recognized CORS name", () => {
    const config = load({
      env: { SECURITY_CORS_ORIGINS: "https://app.example.com, http://localhost:*" },
    }) as ServerConfig;

    expect(config.corsOrigins).toEqual(["https://app.example.com", "http://localhost:*"]);
  });

  it("parses the authentication rate limit in requests per minute", () => {
    const config = load({ env: { SECURITY_RATE_LIMIT: "30/minute" } }) as ServerConfig;
    expect(config.authRateLimitPerMinute).toBe(30);

    const rejected = expectRejected(load({ env: { SECURITY_RATE_LIMIT: "per second" } }));
    expect(rejected.message).toContain("SECURITY_RATE_LIMIT");
  });

  it("rejects a zero rate limit at load time, before any side effect", () => {
    const rejected = expectRejected(load({ env: { SECURITY_RATE_LIMIT: "0/minute" } }));
    expect(rejected.message).toContain("SECURITY_RATE_LIMIT");
  });

  it("rejects unknown environment names loudly", () => {
    const rejected = expectRejected(load({ env: { APP_ENVIRONMENT: "chaos" } }));
    expect(rejected.message).toContain("APP_ENVIRONMENT");
  });

  it("rejects non-SQLite database URLs", () => {
    const rejected = expectRejected(load({ env: { DB_URL: "postgres://db.example/app" } }));
    expect(rejected.message).toContain("sqlite");
  });

  it("keeps an explicit non-default secret outside production", () => {
    const secret = generatedSecret();
    const config = load({ env: { SECURITY_SECRET_KEY: secret } }) as ServerConfig;
    expect(config.sessionSecret).toBe(secret);
  });

  it("keeps the change-me placeholder usable outside production", () => {
    const placeholder = "change-me-to-a-long-random-local-secret";
    const config = load({ env: { SECURITY_SECRET_KEY: placeholder } }) as ServerConfig;
    expect(config.sessionSecret).toBe(placeholder);
  });

  it("refuses production startup when the secret is empty or whitespace", () => {
    for (const empty of ["", "   "]) {
      const rejected = expectRejected(
        load({ env: { APP_ENVIRONMENT: "production", SECURITY_SECRET_KEY: empty } }),
      );
      expect(rejected.message).toContain("SECURITY_SECRET_KEY");
    }
  });

  it("refuses an explicitly short secret in every environment", () => {
    const tooShort = randomBytes(6).toString("hex").slice(0, 12);
    const rejected = expectRejected(load({ env: { SECURITY_SECRET_KEY: tooShort } }));
    expect(rejected.message).toContain("SECURITY_SECRET_KEY");
  });
});
