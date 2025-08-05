/**
 * XTasksDashboardPage.tsx
 * ----------------------
 * Dashboard page for managing X task schedules (main/primary tasks).
 *
 * Renders:
 *   - Parallax/fading background
 *   - Main title
 *   - Action cards for creating or editing X task schedules
 *   - Year/period selectors
 *   - GO buttons for navigation
 *
 * State:
 *   - year, period: Selected year and half (1st/2nd)
 *   - createDisabled: Whether a schedule already exists for the selection
 *   - bgIndex, fade: For background animation
 *
 * Effects:
 *   - Animates/fades background images
 *   - Checks if schedule exists for selected year/period
 *
 * User Interactions:
 *   - Select year/period
 *   - Navigate to create/edit X task schedule
 *
 * Notes:
 *   - Inline comments explain non-obvious logic and UI structure
 */
import React, { useState, useEffect } from 'react';
import { Box, Typography, Button, TextField } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import FadingBackground from '../components/FadingBackground';
import Footer from '../components/Footer';
import Snackbar from '@mui/material/Snackbar';
import MuiAlert from '@mui/material/Alert';

function XTasksDashboardPage() {
  const [year, setYear] = useState(new Date().getFullYear());
  const [period, setPeriod] = useState(1);
  const navigate = useNavigate();
  const [scheduleExists, setScheduleExists] = useState(false);
  const [exists1, setExists1] = useState(false);
  const [exists2, setExists2] = useState(false);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMsg, setSnackbarMsg] = useState('');
  // Restore year options
  const currentYear = new Date().getFullYear();
  const nextYear = currentYear + 1;
  const yearOptions = [currentYear, nextYear];

  useEffect(() => {
    fetch(`http://localhost:5001/api/x-tasks/exists?year=${year}&period=1`, { credentials: 'include' })
      .then(res => res.json())
      .then(data => setExists1(!!data.exists))
      .catch(() => setExists1(false));
    fetch(`http://localhost:5001/api/x-tasks/exists?year=${year}&period=2`, { credentials: 'include' })
      .then(res => res.json())
      .then(data => setExists2(!!data.exists))
      .catch(() => setExists2(false));
  }, [year]);

  useEffect(() => {
    if (period === 1) setScheduleExists(exists1);
    else setScheduleExists(exists2);
  }, [period, exists1, exists2]);

  const handleGo = (mode: 'create' | 'edit') => {
    navigate(`/x-tasks/${mode}?year=${year}&period=${period}`);
  };

  const handleDisabledDoubleClick = (type: 'create' | 'edit') => {
    if (type === 'create') {
      setSnackbarMsg('A schedule for this year and period already exists. Try editing it, or select a different year/period.');
    } else {
      setSnackbarMsg('No schedule exists for this year and period yet. Try creating one, or select a different year/period.');
    }
    setSnackbarOpen(true);
  };

  // Helper: is this period available for creation?
  const canCreate1 = !exists1;
  const canCreate2 = !exists2;
  // Helper: is this period available for editing?
  const canEdit1 = exists1;
  const canEdit2 = exists2;

  return (
    <Box sx={{ minHeight: '100vh', width: '100vw', position: 'relative', overflow: 'hidden', bgcolor: 'transparent' }}>
      <FadingBackground />
      {/* Main content follows */}
      <Box sx={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', pt: 6, position: 'relative', overflow: 'hidden' }}>
        {/* Main Title */}
        <Typography variant="h3" sx={{ fontWeight: 900, mb: 6, color: '#e0e6ed', letterSpacing: 1, textShadow: '0 4px 32px #000a' }}>Main Tasks</Typography>
        {/* Action Cards */}
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 6, justifyContent: 'center', width: '100%', maxWidth: 1200 }}>
          {/* Create Card */}
          <Box
            sx={{
              bgcolor: scheduleExists ? 'rgba(35,39,43,0.85)' : '#2e7dbe',
              borderRadius: 4,
              boxShadow: scheduleExists ? 6 : '0 0 24px 4px #2e7dbe99',
              p: 4,
              minWidth: 260,
              maxWidth: 320,
              minHeight: 320,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              color: '#e0e6ed',
              opacity: scheduleExists ? 0.5 : 1,
              cursor: scheduleExists ? 'not-allowed' : 'pointer',
              transition: 'box-shadow 0.2s, background 0.2s',
            }}
            onDoubleClick={() => scheduleExists && handleDisabledDoubleClick('create')}
          >
            <Typography variant="h5" sx={{ fontWeight: 700, mb: 2 }}>Create</Typography>
            <TextField
              select
              label="Year"
              value={year}
              onChange={e => setYear(Number(e.target.value))}
              sx={{ mb: 2 }}
              SelectProps={{ native: true }}
            >
              {yearOptions.map(y => <option key={y} value={y}>{y}</option>)}
            </TextField>
            <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
              <Button
                variant={period === 1 ? 'contained' : 'outlined'}
                color={canCreate1 ? 'secondary' : 'primary'}
                sx={canCreate1 && scheduleExists ? { boxShadow: '0 0 12px 2px #ff980099', fontWeight: 900 } : {}}
                onClick={() => setPeriod(1)}
                disabled={!canCreate1 && scheduleExists}
              >1st</Button>
              <Button
                variant={period === 2 ? 'contained' : 'outlined'}
                color={canCreate2 ? 'secondary' : 'primary'}
                sx={canCreate2 && scheduleExists ? { boxShadow: '0 0 12px 2px #ff980099', fontWeight: 900 } : {}}
                onClick={() => setPeriod(2)}
                disabled={!canCreate2 && scheduleExists}
              >2nd</Button>
            </Box>
            <Button
              variant="contained"
              color={scheduleExists ? 'primary' : 'secondary'}
              sx={{ fontWeight: 700, fontSize: 18, mt: 2, boxShadow: !scheduleExists ? '0 0 16px 2px #ff980099' : undefined }}
              onClick={() => handleGo('create')}
              disabled={scheduleExists}
              onDoubleClick={() => scheduleExists && handleDisabledDoubleClick('create')}
            >GO</Button>
            <Typography variant="body2" sx={{ mt: 3, color: 'text.secondary', textAlign: 'center' }}>
              {scheduleExists ? 'A schedule for this year and period already exists.' : 'Will generate the exact empty table we already have logic for, or allow the user to input the X tasks to soldiers.'}
            </Typography>
          </Box>
          {/* Edit Card */}
          <Box
            sx={{
              bgcolor: scheduleExists ? '#2e7dbe' : 'rgba(35,39,43,0.85)',
              borderRadius: 4,
              boxShadow: scheduleExists ? '0 0 24px 4px #2e7dbe99' : 6,
              p: 4,
              minWidth: 260,
              maxWidth: 320,
              minHeight: 320,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              color: '#e0e6ed',
              opacity: scheduleExists ? 1 : 0.5,
              cursor: scheduleExists ? 'pointer' : 'not-allowed',
              transition: 'box-shadow 0.2s, background 0.2s',
            }}
            onDoubleClick={() => !scheduleExists && handleDisabledDoubleClick('edit')}
          >
            <Typography variant="h5" sx={{ fontWeight: 700, mb: 2 }}>Edit</Typography>
            <TextField
              select
              label="Year"
              value={year}
              onChange={e => setYear(Number(e.target.value))}
              sx={{ mb: 2 }}
              SelectProps={{ native: true }}
            >
              {yearOptions.map(y => <option key={y} value={y}>{y}</option>)}
            </TextField>
            <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
              <Button
                variant={period === 1 ? 'contained' : 'outlined'}
                color={canEdit1 ? 'secondary' : 'primary'}
                sx={canEdit1 && !scheduleExists ? { boxShadow: '0 0 12px 2px #ff980099', fontWeight: 900 } : {}}
                onClick={() => setPeriod(1)}
                disabled={!canEdit1 && !scheduleExists}
              >1st</Button>
              <Button
                variant={period === 2 ? 'contained' : 'outlined'}
                color={canEdit2 ? 'secondary' : 'primary'}
                sx={canEdit2 && !scheduleExists ? { boxShadow: '0 0 12px 2px #ff980099', fontWeight: 900 } : {}}
                onClick={() => setPeriod(2)}
                disabled={!canEdit2 && !scheduleExists}
              >2nd</Button>
            </Box>
            <Button
              variant="contained"
              color={scheduleExists ? 'secondary' : 'primary'}
              sx={{ fontWeight: 700, fontSize: 18, mt: 2, boxShadow: scheduleExists ? '0 0 16px 2px #ff980099' : undefined }}
              onClick={() => handleGo('edit')}
              disabled={!scheduleExists}
              onDoubleClick={() => !scheduleExists && handleDisabledDoubleClick('edit')}
            >GO</Button>
            <Typography variant="body2" sx={{ mt: 3, color: 'text.secondary', textAlign: 'center' }}>
              {scheduleExists ? 'Generate or load an existing file (if it exists) and allow editing. Saved changes will update the CSV for X tasks for the relevant period.' : 'No schedule exists for this year and period yet.'}
            </Typography>
          </Box>
        </Box>
      </Box>
      <Snackbar open={snackbarOpen} autoHideDuration={5000} onClose={() => setSnackbarOpen(false)} anchorOrigin={{ vertical: 'top', horizontal: 'center' }}>
        <MuiAlert onClose={() => setSnackbarOpen(false)} severity="info" sx={{ width: '100%' }}>
          {snackbarMsg}
        </MuiAlert>
      </Snackbar>
      <Footer />
    </Box>
  );
}

export default XTasksDashboardPage; 