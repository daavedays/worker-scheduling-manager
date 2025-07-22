/**
 * YTaskPage.tsx
 * -------------
 * UI page for creating, editing, and viewing Y task schedules (secondary/support tasks).
 *
 * Renders:
 *   - Schedule selector (buttons for each saved Y schedule period)
 *   - Table/grid for Y task assignments (Y tasks as rows, dates as columns)
 *   - Date pickers for selecting new schedule period
 *   - Buttons for generating, saving, clearing, and hybrid generation
 *   - Dialogs for soldier assignment and schedule deletion
 *   - Snackbar notifications for save/delete actions
 *
 * State:
 *   - startDate, endDate: Date pickers for new schedule
 *   - mode: 'auto' | 'hybrid' | 'manual' (schedule generation mode)
 *   - grid: 2D array of assignments (Y tasks x dates)
 *   - dates: List of date strings (columns)
 *   - warnings: List of warning messages
 *   - loading, saving: UI loading states
 *   - pickerOpen, pickerCell: For soldier assignment dialog
 *   - availableSoldiers, selectedSchedule: List and selection of saved Y schedules
 *   - editMode: Whether editing an existing schedule
 *   - clearDialogOpen, deleteDialogOpen: Dialog states
 *   - scheduleToDelete, deleteError: For deletion
 *
 * Effects:
 *   - Loads available Y schedules on mount
 *   - Loads selected schedule's CSV and parses to grid on selection
 *
 * User Interactions:
 *   - Select/create/edit/clear Y schedules
 *   - Assign soldiers to Y tasks per day (with dialog)
 *   - Save or delete schedules
 *
 * Notes:
 *   - All API calls use fetch with credentials for session
 *   - Grid cells are color-coded by Y task
 *   - Inline comments explain non-obvious logic and UI structure
 */
import React, { useState, useEffect, useMemo } from 'react';
import { Box, Button, Typography, Fab, Snackbar, Alert as MuiAlert, Dialog, DialogTitle, DialogContent, DialogActions, List, ListItemButton, ListItemText, CircularProgress, IconButton } from '@mui/material';
import { DatePicker, LocalizationProvider } from '@mui/x-date-pickers';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import SaveIcon from '@mui/icons-material/Save';
import AutoFixHighIcon from '@mui/icons-material/AutoFixHigh';
import DeleteIcon from '@mui/icons-material/Delete';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import { formatDateDMY, shortWeekRange } from '../components/utils';
import { getWorkerColor, Y_TASK_COLORS } from '../components/colors';
import FadingBackground from '../components/FadingBackground';
import Footer from '../components/Footer';
import PageContainer from '../components/PageContainer';
import TableContainer from '../components/TableContainer';
import DarkModeToggle from '../components/DarkModeToggle';

