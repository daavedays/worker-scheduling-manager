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
import { Box, Typography } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import AssignmentIcon from '@mui/icons-material/Assignment';
import ListAltIcon from '@mui/icons-material/ListAlt';
import DashboardIcon from '@mui/icons-material/Dashboard';
import HistoryIcon from '@mui/icons-material/History';
import BarChartIcon from '@mui/icons-material/BarChart';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import FadingBackground from '../components/FadingBackground';

function MainMenuPage() {
  const navigate = useNavigate();
  const navCards = [
    { label: 'Main Tasks', icon: <AssignmentIcon sx={{ fontSize: 48 }} />, to: '/x-tasks', desc: 'X-tasks: Core scheduling' },
    { label: 'Secondary Tasks', icon: <ListAltIcon sx={{ fontSize: 48 }} />, to: '/y-tasks', desc: 'Y-tasks: Support scheduling' },
    { label: 'Combined Schedule', icon: <DashboardIcon sx={{ fontSize: 48 }} />, to: '/combined', desc: 'View all schedules' },
    { label: 'View History', icon: <HistoryIcon sx={{ fontSize: 48 }} />, to: '/reset-history', desc: 'See changes & resets' },
    { label: 'Statistics', icon: <BarChartIcon sx={{ fontSize: 48 }} />, to: '/statistics', desc: 'View stats & analytics' },
    { label: 'Help', icon: <HelpOutlineIcon sx={{ fontSize: 48 }} />, to: '/help', desc: 'Get help & info' },
    { label: 'Manage Workers', icon: <AssignmentIcon sx={{ fontSize: 48 }} />, to: '/manage-workers', desc: 'Add, update, remove, or edit qualifications for workers.' },
  ];

  return (
    <Box sx={{ minHeight: '100vh', width: '100vw', position: 'relative', overflow: 'hidden', bgcolor: 'transparent' }}>
      <FadingBackground />
      <Box sx={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-start', pt: { xs: 8, sm: 10, md: 12 } }}>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 4, justifyContent: 'center', width: '100%', maxWidth: 1200 }}>
          {navCards.map(card => (
            <Box
              key={card.label}
              onClick={() => navigate(card.to)}
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
                cursor: 'pointer',
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

export default MainMenuPage; 