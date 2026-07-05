/**
 * Smoke tests for PortfolioNotice page
 */
import { describe, it, expect } from '@jest/globals';
import { renderWithProviders } from '@/__tests__/setup/test-utils';
import PortfolioNotice from '../PortfolioNotice';

describe('PortfolioNotice Page', () => {
  it('should render without crashing', () => {
    const { container } = renderWithProviders(<PortfolioNotice />);
    expect(container).toBeInTheDocument();
  });

  it('should render notice message', () => {
    const { container } = renderWithProviders(<PortfolioNotice />);
    // Should have text content
    expect(container.textContent).toBeTruthy();
  });

  it('should render as a notice/banner component', () => {
    const { container } = renderWithProviders(<PortfolioNotice />);
    // Should have styled container
    const notice = container.firstChild;
    expect(notice).toBeInTheDocument();
  });
});
