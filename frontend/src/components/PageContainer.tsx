import React from 'react';
import { Box } from '@mui/material';

interface PageContainerProps {
  children: React.ReactNode;
  sx?: object;
}

const PageContainer: React.FC<PageContainerProps> = ({ children, sx }) => (
  <Box
    sx={{
      pt: { xs: 10, sm: 11, md: 12 }, // Add top padding for header
      px: { xs: 2, sm: 3, md: 4 },
      pb: { xs: 2, sm: 3, md: 4 },
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