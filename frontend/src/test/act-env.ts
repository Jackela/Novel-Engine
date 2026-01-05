// Ensure React 18 treats the Vitest environment as act-compatible before any React import runs.
type ActEnvGlobal = typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean };
const actEnvGlobal = globalThis as ActEnvGlobal;
if (typeof actEnvGlobal.IS_REACT_ACT_ENVIRONMENT === 'undefined') {
  actEnvGlobal.IS_REACT_ACT_ENVIRONMENT = true;
}
