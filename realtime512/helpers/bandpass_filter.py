from scipy.signal import butter
import numpy as np
from multiprocessing import Pool, cpu_count
from scipy.signal import sosfiltfilt
from .vision_raw import load_raw_bin_file


def _filter_channel_batch(args):
    """Filter a batch of channels in parallel. Module-level function for multiprocessing."""
    data_batch, sos = args
    # Apply filter along axis 0 (time axis) for this batch of channels
    return sosfiltfilt(sos, data_batch, axis=0)


def apply_bandpass_filter(input_path, output_path, num_channels, lowcust, highcut, fs, order):
    def butter_bandpass(lowcut, highcut, fs, order=5):
        sos = butter(order, [lowcut, highcut], fs=fs, btype='band', output='sos')
        return sos

    # Read raw data
    data = load_raw_bin_file(input_path, num_channels)

    # Design filter
    sos = butter_bandpass(lowcust, highcut, fs, order=order)

    # Determine number of workers (use all available cores)
    num_workers = cpu_count()
    
    # Split channels into batches for parallel processing
    channels_per_worker = max(1, num_channels // num_workers)
    
    # Create batches of channels
    batches = []
    for i in range(0, num_channels, channels_per_worker):
        end_idx = min(i + channels_per_worker, num_channels)
        batch = data[:, i:end_idx]
        batches.append((batch, sos))
    
    # Process batches in parallel
    print(f"Filtering {num_channels} channels using {num_workers} workers...")
    with Pool(processes=num_workers) as pool:
        filtered_batches = pool.map(_filter_channel_batch, batches)
    
    # Concatenate filtered batches back together
    filtered_data = np.concatenate(filtered_batches, axis=1)

    # Save filtered data
    filtered_data.astype(np.int16).tofile(output_path)
    print(f"Filtered data saved to {output_path}.")