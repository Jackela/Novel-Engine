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

export function createChapterMarkdownUnwrapper(): ChapterMarkdownUnwrapper {
  let phase: Phase = "leading";
  let keyBuffer = "";
  let keyMatchesTarget = false;
  let pendingEscape: EscapeState | undefined;
  let output = "";

  const consumeStringChar = (ch: string, emit: (piece: string) => void): boolean => {
    if (pendingEscape !== undefined) {
      if (pendingEscape.selector === "") {
        pendingEscape = { selector: ch, hex: "" };
        if (ch !== "u") {
          emit(decodedSimpleEscape(ch));
          pendingEscape = undefined;
        }
        return false;
      }
      if (!isHexDigit(ch)) throw contractFailure("incomplete \\u escape sequence");
      const hex = pendingEscape.hex + ch;
      if (hex.length < 4) {
        pendingEscape = { selector: pendingEscape.selector, hex };
        return false;
      }
      emit(String.fromCharCode(Number.parseInt(hex, 16)));
      pendingEscape = undefined;
      return false;
    }
    if (ch === '"') return true;
    if (ch === "\\") {
      pendingEscape = { selector: "", hex: "" };
      return false;
    }
    emit(ch);
    return false;
  };

  const step = (ch: string): void => {
    switch (phase) {
      case "leading":
        if (isJsonWhitespace(ch)) return;
        if (ch !== "{") throw contractFailure("expected a JSON object wrapper");
        phase = "member-start";
        return;
      case "member-start":
        if (isJsonWhitespace(ch)) return;
        if (ch === '"') {
          keyBuffer = "";
          phase = "key";
          return;
        }
        if (ch === "}") throw contractFailure("wrapper object closed before chapter_markdown");
        throw contractFailure("expected a quoted member name");
      case "key":
        if (
          consumeStringChar(ch, (piece) => {
            keyBuffer += piece;
          })
        ) {
          keyMatchesTarget = keyBuffer === TARGET_KEY;
          phase = "colon";
        }
        return;
      case "colon":
        if (isJsonWhitespace(ch)) return;
        if (ch !== ":") throw contractFailure("expected ':' after the member name");
        phase = "value-start";
        return;
      case "value-start":
        if (isJsonWhitespace(ch)) return;
        if (ch === '"') {
          phase = keyMatchesTarget ? "target" : "skip-string";
          return;
        }
        if (keyMatchesTarget) throw contractFailure("chapter_markdown must be a JSON string value");
        if (ch === "{" || ch === "[") {
          throw contractFailure("nested object/array values are not supported");
        }
        phase = "skip-plain";
        return;
      case "skip-string":
        if (consumeStringChar(ch, () => undefined)) phase = "member-continue";
        return;
      case "skip-plain":
        if (ch === ",") {
          phase = "member-start";
          return;
        }
        if (ch === "}") throw contractFailure("wrapper object closed before chapter_markdown");
        if (isJsonWhitespace(ch)) phase = "member-continue";
        return;
      case "member-continue":
        if (isJsonWhitespace(ch)) return;
        if (ch === ",") {
          phase = "member-start";
          return;
        }
        throw contractFailure("wrapper object closed before chapter_markdown");
      case "target":
        if (
          consumeStringChar(ch, (piece) => {
            output += piece;
          })
        ) {
          phase = "trailing";
        }
        return;
      case "trailing":
        return;
    }
  };

  return {
    feed(fragment: string): string | undefined {
      output = "";
      for (const ch of fragment) step(ch);
      return output === "" ? undefined : output;
    },
    finish(): void {
      if (phase !== "trailing") {
        throw contractFailure("stream ended before a complete chapter_markdown string value");
      }
    },
  };
}
