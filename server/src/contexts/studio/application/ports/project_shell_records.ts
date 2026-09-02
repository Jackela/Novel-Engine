import type { ProjectRecord } from "./studio_store.js";
import type { VolumeRecord } from "./volume_store.js";

/** Structural navigation row; accepted body and revision metadata stay absent. */
export interface DocumentSummaryRecord {
  id: string;
  projectId: string;
  kind: string;
  title: string;
  position: number;
  volumeId: string | null;
  beatRef: string | null;
  loreStatus: string;
  currentRevisionId: string;
  wordCount: number;
  createdAt: Date;
  updatedAt: Date;
}

/** One bounded project/navigation projection. */
export interface ProjectShellRecord {
  project: ProjectRecord;
  documents: DocumentSummaryRecord[];
  volumes: VolumeRecord[];
}
