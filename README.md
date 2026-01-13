# realtime512

Real-time processing of multi-electrode array recordings during acquisition.

## Prerequisites

Before installing realtime512, ensure you have the following installed on your system:

- **Python** >= 3.10
- **Node.js** >= 18 (required for building UI components)
- **npm** (usually comes with Node.js)

### Installing Node.js

Download and install Node.js from [https://nodejs.org](https://nodejs.org). We recommend using the LTS (Long Term Support) version.

To verify your installation:

```bash
node --version  # Should show v18.x.x or higher
npm --version   # Should show npm version
```

## Overview

This package provides tools for real-time processing and monitoring of multi-electrode array (MEA) data. It consists of two main components:

1. **Processing Pipeline** (`realtime512 start`) - Monitors raw data and processes it in real-time
2. **Web Dashboard** - Real-time visualization and monitoring interface
3. **API Server** (`realtime512 serve`) - Serves processed data to the dashboard

## Installation

```bash
pip install -e .
```

## Quick Start

### 1. Set Up Your Experiment

Create an experiment directory and initialize it:

```bash
mkdir my_experiment
cd my_experiment
realtime512 start
```

When you run `realtime512 start` in an empty directory, it will:
- Prompt you for configuration options (sampling frequency, number of channels, acquisition mode)
- Create a `realtime512.yaml` configuration file
- Create necessary directories (`acquisition/`, `raw/`, and `computed/`)
- Wait for data files to appear

**Important:** Before processing can begin, you also need to provide an `electrode_coords.txt` file with X Y coordinates for each electrode (one pair per line). See the [Configuration](#configuration) section for details.

### 2. Start Real-Time Processing

Once configured with `realtime512.yaml` and `electrode_coords.txt` in place, the processing pipeline will automatically:

**Acquisition Mode (recommended):** When configured with `use_acquisition_folder: true`, the system monitors the `acquisition/` directory for incoming data files from your acquisition system. These variable-sized chunks are automatically rechunked into fixed-duration files in `raw/` (configured via `raw_chunk_duration_sec`) before processing.

**Bin2py Acquisition Mode:** When configured with both `use_acquisition_folder: true` and `bin2py: true`, the system monitors the `acquisition/` directory for folders (not files) that can be read using the bin2py library. Each folder is rechunked into fixed-duration `.bin` files in `raw/` with naming like `foldername_001.bin`, `foldername_002.bin`, etc. **Note:** For bin2py mode, you must have the `bin2py` package installed in your Python environment.

**Direct Mode:** When `use_acquisition_folder: false`, the system monitors the `raw/` directory directly for `.bin` files and processes them automatically.

### 3. Start the API Server

In a separate terminal, start the API server:

```bash
cd my_experiment
realtime512 serve
```

This starts a Flask server at `http://localhost:5000` that serves processed data.

### 4. Launch the Web Dashboard

Open your browser to: https://realtime512-dashboard.vercel.app/

Or to run it locally, in another terminal, start the dashboard:

```bash
cd dashboard
npm run dev
```

If running locally, open your browser to `http://localhost:5173` to view the real-time dashboard.

## Dashboard Features

The web dashboard provides:

- **Overview**: Configuration, processing status, and file summary
- **File Explorer**: Browse processed files and their status
- **Time Series Viewer**: Visualize raw, filtered, or shifted signals
- **Electrode Heatmap**: View per-channel spike statistics and firing rates

See [dashboard/README.md](dashboard/README.md) for detailed dashboard documentation.

## Processing Pipeline

The processing pipeline performs the following steps:

1. **Filtering**: Bandpass filter raw signals
2. **Shift Estimation**: Estimate time shift coefficients
3. **High Activity Detection**: Identify periods of high neural activity
4. **Spike Statistics**: Calculate firing rates and spike amplitudes per channel
5. **Time Shift Correction**: Apply time shifts to align signals
6. **Template Extraction**: Extract spike templates

## Configuration

Edit `realtime512.yaml` in your experiment directory:

```yaml
# Basic settings
sampling_frequency: 20000
n_channels: 512

# Acquisition mode (recommended)
use_acquisition_folder: true   # Enable acquisition rechunking
raw_chunk_duration_sec: 10     # Duration in seconds for each processed chunk
bin2py: false                  # Set to true for bin2py folder format

# Filter settings
filter_params:
  lowcut: 300
  highcut: 4000
  order: 4

# Detection thresholds
detect_threshold_for_spike_stats: -40
high_activity_threshold: 3
coarse_sorting_detect_threshold: -80
```

### Experiment Directory Structure

With acquisition mode enabled:

```
my_experiment/
├── realtime512.yaml          # Configuration
├── electrode_coords.txt      # Electrode coordinates
├── acquisition/              # Incoming data from acquisition system
│   ├── chunk_0001.bin       # Variable-sized chunks (standard mode)
│   └── ...                   # Or folders (bin2py mode)
├── raw/                      # Fixed-duration rechunked files
│   ├── raw_0001.bin         # Standard mode: raw_NNNN.bin
│   ├── data0001_001.bin     # Bin2py mode: foldername_NNN.bin
│   └── ...
├── computed/                 # Processed outputs
│   ├── filt/                # Filtered data
│   ├── shifted/             # Time-shifted data
│   ├── coarse_sorting/      # Spike sorting results
│   └── ...
└── focus_units.json         # Tracked units
```

## API Endpoints

The server provides the following REST API endpoints:

- `GET /api/config` - Experiment configuration
- `GET /api/files` - List of files and processing status
- `GET /api/shift_coefficients` - Time shift coefficients
- `GET /api/raw/<filename>` - Raw electrode data
- `GET /api/filt/<filename>` - Filtered data
- `GET /api/shifted/<filename>` - Time-shifted data
- `GET /api/templates/<filename>` - Spike templates
- `GET /api/high_activity/<filename>` - High activity intervals
- `GET /api/stats/<filename>` - Spike statistics

See [realtime512/serve/API.md](realtime512/serve/API.md) for complete API documentation.

## Project Structure

```
realtime512/
├── realtime512/           # Python package
│   ├── start/            # Processing pipeline
│   ├── serve/            # API server
│   └── helpers/          # Processing utilities
├── dashboard/            # React web dashboard
│   ├── src/
│   │   ├── components/  # UI components
│   │   ├── services/    # API client
│   │   └── types/       # TypeScript types
│   └── README.md
└── README.md
```

## Development

### Python Package

```bash
pip install -e .
```

### Dashboard

```bash
cd dashboard
npm install
npm run dev
```

## License

MIT
