// ============================================================
// App Core - Navigation, API, Toast
// ============================================================

const API_BASE = '';

async function api(endpoint, options = {}) {
  try {
    const res = await fetch(`${API_BASE}/api${endpoint}`, {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (e) {
    console.error(`API Error: ${endpoint}`, e);
    return null;
  }
}

function toast(msg, type = 'success') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = `toast ${type} show`;
  setTimeout(() => el.className = 'toast', 2500);
}

// Navigation
document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', (e) => {
    e.preventDefault();
    const page = item.dataset.page;
    
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    item.classList.add('active');
    
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById(`page-${page}`).classList.add('active');
    
    if (page === 'dashboard') loadDashboard();
    if (page === 'memory') loadMemory();
    if (page === 'skills') loadSkills();
    if (page === 'logs') loadLogs();
    if (page === 'config') loadConfig();
  });
});

// Auto-refresh
let refreshTimer;
function startAutoRefresh() {
  refreshTimer = setInterval(() => {
    const activePage = document.querySelector('.page.active');
    if (activePage && activePage.id === 'page-dashboard') {
      loadDashboard();
    }
  }, 5000);
}

// Init
document.addEventListener('DOMContentLoaded', () => {
  loadDashboard();
  loadStatus();
  startAutoRefresh();
});

async function loadStatus() {
  const data = await api('/status');
  if (data) {
    document.getElementById('agent-version').textContent = `v${data.version}`;
    document.getElementById('cycle-count').textContent = data.cycle_count;
    const dot = document.getElementById('status-dot').querySelector('.dot');
    const text = document.getElementById('status-text');
    if (data.status === 'idle' || data.status === 'initialized') {
      dot.className = 'dot green';
      text.textContent = 'Online';
    } else if (data.status === 'running') {
      dot.className = 'dot yellow';
      text.textContent = 'Running';
    } else {
      dot.className = 'dot red';
      text.textContent = 'Error';
    }
  }
}

async function runCycle() {
  toast('Running cycle...', 'success');
  const data = await api('/cycle', { method: 'POST' });
  if (data) {
    toast(`Cycle #${data.cycle} completed in ${data.duration_ms}ms`, 'success');
    loadDashboard();
  } else {
    toast('Cycle failed', 'error');
  }
}
