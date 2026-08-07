/**
 * Tests for the MFA settings panel (BUGS #172).
 */
import { describe, it, expect, beforeEach, jest } from '@jest/globals';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithRouter } from '@/__tests__/setup/test-utils';
import { MFAPanel } from '../MFAPanel';
import { mfaApi } from '@/api/mfa';

jest.mock('@/api/mfa', () => ({
  mfaApi: {
    status: jest.fn(),
    enroll: jest.fn(),
    verify: jest.fn(),
    disable: jest.fn(),
    regenerateBackupCodes: jest.fn(),
  },
}));

const mocked = mfaApi as jest.Mocked<typeof mfaApi>;

const OFF = { mfa_enabled: false, mfa_enforced: false, remaining_backup_codes: 0 };
const ON = { mfa_enabled: true, mfa_enforced: false, remaining_backup_codes: 7 };

const ENROLLMENT = {
  secret: 'JBSWY3DPEHPK3PXP', // pragma: allowlist secret
  qr_code: 'data:image/png;base64,iVBORw0KG',
  backup_codes: ['AAAA1111', 'BBBB2222'],
  message: 'Scan the QR code with your authenticator app',
};

describe('MFAPanel', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('shows the off state and offers setup when MFA is not enabled', async () => {
    mocked.status.mockResolvedValue(OFF);

    renderWithRouter(<MFAPanel />);

    expect(await screen.findByText(/not enabled/i)).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /set up two-factor authentication/i })
    ).toBeInTheDocument();
  });

  it('walks through enrollment: QR, manual key, backup codes, then activation', async () => {
    mocked.status.mockResolvedValue(OFF);
    mocked.enroll.mockResolvedValue(ENROLLMENT);
    mocked.verify.mockResolvedValue({ success: true, message: 'MFA successfully enabled' });

    const user = userEvent.setup();
    renderWithRouter(<MFAPanel />);

    await user.click(await screen.findByRole('button', { name: /set up two-factor/i }));

    // The secret is offered both ways — QR for phones, text for password managers.
    expect(await screen.findByAltText(/two-factor qr code/i)).toHaveAttribute(
      'src',
      ENROLLMENT.qr_code
    );
    expect(screen.getByText(ENROLLMENT.secret)).toBeInTheDocument();
    // Backup codes are visible during enrollment — they are never shown again.
    expect(screen.getByText('AAAA1111')).toBeInTheDocument();
    expect(screen.getByText(/shown only once/i)).toBeInTheDocument();

    await user.type(screen.getByLabelText(/verification code/i), '123456');
    await user.click(screen.getByRole('button', { name: /activate/i }));

    await waitFor(() => expect(mocked.verify).toHaveBeenCalledWith('123456'));
  });

  it('surfaces a rejected code, which the backend returns as a 200', async () => {
    mocked.status.mockResolvedValue(OFF);
    mocked.enroll.mockResolvedValue(ENROLLMENT);
    mocked.verify.mockResolvedValue({ success: false, message: 'Invalid verification code' });

    const user = userEvent.setup();
    renderWithRouter(<MFAPanel />);

    await user.click(await screen.findByRole('button', { name: /set up two-factor/i }));
    await user.type(await screen.findByLabelText(/verification code/i), '000000');
    await user.click(screen.getByRole('button', { name: /activate/i }));

    expect(await screen.findByText(/invalid verification code/i)).toBeInTheDocument();
  });

  it('shows management actions and the remaining backup-code count when enabled', async () => {
    mocked.status.mockResolvedValue(ON);

    renderWithRouter(<MFAPanel />);

    expect(await screen.findByText(/7 backup codes left/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /regenerate backup codes/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /turn off/i })).toBeInTheDocument();
  });

  it('hides the off switch for an account under an operator policy', async () => {
    mocked.status.mockResolvedValue({ ...ON, mfa_enforced: true });

    renderWithRouter(<MFAPanel />);

    expect(await screen.findByText(/required by your administrator/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /turn off/i })).toBeNull();
  });

  it('requires both a password and a code to turn MFA off', async () => {
    mocked.status.mockResolvedValue(ON);
    mocked.disable.mockResolvedValue({ success: true, message: 'MFA disabled' });

    const user = userEvent.setup();
    renderWithRouter(<MFAPanel />);

    await user.click(await screen.findByRole('button', { name: /turn off/i }));

    const submit = screen.getByRole('button', { name: /turn off two-factor/i });
    expect(submit).toBeDisabled(); // nothing entered yet

    await user.type(screen.getByLabelText(/^password$/i), 'hunter2hunter2');
    await user.type(screen.getByLabelText(/verification or backup code/i), 'AAAA1111');
    await user.click(submit);

    await waitFor(() =>
      expect(mocked.disable).toHaveBeenCalledWith('hunter2hunter2', 'AAAA1111')
    );
  });

  it('shows the new codes once after a regeneration', async () => {
    mocked.status.mockResolvedValue(ON);
    mocked.regenerateBackupCodes.mockResolvedValue({ backup_codes: ['CCCC3333', 'DDDD4444'] });

    const user = userEvent.setup();
    renderWithRouter(<MFAPanel />);

    await user.click(await screen.findByRole('button', { name: /regenerate backup codes/i }));
    await user.type(screen.getByLabelText(/verification code/i), '654321');
    await user.click(screen.getByRole('button', { name: /generate new codes/i }));

    expect(await screen.findByText('CCCC3333')).toBeInTheDocument();
    expect(mocked.regenerateBackupCodes).toHaveBeenCalledWith('654321');
  });
});
