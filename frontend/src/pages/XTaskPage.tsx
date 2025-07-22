/**
 * XTaskPage.tsx
 * -------------
 * UI page for creating, editing, and viewing X task schedules (main/primary tasks).
 *
 * Renders:
 *   - Table/grid for X task assignments (soldiers as rows, weeks as columns)
 *   - Floating action buttons for navigation and saving
 *   - Dialog for assigning tasks (standard/custom) to soldiers per week
 *   - Snackbar notifications for save/conflict actions
 *
 * State:
 *   - data: Original CSV data (2D array)
 *   - headers, subheaders: Table headers (weeks, date ranges)
 *   - editData: Editable grid of assignments
 *   - customTasks: Custom X task assignments per soldier
 *   - conflicts: Map of X/Y conflicts for highlighting
 *   - modal, modalTask, modalOther: For task assignment dialog
 *   - loading, saving, error: UI states
 *   - saveSuccess, conflictWarning: Snackbar states
 *
 * Effects:
 *   - Loads X task CSV and custom tasks on mount or when year/period changes
 *   - Loads X/Y conflicts for highlighting
 *
 * User Interactions:
 *   - Assign standard/custom tasks to soldiers per week
 *   - Remove assignments
 *   - Save schedule
 *   - See conflict warnings
 *
 * Notes:
 *   - Table cells are color-coded by task type
 *   - Custom tasks show date range in cell
 *   - Inline comments explain non-obvious logic and UI structure
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useLocation, useParams, useNavigate } from 'react-router-dom';
import Papa from 'papaparse';
import { Box, Fab, Dialog, DialogTitle, DialogContent, DialogActions, List, ListItem, ListItemButton, ListItemText, TextField, Typography, Snackbar, Button } from '@mui/material';
import MuiAlert from '@mui/material/Alert';
import SaveIcon from '@mui/icons-material/Save';
import DeleteIcon from '@mui/icons-material/Delete';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import Tooltip from '@mui/material/Tooltip';
import { DatePicker, LocalizationProvider } from '@mui/x-date-pickers';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import { shortWeekRange } from '../components/utils';
import FadingBackground from '../components/FadingBackground';
import Footer from '../components/Footer';
import { getWorkerColor, getXTaskColor } from '../components/colors';
import PageContainer from '../components/PageContainer';
import TableContainer from '../components/TableContainer';
import DarkModeToggle from '../components/DarkModeToggle';

const STANDARD_X_TASKS = ["Guarding Duties", "RASAR", "Kitchen"];
const MAX_CUSTOM_TASK_LEN = 14;

function XTaskPage({ darkMode, onToggleDarkMode }: { darkMode: boolean; onToggleDarkMode: () => void }) {
  const { mode } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const query = new URLSearchParams(location.search);
  const yearParam = parseInt(query.get('year') || '') || new Date().getFullYear();
  const periodParam = parseInt(query.get('period') || '') || 1;
  const [data, setData] = useState<string[][]>([]);
  const [headers, setHeaders] = useState<string[]>([]);
  const [subheaders, setSubheaders] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editData, setEditData] = useState<string[][]>([]);
  const [conflicts, setConflicts] = useState<{[key: string]: {x_task: string, y_task: string}}>({});
  const [customTasks, setCustomTasks] = useState<any>({});
  const [modal, setModal] = useState<{open: boolean, row: number, col: number, weekLabel: string, weekRange: string, soldier: string}>({open: false, row: -1, col: -1, weekLabel: '', weekRange: '', soldier: ''});
  const [modalTask, setModalTask] = useState<string>('');
  const [modalOther, setModalOther] = useState<{name: string, range: [Date | null, Date | null]}>({name: '', range: [null, null]});
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [customTaskWarning, setCustomTaskWarning] = useState('');
  const [conflictWarning, setConflictWarning] = useState(false);
  const [conflictDetails, setConflictDetails] = useState<any[]>([]); // Store conflict details for popup
  const [blinkCells, setBlinkCells] = useState<{[key: string]: boolean}>({}); // Track blinking cells
  const [pendingConflict, setPendingConflict] = useState<any | null>(null); // Track unresolved conflict
  const [showResolveBtn, setShowResolveBtn] = useState(false);
  const [soldiers, setSoldiers] = useState<{id: string, name: string}[]>([]);

  function renderCell(cell: string, colIdx: number, rowIdx: number) {
    // Use a slightly lighter blue for empty cells
    let bg = cell && cell.trim() !== '' && cell !== '-' ? getXTaskColor(cell.split('\n')[0]) : (darkMode ? '#26324a' : '#eaf1fa');
    let color = darkMode ? '#fff' : '#1e3a5c';
    let task = cell.split('\n')[0];
    let isCustom = false;
    let dateRange = '';
    if (cell && cell.trim() !== '' && cell !== '-') {
      if (cell.includes('\n(')) {
        isCustom = true;
        task = cell.split('\n')[0];
        dateRange = '';
        bg = getXTaskColor('Custom');
      } else {
        bg = getXTaskColor(task);
      }
    }
    let isConflict = false;
    let conflictInfo: {x_task: string, y_task: string} | undefined = undefined;
    let shouldBlink = false;
    if (conflicts && colIdx > 0 && editData[rowIdx] && editData[rowIdx][0]) {
      const soldier = editData[rowIdx][0];
      const date = headers[colIdx];
      const key = `${soldier}|${date}`;
      if (conflicts[key]) {
        isConflict = true;
        conflictInfo = conflicts[key];
        shouldBlink = blinkCells[key];
      }
    }
    const cellContent = (
      <div style={{
        width: '100%',
        height: '100%',
        background: isConflict ? '#ffbdbd' : bg,
        color,
        borderRadius: 8,
        padding: '4px 6px',
        fontWeight: 700,
        fontSize: 18,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: 44,
        boxSizing: 'border-box',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
        border: isConflict ? (shouldBlink ? '3.5px solid #ff1744' : '2.5px solid #ff1744') : `2px solid ${darkMode ? '#b0bec5' : '#888'}`,
        boxShadow: cell && cell.trim() !== '' && cell !== '-' ? '0 1px 4px rgba(30,58,92,0.10)' : undefined,
        textShadow: cell && cell.trim() !== '' && cell !== '-' ? '0 1px 4px #000a' : undefined,
        transition: shouldBlink ? 'box-shadow 0.2s, border 0.2s, background 0.2s' : 'box-shadow 0.2s, border 0.2s',
        animation: shouldBlink ? 'blink-border 0.5s alternate 6' : undefined,
        cursor: isConflict ? 'pointer' : 'default',
        opacity: cell && cell.trim() !== '' && cell !== '-' ? 1 : 0.85,
      }}>
        <span style={{
          fontSize: isCustom ? 15 : 18,
          fontWeight: 700,
          maxWidth: 120,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}>{task.length > MAX_CUSTOM_TASK_LEN ? task.slice(0, MAX_CUSTOM_TASK_LEN) + '…' : task}</span>
        {/* No date range for custom tasks on X Tasks page */}
      </div>
    );
    if (isConflict && conflictInfo) {
      return (
        <Tooltip
          title={`Conflict: ${editData[rowIdx][0]} has both X task (${conflictInfo.x_task}) and Y task (${conflictInfo.y_task}) on ${headers[colIdx]}. Please adjust the Y schedule for this date.`}
          arrow
          placement="top"
        >
          {cellContent}
        </Tooltip>
      );
    }
    return cellContent;
  }

  function isCellFilled(cell: string) {
    return cell && cell !== '-';
  }

  const handleRemoveAssignment = () => {
    const { row, col, soldier } = modal;
    const cellValue = editData[row][col];
    if (cellValue.includes('\n(')) {
      const match = cellValue.match(/(.+)\n\((\d{2}\/\d{2}\/\d{4})-(\d{2}\/\d{2}\/\d{4})\)/);
      if (match) {
        const [, taskName, start, end] = match;
        setCustomTasks((prev: any) => {
          const updated = { ...prev };
          if (updated[soldier]) {
            updated[soldier] = updated[soldier].filter((t: any) => !(t.task === taskName && t.start === start && t.end === end));
            if (updated[soldier].length === 0) delete updated[soldier];
          }
          return updated;
        });
        setEditData(prev => {
          const copy = prev.map(r => [...r]);
          for (let c = 1; c < headers.length; ++c) {
            if (copy[row][c] === cellValue) copy[row][c] = '';
          }
          return copy;
        });
      }
    } else {
      setEditData(prev => {
        const copy = prev.map(r => [...r]);
        copy[row][col] = '';
        return copy;
      });
    }
    setModal(m => ({ ...m, open: false }));
  };

  useEffect(() => {
    setLoading(true);
    fetch(`http://localhost:5000/api/x-tasks?year=${yearParam}&period=${periodParam}`, { credentials: 'include' })
      .then(res => res.json())
      .then(({ csv, custom_tasks }) => {
        const parsed = Papa.parse<string[]>(csv, { skipEmptyLines: false });
        setHeaders(parsed.data[0] as string[]);
        setSubheaders(parsed.data[1] as string[]);
        setData(parsed.data.slice(2) as string[][]);
        setEditData(parsed.data.slice(2) as string[][]);
        setCustomTasks(custom_tasks || {});
        setLoading(false);
        fetchConflicts();
      })
      .catch(() => { setError('Failed to load X tasks'); setLoading(false); });
  }, [yearParam, periodParam]);

  const fetchConflicts = useCallback(() => {
    return fetch(`http://localhost:5000/api/x-tasks/conflicts?year=${yearParam}&period=${periodParam}`, { credentials: 'include' })
      .then(res => res.json())
      .then(data => {
        const map: {[key: string]: {x_task: string, y_task: string}} = {};
        const blink: {[key: string]: boolean} = {};
        (data.conflicts || []).forEach((c: any) => {
          map[`${c.soldier}|${c.date}`] = { x_task: c.x_task, y_task: c.y_task };
          blink[`${c.soldier}|${c.date}`] = true;
        });
        setConflicts(map);
        setConflictDetails(data.conflicts || []);
        setBlinkCells(blink);
        setConflictWarning((data.conflicts || []).length > 0);
        // Remove blinking after 3s
        setTimeout(() => setBlinkCells({}), 3000);
        return (data.conflicts || []).length;
      });
  }, [yearParam, periodParam]);

  const handleCellChange = (row: number, col: number, value: string) => {
    setEditData(prev => {
      const copy = prev.map(r => [...r]);
      copy[row][col] = value;
      return copy;
    });
  };

  const handleCellClick = (row: number, col: number) => {
    setModal({
      open: true,
      row,
      col,
      weekLabel: headers[col],
      weekRange: subheaders[col],
      soldier: editData[row][0],
    });
    setModalTask('');
    setModalOther({name: '', range: [null, null]});
  };

  // Helper to parse dd/mm and infer year for week start/end
  function parseDMWithYear(dm: string, weekIdx: number, weeks: {start: Date, end: Date}[]): Date | null {
    // Use the actual week start/end year from the weeks array
    if (!dm) return null;
    const [d, m] = dm.split('/');
    if (!d || !m) return null;
    // For week start, use weeks[weekIdx].start; for week end, use weeks[weekIdx].end
    // If weekIdx is out of bounds, fallback to current year
    let y = new Date().getFullYear();
    if (weeks && weeks[weekIdx]) {
      // If this is the first date in the subheader, it's the week start
      // If this is the second date, it's the week end
      // We'll infer based on the column index
      // If dm matches the week start, use weeks[weekIdx].start.getFullYear()
      // If dm matches the week end, use weeks[weekIdx].end.getFullYear()
      // We'll check both
      if (dm === weeks[weekIdx].start.toLocaleDateString('en-GB', { day: '2-digit', month: '2-digit' })) {
        y = weeks[weekIdx].start.getFullYear();
      } else if (dm === weeks[weekIdx].end.toLocaleDateString('en-GB', { day: '2-digit', month: '2-digit' })) {
        y = weeks[weekIdx].end.getFullYear();
      }
    }
    return new Date(Number(y), Number(m) - 1, Number(d));
  }

  const handleModalSave = () => {
    if (modalTask === 'Other') {
      if (!modalOther.name || !modalOther.range[0] || !modalOther.range[1]) return;
      if (modalOther.name.length > MAX_CUSTOM_TASK_LEN) {
        setCustomTaskWarning(`Custom task name must be at most ${MAX_CUSTOM_TASK_LEN} characters.`);
        return;
      }
      setCustomTaskWarning('');
      const s = modal.soldier;
      const newCustom = {...customTasks};
      if (!newCustom[s]) newCustom[s] = [];
      newCustom[s].push({
        task: modalOther.name,
        start: formatDateDMY(modalOther.range[0]),
        end: formatDateDMY(modalOther.range[1]),
      });
      setCustomTasks(newCustom);
      // Build weeks array for correct year inference
      const weeksArr = headers.slice(2).map((h, i) => {
        const [startDM, endDM] = (subheaders[i+2] || '').split(' - ');
        // Use yearParam and handle year rollover for endDM
        let startYear = yearParam;
        let endYear = yearParam;
        if (i > 0 && startDM && endDM) {
          // If endDM month is January and startDM is December, increment year
          const [endD, endM] = endDM.split('/').map(Number);
          const [startD, startM] = startDM.split('/').map(Number);
          if (startM === 12 && endM === 1) {
            endYear = yearParam + 1;
          }
        }
        const weekStart = new Date(startYear, Number(startDM.split('/')[1]) - 1, Number(startDM.split('/')[0]));
        const weekEnd = new Date(endYear, Number(endDM.split('/')[1]) - 1, Number(endDM.split('/')[0]));
        return { start: weekStart, end: weekEnd };
      });
      setEditData(prev => {
        const copy = prev.map(r => [...r]);
        for (let c = 1; c < headers.length; ++c) {
          const [start, end] = (subheaders[c] || '').split(' - ');
          if (!start || !end) continue;
          // Use the new helper to get correct years
          const weekStart = parseDMWithYear(start, c-2, weeksArr);
          const weekEnd = parseDMWithYear(end, c-2, weeksArr);
          if (!weekStart || !weekEnd) continue;
          if (modalOther.range[0]! <= weekEnd && modalOther.range[1]! >= weekStart) {
            copy[modal.row][c] = `${modalOther.name}\n(${formatDateDMY(modalOther.range[0]!)}-${formatDateDMY(modalOther.range[1]!)})`;
          }
        }
        return copy;
      });
    } else if (modalTask) {
      setEditData(prev => {
        const copy = prev.map(r => [...r]);
        copy[modal.row][modal.col] = modalTask;
        return copy;
      });
    }
    setModal(m => ({...m, open: false}));
  };

  function formatDateDMY(date: Date): string {
    const d = date.getDate().toString().padStart(2, '0');
    const m = (date.getMonth() + 1).toString().padStart(2, '0');
    const y = date.getFullYear().toString();
    return `${d}/${m}/${y}`;
  }
  function parseDM(dm: string, yearHeader: string): Date | null {
    const [d, m] = dm.split('/');
    const y = new Date().getFullYear();
    try {
      return new Date(Number(y), Number(m) - 1, Number(d));
    } catch {
      return null;
    }
  }

  // Helper to check for conflicts for a single cell
  async function checkCellConflict(soldier: string, date: string, xTask: string) {
    // 1. Fetch y_tasks.json to get all Y schedule periods
    const yIndexRes = await fetch('http://localhost:5000/data/y_tasks.json', { credentials: 'include' });
    const yIndex = await yIndexRes.json();
    // 2. For each period, check if date is in range
    for (const key in yIndex) {
      const [start, end] = key.split('_to_');
      const d0 = parseDMY(start);
      const d1 = parseDMY(end);
      const d = parseDMY(date);
      if (!d0 || !d1 || !d) continue;
      if (d >= d0 && d <= d1) {
        // 3. Load the Y schedule CSV for this period
        const yCsvRes = await fetch(`http://localhost:5000/data/${yIndex[key]}`, { credentials: 'include' });
        const yCsv = await yCsvRes.text();
        const rows = yCsv.split('\n').filter(Boolean).map(line => line.split(','));
        const yDates = rows[0].slice(1);
        const yIdx = yDates.indexOf(date);
        if (yIdx === -1) continue;
        for (let r = 1; r < rows.length; ++r) {
          if (rows[r][yIdx + 1] === soldier) {
            // Conflict found
            return {
              soldier,
              date,
              xTask,
              yTask: rows[r][0],
              yPeriod: { start, end, filename: yIndex[key] },
              yRow: r - 1,
              yCol: yIdx
            };
          }
        }
      }
    }
    return null;
  }
  function parseDMY(d: string) {
    const [day, month, year] = d.split('/').map(Number);
    return new Date(year, month - 1, day);
  }

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setShowResolveBtn(false);
    setPendingConflict(null);
    try {
      const csv = Papa.unparse([headers, subheaders, ...editData]);
      const res = await fetch('http://localhost:5000/api/x-tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ csv, custom_tasks: customTasks, year: yearParam, half: periodParam }),
      });
      if (!res.ok) throw new Error('Save failed');
      setSaveSuccess(true);
      // After saving, check for conflicts for changed cells only
      // For demo: check all filled cells (could optimize to only changed)
      let foundConflict = null;
      for (let r = 0; r < editData.length; ++r) {
        for (let c = 1; c < headers.length; ++c) {
          const soldier = editData[r][0];
          const cell = editData[r][c];
          const date = subheaders[c];
          if (soldier && cell && cell !== '-') {
            const conflict = await checkCellConflict(soldier, date, cell);
            if (conflict) {
              foundConflict = conflict;
              break;
            }
          }
        }
        if (foundConflict) break;
      }
      if (foundConflict) {
        setPendingConflict(foundConflict);
        setShowResolveBtn(true);
        setConflictWarning(true);
        setConflictDetails([foundConflict]);
        setBlinkCells({ [`${foundConflict.soldier}|${foundConflict.date}`]: true });
        setTimeout(() => setBlinkCells({}), 3000);
      } else {
        setShowResolveBtn(false);
        setPendingConflict(null);
      }
      // Fetch conflicts for highlighting
      fetch(`http://localhost:5000/api/x-tasks/conflicts?year=${yearParam}&period=${periodParam}`, { credentials: 'include' })
        .then(res => res.json())
        .then(data => {
          const map: {[key: string]: {x_task: string, y_task: string}} = {};
          const blink: {[key: string]: boolean} = {};
          (data.conflicts || []).forEach((c: any) => {
            map[`${c.soldier}|${c.date}`] = { x_task: c.x_task, y_task: c.y_task };
            blink[`${c.soldier}|${c.date}`] = true;
          });
          setConflicts(map);
          setConflictDetails(data.conflicts || []);
          setBlinkCells(blink);
          setConflictWarning((data.conflicts || []).length > 0);
          // Remove blinking after 3s
          setTimeout(() => setBlinkCells({}), 3000);
        });
    } catch (e) {
      setError('An error occurred');
    } finally {
      setSaving(false);
    }
  };

  return (
    <PageContainer>
      <FadingBackground />
      <DarkModeToggle darkMode={darkMode} onToggle={onToggleDarkMode} />
      <Box sx={{ minWidth: 900, position: 'relative' }}>
        {/* Floating Navigation FAB in the top left */}
        <Fab
          color="secondary"
          onClick={() => navigate('/dashboard')}
          sx={{
            position: 'fixed',
            top: 100,
            left: 32,
            zIndex: 1200,
            width: 60,
            height: 60,
            boxShadow: 6,
            borderRadius: '50%',
            fontWeight: 700,
          }}
          aria-label="back"
        >
          <ArrowBackIcon sx={{ fontSize: 28, color: '#fff' }} />
        </Fab>
        {/* Floating Save FAB in the top right, like Y Tasks page */}
        <Fab
          color="primary"
          onClick={handleSave}
          sx={{
            position: 'fixed',
            top: 100,
            right: showResolveBtn ? 112 : 32,
            zIndex: 1200,
            width: 60,
            height: 60,
            boxShadow: 6,
            borderRadius: '50%',
            fontWeight: 700,
          }}
          aria-label="save"
        >
          <SaveIcon sx={{ fontSize: 28, color: '#fff' }} />
        </Fab>
        {showResolveBtn && pendingConflict && (
          <Fab
            color="error"
            onClick={() => {
              localStorage.setItem('resolveConflict', JSON.stringify(pendingConflict));
              navigate('/y-tasks');
            }}
            sx={{
              position: 'fixed',
              top: 100,
              right: 32,
              zIndex: 1200,
              width: 60,
              height: 60,
              boxShadow: 6,
              borderRadius: '50%',
              fontWeight: 700,
              animation: 'blink-border 1s alternate infinite',
            }}
            aria-label="resolve-conflict"
            title="Resolve Conflict"
          >
            <WarningAmberIcon sx={{ fontSize: 32, color: '#fff' }} />
          </Fab>
        )}
        <TableContainer>
          <Box component="table" sx={{ width: '100%', borderCollapse: 'separate', borderSpacing: 0, minWidth: 900, background: 'none', borderRadius: 2, boxShadow: 3 }}>
            <thead>
              <tr style={{ marginBottom: '100px' }}>
                <th style={{
                  minWidth: 160,
                  fontWeight: 700,
                  fontSize: 18,
                  background: darkMode ? '#22304a' : '#e3f2fd',
                  color: darkMode ? '#fff' : '#1e3a5c',
                  borderTopLeftRadius: 8,
                  position: 'sticky',
                  left: 0,
                  zIndex: 3,
                  top: 0,
                  borderLeft: `3px solid ${darkMode ? '#3b4252' : '#b0bec5'}`,
                  paddingLeft: 16,
                  borderRight: `1.5px solid ${darkMode ? '#3b4252' : '#b0bec5'}`,
                  borderBottom: `2px solid ${darkMode ? '#2c3550' : '#b0bec5'}`,
                  backgroundClip: 'padding-box',
                }}>שם</th>
                {headers.slice(2).map((h, i) => (
                  <th key={i} style={{
                    textAlign: 'center',
                    padding: 8,
                    background: '#1e3a5c',
                    color: '#fff',
                    fontWeight: 700,
                    fontSize: 16,
                    position: 'sticky',
                    top: 0,
                    zIndex: 2,
                    minWidth: 120,
                    maxWidth: 160,
                    whiteSpace: 'nowrap',
                    borderBottom: `2px solid ${darkMode ? '#2c3550' : '#b0bec5'}`,
                    backgroundClip: 'padding-box',
                  }}>
                    <div>{h}</div>
                    <div style={{ fontSize: 12, color: '#ff9800', marginTop: 2 }}>{shortWeekRange(subheaders[i+2])}</div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {editData.map((row, rIdx) => {
                // Only render rows with a valid Hebrew name (row[1])
                if (!row[1] || row[1].includes('/')) return null;
                const soldierName = (row[1] || '').trim();
                const rowCells = row.slice(2); // skip id and name
                const numCells = headers.length - 2;
                const paddedCells = rowCells.length < numCells ? [...rowCells, ...Array(numCells - rowCells.length).fill('')] : rowCells;
                return (
                  <tr key={rIdx}>
                    <td style={{
                      fontWeight: 600,
                      background: darkMode ? '#22304a' : '#e3f2fd',
                      color: darkMode ? '#fff' : '#1e3a5c',
                      minWidth: 160,
                      position: 'sticky',
                      left: 0,
                      zIndex: 1,
                      borderLeft: `3px solid ${darkMode ? '#3b4252' : '#b0bec5'}`,
                      paddingLeft: 16,
                      borderRight: `1.5px solid ${darkMode ? '#3b4252' : '#b0bec5'}`,
                      borderBottom: `1.5px solid ${darkMode ? '#2c3550' : '#b0bec5'}`,
                      backgroundClip: 'padding-box',
                    }}>{soldierName}</td>
                    {paddedCells.map((cell, cIdx) => {
                      const colIdx = cIdx + 2;
                      const isFilled = cell && cell.trim() !== '' && cell !== '-';
                      return (
                        <td
                          key={colIdx}
                          style={{
                            background: isFilled
                              ? getXTaskColor(cell.split('\n')[0])
                              : (darkMode ? '#1a2233' : '#f7f9fb'),
                            color: '#fff',
                            textShadow: '0 1px 4px #000a',
                            textAlign: 'center',
                            fontWeight: 600,
                            minWidth: 120,
                            border: darkMode ? '2px solid #232a36' : '2px solid rgba(176,190,197,0.35)',
                            borderRadius: 8,
                            fontSize: 18,
                            height: 56,
                            boxSizing: 'border-box',
                            transition: 'background 0.2s',
                            cursor: 'pointer',
                            boxShadow: '0 1px 4px rgba(30,58,92,0.06)',
                            opacity: isFilled ? 1 : 0.6,
                          }}
                          onClick={() => handleCellClick(rIdx, colIdx)}
                          onMouseOver={e => { (e.currentTarget as HTMLElement).style.background = '#ffe082'; }}
                          onMouseOut={e => { (e.currentTarget as HTMLElement).style.background = isFilled
                            ? getXTaskColor(cell.split('\n')[0])
                            : (darkMode ? '#1a2233' : '#f7f9fb'); }}
                        >
                          {renderCell(cell, colIdx, rIdx)}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </Box>
        </TableContainer>
      </Box>
      <Dialog open={modal.open} onClose={() => setModal(m => ({...m, open: false}))}>
        <DialogTitle sx={{ color: darkMode ? '#fff' : '#1e3a5c', background: darkMode ? '#232a36' : '#fff' }}>Assign X Task for {modal.soldier} - Week {modal.weekLabel}</DialogTitle>
        <DialogContent sx={{ background: darkMode ? '#232a36' : '#fff' }}>
          <List>
            {STANDARD_X_TASKS.map((task, idx) => (
              <ListItem key={idx} disablePadding>
                <ListItemButton selected={modalTask === task} onClick={() => setModalTask(task)} sx={{ color: darkMode ? '#fff' : '#1e3a5c', background: modalTask === task ? (getXTaskColor(task) || '#e3f2fd') : 'inherit' }}>
                  <ListItemText primary={task} />
                </ListItemButton>
              </ListItem>
            ))}
            <ListItem disablePadding>
              <ListItemButton selected={modalTask === 'Other'} onClick={() => setModalTask('Other')} sx={{ color: darkMode ? '#fff' : '#1e3a5c', background: modalTask === 'Other' ? (getXTaskColor('Custom') || '#e3f2fd') : 'inherit' }}>
                <ListItemText primary="Other (Custom Task)" />
              </ListItemButton>
            </ListItem>
          </List>
          {modalTask === 'Other' && (
            <Box sx={{ mt: 2 }}>
              <TextField
                label="Custom Task Name"
                value={modalOther.name}
                onChange={e => {
                  if (e.target.value.length <= MAX_CUSTOM_TASK_LEN) setModalOther(o => ({...o, name: e.target.value}));
                }}
                fullWidth
                sx={{ mb: 2 }}
                inputProps={{ maxLength: MAX_CUSTOM_TASK_LEN }}
                helperText={customTaskWarning || `${modalOther.name.length}/${MAX_CUSTOM_TASK_LEN} chars`}
                error={!!customTaskWarning}
              />
              <LocalizationProvider dateAdapter={AdapterDateFns}>
                <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                  <DatePicker
                    label="Start Date"
                    value={modalOther.range[0]}
                    onChange={(date: Date | null) => setModalOther(o => ({...o, range: [date, o.range[1]]}))}
                    format="dd/MM/yyyy"
                    slotProps={{ textField: { sx: { minWidth: 180 } } }}
                  />
                  <DatePicker
                    label="End Date"
                    value={modalOther.range[1]}
                    onChange={(date: Date | null) => setModalOther(o => ({...o, range: [o.range[0], date]}))}
                    format="dd/MM/yyyy"
                    slotProps={{ textField: { sx: { minWidth: 180 } } }}
                  />
                </Box>
              </LocalizationProvider>
            </Box>
          )}
          {isCellFilled(editData[modal.row]?.[modal.col] || '') && (
            <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
              <Button
                variant="outlined"
                color="error"
                startIcon={<DeleteIcon />}
                onClick={handleRemoveAssignment}
                sx={{ fontWeight: 700 }}
              >
                Remove Assignment
              </Button>
            </Box>
          )}
        </DialogContent>
        <DialogActions sx={{ background: darkMode ? '#232a36' : '#fff' }}>
          <Button onClick={() => setModal(m => ({...m, open: false}))} sx={{ color: darkMode ? '#fff' : '#1e3a5c' }}>Cancel</Button>
          <Button onClick={handleModalSave} disabled={modalTask === '' || (modalTask === 'Other' && (!modalOther.name || !modalOther.range[0] || !modalOther.range[1]))} sx={{ color: darkMode ? '#fff' : '#1e3a5c' }}>Save</Button>
        </DialogActions>
      </Dialog>
      <Snackbar open={saveSuccess} autoHideDuration={3000} onClose={() => setSaveSuccess(false)} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        <MuiAlert onClose={() => setSaveSuccess(false)} severity="success" sx={{ width: '100%' }}>
          X tasks saved successfully!
        </MuiAlert>
      </Snackbar>
      <Snackbar
        open={conflictWarning}
        autoHideDuration={10000}
        onClose={() => setConflictWarning(false)}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <MuiAlert onClose={() => setConflictWarning(false)} severity="warning" sx={{ width: '100%' }}>
          <strong>X/Y Task Conflict Detected!</strong>
          <ul>
            {conflictDetails.map((c, i) => (
              <li key={i}>
                <b>{c.soldier}</b> has <b>X: {c.x_task}</b> and <b>Y: {c.y_task}</b> on <b>{c.date}</b>
              </li>
            ))}
          </ul>
          Please review the highlighted (blinking) cells and adjust the Y schedule as needed.
        </MuiAlert>
      </Snackbar>
      <Footer />
    </PageContainer>
  );
}

export default XTaskPage;