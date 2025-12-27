import { useState, useRef, useEffect } from 'react';
import { MoreVertical, Archive, Copy, Download, ExternalLink, Trash2, Edit, Eye } from 'lucide-react';

export interface QuickAction {
  label: string;
  icon?: 'archive' | 'copy' | 'download' | 'external' | 'delete' | 'edit' | 'view';
  onClick: () => void;
  variant?: 'default' | 'danger';
  dividerAfter?: boolean;
}

interface QuickActionsDropdownProps {
  actions: QuickAction[];
  align?: 'left' | 'right';
  size?: 'sm' | 'md';
}

const ICON_MAP = {
  archive: Archive,
  copy: Copy,
  download: Download,
  external: ExternalLink,
  delete: Trash2,
  edit: Edit,
  view: Eye,
};

export function QuickActionsDropdown({ actions, align = 'right', size = 'md' }: QuickActionsDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen]);

  const handleAction = (action: QuickAction) => {
    action.onClick();
    setIsOpen(false);
  };

  const buttonSizeClasses = {
    sm: 'h-7 w-7',
    md: 'h-8 w-8',
  };

  const iconSizeClasses = {
    sm: 'h-3.5 w-3.5',
    md: 'h-4 w-4',
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Trigger button */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          setIsOpen(!isOpen);
        }}
        className={`inline-flex items-center justify-center rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400 hover:bg-neutral-50 dark:hover:bg-neutral-700 hover:text-neutral-900 dark:hover:text-neutral-100 transition-colors ${buttonSizeClasses[size]}`}
        title="More actions"
      >
        <MoreVertical className={iconSizeClasses[size]} />
      </button>

      {/* Dropdown menu */}
      {isOpen && (
        <div
          className={`absolute z-50 mt-2 min-w-[160px] rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 shadow-lg ${
            align === 'right' ? 'right-0' : 'left-0'
          }`}
        >
          <div className="py-1">
            {actions.map((action, index) => {
              const Icon = action.icon ? ICON_MAP[action.icon] : null;
              const isLast = index === actions.length - 1;
              const hasDropdown = !isLast && action.dividerAfter;

              return (
                <div key={index}>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleAction(action);
                    }}
                    className={`flex w-full items-center gap-3 px-4 py-2 text-sm transition-colors ${
                      action.variant === 'danger'
                        ? 'text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-900/20'
                        : 'text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-700'
                    }`}
                  >
                    {Icon && <Icon className="h-4 w-4" />}
                    <span>{action.label}</span>
                  </button>
                  {hasDropdown && (
                    <div className="my-1 border-t border-neutral-200 dark:border-neutral-700" />
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
