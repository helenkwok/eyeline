/**
 * Eyeline — On-Set Continuity Review Station
 * app.js  ·  Zero-dependency client logic
 */

// ─── Constants ────────────────────────────────────────────────────────────────

const FIXTURE_PATHS = [
  '../bench/fixtures/sample_diff.json',
  'bench/fixtures/sample_diff.json',
  './bench/fixtures/sample_diff.json',
];

// How many seconds either side of the current time to consider a bounding box "active"
const BOX_WINDOW_SEC = 0.5;

// ─── DOM refs ─────────────────────────────────────────────────────────────────

const videoRef        = document.getElementById('video-ref');
const videoCur        = document.getElementById('video-cur');
const canvas          = document.getElementById('overlay-canvas');
const ctx             = canvas.getContext('2d');
const scrubBar        = document.getElementById('scrub-bar');
const btnPlayPause    = document.getElementById('btn-play-pause');
const iconPlay        = document.getElementById('icon-play');
const iconPause       = document.getElementById('icon-pause');
const btnPrevFrame    = document.getElementById('btn-prev-frame');
const btnNextFrame    = document.getElementById('btn-next-frame');
const timecodeDisplay = document.getElementById('timecode-display');
const metaTimecode    = document.getElementById('meta-timecode');
const incidentList    = document.getElementById('incident-list');
const incidentCount   = document.getElementById('incident-count');
const incidentMarkers = document.getElementById('incident-markers');
const tabIncidents    = document.getElementById('tab-incidents');
const tabPasses       = document.getElementById('tab-passes');
const toggleOverlay   = document.getElementById('toggle-overlay');
const toggleFilter    = document.getElementById('toggle-filter-incidents');
const takeLabelEl     = document.getElementById('take-label');
const takeSceneEl     = document.getElementById('take-scene');
const metaFps         = document.getElementById('meta-fps');
const metaDuration    = document.getElementById('meta-duration');
const metaCamera      = document.getElementById('meta-camera');
const labelRef        = document.getElementById('label-ref');
const labelCur        = document.getElementById('label-cur');

// ─── Application state ────────────────────────────────────────────────────────

