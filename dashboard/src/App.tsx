import { Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { AppLayout } from './components/Layout/AppLayout';
import { OverviewView } from './components/Overview/OverviewView';
import { FileExplorerView } from './components/FileExplorer/FileExplorerView';
import { FileDetailView } from './components/FileExplorer/FileDetailView';
import { FocusUnitsView } from './components/FocusUnits/FocusUnitsView';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AppLayout>
        <Routes>
          <Route path="/" element={<OverviewView />} />
          <Route path="/files" element={<FileExplorerView />} />
          <Route path="/files/:filename" element={<FileDetailView />} />
          <Route path="/focus-units" element={<FocusUnitsView />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppLayout>
    </ThemeProvider>
  );
}

export default App;
