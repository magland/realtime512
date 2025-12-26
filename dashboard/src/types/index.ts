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

// Focus Units Types
export interface MutualMatch {
  bin_filename: string;
  unit_id: number;
  overall_score: number;
}

export interface FocusUnit {
  focus_unit_id: string;
  bin_filename: string;
  unit_id: number;
  notes: string;
  spike_labels_hash: string;
  mutual_matches?: MutualMatch[];
}

export interface FocusUnitsResponse {
  focus_units: FocusUnit[];
}

export interface CoarseSortingUnit {
  unit_id: number;
  num_spikes: number;
}

export interface CoarseSortingUnitsResponse {
  units: CoarseSortingUnit[];
  spike_labels_hash: string;
}

// Spike Train Types
export interface SpikeTrainSegment {
  bin_filename: string;
  unit_id: number | null;
  start_time_offset: number;
  end_time_offset: number;
  num_spikes: number;
  spike_times: number[];
  is_focus_unit: boolean;
  is_gap?: boolean;
}

export interface SpikeTrainResponse {
  focus_unit_id: string;
  total_spikes: number;
  total_duration_sec: number;
  segments: SpikeTrainSegment[];
}
