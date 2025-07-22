import React from 'react';
import { IconButton, Tooltip } from '@mui/material';
import { Brightness4, Brightness7 } from '@mui/icons-material';

interface DarkModeToggleProps {
  darkMode: boolean;
  onToggle: () => void;
  sx?: any;
}

const DarkModeToggle: React.FC<DarkModeToggleProps> = ({ darkMode, onToggle, sx }) => {
  return (
    <Tooltip title={darkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'} arrow>
      <IconButton
        onClick={onToggle}
        sx={{
          position: 'fixed',
          top: 20,
          right: 20,
          zIndex: 1000,
          bgcolor: darkMode ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)',
          color: darkMode ? '#fff' : '#333',
          border: `1px solid ${darkMode ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.2)'}`,
          backdropFilter: 'blur(10px)',
          '&:hover': {
            bgcolor: darkMode ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.2)',
            transform: 'scale(1.1)',
          },
          transition: 'all 0.2s ease-in-out',
          ...sx,
        }}
      >
        {darkMode ? <Brightness7 /> : <Brightness4 />}
      </IconButton>
    </Tooltip>
  );
};

export default DarkModeToggle; 