import { useCallback } from 'react';
import {
  Box,
  Card,
  CardContent,
  CircularProgress,
  Typography,
  Alert,
  Stack,
} from '@mui/material';
import {
  Settings as SettingsIcon,
} from '@mui/icons-material';
import { usePolling } from '../../hooks/usePolling';
import { api } from '../../services/api';

export function OverviewView() {
  const fetchConfig = useCallback(() => api.getConfig(), []);
  const fetchFiles = useCallback(() => api.getFiles(), []);
  const fetchShiftCoeffs = useCallback(() => api.getShiftCoefficients(), []);

  const {
    data: config,
    error: configError,
    isLoading: configLoading,
  } = usePolling(fetchConfig, { interval: 10000 });

  const {
    data: filesData,
    error: filesError,
    isLoading: filesLoading,
  } = usePolling(fetchFiles, { interval: 5000 });

  const {
    data: shiftCoeffs,
    error: shiftsError,
  } = usePolling(fetchShiftCoeffs, { interval: 10000 });

  if (configLoading || filesLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress />
      </Box>
    );
  }

  if (configError || filesError) {
    return (
      <Alert severity="error">
        Error loading data: {(configError || filesError)?.message}
      </Alert>
    );
  }

  const files = filesData?.files || [];
  const totalFiles = files.length;
  const processedFiles = files.filter(
    (f) => f.has_filt && f.has_shifted && f.has_coarse_sorting
  ).length;
  const totalDuration = files.reduce((sum, f) => sum + (f.duration_sec || 0), 0);

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Overview
      </Typography>

      <Stack spacing={3}>
        {/* Top Row - Config and Status */}
        <Box display="flex" gap={3} flexWrap="wrap">
          <Box flex="1" minWidth="300px">
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" mb={2}>
                  <SettingsIcon sx={{ mr: 1 }} />
                  <Typography variant="h6">Configuration</Typography>
                </Box>
                {config && (
                  <Stack spacing={1}>
                    <Typography variant="body2" color="text.secondary">
                      <strong>Sampling Frequency:</strong> {config.sampling_frequency} Hz
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      <strong>Channels:</strong> {config.n_channels}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      <strong>Filter Range:</strong> {config.filter_params.lowcut} -{' '}
                      {config.filter_params.highcut} Hz
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      <strong>Filter Order:</strong> {config.filter_params.order}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      <strong>Spike Threshold:</strong> {config.detect_threshold_for_spike_stats}
                    </Typography>
                  </Stack>
                )}
              </CardContent>
            </Card>
          </Box>

          <Box flex="1" minWidth="300px">
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Processing Status
                </Typography>
                <Stack spacing={1} mt={2}>
                  <Typography variant="body2" color="text.secondary">
                    <strong>Total Files:</strong> {totalFiles}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    <strong>Fully Processed:</strong> {processedFiles} / {totalFiles}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    <strong>Total Duration:</strong> {totalDuration.toFixed(2)} seconds
                  </Typography>
                  {shiftCoeffs && !shiftsError && (
                    <>
                      <Typography variant="body2" color="text.secondary">
                        <strong>Shift Coefficient X:</strong> {shiftCoeffs.c_x.toExponential(3)}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        <strong>Shift Coefficient Y:</strong> {shiftCoeffs.c_y.toExponential(3)}
                      </Typography>
                    </>
                  )}
                </Stack>
              </CardContent>
            </Card>
          </Box>
        </Box>
      </Stack>
    </Box>
  );
}
