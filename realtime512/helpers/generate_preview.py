import json
import os

import numpy as np

import figpack.views as vv
import figpack_spike_sorting.views as ssv

from ..figpack_realtime512.MEAMovie import MEAMovie
from ..figpack_realtime512.MEASpikeFramesMovie import MEASpikeFramesMovie
from ..figpack_realtime512.MEAFiringRatesAndAmplitudes import MEAFiringRatesAndAmplitudes
from ..figpack_realtime512.TemplatesView import TemplatesView
from ..figpack_realtime512.ClusterSeparationView import ClusterSeparationView, ClusterSeparationViewItem
from .coarse_sorting import find_nearest_neighbors


def generate_preview(
    *,
    filt_path: str,
    shift_path: str,
    stats_path: str,
    high_activity_intervals: list,
    coarse_sorting_path: str,
    n_channels: int,
    sampling_frequency: float,
    electrode_coords: np.ndarray,
    preview_path: str
):
    # Time series preview for filtered data
    filt_time_series = generate_time_series_preview(
        data_path=filt_path,
        channel_indices=list(range(min(64, n_channels))),
        sampling_frequency=sampling_frequency,
        num_channels=n_channels,
        high_activity_intervals=high_activity_intervals,
        name="Filtered Data (channels 1-64)"
    )

    # Movie preview for filtered data
    filt_movie = MEAMovie(
        raw_data=np.fromfile(filt_path, dtype=np.int16).reshape(-1, n_channels),
        electrode_coords=electrode_coords,
        start_time_sec=0,
        sampling_frequency_hz=sampling_frequency
    )

    # Spike stats view
    with open(stats_path, 'r') as f:
        stats = json.load(f)
    mean_firing_rates = np.array(stats['mean_firing_rates'], dtype=np.float32)
    mean_spike_amplitudes = np.array(stats['mean_spike_amplitudes'], dtype=np.float32)
    spike_stats = MEAFiringRatesAndAmplitudes(
        electrode_coords=electrode_coords,
        mean_firing_rates=mean_firing_rates.reshape(1, -1),
        mean_spike_amplitudes=mean_spike_amplitudes.reshape(1, -1)
    )

    # Templates view
    templates_path = coarse_sorting_path + "/templates.npy"
    if os.path.exists(templates_path):
        templates = np.load(templates_path)
        templates_view = TemplatesView(
            templates=templates,
            electrode_coords=electrode_coords
        )
    else:
        templates_view = vv.Markdown(
            content="Templates file not found."
        )
    
    # Autocorrelograms, Cluster Separation, and Spike Frames Movie
    spike_times_path = coarse_sorting_path + "/spike_times.npy"
    spike_labels_path = coarse_sorting_path + "/spike_labels.npy"
    if os.path.exists(spike_times_path) and os.path.exists(spike_labels_path):
        spike_times = np.load(spike_times_path)
        spike_labels = np.load(spike_labels_path)
        autocorrelograms_view = create_autocorrelograms_view(
            spike_times=spike_times,
            spike_labels=spike_labels
        )
        
        # Create cluster separation view and spike frames movie
        if os.path.exists(templates_path) and os.path.exists(shift_path):
            print('Creating cluster separation view...')
            shifted_data = np.fromfile(shift_path, dtype=np.int16).reshape(-1, n_channels)
            cluster_separation_view = create_cluster_separation_view(
                templates=templates,
                shifted_data=shifted_data,
                spike_times=spike_times,
                spike_labels=spike_labels,
                sampling_frequency=sampling_frequency,
                num_neighbors=10
            )
            
            # Create spike frames movie
            print('Creating spike frames movie...')
            spike_frames_movie = create_spike_frames_movie(
                shifted_data=shifted_data,
                spike_times=spike_times,
                spike_labels=spike_labels,
                electrode_coords=electrode_coords,
                sampling_frequency=sampling_frequency
            )
        else:
            cluster_separation_view = vv.Markdown(
                content="Templates or shifted data not found."
            )
            spike_frames_movie = vv.Markdown(
                content="Shifted data not found."
            )
    else:
        autocorrelograms_view = vv.Markdown(
            content="Spike times or labels file not found."
        )
        cluster_separation_view = vv.Markdown(
            content="Spike times or labels file not found."
        )
        spike_frames_movie = vv.Markdown(
            content="Spike times or labels file not found."
        )

    #########################################################
    # Combine into tab layout
    #########################################################
    tab_items = [
        vv.TabLayoutItem(
            view=spike_stats,
            label="Spike Stats"
        ),
        vv.TabLayoutItem(
            view=templates_view,
            label="Coarse Templates"
        ),
        vv.TabLayoutItem(
            view=cluster_separation_view,
            label="Cluster Separation"
        ),
        vv.TabLayoutItem(
            view=autocorrelograms_view,
            label="Coarse Autocorrelograms"
        ),
        vv.TabLayoutItem(
            view=spike_frames_movie,
            label="Spike Frames"
        ),
        vv.TabLayoutItem(
            view=filt_movie,
            label="Filt Movie"
        ),
        vv.TabLayoutItem(
            view=filt_time_series,
            label="Filt TS"
        )
    ]
    tabs = vv.TabLayout(
        items=tab_items
    )

    tabs.save(
        preview_path,
        title=f"Realtime512 Preview"
    )

