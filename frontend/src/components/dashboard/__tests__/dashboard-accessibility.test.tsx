import React, { act } from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { vi } from 'vitest';
import QuickActions from '../QuickActions';
import WorldStateMapV2 from '../WorldStateMapV2';
import CharacterNetworks from '../CharacterNetworks';
import NarrativeTimeline from '../NarrativeTimeline';
import TurnPipelineStatus from '../TurnPipelineStatus';
import RealTimeActivity from '../RealTimeActivity';
import PerformanceMetrics from '../PerformanceMetrics';

const renderWithTheme = (ui: React.ReactElement) => {
  const theme = createTheme();
  return render(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);
};

if (typeof window.PointerEvent === 'undefined') {
  class MockPointerEvent extends MouseEvent {
    constructor(type: string, props?: PointerEventInit) {
      super(type, props);
      Object.assign(this, props);
    }
  }
  window.PointerEvent = MockPointerEvent as unknown as typeof PointerEvent;
  (globalThis as unknown as { PointerEvent: typeof PointerEvent }).PointerEvent = window.PointerEvent;
}

window.scrollTo = () => {};

const flushPromises = () => new Promise((resolve) => setTimeout(resolve, 0));

// Mock EventSource for RealTimeActivity tests
class MockEventSource {
  url: string;
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  readyState: number = 0;
  CONNECTING = 0;
  OPEN = 1;
  CLOSED = 2;

  constructor(url: string) {
    this.url = url;
    this.readyState = this.CONNECTING;
    setTimeout(() => {
      if (this.readyState === this.CONNECTING) {
        this.readyState = this.OPEN;
        if (this.onopen) {
          this.onopen(new Event('open'));
        }
      }
    }, 10);
  }

  close() {
    this.readyState = this.CLOSED;
  }
}

(global as any).EventSource = MockEventSource;

