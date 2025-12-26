import os
import json
import numpy as np
import yaml

from ..helpers.bandpass_filter import apply_bandpass_filter
from ..helpers.time_shifts import optimize_time_shift, apply_time_shifts
from ..helpers.high_activity_intervals import detect_high_activity_intervals
from ..helpers.channel_spike_stats import compute_channel_spike_stats, detect_spikes_single_channel
from ..helpers.data_utils import set_high_activity_to_zero
from ..helpers.generate_preview import generate_preview
from ..helpers.coarse_sorting import compute_coarse_sorting
from ..helpers.unit_matching import compute_unit_matches, calculate_spike_labels_hash

def process_filtering(bin_files, raw_dir, computed_dir, n_channels, filter_params, sampling_frequency):
    """Apply bandpass filtering to raw .bin files."""
    for fname in bin_files:
        if not os.path.exists(os.path.join(computed_dir, "filt")):
            os.makedirs(os.path.join(computed_dir, "filt"))
        filt_path = os.path.join(computed_dir, "filt", fname + ".filt")
        if os.path.exists(filt_path):
            # Check that it has the expected size (same size as raw file)
            raw_path = os.path.join(raw_dir, fname)
            raw_size = os.path.getsize(raw_path)
            filt_size = os.path.getsize(filt_path)
            if filt_size == raw_size:
                continue  # Already processed
            else:
                proceed = input(
                    f"Filtered file {filt_path} exists but size mismatch. Reprocess? (y/n): "
                )
                if proceed.lower() != 'y':
                    continue  # Skip reprocessing
                else:
                    # remove the existing file to reprocess
                    os.remove(filt_path)
        if not os.path.exists(filt_path):
            raw_path = os.path.join(raw_dir, fname)
            filt_path = os.path.join(computed_dir, "filt", fname + ".filt")
            print(f"Filtering {fname}...")
            apply_bandpass_filter(
                input_path=raw_path,
                output_path=filt_path,
                num_channels=n_channels,
                lowcust=filter_params['lowcut'],
                highcut=filter_params['highcut'],
                fs=sampling_frequency,
                order=filter_params['order']
            )
            return True
    return False

def estimate_shift_coefficients(bin_files, computed_dir, electrode_coords, sampling_frequency):
    """Estimate shift coefficients from first filtered file."""
    shift_coeffs_path = os.path.join(computed_dir, "shift_coeffs.yaml")
    if os.path.exists(shift_coeffs_path):
        return
    if len(bin_files) == 0:
        return
    # path of first filtered file
    first_filt_path = os.path.join(computed_dir, "filt", bin_files[0] + ".filt")
    if not os.path.exists(first_filt_path):
        return
    
    c_x, c_y = optimize_time_shift(
        filtered_data_file_path=first_filt_path,
        electrode_coords=electrode_coords,
        sampling_frequency_hz=sampling_frequency,
        duration_sec=0.5
    )

    # write yaml file
    shift_data = {
        'c_x': c_x,
        'c_y': c_y
    }
    with open(shift_coeffs_path, "w") as f:
        yaml.dump(shift_data, f)
    print(f'Using shift coefficients: c_x={c_x:.6e}, c_y={c_y:.6e}')

def load_shift_coefficients(computed_dir):
    """Load shift coefficients from file if they exist."""
    shift_coeffs_path = os.path.join(computed_dir, "shift_coeffs.yaml")
    if os.path.exists(shift_coeffs_path):
        with open(shift_coeffs_path, "r") as f:
            shift_coeffs = yaml.safe_load(f)
        return shift_coeffs['c_x'], shift_coeffs['c_y']
    return None, None

