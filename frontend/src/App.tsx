/**
 * App.tsx (frontend/src/App.tsx)
 * ------------------------------
 * Main entry point for the React app. Handles global theme, authentication context, routing, and layout.
 *
 * Renders:
 *   - Navigation bar (NavBar)
 *   - All main pages (YTaskPage, XTaskPage, CombinedPage, etc.) via React Router
 *   - Global theme and dark mode
 *   - Authentication context and protected routes
 *
 * Layout:
 *   - Uses Material-UI's ThemeProvider and CssBaseline for global styling
 *   - All pages are rendered inside a <Router>
 *   - Main content is organized by routes
 *
 * State:
 *   - Auth state (loggedIn, user, error, loading)
 *   - Theme (dark mode)
 *
 * Effects:
 *   - Checks session on mount
 *   - Handles login/logout and redirects
 *
 * User Interactions:
 *   - Navigating between pages via the menu
 *   - Logging in/out
 *
 * Sections:
 *   - Navigation bar (top)
 *   - Main content (routes)
 *   - Footer (bottom)
 *
 * Notes:
 *   - All API calls are wrapped with fetchWithAuth to handle 401 redirects
 *   - Each page (YTaskPage, XTaskPage, etc.) is a separate component in /pages
 *   - Inline comments explain each major section and non-obvious logic
 */
import React, { useMemo, useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Link, useLocation, useParams } from 'react-router-dom';
import { ThemeProvider, createTheme, CssBaseline, AppBar, Toolbar, Typography, IconButton, Button, Switch, Box, Menu, MenuItem, TextField } from '@mui/material';
import useMediaQuery from '@mui/material/useMediaQuery';
import Snackbar from '@mui/material/Snackbar';
import MuiAlert from '@mui/material/Alert';
import Fab from '@mui/material/Fab';
import SaveIcon from '@mui/icons-material/Save';
import XTaskPage from './pages/XTaskPage';
import YTaskPage from './pages/YTaskPage';
import XTasksDashboardPage from './pages/XTasksDashboardPage';
import { useNavigate } from 'react-router-dom';
import { formatDateDMY } from './components/utils';
import { getWorkerColor } from './components/colors';
import DarkModeToggle from './components/DarkModeToggle';
import MainMenuPage from './pages/MainMenuPage'; // Import from dedicated file
import ManageWorkersPage from './pages/ManageWorkersPage';
// Remove commented-out imports for unused pages
import StatisticsPage from './pages/StatisticsPage';

// Add a global fetch wrapper to handle 401 Unauthorized and redirect to login
const fetchWithAuth: typeof fetch = async (...args) => {
  const res = await fetch(...args);
  if (res.status === 401) {
    window.location.href = '/login';
    return Promise.reject(new Error('Unauthorized'));
  }
  return res;
};

// --- Theme Setup ---
const getTheme = () => createTheme({
  palette: {
    mode: 'dark',
    primary: { main: '#1e3a5c' }, // Restore previous blue for text
    secondary: { main: '#ff9800' },
    background: {
      default: '#181c23',
      paper: 'rgba(35, 39, 43, 0.85)', // dark gray for boxes
    },
    text: {
      primary: '#e0e6ed',
      secondary: '#b0bec5',
    },
  },
  components: {
    MuiAppBar: {
      styleOverrides: {
        root: { background: 'linear-gradient(90deg, #2d3136 60%, #3a3f44 100%)' },
      },
    },
  },
});

// --- Auth Context ---
type AuthContextType = {
  loggedIn: boolean;
  user: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  error: string | null;
  loading: boolean;
};
const AuthContext = React.createContext<AuthContextType>({
  loggedIn: false,
  user: null,
  login: async () => {},
  logout: async () => {},
  error: null,
  loading: false,
});

function useAuth() {
  return React.useContext(AuthContext);
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { loggedIn } = useAuth();
  const location = useLocation();
  if (!loggedIn) return <Navigate to="/login" state={{ from: location }} replace />;
  // Do NOT redirect to /dashboard if logged in; just render children
  return <>{children}</>;
}

