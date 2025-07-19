import React, { useMemo, useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Link, useLocation, useNavigate } from 'react-router-dom';
import { ThemeProvider, createTheme, CssBaseline, AppBar, Toolbar, Typography, IconButton, Button, Switch, Box, Menu, MenuItem, TextField } from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import MoreVertIcon from '@mui/icons-material/MoreVert';
import useMediaQuery from '@mui/material/useMediaQuery';
import Papa from 'papaparse';
import { DatePicker, LocalizationProvider } from '@mui/x-date-pickers';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemText from '@mui/material/ListItemText';
import Snackbar from '@mui/material/Snackbar';
import MuiAlert from '@mui/material/Alert';
import Fab from '@mui/material/Fab';
import DeleteIcon from '@mui/icons-material/Delete';
import SaveIcon from '@mui/icons-material/Save';
import CircularProgress from '@mui/material/CircularProgress';
import AutoFixHighIcon from '@mui/icons-material/AutoFixHigh';
import logo from './logo_2.png';
import nevatimLogo from './nevatim.jpeg';
import Tooltip from '@mui/material/Tooltip';
import DashboardIcon from '@mui/icons-material/Dashboard';
import AssignmentIcon from '@mui/icons-material/Assignment';
import ListAltIcon from '@mui/icons-material/ListAlt';
import HistoryIcon from '@mui/icons-material/History';
import BarChartIcon from '@mui/icons-material/BarChart';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';

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
  const sectionHeight = 400; // px per section
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
function XTaskPage({ darkMode }: { darkMode: boolean }) {
  const STANDARD_X_TASKS = ["Guarding Duties", "RASAR", "Kitchen"];
  const [data, setData] = useState<string[][]>([]);
  const [headers, setHeaders] = useState<string[]>([]);
  const [subheaders, setSubheaders] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editData, setEditData] = useState<string[][]>([]);
  const [conflicts, setConflicts] = useState<{[key: string]: {x_task: string, y_task: string}}>({});
  const [customTasks, setCustomTasks] = useState<any>({});
  const [modal, setModal] = useState<{open: boolean, row: number, col: number, weekLabel: string, weekRange: string, soldier: string}>({open: false, row: -1, col: -1, weekLabel: '', weekRange: '', soldier: ''});
  const [modalTask, setModalTask] = useState<string>('');
  const [modalOther, setModalOther] = useState<{name: string, range: [Date | null, Date | null]}>({name: '', range: [null, null]});
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [customTaskWarning, setCustomTaskWarning] = useState('');
  const MAX_CUSTOM_TASK_LEN = 14;
  const [conflictWarning, setConflictWarning] = useState(false);
  // Updated color map for tasks (more contrast in light mode)
  const TASK_COLORS: Record<string, string> = {
    'Guarding Duties': darkMode ? '#2e7dbe' : '#90caf9',
    'RASAR': darkMode ? '#8e24aa' : '#ce93d8',
    'Kitchen': darkMode ? '#fbc02d' : '#ffe082',
    'Custom': darkMode ? '#43a047' : '#a5d6a7',
  };
  // Helper: render cell with color, custom task date, and conflict
  function renderCell(cell: string, colIdx: number, rowIdx: number) {
    let bg = darkMode ? '#1a2233' : '#eaf1fa'; // default cell background
    let color = darkMode ? '#fff' : '#1e3a5c';
    let task = cell.split('\n')[0];
    let isCustom = false;
    let dateRange = '';
    if (cell.includes('\n(')) {
      isCustom = true;
      const match = cell.match(/\((\d{2}\/\d{2}\/\d{4})-(\d{2}\/\d{2}\/\d{4})\)/);
      if (match) {
        // Show as dd/mm-dd/mm
        const [_, start, end] = match;
        dateRange = `${start.slice(0,5)}-${end.slice(0,5)}`;
      }
      bg = TASK_COLORS['Custom'];
    } else if (TASK_COLORS[task]) {
      bg = TASK_COLORS[task];
    }
    // Conflict highlight
    let isConflict = false;
    let conflictInfo: {x_task: string, y_task: string} | undefined = undefined;
    if (conflicts && colIdx > 0 && editData[rowIdx] && editData[rowIdx][0]) {
      const soldier = editData[rowIdx][0];
      const date = headers[colIdx]; // Use the actual date, not the week range
      const key = `${soldier}|${date}`;
      if (conflicts[key]) {
        isConflict = true;
        conflictInfo = conflicts[key];
      }
    }
    const cellContent = (
      <div style={{
        width: '100%',
        height: '100%',
        background: isConflict ? '#ffbdbd' : bg,
        color,
        borderRadius: 6,
        padding: '4px 6px',
        fontWeight: 600,
        fontSize: 15,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: 36,
        boxSizing: 'border-box',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
        border: isConflict ? '2.5px solid #ff1744' : `1.5px solid ${darkMode ? '#2c3550' : '#b0bec5'}`,
        boxShadow: isConflict ? '0 0 12px 2px #ff1744cc' : undefined,
        transition: 'box-shadow 0.2s, border 0.2s',
        cursor: isConflict ? 'pointer' : 'default',
      }}>
        <span style={{
          fontSize: isCustom ? 13 : 15,
          fontWeight: 700,
          maxWidth: 90,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}>{task.length > MAX_CUSTOM_TASK_LEN ? task.slice(0, MAX_CUSTOM_TASK_LEN) + '…' : task}</span>
        {isCustom && dateRange && (
          <span style={{ fontSize: 11, color: darkMode ? '#b0bec5' : '#555', marginTop: 2 }}>{dateRange}</span>
        )}
    </div>
    );
    if (isConflict && conflictInfo) {
      return (
        <Tooltip
          title={`Conflict: ${editData[rowIdx][0]} has both X task (${conflictInfo.x_task}) and Y task (${conflictInfo.y_task}) on ${headers[colIdx]}. Please adjust the Y schedule for this date.`}
          arrow
          placement="top"
        >
          {cellContent}
        </Tooltip>
      );
    }
    return cellContent;
  }
  // Helper: check if cell is filled
  function isCellFilled(cell: string) {
    return cell && cell !== '-';
  }
  // Remove assignment logic
  const handleRemoveAssignment = () => {
    const { row, col, soldier } = modal;
    const cellValue = editData[row][col];
    // If custom task, remove from customTasks state for the relevant date range
    if (cellValue.includes('\n(')) {
      // Remove from all weeks and from customTasks
      const match = cellValue.match(/(.+)\n\((\d{2}\/\d{2}\/\d{4})-(\d{2}\/\d{2}\/\d{4})\)/);
      if (match) {
        const [, taskName, start, end] = match;
        setCustomTasks((prev: any) => {
          const updated = { ...prev };
          if (updated[soldier]) {
            updated[soldier] = updated[soldier].filter((t: any) => !(t.task === taskName && t.start === start && t.end === end));
            if (updated[soldier].length === 0) delete updated[soldier];
          }
          return updated;
        });
        setEditData(prev => {
          const copy = prev.map(r => [...r]);
          for (let c = 1; c < headers.length; ++c) {
            if (copy[row][c] === cellValue) copy[row][c] = '';
          }
          return copy;
        });
      }
    } else {
      // Standard task: just clear this cell
      setEditData(prev => {
        const copy = prev.map(r => [...r]);
        copy[row][col] = '';
        return copy;
      });
    }
    setModal(m => ({ ...m, open: false }));
  };
  // Fetch X task CSV and custom tasks
  React.useEffect(() => {
    setLoading(true);
    fetch('http://localhost:5000/api/x-tasks', { credentials: 'include' })
      .then(res => res.json())
      .then(({ csv, custom_tasks }) => {
        const parsed = Papa.parse<string[]>(csv, { skipEmptyLines: false });
        setHeaders(parsed.data[0] as string[]);
        setSubheaders(parsed.data[1] as string[]);
        // Only use actual data rows (skip header and subheader)
        setData(parsed.data.slice(2) as string[][]);
        setEditData(parsed.data.slice(2) as string[][]);
        setCustomTasks(custom_tasks || {});
        setLoading(false);
        fetchConflicts();
      })
      .catch(() => { setError('Failed to load X tasks'); setLoading(false); });
  }, []);

  // Fetch conflicts after saving
  const fetchConflicts = React.useCallback(() => {
    return fetch('http://localhost:5000/api/x-tasks/conflicts', { credentials: 'include' })
      .then(res => res.json())
      .then(data => {
        const map: {[key: string]: {x_task: string, y_task: string}} = {};
        (data.conflicts || []).forEach((c: any) => {
          map[`${c.soldier}|${c.date}`] = { x_task: c.x_task, y_task: c.y_task };
        });
        setConflicts(map);
        return (data.conflicts || []).length;
      });
  }, []);

  const handleCellChange = (row: number, col: number, value: string) => {
    setEditData(prev => {
      const copy = prev.map(r => [...r]);
      copy[row][col] = value;
      return copy;
    });
  };

  const handleCellClick = (row: number, col: number) => {
    setModal({
      open: true,
      row,
      col,
      weekLabel: headers[col],
      weekRange: subheaders[col],
      soldier: editData[row][0],
    });
    setModalTask('');
    setModalOther({name: '', range: [null, null]});
  };
  const handleModalSave = () => {
    if (modalTask === 'Other') {
      if (!modalOther.name || !modalOther.range[0] || !modalOther.range[1]) return;
      if (modalOther.name.length > MAX_CUSTOM_TASK_LEN) {
        setCustomTaskWarning(`Custom task name must be at most ${MAX_CUSTOM_TASK_LEN} characters.`);
        return;
      }
      setCustomTaskWarning('');
      // Save custom task
      const s = modal.soldier;
      const newCustom = {...customTasks};
      if (!newCustom[s]) newCustom[s] = [];
      newCustom[s].push({
        task: modalOther.name,
        start: formatDateDMY(modalOther.range[0]),
        end: formatDateDMY(modalOther.range[1]),
      });
      setCustomTasks(newCustom);
      // Update grid for all overlapping weeks
      setEditData(prev => {
        const copy = prev.map(r => [...r]);
        for (let c = 1; c < headers.length; ++c) {
          const [start, end] = (subheaders[c] || '').split(' - ');
          if (!start || !end) continue;
          const weekStart = parseDM(start, headers[0]);
          const weekEnd = parseDM(end, headers[0]);
          if (!weekStart || !weekEnd) continue;
          // If overlap
          if (modalOther.range[0]! < weekEnd && modalOther.range[1]! > weekStart) {
            copy[modal.row][c] = `${modalOther.name}\n(${formatDateDMY(modalOther.range[0]!)}-${formatDateDMY(modalOther.range[1]!)})`;
          }
        }
        return copy;
      });
    } else if (modalTask) {
      setEditData(prev => {
        const copy = prev.map(r => [...r]);
        copy[modal.row][modal.col] = modalTask;
        return copy;
      });
    }
    setModal(m => ({...m, open: false}));
  };
  function formatDateDMY(date: Date): string {
    const d = date.getDate().toString().padStart(2, '0');
    const m = (date.getMonth() + 1).toString().padStart(2, '0');
    const y = date.getFullYear().toString();
    return `${d}/${m}/${y}`;
  }
  function parseDM(dm: string, yearHeader: string): Date | null {
    // dm: '07/01', yearHeader: '1' (week number, not year, so fallback to current year)
    const [d, m] = dm.split('/');
    const y = new Date().getFullYear();
    try {
      return new Date(Number(y), Number(m) - 1, Number(d));
    } catch {
      return null;
    }
  }
  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const csv = Papa.unparse([headers, subheaders, ...editData]);
      const res = await fetch('http://localhost:5000/api/x-tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ csv, custom_tasks: customTasks, year, half }),
      });
      if (!res.ok) throw new Error('Save failed');
      setSaveSuccess(true);
      fetchConflicts().then((conflictCount) => {
        setConflictWarning(conflictCount > 0);
      });
    } catch {
      setError('Failed to save X tasks');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <Box sx={{ p: 4 }}><Typography>Loading X tasks...</Typography></Box>;
  if (error) return <Box sx={{ p: 4 }}><Typography color="error">{error}</Typography></Box>;

  // Year and half for saving (assume from first week date)
  const firstDate = subheaders[1]?.split(' - ')[0];
  let year = new Date().getFullYear();
  let half = 1;
  if (firstDate) {
    const [d, m] = firstDate.split('/');
    if (m === '07') half = 2;
    if (m === '01') half = 1;
    // Try to infer year from custom tasks or fallback
    const anyCustom = Object.values(customTasks).flat()[0];
    if (anyCustom && typeof anyCustom === 'object' && 'start' in anyCustom) {
      year = parseInt((anyCustom as any).start.split('/')[2], 10) || year;
    }
  }

  return (
    <Box sx={{ p: 2, overflowX: 'auto', minWidth: 900, position: 'relative' }}>
      <Typography variant="h5" sx={{ mb: 2 }}>X Task Assignment</Typography>
      {/* Floating Save Button */}
      <Fab
        color="primary"
        size="large"
        onClick={handleSave}
        sx={{
          position: 'fixed',
          bottom: 32,
          right: 32,
          zIndex: 1000,
          boxShadow: 6,
          width: 78,
          height: 78,
          borderRadius: '50%',
          background: 'linear-gradient(135deg, #1e3a5c 60%, #ff9800 100%)',
          transition: 'all 0.2s',
          '&:hover': {
            boxShadow: 12,
            background: 'linear-gradient(135deg, #223e6a 60%, #ffb74d 100%)',
            transform: 'scale(1.08)',
          },
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
        aria-label="save"
      >
        <SaveIcon sx={{ fontSize: 38, color: '#fff' }} />
      </Fab>
      <Box component="table" sx={{ width: '100%', borderCollapse: 'separate', borderSpacing: 0, minWidth: 900, background: 'none', borderRadius: 2, boxShadow: 3 }}>
        <thead>
          <tr>
            <th style={{
              minWidth: 160,
              fontWeight: 700,
              fontSize: 18,
              background: darkMode ? '#22304a' : '#e3f2fd',
              color: darkMode ? '#fff' : '#1e3a5c',
              borderTopLeftRadius: 8,
              position: 'sticky',
              left: 0,
              zIndex: 3,
              top: 0,
              borderLeft: `3px solid ${darkMode ? '#3b4252' : '#b0bec5'}`,
              paddingLeft: 16,
              borderRight: `1.5px solid ${darkMode ? '#3b4252' : '#b0bec5'}`,
              borderBottom: `2px solid ${darkMode ? '#2c3550' : '#b0bec5'}`,
              backgroundClip: 'padding-box',
            }}>Soldier</th>
            {headers.slice(1).map((h, i) => (
              <th key={i} style={{
                textAlign: 'center',
                padding: 8,
                background: '#1e3a5c',
                color: '#fff',
                fontWeight: 700,
                fontSize: 16,
                position: 'sticky',
                top: 0,
                zIndex: 2,
                minWidth: 120,
                maxWidth: 160,
                whiteSpace: 'nowrap',
                borderBottom: `2px solid ${darkMode ? '#2c3550' : '#b0bec5'}`,
                backgroundClip: 'padding-box',
              }}>
                <div>Week {h}</div>
                <div style={{ fontSize: 12, color: '#ff9800', marginTop: 2 }}>{subheaders[i+1]}</div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {editData.map((row, rIdx) => {
            // Defensive: skip if row[0] is empty or looks like a date range (e.g., accidental subheader)
            if (!row[0] || row[0].includes('/')) return null;
            const soldierName = (row[0] || '').trim();
            // Ensure every row has the same number of cells as the header
            const rowCells = row.slice(1);
            const numCells = headers.length - 1;
            const paddedCells = rowCells.length < numCells ? [...rowCells, ...Array(numCells - rowCells.length).fill('')] : rowCells;
            return (
              <tr key={rIdx}>
                <td style={{
                  fontWeight: 600,
                  background: darkMode ? '#22304a' : '#e3f2fd',
                  color: darkMode ? '#fff' : '#1e3a5c',
                  minWidth: 160,
                  position: 'sticky',
                  left: 0,
                  zIndex: 1,
                  borderLeft: `3px solid ${darkMode ? '#3b4252' : '#b0bec5'}`,
                  paddingLeft: 16,
                  borderRight: `1.5px solid ${darkMode ? '#3b4252' : '#b0bec5'}`,
                  borderBottom: `1.5px solid ${darkMode ? '#2c3550' : '#b0bec5'}`,
                  backgroundClip: 'padding-box',
                }}>{soldierName}</td>
                {paddedCells.map((cell, cIdx) => {
                  const colIdx = cIdx + 1;
                  return (
                    <td key={colIdx} style={{
                      padding: 0,
                      minWidth: 120,
                      maxWidth: 160,
                      borderBottom: `1.5px solid ${darkMode ? '#2c3550' : '#b0bec5'}`,
                      background: darkMode ? '#1a2233' : '#eaf1fa',
                      backgroundClip: 'padding-box',
                      height: 48,
                    }}
                      onClick={() => handleCellClick(rIdx, colIdx)}
                    >
                      {renderCell(cell, colIdx, rIdx)}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </Box>
      {/* Modal for cell editing */}
      <Dialog open={modal.open} onClose={() => setModal(m => ({...m, open: false}))}>
        <DialogTitle sx={{ color: darkMode ? '#fff' : '#1e3a5c', background: darkMode ? '#232a36' : '#fff' }}>Assign X Task for {modal.soldier} - Week {modal.weekLabel}</DialogTitle>
        <DialogContent sx={{ background: darkMode ? '#232a36' : '#fff' }}>
          <List>
            {STANDARD_X_TASKS.map((task, idx) => (
              <ListItem key={idx} disablePadding>
                <ListItemButton selected={modalTask === task} onClick={() => setModalTask(task)} sx={{ color: darkMode ? '#fff' : '#1e3a5c', background: modalTask === task ? (TASK_COLORS[task] || '#e3f2fd') : 'inherit' }}>
                  <ListItemText primary={task} />
                </ListItemButton>
              </ListItem>
            ))}
            <ListItem disablePadding>
              <ListItemButton selected={modalTask === 'Other'} onClick={() => setModalTask('Other')} sx={{ color: darkMode ? '#fff' : '#1e3a5c', background: modalTask === 'Other' ? (TASK_COLORS['Custom'] || '#e3f2fd') : 'inherit' }}>
                <ListItemText primary="Other (Custom Task)" />
              </ListItemButton>
            </ListItem>
          </List>
          {modalTask === 'Other' && (
            <Box sx={{ mt: 2 }}>
              <TextField
                label="Custom Task Name"
                value={modalOther.name}
                onChange={e => {
                  if (e.target.value.length <= MAX_CUSTOM_TASK_LEN) setModalOther(o => ({...o, name: e.target.value}));
                }}
                fullWidth
                sx={{ mb: 2 }}
                inputProps={{ maxLength: MAX_CUSTOM_TASK_LEN }}
                helperText={customTaskWarning || `${modalOther.name.length}/${MAX_CUSTOM_TASK_LEN} chars`}
                error={!!customTaskWarning}
              />
              <LocalizationProvider dateAdapter={AdapterDateFns}>
                <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                  <DatePicker
                    label="Start Date"
                    value={modalOther.range[0]}
                    onChange={(date: Date | null) => setModalOther(o => ({...o, range: [date, o.range[1]]}))}
                    slotProps={{ textField: { sx: { minWidth: 180 } } }}
                  />
                  <DatePicker
                    label="End Date"
                    value={modalOther.range[1]}
                    onChange={(date: Date | null) => setModalOther(o => ({...o, range: [o.range[0], date]}))}
                    slotProps={{ textField: { sx: { minWidth: 180 } } }}
                  />
                </Box>
              </LocalizationProvider>
            </Box>
          )}
          {isCellFilled(editData[modal.row]?.[modal.col] || '') && (
            <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
              <Button
                variant="outlined"
                color="error"
                startIcon={<DeleteIcon />}
                onClick={handleRemoveAssignment}
                sx={{ fontWeight: 700 }}
              >
                Remove Assignment
              </Button>
            </Box>
          )}
        </DialogContent>
        <DialogActions sx={{ background: darkMode ? '#232a36' : '#fff' }}>
          <Button onClick={() => setModal(m => ({...m, open: false}))} sx={{ color: darkMode ? '#fff' : '#1e3a5c' }}>Cancel</Button>
          <Button onClick={handleModalSave} disabled={modalTask === '' || (modalTask === 'Other' && (!modalOther.name || !modalOther.range[0] || !modalOther.range[1]))} sx={{ color: darkMode ? '#fff' : '#1e3a5c' }}>Save</Button>
        </DialogActions>
      </Dialog>
      <Snackbar open={saveSuccess} autoHideDuration={3000} onClose={() => setSaveSuccess(false)} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        <MuiAlert onClose={() => setSaveSuccess(false)} severity="success" sx={{ width: '100%' }}>
          X tasks saved successfully!
        </MuiAlert>
      </Snackbar>
      <Snackbar open={conflictWarning} autoHideDuration={6000} onClose={() => setConflictWarning(false)} anchorOrigin={{ vertical: 'top', horizontal: 'center' }}>
        <MuiAlert onClose={() => setConflictWarning(false)} severity="warning" sx={{ width: '100%' }}>
          X/Y conflict detected! Some X tasks overlap with Y tasks. Please review the highlighted cells and adjust the Y schedule as needed.
        </MuiAlert>
      </Snackbar>
    </Box>
  );
}
function YTaskPage({ darkMode }: { darkMode: boolean }) {
  const Y_TASKS = [
    "Supervisor",
    "C&N Driver",
    "C&N Escort",
    "Southern Driver",
    "Southern Escort"
  ];
  // Fixed color palette for Y tasks, matching X tasks
  const Y_TASK_COLORS: Record<string, { light: string, dark: string }> = {
    'Supervisor':      { light: '#b39ddb', dark: '#5e35b1' },
    'C&N Driver':      { light: '#80cbc4', dark: '#00897b' },
    'C&N Escort':      { light: '#ffe082', dark: '#fbc02d' },
    "Southern Driver": { light: '#90caf9', dark: '#1976d2' },
    "Southern Escort": { light: '#a5d6a7', dark: '#388e3c' },
  };
  const [startDate, setStartDate] = React.useState<Date | null>(null);
  const [endDate, setEndDate] = React.useState<Date | null>(null);
  const [mode, setMode] = React.useState('');
  const [grid, setGrid] = React.useState<string[][]>([]);
  const [dates, setDates] = React.useState<string[]>([]);
  const [warnings, setWarnings] = React.useState<string[]>([]);
  const [loading, setLoading] = React.useState(false);
  // Save button state
  const [saving, setSaving] = React.useState(false);
  const [saveSuccess, setSaveSuccess] = React.useState(false);
  const [saveError, setSaveError] = React.useState<string | null>(null);
  // Manual assignment picker state
  const [pickerOpen, setPickerOpen] = React.useState(false);
  const [pickerCell, setPickerCell] = React.useState<{ y: number, d: number } | null>(null);
  const [availableSoldiers, setAvailableSoldiers] = React.useState<string[]>([]);
  const [pickerLoading, setPickerLoading] = React.useState(false);
  // Hybrid: track if any cell is filled
  const hasManualAssignment = React.useMemo(() => grid.some(row => row.some(cell => cell)), [grid]);
  // Bomb animation state
  const [showBomb, setShowBomb] = React.useState(false);

  const handleGenerate = async () => {
    if (!startDate || !endDate) return;
    setLoading(true);
    setWarnings([]);
    const start = startDate.toLocaleDateString('en-GB').split('/').map((x: string) => x.padStart(2, '0')).join('/');
    const end = endDate.toLocaleDateString('en-GB').split('/').map((x: string) => x.padStart(2, '0')).join('/');
    const res = await fetch('http://localhost:5000/api/y-tasks/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ start, end, mode: 'auto' })
    });
    const data = await res.json();
    if (res.ok) {
      setGrid(data.grid);
      setDates(data.dates);
      setWarnings(data.warnings || []);
    } else {
      setWarnings([data.error || 'Failed to generate schedule']);
      setGrid([]);
      setDates([]);
    }
    setLoading(false);
  };

  // Save Y tasks as CSV
  const handleSave = async () => {
    setSaving(true);
    setSaveError(null);
    try {
      // Build CSV in the format: Name,date1,date2,...\nSoldier1,task1,task2,...\n
      // Transpose grid: grid[yTaskIdx][dateIdx] => assignments[dateIdx][yTaskIdx]
      // For each date, for each yTask, get the soldier
      // Build a map: { soldier: [task1, task2, ...] }
      const assignments: Record<string, string[]> = {};
      for (let y = 0; y < Y_TASKS.length; ++y) {
        for (let d = 0; d < dates.length; ++d) {
          const soldier = grid[y]?.[d] || '';
          if (!soldier) continue;
          if (!assignments[soldier]) assignments[soldier] = Array(dates.length).fill('');
          assignments[soldier][d] = Y_TASKS[y];
        }
      }
      // Ensure all soldiers are present (even if all empty)
      const allSoldiers = Object.keys(assignments);
      // Compose CSV
      let csv = 'Name,' + dates.join(',') + '\n';
      for (const soldier of allSoldiers) {
        csv += soldier + ',' + assignments[soldier].map(t => t || '-').join(',') + '\n';
      }
      const res = await fetch('http://localhost:5000/api/y-tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'text/csv' },
        credentials: 'include',
        body: csv,
      });
      if (!res.ok) throw new Error('Save failed');
      setSaveSuccess(true);
    } catch (e: any) {
      setSaveError(e.message || 'Failed to save Y tasks');
    } finally {
      setSaving(false);
    }
  };

  // Manual cell click handler
  const handleCellClick = async (y: number, d: number) => {
    setPickerCell({ y, d });
    setPickerOpen(true);
    setPickerLoading(true);
    // Build current_assignments map: { soldier: { date: y_task } }
    const current_assignments: Record<string, Record<string, string>> = {};
    for (let yy = 0; yy < Y_TASKS.length; ++yy) {
      for (let dd = 0; dd < dates.length; ++dd) {
        const s = grid[yy]?.[dd];
        if (!s) continue;
        if (!current_assignments[s]) current_assignments[s] = {};
        current_assignments[s][dates[dd]] = Y_TASKS[yy];
      }
    }
    // Fetch available soldiers
    const res = await fetch('http://localhost:5000/api/y-tasks/available-soldiers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({
        date: dates[d],
        task: Y_TASKS[y],
        current_assignments,
      }),
    });
    const data = await res.json();
    setAvailableSoldiers(data.available || []);
    setPickerLoading(false);
  };

  // Hybrid: Generate Automatically handler
  const handleHybridGenerate = async () => {
    // Bomb animation trigger
    setShowBomb(true);
    setTimeout(() => setShowBomb(false), 1200);
    setLoading(true);
    setWarnings([]);
    // Send current grid to backend to fill empty cells
    const res = await fetch('http://localhost:5000/api/y-tasks/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({
        start: dates[0],
        end: dates[dates.length - 1],
        mode: 'hybrid',
        partial_grid: grid,
        y_tasks: Y_TASKS,
        dates,
      }),
    });
    const data = await res.json();
    if (res.ok && data.grid) {
      setGrid(data.grid);
      setWarnings(data.warnings || []);
    } else {
      setWarnings([data.error || 'Failed to generate schedule']);
    }
    setLoading(false);
  };

  // Remove assignment handler for Y task grid
  const handleRemoveYAssignment = () => {
    if (!pickerCell) return;
    setGrid(prev => {
      const copy = prev.map(r => [...r]);
      copy[pickerCell.y][pickerCell.d] = '';
      return copy;
    });
    setPickerOpen(false);
  };

  // Calculate dynamic width for both top bar and table
  const tableWidth = dates.length > 0 ? Math.max(900, 180 + dates.length * 120) : 900;

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ width: '100%', overflowX: 'auto' }}>
        <Box sx={{ minWidth: tableWidth, width: '100%' }}>
          {/* Responsive top section: always match table width */}
          <Box
            sx={{
              minWidth: tableWidth,
              width: '100%',
              background: darkMode ? '#1a2233' : '#eaf1fa',
              borderRadius: 3,
              boxShadow: darkMode ? 3 : '0 2px 12px 0 #b0bec522',
              border: darkMode ? undefined : '1.5px solid #b0bec5',
              p: 2,
              mb: 3,
              pt: 3,
              pb: 3,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'flex-start',
            }}
          >
            <Typography variant="h5" sx={{ mb: 2 }}>Y Task Assignment</Typography>
            <LocalizationProvider dateAdapter={AdapterDateFns}>
              <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                <DatePicker
                  label="Start Date"
                  value={startDate}
                  onChange={(date: Date | null) => setStartDate(date)}
                  slotProps={{ textField: { sx: { minWidth: 180 } } }}
                />
                <DatePicker
                  label="End Date"
                  value={endDate}
                  onChange={(date: Date | null) => setEndDate(date)}
                  slotProps={{ textField: { sx: { minWidth: 180 } } }}
                />
              </Box>
            </LocalizationProvider>
            <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
              <Button variant={mode === 'auto' ? 'contained' : 'outlined'} onClick={() => { setMode('auto'); handleGenerate(); }} disabled={!startDate || !endDate || loading}>Automatic</Button>
              <Button
                variant={mode === 'hybrid' ? 'contained' : 'outlined'}
                onClick={() => {
                  setMode('hybrid');
                  if (startDate && endDate) {
                    // Generate empty grid for selected dates
                    const start = startDate;
                    const end = endDate;
                    const days = [];
                    let d = new Date(start);
                    while (d <= end) {
                      days.push(d.toLocaleDateString('en-GB').split('/').map(x => x.padStart(2, '0')).join('/'));
                      d.setDate(d.getDate() + 1);
                    }
                    setDates(days);
                    setGrid(Array(Y_TASKS.length).fill(0).map(() => Array(days.length).fill('')));
                    setWarnings([]);
                  }
                }}
                disabled={!startDate || !endDate || loading}
              >
                Set Preferences
              </Button>
              {/* Hide Manual button, keep for reference: <Button ...>Manual</Button> */}
              <Button variant={mode === 'manual' ? 'contained' : 'outlined'} sx={{ display: 'none' }}>Manual</Button>
              <Button variant={mode === 'hybrid' ? 'contained' : 'outlined'} disabled sx={{ display: 'none' }}>Hybrid</Button>
            </Box>
          </Box>
          {/* Horizontal FABs for hybrid mode, fixed at top right above the table */}
          {mode === 'hybrid' && grid.length > 0 && (
            <Box sx={{
              position: 'fixed',
              top: 100,
              right: 32,
              zIndex: 1200,
              display: 'flex',
              flexDirection: 'row',
              gap: 2,
              alignItems: 'center',
            }}>
              <Fab
                color="info"
                onClick={handleHybridGenerate}
                disabled={loading}
                sx={{ width: 60, height: 60, boxShadow: 6, borderRadius: '50%', fontWeight: 700 }}
                aria-label="generate-rest"
              >
                <AutoFixHighIcon sx={{ fontSize: 28, color: '#fff' }} />
              </Fab>
              <Fab
                color="primary"
                onClick={handleSave}
                disabled={saving || grid.length === 0}
                sx={{ width: 60, height: 60, boxShadow: 6, borderRadius: '50%', fontWeight: 700 }}
                aria-label="save"
              >
                <SaveIcon sx={{ fontSize: 28, color: '#fff' }} />
              </Fab>
            </Box>
          )}
          {/* Floating Save FAB for auto mode */}
          {mode === 'auto' && grid.length > 0 && (
            <Fab
              color="primary"
              onClick={handleSave}
              sx={{
                position: 'fixed',
                bottom: 32,
                right: 32,
                zIndex: 1200,
                width: 60,
                height: 60,
                boxShadow: 6,
                borderRadius: '50%',
                fontWeight: 700,
              }}
              aria-label="save"
              disabled={saving || grid.length === 0}
            >
              <SaveIcon sx={{ fontSize: 28, color: '#fff' }} />
            </Fab>
          )}
          {warnings.length > 0 && (
            <MuiAlert severity="warning" sx={{ mb: 2 }}>
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                {warnings.map((w: string, i: number) => <li key={i}>{w}</li>)}
              </ul>
            </MuiAlert>
          )}
          {grid.length > 0 && (
            <>
              <Box
                component="table"
                sx={{
                  minWidth: tableWidth,
                  width: '100%',
                  borderCollapse: 'separate',
                  borderSpacing: 0,
                  background: darkMode ? '#1a2233' : '#eaf1fa',
                  borderRadius: 4,
                  boxShadow: darkMode ? '0 6px 32px 0 rgba(30,58,92,0.13)' : '0 2px 12px 0 #b0bec522',
                  border: darkMode ? undefined : '1.5px solid #b0bec5',
                  overflow: 'hidden',
                  pt: 2,
                  pb: 2,
                }}
              >
                <thead>
                  <tr>
                    <th
                      style={{
                        minWidth: 160,
                        background: darkMode ? '#22304a' : '#e3f2fd',
                        color: darkMode ? '#fff' : '#1e3a5c',
                        fontWeight: 700,
                        fontSize: 18,
                        position: 'sticky',
                        left: 0,
                        zIndex: 2,
                        boxShadow: '0 2px 8px rgba(30,58,92,0.08)',
                        borderBottom: '3px solid #ff9800',
                        borderRight: darkMode ? '2px solid #b0bec5' : '2px solid #888',
                        height: 60,
                        letterSpacing: 1,
                      }}
                    >
                      Y Task
                    </th>
                    {dates.map((date: string, i: number) => (
                      <th
                        key={i}
                        style={{
                          minWidth: 120,
                          background: darkMode ? '#1e3a5c' : '#1e3a5c',
                          color: '#fff',
                          fontWeight: 700,
                          fontSize: 16,
                          borderBottom: '3px solid #ff9800',
                          height: 60,
                          boxShadow: '0 2px 8px rgba(30,58,92,0.06)',
                          borderRight: darkMode ? '2px solid #b0bec5' : '2px solid #888',
                        }}
                      >
                        {date}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {Y_TASKS.map((yTask: string, rIdx: number) => (
                    <tr key={rIdx} style={{ background: rIdx % 2 === 0 ? (darkMode ? '#232a36' : '#f9fafb') : (darkMode ? '#181c23' : '#fff') }}>
                      <td
                        style={{
                          background: darkMode ? '#22304a' : '#dbeafe', // deeper blue/gray in light mode
                          color: darkMode ? '#fff' : '#1e3a5c',
                          fontWeight: 600,
                          position: 'sticky',
                          left: 0,
                          zIndex: 1,
                          fontSize: 18,
                          borderRight: darkMode ? '3.5px solid #b0bec5' : '3.5px solid #666',
                          borderBottom: darkMode ? '2px solid #b0bec5' : '2px solid #888',
                          height: 56,
                          paddingLeft: 32,
                          paddingRight: 16,
                          minWidth: 180,
                          boxShadow: darkMode ? undefined : '2px 0 8px -4px #8882',
                        }}
                      >
                        {yTask}
                      </td>
                      {grid[rIdx]?.map((soldier: string, cIdx: number) => (
                        <td
                          key={cIdx}
                          style={{
                            background: soldier
                              ? (Y_TASK_COLORS[yTask]?.[darkMode ? 'dark' : 'light'] || (darkMode ? '#333' : '#f7f9fb'))
                              : (darkMode ? '#1a2233' : '#f7f9fb'),
                            color: darkMode ? '#fff' : '#1e3a5c',
                            textAlign: 'center',
                            fontWeight: 600,
                            minWidth: 120,
                            border: darkMode ? '2px solid #b0bec5' : '2px solid #888',
                            borderRadius: 8,
                            fontSize: 18,
                            height: 56,
                            boxSizing: 'border-box',
                            transition: 'background 0.2s',
                            cursor: mode === 'manual' || mode === 'hybrid' ? 'pointer' : (soldier ? 'pointer' : 'default'),
                            boxShadow: soldier ? '0 1px 4px rgba(30,58,92,0.06)' : undefined,
                          }}
                          onClick={() => (mode === 'manual' || mode === 'hybrid') && handleCellClick(rIdx, cIdx)}
                          onMouseOver={e => { (e.currentTarget as HTMLElement).style.background = '#ffe082'; }}
                          onMouseOut={e => { (e.currentTarget as HTMLElement).style.background = soldier
                            ? (Y_TASK_COLORS[yTask]?.[darkMode ? 'dark' : 'light'] || (darkMode ? '#333' : '#f7f9fb'))
                            : (darkMode ? '#1a2233' : '#f7f9fb'); }}
                        >
                          {soldier}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </Box>
              {/* Soldier Picker Modal */}
              <Dialog open={pickerOpen} onClose={() => setPickerOpen(false)}>
                <DialogTitle>Assign Soldier</DialogTitle>
                <DialogContent>
                  {pickerLoading ? <CircularProgress /> : (
                    <List>
                      {availableSoldiers.map(s => (
                        <ListItemButton key={s} onClick={() => {
                          setGrid(prev => {
                            const copy = prev.map(r => [...r]);
                            if (pickerCell) copy[pickerCell.y][pickerCell.d] = s;
                            return copy;
                          });
                          setPickerOpen(false);
                        }}>
                          <ListItemText primary={s} />
                        </ListItemButton>
                      ))}
                      {availableSoldiers.length === 0 && <Typography>No available soldiers</Typography>}
                      {/* Remove assignment button for Y task cell */}
                      {pickerCell && grid[pickerCell.y][pickerCell.d] && (
                        <ListItemButton onClick={handleRemoveYAssignment} sx={{ color: 'error.main', mt: 1 }}>
                          <DeleteIcon sx={{ mr: 1 }} />
                          <ListItemText primary="Remove Assignment" />
                        </ListItemButton>
                      )}
                    </List>
                  )}
                </DialogContent>
                <DialogActions>
                  <Button onClick={() => setPickerOpen(false)}>Cancel</Button>
                </DialogActions>
              </Dialog>
            </>
          )}
        </Box>
      </Box>
      <Snackbar open={saveSuccess} autoHideDuration={3000} onClose={() => setSaveSuccess(false)} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        <MuiAlert onClose={() => setSaveSuccess(false)} severity="success" sx={{ width: '100%' }}>
          Y tasks saved successfully!
        </MuiAlert>
      </Snackbar>
      <Snackbar open={!!saveError} autoHideDuration={4000} onClose={() => setSaveError(null)} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        <MuiAlert onClose={() => setSaveError(null)} severity="error" sx={{ width: '100%' }}>
          {saveError}
        </MuiAlert>
      </Snackbar>
    </Box>
  );
}
function getSoldierColor(name: string, darkMode: boolean) {
  // Generate a consistent color per soldier name
  // Use HSL for a wide range of hues
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  const hue = Math.abs(hash) % 360;
  return `hsl(${hue}, 60%, ${darkMode ? '32%' : '82%'})`;
}

function CombinedPage({ darkMode }: { darkMode: boolean }) {
  const [rowLabels, setRowLabels] = React.useState<string[]>([]);
  const [dates, setDates] = React.useState<string[]>([]);
  const [grid, setGrid] = React.useState<string[][]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    setLoading(true);
    fetch('http://localhost:5000/api/combined/grid', { credentials: 'include' })
      .then(res => res.json())
      .then(data => {
        setRowLabels(data.row_labels || []);
        setDates(data.dates || []);
        setGrid(data.grid || []);
        setLoading(false);
      })
      .catch(() => { setError('Failed to load combined schedule'); setLoading(false); });
  }, []);

  if (loading) return <Box sx={{ p: 4 }}><Typography>Loading combined schedule...</Typography></Box>;
  if (error) return <Box sx={{ p: 4 }}><Typography color="error">{error}</Typography></Box>;

  return (
    <Box sx={{ p: 4, overflowX: 'auto' }}>
      <Typography variant="h5" sx={{ mb: 2 }}>Combined Schedule</Typography>
      <Box component="table" sx={{
        minWidth: dates.length > 0 ? Math.max(900, 180 + dates.length * 120) : 900,
        width: '100%',
        borderCollapse: 'separate',
        borderSpacing: 0,
        background: darkMode ? '#1a2233' : '#eaf1fa',
        borderRadius: 4,
        boxShadow: darkMode ? '0 6px 32px 0 rgba(30,58,92,0.13)' : '0 2px 12px 0 #b0bec522',
        border: darkMode ? undefined : '1.5px solid #b0bec5',
        overflow: 'hidden',
        pt: 2,
        pb: 2,
      }}>
        <thead>
          <tr>
            <th style={{
              minWidth: 160,
              background: darkMode ? '#22304a' : '#e3f2fd',
              color: darkMode ? '#fff' : '#1e3a5c',
              fontWeight: 700,
              fontSize: 18,
              position: 'sticky',
              left: 0,
              zIndex: 2,
              boxShadow: '0 2px 8px rgba(30,58,92,0.08)',
              borderBottom: '3px solid #ff9800',
              borderRight: darkMode ? '2px solid #b0bec5' : '2px solid #888',
              height: 60,
              letterSpacing: 1,
            }}>
              Task
            </th>
            {dates.map((date, i) => (
              <th key={i} style={{
                minWidth: 120,
                background: darkMode ? '#1e3a5c' : '#1e3a5c',
                color: '#fff',
                fontWeight: 700,
                fontSize: 16,
                borderBottom: '3px solid #ff9800',
                height: 60,
                boxShadow: '0 2px 8px rgba(30,58,92,0.06)',
                borderRight: darkMode ? '2px solid #b0bec5' : '2px solid #888',
              }}>{date}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rowLabels.map((task, rIdx) => (
            <tr key={rIdx} style={{ background: rIdx % 2 === 0 ? (darkMode ? '#232a36' : '#f9fafb') : (darkMode ? '#181c23' : '#fff') }}>
              <td style={{
                background: darkMode ? '#22304a' : '#dbeafe',
                color: darkMode ? '#fff' : '#1e3a5c',
                fontWeight: 600,
                position: 'sticky',
                left: 0,
                zIndex: 1,
                fontSize: 18,
                borderRight: darkMode ? '3.5px solid #b0bec5' : '3.5px solid #666',
                borderBottom: darkMode ? '2px solid #b0bec5' : '2px solid #888',
                height: 56,
                paddingLeft: 32,
                paddingRight: 16,
                minWidth: 180,
                boxShadow: darkMode ? undefined : '2px 0 8px -4px #8882',
              }}>{task}</td>
              {grid[rIdx]?.map((soldier: string, cIdx: number) => (
                <td key={cIdx} style={{
                  background: soldier
                    ? getSoldierColor(soldier, darkMode)
                    : (darkMode ? '#1a2233' : '#f7f9fb'),
                  color: darkMode ? '#fff' : '#1e3a5c',
                  textAlign: 'center',
                  fontWeight: 600,
                  minWidth: 120,
                  border: darkMode ? '2px solid #b0bec5' : '2px solid #888',
                  borderRadius: 8,
                  fontSize: 18,
                  height: 56,
                  boxSizing: 'border-box',
                  transition: 'background 0.2s',
                  opacity: soldier ? 1 : 0.6,
                  boxShadow: soldier ? '0 1px 4px rgba(30,58,92,0.06)' : undefined,
                }}>
                  {soldier}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </Box>
    </Box>
  );
}

function WarningsPage() {
  const [warnings, setWarnings] = React.useState<string[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    setLoading(true);
    fetch('http://localhost:5000/api/warnings', { credentials: 'include' })
      .then(res => res.json())
      .then(data => {
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

function ResetHistoryPage() {
  const [history, setHistory] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [resetting, setResetting] = React.useState(false);
  const [resetSuccess, setResetSuccess] = React.useState(false);
  const [resetError, setResetError] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const fetchHistory = React.useCallback(() => {
    setLoading(true);
    fetch('http://localhost:5000/api/history', { credentials: 'include' })
      .then(res => res.json())
      .then(data => {
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
      const res = await fetch('http://localhost:5000/api/reset', {
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

function MainMenuPage() {
  // Fading background logic (like front page, but always blurred/dark)
  const bgImages = [
    process.env.PUBLIC_URL + '/backgrounds/image_1.png',
    process.env.PUBLIC_URL + '/backgrounds/image_2.png',
    process.env.PUBLIC_URL + '/backgrounds/image_3.jpeg',
  ];
  const [bgIndex, setBgIndex] = React.useState(0);
  // Scroll to top on mount
  React.useEffect(() => { window.scrollTo(0, 0); }, []);
  React.useEffect(() => {
    const interval = setInterval(() => {
      setBgIndex(i => (i + 1) % bgImages.length);
    }, 5000);
    return () => clearInterval(interval);
  }, [bgImages.length]);

  // Fade effect
  const [fade, setFade] = React.useState(false);
  React.useEffect(() => {
    setFade(true);
    const timeout = setTimeout(() => setFade(false), 1000);
    return () => clearTimeout(timeout);
  }, [bgIndex]);

  // Navigation cards
  const navCards = [
    { label: 'Main Tasks', icon: <AssignmentIcon sx={{ fontSize: 48 }} />, to: '/x-tasks', desc: 'X-tasks: Core scheduling' },
    { label: 'Secondary Tasks', icon: <ListAltIcon sx={{ fontSize: 48 }} />, to: '/y-tasks', desc: 'Y-tasks: Support scheduling' },
    { label: 'Combined Schedule', icon: <DashboardIcon sx={{ fontSize: 48 }} />, to: '/combined', desc: 'View all schedules' },
    { label: 'View History', icon: <HistoryIcon sx={{ fontSize: 48 }} />, to: '/reset-history', desc: 'See changes & resets' },
    { label: 'Statistics', icon: <BarChartIcon sx={{ fontSize: 48 }} />, to: '/statistics', desc: 'View stats & analytics' },
    { label: 'Help', icon: <HelpOutlineIcon sx={{ fontSize: 48 }} />, to: '/help', desc: 'Get help & info' },
  ];

  return (
    <Box sx={{ minHeight: '100vh', width: '100vw', position: 'relative', overflow: 'hidden', bgcolor: 'transparent' }}>
      {/* Fading blurred background */}
      <Box sx={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', zIndex: -1, pointerEvents: 'none', overflow: 'hidden' }}>
        {bgImages.map((img, i) => (
          <img
            key={img}
            src={img}
            alt="bg"
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100vw',
              height: '100vh',
              objectFit: 'cover',
              opacity: i === bgIndex ? (fade ? 0.7 : 1) : 0,
              transition: 'opacity 1.2s',
              filter: 'blur(16px) brightness(0.5)',
            }}
          />
        ))}
      </Box>
      <Box sx={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-start', pt: { xs: 8, sm: 10, md: 12 } }}>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 4, justifyContent: 'center', width: '100%', maxWidth: 1200 }}>
          {navCards.map(card => (
            <Box
              key={card.label}
              component={Link}
              to={card.to}
              sx={{
                textDecoration: 'none',
                bgcolor: 'rgba(35,39,43,0.75)',
                borderRadius: 4,
                boxShadow: 6,
                p: 4,
                minWidth: 220,
                maxWidth: 260,
                minHeight: 200,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#e0e6ed',
                transition: 'transform 0.18s, box-shadow 0.18s, background 0.18s',
                '&:hover': {
                  transform: 'scale(1.045)',
                  boxShadow: 12,
                  bgcolor: 'rgba(35,39,43,0.92)',
                },
              }}
            >
              {card.icon}
              <Typography variant="h5" sx={{ fontWeight: 700, mt: 2, mb: 1 }}>{card.label}</Typography>
              <Typography variant="body2" sx={{ color: 'text.secondary', textAlign: 'center' }}>{card.desc}</Typography>
            </Box>
          ))}
        </Box>
      </Box>
      <Box sx={{ width: '100%', textAlign: 'center', py: 2, mt: 4, color: 'text.secondary', fontSize: 16, borderTop: '1px solid #ccc', opacity: 0.8 }}>
        © All Rights Reserved | Davel
      </Box>
    </Box>
  );
}

function AppRoutes() {
  const [loggedIn, setLoggedIn] = useState(false);
  const [user, setUser] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

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
        const res = await fetch('http://localhost:5000/api/session', {
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
        <Route path="/login" element={<LoginPage />} />
        <Route path="/dashboard" element={<ProtectedRoute><MainMenuPage /></ProtectedRoute>} />
        <Route path="/x-tasks" element={<ProtectedRoute><XTaskPage darkMode={true} /></ProtectedRoute>} />
        <Route path="/y-tasks" element={<ProtectedRoute><YTaskPage darkMode={true} /></ProtectedRoute>} />
        <Route path="/combined" element={<ProtectedRoute><CombinedPage darkMode={true} /></ProtectedRoute>} />
        <Route path="/warnings" element={<ProtectedRoute><WarningsPage /></ProtectedRoute>} />
        <Route path="/reset-history" element={<ProtectedRoute><ResetHistoryPage /></ProtectedRoute>} />
        <Route path="/statistics" element={<ProtectedRoute><Box sx={{ p: 4 }}><Typography variant='h4'>Statistics (Coming Soon)</Typography></Box></ProtectedRoute>} />
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
