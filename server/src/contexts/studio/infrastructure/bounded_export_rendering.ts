import type { EventEmitter } from "node:events";
import { Readable } from "node:stream";

import type {
  ArtifactChapter,
  ArtifactWriteRequest,
} from "../application/ports/artifact_gateway.js";
import type { ExportArtifactFormat } from "../application/ports/export_store.js";
import { EXPORT_CAPACITY_LIMITS, ExportCapacityExceededError } from "../domain/exceptions.js";
import { docxManuscriptStream } from "./docx_manuscript.js";
import { epubStream } from "./epub_xml.js";
import { stripRepeatedTitleLine } from "./export_markdown_body.js";

export async function serializeBoundedArtifact(request: ArtifactWriteRequest): Promise<Buffer> {
  return collectBoundedArtifactStream(
    artifactStream(request),
    EXPORT_CAPACITY_LIMITS.artifact_bytes,
  );
}

export async function collectBoundedArtifactStream(
  stream: EventEmitter,
  limit: number,
): Promise<Buffer> {
  return new Promise<Buffer>((resolve, reject) => {
    const chunks: Buffer[] = [];
    let observed = 0;
    let settled = false;
    const finish = (action: () => void) => {
      if (settled) return;
      settled = true;
      stream.removeListener("data", onData);
      stream.removeListener("end", onEnd);
      stream.removeListener("error", onError);
      action();
    };
    const onData = (value: unknown) => {
      const chunk = Buffer.isBuffer(value) ? value : Buffer.from(String(value), "utf8");
      observed += chunk.length;
      if (observed > limit) {
        finish(() => reject(new ExportCapacityExceededError("artifact_bytes", limit, observed)));
        const destroy = Reflect.get(stream, "destroy");
        if (typeof destroy === "function") destroy.call(stream);
        return;
      }
      chunks.push(chunk);
    };
    const onEnd = () => finish(() => resolve(Buffer.concat(chunks, observed)));
    const onError = (error: unknown) => finish(() => reject(error));
    stream.on("data", onData);
    stream.once("end", onEnd);
    stream.once("error", onError);
  });
}

export function assertArtifactByteLength(_format: ExportArtifactFormat, observed: number): void {
  const limit = EXPORT_CAPACITY_LIMITS.artifact_bytes;
  if (observed > limit) {
    throw new ExportCapacityExceededError("artifact_bytes", limit, observed);
  }
}

function artifactStream(request: ArtifactWriteRequest): EventEmitter {
  if (request.format === "markdown") {
    return Readable.from(markdownSegments(request.projectTitle, request.chapters));
  }
  if (request.format === "epub") {
    return epubStream(request);
  }
  return docxManuscriptStream(request);
}

function* markdownSegments(title: string, chapters: readonly ArtifactChapter[]) {
  const parts = [`# ${title}`, ...chapters.map(markdownChapterSegment)];
  let last = parts.length - 1;
  while (last > 0 && parts[last]?.trim() === "") last -= 1;
  for (let index = 0; index <= last; index += 1) {
    const part = parts[index];
    if (part === undefined) throw new Error("Markdown export segment disappeared.");
    yield index === last ? part.trimEnd() : part;
    if (index < last) yield "\n\n";
  }
  yield "\n";
}

/**
 * One chapter segment for the Markdown artifact: the chapter title becomes a
 * level-2 heading (the project title owns the only level-1 heading) followed
 * by the frozen body. A leading body line that merely repeats the chapter
 * title is dropped, exactly like the DOCX/EPUB renderers, so the heading never
 * appears twice and authored subheadings are preserved. An empty body still
 * exports its heading, so no chapter silently vanishes from the file.
 */
function markdownChapterSegment(chapter: ArtifactChapter): string {
  const heading = `## ${chapter.title}`;
  const body = stripRepeatedTitleLine(chapter.title, chapter.contentMarkdown).trim();
  return body === "" ? heading : `${heading}\n\n${body}`;
}
