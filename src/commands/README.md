# Commands

Every user-initiated mutation is a command. No exceptions.

See: `DOCS/Architecture/Architectural_Mandates.md` §1
See: `DOCS/Architecture/ADR_000_EXAMPLE.md`

---

## How to Create a New Command

1. Create `[ActionName]Command.ts` in this directory
2. Implement `IUndoableCommand`
3. Capture all state needed for `undo()` in the constructor
4. Execute through `CommandManager`, never directly

```typescript
// Template
import { IUndoableCommand } from './ICommand';

interface RenameItemSnapshot {
  previousName: string;
}

export class RenameItemCommand implements IUndoableCommand {
  readonly description: string;
  private snapshot: RenameItemSnapshot;

  constructor(
    private readonly itemId: string,
    private readonly newName: string,
    private readonly service: IItemService,
    snapshot: RenameItemSnapshot,
  ) {
    this.snapshot = snapshot;
    this.description = `Rename item ${itemId} to "${newName}"`;
  }

  async execute(): Promise<void> {
    await this.service.rename(this.itemId, this.newName);
  }

  async undo(): Promise<void> {
    await this.service.rename(this.itemId, this.snapshot.previousName);
  }
}
```

## Batch Commands

To group multiple commands into a single undo entry:

```typescript
export class BatchCommand implements IUndoableCommand {
  readonly description: string;

  constructor(
    private readonly commands: IUndoableCommand[],
    description: string,
  ) {
    this.description = description;
  }

  async execute(): Promise<void> {
    for (const cmd of this.commands) {
      await cmd.execute();
    }
  }

  async undo(): Promise<void> {
    // Undo in reverse order
    for (const cmd of [...this.commands].reverse()) {
      await cmd.undo();
    }
  }
}
```

## Commands in This Directory

| Command | What It Does | Undo Behavior |
|---------|-------------|---------------|
| *(none yet — add as you create commands)* | | |
