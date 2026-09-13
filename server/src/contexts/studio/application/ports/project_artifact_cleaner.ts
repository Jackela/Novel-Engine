/** Removes the filesystem artifacts owned by one already-authorized project. */
export interface ProjectArtifactCleaner {
  removeProjectArtifacts(projectId: string): Promise<void>;
}
