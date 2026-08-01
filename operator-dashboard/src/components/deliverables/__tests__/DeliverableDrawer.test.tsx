import { render, screen, waitFor } from '@testing-library/react';
import { DeliverableDrawer } from '@/components/deliverables/DeliverableDrawer';
import { deliverablesApi } from '@/api/deliverables';
import { renderWithProviders } from '@/test-utils';
import type { Deliverable } from '@/types/domain';

jest.mock('@/api/deliverables', () => ({
  deliverablesApi: {
    getDetails: jest.fn(),
    download: jest.fn(),
  },
}));

const mockedGetDetails = deliverablesApi.getDetails as jest.Mock;

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
