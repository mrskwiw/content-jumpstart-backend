/**
 * Smoke tests for UsersTab component
 */
import { describe, it, expect, jest } from '@jest/globals';
import { render } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import UsersTab from '../UsersTab';

// Mock the users API
jest.mock('@/api/users', () => ({
  usersApi: {
    list: jest.fn().mockResolvedValue([]),
    getStats: jest.fn().mockResolvedValue({ total_users: 0, active_users: 0, inactive_users: 0 }),
  },
}));

describe('UsersTab Component', () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  it('should render without crashing', () => {
    const { container } = render(
      <QueryClientProvider client={queryClient}>
        <UsersTab />
      </QueryClientProvider>
    );
    expect(container).toBeInTheDocument();
  });

  it('should render users management interface', () => {
    const { container } = render(
      <QueryClientProvider client={queryClient}>
        <UsersTab />
      </QueryClientProvider>
    );
    // Should have users content
    expect(container.firstChild).toBeInTheDocument();
  });
});
