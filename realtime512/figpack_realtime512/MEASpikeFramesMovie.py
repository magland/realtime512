from typing import Union

import numpy as np

import figpack
from .figpack_realtime512_extension import figpack_realtime512_extension


class MEASpikeFramesMovie(figpack.ExtensionView):
    def __init__(
        self,
        spike_frames_data: np.ndarray,
        electrode_coords: Union[np.ndarray, list[list[float]]],
        spike_times_sec: np.ndarray,
        spike_labels: np.ndarray,
        sampling_frequency_hz: float,
    ):
        """
        Initialize an MEA Spike Frames Movie view
        
        This view shows only frames that contain spikes, allowing users to step through
        detected spike events. Each frame is associated with a spike time and unit label.

        Args:
            spike_frames_data: Spike frame data with shape (num_spikes, num_channels), dtype int16
            electrode_coords: Electrode coordinates with shape (num_channels, 2)
            spike_times_sec: Spike times in seconds with shape (num_spikes,), dtype float32
            spike_labels: Unit labels for each spike with shape (num_spikes,), dtype int32
            sampling_frequency_hz: Sampling frequency in Hz
        """
        super().__init__(
            extension=figpack_realtime512_extension, view_type="realtime512.MEASpikeFramesMovie"
        )

        # Validate inputs
        if spike_frames_data.ndim != 2:
            raise ValueError(f"spike_frames_data must be 2D array, got shape {spike_frames_data.shape}")

        # Convert electrode_coords to numpy array if needed
        electrode_coords_array = np.array(electrode_coords, dtype=np.float32)
        if electrode_coords_array.ndim != 2 or electrode_coords_array.shape[1] != 2:
            raise ValueError(
                f"electrode_coords must have shape (num_channels, 2), got {electrode_coords_array.shape}"
            )

        num_spikes, num_channels = spike_frames_data.shape
        if electrode_coords_array.shape[0] != num_channels:
            raise ValueError(
                f"Number of electrode coordinates ({electrode_coords_array.shape[0]}) "
                f"must match number of channels ({num_channels})"
            )

        # Validate spike times and labels
        spike_times_sec_array = np.array(spike_times_sec, dtype=np.float32)
        spike_labels_array = np.array(spike_labels, dtype=np.int32)

        if spike_times_sec_array.ndim != 1 or spike_labels_array.ndim != 1:
            raise ValueError("Spike times and labels arrays must be 1-dimensional")

        if len(spike_times_sec_array) != num_spikes:
            raise ValueError(
                f"spike_times_sec length ({len(spike_times_sec_array)}) "
                f"must match number of spikes ({num_spikes})"
            )

        if len(spike_labels_array) != num_spikes:
            raise ValueError(
                f"spike_labels length ({len(spike_labels_array)}) "
                f"must match number of spikes ({num_spikes})"
            )

        self.spike_frames_data = spike_frames_data.astype(np.int16)
        self.electrode_coords = electrode_coords_array
        self.spike_times_sec = spike_times_sec_array
        self.spike_labels = spike_labels_array
        self.sampling_frequency_hz = sampling_frequency_hz
        self.num_spikes = num_spikes
        self.num_channels = num_channels

        # Calculate global min/max/median for normalization
        self.data_min = float(np.min(self.spike_frames_data))
        self.data_max = float(np.max(self.spike_frames_data))
        self.data_median = float(np.median(self.spike_frames_data))

    def write_to_zarr_group(self, group: figpack.Group) -> None:
        """
        Write the data to a Zarr group

        Args:
            group: Zarr group to write data into
        """
        super().write_to_zarr_group(group)

        # Store metadata
        group.attrs["sampling_frequency_hz"] = self.sampling_frequency_hz
        group.attrs["num_spikes"] = self.num_spikes
        group.attrs["num_channels"] = self.num_channels
        group.attrs["data_min"] = self.data_min
        group.attrs["data_max"] = self.data_max
        group.attrs["data_median"] = self.data_median

        # Store electrode coordinates
        group.create_dataset("electrode_coords", data=self.electrode_coords)

        # Store spike frames data with chunking optimized for sequential access
        # Chunk by a reasonable number of spikes (100-200)
        num_spikes_per_chunk = min(200, self.num_spikes)
        chunks = (num_spikes_per_chunk, self.num_channels)

        group.create_dataset("spike_frames_data", data=self.spike_frames_data, chunks=chunks)

        # Store spike times and labels with reasonable chunking
        spike_chunk_size = min(1000, max(1, self.num_spikes))

        group.create_dataset(
            "spike_times_sec",
            data=self.spike_times_sec,
            chunks=(spike_chunk_size,),
        )
        group.create_dataset(
            "spike_labels",
            data=self.spike_labels,
            chunks=(spike_chunk_size,),
        )
