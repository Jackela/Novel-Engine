import { describe, expect, it } from "vitest";

import { hasProviderScaffolding } from "../../src/contexts/studio/application/provider_scaffold.js";

const siblingPaddedScaffold = JSON.stringify(
  JSON.stringify({
    nested: { result: "raw provider scaffold" },
    ...Object.fromEntries(Array.from({ length: 129 }, (_, index) => [`padding_${index}`, index])),
  }),
);

describe("provider scaffold detection", () => {
  it.each([
    ["bare line key", "ReSuLt: raw provider scaffold"],
    ["quoted line key", "`EcHo` = raw provider scaffold"],
    ["list label", "  - RESULT: raw provider scaffold"],
    ["task label", "- [x] '\\u0065cho' = raw provider scaffold"],
    ["ordered label", "  2) \\u0072esult: raw provider scaffold"],
    ["Unicode leading indent", "\u2003RESULT: raw provider scaffold"],
    ["Unicode list spacing", "\u2003-\u00a0RESULT: raw provider scaffold"],
    ["Unicode line separator", "prose\u2028\u00a0\\u0072esult\\u003A raw provider scaffold"],
    ["Unicode paragraph separator", "prose\u2029\u00a0'\\u0065cho'\\u003d raw provider scaffold"],
    ["direct object key", "{ RESULT: raw provider scaffold }"],
    ["actual inline whitespace", '{\r\n\t"result" = raw provider scaffold}'],
    ["Unicode structural whitespace", '{"meta":{},\u00a0"result": raw provider scaffold}'],
    ["sibling object key", '{meta: "note", "result": raw provider scaffold}'],
    ["nested object key", "{meta: {EcHo: raw provider scaffold}}"],
    ["nested array key", "{items: [{note: 'x'}, {\\u0072esult: raw provider scaffold}]}"],
    ["array field", "[echo: raw provider scaffold]"],
    ["array sibling field", '["note", result: raw provider scaffold]'],
    ["invalid first token", '{?: "metadata", result: raw provider scaffold}'],
    ["missing first-field separator", '{"meta" "bad", \\u0072esult = raw provider scaffold}'],
    ["bare malformed first field", "{false, result: raw provider scaffold}"],
    ["missing first key", '{: "note", "result": raw provider scaffold}'],
    ["nested malformed first field", "{[broken], nested: [{?bad, echo: raw provider scaffold}]}"],
    ["unclosed array", '{"meta": [ result: raw provider scaffold'],
    ["unterminated quote value", '{"meta": "unterminated, "result": raw provider scaffold}'],
    ["invalid value separator", '{"meta": "note" result: raw provider scaffold}'],
    ["loose continuation", '{meta: "note"}, result: raw provider scaffold'],
    ["immediate continuation", '{meta: "note"} \\u0072esult: raw provider scaffold'],
    ["punctuated loose continuation", '{meta: "note"},,,;:=\u00a0result: raw provider scaffold'],
    ["extra closers", '{"meta": {note: "x"}}}, result = raw provider scaffold'],
    ["unbounded mixed closers", '{meta: "note"}]}]}]}]}], \\u0072esult: raw provider scaffold'],
    ["mismatched closer", '{"meta": [}, result = raw provider scaffold'],
    ["sibling-padded nested serialized target", siblingPaddedScaffold],
    ["double-encoded target", JSON.stringify(JSON.stringify({ result: "raw provider scaffold" }))],
    ["single-quoted JSON target", "'" + JSON.stringify({ result: "raw provider scaffold" }) + "'"],
    ["backticked JSON target", `\`${JSON.stringify({ result: "raw provider scaffold" })}\``],
    ["single-quoted JSON with delimiter value", "'{\"result\":\"Mara said 'stop'\"}'"],
    ["backticked JSON with delimiter value", '`{"result":"Mara wrote `stop`"}`'],
    ["fenced language JSON", '```json\n{"result":"raw provider scaffold"}\n```'],
    ["zero-width layout indent", "\u200B\\u0072esult\\u003A raw provider scaffold"],
    ["NEL line boundary", "prose\u0085\u200B\\u0065cho\\u003D raw provider scaffold"],
    [
      "nested serialized child",
      `\`${JSON.stringify({ payload: JSON.stringify({ meta: { echo: "raw provider scaffold" } }) })}\``,
    ],
    [
      "triple-encoded nested target",
      JSON.stringify(JSON.stringify(JSON.stringify({ meta: { echo: "raw provider scaffold" } }))),
    ],
    [
      "encoded Unicode structural whitespace",
      JSON.stringify(JSON.stringify('{"meta":{},\u00a0"result":"raw provider scaffold"}')),
    ],
  ])("finds a %s", (_label, markdown) => {
    expect(hasProviderScaffolding(markdown)).toBe(true);
  });

  it.each([
    ["double-quoted dialogue", 'Mara said "{result: turn back}" and kept walking.'],
    ["single-quoted dialogue", "Mara read '{echo: turn back}' and kept walking."],
    ["backticked dialogue", "Mara copied `{result: turn back}` into her notebook."],
    ["contractions", "Mara's answer was that she don't know the result of the storm."],
    ["unpaired leading apostrophe", "'Twas only rain on the slate roof."],
    ["quoted non-target value", '{meta: "the result = a promise Mara could trust"}'],
    ["invalid unicode escape", '{"\\uZZZZesult": "not a decoded key"}'],
    ["escaped non-field separator", "\\u0072esult\\u003b raw provider scaffold"],
    [
      "encoded object without target",
      JSON.stringify(JSON.stringify({ note: "result but no field" })),
    ],
    [
      "single-quoted JSON without target",
      "'" + JSON.stringify({ note: "result but no field" }) + "'",
    ],
    [
      "backticked nested JSON without target",
      `\`${JSON.stringify({ payload: JSON.stringify({ note: "result but no field" }) })}\``,
    ],
  ])("preserves %s", (_label, markdown) => {
    expect(hasProviderScaffolding(markdown)).toBe(false);
  });
});
