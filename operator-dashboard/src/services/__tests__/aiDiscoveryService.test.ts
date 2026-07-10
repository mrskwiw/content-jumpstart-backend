/**
 * Smoke tests for aiDiscoveryService
 */
import { describe, it, expect, jest } from '@jest/globals';
import type { AxiosResponse } from 'axios';
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
    // startDiscovery is purely local: it seeds an in-memory session with the
    // first question and does NOT call the backend (no conversationId concept).
    it('should start a local discovery session with a first question', async () => {
      const session = await aiDiscoveryService.startDiscovery();

      expect(api.post).not.toHaveBeenCalled();
      expect(session.id).toMatch(/^discovery_/);
      expect(session.firstQuestion).toBeTruthy();
      expect(session.createdAt).toBeInstanceOf(Date);
    });
  });

  describe('sendMessage', () => {
    it('should send message via the assistant endpoint and return the reply', async () => {
      const session = await aiDiscoveryService.startDiscovery();

      mockedApi.post.mockResolvedValue({
        data: { message: 'Thanks for sharing!' },
      } as unknown as AxiosResponse);

      const result = await aiDiscoveryService.sendMessage(session.id, 'We sell software');

      expect(api.post).toHaveBeenCalledWith(
        '/api/assistant/chat',
        expect.objectContaining({ context: { page: 'client-discovery' } })
      );
      expect(result.message).toBe('Thanks for sharing!');
    });

    it('should parse extracted fields from the <extracted> block in the reply', async () => {
      const session = await aiDiscoveryService.startDiscovery();

      const extracted = JSON.stringify({
        companyName: 'Test Co',
        businessDescription: 'Software company',
      });
      mockedApi.post.mockResolvedValue({
        data: { message: `Great, thanks!<extracted>${extracted}</extracted>` },
      } as unknown as AxiosResponse);

      const result = await aiDiscoveryService.sendMessage(session.id, 'We sell software');

      // Conversational reply has the tag block stripped out
      expect(result.message).toBe('Great, thanks!');
      expect(result.extractedFields.companyName).toBe('Test Co');
      // Extracted (non-null) fields get a 0.9 confidence score
      expect(result.confidence.companyName).toBe(0.9);
    });
  });
});
