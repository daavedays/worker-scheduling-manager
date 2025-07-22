import React from 'react';
import { Box, Typography } from '@mui/material';

const Footer: React.FC = () => {
  const year = new Date().getFullYear();
  return (
    <Box sx={{ width: '100%', textAlign: 'center', py: 2, mt: 4, color: 'text.secondary', fontSize: 16, borderTop: '1px solid #ccc', opacity: 0.8, bgcolor: 'transparent' }}>
      © {year} David Mirzoyan. All rights reserved.
    </Box>
  );
};

export default Footer; 