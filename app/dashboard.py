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
body { background: var(--bg); color: var(--text); font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', monospace; font-size: 13px; line-height: 1.5; overflow: hidden; }

/* ── header ── */
.hdr { display: flex; align-items: center; justify-content: space-between; padding: 0 20px; border-bottom: 1px solid var(--border); background: var(--surface); height: 48px; }
.hdr-left { display: flex; align-items: center; gap: 20px; }
.hdr-title { font-size: 14px; font-weight: 600; letter-spacing: -0.3px; }
.tabs { display: flex; gap: 2px; }
.tab { padding: 5px 12px; border-radius: 5px; cursor: pointer; font-size: 12px; color: var(--muted); font-weight: 500; transition: background 0.1s, color 0.1s; }
.tab:hover { color: var(--text); }
.tab.active { background: var(--border); color: var(--text); }
.hdr-right { display: flex; gap: 8px; align-items: center; }
.badge { background: var(--border); color: var(--muted); padding: 3px 9px; border-radius: 4px; font-size: 11px; }
.live-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--muted); display: inline-block; transition: background 0.3s; }
.live-dot.on { background: var(--live); box-shadow: 0 0 6px var(--live); animation: pulse 2s ease-in-out infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.5} }
.live-label { font-size: 11px; color: var(--muted); }
.live-label.on { color: var(--live); }

