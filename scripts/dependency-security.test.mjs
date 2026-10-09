import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { test } from "node:test";

const require = createRequire(import.meta.url);
const braces = require("@novel-engine/braces");
const golden = JSON.parse(
  readFileSync(new URL("../vendor/braces/semantics.json", import.meta.url)),
);

test("the installed implementation matches the reviewable source SHA manifest", () => {
  const source = JSON.parse(readFileSync(new URL("../vendor/braces/SOURCE.json", import.meta.url)));
  assert.equal(
    createHash("sha256")
      .update(readFileSync(new URL("../vendor/braces/semantics.json", import.meta.url)))
      .digest("hex"),
    source.reusedFrom.semanticsSha256,
  );
  assert.equal(
    createHash("sha256")
      .update(readFileSync(new URL("../vendor/braces/security.patch", import.meta.url)))
      .digest("hex"),
    source.reusedFrom.securityPatchSha256,
  );
  const directory = dirname(require.resolve("@novel-engine/braces"));
  assert.equal(
    createHash("sha256")
      .update(readFileSync(join(directory, "LICENSE")))
      .digest("hex"),
    source.upstream.licenseSha256,
  );
  for (const [file, expected] of Object.entries(source.patchedSourceSha256)) {
    const actual = createHash("sha256")
      .update(readFileSync(join(directory, file)))
      .digest("hex");
    assert.equal(actual, expected, file);
  }
});

test("all six public APIs preserve 732 captured upstream semantics below the hard limits", () => {
  assert.equal(golden.cases.length, 732);
  assert.deepEqual(Object.keys(braces), ["parse", "stringify", "compile", "expand", "create"]);
  for (const fixture of golden.cases) {
    const invoke = () => {
      if (fixture.method === "call") return braces(fixture.input, fixture.options);
      const value = braces[fixture.method](fixture.input, fixture.options);
      if (fixture.method !== "parse") return value;
      return JSON.parse(
        JSON.stringify(value, (key, value) =>
          key === "parent" || key === "prev" ? undefined : value,
        ),
      );
    };
    if (fixture.error) assert.throws(invoke, fixture.error);
    else
      assert.deepEqual(
        invoke(),
        fixture.result,
        `${fixture.method}: ${JSON.stringify(fixture.input)} ${JSON.stringify(fixture.options)}`,
      );
  }
});

for (const method of ["compile", "expand", "parse", "stringify", "create"]) {
  test(`${method} rejects the original 9003-character / 4500-level advisory PoC before recursion`, () => {
    assert.throws(
      () => braces[method](`${"{".repeat(4500)}a,b${"}".repeat(4500)}`),
      /Brace nesting exceeds 32 levels/,
    );
  });
}

test("32 nesting levels are accepted and 33 are rejected, including mixed braces and parentheses", () => {
  assert.doesNotThrow(() => braces.compile(`${"{".repeat(32)}x${"}".repeat(32)}`));
  assert.throws(() => braces.compile(`${"{".repeat(33)}x${"}".repeat(33)}`), /nesting/);
  assert.throws(() => braces.compile(`${"(".repeat(33)}x${")".repeat(33)}`), /nesting/);
  assert.throws(() => braces.compile(`${"{(".repeat(17)}x${")}".repeat(17)}`), /nesting/);
  // Quoted and escaped literals do not create AST nesting and retain upstream lexical rules.
  assert.doesNotThrow(() => braces.compile(`"${"{".repeat(4999)}"`));
  assert.doesNotThrow(() => braces.compile("\\{".repeat(5000)));
});

for (const method of ["compile", "expand", "stringify"]) {
  test(`${method} also bounds supplied ASTs and cannot bypass the parser guard`, () => {
    let ast = { type: "text", value: "x" };
    for (let count = 0; count < 4500; count++) ast = { type: "root", nodes: [ast] };
    assert.throws(() => braces[method](ast), /AST nesting/);
    const cycle = { type: "root", nodes: [] };
    cycle.nodes.push(cycle);
    assert.throws(() => braces[method](cycle), /AST nesting/);
    const parentCycle = { type: "root", nodes: [] };
    parentCycle.parent = parentCycle;
    assert.throws(() => braces[method](parentCycle), /parent chain/);
    assert.throws(
      () =>
        braces[method]({
          type: "root",
          nodes: Array.from({ length: 20003 }, () => ({ type: "text", value: "x" })),
        }),
      /node limit/,
    );
    assert.throws(() => braces[method]({ type: "text", value: "x".repeat(1000001) }), /text limit/);
  });
}

