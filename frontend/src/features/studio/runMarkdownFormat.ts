/**
 * Markdown formatting commands for the studio editor (DR-016). The editor
 * creates its CodeMirror modules through lazy imports, so `EditorSelection`
 * — the only runtime factory these commands dispatch with — arrives as a
 * parameter (`MarkdownCommandRuntime`) instead of a static import.
 */

/** One format command the toolbar and shortcuts can run. */
export type MarkdownFormatCommand = "bold" | "italic" | "heading";

/** The CodeMirror runtime slice a format command needs to dispatch. */
export interface MarkdownCommandRuntime {
  readonly EditorSelection: typeof import("@codemirror/state").EditorSelection;
}

type EditorState = import("@codemirror/state").EditorState;
type SelectionRange = import("@codemirror/state").SelectionRange;
type EditorView = import("@codemirror/view").EditorView;

const INLINE_MARKERS: Record<Exclude<MarkdownFormatCommand, "heading">, string> = {
  bold: "**",
  italic: "*",
};

const HEADING_PREFIX = "# ";

interface LineToggle {
  readonly from: number;
  readonly delta: number;
}

/**
 * Maps one selection endpoint across the line-prefix toggles a heading
 * change made. An endpoint on a line start follows an inserted prefix (so
 * the caret stays inside the heading) and holds the line start when the
 * prefix is removed; endpoints after the prefix shift by the delta.
 */
function mapEndpoint(position: number, toggles: readonly LineToggle[]): number {
  let mapped = position;
  for (const toggle of toggles) {
    if (toggle.from > position) break;
    mapped += toggle.from === position ? Math.max(toggle.delta, 0) : toggle.delta;
    if (toggle.delta < 0) mapped = Math.max(mapped, toggle.from);
  }
  return mapped;
}

/** True when one more marker sits just inside the wrap (a longer marker run). */
function wrappedInLongerMarker(text: string, marker: string): boolean {
  const run = marker.length;
  return (
    text.slice(run, run * 2) === marker ||
    text.slice(text.length - run * 2, text.length - run) === marker
  );
}

/** True when the character just outside a span would extend an asterisk run. */
function touchesLongerMarker(state: EditorState, from: number, to: number): boolean {
  const before = state.sliceDoc(Math.max(0, from - 1), from);
  const after = state.sliceDoc(to, Math.min(state.doc.length, to + 1));
  return before === "*" || after === "*";
}

/**
 * The outer `[from, to]` bounds of an existing marker span for one range,
 * or null when the range is not marked yet. A range counts as marked when
 * its text is wrapped in the marker or when the marker sits immediately
 * outside it (the state a previous wrap leaves behind); spans touching a
 * longer asterisk run are treated as unmarked, so bold and italic never eat
 * each other's markers.
 */
function markedSpan(
  state: EditorState,
  range: SelectionRange,
  marker: string,
): { from: number; to: number } | null {
  const text = state.sliceDoc(range.from, range.to);
  if (
    text.length >= marker.length * 2 + 1 &&
    text.startsWith(marker) &&
    text.endsWith(marker) &&
    !wrappedInLongerMarker(text, marker)
  ) {
    return { from: range.from, to: range.to };
  }
  if (range.from < marker.length || range.to + marker.length > state.doc.length) return null;
  const wrappedOutside =
    state.sliceDoc(range.from - marker.length, range.from) === marker &&
    state.sliceDoc(range.to, range.to + marker.length) === marker;
  if (
    !wrappedOutside ||
    touchesLongerMarker(state, range.from - marker.length, range.to + marker.length)
  ) {
    return null;
  }
  return { from: range.from - marker.length, to: range.to + marker.length };
}

/** Wraps or unwraps one inline range in its marker. */
function inlineChange(
  state: EditorState,
  range: SelectionRange,
  marker: string,
  runtime: MarkdownCommandRuntime,
) {
  const text = state.sliceDoc(range.from, range.to);
  if (text.length === 0) {
    const caret = range.from + marker.length;
    return {
      changes: { from: range.from, to: range.to, insert: marker + marker },
      range: runtime.EditorSelection.range(caret, caret),
    };
  }
  const span = markedSpan(state, range, marker);
  if (span === null) {
    return {
      changes: { from: range.from, to: range.to, insert: marker + text + marker },
      range: runtime.EditorSelection.range(range.from + marker.length, range.to + marker.length),
    };
  }
  const inner = state.sliceDoc(span.from + marker.length, span.to - marker.length);
  return {
    changes: { from: span.from, to: span.to, insert: inner },
    range: runtime.EditorSelection.range(span.from, span.from + inner.length),
  };
}

/** Toggles the heading prefix on every line one range touches. */
function headingChangeSet(view: EditorView, runtime: MarkdownCommandRuntime) {
  // Two ranges can cover the same line; only the first one changes it.
  const toggledLines = new Set<number>();
  return view.state.changeByRange((range) => {
    const changes: { from: number; to: number; insert: string }[] = [];
    const toggles: LineToggle[] = [];
    let line = view.state.doc.lineAt(range.from);
    const last = view.state.doc.lineAt(range.to);
    for (;;) {
      if (!toggledLines.has(line.number)) {
        toggledLines.add(line.number);
        const hasPrefix = line.text.startsWith(HEADING_PREFIX);
        changes.push(
          hasPrefix
            ? { from: line.from, to: line.from + HEADING_PREFIX.length, insert: "" }
            : { from: line.from, to: line.from, insert: HEADING_PREFIX },
        );
        toggles.push({
          from: line.from,
          delta: hasPrefix ? -HEADING_PREFIX.length : HEADING_PREFIX.length,
        });
      }
      if (line.number === last.number) break;
      line = view.state.doc.line(line.number + 1);
    }
    return {
      changes,
      range: runtime.EditorSelection.range(
        mapEndpoint(range.from, toggles),
        mapEndpoint(range.to, toggles),
      ),
    };
  });
}

/**
 * Runs one markdown format command over every selection range and reports
 * whether the editor handled it. Bold/italic wrap (or unwrap) each range in
 * its marker; heading toggles the `# ` prefix on every line the range
 * touches, so a multi-line selection becomes a multi-line heading.
 */
export function runMarkdownFormat(
  view: EditorView,
  command: MarkdownFormatCommand,
  runtime: MarkdownCommandRuntime,
): boolean {
  view.dispatch(
    command === "heading"
      ? headingChangeSet(view, runtime)
      : view.state.changeByRange((range) =>
          inlineChange(view.state, range, INLINE_MARKERS[command], runtime),
        ),
  );
  return true;
}
