import { render, screen } from '@testing-library/react';
import { ToolRunStatusList, type ToolStatusItem } from '../ToolRunStatusList';

const makeItems = (overrides: Partial<ToolStatusItem>[] = []): ToolStatusItem[] =>
  overrides.map((o, i) => ({
    name: `tool_${i}`,
    label: `Tool ${i}`,
    status: 'pending',
    ...o,
  }));

describe('ToolRunStatusList', () => {
  it('renders nothing when items array is empty', () => {
    const { container } = render(<ToolRunStatusList items={[]} />);
    expect(container.firstChild).toBeEmptyDOMElement();
  });

  it('renders a row for each item', () => {
    const items = makeItems([{ label: 'SEO Keywords' }, { label: 'Brand Archetype' }]);
    render(<ToolRunStatusList items={items} />);
    expect(screen.getByText('SEO Keywords')).toBeInTheDocument();
    expect(screen.getByText('Brand Archetype')).toBeInTheDocument();
  });

  it('shows "Pending" badge for pending status', () => {
    render(<ToolRunStatusList items={makeItems([{ status: 'pending', label: 'My Tool' }])} />);
    expect(screen.getByText('Pending')).toBeInTheDocument();
  });

  it('shows "Running" badge for running status', () => {
    render(<ToolRunStatusList items={makeItems([{ status: 'running', label: 'My Tool' }])} />);
    expect(screen.getByText('Running')).toBeInTheDocument();
  });

  it('shows "Done" badge for complete status', () => {
    render(<ToolRunStatusList items={makeItems([{ status: 'complete', label: 'My Tool' }])} />);
    expect(screen.getByText('Done')).toBeInTheDocument();
  });

  it('shows "Failed" badge for failed status', () => {
    render(<ToolRunStatusList items={makeItems([{ status: 'failed', label: 'My Tool' }])} />);
    expect(screen.getByText('Failed')).toBeInTheDocument();
  });

  it('shows "Blocked" badge for blocked status', () => {
    render(<ToolRunStatusList items={makeItems([{ status: 'blocked', label: 'My Tool' }])} />);
    expect(screen.getByText('Blocked')).toBeInTheDocument();
  });

  it('renders error message for failed item', () => {
    const items = makeItems([{ status: 'failed', label: 'SEO', error: 'API rate limit exceeded' }]);
    render(<ToolRunStatusList items={items} />);
    expect(screen.getByText(/API rate limit exceeded/)).toBeInTheDocument();
  });

  it('renders "prerequisite failed" text for blocked item with error', () => {
    const items = makeItems([{ status: 'blocked', label: 'Competitive Analysis', error: 'Blocked: missing deps' }]);
    render(<ToolRunStatusList items={items} />);
    expect(screen.getByText(/prerequisite failed/)).toBeInTheDocument();
  });

  it('does not render error text when no error provided', () => {
    const items = makeItems([{ status: 'complete', label: 'My Tool' }]);
    render(<ToolRunStatusList items={items} />);
    expect(screen.queryByText(/—/)).not.toBeInTheDocument();
  });

  it('renders multiple items with mixed statuses', () => {
    const items: ToolStatusItem[] = [
      { name: 'a', label: 'Tool A', status: 'complete' },
      { name: 'b', label: 'Tool B', status: 'running' },
      { name: 'c', label: 'Tool C', status: 'pending' },
      { name: 'd', label: 'Tool D', status: 'failed', error: 'timeout' },
    ];
    render(<ToolRunStatusList items={items} />);
    expect(screen.getByText('Done')).toBeInTheDocument();
    expect(screen.getByText('Running')).toBeInTheDocument();
    expect(screen.getByText('Pending')).toBeInTheDocument();
    expect(screen.getByText('Failed')).toBeInTheDocument();
    expect(screen.getByText(/timeout/)).toBeInTheDocument();
  });
});