def process_high_activity_intervals(bin_files, computed_dir, n_channels, sampling_frequency, high_activity_threshold):
    """Compute high activity intervals for filtered files."""
    for fname in bin_files:
        filt_path = os.path.join(computed_dir, "filt", fname + ".filt")
        if not os.path.exists(os.path.join(computed_dir, "high_activity")):
            os.makedirs(os.path.join(computed_dir, "high_activity"))
        high_activity_path = os.path.join(computed_dir, "high_activity", fname + ".high_activity.json")
        if os.path.exists(high_activity_path):
            continue  # Already processed
        if not os.path.exists(filt_path):
            continue  # Filtered file does not exist yet
        print(f"Computing high activity intervals: {fname}.high_activity.json")
        high_activity_intervals = detect_high_activity_intervals(
            data_path=filt_path,
            num_channels=n_channels,
            num_frames=os.path.getsize(filt_path) // (2 * n_channels),
            sampling_frequency_hz=sampling_frequency,
            high_activity_threshold=high_activity_threshold
        )
        num_intervals = len(high_activity_intervals)
        print(f"  Found {num_intervals} high activity intervals.")
        total_high_activity_duration_sec = sum(end - start for start, end in high_activity_intervals)
        total_duration_sec = os.path.getsize(filt_path) / (2 * n_channels * sampling_frequency)
        print(f"  Total high activity duration: {total_high_activity_duration_sec:.2f} sec out of {total_duration_sec:.2f} sec.")
        # write to json file
        with open(high_activity_path, "w") as f:
            json.dump({
                "high_activity_intervals": [
                    {"start_sec": start, "end_sec": end} for start, end in high_activity_intervals
                ]
            }, f)
        return True
    return False

def process_spike_stats(bin_files, computed_dir, n_channels, sampling_frequency, detect_threshold_for_spike_stats):
    """Compute spike statistics for filtered files."""
    for fname in bin_files:
        filt_path = os.path.join(computed_dir, "filt", fname + ".filt")
        if not os.path.exists(os.path.join(computed_dir, "stats")):
            os.makedirs(os.path.join(computed_dir, "stats"))
        stats_path = os.path.join(computed_dir, "stats", fname + ".stats.json")
        if os.path.exists(stats_path):
            continue  # Already processed
        if not os.path.exists(filt_path):
            continue  # Filtered file does not exist yet
        print(f"Computing channel spike stats: {fname}.stats.json")
        filt_data = np.fromfile(filt_path, dtype=np.int16).reshape(-1, n_channels)
        mean_firing_rates, mean_spike_amplitudes = compute_channel_spike_stats(
            data=filt_data,
            sampling_frequency_hz=sampling_frequency,
            threshold=detect_threshold_for_spike_stats
        )
        # write to json file
        with open(stats_path, "w") as f:
            json.dump({
                "mean_firing_rates": mean_firing_rates.tolist(),
                "mean_spike_amplitudes": mean_spike_amplitudes.tolist()
            }, f)
        return True
    return False

def process_time_shifts(bin_files, computed_dir, n_channels, sampling_frequency, c_x, c_y, electrode_coords):
    """Apply time shifts to filtered files."""
    if c_x is None or c_y is None:
        return
    for fname in bin_files:
        filt_path = os.path.join(computed_dir, "filt", fname + ".filt")
        if not os.path.exists(os.path.join(computed_dir, "shifted")):
            os.makedirs(os.path.join(computed_dir, "shifted"))
        shifted_path = os.path.join(computed_dir, "shifted", fname + ".shifted")
        if os.path.exists(shifted_path):
            # Check that it has the expected size (same size as filt file)
            filt_size = os.path.getsize(filt_path)
            shifted_size = os.path.getsize(shifted_path)
            if shifted_size == filt_size:
                continue  # Already processed
            else:
                proceed = input(
                    f"Shifted file {shifted_path} exists but size mismatch. Reprocess? (y/n): "
                )
                if proceed.lower() != 'y':
                    continue  # Skip reprocessing
                else:
                    # remove the existing file to reprocess
                    os.remove(shifted_path)
        if not os.path.exists(shifted_path):
            print(f"Applying time shifts cx={c_x:.6e}, cy={c_y:.6e} to {fname}.filt...")
            filt_data = np.fromfile(filt_path, dtype=np.int16).reshape(-1, n_channels)
            shift_data = apply_time_shifts(
                data=filt_data,
                sampling_frequency_hz=sampling_frequency,
                c_x=c_x,
                c_y=c_y,
                electrode_coords=electrode_coords,
            )
            shift_data.astype(np.int16).tofile(shifted_path)
            print(f"Wrote shifted data to {shifted_path}.")
            return True
    return False

