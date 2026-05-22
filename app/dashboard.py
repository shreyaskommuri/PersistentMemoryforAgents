HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>PersistentMemory</title>
<style>
:root {
  --bg:       #0d0d10;
  --surface:  #16161c;
  --border:   #252530;
  --text:     #e2e2ee;
  --muted:    #7070a0;
  --accent:   #7c6af7;
  --working:  #f59e0b;
  --episodic: #3b82f6;
  --semantic: #10b981;
  --archived: #6b7280;
  --danger:   #ef4444;
  --live:     #10b981;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  background: var(--bg);
  color: var(--text);
  font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', monospace;
  font-size: 13px;
  line-height: 1.5;
  overflow: hidden;
}

/* ── Header ── */

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  border-bottom: 1px solid var(--border);
  background: var(--surface);
  height: 48px;
}
.header-left  { display: flex; align-items: center; gap: 20px; }
.header-right { display: flex; gap: 8px; align-items: center; }
.header-title { font-size: 14px; font-weight: 600; letter-spacing: -0.3px; }

.tabs { display: flex; gap: 2px; }
.tab {
  padding: 5px 12px;
  border-radius: 5px;
  cursor: pointer;
  font-size: 12px;
  color: var(--muted);
  font-weight: 500;
  transition: background 0.1s, color 0.1s;
}
.tab:hover  { color: var(--text); }
.tab.active { background: var(--border); color: var(--text); }

.badge {
  background: var(--border);
  color: var(--muted);
  padding: 3px 9px;
  border-radius: 4px;
  font-size: 11px;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--muted);
  display: inline-block;
  transition: background 0.3s;
}
.status-dot.live { background: var(--live); box-shadow: 0 0 6px var(--live); animation: pulse 2s ease-in-out infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }

.status-label      { font-size: 11px; color: var(--muted); }
.status-label.live { color: var(--live); }

button {
  background: var(--accent);
  color: #fff;
  border: none;
  padding: 5px 13px;
  border-radius: 5px;
  cursor: pointer;
  font-family: inherit;
  font-size: 12px;
  font-weight: 500;
}
button:hover  { opacity: 0.82; }
button:active { transform: scale(0.97); }
button.ghost  { background: var(--surface); border: 1px solid var(--border); color: var(--text); }

/* ── Layout ── */

.main {
  display: grid;
  grid-template-columns: 220px 1fr;
  height: calc(100vh - 48px);
}

/* ── Sidebar ── */

