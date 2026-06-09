type SessionKind = 'guest' | 'user';
type WorkspaceKind = 'guest' | 'user' | 'unknown';
type WorkspacePersistence = 'ephemeral' | 'persistent' | 'unknown';
export type WorkspaceSurfaceView = 'workspace' | 'playback';

interface SessionUser {
  id: string;
  name: string;
  email?: string;
}

export interface ActiveWorkspaceSummary {
  workspaceId: string;
  workspaceKind: WorkspaceKind;
  label: string;
  persistence: WorkspacePersistence;
  summary: string;
}

export interface SessionState {
  id: string;
  kind: SessionKind;
  workspaceId: string;
  user?: SessionUser;
  identityKind?: SessionKind;
  activeWorkspace?: ActiveWorkspaceSummary;
  lastWorkspaceId?: string | null;
  lastJobId?: string | null;
  lastView?: WorkspaceSurfaceView;
  createdAt?: string;
  updatedAt?: string;
}

export interface SessionCatalog {
  version: number;
  activeSessionId: string | null;
  sessions: SessionState[];
}

export interface SessionSelectionUpdate {
  lastWorkspaceId?: string | null;
  lastJobId?: string | null;
  lastView?: WorkspaceSurfaceView;
  activeWorkspace?: ActiveWorkspaceSummary | null;
}

interface ActiveWorkspaceResponsePayload {
  workspace_id: string;
  workspace_kind: WorkspaceKind;
  label: string;
  persistence: WorkspacePersistence;
  summary: string;
}

export interface GuestSessionRequest {
  workspace_id?: string | null;
}

export interface GuestSessionResponse {
  workspace_id: string;
  created?: boolean;
  identity_kind?: SessionKind;
  workspace_kind?: WorkspaceKind;
  active_workspace?: ActiveWorkspaceResponsePayload;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  workspace_id: string;
  identity_kind?: SessionKind;
  workspace_kind?: WorkspaceKind;
  active_workspace?: ActiveWorkspaceResponsePayload;
  user: SessionUser;
}

export interface CurrentUserResponse {
  id: string;
  username: string;
  email: string;
  roles: string[];
  workspace_id: string;
  identity_kind?: SessionKind;
  workspace_kind?: WorkspaceKind;
  active_workspace?: ActiveWorkspaceResponsePayload;
}