button { background: var(--accent); color: #fff; border: none; padding: 5px 13px; border-radius: 5px; cursor: pointer; font-family: inherit; font-size: 12px; font-weight: 500; }
button:hover { opacity: 0.82; }
button:active { transform: scale(0.97); }
button.ghost { background: var(--surface); border: 1px solid var(--border); color: var(--text); }

/* ── layout ── */
.main { display: grid; grid-template-columns: 220px 1fr; height: calc(100vh - 48px); }

/* ── sidebar ── */
.sidebar { border-right: 1px solid var(--border); padding: 14px 12px; overflow-y: auto; display: flex; flex-direction: column; gap: 4px; }
.sec-label { font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.7px; color: var(--muted); padding: 10px 6px 4px; }
.sec-label:first-child { padding-top: 2px; }
.tier-btn { display: flex; align-items: center; justify-content: space-between; padding: 7px 10px; border-radius: 6px; cursor: pointer; border: 1px solid transparent; transition: background 0.12s, border-color 0.12s; }
.tier-btn:hover { background: var(--surface); }
.tier-btn.active { background: var(--surface); border-color: var(--accent); }
.tier-left { display: flex; align-items: center; gap: 7px; }
.dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.dot-all      { background: var(--accent); }
.dot-working  { background: var(--working); }
.dot-episodic { background: var(--episodic); }
.dot-semantic { background: var(--semantic); }
.dot-archived { background: var(--archived); }
.tier-name { font-size: 12px; font-weight: 500; }
.tier-sub  { font-size: 10px; color: var(--muted); margin-top: 1px; }
.tier-count { font-size: 12px; font-weight: 600; color: var(--muted); }
.tier-btn.active .tier-count { color: var(--text); }
.gc-section { margin-top: 4px; padding: 0 6px; }
.gc-label { font-size: 11px; color: var(--muted); margin-bottom: 5px; }
.gc-bar { background: var(--border); border-radius: 3px; height: 3px; overflow: hidden; }
.gc-fill { background: var(--accent); height: 100%; border-radius: 3px; transition: width 0.4s; }

/* ── content panels ── */
.panel { display: none; flex-direction: column; overflow: hidden; flex: 1; }
.panel.active { display: flex; }

/* ── memories panel ── */
.toolbar { display: flex; gap: 8px; padding: 10px 14px; border-bottom: 1px solid var(--border); background: var(--surface); align-items: center; }
.search { flex: 1; background: var(--bg); border: 1px solid var(--border); color: var(--text); padding: 5px 10px; border-radius: 5px; font-family: inherit; font-size: 12px; outline: none; }
.search:focus { border-color: var(--accent); }
.search::placeholder { color: var(--muted); }
.gc-panel { overflow: hidden; max-height: 0; transition: max-height 0.25s ease; border-bottom: 1px solid transparent; }
.gc-panel.open { max-height: 260px; border-color: var(--border); overflow-y: auto; }
.gc-inner { padding: 10px 14px; }
.gc-summary { font-size: 11px; color: var(--muted); margin-bottom: 8px; }
.gc-row { display: flex; align-items: center; gap: 8px; padding: 4px 0; border-bottom: 1px solid var(--border); font-size: 11px; }
.gc-row:last-child { border: none; }
.gc-text { flex: 1; color: var(--muted); overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.gc-score-val { color: var(--muted); min-width: 32px; text-align: right; }
.list { flex: 1; overflow-y: auto; padding: 8px; }

/* ── memory cards ── */
.mem { border: 1px solid var(--border); border-radius: 7px; padding: 10px 12px; margin-bottom: 5px; cursor: pointer; transition: border-color 0.12s; }
.mem:hover { border-color: rgba(124,106,247,0.4); }
.mem.open { border-color: var(--accent); background: var(--surface); }
.mem.highlight { border-color: var(--live) !important; }
.mem-top { display: flex; align-items: flex-start; gap: 8px; }
.pill { font-size: 10px; font-weight: 600; padding: 2px 6px; border-radius: 3px; white-space: nowrap; flex-shrink: 0; margin-top: 1px; }
.pill-working  { background: rgba(245,158,11,0.15);  color: var(--working); }
.pill-episodic { background: rgba(59,130,246,0.15);  color: var(--episodic); }
.pill-semantic { background: rgba(16,185,129,0.15);  color: var(--semantic); }
.pill-archived { background: rgba(107,114,128,0.15); color: var(--archived); }
.mem-text { color: var(--text); overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; line-height: 1.45; word-break: break-word; }
.mem.open .mem-text { display: block; -webkit-line-clamp: unset; white-space: pre-wrap; }
.mem-meta { display: flex; gap: 10px; margin-top: 5px; font-size: 11px; color: var(--muted); }
.mem-detail { display: none; margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--border); }
.mem.open .mem-detail { display: block; }
.tags { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 8px; }
.tag { background: var(--border); padding: 2px 6px; border-radius: 3px; font-size: 10px; color: var(--muted); }
.scores { display: grid; grid-template-columns: repeat(4, 1fr); gap: 5px; margin-bottom: 8px; }
.score-box { background: var(--bg); border-radius: 4px; padding: 6px 8px; text-align: center; }
.score-lbl { font-size: 10px; color: var(--muted); display: block; margin-bottom: 1px; }
.score-num { font-size: 13px; font-weight: 600; }
.gc-pred { margin-bottom: 8px; padding: 6px 10px; border-radius: 4px; font-size: 11px; display: flex; align-items: center; gap: 6px; }
.pred-keep    { background: rgba(16,185,129,0.1);  color: var(--semantic); }
.pred-promote { background: rgba(124,106,247,0.1); color: var(--accent); }
.pred-demote  { background: rgba(245,158,11,0.1);  color: var(--working); }
.pred-archive { background: rgba(107,114,128,0.1); color: var(--archived); }
.pred-delete  { background: rgba(239,68,68,0.1);   color: var(--danger); }
.del-btn { background: transparent; border: 1px solid var(--border); color: var(--danger); padding: 3px 9px; font-size: 11px; }
.del-btn:hover { background: rgba(239,68,68,0.1); border-color: var(--danger); }
.ab { font-size: 10px; font-weight: 600; padding: 2px 5px; border-radius: 3px; text-transform: uppercase; flex-shrink: 0; }
.ab-keep    { background: rgba(16,185,129,0.15);  color: var(--semantic); }
.ab-promote { background: rgba(124,106,247,0.15); color: var(--accent); }
.ab-demote  { background: rgba(245,158,11,0.15);  color: var(--working); }
.ab-archive { background: rgba(107,114,128,0.15); color: var(--archived); }
.ab-delete  { background: rgba(239,68,68,0.15);   color: var(--danger); }

/* ── activity panel ── */
.act-list { flex: 1; overflow-y: auto; padding: 8px; }
.act-header { padding: 10px 14px; border-bottom: 1px solid var(--border); background: var(--surface); display: flex; align-items: center; justify-content: space-between; }
.act-header-left { display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--muted); }
.act-item { border: 1px solid var(--border); border-radius: 7px; padding: 10px 14px; margin-bottom: 5px; transition: border-color 0.12s; }
.act-item:hover { border-color: rgba(124,106,247,0.35); }
.act-item.fresh { border-color: rgba(16,185,129,0.4); }
.act-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; margin-bottom: 6px; }
.act-prompt { font-size: 12px; color: var(--text); flex: 1; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.act-time { font-size: 11px; color: var(--muted); white-space: nowrap; flex-shrink: 0; }
.act-meta { display: flex; gap: 12px; font-size: 11px; color: var(--muted); margin-bottom: 6px; }
.act-chips { display: flex; flex-wrap: wrap; gap: 4px; }
.act-chip { background: var(--border); padding: 2px 7px; border-radius: 3px; font-size: 10px; color: var(--muted); cursor: pointer; transition: background 0.1s, color 0.1s; }
.act-chip:hover { background: rgba(124,106,247,0.15); color: var(--accent); }
.act-cwd { font-size: 10px; color: var(--muted); margin-top: 4px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }

/* ── empty / loading ── */
.empty { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 180px; color: var(--muted); gap: 8px; font-size: 12px; }
.spin { border: 2px solid var(--border); border-top-color: var(--accent); border-radius: 50%; width: 16px; height: 16px; animation: spin 0.6s linear infinite; display: inline-block; }
@keyframes spin { to { transform: rotate(360deg); } }
.toast { position: fixed; bottom: 20px; right: 20px; background: var(--surface); border: 1px solid var(--border); border-radius: 6px; padding: 9px 15px; font-size: 12px; opacity: 0; transform: translateY(6px); transition: all 0.18s; pointer-events: none; }
.toast.show { opacity: 1; transform: translateY(0); }
.toast.ok  { border-color: var(--semantic); color: var(--semantic); }
.toast.err { border-color: var(--danger);   color: var(--danger); }
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }
</style>
</head>
<body>