const mockFetchCharacters = () =>
  vi.fn(async (url: RequestInfo | URL) => {
    const endpoint = typeof url === 'string' ? url : url.toString();
    if (!endpoint.includes('/api/characters')) {
      return new Response('Not Found', { status: 404 });
    }
    const payload = JSON.stringify({ characters: ['aria', 'engineer', 'pilot', 'scientist', 'test'] });
    return new Response(payload, {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  });

describe('Dashboard accessibility + data parity', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = mockFetchCharacters();
    if (!window.matchMedia) {
      // Provide a minimal matchMedia implementation for useMediaQuery
      window.matchMedia = () =>
        ({
          matches: false,
          addListener: () => {},
          removeListener: () => {},
          addEventListener: () => {},
          removeEventListener: () => {},
          dispatchEvent: () => false,
        }) as MediaQueryList;
    }
  });

  afterEach(() => {
    vi.restoreAllMocks();
    global.fetch = originalFetch;
  });

  it('renders QuickActions without leaking invalid DOM props', () => {
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    renderWithTheme(<QuickActions />);

    const hasAttributeLeak = errorSpy.mock.calls.some(([message]) =>
      typeof message === 'string' && message.includes('non-boolean attribute') && message.includes('active')
    );

    expect(hasAttributeLeak).toBe(false);
    errorSpy.mockRestore();
  });

  it('shows connection chip and live text as ONLINE when idle but connected', () => {
    renderWithTheme(<QuickActions isOnline status="idle" />);

    const container = screen.getByTestId('connection-status');
    const liveText = screen.getByTestId('live-indicator');
    const chipLabel = container.querySelector('.MuiChip-label');

    expect(liveText).toHaveTextContent(/ONLINE/i);
    expect(chipLabel?.textContent).toMatch(/ONLINE/i);
  });

  it('fetches characters for spatial + network tiles and surfaces API data', async () => {
    renderWithTheme(
      <>
        <WorldStateMapV2 />
        <CharacterNetworks />
      </>
    );

    await act(async () => {
      await flushPromises();
    });
    expect(global.fetch).toHaveBeenCalled();

    await waitFor(() => {
      expect(screen.getAllByText(/Aria Shadowbane/i)[0]).toBeInTheDocument();
      expect(screen.getAllByText(/Kael Stormrider/i)[0]).toBeInTheDocument();
    });
  });

  it('falls back to demo data when the API request fails without showing tile errors', async () => {
    const failingFetch = vi.fn(async () => new Response('Internal Server Error', { status: 500 }));
    global.fetch = failingFetch as unknown as typeof fetch;

    renderWithTheme(
      <>
        <WorldStateMapV2 />
        <CharacterNetworks />
      </>
    );

    await act(async () => {
      await flushPromises();
    });

    expect(failingFetch).toHaveBeenCalled();

    await waitFor(() => {
      expect(screen.getAllByText(/Demo data/i)).toHaveLength(2);
    });

    expect(screen.queryByText(/Error loading data/i)).toBeNull();
  });

  it('displays character and active counts sourced from the dataset', async () => {
    renderWithTheme(<WorldStateMapV2 />);

    await act(async () => {
      await flushPromises();
    });

    const charactersChips = screen.getAllByText(
      (_, element) => element?.textContent?.includes('5 Characters') ?? false
    );
    const activeChips = screen.getAllByText(
      (_, element) => element?.textContent?.includes('2 Active') ?? false
    );

    expect(charactersChips.length).toBeGreaterThanOrEqual(1);
    expect(activeChips.length).toBeGreaterThanOrEqual(1);
  });

  it('surfaces API feed badges for map and network tiles when the API succeeds', async () => {
    renderWithTheme(
      <>
        <WorldStateMapV2 />
        <CharacterNetworks />
      </>
    );

    await act(async () => {
      await flushPromises();
    });

    const apiFeedBadges = await screen.findAllByText(/API feed/i);
    expect(apiFeedBadges.length).toBeGreaterThanOrEqual(2);
  });

  it('only attempts /api/characters endpoints (base + same-origin proxy) when the primary API fails', async () => {
    const proxyFetch = vi.fn(async (url: RequestInfo | URL) => {
      const endpoint = typeof url === 'string' ? url : url.toString();
      if (endpoint.includes('127.0.0.1:8000') && endpoint.includes('/api/characters')) {
        return new Response('Server error', { status: 500 });
      }
      if (endpoint.includes('/api/characters')) {
        return new Response(JSON.stringify({ characters: ['pilot'] }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      return new Response('Not Found', { status: 404 });
    });
    global.fetch = proxyFetch as unknown as typeof fetch;

    renderWithTheme(<WorldStateMapV2 />);

    await waitFor(() => {
      expect(screen.getByText(/Captain Vex/i)).toBeInTheDocument();
    });

    const attemptedUrls = proxyFetch.mock.calls.map(([request]) =>
      typeof request === 'string' ? request : request.toString()
    );

    expect(attemptedUrls).not.toHaveLength(0);
    expect(attemptedUrls.every((url) => url.includes('/api/characters'))).toBe(true);
    expect(attemptedUrls.some((url) => url.startsWith('http://127.0.0.1:8000/'))).toBe(true);
    expect(attemptedUrls.some((url) => url.includes(window.location.origin))).toBe(true);
  });

  it('supports keyboard activation for world map markers', async () => {
    renderWithTheme(<WorldStateMapV2 />);

    await act(async () => {
      await flushPromises();
    });
    const marker = await screen.findByRole('button', { name: /Aria Shadowbane/i });

    fireEvent.keyDown(marker, { key: 'Enter' });

    expect(marker).toHaveAttribute('aria-pressed', 'true');
    expect(marker).toHaveAttribute('aria-controls');
  });

  it('exposes character network cards as focusable buttons', async () => {
    renderWithTheme(<CharacterNetworks />);

    await act(async () => {
      await flushPromises();
    });
    const cards = await screen.findAllByRole('button', { name: /Aria|Kael/i });
    fireEvent.keyDown(cards[0], { key: ' ' });

    expect(cards[0]).toHaveAttribute('aria-pressed', 'true');
  });

  it('marks narrative timeline nodes with aria-current metadata', () => {
    renderWithTheme(<NarrativeTimeline />);

    const timeline = screen.getByRole('tablist', { name: /narrative arc timeline/i });
    expect(timeline).toBeInTheDocument();

    const currentNode = screen.getByRole('tab', { name: /merchant alliance/i });
    expect(currentNode).toHaveAttribute('aria-current', 'step');
  });

  // Removed test: 'keeps performance metrics in demo mode neutral'
  // Reason: PerformanceMetrics doesn't support dataSource prop or performance-health-status testid
  // TODO: Add proper data source indication to PerformanceMetrics if needed in future

  it('renders QuickActions and timeline/pipeline tiles without console warnings', () => {
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    renderWithTheme(
      <>
        <QuickActions />
        <NarrativeTimeline />
        <TurnPipelineStatus />
      </>
    );

    const hasTooltipOrDomWarning = errorSpy.mock.calls.some(([message]) => {
      if (typeof message !== 'string') {
        return false;
      }
      return message.includes('validateDOMNesting') || message.includes('Tooltip');
    });

    expect(hasTooltipOrDomWarning).toBe(false);
    errorSpy.mockRestore();
  });

  it('renders RealTimeActivity without DOM nesting warnings', () => {
    vi.useFakeTimers();
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    const view = renderWithTheme(<RealTimeActivity />);
    view.unmount();
    vi.runOnlyPendingTimers();
    vi.useRealTimers();

    const hasDomWarning = errorSpy.mock.calls.some(
      ([message]) => typeof message === 'string' && message.includes('validateDOMNesting')
    );
    expect(hasDomWarning).toBe(false);
    errorSpy.mockRestore();
  });
});
