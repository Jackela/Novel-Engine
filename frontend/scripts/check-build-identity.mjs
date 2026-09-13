import { existsSync, readdirSync, readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { readProductIdentity } from "../../server/src/shared/infrastructure/workspace_manifest.ts";

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const distRoot = join(frontendRoot, "dist");
const manifestPath = resolve(frontendRoot, "../server/package.json");

function javascriptBundles(directory) {
  if (!existsSync(directory)) {
    throw new Error(`frontend build output is missing: ${directory}`);
  }
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) {
      return javascriptBundles(path);
    }
    return entry.isFile() && entry.name.endsWith(".js") ? [path] : [];
  });
}

const identity = readProductIdentity(manifestPath);
const bundles = javascriptBundles(distRoot);
if (bundles.length === 0) {
  throw new Error(`frontend build emitted no JavaScript bundles beneath ${distRoot}`);
}

const javascript = bundles.map((path) => readFileSync(path, "utf8")).join("\n");
for (const [field, value] of Object.entries(identity)) {
  if (!javascript.includes(value)) {
    throw new Error(
      `frontend build does not project manifest ${field} ${JSON.stringify(value)} into JavaScript`,
    );
  }
}
if (javascript.includes("__PRODUCT_IDENTITY__")) {
  throw new Error("frontend build contains an unresolved __PRODUCT_IDENTITY__ token");
}

const html = readFileSync(join(distRoot, "index.html"), "utf8");
if (!html.includes(`<title>${identity.name}</title>`)) {
  throw new Error("frontend build title does not match the manifest product name");
}
if (!html.includes(`content="${identity.name} is a self-hosted, single-author writing IDE."`)) {
  throw new Error("frontend build description does not match the manifest product name");
}
if (html.includes("__PRODUCT_NAME__")) {
  throw new Error("frontend build contains an unresolved product-name token");
}

console.log(
  `[build-identity] ${identity.name} ${identity.version} verified in HTML and ${bundles.length} JavaScript bundles`,
);
