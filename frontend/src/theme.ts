import { createTheme } from '@mui/material/styles'
import { alpha } from '@mui/material'
import { BRAND, FONT, MOTION, PALETTE, RADIUS, SHADOW, SURFACE } from './design-tokens'

export const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main:         BRAND.primary,
      light:        BRAND.primaryLight,
      dark:         BRAND.primaryDark,
      contrastText: '#FFFFFF',
    },
    secondary: {
      main:         PALETTE.slate[500],
      light:        PALETTE.slate[400],
      dark:         PALETTE.slate[700],
      contrastText: '#FFFFFF',
    },
    success: {
      main:  PALETTE.green.main,
      light: PALETTE.green.light,
      dark:  '#15803D',
    },
    error: {
      main:  PALETTE.red.main,
      light: PALETTE.red.light,
      dark:  '#B91C1C',
    },
    warning: {
      main:  PALETTE.amber.main,
      light: PALETTE.amber.light,
      dark:  '#D97706',
    },
    info: {
      main:  PALETTE.blue.main,
      light: PALETTE.blue.light,
      dark:  '#2563EB',
    },
    background: {
      default: SURFACE.page,   // warm stone — not flat white
      paper:   SURFACE.card,   // pure white — cards "float"
    },
    text: {
      primary:   PALETTE.slate[900],
      secondary: PALETTE.slate[500],
    },
    divider: PALETTE.stone[200],
  },

  shape: { borderRadius: 10 },

  typography: {
    fontFamily: FONT.sans,
    h1: { fontWeight: 800, letterSpacing: '-0.03em' },
    h2: { fontWeight: 800, letterSpacing: '-0.025em' },
    h3: { fontWeight: 700, letterSpacing: '-0.02em' },
    h4: { fontWeight: 700, letterSpacing: '-0.02em', color: PALETTE.slate[900] },
    h5: { fontWeight: 700, letterSpacing: '-0.015em' },
    h6: { fontWeight: 600, fontSize: '1.05rem', letterSpacing: '-0.01em' },
    subtitle1: { color: PALETTE.slate[500], fontWeight: 500 },
    subtitle2: { fontWeight: 600 },
    body1:  { fontSize: '0.9rem' },
    body2:  { fontSize: '0.875rem' },
    caption: { fontSize: '0.75rem' },
    overline: {
      fontWeight: 700,
      fontSize: '0.68rem',
      letterSpacing: '0.08em',
      textTransform: 'uppercase',
    },
    button: {
      textTransform: 'none',
      fontWeight: 600,
      letterSpacing: '0.01em',
    },
  },

  shadows: [
    'none',
    SHADOW.xs,
    SHADOW.sm,
    SHADOW.md,
    SHADOW.lg,
    SHADOW.xl,
    ...Array(19).fill('none'),
  ] as any,

  components: {
    // ── Button ────────────────────────────────────────────────────────────────
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: RADIUS.sm,
          boxShadow: 'none',
          padding: '7px 16px',
          transition: `background ${MOTION.fast}, transform ${MOTION.fast}, box-shadow ${MOTION.base}`,
          '&:hover':  { boxShadow: 'none' },
          '&:active': { transform: 'scale(0.975)' },
        },
        containedPrimary: {
          background: BRAND.gradient,
          '&:hover': {
            background: `linear-gradient(135deg, ${BRAND.primaryLight} 0%, ${BRAND.primary} 60%, ${BRAND.primaryDark} 100%)`,
            boxShadow: SHADOW.teal,
          },
        },
        outlined: {
          borderColor: PALETTE.stone[200],
          '&:hover': {
            borderColor: BRAND.primary,
            background: alpha(BRAND.primary, 0.05),
          },
        },
        sizeLarge: { padding: '10px 22px', fontSize: '0.93rem' },
        sizeSmall: { padding: '5px 12px',  fontSize: '0.8rem' },
      },
    },

    // ── Paper ─────────────────────────────────────────────────────────────────
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          border: `1px solid ${PALETTE.stone[200]}`,
          boxShadow: SHADOW.sm,
          borderRadius: RADIUS.md,
        },
      },
    },

    // ── Card ──────────────────────────────────────────────────────────────────
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          border: `1px solid ${PALETTE.stone[200]}`,
          boxShadow: SHADOW.sm,
          borderRadius: RADIUS.md,
          transition: `box-shadow ${MOTION.smooth}, border-color ${MOTION.base}`,
        },
      },
    },

    // ── Chip ──────────────────────────────────────────────────────────────────
    MuiChip: {
      styleOverrides: {
        root: {
          fontWeight: 600,
          fontSize: '0.7rem',
          height: '22px',
          letterSpacing: '0.01em',
          borderRadius: RADIUS.full,
        },
        sizeSmall: { height: '20px', fontSize: '0.68rem' },
      },
    },

    // ── Table ─────────────────────────────────────────────────────────────────
    MuiTableCell: {
      styleOverrides: {
        head: {
          backgroundColor: SURFACE.muted,
          color: PALETTE.stone[500],
          fontWeight: 700,
          fontSize: '0.67rem',
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
          borderBottom: `1px solid ${PALETTE.stone[200]}`,
          padding: '10px 16px',
        },
        root: {
          padding: '13px 16px',
          fontSize: '0.875rem',
          borderBottom: `1px solid ${SURFACE.page}`,
        },
      },
    },
    MuiTableRow: {
      styleOverrides: {
        root: {
          '&:hover td': { backgroundColor: SURFACE.muted },
          transition: `background ${MOTION.fast}`,
        },
      },
    },

    // ── TextField ─────────────────────────────────────────────────────────────
    MuiTextField: {
      defaultProps: { variant: 'outlined', size: 'small' },
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            backgroundColor: SURFACE.card,
            borderRadius: RADIUS.sm,
            transition: `box-shadow ${MOTION.fast}`,
            '& fieldset': { borderColor: PALETTE.stone[200] },
            '&:hover fieldset': { borderColor: PALETTE.stone[400] },
            '&.Mui-focused': {
              boxShadow: `0 0 0 3px ${alpha(BRAND.primary, 0.12)}`,
            },
            '&.Mui-focused fieldset': {
              borderColor: BRAND.primary,
              borderWidth: '1.5px',
            },
          },
          '& .MuiInputLabel-root': { fontSize: '0.875rem' },
        },
      },
    },

    // ── Select / OutlinedInput ────────────────────────────────────────────────
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          borderRadius: RADIUS.sm,
          '& fieldset': { borderColor: PALETTE.stone[200] },
          '&:hover fieldset': { borderColor: `${PALETTE.stone[400]} !important` },
          '&.Mui-focused': {
            boxShadow: `0 0 0 3px ${alpha(BRAND.primary, 0.12)}`,
          },
          '&.Mui-focused fieldset': {
            borderColor: `${BRAND.primary} !important`,
            borderWidth: '1.5px',
          },
        },
      },
    },

    // ── Dialog ────────────────────────────────────────────────────────────────
    MuiDialog: {
      styleOverrides: {
        paper: {
          borderRadius: RADIUS.xl,
          border: `1px solid ${PALETTE.stone[200]}`,
          boxShadow: SHADOW.xl,
        },
      },
    },
    MuiDialogTitle: {
      styleOverrides: {
        root: {
          fontSize: '1rem',
          fontWeight: 700,
          padding: '20px 24px 16px',
        },
      },
    },
    MuiDialogContent: {
      styleOverrides: {
        root: { padding: '8px 24px 16px' },
      },
    },
    MuiDialogActions: {
      styleOverrides: {
        root: { padding: '12px 24px 20px', gap: '8px' },
      },
    },

    // ── Alert ─────────────────────────────────────────────────────────────────
    MuiAlert: {
      styleOverrides: {
        root: { borderRadius: RADIUS.md, fontSize: '0.875rem' },
      },
    },

    // ── Tabs ──────────────────────────────────────────────────────────────────
    MuiTab: {
      styleOverrides: {
        root: {
          fontWeight: 600,
          fontSize: '0.875rem',
          textTransform: 'none',
          letterSpacing: 0,
          minHeight: '42px',
        },
      },
    },
    MuiTabs: {
      styleOverrides: {
        indicator: { height: '2.5px', borderRadius: '2px' },
      },
    },

    // ── LinearProgress ────────────────────────────────────────────────────────
    MuiLinearProgress: {
      styleOverrides: {
        root: {
          borderRadius: RADIUS.full,
          height: '5px',
          backgroundColor: PALETTE.stone[200],
        },
      },
    },

    // ── Tooltip ───────────────────────────────────────────────────────────────
    MuiTooltip: {
      styleOverrides: {
        tooltip: {
          fontSize: '0.75rem',
          fontFamily: FONT.sans,
          borderRadius: RADIUS.sm,
          padding: '5px 10px',
        },
      },
    },

    // ── Autocomplete ──────────────────────────────────────────────────────────
    MuiAutocomplete: {
      styleOverrides: {
        paper: {
          borderRadius: RADIUS.md,
          boxShadow: SHADOW.lg,
          border: `1px solid ${PALETTE.stone[200]}`,
        },
      },
    },
  },
})
