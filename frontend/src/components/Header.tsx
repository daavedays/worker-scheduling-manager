import React from 'react';
import { Box, Typography, IconButton } from '@mui/material';
import { useNavigate, useLocation } from 'react-router-dom';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import HomeIcon from '@mui/icons-material/Home';
import MenuIcon from '@mui/icons-material/Menu';
import DarkModeToggle from './DarkModeToggle';

interface HeaderProps {
  darkMode: boolean;
  onToggleDarkMode: () => void;
  showBackButton?: boolean;
  showHomeButton?: boolean;
  showMenuButton?: boolean;
  showDarkModeToggle?: boolean;
  title?: string;
  onBackClick?: () => void;
  onHomeClick?: () => void;
  onMenuClick?: () => void;
}

const Header: React.FC<HeaderProps> = ({
  darkMode,
  onToggleDarkMode,
  showBackButton = false,
  showHomeButton = false,
  showMenuButton = false,
  showDarkModeToggle = true,
  title = "Worker Scheduling Manager",
  onBackClick,
  onHomeClick,
  onMenuClick
}) => {
  const navigate = useNavigate();
  const location = useLocation();

  const handleBackClick = () => {
    if (onBackClick) {
      onBackClick();
    } else {
      navigate(-1);
    }
  };

  const handleHomeClick = () => {
    if (onHomeClick) {
      onHomeClick();
    } else {
      navigate('/dashboard');
    }
  };

  const handleMenuClick = () => {
    if (onMenuClick) {
      onMenuClick();
    } else {
      navigate('/dashboard');
    }
  };

  return (
    <Box
      sx={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        height: 64,
        background: darkMode ? '#2c3e50' : '#34495e',
        borderBottom: `2px solid ${darkMode ? '#34495e' : '#2c3e50'}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        px: 3,
        zIndex: 1200,
        boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
      }}
    >
      {/* Left side - Logo and Title */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        {/* Logo */}
        <Box
          sx={{
            width: 40,
            height: 40,
            background: 'linear-gradient(135deg, #3498db, #2980b9)',
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 2px 8px rgba(52, 152, 219, 0.3)',
            position: 'relative',
            overflow: 'hidden',
          }}
        >
          {/* Calendar/Schedule Icon */}
          <Box
            sx={{
              width: 20,
              height: 20,
              position: 'relative',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {/* Calendar base */}
            <Box
              sx={{
                width: 16,
                height: 14,
                border: '2px solid #fff',
                borderRadius: '2px 2px 4px 4px',
                position: 'relative',
              }}
            />
            {/* Calendar top */}
            <Box
              sx={{
                position: 'absolute',
                top: -2,
                left: 2,
                width: 12,
                height: 4,
                background: '#fff',
                borderRadius: '2px 2px 0 0',
              }}
            />
            {/* Calendar rings */}
            <Box
              sx={{
                position: 'absolute',
                top: 0,
                left: 1,
                width: 2,
                height: 2,
                background: '#3498db',
                borderRadius: '50%',
              }}
            />
            <Box
              sx={{
                position: 'absolute',
                top: 0,
                right: 1,
                width: 2,
                height: 2,
                background: '#3498db',
                borderRadius: '50%',
              }}
            />
          </Box>
        </Box>
        {/* Title */}
        <Typography
          variant="h6"
          sx={{
            color: '#fff',
            fontWeight: 600,
            fontSize: 20,
            letterSpacing: 0.5,
          }}
        >
          {title}
        </Typography>
      </Box>

      {/* Right side - Action Buttons and Dark Mode Toggle */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        {showDarkModeToggle && (
          <DarkModeToggle darkMode={darkMode} onToggle={onToggleDarkMode} sx={{ position: 'static', top: 'unset', right: 'unset', zIndex: 1, ml: 1 }} />
        )}
        {showBackButton && (
          <IconButton
            onClick={handleBackClick}
            sx={{
              color: '#fff',
              bgcolor: 'rgba(255,255,255,0.1)',
              '&:hover': {
                bgcolor: 'rgba(255,255,255,0.2)',
              },
            }}
          >
            <ArrowBackIcon />
          </IconButton>
        )}
        {showHomeButton && (
          <IconButton
            onClick={handleHomeClick}
            sx={{
              color: '#fff',
              bgcolor: 'rgba(255,255,255,0.1)',
              '&:hover': {
                bgcolor: 'rgba(255,255,255,0.2)',
              },
            }}
          >
            <HomeIcon />
          </IconButton>
        )}
        {showMenuButton && (
          <IconButton
            onClick={handleMenuClick}
            sx={{
              color: '#fff',
              bgcolor: 'rgba(255,255,255,0.1)',
              '&:hover': {
                bgcolor: 'rgba(255,255,255,0.2)',
              },
            }}
          >
            <MenuIcon />
          </IconButton>
        )}
      </Box>
    </Box>
  );
};

export default Header; 