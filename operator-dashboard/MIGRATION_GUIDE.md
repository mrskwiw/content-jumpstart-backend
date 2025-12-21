# UI Design System Migration Guide

## Overview

This guide walks through migrating existing components from the old blue/slate color scheme to the new brown-based design system with dark mode support.

---

## Step 1: Wrap App with ThemeProvider

Update `src/main.tsx` to include the ThemeProvider:

```tsx
import { ThemeProvider } from '@/contexts/ThemeContext';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ThemeProvider>
      <App />
    </ThemeProvider>
  </React.StrictMode>,
);
```

---

## Step 2: Add Theme Toggle to Layout

Add the ThemeToggle component to your header or settings area:

```tsx
import ThemeToggle from '@/components/ui/ThemeToggle';

// In your header component:
<div className="flex items-center gap-3">
  <ThemeToggle />
  {/* Other header items */}
</div>
```

---

## Step 3: Update Color Classes

### Before (Old Blue Scheme):
```tsx
className="bg-blue-600 text-white"
className="bg-slate-50"
className="text-slate-900"
className="border-slate-200"
className="hover:bg-blue-50"
```

### After (New Brown Scheme):
```tsx
className="bg-primary-500 text-primary-50"
className="bg-neutral-50 dark:bg-neutral-950"
className="text-neutral-900 dark:text-neutral-100"
className="border-neutral-200 dark:border-neutral-700"
className="hover:bg-primary-50 dark:hover:bg-primary-900/20"
```

---

## Step 4: Use Utility Classes

Replace inline styles with the new utility classes:

### Buttons:
```tsx
// Old:
<button className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
  Click me
</button>

// New:
<button className="btn-primary">
  Click me
</button>
```

### Cards:
```tsx
// Old:
<div className="bg-white rounded-lg shadow p-6">
  Content
</div>

// New:
<div className="card">
  Content
</div>
```

### Navigation Items:
```tsx
// Old:
<NavLink
  className={({ isActive }) =>
    isActive
      ? 'bg-blue-50 text-blue-700'
      : 'text-slate-700 hover:bg-slate-50'
  }
>
  Item
</NavLink>

// New:
<NavLink
  className={({ isActive }) =>
    isActive ? 'nav-item-active' : 'nav-item'
  }
>
  Item
</NavLink>
```

---

## Step 5: Update Specific Components

### AppLayout.tsx

```tsx
import { LogOut, PanelsTopLeft, FileStack, ClipboardList, Settings, Rocket } from 'lucide-react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import ThemeToggle from '@/components/ui/ThemeToggle';

const navItems = [
  { to: '/dashboard', label: 'Overview', icon: PanelsTopLeft, end: true },
  { to: '/dashboard/projects', label: 'Projects', icon: ClipboardList },
  { to: '/dashboard/deliverables', label: 'Deliverables', icon: FileStack },
  { to: '/dashboard/wizard', label: 'Wizard / QA', icon: Rocket },
  { to: '/dashboard/settings', label: 'Settings', icon: Settings },
];

export default function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-neutral-950">
      {/* Updated header with dark mode support */}
      <header className="page-header">
        <div className="mx-auto flex h-16 items-center justify-between px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-2">
            {/* Updated logo with brown brand color */}
            <div className="h-10 w-10 rounded-lg bg-primary-500 text-primary-50 flex items-center justify-center font-bold text-lg shadow-md">
              O
            </div>
            <div>
              <p className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                Operator Dashboard
              </p>
              <p className="text-xs text-neutral-500 dark:text-neutral-400">
                Content Jumpstart
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Theme toggle */}
            <ThemeToggle />

            <div className="text-right">
              <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                {user?.name || user?.email}
              </p>
              <p className="text-xs text-neutral-500 dark:text-neutral-400 capitalize">
                {user?.role}
              </p>
            </div>

            <button onClick={handleLogout} className="btn-secondary">
              <LogOut className="h-4 w-4" />
              Logout
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto flex max-w-7xl gap-6 px-4 py-6 sm:px-6 lg:px-8">
        {/* Updated sidebar with dark mode */}
        <aside className="sidebar hidden md:block">
          <nav className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) =>
                    isActive ? 'nav-item-active' : 'nav-item'
                  }
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </NavLink>
              );
            })}
          </nav>
        </aside>

        <main className="flex-1">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
```

