import type { Page } from '@playwright/test';

type MockCharacter = {
  id: string;
  name: string;
  role?: string;
  status?: string;
};

const DEFAULT_CHARACTERS: MockCharacter[] = [
  { id: 'astra', name: 'Astra Vale', role: 'protagonist', status: 'active' },
  { id: 'morrow', name: 'Morrow Kade', role: 'operative', status: 'active' },
  { id: 'lyra', name: 'Lyra Quill', role: 'analyst', status: 'inactive' },
];

const DEFAULT_PIPELINE_STEPS = [
  { id: 'world_update', name: 'World Update' },
  { id: 'subjective_brief', name: 'Subjective Brief' },
  { id: 'interaction_orchestration', name: 'Interaction Orchestration' },
  { id: 'event_integration', name: 'Event Integration' },
  { id: 'narrative_integration', name: 'Narrative Integration' },
];

export const mockDecisionApi = async (page: Page) => {
  await page.route(/\/api\/decision\/status/, async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ success: true, data: { pause_state: 'running' } }),
    });
  });
  await page.route(/\/api\/decision\/respond/, async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ success: true, message: 'ok', data: { needs_negotiation: false } }),
    });
  });
  await page.route(/\/api\/decision\/confirm/, async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ success: true }),
    });
  });
  await page.route(/\/api\/decision\/skip/, async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ success: true }),
    });
  });
  await page.route(/\/api\/decision\/history/, async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ success: true, data: { total_decisions: 0 } }),
    });
  });
};

export const mockDashboardApi = async (page: Page, options: { characters?: MockCharacter[] } = {}) => {
  const baseCharacters = options.characters ?? DEFAULT_CHARACTERS;
  const nowIso = new Date().toISOString();
  const characters = [...baseCharacters];

  let orchestrationState = {
    status: 'idle',
    current_turn: 0,
    total_turns: 0,
    queue_length: 0,
    average_processing_time: 0,
    steps: [] as Array<{ id: string; name: string; status: string; progress: number }>,
  };

  await page.route(
    (url) => /\/meta\/system-status(\/|\?|$)/.test(url.pathname),
    async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'operational',
          uptime: 1234,
          version: '1.0.0',
          components: { api: 'online', simulation: 'running', cache: 'available' },
        }),
      });
    }
  );

  await page.route(
    (url) => /\/health(\/|\?|$)/.test(url.pathname),
    async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'ok',
          timestamp: new Date().toISOString(),
          environment: 'test',
          version: '1.0.0',
          config: {
            simulation_turns: 3,
            max_agents: 5,
            api_timeout: 30000,
          },
        }),
      });
    }
  );

  await page.route(/\/api\/cache\/metrics/, async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        cache_hits: 12,
        cache_misses: 2,
        cache_size: 512,
        cache_max_size: 2048,
        evictions: 0,
        hit_rate: 0.86,
      }),
    });
  });

  await page.route(/\/api\/analytics\/metrics/, async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        data: {
          story_quality: 78,
          engagement: 72,
          coherence: 84,
          complexity: 67,
          data_points: 120,
          metrics_tracked: 6,
          status: 'active',
          last_updated: new Date().toISOString(),
        },
      }),
    });
  });

  await page.route(/\/api\/orchestration\/status/, async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        data: orchestrationState,
      }),
    });
  });

  await page.route(/\/api\/orchestration\/start/, async route => {
    orchestrationState = {
      status: 'running',
      current_turn: orchestrationState.current_turn + 1,
      total_turns: 3,
      queue_length: 0,
      average_processing_time: 2.4,
      steps: DEFAULT_PIPELINE_STEPS.map((step, index) => ({
        id: step.id,
        name: step.name,
        status: index === 0 ? 'processing' : 'queued',
        progress: index === 0 ? 25 : 0,
      })),
    };

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        data: orchestrationState,
      }),
    });
  });

  await page.route(/\/api\/orchestration\/pause/, async route => {
    orchestrationState.status = 'paused';
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ success: true, data: orchestrationState }),
    });
  });

  await page.route(/\/api\/orchestration\/stop/, async route => {
    orchestrationState.status = 'idle';
    orchestrationState.steps = [];
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ success: true, data: orchestrationState }),
    });
  });

  await page.route(/\/api\/orchestration\/narrative/, async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        data: {
          story: 'Mock narrative output for test runs.',
          participants: characters.map((character) => character.name),
          turns_completed: orchestrationState.current_turn,
          last_generated: new Date().toISOString(),
          has_content: true,
        },
      }),
    });
  });

  await page.route(/\/api\/events\/stream/, async route => {
    await route.fulfill({
      status: 200,
      contentType: 'text/event-stream',
      body: ': keep-alive\n\n',
    });
  });

  const toCharacterSummary = (character: MockCharacter) => ({
    id: character.id,
    agent_id: character.id,
    name: character.name,
    status: character.status ?? 'active',
    type: character.role ?? 'npc',
    updated_at: nowIso,
    workspace_id: null,
  });

  const buildCharacterDetail = (character: MockCharacter) => ({
    agent_id: character.id,
    character_id: character.id,
    character_name: character.name,
    name: character.name,
    background_summary: 'Mock character profile.',
    personality_traits: 'Focused and resilient.',
    current_status: character.status ?? 'active',
    narrative_context: 'Operative assigned to test scenarios.',
    skills: {},
    relationships: {},
    current_location: '',
    inventory: [],
    metadata: {},
    structured_data: {},
  });

  await page.route(/\/api\/characters(\/|\?|$)/, async route => {
    if (route.request().method() === 'POST') {
      const payload = (await route.request().postDataJSON()) as {
        agent_id?: string;
        name?: string;
      };
      const characterId = payload.agent_id ?? `character-${Date.now()}`;
      const characterName = payload.name ?? characterId;
      const created = { id: characterId, name: characterName, status: 'active' };
      characters.unshift(created);
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify(buildCharacterDetail(created)),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        characters: characters.map((character) => toCharacterSummary(character)),
      }),
    });
  });

  await page.route(/\/api\/characters\/[^/]+/, async route => {
    const url = new URL(route.request().url());
    const characterId = decodeURIComponent(url.pathname.split('/').pop() || 'unknown');
    const fallback = characters.find((character) => character.id === characterId);
    const fallbackCharacter = fallback ?? { id: characterId, name: characterId, status: 'active' };
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(buildCharacterDetail(fallbackCharacter)),
    });
  });
};

export const mockEventSource = async (page: Page) => {
  await page.addInitScript(() => {
    class MockEventSource extends EventTarget {
      url: string;
      readyState = 0;
      CONNECTING = 0;
      OPEN = 1;
      CLOSED = 2;
      onmessage: ((event: MessageEvent) => void) | null = null;
      onopen: ((event: Event) => void) | null = null;
      onerror: ((event: Event) => void) | null = null;

      constructor(url: string) {
        super();
        this.url = url;
        this.readyState = this.CONNECTING;

        setTimeout(() => {
          this.readyState = this.OPEN;
          const openEvent = new Event('open');
          this.onopen?.(openEvent);
          this.dispatchEvent(openEvent);
        }, 10);
      }

      close() {
        this.readyState = this.CLOSED;
      }
    }

    (window as any).EventSource = MockEventSource;
  });
};