def process_coarse_sorting(bin_files, computed_dir, n_channels, sampling_frequency, electrode_coords, coarse_sorting_detect_threshold):
    """Perform coarse spike sorting on shifted data."""
    for fname in bin_files:
        shift_path = os.path.join(computed_dir, "shifted", fname + ".shifted")
        high_activity_path = os.path.join(computed_dir, "high_activity", fname + ".high_activity.json")
        if not os.path.exists(os.path.join(computed_dir, "coarse_sorting")):
            os.makedirs(os.path.join(computed_dir, "coarse_sorting"))
        
        # Create subdirectory for this file
        coarse_sorting_dir = os.path.join(computed_dir, "coarse_sorting", fname)
        if not os.path.exists(coarse_sorting_dir):
            os.makedirs(coarse_sorting_dir)
        
        # Check if all output files exist
        templates_path = os.path.join(coarse_sorting_dir, "templates.npy")
        spike_times_path = os.path.join(coarse_sorting_dir, "spike_times.npy")
        spike_labels_path = os.path.join(coarse_sorting_dir, "spike_labels.npy")
        spike_amplitudes_path = os.path.join(coarse_sorting_dir, "spike_amplitudes.npy")
        
        if (os.path.exists(templates_path) and os.path.exists(spike_times_path) and 
            os.path.exists(spike_labels_path) and os.path.exists(spike_amplitudes_path)):
            continue  # Already processed
        
        if not os.path.exists(shift_path):
            continue  # Shifted file does not exist yet
        if not os.path.exists(high_activity_path):
            continue  # High activity intervals do not exist yet
        
        print(f"Computing coarse sorting: {fname}")
        shift_data = np.fromfile(shift_path, dtype=np.int16).reshape(-1, n_channels)
        
        with open(high_activity_path, "r") as f:
            high_activity_data = json.load(f)
        high_activity_intervals = [
            (item['start_sec'], item['end_sec']) for item in high_activity_data['high_activity_intervals']
        ]
        
        # Perform coarse sorting
        templates, spike_times, spike_labels, spike_amplitudes = compute_coarse_sorting(
            shifted_data=shift_data,
            high_activity_intervals=high_activity_intervals,
            sampling_frequency_hz=sampling_frequency,
            electrode_coords=electrode_coords,
            detect_threshold=coarse_sorting_detect_threshold,
            num_nearest_neighbors=20,
            num_clusters=100
        )
        
        # Save outputs
        np.save(templates_path, templates)
        np.save(spike_times_path, spike_times)
        np.save(spike_labels_path, spike_labels)
        np.save(spike_amplitudes_path, spike_amplitudes)
        
        print(f"  Saved {len(spike_times)} spikes with {len(templates)} templates")
        return True
    return False

