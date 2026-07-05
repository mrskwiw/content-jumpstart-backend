/**
 * Smoke tests for aiDiscoveryService
 */
import { describe, it, expect, jest } from '@jest/globals';
import { aiDiscoveryService } from '../aiDiscoveryService';
import api from '../../api/client';

// Mock the API client
jest.mock('../../api/client');

const mockedApi = api as jest.Mocked<typeof api>;

describe('aiDiscoveryService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('startDiscovery', () => {
    it('should start AI discovery conversation', async () => {
      const mockResponse = {
        data: {
          conversationId: 'conv-123',
          message: 'Hello! Tell me about your business.',
          fields: {},
        },
      };

      mockedApi.post.mockResolvedValue(mockResponse as any);

      const result = await aiDiscoveryService.startDiscovery();

      expect(api.post).toHaveBeenCalled();
      expect(result.conversationId).toBe('conv-123');
    });
  });

  describe('sendMessage', () => {
    it('should send message and get AI response', async () => {
      const mockResponse = {
        data: {
          conversationId: 'conv-123',
          message: 'Thanks for sharing!',
          fields: {
            businessDescription: { value: 'Test business', confidence: 'high' as const },
          },
        },
      };

      mockedApi.post.mockResolvedValue(mockResponse as any);

      const result = await aiDiscoveryService.sendMessage('conv-123', 'We sell software');

      expect(api.post).toHaveBeenCalled();
      expect(result.message).toBeTruthy();
    });
  });

  describe('extractFields', () => {
    it('should extract client profile fields from conversation', async () => {
      const mockResponse = {
        data: {
          fields: {
            companyName: { value: 'Test Co', confidence: 'high' as const },
            businessDescription: { value: 'Software company', confidence: 'high' as const },
          },
          completeness: 0.8,
        },
      };

      mockedApi.post.mockResolvedValue(mockResponse as any);

      const result = await aiDiscoveryService.extractFields('conv-123');

      expect(api.post).toHaveBeenCalled();
      expect(result.completeness).toBe(0.8);
    });
  });
});
