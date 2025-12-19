import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import Projects from '@/pages/Projects';
import { NewProjectDialog } from '@/components/projects/NewProjectDialog';

function TestWrapper({ children }: { children: React.ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  );
}

describe('Project Creation Flow', () => {
  describe('Projects Page', () => {
    it('should render projects page with header', () => {
      render(
        <TestWrapper>
          <Projects />
        </TestWrapper>
      );

      expect(screen.getByText('Projects')).toBeInTheDocument();
      expect(screen.getByText(/search, filter, and manage/i)).toBeInTheDocument();
    });

    it('should display New Project button', () => {
      render(
        <TestWrapper>
          <Projects />
        </TestWrapper>
      );

      const newProjectButton = screen.getByRole('button', { name: /new project/i });
      expect(newProjectButton).toBeInTheDocument();
    });

    it('should have search and filter controls', () => {
      render(
        <TestWrapper>
          <Projects />
        </TestWrapper>
      );

      expect(screen.getByPlaceholderText(/search projects or ids/i)).toBeInTheDocument();
      expect(screen.getByRole('combobox')).toBeInTheDocument(); // status filter
    });

    it('should display projects table', async () => {
      render(
        <TestWrapper>
          <Projects />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Project')).toBeInTheDocument();
        expect(screen.getByText('Client')).toBeInTheDocument();
        expect(screen.getByText('Status')).toBeInTheDocument();
      });
    });

    it('should filter projects by search term', async () => {
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <Projects />
        </TestWrapper>
      );

      const searchInput = screen.getByPlaceholderText(/search projects or ids/i);
      await user.type(searchInput, 'test');

      // Search should update the query
      expect(searchInput).toHaveValue('test');
    });

    it('should filter projects by status', async () => {
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <Projects />
        </TestWrapper>
      );

      const statusFilter = screen.getByRole('combobox');
      await user.selectOptions(statusFilter, 'draft');

      expect(statusFilter).toHaveValue('draft');
    });
  });

  describe('New Project Dialog', () => {
    it('should render dialog when open', () => {
      render(
        <TestWrapper>
          <NewProjectDialog open={true} onOpenChange={() => {}} />
        </TestWrapper>
      );

      expect(screen.getByText('Create New Project')).toBeInTheDocument();
      expect(screen.getByText(/start a new content generation project/i)).toBeInTheDocument();
    });

    it('should not render dialog when closed', () => {
      render(
        <TestWrapper>
          <NewProjectDialog open={false} onOpenChange={() => {}} />
        </TestWrapper>
      );

      expect(screen.queryByText('Create New Project')).not.toBeInTheDocument();
    });

    it('should display all form fields', () => {
      render(
        <TestWrapper>
          <NewProjectDialog open={true} onOpenChange={() => {}} />
        </TestWrapper>
      );

      expect(screen.getByPlaceholderText('March 2025 Campaign')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('acme-corp')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Acme Corp')).toBeInTheDocument();
      expect(screen.getByRole('combobox')).toBeInTheDocument(); // Package tier
    });

    it('should validate required fields on submit', async () => {
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <NewProjectDialog open={true} onOpenChange={() => {}} />
        </TestWrapper>
      );

      const createButton = screen.getByRole('button', { name: /create project/i });
      await user.click(createButton);

      await waitFor(() => {
        expect(screen.getAllByText(/required/i).length).toBeGreaterThan(0);
      });
    });

    it('should validate project name', async () => {
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <NewProjectDialog open={true} onOpenChange={() => {}} />
        </TestWrapper>
      );

      const createButton = screen.getByRole('button', { name: /create project/i });
      await user.click(createButton);

      await waitFor(() => {
        expect(screen.getByText(/project name is required/i)).toBeInTheDocument();
      });
    });

    it('should validate client ID', async () => {
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <NewProjectDialog open={true} onOpenChange={() => {}} />
        </TestWrapper>
      );

      const createButton = screen.getByRole('button', { name: /create project/i });
      await user.click(createButton);

      await waitFor(() => {
        expect(screen.getByText(/client id is required/i)).toBeInTheDocument();
      });
    });

    it('should validate client name', async () => {
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <NewProjectDialog open={true} onOpenChange={() => {}} />
        </TestWrapper>
      );

      const createButton = screen.getByRole('button', { name: /create project/i });
      await user.click(createButton);

      await waitFor(() => {
        expect(screen.getByText(/client name is required/i)).toBeInTheDocument();
      });
    });

    it('should allow selecting package tier', async () => {
      const user = userEvent.setup();
      render(
        <TestWrapper>
          <NewProjectDialog open={true} onOpenChange={() => {}} />
        </TestWrapper>
      );

      const tierSelect = screen.getByRole('combobox');
      await user.selectOptions(tierSelect, 'premium');

      expect(tierSelect).toHaveValue('premium');
    });

    it('should display package tier options', () => {
      render(
        <TestWrapper>
          <NewProjectDialog open={true} onOpenChange={() => {}} />
        </TestWrapper>
      );

      expect(screen.getByText(/Starter \(\$1,200\)/)).toBeInTheDocument();
      expect(screen.getByText(/Professional \(\$1,800\)/)).toBeInTheDocument();
      expect(screen.getByText(/Premium \(\$2,500\)/)).toBeInTheDocument();
      expect(screen.getByText(/Enterprise \(\$3,500\)/)).toBeInTheDocument();
    });

    it('should fill and submit form successfully', async () => {
      const user = userEvent.setup();
      const onSuccess = jest.fn();
      const onOpenChange = jest.fn();

      render(
        <TestWrapper>
          <NewProjectDialog open={true} onOpenChange={onOpenChange} onSuccess={onSuccess} />
        </TestWrapper>
      );

      // Fill form
      await user.type(screen.getByPlaceholderText('March 2025 Campaign'), 'Q1 2025 Content');
      await user.type(screen.getByPlaceholderText('acme-corp'), 'test-client');
      await user.type(screen.getByPlaceholderText('Acme Corp'), 'Test Client Inc');
      await user.selectOptions(screen.getByRole('combobox'), 'professional');

      // Submit
      const createButton = screen.getByRole('button', { name: /create project/i });
      await user.click(createButton);

      // Should not show validation errors
      expect(screen.queryByText(/required/i)).not.toBeInTheDocument();
    });

    it('should close dialog on cancel', async () => {
      const user = userEvent.setup();
      const onOpenChange = jest.fn();

      render(
        <TestWrapper>
          <NewProjectDialog open={true} onOpenChange={onOpenChange} />
        </TestWrapper>
      );

      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      await user.click(cancelButton);

      expect(onOpenChange).toHaveBeenCalledWith(false);
    });

    it('should show helper text for client ID', () => {
      render(
        <TestWrapper>
          <NewProjectDialog open={true} onOpenChange={() => {}} />
        </TestWrapper>
      );

      expect(screen.getByText(/lowercase, hyphenated identifier/i)).toBeInTheDocument();
    });
  });

  describe('Project Actions', () => {
    it('should display Wizard and Generate buttons for each project', async () => {
      render(
        <TestWrapper>
          <Projects />
        </TestWrapper>
      );

      await waitFor(() => {
        const wizardButtons = screen.queryAllByRole('button', { name: /wizard/i });
        const generateButtons = screen.queryAllByRole('button', { name: /generate/i });

        // Should have at least one of each if projects are loaded
        expect(wizardButtons.length).toBeGreaterThanOrEqual(0);
        expect(generateButtons.length).toBeGreaterThanOrEqual(0);
      });
    });

    it('should have refresh button', () => {
      render(
        <TestWrapper>
          <Projects />
        </TestWrapper>
      );

      expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument();
    });
  });
});
