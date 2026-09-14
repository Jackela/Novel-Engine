import type { Principal } from "../../../shared/application/ports/auth.js";
import type { DiagnosticsHealthProbe } from "./ports/diagnostics_health.js";
import type { StudioJobLedgerStore } from "./ports/job_ledger_store.js";
import { jobPageLimit } from "./ports/job_records.js";
import { scopeForPrincipal } from "./ports/studio_store.js";

/** How many persisted failure messages the export carries. */
const RECENT_ERROR_LIMIT = jobPageLimit(5);

/**
 * The composition-root-supplied facts of the diagnostics export (#654):
 * identity, runtime, and configuration state as plain values, so the service
 * never reads the filesystem or the process itself — and holds no second
 * copy of the provider-configuration rule (the composition root computes
 * the resolved provider's `configured` boolean).
 */
export interface DiagnosticsFacts {
  readonly product: { readonly name: string; readonly version: string };
  readonly runtime: {
    readonly platform: string;
    readonly architecture: string;
    readonly nodeVersion: string;
  };
  /** The resolved provider selection; its label is a display concern (#654). */
  readonly provider: { readonly id: string; readonly configured: boolean };
  /**
   * Set/unset booleans only — the structural redaction rule: the summary has
   * no field capable of carrying a secret value, so the session secret and
   * provider API keys are reported as configured state, never as values.
   */
  readonly keys: {
    readonly sessionSecret: boolean;
    readonly dashscopeApiKey: boolean;
    readonly openaiCompatibleApiKey: boolean;
  };
}

/** One persisted failure message of the project's most recent failed Jobs. */
export interface DiagnosticsRecentError {
  readonly message: string;
  readonly occurredAt: string;
}

/** The complete diagnostics summary the export endpoint serializes. */
export interface DiagnosticsSummary {
  readonly generatedAt: string;
  readonly product: DiagnosticsFacts["product"];
  readonly runtime: DiagnosticsFacts["runtime"];
  readonly configuration: {
    readonly provider: { readonly id: string; readonly configured: boolean };
    readonly keys: {
      readonly sessionSecret: boolean;
      readonly dashscopeApiKey: boolean;
      readonly openaiCompatibleApiKey: boolean;
    };
  };
  readonly database: {
    readonly quickCheck: string;
    readonly journalMode: string;
    readonly foreignKeys: boolean;
    readonly ownerConfigured: boolean;
  };
  /**
   * The current project's most recent failed Jobs' persisted error messages,
   * newest first; empty is an explicit healthy state, not a missing field.
   */
  readonly recentErrors: readonly DiagnosticsRecentError[];
}

interface DiagnosticsServiceOptions {
  readonly now?: (() => Date) | undefined;
}

/**
 * Assembles the opt-in diagnostics export (#654). Everything secret-capable
 * arrives as a boolean and everything book-like is out of scope by
 * construction: the service reads only the facts above, the health probe, and
 * the persisted failure messages of the requesting project's own jobs.
 */
export class DiagnosticsService {
  private readonly jobs: StudioJobLedgerStore;
  private readonly health: DiagnosticsHealthProbe;
  private readonly facts: DiagnosticsFacts;
  private readonly now: () => Date;

  constructor(
    jobs: StudioJobLedgerStore,
    health: DiagnosticsHealthProbe,
    facts: DiagnosticsFacts,
    options: DiagnosticsServiceOptions = {},
  ) {
    this.jobs = jobs;
    this.health = health;
    this.facts = facts;
    this.now = options.now ?? (() => new Date());
  }

  /**
   * Collect the summary for one project. An unknown project identifier fails
   * with the store's NotFoundError (the 404 envelope at the route); failed
   * jobs of other projects are structurally absent because the store query is
   * owner- and project-scoped.
   */
  collectDiagnostics(principal: Principal, projectId: string): DiagnosticsSummary {
    const scope = scopeForPrincipal(principal);
    const recentErrors = this.jobs
      .collectRecentFailedJobErrors(scope, projectId, RECENT_ERROR_LIMIT)
      .map((job) => ({ message: job.error, occurredAt: job.updatedAt.toISOString() }));
    return {
      generatedAt: this.now().toISOString(),
      product: this.facts.product,
      runtime: this.facts.runtime,
      configuration: {
        provider: this.facts.provider,
        keys: this.facts.keys,
      },
      database: this.health(),
      recentErrors,
    };
  }
}
