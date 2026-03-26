import { useState } from 'react';

import { Button } from '@/components/Button';
import { Panel } from '@/components/Panel';
import { StatusPill } from '@/components/StatusPill';
import { useAuth } from '@/features/auth/useAuth';
import { useDashboard } from '@/features/dashboard/useDashboard';
import { useDashboardEvents } from '@/hooks/useDashboardEvents';

function formatSessionLabel(isGuest: boolean, workspaceId: string) {
  return isGuest ? `Guest / ${workspaceId}` : `Workspace / ${workspaceId}`;
}

function formatEventTimestamp(timestamp: string) {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return 'Live';
  }

  return date.toLocaleTimeString();
}

export function DashboardPage() {
  const { session, signOut } = useAuth();
  const [error, setError] = useState<string | null>(null);

  if (!session) {
    return null;
  }

  const {
    status,
    orchestration,
    characters,
    world,
    isRefreshing,
    error: dashboardError,
    refresh,
    start,
    pause,
    stop,
  } = useDashboard(session.workspaceId);

  const { events, connectionState } = useDashboardEvents(session.workspaceId);

  const runAction = async (action: () => Promise<void>) => {
    setError(null);
    try {
      await action();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Action failed.');
    }
  };

  return (
    <main className="dashboard" data-testid="dashboard-page">
      <header className="dashboard-hero" data-testid="dashboard-hero">
        <div>
          <p className="dashboard-hero__eyebrow">Live dashboard</p>
          <h1 className="dashboard-hero__title">{status?.headline ?? 'Narrative control room'}</h1>
          <p className="dashboard-hero__summary">{status?.summary}</p>
        </div>

        <div className="dashboard-hero__meta">
          <StatusPill tone={status?.status ?? 'offline'}>
            {status?.status ?? 'offline'}
          </StatusPill>
          <StatusPill tone={orchestration?.status ?? 'idle'}>
            {orchestration?.status ?? 'idle'}
          </StatusPill>
          <span className="dashboard-hero__workspace" data-testid="workspace-badge">
            {formatSessionLabel(session.kind === 'guest', session.workspaceId)}
          </span>
          <Button variant="ghost" onClick={signOut}>
            Sign out
          </Button>
        </div>
      </header>

      {error || dashboardError ? (
        <p className="form-error">{error ?? dashboardError}</p>
      ) : null}

      <section className="dashboard-grid" data-testid="dashboard-grid">
        <Panel
          title="Orchestration controls"
          eyebrow="Run state"
          testId="orchestration-panel"
          actions={
            <Button variant="ghost" onClick={() => void refresh()}>
              {isRefreshing ? 'Refreshing...' : 'Refresh'}
            </Button>
          }
        >
          <div className="control-strip">
            <Button
              onClick={() => void runAction(start)}
              data-testid="start-orchestration"
              disabled={orchestration?.status === 'running'}
            >
              Start
            </Button>
            <Button
              variant="secondary"
              onClick={() => void runAction(pause)}
              data-testid="pause-orchestration"
              disabled={orchestration?.status !== 'running'}
            >
              Pause
            </Button>
            <Button
              variant="secondary"
              onClick={() => void runAction(stop)}
              data-testid="stop-orchestration"
            >
              Stop
            </Button>
          </div>

          <div className="status-rail" data-testid="orchestration-status">
            <strong>
              Turn {orchestration?.current_turn ?? 0} / {orchestration?.total_turns ?? 0}
            </strong>
            <span>Queue: {orchestration?.queue_length ?? 0}</span>
            <span>
              Avg latency:{' '}
              {orchestration ? orchestration.average_processing_time.toFixed(1) : '0.0'}s
            </span>
          </div>

          <ol className="timeline" data-testid="orchestration-timeline">
            {(orchestration?.steps ?? []).map((step) => (
              <li className="timeline__step" key={step.id} data-status={step.status}>
                <div>
                  <span className="timeline__name">{step.name}</span>
                  <span className="timeline__state">{step.status}</span>
                </div>
                <div className="timeline__progress">
                  <span style={{ width: `${step.progress}%` }} />
                </div>
              </li>
            ))}
          </ol>
        </Panel>

        <Panel title="Character roster" eyebrow="Active cast" testId="character-panel">
          <ul className="character-list" data-testid="character-list">
            {characters.map((character) => (
              <li key={character.id} className="character-card">
                <div>
                  <h3>{character.name}</h3>
                  <p>{character.role}</p>
                </div>
                <dl>
                  <div>
                    <dt>Drive</dt>
                    <dd>{character.drive}</dd>
                  </div>
                  <div>
                    <dt>Region</dt>
                    <dd>{character.region}</dd>
                  </div>
                </dl>
              </li>
            ))}
          </ul>
        </Panel>

        <Panel title="World pulse" eyebrow="Signals" testId="world-panel">
          <ul className="world-list">
            {world.map((entry) => (
              <li key={entry.id} className={`world-list__item world-list__item--${entry.tone}`}>
                <span>{entry.label}</span>
                <strong>{entry.value}</strong>
              </li>
            ))}
          </ul>

          <div className="world-summary">
            <p>Telemetry source</p>
            <strong data-testid="event-mode">
              {connectionState === 'connected'
                ? 'Backend stream'
                : connectionState === 'connecting'
                  ? 'Connecting to backend'
                  : 'Backend stream unavailable'}
            </strong>
          </div>
        </Panel>

        <Panel title="Event stream" eyebrow="Realtime" testId="events-panel">
          <ul className="event-feed" data-testid="event-feed">
            {events.length === 0 ? (
              <li className="event-feed__empty" data-testid="event-feed-empty">
                Waiting for backend events.
              </li>
            ) : (
              events.map((event) => (
                <li key={event.id} className="event-feed__item">
                  <div>
                    <strong>{event.title}</strong>
                    <span>{formatEventTimestamp(event.timestamp)}</span>
                  </div>
                  <p>{event.description}</p>
                </li>
              ))
            )}
          </ul>
        </Panel>
      </section>
    </main>
  );
}
