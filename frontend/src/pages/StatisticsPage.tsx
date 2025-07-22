import React, { useState } from 'react';
import { Box, Typography, Paper } from '@mui/material';
import PageContainer from '../components/PageContainer';
import DarkModeToggle from '../components/DarkModeToggle';

function StatisticsPage({ darkMode, onToggleDarkMode }: { darkMode: boolean; onToggleDarkMode: () => void }) {
  const [soldiers, setSoldiers] = useState<{id: string, name: string}[]>([]);

  return (
    <PageContainer>
      <DarkModeToggle darkMode={darkMode} onToggle={onToggleDarkMode} />
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
    </PageContainer>
  );
}

export default StatisticsPage; 