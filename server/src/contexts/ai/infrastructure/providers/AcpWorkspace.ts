import { constants } from "node:fs";
import { lstat, open, realpath } from "node:fs/promises";
import { basename, isAbsolute, join, relative, resolve } from "node:path";
import type { ReadTextFileRequest, WriteTextFileRequest } from "@agentclientprotocol/sdk";
import { TextGenerationProviderError } from "../../application/ports/text_generation.js";
/** Client filesystem callbacks only operate on explicit material copies inside the configured workspace. */
export class AcpWorkspace {
  private constructor(readonly root: string) {}
  static async open(root: string): Promise<AcpWorkspace> {
    if (!isAbsolute(root))
      throw new TextGenerationProviderError("ACP_WORKSPACE_ROOT must be absolute.");
    const canonical = await realpath(root);
    if (!(await lstat(canonical)).isDirectory())
      throw new TextGenerationProviderError("ACP workspace is not a directory.");
    return new AcpWorkspace(canonical);
  }
  /** Display only relative material paths; outside and secret-capable targets stay hidden. */
  safeTarget(value: string | undefined): string | undefined {
    if (value === undefined) return undefined;
    const name = relative(this.root, resolve(this.root, value));
    if (
      name === "" ||
      name.startsWith("..") ||
      isAbsolute(name) ||
      name
        .split(/[\\/]/u)
        .some(
          (part) =>
            part.startsWith(".") ||
            /secret|credential|token|\.sqlite3|\.db$|^exports$/iu.test(part),
        )
    )
      return undefined;
    return name;
  }
  private async path(value: string, writing: boolean): Promise<string> {
    const name = this.safeTarget(value);
    if (name === undefined)
      throw new TextGenerationProviderError(
        "ACP filesystem target is outside the permitted material workspace.",
      );
    const target = resolve(this.root, value);
    let directory = this.root;
    for (const component of name.split(/[\\/]/u).slice(0, -1)) {
      directory = join(directory, component);
      const info = await lstat(directory);
      if (info.isSymbolicLink() || !info.isDirectory())
        throw new TextGenerationProviderError("ACP filesystem directory alias is forbidden.");
    }
    const parent = await realpath(resolve(target, ".."));
    const parentName = relative(this.root, parent);
    if (parentName.startsWith("..") || isAbsolute(parentName))
      throw new TextGenerationProviderError("ACP filesystem parent escapes the workspace.");
    try {
      if ((await lstat(target)).isSymbolicLink())
        throw new TextGenerationProviderError("ACP filesystem symlink is forbidden.");
    } catch (error) {
      if (!(writing && error instanceof Error && "code" in error && error.code === "ENOENT"))
        throw error;
    }
    const canonical = join(parent, basename(target));
    if (this.safeTarget(canonical) === undefined)
      throw new TextGenerationProviderError("ACP canonical filesystem target is protected.");
    return canonical;
  }
  async read(request: ReadTextFileRequest): Promise<{ content: string }> {
    const handle = await open(
      await this.path(request.path, false),
      constants.O_RDONLY | constants.O_NOFOLLOW,
    );
    try {
      const stat = await handle.stat();
      if (!stat.isFile() || stat.nlink !== 1)
        throw new TextGenerationProviderError("ACP material must be a regular unshared file.");
      if (stat.size > 1024 * 1024)
        throw new TextGenerationProviderError("ACP material file exceeds the byte budget.");
      const text = await handle.readFile("utf8");
      const lines = text.split("\n");
      const start = Math.max(0, (request.line ?? 1) - 1);
      return {
        content: lines
          .slice(start, request.limit == null ? undefined : start + request.limit)
          .join("\n"),
      };
    } finally {
      await handle.close();
    }
  }
  async write(request: WriteTextFileRequest): Promise<void> {
    if (Buffer.byteLength(request.content, "utf8") > 1024 * 1024)
      throw new TextGenerationProviderError("ACP material file exceeds the byte budget.");
    const handle = await open(
      await this.path(request.path, true),
      constants.O_WRONLY | constants.O_CREAT | constants.O_NOFOLLOW,
      0o600,
    );
    try {
      const stat = await handle.stat();
      if (!stat.isFile() || stat.nlink !== 1)
        throw new TextGenerationProviderError("ACP material must be a regular unshared file.");
      await handle.truncate(0);
      await handle.writeFile(request.content, "utf8");
    } finally {
      await handle.close();
    }
  }
}
