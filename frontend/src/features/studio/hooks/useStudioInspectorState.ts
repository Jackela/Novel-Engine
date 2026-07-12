import { useCallback, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';

import type { Project } from '@/app/types/studio';

import type { SettingsFormState } from '../StudioInspector';
import type { InspectorTab } from '../studioConstants';

interface UseStudioInspectorStateArgs {
  readonly section: string;
  readonly project: Project | null;
  readonly loadJobs: () => Promise<void>;
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

function inspectorForSection(section: string): InspectorTab | null {
  if (section === 'review') return 'review';
  if (section === 'history' || section === 'export') return 'history';
  if (section === 'settings') return 'settings';
  return null;
}

function projectKey(project: Project | null): string | null {
  return project
    ? `${project.id}:${project.title}:${project.description}:${String(project.settings.provider ?? 'mock')}`
    : null;
}

function settingsFormFor(project: Project | null): SettingsFormState {
  return {
    title: project?.title ?? '',
    description: project?.description ?? '',
    provider: String(project?.settings.provider ?? 'mock'),
  };
}

export function useStudioInspectorState({
  section,
  project,
  loadJobs,
}: UseStudioInspectorStateArgs): StudioInspectorState {
  const [selectedInspector, setSelectedInspector] = useState<InspectorTab>('copilot');
  const currentProjectKey = projectKey(project);
  const [settingsSnapshot, setSettingsSnapshot] = useState<SettingsFormSnapshot>(() => ({
    projectKey: currentProjectKey,
    form: settingsFormFor(project),
  }));

  const setInspector = useCallback<Dispatch<SetStateAction<InspectorTab>>>(
    (nextInspector) => {
      setSelectedInspector((current) => {
        const next = typeof nextInspector === 'function' ? nextInspector(current) : nextInspector;
        if (next === 'jobs') {
          void loadJobs();
        }
        return next;
      });
    },
    [loadJobs],
  );

  const setSettingsForm = useCallback<Dispatch<SetStateAction<SettingsFormState>>>(
    (nextForm) => {
      setSettingsSnapshot((current) => {
        const currentForm =
          current.projectKey === currentProjectKey ? current.form : settingsFormFor(project);
        return {
          projectKey: currentProjectKey,
          form: typeof nextForm === 'function' ? nextForm(currentForm) : nextForm,
        };
      });
    },
    [currentProjectKey, project],
  );

  const inspector = inspectorForSection(section) ?? selectedInspector;
  const settingsForm =
    settingsSnapshot.projectKey === currentProjectKey
      ? settingsSnapshot.form
      : settingsFormFor(project);

  return { inspector, setInspector, settingsForm, setSettingsForm };
}
