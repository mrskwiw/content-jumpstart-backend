import { getAuthErrorMessage } from './errorMessages';

const axiosError = (overrides: Partial<any>) =>
  ({
    isAxiosError: true,
    response: undefined,
    code: undefined,
    message: 'Axios error',
    ...overrides,
  }) as any;

describe('getAuthErrorMessage', () => {
  it('returns network message on network failure', () => {
    const msg = getAuthErrorMessage(axiosError({ code: 'ERR_NETWORK' }));
    expect(msg).toMatch(/Cannot reach the server/i);
  });

  it('returns auth message for 401', () => {
    const msg = getAuthErrorMessage(
      axiosError({ response: { status: 401, data: { detail: 'Invalid credentials' } } })
    );
    expect(msg).toBe('Invalid credentials');
  });

  it('returns server message for 500+', () => {
    const msg = getAuthErrorMessage(axiosError({ response: { status: 503 } }));
    expect(msg).toMatch(/Server error/i);
  });

  it('returns not found message for 404', () => {
    const msg = getAuthErrorMessage(
      axiosError({ response: { status: 404, data: { detail: 'User not found' } } })
    );
    expect(msg).toBe('User not found');
  });

  it('returns html response warning', () => {
    const msg = getAuthErrorMessage(
      axiosError({ response: { status: 200, data: '<!doctype html><html></html>' } })
    );
    expect(msg).toMatch(/Received HTML/i);
  });

  it('returns invalid credentials for code', () => {
    const msg = getAuthErrorMessage(
      axiosError({ response: { status: 400, data: { code: 'invalid_credentials' } } })
    );
    expect(msg).toMatch(/Invalid email or password/i);
  });

  it('returns fallback for non-Axios errors', () => {
    const msg = getAuthErrorMessage(new Error('boom'));
    expect(msg).toBe('boom');
  });

  it('returns generic fallback for unknown shape', () => {
    const msg = getAuthErrorMessage('weird');
    expect(msg).toMatch(/Unexpected error/i);
  });
});
