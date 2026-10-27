import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import AIAssistantSidebar from '../AIAssistantSidebar';

jest.mock('@/api/assistant', () => ({
  assistantApi: {
    listConversations: jest.fn().mockResolvedValue([]),
    getSuggestions: jest.fn().mockResolvedValue([]),
    getConversation: jest.fn().mockResolvedValue({ messages: [] }),
    deleteConversation: jest.fn().mockResolvedValue(undefined),
  },
}));
jest.mock('@/utils/streamChat', () => ({ streamChat: jest.fn() }));

/**
 * a11y-001/002 (web-qa audit, 2026-09-19): the assistant widget mounts on every
 * authenticated page, and its message box and send button had no accessible name —
 * a placeholder isn't one, and the send button holds only an icon.
 */
describe('AIAssistantSidebar accessibility', () => {
  beforeAll(() => {
    // jsdom has no layout, so no scrollIntoView; the component auto-scrolls on mount.
    Element.prototype.scrollIntoView = jest.fn();
  });

  const renderSidebar = () =>
    render(
      <MemoryRouter>
        <AIAssistantSidebar />
      </MemoryRouter>
    );

  it('gives the message box an accessible name', () => {
    renderSidebar();
    expect(screen.getByRole('textbox', { name: /message the ai assistant/i })).toBeInTheDocument();
  });

  it('gives the icon-only send button an accessible name', () => {
    renderSidebar();
    expect(screen.getByRole('button', { name: /send message/i })).toBeInTheDocument();
  });
});