def create_cluster_separation_view(
    *,
    templates: np.ndarray,
    shifted_data: np.ndarray,
    spike_times: np.ndarray,
    spike_labels: np.ndarray,
    sampling_frequency: float,
    num_neighbors: int = 5
):
    """
    Create a cluster separation view showing discriminant projections.
    
    Parameters
    ----------
    templates : np.ndarray
        Templates array of shape (num_units, num_channels)
    shifted_data : np.ndarray
        Shifted data array of shape (num_frames, num_channels)
    spike_times : np.ndarray
        Spike times in seconds
    spike_labels : np.ndarray
        Spike labels (1-based)
    sampling_frequency : float
        Sampling frequency in Hz
    num_neighbors : int
        Number of nearest neighbors to compute for each unit
    
    Returns
    -------
    ClusterSeparationView
    """
    num_units = templates.shape[0]
    
    # Find nearest neighbors in template space
    print(f'Finding {num_neighbors} nearest neighbors for each unit in template space...')
    neighbor_indices = find_nearest_neighbors(templates, num_neighbors=num_neighbors + 1)
    
    # Build separation items for each unit and its neighbors
    # Track processed pairs to avoid redundancy
    processed_pairs = set()
    separation_items = []
    
    for unit_idx in range(num_units):
        unit_id = unit_idx + 1  # 1-based
        
        # Get neighbor indices (excluding self at index 0)
        neighbor_unit_indices = neighbor_indices[unit_idx, 1:]
        
        for neighbor_idx in neighbor_unit_indices:
            neighbor_id = neighbor_idx + 1  # 1-based
            
            # Skip if we've already processed this pair (in either order)
            pair_key = tuple(sorted([unit_id, neighbor_id]))
            if pair_key in processed_pairs:
                continue
            processed_pairs.add(pair_key)
            
            # Get spike indices for both units
            spike_inds_1 = np.where(spike_labels == unit_id)[0]
            spike_inds_2 = np.where(spike_labels == neighbor_id)[0]
            
            if len(spike_inds_1) < 2 or len(spike_inds_2) < 2:
                continue
            
            # Compute discriminant direction (difference of template means)
            template_1 = templates[unit_idx, :]
            template_2 = templates[neighbor_idx, :]
            discriminant_direction = template_2 - template_1
            norm = np.linalg.norm(discriminant_direction)
            if norm > 0:
                discriminant_direction = discriminant_direction / norm
            else:
                continue
            
            # Get spike frame indices
            spike_frames_1 = (spike_times[spike_inds_1] * sampling_frequency).astype(int)
            spike_frames_2 = (spike_times[spike_inds_2] * sampling_frequency).astype(int)
            
            # Filter out invalid frame indices
            valid_frames_1 = (spike_frames_1 >= 0) & (spike_frames_1 < shifted_data.shape[0])
            valid_frames_2 = (spike_frames_2 >= 0) & (spike_frames_2 < shifted_data.shape[0])
            spike_frames_1 = spike_frames_1[valid_frames_1]
            spike_frames_2 = spike_frames_2[valid_frames_2]
            
            if len(spike_frames_1) == 0 or len(spike_frames_2) == 0:
                continue
            
            # Extract spike waveforms and project onto discriminant direction
            spike_waveforms_1 = shifted_data[spike_frames_1, :]
            spike_waveforms_2 = shifted_data[spike_frames_2, :]
            
            projections_1 = np.dot(spike_waveforms_1, discriminant_direction)
            projections_2 = np.dot(spike_waveforms_2, discriminant_direction)
            
            # Create separation item
            item = ClusterSeparationViewItem(
                unit_id_1=unit_id,
                unit_id_2=neighbor_id,
                projections_1=projections_1,
                projections_2=projections_2
            )
            separation_items.append(item)
    
    print(f'Created {len(separation_items)} separation items')
    
    return ClusterSeparationView(separation_items=separation_items)

def create_autocorrelograms_view(
    *,
    spike_times: np.ndarray,
    spike_labels: np.ndarray
):
    """Create a view with autocorrelograms for each unit."""
    num_units = np.max(spike_labels)
    autocorrelograms = []
    for unit_id in range(1, num_units + 1):
        spike_train_sec = spike_times[spike_labels == unit_id]
        if len(spike_train_sec) < 2:
            continue
        bin_edges_sec, bin_counts = compute_unit_autocorrelogram(
            spike_train_sec,
            bin_size_ms=1,
            window_ms=100
        )
        autocorrelogram = ssv.AutocorrelogramItem(
            unit_id=str(unit_id),
            bin_edges_sec=bin_edges_sec,
            bin_counts=bin_counts
        )
        autocorrelograms.append(autocorrelogram)
    view = ssv.Autocorrelograms(
        autocorrelograms=autocorrelograms
    )
    return view

