// Ensure React 18 treats the Vitest environment as act-compatible before any React import runs.
if (typeof (globalThis as any).IS_REACT_ACT_ENVIRONMENT === 'undefined') {
  (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
}
