# UI Component Library

Centralized, reusable UI components for the Operator Dashboard. All components support dark mode and follow the brown/neutral color scheme.

## Quick Start

```tsx
import { Button, Card, Badge } from '@/components/ui';

function MyComponent() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Hello World</CardTitle>
      </CardHeader>
      <CardContent>
        <Button variant="primary">Click me</Button>
        <Badge variant="success">Active</Badge>
      </CardContent>
    </Card>
  );
}
```

## Core Benefits

✅ **Single source of truth** - Update styles in one place
✅ **Type-safe** - Full TypeScript support
✅ **Dark mode built-in** - All components handle theme automatically
✅ **Consistent** - Same look and feel across the app
✅ **Accessible** - ARIA attributes and keyboard support

---

## Components

### Button

Primary action component with multiple variants and sizes.

**Variants:** `primary` | `secondary` | `outline` | `ghost` | `danger` | `success` | `warning` | `link`
**Sizes:** `xs` | `sm` | `md` | `lg` | `xl` | `icon`

```tsx
import { Button } from '@/components/ui';

// Basic usage
<Button variant="primary" size="md">Save</Button>

// With loading state
<Button loading>Saving...</Button>

// Icon button
<Button variant="ghost" size="icon">
  <TrashIcon className="h-4 w-4" />
</Button>

// Disabled
<Button disabled>Can't click</Button>
```

**Props:**
- `variant` - Visual style
- `size` - Button size
- `loading` - Show loading spinner
- `disabled` - Disable interaction
- All standard button HTML attributes

---

### Card

Container component for grouping related content.

**Variants:** `default` | `elevated` | `outlined` | `ghost`
**Padding:** `none` | `sm` | `md` | `lg`
**Hoverable:** `true` | `false`

```tsx
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui';

<Card variant="default" padding="md" hoverable>
  <CardHeader>
    <CardTitle>Project Details</CardTitle>
    <CardDescription>View and edit project information</CardDescription>
  </CardHeader>
  <CardContent>
    {/* Your content here */}
  </CardContent>
  <CardFooter>
    <Button>Save Changes</Button>
  </CardFooter>
</Card>
```

**Sub-components:**
- `CardHeader` - Optional header section
- `CardTitle` - Card title (h3)
- `CardDescription` - Subtitle/description
- `CardContent` - Main content area
- `CardFooter` - Optional footer with actions

---

### Badge

Small status indicator with semantic colors.

**Variants:** `default` | `primary` | `secondary` | `success` | `warning` | `danger` | `info` | `purple` | `orange`
**Status Variants:** `draft` | `ready` | `generating` | `qa` | `exported` | `delivered` | `error`
**Sizes:** `sm` | `md` | `lg`

```tsx
import { Badge } from '@/components/ui';

// Basic badge
<Badge variant="success">Active</Badge>

// Project status
<Badge variant="generating">Generating</Badge>

// With remove button
<Badge variant="primary" onRemove={() => console.log('removed')}>
  Tag
</Badge>

// Different sizes
<Badge size="sm">Small</Badge>
<Badge size="lg">Large</Badge>
```

**Props:**
- `variant` - Badge color/style
- `size` - Badge size
- `onRemove` - Optional remove callback (adds X button)

---

### Input

Text input field with label and error support.

**Variants:** `default` | `error`

```tsx
import { Input } from '@/components/ui';

// Basic input
<Input placeholder="Enter your name" />

// With label
<Input label="Email Address" type="email" />

// With error
<Input
  label="Password"
  type="password"
  error="Password must be at least 8 characters"
/>

// With helper text
<Input
  label="Username"
  helperText="This will be visible to others"
/>
```

**Props:**
- `label` - Optional label text
- `error` - Error message (shows in red)
- `helperText` - Helper text (shows below input)
- `variant` - Input style (auto-set to 'error' if error prop exists)
- All standard input HTML attributes

---

### Select

Dropdown select component with label and error support.

**Variants:** `default` | `error`

```tsx
import { Select } from '@/components/ui';

<Select label="Choose a platform">
  <option value="">Select...</option>
  <option value="linkedin">LinkedIn</option>
  <option value="twitter">Twitter</option>
  <option value="facebook">Facebook</option>
</Select>

// With error
<Select
  label="Status"
  error="Please select a status"
>
  <option value="draft">Draft</option>
  <option value="published">Published</option>
</Select>
```

**Props:**
- `label` - Optional label text
- `error` - Error message (shows in red)
- `helperText` - Helper text (shows below select)
- All standard select HTML attributes

---

### Textarea

Multi-line text input with character counter.

**Variants:** `default` | `error`

```tsx
import { Textarea } from '@/components/ui';

// Basic textarea
<Textarea placeholder="Enter description..." />

// With label and character count
<Textarea
  label="Project Description"
  maxLength={500}
  showCount
  rows={4}
/>

// With error
<Textarea
  label="Notes"
  error="This field is required"
/>
```

**Props:**
- `label` - Optional label text
- `error` - Error message (shows in red)
- `helperText` - Helper text (shows below textarea)
- `showCount` - Show character counter (requires maxLength)
- `maxLength` - Maximum character limit
- All standard textarea HTML attributes

---

### Table

Consistent table styling with header, body, and row components.