test("expansion is bounded before range allocation and Cartesian products, regardless of options", () => {
  assert.equal(braces.expand("{1..1000}").length, 1000);
  for (const pattern of ["{1..1001}", "{10000000..1}", "{1..10000000}"]) {
    assert.throws(() => braces.expand(pattern, { rangeLimit: false }), /exceeds/);
  }
  assert.equal(braces.expand("{a,b}".repeat(9)).length, 512);
  assert.throws(() => braces.expand("{a,b}".repeat(10)), /1000 results/);
  assert.equal(braces(Array.from({ length: 1000 }, () => "a")).length, 1000);
  assert.throws(() => braces(Array.from({ length: 1001 }, () => "a")), /1000 patterns/);
  assert.throws(() => braces.compile("x".repeat(10001)), /max characters/);
});

test("unsafe numeric endpoints and steps terminate with a controlled error in a bounded subprocess", () => {
  // An earlier guard accepted the first pattern and fill-range's +1 never progressed.
  const code = `
    const assert = require('node:assert/strict');
    const braces = require('@novel-engine/braces');
    const patterns = [
      '{9007199254740992..9007199254740994}',
      '{9007199254740994..9007199254740992}',
      '{-9007199254740992..-9007199254740994}',
      '{-9007199254740994..-9007199254740992}',
      '{999999999999999999999999999999999999999..1}',
      '{1..-999999999999999999999999999999999999999}',
      '{ 9007199254740992 .. 9007199254740994 }',
      '{0x20000000000000..0x20000000000002}',
      '{0b100000000000000000000000000000000000000000000000000000..0b100000000000000000000000000000000000000000000000000010}',
    ];
    for (const method of ['compile', 'expand']) {
      for (const pattern of patterns) assert.throws(() => braces[method](pattern, { rangeLimit: false }), /safe integers/);
      for (const step of [NaN, Infinity, -Infinity, 'NaN', 'Infinity', Number.MAX_SAFE_INTEGER + 1, 0.5]) {
        assert.throws(() => braces[method]('{1..5}', { step }), /safe integer/);
        assert.throws(() => braces[method]('{a..z}', { step }), /safe integer/);
      }
    }
  `;
  const result = spawnSync(process.execPath, ["--max-old-space-size=128", "-e", code], {
    encoding: "utf8",
    timeout: 1000,
  });
  assert.equal(result.error, undefined);
  assert.equal(result.signal, null);
  assert.equal(result.status, 0, result.stderr);
});

test("safe endpoints, signed/zero/padded steps, letters, and efficient regex ranges retain semantics", () => {
  assert.deepEqual(braces.expand("{9007199254740989..9007199254740991}"), [
    "9007199254740989",
    "9007199254740990",
    "9007199254740991",
  ]);
  assert.deepEqual(braces.expand("{-9007199254740991..-9007199254740989}"), [
    "-9007199254740991",
    "-9007199254740990",
    "-9007199254740989",
  ]);
  assert.deepEqual(braces.expand("{01..05..02}"), ["01", "03", "05"]);
  assert.deepEqual(braces.expand("{5..1..-2}"), ["5", "3", "1"]);
  assert.deepEqual(braces.expand("{a..f..2}"), ["a", "c", "e"]);
  assert.deepEqual(braces.expand("{a..c}", { step: 0 }), ["a", "b", "c"]);
  assert.match(braces.compile("{1..1000000}"), /1000000/);
});

for (const chain of [
  {
    owner: "@fission-ai/openspec",
    entry: "@fission-ai/openspec",
    dependencies: ["fast-glob", "micromatch"],
  },
  {
    owner: "react-doctor",
    entry: "../frontend/package.json",
    dependencies: ["react-doctor", "deslop-js", "fast-glob", "micromatch"],
  },
]) {
  test(
    chain.owner +
      " actually resolves the guarded implementation through its installed dependencies",
    () => {
      let consumer = createRequire(require.resolve(chain.entry));
      let matching;
      for (const dependency of chain.dependencies) {
        const entry = consumer.resolve(dependency);
        consumer = createRequire(entry);
        if (dependency === "micromatch") matching = require(entry);
      }
      assert.equal(consumer("braces"), braces);
      assert.throws(
        () => consumer("braces").expand(`${"{".repeat(4500)}a,b${"}".repeat(4500)}`),
        /Brace nesting exceeds 32 levels/,
      );
      assert.deepEqual(matching(["server/src/main.ts", "README.md"], "**/*.{ts,tsx}"), [
        "server/src/main.ts",
      ]);
    },
  );
}
