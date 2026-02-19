/**
 * Simulation Store (Zustand) - SIM-031
 *
 * Manages simulation state including loading states, last tick results,
 * snapshots, and error handling for the simulation dashboard.
 */
import { create } from 'zustand';
import type {
  SimulationTickResponse,
  SnapshotSummary,
} from '@/types/schemas';

interface SimulationState {
  // State
  isLoading: boolean;
  isPreviewing: boolean;
  lastTick: SimulationTickResponse | null;
  snapshots: SnapshotSummary[];
  error: string | null;
  statusMessage: string | null;

  // Actions
  setLoading: (isLoading: boolean) => void;
  setPreviewing: (isPreviewing: boolean) => void;
  setLastTick: (tick: SimulationTickResponse | null) => void;
  setSnapshots: (snapshots: SnapshotSummary[]) => void;
  setError: (error: string | null) => void;
  setStatusMessage: (message: string | null) => void;
  clearError: () => void;
  reset: () => void;
}

const initialState = {
  isLoading: false,
  isPreviewing: false,
  lastTick: null,
  snapshots: [],
  error: null,
  statusMessage: null,
};

export const useSimulationStore = create<SimulationState>((set) => ({
  // Initial state
  ...initialState,

  // Actions
  setLoading: (isLoading: boolean) => set({ isLoading }),
  setPreviewing: (isPreviewing: boolean) => set({ isPreviewing }),
  setLastTick: (lastTick: SimulationTickResponse | null) => set({ lastTick }),
  setSnapshots: (snapshots: SnapshotSummary[]) => set({ snapshots }),
  setError: (error: string | null) => set({ error, isLoading: false, isPreviewing: false }),
  setStatusMessage: (statusMessage: string | null) => set({ statusMessage }),
  clearError: () => set({ error: null }),
  reset: () => set(initialState),
}));

// Selector hooks for common use cases
export const useSimulationLoading = () =>
  useSimulationStore((state) => state.isLoading);
export const useSimulationPreviewing = () =>
  useSimulationStore((state) => state.isPreviewing);
export const useSimulationLastTick = () =>
  useSimulationStore((state) => state.lastTick);
export const useSimulationSnapshots = () =>
  useSimulationStore((state) => state.snapshots);
export const useSimulationError = () =>
  useSimulationStore((state) => state.error);
export const useSimulationStatusMessage = () =>
  useSimulationStore((state) => state.statusMessage);
