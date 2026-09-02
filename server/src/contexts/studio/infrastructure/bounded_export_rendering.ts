import type { EventEmitter } from "node:events";
import { Readable } from "node:stream";

import { Document, HeadingLevel, Packer, Paragraph } from "docx";

import type {
  ArtifactChapter,
  ArtifactWriteRequest,
} from "../application/export_artifact_service.js";
import type { ExportArtifactFormat } from "../application/ports/export_store.js";
import { EXPORT_CAPACITY_LIMITS, ExportCapacityExceededError } from "../domain/exceptions.js";
import { epubStream, plainText, xmlSafeText } from "./epub_xml.js";

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
    return epubStream(request.projectTitle, request.artifactId, request.chapters);
  }
  return docxStream(request.projectTitle, request.chapters);
}

function* markdownSegments(title: string, chapters: readonly ArtifactChapter[]) {
  const parts = [`# ${title}`, ...chapters.map((chapter) => chapter.contentMarkdown.trim())];
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

function docxStream(title: string, chapters: readonly ArtifactChapter[]): EventEmitter {
  const children: Paragraph[] = [
    new Paragraph({ text: xmlSafeText(title), heading: HeadingLevel.TITLE }),
  ];
  for (const chapter of chapters) {
    children.push(
      new Paragraph({ text: xmlSafeText(chapter.title), heading: HeadingLevel.HEADING_1 }),
    );
    for (const paragraph of plainText(chapter.contentMarkdown).split(/\n\s*\n/)) {
      const text = xmlSafeText(paragraph.trim());
      if (text !== "") children.push(new Paragraph({ text }));
    }
  }
  const stream = Packer.toStream(new Document({ sections: [{ children }] }));
  return stream;
}
