import { Linkedin, Twitter, Facebook, Mail, PenLine } from 'lucide-react';

interface PlatformTarget {
  id: string;
  name: string;
  description: string;
  category: 'social' | 'longform';
  icon: typeof Linkedin;
  charLimit?: number;
  recommended?: boolean;
}

const platforms: PlatformTarget[] = [
  // Social Media
  {
    id: 'linkedin',
    name: 'LinkedIn',
    description: 'Professional networking posts',
    category: 'social',
    icon: Linkedin,
    charLimit: 3000,
    recommended: true,
  },
  {
    id: 'twitter',
    name: 'Microblog',
    description: 'Short-form microblog posts',
    category: 'social',
    icon: Twitter,
    charLimit: 280,
  },
  {
    id: 'facebook',
    name: 'Facebook',
    description: 'Social engagement posts',
    category: 'social',
    icon: Facebook,
    charLimit: 63206,
  },
  // Long-form
  {
    id: 'blog',
    name: 'Blog',
    description: 'Long-form blog articles',
    category: 'longform',
    icon: PenLine,
  },
  {
    id: 'email',
    name: 'Email Newsletter',
    description: 'Direct audience newsletter',
    category: 'longform',
    icon: Mail,
  },
];

interface PlatformSelectorProps {
  selected: string;
  onChange: (platform: string) => void;
}

export function PlatformSelector({ selected, onChange }: PlatformSelectorProps) {
  const categories = [
    { id: 'social', label: 'Social Media', platforms: platforms.filter(p => p.category === 'social') },
    { id: 'longform', label: 'Long-form', platforms: platforms.filter(p => p.category === 'longform') },
  ];

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-medium text-neutral-900 dark:text-neutral-100 mb-1">
          Target Platform
        </h3>
        <p className="text-sm text-neutral-600 dark:text-neutral-400">
          Select where you'll publish this content. This optimizes the generated posts for your platform.
        </p>
      </div>

      <div className="space-y-6">
        {categories.map(category => (
          <div key={category.id}>
            <h4 className="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-3">
              {category.label}
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {category.platforms.map(platform => {
                const Icon = platform.icon;
                const isSelected = selected === platform.id;

                return (
                  <label
                    key={platform.id}
                    className={`
                      relative flex items-start p-4 cursor-pointer rounded-lg border-2 transition-all
                      ${
                        isSelected
                          ? 'border-primary-600 bg-primary-50 dark:bg-primary-900/20 dark:border-primary-500'
                          : 'border-neutral-200 dark:border-neutral-700 hover:border-neutral-300 dark:hover:border-neutral-600 bg-white dark:bg-neutral-900'
                      }
                    `}
                  >
                    <input
                      type="radio"
                      name="platform"
                      value={platform.id}
                      checked={isSelected}
                      onChange={() => onChange(platform.id)}
                      className="sr-only"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <Icon className={`h-5 w-5 flex-shrink-0 ${isSelected ? 'text-primary-600 dark:text-primary-400' : 'text-neutral-500 dark:text-neutral-400'}`} />
                        <span className={`font-medium text-sm ${isSelected ? 'text-primary-900 dark:text-primary-100' : 'text-neutral-900 dark:text-neutral-100'}`}>
                          {platform.name}
                          {platform.recommended && (
                            <span className="ml-2 inline-flex items-center rounded-full bg-emerald-100 dark:bg-emerald-900/20 px-2 py-0.5 text-xs font-medium text-emerald-800 dark:text-emerald-300">
                              Popular
                            </span>
                          )}
                        </span>
                      </div>
                      <p className={`text-xs ${isSelected ? 'text-primary-700 dark:text-primary-300' : 'text-neutral-500 dark:text-neutral-400'}`}>
                        {platform.description}
                      </p>
                      {platform.charLimit && (
                        <p className={`text-xs mt-1 ${isSelected ? 'text-primary-600 dark:text-primary-400' : 'text-neutral-400 dark:text-neutral-500'}`}>
                          Max {platform.charLimit.toLocaleString()} chars
                        </p>
                      )}
                    </div>
                    {isSelected && (
                      <div className="absolute top-3 right-3">
                        <div className="h-5 w-5 rounded-full bg-primary-600 dark:bg-primary-500 flex items-center justify-center">
                          <svg className="h-3 w-3 text-white" fill="currentColor" viewBox="0 0 12 12">
                            <path d="M10 3L4.5 8.5L2 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
                          </svg>
                        </div>
                      </div>
                    )}
                  </label>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