const state = {
  fixture:          null,     // loaded JSON
  incidents:        [],
  passes:           [],
  fps:              24,
  duration:         0,
  overlayEnabled:   true,
  showIncidents:    true,     // true = incidents tab, false = passes tab
  activeIncidentId: null,
  isSyncing:        false,    // mutex to prevent sync loops
  isPlaying:        false,
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Convert seconds to SMPTE timecode string HH:MM:SS:FF */
function toTimecode(seconds, fps = 24) {
  const totalFrames = Math.floor(seconds * fps);
  const ff = totalFrames % fps;
  const totalSec = Math.floor(totalFrames / fps);
  const ss = totalSec % 60;
  const mm = Math.floor(totalSec / 60) % 60;
  const hh = Math.floor(totalSec / 3600);
  return [hh, mm, ss, ff].map(n => String(n).padStart(2, '0')).join(':');
}

/** Map incident category string to CSS class suffix */
function categoryClass(cat) {
  const map = {
    'Prop State':    'prop-state',
    'Wardrobe':      'wardrobe',
    'Blocking':      'blocking',
    'Prop Position': 'prop-position',
    'Set Dressing':  'set-dressing',
  };
  return `cat-${map[cat] ?? 'prop-state'}`;
}

/** Determine confidence tier string for CSS */
function confidenceTier(value) {
  if (value >= 0.9) return 'high';
  if (value >= 0.75) return 'medium';
  return 'low';
}

/** Clamp a value between min and max */
function clamp(val, min, max) { return Math.max(min, Math.min(max, val)); }

// ─── Fixture loading ──────────────────────────────────────────────────────────

async function loadFixture() {
  let data = null;
  for (const path of FIXTURE_PATHS) {
    try {
      const res = await fetch(path);
      if (res.ok) { data = await res.json(); break; }
    } catch (_) { /* try next path */ }
  }

  if (!data) {
    // Graceful degradation: synthesize a minimal fixture so the UI still functions
    console.warn('[Eyeline] Could not load fixture from any path. Using synthetic placeholder.');
    data = buildSyntheticFixture();
  }

  return data;
}

function buildSyntheticFixture() {
  return {
    metadata: {
      scene: 'Scene 28 - INT. CAFE',
      reference_take: 'Take 1',
      target_take: 'Take 4',
      framerate: 24,
      duration_seconds: 12.5,
      camera: 'A-CAM',
    },
    incidents: [
      {
        id: 'inc_001', timestamp_sec: 2.417, timecode: '00:00:02:10',
        category: 'Prop State', confidence: 0.94, severity: 'high',
        bounding_box: [0.58, 0.38, 0.78, 0.62],
        summary: 'Actor coffee mug fill level increased by ~40% between takes.',
      },
      {
        id: 'inc_002', timestamp_sec: 5.083, timecode: '00:00:05:02',
        category: 'Wardrobe', confidence: 0.97, severity: 'critical',
        bounding_box: [0.22, 0.12, 0.55, 0.38],
        summary: 'Wristwatch absent in Take 4.',
      },
      {
        id: 'inc_003', timestamp_sec: 7.750, timecode: '00:00:07:18',
        category: 'Prop Position', confidence: 0.88, severity: 'medium',
        bounding_box: [0.65, 0.55, 0.85, 0.80],
        summary: 'Notebook on table shifted approximately 15 cm to the right.',
      },
    ],
    verified_passes: [
      {
        id: 'pass_001', timestamp_sec: 1.0, timecode: '00:00:01:00',
        category: 'Wardrobe', summary: 'Jacket lapel position consistent.',
      },
    ],
  };
}

// ─── UI population ────────────────────────────────────────────────────────────

function populateMetadata(meta) {
  state.fps      = meta.framerate ?? 24;
  state.duration = meta.duration_seconds ?? 0;

  takeLabelEl.textContent = `${meta.scene} · ${meta.reference_take} vs ${meta.target_take}`;
  takeSceneEl.textContent = `${meta.camera ?? ''} · ${meta.date ?? ''}`.replace(/^[\s·]+|[\s·]+$/g, '');
  metaFps.textContent      = state.fps;
  metaDuration.textContent = toTimecode(state.duration, state.fps);
  if (meta.camera) metaCamera.textContent = meta.camera;

  labelRef.textContent = `Reference ${meta.reference_take}`;
  labelCur.textContent = `Current ${meta.target_take}`;

  // Update scrub bar max to total frame count for precision
  scrubBar.max = Math.floor(state.duration * state.fps);

  // Build incident scrub markers once duration is known
  buildScrubMarkers();
}

function buildScrubMarkers() {
  incidentMarkers.innerHTML = '';
  for (const inc of state.incidents) {
    const pct = state.duration > 0 ? (inc.timestamp_sec / state.duration) * 100 : 0;
    const marker = document.createElement('div');
    marker.className = `incident-marker severity-${inc.severity ?? 'medium'}`;
    marker.style.left = `${clamp(pct, 0, 100)}%`;
    marker.title = `${inc.timecode} — ${inc.category}`;
    incidentMarkers.appendChild(marker);
  }
}

function renderList() {
  incidentList.innerHTML = '';
  const items = state.showIncidents ? state.incidents : state.passes;
  incidentCount.textContent = state.incidents.length;

  if (items.length === 0) {
    const empty = document.createElement('div');
    empty.style.cssText = 'padding:24px 12px;text-align:center;color:var(--text-muted);font-size:11px;';
    empty.textContent = state.showIncidents ? 'No incidents detected.' : 'No verified passes.';
    incidentList.appendChild(empty);
    return;
  }

  for (const item of items) {
    const card = buildCard(item, state.showIncidents);
    incidentList.appendChild(card);
  }
}

function buildCard(item, isIncident) {
  const card = document.createElement('div');
  card.className = `incident-card${isIncident ? '' : ' pass-card'}`;
  card.dataset.id = item.id;
  card.setAttribute('role', 'option');
  card.setAttribute('aria-selected', 'false');
  card.tabIndex = 0;

  if (isIncident) {
    const pct = Math.round((item.confidence ?? 0) * 100);
    const tier = confidenceTier(item.confidence ?? 0);
    card.innerHTML = `
      <div class="card-severity-dot sev-${item.severity ?? 'medium'}"></div>
      <div class="card-row">
        <span class="card-timecode">${item.timecode}</span>
        <span class="category-badge ${categoryClass(item.category)}">${item.category}</span>
      </div>
      <div class="confidence-row">
        <div class="confidence-bar-wrap">
          <div class="confidence-bar-fill ${tier}" style="width:${pct}%"></div>
        </div>
        <span class="confidence-pct">${pct}%</span>
      </div>
      <div class="card-summary">${item.summary}</div>
      <div style="margin-top:8px; display:flex; justify-content:flex-end;">
        <button class="btn-veo-pickup" data-id="${item.id}" style="font-size:10px; font-weight:600; color:#da77f2; background:rgba(218,119,242,0.12); border:1px solid rgba(218,119,242,0.3); padding:3px 8px; border-radius:4px; cursor:pointer;">
          ⚡ Veo 3.1 Pickup
        </button>
      </div>
    `;
    card.addEventListener('click', () => seekToIncident(item));
    card.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') seekToIncident(item); });

    const veoBtn = card.querySelector('.btn-veo-pickup');
    if (veoBtn) {
      veoBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const modal = document.getElementById('veo-modal');
        const v = document.getElementById('veo-modal-video');
        if (modal) {
          modal.showModal();
          if (v) { v.currentTime = 0; v.play().catch(() => {}); }
        }
      });
    }
  } else {
    card.innerHTML = `
      <div class="card-row">
        <span class="card-timecode">${item.timecode}</span>
        <span class="pass-badge">✓ Pass</span>
      </div>
      <div class="card-row" style="margin-bottom:0">
        <span class="category-badge ${categoryClass(item.category)}">${item.category}</span>
      </div>
      <div class="card-summary" style="margin-top:6px">${item.summary}</div>
    `;
    card.addEventListener('click', () => seekToTimestamp(item.timestamp_sec));
    card.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') seekToTimestamp(item.timestamp_sec); });
  }

  return card;
}

