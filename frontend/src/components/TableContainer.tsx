import React from 'react';
import { Box } from '@mui/material';

interface TableContainerProps {
  children: React.ReactNode;
  sx?: object;
}

const TableContainer: React.FC<TableContainerProps> = ({ children, sx }) => (
  <Box
    sx={{
      width: '100%',
      overflowX: 'auto',
      background: theme => theme.palette.mode === 'dark' ? '#1a2233' : '#eaf1fa',
      borderRadius: 4,
      boxShadow: theme => theme.palette.mode === 'dark' ? 3 : '0 2px 12px 0 #b0bec522',
      border: theme => theme.palette.mode === 'dark' ? undefined : '1.5px solid #b0bec5',
      p: 2,
      mb: 3,
      ...sx,
    }}
  >
    {children}
  </Box>
);

export default TableContainer; 