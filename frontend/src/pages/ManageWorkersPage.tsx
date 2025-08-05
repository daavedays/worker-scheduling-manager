import React, { useEffect, useState } from 'react';
import { 
  Box, 
  Typography, 
  Table, 
  TableHead, 
  TableRow, 
  TableCell, 
  TableBody, 
  Button, 
  Select, 
  MenuItem, 
  Chip, 
  CircularProgress, 
  TextField, 
  Autocomplete, 
  Dialog, 
  DialogTitle, 
  DialogContent, 
  DialogActions, 
  IconButton, 
  Checkbox,
  FormControl,
  InputLabel,
  ListItemText,
  OutlinedInput,
  Paper,
  Alert,
  Snackbar,
  Tooltip,
  Divider
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import SaveIcon from '@mui/icons-material/Save';
import CancelIcon from '@mui/icons-material/Cancel';
import AddIcon from '@mui/icons-material/Add';
import SearchIcon from '@mui/icons-material/Search';
import PersonIcon from '@mui/icons-material/Person';
import FadingBackground from '../components/FadingBackground';
import Footer from '../components/Footer';
import PageContainer from '../components/PageContainer';
import TableContainer from '../components/TableContainer';
import Header from '../components/Header';

const QUALIFICATIONS = [
  'Supervisor', 'C&N Driver', 'C&N Escort', 'Southern Driver', 'Southern Escort', 'Guarding Duties', 'RASAR', 'Kitchen'
];

// Helper function to convert closing interval numbers to Hebrew text
const getClosingIntervalText = (value: number): string => {
  switch (value) {
    case 0: return 'ללא סגירות';
    case 2: return 'חצאים';
    case 3: return 'שלישים';
    case 4: return 'רבעים';
    case 5: return 'אחד לחמש';
    case 6: return 'אחד לשש';
    default: return `${value} weeks`;
  }
};

// Helper function to convert Hebrew text to closing interval numbers
const getClosingIntervalValue = (text: string): number => {
  switch (text) {
    case 'ללא סגירות': return 0;
    case 'חצאים': return 2;
    case 'שלישים': return 3;
    case 'רבעים': return 4;
    case 'אחד לחמש': return 5;
    case 'אחד לשש': return 6;
    default: return 4; // Default to quarters
  }
};

// Closing interval options
const CLOSING_INTERVAL_OPTIONS = [
  { value: 0, label: 'ללא סגירות' },
  { value: 2, label: 'חצאים' },
  { value: 3, label: 'שלישים' },
  { value: 4, label: 'רבעים' },
  { value: 5, label: 'אחד לחמש' },
  { value: 6, label: 'אחד לשש' }
];

function ManageWorkersPage({ darkMode, onToggleDarkMode }: { darkMode: boolean; onToggleDarkMode: () => void }) {
  const [workers, setWorkers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [editId, setEditId] = useState<string | null>(null);
  const [editWorker, setEditWorker] = useState<any | null>(null);
  const [editQuals, setEditQuals] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [selectedWorker, setSelectedWorker] = useState<any | null>(null);
  const [addDialog, setAddDialog] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [newWorker, setNewWorker] = useState<any>({ 
    id: '', 
    name: '', 
    qualifications: [], 
    closing_interval: 4, // Default to רבעים (quarters)
    officer: false 
  });

  useEffect(() => {
    fetchWorkers();
  }, []);

  const fetchWorkers = () => {
    setLoading(true);
    fetch('http://localhost:5001/api/workers', { credentials: 'include' })
      .then(res => res.json())
      .then(data => { 
        setWorkers(data.workers || []); 
        setLoading(false); 
      })
      .catch(() => { 
        setError('Failed to load workers'); 
        setLoading(false); 
      });
  };

  const handleEdit = (worker: any) => {
    setEditId(worker.id);
    setEditWorker({ ...worker });
    setEditQuals(worker.qualifications);
    setSuccess(null);
    setError(null);
  };

  const handleSave = () => {
    if (!editWorker) return;
    
    setLoading(true);
    fetch(`http://localhost:5001/api/workers/${editWorker.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ ...editWorker, qualifications: editQuals })
    })
      .then(res => res.json())
      .then(() => { 
        setEditId(null); 
        setEditWorker(null); 
        setEditQuals([]); 
        fetchWorkers();
        setSuccess('Worker updated successfully!');
      })
      .catch(() => {
        setError('Failed to save worker');
        setLoading(false);
      });
  };

  const handleCancel = () => {
    setEditId(null);
    setEditWorker(null);
    setEditQuals([]);
    setError(null);
  };

  const handleDelete = (id: string) => {
    setLoading(true);
    fetch(`http://localhost:5001/api/workers/${id}`, { 
      method: 'DELETE', 
      credentials: 'include' 
    })
      .then(res => res.json())
      .then(() => { 
        setSelectedWorker(null); 
        fetchWorkers();
        setSuccess('Worker deleted successfully!');
        setDeleteConfirm(null);
      })
      .catch(() => {
        setError('Failed to delete worker');
        setLoading(false);
      });
  };

  const handleAdd = () => {
    if (!newWorker.id || !newWorker.name) {
      setError('Please fill in all required fields');
      return;
    }
    
    setLoading(true);
    fetch('http://localhost:5001/api/workers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(newWorker)
    })
      .then(res => res.json())
      .then(() => { 
        setAddDialog(false); 
        setNewWorker({ id: '', name: '', qualifications: [], closing_interval: 4, officer: false }); // Default to רבעים 
        fetchWorkers();
        setSuccess('Worker added successfully!');
      })
      .catch(() => {
        setError('Failed to add worker');
        setLoading(false);
      });
  };

  const handleCloseSnackbar = () => {
    setError(null);
    setSuccess(null);
  };

  if (loading && workers.length === 0) {
    return (
      <PageContainer>
        <FadingBackground />
        <Header 
          darkMode={darkMode}
          onToggleDarkMode={onToggleDarkMode}
          showBackButton={true}
          showHomeButton={true}
          showDarkModeToggle={false}
          title="Manage Workers"
        />
        <Box sx={{ 
          display: 'flex', 
          justifyContent: 'center', 
          alignItems: 'center', 
          height: '60vh',
          position: 'relative',
          zIndex: 1
        }}>
          <CircularProgress size={60} sx={{ color: '#1976d2' }} />
        </Box>
        <Footer />
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <FadingBackground />
      <Header 
        darkMode={darkMode}
        onToggleDarkMode={onToggleDarkMode}
        showBackButton={true}
        showHomeButton={true}
        showDarkModeToggle={false}
        title="Manage Workers"
      />
      
      <Box sx={{ position: 'relative', zIndex: 1, p: 3 }}>
        {/* Page Header */}
        <Box sx={{ mb: 4 }}>
          <Typography 
            variant="h4" 
            sx={{ 
              color: 'white',
              textShadow: '0 2px 4px rgba(0,0,0,0.5)',
              fontWeight: 'bold',
              mb: 1
            }}
          >
            Manage Workers
          </Typography>
          <Typography 
            variant="body1" 
            sx={{ 
              color: 'rgba(255,255,255,0.8)',
              textShadow: '0 1px 2px rgba(0,0,0,0.3)'
            }}
          >
            Add, edit, and manage worker information and qualifications
          </Typography>
        </Box>

        {/* Action Bar */}
        <Paper sx={{ 
          p: 3, 
          mb: 3, 
          bgcolor: 'rgba(30,42,60,0.9)',
          borderRadius: 3,
          border: '1px solid rgba(255,255,255,0.1)',
          boxShadow: '0 8px 32px rgba(0,0,0,0.3)'
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 3, flexWrap: 'wrap' }}>
            {/* Add Worker Button */}
            <Button 
              variant="contained" 
              startIcon={<AddIcon />}
              onClick={() => setAddDialog(true)}
              sx={{ 
                bgcolor: '#2e7d32',
                color: 'white',
                px: 3,
                py: 1.5,
                borderRadius: 2,
                fontWeight: 'bold',
                fontSize: '1rem',
                textTransform: 'none',
                boxShadow: '0 4px 12px rgba(46,125,50,0.3)',
                '&:hover': {
                  bgcolor: '#1b5e20',
                  boxShadow: '0 6px 16px rgba(46,125,50,0.4)',
                  transform: 'translateY(-1px)'
                }
              }}
            >
              Add New Worker
            </Button>

            {/* Search Field */}
            <Box sx={{ flex: 1, minWidth: 300 }}>
        <Autocomplete
          options={workers}
          getOptionLabel={option => `${option.id} - ${option.name}`}
          value={selectedWorker}
                onChange={(_, value) => { 
                  setSelectedWorker(value); 
                  setEditId(null); 
                  setEditWorker(null); 
                  setEditQuals([]); 
                  setSearch(''); 
                }}
          inputValue={search}
                onInputChange={(_, value) => { 
                  setSearch(value); 
                  if (!value) setSelectedWorker(null); 
                }}
          renderInput={params => (
                  <TextField 
                    {...params} 
                    placeholder="Search workers by ID or name..."
                    variant="outlined" 
                    InputProps={{
                      ...params.InputProps,
                      startAdornment: <SearchIcon sx={{ color: 'rgba(255,255,255,0.5)', mr: 1 }} />
                    }}
                    sx={{ 
                      '& .MuiOutlinedInput-root': {
                        bgcolor: 'rgba(255,255,255,0.05)',
                        borderRadius: 2,
                        '& fieldset': {
                          borderColor: 'rgba(255,255,255,0.2)',
                        },
                        '&:hover fieldset': {
                          borderColor: 'rgba(255,255,255,0.3)',
                        },
                        '&.Mui-focused fieldset': {
                          borderColor: '#1976d2',
                        },
                      },
                      '& .MuiInputLabel-root': {
                        color: 'rgba(255,255,255,0.7)',
                      },
                      '& .MuiInputBase-input': {
                        color: 'white',
                        '&::placeholder': {
                          color: 'rgba(255,255,255,0.5)',
                          opacity: 1
                        }
                      }
                    }} 
                  />
                )}
                sx={{
                  '& .MuiAutocomplete-popupIndicator': {
                    color: 'rgba(255,255,255,0.7)'
                  }
                }}
          isOptionEqualToValue={(option, value) => option.id === value.id}
        />
            </Box>
          </Box>
        </Paper>

        {/* Worker Details */}
        {selectedWorker ? (
          <Paper sx={{ 
            bgcolor: 'rgba(30,42,60,0.9)', 
            borderRadius: 3,
            border: '1px solid rgba(255,255,255,0.1)',
            boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
            overflow: 'hidden'
          }}>
            {/* Worker Header */}
            <Box sx={{ 
              p: 3, 
              bgcolor: 'rgba(25,118,210,0.2)',
              borderBottom: '1px solid rgba(255,255,255,0.1)'
            }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <PersonIcon sx={{ color: '#1976d2', fontSize: 28 }} />
                <Box>
                  <Typography variant="h6" sx={{ color: 'white', fontWeight: 'bold' }}>
                    {selectedWorker.name}
                  </Typography>
                  <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.7)' }}>
                    ID: {selectedWorker.id}
                  </Typography>
                </Box>
              </Box>
            </Box>

            {/* Worker Details Table */}
          <TableContainer>
              <Table>
              <TableHead>
                  <TableRow sx={{ bgcolor: 'rgba(25,118,210,0.1)' }}>
                    <TableCell sx={{ color: 'white', fontWeight: 'bold', borderColor: 'rgba(255,255,255,0.1)' }}>
                      Field
                    </TableCell>
                    <TableCell sx={{ color: 'white', fontWeight: 'bold', borderColor: 'rgba(255,255,255,0.1)' }}>
                      Value
                    </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                  {/* Qualifications Row */}
                  <TableRow>
                    <TableCell sx={{ color: 'rgba(255,255,255,0.8)', borderColor: 'rgba(255,255,255,0.1)', fontWeight: 'bold' }}>
                      Qualifications
                    </TableCell>
                    <TableCell sx={{ borderColor: 'rgba(255,255,255,0.1)' }}>
                    {editId === selectedWorker.id ? (
                        <FormControl fullWidth>
                      <Select
                        multiple
                        value={editQuals}
                        onChange={e => setEditQuals(e.target.value as string[])}
                            input={<OutlinedInput />}
                            renderValue={(selected) => (
                              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                                {(selected as string[]).map((value) => (
                                  <Chip 
                                    key={value} 
                                    label={value} 
                                    size="small"
                                    sx={{ 
                                      bgcolor: '#1976d2',
                                      color: 'white',
                                      fontWeight: 'bold'
                                    }}
                                  />
                                ))}
                              </Box>
                            )}
                            sx={{
                              color: 'white',
                              '& .MuiOutlinedInput-notchedOutline': {
                                borderColor: 'rgba(255,255,255,0.3)',
                              },
                              '&:hover .MuiOutlinedInput-notchedOutline': {
                                borderColor: 'rgba(255,255,255,0.5)',
                              },
                              '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                                borderColor: '#1976d2',
                              },
                            }}
                          >
                            {QUALIFICATIONS.map((qualification) => (
                              <MenuItem key={qualification} value={qualification}>
                                <Checkbox 
                                  checked={editQuals.indexOf(qualification) > -1}
                                  sx={{ 
                                    color: 'rgba(255,255,255,0.7)',
                                    '&.Mui-checked': {
                                      color: '#1976d2',
                                    },
                                  }}
                                />
                                <ListItemText 
                                  primary={qualification}
                                  sx={{ color: 'white' }}
                                />
                              </MenuItem>
                            ))}
                      </Select>
                        </FormControl>
                      ) : (
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                          {selectedWorker.qualifications.map((qual: string) => (
                            <Chip 
                              key={qual} 
                              label={qual} 
                              size="small"
                              sx={{ 
                                bgcolor: '#1976d2',
                                color: 'white',
                                fontWeight: 'bold'
                              }}
                            />
                          ))}
                        </Box>
                    )}
                  </TableCell>
                  </TableRow>

                  {/* Closing Interval Row */}
                  <TableRow>
                    <TableCell sx={{ color: 'rgba(255,255,255,0.8)', borderColor: 'rgba(255,255,255,0.1)', fontWeight: 'bold' }}>
                      Closing Interval
                    </TableCell>
                    <TableCell sx={{ borderColor: 'rgba(255,255,255,0.1)' }}>
                    {editId === selectedWorker.id ? (
                                                 <FormControl fullWidth>
                           <Select
                             value={editWorker?.closing_interval || selectedWorker.closing_interval}
                             onChange={e => setEditWorker((w: any) => ({ ...w, closing_interval: Number(e.target.value) }))}
                             input={<OutlinedInput />}
                             renderValue={(selected) => (
                               <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                                 <Chip 
                                   label={getClosingIntervalText(selected as number)} 
                                   size="small"
                                   sx={{ 
                                     bgcolor: '#1976d2',
                                     color: 'white',
                                     fontWeight: 'bold'
                                   }}
                                 />
                               </Box>
                             )}
                             sx={{
                               color: 'white',
                               '& .MuiOutlinedInput-notchedOutline': {
                                 borderColor: 'rgba(255,255,255,0.3)',
                               },
                               '&:hover .MuiOutlinedInput-notchedOutline': {
                                 borderColor: 'rgba(255,255,255,0.5)',
                               },
                               '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                                 borderColor: '#1976d2',
                               },
                             }}
                           >
                             {CLOSING_INTERVAL_OPTIONS.map((option) => (
                               <MenuItem key={option.value} value={option.value}>
                                 <ListItemText primary={option.label} sx={{ color: 'white' }} />
                               </MenuItem>
                             ))}
                           </Select>
                         </FormControl>
                      ) : (
                        <Chip 
                          label={getClosingIntervalText(selectedWorker.closing_interval)} 
                          size="small"
                          sx={{ 
                            bgcolor: '#1976d2',
                            color: 'white',
                            fontWeight: 'bold'
                          }}
                        />
                    )}
                  </TableCell>
                </TableRow>

                  {/* Officer Status Row */}
                  <TableRow>
                    <TableCell sx={{ color: 'rgba(255,255,255,0.8)', borderColor: 'rgba(255,255,255,0.1)', fontWeight: 'bold' }}>
                      Officer Status
                    </TableCell>
                    <TableCell sx={{ borderColor: 'rgba(255,255,255,0.1)' }}>
                      <Chip 
                        label={selectedWorker.officer ? 'Yes' : 'No'} 
                        size="small"
                        sx={{ 
                          bgcolor: selectedWorker.officer ? '#2e7d32' : '#757575',
                          color: 'white',
                          fontWeight: 'bold'
                        }}
                      />
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </TableContainer>

            {/* Action Buttons */}
            <Box sx={{ p: 3, bgcolor: 'rgba(0,0,0,0.1)', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
              {editId === selectedWorker.id ? (
                <Box sx={{ display: 'flex', gap: 2 }}>
                  <Button 
                    variant="contained" 
                    startIcon={<SaveIcon />}
                    onClick={handleSave}
                    sx={{ 
                      bgcolor: '#2e7d32',
                      color: 'white',
                      px: 3,
                      py: 1.5,
                      borderRadius: 2,
                      fontWeight: 'bold',
                      textTransform: 'none',
                      boxShadow: '0 4px 12px rgba(46,125,50,0.3)',
                      '&:hover': {
                        bgcolor: '#1b5e20',
                        boxShadow: '0 6px 16px rgba(46,125,50,0.4)',
                        transform: 'translateY(-1px)'
                      }
                    }}
                  >
                    Save Changes
                  </Button>
                  <Button 
                    variant="outlined" 
                    startIcon={<CancelIcon />}
                    onClick={handleCancel}
                    sx={{
                      color: 'rgba(255,255,255,0.8)',
                      borderColor: 'rgba(255,255,255,0.3)',
                      px: 3,
                      py: 1.5,
                      borderRadius: 2,
                      fontWeight: 'bold',
                      textTransform: 'none',
                      '&:hover': {
                        borderColor: 'rgba(255,255,255,0.5)',
                        bgcolor: 'rgba(255,255,255,0.05)'
                      }
                    }}
                  >
                    Cancel
                  </Button>
                </Box>
              ) : (
                <Box sx={{ display: 'flex', gap: 2 }}>
                  <Button 
                    variant="contained" 
                    startIcon={<EditIcon />}
                    onClick={() => handleEdit(selectedWorker)}
                    sx={{ 
                      bgcolor: '#1976d2',
                      color: 'white',
                      px: 3,
                      py: 1.5,
                      borderRadius: 2,
                      fontWeight: 'bold',
                      textTransform: 'none',
                      boxShadow: '0 4px 12px rgba(25,118,210,0.3)',
                      '&:hover': {
                        bgcolor: '#1565c0',
                        boxShadow: '0 6px 16px rgba(25,118,210,0.4)',
                        transform: 'translateY(-1px)'
                      }
                    }}
                  >
                    Edit Worker
                  </Button>
                  <Tooltip title="Delete worker">
                    <Button 
                      variant="outlined" 
                      startIcon={<DeleteIcon />}
                      onClick={() => setDeleteConfirm(selectedWorker.id)}
                      sx={{
                        color: '#f44336',
                        borderColor: '#f44336',
                        px: 3,
                        py: 1.5,
                        borderRadius: 2,
                        fontWeight: 'bold',
                        textTransform: 'none',
                        '&:hover': {
                          borderColor: '#d32f2f',
                          bgcolor: 'rgba(244,67,54,0.05)'
                        }
                      }}
                    >
                      Delete
                    </Button>
                  </Tooltip>
                </Box>
              )}
            </Box>
          </Paper>
        ) : (
          <Paper sx={{ 
            p: 4, 
            bgcolor: 'rgba(30,42,60,0.9)', 
            borderRadius: 3,
            border: '1px solid rgba(255,255,255,0.1)',
            boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
            textAlign: 'center'
          }}>
            <SearchIcon sx={{ fontSize: 48, color: 'rgba(255,255,255,0.3)', mb: 2 }} />
            <Typography 
              variant="h6" 
              sx={{ 
                color: 'rgba(255,255,255,0.8)', 
                mb: 1,
                fontWeight: 'bold'
              }}
            >
              Search for a Worker
            </Typography>
            <Typography 
              variant="body1" 
              sx={{ 
                color: 'rgba(255,255,255,0.6)',
                textShadow: '0 1px 2px rgba(0,0,0,0.3)'
              }}
            >
              Use the search field above to find and manage worker information
            </Typography>
          </Paper>
        )}

        {/* Add Worker Dialog */}
        <Dialog 
          open={addDialog} 
          onClose={() => setAddDialog(false)}
          maxWidth="sm"
          fullWidth
          PaperProps={{
            sx: {
              bgcolor: 'rgba(30,42,60,0.95)',
              color: 'white',
              borderRadius: 3,
              boxShadow: '0 16px 48px rgba(0,0,0,0.5)'
            }
          }}
        >
          <DialogTitle sx={{ 
            color: 'white', 
            borderBottom: '1px solid rgba(255,255,255,0.1)',
            pb: 2
          }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <AddIcon sx={{ color: '#2e7d32' }} />
              <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
                Add New Worker
              </Typography>
            </Box>
          </DialogTitle>
          <DialogContent sx={{ pt: 3 }}>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              <TextField 
                label="Worker ID" 
                value={newWorker.id} 
                onChange={e => setNewWorker((w: any) => ({ ...w, id: e.target.value }))} 
                fullWidth
                required
                InputProps={{
                  sx: {
                    color: 'white',
                    '& fieldset': {
                      borderColor: 'rgba(255,255,255,0.3)',
                    },
                    '&:hover fieldset': {
                      borderColor: 'rgba(255,255,255,0.5)',
                    },
                    '&.Mui-focused fieldset': {
                      borderColor: '#1976d2',
                    },
                  }
                }}
                InputLabelProps={{
                  sx: { color: 'rgba(255,255,255,0.7)' }
                }}
              />
              <TextField 
                label="Worker Name" 
                value={newWorker.name} 
                onChange={e => setNewWorker((w: any) => ({ ...w, name: e.target.value }))} 
                fullWidth
                required
                InputProps={{
                  sx: {
                    color: 'white',
                    '& fieldset': {
                      borderColor: 'rgba(255,255,255,0.3)',
                    },
                    '&:hover fieldset': {
                      borderColor: 'rgba(255,255,255,0.5)',
                    },
                    '&.Mui-focused fieldset': {
                      borderColor: '#1976d2',
                    },
                  }
                }}
                InputLabelProps={{
                  sx: { color: 'rgba(255,255,255,0.7)' }
                }}
              />
              <FormControl fullWidth>
                <InputLabel sx={{ color: 'rgba(255,255,255,0.7)' }}>Qualifications</InputLabel>
            <Select
              multiple
              value={newWorker.qualifications}
              onChange={e => setNewWorker((w: any) => ({ ...w, qualifications: e.target.value }))}
                  input={<OutlinedInput label="Qualifications" />}
                  renderValue={(selected) => (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {(selected as string[]).map((value) => (
                        <Chip 
                          key={value} 
                          label={value} 
                          size="small"
                          sx={{ 
                            bgcolor: '#1976d2',
                            color: 'white',
                            fontWeight: 'bold'
                          }}
                        />
                      ))}
                    </Box>
                  )}
                  sx={{
                    color: 'white',
                    '& .MuiOutlinedInput-notchedOutline': {
                      borderColor: 'rgba(255,255,255,0.3)',
                    },
                    '&:hover .MuiOutlinedInput-notchedOutline': {
                      borderColor: 'rgba(255,255,255,0.5)',
                    },
                    '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                      borderColor: '#1976d2',
                    },
                  }}
                >
                  {QUALIFICATIONS.map((qualification) => (
                    <MenuItem key={qualification} value={qualification}>
                      <Checkbox 
                        checked={newWorker.qualifications.indexOf(qualification) > -1}
                        sx={{ 
                          color: 'rgba(255,255,255,0.7)',
                          '&.Mui-checked': {
                            color: '#1976d2',
                          },
                        }}
                      />
                      <ListItemText primary={qualification} sx={{ color: 'white' }} />
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
                             <FormControl fullWidth>
                 <InputLabel sx={{ color: 'rgba(255,255,255,0.7)' }}>Closing Interval</InputLabel>
                 <Select
                   value={newWorker.closing_interval}
                   onChange={e => setNewWorker((w: any) => ({ ...w, closing_interval: Number(e.target.value) }))}
                   input={<OutlinedInput />}
                   renderValue={(selected) => (
                     <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                       <Chip 
                         label={getClosingIntervalText(selected as number)} 
                         size="small"
                         sx={{ 
                           bgcolor: '#1976d2',
                           color: 'white',
                           fontWeight: 'bold'
                         }}
                       />
                     </Box>
                   )}
                   sx={{
                     color: 'white',
                     '& .MuiOutlinedInput-notchedOutline': {
                       borderColor: 'rgba(255,255,255,0.3)',
                     },
                     '&:hover .MuiOutlinedInput-notchedOutline': {
                       borderColor: 'rgba(255,255,255,0.5)',
                     },
                     '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                       borderColor: '#1976d2',
                     },
                   }}
                 >
                   {CLOSING_INTERVAL_OPTIONS.map((option) => (
                     <MenuItem key={option.value} value={option.value}>
                       <ListItemText primary={option.label} sx={{ color: 'white' }} />
                     </MenuItem>
                   ))}
                 </Select>
               </FormControl>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Checkbox 
                  checked={!!newWorker.officer} 
                  onChange={e => setNewWorker((w: any) => ({ ...w, officer: e.target.checked }))}
                  sx={{
                    color: 'rgba(255,255,255,0.7)',
                    '&.Mui-checked': {
                      color: '#1976d2',
                    },
                  }}
                /> 
                <Typography sx={{ color: 'white', fontWeight: 'bold' }}>Officer Status</Typography>
              </Box>
            </Box>
          </DialogContent>
          <DialogActions sx={{ 
            borderTop: '1px solid rgba(255,255,255,0.1)', 
            p: 3,
            gap: 2
          }}>
            <Button 
              onClick={() => setAddDialog(false)}
              sx={{
                color: 'rgba(255,255,255,0.7)',
                px: 3,
                py: 1.5,
                borderRadius: 2,
                fontWeight: 'bold',
                textTransform: 'none',
                '&:hover': {
                  bgcolor: 'rgba(255,255,255,0.1)',
                }
              }}
            >
              Cancel
            </Button>
            <Button 
              onClick={handleAdd} 
              variant="contained"
              startIcon={<AddIcon />}
              sx={{
                bgcolor: '#2e7d32',
                color: 'white',
                px: 3,
                py: 1.5,
                borderRadius: 2,
                fontWeight: 'bold',
                textTransform: 'none',
                boxShadow: '0 4px 12px rgba(46,125,50,0.3)',
                '&:hover': {
                  bgcolor: '#1b5e20',
                  boxShadow: '0 6px 16px rgba(46,125,50,0.4)',
                  transform: 'translateY(-1px)'
                }
              }}
            >
              Add Worker
            </Button>
          </DialogActions>
        </Dialog>

        {/* Delete Confirmation Dialog */}
        <Dialog 
          open={!!deleteConfirm} 
          onClose={() => setDeleteConfirm(null)}
          PaperProps={{
            sx: {
              bgcolor: 'rgba(30,42,60,0.95)',
              color: 'white',
              borderRadius: 3,
              boxShadow: '0 16px 48px rgba(0,0,0,0.5)'
            }
          }}
        >
          <DialogTitle sx={{ color: 'white', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <DeleteIcon sx={{ color: '#f44336' }} />
              <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
                Confirm Deletion
              </Typography>
            </Box>
          </DialogTitle>
          <DialogContent sx={{ pt: 3 }}>
            <Typography sx={{ color: 'white', mb: 2 }}>
              Are you sure you want to delete this worker? This action cannot be undone.
            </Typography>
            <Typography sx={{ color: 'rgba(255,255,255,0.7)', fontWeight: 'bold' }}>
              Worker: {selectedWorker?.name} (ID: {selectedWorker?.id})
            </Typography>
          </DialogContent>
          <DialogActions sx={{ 
            borderTop: '1px solid rgba(255,255,255,0.1)', 
            p: 3,
            gap: 2
          }}>
            <Button 
              onClick={() => setDeleteConfirm(null)}
              sx={{
                color: 'rgba(255,255,255,0.7)',
                px: 3,
                py: 1.5,
                borderRadius: 2,
                fontWeight: 'bold',
                textTransform: 'none',
                '&:hover': {
                  bgcolor: 'rgba(255,255,255,0.1)',
                }
              }}
            >
              Cancel
            </Button>
            <Button 
              onClick={() => handleDelete(deleteConfirm!)}
              variant="contained"
              startIcon={<DeleteIcon />}
              sx={{
                bgcolor: '#f44336',
                color: 'white',
                px: 3,
                py: 1.5,
                borderRadius: 2,
                fontWeight: 'bold',
                textTransform: 'none',
                boxShadow: '0 4px 12px rgba(244,67,54,0.3)',
                '&:hover': {
                  bgcolor: '#d32f2f',
                  boxShadow: '0 6px 16px rgba(244,67,54,0.4)',
                  transform: 'translateY(-1px)'
                }
              }}
            >
              Delete Worker
            </Button>
          </DialogActions>
        </Dialog>

        {/* Success/Error Messages */}
        <Snackbar 
          open={!!success} 
          autoHideDuration={4000} 
          onClose={handleCloseSnackbar}
          anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
        >
          <Alert onClose={handleCloseSnackbar} severity="success" sx={{ width: '100%' }}>
            {success}
          </Alert>
        </Snackbar>

        <Snackbar 
          open={!!error} 
          autoHideDuration={6000} 
          onClose={handleCloseSnackbar}
          anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
        >
          <Alert onClose={handleCloseSnackbar} severity="error" sx={{ width: '100%' }}>
            {error}
          </Alert>
        </Snackbar>
      </Box>
      
      <Footer />
    </PageContainer>
  );
}

export default ManageWorkersPage; 