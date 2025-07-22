import React, { useEffect, useState } from 'react';
import { Box, Typography, Table, TableHead, TableRow, TableCell, TableBody, Button, Select, MenuItem, Chip, CircularProgress, TextField, Autocomplete, Dialog, DialogTitle, DialogContent, DialogActions, IconButton, Checkbox } from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import FadingBackground from '../components/FadingBackground';
import Footer from '../components/Footer';
import PageContainer from '../components/PageContainer';
import TableContainer from '../components/TableContainer';
import DarkModeToggle from '../components/DarkModeToggle';

const QUALIFICATIONS = [
  'Supervisor', 'C&N Driver', 'C&N Escort', 'Southern Driver', 'Southern Escort', 'Guarding Duties', 'RASAR', 'Kitchen'
];

function ManageWorkersPage({ darkMode, onToggleDarkMode }: { darkMode: boolean; onToggleDarkMode: () => void }) {
  const [workers, setWorkers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [editId, setEditId] = useState<string | null>(null);
  const [editWorker, setEditWorker] = useState<any | null>(null);
  const [editQuals, setEditQuals] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [selectedWorker, setSelectedWorker] = useState<any | null>(null);
  const [addDialog, setAddDialog] = useState(false);
  const [newWorker, setNewWorker] = useState<any>({ id: '', name: '', start_date: '', qualifications: [], closing_interval: 4, officer: false, seniority: '', score: '' });

  useEffect(() => {
    fetchWorkers();
  }, []);

  const fetchWorkers = () => {
    setLoading(true);
    fetch('http://localhost:5000/api/workers', { credentials: 'include' })
      .then(res => res.json())
      .then(data => { setWorkers(data.workers || []); setLoading(false); })
      .catch(() => { setError('Failed to load workers'); setLoading(false); });
  };

  const handleEdit = (worker: any) => {
    setEditId(worker.id);
    setEditWorker({ ...worker });
    setEditQuals(worker.qualifications);
  };

  const handleSave = () => {
    if (!editWorker) return;
    fetch(`http://localhost:5000/api/workers/${editWorker.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ ...editWorker, qualifications: editQuals })
    })
      .then(res => res.json())
      .then(() => { setEditId(null); setEditWorker(null); setEditQuals([]); fetchWorkers(); })
      .catch(() => setError('Failed to save worker'));
  };

  const handleDelete = (id: string) => {
    fetch(`http://localhost:5000/api/workers/${id}`, { method: 'DELETE', credentials: 'include' })
      .then(res => res.json())
      .then(() => { setSelectedWorker(null); fetchWorkers(); });
  };

  const handleAdd = () => {
    fetch('http://localhost:5000/api/workers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(newWorker)
    })
      .then(res => res.json())
      .then(() => { setAddDialog(false); setNewWorker({ id: '', name: '', start_date: '', qualifications: [], closing_interval: 4, officer: false, seniority: '', score: '' }); fetchWorkers(); });
  };

  if (loading) return <Box sx={{ p: 4 }}><CircularProgress /></Box>;
  if (error) return <Box sx={{ p: 4 }}><Typography color="error">{error}</Typography></Box>;

  return (
    <PageContainer>
      <FadingBackground />
      <DarkModeToggle darkMode={darkMode} onToggle={onToggleDarkMode} />
      <Box sx={{ position: 'relative', zIndex: 1 }}>
        <Typography variant="h5" sx={{ mb: 2 }}>Manage Workers</Typography>
        <Button variant="contained" sx={{ mb: 3 }} onClick={() => setAddDialog(true)}>Add Worker</Button>
        <Autocomplete
          options={workers}
          getOptionLabel={option => `${option.id} - ${option.name}`}
          value={selectedWorker}
          onChange={(_, value) => { setSelectedWorker(value); setEditId(null); setEditWorker(null); setEditQuals([]); setSearch(''); }}
          inputValue={search}
          onInputChange={(_, value) => { setSearch(value); if (!value) setSelectedWorker(null); }}
          renderInput={params => (
            <TextField {...params} label="Search by ID or Name" variant="outlined" sx={{ mb: 3, width: 400, bgcolor: 'rgba(30,42,60,0.85)', borderRadius: 2 }} />
          )}
          sx={{ mb: 3 }}
          isOptionEqualToValue={(option, value) => option.id === value.id}
        />
        {selectedWorker ? (
          <TableContainer>
            <Table sx={{ bgcolor: 'rgba(30,42,60,0.85)', borderRadius: 2 }}>
              <TableHead>
                <TableRow>
                  <TableCell>ID</TableCell>
                  <TableCell>שם</TableCell>
                  <TableCell>Start Date</TableCell>
                  <TableCell>Qualifications</TableCell>
                  <TableCell>Closing Interval</TableCell>
                  <TableCell>Officer</TableCell>
                  <TableCell>Seniority</TableCell>
                  <TableCell>Score</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                <TableRow key={selectedWorker.id}>
                  <TableCell>{selectedWorker.id}</TableCell>
                  <TableCell>{selectedWorker.name}</TableCell>
                  <TableCell>{selectedWorker.start_date}</TableCell>
                  <TableCell>
                    {editId === selectedWorker.id ? (
                      <Select
                        multiple
                        value={editQuals}
                        onChange={e => setEditQuals(e.target.value as string[])}
                        fullWidth
                        renderValue={selected => (
                          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>{selected.map((val: string) => (<Chip key={val} label={val} />))}</Box>
                        )}
                      >
                        {QUALIFICATIONS.map(q => <MenuItem key={q} value={q}>{q}</MenuItem>)}
                      </Select>
                    ) : (
                      selectedWorker.qualifications.join(', ')
                    )}
                  </TableCell>
                  <TableCell>{selectedWorker.closing_interval}</TableCell>
                  <TableCell>{selectedWorker.officer ? 'Yes' : 'No'}</TableCell>
                  <TableCell>{selectedWorker.seniority}</TableCell>
                  <TableCell>{selectedWorker.score}</TableCell>
                  <TableCell>
                    {editId === selectedWorker.id ? (
                      <>
                        <Button variant="contained" size="small" onClick={handleSave} sx={{ mr: 1 }}>Save</Button>
                        <Button variant="outlined" size="small" onClick={() => { setEditId(null); setEditWorker(null); setEditQuals([]); }}>Cancel</Button>
                      </>
                    ) : (
                      <>
                        <Button variant="outlined" size="small" onClick={() => handleEdit(selectedWorker)}>Edit</Button>
                        <IconButton color="error" onClick={() => handleDelete(selectedWorker.id)}><DeleteIcon /></IconButton>
                      </>
                    )}
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </TableContainer>
        ) : (
          <Typography sx={{ color: 'text.secondary', mt: 4, fontSize: 18 }}>Search for a worker by ID or name to view and edit qualifications.</Typography>
        )}
        {/* Add Worker Dialog */}
        <Dialog open={addDialog} onClose={() => setAddDialog(false)}>
          <DialogTitle>Add Worker</DialogTitle>
          <DialogContent>
            <TextField label="ID" value={newWorker.id} onChange={e => setNewWorker((w: any) => ({ ...w, id: e.target.value }))} fullWidth sx={{ mb: 2 }} />
            <TextField label="Name" value={newWorker.name} onChange={e => setNewWorker((w: any) => ({ ...w, name: e.target.value }))} fullWidth sx={{ mb: 2 }} />
            <TextField label="Start Date" value={newWorker.start_date} onChange={e => setNewWorker((w: any) => ({ ...w, start_date: e.target.value }))} fullWidth sx={{ mb: 2 }} />
            <Select
              multiple
              value={newWorker.qualifications}
              onChange={e => setNewWorker((w: any) => ({ ...w, qualifications: e.target.value }))}
              fullWidth
              renderValue={selected => (<Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>{selected.map((val: string) => (<Chip key={val} label={val} />))}</Box>)}
              sx={{ mb: 2 }}
            >
              {QUALIFICATIONS.map(q => <MenuItem key={q} value={q}>{q}</MenuItem>)}
            </Select>
            <TextField label="Closing Interval" type="number" value={newWorker.closing_interval} onChange={e => setNewWorker((w: any) => ({ ...w, closing_interval: Number(e.target.value) }))} fullWidth sx={{ mb: 2 }} />
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <Checkbox checked={!!newWorker.officer} onChange={e => setNewWorker((w: any) => ({ ...w, officer: e.target.checked }))} /> Officer
            </Box>
            <TextField label="Seniority" value={newWorker.seniority} onChange={e => setNewWorker((w: any) => ({ ...w, seniority: e.target.value }))} fullWidth sx={{ mb: 2 }} />
            <TextField label="Score" type="number" value={newWorker.score} onChange={e => setNewWorker((w: any) => ({ ...w, score: e.target.value }))} fullWidth sx={{ mb: 2 }} />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setAddDialog(false)}>Cancel</Button>
            <Button onClick={handleAdd} variant="contained">Add</Button>
          </DialogActions>
        </Dialog>
      </Box>
      <Footer />
    </PageContainer>
  );
}

export default ManageWorkersPage; 