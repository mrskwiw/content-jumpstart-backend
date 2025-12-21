# Tailwind CSS v4 Compatibility Notes

## Important Changes

This project uses **Tailwind CSS v4**, which has significant differences from v3. The design system has been adapted to work with v4's new architecture.

## What Changed from the Original Design

### 1. No Custom Utility Classes
The original design system document (`UI_DESIGN_SYSTEM.md`) included utility classes like:
- `.btn-primary`
- `.card`
- `.input`
- `.nav-item-active`
- etc.

**These are NOT implemented** because Tailwind v4 doesn't support `@apply` with custom color palettes in the same way as v3.

### 2. Use Inline Tailwind Classes Instead
Instead of utility classes, use Tailwind classes directly in your components:

#### Button Example
```tsx
// Instead of: <button className="btn-primary">
<button className="px-4 py-2 rounded-md bg-primary-500 text-primary-50 hover:bg-primary-600 font-medium text-sm shadow-sm transition-all duration-200">
  Primary Button
</button>
```

#### Card Example
```tsx
// Instead of: <div className="card">
<div className="rounded-lg bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 shadow-md p-6">
  Card Content
</div>
```

#### Input Example
```tsx
// Instead of: <input className="input" />
<input className="w-full px-3 py-2 rounded-md bg-white dark:bg-neutral-900 border border-neutral-300 dark:border-neutral-600 text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-primary-500" />
```

### 3. What IS Included in index.css

The simplified `index.css` includes:
- **CSS Custom Properties** for theme colors (light and dark)
- **Base styles** for body, html (using plain CSS, not @apply)
- **Smooth theme transitions**
- **Custom scrollbar** styles (.scrollbar-thin)
- **Screen reader utility** (.sr-only)
- **Print styles**

### 4. Color Palette (Still Available via Tailwind)

The custom brown color palette is defined in `tailwind.config.js` and works with Tailwind's utility classes:

```tsx
// Use these directly:
<div className="bg-primary-500 text-primary-50">
  Brown brand color
</div>

<div className="bg-neutral-900 dark:bg-neutral-100">
  Neutral gray
</div>
```

## Migration from Design System Docs

When referencing the design system documentation (`UI_DESIGN_SYSTEM.md`), note:

1. **Color palettes** → Use directly as Tailwind classes
2. **Component patterns** → Reference for visual design, implement with inline classes
3. **Utility classes** → NOT implemented, use inline Tailwind instead

## Why This Approach?

Tailwind v4 introduced architectural changes that make `@apply` less flexible:
- Custom color references in `@apply` cause build errors
- The `theme()` function syntax changed
- Component layer utilities with custom colors don't work the same way

The recommended Tailwind v4 approach is to use utility classes directly in components rather than creating abstraction layers.

## Benefits

1. **Build compatibility** - Works with Tailwind v4 out of the box
2. **Flexibility** - Easy to customize styles per-component
3. **Performance** - No additional CSS layer overhead
4. **Clarity** - Styles are colocated with components

## Drawbacks

1. **Verbosity** - Longer className strings
2. **Repetition** - Common patterns repeated across components
3. **No abstraction** - Can't centralize component styles in CSS

## Recommended Pattern

Create reusable React components for common patterns:

```tsx
// components/ui/Button.tsx
export function Button({ variant = 'primary', children, ...props }) {
  const styles = {
    primary: 'px-4 py-2 rounded-md bg-primary-500 text-primary-50 hover:bg-primary-600 font-medium text-sm shadow-sm transition-all duration-200',
    secondary: 'px-4 py-2 rounded-md border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-200 hover:bg-neutral-50 dark:hover:bg-neutral-700 font-medium text-sm shadow-sm transition-all duration-200',
  };

  return <button className={styles[variant]} {...props}>{children}</button>;
}
```

This gives you the abstraction benefits without fighting Tailwind v4's architecture.

## References

- Tailwind CSS v4 migration guide: https://tailwindcss.com/docs/upgrade-guide
- Tailwind v4 architecture changes: https://tailwindcss.com/blog/tailwindcss-v4
