/**
 * The beat vocabulary (#313, ADR-0004): a beat is one `##`/`###` section of
 * the project's outline document. The heading line is the beat title and the
 * body until the next heading is the beat content; text before the first
 * heading is preamble and never becomes a beat. Splitting is pure so both
 * the association surface and the proposal pipeline resolve against the
 * outline's current markdown through this single source.
 */
export interface OutlineBeat {
  readonly title: string;
  readonly content: string;
}

/** An ATX heading of level two or three: exactly what delimits one beat. */
const BEAT_HEADING = /^ {0,3}(?:##|###) +(?! )(.*)$/;

/**
 * Split an outline document's current markdown into its beats, in document
 * order. Headings without a body yield empty content; only levels two and
 * three split (`#`, `####`, and `##NoSpace` stay inside beat bodies).
 */
export function splitOutlineBeats(markdown: string): OutlineBeat[] {
  const beats: OutlineBeat[] = [];
  let current: { title: string; lines: string[] } | undefined;
  for (const line of String(markdown).split("\n")) {
    const heading = BEAT_HEADING.exec(line);
    if (heading !== null) {
      if (current !== undefined) {
        beats.push(finishBeat(current));
      }
      const title = heading[1]?.trim() ?? "";
      current = { title, lines: [] };
      continue;
    }
    current?.lines.push(line);
  }
  if (current !== undefined) {
    beats.push(finishBeat(current));
  }
  return beats;
}

function finishBeat(partial: { title: string; lines: string[] }): OutlineBeat {
  return { title: partial.title, content: partial.lines.join("\n").trim() };
}
