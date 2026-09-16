import type { FastifyPluginAsync } from "fastify";

import type {
  HealthComponent,
  HealthProbe,
  HealthReport,
  HealthStatus,
} from "../../application/ports/health.js";

interface HealthRoutesOptions {
  healthProbe: HealthProbe;
}

interface SerializedComponent {
  status: HealthStatus;
  message: string;
  error: string | null;
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
    message: { type: "string" },
    error: { type: "string", nullable: true },
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

/**
 * Projects a probe component onto the wire shape. The wire shape stays exactly as
 * wide as the port: `HealthComponent` carries no timing and no structured detail,
 * so a `response_time_ms` or `details` field here would publish a constant as if it
 * had been measured. Extend the port first if either is genuinely wanted.
 */
function serializeComponent(component: HealthComponent): SerializedComponent {
  return {
    status: component.status,
    message: component.message ?? "",
    error: component.error ?? null,
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
