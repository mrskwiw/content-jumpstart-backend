# UI Design System - Content Jumpstart Operator Dashboard

## Design Philosophy

**Modern, Sleek, Professional** - A warm, earthy design system built around browns and neutrals, avoiding purple entirely. Designed for operator efficiency with clear visual hierarchy and accessible contrast ratios.

---

## Color Palette

### Light Theme (Default)
```css
/* Primary - Warm Browns */
--primary-50: #faf8f5;      /* Lightest cream */
--primary-100: #f5f0e8;     /* Soft cream */
--primary-200: #e8dcc8;     /* Light tan */
--primary-300: #d4c1a0;     /* Warm tan */
--primary-400: #b89968;     /* Medium brown */
--primary-500: #8b6f47;     /* Rich brown (brand color) */
--primary-600: #6b5538;     /* Deep brown */
--primary-700: #4a3a26;     /* Dark brown */
--primary-800: #2d2318;     /* Darker brown */
--primary-900: #1a140e;     /* Nearly black brown */

/* Neutrals - Cool Grays */
--neutral-50: #fafafa;
--neutral-100: #f5f5f5;
--neutral-200: #e5e5e5;
--neutral-300: #d4d4d4;
--neutral-400: #a3a3a3;
--neutral-500: #737373;
--neutral-600: #525252;
--neutral-700: #404040;
--neutral-800: #262626;
--neutral-900: #171717;

/* Semantic Colors */
--success-50: #f0fdf4;
--success-500: #22c55e;
--success-600: #16a34a;
--success-700: #15803d;

--warning-50: #fffbeb;
--warning-500: #f59e0b;
--warning-600: #d97706;
--warning-700: #b45309;

--error-50: #fef2f2;
--error-500: #ef4444;
--error-600: #dc2626;
--error-700: #b91c1c;

--info-50: #eff6ff;
--info-500: #3b82f6;
--info-600: #2563eb;
--info-700: #1d4ed8;

/* Surface Colors */
--background: #ffffff;
--surface: #fafafa;
--surface-elevated: #ffffff;
--border: #e5e5e5;
--border-strong: #d4d4d4;

/* Text Colors */
--text-primary: #171717;
--text-secondary: #525252;
--text-tertiary: #a3a3a3;
--text-on-primary: #faf8f5;
```

### Dark Theme
```css
/* Primary - Warm Browns (adjusted for dark mode) */
--primary-50: #1a140e;      /* Darkest */
--primary-100: #2d2318;
--primary-200: #4a3a26;
--primary-300: #6b5538;
--primary-400: #8b6f47;
--primary-500: #a68a5c;     /* Rich brown (brand color) */
--primary-600: #b89968;
--primary-700: #d4c1a0;
--primary-800: #e8dcc8;
--primary-900: #faf8f5;     /* Lightest cream */

/* Neutrals - Cool Grays (inverted) */
--neutral-50: #0a0a0a;
--neutral-100: #171717;
--neutral-200: #262626;
--neutral-300: #404040;
--neutral-400: #525252;
--neutral-500: #737373;
--neutral-600: #a3a3a3;
--neutral-700: #d4d4d4;
--neutral-800: #e5e5e5;
--neutral-900: #fafafa;

/* Semantic Colors (slightly adjusted for dark) */
--success-500: #22c55e;
--success-600: #4ade80;

--warning-500: #f59e0b;
--warning-600: #fbbf24;

--error-500: #ef4444;
--error-600: #f87171;

--info-500: #3b82f6;
--info-600: #60a5fa;

/* Surface Colors */
--background: #0a0a0a;
--surface: #171717;
--surface-elevated: #262626;
--border: #404040;
--border-strong: #525252;

/* Text Colors */
--text-primary: #fafafa;
--text-secondary: #a3a3a3;
--text-tertiary: #737373;
--text-on-primary: #0a0a0a;
```

---

## Typography Scale

```css
/* Font Families */
--font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
--font-mono: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace;

/* Font Sizes */
--text-xs: 0.75rem;      /* 12px */
--text-sm: 0.875rem;     /* 14px */
--text-base: 1rem;       /* 16px */
--text-lg: 1.125rem;     /* 18px */
--text-xl: 1.25rem;      /* 20px */
--text-2xl: 1.5rem;      /* 24px */
--text-3xl: 1.875rem;    /* 30px */
--text-4xl: 2.25rem;     /* 36px */

/* Font Weights */
--font-normal: 400;
--font-medium: 500;
--font-semibold: 600;
--font-bold: 700;

/* Line Heights */
--leading-tight: 1.25;
--leading-snug: 1.375;
--leading-normal: 1.5;
--leading-relaxed: 1.625;
```

---

## Spacing Scale

