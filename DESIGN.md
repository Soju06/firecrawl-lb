# Firecrawl LB Design System

## 1. Atmosphere & Identity

Firecrawl LB is a quiet operations console for API capacity, credits, and proxy health. It should feel precise, dense, and calm: operators can scan status quickly without decorative noise. The signature is restrained telemetry with small status chips, compact tables, and warm fire-accented highlights only where they identify Firecrawl-specific state.

## 2. Color

### Palette

| Role | Token | Light | Dark | Usage |
|------|-------|-------|------|-------|
| Surface/primary | `--background` | `oklch(0.985 0.002 260)` | `oklch(0 0 0)` | Page background |
| Surface/card | `--card` | `oklch(1 0 0)` | `oklch(0.145 0 0)` | Cards, dialogs, panels |
| Surface/muted | `--muted` | `oklch(0.955 0.006 264)` | `oklch(0.22 0 0)` | Subtle bands, table hover |
| Text/primary | `--foreground` | `oklch(0.13 0.028 260)` | `oklch(0.95 0 0)` | Body and headings |
| Text/secondary | `--muted-foreground` | `oklch(0.50 0.015 264)` | `oklch(0.65 0 0)` | Labels, metadata |
| Border/default | `--border` | `oklch(0.920 0.005 264)` | `oklch(0.26 0 0)` | Dividers and card outlines |
| Accent/primary | `--primary` | `oklch(0.488 0.185 264)` | `oklch(0.68 0.10 245)` | Primary actions and focus |
| Status/success | Tailwind `emerald` | semantic utility | semantic utility | Active, success |
| Status/warning | Tailwind `amber` | semantic utility | semantic utility | Rate limits, cooldowns |
| Status/error | `--destructive` | `oklch(0.577 0.245 27.325)` | `oklch(0.704 0.191 22.216)` | Errors, exhausted credits |
| Fire/accent | Tailwind `orange` | semantic utility | semantic utility | Firecrawl brand icon and endpoint accent |

### Rules

- Use existing CSS variables and Tailwind semantic utilities; do not add ad-hoc hex colors in components.
- Status color is functional only: active green, rate-limited orange/amber, exhausted red, paused gray.
- The interface must not become a one-hue dashboard; charts and endpoint chips use the existing chart/status palette.

## 3. Typography

### Scale

| Level | Size | Weight | Line Height | Tracking | Usage |
|-------|------|--------|-------------|----------|-------|
| H1 | `text-2xl` | 600 | default | 0 | Page titles |
| H2 | `text-lg` | 600 | default | 0 | Section headers |
| H3 | `text-sm` | 600 | default | 0 | Card titles |
| Body | `text-sm` | 400 | default | 0 | Tables and controls |
| Caption | `text-xs` | 500 | default | 0 | Labels, metadata, badges |

### Font Stack

- Primary: `Geist Sans`, `ui-sans-serif`, `system-ui`, `-apple-system`, `sans-serif`
- Mono: `JetBrains Mono`, `ui-monospace`, `monospace`

### Rules

- Operational pages prioritize scan density; reserve `text-2xl` for page titles only.
- Letter spacing stays at zero except for existing tokenized labels.

## 4. Spacing & Layout

### Base Unit

All spacing derives from 4px Tailwind increments.

| Token | Value | Usage |
|-------|-------|-------|
| `space-1` | 4px | Tight icon and label gaps |
| `space-2` | 8px | Compact cell and badge rhythm |
| `space-3` | 12px | Form field groups |
| `space-4` | 16px | Card padding, row groups |
| `space-6` | 24px | Page section gaps |
| `space-8` | 32px | Major groups |

### Grid

- Max content width: 1500px, matching the existing app shell.
- Breakpoints: Tailwind defaults, with tables horizontally scrollable on mobile.

### Rules

- Forms and tables use compact vertical rhythm.
- Fixed-format controls and meters keep stable dimensions to avoid reflow during polling.

## 5. Components

### Status Badge

- **Structure**: shadcn `Badge` with semantic Tailwind color utilities.
- **Variants**: account status, credential status, job status, request status.
- **Spacing**: `gap-1`, `px-2`, `py-0.5`.
- **States**: passive display only; interactive status updates use selects or buttons.
- **Accessibility**: visible text always names the status.
- **Motion**: no motion.

### Metric Card

- **Structure**: shadcn `Card` with caption, value, optional icon, and optional progress.
- **Variants**: overview stat, endpoint breakdown, per-account credit.
- **Spacing**: `p-4`, inner `gap-2`.
- **States**: loading skeleton, error fallback, empty value.
- **Accessibility**: icon is decorative unless it is the only affordance.
- **Motion**: page-level fade only.

### Data Table

- **Structure**: shadcn `Table` inside an overflow container.
- **Variants**: accounts, jobs, logs.
- **Spacing**: compact `p-2` cells.
- **States**: loading, empty, error, filtered.
- **Accessibility**: real table elements, labeled filters, button text for row actions.
- **Motion**: no row motion.

## 6. Motion & Interaction

| Type | Duration | Easing | Usage |
|------|----------|--------|-------|
| Micro | 100-150ms | ease-out | Button press |
| Standard | 200-300ms | ease-in-out | Dialog and sheet transitions |
| Page | 350ms | ease-out | Existing `animate-fade-in-up` |

### Rules

- Animate only `transform` and `opacity`.
- Respect `prefers-reduced-motion` through existing CSS.
- Every button, link, select, and input uses visible focus styles from shadcn/ui.

## 7. Depth & Surface

### Strategy

Mixed, matching the current app: light borders for structure, small tokenized shadows only on persistent chrome and hover lift.

| Level | Token | Usage |
|-------|-------|-------|
| Subtle | `--shadow-xs` | Inputs and nav active state |
| Default | `--shadow-md` | Card hover and elevated overlays |
| Border | `--border` | Cards, tables, dialogs |

Depth is functional, not decorative. Do not nest cards inside cards.
