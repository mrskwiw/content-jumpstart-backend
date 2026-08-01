import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { DeliverableDrawer } from '@/components/deliverables/DeliverableDrawer';
import { deliverablesApi } from '@/api/deliverables';
import { renderWithProviders } from '@/test-utils';
import type { Deliverable } from '@/types/domain';

jest.mock('@/api/deliverables', () => ({
  deliverablesApi: {
    getDetails: jest.fn(),
    download: jest.fn(),
    markDelivered: jest.fn(),
  },
}));

const mockedGetDetails = deliverablesApi.getDetails as jest.Mock;
const mockedMarkDelivered = deliverablesApi.markDelivered as jest.Mock;

const mediaDeliverable: Deliverable = {
  id: 'd-img',
  projectId: 'p1',
  clientId: 'c1',
  format: 'image',
  path: 'media/u/j/asset.png',
  createdAt: '2026-08-01T00:00:00Z',
  status: 'ready',
};

describe('DeliverableDrawer — media deliverables', () => {
  beforeEach(() => jest.clearAllMocks());

  it('renders a media panel with a download action and does NOT fetch export details', async () => {
    const { wrapper } = renderWithProviders();
    render(<DeliverableDrawer deliverable={mediaDeliverable} onClose={() => {}} />, { wrapper });

    await waitFor(() =>
      expect(screen.getByText(/media deliverable/i)).toBeInTheDocument()
    );
    // The export-oriented tabs are NOT shown for media…
    expect(screen.queryByText(/^Preview$/)).not.toBeInTheDocument();
    expect(screen.queryByText(/^Posts/)).not.toBeInTheDocument();
    // …and the export details endpoint is never called for a media deliverable.
    expect(mockedGetDetails).not.toHaveBeenCalled();
    // A download action is offered.
    expect(screen.getByRole('button', { name: /download/i })).toBeInTheDocument();
  });

  it('keeps metadata and the mark-delivered workflow for media deliverables', async () => {
    mockedMarkDelivered.mockResolvedValue({});
    const { wrapper } = renderWithProviders();
    render(<DeliverableDrawer deliverable={mediaDeliverable} onClose={() => {}} />, { wrapper });

    // Metadata is still shown (status, created, format labels).
    await waitFor(() => expect(screen.getByText('Status')).toBeInTheDocument());
    expect(screen.getByText('Created')).toBeInTheDocument();
    expect(screen.getByText('Delivered')).toBeInTheDocument();

    // The delivery workflow is retained (status is 'ready', not 'delivered').
    const markBtn = screen.getByRole('button', { name: /mark delivered/i });
    fireEvent.click(markBtn);
    await waitFor(() => expect(mockedMarkDelivered).toHaveBeenCalledWith('d-img', expect.any(Object)));

    // After success the button is replaced by a confirmation — it can't be re-fired in
    // the window before the parent refetch lands (no duplicate mark-delivered PATCH).
    await waitFor(() =>
      expect(screen.queryByRole('button', { name: /mark delivered/i })).not.toBeInTheDocument()
    );
    expect(mockedMarkDelivered).toHaveBeenCalledTimes(1);
  });

  it('does not leak a prior "delivered" success onto a different deliverable', async () => {
    mockedMarkDelivered.mockResolvedValue({});
    const { wrapper } = renderWithProviders();
    const { rerender } = render(
      <DeliverableDrawer deliverable={mediaDeliverable} onClose={() => {}} />,
      { wrapper }
    );

    fireEvent.click(await screen.findByRole('button', { name: /mark delivered/i }));
    await waitFor(() =>
      expect(screen.queryByRole('button', { name: /mark delivered/i })).not.toBeInTheDocument()
    );

    // Switch the drawer to a DIFFERENT, still-undelivered media deliverable.
    const other: Deliverable = { ...mediaDeliverable, id: 'd-img-2', path: 'media/u/j/two.png' };
    rerender(<DeliverableDrawer deliverable={other} onClose={() => {}} />);

    // The Mark-Delivered control is back — the previous success didn't carry over.
    expect(await screen.findByRole('button', { name: /mark delivered/i })).toBeInTheDocument();
  });

  it('fetches export details for a document deliverable (not the media panel)', async () => {
    mockedGetDetails.mockResolvedValue({
      ...mediaDeliverable,
      id: 'd-doc',
      format: 'docx',
      path: 'outputs/p1/report.docx',
      filePreview: 'hello',
      filePreviewTruncated: false,
      posts: [],
    });

    const doc: Deliverable = {
      ...mediaDeliverable,
      id: 'd-doc',
      format: 'docx',
      path: 'outputs/p1/report.docx',
    };
    const { wrapper } = renderWithProviders();
    render(<DeliverableDrawer deliverable={doc} onClose={() => {}} />, { wrapper });

    await waitFor(() => expect(mockedGetDetails).toHaveBeenCalledWith('d-doc'));
    expect(screen.queryByText(/media deliverable/i)).not.toBeInTheDocument();
  });
});
