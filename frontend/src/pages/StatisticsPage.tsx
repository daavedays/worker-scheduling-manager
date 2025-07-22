import React, { useState } from 'react';
import { Box, Typography, Paper } from '@mui/material';

function StatisticsPage() {
  const [soldiers, setSoldiers] = useState<{id: string, name: string}[]>([]);

  return (
    <Box sx={{ p: 4 }}>
      <Typography variant="h5" sx={{ mb: 2 }}>Statistics</Typography>
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6">X/Y Tasks per Soldier</Typography>
        <Typography>Chart/Table coming soon...</Typography>
      </Paper>
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6">Task Distribution Over Time</Typography>
        <Typography>Chart/Table coming soon...</Typography>
      </Paper>
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6">Fairness (Closings, Weekends, etc.)</Typography>
        <Typography>Chart/Table coming soon...</Typography>
      </Paper>
    </Box>
  );
}

export default StatisticsPage; 