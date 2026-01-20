import { http, HttpResponse, delay } from 'msw';
import type { Character, CharacterStats } from '@/shared/types/character';

const API_PREFIX = '/api';

const baseStats: CharacterStats = {
  strength: 10,
  intelligence: 10,
  charisma: 10,
  agility: 10,
  wisdom: 10,
  luck: 10,
};

const createId = (prefix: string) => {
  if (globalThis.crypto && typeof globalThis.crypto.randomUUID === 'function') {
    return `${prefix}_${globalThis.crypto.randomUUID()}`;
  }
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
};

const nowIso = () => new Date().toISOString();

const characters: Character[] = [
  {
    id: 'char-001',
    name: 'Aria Shadowbane',
    description: 'A tactician navigating a fractured realm.',
    role: 'protagonist',
    traits: ['strategic', 'resilient'],
    stats: { ...baseStats, wisdom: 14, charisma: 12 },
    relationships: [],
    createdAt: nowIso(),
    updatedAt: nowIso(),
  },
  {
    id: 'char-002',
    name: 'Merchant Aldric',
    description: 'A seasoned trader with a hidden agenda.',
    role: 'npc',
    traits: ['connected', 'observant'],
    stats: { ...baseStats, intelligence: 13 },
    relationships: [],
    createdAt: nowIso(),
    updatedAt: nowIso(),
  },
];

let orchestrationState = {
  status: 'idle',
  current_turn: 0,
  total_turns: 0,
  queue_length: 0,
  average_processing_time: 0,
  steps: [] as Array<{ id: string; name: string; status: string; progress: number }>,
};

const orchestrationSteps = [
  { id: 'context_gathering', name: 'Context Gathering' },
  { id: 'planning', name: 'Planning' },
  { id: 'execution', name: 'Execution' },
  { id: 'synthesis', name: 'Synthesis' },
  { id: 'output', name: 'Output' },
];

const withLatency = async () => {
  await delay(120);
};

export const handlers = [
  http.post(`${API_PREFIX}/auth/login`, async ({ request }) => {
    await withLatency();
    const body = await request.json().catch(() => ({}));
    const username = typeof body === 'object' && body !== null && 'username' in body
      ? String((body as { username?: string }).username)
      : 'operator';

    return HttpResponse.json({
      access_token: 'mock-access-token',
      refresh_token: 'mock-refresh-token',
      token_type: 'Bearer',
      expires_in: 3600,
      refresh_expires_in: 86400,
      user: {
        id: 'user-001',
        username,
        email: `${username}@novel.engine`,
        roles: ['operator'],
      },
    });
  }),

  http.post(`${API_PREFIX}/auth/logout`, async () => {
    await withLatency();
    return HttpResponse.json({ success: true });
  }),

  http.post(`${API_PREFIX}/auth/refresh`, async () => {
    await withLatency();
    return HttpResponse.json({
      access_token: 'mock-access-token',
      refresh_token: 'mock-refresh-token',
      token_type: 'Bearer',
      expires_in: 3600,
      refresh_expires_in: 86400,
      user: {
        id: 'user-001',
        username: 'operator',
        email: 'operator@novel.engine',
        roles: ['operator'],
      },
    });
  }),

  http.post(`${API_PREFIX}/guest/sessions`, async () => {
    await withLatency();
    return HttpResponse.json({ workspace_id: 'guest-workspace' });
  }),

  http.get(`${API_PREFIX}/orchestration/status`, async () => {
    await withLatency();
    return HttpResponse.json({ success: true, data: orchestrationState });
  }),

  http.post(`${API_PREFIX}/orchestration/start`, async ({ request }) => {
    await withLatency();
    const body = await request.json().catch(() => ({}));
    const turns = typeof body === 'object' && body !== null && 'total_turns' in body
      ? Number((body as { total_turns?: number }).total_turns ?? 3)
      : 3;

    orchestrationState = {
      status: 'running',
      current_turn: orchestrationState.current_turn + 1,
      total_turns: turns,
      queue_length: 0,
      average_processing_time: 2.4,
      steps: orchestrationSteps.map((step, index) => ({
        id: step.id,
        name: step.name,
        status: index === 0 ? 'processing' : 'queued',
        progress: index === 0 ? 25 : 0,
      })),
    };

    return HttpResponse.json({ success: true, data: orchestrationState });
  }),

  http.post(`${API_PREFIX}/orchestration/pause`, async () => {
    await withLatency();
    orchestrationState = { ...orchestrationState, status: 'paused' };
    return HttpResponse.json({ success: true, data: orchestrationState });
  }),

  http.post(`${API_PREFIX}/orchestration/stop`, async () => {
    await withLatency();
    orchestrationState = { ...orchestrationState, status: 'idle', steps: [] };
    return HttpResponse.json({ success: true, data: orchestrationState });
  }),

  http.get(`${API_PREFIX}/orchestration/narrative`, async () => {
    await withLatency();
    return HttpResponse.json({
      success: true,
      data: {
        story: 'Mock narrative output generated for Weaver sessions.',
        participants: characters.map((character) => character.name),
        turns_completed: orchestrationState.current_turn,
        last_generated: nowIso(),
        has_content: true,
      },
    });
  }),

  http.get(`${API_PREFIX}/characters`, async () => {
    await withLatency();
    return HttpResponse.json(characters);
  }),

  http.get(`${API_PREFIX}/characters/:id`, async ({ params }) => {
    await withLatency();
    const character = characters.find((item) => item.id === params.id);
    if (!character) {
      return HttpResponse.json({ detail: 'Character not found' }, { status: 404 });
    }
    return HttpResponse.json(character);
  }),

  http.post(`${API_PREFIX}/characters`, async ({ request }) => {
    await withLatency();
    const body = await request.json();
    const createdAt = nowIso();
    const newCharacter: Character = {
      id: createId('char'),
      name: String(body.name ?? 'New Character'),
      description: String(body.description ?? ''),
      role: (body.role ?? 'supporting') as Character['role'],
      traits: Array.isArray(body.traits) ? body.traits : [],
      stats: { ...baseStats, ...(body.stats ?? {}) },
      relationships: [],
      createdAt,
      updatedAt: createdAt,
    };
    characters.unshift(newCharacter);
    return HttpResponse.json(newCharacter, { status: 201 });
  }),

  http.put(`${API_PREFIX}/characters/:id`, async ({ params, request }) => {
    await withLatency();
    const index = characters.findIndex((item) => item.id === params.id);
    if (index === -1) {
      return HttpResponse.json({ detail: 'Character not found' }, { status: 404 });
    }
    const body = await request.json();
    const updated: Character = {
      ...characters[index],
      ...body,
      traits: Array.isArray(body.traits) ? body.traits : characters[index].traits,
      stats: { ...characters[index].stats, ...(body.stats ?? {}) },
      updatedAt: nowIso(),
    };
    characters[index] = updated;
    return HttpResponse.json(updated);
  }),

  http.delete(`${API_PREFIX}/characters/:id`, async ({ params }) => {
    await withLatency();
    const index = characters.findIndex((item) => item.id === params.id);
    if (index === -1) {
      return HttpResponse.json({ detail: 'Character not found' }, { status: 404 });
    }
    characters.splice(index, 1);
    return HttpResponse.json({ success: true });
  }),
];
