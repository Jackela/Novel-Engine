import { TextGenerationProviderError } from "../../application/ports/text_generation.js";

/** The only wrapper key the streaming adapters accept from JSON-mode providers. */
const TARGET_KEY = "chapter_markdown";

/**
 * Feed states: `leading` waits for the root `{`, the object phases walk
 * members until the `chapter_markdown` key, `target` unescapes its string
 * value, and `trailing` ignores everything after that value completed.
 */
type Phase =
  | "leading"
  | "member-start"
  | "key"
  | "colon"
  | "value-start"
  | "skip-string"
  | "skip-plain"
  | "member-continue"
  | "target"
  | "trailing";

/** Pending escape inside the string currently being read (`""` = await selector). */
interface EscapeState {
  readonly selector: string;
  readonly hex: string;
}

/**
 * Mutable walker state shared by the module-level phase handlers. `output`
 * accumulates the prose pieces of the current fragment and resets per `feed`.
 */
interface UnwrapperState {
  phase: Phase;
  keyBuffer: string;
  keyMatchesTarget: boolean;
  pendingEscape: EscapeState | undefined;
  output: string;
}

function contractFailure(detail: string): TextGenerationProviderError {
  return new TextGenerationProviderError(
    `Provider stream payload did not satisfy the chapter_markdown JSON contract: ${detail}`,
  );
}

function isJsonWhitespace(ch: string): boolean {
  return ch === " " || ch === "\t" || ch === "\n" || ch === "\r";
}

function isHexDigit(ch: string): boolean {
  return (ch >= "0" && ch <= "9") || (ch >= "a" && ch <= "f") || (ch >= "A" && ch <= "F");
}

function decodedSimpleEscape(selector: string): string {
  switch (selector) {
    case '"':
      return '"';
    case "\\":
      return "\\";
    case "/":
      return "/";
    case "b":
      return "\b";
    case "f":
      return "\f";
    case "n":
      return "\n";
    case "r":
      return "\r";
    case "t":
      return "\t";
    default:
      throw contractFailure(`invalid escape sequence '\\${selector}'`);
  }
}

/**
 * Incremental unwrapper for the JSON-object wrapper HTTP providers emit under
 * `response_format: json_object`. `feed` consumes raw payload fragments and
 * returns the unescaped `chapter_markdown` prose pieces (undefined when a
 * fragment yields nothing), tolerating leading/sibling content and
 * pretty-printing while staying strict — never passing bare text through.
 * Escape sequences may split across fragments; the concatenated pieces equal
 * `JSON.parse(payload).chapter_markdown` byte-for-byte. Nested object/array
 * sibling values are rejected to keep the walker small.
 */
export interface ChapterMarkdownUnwrapper {
  feed(fragment: string): string | undefined;
  /** Ends the stream; throws when no complete chapter_markdown string arrived. */
  finish(): void;
}

function createUnwrapperState(): UnwrapperState {
  return {
    phase: "leading",
    keyBuffer: "",
    keyMatchesTarget: false,
    pendingEscape: undefined,
    output: "",
  };
}

/** Consumes one character inside a JSON string body; true when the closing quote arrived. */
function consumeStringChar(
  state: UnwrapperState,
  ch: string,
  emit: (piece: string) => void,
): boolean {
  if (state.pendingEscape !== undefined) {
    if (state.pendingEscape.selector === "") {
      state.pendingEscape = { selector: ch, hex: "" };
      if (ch !== "u") {
        emit(decodedSimpleEscape(ch));
        state.pendingEscape = undefined;
      }
      return false;
    }
    if (!isHexDigit(ch)) throw contractFailure("incomplete \\u escape sequence");
    const hex = state.pendingEscape.hex + ch;
    if (hex.length < 4) {
      state.pendingEscape = { selector: state.pendingEscape.selector, hex };
      return false;
    }
    emit(String.fromCharCode(Number.parseInt(hex, 16)));
    state.pendingEscape = undefined;
    return false;
  }
  if (ch === '"') return true;
  if (ch === "\\") {
    state.pendingEscape = { selector: "", hex: "" };
    return false;
  }
  emit(ch);
  return false;
}

