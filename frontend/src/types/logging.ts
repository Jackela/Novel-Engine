export enum LogLevel {
  DEBUG = 'debug',
  INFO = 'info',
  WARN = 'warn',
  ERROR = 'error',
}

export interface LogContext {
  component?: string;
  action?: string;
  userId?: string;
  [key: string]: unknown;
}

export interface LogEntry {
  id: string;
  level: LogLevel;
  message: string;
  timestamp: string;
  component?: string;
  action?: string;
  userId?: string;
  sessionId?: string;
  context?: Record<string, unknown>;
  error?: {
    message: string;
    stack?: string;
    name: string;
  };
}

export interface LoggerConfig {
  minLevel: LogLevel;
  environment: 'development' | 'production';
  includeTimestamp: boolean;
  includeComponent: boolean;
  enableRemoteLogging: boolean;
  remoteUrl?: string;
}
