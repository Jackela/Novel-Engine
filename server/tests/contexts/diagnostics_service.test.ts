/**
 * Direct contract tests for DiagnosticsService (#654): the export assembles
 * composition-root facts, the database health probe, and the requesting
 * project's own persisted failure messages. Fakes carry typed method objects
 * captured through the ports, so these tests pin the service's field mapping,
 * its bounded owner/project-scoped failure scan, and its structural
 * secret-capability rule — never store or filesystem behavior.
 */
import { describe, expect, it } from "vitest";

import {
  type DiagnosticsFacts,
  DiagnosticsService,
} from "../../src/contexts/studio/application/diagnostics_service.js";
import type { DiagnosticsHealthReport } from "../../src/contexts/studio/application/ports/diagnostics_health.js";
import type { StudioJobLedgerStore } from "../../src/contexts/studio/application/ports/job_ledger_store.js";
import type {
  FailedJobErrorRecord,
  JobPageLimit,
} from "../../src/contexts/studio/application/ports/job_records.js";
import type { ProjectScope } from "../../src/contexts/studio/application/ports/studio_store.js";
import { NotFoundError } from "../../src/contexts/studio/domain/exceptions.js";
import type { Principal } from "../../src/shared/application/ports/auth.js";

const PRINCIPAL: Principal = {
  sessionId: "session-1",
  kind: "owner",
  ownerId: "owner-1",
  expiresAt: null,
};
const NOW = new Date("2026-09-03T10:30:00.000Z");

const FACTS: DiagnosticsFacts = {
  product: { name: "Novel Engine", version: "0.8.0" },
  runtime: { platform: "darwin", architecture: "arm64", nodeVersion: "v24.0.0" },
  provider: { id: "mock", configured: true },
  keys: { sessionSecret: true, dashscopeApiKey: false, openaiCompatibleApiKey: false },
};

const HEALTH: DiagnosticsHealthReport = {
  quickCheck: "ok",
  journalMode: "wal",
  foreignKeys: true,
  ownerConfigured: true,
};

function failedJob(error: string, updatedAt: string): FailedJobErrorRecord {
  return { error, updatedAt: new Date(updatedAt) };
}

interface FailedScan {
  scope: ProjectScope;
  projectId: string;
  limit: JobPageLimit;
}

interface FakeJobs {
  collectRecentFailedJobErrors(
    scope: ProjectScope,
    projectId: string,
    limit: JobPageLimit,
  ): FailedJobErrorRecord[];
}

function harness(
  config: {
    failures?: FailedJobErrorRecord[];
    failure?: Error;
    reports?: DiagnosticsHealthReport[];
    clock?: () => Date;
  } = {},
) {
  const scans: FailedScan[] = [];
  let healthCalls = 0;
  const jobs: FakeJobs = {
    collectRecentFailedJobErrors: (scope, projectId, limit) => {
      scans.push({ scope, projectId, limit });
      if (config.failure !== undefined) throw config.failure;
      // The port owns the bound; the fake honors it so the service's mapping
      // is asserted one-to-one over the scan's own result.
      return (config.failures ?? []).slice(0, limit);
    },
  };
  const health = () => {
    const report = config.reports?.[healthCalls] ?? HEALTH;
    healthCalls += 1;
    return report;
  };
  const service = new DiagnosticsService(jobs as unknown as StudioJobLedgerStore, health, FACTS, {
    now: config.clock ?? (() => NOW),
  });
  return { service, scans, healthCalls: () => healthCalls };
}

