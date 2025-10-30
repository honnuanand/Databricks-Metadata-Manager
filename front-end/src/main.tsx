import React from 'react'
import ReactDOM from 'react-dom/client'
import { Provider } from 'react-redux'
import { BrowserRouter } from 'react-router-dom'
import { ThemeProvider, createTheme, CssBaseline } from '@mui/material'
import App from './App'
import { store } from './store/store'

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#FF6F3F', // Databricks orange
      light: '#FF8A65',
      dark: '#E64A19',
      contrastText: '#fff',
    },
    secondary: {
      main: '#00B4D8', // Modern blue
      light: '#33C1E8',
      dark: '#007EA7',
      contrastText: '#fff',
    },
    info: {
      main: '#6366F1', // Modern indigo
      light: '#8B92F7',
      dark: '#4F46E5',
    },
    success: {
      main: '#10B981', // Modern green
      light: '#34D399',
      dark: '#059669',
    },
    warning: {
      main: '#F59E0B', // Modern amber
      light: '#FBBF24',
      dark: '#D97706',
    },
    error: {
      main: '#EF4444', // Modern red
      light: '#F87171',
      dark: '#DC2626',
    },
    background: {
      default: '#F8FAFC', // Very light gray
      paper: '#FFFFFF',
    },
    text: {
      primary: '#1E293B', // Dark slate
      secondary: '#64748B', // Slate
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica Neue", Arial, sans-serif',
    h1: {
      fontWeight: 700,
      letterSpacing: '-0.025em',
    },
    h2: {
      fontWeight: 600,
      letterSpacing: '-0.025em',
    },
    h3: {
      fontWeight: 600,
      letterSpacing: '-0.015em',
    },
    h4: {
      fontWeight: 600,
    },
    h5: {
      fontWeight: 600,
    },
    h6: {
      fontWeight: 600,
    },
    button: {
      fontWeight: 500,
      textTransform: 'none', // Disable uppercase
    },
  },
  shape: {
    borderRadius: 8, // More modern border radius
  },
  shadows: [
    'none',
    '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
    '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
    '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
    '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
    '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
    ...Array(19).fill('none'),
  ] as any,
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          padding: '8px 16px',
          fontWeight: 500,
        },
        contained: {
          boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
          '&:hover': {
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
        },
      },
    },
    MuiAccordion: {
      styleOverrides: {
        root: {
          '&:before': {
            display: 'none',
          },
          boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
          marginBottom: 8,
          borderRadius: 8,
          overflow: 'hidden',
        },
      },
    },
    MuiAccordionSummary: {
      styleOverrides: {
        root: {
          backgroundColor: '#FAFAFA',
          '&.Mui-expanded': {
            backgroundColor: '#F5F5F5',
          },
        },
      },
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Provider store={store}>
      <BrowserRouter>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          <App />
        </ThemeProvider>
      </BrowserRouter>
    </Provider>
  </React.StrictMode>,
)