```css
--spacing-0: 0;
--spacing-1: 0.25rem;    /* 4px */
--spacing-2: 0.5rem;     /* 8px */
--spacing-3: 0.75rem;    /* 12px */
--spacing-4: 1rem;       /* 16px */
--spacing-5: 1.25rem;    /* 20px */
--spacing-6: 1.5rem;     /* 24px */
--spacing-8: 2rem;       /* 32px */
--spacing-10: 2.5rem;    /* 40px */
--spacing-12: 3rem;      /* 48px */
--spacing-16: 4rem;      /* 64px */
--spacing-20: 5rem;      /* 80px */
```

---

## Border Radius

```css
--radius-none: 0;
--radius-sm: 0.25rem;    /* 4px - Tight elements */
--radius-md: 0.5rem;     /* 8px - Cards, buttons */
--radius-lg: 0.75rem;    /* 12px - Panels */
--radius-xl: 1rem;       /* 16px - Modals */
--radius-full: 9999px;   /* Pills, avatars */
```

---

## Shadows

```css
/* Light Theme Shadows */
--shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
--shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
--shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
--shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);

/* Dark Theme Shadows */
--shadow-sm-dark: 0 1px 2px 0 rgba(0, 0, 0, 0.3);
--shadow-md-dark: 0 4px 6px -1px rgba(0, 0, 0, 0.4), 0 2px 4px -1px rgba(0, 0, 0, 0.3);
--shadow-lg-dark: 0 10px 15px -3px rgba(0, 0, 0, 0.5), 0 4px 6px -2px rgba(0, 0, 0, 0.4);
--shadow-xl-dark: 0 20px 25px -5px rgba(0, 0, 0, 0.6), 0 10px 10px -5px rgba(0, 0, 0, 0.5);
```

---

## Component Patterns

### Buttons

**Primary Button (Brand Brown)**
```tsx
<button className="
  px-4 py-2 rounded-md
  bg-primary-500 text-primary-50
  hover:bg-primary-600 active:bg-primary-700
  font-medium text-sm
  shadow-sm hover:shadow-md
  transition-all duration-200
  disabled:opacity-50 disabled:cursor-not-allowed
">
  Primary Action
</button>
```

**Secondary Button**
```tsx
<button className="
  px-4 py-2 rounded-md
  border border-neutral-300 dark:border-neutral-600
  bg-white dark:bg-neutral-800
  text-neutral-700 dark:text-neutral-200
  hover:bg-neutral-50 dark:hover:bg-neutral-700
  font-medium text-sm
  shadow-sm hover:shadow-md
  transition-all duration-200
">
  Secondary Action
</button>
```

**Ghost Button**
```tsx
<button className="
  px-4 py-2 rounded-md
  text-neutral-700 dark:text-neutral-200
  hover:bg-neutral-100 dark:hover:bg-neutral-800
  font-medium text-sm
  transition-colors duration-200
">
  Ghost Action
</button>
```

### Cards

**Standard Card**
```tsx
<div className="
  rounded-lg
  bg-white dark:bg-neutral-800
  border border-neutral-200 dark:border-neutral-700
  shadow-md
  p-6
">
  Card Content
</div>
```

**Elevated Card (Hover States)**
```tsx
<div className="
  rounded-lg
  bg-white dark:bg-neutral-800
  border border-neutral-200 dark:border-neutral-700
  shadow-md hover:shadow-lg
  p-6
  transition-shadow duration-200
  cursor-pointer
">
  Interactive Card
</div>
```

### Inputs

**Text Input**
```tsx
<input className="
  w-full px-3 py-2 rounded-md
  bg-white dark:bg-neutral-900
  border border-neutral-300 dark:border-neutral-600
  text-neutral-900 dark:text-neutral-100
  placeholder:text-neutral-400 dark:placeholder:text-neutral-500
  focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent
  transition-all duration-200
" />
```

**Select Dropdown**
```tsx
<select className="
  w-full px-3 py-2 rounded-md
  bg-white dark:bg-neutral-900
  border border-neutral-300 dark:border-neutral-600
  text-neutral-900 dark:text-neutral-100
  focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent
  transition-all duration-200
  appearance-none
">
  <option>Option 1</option>
</select>
```

### Navigation

**Sidebar Nav Item (Active)**
```tsx
<a className="
  flex items-center gap-2 px-3 py-2 rounded-md
  bg-primary-50 dark:bg-primary-900/20
  text-primary-700 dark:text-primary-300
  font-medium text-sm
  border-l-2 border-primary-500
">
  Active Item
</a>
```

**Sidebar Nav Item (Inactive)**
```tsx
<a className="
  flex items-center gap-2 px-3 py-2 rounded-md
  text-neutral-700 dark:text-neutral-300
  hover:bg-neutral-100 dark:hover:bg-neutral-800
  font-medium text-sm
  transition-colors duration-200
">
  Inactive Item
</a>
```

### Badges