<div class="hdr">
  <div class="hdr-left">
    <span class="hdr-title">PersistentMemory</span>
    <div class="tabs">
      <div class="tab active" onclick="switchTab('memories')">Memories</div>
      <div class="tab" onclick="switchTab('activity')">Activity <span id="act-count-badge" style="font-size:10px;opacity:0.6"></span></div>
    </div>
  </div>
  <div class="hdr-right">
    <span class="live-dot" id="live-dot"></span>
    <span class="live-label" id="live-label">idle</span>
    <span class="badge" id="b-total">— memories</span>
    <span class="badge" id="b-tokens">— tokens</span>
    <button class="ghost" onclick="toggleGC()">GC Preview</button>
    <button onclick="runGC()">Run GC</button>
  </div>
</div>

<div class="main">
  <!-- sidebar -->
  <div class="sidebar">
    <div class="sec-label">Tiers</div>
    <div class="tier-btn active" id="tb-all" onclick="setTier(null)">
      <div class="tier-left"><div class="dot dot-all"></div><div><div class="tier-name">All</div></div></div>
      <span class="tier-count" id="cnt-all">—</span>
    </div>
    <div class="tier-btn" id="tb-working" onclick="setTier('working')">
      <div class="tier-left"><div class="dot dot-working"></div><div><div class="tier-name">Working</div><div class="tier-sub">L1 · max 1 h</div></div></div>
      <span class="tier-count" id="cnt-working">—</span>
    </div>
    <div class="tier-btn" id="tb-episodic" onclick="setTier('episodic')">
      <div class="tier-left"><div class="dot dot-episodic"></div><div><div class="tier-name">Episodic</div><div class="tier-sub">L2 · max 24 h</div></div></div>
      <span class="tier-count" id="cnt-episodic">—</span>
    </div>
    <div class="tier-btn" id="tb-semantic" onclick="setTier('semantic')">
      <div class="tier-left"><div class="dot dot-semantic"></div><div><div class="tier-name">Semantic</div><div class="tier-sub">RAM · max 7 d</div></div></div>
      <span class="tier-count" id="cnt-semantic">—</span>
    </div>
    <div class="tier-btn" id="tb-archived" onclick="setTier('archived')">
      <div class="tier-left"><div class="dot dot-archived"></div><div><div class="tier-name">Archived</div><div class="tier-sub">Disk · unlimited</div></div></div>
      <span class="tier-count" id="cnt-archived">—</span>
    </div>
    <div class="sec-label" style="margin-top:8px">GC Pressure</div>
    <div class="gc-section">
      <div class="gc-label"><span id="gc-n">—</span> memories would change tier</div>
      <div class="gc-bar"><div class="gc-fill" id="gc-fill" style="width:0"></div></div>
    </div>
  </div>

  <!-- content -->
  <div style="display:flex;flex-direction:column;overflow:hidden;flex:1">

    <!-- memories panel -->
    <div class="panel active" id="panel-memories">
      <div class="toolbar">
        <input class="search" id="search" placeholder="Search memories…" oninput="onSearch()">
        <button class="ghost" onclick="refresh()">↺</button>
      </div>
      <div class="gc-panel" id="gc-panel">
        <div class="gc-inner" id="gc-inner"><div class="gc-summary">Loading…</div></div>
      </div>
      <div class="list" id="list">
        <div class="empty"><div class="spin"></div><div>Loading…</div></div>
      </div>
    </div>

    <!-- activity panel -->
    <div class="panel" id="panel-activity">
      <div class="act-header">
        <div class="act-header-left">
          <span>Hook injections — click a memory chip to jump to it</span>
        </div>
        <button class="ghost" onclick="loadActivity()">↺</button>
      </div>
      <div class="act-list" id="act-list">
        <div class="empty"><div class="spin"></div><div>Loading…</div></div>
      </div>
    </div>

  </div>
