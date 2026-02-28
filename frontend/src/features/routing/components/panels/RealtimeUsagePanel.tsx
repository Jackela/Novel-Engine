/**
 * RealtimeUsagePanel - Live usage counter for active generation sessions
 *
 * BRAIN-035B-04: Real-time Usage Counter
 *
 * Displays real-time token usage and costs for active LLM generation sessions.
 */

import { useEffect, useRef, useState } from 'react';

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { brainSettingsApi } from '@/features/routing/api/brainSettingsApi';
import { type RealtimeUsageEvent } from '@/features/routing/api/brainSettingsApi';
import { Loader2 } from 'lucide-react';

interface ActiveSession {
  session_id: string;
  provider: string;
  model_name: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost: number;
  is_complete: boolean;
}

interface UseRealtimeUsageResult {
  activeSessions: ActiveSession[];
  currentSession: ActiveSession | null;
  totalTokens: number;
  totalCost: number;
  isConnected: boolean;
}

function useRealtimeUsage(): UseRealtimeUsageResult {
  const [activeSessions, setActiveSessions] = useState<ActiveSession[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    eventSourceRef.current = brainSettingsApi.streamRealtimeUsage(
      (event: RealtimeUsageEvent) => {
        if (event.type === 'session_start') {
          setActiveSessions((prev) => [
            ...prev,
            {
              session_id: event.session_id,
              provider: event.provider,
              model_name: event.model_name,
              input_tokens: 0,
              output_tokens: 0,
              total_tokens: 0,
              cost: 0,
              is_complete: false,
            },
          ]);
        } else if (event.type === 'token_update') {
          setActiveSessions((prev) =>
            prev.map((s) =>
              s.session_id === event.session_id
                ? {
                    ...s,
                    input_tokens: event.input_tokens,
                    output_tokens: event.output_tokens,
                    total_tokens: event.total_tokens,
                    cost: event.cost,
                  }
                : s
            )
          );
        } else if (event.type === 'session_complete') {
          setActiveSessions((prev) =>
            prev.map((s) =>
              s.session_id === event.session_id ? { ...s, is_complete: true } : s
            )
          );
          setTimeout(() => {
            setActiveSessions((prev) =>
              prev.filter((s) => s.session_id !== event.session_id)
            );
          }, 5000);
        } else if (event.type === 'session_state') {
          setActiveSessions((prev) => {
            const existing = prev.find((s) => s.session_id === event.session_id);
            if (existing) {
              return prev.map((s) =>
                s.session_id === event.session_id
                  ? {
                      ...s,
                      input_tokens: event.input_tokens,
                      output_tokens: event.output_tokens,
                      total_tokens: event.total_tokens,
                      cost: event.cost,
                      is_complete: event.is_complete,
                    }
                  : s
              );
            }
            return [
              ...prev,
              {
                session_id: event.session_id,
                provider: event.provider,
                model_name: event.model_name,
                input_tokens: event.input_tokens,
                output_tokens: event.output_tokens,
                total_tokens: event.total_tokens,
                cost: event.cost,
                is_complete: event.is_complete,
              },
            ];
          });
        }
        setIsConnected(true);
      },
      (error) => {
        console.error('Real-time usage error:', error);
        setIsConnected(false);
      }
    );

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  const totalTokens = activeSessions.reduce((sum, s) => sum + s.total_tokens, 0);
  const totalCost = activeSessions.reduce((sum, s) => sum + s.cost, 0);

  const currentSession =
    activeSessions.length > 0
      ? activeSessions.reduce((latest, s) =>
          !latest || s.total_tokens > latest.total_tokens ? s : latest
        )
      : null;

  return {
    activeSessions,
    currentSession,
    totalTokens,
    totalCost,
    isConnected,
  };
}

export function RealtimeUsagePanel() {
  const { activeSessions, currentSession, isConnected } = useRealtimeUsage();

  if (!isConnected && activeSessions.length === 0) {
    return null;
  }

  return (
    <Card
      className={isConnected && activeSessions.length > 0 ? 'border-primary/50' : ''}
    >
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-lg">
              {activeSessions.length > 0 ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin text-primary" />
                  Live Usage
                </>
              ) : (
                'Real-time Counter'
              )}
            </CardTitle>
            <CardDescription>
              {activeSessions.length > 0
                ? `Active generation${activeSessions.length > 1 ? `s (${activeSessions.length})` : ''}`
                : isConnected
                  ? 'Connected - waiting for generation...'
                  : 'Connecting...'}
            </CardDescription>
          </div>
          <div
            className={`flex items-center gap-1.5 text-xs ${isConnected ? 'text-green-500' : 'text-muted-foreground'}`}
          >
            <div
              className={`h-2 w-2 rounded-full ${isConnected ? 'animate-pulse bg-green-500' : 'bg-muted-foreground'}`}
            />
            {isConnected ? 'Live' : 'Offline'}
          </div>
        </div>
      </CardHeader>
      {activeSessions.length > 0 && (
        <CardContent className="space-y-4">
          {currentSession && (
            <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
              <div>
                <p className="text-xs text-muted-foreground">Tokens</p>
                <p className="text-xl font-semibold">
                  {currentSession.total_tokens.toLocaleString()}
                </p>
                <p className="text-xs text-muted-foreground">
                  {currentSession.input_tokens} in / {currentSession.output_tokens} out
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Cost</p>
                <p className="text-xl font-semibold text-green-600">
                  ${currentSession.cost.toFixed(4)}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Model</p>
                <p className="text-sm font-medium capitalize">
                  {currentSession.provider}
                </p>
                <p className="text-xs text-muted-foreground">
                  {currentSession.model_name}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Status</p>
                <p
                  className={`text-sm font-medium ${currentSession.is_complete ? 'text-green-500' : 'text-primary'}`}
                >
                  {currentSession.is_complete ? 'Complete' : 'Generating...'}
                </p>
              </div>
            </div>
          )}

          {activeSessions.length > 1 && (
            <div className="space-y-2 border-t pt-2">
              <p className="text-xs text-muted-foreground">All Active Sessions</p>
              {activeSessions.map((session) => (
                <div
                  key={session.session_id}
                  className="flex items-center justify-between rounded bg-muted/50 p-2"
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={`h-2 w-2 rounded-full ${session.is_complete ? 'bg-green-500' : 'animate-pulse bg-primary'}`}
                    />
                    <div>
                      <p className="text-sm font-medium capitalize">
                        {session.provider}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {session.model_name}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium">
                      {session.total_tokens.toLocaleString()} tokens
                    </p>
                    <p className="text-xs text-green-600">${session.cost.toFixed(4)}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      )}
    </Card>
  );
}
