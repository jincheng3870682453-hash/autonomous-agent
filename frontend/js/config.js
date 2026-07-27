// ============================================================
// Configuration Viewer
// ============================================================

async function loadConfig() {
  const data = await api('/growth/config');
  if (!data) return;

  const container = document.getElementById('config-display');
  // Remove sensitive keys
  const sanitized = { ...data };
  if (sanitized.llm) sanitized.llm.api_key = sanitized.llm.api_key ? '***' : '';
  if (sanitized.channels?.telegram) sanitized.channels.telegram.bot_token = sanitized.channels.telegram.bot_token ? '***' : '';
  if (sanitized.channels?.discord) sanitized.channels.discord.bot_token = sanitized.channels.discord.bot_token ? '***' : '';

  container.textContent = JSON.stringify(sanitized, null, 2);
}
