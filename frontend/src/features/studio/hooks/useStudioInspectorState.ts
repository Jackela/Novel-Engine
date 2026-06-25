import { useEffect, useState } from 'react';
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

export function useStudioInspectorState({
  section,
  project,
  loadJobs,
}: UseStudioInspectorStateArgs): StudioInspectorState {
  const [inspector, setInspector] = useState<InspectorTab>('copilot');
  const [settingsForm, setSettingsForm] = useState<SettingsFormState>({
    title: '',
    description: '',
    provider: 'mock',
  });

  useEffect(() => {
    if (section === 'review') setInspector('review');
    if (section === 'history' || section === 'export') setInspector('history');
    if (section === 'settings') setInspector('settings');
  }, [section]);

  useEffect(() => {
    if (inspector === 'jobs') {
      void loadJobs();
    }
  }, [inspector, loadJobs]);

  useEffect(() => {
    if (inspector === 'settings' && project) {
      setSettingsForm({
        title: project.title,
        description: project.description,
        provider: String(project.settings.provider ?? 'mock'),
      });
    }
  }, [inspector, project]);

  return { inspector, setInspector, settingsForm, setSettingsForm };
}