---

## Step 6: Update Status Badges

### Before:
```tsx
<span className="px-2 py-1 text-xs bg-green-100 text-green-800 rounded">
  Active
</span>
```

### After:
```tsx
<span className="badge-success">Active</span>
<span className="badge-warning">Pending</span>
<span className="badge-error">Failed</span>
<span className="badge-info">Info</span>
```

---

## Step 7: Update Form Inputs

### Before:
```tsx
<input
  type="text"
  className="w-full px-3 py-2 border border-gray-300 rounded-md"
/>
```

### After:
```tsx
<input type="text" className="input" />
```

---

## Step 8: Update Tables

### Before:
```tsx
<thead className="bg-gray-50">
  <tr>
    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
      Header
    </th>
  </tr>
</thead>
<tbody>
  <tr className="hover:bg-gray-50">
    <td className="px-6 py-4 text-sm text-gray-900">
      Cell
    </td>
  </tr>
</tbody>
```

### After:
```tsx
<thead className="table-header">
  <tr>
    <th className="table-header-cell">Header</th>
  </tr>
</thead>
<tbody>
  <tr className="table-row">
    <td className="table-cell">Cell</td>
  </tr>
</tbody>
```

---

## Step 9: Update Alerts/Notifications

### Before:
```tsx
<div className="p-4 bg-blue-50 border border-blue-200 rounded-md">
  <p className="text-sm text-blue-800">Information</p>
</div>
```

### After:
```tsx
<div className="alert-info">
  <p className="text-sm">Information</p>
</div>
```

---

## Step 10: Testing Checklist

- [ ] Test all pages in light mode
- [ ] Test all pages in dark mode
- [ ] Test system theme preference
- [ ] Verify theme persists on page reload
- [ ] Check contrast ratios (WCAG AA compliance)
- [ ] Test focus states on all interactive elements
- [ ] Verify hover states in both themes
- [ ] Check mobile responsiveness
- [ ] Test with reduced motion preference
- [ ] Verify print styles (if applicable)

---

## Common Patterns

### Component with Dark Mode Support:
```tsx
export default function MyComponent() {
  return (
    <div className="bg-white dark:bg-neutral-800 p-6 rounded-lg">
      <h2 className="text-neutral-900 dark:text-neutral-100 font-bold">
        Title
      </h2>
      <p className="text-neutral-600 dark:text-neutral-300">
        Description
      </p>
    </div>
  );
}
```

### Conditional Rendering Based on Theme:
```tsx
import { useTheme } from '@/contexts/ThemeContext';

export default function MyComponent() {
  const { actualTheme } = useTheme();

  return (
    <div>
      {actualTheme === 'dark' ? (
        <DarkModeIcon />
      ) : (
        <LightModeIcon />
      )}
    </div>
  );
}
```

---

## Color Reference Quick Guide

| Old Color | New Color | Usage |
|-----------|-----------|-------|
| `blue-600` | `primary-500` | Primary actions, brand elements |
| `blue-50` | `primary-50` (light) / `primary-900/20` (dark) | Active states, highlights |
| `slate-50` | `neutral-50` (light) / `neutral-950` (dark) | Background |
| `slate-100` | `neutral-100` (light) / `neutral-900` (dark) | Surface |
| `slate-900` | `neutral-900` (light) / `neutral-100` (dark) | Primary text |
| `slate-600` | `neutral-600` (light) / `neutral-400` (dark) | Secondary text |
| `slate-200` | `neutral-200` (light) / `neutral-700` (dark) | Borders |

---

## Accessibility Notes

1. **Contrast Ratios**: All color combinations meet WCAG AA standards
2. **Focus Indicators**: Use `.focus-ring` utility for consistent focus states
3. **Color Independence**: Never rely on color alone to convey information
4. **Dark Mode**: Test dark mode with actual dark backgrounds, not just inverted colors
5. **Reduced Motion**: Animations respect `prefers-reduced-motion` preference

---

## Performance Tips

1. Theme transitions use `transition-colors` for smooth switching
2. CSS variables reduce bundle size compared to inline styles
3. `@layer` directives optimize Tailwind output
4. Theme preference cached in localStorage to prevent flash
5. System theme listener only active when needed

---

## Need Help?

See `UI_DESIGN_SYSTEM.md` for complete design system documentation and component examples.
