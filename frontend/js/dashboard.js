// ============================================================
// Dashboard Page
// ============================================================

async function loadDashboard() {
  const data = await api('/status');
  if (!data) return;

  // Stats
  document.getElementById('stat-knowledge').textContent = data.stats?.knowledge?.total || 0;
  document.getElementById('stat-events').textContent = data.stats?.events?.total || 0;
  document.getElementById('stat-growth').textContent = data.stats?.growth?.total || 0;
  document.getElementById('stat-cycles').textContent = data.stats?.cycles?.total || 0;
  document.getElementById('stat-skills').textContent = data.stats?.skills?.installed || 0;
  document.getElementById('stat-graph-nodes').textContent = data.stats?.graph?.nodes || 0;

  // Categories chart
  const categories = data.stats?.knowledge?.categories || {};
  const catChart = document.getElementById('categories-chart');
  const maxVal = Math.max(...Object.values(categories), 1);
  catChart.innerHTML = Object.entries(categories)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([name, count]) => `
      <div class="bar-item">
        <span class="bar-label">${name}</span>
        <div class="bar-track">
          <div class="bar-fill" style="width:${(count/maxVal*100).toFixed(0)}%">${count}</div>
        </div>
      </div>
    `).join('');

  // Cycles
  const cycles = data.recent_cycles || [];
  const cyclesList = document.getElementById('cycles-list');
  cyclesList.innerHTML = cycles.map(c => `
    <div class="list-item">
      <span class="item-title">Cycle #${c.cycle_number}</span>
      <span class="item-meta">${c.status} · ${c.duration_ms}ms · ${c.created_at?.slice(0,19) || ''}</span>
    </div>
  `).join('') || '<div class="list-item"><span class="item-meta">No cycles yet</span></div>';

  // Growth
  const growth = data.recent_growth || [];
  const growthList = document.getElementById('growth-list');
  growthList.innerHTML = growth.map(g => `
    <div class="list-item">
      <span class="item-title">🌱 ${g.action}</span>
      <span class="item-meta">${g.detail || ''} · ${g.created_at?.slice(0,19) || ''}</span>
    </div>
  `).join('') || '<div class="list-item"><span class="item-meta">No growth yet</span></div>';

  // Collector health
  const health = data.collector_health || [];
  const healthList = document.getElementById('collector-health');
  healthList.innerHTML = health.map(h => `
    <div class="list-item">
      <span class="item-title">📡 ${h.name}</span>
      <span class="item-meta">Success: ${h.success} · Rate: ${(h.success_rate*100).toFixed(0)}%</span>
    </div>
  `).join('') || '<div class="list-item"><span class="item-meta">No collectors</span></div>';

  // Update version
  document.getElementById('agent-version').textContent = `v${data.version}`;
  document.getElementById('cycle-count').textContent = data.cycle_count;
}
