import { randomBytes } from "node:crypto";
import { mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import {
  DEFAULT_SECRET_KEY,
  loadServerConfig,
  type ServerConfig,
} from "../../src/shared/infrastructure/config/server_config.js";

/** A usable secret generated per run — never a credential literal in source. */
function generatedSecret(): string {
  return randomBytes(32).toString("base64url");
}

async function makeWorkspace(): Promise<string> {
  return mkdtemp(join(tmpdir(), "novel-engine-config-"));
}

interface LoadOptions {
  env?: Record<string, string>;
  envFile?: string | null;
  workingDirectory?: string;
}

function load(options: LoadOptions = {}): ServerConfig | ConfigurationErrorLike {
  const input: {
    env: Record<string, string>;
    envFile: string | null;
    workingDirectory?: string;
  } = {
    env: options.env ?? {},
    envFile: options.envFile ?? null,
  };
  if (options.workingDirectory !== undefined) {
    input.workingDirectory = options.workingDirectory;
  }
  try {
    return loadServerConfig(input);
  } catch (error) {
    return error as ConfigurationErrorLike;
  }
}

interface ConfigurationErrorLike {
  readonly message: string;
  readonly name: string;
}

function expectRejected(config: ServerConfig | ConfigurationErrorLike): ConfigurationErrorLike {
  expect(config).toBeInstanceOf(Error);
  return config as ConfigurationErrorLike;
}

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

  it("keeps provider configuration server-owned with safe hard-default fallthrough", () => {
    const config = load() as ServerConfig;

    expect(config.llm.defaultProvider).toBe("mock");
    expect(config.llm.genericModel).toBeUndefined();
    expect(config.llm.dashscopeModel).toBeUndefined();
    expect(config.llm.dashscopeReviewModel).toBeUndefined();
    expect(config.llm.openaiCompatibleModel).toBeUndefined();
    expect(config.llm.dashscopeApiKey).toBeUndefined();
    expect(config.llm.openaiCompatibleApiKey).toBeUndefined();
    expect(config.llm.dashscopeApiBase).toBeUndefined();
    expect(config.llm.openaiCompatibleApiBase).toBeUndefined();
    expect(config.llm.dashscopeTransportMode).toBe("multimodal_generation");
    expect(config.llm.timeoutSeconds).toBe(30);
    expect(config.llm.retryAttempts).toBe(3);
    expect(config.llm.retryDelayMs).toBe(1_000);
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
        DASHSCOPE_API_KEY: "env-dashscope-key",
        DASHSCOPE_API_BASE: "https://env-dashscope.example/v1",
        DASHSCOPE_MODEL: "env-dashscope-model",
        DASHSCOPE_REVIEW_MODEL: "env-review-model",
        LLM_API_KEY: "env-openai-key",
        LLM_API_BASE: "https://env-openai.example/v1",
        OPENAI_COMPATIBLE_MODEL: "env-openai-model",
        DASHSCOPE_TRANSPORT_MODE: "responses",
        LLM_TIMEOUT: "180",
        LLM_RETRY_ATTEMPTS: "3",
        LLM_RETRY_DELAY: "2.5",
      },
    }) as ServerConfig;

    expect(config.llm).toEqual({
      defaultProvider: "dashscope",
      genericModel: "env-model",
      dashscopeModel: "env-dashscope-model",
      dashscopeReviewModel: "env-review-model",
      openaiCompatibleModel: "env-openai-model",
      dashscopeApiKey: "env-dashscope-key",
      dashscopeApiBase: "https://env-dashscope.example/v1",
      openaiCompatibleApiKey: "env-openai-key",
      openaiCompatibleApiBase: "https://env-openai.example/v1",
      dashscopeTransportMode: "responses",
      timeoutSeconds: 180,
      retryAttempts: 3,
      retryDelayMs: 2_500,
    });
  });

  it("treats blank provider overrides and credentials as unset", () => {
    const config = load({
      env: {
        LLM_PROVIDER: "  ",
        LLM_MODEL: "  ",
        DASHSCOPE_MODEL: "",
        DASHSCOPE_REVIEW_MODEL: "  ",
        OPENAI_COMPATIBLE_MODEL: "  ",
        DASHSCOPE_API_KEY: "  ",
        DASHSCOPE_API_BASE: " ",
        LLM_API_KEY: "  ",
        OPENAI_API_KEY: " ",
        LLM_API_BASE: "  ",
        OPENAI_API_BASE: " ",
        DASHSCOPE_TRANSPORT_MODE: "  ",
        LLM_TIMEOUT: " ",
        LLM_RETRY_ATTEMPTS: " ",
        LLM_RETRY_DELAY: " ",
      },
    }) as ServerConfig;

    expect(config.llm).toEqual({
      defaultProvider: "mock",
      genericModel: undefined,
      dashscopeModel: undefined,
      dashscopeReviewModel: undefined,
      openaiCompatibleModel: undefined,
      dashscopeApiKey: undefined,
      dashscopeApiBase: undefined,
      openaiCompatibleApiKey: undefined,
      openaiCompatibleApiBase: undefined,
      dashscopeTransportMode: "multimodal_generation",
      timeoutSeconds: 30,
      retryAttempts: 3,
      retryDelayMs: 1_000,
    });
  });

  it("rejects invalid provider controls and numeric bounds without exposing credentials", () => {
    const credential = "test-credential-must-not-leak";
    const cases: readonly [Record<string, string>, string][] = [
      [{ LLM_PROVIDER: "remote", LLM_API_KEY: credential }, "LLM_PROVIDER"],
      [{ DASHSCOPE_TRANSPORT_MODE: "legacy", LLM_API_KEY: credential }, "DASHSCOPE_TRANSPORT_MODE"],
      [{ LLM_TIMEOUT: "slow", LLM_API_KEY: credential }, "LLM_TIMEOUT"],
      [{ LLM_TIMEOUT: "4", LLM_API_KEY: credential }, "LLM_TIMEOUT"],
      [{ LLM_TIMEOUT: "301", LLM_API_KEY: credential }, "LLM_TIMEOUT"],
      [{ LLM_RETRY_ATTEMPTS: "many", LLM_API_KEY: credential }, "LLM_RETRY_ATTEMPTS"],
      [{ LLM_RETRY_ATTEMPTS: "0", LLM_API_KEY: credential }, "LLM_RETRY_ATTEMPTS"],
      [{ LLM_RETRY_ATTEMPTS: "4", LLM_API_KEY: credential }, "LLM_RETRY_ATTEMPTS"],
      [{ LLM_RETRY_DELAY: "later", LLM_API_KEY: credential }, "LLM_RETRY_DELAY"],
      [{ LLM_RETRY_DELAY: "0.09", LLM_API_KEY: credential }, "LLM_RETRY_DELAY"],
      [{ LLM_RETRY_DELAY: "10.1", LLM_API_KEY: credential }, "LLM_RETRY_DELAY"],
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
    await writeFile(envFile, "APP_ENVIRONMENT=testing\nSECURITY_TRUSTED_PROXIES=10.0.0.0/8\n");

    const config = load({ envFile, workingDirectory: workspace }) as ServerConfig;

    expect(config.environment).toBe("testing");
    expect(config.trustedProxies).toEqual(["10.0.0.0/8"]);
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

describe("production configuration guards", () => {
  it("refuses production startup when the secret is missing", () => {
    const rejected = expectRejected(load({ env: { APP_ENVIRONMENT: "production" } }));
    expect(rejected.message).toContain("SECURITY_SECRET_KEY");
  });

  it("refuses production startup when the secret is the default value", () => {
    const rejected = expectRejected(
      load({ env: { APP_ENVIRONMENT: "production", SECURITY_SECRET_KEY: DEFAULT_SECRET_KEY } }),
    );
    expect(rejected.message).toContain("SECURITY_SECRET_KEY");
  });

  it("refuses staging startup when the secret is the default value", () => {
    const rejected = expectRejected(
      load({ env: { APP_ENVIRONMENT: "staging", SECURITY_SECRET_KEY: DEFAULT_SECRET_KEY } }),
    );
    expect(rejected.message).toContain("SECURITY_SECRET_KEY");
  });

  it("accepts production with an explicit secret, SQLite, and public origins", () => {
    const config = load({
      env: {
        APP_ENVIRONMENT: "production",
        SECURITY_SECRET_KEY: generatedSecret(),
        SECURITY_CORS_ORIGINS: "https://app.example.com",
      },
    }) as ServerConfig;

    expect(config.environment).toBe("production");
  });

  it("refuses production CORS containing a wildcard", () => {
    const rejected = expectRejected(
      load({
        env: {
          APP_ENVIRONMENT: "production",
          SECURITY_SECRET_KEY: generatedSecret(),
          SECURITY_CORS_ORIGINS: "https://*.example.com",
        },
      }),
    );
    expect(rejected.message).toContain("wildcard");
  });

  it("refuses production CORS containing localhost", () => {
    const rejected = expectRejected(
      load({
        env: {
          APP_ENVIRONMENT: "production",
          SECURITY_SECRET_KEY: generatedSecret(),
          SECURITY_CORS_ORIGINS: "https://app.example.com, http://localhost:5173",
        },
      }),
    );
    expect(rejected.message).toContain("localhost");
  });

  it("refuses staging default secrets but keeps the store and CORS unconstrained", () => {
    const config = load({
      env: {
        APP_ENVIRONMENT: "staging",
        SECURITY_SECRET_KEY: generatedSecret(),
      },
    }) as ServerConfig;

    expect(config.corsOrigins).toContain("http://localhost:5173");
  });
});
