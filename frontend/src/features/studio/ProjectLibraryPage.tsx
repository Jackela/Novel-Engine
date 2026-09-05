import { BookOpen, Loader2, LogOut, Plus } from "lucide-react";
import { type FormEvent, useCallback, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "@/app/api";
import { productIdentity } from "@/app/productIdentity";

import { ProjectCatalogList } from "./components/ProjectCatalogList";
import { ProjectLibraryLoadState } from "./components/ProjectLibraryLoadState";
import { toErrorMessage } from "./hooks/toErrorMessage";
import { useCommandFocusRestoration } from "./hooks/useCommandFocusRestoration";
import { useProjectLibraryBootstrap } from "./hooks/useProjectLibraryBootstrap";

type LibraryOperation = "create" | "logout";
type LibraryCommand = LibraryOperation | "retry";

export function ProjectLibraryPage() {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [operation, setOperation] = useState<LibraryOperation | null>(null);
  const commandRef = useRef<LibraryCommand | null>(null);
  const createButtonRef = useRef<HTMLButtonElement | null>(null);
  const headingRef = useRef<HTMLHeadingElement | null>(null);
  const onUnauthenticated = useCallback(() => {
    navigate("/", { replace: true });
  }, [navigate]);
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
      if (mountedRef.current) navigate(`/projects/${project.id}/manuscript`);
    } catch (reason) {
      if (mountedRef.current) {
        setActionError(toErrorMessage(reason, "Unable to create project."));
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
      if (mountedRef.current) setActionError(toErrorMessage(reason, "Unable to sign out."));
      return;
    } finally {
      finishOperation();
    }
    if (mountedRef.current) navigate("/");
  };

  const submitProject = (event: FormEvent) => {
    event.preventDefault();
    if (commandRef.current !== null || createButtonRef.current === null) return;
    void runOperationWithFocusRestoration(createButtonRef.current, createProject);
  };

  const activateLoadOlder = (target: HTMLButtonElement) => {
    if (commandRef.current !== null) return;
    void runOlderWithFocusRestoration(target, loadOlder, () => headingRef.current);
  };

  return (
    <main className="library">
      <header className="library__header">
        <div className="ui-brand">
          <BookOpen aria-hidden="true" /> {productIdentity.name}
        </div>
        <div className="library__header-actions">
          <button
            aria-busy={operation === "logout" || undefined}
            aria-label="Sign out"
            className="ui-command--icon"
            disabled={operation !== null || isLoading}
            onClick={(event) => {
              if (commandRef.current !== null) return;
              void runOperationWithFocusRestoration(event.currentTarget, logout);
            }}
            title="Sign out"
            type="button"
          >
            {operation === "logout" ? (
              <Loader2 aria-hidden="true" className="ui-spin" />
            ) : (
              <LogOut aria-hidden="true" />
            )}
          </button>
        </div>
      </header>

      <section className="library__content">
        <div className="library__heading">
          <div>
            <h1 ref={headingRef} tabIndex={-1}>
              Projects
            </h1>
            <p>Open a manuscript or start a new novel.</p>
          </div>
        </div>
        {actionError ? (
          <p aria-live="assertive" className="library__action-error ui-form-error" role="alert">
            {actionError}
          </p>
        ) : null}
        {!hasLoaded ? (
          <ProjectLibraryLoadState
            commandsLocked={operation !== null}
            error={error}
            headingRef={headingRef}
            isLoading={isLoading}
            onRetry={(target, heading) => {
              if (commandRef.current !== null) return;
              void runRetryWithFocusRestoration(target, retryLoad, heading);
            }}
          />
        ) : (
          <div className="library__grid">
            <form className="library-create" onSubmit={submitProject}>
              <div className="library-create__icon">
                <Plus aria-hidden="true" />
              </div>
              <h2>New project</h2>
              <label>
                <span>Title</span>
                <input
                  disabled={operation !== null}
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  required
                />
              </label>
              <label>
                <span>Premise</span>
                <textarea
                  value={description}
                  disabled={operation !== null}
                  onChange={(event) => setDescription(event.target.value)}
                  rows={4}
                />
              </label>
              <button
                aria-busy={operation === "create" || undefined}
                className="ui-command ui-command--primary"
                disabled={operation !== null}
                ref={createButtonRef}
                type="submit"
              >
                {operation === "create" ? <Loader2 aria-hidden="true" className="ui-spin" /> : null}
                {operation === "create" ? "Creating project..." : "Create project"}
              </button>
            </form>
            <ProjectCatalogList
              disabled={operation !== null || isLoadingOlder}
              hasOlderProjects={nextCursor !== null}
              isLoadingOlder={isLoadingOlder}
              olderError={olderError}
              onActivateOlder={activateLoadOlder}
              onOpenProject={(projectId) => navigate(`/projects/${projectId}/manuscript`)}
              projects={projects}
            />
          </div>
        )}
      </section>
    </main>
  );
}
