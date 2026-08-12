/**
 * Every user-initiated mutation must implement this interface.
 * See: DOCS/Architecture/Architectural_Mandates.md §1
 * See: DOCS/Architecture/ADR_000_EXAMPLE.md
 */
export interface IUndoableCommand {
  /** Apply the mutation. Must be idempotent on consecutive calls (or guard against re-execution). */
  execute(): Promise<void>;

  /** Reverse the mutation to the exact state before execute() was called. */
  undo(): Promise<void>;

  /** Human-readable description for audit logs and undo UI. */
  readonly description: string;
}

/**
 * Result returned by CommandManager.execute().
 * Carry the command through the result so callers can inspect what was done.
 */
export interface CommandResult<T = void> {
  success: boolean;
  data?: T;
  error?: Error;
  command: IUndoableCommand;
}
