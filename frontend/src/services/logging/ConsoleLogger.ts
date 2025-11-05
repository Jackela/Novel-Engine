import type { ILogger } from './ILogger';
import type { LogLevel, LogContext, LogEntry, LoggerConfig } from '../../types/logging';
import { Sanitizer } from './Sanitizer';
import { LogLevel as LogLevelEnum } from '../../types/logging';

export class ConsoleLogger implements ILogger {
  private config: LoggerConfig;

  constructor(config?: Partial<LoggerConfig>) {
    this.config = {
      minLevel: config?.minLevel ?? LogLevelEnum.DEBUG,
      environment: config?.environment ?? 'development',
      includeTimestamp: config?.includeTimestamp ?? true,
      includeComponent: config?.includeComponent ?? true,
      enableRemoteLogging: config?.enableRemoteLogging ?? false,
      ...(config?.remoteUrl !== undefined && { remoteUrl: config.remoteUrl }),
    };
  }

  debug(message: string, context?: LogContext): void {
    if (this.shouldLog(LogLevelEnum.DEBUG)) {
      const entry = this.createLogEntry(LogLevelEnum.DEBUG, message, context);
      console.log(`[DEBUG] ${entry.message}`, entry.context || {});
    }
  }

  info(message: string, context?: LogContext): void {
    if (this.shouldLog(LogLevelEnum.INFO)) {
      const entry = this.createLogEntry(LogLevelEnum.INFO, message, context);
      console.info(`[INFO] ${entry.message}`, entry.context || {});
    }
  }

  warn(message: string, context?: LogContext): void {
    if (this.shouldLog(LogLevelEnum.WARN)) {
      const entry = this.createLogEntry(LogLevelEnum.WARN, message, context);
      console.warn(`[WARN] ${entry.message}`, entry.context || {});
    }
  }

  error(message: string, error?: Error, context?: LogContext): void {
    if (this.shouldLog(LogLevelEnum.ERROR)) {
      const entry = this.createLogEntry(LogLevelEnum.ERROR, message, context, error);
      console.error(`[ERROR] ${entry.message}`, entry.error || {}, entry.context || {});
    }
  }

  createLogEntry(level: LogLevel, message: string, context?: LogContext, error?: Error): LogEntry {
    const sessionId = this.getSessionId();
    
    return {
      id: crypto.randomUUID(),
      level,
      message,
      timestamp: new Date().toISOString(),
      ...(context?.component !== undefined && { component: context.component }),
      ...(context?.action !== undefined && { action: context.action }),
      ...(context?.userId !== undefined && { userId: context.userId }),
      ...(sessionId !== undefined && { sessionId }),
      ...(context && { context: this.sanitize(context as Record<string, unknown>) }),
      ...(error && {
        error: {
          message: error.message,
          name: error.name,
          ...(this.config.environment === 'development' && error.stack && { stack: error.stack }),
        },
      }),
    };
  }

  sanitize(context: Record<string, unknown>): Record<string, unknown> {
    return Sanitizer.sanitize(context) as Record<string, unknown>;
  }

  setMinLevel(level: LogLevel): void {
    this.config.minLevel = level;
  }

  getMinLevel(): LogLevel {
    return this.config.minLevel;
  }

  private shouldLog(level: LogLevel): boolean {
    const levels = [LogLevelEnum.DEBUG, LogLevelEnum.INFO, LogLevelEnum.WARN, LogLevelEnum.ERROR];
    const minIndex = levels.indexOf(this.config.minLevel);
    const currentIndex = levels.indexOf(level);
    return currentIndex >= minIndex;
  }

  private getSessionId(): string | undefined {
    try {
      return sessionStorage.getItem('sessionId') ?? undefined;
    } catch {
      return undefined;
    }
  }
}
