import { spawnSync } from "node:child_process";
import { copyFile, mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const QA_SOURCE_DIRECTORY = resolve(dirname(fileURLToPath(import.meta.url)), "../../scripts/qa");

async function createQaRepository(): Promise<string> {
  const root = await mkdtemp(join(tmpdir(), "novel-engine-compose-passthrough-gate-"));
  const destination = join(root, "server/scripts/qa");
  await mkdir(destination, { recursive: true });
  await copyFile(join(QA_SOURCE_DIRECTORY, "common.mjs"), join(destination, "common.mjs"));
  await copyFile(
    join(QA_SOURCE_DIRECTORY, "check_compose_passthrough.mjs"),
    join(destination, "check_compose_passthrough.mjs"),
  );
  return root;
}

function initializeGitRepository(root: string): void {
  const result = spawnSync("git", ["init", "--quiet"], { cwd: root, encoding: "utf8" });
  if (result.status !== 0) {
    throw new Error(`git init failed: ${result.stderr}`);
  }
}

async function writeCandidate(root: string, relativePath: string, contents: string): Promise<void> {
  const absolutePath = join(root, relativePath);
  await mkdir(dirname(absolutePath), { recursive: true });
  await writeFile(absolutePath, contents, "utf8");
}

function runGate(root: string) {
  return spawnSync(
    process.execPath,
    [join(root, "server/scripts/qa/check_compose_passthrough.mjs")],
    {
      cwd: root,
      encoding: "utf8",
    },
  );
}

// Fixture loaders keep the real call shapes (single key, alias array,
// multiline enum/integer calls, reads nested in helpers) so the extraction
// regex is exercised against the shapes it must keep understanding.
const PROVIDER_LOADER_FIXTURE = `const LLM_PROVIDERS = ["mock", "dashscope", "openai_compatible"] as const;

export interface LlmServerConfig {
  readonly defaultProvider: (typeof LLM_PROVIDERS)[number];
}

export function loadLlmServerConfig(env: ReadonlyMap<string, string>): LlmServerConfig {
  return {
    defaultProvider: enumFrom(env, "LLM_PROVIDER", LLM_PROVIDERS, "mock"),
    genericModel: nonBlankStringFrom(env, "LLM_MODEL"),
    dashscopeModel: nonBlankStringFrom(env, "DASHSCOPE_MODEL"),
    dashscopeReviewModel: nonBlankStringFrom(env, "DASHSCOPE_REVIEW_MODEL"),
    openaiCompatibleModel: nonBlankStringFrom(env, "OPENAI_COMPATIBLE_MODEL"),
    dashscopeApiKey: nonBlankStringFrom(env, "DASHSCOPE_API_KEY"),
    dashscopeApiBase: nonBlankStringFrom(env, "DASHSCOPE_API_BASE"),
    openaiCompatibleApiKey: firstNonBlankStringFrom(env, ["LLM_API_KEY", "OPENAI_API_KEY"]),
    openaiCompatibleApiBase: firstNonBlankStringFrom(env, ["LLM_API_BASE", "OPENAI_API_BASE"]),
    dashscopeTransportMode: enumFrom(
      env,
      "DASHSCOPE_TRANSPORT_MODE",
      TRANSPORT_MODES,
      "multimodal_generation",
    ),
    timeoutSeconds: integerFrom(
      env,
      "LLM_TIMEOUT",
      30,
      5,
      300,
    ),
    retryAttempts: integerFrom(env, "LLM_RETRY_ATTEMPTS", 3, 1, 3),
    retryDelayMs: numberFrom(env, "LLM_RETRY_DELAY", 1) * 1_000,
    streamFirstByteTimeoutMs: integerFrom(env, "LLM_STREAM_FIRST_BYTE_TIMEOUT_MS", 30_000, 1, 300_000),
    streamIdleTimeoutMs: integerFrom(env, "LLM_STREAM_IDLE_TIMEOUT_MS", 60_000, 1, 300_000),
    lorebookBudgetCharacters: integerFrom(env, "LLM_LOREBOOK_BUDGET_CHARACTERS", 4_000, 1, 1_000_000),
  };
}

function stringFrom(env: ReadonlyMap<string, string>, key: string): string | undefined {
  return env.get(key.toLowerCase());
}
`;

const SERVER_LOADER_FIXTURE = `export interface ServerConfig {
  readonly environment: string;
  readonly sessionSecret: string | undefined;
  readonly databaseUrl: string;
}

export function loadServerConfig(input: LoadServerConfigInput = {}): ServerConfig {
  const env = mergedEnvironment(input);
  const databaseUrl = stringFrom(env, "DB_URL") ?? "sqlite:///./data/novel-engine.sqlite3";
  const sessionSecret = secretFrom(stringFrom(env, "SECURITY_SECRET_KEY"));
  const maxActiveWorkflows = boundedIntegerFrom(env, "API_MAX_ACTIVE_WORKFLOWS", 4);
  const maxActiveWorkflowsPerProject = boundedIntegerFrom(
    env,
    "API_MAX_ACTIVE_WORKFLOWS_PER_PROJECT",
    2,
  );
  return {
    environment: environmentFrom(env),
    sessionSecret,
    databaseUrl,
    host: stringFrom(env, "API_HOST") ?? "0.0.0.0",
    port: portFrom(env),
    corsOrigins: listFrom(env, "SECURITY_CORS_ORIGINS") ?? [],
    trustedProxies: listFrom(env, "SECURITY_TRUSTED_PROXIES") ?? [],
    authRateLimitPerMinute: rateLimitFrom(env),
    maxActiveWorkflows,
    maxActiveWorkflowsPerProject,
  };
}

function environmentFrom(env: Map<string, string>): string {
  const raw = stringFrom(env, "APP_ENVIRONMENT") ?? "development";
  return raw.trim().toLowerCase();
}

function portFrom(env: Map<string, string>): number {
  const raw = stringFrom(env, "API_PORT");
  return raw === undefined ? 8000 : Number(raw);
}

function rateLimitFrom(env: Map<string, string>): number {
  const raw = stringFrom(env, "SECURITY_RATE_LIMIT") ?? "5/minute";
  return Number(raw.split("/")[0]);
}
`;

const COMPOSE_FIXTURE = `services:
  novel-engine:
    build: .
    environment:
      APP_ENVIRONMENT: production
      # Provider settings pass through from the project .env file.
      DB_URL: sqlite:///./data/novel-engine.sqlite3
      SECURITY_SECRET_KEY: \${SECURITY_SECRET_KEY:-}
      LLM_PROVIDER: \${LLM_PROVIDER:-mock}
      LLM_MODEL: \${LLM_MODEL:-}
      DASHSCOPE_MODEL: \${DASHSCOPE_MODEL:-}
      DASHSCOPE_REVIEW_MODEL: \${DASHSCOPE_REVIEW_MODEL:-}
      OPENAI_COMPATIBLE_MODEL: \${OPENAI_COMPATIBLE_MODEL:-}
      DASHSCOPE_API_KEY: \${DASHSCOPE_API_KEY:-}
      DASHSCOPE_API_BASE: \${DASHSCOPE_API_BASE:-}
      DASHSCOPE_TRANSPORT_MODE: \${DASHSCOPE_TRANSPORT_MODE:-}
      LLM_API_KEY: \${LLM_API_KEY:-}
      OPENAI_API_KEY: \${OPENAI_API_KEY:-}
      LLM_API_BASE: \${LLM_API_BASE:-}
      OPENAI_API_BASE: \${OPENAI_API_BASE:-}
      LLM_TIMEOUT: \${LLM_TIMEOUT:-}
      LLM_RETRY_ATTEMPTS: \${LLM_RETRY_ATTEMPTS:-}
      LLM_RETRY_DELAY: \${LLM_RETRY_DELAY:-}
      LLM_STREAM_FIRST_BYTE_TIMEOUT_MS: \${LLM_STREAM_FIRST_BYTE_TIMEOUT_MS:-}
      LLM_STREAM_IDLE_TIMEOUT_MS: \${LLM_STREAM_IDLE_TIMEOUT_MS:-}
      LLM_LOREBOOK_BUDGET_CHARACTERS: \${LLM_LOREBOOK_BUDGET_CHARACTERS:-}
    volumes:
      - novel-engine-data:/app/data
`;

async function writeLoaderFixtures(root: string): Promise<void> {
  await writeCandidate(
    root,
    "server/src/shared/infrastructure/config/provider_config.ts",
    PROVIDER_LOADER_FIXTURE,
  );
  await writeCandidate(
    root,
    "server/src/shared/infrastructure/config/server_config.ts",
    SERVER_LOADER_FIXTURE,
  );
}

describe("compose passthrough gate", () => {
  it("accepts both compose files whose environment covers the provider read set", async () => {
    const root = await createQaRepository();

    try {
      initializeGitRepository(root);
      await writeLoaderFixtures(root);
      await writeCandidate(root, "compose.yaml", COMPOSE_FIXTURE);
      await writeCandidate(root, "deploy/compose.yaml", COMPOSE_FIXTURE);

      const result = runGate(root);

      expect(result.status).toBe(0);
      expect(result.stdout).toContain("[compose-passthrough] clean");
      expect(result.stdout).toContain("compose.yaml and deploy/compose.yaml");
      expect(result.stdout).toContain("all 18 provider variables");
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it("rejects a compose file that drops a provider passthrough variable", async () => {
    const root = await createQaRepository();

    try {
      initializeGitRepository(root);
      await writeLoaderFixtures(root);
      await writeCandidate(root, "compose.yaml", COMPOSE_FIXTURE);
      await writeCandidate(
        root,
        "deploy/compose.yaml",
        COMPOSE_FIXTURE.replace(/^ {6}DASHSCOPE_REVIEW_MODEL:.*\n/m, ""),
      );

      const result = runGate(root);

      expect(result.status).toBe(1);
      expect(result.stderr).toContain(
        "deploy/compose.yaml environment is missing provider variable DASHSCOPE_REVIEW_MODEL",
      );
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it("fails loudly when an extraction shape change hides a loader variable", async () => {
    const root = await createQaRepository();

    try {
      initializeGitRepository(root);
      // The review finding (#626): refactoring a loader call into an options
      // shape must not silently shrink the extracted set.
      await writeCandidate(
        root,
        "server/src/shared/infrastructure/config/provider_config.ts",
        PROVIDER_LOADER_FIXTURE.replace(
          'nonBlankStringFrom(env, "LLM_MODEL")',
          'nonBlankStringFrom(env, { key: "LLM_MODEL" })',
        ),
      );
      await writeCandidate(
        root,
        "server/src/shared/infrastructure/config/server_config.ts",
        SERVER_LOADER_FIXTURE,
      );
      await writeCandidate(root, "compose.yaml", COMPOSE_FIXTURE);
      await writeCandidate(root, "deploy/compose.yaml", COMPOSE_FIXTURE);

      const result = runGate(root);

      expect(result.status).toBe(1);
      expect(result.stderr).toContain("missed anchor LLM_MODEL");
      expect(result.stderr).toContain("the extraction rotted");
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it("fails closed when a required compose file is missing", async () => {
    const root = await createQaRepository();

    try {
      initializeGitRepository(root);
      await writeLoaderFixtures(root);
      await writeCandidate(root, "compose.yaml", COMPOSE_FIXTURE);

      const result = runGate(root);

      expect(result.status).toBe(1);
      expect(result.stderr).toContain("required compose file is missing: deploy/compose.yaml");
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });
});
