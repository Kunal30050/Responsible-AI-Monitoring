import axios from 'axios';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

export const fetchDashboardSummary = () =>
  api.get('/api/v1/models/dashboard/summary').then(r => r.data);

export const fetchModels = () =>
  api.get('/api/v1/models/').then(r => r.data);

export const fetchBiasHistory = (modelId: number, hours = 168) =>
  api.get(`/api/v1/bias/${modelId}/history?hours=${hours}`).then(r => r.data);

export const fetchDriftHistory = (modelId: number, hours = 168) =>
  api.get(`/api/v1/drift/${modelId}/history?hours=${hours}`).then(r => r.data);

export const fetchRiskHistory = (modelId: number, hours = 168) =>
  api.get(`/api/v1/risk/${modelId}/history?hours=${hours}`).then(r => r.data);

export const fetchAlertHistory = (hours = 168) =>
  api.get(`/api/v1/alerts/history?hours=${hours}`).then(r => r.data);

export const triggerBiasAnalysis = (data: any) =>
  api.post('/api/v1/bias/analyze', data).then(r => r.data);

export const triggerDriftAnalysis = (data: any) =>
  api.post('/api/v1/drift/analyze', data).then(r => r.data);

export const computeRiskScore = (modelId: number) =>
  api.post(`/api/v1/risk/${modelId}/compute`).then(r => r.data);

export const explainPrediction = (data: any) =>
  api.post('/api/v1/explain/', data).then(r => r.data);

export default api;