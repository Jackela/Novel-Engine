import type {
  FastifyPluginAsync,
  FastifyReply,
  FastifyRequest,
  HookHandlerDoneFunction,
} from "fastify";

import type { AuthService } from "../../application/auth_service.js";
import type { MetricsProbe, MetricsSnapshot } from "../../application/ports/metrics.js";
import { principalGuard } from "./auth_guard.js";
import { isLoopbackPeerAddress } from "./peer_address.js";

interface MetricsRoutesOptions {
  probe: MetricsProbe;
  authService: AuthService | undefined;
  productIdentity: { name: string; version: string };
}

/**
 * The internal-only metrics surface (DR-041). Access is either the loopback
 * peer (a Prometheus sidecar sharing the network namespace, or `docker exec`
 * on the host) or an authenticated owner session — the two shapes that do not
 * widen the unauthenticated surface DR-035 closed. A non-loopback anonymous
 * scrape answers the unified 401 envelope, so an exposed port yields no
 * figures instead of a fingerprint.
 *
 * The rendered text carries process and job/usage gauges only: counts, sums,
 * uptime, and memory. No configuration value, credential, path, or manuscript
 * content enters the snapshot, so the body cannot leak one.
 */
export const metricsRoutes: FastifyPluginAsync<MetricsRoutesOptions> = async (app, options) => {
  const ownerGuard = principalGuard(options.authService);
  const internalOrOwner = (
    request: FastifyRequest,
    reply: FastifyReply,
    done: HookHandlerDoneFunction,
  ): void => {
    if (isLoopbackPeerAddress(request.socket?.remoteAddress)) {
      done();
      return;
    }
    ownerGuard(request, reply, done);
  };

  app.get(
    "/metrics",
    // Hidden from the OpenAPI document: an internal scrape surface is not part
    // of the public contract, so adding it must not move the snapshot.
    { schema: { hide: true }, preHandler: [internalOrOwner] },
    async (_request, reply) => {
      reply.type("text/plain; version=0.0.4; charset=utf-8");
      return renderPrometheusText(options.probe(), options.productIdentity);
    },
  );
};

/** A finite number, or a programming error surfaced as a 500 instead of `NaN`. */
function numeric(value: number): string {
  if (!Number.isFinite(value)) {
    throw new Error(`Metrics value is not a finite number: ${value}`);
  }
  return String(value);
}

/** Escape a Prometheus label value (backslash, quote, newline). */
function labelValue(value: string): string {
  return value.replace(/\\/g, "\\\\").replace(/"/g, '\\"').replace(/\n/g, "\\n");
}

function gauge(lines: string[], name: string, help: string, value: number): void {
  lines.push(`# HELP ${name} ${help}`, `# TYPE ${name} gauge`, `${name} ${numeric(value)}`);
}

/** Prometheus text exposition (version 0.0.4) of one snapshot. */
function renderPrometheusText(
  snapshot: MetricsSnapshot,
  identity: MetricsRoutesOptions["productIdentity"],
): string {
  const lines: string[] = [];
  lines.push(
    "# HELP novel_engine_info Running product identity.",
    "# TYPE novel_engine_info gauge",
    `novel_engine_info{product="${labelValue(identity.name)}",version="${labelValue(identity.version)}"} 1`,
  );
  gauge(
    lines,
    "novel_engine_uptime_seconds",
    "Seconds since this process started.",
    snapshot.uptimeSeconds,
  );
  gauge(
    lines,
    "novel_engine_process_resident_memory_bytes",
    "Resident memory of the server process, in bytes.",
    snapshot.residentMemoryBytes,
  );
  gauge(
    lines,
    "novel_engine_nodejs_heap_used_bytes",
    "Used V8 heap of the server process, in bytes.",
    snapshot.heapUsedBytes,
  );
  gauge(lines, "novel_engine_documents", "Documents in the content authority.", snapshot.documents);
  gauge(
    lines,
    "novel_engine_revisions",
    "Immutable revisions in the content authority.",
    snapshot.revisions,
  );
  lines.push(
    "# HELP novel_engine_jobs Jobs of the content authority, by status.",
    "# TYPE novel_engine_jobs gauge",
  );
  for (const status of Object.keys(snapshot.jobsByStatus).sort()) {
    lines.push(
      `novel_engine_jobs{status="${labelValue(status)}"} ${numeric(snapshot.jobsByStatus[status] ?? 0)}`,
    );
  }
  lines.push(
    "# HELP novel_engine_usage_requests_total Provider attempts recorded in the usage ledger.",
    "# TYPE novel_engine_usage_requests_total counter",
    `novel_engine_usage_requests_total ${numeric(snapshot.usageRequests)}`,
    "# HELP novel_engine_usage_prompt_tokens_total Provider prompt tokens of completed attempts.",
    "# TYPE novel_engine_usage_prompt_tokens_total counter",
    `novel_engine_usage_prompt_tokens_total ${numeric(snapshot.promptTokens)}`,
    "# HELP novel_engine_usage_completion_tokens_total Provider completion tokens of completed attempts.",
    "# TYPE novel_engine_usage_completion_tokens_total counter",
    `novel_engine_usage_completion_tokens_total ${numeric(snapshot.completionTokens)}`,
  );
  return `${lines.join("\n")}\n`;
}
