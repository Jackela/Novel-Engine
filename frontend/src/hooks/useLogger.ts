import { useCallback, useMemo } from 'react';
import { logger } from '../services/logging/LoggerFactory';
import type { LogContext } from '../types/logging';

export function useLogger(componentName?: string) {
  const baseContext: LogContext = useMemo(
    () => ({ component: componentName }),
    [componentName]
  );

  const debug = useCallback(
    (message: string, context?: LogContext) => {
      logger.debug(message, { ...baseContext, ...context });
    },
    [baseContext]
  );

  const info = useCallback(
    (message: string, context?: LogContext) => {
      logger.info(message, { ...baseContext, ...context });
    },
    [baseContext]
  );

  const warn = useCallback(
    (message: string, context?: LogContext) => {
      logger.warn(message, { ...baseContext, ...context });
    },
    [baseContext]
  );

  const error = useCallback(
    (message: string, err?: Error, context?: LogContext) => {
      logger.error(message, err, { ...baseContext, ...context });
    },
    [baseContext]
  );

  return { debug, info, warn, error };
}
