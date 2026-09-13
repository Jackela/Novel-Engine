/**
 * Executable architecture policy for server/src — the layer-isolation contracts,
 * plus the gap closures adjudicated in #253 and #420:
 *   (a) the interface layer may not import shared infrastructure either (audit F-8);
 *   (b) the ai context is a leaf provider module, importable only through its
 *       application ports — the only exemptions are the named composition-root
 *       wiring files in src/apps (they wire concrete providers), and ai never
 *       imports the studio context.
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
      to: {
        path: "^src/(contexts/[^/]+/(application|infrastructure)|shared/(application|infrastructure))",
      },
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
        "Audit gap closure: the ai context is a leaf provider module — everything outside its application layer (infrastructure, interface, and any domain or root-level files) is invisible from outside; application-layer imports are narrowed to ports/ by ai-ports-only. Exemption granularity (#535): only the named composition-root wiring files are exempt, mirroring the Python authority whose runtime wires create_text_generation_provider directly — api/app.ts (mounts provider routes), api/provider_runtime.ts and cli/legacy_import_command.ts (wire the provider factory). Every other src/apps file goes through ai application ports like the rest of the tree.",
      severity: "error",
      from: {
        pathNot: [
          "^src/contexts/ai/",
          "^src/apps/api/app\\.ts$",
          "^src/apps/api/provider_runtime\\.ts$",
          "^src/apps/cli/legacy_import_command\\.ts$",
        ],
      },
      to: { path: "^src/contexts/ai/(?!application/)" },
    },
    {
      name: "ai-ports-only",
      comment:
        "Audit gap closure (#420): inside the ai application layer only ports/ is importable from outside the ai context — application internals (e.g. model_resolution) stay private. Exemption granularity (#535): api/provider_runtime.ts is the only src/apps file exempt (its provider wiring resolves models through ai application internals, same rationale as ai-leaf-ports-only); the other wiring files import ports/ only, so they need no exemption here.",
      severity: "error",
      from: {
        pathNot: ["^src/contexts/ai/", "^src/apps/api/provider_runtime\\.ts$"],
      },
      to: { path: "^src/contexts/ai/application/(?!ports/)[^/]" },
    },
    {
      name: "ai-never-imports-studio",
      comment:
        "Audit gap closure: the ai context stays independent — it never imports the studio context.",
      severity: "error",
      from: { path: "^src/contexts/ai" },
      to: { path: "^src/contexts/studio" },
    },
    {
      name: "ai-providers-neutral-no-vendor",
      comment:
        "Neutral shared modules in the ai providers directory (provider_* prefix convention) must not import vendor/adapter modules; the dependency direction is always vendor → neutral (B4 follow-up, 2026-09-11).",
      severity: "error",
      from: { path: "^src/contexts/ai/infrastructure/providers/provider_[^/]+\\.ts$" },
      to: { path: "^src/contexts/ai/infrastructure/providers/(?!provider_)[^/]+\\.ts$" },
    },
  ],
  options: {
    // TypeScript 7 ships no JS compiler API yet (that lands with typescript@7.1),
    // so dependency-cruiser's tsc parser range (>=2 <7) would silently skip every
    // TS source. The swc parser (>=1 <2) parses TS itself and keeps the gate
    // meaningful; server/src uses no tsconfig path aliases, so dropping the
    // tsConfig option loses nothing.
    parser: "swc",
    doNotFollow: {
      path: "node_modules",
    },
    enhancedResolveOptions: {
      extensions: [".ts", ".mts", ".cts", ".js", ".mjs", ".cjs"],
    },
  },
};
