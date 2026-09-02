import { OperationCapacityExceededError } from "../domain/exceptions.js";

export interface ExportRendererPermit {
  release(): void;
}

/** One generation-safe renderer owner per API app instance. */
export class ExportRendererGuard {
  private owner: symbol | null = null;

  acquire(projectId: string): ExportRendererPermit {
    if (this.owner !== null) {
      throw new OperationCapacityExceededError("application", 1, 1, projectId);
    }
    const token = Symbol("export-renderer");
    this.owner = token;
    let released = false;
    return {
      release: () => {
        if (released) return;
        released = true;
        if (this.owner === token) this.owner = null;
      },
    };
  }
}
