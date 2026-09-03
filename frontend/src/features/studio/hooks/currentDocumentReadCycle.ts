import { api, HttpError } from "@/app/api";
import type { DocumentSummary, ProjectShell, StudioDocument } from "@/app/types/studio";

import type { CurrentDocumentReadKey } from "./currentDocumentReadRegistry";
import type { ProjectShellReadAuthority } from "./projectShellReadAuthority";
import { reportUnexpectedError } from "./reportUnexpectedError";
import { toErrorMessage } from "./toErrorMessage";

const DEFAULT_ERROR = "Unable to load this document. Please retry.";
const CHURN_ERROR = "This document changed again while loading. Please retry.";
const INCONSISTENT_ERROR = "This document is listed but could not be loaded. Please retry.";

export type CommitShellResult = "published" | "superseded" | "unexpected";
type CommitShell = () => CommitShellResult;

export type CurrentDocumentReadOutcome =
  | {
      readonly status: "document";
      readonly key: CurrentDocumentReadKey;
      readonly document: StudioDocument;
      readonly commitShell?: CommitShell;
    }
  | { readonly status: "missing"; readonly commitShell: CommitShell }
  | { readonly status: "session-lost"; readonly commitShell?: CommitShell }
  | { readonly status: "project-missing" }
  | { readonly status: "unexpected" }
  | {
      readonly status: "failure";
      readonly message: string;
      readonly key?: CurrentDocumentReadKey;
      readonly commitShell?: CommitShell;
    };

type TerminalReadOutcome = Extract<
  CurrentDocumentReadOutcome,
  | { readonly status: "session-lost" }
  | { readonly status: "project-missing" }
  | { readonly status: "failure" }
  | { readonly status: "unexpected" }
>;

type ShellReadOutcome =
  | { readonly status: "shell"; readonly shell: ProjectShell; readonly commitShell: CommitShell }
  | TerminalReadOutcome;

function summaryIn(
  shell: ProjectShell,
  projectId: string,
  documentId: string,
): DocumentSummary | null {
  if (shell.id !== projectId) return null;
  const summary = shell.documents.find((document) => document.id === documentId) ?? null;
  return summary?.project_id === projectId ? summary : null;
}

function validIdentity(document: StudioDocument, key: CurrentDocumentReadKey): boolean {
  return document.project_id === key.projectId && document.id === key.documentId;
}

function classifyFailure(
  reason: unknown,
  commitShell?: CommitShell,
  key?: CurrentDocumentReadKey,
): Extract<CurrentDocumentReadOutcome, { readonly status: "session-lost" | "failure" }> {
  if (reason instanceof HttpError && reason.status === 401)
    return { status: "session-lost", commitShell };
  return { status: "failure", message: toErrorMessage(reason, DEFAULT_ERROR), commitShell, key };
}

async function refreshShell(
  key: CurrentDocumentReadKey,
  authority: ProjectShellReadAuthority,
  signal: AbortSignal,
): Promise<ShellReadOutcome> {
  const capture = authority.captureProjectShellRead();
  try {
    const shell = await api.project(key.projectId, { signal });
    let result: CommitShellResult | undefined;
    const commitShell = () => {
      if (result) return result;
      try {
        result = authority.publishProjectShellRead(capture, shell) ? "published" : "superseded";
      } catch (reason) {
        reportUnexpectedError("Unexpected current-document shell publication failure.", reason);
        result = "unexpected";
      }
      return result;
    };
    return { status: "shell", shell, commitShell };
  } catch (reason) {
    if (reason instanceof HttpError && reason.status === 401) return { status: "session-lost" };
    if (reason instanceof HttpError && reason.status === 404) return { status: "project-missing" };
    return classifyFailure(reason);
  }
}

async function convergeAfterRead(
  key: CurrentDocumentReadKey,
  document: StudioDocument | null,
  authority: ProjectShellReadAuthority,
  signal: AbortSignal,
): Promise<CurrentDocumentReadOutcome> {
  const refreshed = await refreshShell(key, authority, signal);
  if (refreshed.status !== "shell") return refreshed;
  const freshSummary = summaryIn(refreshed.shell, key.projectId, key.documentId);
  if (!freshSummary) return { status: "missing", commitShell: refreshed.commitShell };
  if (document === null)
    return {
      status: "failure",
      message: INCONSISTENT_ERROR,
      key: { ...key, expectedRevisionId: freshSummary.current_revision_id },
      commitShell: refreshed.commitShell,
    };

  const freshKey = { ...key, expectedRevisionId: freshSummary.current_revision_id };
  if (document.current_revision_id === freshKey.expectedRevisionId)
    return { status: "document", key: freshKey, document, commitShell: refreshed.commitShell };

  try {
    const replacement = await api.document(key.projectId, key.documentId, { signal });
    if (!validIdentity(replacement, freshKey))
      return {
        status: "failure",
        message: INCONSISTENT_ERROR,
        key: freshKey,
        commitShell: refreshed.commitShell,
      };
    if (replacement.current_revision_id !== freshKey.expectedRevisionId)
      return {
        status: "failure",
        message: CHURN_ERROR,
        key: freshKey,
        commitShell: refreshed.commitShell,
      };
    return {
      status: "document",
      key: freshKey,
      document: replacement,
      commitShell: refreshed.commitShell,
    };
  } catch (reason) {
    if (reason instanceof HttpError && reason.status === 404)
      return {
        status: "failure",
        message: INCONSISTENT_ERROR,
        key: freshKey,
        commitShell: refreshed.commitShell,
      };
    return classifyFailure(reason, refreshed.commitShell, freshKey);
  }
}

export async function runCurrentDocumentReadCycle(
  key: CurrentDocumentReadKey,
  authority: ProjectShellReadAuthority,
  signal: AbortSignal,
): Promise<CurrentDocumentReadOutcome> {
  try {
    const document = await api.document(key.projectId, key.documentId, { signal });
    if (!validIdentity(document, key)) return { status: "failure", message: INCONSISTENT_ERROR };
    if (document.current_revision_id === key.expectedRevisionId)
      return { status: "document", key, document };
    return convergeAfterRead(key, document, authority, signal);
  } catch (reason) {
    if (reason instanceof HttpError && reason.status === 404)
      return convergeAfterRead(key, null, authority, signal);
    return classifyFailure(reason);
  }
}