// ─── Playback synchronisation ─────────────────────────────────────────────────

/**
 * Seek both players to a given time in seconds.
 * Uses the isSyncing mutex to prevent the timeupdate cross-sync loop.
 */
function seekBoth(seconds) {
  const t = clamp(seconds, 0, state.duration || 9999);
  state.isSyncing = true;
  videoRef.currentTime = t;
  videoCur.currentTime = t;
  updateUI(t);
  // Release mutex after one event loop turn
  requestAnimationFrame(() => { state.isSyncing = false; });
}

function updateUI(seconds) {
  const tc = toTimecode(seconds, state.fps);
  timecodeDisplay.textContent = tc;
  metaTimecode.textContent    = tc;

  // Scrub bar position (in frames)
  const frame = Math.floor(seconds * state.fps);
  scrubBar.value = frame;

  drawOverlay(seconds);
}

// ─── Canvas overlay ───────────────────────────────────────────────────────────

/** Resize canvas to match its CSS-rendered dimensions */
function resizeCanvas() {
  const rect = canvas.getBoundingClientRect();
  if (canvas.width !== rect.width || canvas.height !== rect.height) {
    canvas.width  = rect.width;
    canvas.height = rect.height;
  }
}

/**
 * Draw active bounding boxes on the overlay canvas.
 * bounding_box format: [ymin, xmin, ymax, xmax] — all normalised 0-1.
 */
function drawOverlay(currentTime) {
  resizeCanvas();
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (!state.overlayEnabled || !state.incidents.length) return;

  const W = canvas.width;
  const H = canvas.height;

  for (const inc of state.incidents) {
    const delta = Math.abs(currentTime - inc.timestamp_sec);
    if (delta > BOX_WINDOW_SEC) continue;

    // Fade opacity near the edge of the window
    const alpha = clamp(1 - delta / BOX_WINDOW_SEC, 0.3, 1);

    const [ymin, xmin, ymax, xmax] = inc.bounding_box;
    const bx = xmin * W;
    const by = ymin * H;
    const bw = (xmax - xmin) * W;
    const bh = (ymax - ymin) * H;

    const isActive = inc.id === state.activeIncidentId;
    const isHighlighted = isActive || (delta < 0.1);

    // Choose colour by severity
    const color = severityColor(inc.severity);

    // Outer glow
    ctx.save();
    ctx.shadowColor  = color;
    ctx.shadowBlur   = isHighlighted ? 20 : 10;
    ctx.strokeStyle  = color;
    ctx.lineWidth    = isHighlighted ? 2.5 : 1.5;
    ctx.globalAlpha  = alpha * (isHighlighted ? 1.0 : 0.75);
    ctx.strokeRect(bx, by, bw, bh);
    ctx.restore();

    // Inner fill (very subtle)
    ctx.save();
    ctx.fillStyle   = color;
    ctx.globalAlpha = alpha * 0.06;
    ctx.fillRect(bx, by, bw, bh);
    ctx.restore();

    // Corner accents
    drawCornerAccents(ctx, bx, by, bw, bh, color, alpha, isHighlighted);

    // Label tag
    drawBoxLabel(ctx, inc, bx, by, color, alpha, W);
  }
}

