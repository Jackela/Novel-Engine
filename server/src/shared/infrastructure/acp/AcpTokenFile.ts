import { randomBytes } from "node:crypto";
import { constants } from "node:fs";
import { open } from "node:fs/promises";

/** Read a private token, optionally creating it atomically. Refuse links, non-files,
 * foreign owners, unsafe permissions, and malformed contents without logging a token. */
export async function AcpTokenFile(
  path: string,
  options: { readonly create?: boolean } = {},
): Promise<string> {
  if (options.create) {
    try {
      const file = await open(
        path,
        constants.O_WRONLY | constants.O_CREAT | constants.O_EXCL | constants.O_NOFOLLOW,
        0o600,
      );
      try {
        await file.writeFile(`${randomBytes(32).toString("base64url")}\n`);
      } finally {
        await file.close();
      }
    } catch (error) {
      if (!(error instanceof Error && "code" in error && error.code === "EEXIST")) throw error;
    }
  }
  const file = await open(path, constants.O_RDONLY | constants.O_NOFOLLOW);
  try {
    const status = await file.stat();
    if (
      !status.isFile() ||
      (status.mode & 0o777) !== 0o600 ||
      (process.getuid && status.uid !== process.getuid())
    ) {
      throw new Error("ACP token must be an owner-held regular file with mode 0600.");
    }
    if (status.size > 128) throw new Error("ACP token file is malformed.");
    const token = (await file.readFile("utf8")).trim();
    if (!/^[A-Za-z0-9_-]{43}$/.test(token) || Buffer.from(token, "base64url").length !== 32) {
      throw new Error("ACP token file is malformed.");
    }
    return token;
  } finally {
    await file.close();
  }
}
