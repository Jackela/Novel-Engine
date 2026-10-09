'use strict';

const fill = require('fill-range');
const stringify = require('./stringify');
const utils = require('./utils');
const { assertAst, assertRange, assertResults } = require('./limits');

const append = (queue = '', stash = '', enclose = false) => {
  const result = [];
  queue = utils.flatten([].concat(queue));
  stash = utils.flatten([].concat(stash));
  if (!stash.length) return queue;
  if (!queue.length) {
    const values = enclose ? stash.map(ele => `{${ele}}`) : stash;
    assertResults(values);
    return values;
  }
  if (queue.length * stash.length > 1000) throw new RangeError('Brace expansion exceeds 1000 results');
  let length = 0;
  for (const item of queue) {
    for (let ele of stash) {
      if (enclose === true && typeof ele === 'string') ele = `{${ele}}`;
      const value = item + ele;
      if (typeof value === 'string') length += value.length;
      if (length > 1000000) throw new RangeError('Brace expansion exceeds text limit');
      result.push(value);
    }
  }
  return result;
};

const expand = (ast, options = {}) => {
  assertAst(ast);
  const rangeLimit = options.rangeLimit === undefined ? 1000 : options.rangeLimit;

  const walk = (node, parent = {}) => {
    node.queue = [];

    let p = parent;
    let q = parent.queue;

    while (p.type !== 'brace' && p.type !== 'root' && p.parent) {
      p = p.parent;
      q = p.queue;
    }

    if (node.invalid || node.dollar) {
      q.push(append(q.pop(), stringify(node, options)));
      return;
    }

    if (node.type === 'brace' && node.invalid !== true && node.nodes.length === 2) {
      q.push(append(q.pop(), ['{}']));
      return;
    }

    if (node.nodes && node.ranges > 0) {
      const args = utils.reduce(node.nodes);

      if (utils.exceedsLimit(...args, options.step, rangeLimit)) {
        throw new RangeError('expanded array length exceeds range limit. Use options.rangeLimit to increase or disable the limit.');
      }

      assertRange(args, options);
      let range = fill(...args, options);
      if (range.length === 0) {
        range = stringify(node, options);
      }

      q.push(append(q.pop(), range));
      node.nodes = [];
      return;
    }

    const enclose = utils.encloseBrace(node);
    let queue = node.queue;
    let block = node;

    while (block.type !== 'brace' && block.type !== 'root' && block.parent) {
      block = block.parent;
      queue = block.queue;
    }

    for (let i = 0; i < node.nodes.length; i++) {
      const child = node.nodes[i];

      if (child.type === 'comma' && node.type === 'brace') {
        if (i === 1) queue.push('');
        queue.push('');
        continue;
      }

      if (child.type === 'close') {
        q.push(append(q.pop(), queue, enclose));
        continue;
      }

      if (child.value && child.type !== 'open') {
        queue.push(append(queue.pop(), child.value));
        continue;
      }

      if (child.nodes) {
        walk(child, node);
      }
    }

    return queue;
  };

  return utils.flatten(walk(ast));
};

module.exports = expand;
