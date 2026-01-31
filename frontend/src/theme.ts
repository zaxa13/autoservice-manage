import { createTheme, alpha } from '@mui/material/styles';

// Цветовая палитра "Modern Slate & Indigo"
const PRIMARY = {
  main: '#4F46E5', // Indigo 600
  light: '#818CF8',
  dark: '#3730A3',
  contrastText: '#FFFFFF',
};

const SECONDARY = {
  main: '#64748B', // Slate 500
  light: '#94A3B8',
  dark: '#334155',
  contrastText: '#FFFFFF',
};

const SUCCESS = {
  main: '#10B981', // Emerald 500
  light: '#34D399',
  dark: '#059669',
};

const ERROR = {
  main: '#EF4444', // Red 500
  light: '#F87171',
  dark: '#B91C1C',
};

export const theme = createTheme({
  palette: {
    mode: 'light',
    primary: PRIMARY,
    secondary: SECONDARY,
    success: SUCCESS,
    error: ERROR,
    background: {
      default: '#F8FAFC', // Очень светлый серо-голубой фон
      paper: '#FFFFFF',
    },
    text: {
      primary: '#1E293B', // Slate 800
      secondary: '#64748B', // Slate 500
    },
    divider: '#E2E8F0',
  },
  shape: {
    borderRadius: 12, // Делаем интерфейс мягче
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", Arial, sans-serif',
    h1: { fontWeight: 800, letterSpacing: '-0.02em' },
    h4: { fontWeight: 700, letterSpacing: '-0.02em', color: '#1E293B' },
    h6: { fontWeight: 600, fontSize: '1.1rem' },
    button: { textTransform: 'none', fontWeight: 600 },
    subtitle1: { color: '#64748B' },
  },
  shadows: [
    'none',
    '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
    '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px -1px rgba(0, 0, 0, 0.1)',
    '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1)',
    '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1)',
    ...Array(20).fill('none'), // Заполняем остальные, чтобы не было ошибок
  ] as any,
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          padding: '8px 20px',
          boxShadow: 'none',
          '&:hover': {
            boxShadow: 'none',
          },
        },
        containedPrimary: {
          background: `linear-gradient(135deg, ${PRIMARY.main} 0%, ${PRIMARY.dark} 100%)`,
          '&:hover': {
            background: `linear-gradient(135deg, ${PRIMARY.light} 0%, ${PRIMARY.main} 100%)`,
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          border: '1px solid #E2E8F0',
          boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.05)',
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        head: {
          backgroundColor: '#F1F5F9',
          color: '#475569',
          fontWeight: 700,
          borderBottom: '1px solid #E2E8F0',
        },
        root: {
          padding: '16px',
        },
      },
    },
    MuiTextField: {
      defaultProps: {
        variant: 'outlined',
        size: 'small',
      },
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            backgroundColor: '#FFFFFF',
            '&:hover fieldset': {
              borderColor: PRIMARY.main,
            },
          },
        },
      },
    },
  },
});