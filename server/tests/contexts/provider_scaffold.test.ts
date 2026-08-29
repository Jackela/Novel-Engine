import { describe, expect, it } from "vitest";

import { hasProviderScaffolding } from "../../src/contexts/studio/application/provider_scaffold.js";

const siblingPaddedScaffold = JSON.stringify(
  JSON.stringify({
    nested: { result: "raw provider scaffold" },
    ...Object.fromEntries(Array.from({ length: 129 }, (_, index) => [`padding_${index}`, index])),
  }),
);

describe("limit sentinels are treated as scaffolding", () => {
  // Existing behavior pinned by the audit: when a scan budget
  // (candidate length, candidate count, walk work, or depth) is exceeded,
  // detection returns true ("treat as guilty") even without a provider key.
  const longJsonCandidate = `{"note":"${"x".repeat(24e3 + 10)}"}`;
  it("flags a JSON candidate exceeding the candidate-length budget", () => {
    expect(hasProviderScaffolding(longJsonCandidate)).toBe(true);
  });
  it("flags a quoted projected target exceeding the candidate-length budget", () => {
    expect(hasProviderScaffolding(`'${longJsonCandidate.slice(1, -1)}'`)).toBe(true);
  });
  it("flags a serialized tree exceeding the walk work budget", () => {
    const wide = JSON.stringify({ items: Array.from({ length: 600 }, (_, i) => i) });
    expect(hasProviderScaffolding(wide)).toBe(true);
  });
  it("flags a serialized tree exceeding the depth budget", () => {
    let deep: unknown = "leaf";
    for (let i = 0; i < 30; i += 1) deep = { nested: deep };
    expect(hasProviderScaffolding(JSON.stringify(deep))).toBe(true);
  });
});

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
    ["single-quoted JSON target", `'${JSON.stringify({ result: "raw provider scaffold" })}'`],
    ["backticked JSON target", `\`${JSON.stringify({ result: "raw provider scaffold" })}\``],
    [
      "trimmed single-quoted decoded child",
      JSON.stringify({
        note: ' \u00a0\u0085\u200B\'{"result":"raw provider scaffold"}\'\u200B\u0085\u00a0 ',
      }),
    ],
    [
      "trimmed backticked decoded child",
      JSON.stringify({
        note: ' \u00a0\u0085\u200B`{"result":"raw provider scaffold"}`\u200B\u0085\u00a0 ',
      }),
    ],
    ["single-quoted JSON with delimiter value", "'{\"result\":\"Mara said 'stop'\"}'"],
    ["backticked JSON with delimiter value", '`{"result":"Mara wrote `stop`"}`'],
    [
      "single-quoted projected JSON with inner delimiter",
      ["'", String.raw`{\u0022result\u0022:\u0022Mara: 'stop'\u0022}`, "'"].join(""),
    ],
    [
      "backticked projected JSON with inner delimiter",
      ["`", String.raw`{\u0022result\u0022:\u0022Mara: `, "`", String.raw`stop\u0022}`, "`"].join(
        "",
      ),
    ],
    ["fenced language JSON", '```json\n{"result":"raw provider scaffold"}\n```'],
    ["zero-width layout indent", "\u200B\\u0072esult\\u003A raw provider scaffold"],
    ["NEL line boundary", "prose\u0085\u200B\\u0065cho\\u003D raw provider scaffold"],
    [
      "nested serialized child",
      `\`${JSON.stringify({ payload: JSON.stringify({ meta: { echo: "raw provider scaffold" } }) })}\``,
    ],
    [
      "neutral outer JSON quoted target",
      JSON.stringify({ note: '\'{"result":"raw provider scaffold"}\'' }),
    ],
    [
      "triple-encoded nested target",
      JSON.stringify(JSON.stringify(JSON.stringify({ meta: { echo: "raw provider scaffold" } }))),
    ],
    [
      "encoded Unicode structural whitespace",
      JSON.stringify(JSON.stringify('{"meta":{},\u00a0"result":"raw provider scaffold"}')),
    ],
    [
      "fully escaped JSON",
      String.raw`\u007b\u0022result\u0022\u003a\u0022raw provider scaffold\u0022\u007d`,
    ],
    ["slash-escaped JSON", String.raw`{\"result\":\"raw provider scaffold\"}`],
    ["escaped layout field", String.raw`{meta:1,\u00a0result:raw provider scaffold}`],
    ["escaped NEL field", String.raw`prose\u0085result:raw provider scaffold`],
    ["escaped zero-width field", String.raw`\u200becho:raw provider scaffold`],
    ["escaped plus list label", String.raw`\u002B result: raw provider scaffold`],
    ["escaped dash list label", String.raw`\u002D result: raw provider scaffold`],
    ["escaped star list label", String.raw`\u002A result: raw provider scaffold`],
    ["escaped ordered dot label", String.raw`1\u002E result: raw provider scaffold`],
    ["escaped ordered close label", String.raw`1\u0029 result: raw provider scaffold`],
    [
      "single-quoted projected JSON",
      String.raw`'{\u0022result\u0022:\u0022raw provider scaffold\u0022}'`,
    ],
    [
      "double-quoted projected JSON",
      String.raw`"{\u0022result\u0022:\u0022raw provider scaffold\u0022}"`,
    ],
    [
      "Unicode-escaped outer double JSON",
      String.raw`\u0022{\u0022result\u0022:\u0022raw provider scaffold\u0022}\u0022`,
    ],
    ["slash-escaped outer double JSON", String.raw`\"{\"result\":\"raw provider scaffold\"}\"`],
    [
      "Unicode-escaped outer double array JSON",
      String.raw`\u0022[{\u0022result\u0022:\u0022raw provider scaffold\u0022}]\u0022`,
    ],
    [
      "Unicode-escaped outer double spaced array JSON",
      String.raw`\u0022[\u00a0{\u0022result\u0022:\u0022raw provider scaffold\u0022}]\u0022`,
    ],
    [
      "slash-escaped outer double array JSON",
      String.raw`\"[{\"result\":\"raw provider scaffold\"}]\"`,
    ],
    [
      "backticked projected JSON",
      ["`", String.raw`{\u0022result\u0022:\u0022raw provider scaffold\u0022}`, "`"].join(""),
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
    ["single-quoted JSON without target", `'${JSON.stringify({ note: "result but no field" })}'`],
    [
      "backticked nested JSON without target",
      `\`${JSON.stringify({ payload: JSON.stringify({ note: "result but no field" }) })}\``,
    ],
    [
      "double-escaped documentation",
      String.raw`\\u007b\\u0022result\\u0022\\u003a\\u0022raw provider scaffold\\u0022\\u007d`,
    ],
    ["escaped unsupported ordered opener", String.raw`1\u0028 result: raw provider scaffold`],
    [
      "real JSON string escapes",
      String.raw`{"note":"Mara quoted \u0022result\u0022 and kept walking."}`,
    ],
    [
      "quoted escaped dialogue",
      String.raw`Mara read '{\u007bresult: turn back\u007d}' and kept walking.`,
    ],
  ])("preserves %s", (_label, markdown) => {
    expect(hasProviderScaffolding(markdown)).toBe(false);
  });
});
