/**
 * ResultDetailModal component tests.
 *
 * Verifies the modal renders the selected result content, exposes structured
 * data, and can export the current result payload as a JSON download.
 */
import { afterEach, beforeEach, describe, expect, it, jest } from '@jest/globals';
import { fireEvent, render, screen } from '@testing-library/react';
import { ResultDetailModal } from './ResultDetailModal';
import type { ResearchResult } from '@/types/domain';

const mockResult: ResearchResult = {
  id: 'rr-1',
  userId: 'user-1',
  clientId: 'client-1',
  projectId: 'proj-1',
  toolName: 'voice_analysis',
  toolLabel: 'Voice Analysis',
  toolPrice: 400,
  actualCostUsd: 0.42,
  params: {},
  outputs: {
    report: 'This is the primary output.',
    summary: 'Short summary',
  },
  data: {
    report: 'This is the primary output.',
    summary: 'Short summary',
  },
  status: 'succeeded',
  errorMessage: null,
  durationSeconds: 65,
  createdAt: '2026-04-27T08:00:00Z',
  inputTokens: null,
  outputTokens: null,
  cacheCreationTokens: null,
  cacheReadTokens: null,
};

describe('ResultDetailModal', () => {
  const createObjectURL = jest.fn(() => 'blob:mock');
  const revokeObjectURL = jest.fn();
  const click = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    Object.defineProperty(global.URL, 'createObjectURL', {
      configurable: true,
      value: createObjectURL,
    });
    Object.defineProperty(global.URL, 'revokeObjectURL', {
      configurable: true,
      value: revokeObjectURL,
    });
    jest.spyOn(document, 'createElement').mockImplementation((tagName: string) => {
      if (tagName === 'a') {
        return {
          href: '',
          download: '',
          click,
        } as unknown as HTMLAnchorElement;
      }
      return document.createElementNS('http://www.w3.org/1999/xhtml', tagName) as HTMLElement;
    });
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('renders the selected result in preview, data, and metadata tabs', () => {
    render(<ResultDetailModal result={mockResult} onClose={jest.fn()} />);

    expect(screen.getByText('Voice Analysis')).toBeInTheDocument();
    expect(screen.getByText('report')).toBeInTheDocument();
    expect(screen.getByText('This is the primary output.')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /structured data/i }));
    expect(screen.getByText(/"report": "This is the primary output\."/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /execution details/i }));
    expect(screen.getByText('Status')).toBeInTheDocument();
    expect(screen.getByText('succeeded')).toBeInTheDocument();
    expect(screen.getByText('Duration')).toBeInTheDocument();
    expect(screen.getByText('65s')).toBeInTheDocument();
  });

  it('downloads a JSON snapshot of the result payload', () => {
    render(<ResultDetailModal result={mockResult} onClose={jest.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: /download all/i }));

    expect(createObjectURL).toHaveBeenCalledTimes(1);
    expect(click).toHaveBeenCalledTimes(1);
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:mock');
  });
});