// --- Pages ---
function LoginPage() {
  const { login, error, loading, loggedIn } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();
  React.useEffect(() => {
    window.scrollTo(0, 0);
    // Safari/Chrome autofill workaround: scroll to top again after a short delay
    const t1 = setTimeout(() => window.scrollTo(0, 0), 100);
    const t2 = setTimeout(() => window.scrollTo(0, 0), 300);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, []);
  React.useEffect(() => {
    if (loggedIn && !loading) {
      navigate('/dashboard', { replace: true });
    }
  }, [loggedIn, loading, navigate]);
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    await login(username, password);
    setSubmitting(false);
  };

  // Parallax/fade background logic
  const bgImages = [
    process.env.PUBLIC_URL + '/backgrounds/image_1.png',
    process.env.PUBLIC_URL + '/backgrounds/image_2.png',
    process.env.PUBLIC_URL + '/backgrounds/image_3.jpeg',
  ];
  // We'll use 3 sections: welcome, description, login
  // As user scrolls, fade between images
  const [scrollY, setScrollY] = useState(0);
  React.useEffect(() => {
    const onScroll = () => setScrollY(window.scrollY);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);
  // Calculate which image to show and fade amount
  const sectionHeight = 1000; // px per section
  let fade = (scrollY % sectionHeight) / sectionHeight;
  let bgIndex1 = Math.floor(scrollY / sectionHeight) % bgImages.length;
  let bgIndex2 = (bgIndex1 + 1) % bgImages.length;
  // Clamp for top and bottom
  if (scrollY <= 0) {
    fade = 0;
    bgIndex1 = 0;
    bgIndex2 = 1;
  } else if (scrollY >= (bgImages.length - 1) * sectionHeight) {
    fade = 0;
    bgIndex1 = bgImages.length - 1;
    bgIndex2 = bgImages.length - 1;
  }

  // Style for the parallax/fade background
  const backgroundStyle = {
    position: 'fixed',
    top: 0,
    left: 0,
    width: '100vw',
    height: '100vh',
    zIndex: -1,
    pointerEvents: 'none',
    overflow: 'hidden',
  } as React.CSSProperties;

  // Style for each image (fade in/out)
  const imageStyle = (opacity: number) => ({
    position: 'absolute' as const,
    top: 0,
    left: 0,
    width: '100vw',
    height: '100vh',
    objectFit: 'cover' as const,
    transition: 'opacity 0.7s',
    opacity,
    willChange: 'opacity',
  });

  // Helper for blurred box
  const blurredBox = (children: React.ReactNode, sx: any = {}) => (
    <Box
      sx={{
        width: { xs: '95%', sm: '80%', md: '60%' },
        bgcolor: 'rgba(30, 42, 60, 0.55)',
        borderRadius: 3,
        boxShadow: 4,
        p: 4,
        mb: 3,
        textAlign: 'center',
        backdropFilter: 'blur(8px)',
        WebkitBackdropFilter: 'blur(8px)',
        ...sx,
      }}
    >
      {children}
    </Box>
  );

  return (
    <Box sx={{ minHeight: '100vh', width: '100vw', overflowX: 'hidden', bgcolor: 'transparent', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-start', position: 'relative' }}>
      {/* Parallax/Fade Background */}
      <Box style={backgroundStyle}>
        <img src={bgImages[bgIndex1]} alt="bg1" style={imageStyle(1 - fade)} />
        <img src={bgImages[bgIndex2]} alt="bg2" style={imageStyle(fade)} />
      </Box>
      {/* Welcome Section */}
      <Box sx={{ minHeight: '100vh', width: '100vw', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-start', pt: { xs: 6, sm: 8, md: 10 }, position: 'relative' }}>
        <Box sx={{ width: '100%', display: 'flex', alignItems: 'flex-start', justifyContent: 'center', position: 'relative', zIndex: 2 }}>
          <Box sx={{ bgcolor: 'rgba(35, 39, 43, 0.24)', borderRadius: 6, px: 6, py: 3, boxShadow: 4 }}>
            <Typography variant="h2" sx={{ fontWeight: 900, color: '#e0e6ed', letterSpacing: 1, textShadow: '0 4px 32px #000a' }}>Welcome</Typography>
          </Box>
        </Box>
      </Box>
      {/* Description Section */}
      <Box sx={{ minHeight: '100vh', width: '100vw', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
        <Box sx={{ width: { xs: '95%', sm: '80%', md: '60%' }, bgcolor: 'rgba(35,39,43,0.65)', borderRadius: 3, boxShadow: 4, p: 4, mb: 3, textAlign: 'center', backdropFilter: 'blur(8px)', WebkitBackdropFilter: 'blur(8px)' }}>
          <Typography variant="h5" sx={{ mb: 2, fontWeight: 600, color: '#e0e6ed' }}>Description</Typography>
          <Typography variant="body1" sx={{ color: 'text.secondary' }}>
            This is the Worker Scheduling Manager. Easily create, edit, and view X and Y task schedules for your team. Enjoy a modern, responsive interface with beautiful backgrounds and secure login. (This is placeholder text. Replace with your real description!)
          </Typography>
        </Box>
      </Box>
      {/* Login Section */}
      <Box sx={{ minHeight: '100vh', width: '100vw', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
        <Box sx={{ width: 360, maxWidth: '95vw', bgcolor: 'rgba(35,39,43,0.65)', borderRadius: 3, boxShadow: 4, p: 4, mb: 3, display: 'flex', flexDirection: 'column', alignItems: 'center', backdropFilter: 'blur(8px)', WebkitBackdropFilter: 'blur(8px)' }}>
          <Typography variant="h5" sx={{ mb: 2, fontWeight: 700, color: '#e0e6ed' }}>Log In</Typography>
          <form onSubmit={handleSubmit} style={{ width: '100%' }}>
            <TextField
              label="Username"
              value={username}
              onChange={e => setUsername(e.target.value)}
              fullWidth
              sx={{ mb: 2 }}
              autoFocus
              required
            />
            <TextField
              label="Password"
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              fullWidth
              sx={{ mb: 1 }}
              required
            />
            <Box sx={{ width: '100%', display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
              <Button variant="text" size="small" sx={{ textTransform: 'none' }} disabled>Forgot password?</Button>
            </Box>
            <Button
              variant="contained"
              color="primary"
              type="submit"
              disabled={submitting || loading}
              fullWidth
              sx={{ fontWeight: 700, fontSize: 18 }}
            >
              {submitting || loading ? 'Logging in...' : 'Log In'}
            </Button>
            {error && <Typography color="error" sx={{ mt: 2 }}>{error}</Typography>}
          </form>
        </Box>
      </Box>
      {/* Footer */}
      <Box sx={{ width: '100%', textAlign: 'center', py: 2, mt: 2, color: 'text.secondary', fontSize: 16, borderTop: '1px solid #ccc', opacity: 0.8 }}>
        © All Rights Reserved | Davel
      </Box>
    </Box>
  );
}

function CombinedPage({ darkMode, onToggleDarkMode }: { darkMode: boolean; onToggleDarkMode: () => void }) {
  const [availableSchedules, setAvailableSchedules] = React.useState<any[]>([]);
  const [selectedSchedule, setSelectedSchedule] = React.useState<any | null>(null);
  const [rowLabels, setRowLabels] = React.useState<string[]>([]);
  const [dates, setDates] = React.useState<string[]>([]);
  const [grid, setGrid] = React.useState<string[][]>([]);
  const [loading, setLoading] = React.useState(false);
  const [saving, setSaving] = React.useState(false);
  const [saveSuccess, setSaveSuccess] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  // Load available Y schedule periods
  React.useEffect(() => {
    fetchWithAuth('http://localhost:5000/api/y-tasks/list', { credentials: 'include' })
      .then(res => res.json())
      .then(data => {
        setAvailableSchedules(data.schedules || []);
        if (data.schedules?.length > 0) setSelectedSchedule(data.schedules[0]);
      })
      .catch(() => setError('Failed to load available schedules'));
  }, []);

  // Load combined grid when a schedule is selected
  React.useEffect(() => {
    if (!selectedSchedule) return;
    setLoading(true);
    fetchWithAuth(`http://localhost:5000/api/combined/by-range?start=${encodeURIComponent(selectedSchedule.start)}&end=${encodeURIComponent(selectedSchedule.end)}`, { credentials: 'include' })
      .then(res => res.json())
      .then(data => {
        setRowLabels(data.row_labels || []);
        setDates(data.dates || []);
        setGrid(data.grid || []);
        setLoading(false);
      })
      .catch(() => { setError('Failed to load combined schedule'); setLoading(false); });
  }, [selectedSchedule]);

  const handleSave = async () => {
    if (!selectedSchedule) return;
    setSaving(true);
    try {
      // Create CSV content
      let csv = 'Task,' + dates.join(',') + '\n';
      for (let i = 0; i < rowLabels.length; i++) {
        const row = [rowLabels[i], ...grid[i].map(cell => cell || '-')];
        csv += row.join(',') + '\n';
      }
      const filename = `combined_${selectedSchedule.start.replace(/\//g, '-')}_${selectedSchedule.end.replace(/\//g, '-')}.csv`;
      const res = await fetchWithAuth('http://localhost:5000/api/combined/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ csv, filename }),
      });
      if (!res.ok) throw new Error('Save failed');
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (e: any) {
      setError(e.message || 'Failed to save combined schedule');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Box sx={{ p: 4 }}>
      <DarkModeToggle darkMode={darkMode} onToggle={onToggleDarkMode} />
      <Typography variant="h5" sx={{ mb: 2 }}>Combined Schedule</Typography>
      
      {/* Schedule Selection */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h6" sx={{ mb: 1 }}>Select Schedule Period</Typography>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          {availableSchedules.map((sch: any) => (
            <Button
              key={sch.filename}
              variant={selectedSchedule && sch.filename === selectedSchedule.filename ? 'contained' : 'outlined'}
              onClick={() => setSelectedSchedule(sch)}
              sx={{ minWidth: 200 }}
            >
              {formatDateDMY(sch.start)} TO {formatDateDMY(sch.end)}
            </Button>
          ))}
        </Box>
      </Box>

      {/* Save Button */}
      {grid.length > 0 && (
        <Box sx={{ width: '100%', display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
          <Fab
            color="primary"
            onClick={handleSave}
            disabled={saving || !selectedSchedule}
            sx={{ width: 60, height: 60, boxShadow: 6, borderRadius: '50%', fontWeight: 700 }}
            aria-label="save"
          >
            <SaveIcon sx={{ fontSize: 28, color: '#fff' }} />
          </Fab>
        </Box>
      )}

      {/* Grid */}
      {loading ? (
        <Typography>Loading...</Typography>
      ) : error ? (
        <Typography color="error">{error}</Typography>
      ) : grid.length > 0 ? (
        <Box sx={{ overflowX: 'auto' }}>
          <Box component="table" sx={{ minWidth: dates.length > 0 ? Math.max(900, 180 + dates.length * 120) : 900, width: '100%', borderCollapse: 'separate', borderSpacing: 0, background: darkMode ? '#1a2233' : '#eaf1fa', borderRadius: 4, boxShadow: darkMode ? '0 6px 32px 0 rgba(30,58,92,0.13)' : '0 2px 12px 0 #b0bec522', border: darkMode ? undefined : '1.5px solid #b0bec5', overflow: 'hidden', pt: 2, pb: 2 }}>
            <thead>
              <tr>
                <th style={{ minWidth: 180, background: darkMode ? '#22304a' : '#e3f2fd', color: darkMode ? '#fff' : '#1e3a5c', fontWeight: 700, fontSize: 18, position: 'sticky', left: 0, zIndex: 2, boxShadow: '0 2px 8px rgba(30,58,92,0.08)', borderBottom: '3px solid #ff9800', borderRight: darkMode ? '2px solid #b0bec5' : '2px solid #888', height: 60, letterSpacing: 1 }}>Task</th>
                {dates.map((date, i) => (
                  <th key={i} style={{ minWidth: 120, background: darkMode ? '#1e3a5c' : '#1e3a5c', color: '#fff', fontWeight: 700, fontSize: 16, borderBottom: '3px solid #ff9800', height: 60, boxShadow: '0 2px 8px rgba(30,58,92,0.06)', borderRight: darkMode ? '2px solid #b0bec5' : '2px solid #888' }}>{date}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rowLabels.map((task, rIdx) => (
                <tr key={rIdx} style={{ background: rIdx % 2 === 0 ? (darkMode ? '#232a36' : '#f9fafb') : (darkMode ? '#181c23' : '#fff') }}>
                  <td style={{ background: darkMode ? '#22304a' : '#dbeafe', color: darkMode ? '#fff' : '#1e3a5c', fontWeight: 600, position: 'sticky', left: 0, zIndex: 1, fontSize: 18, borderRight: darkMode ? '3.5px solid #b0bec5' : '3.5px solid #666', borderBottom: darkMode ? '2px solid #b0bec5' : '2px solid #888', height: 56, paddingLeft: 32, paddingRight: 16, minWidth: 180, boxShadow: darkMode ? undefined : '2px 0 8px -4px #8882' }}>{task}</td>
                  {grid[rIdx]?.map((soldier: string, cIdx: number) => (
                    <td key={cIdx} style={{ background: soldier ? getWorkerColor(soldier, darkMode) : (darkMode ? '#1a2233' : '#f7f9fb'), color: darkMode ? '#fff' : '#1e3a5c', textAlign: 'center', fontWeight: 600, minWidth: 120, border: darkMode ? '2px solid #b0bec5' : '2px solid #888', borderRadius: 8, fontSize: 18, height: 56, boxSizing: 'border-box', transition: 'background 0.2s', opacity: soldier ? 1 : 0.6, boxShadow: soldier ? '0 1px 4px rgba(30,58,92,0.06)' : undefined }}>{soldier}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </Box>
        </Box>
      ) : null}

      {/* Save Success Snackbar */}
      <Snackbar open={saveSuccess} autoHideDuration={3000} onClose={() => setSaveSuccess(false)} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        <MuiAlert onClose={() => setSaveSuccess(false)} severity="success" sx={{ width: '100%' }}>
          Combined schedule saved successfully!
        </MuiAlert>
      </Snackbar>
    </Box>
  );
}

function WarningsPage() {
  const [warnings, setWarnings] = React.useState<string[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    setLoading(true);
    fetchWithAuth('http://localhost:5000/api/warnings', { credentials: 'include' })
      .then((res: Response) => res.json())
      .then((data: any) => {
        setWarnings(data.warnings || []);
        setLoading(false);
      })
      .catch(() => { setError('Failed to load warnings'); setLoading(false); });
  }, []);

  if (loading) return <Box sx={{ p: 4 }}><Typography>Loading warnings...</Typography></Box>;
  if (error) return <Box sx={{ p: 4 }}><Typography color="error">{error}</Typography></Box>;

  return (
    <Box sx={{ p: 4 }}>
      <Typography variant="h5" sx={{ mb: 2 }}>Warnings</Typography>
      {warnings.length === 0 ? (
        <Typography>No warnings found.</Typography>
      ) : (
        <ul>
          {warnings.map((w, i) => <li key={i}>{w}</li>)}
        </ul>
      )}
    </Box>
  );
}
{/* Either incorperate or get rid of this */}
function ResetHistoryPage() {
  const [history, setHistory] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [resetting, setResetting] = React.useState(false);
  const [resetSuccess, setResetSuccess] = React.useState(false);
  const [resetError, setResetError] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const fetchHistory = React.useCallback(() => {
    setLoading(true);
    fetchWithAuth('http://localhost:5000/api/history', { credentials: 'include' })
      .then((res: Response) => res.json())
      .then((data: any) => {
        setHistory(data.history || []);
        setLoading(false);
      })
      .catch(() => { setError('Failed to load history'); setLoading(false); });
  }, []);

  React.useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const handleReset = async () => {
    setResetting(true);
    setResetError(null);
    try {
      const res = await fetchWithAuth('http://localhost:5000/api/reset', {
        method: 'POST',
        credentials: 'include',
      });
      if (!res.ok) throw new Error('Reset failed');
      setResetSuccess(true);
      fetchHistory();
    } catch (e: any) {
      setResetError(e.message || 'Failed to reset');
    } finally {
      setResetting(false);
    }
  };

  if (loading) return <Box sx={{ p: 4 }}><Typography>Loading history...</Typography></Box>;
  if (error) return <Box sx={{ p: 4 }}><Typography color="error">{error}</Typography></Box>;

  return (
    <Box sx={{ p: 4 }}>
      <Typography variant="h5" sx={{ mb: 2 }}>Reset / History</Typography>
      <Button variant="contained" color="error" onClick={handleReset} disabled={resetting} sx={{ mb: 2 }}>
        {resetting ? 'Resetting...' : 'Reset All Schedules'}
      </Button>
      {resetSuccess && <MuiAlert severity="success" sx={{ mb: 2 }}>Reset successful!</MuiAlert>}
      {resetError && <MuiAlert severity="error" sx={{ mb: 2 }}>{resetError}</MuiAlert>}
      <Typography variant="h6" sx={{ mt: 3, mb: 1 }}>History</Typography>
      {history.length === 0 ? (
        <Typography>No history found.</Typography>
      ) : (
        <ul>
          {history.map((h, i) => <li key={i}>{typeof h === 'string' ? h : JSON.stringify(h)}</li>)}
        </ul>
      )}
    </Box>
  );
}

// --- Navigation ---
function NavBar() {
  const { loggedIn, logout } = useAuth();
  const isSmall = useMediaQuery('(max-width:900px)');
  const location = useLocation();
  const isLoginPage = location.pathname === '/login';
  return (
    <AppBar position="static" elevation={2}>
      <Toolbar>
        <Box sx={{ display: 'flex', alignItems: 'center', mr: 2 }}>
          <Link to="/dashboard" style={{ display: 'flex', alignItems: 'center' }}>
            <img src={process.env.PUBLIC_URL + '/logos/nevatim.jpeg'} alt="Logo" style={{ height: 44, width: 44, marginRight: 16, borderRadius: '50%', objectFit: 'cover', background: 'none', boxShadow: '0 2px 8px #0002' }} />
          </Link>
        </Box>
        <Typography variant="h6" sx={{ flexGrow: 1 }}>Worker Scheduling Manager</Typography>
        {loggedIn && !isLoginPage && (
          <>
            <Button color="inherit" component={Link} to="/dashboard" sx={{ fontWeight: 700, mr: 2 }}>Menu</Button>
            <Button color="inherit" onClick={logout}>Logout</Button>
          </>
        )}
      </Toolbar>
    </AppBar>
  );
}

function AppRoutes() {
  const [loggedIn, setLoggedIn] = useState(false);
  const [user, setUser] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  
  // Dark mode state with localStorage persistence
  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem('darkMode');
    return saved ? JSON.parse(saved) : true; // Default to dark mode
  });

  const toggleDarkMode = () => {
    const newMode = !darkMode;
    setDarkMode(newMode);
    localStorage.setItem('darkMode', JSON.stringify(newMode));
  };

  // Scroll to top on route change
  React.useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);

  // Real login/logout logic
  const login = async (username: string, password: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('http://localhost:5000/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ username, password }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setLoggedIn(true);
        setUser(data.user);
        setError(null);
      } else {
        setLoggedIn(false);
        setUser(null);
        setError(data.error || 'Login failed');
      }
    } catch (err) {
      setError('Network error');
      setLoggedIn(false);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };
  const logout = async () => {
    setLoading(true);
    try {
      await fetch('http://localhost:5000/api/logout', {
        method: 'POST',
        credentials: 'include',
      });
    } catch {}
    setLoggedIn(false);
    setUser(null);
    setLoading(false);
    navigate('/login');
  };

  // Remember last visited page in localStorage
  useEffect(() => {
    if (loggedIn && location.pathname !== '/login') {
      localStorage.setItem('lastPage', location.pathname);
    }
  }, [loggedIn, location.pathname]);

  // Check session on mount
  React.useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const res = await fetchWithAuth('http://localhost:5000/api/session', {
          credentials: 'include',
        });
        const data = await res.json();
        if (data.logged_in) {
          setLoggedIn(true);
          setUser(data.user);
        } else {
          setLoggedIn(false);
          setUser(null);
        }
      } catch {
        setLoggedIn(false);
        setUser(null);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <AuthContext.Provider value={{ loggedIn, user, login, logout, error, loading }}>
      <NavBar />
      <Routes>
        <Route
          path="/"
          element={
            loggedIn
              ? <Navigate to="/dashboard" replace />
              : <Navigate to="/login" replace />
          }
        />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/dashboard" element={<ProtectedRoute><MainMenuPage /></ProtectedRoute>} />
        <Route path="/x-tasks" element={<ProtectedRoute><XTasksDashboardPage /></ProtectedRoute>} />
        <Route path="/x-tasks/:mode" element={<ProtectedRoute><XTaskPage darkMode={darkMode} onToggleDarkMode={toggleDarkMode} /></ProtectedRoute>} />
        <Route path="/y-tasks" element={<ProtectedRoute><YTaskPage darkMode={darkMode} onToggleDarkMode={toggleDarkMode} /></ProtectedRoute>} />
        <Route path="/combined" element={<ProtectedRoute><CombinedPage darkMode={darkMode} onToggleDarkMode={toggleDarkMode} /></ProtectedRoute>} />
        <Route path="/warnings" element={<ProtectedRoute><WarningsPage /></ProtectedRoute>} />
        <Route path="/reset-history" element={<ProtectedRoute><ResetHistoryPage /></ProtectedRoute>} />
        <Route path="/manage-workers" element={<ProtectedRoute><ManageWorkersPage darkMode={darkMode} onToggleDarkMode={toggleDarkMode} /></ProtectedRoute>} />
        {/* Remove commented-out routes for unused pages */}
        <Route path="/help" element={<ProtectedRoute><Box sx={{ p: 4 }}><Typography variant='h4'>Help (Coming Soon)</Typography></Box></ProtectedRoute>} />
        {/* No catch-all redirect; let router handle refresh and unknown routes */}
      </Routes>
    </AuthContext.Provider>
  );
}

const App: React.FC = () => {
  const theme = useMemo(() => getTheme(), []);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <AppRoutes />
      </Router>
    </ThemeProvider>
  );
};

export default App;
