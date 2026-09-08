const API_BASE = window.location.port === '5173' ? 'http://localhost:8000/api' : '/api';

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}

export async function fetchCarlaStatus() {
  const res = await fetch(`${API_BASE}/carla/status`);
  return res.json();
}

export async function connectCarla(host: string = 'localhost', port: number = 2000) {
  const res = await fetch(`${API_BASE}/carla/connect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ host, port })
  });
  return res.json();
}

export async function setDriver(driver: 'NONE' | 'META' | 'CARLA') {
  const res = await fetch(`${API_BASE}/driver/set`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ driver })
  });
  return res.json();
}

export async function getDriverStatus() {
  const res = await fetch(`${API_BASE}/driver/status`);
  return res.json();
}

export async function fetchScenarios() {
  const res = await fetch(`${API_BASE}/scenarios`);
  return res.json();
}

export async function loadScenario(scenarioId: string) {
  const res = await fetch(`${API_BASE}/scenarios/load`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario_id: scenarioId })
  });
  return res.json();
}

export async function startSimulation() {
  const res = await fetch(`${API_BASE}/simulation/engine/start`, { method: 'POST' });
  return res.json();
}

export async function stopSimulation() {
  const res = await fetch(`${API_BASE}/simulation/engine/stop`, { method: 'POST' });
  return res.json();
}

export async function resetSimulation() {
  const res = await fetch(`${API_BASE}/simulation/engine/reset`, { method: 'POST' });
  return res.json();
}

export async function fetchSimulationState() {
  const res = await fetch(`${API_BASE}/simulation/state`);
  return res.json();
}

export async function fetchMetrics() {
  const res = await fetch(`${API_BASE}/metrics`);
  return res.json();
}

export async function fetchEvents() {
  const res = await fetch(`${API_BASE}/events`);
  return res.json();
}

export async function fetchBenchmarkResults() {
  const res = await fetch(`${API_BASE}/results`);
  return res.json();
}

export function getExportCsvUrl(): string {
  return `${API_BASE}/results/export`;
}