.sidebar {
  border-right: 1px solid var(--border);
  padding: 14px 12px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.section-label {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.7px;
  color: var(--muted);
  padding: 10px 6px 4px;
}
.section-label:first-child { padding-top: 2px; }

.tier-button {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 7px 10px;
  border-radius: 6px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: background 0.12s, border-color 0.12s;
}
.tier-button:hover        { background: var(--surface); }
.tier-button.active       { background: var(--surface); border-color: var(--accent); }
.tier-label               { display: flex; align-items: center; gap: 7px; }
.tier-title               { font-size: 12px; font-weight: 500; }
.tier-description         { font-size: 10px; color: var(--muted); margin-top: 1px; }
.tier-memory-count        { font-size: 12px; font-weight: 600; color: var(--muted); }
.tier-button.active .tier-memory-count { color: var(--text); }

.color-dot           { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.color-dot-all       { background: var(--accent); }
.color-dot-working   { background: var(--working); }
.color-dot-episodic  { background: var(--episodic); }
.color-dot-semantic  { background: var(--semantic); }
.color-dot-archived  { background: var(--archived); }

.gc-pressure-section { margin-top: 4px; padding: 0 6px; }
.gc-pressure-label   { font-size: 11px; color: var(--muted); margin-bottom: 5px; }
.gc-pressure-bar     { background: var(--border); border-radius: 3px; height: 3px; overflow: hidden; }
.gc-pressure-fill    { background: var(--accent); height: 100%; border-radius: 3px; transition: width 0.4s; }

/* ── Panels ── */

.panel        { display: none; flex-direction: column; overflow: hidden; flex: 1; }
.panel.active { display: flex; }

.toolbar {
  display: flex;
  gap: 8px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
  background: var(--surface);
  align-items: center;
}

.search-input {
  flex: 1;
  background: var(--bg);
  border: 1px solid var(--border);
  color: var(--text);
  padding: 5px 10px;
  border-radius: 5px;
  font-family: inherit;
  font-size: 12px;
  outline: none;
}
.search-input:focus       { border-color: var(--accent); }
.search-input::placeholder { color: var(--muted); }

/* ── GC Preview panel ── */

.gc-preview-panel {
  overflow: hidden;
  max-height: 0;
  transition: max-height 0.25s ease;
  border-bottom: 1px solid transparent;
}
.gc-preview-panel.open { max-height: 260px; border-color: var(--border); overflow-y: auto; }
.gc-preview-body       { padding: 10px 14px; }
.gc-preview-summary    { font-size: 11px; color: var(--muted); margin-bottom: 8px; }
.gc-preview-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  border-bottom: 1px solid var(--border);
  font-size: 11px;
}
.gc-preview-row:last-child { border: none; }
.gc-preview-text  { flex: 1; color: var(--muted); overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.gc-preview-score { color: var(--muted); min-width: 32px; text-align: right; }

/* ── Memory list ── */

.memory-list { flex: 1; overflow-y: auto; padding: 8px; }

/* ── Memory cards ── */

.memory-card {
  border: 1px solid var(--border);
  border-radius: 7px;
  padding: 10px 12px;
  margin-bottom: 5px;
  cursor: pointer;
  transition: border-color 0.12s;
}
.memory-card:hover        { border-color: rgba(124,106,247,0.4); }
.memory-card.open         { border-color: var(--accent); background: var(--surface); }
.memory-card.highlighted  { border-color: var(--live) !important; }

.card-top     { display: flex; align-items: flex-start; gap: 8px; }
.card-content {
  color: var(--text);
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  line-height: 1.45;
  word-break: break-word;
}
.memory-card.open .card-content { display: block; -webkit-line-clamp: unset; white-space: pre-wrap; }
.card-meta   { display: flex; gap: 10px; margin-top: 5px; font-size: 11px; color: var(--muted); }
.card-detail { display: none; margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--border); }
.memory-card.open .card-detail { display: block; }

.tier-pill             { font-size: 10px; font-weight: 600; padding: 2px 6px; border-radius: 3px; white-space: nowrap; flex-shrink: 0; margin-top: 1px; }
.tier-pill-working     { background: rgba(245,158,11,0.15);  color: var(--working); }
.tier-pill-episodic    { background: rgba(59,130,246,0.15);  color: var(--episodic); }
.tier-pill-semantic    { background: rgba(16,185,129,0.15);  color: var(--semantic); }
.tier-pill-archived    { background: rgba(107,114,128,0.15); color: var(--archived); }

.tag-list { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 8px; }
.tag      { background: var(--border); padding: 2px 6px; border-radius: 3px; font-size: 10px; color: var(--muted); }

.score-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 5px; margin-bottom: 8px; }
.score-cell { background: var(--bg); border-radius: 4px; padding: 6px 8px; text-align: center; }
.score-label { font-size: 10px; color: var(--muted); display: block; margin-bottom: 1px; }
.score-value { font-size: 13px; font-weight: 600; }

.gc-prediction {
  margin-bottom: 8px;
  padding: 6px 10px;
  border-radius: 4px;
  font-size: 11px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.pred-keep    { background: rgba(16,185,129,0.1);  color: var(--semantic); }
.pred-promote { background: rgba(124,106,247,0.1); color: var(--accent); }
.pred-demote  { background: rgba(245,158,11,0.1);  color: var(--working); }
.pred-archive { background: rgba(107,114,128,0.1); color: var(--archived); }
.pred-delete  { background: rgba(239,68,68,0.1);   color: var(--danger); }

.delete-button {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--danger);
  padding: 3px 9px;
  font-size: 11px;
}
.delete-button:hover { background: rgba(239,68,68,0.1); border-color: var(--danger); }

