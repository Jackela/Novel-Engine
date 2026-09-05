import { existsSync, readFileSync } from "node:fs";
import { join, resolve } from "node:path";

import {
  fileSuffix,
  listRepoFiles,
  readTextLines,
  repoRoot,
  reportFailures,
  scanRootFiles,
} from "./common.mjs";

/**
 * Product identity and version authority. Since the cutover retired the
 * Python tree, the server package manifest release version is the single
 * source of truth.
 */

const AUTHORITY_MANIFEST = "server/package.json";
const PRODUCT_NAME = "Novel Engine";
const SEMVER =
  /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|[0-9]*[A-Za-z-][0-9A-Za-z-]*)(?:\.(?:0|[1-9]\d*|[0-9]*[A-Za-z-][0-9A-Za-z-]*))*))?(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$/;
const SEMVER_CORE = SEMVER.source.slice(1, -1);
const TEXT_SUFFIXES = new Set([".md", ".ts", ".tsx", ".js", ".mjs", ".cjs", ".json"]);
const SCAN_SKIP_DIRECTORIES = new Set(["node_modules", "dist", "tmp", "coverage"]);
const IDENTITY_SCAN_PATHS = [
  "README.md",
  "AGENTS.md",
  "openwiki",
  "frontend/index.html",
  "frontend/src",
  "server/src",
  "server/package.json",
];
const CURRENT_DECLARATION_PATHS = ["AGENTS.md", "openwiki/quickstart.md"];
const RETIRED_IDENTITY = new RegExp(
  [
    "Story",
    "Forge|Novel",
    " Studio|multi-agent",
    " narrative|Markdown files are the manuscript",
    " source of truth",
  ].join(""),
  "i",
);
const RETIRED_CAPABILITY_REFERENCE = ["openspec/specs/novel-", "studio/spec.md"].join("");

function readJson(root, relativePath) {
  return JSON.parse(readFileSync(join(root, relativePath), "utf8"));
}

function productIdentity(root) {
  const manifest = readJson(root, AUTHORITY_MANIFEST);
  const rawProductName = typeof manifest.productName === "string" ? manifest.productName : "";
  const rawVersion = typeof manifest.version === "string" ? manifest.version : "";
  const productName = rawProductName.trim();
  const version = rawVersion.trim();
  const failures = [];
  if (productName === "") {
    failures.push(`${AUTHORITY_MANIFEST} must define a non-blank productName`);
  } else if (rawProductName !== productName) {
    failures.push(`${AUTHORITY_MANIFEST} productName must not contain surrounding whitespace`);
  } else if (productName !== PRODUCT_NAME) {
    failures.push(`${AUTHORITY_MANIFEST} productName must be ${PRODUCT_NAME}, got ${productName}`);
  }
  if (!SEMVER.test(rawVersion)) {
    failures.push(
      `${AUTHORITY_MANIFEST} version must be valid SemVer, got ${JSON.stringify(rawVersion)}`,
    );
  }
  return { productName, version, failures };
}

function workspacePackageFailures(root) {
  const failures = [];
  for (const relativePath of listRepoFiles(root)) {
    if (relativePath !== "package.json" && !relativePath.endsWith("/package.json")) {
      continue;
    }
    const manifest = readJson(root, relativePath);
    if (
      relativePath !== AUTHORITY_MANIFEST &&
      ("version" in manifest || "productName" in manifest)
    ) {
      failures.push(`${relativePath} must not define version or productName`);
    }
  }
  const frontend = readJson(root, "frontend/package.json");
  if (frontend.name !== "novel-engine-studio") {
    failures.push("frontend package must be named novel-engine-studio");
  }
  const server = readJson(root, AUTHORITY_MANIFEST);
  if (server.name !== "novel-engine-server") {
    failures.push("server package must be named novel-engine-server");
  }
  return failures;
}

function openspecFailures(root) {
  const failures = [];
  if (!existsSync(join(root, "openspec", "specs", "novel-engine", "spec.md"))) {
    failures.push("canonical OpenSpec capability novel-engine is missing");
  }
  // novel-studio may only remain while the cutover-consolidation change that
  // retires it is still open; once archived, the retired spec must be gone.
  if (
    existsSync(join(root, "openspec", "specs", "novel-studio", "spec.md")) &&
    !existsSync(join(root, "openspec", "changes", "2026-08-25-cutover-consolidation"))
  ) {
    failures.push("retired OpenSpec capability novel-studio still exists");
  }
  for (const relativePath of listRepoFiles(root)) {
    if (
      relativePath.includes("openspec/changes/archive/") ||
      !isActiveInstructionPath(relativePath) ||
      !TEXT_SUFFIXES.has(fileSuffix(relativePath))
    ) {
      continue;
    }
    if (readTextLines(join(root, relativePath)).join("\n").includes(RETIRED_CAPABILITY_REFERENCE)) {
      failures.push(`${relativePath} contains a retired OpenSpec capability reference`);
    }
  }
  return failures;
}

function isActiveInstructionPath(relativePath) {
  return (
    relativePath === "AGENTS.md" ||
    relativePath.endsWith("/AGENTS.md") ||
    relativePath.startsWith(".agents/skills/") ||
    relativePath.startsWith("docs/agents/") ||
    relativePath.startsWith("openwiki/")
  );
}

function projectionFailures(root, productName, version) {
  const failures = [];
  const readme = readTextLines(join(root, "README.md")).join("\n");
  if (!readme.includes(`${productName} \`${version}\``)) {
    failures.push(`README.md current product version must match ${AUTHORITY_MANIFEST}`);
  }

  const currentRelease = readTextLines(join(root, "CHANGELOG.md")).find((line) =>
    /^##\s+\S/.test(line),
  );
  if (currentRelease !== `## ${version}`) {
    failures.push(`CHANGELOG.md current release must be ## ${version}, got ${currentRelease}`);
  }

  const openapi = readJson(root, "server/qa-baselines/openapi.current.json");
  if (openapi.info?.title !== `${productName} API` || openapi.info?.version !== version) {
    failures.push("OpenAPI info title/version must match the server manifest product identity");
  }

  const currentVersionDeclaration = new RegExp(
    `${productName}\\s+(?:\\*\\*|\`)?${SEMVER_CORE}(?:\\*\\*|\`)?\\s+is\\b`,
    "i",
  );
  for (const relativePath of CURRENT_DECLARATION_PATHS) {
    const introduction = readTextLines(join(root, relativePath)).slice(0, 8).join("\n");
    if (currentVersionDeclaration.test(introduction)) {
      failures.push(`${relativePath} current product declaration must be versionless`);
    }
  }
  return failures;
}

function identityFailures(root) {
  const failures = [];
  for (const scanPath of IDENTITY_SCAN_PATHS) {
    for (const relativePath of scanRootFiles(root, scanPath, SCAN_SKIP_DIRECTORIES)) {
      if (!TEXT_SUFFIXES.has(fileSuffix(relativePath))) {
        continue;
      }
      if (RETIRED_IDENTITY.test(readTextLines(join(root, relativePath)).join("\n"))) {
        failures.push(`${relativePath} contains a retired product identity`);
      }
    }
  }
  return failures;
}

const root = process.argv[2] === undefined ? repoRoot() : resolve(process.argv[2]);
const { productName, version, failures: identityProblems } = productIdentity(root);
const failures = [
  ...identityProblems,
  ...workspacePackageFailures(root),
  ...openspecFailures(root),
  ...projectionFailures(root, productName, version),
  ...identityFailures(root),
];

if (reportFailures("ssot", failures)) {
  console.log(`[ssot] ${productName} ${version} is aligned`);
}
