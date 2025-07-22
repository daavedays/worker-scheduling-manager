import React from 'react';
import { Box } from '@mui/material';

interface PageContainerProps {
  children: React.ReactNode;
  sx?: object;
}

const PageContainer: React.FC<PageContainerProps> = ({ children, sx }) => (
  <Box
    sx={{
      p: { xs: 2, sm: 3, md: 4 },
      minHeight: '100vh',
      width: '100vw',
      background: 'none',
      position: 'relative',
      ...sx,
    }}
  >
    {children}
  </Box>
);

export default PageContainer; 