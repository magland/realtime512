import numpy as np
from sklearn.neighbors import NearestNeighbors
import sklearn.cluster

def find_nearest_neighbors(data: np.ndarray, *, num_neighbors: int):
    """
    Find nearest neighbors for each data point.
    
    Parameters
    ----------
    data : np.ndarray
        Data array where each row is a data point
    num_neighbors : int
        Number of nearest neighbors to find
    
    Returns
    -------
    np.ndarray
        Array of indices of nearest neighbors for each data point
    """
    nbrs = NearestNeighbors(n_neighbors=num_neighbors, algorithm='auto').fit(data)
    distances, indices = nbrs.kneighbors(data)
    return indices

def cluster_kmeans(data: np.ndarray, *, num_clusters: int):
    """
    Cluster data using K-means algorithm.
    
    Parameters
    ----------
    data : np.ndarray
        Data array where each row is a data point
    num_clusters : int
        Number of clusters to create
    
    Returns
    -------
    np.ndarray
        Array of cluster labels (1-based)
    """
    kmeans = sklearn.cluster.KMeans(n_clusters=num_clusters, n_init=10)
    labels = kmeans.fit_predict(data)
    return labels + 1  # make labels 1-based

def compute_template_peak_channel_x_coordinate(templates: np.ndarray, electrode_coords: np.ndarray):
    """
    Compute the x-coordinate of the peak channel for each template.
    
    Parameters
    ----------
    templates : np.ndarray
        Array of templates, shape (num_templates, num_channels)
    electrode_coords : np.ndarray
        Array of electrode coordinates, shape (num_channels, 2)
    
    Returns
    -------
    np.ndarray
        Array of x-coordinates, shape (num_templates, 1)
    """
    num_templates = templates.shape[0]
    template_x_coords = np.zeros((num_templates, 1), dtype=np.float32)
    electrode_coords = np.array(electrode_coords)
    for k in range(num_templates):
        template = templates[k, :]
        peak_channel = np.argmin(template)
        template_x_coords[k, 0] = electrode_coords[peak_channel, 0]
    return template_x_coords

def detect_spikes_single_channel(data: np.ndarray, threshold: float, sign: int, window_size: int):
    """
    Detect spikes in a single channel based on threshold crossings.
    Uses the existing multichannel detection method.
    
    Parameters
    ----------
    data : np.ndarray
        1D array of data values
    threshold : float
        Detection threshold
    sign : int
        Sign of spikes to detect (-1 for negative, 1 for positive)
    window_size : int
        Window size for local maximum detection
        
    Returns
    -------
    spike_inds : np.ndarray
        Indices of detected spikes
    """
    from .channel_spike_stats import detect_spikes_multichannel
    
    # Use the existing multichannel function
    data2 = data.reshape(-1, 1)  # make it 2D
    spike_mask = detect_spikes_multichannel(data2, threshold=threshold, sign=sign, window_size=window_size)
    spike_inds = np.where(spike_mask[:, 0])[0]
    return spike_inds

