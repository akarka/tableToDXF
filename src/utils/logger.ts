/**
 * Structured logger.
 * Outputs key=value lines parseable by log aggregators (Datadog, Grafana Loki, etc.)
 *
 * Usage:
 *   const logger = createLogger({ prefix: 'UserService', level: 'info' });
 *   logger.info('create', { userId, email });
 *   logger.error('save failed', { userId, reason: err.message });
 *
 * See: DOCS/Architecture/Architectural_Mandates.md §5
 */

export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

export interface ILogger {
  debug(message: string, context?: Record<string, unknown>): void;
  info(message: string, context?: Record<string, unknown>): void;
  warn(message: string, context?: Record<string, unknown>): void;
  error(message: string, context?: Record<string, unknown>): void;
}

const LEVELS: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
};

export function createLogger(options: {
  prefix?: string;
  level?: LogLevel;
  output?: (line: string) => void;
} = {}): ILogger {
  const minLevel = LEVELS[options.level ?? 'info'];
  const prefix = options.prefix ? `[${options.prefix}] ` : '';
  const write = options.output ?? console.log;

  function log(level: LogLevel, message: string, context?: Record<string, unknown>): void {
    if (LEVELS[level] < minLevel) return;

    const timestamp = new Date().toISOString();
    const contextStr = context
      ? ' ' + Object.entries(context)
          .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
          .join(' ')
      : '';

    write(`${timestamp} ${level.toUpperCase()} ${prefix}${message}${contextStr}`);
  }

  return {
    debug: (msg, ctx) => log('debug', msg, ctx),
    info: (msg, ctx) => log('info', msg, ctx),
    warn: (msg, ctx) => log('warn', msg, ctx),
    error: (msg, ctx) => log('error', msg, ctx),
  };
}

/** Null logger for use in tests where log output is irrelevant. */
export const nullLogger: ILogger = {
  debug: () => {},
  info: () => {},
  warn: () => {},
  error: () => {},
};
