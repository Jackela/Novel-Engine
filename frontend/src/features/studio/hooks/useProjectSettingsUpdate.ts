import type { Dispatch, FormEvent, SetStateAction } from "react";
import { useCallback, useLayoutEffect, useRef, useState } from "react";

import { api, HttpError } from "@/app/api";
import type { Project } from "@/app/types/studio";
import type { SettingsFormState } from "../studioInspectorTypes";
import { mergeProjectSettings } from "./projectState";
import { toErrorMessage } from "./toErrorMessage";

interface SettingsOwner {
  readonly projectId: string;
  readonly controllers: Set<AbortController>;
  active: boolean;
  intent: number;
  pendingFingerprint: string | null;
}

interface UseProjectSettingsUpdateOptions {
  readonly project: Project | null;
  readonly projectId: string;
  readonly settingsForm: SettingsFormState;
  readonly setProject: Dispatch<SetStateAction<Project | null>>;
  readonly setSettingsForm?: Dispatch<SetStateAction<SettingsFormState>>;
  readonly setSettingsError: Dispatch<SetStateAction<string | null>>;
  readonly onSessionLost?: () => void;
  readonly onProjectMissing?: () => void;
}

function formFromProject(project: Project): SettingsFormState {
  return {
    title: project.title,
    description: project.description,
    provider: String(project.settings.provider ?? "mock"),
  };
}

export function useProjectSettingsUpdate({
  project,
  projectId,
  settingsForm,
  setProject,
  setSettingsForm,
  setSettingsError,
  onSessionLost,
  onProjectMissing,
}: UseProjectSettingsUpdateOptions) {
  const [pendingIntent, setPendingIntent] = useState<number | null>(null);
  const ownerRef = useRef<SettingsOwner | null>(null);
  const projectRef = useRef(project);

  useLayoutEffect(() => {
    projectRef.current = project;
  }, [project]);

  useLayoutEffect(() => {
    const owner: SettingsOwner = {
      projectId,
      controllers: new Set(),
      active: true,
      intent: 0,
      pendingFingerprint: null,
    };
    ownerRef.current = owner;
    return () => {
      owner.active = false;
      owner.intent += 1;
      for (const controller of owner.controllers) controller.abort();
      owner.controllers.clear();
      if (ownerRef.current === owner) ownerRef.current = null;
    };
  }, [projectId]);

  const updateProjectSettings = useCallback(
    async (event: FormEvent) => {
      event.preventDefault();
      const owner = ownerRef.current;
      const capturedProject = projectRef.current;
      if (!owner?.active || owner.projectId !== projectId || capturedProject?.id !== projectId) {
        return;
      }

      const payload = {
        title: settingsForm.title,
        description: settingsForm.description,
        settings: { ...capturedProject.settings, provider: settingsForm.provider },
      };
      const fingerprint = JSON.stringify(payload);
      if (owner.pendingFingerprint === fingerprint) return;

      const intent = owner.intent + 1;
      owner.intent = intent;
      owner.pendingFingerprint = fingerprint;
      const controller = new AbortController();
      owner.controllers.add(controller);
      setPendingIntent(intent);
      setSettingsError(null);

      const isCurrentIntent = () =>
        owner.active &&
        ownerRef.current === owner &&
        owner.projectId === projectId &&
        owner.intent === intent;

      try {
        const updated = await api.updateProject(projectId, payload, { signal: controller.signal });
        if (!isCurrentIntent()) return;
        if (updated.id !== projectId || projectRef.current?.id !== projectId) {
          throw new Error("Invalid project settings response identity.");
        }

        const merged = mergeProjectSettings(projectRef.current, updated);
        projectRef.current = merged;
        setProject((current) =>
          isCurrentIntent() && current?.id === projectId
            ? mergeProjectSettings(current, updated)
            : current,
        );
        setSettingsForm?.(formFromProject(merged));
        setSettingsError(null);
      } catch (reason) {
        if (!isCurrentIntent()) return;
        if (reason instanceof HttpError && reason.status === 401) {
          onSessionLost?.();
          return;
        }
        if (reason instanceof HttpError && reason.status === 404) {
          onProjectMissing?.();
          return;
        }
        setSettingsError(toErrorMessage(reason, "Unable to update project."));
      } finally {
        owner.controllers.delete(controller);
        if (isCurrentIntent()) {
          owner.pendingFingerprint = null;
          setPendingIntent((current) => (current === intent ? null : current));
        }
      }
    },
    [
      onProjectMissing,
      onSessionLost,
      projectId,
      setProject,
      setSettingsError,
      setSettingsForm,
      settingsForm,
    ],
  );

  return { isUpdatingSettings: pendingIntent !== null, updateProjectSettings };
}
