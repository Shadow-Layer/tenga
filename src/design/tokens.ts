/**
 * Design System Tokens
 * 
 * Establish a consistent vocabulary for colors, spacing, typography, and states.
 * These map to Tailwind CSS utilities. All UI should use these tokens for consistency.
 */

export const tokens = {
  // Color Palette
  colors: {
    // Primary (Action, CTA, Success states)
    primary: {
      50: '#ecf0ff',
      100: '#d9e0ff',
      200: '#b3c1ff',
      300: '#8ca2ff',
      400: '#6583ff',
      500: '#3e64ff', // Primary brand
      600: '#2e50e6',
      700: '#1e3ccc',
      800: '#1428b3',
      900: '#0f1a99',
    },

    // Neutral (Text, backgrounds, borders)
    neutral: {
      0: '#ffffff',
      50: '#f9fafb',
      100: '#f3f4f6',
      200: '#e5e7eb',
      300: '#d1d5db',
      400: '#9ca3af',
      500: '#6b7280',
      600: '#4b5563',
      700: '#374151',
      800: '#1f2937',
      900: '#111827',
    },

    // Success (Stock available, approved, positive)
    success: {
      50: '#ecfdf5',
      100: '#d1fae5',
      200: '#a7f3d0',
      500: '#10b981', // Main
      600: '#059669',
      700: '#047857',
    },

    // Warning (Low stock, caution)
    warning: {
      50: '#fffbeb',
      100: '#fef3c7',
      200: '#fde68a',
      500: '#f59e0b', // Main
      600: '#d97706',
      700: '#b45309',
    },

    // Error (Stock out, transaction failed, critical)
    error: {
      50: '#fef2f2',
      100: '#fee2e2',
      200: '#fecaca',
      500: '#ef4444', // Main
      600: '#dc2626',
      700: '#b91c1c',
    },

    // Info (Informational messages, offline status)
    info: {
      50: '#eff6ff',
      100: '#dbeafe',
      200: '#bfdbfe',
      500: '#3b82f6', // Main
      600: '#2563eb',
      700: '#1d4ed8',
    },
  },

  // Spacing Scale (rem-based, compatible with Tailwind)
  spacing: {
    0: '0',
    1: '0.25rem',
    2: '0.5rem',
    3: '0.75rem',
    4: '1rem',
    5: '1.25rem',
    6: '1.5rem',
    8: '2rem',
    10: '2.5rem',
    12: '3rem',
    16: '4rem',
  },

  // Component-specific sizing
  size: {
    button: {
      small: { px: 'px-3', py: 'py-1.5', fontSize: 'text-sm' },
      medium: { px: 'px-4', py: 'py-2', fontSize: 'text-base' },
      large: { px: 'px-6', py: 'py-3', fontSize: 'text-base' },
    },
    card: {
      padding: '1.5rem',
      radius: '0.75rem',
    },
    input: {
      height: '2.5rem',
      padding: '0.75rem',
      borderRadius: '0.5rem',
      fontSize: 'text-base',
    },
    icon: {
      small: '1rem',
      medium: '1.25rem',
      large: '1.5rem',
      xl: '2rem',
    },
  },

  // Semantic state colors
  state: {
    success: '#10b981',
    warning: '#f59e0b',
    error: '#ef4444',
    info: '#3b82f6',
    disabled: '#d1d5db',
  },
}

export const semanticColors = {
  text: {
    primary: '#111827',
    secondary: '#4b5563',
    tertiary: '#6b7280',
    disabled: '#9ca3af',
  },
  background: {
    primary: '#ffffff',
    secondary: '#f9fafb',
    tertiary: '#f3f4f6',
  },
  border: {
    light: '#e5e7eb',
    medium: '#d1d5db',
    focus: '#3e64ff',
  },
  status: {
    success: '#10b981',
    warning: '#f59e0b',
    error: '#ef4444',
    info: '#3b82f6',
  },
}

export default tokens
