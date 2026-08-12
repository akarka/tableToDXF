import { IUndoableCommand, CommandResult } from './ICommand';

/**
 * Executes commands and maintains an undo/redo stack.
 *
 * Usage:
 *   const manager = new CommandManager(logger, { capacity: 20 });
 *   const result = await manager.execute(new RenameItemCommand(...));
 *   await manager.undo();
 *   await manager.redo();
 */
export class CommandManager {
  private readonly undoStack: IUndoableCommand[] = [];
  private readonly redoStack: IUndoableCommand[] = [];
  private readonly capacity: number;
  private readonly logger: ILogger;

  constructor(logger: ILogger, options: { capacity?: number } = {}) {
    this.logger = logger;
    this.capacity = options.capacity ?? 20;
  }

  async execute<T = void>(command: IUndoableCommand): Promise<CommandResult<T>> {
    this.logger.info('CommandManager.execute', { description: command.description });

    try {
      await command.execute();

      this.undoStack.push(command);
      this.redoStack.length = 0; // new execution clears the redo branch

      // Enforce capacity cap (circular buffer behavior)
      if (this.undoStack.length > this.capacity) {
        this.undoStack.shift();
      }

      return { success: true, command };
    } catch (err) {
      this.logger.error('CommandManager.execute failed', {
        description: command.description,
        reason: err instanceof Error ? err.message : String(err),
      });
      return {
        success: false,
        error: err instanceof Error ? err : new Error(String(err)),
        command,
      };
    }
  }

  async undo(): Promise<boolean> {
    const command = this.undoStack.pop();
    if (!command) {
      this.logger.info('CommandManager.undo: stack is empty');
      return false;
    }

    this.logger.info('CommandManager.undo', { description: command.description });

    try {
      await command.undo();
      this.redoStack.push(command);
      return true;
    } catch (err) {
      this.logger.error('CommandManager.undo failed', {
        description: command.description,
        reason: err instanceof Error ? err.message : String(err),
      });
      // Push back — state is unknown; safest to not modify the stack further
      this.undoStack.push(command);
      throw err;
    }
  }

  async redo(): Promise<boolean> {
    const command = this.redoStack.pop();
    if (!command) {
      this.logger.info('CommandManager.redo: stack is empty');
      return false;
    }

    this.logger.info('CommandManager.redo', { description: command.description });

    try {
      await command.execute();
      this.undoStack.push(command);
      return true;
    } catch (err) {
      this.logger.error('CommandManager.redo failed', {
        description: command.description,
        reason: err instanceof Error ? err.message : String(err),
      });
      this.redoStack.push(command);
      throw err;
    }
  }

  get canUndo(): boolean {
    return this.undoStack.length > 0;
  }

  get canRedo(): boolean {
    return this.redoStack.length > 0;
  }

  get undoDescription(): string | undefined {
    return this.undoStack.at(-1)?.description;
  }

  get redoDescription(): string | undefined {
    return this.redoStack.at(-1)?.description;
  }

  /** For audit logging: returns descriptions of all commands in undo stack, newest first. */
  getHistory(): string[] {
    return [...this.undoStack].reverse().map((c) => c.description);
  }

  clearHistory(): void {
    this.undoStack.length = 0;
    this.redoStack.length = 0;
    this.logger.info('CommandManager.clearHistory');
  }
}

// Minimal logger interface — replace with your actual logger type
export interface ILogger {
  info(message: string, context?: Record<string, unknown>): void;
  error(message: string, context?: Record<string, unknown>): void;
}