</div>

<div class="toast" id="toast"></div>

<script>
let all = [], activeTier = null, expandedId = null, gcOpen = false, searchTmr = null;
let activityLog = [], lastActivityTs = null, pollTimer = null;

window.onload = () => {
  loadStats();
  loadMems();
  loadActivity();
  startPolling();
};

// ── tab switching ─────────────────────────────────────────────────────────────
function switchTab(name) {
  document.querySelectorAll('.tab').forEach((t,i) => t.classList.toggle('active', ['memories','activity'][i] === name));
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  $('panel-'+name).classList.add('active');
  if (name === 'activity') loadActivity();
}

// ── live indicator + polling ──────────────────────────────────────────────────
function startPolling() {
  pollTimer = setInterval(async () => {
    await loadActivity();
    await loadStats();
  }, 4000);
}

function updateLiveIndicator(log) {
  const dot = $('live-dot'), lbl = $('live-label');
  if (!log.length) { dot.className = 'live-dot'; lbl.textContent = 'no activity'; lbl.className = 'live-label'; return; }
  const secAgo = (Date.now() - new Date(log[0].ts)) / 1000;
  if (secAgo < 30) {
    dot.className = 'live-dot on'; lbl.textContent = 'live'; lbl.className = 'live-label on';
  } else if (secAgo < 300) {
    dot.className = 'live-dot on'; lbl.textContent = age(log[0].ts); lbl.className = 'live-label on';
  } else {
    dot.className = 'live-dot'; lbl.textContent = age(log[0].ts); lbl.className = 'live-label';
  }
}

// ── stats ─────────────────────────────────────────────────────────────────────
async function loadStats() {
  try {
    const s = await api('/memory/stats');
    $('b-total').textContent = s.total + ' memories';
    $('b-tokens').textContent = fmt(s.total_tokens) + ' tokens';
    $('cnt-all').textContent = s.total;
    for (const t of ['working','episodic','semantic','archived']) {
      const d = s.by_tier[t] || {};
      $('cnt-'+t).textContent = d.count || 0;
    }
    const pct = s.total ? Math.min(100, (s.gc_pressure/s.total)*100) : 0;
    $('gc-n').textContent = s.gc_pressure || 0;
    $('gc-fill').style.width = pct + '%';
  } catch(_) {}
}

// ── memories ──────────────────────────────────────────────────────────────────
async function loadMems() {
  $('list').innerHTML = '<div class="empty"><div class="spin"></div><div>Loading…</div></div>';
  try {
    const url = activeTier ? '/memories?memory_type='+activeTier : '/memories';
    all = await api(url);
    render(all);
    loadStats();
  } catch(_) {
    $('list').innerHTML = '<div class="empty">⚠ Failed to load</div>';
  }
}

function render(mems) {
  if (!mems.length) {
    $('list').innerHTML = '<div class="empty">No memories'+(activeTier?' in '+activeTier:'')+'</div>';
    return;
  }
  $('list').innerHTML = mems.map(m => card(m)).join('');
}

function tier(m) { return (m.memory_type||'').replace('MemoryType.',''); }