def compute_unit_autocorrelogram(spike_train, bin_size_ms=1.0, window_ms=100.0):
    """
    Compute the autocorrelogram for a single unit's spike train.

    Args:
        spike_train: 1D numpy array of spike times in seconds
        bin_size_ms: Size of each bin in milliseconds
        window_ms: Total window size in milliseconds (centered around zero)

    Returns:
        bin_edges_sec: 1D numpy array of bin edges in seconds
        bin_counts: 1D numpy array of spike counts per bin
    """
    # based off of compute_correlogram_data below
    num_bins = int(window_ms / bin_size_ms)
    if num_bins % 2 == 0:
        num_bins = num_bins - 1  # odd number of bins
    num_bins_half = int((num_bins + 1) / 2)
    bin_edges_msec = np.array(
        (np.arange(num_bins + 1) - num_bins / 2) * bin_size_ms, dtype=np.float32
    )
    bin_counts = np.zeros((num_bins,), dtype=np.int32)
    times1 = spike_train
    offset = 1
    while True:
        if offset >= len(times1):
            break
        deltas_msec = (
            (times1[offset:] - times1[:-offset])
            * 1000.0
        )
        deltas_msec = deltas_msec[deltas_msec <= bin_edges_msec[-1]]
        if len(deltas_msec) == 0:
            break
        for i in range(num_bins_half):
            start_msec = bin_edges_msec[num_bins_half - 1 + i]
            end_msec = bin_edges_msec[num_bins_half + i]
            ct = len(
                deltas_msec[(start_msec <= deltas_msec) & (deltas_msec < end_msec)]
            )
            bin_counts[num_bins_half - 1 + i] += ct
            bin_counts[num_bins_half - 1 - i] += ct
        offset = offset + 1
    return (bin_edges_msec / 1000).astype(np.float32), bin_counts

def create_spike_frames_movie(
    *,
    shifted_data: np.ndarray,
    spike_times: np.ndarray,
    spike_labels: np.ndarray,
    electrode_coords: np.ndarray,
    sampling_frequency: float
):
    """
    Create a spike frames movie view showing only frames that contain spikes.
    
    Parameters
    ----------
    shifted_data : np.ndarray
        Shifted data array of shape (num_frames, num_channels)
    spike_times : np.ndarray
        Spike times in seconds
    spike_labels : np.ndarray
        Spike labels (1-based unit IDs)
    electrode_coords : np.ndarray
        Electrode coordinates array of shape (num_channels, 2)
    sampling_frequency : float
        Sampling frequency in Hz
    
    Returns
    -------
    MEASpikeFramesMovie
    """
    # Convert spike times to frame indices
    spike_frame_indices = (spike_times * sampling_frequency).astype(int)
    
    # Filter out invalid frame indices
    valid_mask = (spike_frame_indices >= 0) & (spike_frame_indices < shifted_data.shape[0])
    spike_frame_indices = spike_frame_indices[valid_mask]
    spike_times_valid = spike_times[valid_mask]
    spike_labels_valid = spike_labels[valid_mask]
    
    if len(spike_frame_indices) == 0:
        # Return empty view
        return MEASpikeFramesMovie(
            spike_frames_data=np.zeros((0, shifted_data.shape[1]), dtype=np.int16),
            electrode_coords=electrode_coords,
            spike_times_sec=np.array([], dtype=np.float32),
            spike_labels=np.array([], dtype=np.int32),
            sampling_frequency_hz=sampling_frequency
        )
    
    # Extract spike frames
    spike_frames_data = shifted_data[spike_frame_indices, :]
    
    print(f'Created spike frames movie with {len(spike_frame_indices)} frames')
    
    return MEASpikeFramesMovie(
        spike_frames_data=spike_frames_data,
        electrode_coords=electrode_coords,
        spike_times_sec=spike_times_valid,
        spike_labels=spike_labels_valid,
        sampling_frequency_hz=sampling_frequency
    )

def generate_time_series_preview(
    *,
    data_path: str,
    channel_indices: list,
    sampling_frequency: float,
    num_channels: int,
    high_activity_intervals: list,
    name: str
):
    """Generate a figpack TimeSeriesGraph preview with high activity intervals."""
    V = vv.TimeseriesGraph()
    V.add_uniform_series(
        name=name,
        start_time_sec=0,
        sampling_frequency_hz=sampling_frequency,
        data=np.fromfile(data_path, dtype=np.int16).reshape(-1, num_channels)[:, channel_indices],
        auto_channel_spacing=50
    )
    t_start = np.array([i[0] for i in high_activity_intervals], dtype=np.float32)
    t_end = np.array([i[1] for i in high_activity_intervals], dtype=np.float32)
    V.add_interval_series(
        name="High Activity",
        t_start=t_start,
        t_end=t_end,
        color="yellow",
        alpha=0.3
    )
    return V
