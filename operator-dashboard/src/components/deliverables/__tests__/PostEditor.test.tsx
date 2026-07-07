/**
 * Smoke tests for PostEditor component
 */
import { describe, it, expect, jest } from '@jest/globals';
import { render } from '@testing-library/react';
import { PostEditor } from '../PostEditor';

describe('PostEditor Component', () => {
  const mockPost = {
    id: 'post-1',
    content: 'Test content',
    status: 'approved' as const,
    contentPreview: 'Test',
  };

  const mockOnSave = jest.fn();
  const mockOnCancel = jest.fn();

  it('should render without crashing', () => {
    const { container } = render(
      <PostEditor post={mockPost} onSave={mockOnSave} onCancel={mockOnCancel} />
    );
    expect(container).toBeInTheDocument();
  });

  it('should render post content', () => {
    const { container } = render(
      <PostEditor post={mockPost} onSave={mockOnSave} onCancel={mockOnCancel} />
    );
    expect(container).toHaveTextContent('Test content');
  });

  it('should render save and cancel buttons', () => {
    const { container } = render(
      <PostEditor post={mockPost} onSave={mockOnSave} onCancel={mockOnCancel} />
    );
    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
  });
});
