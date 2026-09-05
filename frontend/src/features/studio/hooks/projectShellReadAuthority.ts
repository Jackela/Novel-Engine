import type { ProjectShell } from "@/app/types/studio";

export interface ProjectShellReadCapture {
  readonly projectId: string;
  readonly readEpoch: number;
  readonly mutationEpoch: number;
}

export interface ProjectShellReadAuthority {
  captureProjectShellRead: () => ProjectShellReadCapture;
  publishProjectShellRead: (capture: ProjectShellReadCapture, project: ProjectShell) => boolean;
}
