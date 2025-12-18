import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Card,
  CardContent,
  CircularProgress,
  Typography,
  Chip,
  Alert,
  Button,
  Stack,
} from '@mui/material';
import {
  CheckCircle as CheckIcon,
  Cancel as ErrorIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { usePolling } from '../../hooks/usePolling';
import { api } from '../../services/api';
import { navigateWithQuery } from '../../utils/navigation';

export function FileExplorerView() {
  const navigate = useNavigate();

  const fetchFiles = useCallback(() => api.getFiles(), []);

  const {
    data: filesData,
    error: filesError,
    isLoading: filesLoading,
  } = usePolling(fetchFiles, { interval: 5000 });


  if (filesLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress />
      </Box>
    );
  }

  if (filesError) {
    return (
      <Alert severity="error">
        Error loading files: {filesError.message}
      </Alert>
    );
  }

  // Sort files in reverse alphabetical order
  const files = (filesData?.files || []).sort((a, b) => 
    b.filename.localeCompare(a.filename)
  );

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">
          File Explorer
        </Typography>
        <Button
          startIcon={<RefreshIcon />}
          variant="outlined"
          onClick={() => window.location.reload()}
        >
          Refresh
        </Button>
      </Box>

      {files.length === 0 ? (
        <Alert severity="info">
          No files found. Waiting for data to be processed...
        </Alert>
      ) : (
        <Stack spacing={2}>
          {files.map((file) => (
            <Card
              key={file.filename}
              variant="outlined"
              sx={{
                cursor: 'pointer',
                transition: 'all 0.2s',
                '&:hover': {
                  boxShadow: 3,
                },
              }}
              onClick={() => navigate(navigateWithQuery(`/files/${encodeURIComponent(file.filename)}`))}
            >
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="flex-start" flexWrap="wrap" gap={2}>
                  <Box flex="1" minWidth="200px">
                    <Typography variant="h6" gutterBottom>
                      {file.filename}
                    </Typography>
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
          ))}
        </Stack>
      )}
    </Box>
  );
}
