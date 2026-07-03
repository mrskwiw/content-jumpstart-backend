/**
 * Tests for Dialog component - Dark mode support
 */
import { render, screen, fireEvent } from '@testing-library/react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '../dialog';

describe('Dialog', () => {
  describe('Basic Rendering', () => {
    it('should not render when open is false', () => {
      const { container } = render(
        <Dialog open={false} onOpenChange={jest.fn()}>
          <div>Dialog content</div>
        </Dialog>
      );

      expect(container.firstChild).toBeNull();
    });

    it('should render when open is true', () => {
      render(
        <Dialog open={true} onOpenChange={jest.fn()}>
          <div>Dialog content</div>
        </Dialog>
      );

      expect(screen.getByText('Dialog content')).toBeInTheDocument();
    });

    it('should render backdrop overlay', () => {
      const { container } = render(
        <Dialog open={true} onOpenChange={jest.fn()}>
          <div>Dialog content</div>
        </Dialog>
      );

      const backdrop = container.querySelector('.bg-black\\/50');
      expect(backdrop).toBeInTheDocument();
    });
  });

  describe('Dark Mode Support', () => {
    it('should have dark mode class on dialog container', () => {
      const { container } = render(
        <Dialog open={true} onOpenChange={jest.fn()}>
          <div>Dialog content</div>
        </Dialog>
      );

      const dialogContainer = container.querySelector('.bg-white');
      expect(dialogContainer).toHaveClass('dark:bg-neutral-900');
    });

    it('should apply light mode background by default', () => {
      const { container } = render(
        <Dialog open={true} onOpenChange={jest.fn()}>
          <div>Dialog content</div>
        </Dialog>
      );

      const dialogContainer = container.querySelector('.bg-white');
      expect(dialogContainer).toBeInTheDocument();
    });
  });

  describe('Click Handling', () => {
    it('should call onOpenChange when backdrop is clicked', () => {
      const handleOpenChange = jest.fn();
      const { container } = render(
        <Dialog open={true} onOpenChange={handleOpenChange}>
          <div>Dialog content</div>
        </Dialog>
      );

      const backdrop = container.querySelector('.fixed.inset-0');
      fireEvent.click(backdrop!);

      expect(handleOpenChange).toHaveBeenCalledWith(false);
    });

    it('should not call onOpenChange when dialog content is clicked', () => {
      const handleOpenChange = jest.fn();
      render(
        <Dialog open={true} onOpenChange={handleOpenChange}>
          <div>Dialog content</div>
        </Dialog>
      );

      fireEvent.click(screen.getByText('Dialog content'));

      expect(handleOpenChange).not.toHaveBeenCalled();
    });
  });
});

describe('DialogContent', () => {
  it('should render children', () => {
    render(
      <DialogContent>
        <p>Content paragraph</p>
      </DialogContent>
    );

    expect(screen.getByText('Content paragraph')).toBeInTheDocument();
  });

  it('should apply spacing classes', () => {
    const { container } = render(
      <DialogContent>
        <p>Content</p>
      </DialogContent>
    );

    const content = container.firstChild;
    expect(content).toHaveClass('space-y-4');
  });

  it('should merge custom className', () => {
    const { container } = render(
      <DialogContent className="custom-class">
        <p>Content</p>
      </DialogContent>
    );

    const content = container.firstChild;
    expect(content).toHaveClass('space-y-4');
    expect(content).toHaveClass('custom-class');
  });
});

describe('DialogHeader', () => {
  it('should render children', () => {
    render(
      <DialogHeader>
        <h2>Header title</h2>
      </DialogHeader>
    );

    expect(screen.getByText('Header title')).toBeInTheDocument();
  });

  it('should apply spacing classes', () => {
    const { container } = render(
      <DialogHeader>
        <h2>Header</h2>
      </DialogHeader>
    );

    expect(container.firstChild).toHaveClass('space-y-2');
  });
});

describe('DialogTitle', () => {
  it('should render as h2 element', () => {
    render(<DialogTitle>Dialog Title</DialogTitle>);

    const title = screen.getByText('Dialog Title');
    expect(title.tagName).toBe('H2');
  });

  it('should apply light mode text color by default', () => {
    render(<DialogTitle>Dialog Title</DialogTitle>);

    const title = screen.getByText('Dialog Title');
    expect(title).toHaveClass('text-neutral-900');
  });

  it('should have dark mode text color class', () => {
    render(<DialogTitle>Dialog Title</DialogTitle>);

    const title = screen.getByText('Dialog Title');
    expect(title).toHaveClass('dark:text-neutral-100');
  });

  it('should apply font styles', () => {
    render(<DialogTitle>Dialog Title</DialogTitle>);

    const title = screen.getByText('Dialog Title');
    expect(title).toHaveClass('text-lg');
    expect(title).toHaveClass('font-semibold');
  });
});

