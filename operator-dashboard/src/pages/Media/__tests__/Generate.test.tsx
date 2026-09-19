import { render, screen, fireEvent } from '@testing-library/react';
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

describe('MediaGenerate — under development (Bug fix 2026-09-19)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedGenerate.mockResolvedValue({
      estimate: { pipeline: 'gen_image', stages: [], total_cost_cents: 5 },
      confirmed: false,
    });
  });

  it('discloses that media generation is under development instead of silently failing on confirm', async () => {
    const { wrapper } = renderWithProviders();
    render(<MediaGenerate />, { wrapper });

    expect(screen.getByText(/media generation is under development/i)).toBeInTheDocument();
  });

  it('disables the whole form so no pipeline can be estimated or confirmed', async () => {
    const { wrapper } = renderWithProviders();
    render(<MediaGenerate />, { wrapper });

    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'gen_image' } });
    const promptBox = await screen.findByPlaceholderText(/golden retriever/i);
    expect(promptBox).toBeDisabled();

    const submit = screen.getByRole('button', { name: /under development/i });
    expect(submit).toBeDisabled();

    fireEvent.click(submit);
    expect(mockedGenerate).not.toHaveBeenCalled();
  });
});
