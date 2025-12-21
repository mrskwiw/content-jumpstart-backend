import { Moon, Sun, Monitor } from 'lucide-react';
import { useTheme } from '@/contexts/ThemeContext';

export default function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  return (
    <div className="inline-flex items-center rounded-md border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 p-1 shadow-sm">
      <button
        onClick={() => setTheme('light')}
        className={`
          inline-flex items-center justify-center rounded px-3 py-1.5 text-sm font-medium transition-colors
          ${
            theme === 'light'
              ? 'bg-primary-500 text-primary-50 shadow-sm'
              : 'text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-700'
          }
        `}
        aria-label="Light theme"
      >
        <Sun className="h-4 w-4" />
      </button>

      <button
        onClick={() => setTheme('system')}
        className={`
          inline-flex items-center justify-center rounded px-3 py-1.5 text-sm font-medium transition-colors
          ${
            theme === 'system'
              ? 'bg-primary-500 text-primary-50 shadow-sm'
              : 'text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-700'
          }
        `}
        aria-label="System theme"
      >
        <Monitor className="h-4 w-4" />
      </button>

      <button
        onClick={() => setTheme('dark')}
        className={`
          inline-flex items-center justify-center rounded px-3 py-1.5 text-sm font-medium transition-colors
          ${
            theme === 'dark'
              ? 'bg-primary-500 text-primary-50 shadow-sm'
              : 'text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-700'
          }
        `}
        aria-label="Dark theme"
      >
        <Moon className="h-4 w-4" />
      </button>
    </div>
  );
}
