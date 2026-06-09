import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { SessionCatalog, SessionState } from '@/app/types/auth';
import {
  buildSessionId,
  emptySessionCatalog,
  getActiveSession,
  readSessionCatalog,
  removeSession,
  setActiveSessionId,
  updateSessionSelection,
  upsertSession,
} from './storage';

const catalogStorageKey = 'novel-engine-session-catalog';

function makeSession(
  overrides: Partial<SessionState> & Pick<SessionState, 'kind' | 'workspaceId'>,
): SessionState {
  return {
    id: buildSessionId(overrides),
    kind: overrides.kind,
    workspaceId: overrides.workspaceId,
    user: overrides.user,
    activeWorkspace: overrides.activeWorkspace,
    lastWorkspaceId: overrides.lastWorkspaceId ?? null,
    lastJobId: overrides.lastJobId ?? null,
    lastView: overrides.lastView ?? 'workspace',
    createdAt: overrides.createdAt,
    updatedAt: overrides.updatedAt,
  };
}

describe('session storage catalog', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2024-01-02T03:04:05.000Z'));
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.useRealTimers();
    window.localStorage.clear();
  });

  it('creates empty catalogs and stable session ids', () => {
    expect(emptySessionCatalog()).toEqual({
      version: 3,
      activeSessionId: null,
      sessions: [],
    });
    expect(buildSessionId({ kind: 'guest', workspaceId: 'workspace-1' })).toBe(
      'guest:workspace-1',
    );
  });

  it('upserts active sessions and normalizes timestamps', () => {
    const catalog = emptySessionCatalog();
    const session = makeSession({
      kind: 'user',
      workspaceId: 'user-operator',
      user: {
        id: 'user-1',
        name: 'operator',
        email: 'operator@novel.engine',
      },
    });

    const nextCatalog = upsertSession(catalog, session);

    expect(nextCatalog.activeSessionId).toBe('user:user-operator');
    expect(nextCatalog.sessions[0]).toMatchObject({
      id: 'user:user-operator',
      createdAt: '2024-01-02T03:04:05.000Z',
      updatedAt: '2024-01-02T03:04:05.000Z',
      lastWorkspaceId: null,
      lastJobId: null,
      lastView: 'workspace',
    });
    expect(window.localStorage.getItem(catalogStorageKey)).toContain('user-operator');
    expect(window.localStorage.getItem(catalogStorageKey)).not.toContain('token');
  });

  it('can keep an existing active session while adding a background session', () => {
    const active = makeSession({ kind: 'guest', workspaceId: 'guest-1' });
    const catalog = upsertSession(emptySessionCatalog(), active);
    const background = makeSession({ kind: 'user', workspaceId: 'user-1' });

    const nextCatalog = upsertSession(catalog, background, { makeActive: false });

    expect(nextCatalog.activeSessionId).toBe('guest:guest-1');
    expect(nextCatalog.sessions.map((session) => session.id)).toEqual([
      'user:user-1',
      'guest:guest-1',
    ]);
  });

  it('switches active sessions and clears the active catalog pointer', () => {
    const guest = makeSession({ kind: 'guest', workspaceId: 'guest-1' });
    const user = makeSession({ kind: 'user', workspaceId: 'user-1' });
    const catalog = upsertSession(upsertSession(emptySessionCatalog(), guest), user);

    const switched = setActiveSessionId(catalog, guest.id);
    expect(getActiveSession(switched)?.workspaceId).toBe('guest-1');

    const cleared = setActiveSessionId(switched, null);
    expect(getActiveSession(cleared)).toBeNull();
    expect(readSessionCatalog().activeSessionId).toBeNull();
  });

  it('updates workspace selection metadata without losing existing fields', () => {
    const session = makeSession({
      kind: 'guest',
      workspaceId: 'guest-1',
      lastWorkspaceId: 'workspace-old',
      lastJobId: 'job-old',
      lastView: 'playback',
    });
    const catalog = upsertSession(emptySessionCatalog(), session);

    const nextCatalog = updateSessionSelection(catalog, session.id, {
      lastWorkspaceId: 'workspace-new',
      lastJobId: null,
      lastView: 'workspace',
      activeWorkspace: {
        workspaceId: 'workspace-new',
        workspaceKind: 'guest',
        label: 'The Salt Ledger',
        persistence: 'ephemeral',
        summary: 'workspace-new / 1 chapter',
      },
    });

    expect(getActiveSession(nextCatalog)).toMatchObject({
      lastWorkspaceId: 'workspace-new',
      lastJobId: null,
      lastView: 'workspace',
      activeWorkspace: {
        workspaceId: 'workspace-new',
        label: 'The Salt Ledger',
        summary: 'workspace-new / 1 chapter',
      },
    });
  });

  it('clears selection metadata when null patches are explicit', () => {
    const session = makeSession({
      kind: 'guest',
      workspaceId: 'guest-1',
      activeWorkspace: {
        workspaceId: 'workspace-old',
        workspaceKind: 'guest',
        label: 'Old Story',
        persistence: 'ephemeral',
        summary: 'workspace-old / 3 chapters',
      },
      lastWorkspaceId: 'workspace-old',
      lastJobId: 'job-old',
      lastView: 'playback',
    });
    const catalog = upsertSession(emptySessionCatalog(), session);

    const nextCatalog = updateSessionSelection(catalog, session.id, {
      lastWorkspaceId: null,
      lastJobId: null,
      lastView: 'workspace',
      activeWorkspace: null,
    });

    expect(getActiveSession(nextCatalog)).toMatchObject({
      lastWorkspaceId: null,
      lastJobId: null,
      lastView: 'workspace',
    });
    expect(getActiveSession(nextCatalog)?.activeWorkspace).toBeUndefined();
  });

  it('removes sessions and deactivates the removed active session', () => {
    const session = makeSession({ kind: 'guest', workspaceId: 'guest-1' });
    const catalog = upsertSession(emptySessionCatalog(), session);

    const nextCatalog = removeSession(catalog, session.id);

    expect(nextCatalog.sessions).toEqual([]);
    expect(nextCatalog.activeSessionId).toBeNull();
  });

  it('reads valid catalogs sorted by recency', () => {
    const stored: SessionCatalog & {
      sessions: Array<SessionState & { token?: string; refreshToken?: string }>;
    } = {
      version: 2,
      activeSessionId: 'guest:new',
      sessions: [
        makeSession({
          kind: 'guest',
          workspaceId: 'old',
          updatedAt: '2024-01-01T00:00:00.000Z',
        }),
        makeSession({
          kind: 'guest',
          workspaceId: 'new',
          updatedAt: '2024-01-03T00:00:00.000Z',
        }),
        {
          ...makeSession({
            kind: 'user',
            workspaceId: 'user-saved',
            updatedAt: '2024-01-02T00:00:00.000Z',
          }),
          token: 'stale-token',
          refreshToken: 'stale-refresh-token',
        },
      ],
    };
    window.localStorage.setItem(catalogStorageKey, JSON.stringify(stored));

    const catalog = readSessionCatalog();

    expect(catalog.sessions.map((session) => session.workspaceId)).toEqual([
      'new',
      'user-saved',
      'old',
    ]);
    expect(getActiveSession(catalog)?.workspaceId).toBe('new');
    expect(window.localStorage.getItem(catalogStorageKey)).not.toContain('stale-token');
  });

  it('falls back to an empty catalog for malformed storage', () => {
    window.localStorage.setItem(catalogStorageKey, '{not-json');

    expect(readSessionCatalog()).toEqual(emptySessionCatalog());
  });
});
