import React, { useEffect, useState } from 'react';
import { Box, Typography, Table, TableHead, TableRow, TableCell, TableBody, Button, Select, MenuItem, Chip, CircularProgress, TextField, Autocomplete } from '@mui/material';
import FadingBackground from '../components/FadingBackground';

const QUALIFICATIONS = [
  'Supervisor', 'C&N Driver', 'C&N Escort', 'Southern Driver', 'Southern Escort', 'Guarding Duties', 'RASAR', 'Kitchen'
];

function ManageQualificationsPage() {
  const [workers, setWorkers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [editId, setEditId] = useState<string | null>(null);
  const [editQuals, setEditQuals] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [selectedWorker, setSelectedWorker] = useState<any | null>(null);

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

  const handleEdit = (id: string, currentQuals: string[]) => {
    setEditId(id);
    setEditQuals(currentQuals);
  };

  const handleSave = (id: string) => {
    fetch(`http://localhost:5000/api/workers/${id}/qualifications`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ qualifications: editQuals })
    })
      .then(res => res.json())
      .then(() => { setEditId(null); setEditQuals([]); fetchWorkers(); })
      .catch(() => setError('Failed to save qualifications'));
  };

  // Filter workers by search (id or name, case-insensitive, supports Hebrew)
  const filteredWorkers = selectedWorker
    ? workers.filter(w => w.id === selectedWorker.id)
    : search.trim() === ''
      ? workers
      : workers.filter(w =>
          w.id.toString().includes(search.trim()) ||
          (w.name && w.name.includes(search.trim()))
        );

  if (loading) return <Box sx={{ p: 4 }}><CircularProgress /></Box>;
  if (error) return <Box sx={{ p: 4 }}><Typography color="error">{error}</Typography></Box>;

  return (
    <Box sx={{ p: 4, position: 'relative', minHeight: '100vh', width: '100vw', overflow: 'hidden' }}>
      <FadingBackground />
      <Box sx={{ position: 'relative', zIndex: 1 }}>
        <Typography variant="h5" sx={{ mb: 2 }}>Manage Worker Qualifications</Typography>
        <Autocomplete
          options={workers}
          getOptionLabel={option => `${option.id} - ${option.name}`}
          value={selectedWorker}
          onChange={(_, value) => { setSelectedWorker(value); setSearch(''); }}
          inputValue={search}
          onInputChange={(_, value) => { setSearch(value); if (!value) setSelectedWorker(null); }}
          renderInput={params => (
            <TextField {...params} label="Search by ID or Name" variant="outlined" sx={{ mb: 3, width: 400, bgcolor: 'rgba(30,42,60,0.85)', borderRadius: 2 }} />
          )}
          sx={{ mb: 3 }}
          isOptionEqualToValue={(option, value) => option.id === value.id}
        />
        {selectedWorker ? (
          <Table sx={{ bgcolor: 'rgba(30,42,60,0.85)', borderRadius: 2 }}>
            <TableHead>
              <TableRow>
                <TableCell>ID</TableCell>
                <TableCell>שם</TableCell>
                <TableCell>Qualifications</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              <TableRow key={selectedWorker.id}>
                <TableCell>{selectedWorker.id}</TableCell>
                <TableCell>{selectedWorker.name}</TableCell>
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
                <TableCell>
                  {editId === selectedWorker.id ? (
                    <>
                      <Button variant="contained" size="small" onClick={() => handleSave(selectedWorker.id)} sx={{ mr: 1 }}>Save</Button>
                      <Button variant="outlined" size="small" onClick={() => setEditId(null)}>Cancel</Button>
                    </>
                  ) : (
                    <Button variant="outlined" size="small" onClick={() => handleEdit(selectedWorker.id, selectedWorker.qualifications)}>Edit</Button>
                  )}
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        ) : (
          <Typography sx={{ color: 'text.secondary', mt: 4, fontSize: 18 }}>Search for a worker by ID or name to view and edit qualifications.</Typography>
        )}
      </Box>
    </Box>
  );
}

export default ManageQualificationsPage; 