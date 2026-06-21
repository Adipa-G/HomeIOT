# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## Component Documentation

### ModuleVariableVisualizer

Located at `src/components/ModuleVariableVisualizer.tsx`

Renders rich visual representations of module output data. Supports six visualization types: gauge, progress bar, number display, text display, bar chart, and line chart.

**Features:**
- Pure CSS and SVG rendering (no external chart libraries)
- Responsive design with dynamic scaling
- Color theming with threshold-based colors
- Automatic formatting with decimals and units
- Full test coverage (60+ tests)

See [`docs/features-visualizations.md`](../docs/features-visualizations.md) for complete configuration guide and examples.

**Quick Example:**
```typescript
<ModuleVariableVisualizer
  type="gauge"
  value={72.5}
  config={{
    min: 0,
    max: 100,
    unit: "°C",
    decimals: 1,
    thresholds: [
      { value: 30, color: "#3b82f6" },
      { value: 40, color: "#ef4444" }
    ]
  }}
  displayName="Room Temperature"
/>
```

**Testing:**
Run visualization tests with:
```bash
npm run test -- src/test/components/ModuleVariableVisualizer.test.tsx
```

All 60 tests validate configuration properties, threshold behavior, and responsive rendering.

### MetricCard

Located at `src/components/MetricCard.tsx`

Displays a single metric with label, value, and optional sub-text. Used for dashboard statistics and key performance indicators.

**Props:**
- `label` (string) — Display label
- `value` (string | number) — Metric value to display
- `sub?` (string) — Optional subtitle or additional info

**Example:**
```typescript
<MetricCard label="Online Devices" value={42} sub="24h window" />
```

### StatusBadge

Located at `src/components/StatusBadge.tsx`

Color-coded badge for displaying status information. Supports multiple color variants for different states.

**Props:**
- `text` (string) — Badge text
- `variant?` ('green' | 'yellow' | 'red' | 'gray' | 'blue') — Color variant (default: 'gray')

**Example:**
```typescript
<StatusBadge text="Online" variant="green" />
<StatusBadge text="Warning" variant="yellow" />
<StatusBadge text="Error" variant="red" />
```

### Toast

Located at `src/components/Toast.tsx`

Notification system for success and error messages. Includes `ToastContainer` component and `toast()` function.

**Features:**
- Non-blocking notifications
- Auto-dismiss after 3 seconds
- Success and error variants

**Usage:**
```typescript
import { toast, ToastContainer } from './components/Toast';

// In your app root:
<ToastContainer />

// Display notifications:
toast('Operation successful', 'success');
toast('An error occurred', 'error');
```

### ConfirmModal

Located at `src/components/ConfirmModal.tsx`

Modal dialog for confirming destructive or important actions. Renders a trigger button and confirmation dialog.

**Props:**
- `title` (string) — Modal title
- `description?` (string) — Optional description text
- `confirmLabel?` (string) — Button label (default: 'Delete')
- `onConfirm` () => void | Promise<void> — Handler called on confirmation
- `children` (function) — Render function receiving `open()` callback

**Example:**
```typescript
<ConfirmModal
  title="Delete Device?"
  description="This action cannot be undone"
  confirmLabel="Delete"
  onConfirm={async () => await api.delete(`/device/${id}`)}
>
  {(open) => (
    <button onClick={open} className="text-red-600">
      Delete Device
    </button>
  )}
</ConfirmModal>
```

### ControlInput

Located at `src/components/ControlInput.tsx`

Flexible input component for device module control variables. Supports text input and type-specific control types (e.g., selects, toggles).

**Props:**
- `label?` (string) — Input label
- `controlType?` (string | null) — Type of control UI to render
- `controlOptions?` (unknown | null) — Options for the control type
- `value` (string | null) — Current value
- `onChange` (value: string | null) => void — Change handler
- `disabled?` (boolean) — Disable input (default: false)

**Example:**
```typescript
<ControlInput
  label="Power Mode"
  value={powerMode}
  onChange={setPowerMode}
/>
```

### Pagination

Located at `src/components/Pagination.tsx`

Navigation component for paginated list views. Shows current position and previous/next buttons.

**Props:**
- `offset` (number) — Current offset
- `limit` (number) — Items per page
- `total` (number) — Total item count
- `onChange` (offset: number) => void — Called when page changes

**Example:**
```typescript
<Pagination
  offset={currentOffset}
  limit={20}
  total={totalItems}
  onChange={setOffset}
/>
```

### ProtectedRoute

Located at `src/components/ProtectedRoute.tsx`

Route wrapper that ensures user is authenticated. Redirects unauthenticated users to login page.

**Usage:**
```typescript
import { ProtectedRoute } from './components/ProtectedRoute';

<Routes>
  <Route element={<ProtectedRoute />}>
    <Route path="/dashboard" element={<DashboardPage />} />
    <Route path="/devices" element={<DevicesPage />} />
  </Route>
  <Route path="/login" element={<LoginPage />} />
</Routes>
```

### AssignmentVariablesPanel

Located at `src/components/AssignmentVariablesPanel.tsx`

Panel for viewing and editing module variable overrides on device assignments. Manages save/delete operations with API integration.

**Props:**
- `assignmentId` (string) — Module assignment ID

**Features:**
- Displays list of variables with current values
- Edit variable overrides
- Delete overrides to revert to defaults
- Real-time API sync with react-query

### DeviceModuleSettingsPanel

Located at `src/components/DeviceModuleSettingsPanel.tsx`

Settings panel for configuring module variables on a specific device assignment. Integrated with `ControlInput` for type-specific control rendering.

**Props:**
- `moduleId` (string) — Module ID
- `assignmentId` (string) — Assignment ID
- `variableDefs` (ModuleVariableDefItem[]) — Variable definitions
- `variableValues` (ModuleVariableValueItem[]) — Current values
- `onClose` () => void — Close handler

**Features:**
- Variable configuration UI based on control types
- API sync with real-time updates
- Dedicated settings modal for devices

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```
