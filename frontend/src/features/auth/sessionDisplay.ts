import type { SessionState } from '@/app/types/auth';

export function sessionDisplayTitle(session: SessionState): string {
  if (session.activeWorkspace?.label) {
    return session.activeWorkspace.label;
  }

  if (session.kind === 'user') {
    return session.user?.name ?? 'Signed-in author';
  }

  return 'Guest workspace';
}

export function sessionDisplayMeta(session: SessionState): string {
  const workspaceMeta =
    session.activeWorkspace?.summary ??
    session.lastWorkspaceId ??
    session.workspaceId;

  if (session.user?.email) {
    return `${session.user.email} / ${workspaceMeta}`;
  }

  return workspaceMeta;
}