```tsx
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from '@/components/ui';

<Table>
  <TableHeader>
    <TableRow>
      <TableHead>Name</TableHead>
      <TableHead>Status</TableHead>
      <TableHead className="text-right">Actions</TableHead>
    </TableRow>
  </TableHeader>
  <TableBody>
    <TableRow>
      <TableCell className="font-medium">Project A</TableCell>
      <TableCell>
        <Badge variant="success">Active</Badge>
      </TableCell>
      <TableCell className="text-right">
        <Button variant="ghost" size="sm">Edit</Button>
      </TableCell>
    </TableRow>
  </TableBody>
</Table>
```

**Sub-components:**
- `Table` - Main wrapper (includes overflow container)
- `TableHeader` - Table header section (thead)
- `TableBody` - Table body section (tbody)
- `TableFooter` - Table footer section (tfoot)
- `TableRow` - Table row (tr) with hover effect
- `TableHead` - Header cell (th)
- `TableCell` - Body cell (td)
- `TableCaption` - Optional table caption

---

### Tabs

Tab navigation component with content panels.

```tsx
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui';
import { FileText, Users } from 'lucide-react';

<Tabs defaultValue="overview">
  <TabsList>
    <TabsTrigger value="overview" icon={<FileText className="h-4 w-4" />}>
      Overview
    </TabsTrigger>
    <TabsTrigger value="team" icon={<Users className="h-4 w-4" />} count={5}>
      Team
    </TabsTrigger>
  </TabsList>

  <TabsContent value="overview">
    <p>Overview content here</p>
  </TabsContent>

  <TabsContent value="team">
    <p>Team content here</p>
  </TabsContent>
</Tabs>
```

**Props:**
- `defaultValue` - Initial active tab (required)
- `value` - Controlled active tab (optional)
- `onValueChange` - Callback when tab changes
- `icon` - Optional icon (on TabsTrigger)
- `count` - Optional count badge (on TabsTrigger)

---

### Alert

Alert/notification component with variants and icons.

**Variants:** `default` | `info` | `success` | `warning` | `danger`

```tsx
import { Alert, AlertTitle, AlertDescription } from '@/components/ui';

// Basic alert
<Alert variant="success">
  <AlertTitle>Success!</AlertTitle>
  <AlertDescription>
    Your changes have been saved successfully.
  </AlertDescription>
</Alert>

// With close button
<Alert variant="warning" onClose={() => console.log('closed')}>
  <AlertTitle>Warning</AlertTitle>
  <AlertDescription>This action cannot be undone.</AlertDescription>
</Alert>

// Without icon
<Alert variant="info" showIcon={false}>
  <AlertDescription>Info message without icon</AlertDescription>
</Alert>

// Custom icon
<Alert variant="danger" icon={<CustomIcon />}>
  <AlertDescription>Custom icon alert</AlertDescription>
</Alert>
```

**Props:**
- `variant` - Alert style and color
- `onClose` - Optional close callback (adds X button)
- `icon` - Custom icon (overrides default)
- `showIcon` - Show/hide icon (default: true)

**Sub-components:**
- `AlertTitle` - Optional alert title
- `AlertDescription` - Alert message content

---

## Migration Guide

### Before (inline Tailwind)

```tsx
<button className="inline-flex items-center gap-2 rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 dark:hover:bg-primary-600">
  Save
</button>
```

### After (Component)

```tsx
<Button variant="primary">Save</Button>
```

### Benefits of Migration

1. **Consistency** - All buttons look identical across the app
2. **Maintainability** - Change button style once, updates everywhere
3. **Type Safety** - TypeScript ensures correct props
4. **Accessibility** - Focus states and ARIA attributes built-in
5. **Dark Mode** - Automatically handles theme switching

---

## Customization

### Extending Components

You can extend components with additional classes:

```tsx
<Button className="mt-4 w-full">
  Full Width Button
</Button>

<Card className="max-w-md mx-auto">
  Centered Card
</Card>
```

### Custom Variants

To add new variants, edit the component file:

```tsx
// In Button.tsx
const buttonVariants = cva(
  // ... base styles
  {
    variants: {
      variant: {
        // ... existing variants
        custom: 'bg-purple-600 text-white hover:bg-purple-700',
      },
    },
  }
);
```

---

## Dark Mode

All components automatically support dark mode via the `dark:` prefix in Tailwind classes. The theme is controlled by the `ThemeContext` and `ThemeToggle` component.

**Theme is stored in localStorage** and persists across sessions.

---

## Accessibility

All components follow accessibility best practices:

- ✅ Proper ARIA attributes
- ✅ Keyboard navigation support
- ✅ Focus indicators
- ✅ Screen reader friendly
- ✅ Color contrast compliance (WCAG AA)

---

## Performance

Components are optimized for performance:

- React.forwardRef for ref forwarding
- Minimal re-renders
- Tree-shakeable exports
- Small bundle size (~5KB gzipped)

---

## Contributing

When adding new components:

1. Create component file in `src/components/ui/`
2. Use CVA for variants
3. Add TypeScript types
4. Include dark mode support
5. Export from `index.ts`
6. Document usage in this file
7. Test in both light and dark modes

---

## Support

For questions or issues with components:

1. Check this documentation
2. Review component source code
3. Check existing page implementations
4. Consult with the team

---

**Last Updated:** December 2025
**Version:** 1.0.0
