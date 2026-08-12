/**
 * Unit tests for [DOMAIN]Service
 *
 * Rules:
 * - No real I/O — all dependencies are mocked
 * - Each test describes one observable behavior
 * - See: DOCS/Testing/TEST_STRATEGY.md
 */

import { [DOMAIN]Service, [DOMAIN]NotFoundError, [DOMAIN]ConflictError } from './service';
import type { I[DOMAIN]Repository, [DOMAIN]Entity, Create[DOMAIN]Dto } from './service';

// ---------------------------------------------------------------------------
// Test Fixtures & Factories
// ---------------------------------------------------------------------------

function make[DOMAIN](overrides: Partial<[DOMAIN]Entity> = {}): [DOMAIN]Entity {
  return {
    id: 'entity-id-001',
    createdAt: new Date('2025-01-01T00:00:00Z'),
    updatedAt: new Date('2025-01-01T00:00:00Z'),
    // ...add default field values here
    ...overrides,
  };
}

function makeCreate[DOMAIN]Dto(overrides: Partial<Create[DOMAIN]Dto> = {}): Create[DOMAIN]Dto {
  return {
    // ...required fields with safe defaults
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Mock Factory
// (Returns a fresh mock repo and logger for each test)
// ---------------------------------------------------------------------------

function makeMocks() {
  const repo: jest.Mocked<I[DOMAIN]Repository> = {
    findById: jest.fn(),
    findAll: jest.fn(),
    save: jest.fn(),
    delete: jest.fn(),
  };

  const logger = {
    info: jest.fn(),
    error: jest.fn(),
    warn: jest.fn(),
  };

  const service = new [DOMAIN]Service(repo, logger);

  return { repo, logger, service };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('[DOMAIN]Service', () => {
  describe('create', () => {
    it('returns a new entity with a generated ID when input is valid', async () => {
      const { repo, service } = makeMocks();
      repo.save.mockResolvedValue();

      const result = await service.create(makeCreate[DOMAIN]Dto());

      expect(result.id).toBeDefined();
      expect(result.createdAt).toBeInstanceOf(Date);
      expect(repo.save).toHaveBeenCalledTimes(1);
    });

    it('throws [DOMAIN]ConflictError when [conflict condition]', async () => {
      const { repo, service } = makeMocks();
      // Setup: simulate the conflict condition
      // repo.findBy[Field].mockResolvedValue(make[DOMAIN]());

      await expect(
        service.create(makeCreate[DOMAIN]Dto({ /* conflicting field */ }))
      ).rejects.toThrow([DOMAIN]ConflictError);
    });

    it('re-throws a wrapped error when the repository fails to save', async () => {
      const { repo, service } = makeMocks();
      repo.save.mockRejectedValue(new Error('DB connection lost'));

      await expect(service.create(makeCreate[DOMAIN]Dto())).rejects.toThrow();
    });

    it('logs an error with context when save fails', async () => {
      const { repo, logger, service } = makeMocks();
      repo.save.mockRejectedValue(new Error('DB error'));

      try {
        await service.create(makeCreate[DOMAIN]Dto());
      } catch {
        // expected
      }

      expect(logger.error).toHaveBeenCalledWith(
        expect.stringContaining('[DOMAIN]Service.create failed'),
        expect.objectContaining({ reason: expect.any(String) })
      );
    });
  });

  describe('findById', () => {
    it('returns the entity when it exists', async () => {
      const { repo, service } = makeMocks();
      const entity = make[DOMAIN]({ id: 'test-id' });
      repo.findById.mockResolvedValue(entity);

      const result = await service.findById('test-id');

      expect(result).toEqual(entity);
    });

    it('throws [DOMAIN]NotFoundError when entity does not exist', async () => {
      const { repo, service } = makeMocks();
      repo.findById.mockResolvedValue(null);

      await expect(service.findById('missing-id')).rejects.toThrow([DOMAIN]NotFoundError);
    });
  });

  describe('update', () => {
    it('returns both previous and updated state for undo support', async () => {
      const { repo, service } = makeMocks();
      const existing = make[DOMAIN]({ id: 'e1' });
      repo.findById.mockResolvedValue(existing);
      repo.save.mockResolvedValue();

      const result = await service.update({ id: 'e1', /* changed fields */ });

      expect(result.previous).toEqual(existing);
      expect(result.updated.id).toBe('e1');
      expect(result.updated.updatedAt.getTime()).toBeGreaterThanOrEqual(existing.updatedAt.getTime());
    });

    it('throws [DOMAIN]NotFoundError when updating a non-existent entity', async () => {
      const { repo, service } = makeMocks();
      repo.findById.mockResolvedValue(null);

      await expect(service.update({ id: 'missing' })).rejects.toThrow([DOMAIN]NotFoundError);
    });
  });

  describe('delete', () => {
    it('returns the deleted entity so callers can undo the deletion', async () => {
      const { repo, service } = makeMocks();
      const entity = make[DOMAIN]({ id: 'd1' });
      repo.findById.mockResolvedValue(entity);
      repo.delete.mockResolvedValue();

      const deleted = await service.delete('d1');

      expect(deleted).toEqual(entity);
      expect(repo.delete).toHaveBeenCalledWith('d1');
    });

    it('throws [DOMAIN]NotFoundError when entity does not exist', async () => {
      const { repo, service } = makeMocks();
      repo.findById.mockResolvedValue(null);

      await expect(service.delete('missing')).rejects.toThrow([DOMAIN]NotFoundError);
    });
  });
});
