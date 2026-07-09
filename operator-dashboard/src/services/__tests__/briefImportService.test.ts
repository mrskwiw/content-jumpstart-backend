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

  describe('parseFile error handling', () => {
    it('should surface the structured error message from the backend detail', async () => {
      // Backend returns FastAPI-style { detail: { code, message } }
      mockedApi.post.mockRejectedValue({
        response: {
          data: { detail: { code: 'PARSE_ERROR', message: 'Unsupported file format' } },
        },
      });

      const file = new File(['content'], 'brief.txt', { type: 'text/plain' });

      await expect(briefImportService.parseFile(file)).rejects.toThrow('Unsupported file format');
    });

    it('should surface a friendly message on request timeout', async () => {
      mockedApi.post.mockRejectedValue({ code: 'ECONNABORTED' });

      const file = new File(['content'], 'brief.txt', { type: 'text/plain' });

      await expect(briefImportService.parseFile(file)).rejects.toThrow(
        'Request timed out. Please try again.'
      );
    });
  });
});