.action-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 5px;
  border-radius: 3px;
  text-transform: uppercase;
  flex-shrink: 0;
}
.action-badge-keep    { background: rgba(16,185,129,0.15);  color: var(--semantic); }
.action-badge-promote { background: rgba(124,106,247,0.15); color: var(--accent); }
.action-badge-demote  { background: rgba(245,158,11,0.15);  color: var(--working); }
.action-badge-archive { background: rgba(107,114,128,0.15); color: var(--archived); }
.action-badge-delete  { background: rgba(239,68,68,0.15);   color: var(--danger); }

/* ── Activity panel ── */

.activity-header {
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
  background: var(--surface);
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.activity-header-label { display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--muted); }

.activity-list { flex: 1; overflow-y: auto; padding: 8px; }

.activity-item {
  border: 1px solid var(--border);
  border-radius: 7px;
  padding: 10px 14px;
  margin-bottom: 5px;
  transition: border-color 0.12s;
}
.activity-item:hover       { border-color: rgba(124,106,247,0.35); }
.activity-item.recent      { border-color: rgba(16,185,129,0.4); }
.activity-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 6px;
}
.activity-prompt { font-size: 12px; color: var(--text); flex: 1; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.activity-time   { font-size: 11px; color: var(--muted); white-space: nowrap; flex-shrink: 0; }
.activity-stats  { display: flex; gap: 12px; font-size: 11px; color: var(--muted); margin-bottom: 6px; }
.activity-cwd    { font-size: 10px; color: var(--muted); margin-top: 4px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }

.memory-chips { display: flex; flex-wrap: wrap; gap: 4px; }
.memory-chip  {
  background: var(--border);
  padding: 2px 7px;
  border-radius: 3px;
  font-size: 10px;
  color: var(--muted);
  cursor: pointer;
  transition: background 0.1s, color 0.1s;
}
.memory-chip:hover { background: rgba(124,106,247,0.15); color: var(--accent); }

/* ── Empty / loading states ── */

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 180px;
  color: var(--muted);
  gap: 8px;
  font-size: 12px;
}
.spinner {
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  width: 16px;
  height: 16px;
  animation: spin 0.6s linear infinite;
  display: inline-block;
}
@keyframes spin { to { transform: rotate(360deg); } }

.toast {
  position: fixed;
  bottom: 20px;
  right: 20px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 9px 15px;
  font-size: 12px;
  opacity: 0;
  transform: translateY(6px);
  transition: all 0.18s;
  pointer-events: none;
}
.toast.visible    { opacity: 1; transform: translateY(0); }
.toast.success    { border-color: var(--semantic); color: var(--semantic); }
.toast.error      { border-color: var(--danger);   color: var(--danger); }

::-webkit-scrollbar       { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }
</style>
</head>
<body>

<div class="header">
  <div class="header-left">
    <span class="header-title">PersistentMemory</span>
    <div class="tabs">
      <div class="tab active" onclick="switchTab('memories')">Memories</div>
      <div class="tab" onclick="switchTab('activity')">
        Activity <span id="activity-count" style="font-size:10px;opacity:0.6"></span>
      </div>
    </div>
  </div>
  <div class="header-right">
    <span class="status-dot" id="status-dot"></span>
    <span class="status-label" id="status-label">idle</span>
    <span class="badge" id="badge-total">— memories</span>
    <span class="badge" id="badge-tokens">— tokens</span>
    <button class="ghost" onclick="toggleGCPreview()">GC Preview</button>
    <button onclick="runGC()">Run GC</button>
  </div>
</div>

