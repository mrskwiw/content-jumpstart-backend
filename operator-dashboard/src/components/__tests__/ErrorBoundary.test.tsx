/**
 * Regression tests for Bug #187 (part 2): the ErrorBoundary state persisted
 * across client-side navigation. Because every route reuses the same boundary
 * instance at a fixed tree position, a crash on one page left `hasError` set and
 * every subsequently-navigated page rendered the fallback until a full reload.
 * The fix keys recovery on `resetKey` (wired to `location.pathname` in the router).
 */
import { describe, it, expect, beforeAll, afterAll, jest } from '@jest/globals';
import { render, screen } from '@testing-library/react';
import { ErrorBoundary } from '../ErrorBoundary';

const Boom = (): JSX.Element => {
  throw new Error('boom');
};

describe('ErrorBoundary — resetKey recovery (Bug #187)', () => {
  let errSpy: ReturnType<typeof jest.spyOn>;
  beforeAll(() => {
    errSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
  });
  afterAll(() => {
    errSpy.mockRestore();
  });

  it('shows the fallback when a child throws', () => {
    render(
      <ErrorBoundary resetKey="/a">
        <Boom />
      </ErrorBoundary>
    );
    expect(screen.getByText('Something Went Wrong')).toBeInTheDocument();
  });

  it('recovers when resetKey changes (route navigation)', () => {
    const { rerender } = render(
      <ErrorBoundary resetKey="/a">
        <Boom />
      </ErrorBoundary>
    );
    expect(screen.getByText('Something Went Wrong')).toBeInTheDocument();

    // Simulate navigating to a different, healthy route.
    rerender(
      <ErrorBoundary resetKey="/b">
        <div>Healthy page</div>
      </ErrorBoundary>
    );

    expect(screen.getByText('Healthy page')).toBeInTheDocument();
    expect(screen.queryByText('Something Went Wrong')).not.toBeInTheDocument();
  });

  it('keeps showing the fallback while resetKey is unchanged', () => {
    const { rerender } = render(
      <ErrorBoundary resetKey="/a">
        <Boom />
      </ErrorBoundary>
    );

    // Same route (resetKey unchanged) → boundary must not auto-recover.
    rerender(
      <ErrorBoundary resetKey="/a">
        <div>Healthy page</div>
      </ErrorBoundary>
    );

    expect(screen.getByText('Something Went Wrong')).toBeInTheDocument();
    expect(screen.queryByText('Healthy page')).not.toBeInTheDocument();
  });
});
