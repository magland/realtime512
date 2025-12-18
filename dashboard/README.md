# Realtime512 Dashboard

A real-time web dashboard for monitoring and visualizing multi-electrode array recording data processed by realtime512.

## Features

- **Overview Dashboard**: View experiment configuration, processing status, and file summary
- **File Explorer**: Browse processed files and their processing status
- **Time Series Viewer**: Visualize raw, filtered, or shifted electrode signals
- **Electrode Heatmap**: View per-channel spike statistics and activity patterns
- **Real-time Updates**: Automatic polling for new processed data

## Prerequisites

- Node.js (v18 or later)
- npm or yarn
- realtime512 backend server running (`realtime512 serve`)

## Installation

Dependencies should already be installed. If not, run:

```bash
npm install
```

## Running the Dashboard

1. Start the realtime512 backend server in your experiment directory:
   ```bash
   cd /path/to/experiment
   realtime512 serve
   ```

2. In a new terminal, start the dashboard development server:
   ```bash
   cd dashboard
   npm run dev
   ```

3. Open your browser and navigate to:
   ```
   http://localhost:5173
   ```

## Usage

### Overview Tab
- View experiment configuration (sampling frequency, channels, filter settings)
- Monitor processing status of all files
- See shift coefficients and overall statistics

### File Explorer Tab
- Browse all .bin files being processed
- Check processing status (filtered, shifted, etc.)
- View file metadata (duration, size, frames)

### Time Series Tab
- Select a file and data type (raw/filtered/shifted)
- Specify time range and channels to visualize
- View multi-channel signal plots

### Electrode Heatmap Tab
- Select a processed file
- View firing rates and spike amplitudes by channel
- See summary statistics for the recording

## API Endpoint

The dashboard connects to the backend API at:
```
http://localhost:5000/api
```

If your backend is running on a different host/port, update the `API_BASE_URL` in `src/services/api.ts`.

## Building for Production

To create a production build:

```bash
npm run build
```

The built files will be in the `dist` directory. Serve them with any static file server.

## Development

### Project Structure

```
dashboard/
├── src/
│   ├── components/          # React components
│   │   ├── Layout/         # App layout and navigation
│   │   ├── Overview/       # Overview dashboard
│   │   ├── FileExplorer/   # File browser
│   │   └── Visualization/  # Data visualization components
│   ├── hooks/              # Custom React hooks
│   ├── services/           # API client
│   ├── types/              # TypeScript type definitions
│   ├── App.tsx             # Main app component
│   └── main.tsx            # Entry point
├── package.json
└── vite.config.ts
```

### Technologies Used

- **React** - UI framework
- **TypeScript** - Type safety
- **Material-UI (MUI)** - Component library
- **Recharts** - Data visualization
- **Axios** - HTTP client
- **Vite** - Build tool

## Troubleshooting

### Cannot connect to backend

- Ensure `realtime512 serve` is running
- Check that the backend is running on `http://localhost:5000`
- Verify CORS is enabled for `http://localhost:5173`

### No files showing up

- Confirm .bin files exist in the `raw/` directory
- Wait for processing to complete (check `realtime512 start` output)
- Refresh the File Explorer tab

### Charts not displaying

- Ensure the selected file has been processed (check status chips)
- Verify the time range is valid for the file duration
- Check browser console for errors

## License

Same as realtime512 package.