describe('DialogDescription', () => {
  it('should render as p element', () => {
    render(<DialogDescription>Dialog description text</DialogDescription>);

    const description = screen.getByText('Dialog description text');
    expect(description.tagName).toBe('P');
  });

  it('should apply light mode text color by default', () => {
    render(<DialogDescription>Description</DialogDescription>);

    const description = screen.getByText('Description');
    expect(description).toHaveClass('text-neutral-600');
  });

  it('should have dark mode text color class', () => {
    render(<DialogDescription>Description</DialogDescription>);

    const description = screen.getByText('Description');
    expect(description).toHaveClass('dark:text-neutral-400');
  });

  it('should apply text size class', () => {
    render(<DialogDescription>Description</DialogDescription>);

    const description = screen.getByText('Description');
    expect(description).toHaveClass('text-sm');
  });
});

describe('DialogFooter', () => {
  it('should render children', () => {
    render(
      <DialogFooter>
        <button>Cancel</button>
        <button>Confirm</button>
      </DialogFooter>
    );

    expect(screen.getByText('Cancel')).toBeInTheDocument();
    expect(screen.getByText('Confirm')).toBeInTheDocument();
  });

  it('should apply flex layout classes', () => {
    const { container } = render(
      <DialogFooter>
        <button>Action</button>
      </DialogFooter>
    );

    expect(container.firstChild).toHaveClass('flex');
    expect(container.firstChild).toHaveClass('justify-end');
    expect(container.firstChild).toHaveClass('gap-2');
  });
});

describe('Dialog Integration', () => {
  it('should render complete dialog with all components', () => {
    const handleOpenChange = jest.fn();
    render(
      <Dialog open={true} onOpenChange={handleOpenChange}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirm Action</DialogTitle>
            <DialogDescription>
              Are you sure you want to proceed with this action?
            </DialogDescription>
          </DialogHeader>
          <div>Additional content</div>
          <DialogFooter>
            <button onClick={() => handleOpenChange(false)}>Cancel</button>
            <button>Confirm</button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    );

    expect(screen.getByText('Confirm Action')).toBeInTheDocument();
    expect(
      screen.getByText('Are you sure you want to proceed with this action?')
    ).toBeInTheDocument();
    expect(screen.getByText('Additional content')).toBeInTheDocument();
    expect(screen.getByText('Cancel')).toBeInTheDocument();
    expect(screen.getByText('Confirm')).toBeInTheDocument();
  });

  it('should close dialog when Cancel button is clicked', () => {
    const handleOpenChange = jest.fn();
    render(
      <Dialog open={true} onOpenChange={handleOpenChange}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirm Action</DialogTitle>
          </DialogHeader>
          <DialogFooter>
            <button onClick={() => handleOpenChange(false)}>Cancel</button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    );

    fireEvent.click(screen.getByText('Cancel'));
    expect(handleOpenChange).toHaveBeenCalledWith(false);
  });
});

describe('Accessibility', () => {
  it('should have proper z-index for overlay', () => {
    const { container } = render(
      <Dialog open={true} onOpenChange={jest.fn()}>
        <div>Content</div>
      </Dialog>
    );

    const backdrop = container.querySelector('.fixed.inset-0');
    expect(backdrop).toHaveClass('z-50');
  });

  it('should have proper positioning for centered dialog', () => {
    const { container } = render(
      <Dialog open={true} onOpenChange={jest.fn()}>
        <div>Content</div>
      </Dialog>
    );

    const backdrop = container.querySelector('.fixed.inset-0');
    expect(backdrop).toHaveClass('flex');
    expect(backdrop).toHaveClass('items-center');
    expect(backdrop).toHaveClass('justify-center');
  });

  it('should have max width constraint on dialog', () => {
    const { container } = render(
      <Dialog open={true} onOpenChange={jest.fn()}>
        <div>Content</div>
      </Dialog>
    );

    const dialogBox = container.querySelector('.max-w-lg');
    expect(dialogBox).toBeInTheDocument();
  });
});
