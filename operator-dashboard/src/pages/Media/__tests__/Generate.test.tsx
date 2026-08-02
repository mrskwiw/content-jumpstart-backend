import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import MediaGenerate from '@/pages/Media/Generate';
import { mediaApi } from '@/api/media';
import { renderWithProviders } from '@/test-utils';

jest.mock('@/api/media', () => ({
  mediaApi: {
    pipelines: jest.fn().mockResolvedValue({}),
    generate: jest.fn(),
  },
}));

const mockedGenerate = mediaApi.generate as jest.Mock;

describe('MediaGenerate — image (Flux)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedGenerate.mockResolvedValue({
      estimate: { pipeline: 'gen_image', stages: [], total_cost_cents: 5 },
      confirmed: false,
    });
  });

  it('estimates a gen_image job with the prompt spec', async () => {
    const { wrapper } = renderWithProviders();
    render(<MediaGenerate />, { wrapper });

    // Choose the image pipeline.
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'gen_image' } });
    // The prompt field appears with the image label.
    const promptBox = await screen.findByPlaceholderText(/golden retriever/i);
    fireEvent.change(promptBox, { target: { value: 'a red bicycle in the rain' } });

    fireEvent.click(screen.getByRole('button', { name: /estimate cost/i }));

    await waitFor(() =>
      expect(mockedGenerate).toHaveBeenCalledWith(
        expect.objectContaining({
          pipeline: 'gen_image',
          confirm: false,
          spec: { prompt: 'a red bicycle in the rain' },
        })
      )
    );
  });

  it('disables Estimate until a prompt is entered', async () => {
    const { wrapper } = renderWithProviders();
    render(<MediaGenerate />, { wrapper });

    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'gen_image' } });
    expect(screen.getByRole('button', { name: /estimate cost/i })).toBeDisabled();
  });
});