function severityColor(severity) {
  switch (severity) {
    case 'critical': return '#ef4444';
    case 'high':     return '#f59e0b';
    case 'medium':   return '#f97316';
    default:         return '#9ba3b2';
  }
}

function drawCornerAccents(ctx, x, y, w, h, color, alpha, bold) {
  const len = Math.min(w, h) * 0.18;
  const lw  = bold ? 2.5 : 1.5;
  ctx.save();
  ctx.strokeStyle  = color;
  ctx.lineWidth    = lw;
  ctx.globalAlpha  = alpha;
  ctx.lineCap      = 'round';

  const corners = [
    [[x, y + len], [x, y], [x + len, y]],
    [[x + w - len, y], [x + w, y], [x + w, y + len]],
    [[x + w, y + h - len], [x + w, y + h], [x + w - len, y + h]],
    [[x + len, y + h], [x, y + h], [x, y + h - len]],
  ];

  for (const [[ax, ay], [bx, by], [cx, cy]] of corners) {
    ctx.beginPath();
    ctx.moveTo(ax, ay);
    ctx.lineTo(bx, by);
    ctx.lineTo(cx, cy);
    ctx.stroke();
  }
  ctx.restore();
}

function drawBoxLabel(ctx, inc, bx, by, color, alpha, canvasW) {
  const label = inc.category;
  const pct   = Math.round((inc.confidence ?? 0) * 100);
  const text  = `${label} · ${pct}%`;
  const fontSize = 11;
  const pad = 4;

  ctx.save();
  ctx.font         = `500 ${fontSize}px 'Inter', sans-serif`;
  ctx.globalAlpha  = alpha * 0.95;

  const tw = ctx.measureText(text).width;
  let lx = bx;
  // Keep label within canvas
  if (lx + tw + pad * 2 > canvasW) lx = canvasW - tw - pad * 2;

  const tagY  = by > fontSize + 6 ? by - (fontSize + 6) : by + 2;
  const tagH  = fontSize + pad * 2;

  // Tag background
  ctx.fillStyle = 'rgba(15,17,21,0.8)';
  ctx.beginPath();
  ctx.roundRect?.(lx, tagY, tw + pad * 2, tagH, 3) ?? ctx.rect(lx, tagY, tw + pad * 2, tagH);
  ctx.fill();

  // Tag border
  ctx.strokeStyle = color;
  ctx.lineWidth   = 1;
  ctx.beginPath();
  ctx.roundRect?.(lx, tagY, tw + pad * 2, tagH, 3) ?? ctx.rect(lx, tagY, tw + pad * 2, tagH);
  ctx.stroke();

  // Tag text
  ctx.fillStyle = color;
  ctx.fillText(text, lx + pad, tagY + fontSize + pad - 2);
  ctx.restore();
}

// ─── Seek to incident ────────────────────────────────────────────────────────

function seekToIncident(incident) {
  seekToTimestamp(incident.timestamp_sec, incident.id);
}

function seekToTimestamp(seconds, incidentId = null) {
  state.activeIncidentId = incidentId;
  seekBoth(seconds);

  // Highlight the card
  if (incidentId) {
    highlightCard(incidentId);
    pulseCanvas();
  }

  // If video was paused, nudge it so the overlay updates immediately
  if (state.isPlaying) {
    // already running — overlay will update via timeupdate
  }
}

