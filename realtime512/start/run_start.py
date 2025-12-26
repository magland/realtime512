import os
import time

from .config_utils import check_or_create_config, load_and_validate_config
from .file_setup import download_simulated_data, load_electrode_coords, setup_directories
from .file_processors import (
    process_filtering,
    estimate_shift_coefficients,
    load_shift_coefficients,
    process_high_activity_intervals,
    process_spike_stats,
    process_time_shifts,
    process_coarse_sorting,
    process_unit_matching,
    process_preview,
)

def run_start():
    """Main entry point for realtime512 processing."""
    # Check or create configuration file
    config_path = check_or_create_config()
    if config_path is None:
        return
    
    # Load and validate configuration
    config = load_and_validate_config(config_path)
    
    # Extract configuration parameters
    filter_params = config['filter_params']
    sampling_frequency = config['sampling_frequency']
    n_channels = config['n_channels']
    detect_threshold_for_spike_stats = config['detect_threshold_for_spike_stats']
    high_activity_threshold = config['high_activity_threshold']
    course_sorting_detect_threshold = config.get('coarse_sorting_detect_threshold')

    # Download simulated data if configured
    download_simulated_data()
    
    # Load electrode coordinates
    electrode_coords = load_electrode_coords(n_channels)
    if electrode_coords is None:
        return

    # Setup directories
    raw_dir, computed_dir = setup_directories()

    # Wait for at least one file of type .bin to appear in raw/
    while True:
        if any(fname.endswith(".bin") for fname in os.listdir(raw_dir)):
            break
        print("Waiting for .bin file to appear in raw/ directory...")
        time.sleep(2)
    
    # Main processing loop
    up_to_date_has_been_printed = False
    while True:
        # Get list of all .bin files in raw/
        bin_files = [
            fname for fname in os.listdir(raw_dir) if fname.endswith(".bin")
        ]
        # reverse the order so that newer files are processed first
        bin_files.sort(reverse=True)
        
        # Only consider files that have not been modified in the last 5 seconds
        # to avoid processing files that are still being written
        bin_files = [
            fname for fname in bin_files
            if time.time() - os.path.getmtime(os.path.join(raw_dir, fname)) > 5
        ]

        something_processed = False

        # Process filtering
        if process_filtering(
            bin_files, raw_dir, computed_dir, n_channels, 
            filter_params, sampling_frequency
        ):
            something_processed = True

        # Estimate shift coefficients
        if estimate_shift_coefficients(
            bin_files, computed_dir, electrode_coords, sampling_frequency
        ):
            something_processed = True

        # Load shift coefficients
        c_x, c_y = load_shift_coefficients(computed_dir)

        # Compute high activity intervals
        if process_high_activity_intervals(
            bin_files, computed_dir, n_channels, sampling_frequency, high_activity_threshold
        ):
            something_processed = True

        # Compute spike stats
        if process_spike_stats(
            bin_files, computed_dir, n_channels,
            sampling_frequency, detect_threshold_for_spike_stats
        ):
            something_processed = True

        # Apply time shifts
        if process_time_shifts(
            bin_files, computed_dir, n_channels, sampling_frequency,
            c_x, c_y, electrode_coords
        ):
            something_processed = True

        # Perform coarse sorting
        if process_coarse_sorting(
            bin_files, computed_dir, n_channels, sampling_frequency, electrode_coords, course_sorting_detect_threshold
        ):
            something_processed = True

        # Match units across files with focus units
        if process_unit_matching(
            bin_files, computed_dir, n_channels, sampling_frequency
        ):
            something_processed = True

        # Generate figpack preview
        if process_preview(
            bin_files, computed_dir, n_channels, sampling_frequency, electrode_coords
        ):
            something_processed = True

        if something_processed:
            up_to_date_has_been_printed = False
        else:
            if not up_to_date_has_been_printed:
                print("All files are up to date.")
                up_to_date_has_been_printed = True
            # only sleep if nothing was processed
            time.sleep(5)
