"""Helper functions for matching units between different recordings."""

import numpy as np
import hashlib
from sklearn.neighbors import NearestNeighbors


def calculate_spike_labels_hash(spike_labels_path):
    """
    Calculate SHA-1 hash of spike_labels.npy file.
    
    Parameters
    ----------
    spike_labels_path : str
        Path to spike_labels.npy file
        
    Returns
    -------
    str or None
        SHA-1 hash hexdigest, or None if file doesn't exist
    """
    import os
    
    if not os.path.exists(spike_labels_path):
        return None
    
    sha1 = hashlib.sha1()
    with open(spike_labels_path, "rb") as f:
        while chunk := f.read(8192):
            sha1.update(chunk)
    
    return sha1.hexdigest()


def nearest_neighbors(data1: np.ndarray, data2: np.ndarray, *, n_neighbors: int):
    """
    For each point in data2, find the nearest neighbors in data1.
    
    Parameters
    ----------
    data1 : np.ndarray
        Reference data array of shape (num_points_1, num_features)
    data2 : np.ndarray
        Query data array of shape (num_points_2, num_features)
    n_neighbors : int
        Number of nearest neighbors to find
    
    Returns
    -------
    np.ndarray
        Array of shape (num_points_2, n_neighbors) with indices into data1
    """
    nbrs = NearestNeighbors(n_neighbors=n_neighbors, algorithm='auto').fit(data1)
    distances, indices = nbrs.kneighbors(data2)
    return indices


def compute_unit_matches(frames_x, labels_x, frames_y, labels_y, n_neighbors=10):
    """
    Compute unit matches between two datasets using nearest neighbor matching.
    
    This finds mutual matches where units in X map to units in Y and vice versa.
    
    Parameters
    ----------
    frames_x : np.ndarray
        Spike frames from dataset X, shape (num_spikes_x, num_channels)
    labels_x : np.ndarray
        Unit labels for dataset X, shape (num_spikes_x,)
    frames_y : np.ndarray
        Spike frames from dataset Y, shape (num_spikes_y, num_channels)
    labels_y : np.ndarray
        Unit labels for dataset Y, shape (num_spikes_y,)
    n_neighbors : int
        Number of nearest neighbors to use (default: 10)
        
    Returns
    -------
    dict
        Dictionary containing:
        - 'mutual_matches': list of dicts with 'unit_x', 'unit_y', 'score_x_to_y', 'score_y_to_x', 'overall_score'
        - 'event_matches_x_to_y': np.ndarray of shape (num_spikes_x,) with matched unit IDs from Y
        - 'event_matches_y_to_x': np.ndarray of shape (num_spikes_y,) with matched unit IDs from X
    """
    # Find nearest neighbors in both directions
    nearest_y_to_x = nearest_neighbors(frames_x, frames_y, n_neighbors=n_neighbors)
    nearest_x_to_y = nearest_neighbors(frames_y, frames_x, n_neighbors=n_neighbors)
    
    # Compute best matches from Y to X
    max_label_y = int(np.max(labels_y))
    best_matches_y_to_x = np.zeros(max_label_y + 1, dtype=np.int32)
    match_scores_y_to_x = np.zeros(max_label_y + 1, dtype=np.float32)
    
    for ky in range(1, max_label_y + 1):
        inds_y = np.where(labels_y == ky)[0]
        if len(inds_y) == 0:
            continue
            
        cluster_matches = []
        for i in range(len(inds_y)):
            ind_y = inds_y[i]
            neighbors = nearest_y_to_x[ind_y]
            neighbor_labels = labels_x[neighbors]
            unique, counts = np.unique(neighbor_labels, return_counts=True)
            best_label = unique[np.argmax(counts)]
            cluster_matches.append(best_label)
        
        best_label = max(cluster_matches, key=cluster_matches.count)
        best_label_count = cluster_matches.count(best_label)
        match_score = best_label_count / len(inds_y)
        best_matches_y_to_x[ky] = best_label
        match_scores_y_to_x[ky] = match_score
    
    # Compute best matches from X to Y
    max_label_x = int(np.max(labels_x))
    best_matches_x_to_y = np.zeros(max_label_x + 1, dtype=np.int32)
    match_scores_x_to_y = np.zeros(max_label_x + 1, dtype=np.float32)
    
    for kx in range(1, max_label_x + 1):
        inds_x = np.where(labels_x == kx)[0]
        if len(inds_x) == 0:
            continue
            
        cluster_matches = []
        for i in range(len(inds_x)):
            ind_x = inds_x[i]
            neighbors = nearest_x_to_y[ind_x]
            neighbor_labels = labels_y[neighbors]
            unique, counts = np.unique(neighbor_labels, return_counts=True)
            best_label = unique[np.argmax(counts)]
            cluster_matches.append(best_label)
        
        best_label = max(cluster_matches, key=cluster_matches.count)
        best_label_count = cluster_matches.count(best_label)
        match_score = best_label_count / len(inds_x)
        best_matches_x_to_y[kx] = best_label
        match_scores_x_to_y[kx] = match_score
    
    # Find mutual matches
    mutual_matches = []
    for kx in range(1, max_label_x + 1):
        ky = best_matches_x_to_y[kx]
        if ky > 0 and best_matches_y_to_x[ky] == kx:
            # Mutual match found
            score_x_to_y = float(match_scores_x_to_y[kx])
            score_y_to_x = float(match_scores_y_to_x[ky])
            overall_score = (score_x_to_y + score_y_to_x) / 2.0
            
            mutual_matches.append({
                'unit_x': int(kx),
                'unit_y': int(ky),
                'score_x_to_y': score_x_to_y,
                'score_y_to_x': score_y_to_x,
                'overall_score': overall_score
            })
    
    # Create event-level matches for all spikes
    event_matches_x_to_y = np.zeros(len(labels_x), dtype=np.int32)
    for i in range(len(labels_x)):
        neighbors = nearest_x_to_y[i]
        neighbor_labels = labels_y[neighbors]
        unique, counts = np.unique(neighbor_labels, return_counts=True)
        best_label = unique[np.argmax(counts)]
        event_matches_x_to_y[i] = best_label
    
    event_matches_y_to_x = np.zeros(len(labels_y), dtype=np.int32)
    for i in range(len(labels_y)):
        neighbors = nearest_y_to_x[i]
        neighbor_labels = labels_x[neighbors]
        unique, counts = np.unique(neighbor_labels, return_counts=True)
        best_label = unique[np.argmax(counts)]
        event_matches_y_to_x[i] = best_label
    
    return {
        'mutual_matches': mutual_matches,
        'event_matches_x_to_y': event_matches_x_to_y,
        'event_matches_y_to_x': event_matches_y_to_x
    }
