/**
 * Tests for the VerifyEmail page (GAP-AUTH-02).
 */
import { describe, it, expect, beforeEach, jest } from '@jest/globals';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithRouter } from '@/__tests__/setup/test-utils';
import VerifyEmail from '../VerifyEmail';
import { authApi } from '@/api/auth';

jest.mock('@/api/auth', () => ({
  authApi: {
    verifyEmail: jest.fn(),
    resendVerification: jest.fn(),
  },
}));

const mockedVerify = authApi.verifyEmail as jest.MockedFunction<typeof authApi.verifyEmail>;
const mockedResend = authApi.resendVerification as jest.MockedFunction<
  typeof authApi.resendVerification
>;

const at = (path: string) => renderWithRouter(<VerifyEmail />, { initialEntries: [path] });

describe('VerifyEmail Page', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('verifies the account when a token is present and shows success', async () => {
    mockedVerify.mockResolvedValue({ status: 'success', message: 'Email verified' });

    at('/verify-email?token=good-token');

    await waitFor(() => expect(screen.getByText(/your email address is verified/i)).toBeInTheDocument());
    expect(mockedVerify).toHaveBeenCalledWith('good-token');
    expect(screen.getByRole('button', { name: /go to sign in/i })).toBeInTheDocument();
  });

  it('shows an error and a resend form when the token is invalid or expired', async () => {
    mockedVerify.mockRejectedValue(new Error('Invalid or expired verification link'));

    at('/verify-email?token=bad-token');

    // The resend form (email field + resend button) only renders in the error state.
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /resend verification link/i })).toBeInTheDocument()
    );
    expect(screen.getByPlaceholderText(/you@example.com/i)).toBeInTheDocument();
  });

  it('skips verification and offers a resend form when no token is present', async () => {
    at('/verify-email');

    expect(await screen.findByText(/missing or malformed/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /resend verification link/i })).toBeInTheDocument();
    expect(mockedVerify).not.toHaveBeenCalled();
  });

  it('resends a verification link with a generic, no-enumeration confirmation', async () => {
    mockedResend.mockResolvedValue({ status: 'success', message: 'sent' });

    at('/verify-email'); // starts in the error/resend state

    const user = userEvent.setup();
    await user.type(screen.getByPlaceholderText(/you@example.com/i), 'user@example.com');
    await user.click(screen.getByRole('button', { name: /resend verification link/i }));

    await waitFor(() => expect(mockedResend).toHaveBeenCalledWith('user@example.com'));
    expect(await screen.findByText(/a\s*new link is on its way/i)).toBeInTheDocument();
  });
});