<div class="main">

  <!-- Sidebar -->
  <div class="sidebar">
    <div class="section-label">Tiers</div>
    <div class="tier-button active" id="tier-btn-all" onclick="setTierFilter(null)">
      <div class="tier-label">
        <div class="color-dot color-dot-all"></div>
        <div><div class="tier-title">All</div></div>
      </div>
      <span class="tier-memory-count" id="count-all">—</span>
    </div>
    <div class="tier-button" id="tier-btn-working" onclick="setTierFilter('working')">
      <div class="tier-label">
        <div class="color-dot color-dot-working"></div>
        <div>
          <div class="tier-title">Working</div>
          <div class="tier-description">L1 · max 1 h</div>
        </div>
      </div>
      <span class="tier-memory-count" id="count-working">—</span>
    </div>
    <div class="tier-button" id="tier-btn-episodic" onclick="setTierFilter('episodic')">
      <div class="tier-label">
        <div class="color-dot color-dot-episodic"></div>
        <div>
          <div class="tier-title">Episodic</div>
          <div class="tier-description">L2 · max 24 h</div>
        </div>
      </div>
      <span class="tier-memory-count" id="count-episodic">—</span>
    </div>
    <div class="tier-button" id="tier-btn-semantic" onclick="setTierFilter('semantic')">
      <div class="tier-label">
        <div class="color-dot color-dot-semantic"></div>
        <div>
          <div class="tier-title">Semantic</div>
          <div class="tier-description">RAM · max 7 d</div>
        </div>
      </div>
      <span class="tier-memory-count" id="count-semantic">—</span>
    </div>
    <div class="tier-button" id="tier-btn-archived" onclick="setTierFilter('archived')">
      <div class="tier-label">
        <div class="color-dot color-dot-archived"></div>
        <div>
          <div class="tier-title">Archived</div>
          <div class="tier-description">Disk · unlimited</div>
        </div>
      </div>
      <span class="tier-memory-count" id="count-archived">—</span>
    </div>

    <div class="section-label" style="margin-top:8px">GC Pressure</div>
    <div class="gc-pressure-section">
      <div class="gc-pressure-label"><span id="gc-pressure-count">—</span> memories would change tier</div>
      <div class="gc-pressure-bar">
        <div class="gc-pressure-fill" id="gc-pressure-fill" style="width:0"></div>
      </div>
    </div>
  </div>

  <!-- Content area -->
  <div style="display:flex; flex-direction:column; overflow:hidden; flex:1">

    <!-- Memories panel -->
    <div class="panel active" id="panel-memories">
      <div class="toolbar">
        <input class="search-input" id="search-input" placeholder="Search memories…" oninput="onSearchInput()">
        <button class="ghost" onclick="refresh()">↺</button>
      </div>
      <div class="gc-preview-panel" id="gc-preview-panel">
        <div class="gc-preview-body" id="gc-preview-body">
          <div class="gc-preview-summary">Loading…</div>
        </div>
      </div>
      <div class="memory-list" id="memory-list">
        <div class="empty-state"><div class="spinner"></div><div>Loading…</div></div>
      </div>
    </div>

    <!-- Activity panel -->
    <div class="panel" id="panel-activity">
      <div class="activity-header">
        <div class="activity-header-label">
          Hook injections — click a memory chip to jump to it
        </div>
        <button class="ghost" onclick="loadActivity()">↺</button>
      </div>
      <div class="activity-list" id="activity-list">
        <div class="empty-state"><div class="spinner"></div><div>Loading…</div></div>
      </div>
    </div>

  </div>
</div>

<div class="toast" id="toast"></div>

<script>
let memories = [];
let activeTier = null;
let expandedMemoryId = null;
let gcPreviewOpen = false;
let searchTimer = null;
let lastActivityTimestamp = null;

// ── Startup ───────────────────────────────────────────────────────────────────

window.onload = async () => {
  try { await fetch('/reload', { method: 'POST' }); } catch (_) {}
  loadStats();
  loadMemories();
  loadActivity();
  setInterval(async () => {
    await loadActivity();
    await loadStats();
  }, 4000);
};

// ── Tab switching ─────────────────────────────────────────────────────────────

function switchTab(name) {
  document.querySelectorAll('.tab').forEach((tab, i) => {
    tab.classList.toggle('active', ['memories', 'activity'][i] === name);
  });
  document.querySelectorAll('.panel').forEach(panel => panel.classList.remove('active'));
  document.getElementById('panel-' + name).classList.add('active');
  if (name === 'activity') loadActivity();
}

// ── Status indicator ──────────────────────────────────────────────────────────

function updateStatusIndicator(log) {
  const dot   = document.getElementById('status-dot');
  const label = document.getElementById('status-label');

  if (!log.length) {
    dot.className   = 'status-dot';
    label.textContent = 'no activity';
    label.className = 'status-label';
    return;
  }

  const secondsAgo = (Date.now() - new Date(log[0].ts)) / 1000;

  if (secondsAgo < 300) {
    dot.className     = 'status-dot live';
    label.textContent = secondsAgo < 30 ? 'live' : timeAgo(log[0].ts);
    label.className   = 'status-label live';
  } else {
    dot.className     = 'status-dot';
    label.textContent = timeAgo(log[0].ts);
    label.className   = 'status-label';
  }
}

