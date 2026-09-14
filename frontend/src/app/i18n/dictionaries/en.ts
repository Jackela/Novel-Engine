/**
 * English dictionary — the SSOT for the message-key family. Every key a
 * component may request is declared here as a literal, so `Dictionary`
 * (and therefore `MessageKey`) is derived from this object: requesting an
 * unknown key is a compile error, and `zh.ts` must provide every key
 * before it type-checks. English is the default language, so these values
 * are also the exact strings the e2e suite locates against — edit them
 * only together with the matching e2e specs.
 *
 * Key families (phase-2 convention): `<screen>.<group>.<camelCaseLeaf>`
 * — `entry.*`, `library.*`, `settings.*`, `shell.*`, plus the shared
 * `common.*`, `theme.*`, `language.*`, and `provider.*` families. When a
 * dictionary outgrows the file-size budget, split it per screen and
 * re-merge the key types here.
 */
export const en = {
  "common.action.tryAgain": "Try again",
  "common.action.tryingAgain": "Trying again...",
  "common.field.title": "Title",
  "common.field.description": "Description",

  "theme.legend": "Theme",
  "theme.option.system": "System",
  "theme.option.systemLight": "System (light)",
  "theme.option.systemDark": "System (dark)",
  "theme.option.light": "Light",
  "theme.option.dark": "Dark",

  // Option labels are native names shown in their own language on purpose:
  // a reader who cannot parse the active language must still find theirs.
  "language.legend": "Language",
  "language.option.en": "English",
  "language.option.zh": "中文",

  "entry.heading.signedIn": "Open your writing studio",
  "entry.heading.createOwner": "Create the local owner",
  "entry.heading.unavailable": "Unable to open your writing studio",
  "entry.heading.loading": "Opening your writing studio",
  "entry.intro.selfHosted":
    "Your projects, Markdown revisions, reviews, and exports stay in this self-hosted instance.",
  "entry.intro.trialProvider":
    "No API key? Generation runs on the built-in trial provider — connect a real one in a project's Settings when you're ready.",
  "entry.field.username": "Username",
  "entry.field.password": "Password",
  "entry.action.signIn": "Sign in",
  "entry.action.signingIn": "Signing in...",
  "entry.action.createOwner": "Create owner",
  "entry.action.creatingOwner": "Creating owner...",
  "entry.status.checkingSession": "Checking your session...",
  "entry.error.unableToContinue": "Unable to continue.",
  "entry.error.unableToCheckOwner": "Unable to check the local owner.",

  "library.action.signOut": "Sign out",
  "library.heading.projects": "Projects",
  "library.intro": "Open a manuscript or start a new novel.",
  "library.create.newProject": "New project",
  "library.create.premise": "Premise",
  "library.action.create": "Create project",
  "library.action.creating": "Creating project...",
  "library.status.loading": "Loading projects...",
  "library.error.unableToCreate": "Unable to create project.",
  "library.error.unableToSignOut": "Unable to sign out.",
  "library.error.unableToLoad": "Unable to load projects.",
  "library.error.unableToLoadOlder": "Unable to load older projects.",
  "library.catalog.noPremise": "No premise yet",
  "library.catalog.end": "End of project catalog.",
  "library.action.loadOlder": "Load older projects",
  "library.action.loadingOlder": "Loading older projects...",

  "settings.heading": "Project settings",
  "settings.field.provider": "Provider",
  "settings.field.storage": "Storage",
  "settings.field.documentSyntax": "Document syntax",
  "settings.value.sqlite": "SQLite",
  "settings.value.markdown": "Markdown",
  "settings.action.save": "Save settings",
  "settings.action.saving": "Saving…",
  "settings.status.saving": "Saving project settings.",

  "shell.action.backToProjects": "Back to projects",

  "provider.mock": "Mock (trial — no API key)",
  "provider.dashscope": "DashScope",
  "provider.openaiCompatible": "OpenAI-compatible",
} as const;

/**
 * The canonical key set every dictionary must satisfy. Keys stay literal
 * (an unknown key never type-checks) while values widen to `string`, so
 * translations hold different text under the same keys.
 */
export type Dictionary = Record<keyof typeof en, string>;

/** Any key the active dictionary resolves; unknown keys fail to compile. */
export type MessageKey = keyof Dictionary;
