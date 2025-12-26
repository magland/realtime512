import { useState } from 'react';
import {
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Box,
  Typography,
  CircularProgress,
  Alert,
  Grid,
  Paper,
  Chip,
  Stack,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
} from '@mui/icons-material';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceArea,
} from 'recharts';
import type { FocusUnit, SpikeTrainResponse } from '../../types';
import { api } from '../../services/api';

interface FocusUnitDetailSectionProps {
  focusUnit: FocusUnit;
}

export function FocusUnitDetailSection({ focusUnit }: FocusUnitDetailSectionProps) {
  const [expanded, setExpanded] = useState(false);
  const [spikeTrainData, setSpikeTrainData] = useState<SpikeTrainResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [windowWidthMs, setWindowWidthMs] = useState(200);
  const [binSizeMs, setBinSizeMs] = useState(0.5);

  const handleExpand = async () => {
    if (!expanded && !spikeTrainData) {
      // Fetch data when expanding for the first time
      setLoading(true);
      setError(null);
      try {
        const data = await api.getSpikeTrainForFocusUnit(focusUnit.focus_unit_id);
        setSpikeTrainData(data);
      } catch (err) {
        console.error('Failed to fetch spike train data:', err);
        setError(err instanceof Error ? err.message : 'Failed to load spike train data');
      } finally {
        setLoading(false);
      }
    }
    setExpanded(!expanded);
  };

  // Compute firing rates from spike times
  const computeFiringRates = (data: SpikeTrainResponse, binSizeSec: number = 1.0) => {
    const numBins = Math.ceil(data.total_duration_sec / binSizeSec);
    const firingRates = new Array(numBins).fill(0);
    
    // Count spikes in each bin across all segments
    data.segments.forEach(segment => {
      segment.spike_times.forEach(spikeTime => {
        const binIdx = Math.floor(spikeTime / binSizeSec);
        if (binIdx >= 0 && binIdx < numBins) {
          firingRates[binIdx] += 1;
        }
      });
    });
    
    // Convert to chart data format
    return Array.from({ length: numBins }, (_, idx) => ({
      time: idx * binSizeSec,
      firingRate: firingRates[idx],
    }));
  };

  // Compute autocorrelogram from spike times
  const computeAutocorrelogram = (data: SpikeTrainResponse, windowMs: number = 200, binSizeMs: number = 0.5) => {
    // Collect all spike times across all segments
    const allSpikeTimes: number[] = [];
    data.segments.forEach(segment => {
      allSpikeTimes.push(...segment.spike_times);
    });
    
    // Sort spike times
    allSpikeTimes.sort((a, b) => a - b);
    
    // Convert parameters to seconds
    const windowSec = windowMs / 1000;
    const binSizeSec = binSizeMs / 1000;
    const halfWindow = windowSec / 2;
    
    // Calculate number of bins (symmetric around 0)
    const numBins = Math.floor(windowSec / binSizeSec);
    const counts = new Array(numBins).fill(0);
    
    // Compute autocorrelogram
    for (let i = 0; i < allSpikeTimes.length; i++) {
      const refTime = allSpikeTimes[i];
      
      // Look at spikes within the window
      for (let j = i + 1; j < allSpikeTimes.length; j++) {
        const diff = allSpikeTimes[j] - refTime;
        
        if (diff > halfWindow) break; // Beyond window, stop
        
        // Calculate bin index (symmetric)
        const binIdx = Math.floor((diff + halfWindow) / binSizeSec);
        if (binIdx >= 0 && binIdx < numBins) {
          counts[binIdx]++;
        }
        
        // Also add the negative lag (symmetric)
        const negBinIdx = Math.floor((-diff + halfWindow) / binSizeSec);
        if (negBinIdx >= 0 && negBinIdx < numBins && i !== j) {
          counts[negBinIdx]++;
        }
      }
    }
    
    // Convert to chart data format
    return Array.from({ length: numBins }, (_, idx) => ({
      lag: (idx * binSizeSec - halfWindow) * 1000, // Convert back to ms
      count: counts[idx],
    }));
  };

  const firingRateChartData = spikeTrainData ? computeFiringRates(spikeTrainData) : [];
  const autocorrelogramData = spikeTrainData ? computeAutocorrelogram(spikeTrainData, windowWidthMs, binSizeMs) : [];

  return (
    <Accordion expanded={expanded} onChange={handleExpand}>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Box display="flex" alignItems="center" gap={2}>
          <Typography variant="h6">{focusUnit.focus_unit_id}</Typography>
          <Chip
            label={`${focusUnit.bin_filename} - Unit ${focusUnit.unit_id}`}
            size="small"
            color="primary"
          />
        </Box>
      </AccordionSummary>
      <AccordionDetails>
        {loading && (
          <Box display="flex" justifyContent="center" alignItems="center" minHeight={200}>
            <CircularProgress />
          </Box>
        )}

        {error && (
          <Alert severity="error">
            {error}
          </Alert>
        )}

        {spikeTrainData && !loading && (
          <Box>
            {/* Summary Statistics */}
            <Grid container spacing={2} sx={{ mb: 3 }}>
              <Grid item xs={12} sm={4}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="body2" color="text.secondary">
                    Total Spikes
                  </Typography>
                  <Typography variant="h4">
                    {spikeTrainData.total_spikes.toLocaleString()}
                  </Typography>
                </Paper>
              </Grid>
              <Grid item xs={12} sm={4}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="body2" color="text.secondary">
                    Total Duration
                  </Typography>
                  <Typography variant="h4">
                    {spikeTrainData.total_duration_sec.toFixed(1)}s
                  </Typography>
                </Paper>
              </Grid>
              <Grid item xs={12} sm={4}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="body2" color="text.secondary">
                    Mean Firing Rate
                  </Typography>
                  <Typography variant="h4">
                    {(spikeTrainData.total_spikes / spikeTrainData.total_duration_sec).toFixed(1)} Hz
                  </Typography>
                </Paper>
              </Grid>
            </Grid>

            {/* Segment Timeline */}
            <Paper sx={{ p: 2, mb: 3 }}>
              <Typography variant="h6" gutterBottom>
                Recording Segments
              </Typography>
              <Stack spacing={1}>
                {spikeTrainData.segments.map((segment, idx) => (
                  <Box
                    key={idx}
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 1,
                      p: 1,
                      bgcolor: segment.is_gap ? 'grey.100' : segment.is_focus_unit ? 'primary.50' : 'secondary.50',
                      borderRadius: 1,
                    }}
                  >
                    <Chip
                      label={segment.bin_filename}
                      size="small"
                      color={segment.is_focus_unit ? 'primary' : 'default'}
                    />
                    {segment.is_gap ? (
                      <Chip label="No Match" size="small" color="default" variant="outlined" />
                    ) : (
                      <Chip label={`Unit ${segment.unit_id}`} size="small" />
                    )}
                    <Typography variant="body2" sx={{ ml: 'auto' }}>
                      {segment.start_time_offset.toFixed(1)}s - {segment.end_time_offset.toFixed(1)}s
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      ({(segment.end_time_offset - segment.start_time_offset).toFixed(1)}s, {segment.num_spikes.toLocaleString()} spikes)
                    </Typography>
                  </Box>
                ))}
              </Stack>
            </Paper>

            {/* Firing Rate Plot */}
            <Paper sx={{ p: 2, mb: 3 }}>
              <Typography variant="h6" gutterBottom>
                Firing Rate Over Time
              </Typography>
              <ResponsiveContainer width="100%" height={400}>
                <LineChart data={firingRateChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="time"
                    label={{ value: 'Time (s)', position: 'insideBottom', offset: -5 }}
                  />
                  <YAxis
                    label={{ value: 'Firing Rate (Hz)', angle: -90, position: 'insideLeft' }}
                  />
                  <Tooltip
                    formatter={(value: number) => [`${value.toFixed(2)} Hz`, 'Firing Rate']}
                    labelFormatter={(label) => `Time: ${label}s`}
                  />
                  <Legend />
                  
                  {/* Add shaded regions for gaps */}
                  {spikeTrainData.segments
                    .filter(seg => seg.is_gap)
                    .map((seg, idx) => (
                      <ReferenceArea
                        key={`gap-${idx}`}
                        x1={seg.start_time_offset}
                        x2={seg.end_time_offset}
                        fill="#e0e0e0"
                        fillOpacity={0.3}
                      />
                    ))}
                  
                  {/* Add subtle regions for different segments */}
                  {spikeTrainData.segments
                    .filter(seg => !seg.is_gap && !seg.is_focus_unit)
                    .map((seg, idx) => (
                      <ReferenceArea
                        key={`match-${idx}`}
                        x1={seg.start_time_offset}
                        x2={seg.end_time_offset}
                        fill="#1976d2"
                        fillOpacity={0.05}
                      />
                    ))}
                  
                  <Line
                    type="monotone"
                    dataKey="firingRate"
                    stroke="#1976d2"
                    strokeWidth={2}
                    dot={false}
                    name="Firing Rate"
                  />
                </LineChart>
              </ResponsiveContainer>
            </Paper>

            {/* Autocorrelogram */}
            <Paper sx={{ p: 2 }}>
              <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
                <Typography variant="h6">
                  Autocorrelogram
                </Typography>
                <Box display="flex" gap={2}>
                  <FormControl size="small" sx={{ minWidth: 150 }}>
                    <InputLabel>Window Width</InputLabel>
                    <Select
                      value={windowWidthMs}
                      label="Window Width"
                      onChange={(e) => setWindowWidthMs(Number(e.target.value))}
                    >
                      <MenuItem value={50}>50 ms</MenuItem>
                      <MenuItem value={100}>100 ms</MenuItem>
                      <MenuItem value={200}>200 ms</MenuItem>
                      <MenuItem value={500}>500 ms</MenuItem>
                      <MenuItem value={1000}>1000 ms</MenuItem>
                    </Select>
                  </FormControl>
                  <FormControl size="small" sx={{ minWidth: 150 }}>
                    <InputLabel>Bin Size</InputLabel>
                    <Select
                      value={binSizeMs}
                      label="Bin Size"
                      onChange={(e) => setBinSizeMs(Number(e.target.value))}
                    >
                      <MenuItem value={0.1}>0.1 ms</MenuItem>
                      <MenuItem value={0.25}>0.25 ms</MenuItem>
                      <MenuItem value={0.5}>0.5 ms</MenuItem>
                      <MenuItem value={1}>1 ms</MenuItem>
                      <MenuItem value={2}>2 ms</MenuItem>
                      <MenuItem value={5}>5 ms</MenuItem>
                    </Select>
                  </FormControl>
                </Box>
              </Box>
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={autocorrelogramData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="lag"
                    label={{ value: 'Lag (ms)', position: 'insideBottom', offset: -5 }}
                    tickFormatter={(value) => value.toFixed(1)}
                    type="number"
                    domain={['dataMin', 'dataMax']}
                    scale="linear"
                  />
                  <YAxis
                    label={{ value: 'Count', angle: -90, position: 'insideLeft' }}
                  />
                  <Tooltip
                    formatter={(value: number) => [`${value}`, 'Count']}
                    labelFormatter={(label) => `Lag: ${Number(label).toFixed(2)} ms`}
                  />
                  <Legend />
                  <Bar
                    dataKey="count"
                    fill="#2e7d32"
                    name="Autocorrelogram"
                    isAnimationActive={false}
                  />
                </BarChart>
              </ResponsiveContainer>
            </Paper>
          </Box>
        )}
      </AccordionDetails>
    </Accordion>
  );
}
