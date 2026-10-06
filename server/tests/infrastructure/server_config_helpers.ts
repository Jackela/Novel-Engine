import { randomBytes } from "node:crypto";
import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { expect } from "vitest";

import {
  loadServerConfig,
  type ServerConfig,
} from "../../src/shared/infrastructure/config/server_config.js";

/** A usable secret generated per run — never a credential literal in source. */
export function generatedSecret(): string {
  return randomBytes(32).toString("base64url");
}

export async function makeWorkspace(): Promise<string> {
  return mkdtemp(join(tmpdir(), "novel-engine-config-"));
}

export interface LoadOptions {
  env?: Record<string, string>;
  envFile?: string | null;
  workingDirectory?: string;
}

export function load(options: LoadOptions = {}): ServerConfig | ConfigurationErrorLike {
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

export interface ConfigurationErrorLike {
  readonly message: string;
  readonly name: string;
}

export function expectRejected(
  config: ServerConfig | ConfigurationErrorLike,
): ConfigurationErrorLike {
  expect(config).toBeInstanceOf(Error);
  return config as ConfigurationErrorLike;
}
