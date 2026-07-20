export interface SettingsFormState {
  title: string;
  description: string;
  provider: string;
}

export interface InspectorPendingState {
  proposal: {
    running: boolean;
    accepting: boolean;
  };
  review: boolean;
  jobs: {
    loading: boolean;
    retrying: boolean;
    retryingJobId?: string | null;
  };
  settings: boolean;
  history?: {
    restoringRevisionId: string | null;
  };
}
