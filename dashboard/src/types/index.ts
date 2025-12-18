// API Response Types

export interface Config {
  filter_params: {
    lowcut: number;
    highcut: number;
    order: number;
  };
  sampling_frequency: number;
  n_channels: number;
  detect_threshold_for_spike_stats: number;
}

export interface FileInfo {
  filename: string;
  has_filt: boolean;
  has_shifted: boolean;
  has_coarse_sorting: boolean;
  has_high_activity: boolean;
  has_stats: boolean;
  has_preview: boolean;
  size_bytes?: number;
  num_frames?: number;
  duration_sec?: number;
}

export interface FilesResponse {
  files: FileInfo[];
}

export interface ShiftCoefficients {
  c_x: number;
  c_y: number;
}

export interface HighActivityInterval {
  start_sec: number;
  end_sec: number;
}

export interface HighActivityResponse {
  high_activity_intervals: HighActivityInterval[];
}

export interface StatsResponse {
  mean_firing_rates: number[];
  mean_spike_amplitudes: number[];
}

export interface BinaryDataResponse {
  data: Int16Array;
  numFrames: number;
  numChannels: number;
  samplingFrequency: number;
  startSec: number;
  endSec: number;
}

export type DataType = 'raw' | 'filt' | 'shifted';