// ── Stats ─────────────────────────────────────────────────────────────────────

async function loadStats() {
  try {
    const stats = await apiFetch('/memory/stats');
    document.getElementById('badge-total').textContent  = stats.total + ' memories';
    document.getElementById('badge-tokens').textContent = formatNumber(stats.total_tokens) + ' tokens';
    document.getElementById('count-all').textContent    = stats.total;

    for (const tier of ['working', 'episodic', 'semantic', 'archived']) {
      const tierData = stats.by_tier[tier] || {};
      document.getElementById('count-' + tier).textContent = tierData.count || 0;
    }

    const pressurePct = stats.total ? Math.min(100, (stats.gc_pressure / stats.total) * 100) : 0;
    document.getElementById('gc-pressure-count').textContent = stats.gc_pressure || 0;
    document.getElementById('gc-pressure-fill').style.width  = pressurePct + '%';
  } catch (_) {}
}

// ── Memories ──────────────────────────────────────────────────────────────────

async function loadMemories() {
  document.getElementById('memory-list').innerHTML =
    '<div class="empty-state"><div class="spinner"></div><div>Loading…</div></div>';
  try {
    const url = activeTier ? '/memories?memory_type=' + activeTier : '/memories';
    memories = await apiFetch(url);
    renderMemories(memories);
    loadStats();
  } catch (_) {
    document.getElementById('memory-list').innerHTML =
      '<div class="empty-state">⚠ Failed to load</div>';
  }
}

function renderMemories(list) {
  if (!list.length) {
    document.getElementById('memory-list').innerHTML =
      '<div class="empty-state">No memories' + (activeTier ? ' in ' + activeTier : '') + '</div>';
    return;
  }
  document.getElementById('memory-list').innerHTML = list.map(buildMemoryCard).join('');
}

function getTierName(memory) {
  return (memory.memory_type || '').replace('MemoryType.', '');
}

function buildMemoryCard(memory) {
  const tier   = getTierName(memory);
  const isOpen = memory.id === expandedMemoryId;

  const tagHTML = [
    ...(memory.tags || []).map(t => `<span class="tag">${escapeHTML(t)}</span>`),
    ...(memory.linked_entities || []).map(e => `<span class="tag">@${escapeHTML(e)}</span>`),
  ].join('');

  return `
    <div class="memory-card${isOpen ? ' open' : ''}" id="card-${memory.id}" onclick="toggleCard('${memory.id}')">
      <div class="card-top">
        <span class="tier-pill tier-pill-${tier}">${tier}</span>
        <span class="card-content">${escapeHTML(memory.content)}</span>
      </div>
      <div class="card-meta">
        <span>imp ${memory.importance.toFixed(1)}</span>
        <span>${memory.id.slice(0, 8)}</span>
        <span>${timeAgo(memory.created_at)}</span>
        ${memory.access_count ? '<span>↑' + memory.access_count + '</span>' : ''}
      </div>
      <div class="card-detail">
        ${tagHTML ? '<div class="tag-list">' + tagHTML + '</div>' : ''}
        <div class="score-grid" id="scores-${memory.id}">
          <div style="grid-column:span 4; color:var(--muted); font-size:11px">Loading scores…</div>
        </div>
        <button class="delete-button" onclick="event.stopPropagation(); deleteMemory('${memory.id}')">Delete</button>
      </div>
    </div>`;
}

