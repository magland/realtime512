import bin2py
import numpy as np
import os

# Constants
RW_BLOCKSIZE = 100000  # Block size for reading data
TTL_THRESHOLD = 1000
SAMPLE_RATE = 20000 # Hz
class RawTraces:
    def __init__(self, binpath):
        self.binpath = binpath
        self.data = None
        self.ttl_times = None
        self.ttl_samples = None
        self.sample_rate = SAMPLE_RATE  # Hz
        self.epoch_idx = None

    def load_bin_data(self, start_sample=0, end_sample=None, verbose=False):
        """
        Load raw .bin data into a NumPy array.

        Parameters:
            binpath (str): Path to the .bin file.
            start_sample (int): Starting sample index (default: 0).
            end_sample (int): Ending sample index (default: None, reads till the end).

        Returns:
            np.ndarray: Loaded data as a NumPy array of shape [electrodes, samples].
        """
        with bin2py.PyBinFileReader(self.binpath, chunk_samples=RW_BLOCKSIZE, is_row_major=True) as pbfr:
            # Determine the number of electrodes and total samples
            n_channels = pbfr.num_electrodes
            total_samples = pbfr.length
            
            if verbose:
                print(f"Number of electrodes: {n_channels}, Total samples: {total_samples}.")
                print(f"Total time: {total_samples / SAMPLE_RATE} seconds")
                print(f"Sample rate: {SAMPLE_RATE} Hz")

            # Set end_sample to the total length if not specified
            if end_sample is None:
                end_sample = total_samples

            # Validate sample range
            if start_sample < 0 or end_sample > total_samples or start_sample >= end_sample:
                raise ValueError("Invalid start_sample or end_sample range.")

            query_samples = end_sample - start_sample
            if verbose:
                print(f"Querying {query_samples} samples from {start_sample} to {end_sample}.")
                print(f'Queried time: {query_samples / SAMPLE_RATE} seconds')
                print(f'From {start_sample / SAMPLE_RATE} to {end_sample / SAMPLE_RATE} seconds')
                
            # Preallocate array for the data
            data = np.zeros((n_channels, query_samples), dtype=np.float32)

            ttl_times_buffer = []
            ttl_samples = np.zeros((query_samples,), dtype=np.float32)
            # Read data in chunks
            for start_idx in range(start_sample, end_sample, RW_BLOCKSIZE):
                n_samples_to_get = min(RW_BLOCKSIZE, end_sample - start_idx)
                chunk = pbfr.get_data(start_idx, n_samples_to_get)

                # Extract TTL data (channel 0) and compute TTL times
                ttl_samples = chunk[0, :]
                below_threshold = (ttl_samples < -TTL_THRESHOLD)
                above_threshold = np.logical_not(below_threshold)
                below_to_above = np.logical_and.reduce([
                    below_threshold[:-1],
                    above_threshold[1:]
                ])
                trigger_indices = np.argwhere(below_to_above) + start_idx
                ttl_times_buffer.append(trigger_indices[:, 0])

                # Populate the data matrix (exclude channel 0)
                data[:, start_idx - start_sample:start_idx - start_sample + n_samples_to_get] = chunk[1:, :]
                # ttl_samples[start_idx - start_sample:start_idx - start_sample + n_samples_to_get] = chunk[0, :]

            # Concatenate TTL times
            ttl_times = np.concatenate(ttl_times_buffer, axis=0)
        
        if verbose:
            print(f'Data shape: {data.shape}')
        # print(f'TTL times shape: {ttl_times.shape}')
        
        # Store as [samples, electrodes]
        self.data = data.T
        self.ttl_times = ttl_times
        self.ttl_samples = ttl_samples

def load_raw_bin_file(input_path: str, num_channels: int, b_np: bool=False) -> np.ndarray:
    # b_np: if True, data is in numpy format, otherwise needs bin2py from vision utils.
    if b_np:
        data = np.fromfile(input_path, dtype=np.int16)
        data = data.reshape(-1, num_channels)
        return data
    
    rt = RawTraces(input_path)
    rt.load_bin_data(verbose=True)
    return rt.data
