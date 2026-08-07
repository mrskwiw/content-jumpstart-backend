import apiClient from './client';

/**
 * MFA (TOTP two-factor) client — BUGS #172.
 *
 * Enrollment is two-step by design: `enroll` provisions a secret and returns the QR
 * plus one-time backup codes, but the account is not protected until `verify` confirms
 * a code from the authenticator app, which proves the secret was actually stored.
 */

export interface MFAStatus {
  mfa_enabled: boolean;
  /** Operator policy: the account may not turn MFA off. */
  mfa_enforced: boolean;
  remaining_backup_codes: number;
}

export interface MFAEnrollment {
  /** Base32 secret, for manual entry when a QR can't be scanned. */
  secret: string;
  /** `data:image/png;base64,...` — renderable directly in an <img src>. */
  qr_code: string;
  /** Shown once; only hashes are stored server-side. */
  backup_codes: string[];
  message: string;
}

export const mfaApi = {
  status: async (): Promise<MFAStatus> => {
    const { data } = await apiClient.get<MFAStatus>('/api/mfa/status');
    return data;
  },

  enroll: async (): Promise<MFAEnrollment> => {
    const { data } = await apiClient.post<MFAEnrollment>('/api/mfa/enroll');
    return data;
  },

  /**
   * Confirm a TOTP code. Completes enrollment the first time it succeeds.
   * Note: an invalid code comes back as HTTP 200 with `success: false`.
   */
  verify: async (token: string): Promise<{ success: boolean; message: string }> => {
    const { data } = await apiClient.post('/api/mfa/verify', { token });
    return data;
  },

  /** Requires the account password AND a live code (TOTP or a backup code). */
  disable: async (password: string, code: string): Promise<{ success: boolean; message: string }> => {
    const { data } = await apiClient.post('/api/mfa/disable', { password, code });
    return data;
  },

  /** Requires a live TOTP code; invalidates the previous set. */
  regenerateBackupCodes: async (token: string): Promise<{ backup_codes: string[] }> => {
    const { data } = await apiClient.post('/api/mfa/backup-codes/regenerate', { token });
    return data;
  },
};
