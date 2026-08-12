/**
 * [DOMAIN]Service — [one-line description of what this service manages]
 *
 * Responsibilities:
 * - [responsibility 1]
 * - [responsibility 2]
 *
 * This service is stateless. All mutations must be triggered from Command classes.
 * See: DOCS/Architecture/Architectural_Mandates.md §1, §2
 */

// ---------------------------------------------------------------------------
// Dependency Interfaces
// (Define here; inject via constructor; swap in tests)
// ---------------------------------------------------------------------------

export interface I[DOMAIN]Repository {
  findById(id: string): Promise<[DOMAIN]Entity | null>;
  findAll(): Promise<[DOMAIN]Entity[]>;
  save(entity: [DOMAIN]Entity): Promise<void>;
  delete(id: string): Promise<void>;
}

export interface ILogger {
  info(message: string, context?: Record<string, unknown>): void;
  error(message: string, context?: Record<string, unknown>): void;
  warn(message: string, context?: Record<string, unknown>): void;
}

// ---------------------------------------------------------------------------
// Domain Types
// ---------------------------------------------------------------------------

export interface [DOMAIN]Entity {
  id: string;
  // [add fields]
  createdAt: Date;
  updatedAt: Date;
}

export interface Create[DOMAIN]Dto {
  // [required fields for creation]
}

export interface Update[DOMAIN]Dto {
  id: string;
  // [fields that can be updated]
}

// ---------------------------------------------------------------------------
// Domain Errors
// (Stable error codes allow i18n and support tooling)
// ---------------------------------------------------------------------------

export class [DOMAIN]NotFoundError extends Error {
  readonly code = '[DOMAIN]_NOT_FOUND';
  constructor(id: string) {
    super(`[DOMAIN] not found: ${id}`);
  }
}

export class [DOMAIN]ConflictError extends Error {
  readonly code = '[DOMAIN]_CONFLICT';
  constructor(detail: string) {
    super(detail);
  }
}

// ---------------------------------------------------------------------------
// Service
// ---------------------------------------------------------------------------

export class [DOMAIN]Service {
  constructor(
    private readonly repo: I[DOMAIN]Repository,
    private readonly logger: ILogger,
  ) {}

  /**
   * [What this method does in one sentence.]
   * Called from: [DOMAIN]CreateCommand.execute()
   */
  async create(dto: Create[DOMAIN]Dto): Promise<[DOMAIN]Entity> {
    this.logger.info('[DOMAIN]Service.create', { /* relevant fields */ });

    // 1. Domain validation (not boundary validation — that happens in handlers)
    // [validate business rules, e.g., uniqueness check]

    // 2. Build entity
    const entity: [DOMAIN]Entity = {
      id: crypto.randomUUID(),
      // ...dto,
      createdAt: new Date(),
      updatedAt: new Date(),
    };

    // 3. Persist
    try {
      await this.repo.save(entity);
    } catch (err) {
      this.logger.error('[DOMAIN]Service.create failed', {
        reason: err instanceof Error ? err.message : String(err),
      });
      throw new Error('[DOMAIN]_SAVE_FAILED');
    }

    return entity;
  }

  async findById(id: string): Promise<[DOMAIN]Entity> {
    const entity = await this.repo.findById(id);
    if (!entity) {
      throw new [DOMAIN]NotFoundError(id);
    }
    return entity;
  }

  async findAll(): Promise<[DOMAIN]Entity[]> {
    return this.repo.findAll();
  }

  /**
   * Called from: [DOMAIN]UpdateCommand.execute()
   * Returns the previous state (needed by the command for undo)
   */
  async update(dto: Update[DOMAIN]Dto): Promise<{ previous: [DOMAIN]Entity; updated: [DOMAIN]Entity }> {
    const previous = await this.findById(dto.id);

    const updated: [DOMAIN]Entity = {
      ...previous,
      // ...dto,
      updatedAt: new Date(),
    };

    try {
      await this.repo.save(updated);
    } catch (err) {
      this.logger.error('[DOMAIN]Service.update failed', {
        id: dto.id,
        reason: err instanceof Error ? err.message : String(err),
      });
      throw new Error('[DOMAIN]_UPDATE_FAILED');
    }

    return { previous, updated };
  }

  /**
   * Called from: [DOMAIN]DeleteCommand.execute()
   * Returns the deleted entity (needed by the command for undo)
   */
  async delete(id: string): Promise<[DOMAIN]Entity> {
    const entity = await this.findById(id);

    try {
      await this.repo.delete(id);
    } catch (err) {
      this.logger.error('[DOMAIN]Service.delete failed', {
        id,
        reason: err instanceof Error ? err.message : String(err),
      });
      throw new Error('[DOMAIN]_DELETE_FAILED');
    }

    return entity;
  }
}
