import type { FastifyPluginAsync } from "fastify";

import { beatRoutes } from "./beat_routes.js";
import { documentRoutes } from "./document_routes.js";
import { exportRoutes } from "./export_routes.js";
import { importRoutes } from "./import_routes.js";
import { jobRoutes } from "./job_routes.js";
import { projectRoutes, type StudioRoutesOptions } from "./project_routes.js";
import { proposalRoutes } from "./proposal_routes.js";
import { reviewRoutes } from "./review_routes.js";
import { volumeRoutes } from "./volume_routes.js";

/** Registers the existing Studio HTTP surfaces in their public route order. */
export const studioRoutes: FastifyPluginAsync<StudioRoutesOptions> = async (app, options) => {
  await app.register(projectRoutes, options);
  await app.register(documentRoutes, options);
  await app.register(beatRoutes, options);
  await app.register(volumeRoutes, options);
  await app.register(proposalRoutes, options);
  await app.register(reviewRoutes, options);
  await app.register(exportRoutes, options);
  await app.register(importRoutes, options);
  await app.register(jobRoutes, options);
};
