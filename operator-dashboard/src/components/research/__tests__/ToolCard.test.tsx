import { render, screen, fireEvent } from '@testing-library/react';
import { ToolCard } from '../ToolCard';
import type { ResearchTool } from '../../../api/research';

const tool = (status: ResearchTool['status']): ResearchTool => ({
  name: 'content_audit',
  label: 'Content Audit',
  credits: 400,
  status,
  category: 'advanced',
});

describe('ToolCard', () => {
  it('toggles an available tool on click and on Enter', () => {
    const onToggle = jest.fn();
    render(<ToolCard tool={tool('available')} isSelected={false} onToggle={onToggle} />);
    const card = screen.getByRole('button', { name: /content audit/i });

    fireEvent.click(card);
    fireEvent.keyDown(card, { key: 'Enter' });

    expect(onToggle).toHaveBeenCalledTimes(2);
    expect(card).toHaveAttribute('tabindex', '0');
    expect(card).not.toHaveAttribute('aria-disabled', 'true');
  });

  // Phase C (ALIGN-01): a backend `coming_soon` tool was still selectable, because only
  // the feature registry's disabled list was guarded. The card itself now refuses.
  it('cannot be selected when the tool is coming soon — by click, keyboard or focus', () => {
    const onToggle = jest.fn();
    render(<ToolCard tool={tool('coming_soon')} isSelected={false} onToggle={onToggle} />);
    const card = screen.getByRole('button', { name: /content audit/i });

    fireEvent.click(card);
    fireEvent.keyDown(card, { key: 'Enter' });
    fireEvent.keyDown(card, { key: ' ' });

    expect(onToggle).not.toHaveBeenCalled();
    expect(card).toHaveAttribute('aria-disabled', 'true');
    expect(card).toHaveAttribute('tabindex', '-1');
    expect(screen.getByText('Coming Soon')).toBeInTheDocument();
  });

  it('still honours an explicit disabled prop', () => {
    const onToggle = jest.fn();
    render(<ToolCard tool={tool('available')} isSelected={false} onToggle={onToggle} disabled />);
    const card = screen.getByRole('button', { name: /content audit/i });

    fireEvent.click(card);
    expect(onToggle).not.toHaveBeenCalled();
    expect(card).toHaveAttribute('aria-disabled', 'true');
  });
});