function YTaskPage({ darkMode, onToggleDarkMode }: { darkMode: boolean; onToggleDarkMode: () => void }) {
  const Y_TASKS = [
    "Supervisor",
    "C&N Driver",
    "C&N Escort",
    "Southern Driver",
    "Southern Escort"
  ];
  const [startDate, setStartDate] = useState<Date | null>(null);
  const [endDate, setEndDate] = useState<Date | null>(null);
  const [mode, setMode] = useState('');
  const [grid, setGrid] = useState<string[][]>([]);
  const [dates, setDates] = useState<string[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [pickerCell, setPickerCell] = useState<{ y: number, d: number } | null>(null);
  const [availableSoldiers, setAvailableSoldiers] = useState<{id: string, name: string}[]>([]);
  const [pickerLoading, setPickerLoading] = useState(false);
  const [showBomb, setShowBomb] = useState(false);
  const [availableSchedules, setAvailableSchedules] = useState<any[]>([]);
  const [selectedSchedule, setSelectedSchedule] = useState<any | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [clearDialogOpen, setClearDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [scheduleToDelete, setScheduleToDelete] = useState<any | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [highlightCell, setHighlightCell] = useState<{row: number, col: number} | null>(null);
  const [resolveConflictInfo, setResolveConflictInfo] = useState<any | null>(null);
  const [showResolveWarning, setShowResolveWarning] = useState(false);

  // On mount, check for resolveConflict in localStorage
  useEffect(() => {
    const info = localStorage.getItem('resolveConflict');
    if (info) {
      try {
        const parsed = JSON.parse(info);
        setResolveConflictInfo(parsed);
        setHighlightCell({ row: parsed.yRow, col: parsed.yCol });
        setShowResolveWarning(true);
        // Optionally, scroll to the cell
        setTimeout(() => {
          const el = document.getElementById(`ycell-${parsed.yRow}-${parsed.yCol}`);
          if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });
        }, 500);
      } catch {}
    }
  }, []);

  // After user edits or dismisses, clear highlight and flag
  const handleResolveWarningClose = () => {
    setShowResolveWarning(false);
    setHighlightCell(null);
    setResolveConflictInfo(null);
    localStorage.removeItem('resolveConflict');
  };

  useEffect(() => {
    fetch('http://localhost:5000/api/y-tasks/list', { credentials: 'include' })
      .then(res => res.json())
      .then(data => setAvailableSchedules(data.schedules || []));
  }, []);

  useEffect(() => {
    if (!selectedSchedule) return;
    setLoading(true);
    setWarnings([]);
    fetch(`http://localhost:5000/api/y-tasks?start=${selectedSchedule.start}&end=${selectedSchedule.end}`, { credentials: 'include' })
      .then(res => res.text())
      .then(csv => {
        const rows = csv.split('\n').filter(Boolean).map(line => line.split(','));
        setDates(rows[0].slice(1));
        // Patch: replace all '-' with '' in the grid
        setGrid(
          rows.slice(1).map(r =>
            r.slice(1).map(cell => cell === '-' ? '' : cell)
          )
        );
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [selectedSchedule]);

  const handleGenerate = async () => {
    if (!startDate || !endDate) return;
    setLoading(true);
    setWarnings([]);
    const start = startDate.toLocaleDateString('en-GB').split('/').map((x: string) => x.padStart(2, '0')).join('/');
    const end = endDate.toLocaleDateString('en-GB').split('/').map((x: string) => x.padStart(2, '0')).join('/');
    const res = await fetch('http://localhost:5000/api/y-tasks/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ start, end, mode: 'auto' })
    });
    const data = await res.json();
    if (res.ok) {
      setGrid(data.grid);
      setDates(data.dates);
      setWarnings(data.warnings || []);
    } else {
      setWarnings([data.error || 'Failed to generate schedule']);
      setGrid([]);
      setDates([]);
    }
    setLoading(false);
  };

  const handleSave = async () => {
    setSaving(true);
    setSaveError(null);
    try {
      // Save as Y tasks (rows) x dates (columns)
      let csv = 'Y Task,' + dates.join(',') + '\n';
      for (let y = 0; y < Y_TASKS.length; ++y) {
        const row = [Y_TASKS[y], ...grid[y].map(s => s || '-')];
        csv += row.join(',') + '\n';
      }
      // Always use dd/mm/yyyy for start/end
      const getDMY = (d: Date | string | undefined | null) => {
        if (!d) return '';
        if (typeof d === 'string' && d.includes('/')) return d;
        if (d instanceof Date && !isNaN(d as any)) return d.toLocaleDateString('en-GB');
        return '';
      };
      const startDMY = getDMY(selectedSchedule?.start) || getDMY(startDate);
      const endDMY = getDMY(selectedSchedule?.end) || getDMY(endDate);
      const res = await fetch('http://localhost:5000/api/y-tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          start: startDMY,
          end: endDMY,
          csv,
        }),
      });
      if (!res.ok) throw new Error('Save failed');
      setSaveSuccess(true);
    } catch (e: any) {
      setSaveError(e.message || 'Failed to save Y tasks');
    } finally {
      setSaving(false);
    }
  };

  const handleEditSchedule = (sch: any) => {
    setSelectedSchedule(sch);
    setEditMode(true);
  };

  const handleClear = async () => {
    if (!selectedSchedule) return;
    setClearDialogOpen(false);
    await fetch('http://localhost:5000/api/y-tasks/clear', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ start: selectedSchedule.start, end: selectedSchedule.end })
    });
    fetch(`http://localhost:5000/api/y-tasks?start=${selectedSchedule.start}&end=${selectedSchedule.end}`, { credentials: 'include' })
      .then(res => res.text())
      .then(csv => {
        const rows = csv.split('\n').filter(Boolean).map(line => line.split(','));
        setDates(rows[0].slice(1));
        setGrid(rows.slice(1).map(r => r.slice(1)));
      });
  };

  const handleCellClick = async (y: number, d: number) => {
    setPickerCell({ y, d });
    setPickerOpen(true);
    setPickerLoading(true);
    const current_assignments: Record<string, Record<string, string>> = {};
    for (let yy = 0; yy < Y_TASKS.length; ++yy) {
      for (let dd = 0; dd < dates.length; ++dd) {
        const s = grid[yy]?.[dd];
        if (!s) continue;
        if (!current_assignments[s]) current_assignments[s] = {};
        current_assignments[s][dates[dd]] = Y_TASKS[yy];
      }
    }
    const res = await fetch('http://localhost:5000/api/y-tasks/available-soldiers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({
        date: dates[d],
        task: Y_TASKS[y],
        current_assignments,
      }),
    });
    const data = await res.json();
    setAvailableSoldiers(data.available || []);
    setPickerLoading(false);
  };

  const handleHybridGenerate = async () => {
    setShowBomb(true);
    setTimeout(() => setShowBomb(false), 1200);
    setLoading(true);
    setWarnings([]);
    const res = await fetch('http://localhost:5000/api/y-tasks/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({
        start: dates[0],
        end: dates[dates.length - 1],
        mode: 'hybrid',
        partial_grid: grid,
        y_tasks: Y_TASKS,
        dates,
      }),
    });
    const data = await res.json();
    if (res.ok && data.grid) {
      setGrid(prevGrid => prevGrid.map((row, yIdx) => row.map((cell, dIdx) => cell || data.grid[yIdx][dIdx])));
      setWarnings(data.warnings || []);
    } else {
      setWarnings([data.error || 'Failed to generate schedule']);
    }
    setLoading(false);
  };

  const handleRemoveYAssignment = () => {
    if (!pickerCell) return;
    setGrid(prev => {
      const copy = prev.map(r => [...r]);
      copy[pickerCell.y][pickerCell.d] = '';
      return copy;
    });
    setPickerOpen(false);
  };

  const handleDeleteSchedule = async () => {
    if (!scheduleToDelete) return;
    setDeleteDialogOpen(false);
    setDeleteError(null);
    try {
      const res = await fetch('http://localhost:5000/api/y-tasks/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ filename: scheduleToDelete.filename })
      });
      if (!res.ok) throw new Error('Delete failed');
      // Refresh schedule list
      fetch('http://localhost:5000/api/y-tasks/list', { credentials: 'include' })
        .then(res => res.json())
        .then(data => setAvailableSchedules(data.schedules || []));
      // If the deleted schedule was selected, clear selection
      if (selectedSchedule && selectedSchedule.filename === scheduleToDelete.filename) {
        setSelectedSchedule(null);
        setGrid([]);
        setDates([]);
      }
    } catch (e: any) {
      setDeleteError(e.message || 'Failed to delete schedule');
    }
  };

  const tableWidth = dates.length > 0 ? Math.max(900, 180 + dates.length * 120) : 900;
  const formattedStartDate = startDate ? formatDateDMY(startDate.toLocaleDateString('en-GB')) : '';
  const formattedEndDate = endDate ? formatDateDMY(endDate.toLocaleDateString('en-GB')) : '';

  return (
    <PageContainer>
      <FadingBackground />
      <DarkModeToggle darkMode={darkMode} onToggle={onToggleDarkMode} />
      <Box sx={{ width: '100%', overflowX: 'auto' }}>
        {/* Schedule Selector */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" sx={{ mb: 1 }}>Select Y Task Schedule</Typography>
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            {availableSchedules.map((sch: any) => (
              <Box key={sch.filename} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Button
                  variant={selectedSchedule && sch.filename === selectedSchedule.filename ? 'contained' : 'outlined'}
                  onClick={() => setSelectedSchedule(sch)}
                >
                  {formatDateDMY(sch.start)} TO {formatDateDMY(sch.end)}
                </Button>
                <IconButton
                  size="small"
                  color="error"
                  onClick={() => { setScheduleToDelete(sch); setDeleteDialogOpen(true); }}
                  sx={{ ml: 0.5 }}
                  aria-label="Delete schedule"
                >
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </Box>
            ))}
          </Box>
        </Box>
        {/* Delete confirmation dialog */}
        <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
          <DialogTitle>Delete Schedule</DialogTitle>
          <DialogContent>
            <Typography color="error" sx={{ mb: 2 }}>
              Warning: This will permanently delete the selected Y task schedule CSV file and remove it from the list. This action cannot be undone.
            </Typography>
            <Typography>
              Are you sure you want to delete the schedule for <b>{scheduleToDelete && formatDateDMY(scheduleToDelete.start)} to {scheduleToDelete && formatDateDMY(scheduleToDelete.end)}</b>?
            </Typography>
            {deleteError && <MuiAlert severity="error" sx={{ mt: 2 }}>{deleteError}</MuiAlert>}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
            <Button color="error" onClick={handleDeleteSchedule}>Delete</Button>
          </DialogActions>
        </Dialog>
        {grid.length > 0 && (
          <Box sx={{ width: '100%', display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 2, mb: 2 }}>
            <Fab
              color="info"
              onClick={handleHybridGenerate}
              disabled={loading}
              sx={{ width: 60, height: 60, boxShadow: 6, borderRadius: '50%', fontWeight: 700 }}
              aria-label="generate-rest"
            >
              <AutoFixHighIcon sx={{ fontSize: 28, color: '#fff' }} />
            </Fab>
            <Fab
              color="primary"
              onClick={handleSave}
              disabled={saving || grid.length === 0}
              sx={{ width: 60, height: 60, boxShadow: 6, borderRadius: '50%', fontWeight: 700 }}
              aria-label="save"
            >
              <SaveIcon sx={{ fontSize: 28, color: '#fff' }} />
            </Fab>
            <Button variant="outlined" color="error" onClick={() => setClearDialogOpen(true)} sx={{ height: 60 }}>Clear</Button>
          </Box>
        )}
        <Dialog open={clearDialogOpen} onClose={() => setClearDialogOpen(false)}>
          <DialogTitle>Clear Schedule</DialogTitle>
          <DialogContent>Are you sure you would like to clear the table?</DialogContent>
          <DialogActions>
            <Button onClick={() => setClearDialogOpen(false)}>Cancel</Button>
            <Button color="error" onClick={handleClear}>Clear</Button>
          </DialogActions>
        </Dialog>
        <Box sx={{ width: '100%', overflowX: 'auto' }}>
          <Box sx={{ minWidth: tableWidth, width: '100%' }}>
            <Box
              sx={{
                minWidth: tableWidth,
                width: '100%',
                background: darkMode ? '#1a2233' : '#eaf1fa',
                borderRadius: 3,
                boxShadow: darkMode ? 3 : '0 2px 12px 0 #b0bec522',
                border: darkMode ? undefined : '1.5px solid #b0bec5',
                p: 2,
                mb: 3,
                pt: 3,
                pb: 3,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'flex-start',
              }}
            >
              <Typography variant="h5" sx={{ mb: 2 }}>Y Task Assignment</Typography>
              <LocalizationProvider dateAdapter={AdapterDateFns}>
                <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                  <DatePicker
                    label="Start Date"
                    value={startDate}
                    onChange={(date: Date | null) => setStartDate(date)}
                    format="dd/MM/yyyy"
                    slotProps={{ textField: { sx: { minWidth: 180 } } }}
                  />
                  <DatePicker
                    label="End Date"
                    value={endDate}
                    onChange={(date: Date | null) => setEndDate(date)}
                    format="dd/MM/yyyy"
                    slotProps={{ textField: { sx: { minWidth: 180 } } }}
                  />
                </Box>
              </LocalizationProvider>
              <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
                <Button variant={mode === 'auto' ? 'contained' : 'outlined'} onClick={() => { setMode('auto'); handleGenerate(); }} disabled={!startDate || !endDate || loading}>Automatic</Button>
                <Button
                  variant={mode === 'hybrid' ? 'contained' : 'outlined'}
                  onClick={() => {
                    setMode('hybrid');
                    if (startDate && endDate) {
                      const start = startDate;
                      const end = endDate;
                      const days = [];
                      let d = new Date(start);
                      while (d <= end) {
                        days.push(d.toLocaleDateString('en-GB').split('/').map(x => x.padStart(2, '0')).join('/'));
                        d.setDate(d.getDate() + 1);
                      }
                      setDates(days);
                      setGrid(Array(Y_TASKS.length).fill(0).map(() => Array(days.length).fill('')));
                      setWarnings([]);
                    }
                  }}
                  disabled={!startDate || !endDate || loading}
                >
                  Set Preferences
                </Button>
                <Button variant={mode === 'manual' ? 'contained' : 'outlined'} sx={{ display: 'none' }}>Manual</Button>
                <Button variant={mode === 'hybrid' ? 'contained' : 'outlined'} disabled sx={{ display: 'none' }}>Hybrid</Button>
              </Box>
            </Box>
            {warnings.length > 0 && (
              <MuiAlert severity="warning" sx={{ mb: 2 }}>
                <ul style={{ margin: 0, paddingLeft: 20 }}>
                  {warnings.map((w: string, i: number) => <li key={i}>{w}</li>)}
                </ul>
              </MuiAlert>
            )}
            {grid.length > 0 && (
              <TableContainer>
                <Box
                  component="table"
                  sx={{
                    minWidth: tableWidth,
                    width: '100%',
                    borderCollapse: 'separate',
                    borderSpacing: 0,
                    background: darkMode ? '#1a2233' : '#eaf1fa',
                    borderRadius: 4,
                    boxShadow: darkMode ? '0 6px 32px 0 rgba(30,58,92,0.13)' : '0 2px 12px 0 #b0bec522',
                    border: darkMode ? undefined : '1.5px solid #b0bec5',
                    overflow: 'hidden',
                    pt: 2,
                    pb: 2,
                  }}
                >
                  <thead>
                    <tr>
                      <th
                        style={{
                          minWidth: 160,
                          background: darkMode ? '#22304a' : '#e3f2fd',
                          color: darkMode ? '#fff' : '#1e3a5c',
                          fontWeight: 700,
                          fontSize: 18,
                          position: 'sticky',
                          left: 0,
                          zIndex: 2,
                          boxShadow: '0 2px 8px rgba(30,58,92,0.08)',
                          borderBottom: '3px solid #ff9800',
                          borderRight: darkMode ? '2px solid #b0bec5' : '2px solid #888',
                          height: 60,
                          letterSpacing: 1,
                        }}
                      >
                        שם
                      </th>
                      {dates.map((date: string, i: number) => (
                        <th
                          key={i}
                          style={{
                            minWidth: 120,
                            background: darkMode ? '#1e3a5c' : '#1e3a5c',
                            color: '#fff',
                            fontWeight: 700,
                            fontSize: 16,
                            borderBottom: '3px solid #ff9800',
                            height: 60,
                            boxShadow: '0 2px 8px rgba(30,58,92,0.06)',
                            borderRight: darkMode ? '2px solid #b0bec5' : '2px solid #888',
                          }}
                        >
                          {formatDateDMY(date)}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {Y_TASKS.map((yTask: string, rIdx: number) => (
                      <tr key={rIdx} style={{ background: rIdx % 2 === 0 ? (darkMode ? '#232a36' : '#f9fafb') : (darkMode ? '#181c23' : '#fff') }}>
                        <td
                          style={{
                            background: darkMode ? '#22304a' : '#dbeafe',
                            color: darkMode ? '#fff' : '#1e3a5c',
                            fontWeight: 600,
                            position: 'sticky',
                            left: 0,
                            zIndex: 1,
                            fontSize: 18,
                            borderRight: darkMode ? '3.5px solid #b0bec5' : '3.5px solid #666',
                            borderBottom: darkMode ? '2px solid #b0bec5' : '2px solid #888',
                            height: 56,
                            paddingLeft: 32,
                            paddingRight: 16,
                            minWidth: 180,
                            boxShadow: darkMode ? undefined : '2px 0 8px -4px #8882',
                          }}
                        >
                          {yTask}
                        </td>
                        {grid[rIdx]?.map((soldier: string, cIdx: number) => (
                          <td
                            key={cIdx}
                            id={`ycell-${rIdx}-${cIdx}`}
                            style={{
                              background: soldier
                                ? (Y_TASK_COLORS[yTask]?.[darkMode ? 'dark' : 'light'] || (darkMode ? '#333' : '#f7f9fb'))
                                : (darkMode ? '#1a2233' : '#f7f9fb'),
                              color: '#fff',
                              textShadow: '0 1px 4px #000a',
                              textAlign: 'center',
                              fontWeight: 600,
                              minWidth: 120,
                              border: darkMode ? '2px solid #b0bec5' : '2px solid #888',
                              borderRadius: 8,
                              fontSize: 18,
                              height: 56,
                              boxSizing: 'border-box',
                              transition: 'background 0.2s',
                              cursor: 'pointer',
                              boxShadow: soldier ? '0 1px 4px rgba(30,58,92,0.06)' : undefined,
                              opacity: soldier ? 1 : 0.6,
                              outline: highlightCell && highlightCell.row === rIdx && highlightCell.col === cIdx ? '4px solid #ff1744' : undefined,
                              animation: highlightCell && highlightCell.row === rIdx && highlightCell.col === cIdx ? 'blink-border 0.7s alternate infinite' : undefined,
                            }}
                            onClick={() => handleCellClick(rIdx, cIdx)}
                            onMouseOver={e => { (e.currentTarget as HTMLElement).style.background = '#ffe082'; }}
                            onMouseOut={e => { (e.currentTarget as HTMLElement).style.background = soldier
                              ? (Y_TASK_COLORS[yTask]?.[darkMode ? 'dark' : 'light'] || (darkMode ? '#333' : '#f7f9fb'))
                              : (darkMode ? '#1a2233' : '#f7f9fb'); }}
                          >
                            {soldier}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </Box>
                <Dialog open={pickerOpen} onClose={() => setPickerOpen(false)}>
                  <DialogTitle>Assign Soldier</DialogTitle>
                  <DialogContent>
                    {pickerLoading ? <CircularProgress /> : (
                      <List>
                        {availableSoldiers.map(s => (
                          <ListItemButton key={s.id} onClick={() => {
                            setGrid(prev => {
                              const copy = prev.map(r => [...r]);
                              if (pickerCell) copy[pickerCell.y][pickerCell.d] = s.name;
                              return copy;
                            });
                            setPickerOpen(false);
                          }}>
                            <ListItemText primary={s.name} />
                          </ListItemButton>
                        ))}
                        {availableSoldiers.length === 0 && <Typography>No available soldiers</Typography>}
                        {pickerCell && grid[pickerCell.y][pickerCell.d] && (
                          <ListItemButton onClick={handleRemoveYAssignment} sx={{ color: 'error.main', mt: 1 }}>
                            <DeleteIcon sx={{ mr: 1 }} />
                            <ListItemText primary="Remove Assignment" />
                          </ListItemButton>
                        )}
                      </List>
                    )}
                  </DialogContent>
                  <DialogActions>
                    <Button onClick={() => setPickerOpen(false)}>Cancel</Button>
                  </DialogActions>
                </Dialog>
              </TableContainer>
            )}
          </Box>
        </Box>
        <Snackbar open={saveSuccess} autoHideDuration={3000} onClose={() => setSaveSuccess(false)} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
          <MuiAlert onClose={() => setSaveSuccess(false)} severity="success" sx={{ width: '100%' }}>
            Y tasks saved successfully!
          </MuiAlert>
        </Snackbar>
        <Snackbar open={!!saveError} autoHideDuration={4000} onClose={() => setSaveError(null)} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
          <MuiAlert onClose={() => setSaveError(null)} severity="error" sx={{ width: '100%' }}>
            {saveError}
          </MuiAlert>
        </Snackbar>
        <Snackbar open={showResolveWarning} autoHideDuration={10000} onClose={handleResolveWarningClose} anchorOrigin={{ vertical: 'top', horizontal: 'center' }}>
          <MuiAlert onClose={handleResolveWarningClose} severity="warning" sx={{ width: '100%' }} icon={<WarningAmberIcon />}>
            <strong>Conflict: X/Y Task Overlap</strong><br />
            {resolveConflictInfo && (
              <>
                <b>{resolveConflictInfo.soldier}</b> is assigned to <b>Y: {resolveConflictInfo.yTask}</b> and <b>X: {resolveConflictInfo.xTask}</b> on <b>{resolveConflictInfo.date}</b>.<br />
                Please update the highlighted cell in the Y schedule for <b>{resolveConflictInfo.date}</b>.
              </>
            )}
          </MuiAlert>
        </Snackbar>
      </Box>
      <Footer />
    </PageContainer>
  );
}

export default YTaskPage; 