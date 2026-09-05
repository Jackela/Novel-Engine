import type { InspectorTab } from "./studioConstants";

const AUTHORING_SECTIONS = ["manuscript", "outline", "characters", "world"] as const;
const ROUTE_INSPECTORS = ["review", "history", "export", "settings"] as const;
const LOCAL_INSPECTORS = ["copilot", "jobs", "usage"] as const;

export type StudioSection = (typeof AUTHORING_SECTIONS)[number] | (typeof ROUTE_INSPECTORS)[number];

export interface StudioRouteState {
  readonly section: StudioSection;
  readonly inspector: InspectorTab;
  readonly canonicalPath: string;
}

function includes<const Values extends readonly string[]>(
  values: Values,
  value: string,
): value is Values[number] {
  return values.includes(value as Values[number]);
}

function projectPath(projectId: string, section: StudioSection): string {
  return `/projects/${encodeURIComponent(projectId)}/${section}`;
}

function localInspectorPath(
  projectId: string,
  section: (typeof AUTHORING_SECTIONS)[number],
  inspector: (typeof LOCAL_INSPECTORS)[number],
): string {
  const path = projectPath(projectId, section);
  return inspector === "copilot" ? path : `${path}?inspector=${inspector}`;
}

export function resolveStudioRoute(
  projectId: string,
  currentSection: string | undefined,
  search: string,
): StudioRouteState {
  const section = currentSection ?? "manuscript";
  if (includes(ROUTE_INSPECTORS, section)) {
    return {
      section,
      inspector: section,
      canonicalPath: projectPath(projectId, section),
    };
  }
  if (!includes(AUTHORING_SECTIONS, section)) {
    return {
      section: "manuscript",
      inspector: "copilot",
      canonicalPath: projectPath(projectId, "manuscript"),
    };
  }

  const inspectorValue = new URLSearchParams(search).get("inspector") ?? "copilot";
  const inspector = includes(LOCAL_INSPECTORS, inspectorValue) ? inspectorValue : "copilot";
  return {
    section,
    inspector,
    canonicalPath: localInspectorPath(projectId, section, inspector),
  };
}

export function studioInspectorPath(
  projectId: string,
  currentSection: string | undefined,
  inspector: InspectorTab,
): string {
  if (includes(ROUTE_INSPECTORS, inspector)) {
    return projectPath(projectId, inspector);
  }
  const authoringSection =
    currentSection && includes(AUTHORING_SECTIONS, currentSection) ? currentSection : "manuscript";
  return localInspectorPath(projectId, authoringSection, inspector);
}
