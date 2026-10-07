import { type FormEvent, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "@/app/api";
import { useTranslation } from "@/app/i18n/useTranslation";
import { useSessionExpiredRedirect } from "@/app/sessionExpiry";

import { toErrorMessage } from "./toErrorMessage";
import { useCommandFocusRestoration } from "./useCommandFocusRestoration";
import { useProjectLibraryBootstrap } from "./useProjectLibraryBootstrap";
import { useProjectLibraryDeletion } from "./useProjectLibraryDeletion";

export type LibraryOperation = "create" | "logout" | "delete";
export type LibraryCommand = LibraryOperation | "retry";

/**
 * Project-library command orchestration: the catalog bootstrap, the
 * page's single-flight command lock, and the create, sign-out, retry,
 * delete, and load-older commands the page owns. While one command
 * holds `commandRef`, every other command is refused — a slow create
 * cannot race a sign-out — and each command restores focus to its
 * trigger when it settles. Command failures publish `actionError`
 * only while the page is mounted.
 */
export function useProjectLibraryActions() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [operation, setOperation] = useState<LibraryOperation | null>(null);
  const commandRef = useRef<LibraryCommand | null>(null);
  const createButtonRef = useRef<HTMLButtonElement | null>(null);
  const headingRef = useRef<HTMLHeadingElement | null>(null);
  // DR-020: a session the server rejects returns to the entry page with the
  // library route preserved, so signing in again lands back on the catalog.
  // Sign-out below navigates deliberately and shows no expiry notice.
  const onUnauthenticated = useSessionExpiredRedirect();
  const {
    projects,
    nextCursor,
    error,
    olderError,
    isLoading,
    isLoadingOlder,
    hasLoaded,
    reload,
    loadOlder,
    mountedRef,
  } = useProjectLibraryBootstrap(onUnauthenticated);
  const runRetryWithFocusRestoration = useCommandFocusRestoration(isLoading);
  const runOperationWithFocusRestoration = useCommandFocusRestoration(operation !== null);
  const runOlderWithFocusRestoration = useCommandFocusRestoration(isLoadingOlder);

  const beginOperation = (next: LibraryOperation): boolean => {
    if (commandRef.current !== null) return false;
    commandRef.current = next;
    setOperation(next);
    setActionError(null);
    return true;
  };

  const finishOperation = () => {
    commandRef.current = null;
    if (mountedRef.current) setOperation(null);
  };

  const deletion = useProjectLibraryDeletion({
    reload,
    isMounted: mountedRef,
    beginDelete: () => beginOperation("delete"),
    finishDelete: finishOperation,
  });
  const runDeleteWithFocusRestoration = useCommandFocusRestoration(
    deletion.deletingProjectId !== null,
  );

  const retryLoad = async () => {
    if (commandRef.current !== null) return;
    commandRef.current = "retry";
    try {
      await reload();
    } finally {
      if (commandRef.current === "retry") commandRef.current = null;
    }
  };

  const createProject = async () => {
    if (!beginOperation("create")) return;
    try {
      const project = await api.createProject(title, description);
      if (mountedRef.current) {
        void navigate(`/projects/${project.id}/manuscript`);
      }
    } catch (reason) {
      if (mountedRef.current) {
        setActionError(toErrorMessage(reason, t("library.error.unableToCreate")));
      }
    } finally {
      finishOperation();
    }
  };

  const logout = async () => {
    if (!beginOperation("logout")) return;
    try {
      await api.logout();
    } catch (reason) {
      if (mountedRef.current) {
        setActionError(toErrorMessage(reason, t("library.error.unableToSignOut")));
      }
      return;
    } finally {
      finishOperation();
    }
    if (mountedRef.current) {
      // Voluntary sign-out carries no expiry state: the entry page stays quiet.
      void navigate("/");
    }
  };

  const submitProject = (event: FormEvent) => {
    event.preventDefault();
    if (commandRef.current !== null || createButtonRef.current === null) return;
    void runOperationWithFocusRestoration(createButtonRef.current, createProject);
  };

  const requestSignOut = (target: HTMLButtonElement) => {
    if (commandRef.current !== null) return;
    void runOperationWithFocusRestoration(target, logout);
  };

  const requestRetry = (target: HTMLButtonElement, heading: () => HTMLElement | null) => {
    if (commandRef.current !== null) return;
    void runRetryWithFocusRestoration(target, retryLoad, heading);
  };

  const requestDelete = (target: HTMLButtonElement, projectId: string, projectTitle: string) => {
    void runDeleteWithFocusRestoration(
      target,
      () => deletion.deleteProject(projectId, projectTitle),
      () => headingRef.current,
    );
  };

  const activateLoadOlder = (target: HTMLButtonElement) => {
    if (commandRef.current !== null) return;
    void runOlderWithFocusRestoration(target, loadOlder, () => headingRef.current);
  };

  const openProject = (projectId: string) => {
    void navigate(`/projects/${projectId}/manuscript`);
  };

  return {
    actionError,
    activateLoadOlder,
    createButtonRef,
    deletion,
    description,
    error,
    hasLoaded,
    headingRef,
    isLoading,
    isLoadingOlder,
    nextCursor,
    olderError,
    openProject,
    operation,
    projects,
    requestDelete,
    requestRetry,
    requestSignOut,
    setDescription,
    setTitle,
    submitProject,
    title,
  };
}
