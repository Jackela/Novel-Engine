/**
 * Executable architecture policy for server/src — the dependency-cruiser twin of
 * .importlinter's six contracts, plus the two gap closures adjudicated in #253:
 *   (a) the interface layer may not import shared infrastructure either (audit F-8);
 *   (b) the ai context is a leaf provider module, importable only through its
 *       application ports (the composition root src/apps is exempt — it wires
 *       concrete providers), and never importing the studio context.
 *
 * Paths are relative to server/ (cruise target: src).
 *
 * @type {import('dependency-cruiser').IConfiguration}
 */
module.exports = {
  forbidden: [
    {
      name: "functional-core-isolation",
      comment: "Domain layers never import application or infrastructure layers.",
      severity: "error",
      from: { path: "^src/(contexts/[^/]+|shared)/domain" },
      to: { path: "^src/(contexts/[^/]+/(application|infrastructure)|shared/infrastructure)" },
    },
    {
      name: "application-isolation",
      comment: "Application layers orchestrate through ports; they never import infrastructure.",
      severity: "error",
      from: { path: "^src/(contexts/[^/]+|shared)/application" },
      to: { path: "^src/(contexts/[^/]+/infrastructure|shared/infrastructure)" },
    },
    {
      name: "contexts-outside-apps",
      comment: "Bounded contexts never import composition roots.",
      severity: "error",
      from: { path: "^src/contexts" },
      to: { path: "^src/apps" },
    },
    {
      name: "shared-kernel",
      comment: "The shared kernel never imports bounded contexts.",
      severity: "error",
      from: { path: "^src/shared" },
      to: { path: "^src/contexts" },
    },
    {
      name: "interface-isolation",
      comment:
        "Interface layers own HTTP concerns only — no direct infrastructure imports, including shared infrastructure (audit gap closure F-8).",
      severity: "error",
      from: { path: "^src/(contexts/[^/]+|shared)/interface" },
      to: { path: "^src/(contexts/[^/]+/infrastructure|shared/infrastructure)" },
    },
    {
      name: "domain-application-avoid-interface",
      comment: "Domain and application layers never import interface layers.",
      severity: "error",
      from: { path: "^src/(contexts/[^/]+/(domain|application)|shared/(domain|application))" },
      to: { path: "^src/(contexts/[^/]+/interface|shared/interface)" },
    },
    {
      name: "ai-leaf-ports-only",
      comment:
        "Audit gap closure: the ai context is a leaf provider module — code outside it may only import it through its application ports. The composition root (src/apps) is exempt, mirroring the Python authority whose runtime wires create_text_generation_provider directly.",
      severity: "error",
      from: { pathNot: ["^src/contexts/ai/", "^src/apps/"] },
      to: { path: "^src/contexts/ai/(domain|infrastructure|interface)" },
    },
    {
      name: "ai-never-imports-studio",
      comment:
        "Audit gap closure: the ai context stays independent — it never imports the studio context.",
      severity: "error",
      from: { path: "^src/contexts/ai" },
      to: { path: "^src/contexts/studio" },
    },
  ],
  options: {
    doNotFollow: {
      path: "node_modules",
    },
    tsConfig: {
      fileName: "tsconfig.json",
    },
    enhancedResolveOptions: {
      extensions: [".ts", ".mts", ".cts", ".js", ".mjs", ".cjs"],
    },
  },
};
