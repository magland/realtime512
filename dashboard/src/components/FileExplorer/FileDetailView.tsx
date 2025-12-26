import { useCallback, useMemo, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Alert,
  CircularProgress,
  Button,
  Stack,
  Paper,
  IconButton,
  Snackbar,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Checkbox,
} from '@mui/material';
import {
  CheckCircle as CheckIcon,
  Cancel as ErrorIcon,
  ArrowBack as ArrowBackIcon,
  NavigateBefore as NavigateBeforeIcon,
  NavigateNext as NavigateNextIcon,
  OpenInNew as OpenInNewIcon,
  ContentCopy as ContentCopyIcon,
  Star as StarIcon,
} from '@mui/icons-material';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { usePolling } from '../../hooks/usePolling';
import { api, getApiUrl } from '../../services/api';
import { navigateWithQuery } from '../../utils/navigation';
import instructionsTemplate from './python-instructions.py?raw';

export function FileDetailView() {
  const { filename: encodedFilename } = useParams<{ filename: string }>();
  const navigate = useNavigate();
  const filename = encodedFilename ? decodeURIComponent(encodedFilename) : '';
  const fetchFiles = useCallback(() => api.getFiles(), []);
  const fetchConfig = useCallback(() => api.getConfig(), []);
  const [copySnackbarOpen, setCopySnackbarOpen] = useState(false);
  const [addUnitsDialogOpen, setAddUnitsDialogOpen] = useState(false);
  const [availableUnits, setAvailableUnits] = useState<{ unit_id: number; num_spikes: number }[]>([]);
  const [selectedUnitIds, setSelectedUnitIds] = useState<number[]>([]);
  const [isLoadingUnits, setIsLoadingUnits] = useState(false);
  const [isAddingUnits, setIsAddingUnits] = useState(false);
  const [addUnitsSuccess, setAddUnitsSuccess] = useState(false);

  const {
    data: filesData,
    error: filesError,
    isLoading: filesLoading,
  } = usePolling(fetchFiles, { interval: 5000 });

  const {
    data: configData,
    error: configError,
    isLoading: configLoading,
  } = usePolling(fetchConfig, { interval: 5000 });

  const file = filesData?.files.find(f => f.filename === filename);

  // Sort files alphabetically to determine previous/next
  const sortedFiles = (filesData?.files || []).sort((a, b) => 
    a.filename.localeCompare(b.filename)
  );
  
  const currentIndex = sortedFiles.findIndex(f => f.filename === filename);
  const previousFile = currentIndex > 0 ? sortedFiles[currentIndex - 1] : null;
  const nextFile = currentIndex >= 0 && currentIndex < sortedFiles.length - 1 ? sortedFiles[currentIndex + 1] : null;

  // Replace template variables in markdown
  const renderedInstructions = useMemo(() => {
    if (!file || !configData) return '';
    
    return instructionsTemplate
      .replace(/\{\{\s*filename\s*\}\}/g, file.filename)
      .replace(/\{\{\s*num_channels\s*\}\}/g, String(configData.n_channels))
      .replace(/\{\{\s*sampling_frequency\s*\}\}/g, String(configData.sampling_frequency))
      .replace(/\{\{\s*num_frames\s*\}\}/g, String(file.num_frames || 0));
  }, [file, configData]);

  const getPreviewUrl = (fname: string) => {
    const apiUrl = getApiUrl();
    return `${apiUrl}/preview/${fname}/index.html?ext_dev_x=figpack-realtime512:http://localhost:5174/figpack_realtime512.js`;
  };

  const handleCopyCode = async () => {
    try {
      await navigator.clipboard.writeText(renderedInstructions);
      setCopySnackbarOpen(true);
    } catch (err) {
      console.error('Failed to copy code:', err);
    }
  };

  const handleAddToFocusUnits = async () => {
    if (!file) return;
    
    setIsLoadingUnits(true);
    setAddUnitsDialogOpen(true);
    
    try {
      const response = await api.getCoarseSortingUnits(file.filename);
      setAvailableUnits(response.units);
    } catch (err) {
      console.error('Failed to load units:', err);
      setAvailableUnits([]);
    } finally {
      setIsLoadingUnits(false);
    }
  };

  const handleToggleUnit = (unitId: number) => {
    setSelectedUnitIds(prev =>
      prev.includes(unitId)
        ? prev.filter(id => id !== unitId)
        : [...prev, unitId]
    );
  };

  const handleConfirmAddUnits = async () => {
    if (!file || selectedUnitIds.length === 0) return;
    
    setIsAddingUnits(true);
    try {
      const units = selectedUnitIds.map(unit_id => ({
        bin_filename: file.filename,
        unit_id,
      }));
      await api.addFocusUnits(units);
      setAddUnitsSuccess(true);
      setAddUnitsDialogOpen(false);
      setSelectedUnitIds([]);
    } catch (err) {
      console.error('Failed to add units:', err);
    } finally {
      setIsAddingUnits(false);
    }
  };

  const handleCancelAddUnits = () => {
    setAddUnitsDialogOpen(false);
    setSelectedUnitIds([]);
  };

  if (filesLoading || configLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress />
      </Box>
    );
  }

  if (filesError || configError) {
    return (
      <Alert severity="error">
        Error loading data: {filesError?.message || configError?.message}
      </Alert>
    );
  }

  if (!file) {
    return (
      <Box>
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate(navigateWithQuery('/files'))} sx={{ mb: 2 }}>
          Back to File Explorer
        </Button>
        <Alert severity="warning">
          File not found: {filename}
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" gap={2} mb={2} flexWrap="wrap">
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate(navigateWithQuery('/files'))}>
          Back to File Explorer
        </Button>
        <Box display="flex" gap={1}>
          <Button
            startIcon={<NavigateBeforeIcon />}
            onClick={() => previousFile && navigate(navigateWithQuery(`/files/${encodeURIComponent(previousFile.filename)}`))}
            disabled={!previousFile}
            variant="outlined"
          >
            Previous
          </Button>
          <Button
            endIcon={<NavigateNextIcon />}
            onClick={() => nextFile && navigate(navigateWithQuery(`/files/${encodeURIComponent(nextFile.filename)}`))}
            disabled={!nextFile}
            variant="outlined"
          >
            Next
          </Button>
        </Box>
      </Box>

      <Typography variant="h4" gutterBottom>
        {file.filename}
      </Typography>

      {/* Add to Focus Units */}
      {file.has_coarse_sorting && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Box display="flex" justifyContent="space-between" alignItems="center">
              <Typography variant="h6">
                Focus Units
              </Typography>
              <Button
                variant="contained"
                startIcon={<StarIcon />}
                onClick={handleAddToFocusUnits}
              >
                Add to Focus Units
              </Button>
            </Box>
          </CardContent>
        </Card>
      )}

      {/* File Overview */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            File Overview
          </Typography>
          <Box display="flex" justifyContent="space-between" alignItems="flex-start" flexWrap="wrap" gap={2}>
            <Box flex="1" minWidth="200px">
              <Stack spacing={0.5}>
                {file.duration_sec !== undefined && (
                  <Typography variant="body2" color="text.secondary">
                    <strong>Duration:</strong> {file.duration_sec.toFixed(2)} seconds
                  </Typography>
                )}
                {file.num_frames !== undefined && (
                  <Typography variant="body2" color="text.secondary">
                    <strong>Frames:</strong> {file.num_frames.toLocaleString()}
                  </Typography>
                )}
                {file.size_bytes !== undefined && (
                  <Typography variant="body2" color="text.secondary">
                    <strong>Size:</strong> {(file.size_bytes / 1024 / 1024).toFixed(2)} MB
                  </Typography>
                )}
              </Stack>
            </Box>

            <Box>
              <Typography variant="subtitle2" gutterBottom>
                Processing Status
              </Typography>
              <Box display="flex" flexWrap="wrap" gap={1}>
                <Chip
                  size="small"
                  label="Filtered"
                  color={file.has_filt ? 'success' : 'default'}
                  icon={file.has_filt ? <CheckIcon /> : <ErrorIcon />}
                />
                <Chip
                  size="small"
                  label="Shifted"
                  color={file.has_shifted ? 'success' : 'default'}
                  icon={file.has_shifted ? <CheckIcon /> : <ErrorIcon />}
                />
                <Chip
                  size="small"
                  label="Coarse Sorting"
                  color={file.has_coarse_sorting ? 'success' : 'default'}
                  icon={file.has_coarse_sorting ? <CheckIcon /> : <ErrorIcon />}
                />
                <Chip
                  size="small"
                  label="High Activity"
                  color={file.has_high_activity ? 'success' : 'default'}
                  icon={file.has_high_activity ? <CheckIcon /> : <ErrorIcon />}
                />
                <Chip
                  size="small"
                  label="Statistics"
                  color={file.has_stats ? 'success' : 'default'}
                  icon={file.has_stats ? <CheckIcon /> : <ErrorIcon />}
                />
                <Chip
                  size="small"
                  label="Preview"
                  color={file.has_preview ? 'success' : 'default'}
                  icon={file.has_preview ? <CheckIcon /> : <ErrorIcon />}
                />
              </Box>
            </Box>
          </Box>
        </CardContent>
      </Card>

      {/* Preview */}
      <Box mb={3}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h6">
            Preview
          </Typography>
          {file.has_preview && (
            <Button
              variant="outlined"
              size="small"
              startIcon={<OpenInNewIcon />}
              onClick={() => window.open(getPreviewUrl(file.filename), '_blank')}
            >
              Open in New Tab
            </Button>
          )}
        </Box>
        {file.has_preview ? (
          <Paper sx={{ p: 0, height: 'calc(100vh - 400px)', minHeight: '600px' }}>
            <iframe
              src={getPreviewUrl(file.filename)}
              style={{
                width: '100%',
                height: '100%',
                border: 'none',
              }}
              title={`Preview of ${file.filename}`}
            />
          </Paper>
        ) : (
          <Alert severity="info">
            Preview not available yet. Previews are generated after filtering and shifting.
          </Alert>
        )}
      </Box>

      {/* Python Instructions */}
      <Card>
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">
              Python Code
            </Typography>
            <IconButton 
              onClick={handleCopyCode}
              size="small"
              color="primary"
              title="Copy code to clipboard"
            >
              <ContentCopyIcon />
            </IconButton>
          </Box>
          <Box
            sx={{
              maxHeight: '600px',
              overflowY: 'auto',
              '& pre': {
                backgroundColor: '#f5f5f5',
                padding: 2,
                borderRadius: 1,
                overflow: 'auto',
                margin: 0,
              },
              '& code': {
                fontFamily: 'monospace',
                fontSize: '0.9em',
              },
              '& pre code': {
                backgroundColor: 'transparent',
                padding: 0,
              },
            }}
          >
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {"```python\n" + renderedInstructions + "\n```"}
            </ReactMarkdown>
          </Box>
        </CardContent>
      </Card>

      {/* Add Units Dialog */}
      <Dialog open={addUnitsDialogOpen} onClose={handleCancelAddUnits} maxWidth="sm" fullWidth>
        <DialogTitle>Add Units to Focus Units</DialogTitle>
        <DialogContent>
          {isLoadingUnits ? (
            <Box display="flex" justifyContent="center" p={3}>
              <CircularProgress />
            </Box>
          ) : availableUnits.length === 0 ? (
            <Alert severity="info">No units found in coarse sorting</Alert>
          ) : (
            <List>
              {availableUnits.map(unit => (
                <ListItem key={unit.unit_id} disablePadding>
                  <ListItemButton onClick={() => handleToggleUnit(unit.unit_id)} dense>
                    <Checkbox
                      edge="start"
                      checked={selectedUnitIds.includes(unit.unit_id)}
                      tabIndex={-1}
                      disableRipple
                    />
                    <ListItemText
                      primary={`Unit ${unit.unit_id}`}
                      secondary={`${unit.num_spikes.toLocaleString()} spikes`}
                    />
                  </ListItemButton>
                </ListItem>
              ))}
            </List>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCancelAddUnits} disabled={isAddingUnits}>
            Cancel
          </Button>
          <Button
            onClick={handleConfirmAddUnits}
            variant="contained"
            disabled={isAddingUnits || selectedUnitIds.length === 0}
          >
            {isAddingUnits ? 'Adding...' : `Add ${selectedUnitIds.length} Unit${selectedUnitIds.length !== 1 ? 's' : ''}`}
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={copySnackbarOpen}
        autoHideDuration={2000}
        onClose={() => setCopySnackbarOpen(false)}
        message="Code copied to clipboard"
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      />

      <Snackbar
        open={addUnitsSuccess}
        autoHideDuration={3000}
        onClose={() => setAddUnitsSuccess(false)}
        message="Units added to focus units successfully"
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      />
    </Box>
  );
}