async function toggleCard(id) {
  if (expandedMemoryId === id) {
    expandedMemoryId = null;
    setCardOpen(id, false);
    return;
  }
  if (expandedMemoryId) setCardOpen(expandedMemoryId, false);
  expandedMemoryId = id;
  setCardOpen(id, true);

  try {
    const inspect = await apiFetch('/memory/inspect/' + id);
    const breakdown = inspect.score_breakdown;
    const action    = (inspect.gc_action || 'keep').toLowerCase();
    const fromTier  = getTierName(inspect.memory);
    const toTier    = (inspect.predicted_tier || '').replace('MemoryType.', '') || fromTier;

    document.getElementById('scores-' + id).innerHTML = `
      <div class="score-cell">
        <span class="score-label">importance</span>
        <span class="score-value">${(breakdown.importance || 0).toFixed(3)}</span>
      </div>
      <div class="score-cell">
        <span class="score-label">recency</span>
        <span class="score-value">${(breakdown.recency || 0).toFixed(3)}</span>
      </div>
      <div class="score-cell">
        <span class="score-label">access freq</span>
        <span class="score-value">${(breakdown.access_frequency || 0).toFixed(3)}</span>
      </div>
      <div class="score-cell">
        <span class="score-label">composite</span>
        <span class="score-value" style="color:var(--accent)">${(breakdown.composite || 0).toFixed(3)}</span>
      </div>
      <div class="gc-prediction pred-${action}" style="grid-column:span 4">
        GC would <strong>${action}</strong>${toTier !== fromTier ? ' (→ ' + toTier + ')' : ''}
        — ${inspect.gc_reason || 'no change'}
      </div>`;
  } catch (_) {}
}

function setCardOpen(id, open) {
  const el = document.getElementById('card-' + id);
  if (el) el.classList.toggle('open', open);
}

// ── Search ────────────────────────────────────────────────────────────────────

function onSearchInput() {
  clearTimeout(searchTimer);
  const query = document.getElementById('search-input').value.trim();

  if (!query) {
    renderMemories(memories);
    return;
  }

  searchTimer = setTimeout(async () => {
    try {
      const url = '/memories/search?q=' + encodeURIComponent(query) + '&limit=50'
        + (activeTier ? '&memory_type=' + activeTier : '');
      const results = await apiFetch(url);
      renderMemories(results.map(r => r.memory));
    } catch (_) {}
  }, 260);
}

function setTierFilter(tier) {
  activeTier        = tier;
  expandedMemoryId  = null;

  document.querySelectorAll('.tier-button').forEach(btn => btn.classList.remove('active'));
  document.getElementById('tier-btn-' + (tier || 'all')).classList.add('active');

  const hasSearch = document.getElementById('search-input').value.trim();
  hasSearch ? onSearchInput() : loadMemories();
}

async function refresh() {
  try { await fetch('/reload', { method: 'POST' }); } catch (_) {}
  loadStats();
  loadMemories();
}

// ── GC preview ────────────────────────────────────────────────────────────────

async function toggleGCPreview() {
  gcPreviewOpen = !gcPreviewOpen;
  document.getElementById('gc-preview-panel').classList.toggle('open', gcPreviewOpen);
  if (gcPreviewOpen) await loadGCPreview();
}

async function loadGCPreview() {
  document.getElementById('gc-preview-body').innerHTML =
    '<div class="gc-preview-summary">Loading…</div>';
  try {
    const preview = await apiFetch('/memory/gc/preview');

    const allRows = [
      ...preview.to_delete.map(e  => [e, 'delete']),
      ...preview.to_archive.map(e => [e, 'archive']),
      ...preview.to_demote.map(e  => [e, 'demote']),
      ...preview.to_promote.map(e => [e, 'promote']),
      ...preview.to_keep.map(e    => [e, 'keep']),
    ];

    const rowsHTML = allRows.slice(0, 50).map(([entry, action]) => `
      <div class="gc-preview-row">
        <span class="action-badge action-badge-${action}">${action}</span>
        <span class="gc-preview-text">${escapeHTML(entry.content_preview || '')}</span>
        <span class="gc-preview-score">${(entry.score || 0).toFixed(2)}</span>
      </div>`).join('');

    document.getElementById('gc-preview-body').innerHTML =
      `<div class="gc-preview-summary">${escapeHTML(preview.summary)}</div>` + rowsHTML;

  } catch (_) {
    document.getElementById('gc-preview-body').innerHTML =
      '<div class="gc-preview-summary" style="color:var(--danger)">Failed to load</div>';
  }
}

async function runGC() {
  try {
    const result = await fetch('/gc', { method: 'POST' }).then(r => r.json());
    showToast(
      `GC: +${result.promoted} promoted  −${result.deleted} deleted  ↓${result.archived} archived`,
      'success'
    );
    refresh();
    if (gcPreviewOpen) loadGCPreview();
  } catch (_) {
    showToast('GC failed', 'error');
  }
}

