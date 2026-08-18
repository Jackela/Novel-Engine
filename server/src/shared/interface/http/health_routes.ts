import type { FastifyPluginAsync } from "fastify";

import type {
  HealthComponent,
  HealthProbe,
  HealthReport,
  HealthStatus,
} from "../../application/ports/health.js";

export interface HealthRoutesOptions {
  healthProbe: HealthProbe;
}

interface SerializedComponent {
  status: HealthStatus;
  response_time_ms: number;
  message: string;
  error: string | null;
  details: Record<string, unknown>;
}

interface DetailedHealthPayload {
  overall_status: HealthStatus;
  timestamp: string;
  components: Record<string, SerializedComponent>;
}

const componentSchema = {
  type: "object",
  properties: {
    status: { type: "string", enum: ["healthy", "unhealthy"] },
    response_time_ms: { type: "number" },
    message: { type: "string" },
    error: { type: "string", nullable: true },
    details: { type: "object" },
  },
};

/**
 * Probe transport failures count as a failed dependency instead of crashing
 * the health surface itself.
 */
async function collectReport(probe: HealthProbe): Promise<HealthReport> {
  try {
    return await probe();
  } catch (error) {
    return {
      components: [
        {
          name: "health_probe",
          status: "unhealthy",
          error: error instanceof Error ? error.message : String(error),
        },
      ],
    };
  }
}

function serializeComponent(component: HealthComponent): SerializedComponent {
  return {
    status: component.status,
    response_time_ms: 0,
    message: component.message ?? "",
    error: component.error ?? null,
    details: {},
  };
}

export const healthRoutes: FastifyPluginAsync<HealthRoutesOptions> = async (app, options) => {
  app.get(
    "/health",
    {
      schema: {
        response: {
          200: {
            type: "object",
            properties: {
              overall_status: { type: "string", enum: ["healthy", "unhealthy"] },
              timestamp: { type: "string" },
              components: { type: "object", additionalProperties: componentSchema },
            },
          },
        },
      },
    },
    async (): Promise<DetailedHealthPayload> => {
      const report = await collectReport(options.healthProbe);
      const components: Record<string, SerializedComponent> = {};
      let overall: HealthStatus = "healthy";
      for (const component of report.components) {
        components[component.name] = serializeComponent(component);
        if (component.status !== "healthy") {
          overall = "unhealthy";
        }
      }
      return { overall_status: overall, timestamp: new Date().toISOString(), components };
    },
  );

  app.get(
    "/health/live",
    {
      schema: {
        response: { 200: { type: "object", properties: { status: { type: "string" } } } },
      },
    },
    async () => ({ status: "alive" }),
  );

  app.get(
    "/health/ready",
    {
      schema: {
        response: {
          200: { type: "object", properties: { status: { type: "string" } } },
          503: {
            type: "object",
            properties: {
              status: { type: "string" },
              reason: { type: "string", nullable: true },
            },
          },
        },
      },
    },
    async (_request, reply) => {
      const report = await collectReport(options.healthProbe);
      const failed = report.components.find((component) => component.status !== "healthy");
      if (failed) {
        return await reply.status(503).send({
          status: "not_ready",
          reason: failed.error ?? `${failed.name} is not ready`,
        });
      }
      return { status: "ready" };
    },
  );
};