def process_unit_matching(bin_files, computed_dir, n_channels, sampling_frequency):
    """
    Match units in each file X against files Y that have focus units.
    
    This function:
    1. Loads focus units from focus_units.json
    2. For each file X with coarse sorting, matches against all Y files with focus units
    3. Stores match results in computed/unit_matching/{filename_x}/{filename_y}/
    4. Validates hashes and deletes invalid match results
    """
    # Load focus units
    focus_units_path = os.path.join(os.getcwd(), "focus_units.json")
    if not os.path.exists(focus_units_path):
        return False  # No focus units defined yet
    
    with open(focus_units_path, "r") as f:
        focus_units_data = json.load(f)
    
    focus_units = focus_units_data.get("focus_units", [])
    if len(focus_units) == 0:
        return False  # No focus units defined
    
    # Get unique Y filenames that have focus units
    y_filenames = list(set(unit["bin_filename"] for unit in focus_units))
    
    something_processed = False
    
    # Process each file X
    for fname_x in bin_files:
        coarse_sorting_dir_x = os.path.join(computed_dir, "coarse_sorting", fname_x)
        spike_labels_path_x = os.path.join(coarse_sorting_dir_x, "spike_labels.npy")
        spike_times_path_x = os.path.join(coarse_sorting_dir_x, "spike_times.npy")
        shifted_path_x = os.path.join(computed_dir, "shifted", fname_x + ".shifted")
        
        # Skip if X doesn't have coarse sorting
        if not os.path.exists(spike_labels_path_x):
            continue
        
        # Calculate current hash for X
        current_hash_x = calculate_spike_labels_hash(spike_labels_path_x)
        if current_hash_x is None:
            continue
        
        # Match against each Y file
        for fname_y in y_filenames:
            # Skip matching X against itself
            if fname_x == fname_y:
                continue
            
            coarse_sorting_dir_y = os.path.join(computed_dir, "coarse_sorting", fname_y)
            spike_labels_path_y = os.path.join(coarse_sorting_dir_y, "spike_labels.npy")
            spike_times_path_y = os.path.join(coarse_sorting_dir_y, "spike_times.npy")
            shifted_path_y = os.path.join(computed_dir, "shifted", fname_y + ".shifted")
            
            # Skip if Y doesn't have coarse sorting
            if not os.path.exists(spike_labels_path_y):
                continue
            
            # Calculate current hash for Y
            current_hash_y = calculate_spike_labels_hash(spike_labels_path_y)
            if current_hash_y is None:
                continue
            
            # Create output directory for this X-Y pair
            unit_matching_dir = os.path.join(computed_dir, "unit_matching", fname_x, fname_y)
            if not os.path.exists(unit_matching_dir):
                os.makedirs(unit_matching_dir)
            
            # Check if matching already exists and is valid
            metadata_path = os.path.join(unit_matching_dir, "metadata.json")
            mutual_matches_path = os.path.join(unit_matching_dir, "mutual_matches.json")
            event_matches_x_to_y_path = os.path.join(unit_matching_dir, "event_matches_x_to_y.npy")
            event_matches_y_to_x_path = os.path.join(unit_matching_dir, "event_matches_y_to_x.npy")
            
            need_recompute = False
            
            if os.path.exists(metadata_path):
                # Check if hashes match
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                
                stored_hash_x = metadata.get("spike_labels_hash_x")
                stored_hash_y = metadata.get("spike_labels_hash_y")
                
                if stored_hash_x != current_hash_x or stored_hash_y != current_hash_y:
                    # Hashes changed, need to recompute and delete old results
                    print(f"Hash mismatch for {fname_x} <-> {fname_y}, deleting old match results")
                    if os.path.exists(mutual_matches_path):
                        os.remove(mutual_matches_path)
                    if os.path.exists(event_matches_x_to_y_path):
                        os.remove(event_matches_x_to_y_path)
                    if os.path.exists(event_matches_y_to_x_path):
                        os.remove(event_matches_y_to_x_path)
                    os.remove(metadata_path)
                    need_recompute = True
                else:
                    # Hashes match, check if all files exist
                    if (os.path.exists(mutual_matches_path) and 
                        os.path.exists(event_matches_x_to_y_path) and 
                        os.path.exists(event_matches_y_to_x_path)):
                        continue  # Already processed and valid
                    else:
                        need_recompute = True
            else:
                need_recompute = True
            
            if not need_recompute:
                continue
            
            # Need to compute matching
            print(f"Computing unit matching: {fname_x} <-> {fname_y}")
            
            # Load spike data for X
            spike_labels_x = np.load(spike_labels_path_x)
            spike_times_x = np.load(spike_times_path_x)
            shifted_data_x = np.fromfile(shifted_path_x, dtype=np.int16).reshape(-1, n_channels)
            
            # Convert spike times to frame indices
            spike_frames_x = (spike_times_x * sampling_frequency).astype(np.int64)
            frames_x = shifted_data_x[spike_frames_x, :].astype(np.float32)
            
            # Load spike data for Y
            spike_labels_y = np.load(spike_labels_path_y)
            spike_times_y = np.load(spike_times_path_y)
            shifted_data_y = np.fromfile(shifted_path_y, dtype=np.int16).reshape(-1, n_channels)
            
            # Convert spike times to frame indices
            spike_frames_y = (spike_times_y * sampling_frequency).astype(np.int64)
            frames_y = shifted_data_y[spike_frames_y, :].astype(np.float32)
            
            # Compute matches
            match_results = compute_unit_matches(
                frames_x=frames_x,
                labels_x=spike_labels_x,
                frames_y=frames_y,
                labels_y=spike_labels_y,
                n_neighbors=10
            )
            
            # Save results
            with open(mutual_matches_path, "w") as f:
                json.dump(match_results["mutual_matches"], f, indent=2)
            
            np.save(event_matches_x_to_y_path, match_results["event_matches_x_to_y"])
            np.save(event_matches_y_to_x_path, match_results["event_matches_y_to_x"])
            
            # Save metadata with hashes
            metadata = {
                "filename_x": fname_x,
                "filename_y": fname_y,
                "spike_labels_hash_x": current_hash_x,
                "spike_labels_hash_y": current_hash_y,
                "num_mutual_matches": len(match_results["mutual_matches"])
            }
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
            
            print(f"  Found {len(match_results['mutual_matches'])} mutual matches")
            something_processed = True
    
    return something_processed

