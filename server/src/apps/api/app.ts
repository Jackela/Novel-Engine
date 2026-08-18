import type { TypeBoxTypeProvider } from "@fastify/type-provider-typebox";
import Fastify from "fastify";

export async function buildApp() {
  const app = Fastify({ logger: false }).withTypeProvider<TypeBoxTypeProvider>();

  app.get("/api/hello", async () => ({ message: "hello from novel-engine server" }));

  return app;
}