describe("DiagnosticsService export assembly", () => {
  it("assembles the field families of one collection into the summary", () => {
    const { service } = harness({
      failures: [
        failedJob("provider returned HTTP 401.", "2026-09-03T10:00:01.000Z"),
        failedJob("provider returned HTTP 403.", "2026-09-03T10:00:00.000Z"),
      ],
    });

    const summary = service.collectDiagnostics(PRINCIPAL, "project-1");

    expect(summary).toEqual({
      generatedAt: NOW.toISOString(),
      product: FACTS.product,
      runtime: FACTS.runtime,
      configuration: {
        provider: { id: "mock", configured: true },
        keys: { sessionSecret: true, dashscopeApiKey: false, openaiCompatibleApiKey: false },
      },
      database: HEALTH,
      recentErrors: [
        { message: "provider returned HTTP 401.", occurredAt: "2026-09-03T10:00:01.000Z" },
        { message: "provider returned HTTP 403.", occurredAt: "2026-09-03T10:00:00.000Z" },
      ],
    });
  });

  it("keeps an explicit empty error state instead of an absent field", () => {
    const { service } = harness();
    const summary = service.collectDiagnostics(PRINCIPAL, "project-1");
    expect(Object.hasOwn(summary, "recentErrors")).toBe(true);
    expect(summary.recentErrors).toEqual([]);
  });

  it("asks for the five most recent failures, owner- and project-scoped", () => {
    const failures = Array.from({ length: 7 }, (_, index) =>
      failedJob(`failure ${index}`, `2026-09-03T10:00:0${index}.000Z`),
    );
    const { service, scans } = harness({ failures });

    const summary = service.collectDiagnostics(PRINCIPAL, "project-1");

    expect(scans).toEqual([{ scope: { ownerId: "owner-1" }, projectId: "project-1", limit: 5 }]);
    // The scan's bounded newest-first page is carried one-to-one, never re-sorted.
    expect(summary.recentErrors).toEqual(
      failures.slice(0, 5).map((job) => ({
        message: job.error,
        occurredAt: job.updatedAt.toISOString(),
      })),
    );
  });

  it("reads the health probe once per collection instead of caching a report", () => {
    const failing = { ...HEALTH, quickCheck: "database disk image is malformed" };
    const { service, healthCalls } = harness({ reports: [HEALTH, failing] });

    const first = service.collectDiagnostics(PRINCIPAL, "project-1");
    const second = service.collectDiagnostics(PRINCIPAL, "project-2");

    expect(healthCalls()).toBe(2);
    expect(first.database).toEqual(HEALTH);
    expect(second.database).toEqual(failing);
  });

  it("stamps every collection with its own clock reading", () => {
    let calls = 0;
    const { service } = harness({
      clock: () => new Date(NOW.getTime() + calls++ * 60_000),
    });

    expect(service.collectDiagnostics(PRINCIPAL, "project-1").generatedAt).toBe(NOW.toISOString());
    expect(service.collectDiagnostics(PRINCIPAL, "project-1").generatedAt).toBe(
      new Date(NOW.getTime() + 60_000).toISOString(),
    );
    expect(calls).toBe(2);
  });

  it("exposes no field capable of carrying a secret value", () => {
    const { service } = harness();
    const configuration = service.collectDiagnostics(PRINCIPAL, "project-1").configuration;

    expect(Object.keys(configuration).sort()).toEqual(["keys", "provider"]);
    expect(Object.keys(configuration.provider).sort()).toEqual(["configured", "id"]);
    expect(Object.keys(configuration.keys).sort()).toEqual([
      "dashscopeApiKey",
      "openaiCompatibleApiKey",
      "sessionSecret",
    ]);
    for (const value of Object.values(configuration.keys)) {
      expect(typeof value).toBe("boolean");
    }
    expect(typeof configuration.provider.configured).toBe("boolean");
  });

  it("propagates an unknown project as not-found before touching the health probe", () => {
    const failure = new NotFoundError("Project not found: ghost.");
    const { service, healthCalls } = harness({ failure });
    let caught: unknown;
    try {
      service.collectDiagnostics(PRINCIPAL, "ghost");
    } catch (error) {
      caught = error;
    }
    expect(caught).toBe(failure);
    expect(healthCalls()).toBe(0);
  });

  it("refuses a principal without an owner before consulting any dependency", () => {
    const anonymous: Principal = {
      sessionId: "session-2",
      kind: "owner",
      ownerId: null,
      expiresAt: null,
    };
    const { service, scans, healthCalls } = harness();
    expect(() => service.collectDiagnostics(anonymous, "project-1")).toThrow(
      "A principal without an owner cannot scope studio data.",
    );
    expect(scans).toEqual([]);
    expect(healthCalls()).toBe(0);
  });
});
