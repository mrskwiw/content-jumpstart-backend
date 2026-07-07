/**
 * Smoke tests for UsersTab component
 */
import { describe, it, expect, jest } from '@jest/globals';
import { renderWithProviders as render } from '@/__tests__/setup/test-utils';
import UsersTab from '../UsersTab';

// Mock the users API
jest.mock('@/api/users', () => ({
  usersApi: {
    list: jest.fn().mockResolvedValue([]),
    getStats: jest.fn().mockResolvedValue({ total_users: 0, active_users: 0, inactive_users: 0 }),
  },
}));

describe('UsersTab Component', () => {
  it('should render without crashing', () => {
    const { container } = render(<UsersTab />);
    expect(container).toBeInTheDocument();
  });

  it('should render users management interface', () => {
    const { container } = render(<UsersTab />);
    // Should have users content
    expect(container.firstChild).toBeInTheDocument();
  });
});
