import { apiUrl, getCsrfToken, HttpError, readHttpError } from '@/app/api';
import { parseJob } from '@/app/apiWorkflowContract';
import type { StudioJob } from '@/app/types/studio';

/**
 * Streaming proposal client (#308): consumes the server's
 * `text/event-stream` with fetch + ReadableStream so credentials and the
 * CSRF header stay identical to the synchronous client. One terminal frame
 * resolves the stream — `done` carries the same job payload as the
 * synchronous endpoint, `error` rejects with the failed-job message.
 */

export type ProposalStreamFrame =
  | { type: 'delta'; text: string }
  | { type: 'done'; job: StudioJob }
  | { type: 'error'; error: { code: string; message: string } };

function parseFrameEvent(rawEvent: string): ProposalStreamFrame | null {
  const data = rawEvent
    .split('\n')
    .filter((line) => line.startsWith('data:'))
    .map((line) => (line.startsWith('data: ') ? line.slice(6) : line.slice(5)))
    .join('\n');
  if (data === '') return null;
  return JSON.parse(data) as ProposalStreamFrame;
}

/**
 * Incremental parser for the SSE frame stream: feed it decoded text chunks,
 * it returns the complete frames. A trailing partial event stays buffered
 * until its terminating blank line arrives.
 */
export class ProposalStreamParser {
  private buffer = '';

  append(chunk: string): ProposalStreamFrame[] {
    this.buffer += chunk;
    const frames: ProposalStreamFrame[] = [];
    let boundary = this.buffer.indexOf('\n\n');
    while (boundary !== -1) {
      const rawEvent = this.buffer.slice(0, boundary);
      this.buffer = this.buffer.slice(boundary + 2);
      const frame = parseFrameEvent(rawEvent);
      if (frame !== null) frames.push(frame);
      boundary = this.buffer.indexOf('\n\n');
    }
    return frames;
  }
}

export interface ProposalStreamRequest {
  readonly projectId: string;
  readonly documentId: string;
  readonly operation: 'continue' | 'rewrite' | 'generate';
  readonly instruction: string;
  readonly provider: string;
  /** Aborting cancels the proposal: the server persists nothing. */
  readonly signal?: AbortSignal;
  /** Invoked for every delta as the proposal markdown arrives. */
  readonly onDelta: (text: string) => void;
}

/** Consume one streamed proposal; resolves with the terminal job payload. */
export async function streamProposal({
  projectId,
  documentId,
  operation,
  instruction,
  provider,
  signal,
  onDelta,
}: ProposalStreamRequest): Promise<StudioJob> {
  const path = `/api/projects/${projectId}/documents/${documentId}/ai-proposals/stream`;
  const csrfToken = getCsrfToken();
  let response: Response;
  try {
    response = await fetch(apiUrl(path), {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {}),
      },
      body: JSON.stringify({ operation, instruction, provider }),
      signal,
    });
  } catch (error) {
    if ((error instanceof Error || error instanceof DOMException) && error.name === 'AbortError') {
      throw new Error('Request cancelled.');
    }
    if (error instanceof TypeError) {
      throw new Error('Novel Engine is unavailable. Check the local service and retry.');
    }
    throw error;
  }
  if (!response.ok) {
    throw await readHttpError(response, `Proposal stream failed with status ${response.status}`);
  }
  const body = response.body;
  if (body === null) {
    throw new HttpError('Proposal stream returned no body.', 502);
  }
  const reader = body.getReader();
  const decoder = new TextDecoder();
  const parser = new ProposalStreamParser();
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      for (const frame of parser.append(decoder.decode(value, { stream: true }))) {
        if (frame.type === 'delta') {
          onDelta(frame.text);
        } else if (frame.type === 'done') {
          return parseJob(frame.job);
        } else {
          throw new HttpError(frame.error.message, 502, undefined, frame.error.code);
        }
      }
    }
  } catch (error) {
    if ((error instanceof Error || error instanceof DOMException) && error.name === 'AbortError') {
      throw new Error('Request cancelled.');
    }
    throw error;
  }
  throw new HttpError('Proposal stream ended without a result.', 502);
}
