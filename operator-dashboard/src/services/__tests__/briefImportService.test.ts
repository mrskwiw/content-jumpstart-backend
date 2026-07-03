/**
 * Smoke tests for briefImportService
 */
import { describe, it, expect, jest } from '@jest/globals';
import { briefImportService } from '../briefImportService';
import api from '../../api/client';

// Mock the API client
jest.mock('../../api/client');

const mockedApi = api as jest.Mocked<typeof api>;

describe('briefImportService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('parseFile', () => {
    it('should parse brief file successfully', async () => {
      const mockResponse = {
        data: {
          success: true,
          fields: {
            companyName: { value: 'Test Co', confidence: 'high' as const },
          },
          warnings: [],
          metadata: {
            filename: 'brief.txt',
            parseTimeMs: 100,
            fieldsExtracted: 1,
            fieldsTotal: 1,
          },
        },
      };

      mockedApi.post.mockResolvedValue(mockResponse as any);

      const file = new File(['content'], 'brief.txt', { type: 'text/plain' });
      const result = await briefImportService.parseFile(file);

      expect(api.post).toHaveBeenCalled();
      expect(result.success).toBe(true);
    });

    it('should handle parse errors', async () => {
      const mockError = {
        response: {
          data: {
            code: 'PARSE_ERROR',
            message: 'Failed to parse',
          },
        },
      };

      mockedApi.post.mockRejectedValue(mockError);

      const file = new File(['invalid'], 'brief.txt', { type: 'text/plain' });

      await expect(briefImportService.parseFile(file)).rejects.toThrow();
    });
  });

  describe('validateParsedData', () => {
    it('should validate parsed data', () => {
      const validData = {
        companyName: { value: 'Test', confidence: 'high' as const },
      };

      const result = briefImportService.validateParsedData(validData);

      expect(result.isValid).toBe(true);
    });

    it('should detect missing required fields', () => {
      const invalidData = {};

      const result = briefImportService.validateParsedData(invalidData);

      expect(result.isValid).toBe(false);
      expect(result.errors.length).toBeGreaterThan(0);
    });
  });
});
