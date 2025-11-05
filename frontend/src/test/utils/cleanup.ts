type Cleanup = () => Promise<void> | void;

const cleaners: Cleanup[] = [];

export const registerCleanup = (fn: Cleanup): void => {
  cleaners.push(fn);
};

export const runCleanups = async (): Promise<void> => {
  const fns = cleaners.splice(0);
  for (const fn of fns) {
    try {
      await fn();
    } catch (error) {
      console.error('Cleanup function failed:', error);
    }
  }
};

export const clearCleanups = (): void => {
  cleaners.length = 0;
};
