import { type ClientConnection, PROTOCOL_VERSION } from "@agentclientprotocol/sdk";
import { readProductIdentity } from "../../../../shared/infrastructure/workspace_manifest.js";
import {
  ProviderNotConfiguredError,
  TextGenerationProviderError,
  type TextGenerationTask,
} from "../../application/ports/text_generation.js";
import type { AcpTurnBudget } from "./AcpTurnBudget.js";
import { buildAcpSystemContent } from "./buildAcpSystemContent.js";
/** Negotiate, authenticate cached CLI credentials, create one isolated session and confirm any model override. */
export async function openAcpSession(
  connection: ClientConnection,
  options: { command: string; args: readonly string[]; model?: string | undefined },
  root: string,
  task: TextGenerationTask,
  budget: AcpTurnBudget,
) {
  const initialized = await budget.wait(
    connection.agent.request("initialize", {
      protocolVersion: PROTOCOL_VERSION,
      clientInfo: { name: "novel-engine", version: readProductIdentity().version },
      clientCapabilities: { fs: { readTextFile: true, writeTextFile: true }, terminal: false },
      _meta: {
        "novel-engine/acp-proxy": {
          command: options.command,
          args: [...options.args],
          cwd: root,
        },
      },
    }),
  );
  if (!initialized.authMethods?.some((method) => method.id === "cached_token"))
    throw new ProviderNotConfiguredError(
      "ACP agent does not advertise cached_token authentication.",
    );
  await budget.wait(connection.agent.request("authenticate", { methodId: "cached_token" }));
  const session = await budget.wait(
    connection.agent.request("session/new", {
      cwd: root,
      mcpServers: [],
      _meta: { systemPromptOverride: buildAcpSystemContent(task) },
    }),
  );
  let configOptions = session.configOptions;
  if (options.model !== undefined) {
    const option = session.configOptions?.find(
      (candidate) => candidate.category === "model" && candidate.type === "select",
    );
    if (option === undefined)
      throw new TextGenerationProviderError(
        "ACP model override cannot be confirmed by session configuration.",
      );
    const confirmed = await budget.wait(
      connection.agent.request("session/set_config_option", {
        sessionId: session.sessionId,
        configId: option.id,
        value: options.model,
      }),
    );
    configOptions = confirmed.configOptions;
    const model = confirmed.configOptions.find(
      (candidate) => candidate.category === "model" && candidate.type === "select",
    );
    if (model?.type !== "select" || model.currentValue !== options.model)
      throw new TextGenerationProviderError("ACP model override was not confirmed.");
  }
  return { sessionId: session.sessionId, configOptions };
}
