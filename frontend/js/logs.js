// ============================================================
// Logs Viewer
// ============================================================

async function loadLogs() {
  const data = await api('/growth/log?limit=50');
  if (!data) return;

  const container = document.getElementById('logs-container');
  container.innerHTML = data.map(g => {
    let cls = 'info';
    if (g.action === 'evolve') cls = 'growth';
    if (g.action === 'self_heal') cls = 'warning';
    if (g.category === 'insight') cls = 'insight';
    
    return `<div class="log-entry ${cls}">
      <span class="log-time">${(g.created_at || '').slice(0,19)}</span>
      <span>[${g.category}]</span> ${g.action}: ${g.detail || ''}
    </div>`;
  }).join('') || '<div class="log-entry">No logs yet</div>';
}
