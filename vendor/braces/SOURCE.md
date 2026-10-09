# Controlled braces replacement

This private package is a local security-maintained copy of MIT-licensed `braces` 3.0.3. It is named `@novel-engine/braces`, without a version field (the repository keeps product identity solely in `server/package.json`), and is not published or represented as an upstream fix. The root override replaces the actual OpenSpec and React Doctor micromatch implementation. It does not ignore an advisory or relabel an unchanged vulnerable implementation.

`SOURCE.json` pins the upstream commit, verified official tarball integrity, original source SHA-256 values, patched source SHA-256 values, and fixed bounds. `LICENSE` preserves MIT attribution. `security.patch` is the complete source difference against that verified upstream snapshot. `POC.json` records the original failure and controlled rejection on Node 24. `semantics.json` captures the unmodified upstream's normal API outputs as a compatibility oracle.

## Root cause and entry points

[GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm) and [upstream issue 70](https://github.com/micromatch/braces/issues/70) describe unchecked AST nesting. The 10,000-character limit admits a 9,003-character pattern with 4,500 nested braces. The upstream recursive walkers can exhaust the stack; in the Novel Engine Node 24.19.0 reproduction, `expand` overflowed while `compile` returned. `stringify` also recurses; `parse` invokes it for malformed ranges. Expansion additionally recurses through intermediate arrays.

All six public interfaces remain: the callable function, `parse`, `stringify`, `compile`, `expand`, and `create`. String parsing checks its actual lexical brace/parenthesis stack before nesting can grow. Every AST walker validates externally supplied ASTs iteratively before recursing, including child and parent cycles. Array flattening and Cartesian append now use iteration. Numeric range endpoints and steps must be safe integers before compilation or expansion. This also prevents a unit increment from stalling beyond the JavaScript safe-integer limit, found during independent review. Expansion counts are bounded before allocation, including descending ranges and `rangeLimit: false`.

## Fixed boundaries

| Resource                                          |             Hard maximum |
| ------------------------------------------------- | -----------------------: |
| Syntactic brace and parenthesis nesting, combined |                       32 |
| AST depth including the final leaf                |                       33 |
| AST/flattening node visits                        |                   20,002 |
| Pattern characters (original upstream limit)      |                   10,000 |
| Input pattern count and expansion results         |                    1,000 |
| Numeric endpoints and steps                       | JavaScript safe integers |
| AST/output text characters                        |                1,000,000 |

Options cannot disable these bounds. Inputs beyond them receive an explicit `RangeError` before uncontrolled recursion or expansion. Ordinary patterns below the limits retain upstream output and ordering, including escapes, quotes, malformed literal braces, ranges, noempty/nodupes, arrays, and AST input. Arbitrary caller-supplied callbacks or JavaScript getters remain trusted executable code; this package does not sandbox them.

## Executable evidence and rollback

`pnpm run test:dependency-security` checks installed source hashes, 732 captured semantic comparisons, the original PoC, 32/33-depth boundaries, AST bypass/cycles, broad ASTs, large and descending ranges, Cartesian growth, pattern arrays, and actual resolution through both active OpenSpec and React Doctor dependency chains. CI runs it before the unchanged strict audit gate. All application test layers, lint, typecheck, build, and normal Chromium E2E must also pass before compatibility is claimed.

The reused MIT source was independently reviewed for ClarityOKR on 2026-10-09, including an unsafe-integer bypass that was corrected and rechecked. Novel Engine independently verified the official tarball integrity, original source hashes and all 732 upstream semantic fixtures before applying it. `SOURCE.json` separates that inherited review from this candidate, whose installed dependency chains and repository checks require independent review. No upstream fix has been published. `POC.json` records this repository’s actual before/after reproduction, including the unsafe range’s bounded subprocess outcome.

To roll back, remove the root `braces` override and the direct private test dependency, resolve the lock, and rerun all gates. That restores vulnerable upstream 3.0.3 and the strict audit failure. Do not roll back by excluding or ignoring the advisory. Replace this copy with a verified published upstream fix when one exists; compare API semantics and rerun the security tests first.