**Status Badges**
```tsx
/* Success */
<span className="
  inline-flex items-center px-2.5 py-0.5 rounded-full
  bg-success-50 dark:bg-success-900/20
  text-success-700 dark:text-success-300
  text-xs font-medium
">
  Completed
</span>

/* Warning */
<span className="
  inline-flex items-center px-2.5 py-0.5 rounded-full
  bg-warning-50 dark:bg-warning-900/20
  text-warning-700 dark:text-warning-300
  text-xs font-medium
">
  Pending
</span>

/* Error */
<span className="
  inline-flex items-center px-2.5 py-0.5 rounded-full
  bg-error-50 dark:bg-error-900/20
  text-error-700 dark:text-error-300
  text-xs font-medium
">
  Failed
</span>
```

### Alerts/Notifications

**Info Alert**
```tsx
<div className="
  rounded-md p-4
  bg-info-50 dark:bg-info-900/20
  border border-info-200 dark:border-info-800
">
  <p className="text-sm text-info-800 dark:text-info-200">
    Information message
  </p>
</div>
```

### Tables

**Table Header**
```tsx
<thead className="
  bg-neutral-50 dark:bg-neutral-800
  border-b border-neutral-200 dark:border-neutral-700
">
  <tr>
    <th className="
      px-6 py-3 text-left
      text-xs font-semibold uppercase tracking-wider
      text-neutral-700 dark:text-neutral-300
    ">
      Header
    </th>
  </tr>
</thead>
```

**Table Row**
```tsx
<tr className="
  border-b border-neutral-200 dark:border-neutral-700
  hover:bg-neutral-50 dark:hover:bg-neutral-800/50
  transition-colors duration-150
">
  <td className="px-6 py-4 text-sm text-neutral-900 dark:text-neutral-100">
    Cell Content
  </td>
</tr>
```

---

## Layout Patterns

### Page Header
```tsx
<header className="
  border-b border-neutral-200 dark:border-neutral-700
  bg-white dark:bg-neutral-900
">
  <div className="mx-auto flex h-16 items-center justify-between px-6">
    {/* Logo and content */}
  </div>
</header>
```

### Main Container
```tsx
<main className="
  mx-auto max-w-7xl px-6 py-8
  bg-neutral-50 dark:bg-neutral-950
  min-h-screen
">
  {/* Content */}
</main>
```

### Sidebar Layout
```tsx
<aside className="
  w-64 flex-shrink-0
  bg-white dark:bg-neutral-900
  border-r border-neutral-200 dark:border-neutral-700
  p-4
">
  {/* Navigation */}
</aside>
```

---

## Animation & Transitions

```css
/* Smooth transitions for theme switching */
* {
  transition-property: background-color, border-color, color, fill, stroke;
  transition-duration: 200ms;
  transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
}

/* Disable transitions for reduced motion */
@media (prefers-reduced-motion: reduce) {
  * {
    transition: none !important;
  }
}

/* Hover scale effect */
.hover-scale {
  transition: transform 200ms ease-in-out;
}
.hover-scale:hover {
  transform: scale(1.02);
}

/* Fade in animation */
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.fade-in {
  animation: fadeIn 300ms ease-in-out;
}
```

---

## Accessibility

### Focus States
```css
/* Custom focus ring using brand color */
.focus-ring {
  @apply focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:focus:ring-offset-neutral-900;
}
```

### Contrast Requirements
- All text must meet WCAG AA standards (4.5:1 for normal text)
- Interactive elements must have 3:1 contrast
- Focus indicators must be clearly visible in both themes

### Screen Reader Support
```tsx
/* Hidden but accessible labels */
<span className="sr-only">Accessible description</span>
```

---

## Tailwind Configuration

See `tailwind.config.js` for implementation of this design system.

---

## Implementation Checklist

- [ ] Update `tailwind.config.js` with custom color palette
- [ ] Create CSS variables in `index.css`
- [ ] Implement theme toggle component
- [ ] Add theme context provider
- [ ] Update all components to use new color scheme
- [ ] Test dark mode across all components
- [ ] Verify accessibility compliance
- [ ] Add smooth theme transition animations
- [ ] Document component usage examples
- [ ] Create Storybook documentation (optional)

---

## Usage Guidelines

### When to Use Each Color

**Primary (Brown):**
- Main CTAs and action buttons
- Active navigation states
- Brand elements and logos
- Key interactive elements

**Neutral (Gray):**
- Text content
- Borders and dividers
- Backgrounds and surfaces
- Non-primary UI elements

**Semantic Colors:**
- Success: Completed states, confirmations
- Warning: Pending states, cautions
- Error: Failed states, validation errors
- Info: Informational messages, tips

### Dark Mode Best Practices

1. Use slightly muted colors in dark mode (avoid pure white/black)
2. Reduce shadow intensity in dark mode
3. Increase border visibility with lighter borders
4. Test contrast ratios in both themes
5. Use `dark:` prefix for all dark mode variants

---

## Browser Support

- Chrome/Edge: Full support
- Firefox: Full support
- Safari: Full support (with CSS variable fallbacks)
- Mobile browsers: Full responsive support
