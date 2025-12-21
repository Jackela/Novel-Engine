import type { LogLevel, LogContext, LogEntry } from '@/types/logging';

export interface ILogger {
  debug(message: string, context?: LogContext | Error, extraContext?: LogContext): void;
  info(message: string, context?: LogContext | Error, extraContext?: LogContext): void;
  warn(message: string, context?: LogContext | Error, extraContext?: LogContext): void;
  error(message: string, error?: Error, context?: LogContext): void;
  createLogEntry(level: LogLevel, message: string, context?: LogContext, error?: Error): LogEntry;
  sanitize(context: Record<string, unknown>): Record<string, unknown>;
  setMinLevel(level: LogLevel): void;
  getMinLevel(): LogLevel;
}
