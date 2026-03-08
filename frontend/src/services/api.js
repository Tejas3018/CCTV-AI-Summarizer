import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Events API
export const eventsAPI = {
  getRecent: (limit = 100) => api.get(`/api/events?limit=${limit}`),
  getToday: () => api.get('/api/events/today'),
  getByRange: (start, end) => api.get(`/api/events/range?start=${start}&end=${end}`),
  getById: (id) => api.get(`/api/events/${id}`),
  getClipUrl: (id) => `${API_BASE_URL}/api/events/clip/${id}`,
  getThumbnailUrl: (id) => `${API_BASE_URL}/api/events/thumbnail/${id}`,
  getTodayStats: () => api.get('/api/events/stats/today'),
  getStatsByDate: (date) => api.get(`/api/events/stats/day?date=${date}`),
};

// Summary API
export const summaryAPI = {
  getToday: () => api.get('/api/summary/today'),
  getByDate: (date) => api.get(`/api/summary/date/${date}`),
  getRecent: (limit = 7) => api.get(`/api/summary/recent?limit=${limit}`),
  generate: (date = null) => api.post(`/api/summary/generate${date ? `?date=${date}` : ''}`),
  generateSync: (date = null) => api.post(`/api/summary/generate/sync${date ? `?date=${date}` : ''}`),
};

// Query API
export const queryAPI = {
  ask: (query, date = null) => api.post('/api/query/', { query, date }),
  getExamples: () => api.get('/api/query/examples'),
};

export default api;
