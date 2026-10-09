
'use strict';

// Hard ceilings cannot be disabled by options. Existing valid patterns below them keep upstream semantics.
const MAX_DEPTH = 32;
const MAX_NODES = 20002;
const MAX_RESULTS = 1000;
const MAX_OUTPUT_LENGTH = 1000000;

function assertAst(ast) {
  const stack = [{ node: ast, depth: 0 }];
  let count = 0;
  let length = 0;
  while (stack.length) {
    const { node, depth } = stack.pop();
    if (++count > MAX_NODES) throw new RangeError('Brace AST exceeds node limit');
    if (depth > MAX_DEPTH + 1) throw new RangeError('Brace AST nesting exceeds 32 levels');
    if (!node || typeof node !== 'object') throw new TypeError('Expected a brace AST node');
    if (node.value != null) length += String(node.value).length;
    if (length > MAX_OUTPUT_LENGTH) throw new RangeError('Brace AST exceeds text limit');
    let parent = node.parent;
    let parentDepth = 0;
    while (parent) {
      if (++parentDepth > MAX_DEPTH + 1) throw new RangeError('Brace AST parent chain exceeds 32 levels');
      parent = parent.parent;
    }
    if (Array.isArray(node.nodes)) {
      if (count + stack.length + node.nodes.length > MAX_NODES) throw new RangeError('Brace AST exceeds node limit');
      for (const child of node.nodes) stack.push({ node: child, depth: depth + 1 });
    }
  }
}

function assertResults(results) {
  if (results.length > MAX_RESULTS) throw new RangeError('Brace expansion exceeds 1000 results');
  let length = 0;
  for (const result of results) {
    if (result != null) length += String(result).length;
    if (length > MAX_OUTPUT_LENGTH) throw new RangeError('Brace expansion exceeds text limit');
  }
}

function assertRange(args, options) {
  const [start, end, patternStep] = args;
  const rawStep = Number(patternStep ?? options.step ?? 1);
  if (!Number.isSafeInteger(rawStep)) throw new RangeError('Brace range step must be a safe integer');
  const step = Math.max(Math.abs(rawStep), 1);
  const numeric = value => typeof value === 'number' ||
    (typeof value === 'string' && (Number.isInteger(Number(value)) ||
      /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i.test(value.trim())));
  for (const endpoint of [start, end]) {
    if (numeric(endpoint) && !Number.isSafeInteger(Number(endpoint))) {
      throw new RangeError('Brace range endpoints must be safe integers');
    }
  }
  let first;
  let last;
  if (numeric(start) && numeric(end)) {
    first = Number(start);
    last = Number(end);
  } else {
    // fill-range treats mixed single characters as a character sequence.
    if (typeof start !== 'string' || typeof end !== 'string' ||
        (start.length !== 1 && !Number.isSafeInteger(Number(start))) ||
        (end.length !== 1 && !Number.isSafeInteger(Number(end)))) return;
    first = start.charCodeAt(0);
    last = end.charCodeAt(0);
  }
  // Unit-step regex compilation does not enumerate the range; its safe endpoints are still mandatory.
  if (options.toRegex === true && step === 1) return;
  const count = Math.floor(Math.abs(last - first) / step) + 1;
  if (count > MAX_RESULTS) throw new RangeError('Brace range exceeds 1000 results');
}

module.exports = { MAX_DEPTH, MAX_NODES, MAX_RESULTS, assertAst, assertResults, assertRange };
