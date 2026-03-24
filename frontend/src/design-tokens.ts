/**
 * Design tokens — type-safe design system.
 * Single source of truth for all visual decisions.
 * Use `satisfies` + `as const` for full inference.
 */
import type { SxProps, Theme } from '@mui/material'

// ── Palette ───────────────────────────────────────────────────────────────────

export const PALETTE = {
  teal: {
    50:  '#F0FDFA',
    100: '#CCFBF1',
    300: '#5EEAD4',
    400: '#2DD4BF',
    500: '#14B8A6',
    600: '#0D9488',
    700: '#0F766E',
    800: '#115E59',
    900: '#134E4A',
  },
  stone: {
    50:  '#FAFAF9',
    100: '#F5F5F4',
    200: '#E7E5E4',
    300: '#D6D3D1',
    400: '#A8A29E',
    500: '#78716C',
    600: '#57534E',
    700: '#44403C',
    800: '#292524',
    900: '#1C1917',
  },
  slate: {
    50:  '#F8FAFC',
    100: '#F1F5F9',
    200: '#E2E8F0',
    400: '#94A3B8',
    500: '#64748B',
    700: '#334155',
    800: '#1E293B',
    900: '#0F172A',
  },
  green:  { main: '#16A34A', light: '#4ADE80', bg: '#F0FDF4', border: '#BBF7D0' },
  red:    { main: '#EF4444', light: '#F87171', bg: '#FEF2F2', border: '#FECACA' },
  amber:  { main: '#F59E0B', light: '#FCD34D', bg: '#FFFBEB', border: '#FDE68A' },
  blue:   { main: '#3B82F6', light: '#93C5FD', bg: '#EFF6FF', border: '#BFDBFE' },
} as const satisfies Record<string, Record<string | number, string>>

// ── Brand ─────────────────────────────────────────────────────────────────────

export const BRAND = {
  primary:     PALETTE.teal[600],
  primaryHover: PALETTE.teal[500],
  primaryDark: PALETTE.teal[700],
  primaryLight: PALETTE.teal[400],
  gradient:    `linear-gradient(135deg, ${PALETTE.teal[400]} 0%, ${PALETTE.teal[600]} 100%)`,
  gradientDeep:`linear-gradient(135deg, ${PALETTE.teal[300]} 0%, ${PALETTE.teal[600]} 55%, ${PALETTE.teal[800]} 100%)`,
} as const

// ── Surfaces ──────────────────────────────────────────────────────────────────

export const SURFACE = {
  page:    PALETTE.stone[100],  // warm off-white page background
  card:    '#FFFFFF',           // cards "float" above page
  muted:   PALETTE.stone[50],   // table rows, secondary areas
  sidebar: '#111827',           // dark nav panel (gray-900)
  overlay: 'rgba(0,0,0,0.45)',  // modal backdrop
} as const

// ── Typography ────────────────────────────────────────────────────────────────

export const FONT = {
  sans: '"Plus Jakarta Sans", system-ui, -apple-system, sans-serif',
  mono: '"JetBrains Mono", "Fira Code", ui-monospace, monospace',
} as const

// ── Motion ────────────────────────────────────────────────────────────────────

export const MOTION = {
  fast:   '120ms ease',
  base:   '200ms ease',
  smooth: '260ms cubic-bezier(0.4, 0, 0.2, 1)',
  spring: '380ms cubic-bezier(0.16, 1, 0.3, 1)',
} as const

// ── Shadows ───────────────────────────────────────────────────────────────────

export const SHADOW = {
  xs:   '0 1px 2px rgba(0,0,0,0.05)',
  sm:   '0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.04)',
  md:   '0 4px 8px -1px rgba(0,0,0,0.08), 0 2px 4px rgba(0,0,0,0.04)',
  lg:   '0 12px 24px -3px rgba(0,0,0,0.1), 0 4px 8px rgba(0,0,0,0.04)',
  xl:   '0 20px 40px -5px rgba(0,0,0,0.12), 0 8px 16px rgba(0,0,0,0.06)',
  teal: `0 4px 14px rgba(13,148,136,0.35)`,
  tealLg:`0 8px 24px rgba(13,148,136,0.28)`,
} as const

// ── Radius ────────────────────────────────────────────────────────────────────

export const RADIUS = {
  xs:  '4px',
  sm:  '8px',
  md:  '10px',
  lg:  '14px',
  xl:  '20px',
  '2xl': '28px',
  full: '9999px',
} as const

// ── Sidebar constants ─────────────────────────────────────────────────────────

export const SIDEBAR = {
  width:       264,
  bg:          '#111827',
  text:        'rgba(255,255,255,0.5)',
  textHover:   'rgba(255,255,255,0.88)',
  hoverBg:     'rgba(255,255,255,0.06)',
  activeBg:    PALETTE.teal[600],
  activeHover: PALETTE.teal[700],
  divider:     'rgba(255,255,255,0.07)',
} as const

// ── Reusable sx helpers ───────────────────────────────────────────────────────

/** Tinted icon box — used for KPI cards, dialog headers, etc. */
export function iconBoxSx(color: string): SxProps<Theme> {
  return {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
    borderRadius: RADIUS.sm,
    p: 1.1,
    bgcolor: `${color}18`,
    border: `1px solid ${color}28`,
    color,
  }
}

/** Card with hover elevation */
export const cardSx: SxProps<Theme> = {
  border: `1px solid ${PALETTE.stone[200]}`,
  borderRadius: RADIUS.md,
  bgcolor: SURFACE.card,
  boxShadow: SHADOW.sm,
  transition: `box-shadow ${MOTION.smooth}, transform ${MOTION.smooth}, border-color ${MOTION.base}`,
  '&:hover': {
    boxShadow: SHADOW.lg,
    transform: 'translateY(-1px)',
    borderColor: PALETTE.stone[300],
  },
}

/** Overline label style */
export const overlineSx: SxProps<Theme> = {
  fontSize: '0.68rem',
  fontWeight: 700,
  letterSpacing: '0.08em',
  textTransform: 'uppercase',
  color: PALETTE.stone[500],
  display: 'block',
}

/** Monospace style for technical data (VIN, plates, IDs) */
export const monoSx: SxProps<Theme> = {
  fontFamily: FONT.mono,
  fontSize: '0.8rem',
  letterSpacing: '0.04em',
}
