import { create } from 'zustand';

type PhaseStatus = 'pending' | 'processing' | 'completed';
type RunState = 'idle' | 'running' | 'paused';

export interface PipelinePhase {
  name: string;
  status: PhaseStatus;
}

const PHASES: PipelinePhase[] = [
  { name: 'World Update', status: 'pending' },
  { name: 'Subjective Brief', status: 'pending' },
  { name: 'Interaction Orchestration', status: 'pending' },
  { name: 'Event Integration', status: 'pending' },
  { name: 'Narrative Integration', status: 'pending' },
];

let phaseTimers: number[] = [];

const clearPhaseTimers = () => {
  phaseTimers.forEach((timer) => window.clearTimeout(timer));
  phaseTimers = [];
};

interface OrchestrationState {
  runState: RunState;
  live: boolean;
  phases: PipelinePhase[];
  start: () => void;
  pause: () => void;
  stop: () => void;
  reset: () => void;
}

export const useOrchestrationStore = create<OrchestrationState>((set, get) => ({
  runState: 'idle',
  live: false,
  phases: PHASES,
  start: () => {
    clearPhaseTimers();
    const initialPhases: PipelinePhase[] = PHASES.map((phase, index) => ({
      ...phase,
      status: (index === 0 ? 'processing' : 'pending') as PhaseStatus,
    }));
    set({ runState: 'running', live: true, phases: initialPhases });

    PHASES.forEach((_, index) => {
      const timer = window.setTimeout(
        () => {
          set((state) => {
            const updated = state.phases.map((phase, phaseIndex) => {
              if (phaseIndex < index) {
                return { ...phase, status: 'completed' as PhaseStatus };
              }
              if (phaseIndex === index) {
                return { ...phase, status: 'completed' as PhaseStatus };
              }
              if (phaseIndex === index + 1) {
                return { ...phase, status: 'processing' as PhaseStatus };
              }
              return phase;
            });
            const isLast = index === PHASES.length - 1;
            return {
              phases: updated,
              runState: isLast ? 'idle' : state.runState,
              live: isLast ? false : state.live,
            };
          });
        },
        400 * (index + 1)
      );
      phaseTimers.push(timer);
    });
  },
  pause: () => {
    clearPhaseTimers();
    set({ runState: 'paused', live: false });
  },
  stop: () => {
    clearPhaseTimers();
    set({ runState: 'idle', live: false, phases: PHASES });
  },
  reset: () => {
    clearPhaseTimers();
    set({ runState: 'idle', live: false, phases: PHASES });
  },
}));
