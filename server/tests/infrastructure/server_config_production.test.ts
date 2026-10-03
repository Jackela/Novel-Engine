import { describe, expect, it } from "vitest";

import {
  DEFAULT_SECRET_KEY,
  type ServerConfig,
} from "../../src/shared/infrastructure/config/server_config.js";
import { expectRejected, generatedSecret, load } from "./server_config_helpers.js";

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

  it("refuses production startup when the secret keeps the change-me placeholder prefix", () => {
    for (const placeholder of [
      "change-me-to-a-long-random-local-secret",
      "change-me-installation-specific-value",
    ]) {
      const rejected = expectRejected(
        load({
          env: {
            APP_ENVIRONMENT: "production",
            SECURITY_SECRET_KEY: placeholder,
            // Valid public CORS so only the secret guard can reject this.
            SECURITY_CORS_ORIGINS: "https://app.example.com",
          },
        }),
      );
      expect(rejected.message).toContain("SECURITY_SECRET_KEY");
    }
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

  it("refuses production startup when SECURITY_CORS_ORIGINS is empty (the Compose passthrough default)", () => {
    const rejected = expectRejected(
      load({
        env: {
          APP_ENVIRONMENT: "production",
          SECURITY_SECRET_KEY: generatedSecret(),
          SECURITY_CORS_ORIGINS: "",
        },
      }),
    );
    // Empty means unset for the loader, so the localhost defaults apply and
    // the production guard refuses them: a missing Compose configuration
    // fails fast instead of silently allowing a placeholder origin.
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