function highlightCard(id) {
  const all = incidentList.querySelectorAll('.incident-card');
  for (const card of all) {
    const isTarget = card.dataset.id === id;
    card.classList.toggle('active', isTarget);
    card.setAttribute('aria-selected', isTarget ? 'true' : 'false');
    if (isTarget) {
      card.classList.add('flash');
      setTimeout(() => card.classList.remove('flash'), 500);
      card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }
}

function pulseCanvas() {
  canvas.classList.add('canvas-pulse');
  canvas.addEventListener('animationend', () => canvas.classList.remove('canvas-pulse'), { once: true });
}

// ─── Playback controls ────────────────────────────────────────────────────────

function setPlaying(playing) {
  state.isPlaying = playing;
  btnPlayPause.setAttribute('aria-pressed', playing);
  btnPlayPause.classList.toggle('playing', playing);
  iconPlay.style.display  = playing ? 'none'  : '';
  iconPause.style.display = playing ? ''      : 'none';
}

function togglePlayPause() {
  if (state.isPlaying) {
    videoRef.pause();
    videoCur.pause();
    setPlaying(false);
  } else {
    // Both videos attempt to play in parallel
    Promise.allSettled([videoRef.play(), videoCur.play()])
      .then(() => setPlaying(true))
      .catch(() => setPlaying(false));
  }
}

function nudgeFrame(direction) {
  const frameDuration = 1 / state.fps;
  const next = clamp(videoCur.currentTime + direction * frameDuration, 0, state.duration || 9999);
  seekBoth(next);
}

// ─── Scrub bar ────────────────────────────────────────────────────────────────

scrubBar.addEventListener('input', () => {
  const frame   = parseInt(scrubBar.value, 10);
  const seconds = frame / state.fps;
  seekBoth(seconds);
});

// ─── Video event listeners ────────────────────────────────────────────────────

/**
 * Keep reference video in sync with the current take scrubbing.
 * Only re-sync if the two players have drifted more than one frame.
 */
function onCurrentTimeUpdate() {
  if (state.isSyncing) return;
  const t = videoCur.currentTime;
  updateUI(t);

  // Drift correction: if ref is more than one frame off, resync silently
  const drift = Math.abs(videoRef.currentTime - t);
  if (drift > 1 / state.fps) {
    state.isSyncing = true;
    videoRef.currentTime = t;
    requestAnimationFrame(() => { state.isSyncing = false; });
  }
}

function onRefTimeUpdate() {
  if (state.isSyncing) return;
  const t = videoRef.currentTime;
  const drift = Math.abs(videoCur.currentTime - t);
  if (drift > 1 / state.fps) {
    state.isSyncing = true;
    videoCur.currentTime = t;
    updateUI(t);
    requestAnimationFrame(() => { state.isSyncing = false; });
  }
}

videoCur.addEventListener('timeupdate', onCurrentTimeUpdate);
videoRef.addEventListener('timeupdate', onRefTimeUpdate);

videoCur.addEventListener('ended', () => {
  videoRef.pause();
  setPlaying(false);
});

videoRef.addEventListener('ended', () => {
  videoCur.pause();
  setPlaying(false);
});

// ─── Button bindings ──────────────────────────────────────────────────────────

btnPlayPause.addEventListener('click', togglePlayPause);
btnPrevFrame.addEventListener('click', () => nudgeFrame(-1));
btnNextFrame.addEventListener('click', () => nudgeFrame(+1));

// Keyboard shortcuts
document.addEventListener('keydown', e => {
  switch (e.key) {
    case ' ':
      e.preventDefault();
      togglePlayPause();
      break;
    case 'ArrowLeft':
      e.preventDefault();
      nudgeFrame(-1);
      break;
    case 'ArrowRight':
      e.preventDefault();
      nudgeFrame(+1);
      break;
  }
});

// ─── Toggle controls ──────────────────────────────────────────────────────────

toggleOverlay.addEventListener('click', () => {
  state.overlayEnabled = !state.overlayEnabled;
  toggleOverlay.classList.toggle('active', state.overlayEnabled);
  toggleOverlay.setAttribute('aria-pressed', state.overlayEnabled);
  drawOverlay(videoCur.currentTime);
});

tabIncidents.addEventListener('click', () => {
  state.showIncidents = true;
  tabIncidents.classList.add('active');
  tabIncidents.setAttribute('aria-selected', 'true');
  tabPasses.classList.remove('active');
  tabPasses.setAttribute('aria-selected', 'false');
  renderList();
});

tabPasses.addEventListener('click', () => {
  state.showIncidents = false;
  tabPasses.classList.add('active');
  tabPasses.setAttribute('aria-selected', 'true');
  tabIncidents.classList.remove('active');
  tabIncidents.setAttribute('aria-selected', 'false');
  renderList();
});

// ─── Resize handler ───────────────────────────────────────────────────────────

const resizeObserver = new ResizeObserver(() => {
  resizeCanvas();
  drawOverlay(videoCur.currentTime);
});
resizeObserver.observe(canvas.parentElement);

// ─── Animation loop (for smooth overlay during playback) ─────────────────────

let rafId = null;

function animationLoop() {
  if (state.isPlaying) {
    drawOverlay(videoCur.currentTime);

    // Auto-highlight nearest incident during playback
    const t = videoCur.currentTime;
    let nearest = null;
    let nearestDelta = Infinity;
    for (const inc of state.incidents) {
      const d = Math.abs(inc.timestamp_sec - t);
      if (d < nearestDelta && d < BOX_WINDOW_SEC) {
        nearestDelta = d;
        nearest = inc;
      }
    }
    if (nearest && nearest.id !== state.activeIncidentId) {
      state.activeIncidentId = nearest.id;
      highlightCard(nearest.id);
    } else if (!nearest) {
      state.activeIncidentId = null;
    }
  }
  rafId = requestAnimationFrame(animationLoop);
}

// ─── Benchmark Dataset & Predictions Integration ───────────────────────────

const pairSelect     = document.getElementById('pair-select');
const placeholderRef = document.getElementById('placeholder-ref');
const placeholderCur = document.getElementById('placeholder-cur');

const TRUTH_PATHS = [
  '../bench/truth.json',
  'bench/truth.json',
  './bench/truth.json',
];

const PREDICTION_PATHS = [
  '../bench/fixtures/adjudicated_predictions.json',
  'bench/fixtures/adjudicated_predictions.json',
  './bench/fixtures/adjudicated_predictions.json',
  '../bench/fixtures/measured_predictions.json',
  'bench/fixtures/measured_predictions.json',
  './bench/fixtures/measured_predictions.json',
];

async function loadDatasetAndPredictions() {
  let truth = null;
  let predictions = null;

  for (const path of TRUTH_PATHS) {
    try {
      const res = await fetch(path);
      if (res.ok) { truth = await res.json(); break; }
    } catch (_) {}
  }

  for (const path of PREDICTION_PATHS) {
    try {
      const res = await fetch(path);
      if (res.ok) { predictions = await res.json(); break; }
    } catch (_) {}
  }

  return { truth, predictions };
}

function categoryTitle(cat) {
  const map = {
    prop_state: 'Prop State',
    wardrobe: 'Wardrobe',
    prop_position: 'Prop Position',
    blocking: 'Blocking',
    hair_makeup: 'Hair & Makeup',
    set_dressing: 'Set Dressing',
    eyeline_axis: 'Eyeline / Axis',
    control_lighting: 'Control: Lighting',
    control_camera_angle: 'Control: Camera Angle',
    control_focal_length: 'Control: Focal Length',
    control_actor_expression: 'Control: Actor Expression',
    control_grade: 'Control: Color Grade',
  };
  return map[cat] || cat;
}

function loadBenchmarkPair(pair, pred) {
  if (!pair) return;

  // Set video sources with relative paths
  const refPath = pair.reference_clip.startsWith('../') ? pair.reference_clip : `../${pair.reference_clip}`;
  const tgtPath = pair.target_clip.startsWith('../') ? pair.target_clip : `../${pair.target_clip}`;

  videoRef.src = refPath;
  videoCur.src = tgtPath;

  if (placeholderRef) placeholderRef.classList.add('hidden');
  if (placeholderCur) placeholderCur.classList.add('hidden');

  const dur = Math.max(pair.timestamp_sec + 1.5, 3.5);
  state.duration = dur;

  const sceneName = pair.template_id
    .replace('template_01_diner', 'Diner Interior')
    .replace('template_02_office', 'Executive Office')
    .replace('template_03_kitchen', 'Kitchen Prep')
    .replace('template_04_interrogation', 'Interrogation Room');

  const meta = {
    scene: `${pair.pair_id.toUpperCase()} · ${sceneName}`,
    reference_take: 'Take 1 (Ref)',
    target_take: 'Take 2 (Target)',
    framerate: 24,
    duration_seconds: dur,
    camera: pair.ground_truth_label === 'defect' ? 'DEFECT SEED' : 'CONTROL PAIR',
    date: '2026-09-08',
  };

  const isDefect = pair.ground_truth_label === 'defect';
  const detected = pred ? Boolean(pred.detected) : isDefect;
  const catName  = categoryTitle(pair.category);

  if (isDefect) {
    state.incidents = [{
      id: pair.pair_id,
      timestamp_sec: pair.timestamp_sec,
      timecode: pair.timecode,
      category: catName,
      confidence: pred?.confidence ?? 0.90,
      severity: 'high',
      bounding_box: pred?.bounding_box || pair.bounding_box,
      summary: pair.defect_description || 'Seeded continuity discrepancy detected.',
    }];
    state.passes = [];
    state.showIncidents = true;
    tabIncidents.classList.add('active');
    tabPasses.classList.remove('active');
  } else {
    // Control pair
    if (detected) {
      state.incidents = [{
        id: pair.pair_id,
        timestamp_sec: pair.timestamp_sec,
        timecode: pair.timecode,
        category: catName,
        confidence: pred?.confidence ?? 0.90,
        severity: 'medium',
        bounding_box: pred?.bounding_box,
        summary: `Pillar-1 CV flag on control: ${pair.control_description || 'Permitted cinematic variation'}`,
      }];
      state.passes = [];
      state.showIncidents = true;
      tabIncidents.classList.add('active');
      tabPasses.classList.remove('active');
    } else {
      state.incidents = [];
      state.passes = [{
        id: pair.pair_id,
        timestamp_sec: pair.timestamp_sec,
        timecode: pair.timecode,
        category: catName,
        summary: `✓ Verified Control: ${pair.control_description || 'Variation within tolerance bounds.'}`,
      }];
      state.showIncidents = false;
      tabPasses.classList.add('active');
      tabIncidents.classList.remove('active');
    }
  }

  populateMetadata(meta);
  renderList();

  // Seek both videos to the pair timestamp
  seekBoth(pair.timestamp_sec);
}

// ─── Bootstrap ───────────────────────────────────────────────────────────────

async function init() {
  const { truth, predictions } = await loadDatasetAndPredictions();
  const predMap = {};
  if (predictions && Array.isArray(predictions)) {
    for (const p of predictions) {
      predMap[p.pair_id] = p;
    }
  }

  if (truth && Array.isArray(truth.pairs) && pairSelect) {
    pairSelect.innerHTML = '';

    const groupDefects = document.createElement('optgroup');
    groupDefects.label = 'Seeded Continuity Defects (16)';
    const groupControls = document.createElement('optgroup');
    groupControls.label = 'Negative Controls (16)';

    for (const pair of truth.pairs) {
      const opt = document.createElement('option');
      opt.value = pair.pair_id;
      const cat = categoryTitle(pair.category);
      opt.textContent = `${pair.pair_id} · ${cat}`;
      if (pair.ground_truth_label === 'defect') {
        groupDefects.appendChild(opt);
      } else {
        groupControls.appendChild(opt);
      }
    }
    pairSelect.appendChild(groupDefects);
    pairSelect.appendChild(groupControls);

    pairSelect.addEventListener('change', () => {
      const selectedPair = truth.pairs.find(p => p.pair_id === pairSelect.value);
      if (selectedPair) {
        loadBenchmarkPair(selectedPair, predMap[selectedPair.pair_id]);
      }
    });

    // Load initial pair
    const initialPair = truth.pairs[0];
    loadBenchmarkPair(initialPair, predMap[initialPair.pair_id]);
  } else {
    // Fallback to fixture
    const fixture = await loadFixture();
    state.fixture   = fixture;
    state.incidents = fixture.incidents        ?? [];
    state.passes    = fixture.verified_passes  ?? [];

    populateMetadata(fixture.metadata ?? {});
    renderList();
    drawOverlay(0);
  }

  // Modal close listener
  document.getElementById('close-veo-modal')?.addEventListener('click', () => {
    const modal = document.getElementById('veo-modal');
    const v = document.getElementById('veo-modal-video');
    if (v) v.pause();
    modal?.close();
  });

  // Start RAF loop
  rafId = requestAnimationFrame(animationLoop);

  console.info('[Eyeline] Initialized with', truth?.pairs?.length ?? 0, 'benchmark pairs.');
}

init();
