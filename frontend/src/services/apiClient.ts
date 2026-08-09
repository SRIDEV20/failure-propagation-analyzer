import axios from 'axios';

const fallbackBaseURL = import.meta.env.DEV ? 'http://localhost:8000' : '';

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? fallbackBaseURL,
  timeout: 6000,
});
