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

function XTasksDashboardPage() {
  const [year, setYear] = useState(new Date().getFullYear());
  const [period, setPeriod] = useState(1);
  const navigate = useNavigate();
  const [createDisabled, setCreateDisabled] = useState(false);
  // Parallax/fade background logic (reuse from LoginPage/MainMenuPage)
  const bgImages = [
    process.env.PUBLIC_URL + '/backgrounds/image_1.png',
    process.env.PUBLIC_URL + '/backgrounds/image_2.png',
    process.env.PUBLIC_URL + '/backgrounds/image_3.jpeg',
  ];
  const [bgIndex, setBgIndex] = useState(0);
  useEffect(() => {
    const interval = setInterval(() => {
      setBgIndex(i => (i + 1) % bgImages.length);
    }, 5000);
    return () => clearInterval(interval);
  }, [bgImages.length]);
  const [fade, setFade] = useState(false);
  useEffect(() => {
    setFade(true);
    const timeout = setTimeout(() => setFade(false), 1000);
    return () => clearTimeout(timeout);
  }, [bgIndex]);
  // Year dropdown options
  const currentYear = new Date().getFullYear();
  const nextYear = currentYear + 1;
  const yearOptions = [currentYear, nextYear];
  // Check if schedule exists for selected year/period
  useEffect(() => {
    fetch(`http://localhost:5000/api/x-tasks/exists?year=${year}&period=${period}`, { credentials: 'include' })
      .then(res => res.json())
      .then(data => setCreateDisabled(data.exists))
      .catch(() => setCreateDisabled(false));
  }, [year, period]);
  // Card action handlers
  const handleGo = (mode: 'create' | 'edit') => {
    navigate(`/x-tasks/${mode}?year=${year}&period=${period}`);
  };
  return (
    <Box sx={{ minHeight: '100vh', width: '100vw', bgcolor: 'transparent', display: 'flex', flexDirection: 'column', alignItems: 'center', pt: 6, position: 'relative', overflow: 'hidden' }}>
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
      {/* Main Title */}
      <Typography variant="h3" sx={{ fontWeight: 900, mb: 6, color: '#e0e6ed', letterSpacing: 1, textShadow: '0 4px 32px #000a' }}>Main Tasks</Typography>
      {/* Action Cards */}
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 6, justifyContent: 'center', width: '100%', maxWidth: 1200 }}>
        {/* Create Card */}
        <Box sx={{ bgcolor: 'rgba(35,39,43,0.85)', borderRadius: 4, boxShadow: 6, p: 4, minWidth: 260, maxWidth: 320, minHeight: 320, display: 'flex', flexDirection: 'column', alignItems: 'center', color: '#e0e6ed', opacity: createDisabled ? 0.5 : 1 }}>
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
            <Button variant={period === 1 ? 'contained' : 'outlined'} onClick={() => setPeriod(1)}>1st</Button>
            <Button variant={period === 2 ? 'contained' : 'outlined'} onClick={() => setPeriod(2)}>2nd</Button>
          </Box>
          <Button variant="contained" color="primary" sx={{ fontWeight: 700, fontSize: 18, mt: 2 }} onClick={() => handleGo('create')} disabled={createDisabled}>GO</Button>
          <Typography variant="body2" sx={{ mt: 3, color: 'text.secondary', textAlign: 'center' }}>
            {createDisabled ? 'A schedule for this year and period already exists.' : 'Will generate the exact empty table we already have logic for, or allow the user to input the X tasks to soldiers.'}
          </Typography>
        </Box>
        {/* Edit Card */}
        <Box sx={{ bgcolor: 'rgba(35,39,43,0.85)', borderRadius: 4, boxShadow: 6, p: 4, minWidth: 260, maxWidth: 320, minHeight: 320, display: 'flex', flexDirection: 'column', alignItems: 'center', color: '#e0e6ed' }}>
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
            <Button variant={period === 1 ? 'contained' : 'outlined'} onClick={() => setPeriod(1)}>1st</Button>
            <Button variant={period === 2 ? 'contained' : 'outlined'} onClick={() => setPeriod(2)}>2nd</Button>
          </Box>
          <Button variant="contained" color="primary" sx={{ fontWeight: 700, fontSize: 18, mt: 2 }} onClick={() => handleGo('edit')}>GO</Button>
          <Typography variant="body2" sx={{ mt: 3, color: 'text.secondary', textAlign: 'center' }}>
            Generate or load an existing file (if it exists) and allow editing. Saved changes will update the CSV for X tasks for the relevant period.
          </Typography>
        </Box>
      </Box>
    </Box>
  );
}

export default XTasksDashboardPage; 