def compute_coarse_sorting(
    shifted_data,
    high_activity_intervals,
    sampling_frequency_hz,
    electrode_coords,
    detect_threshold=-80,
    num_nearest_neighbors=20,
    num_clusters=100
):
    """
    Perform coarse spike sorting on shifted data.
    
    Parameters
    ----------
    shifted_data : np.ndarray
        Shifted data array of shape (num_frames, num_channels)
    high_activity_intervals : list of tuple
        List of (start_sec, end_sec) tuples for high activity periods to exclude
    sampling_frequency_hz : float
        Sampling frequency in Hz
    electrode_coords : np.ndarray
        Electrode coordinates array of shape (num_channels, 2)
    detect_threshold : float
        Spike detection threshold (default: -80)
    num_nearest_neighbors : int
        Number of nearest neighbors for clustering (default: 20)
    num_clusters : int
        Number of clusters for K-means (default: 100)
        
    Returns
    -------
    templates : np.ndarray
        Spike templates of shape (num_clusters, num_channels)
    spike_times : np.ndarray
        Spike times in samples
    spike_labels : np.ndarray
        Cluster labels for each spike
    spike_amplitudes : np.ndarray
        Spike amplitudes
    """
    num_frames, num_channels = shifted_data.shape
    
    # Create mask for low activity frames
    low_activity_mask = np.ones(num_frames, dtype=bool)
    for start_sec, end_sec in high_activity_intervals:
        start_frame = int(start_sec * sampling_frequency_hz)
        end_frame = int(end_sec * sampling_frequency_hz)
        start_frame = max(0, start_frame)
        end_frame = min(num_frames, end_frame)
        low_activity_mask[start_frame:end_frame] = False
    
    # Set high activity frames to zero
    shifted_data_low_activity = shifted_data.copy()
    shifted_data_low_activity[~low_activity_mask, :] = 0
    
    # Detect spikes on minimum across channels
    data_min = np.min(shifted_data_low_activity, axis=1)
    spike_inds = detect_spikes_single_channel(
        data=data_min,
        threshold=detect_threshold,
        sign=-1,
        window_size=10
    )
    
    print(f'Detected {len(spike_inds)} spikes')
    
    if len(spike_inds) == 0:
        # Return empty results
        return (
            np.zeros((0, num_channels), dtype=np.float32),
            np.array([], dtype=np.int64),
            np.array([], dtype=np.int32),
            np.array([], dtype=np.float32)
        )
    
    # Extract spike frames
    frames = shifted_data_low_activity[spike_inds, :].astype(np.float32)
    
    # # Find nearest neighbors
    # print(f'Finding nearest neighbors for {frames.shape[0]} frames...')
    # nearest_neighbors = find_nearest_neighbors(frames, num_neighbors=num_nearest_neighbors)
    
    # # Non-local means averaging of nearest neighbors (denoising)
    # print(f'Denoising frames...')
    # # Q: Should we use mean or median here?
    # denoised_frames = np.median(frames[nearest_neighbors], axis=1)
    
    # # Cluster denoised frames
    # n_clusters = min(num_clusters, len(denoised_frames))
    # print(f'Clustering into {n_clusters} clusters...')
    # labels = cluster_kmeans(denoised_frames, num_clusters=n_clusters)
    # num_clusters_found = np.max(labels)

    from isosplit import isosplit
    labels = isosplit(
        frames.astype(np.float32),
        initial_k=300,
        separation_threshold=3,
        use_lda_for_merge_test=False
    )
    num_clusters_found = np.max(labels)
    
    # Compute cluster templates
    templates = np.zeros((num_clusters_found, num_channels), dtype=np.float32)
    for k in range(1, num_clusters_found + 1):
        # Should we use mean or median here?
        templates[k - 1, :] = np.median(frames[labels == k, :], axis=0)
    
    # Sort templates by peak channel x-coordinate
    template_x_coords = compute_template_peak_channel_x_coordinate(templates, np.array(electrode_coords))
    sorted_indices = np.argsort(template_x_coords[:, 0])
    templates = templates[sorted_indices, :]
    
    # Create mapping from old labels to new sorted labels
    old_to_new = np.zeros(num_clusters_found + 1, dtype=np.int32)
    for new_idx, old_idx in enumerate(sorted_indices):
        old_to_new[old_idx + 1] = new_idx + 1  # +1 because labels are 1-based
    
    # Remap spike labels to sorted order
    spike_labels = old_to_new[labels].astype(np.int32)
    
    # Compute spike amplitudes from denoised frames (negative of minimum value across channels)
    spike_amplitudes = -np.min(frames, axis=1).astype(np.float32)
    
    # Return results
    spike_times = spike_inds.astype(np.float32) / sampling_frequency_hz  # in seconds
    spike_times = spike_times
    
    return templates, spike_times, spike_labels, spike_amplitudes
