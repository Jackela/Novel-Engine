import { realpathSync } from "node:fs";
import { basename, isAbsolute, relative } from "node:path";
import { ConfigurationError } from "../../shared/infrastructure/config/configuration_error.js";
import type { LlmServerConfig } from "../../shared/infrastructure/config/provider_config.js";

function contains(parent: string, child: string): boolean {
  const path = relative(parent, child);
  return path === "" || (!path.startsWith("..") && !isAbsolute(path));
}
/** ACP materials never overlap the Studio data authority; Grok launches retain fail-closed custom native sandbox flags. */
export function validateAcpWorkspace(acp: LlmServerConfig["acp"], dataDirectory?: string): void {
  if (acp?.workspaceRoot === undefined) return;
  if (!isAbsolute(acp.workspaceRoot))
    throw new ConfigurationError("ACP_WORKSPACE_ROOT must be absolute.");
  let workspace: string;
  try {
    workspace = realpathSync(acp.workspaceRoot);
  } catch (error) {
    if (!(error instanceof Error && "code" in error)) throw error;
    throw new ConfigurationError("ACP_WORKSPACE_ROOT must name an existing material directory.");
  }
  if (dataDirectory !== undefined) {
    const data = realpathSync(dataDirectory);
    if (contains(data, workspace) || contains(workspace, data))
      throw new ConfigurationError("ACP workspace and Studio data directory must not overlap.");
  }
  if (/^grok(?:\.exe)?$/u.test(basename(acp.command))) {
    const declarations = acp.args.flatMap((arg, index) =>
      arg === "--sandbox"
        ? [acp.args[index + 1]]
        : arg.startsWith("--sandbox=")
          ? [arg.slice(10)]
          : [],
    );
    if (
      declarations.length !== 1 ||
      declarations[0] === undefined ||
      !/^[a-zA-Z][a-zA-Z0-9_-]*$/u.test(declarations[0]) ||
      ["off", "workspace", "devbox", "read-only", "strict"].includes(declarations[0])
    )
      throw new ConfigurationError(
        "Grok ACP launches require exactly one custom --sandbox profile; built-in profiles may fail open.",
      );
  }
}
