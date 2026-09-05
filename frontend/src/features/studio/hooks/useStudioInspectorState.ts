import type { Dispatch, SetStateAction } from "react";
import { useCallback, useEffect, useState } from "react";

import type { Project } from "@/app/types/studio";
import type { InspectorTab } from "../studioConstants";
import type { SettingsFormState } from "../studioInspectorTypes";

interface UseStudioInspectorStateArgs {
  readonly inspector: InspectorTab;
  readonly project: Project | null;
  readonly loadJobs: () => Promise<void>;
  readonly onSelectInspector: (inspector: InspectorTab) => void;
}

interface StudioInspectorState {
  readonly inspector: InspectorTab;
  readonly setInspector: Dispatch<SetStateAction<InspectorTab>>;
  readonly settingsForm: SettingsFormState;
  readonly setSettingsForm: Dispatch<SetStateAction<SettingsFormState>>;
}

interface SettingsFormSnapshot {
  readonly projectKey: string | null;
  readonly form: SettingsFormState;
}

function projectKey(project: Project | null): string | null {
  return project
    ? `${project.id}:${project.title}:${project.description}:${String(project.settings.provider ?? "mock")}`
    : null;
}

function settingsFormFor(project: Project | null): SettingsFormState {
  return {
    title: project?.title ?? "",
    description: project?.description ?? "",
    provider: String(project?.settings.provider ?? "mock"),
  };
}

export function useStudioInspectorState({
  inspector,
  project,
  loadJobs,
  onSelectInspector,
}: UseStudioInspectorStateArgs): StudioInspectorState {
  const currentProjectKey = projectKey(project);
  const [settingsSnapshot, setSettingsSnapshot] = useState<SettingsFormSnapshot>(() => ({
    projectKey: currentProjectKey,
    form: settingsFormFor(project),
  }));

  const setInspector = useCallback<Dispatch<SetStateAction<InspectorTab>>>(
    (nextInspector) => {
      const next = typeof nextInspector === "function" ? nextInspector(inspector) : nextInspector;
      onSelectInspector(next);
    },
    [inspector, onSelectInspector],
  );

  useEffect(() => {
    if (inspector === "jobs") {
      void loadJobs();
    }
  }, [inspector, loadJobs]);

  const setSettingsForm = useCallback<Dispatch<SetStateAction<SettingsFormState>>>(
    (nextForm) => {
      setSettingsSnapshot((current) => {
        const currentForm =
          current.projectKey === currentProjectKey ? current.form : settingsFormFor(project);
        return {
          projectKey: currentProjectKey,
          form: typeof nextForm === "function" ? nextForm(currentForm) : nextForm,
        };
      });
    },
    [currentProjectKey, project],
  );

  const settingsForm =
    settingsSnapshot.projectKey === currentProjectKey
      ? settingsSnapshot.form
      : settingsFormFor(project);

  return { inspector, setInspector, settingsForm, setSettingsForm };
}
