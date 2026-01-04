import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import type { FadeProps } from '@mui/material/Fade';
import QuickActions from '../QuickActions';
import WorldStateMap from '../WorldStateMap';
import CharacterNetworks from '../CharacterNetworks';
import NarrativeTimeline from '../NarrativeTimeline';
import RealTimeActivity from '../RealTimeActivity';

// Mock MUI Fade's reflow function to avoid jsdom scrollTop errors
vi.mock('@mui/material/Fade', () => {
  const actual = vi.importActual('@mui/material/Fade');
  return {
    ...actual as object,
    default: ({ children, in: inProp }: FadeProps) =>
      (inProp ? <>{children}</> : null),
  };
});

const mockDashboardDataset = vi.fn();
const mockRealtimeEvents = vi.fn();

vi.mock('@/hooks/useDashboardCharactersDataset', () => ({
  useDashboardCharactersDataset: () => mockDashboardDataset(),
}));

vi.mock('@/hooks/useRealtimeEvents', () => ({
  useRealtimeEvents: () => mockRealtimeEvents(),
}));

const sampleCharacters = [
  { id: 'aria', name: 'Aria Shadowbane', status: 'active', role: 'protagonist', trust: 82 },
  { id: 'lyra', name: 'Captain Lyra', status: 'inactive', role: 'npc', trust: 64 },
  { id: 'kael', name: 'Kael Voss', status: 'hostile', role: 'antagonist', trust: 40 },
];

const setupMockData = (source: 'api' | 'fallback', error: string | null = null) => {
  mockDashboardDataset.mockReturnValue({
    characters: sampleCharacters,
    loading: false,
    error,
    source,
  });
  mockRealtimeEvents.mockReturnValue({
    events: [],
    loading: false,
    error: null,
    connectionState: 'connected',
  });
};

const renderSpatialTiles = () => {
  render(
    <>
      <WorldStateMap />
      <CharacterNetworks />
    </>
  );
  const mapTile = screen.getByTestId('world-state-map');
  const networkTile = screen.getByTestId('character-networks');
  return { mapTile, networkTile };
};

const hasConsoleMessage = (
  spy: ReturnType<typeof vi.spyOn>,
  matcher: (message: string) => boolean
) => spy.mock.calls.some(([message]) => typeof message === 'string' && matcher(message));

let errorSpy: ReturnType<typeof vi.spyOn>;
let warnSpy: ReturnType<typeof vi.spyOn>;

const setupConsoleSpies = () => {
  beforeEach(() => {
    setupMockData('api');
    errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
  });

  afterEach(() => {
    errorSpy.mockRestore();
    warnSpy.mockRestore();
  });
};

describe('Dashboard accessibility + data parity', () => {
  setupConsoleSpies();

  it('renders QuickActions without leaking invalid DOM props', () => {
    render(<QuickActions />);

    const hasInvalidPropWarning = hasConsoleMessage(
      errorSpy,
      (message) => message.includes('React does not recognize the') || message.includes('Invalid DOM property')
    );

    expect(hasInvalidPropWarning).toBe(false);
  });

  it('shows connection chip and live text as ONLINE when idle but connected', () => {
    render(<QuickActions />);

    expect(screen.getByTestId('connection-status')).toHaveAttribute('data-status', 'online');
    expect(screen.getByTestId('live-indicator')).toHaveTextContent('ONLINE');
  });
});

describe('Dashboard data fallback', () => {
  setupConsoleSpies();

  it('fetches characters for spatial + network tiles and surfaces API data', () => {
    const { mapTile, networkTile } = renderSpatialTiles();

    expect(within(mapTile).getByText('3 Characters')).toBeInTheDocument();
    expect(within(networkTile).getByText('3 Characters')).toBeInTheDocument();
    expect(within(mapTile).getByText('API feed')).toBeInTheDocument();
    expect(within(networkTile).getByText('API feed')).toBeInTheDocument();
  });

  it('falls back to demo data when the API request fails without showing tile errors', () => {
    setupMockData('fallback', 'offline');
    const { mapTile, networkTile } = renderSpatialTiles();

    expect(within(mapTile).getByText('Demo data')).toBeInTheDocument();
    expect(within(networkTile).getByText('Demo data')).toBeInTheDocument();
  });
});

describe('Dashboard interaction affordances', () => {
  setupConsoleSpies();

  it('supports keyboard activation for world map markers', () => {
    render(<WorldStateMap />);

    const markers = screen.getAllByRole('button');
    expect(markers.length).toBeGreaterThan(1);

    fireEvent.keyDown(markers[1], { key: 'Enter' });
    expect(markers[1]).toHaveAttribute('aria-pressed', 'true');
  });

  it('exposes character network cards as focusable buttons', () => {
    render(<CharacterNetworks />);

    const cards = screen.getAllByTestId('character-node');
    expect(cards.length).toBeGreaterThan(0);
    expect(cards[0]).toHaveAttribute('role', 'button');
    expect(cards[0]).toHaveAttribute('tabindex', '0');

    fireEvent.keyDown(cards[0], { key: 'Enter' });
    expect(cards[0]).toHaveAttribute('aria-pressed', 'true');
  });

  it('marks narrative timeline nodes with aria-current metadata', () => {
    render(<NarrativeTimeline />);

    const currentNode = screen.getAllByTestId('timeline-node').find((node) =>
      node.getAttribute('data-status') === 'current'
    );

    expect(currentNode).toBeTruthy();
    expect(currentNode).toHaveAttribute('aria-current', 'step');
  });

  it('renders QuickActions and narrative timeline without console warnings', () => {
    render(
      <>
        <QuickActions />
        <NarrativeTimeline />
      </>
    );

    const hasWarning = hasConsoleMessage(warnSpy, (message) => message.includes('Warning'));

    expect(hasWarning).toBe(false);
  });

  it('renders RealTimeActivity without DOM nesting warnings', () => {
    render(<RealTimeActivity />);

    const hasNestingWarning = hasConsoleMessage(
      errorSpy,
      (message) => message.includes('validateDOMNesting')
    );

    expect(hasNestingWarning).toBe(false);
  });
});
