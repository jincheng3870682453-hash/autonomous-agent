// ============================================================
// Memory Explorer
// ============================================================

async function loadMemory(category) {
  const params = category ? `?category=${encodeURIComponent(category)}` : '';
  const data = await api(`/memory/recall${params}&limit=50`);
  if (!data) return;

  // Update category dropdown
  const select = document.getElementById('memory-category');
  if (select.options.length <= 1) {
    const cats = [...new Set(data.map(d => d.category))];
    cats.forEach(c => {
      select.innerHTML += `<option value="${c}">${c}</option>`;
    });
  }

  const container = document.getElementById('memory-results');
  container.innerHTML = data.map(m => `
    <div class="memory-card">
      <div class="card-header">
        <span class="card-category">${m.category}</span>
        <span style="font-size:11px;color:var(--text-muted)">conf: ${m.confidence}</span>
      </div>
      <div class="card-key">${m.key}</div>
      <div class="card-value">${truncate(m.value, 200)}</div>
      <div class="card-meta">
        <span>📅 ${(m.updated_at || m.created_at || '').slice(0,19)}</span>
        <span>👁 ${m.access_count} views</span>
      </div>
    </div>
  `).join('') || '<p style="color:var(--text-muted);padding:20px">No memories found</p>';
}

async function searchMemory() {
  const query = document.getElementById('memory-search').value.trim();
  if (!query) { loadMemory(); return; }
  
  const data = await api('/memory/search', {
    method: 'POST',
    body: JSON.stringify({ query, limit: 30 })
  });
  
  const container = document.getElementById('memory-results');
  if (data && data.length > 0) {
    container.innerHTML = data.map(m => `
      <div class="memory-card">
        <div class="card-header">
          <span class="card-category">${m.category}</span>
          <span style="font-size:11px;color:var(--text-muted)">conf: ${m.confidence}</span>
        </div>
        <div class="card-key">${m.key}</div>
        <div class="card-value">${truncate(m.value, 200)}</div>
      </div>
    `).join('');
  } else {
    container.innerHTML = '<p style="color:var(--text-muted);padding:20px">No results for "' + query + '"</p>';
  }
}

function truncate(str, len) {
  if (!str) return '';
  try {
    const parsed = JSON.parse(str);
    str = JSON.stringify(parsed, null, 2);
  } catch(e) {}
  return str.length > len ? str.slice(0, len) + '...' : str;
}