// ── Delete ────────────────────────────────────────────────────────────────────

async function deleteMemory(id) {
  try {
    await fetch('/memories/' + id, { method: 'DELETE' });
    memories       = memories.filter(m => m.id !== id);
    expandedMemoryId = null;
    renderMemories(memories);
    loadStats();
    showToast('Deleted', 'success');
  } catch (_) {
    showToast('Delete failed', 'error');
  }
}

// ── Activity ──────────────────────────────────────────────────────────────────

async function loadActivity() {
  try {
    const log = await apiFetch('/activity?limit=50');

    const hasNew = log.length && log[0].ts !== lastActivityTimestamp;
    if (hasNew) {
      lastActivityTimestamp = log[0].ts;
      const dot = document.getElementById('status-dot');
      dot.style.transform = 'scale(1.5)';
      setTimeout(() => dot.style.transform = '', 300);
    }

    document.getElementById('activity-count').textContent = log.length ? '(' + log.length + ')' : '';
    updateStatusIndicator(log);

    if (document.getElementById('panel-activity').classList.contains('active')) {
      renderActivity(log);
    }
  } catch (_) {}
}

function renderActivity(log) {
  if (!log.length) {
    document.getElementById('activity-list').innerHTML =
      '<div class="empty-state">No hook activity yet — send a prompt in any Claude Code session to see it here</div>';
    return;
  }

  const now = Date.now();
  document.getElementById('activity-list').innerHTML = log.map(entry => {
    const isRecent = (now - new Date(entry.ts)) / 1000 < 60;
    const chips    = (entry.ids || []).map(id =>
      `<span class="memory-chip" onclick="jumpToMemory('${id}')" title="${id}">${id.slice(0, 8)}</span>`
    ).join('');
    const cwd = entry.cwd ? entry.cwd.replace(/.*\\//, '…/') : '';

    return `
      <div class="activity-item${isRecent ? ' recent' : ''}">
        <div class="activity-top">
          <span class="activity-prompt">${escapeHTML(entry.prompt || '')}</span>
          <span class="activity-time">${timeAgo(entry.ts)}</span>
        </div>
        <div class="activity-stats">
          <span>${entry.count} memories</span>
          <span>${entry.tokens} tokens</span>
        </div>
        ${chips ? '<div class="memory-chips">' + chips + '</div>' : ''}
        ${cwd   ? '<div class="activity-cwd">' + escapeHTML(cwd) + '</div>' : ''}
      </div>`;
  }).join('');
}

async function jumpToMemory(id) {
  switchTab('memories');

  if (activeTier !== null) {
    setTierFilter(null);
    await loadMemories();
  }

  await new Promise(resolve => setTimeout(resolve, 60));

  const card = document.getElementById('card-' + id);
  if (card) {
    card.scrollIntoView({ behavior: 'smooth', block: 'center' });
    card.classList.add('highlighted');
    setTimeout(() => card.classList.remove('highlighted'), 2000);
    toggleCard(id);
  } else {
    showToast('Memory no longer in store', 'error');
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

async function apiFetch(path) {
  const response = await fetch(path);
  if (!response.ok) throw response;
  return response.json();
}

function escapeHTML(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function formatNumber(n) {
  return n >= 1000 ? (n / 1000).toFixed(1) + 'k' : String(n);
}

function timeAgo(iso) {
  if (!iso) return '';
  const seconds = (Date.now() - new Date(iso)) / 1000;
  if (seconds < 5)     return 'just now';
  if (seconds < 60)    return Math.round(seconds) + 's ago';
  if (seconds < 3600)  return Math.round(seconds / 60) + 'm ago';
  if (seconds < 86400) return Math.round(seconds / 3600) + 'h ago';
  return Math.round(seconds / 86400) + 'd ago';
}

function showToast(message, type) {
  const el      = document.getElementById('toast');
  el.textContent = message;
  el.className  = 'toast visible ' + (type || 'success');
  setTimeout(() => el.classList.remove('visible'), 3000);
}
</script>
</body>
</html>"""