function stepLeading(state: UnwrapperState, ch: string): void {
  if (isJsonWhitespace(ch)) return;
  if (ch !== "{") throw contractFailure("expected a JSON object wrapper");
  state.phase = "member-start";
}

function stepMemberStart(state: UnwrapperState, ch: string): void {
  if (isJsonWhitespace(ch)) return;
  if (ch === '"') {
    state.keyBuffer = "";
    state.phase = "key";
    return;
  }
  if (ch === "}") throw contractFailure("wrapper object closed before chapter_markdown");
  throw contractFailure("expected a quoted member name");
}

function stepKey(state: UnwrapperState, ch: string): void {
  if (
    consumeStringChar(state, ch, (piece) => {
      state.keyBuffer += piece;
    })
  ) {
    state.keyMatchesTarget = state.keyBuffer === TARGET_KEY;
    state.phase = "colon";
  }
}

function stepColon(state: UnwrapperState, ch: string): void {
  if (isJsonWhitespace(ch)) return;
  if (ch !== ":") throw contractFailure("expected ':' after the member name");
  state.phase = "value-start";
}

function stepValueStart(state: UnwrapperState, ch: string): void {
  if (isJsonWhitespace(ch)) return;
  if (ch === '"') {
    state.phase = state.keyMatchesTarget ? "target" : "skip-string";
    return;
  }
  if (state.keyMatchesTarget) throw contractFailure("chapter_markdown must be a JSON string value");
  if (ch === "{" || ch === "[") {
    throw contractFailure("nested object/array values are not supported");
  }
  state.phase = "skip-plain";
}

function stepSkipString(state: UnwrapperState, ch: string): void {
  if (consumeStringChar(state, ch, () => undefined)) state.phase = "member-continue";
}

function stepSkipPlain(state: UnwrapperState, ch: string): void {
  if (ch === ",") {
    state.phase = "member-start";
    return;
  }
  if (ch === "}") throw contractFailure("wrapper object closed before chapter_markdown");
  if (isJsonWhitespace(ch)) state.phase = "member-continue";
}

function stepMemberContinue(state: UnwrapperState, ch: string): void {
  if (isJsonWhitespace(ch)) return;
  if (ch === ",") {
    state.phase = "member-start";
    return;
  }
  throw contractFailure("wrapper object closed before chapter_markdown");
}

function stepTarget(state: UnwrapperState, ch: string): void {
  if (
    consumeStringChar(state, ch, (piece) => {
      state.output += piece;
    })
  ) {
    state.phase = "trailing";
  }
}

function stepTrailing(): void {
  // Everything after the completed chapter_markdown value is ignored.
}

/** Per-phase handler for one consumed character; handlers advance `state.phase`. */
type StepHandler = (state: UnwrapperState, ch: string) => void;

const STEP_BY_PHASE: Readonly<Record<Phase, StepHandler>> = {
  leading: stepLeading,
  "member-start": stepMemberStart,
  key: stepKey,
  colon: stepColon,
  "value-start": stepValueStart,
  "skip-string": stepSkipString,
  "skip-plain": stepSkipPlain,
  "member-continue": stepMemberContinue,
  target: stepTarget,
  trailing: stepTrailing,
};

export function createChapterMarkdownUnwrapper(): ChapterMarkdownUnwrapper {
  const state = createUnwrapperState();
  return {
    feed(fragment: string): string | undefined {
      state.output = "";
      for (const ch of fragment) STEP_BY_PHASE[state.phase](state, ch);
      return state.output === "" ? undefined : state.output;
    },
    finish(): void {
      if (state.phase !== "trailing") {
        throw contractFailure("stream ended before a complete chapter_markdown string value");
      }
    },
  };
}
