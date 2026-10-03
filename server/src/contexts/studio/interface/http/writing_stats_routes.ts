import type { TypeBoxTypeProvider } from "@fastify/type-provider-typebox";
import { Type } from "@fastify/type-provider-typebox";
import type { FastifyPluginAsync } from "fastify";
import { principalGuard, requirePrincipal } from "../../../../shared/interface/http/auth_guard.js";
import type {
  WritingStatsSummary,
  WritingStatsWords,
} from "../../application/ports/writing_stats.js";
import { usageWirePayload } from "./job_routes.js";
import { usageResponseSchema } from "./job_schemas.js";
import { requireServices, type StudioRoutesOptions } from "./project_routes.js";
import { authedReadResponses } from "./route_responses.js";
import { withStudioErrors } from "./studio_error_mapping.js";
import { projectIdParams } from "./studio_request_schemas.js";

/** One calendar day key, `YYYY-MM-DD`, on the caller's own day boundary. */
const UTC_DAY_PATTERN = "^[0-9]{4}-[0-9]{2}-[0-9]{2}$";

/**
 * The day-boundary selector (DR-045): the browser sends its own offset east
 * of UTC in whole minutes, so an author in UTC+8 sees their local day rather
 * than the UTC day. Absent means UTC, and the accepted range is every real
 * offset (UTC-12 … UTC+14).
 */
const statsQuerySchema = Type.Object(
  {
    tz_offset_minutes: Type.Optional(Type.Integer({ default: 0, minimum: -840, maximum: 840 })),
  },
  { additionalProperties: false },
);

/**
 * Word figures split by revision source (#653). Deltas are honest: an author
 * cut contributes a negative `author` figure, so no `minimum` is declared.
 */
const statsWordsSchema = Type.Object(
  {
    author: Type.Integer(),
    ai_accepted: Type.Integer(),
    restore: Type.Integer(),
  },
  { additionalProperties: false },
);

/**
 * The writing-statistics response (#653): rendered-ready output of the
 * aggregation service. Every calendar bucket is a day on `tz_offset_minutes`
 * — the caller's own day boundary (DR-045), echoed back so the view can
 * label it. The `usage` member reuses the usage aggregation's wire shape
 * verbatim (one contract, never a second accounting).
 */
export const writingStatsResponseSchema = Type.Object(
  {
    project_id: Type.String(),
    tz_offset_minutes: Type.Integer({ minimum: -840, maximum: 840 }),
    daily: Type.Array(
      Type.Object(
        {
          date: Type.String({ pattern: UTC_DAY_PATTERN }),
          words: statsWordsSchema,
        },
        { additionalProperties: false },
      ),
    ),
    weekly: Type.Array(
      Type.Object(
        {
          start_date: Type.String({ pattern: UTC_DAY_PATTERN }),
          words: statsWordsSchema,
        },
        { additionalProperties: false },
      ),
    ),
    streak_days: Type.Integer({ minimum: 0 }),
    chapters: Type.Object(
      {
        total: Type.Integer({ minimum: 0 }),
        started: Type.Integer({ minimum: 0 }),
      },
      { additionalProperties: false },
    ),
    usage: Type.Unsafe(usageResponseSchema),
  },
  { additionalProperties: false },
);

function statsWordsPayload(words: WritingStatsWords) {
  return { author: words.author, ai_accepted: words.aiAccepted, restore: words.restore };
}

/** The snake_case wire view of the service's summary. */
function writingStatsPayload(summary: WritingStatsSummary) {
  return {
    project_id: summary.projectId,
    tz_offset_minutes: summary.tzOffsetMinutes,
    daily: summary.daily.map((row) => ({ date: row.date, words: statsWordsPayload(row.words) })),
    weekly: summary.weekly.map((row) => ({
      start_date: row.startDate,
      words: statsWordsPayload(row.words),
    })),
    streak_days: summary.streakDays,
    chapters: summary.chapters,
    usage: usageWirePayload(summary.usage),
  };
}

/**
 * The project writing-statistics read (#653): one owner-guarded read-only
 * route exposing the server-side aggregation. Thin-handler discipline — the
 * attribution and bucketing rules live in the application service.
 */
export const writingStatsRoutes: FastifyPluginAsync<StudioRoutesOptions> = async (
  fastify,
  options,
) => {
  const app = fastify.withTypeProvider<TypeBoxTypeProvider>();
  const guard = principalGuard(options.authService);

  app.get(
    "/api/projects/:projectId/stats",
    {
      preHandler: [guard],
      schema: {
        params: projectIdParams,
        querystring: statsQuerySchema,
        response: authedReadResponses({
          200: writingStatsResponseSchema,
        }),
      },
    },
    async (request) =>
      withStudioErrors(() =>
        writingStatsPayload(
          requireServices(options).writingStats.aggregateWritingStats(
            requirePrincipal(request),
            request.params.projectId,
            request.query.tz_offset_minutes,
          ),
        ),
      ),
  );
};
