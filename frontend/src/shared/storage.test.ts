import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { SessionCatalog, SessionState } from '@/app/types/auth';
import {
  buildSessionId,
  emptySessionCatalog,
  getActiveSession,
  readSessionCatalog,
  removeSession,
  sessionStorageKey,
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
    token: overrides.token,
    refreshToken: overrides.refreshToken,
    user: overrides.user,
    lastStoryId: overrides.lastStoryId ?? null,
    lastRunId: overrides.lastRunId ?? null,
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
      version: 2,
      activeSessionId: null,
      sessions: [],
    });
    expect(buildSessionId({ kind: 'guest', workspaceId: 'workspace-1' })).toBe(
      'guest:workspace-1',
    );
  });

  it('upserts active sessions, normalizes timestamps, and writes the legacy slot', () => {
    const catalog = emptySessionCatalog();
    const session = makeSession({
      kind: 'user',
      workspaceId: 'user-operator',
      token: 'access-token',
      refreshToken: 'refresh-token',
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
      lastStoryId: null,
      lastRunId: null,
      lastView: 'workspace',
    });
    expect(JSON.parse(window.localStorage.getItem(sessionStorageKey) ?? '{}')).toMatchObject({
      kind: 'user',
      workspaceId: 'user-operator',
      token: 'access-token',
      refreshToken: 'refresh-token',
    });
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

  it('switches active sessions and clears the legacy slot when no session is active', () => {
    const guest = makeSession({ kind: 'guest', workspaceId: 'guest-1' });
    const user = makeSession({ kind: 'user', workspaceId: 'user-1', token: 'token' });
    const catalog = upsertSession(upsertSession(emptySessionCatalog(), guest), user);

    const switched = setActiveSessionId(catalog, guest.id);
    expect(getActiveSession(switched)?.workspaceId).toBe('guest-1');

    const cleared = setActiveSessionId(switched, null);
    expect(getActiveSession(cleared)).toBeNull();
    expect(window.localStorage.getItem(sessionStorageKey)).toBeNull();
  });

  it('updates story selection metadata without losing existing fields', () => {
    const session = makeSession({
      kind: 'guest',
      workspaceId: 'guest-1',
      lastStoryId: 'story-old',
      lastRunId: 'run-old',
      lastView: 'playback',
    });
    const catalog = upsertSession(emptySessionCatalog(), session);

    const nextCatalog = updateSessionSelection(catalog, session.id, {
      lastStoryId: 'story-new',
      lastRunId: null,
      lastView: 'workspace',
    });

    expect(getActiveSession(nextCatalog)).toMatchObject({
      lastStoryId: 'story-new',
      lastRunId: null,
      lastView: 'workspace',
    });
  });

  it('removes sessions and deactivates the removed active session', () => {
    const session = makeSession({ kind: 'guest', workspaceId: 'guest-1' });
    const catalog = upsertSession(emptySessionCatalog(), session);

    const nextCatalog = removeSession(catalog, session.id);

    expect(nextCatalog.sessions).toEqual([]);
    expect(nextCatalog.activeSessionId).toBeNull();
    expect(window.localStorage.getItem(sessionStorageKey)).toBeNull();
  });

  it('reads valid catalogs sorted by recency', () => {
    const stored: SessionCatalog = {
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
      ],
    };
    window.localStorage.setItem(catalogStorageKey, JSON.stringify(stored));

    const catalog = readSessionCatalog();

    expect(catalog.sessions.map((session) => session.workspaceId)).toEqual(['new', 'old']);
    expect(getActiveSession(catalog)?.workspaceId).toBe('new');
  });

  it('migrates the legacy session slot when the catalog is absent', () => {
    window.localStorage.setItem(
      sessionStorageKey,
      JSON.stringify({
        kind: 'guest',
        workspaceId: 'legacy-guest',
      }),
    );

    const catalog = readSessionCatalog();

    expect(catalog.activeSessionId).toBe('guest:legacy-guest');
    expect(catalog.sessions[0]).toMatchObject({
      id: 'guest:legacy-guest',
      workspaceId: 'legacy-guest',
    });
    expect(window.localStorage.getItem(catalogStorageKey)).toContain('legacy-guest');
  });

  it('falls back to an empty catalog for malformed storage', () => {
    window.localStorage.setItem(catalogStorageKey, '{not-json');
    window.localStorage.setItem(sessionStorageKey, JSON.stringify({ kind: 'guest' }));

    expect(readSessionCatalog()).toEqual(emptySessionCatalog());
  });
});