function card(m) {
  const t = tier(m), isOpen = m.id === expandedId;
  const tags = [...(m.tags||[]).map(x=>'<span class="tag">'+esc(x)+'</span>'),
                ...(m.linked_entities||[]).map(x=>'<span class="tag">@'+esc(x)+'</span>')].join('');
  return `<div class="mem${isOpen?' open':''}" id="m-${m.id}" onclick="toggle('${m.id}')">
    <div class="mem-top">
      <span class="pill pill-${t}">${t}</span>
      <span class="mem-text">${esc(m.content)}</span>
    </div>
    <div class="mem-meta">
      <span>imp ${m.importance.toFixed(1)}</span>
      <span>${m.id.slice(0,8)}</span>
      <span>${age(m.created_at)}</span>
      ${m.access_count ? '<span>↑'+m.access_count+'</span>' : ''}
    </div>
    <div class="mem-detail">
      ${tags ? '<div class="tags">'+tags+'</div>' : ''}
      <div class="scores" id="sc-${m.id}"><div style="grid-column:span 4;color:var(--muted);font-size:11px">Loading scores…</div></div>
      <button class="del-btn" onclick="event.stopPropagation();del('${m.id}')">Delete</button>
    </div>
  </div>`;
}

async function toggle(id) {
  if (expandedId === id) { expandedId = null; reopen(id, false); return; }
  if (expandedId) reopen(expandedId, false);
  expandedId = id;
  reopen(id, true);
  try {
    const ins = await api('/memory/inspect/'+id);
    const b = ins.score_breakdown, act = (ins.gc_action||'keep').toLowerCase();
    const from = tier(ins.memory), to = (ins.predicted_tier||'').replace('MemoryType.','') || from;
    $('sc-'+id).innerHTML = `
      <div class="score-box"><span class="score-lbl">importance</span><span class="score-num">${(b.importance||0).toFixed(2)}</span></div>
      <div class="score-box"><span class="score-lbl">recency</span><span class="score-num">${(b.recency||0).toFixed(2)}</span></div>
      <div class="score-box"><span class="score-lbl">access freq</span><span class="score-num">${(b.access_frequency||0).toFixed(2)}</span></div>
      <div class="score-box"><span class="score-lbl">composite</span><span class="score-num" style="color:var(--accent)">${(b.composite||0).toFixed(2)}</span></div>
      <div class="gc-pred pred-${act}" style="grid-column:span 4">
        GC would <strong>${act}</strong>${to!==from?' (→ '+to+')':''} — ${ins.gc_reason||'no change'}
      </div>`;
  } catch(_) {}
}

function reopen(id, open) { const el = document.getElementById('m-'+id); if (el) el.classList.toggle('open', open); }

// ── search ────────────────────────────────────────────────────────────────────
function onSearch() {
  clearTimeout(searchTmr);
  const q = $('search').value.trim();
  if (!q) { render(all); return; }
  searchTmr = setTimeout(async () => {
    try {
      const res = await api('/memories/search?q='+encodeURIComponent(q)+'&limit=50'+(activeTier?'&memory_type='+activeTier:''));
      render(res.map(r => r.memory));
    } catch(_) {}
  }, 260);
}

function setTier(t) {
  activeTier = t; expandedId = null;
  document.querySelectorAll('.tier-btn').forEach(b => b.classList.remove('active'));
  $('tb-'+(t||'all')).classList.add('active');
  $('search').value.trim() ? onSearch() : loadMems();
}

function refresh() { loadStats(); loadMems(); }

// ── gc ────────────────────────────────────────────────────────────────────────
async function toggleGC() {
  gcOpen = !gcOpen;
  $('gc-panel').classList.toggle('open', gcOpen);
  if (gcOpen) await loadGCPreview();
}

async function loadGCPreview() {
  $('gc-inner').innerHTML = '<div class="gc-summary">Loading…</div>';
  try {
    const p = await api('/memory/gc/preview');
    const rows = [
      ...p.to_delete.map(e=>[e,'delete']), ...p.to_archive.map(e=>[e,'archive']),
      ...p.to_demote.map(e=>[e,'demote']),  ...p.to_promote.map(e=>[e,'promote']),
      ...p.to_keep.map(e=>[e,'keep']),
    ];
    $('gc-inner').innerHTML = `<div class="gc-summary">${esc(p.summary)}</div>`
      + rows.slice(0,50).map(([e,a]) => `<div class="gc-row"><span class="ab ab-${a}">${a}</span><span class="gc-text">${esc(e.content_preview||'')}</span><span class="gc-score-val">${(e.score||0).toFixed(2)}</span></div>`).join('');
  } catch(_) { $('gc-inner').innerHTML = '<div class="gc-summary" style="color:var(--danger)">Failed to load</div>'; }
}

