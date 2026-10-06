/**
 * The shared CJK segmentation strategy of full-text search (#DR-003). The
 * FTS5 unicode61 tokenizer that backs `document_search` treats a
 * punctuation-delimited run of Han characters as a single token, so a query
 * like 黛玉 can never match a body that wrote 林黛玉. Both sides of the index
 * therefore go through this module: index text separates adjacent Han
 * characters (and Han/Latin script boundaries) so every character is its own
 * unicode61 token, and query text turns each Han run into one quoted
 * character phrase, which FTS5 matches as an exact contiguous substring.
 * `Intl.Segmenter` is deliberately unused: its `word` granularity keeps
 * 林黛玉 as one word, so the required 黛玉/宝玉 subword queries would still
 * return nothing. All functions are total string transformations over
 * untrusted input; none of them interprets FTS5 syntax, the empty string
 * stays empty, and no function ever throws.
 */

/** The unicode61 word-run shape `buildFtsMatchQuery` reduces toward. */
const WORD_RUN_PATTERN = /[\p{L}\p{N}_]+/gu;

/** One code point unicode61 folds into a token with no separator. */
const WORD_CHARACTER_PATTERN = /[\p{L}\p{N}_]/u;

/** A Han code point (CJK Unified Ideographs and their extensions). */
const HAN_CHARACTER_PATTERN = /^\p{Script=Han}$/u;

/** An artificial space between two Han characters produced by this module. */
const HAN_SPACE_HAN_PATTERN = /(?<=\p{Script=Han}) (?=\p{Script=Han})/gu;

function isHan(char: string): boolean {
  return HAN_CHARACTER_PATTERN.test(char);
}

/**
 * Index-side preparation: insert one space between two token-forming
 * characters whenever at least one of them is Han, so "林黛玉进了贾府"
 * becomes "林 黛 玉 进 了 贾 府" and "用Node写" becomes "用 Node 写".
 * Latin-only text is returned unchanged.
 */
export function segmentFtsIndexText(text: string): string {
  let segmented = "";
  let previous: string | null = null;
  for (const char of text) {
    if (
      previous !== null &&
      (isHan(previous) || isHan(char)) &&
      WORD_CHARACTER_PATTERN.test(previous) &&
      WORD_CHARACTER_PATTERN.test(char)
    ) {
      segmented += " ";
    }
    segmented += char;
    previous = char;
  }
  return segmented;
}

/**
 * Display-side restoration: excerpts and titles come back from the index
 * with the artificial separators; removing one space between two Han
 * characters restores the author's text. The one lossy corner — an author's
 * own Han-space-Han sequence — collapses to the same reading, and Chinese
 * prose does not use that spacing.
 */
export function restoreFtsDisplayText(text: string): string {
  return text.replace(HAN_SPACE_HAN_PATTERN, "");
}

/**
 * Query-side reduction: one match element per Latin word or per Han run.
 * A Han run becomes a space-joined character phrase ("黛玉" -> "黛 玉")
 * because a quoted multi-token FTS5 phrase is exactly the substring match
 * Chinese search needs; a run that glues Han and Latin is split at the
 * script boundary ("用Node写" -> "用", "node", "写") to mirror the index
 * text. The caller owns quoting, de-duplication, and caps.
 */
export function reduceFtsQueryElements(query: string): string[] {
  const elements: string[] = [];
  for (const run of query.matchAll(WORD_RUN_PATTERN)) {
    elements.push(...splitWordRun(run[0]));
  }
  return elements;
}

function splitWordRun(run: string): string[] {
  const elements: string[] = [];
  let group = "";
  let groupIsHan = false;
  for (const char of run) {
    const isHanChar = isHan(char);
    if (group !== "" && isHanChar !== groupIsHan) {
      elements.push(encodeGroup(group, groupIsHan));
      group = "";
    }
    group += char;
    groupIsHan = isHanChar;
  }
  if (group !== "") {
    elements.push(encodeGroup(group, groupIsHan));
  }
  return elements;
}

function encodeGroup(group: string, groupIsHan: boolean): string {
  return groupIsHan ? [...group].join(" ") : group;
}
