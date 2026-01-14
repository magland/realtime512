"""
Acquisition processor module for rechunking variable-sized acquisition files
into fixed-duration raw files.

This module uses a stateless approach - it determines what needs to be done
based on existing acquisition and raw files, so it can recover from restarts.
"""

import os
import time
import numpy as np

# Constants for bin2py format
RW_BLOCKSIZE = 100000  # Block size for reading data


class AcquisitionProcessor:
    """
    Processes acquisition files (variable-sized chunks from acquisition system)
    and rechunks them into fixed-duration files in the raw/ directory.
    
    This uses a stateless approach: each time process_acquisition_files() is called,
    it examines existing acquisition and raw files to determine what needs to be created.
    """
    
    def __init__(
        self,
        acquisition_dir: str,
        raw_dir: str,
        computed_dir: str,
        n_channels: int,
        sampling_frequency: float,
        chunk_duration_sec: float
    ):
        self.acquisition_dir = acquisition_dir
        self.raw_dir = raw_dir
        self.computed_dir = computed_dir
        self.n_channels = n_channels
        self.sampling_frequency = sampling_frequency
        self.chunk_duration_sec = chunk_duration_sec
        self.frames_per_chunk = int(sampling_frequency * chunk_duration_sec)
        self.bytes_per_frame = 2 * n_channels  # int16
        self.bytes_per_chunk = self.frames_per_chunk * self.bytes_per_frame
    
    def process_acquisition_files(self) -> bool:
        """
        Process any new acquisition files and rechunk to raw/.
        
        This method is stateless: it looks at what raw files already exist,
        calculates how much data has been chunked, and creates new raw files
        as needed based on the acquisition files.
        
        Returns True if any processing was done, False otherwise.
        """
        # Get sorted list of acquisition .bin files
        acq_files = sorted([
            fname for fname in os.listdir(self.acquisition_dir)
            if fname.endswith(".bin")
        ])
        
        if len(acq_files) == 0:
            return False
        
        # Skip acquisition files still being written (modified in last 5 seconds)
        acq_files = [
            fname for fname in acq_files
            if time.time() - os.path.getmtime(os.path.join(self.acquisition_dir, fname)) > 5
        ]
        
        if len(acq_files) == 0:
            return False
        
        # Calculate total frames available from acquisition files
        total_acq_bytes = 0
        for fname in acq_files:
            filepath = os.path.join(self.acquisition_dir, fname)
            file_size = os.path.getsize(filepath)
            
            # Validate file size
            if file_size % self.bytes_per_frame != 0:
                print(f"Warning: {fname} has invalid size ({file_size} bytes), skipping")
                continue
            
            total_acq_bytes += file_size
        
        total_acq_frames = total_acq_bytes // self.bytes_per_frame
        
        # Count existing raw files and their total frames
        raw_files = sorted([
            fname for fname in os.listdir(self.raw_dir)
            if fname.startswith("raw_") and fname.endswith(".bin")
        ])
        
        total_raw_frames = 0
        for fname in raw_files:
            filepath = os.path.join(self.raw_dir, fname)
            file_size = os.path.getsize(filepath)
            total_raw_frames += file_size // self.bytes_per_frame
        
        # Determine how many new raw chunks we can create
        # We can create a chunk if we have enough unprocessed frames
        frames_available = total_acq_frames
        frames_already_chunked = total_raw_frames
        frames_remaining = frames_available - frames_already_chunked

        # debug print
        print(
            f"Acquisition frames: {frames_available}, "
            f"Raw frames: {frames_already_chunked}, "
            f"Frames remaining: {frames_remaining}"
        )
        
        if frames_remaining < self.frames_per_chunk:
            # Not enough data for a new chunk yet
            return False
        
        # debug print
        print(f"Processing acquisition files to create new raw chunks...")
        
        # Determine next raw file index
        if len(raw_files) == 0:
            next_raw_index = 1
        else:
            # Extract index from last raw file (e.g., raw_0005.bin -> 5)
            last_file = raw_files[-1]
            try:
                last_index = int(last_file.replace("raw_", "").replace(".bin", ""))
                next_raw_index = last_index + 1
            except ValueError:
                next_raw_index = len(raw_files) + 1

        # debug print
        print(f"Next raw file index: {next_raw_index}")

        # Create new raw chunks
        something_processed = False
        while frames_remaining >= self.frames_per_chunk:
            # Read data starting from offset frames_already_chunked
            data = self._read_frames_from_acquisition(
                acq_files,
                start_frame=frames_already_chunked,
                num_frames=self.frames_per_chunk
            )
            
            if data is None or data.nbytes < self.bytes_per_chunk:
                break
            
            # Write raw chunk
            filename = f"raw_{next_raw_index:04d}.bin"
            filepath = os.path.join(self.raw_dir, filename)
            data[:self.bytes_per_chunk].tofile(filepath)
            
            print(f"Created {filename} ({self.chunk_duration_sec}s, {self.frames_per_chunk} frames)")
            
            frames_already_chunked += self.frames_per_chunk
            frames_remaining -= self.frames_per_chunk
            next_raw_index += 1
            something_processed = True
        
        return something_processed
    
    def _read_frames_from_acquisition(
        self,
        acq_files: list,
        start_frame: int,
        num_frames: int
    ) -> np.ndarray:
        """
        Read num_frames frames starting from start_frame across the acquisition files.
        
        Returns int16 array of data (flat), or None if not enough data available.
        """
        # Calculate byte offset within the acquisition data
        start_byte = start_frame * self.bytes_per_frame
        bytes_needed = num_frames * self.bytes_per_frame
        
        # Find which acquisition files we need to read from
        current_byte = 0
        data_parts = []
        
        for fname in acq_files:
            filepath = os.path.join(self.acquisition_dir, fname)
            file_size = os.path.getsize(filepath)
            
            # Skip invalid files
            if file_size % self.bytes_per_frame != 0:
                continue
            
            # Check if this file contains any of the bytes we need
            file_start_byte = current_byte
            file_end_byte = current_byte + file_size
            
            if file_end_byte <= start_byte:
                # This file is entirely before our start offset
                current_byte = file_end_byte
                continue
            
            if file_start_byte >= start_byte + bytes_needed:
                # This file is entirely after what we need
                break
            
            # This file contains some portion of the data we need
            # Calculate offset within this file
            offset_in_file = max(0, start_byte - file_start_byte)
            bytes_from_this_file = min(
                file_size - offset_in_file,
                bytes_needed - sum(len(p) for p in data_parts) * 2
            )
            
            # Read the needed portion
            file_data = np.fromfile(filepath, dtype=np.int16, count=-1)
            start_idx = offset_in_file // 2  # Convert bytes to int16 samples
            end_idx = start_idx + (bytes_from_this_file // 2)
            data_parts.append(file_data[start_idx:end_idx])
            
            current_byte = file_end_byte
            
            # Check if we have all the data we need
            if sum(len(p) for p in data_parts) * 2 >= bytes_needed:
                break
        
        if len(data_parts) == 0:
            return None
        
        # Concatenate all parts
        data = np.concatenate(data_parts)
        
        return data


class Bin2PyAcquisitionProcessor:
    """
    Processes acquisition folders in bin2py format and rechunks them into
    fixed-duration files in the raw/ directory.
    
    In bin2py mode, acquisition/ contains folders (not .bin files), and each folder
    is readable using the bin2py utility. The output files in raw/ follow the naming
    scheme: data0001_001.bin, data0001_002.bin, etc., where data0001 is the folder name.
    """
    
    def __init__(
        self,
        acquisition_dir: str,
        raw_dir: str,
        computed_dir: str,
        n_channels: int,
        sampling_frequency: float,
        chunk_duration_sec: float
    ):
        self.acquisition_dir = acquisition_dir
        self.raw_dir = raw_dir
        self.computed_dir = computed_dir
        self.n_channels = n_channels
        self.sampling_frequency = sampling_frequency
        self.chunk_duration_sec = chunk_duration_sec
        self.frames_per_chunk = int(sampling_frequency * chunk_duration_sec)
        self.bytes_per_frame = 2 * n_channels  # int16
        self.bytes_per_chunk = self.frames_per_chunk * self.bytes_per_frame
    
    def process_acquisition_files(self) -> bool:
        """
        Process any new acquisition folders and rechunk to raw/.
        
        This method looks at bin2py folders in acquisition/, reads data using bin2py,
        and creates fixed-duration .bin files in raw/ with naming like:
        data0001_001.bin, data0001_002.bin, etc.
        
        Returns True if any processing was done, False otherwise.
        """
        # Get sorted list of acquisition folders (directories, not files)
        acq_folders = sorted([
            fname for fname in os.listdir(self.acquisition_dir)
            if os.path.isdir(os.path.join(self.acquisition_dir, fname))
        ])
        
        if len(acq_folders) == 0:
            return False
        
        # Skip folders still being written (modified in last 5 seconds)
        acq_folders = [
            fname for fname in acq_folders
            if time.time() - os.path.getmtime(os.path.join(self.acquisition_dir, fname)) > 5
        ]
        
        if len(acq_folders) == 0:
            return False
        
        something_processed = False
        
        for folder_name in acq_folders:
            folder_path = os.path.join(self.acquisition_dir, folder_name)
            
            # Count existing raw files for this folder
            existing_chunks = self._get_existing_chunks_for_folder(folder_name)
            total_raw_frames = len(existing_chunks) * self.frames_per_chunk
            
            # Get total frames available from this bin2py folder
            total_folder_frames = self._get_total_frames_bin2py(folder_path)
            if total_folder_frames is None:
                continue
            
            frames_remaining = total_folder_frames - total_raw_frames
            
            if frames_remaining < self.frames_per_chunk:
                # Not enough data for a new chunk yet
                continue
            
            print(f"Processing bin2py folder {folder_name}...")
            print(f"  Total frames: {total_folder_frames}, Already chunked: {total_raw_frames}, Remaining: {frames_remaining}")
            
            # Determine next chunk index for this folder
            next_chunk_index = len(existing_chunks) + 1
            
            # Create new raw chunks
            while frames_remaining >= self.frames_per_chunk:
                # Read data starting from offset total_raw_frames
                data = self._read_frames_from_bin2py(
                    folder_path,
                    start_frame=total_raw_frames,
                    num_frames=self.frames_per_chunk
                )
                
                if data is None or len(data) < self.frames_per_chunk:
                    break
                
                # Write raw chunk with naming: foldername_001.bin, foldername_002.bin, etc.
                filename = f"{folder_name}_{next_chunk_index:03d}.bin"
                filepath = os.path.join(self.raw_dir, filename)
                
                # Data from bin2py is [samples, electrodes], convert to int16 and save
                data_int16 = data[:self.frames_per_chunk].astype(np.int16)
                data_int16.tofile(filepath)
                
                print(f"  Created {filename} ({self.chunk_duration_sec}s, {self.frames_per_chunk} frames)")
                
                total_raw_frames += self.frames_per_chunk
                frames_remaining -= self.frames_per_chunk
                next_chunk_index += 1
                something_processed = True
        
        return something_processed
    
    def _get_existing_chunks_for_folder(self, folder_name: str) -> list:
        """
        Get list of existing raw chunks for a specific folder.
        Returns sorted list of chunk filenames like ['foldername_001.bin', 'foldername_002.bin', ...]
        """
        prefix = f"{folder_name}_"
        chunks = sorted([
            fname for fname in os.listdir(self.raw_dir)
            if fname.startswith(prefix) and fname.endswith(".bin")
        ])
        return chunks
    
    def _get_total_frames_bin2py(self, folder_path: str) -> int:
        """
        Get total number of frames from a bin2py folder.
        Returns the total sample count, or None if unable to read.
        """
        try:
            import bin2py
            with bin2py.PyBinFileReader(folder_path, chunk_samples=RW_BLOCKSIZE, is_row_major=True) as pbfr:
                return pbfr.length
        except Exception as e:
            print(f"Warning: Could not read bin2py folder {folder_path}: {e}")
            return None
    
    def _read_frames_from_bin2py(
        self,
        folder_path: str,
        start_frame: int,
        num_frames: int
    ) -> np.ndarray:
        """
        Read num_frames frames starting from start_frame from a bin2py folder.
        
        Returns float32 array of shape [samples, electrodes], or None if not enough data available.
        Note: bin2py returns [electrodes, samples] which we transpose to [samples, electrodes].
        Also note: bin2py channel 0 is TTL, so we skip it and return only channels 1+.
        """
        try:
            import bin2py
            with bin2py.PyBinFileReader(folder_path, chunk_samples=RW_BLOCKSIZE, is_row_major=True) as pbfr:
                total_samples = pbfr.length
                n_electrodes = pbfr.num_electrodes
                
                if start_frame + num_frames > total_samples:
                    return None
                
                # Preallocate array (excluding channel 0 which is TTL)
                # bin2py has n_electrodes channels, channel 0 is TTL, rest are data
                data = np.zeros((num_frames, n_electrodes), dtype=np.float32)
                
                # Read data in chunks
                data_offset = 0
                for chunk_start in range(start_frame, start_frame + num_frames, RW_BLOCKSIZE):
                    n_samples_to_get = min(RW_BLOCKSIZE, start_frame + num_frames - chunk_start)
                    chunk = pbfr.get_data(chunk_start, n_samples_to_get)
                    
                    # chunk is [electrodes, samples], skip channel 0 and transpose
                    # Skip TTL channel (index 0), take channels 1 onwards
                    chunk_data = chunk[1:, :].T  # Now [samples, electrodes]
                    
                    data[data_offset:data_offset + n_samples_to_get, :] = chunk_data
                    data_offset += n_samples_to_get
                
                return data
                
        except Exception as e:
            print(f"Warning: Could not read data from bin2py folder {folder_path}: {e}")
            return None
