import { useCallback, useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Alert,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  TextField,
  Paper,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Button,
  Chip,
  Stack,
} from '@mui/material';
import {
  Delete as DeleteIcon,
  Warning as WarningIcon,
  Edit as EditIcon,
  Save as SaveIcon,
  Close as CloseIcon,
} from '@mui/icons-material';
import { usePolling } from '../../hooks/usePolling';
import { api } from '../../services/api';
import type { FocusUnit } from '../../types';
import { FocusUnitDetailSection } from './FocusUnitDetailSection';

export function FocusUnitsView() {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editNotes, setEditNotes] = useState('');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [unitToDelete, setUnitToDelete] = useState<FocusUnit | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const [refreshKey, setRefreshKey] = useState(0);
  
  const fetchFocusUnits = useCallback(() => api.getFocusUnits(), [refreshKey]);
  const fetchFiles = useCallback(() => api.getFiles(), []);

  const {
    data: focusUnitsData,
    error: focusUnitsError,
    isLoading: focusUnitsLoading,
  } = usePolling(fetchFocusUnits, { interval: 5000 });

  const {
    data: filesData,
  } = usePolling(fetchFiles, { interval: 5000 });

  const refetchFocusUnits = () => setRefreshKey(prev => prev + 1);

  const handleEditClick = (unit: FocusUnit) => {
    setEditingId(unit.focus_unit_id);
    setEditNotes(unit.notes);
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditNotes('');
  };

  const handleSaveEdit = async (focusUnitId: string) => {
    setIsSaving(true);
    try {
      await api.updateFocusUnit(focusUnitId, editNotes);
      setEditingId(null);
      setEditNotes('');
      refetchFocusUnits();
    } catch (error) {
      console.error('Failed to update focus unit:', error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteClick = (unit: FocusUnit) => {
    setUnitToDelete(unit);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!unitToDelete) return;
    
    setIsDeleting(true);
    try {
      await api.deleteFocusUnit(unitToDelete.focus_unit_id);
      setDeleteDialogOpen(false);
      setUnitToDelete(null);
      refetchFocusUnits();
    } catch (error) {
      console.error('Failed to delete focus unit:', error);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteDialogOpen(false);
    setUnitToDelete(null);
  };

  // Check if hash matches current file
  const checkHashMismatch = (unit: FocusUnit): boolean => {
    if (!filesData) return false;
    
    const file = filesData.files.find(f => f.filename === unit.bin_filename);
    if (!file || !file.has_coarse_sorting) return false;
    
    // We would need to fetch the current hash to compare
    // For now, we'll show warning icon if file doesn't have coarse sorting
    return !file.has_coarse_sorting;
  };

  if (focusUnitsLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress />
      </Box>
    );
  }

  if (focusUnitsError) {
    return (
      <Alert severity="error">
        Error loading focus units: {focusUnitsError.message}
      </Alert>
    );
  }

  const focusUnits = focusUnitsData?.focus_units || [];

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Focus Units
      </Typography>

      {focusUnits.length === 0 ? (
        <Card>
          <CardContent>
            <Alert severity="info">
              No focus units yet. Add units from the File Explorer by viewing a file with coarse sorting.
            </Alert>
          </CardContent>
        </Card>
      ) : (
        <>
          <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Focus Unit ID</TableCell>
                <TableCell>Bin File</TableCell>
                <TableCell>Unit ID</TableCell>
                <TableCell>Mutual Matches</TableCell>
                <TableCell>Notes</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {focusUnits.map((unit) => (
                <TableRow key={unit.focus_unit_id}>
                  <TableCell>
                    <Box display="flex" alignItems="center" gap={1}>
                      {unit.focus_unit_id}
                      {checkHashMismatch(unit) && (
                        <Tooltip title="Coarse sorting may have been re-run. Unit ID may no longer correspond.">
                          <WarningIcon color="warning" fontSize="small" />
                        </Tooltip>
                      )}
                    </Box>
                  </TableCell>
                  <TableCell>{unit.bin_filename}</TableCell>
                  <TableCell>{unit.unit_id}</TableCell>
                  <TableCell>
                    {unit.mutual_matches && unit.mutual_matches.length > 0 ? (
                      <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                        {unit.mutual_matches.map((match, idx) => (
                          <Chip
                            key={idx}
                            label={`${match.bin_filename} (U${match.unit_id}) - ${(match.overall_score * 100).toFixed(1)}%`}
                            size="small"
                            color="primary"
                            variant="outlined"
                          />
                        ))}
                      </Stack>
                    ) : (
                      <Typography variant="body2" color="text.secondary">
                        <em>None</em>
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    {editingId === unit.focus_unit_id ? (
                      <TextField
                        fullWidth
                        size="small"
                        multiline
                        value={editNotes}
                        onChange={(e) => setEditNotes(e.target.value)}
                        disabled={isSaving}
                      />
                    ) : (
                      <Typography variant="body2">
                        {unit.notes || <em>No notes</em>}
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell align="right">
                    {editingId === unit.focus_unit_id ? (
                      <Box display="flex" gap={1} justifyContent="flex-end">
                        <IconButton
                          size="small"
                          color="primary"
                          onClick={() => handleSaveEdit(unit.focus_unit_id)}
                          disabled={isSaving}
                        >
                          <SaveIcon />
                        </IconButton>
                        <IconButton
                          size="small"
                          onClick={handleCancelEdit}
                          disabled={isSaving}
                        >
                          <CloseIcon />
                        </IconButton>
                      </Box>
                    ) : (
                      <Box display="flex" gap={1} justifyContent="flex-end">
                        <IconButton
                          size="small"
                          color="primary"
                          onClick={() => handleEditClick(unit)}
                        >
                          <EditIcon />
                        </IconButton>
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => handleDeleteClick(unit)}
                        >
                          <DeleteIcon />
                        </IconButton>
                      </Box>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>

        {/* Focus Unit Detail Sections */}
        <Box sx={{ mt: 4 }}>
          <Typography variant="h5" gutterBottom>
            Detailed Analysis
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Expand each focus unit to view spike train data and firing rate analysis across all matched recordings.
          </Typography>
          <Stack spacing={2}>
            {focusUnits.map((unit) => (
              <FocusUnitDetailSection key={unit.focus_unit_id} focusUnit={unit} />
            ))}
          </Stack>
        </Box>
        </>
      )}

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={handleDeleteCancel}>
        <DialogTitle>Delete Focus Unit</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete focus unit{' '}
            <strong>{unitToDelete?.focus_unit_id}</strong> ({unitToDelete?.bin_filename}, Unit{' '}
            {unitToDelete?.unit_id})?
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleDeleteCancel} disabled={isDeleting}>
            Cancel
          </Button>
          <Button onClick={handleDeleteConfirm} color="error" disabled={isDeleting}>
            {isDeleting ? 'Deleting...' : 'Delete'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
