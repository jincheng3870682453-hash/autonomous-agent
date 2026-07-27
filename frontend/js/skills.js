// ============================================================
// Skills Marketplace
// ============================================================

let currentSkillTab = 'installed';

async function loadSkills() {
  const data = await api('/skills');
  if (!data) return;

  renderSkillCards('skills-installed', data.installed || [], true);
  renderSkillCards('skills-available', data.available || [], false);
}

function renderSkillCards(containerId, skills, isInstalled) {
  const container = document.getElementById(containerId);
  container.innerHTML = skills.map(s => `
    <div class="skill-card">
      <div class="skill-header">
        <span class="skill-name">${s.name}</span>
        <span class="skill-version">v${s.version}</span>
      </div>
      <div class="skill-desc">${s.description || 'No description'}</div>
      <div class="skill-tags">
        ${(s.tags || []).map(t => `<span class="tag">${t}</span>`).join('')}
      </div>
      <div class="skill-actions">
        ${isInstalled 
          ? `<span style="color:var(--success);font-size:12px">✅ Installed</span>`
          : `<button class="btn btn-primary btn-sm" onclick="installSkill('${s.name}')">Install</button>`
        }
      </div>
    </div>
  `).join('') || '<p style="color:var(--text-muted);padding:20px">No skills found</p>';
}

function showSkillTab(tab) {
  currentSkillTab = tab;
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  event.target.classList.add('active');
  document.getElementById('skills-installed').style.display = tab === 'installed' ? 'grid' : 'none';
  document.getElementById('skills-available').style.display = tab === 'available' ? 'grid' : 'none';
}

async function installSkill(name) {
  const data = await api('/skills/install', {
    method: 'POST',
    body: JSON.stringify({ name_or_url: name })
  });
  if (data && data.success) {
    toast(`Skill "${name}" installed!`, 'success');
    loadSkills();
  } else {
    toast(`Failed to install "${name}"`, 'error');
  }
}

async function discoverSkills() {
  const data = await api('/skills/discover', { method: 'POST' });
  if (data && data.installed) {
    toast(`Discovered and installed: ${data.installed.join(', ') || 'none'}`, 'success');
    loadSkills();
  }
}