def process_preview(bin_files, computed_dir, n_channels, sampling_frequency, electrode_coords):
    for fname in bin_files:
        filt_path = os.path.join(computed_dir, "filt", fname + ".filt")
        shift_path = os.path.join(computed_dir, "shifted", fname + ".shifted")
        high_activity_intervals_path = os.path.join(computed_dir, "high_activity", fname + ".high_activity.json")
        stats_path = os.path.join(computed_dir, "stats", fname + ".stats.json")
        coarse_sorting_path = os.path.join(computed_dir, "coarse_sorting", fname)
        if not os.path.exists(os.path.join(computed_dir, "preview")):
            os.makedirs(os.path.join(computed_dir, "preview"))
        preview_path = os.path.join(computed_dir, "preview", fname + ".figpack")
        if os.path.exists(preview_path):
            continue  # Already processed
        if not os.path.exists(filt_path):
            continue  # Filtered file does not exist yet
        if not os.path.exists(shift_path):
            continue  # Shifted file does not exist yet
        if not os.path.exists(high_activity_intervals_path):
            continue  # High activity intervals do not exist yet
        if not os.path.exists(stats_path):
            continue  # Stats file does not exist yet
        if not os.path.exists(coarse_sorting_path):
            continue  # Coarse sorting does not exist yet

        with open(high_activity_intervals_path, "r") as f:
            high_activity_data = json.load(f)
        high_activity_intervals = [
            (item['start_sec'], item['end_sec']) for item in high_activity_data['high_activity_intervals']
        ]
        print(f"Generating preview figpack: {fname}.figpack")
        generate_preview(
            filt_path=filt_path,
            shift_path=shift_path,
            high_activity_intervals=high_activity_intervals,
            stats_path=stats_path,
            coarse_sorting_path=coarse_sorting_path,
            n_channels=n_channels,
            sampling_frequency=sampling_frequency,
            electrode_coords=electrode_coords,
            preview_path=preview_path
        )
        return True
    return False
