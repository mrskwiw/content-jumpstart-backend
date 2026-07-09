/**
 * Comprehensive tests for Pagination component
 */
import { describe, it, expect, jest } from '@jest/globals';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Pagination } from '../Pagination';
import type { PaginationMetadata } from '@/types/pagination';

describe('Pagination', () => {
  const mockOnPageChange = jest.fn<(page: number) => void>();
  const mockOnCursorChange = jest.fn<(cursor: string) => void>();
  const mockOnPageSizeChange = jest.fn<(size: number) => void>();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('rendering', () => {
    it('should return null when metadata is undefined', () => {
      const { container } = render(
        <Pagination currentPage={1} onPageChange={mockOnPageChange} />
      );
      expect(container.firstChild).toBeNull();
    });

    it('should return null when on page 1 with no next/prev', () => {
      const metadata: PaginationMetadata = {
        has_next: false,
        has_prev: false,
        total: 10,
        total_pages: 1,
        strategy: 'offset',
      };

      const { container } = render(
        <Pagination
          metadata={metadata}
          currentPage={1}
          onPageChange={mockOnPageChange}
        />
      );
      expect(container.firstChild).toBeNull();
    });

    it('should render pagination with offset strategy', () => {
      const metadata: PaginationMetadata = {
        has_next: true,
        has_prev: false,
        total: 100,
        total_pages: 5,
        strategy: 'offset',
      };

      render(
        <Pagination
          metadata={metadata}
          currentPage={1}
          onPageChange={mockOnPageChange}
        />
      );

      expect(screen.getByText(/Showing page/i)).toBeInTheDocument();
      // The total count and its label render in separate elements.
      expect(screen.getByText('100')).toBeInTheDocument();
      expect(screen.getByText(/total items/i)).toBeInTheDocument();
    });

    it('should render pagination with cursor strategy', () => {
      const metadata: PaginationMetadata = {
        has_next: true,
        has_prev: false,
        strategy: 'cursor',
        next_cursor: 'next_abc',
      };

      render(
        <Pagination
          metadata={metadata}
          currentPage={1}
          onPageChange={mockOnPageChange}
          onCursorChange={mockOnCursorChange}
        />
      );

      expect(screen.getByText(/Deep pagination mode/i)).toBeInTheDocument();
    });

    it('should render page numbers for offset pagination with <= 10 pages', () => {
      const metadata: PaginationMetadata = {
        has_next: true,
        has_prev: false,
        total: 50,
        total_pages: 5,
        strategy: 'offset',
      };

      render(
        <Pagination
          metadata={metadata}
          currentPage={1}
          onPageChange={mockOnPageChange}
        />
      );

      expect(screen.getByRole('button', { name: '1' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: '2' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: '5' })).toBeInTheDocument();
    });

    it('should not render page numbers for > 10 pages', () => {
      const metadata: PaginationMetadata = {
        has_next: true,
        has_prev: false,
        total: 500,
        total_pages: 25,
        strategy: 'offset',
      };

      render(
        <Pagination
          metadata={metadata}
          currentPage={1}
          onPageChange={mockOnPageChange}
        />
      );

      expect(screen.queryByRole('button', { name: '1' })).not.toBeInTheDocument();
    });
  });

  describe('navigation', () => {
    it('should call onPageChange when next button is clicked (offset)', async () => {
      const user = userEvent.setup();
      const metadata: PaginationMetadata = {
        has_next: true,
        has_prev: false,
        total: 100,
        total_pages: 5,
        strategy: 'offset',
      };

      render(
        <Pagination
          metadata={metadata}
          currentPage={1}
          onPageChange={mockOnPageChange}
        />
      );

      const nextButton = screen.getAllByRole('button', { name: /next/i })[0];
      await user.click(nextButton);

      expect(mockOnPageChange).toHaveBeenCalledWith(2);
    });

    it('should call onPageChange when previous button is clicked (offset)', async () => {
      const user = userEvent.setup();
      const metadata: PaginationMetadata = {
        has_next: true,
        has_prev: true,
        total: 100,
        total_pages: 5,
        strategy: 'offset',
      };

      render(
        <Pagination
          metadata={metadata}
          currentPage={3}
          onPageChange={mockOnPageChange}
        />
      );

      const prevButton = screen.getAllByRole('button', { name: /previous/i })[0];
      await user.click(prevButton);

      expect(mockOnPageChange).toHaveBeenCalledWith(2);
    });

    it('should call onCursorChange when next is clicked (cursor)', async () => {
      const user = userEvent.setup();
      const metadata: PaginationMetadata = {
        has_next: true,
        has_prev: false,
        strategy: 'cursor',
        next_cursor: 'cursor_123',
      };

      render(
        <Pagination
          metadata={metadata}
          currentPage={1}
          onPageChange={mockOnPageChange}
          onCursorChange={mockOnCursorChange}
        />
      );

      const nextButton = screen.getAllByRole('button', { name: /next/i })[0];
      await user.click(nextButton);

      expect(mockOnCursorChange).toHaveBeenCalledWith('cursor_123');
      expect(mockOnPageChange).not.toHaveBeenCalled();
    });

    it('should call onCursorChange when previous is clicked (cursor)', async () => {
      const user = userEvent.setup();
      const metadata: PaginationMetadata = {
        has_next: true,
        has_prev: true,
        strategy: 'cursor',
        prev_cursor: 'cursor_prev',
      };

      render(
        <Pagination
          metadata={metadata}
          currentPage={2}
          onPageChange={mockOnPageChange}
          onCursorChange={mockOnCursorChange}
        />
      );

      const prevButton = screen.getAllByRole('button', { name: /previous/i })[0];
      await user.click(prevButton);

      expect(mockOnCursorChange).toHaveBeenCalledWith('cursor_prev');
    });

    it('should call onPageChange when page number is clicked', async () => {
      const user = userEvent.setup();
      const metadata: PaginationMetadata = {
        has_next: true,
        has_prev: false,
        total: 50,
        total_pages: 5,
        strategy: 'offset',
      };

      render(
        <Pagination
          metadata={metadata}
          currentPage={1}
          onPageChange={mockOnPageChange}
        />
      );

      const page3Button = screen.getByRole('button', { name: '3' });
      await user.click(page3Button);

      expect(mockOnPageChange).toHaveBeenCalledWith(3);
    });

    it('should disable previous button when has_prev is false', () => {
      const metadata: PaginationMetadata = {
        has_next: true,
        has_prev: false,
        total: 100,
        total_pages: 5,
        strategy: 'offset',
      };

      render(
        <Pagination
          metadata={metadata}
          currentPage={1}
          onPageChange={mockOnPageChange}
        />
      );

      const prevButtons = screen.getAllByRole('button', { name: /previous/i });
      prevButtons.forEach(btn => {
        expect(btn).toBeDisabled();
      });
    });

    it('should disable next button when has_next is false', () => {
      const metadata: PaginationMetadata = {
        has_next: false,
        has_prev: true,
        total: 100,
        total_pages: 5,
        strategy: 'offset',
      };

      render(
        <Pagination
          metadata={metadata}
          currentPage={5}
          onPageChange={mockOnPageChange}
        />
      );

      const nextButtons = screen.getAllByRole('button', { name: /next/i });
      nextButtons.forEach(btn => {
        expect(btn).toBeDisabled();
      });
    });
  });

  describe('page size selector', () => {
    it('should render page size selector when showPageSize is true', () => {
      const metadata: PaginationMetadata = {
        has_next: true,
        has_prev: false,
        total: 100,
        total_pages: 5,
        strategy: 'offset',
      };

      render(
        <Pagination
          metadata={metadata}
          currentPage={1}
          onPageChange={mockOnPageChange}
          showPageSize={true}
          pageSize={20}
          onPageSizeChange={mockOnPageSizeChange}
        />
      );

      expect(screen.getByLabelText(/items per page/i)).toBeInTheDocument();
    });

    it('should call onPageSizeChange when size is changed', async () => {
      const user = userEvent.setup();
      const metadata: PaginationMetadata = {
        has_next: true,
        has_prev: false,
        total: 100,
        total_pages: 5,
        strategy: 'offset',
      };

      render(
        <Pagination
          metadata={metadata}
          currentPage={1}
          onPageChange={mockOnPageChange}
          showPageSize={true}
          pageSize={20}
          onPageSizeChange={mockOnPageSizeChange}
        />
      );

      const select = screen.getByLabelText(/items per page/i);
      await user.selectOptions(select, '50');

      expect(mockOnPageSizeChange).toHaveBeenCalledWith(50);
    });

    it('should not render page size selector when showPageSize is false', () => {
      const metadata: PaginationMetadata = {
        has_next: true,
        has_prev: false,
        total: 100,
        total_pages: 5,
        strategy: 'offset',
      };

      render(
        <Pagination
          metadata={metadata}
          currentPage={1}
          onPageChange={mockOnPageChange}
          showPageSize={false}
        />
      );

      expect(screen.queryByLabelText(/items per page/i)).not.toBeInTheDocument();
    });
  });

  describe('current page highlighting', () => {
    it('should highlight the current page button', () => {
      const metadata: PaginationMetadata = {
        has_next: true,
        has_prev: true,
        total: 50,
        total_pages: 5,
        strategy: 'offset',
      };

      render(
        <Pagination
          metadata={metadata}
          currentPage={3}
          onPageChange={mockOnPageChange}
        />
      );

      const page3Button = screen.getByRole('button', { name: '3' });
      expect(page3Button).toHaveClass('bg-blue-600');
    });
  });
});
