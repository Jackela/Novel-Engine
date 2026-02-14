const isSlowEnv =
  Boolean(process.env.CI) ||
  Boolean(process.env.WSL_DISTRO_NAME) ||
  Boolean(process.env.WSLENV);

const rawMultiplier = Number(process.env.PLAYWRIGHT_PERF_MULTIPLIER);
const defaultMultiplier = isSlowEnv ? 2.5 : 1;

export const perfMultiplier =
  Number.isFinite(rawMultiplier) && rawMultiplier > 0 ? rawMultiplier : defaultMultiplier;

export const scalePerf = (ms: number) => Math.round(ms * perfMultiplier);
