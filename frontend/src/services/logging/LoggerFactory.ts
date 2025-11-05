import type { ILogger } from './ILogger';
import { ConsoleLogger } from './ConsoleLogger';
import { LogLevel } from '../../types/logging';

export class LoggerFactory {
  private static instance: ILogger | null = null;

  static create(): ILogger {
    if (this.instance) {
      return this.instance;
    }

    const environment = process.env.NODE_ENV === 'production' ? 'production' : 'development';
    const minLevel = process.env.NODE_ENV === 'production' ? LogLevel.WARN : LogLevel.DEBUG;

    this.instance = new ConsoleLogger({ environment, minLevel });
    return this.instance;
  }

  static reset(): void {
    this.instance = null;
  }
}

// Global logger instance
export const logger = LoggerFactory.create();
