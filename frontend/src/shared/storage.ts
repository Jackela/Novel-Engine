export const sessionStorageKey = 'novel-engine-session';

export const safeStorage = {
  read<T>(key: string): T | null {
    if (typeof window === 'undefined') {
      return null;
    }

    const raw = window.localStorage.getItem(key);
    if (!raw) {
      return null;
    }

    try {
      return JSON.parse(raw) as T;
    } catch {
      return null;
    }
  },

  write<T>(key: string, value: T) {
    if (typeof window === 'undefined') {
      return;
    }

    window.localStorage.setItem(key, JSON.stringify(value));
  },

  remove(key: string) {
    if (typeof window === 'undefined') {
      return;
    }

    window.localStorage.removeItem(key);
  },
};
