import axios from 'axios';
import type {
  Config,
  FilesResponse,
  ShiftCoefficients,
  HighActivityResponse,
  StatsResponse,
  BinaryDataResponse,
  DataType,
} from '../types';

const API_BASE_URL = 'http://localhost:5000/api';

// Get server URL from query parameter if provided
function getServerUrlFromQuery(): string | null {
  const params = new URLSearchParams(window.location.search);
  const serverUrl = params.get('serverUrl');
  if (serverUrl) {
    // Ensure the URL ends with /api if not already present
    return serverUrl.endsWith('/api') ? serverUrl : `${serverUrl}/api`;
  }
  return null;
}

class RealtimeAPI {
  private baseURL: string;

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL;
  }

  async getConfig(): Promise<Config> {
    const response = await axios.get<Config>(`${this.baseURL}/config`);
    return response.data;
  }

  async getFiles(): Promise<FilesResponse> {
    const response = await axios.get<FilesResponse>(`${this.baseURL}/files`);
    return response.data;
  }

  async getShiftCoefficients(): Promise<ShiftCoefficients> {
    const response = await axios.get<ShiftCoefficients>(
      `${this.baseURL}/shift_coefficients`
    );
    return response.data;
  }

  async getHighActivity(filename: string): Promise<HighActivityResponse> {
    const response = await axios.get<HighActivityResponse>(
      `${this.baseURL}/high_activity/${filename}`
    );
    return response.data;
  }

  async getStats(filename: string): Promise<StatsResponse> {
    const response = await axios.get<StatsResponse>(
      `${this.baseURL}/stats/${filename}`
    );
    return response.data;
  }

  async getBinaryData(
    dataType: DataType,
    filename: string,
    startSec?: number,
    endSec?: number
  ): Promise<BinaryDataResponse> {
    const params = new URLSearchParams();
    if (startSec !== undefined) params.append('start_sec', startSec.toString());
    if (endSec !== undefined) params.append('end_sec', endSec.toString());

    const url = `${this.baseURL}/${dataType}/${filename}${
      params.toString() ? '?' + params.toString() : ''
    }`;

    const response = await axios.get(url, {
      responseType: 'arraybuffer',
    });

    const data = new Int16Array(response.data);
    
    // Axios lowercases header names, so we need to access them in lowercase
    const headers = response.headers;
    const numFrames = parseInt(headers['x-num-frames'] || headers['X-Num-Frames'] || '0');
    const numChannels = parseInt(headers['x-num-channels'] || headers['X-Num-Channels'] || '0');
    const samplingFrequency = parseInt(
      headers['x-sampling-frequency'] || headers['X-Sampling-Frequency'] || '0'
    );
    const actualStartSec = parseFloat(headers['x-start-sec'] || headers['X-Start-Sec'] || '0');
    const actualEndSec = parseFloat(headers['x-end-sec'] || headers['X-End-Sec'] || '0');
    
    console.log('Response headers:', headers);
    console.log('Parsed values:', { numFrames, numChannels, samplingFrequency, actualStartSec, actualEndSec });

    return {
      data,
      numFrames,
      numChannels,
      samplingFrequency,
      startSec: actualStartSec,
      endSec: actualEndSec,
    };
  }
}

// Initialize API with custom URL from query parameter if provided, otherwise use default
const customServerUrl = getServerUrlFromQuery();
export const getApiUrl = () => {
  return customServerUrl || API_BASE_URL;
};
export const api = new RealtimeAPI(getApiUrl());
