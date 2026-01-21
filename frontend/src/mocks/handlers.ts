import { http, HttpResponse, delay } from 'msw';
import type { CharacterDetail, CharacterSummary } from '@/shared/types/character';
import { CharactersListResponseSchema, OrchestrationStartRequestSchema } from '@/types/schemas';

const API_PREFIX = '/api';

const nowIso = () => new Date().toISOString();

const characterSummaries: CharacterSummary[] = [
  {
    id: 'aria-shadowbane',
    agent_id: 'aria-shadowbane',
    name: 'Aria Shadowbane',
    status: 'active',
    type: 'protagonist',
    updated_at: nowIso(),
    workspace_id: 'guest-workspace',
  },
  {
    id: 'merchant-aldric',
    agent_id: 'merchant-aldric',
    name: 'Merchant Aldric',
    status: 'active',
    type: 'npc',
    updated_at: nowIso(),
    workspace_id: 'guest-workspace',
  },
];

const characterDetails: CharacterDetail[] = [
  {
    agent_id: 'aria-shadowbane',
    character_id: 'aria-shadowbane',
    character_name: 'Aria Shadowbane',
    name: 'Aria Shadowbane',
    background_summary: 'A tactician navigating a fractured realm.',
    personality_traits: 'Strategic, resilient, decisive.',
    current_status: 'active',
    narrative_context: '',
    skills: { tactics: 0.8, leadership: 0.7 },
    relationships: {},
    current_location: 'Meridian Station',
    inventory: [],
    metadata: {},
    structured_data: {},
  },
  {
    agent_id: 'merchant-aldric',
    character_id: 'merchant-aldric',
    character_name: 'Merchant Aldric',
    name: 'Merchant Aldric',
    background_summary: 'A seasoned trader with a hidden agenda.',
    personality_traits: 'Connected, observant, cautious.',
    current_status: 'active',
    narrative_context: '',
    skills: { negotiation: 0.7 },
    relationships: {},
    current_location: 'Trade Hub',
    inventory: [],
    metadata: {},
    structured_data: {},
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
    const parsed = OrchestrationStartRequestSchema.safeParse(body);
    const turns = parsed.success ? parsed.data.total_turns ?? 3 : 3;

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
    return HttpResponse.json(
      CharactersListResponseSchema.parse({ characters: characterSummaries })
    );
  }),

  http.get(`${API_PREFIX}/characters/:id`, async ({ params }) => {
    await withLatency();
    const character = characterDetails.find((item) => item.character_id === params.id);
    if (!character) {
      return HttpResponse.json({ detail: 'Character not found' }, { status: 404 });
    }
    return HttpResponse.json(character);
  }),

  http.post(`${API_PREFIX}/characters`, async ({ request }) => {
    await withLatency();
    const body = await request.json().catch(() => ({}));
    const agentId = typeof body === 'object' && body !== null && 'agent_id' in body
      ? String((body as { agent_id?: string }).agent_id ?? '')
      : '';
    const name = typeof body === 'object' && body !== null && 'name' in body
      ? String((body as { name?: string }).name ?? '')
      : agentId;
    const character_id = agentId || name.toLowerCase().replace(/\s+/g, '-');
    const newCharacter: CharacterDetail = {
      agent_id: character_id,
      character_id,
      character_name: name,
      name,
      background_summary: String((body as { background_summary?: string }).background_summary ?? ''),
      personality_traits: String((body as { personality_traits?: string }).personality_traits ?? ''),
      current_status: 'active',
      narrative_context: '',
      skills: (body as { skills?: Record<string, number> }).skills ?? {},
      relationships: (body as { relationships?: Record<string, number> }).relationships ?? {},
      current_location: String((body as { current_location?: string }).current_location ?? ''),
      inventory: Array.isArray((body as { inventory?: unknown }).inventory)
        ? (body as { inventory?: string[] }).inventory ?? []
        : [],
      metadata: (body as { metadata?: Record<string, unknown> }).metadata ?? {},
      structured_data: (body as { structured_data?: Record<string, unknown> }).structured_data ?? {},
    };
    characterDetails.unshift(newCharacter);
    characterSummaries.unshift({
      id: character_id,
      agent_id: character_id,
      name,
      status: 'active',
      type: 'npc',
      updated_at: nowIso(),
      workspace_id: 'guest-workspace',
    });
    return HttpResponse.json(newCharacter, { status: 201 });
  }),

  http.put(`${API_PREFIX}/characters/:id`, async ({ params, request }) => {
    await withLatency();
    const index = characterDetails.findIndex((item) => item.character_id === params.id);
    if (index === -1) {
      return HttpResponse.json({ detail: 'Character not found' }, { status: 404 });
    }
    const body = await request.json().catch(() => ({}));
    const current = characterDetails[index];
    const updated: CharacterDetail = {
      ...current,
      name: String((body as { name?: string }).name ?? current.name),
      background_summary: String((body as { background_summary?: string }).background_summary ?? current.background_summary),
      personality_traits: String((body as { personality_traits?: string }).personality_traits ?? current.personality_traits),
      skills: (body as { skills?: Record<string, number> }).skills ?? current.skills,
      relationships: (body as { relationships?: Record<string, number> }).relationships ?? current.relationships,
      current_location: String((body as { current_location?: string }).current_location ?? current.current_location),
      inventory: Array.isArray((body as { inventory?: unknown }).inventory)
        ? (body as { inventory?: string[] }).inventory ?? current.inventory
        : current.inventory,
      metadata: (body as { metadata?: Record<string, unknown> }).metadata ?? current.metadata,
      structured_data: (body as { structured_data?: Record<string, unknown> }).structured_data ?? current.structured_data,
    };
    characterDetails[index] = updated;
    const summaryIndex = characterSummaries.findIndex((item) => item.id === params.id);
    if (summaryIndex !== -1) {
      characterSummaries[summaryIndex] = {
        ...characterSummaries[summaryIndex],
        name: updated.name,
        updated_at: nowIso(),
      };
    }
    return HttpResponse.json(updated);
  }),

  http.delete(`${API_PREFIX}/characters/:id`, async ({ params }) => {
    await withLatency();
    const index = characterDetails.findIndex((item) => item.character_id === params.id);
    if (index === -1) {
      return HttpResponse.json({ detail: 'Character not found' }, { status: 404 });
    }
    characterDetails.splice(index, 1);
    const summaryIndex = characterSummaries.findIndex((item) => item.id === params.id);
    if (summaryIndex !== -1) {
      characterSummaries.splice(summaryIndex, 1);
    }
    return HttpResponse.json({ success: true });
  }),
];