async function runGC() {
  try {
    const s = await fetch('/gc',{method:'POST'}).then(r=>r.json());
    toast(`GC: +${s.promoted} promoted  −${s.deleted} deleted  ↓${s.archived} archived`, 'ok');
    refresh(); if (gcOpen) loadGCPreview();
  } catch(_) { toast('GC failed','err'); }
}

// ── delete ────────────────────────────────────────────────────────────────────
async function del(id) {
  try {
    await fetch('/memories/'+id,{method:'DELETE'});
    all = all.filter(m => m.id !== id); expandedId = null;
    render(all); loadStats(); toast('Deleted','ok');
  } catch(_) { toast('Delete failed','err'); }
}

// ── activity ──────────────────────────────────────────────────────────────────
async function loadActivity() {
  try {
    const log = await api('/activity?limit=50');

    // detect new injection since last poll
    const isNew = log.length && log[0].ts !== lastActivityTs;
    if (isNew) lastActivityTs = log[0].ts;

    activityLog = log;
    $('act-count-badge').textContent = log.length ? '('+log.length+')' : '';
    updateLiveIndicator(log);

    // only re-render if activity tab is visible
    if ($('panel-activity').classList.contains('active')) renderActivity(log);

    // flash live dot on new injection
    if (isNew) {
      $('live-dot').style.transform = 'scale(1.5)';
      setTimeout(() => $('live-dot').style.transform = '', 300);
    }
  } catch(_) {}
}

function renderActivity(log) {
  if (!log.length) {
    $('act-list').innerHTML = '<div class="empty">No hook activity yet — send a prompt in any Claude Code session to see it here</div>';
    return;
  }
  const now = Date.now();
  $('act-list').innerHTML = log.map((e, i) => {
    const secAgo = (now - new Date(e.ts)) / 1000;
    const fresh = secAgo < 60;
    const chips = (e.ids||[]).map(id =>
      `<span class="act-chip" onclick="jumpToMemory('${id}')" title="${id}">${id.slice(0,8)}</span>`
    ).join('');
    const cwd = e.cwd ? e.cwd.replace(/.*\//, '…/') : '';
    return `<div class="act-item${fresh?' fresh':''}">
      <div class="act-top">
        <span class="act-prompt">${esc(e.prompt||'')}</span>
        <span class="act-time">${age(e.ts)}</span>
      </div>
      <div class="act-meta">
        <span>${e.count} memories</span>
        <span>${e.tokens} tokens</span>
      </div>
      ${chips ? '<div class="act-chips">'+chips+'</div>' : ''}
      ${cwd ? '<div class="act-cwd">'+esc(cwd)+'</div>' : ''}
    </div>`;
  }).join('');
}

function jumpToMemory(id) {
  switchTab('memories');
  // wait for panel to render then scroll to and highlight
  setTimeout(() => {
    const el = document.getElementById('m-'+id);
    if (el) {
      el.scrollIntoView({behavior:'smooth', block:'center'});
      el.classList.add('highlight');
      setTimeout(() => el.classList.remove('highlight'), 2000);
      toggle(id);
    } else {
      toast('Memory not visible in current filter — switch to All', 'err');
    }
  }, 50);
}

// ── helpers ───────────────────────────────────────────────────────────────────
function $(id) { return document.getElementById(id); }
async function api(path) { const r = await fetch(path); if (!r.ok) throw r; return r.json(); }
function esc(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function fmt(n) { return n>=1000?(n/1000).toFixed(1)+'k':String(n); }
function age(iso) {
  if (!iso) return '';
  const d = (Date.now()-new Date(iso))/1000;
  if (d<5)   return 'just now';
  if (d<60)  return Math.round(d)+'s ago';
  if (d<3600) return Math.round(d/60)+'m ago';
  if (d<86400) return Math.round(d/3600)+'h ago';
  return Math.round(d/86400)+'d ago';
}
function toast(msg, type) {
  const el = $('toast'); el.textContent = msg;
  el.className = 'toast show '+(type||'ok');
  setTimeout(()=>el.classList.remove('show'), 3000);
}
</script>
</body>
</html>"""
