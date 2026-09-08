/**
 * Eyeline Judge Index — Interactive 30-Second Path Runner
 * Provides instant execution of bundled seed presets without upload or credentials.
 */

// Presets data
const PRESETS = {
  defect: {
    id: "preset_defect_prop",
    name: "Diner Table: Mug Level",
    category: "Prop State: Glassware Liquid Level Jump",
    badgeClass: "cat-prop-state",
    pillClass: "prov-adjudicated",
    pillText: "ADJUDICATED",
    confidence: "94% Confidence",
    bbox: [0.68, 0.44, 0.88, 0.54],
    desc: "Coffee mug liquid height increased by ~55% volume between Take 1 (reference, level 25%) and Take 4 (current, level 80%). Physical consumption discontinuity detected across coverage.",
    latency: "82ms (CV) + 620ms (ADK)",
    remediation: "Immediate Retake",
    refLabel: "Reference Take 1 (Liquid 25%)",
    curLabel: "Current Take 4 (Liquid 80%)",
    draw: (ctxRef, ctxCur, w, h) => {
      drawDinerScene(ctxRef, w, h, 0.25);
      drawDinerScene(ctxCur, w, h, 0.80);
      drawBoundingBox(ctxCur, [0.68, 0.44, 0.88, 0.54], "#f59e0b", "PROP STATE: MUG LEVEL (+55%)", w, h);
    }
  },
  control: {
    id: "preset_control_lighting",
    name: "Office Brief: Mood Dim",
    category: "Controlled Variation: Key Light Dimmed (Mood Shift)",
    badgeClass: "pass-badge",
    pillClass: "prov-verified",
    pillText: "VERIFIED PASS",
    confidence: "99% Invariance",
    bbox: null,
    desc: "Uniform 1.5-stop illumination drop across setup. Classical CV isolated global histogram shift; Google ADK Agent verified intentional dramatic mood dim. Exactly 0 false alarms reported.",
    latency: "75ms (CV) + 510ms (ADK)",
    remediation: "Verified Pass (No Action Needed)",
    refLabel: "Reference Take 1 (Key Light 100%)",
    curLabel: "Current Take 2 (Key Light 35% - Mood Dim)",
    draw: (ctxRef, ctxCur, w, h) => {
      drawOfficeScene(ctxRef, w, h, 1.0);
      drawOfficeScene(ctxCur, w, h, 0.4);
      drawControlPassBanner(ctxCur, w, h);
    }
  },
  resample: {
    id: "preset_resample_wardrobe",
    name: "Kitchen: Lapel Flip",
    category: "Wardrobe: Chef Jacket Lapel Fold Discrepancy",
    badgeClass: "cat-wardrobe",
    pillClass: "prov-adjudicated",
    pillText: "RESAMPLED + ADJUDICATED",
    confidence: "91% Confidence (Calibrated)",
    bbox: [0.35, 0.46, 0.52, 0.58],
    desc: "Initial delta confidence was borderline (54%) due to actor head turn motion. Agent automatically triggered temporal resample (±12 frames @ 60fps) and 2x sub-patch zoom, confirming persistent lapel flip.",
    latency: "110ms (Resample) + 710ms (ADK)",
    remediation: "Veo Generative Pickup (Stove Insert)",
    refLabel: "Reference Take 1 (Lapel Flat)",
    curLabel: "Current Take 3 (Lapel Flipped + Resampled)",
    draw: (ctxRef, ctxCur, w, h) => {
      drawKitchenScene(ctxRef, w, h, false);
      drawKitchenScene(ctxCur, w, h, true);
      drawBoundingBox(ctxCur, [0.35, 0.46, 0.52, 0.58], "#ef4444", "WARDROBE: LAPEL INVERTED [RESAMPLED]", w, h);
    }
  },
  veo: {
    id: "preset_veo_pickup",
    name: "Set Struck: B-Roll Pickup",
    category: "Pillar 3 Generative Cutaway: Macro B-Roll Insert",
    badgeClass: "prov-generated",
    pillClass: "prov-generated",
    pillText: "GENERATED: VEO 3.1",
    confidence: "100% Watermarked",
    bbox: null,
    desc: "Production set was struck after wrap; discovered unscripted prop discrepancy on the timeline. Eyeline invoked Google Cloud Veo 3.1 to synthesize a 4.0-second macro B-roll insert shot, stamped with the SYNTHETIC CONTINUITY INSERT disclosure watermark, allowing editorial to bridge the cut without an expensive reshoot.",
    latency: "2.10s (Veo 3.1 Synthesis)",
    remediation: "Editorial Cutaway Bridge (Approved)",
    refLabel: "Defect Take (Diner - Set Struck)",
    curLabel: "Veo 3.1 Generative Pickup (4.0s Video)",
    isVideo: true,
    draw: (ctxRef, ctxCur, w, h) => {
      drawDinerScene(ctxRef, w, h, 0.80);
      drawBoundingBox(ctxRef, [0.68, 0.44, 0.88, 0.54], "#ef4444", "DEFECT UNRESOLVED (SET STRUCK)", w, h);
    }
  }
};

// Canvas drawing helpers
function drawDinerScene(ctx, w, h, liquidLevel) {
  // Background
  ctx.fillStyle = "#1e2129";
  ctx.fillRect(0, 0, w, h);

  // Table
  ctx.fillStyle = "#4a3b32";
  ctx.fillRect(0, h * 0.65, w, h * 0.35);

  // Character silhouette Left
  ctx.fillStyle = "#2d323f";
  ctx.beginPath();
  ctx.arc(w * 0.25, h * 0.45, 45, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillRect(w * 0.12, h * 0.52, 130, 90);

  // Character silhouette Right
  ctx.fillStyle = "#262b37";
  ctx.beginPath();
  ctx.arc(w * 0.75, h * 0.45, 45, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillRect(w * 0.62, h * 0.52, 130, 90);

  // Coffee Mug on Table
  const mugX = w * 0.49;
  const mugY = h * 0.72;
  const mugW = 32;
  const mugH = 44;

  // Mug Body
  ctx.fillStyle = "#e5e7eb";
  ctx.fillRect(mugX - mugW/2, mugY - mugH/2, mugW, mugH);
  ctx.strokeStyle = "#9ca3af";
  ctx.lineWidth = 2;
  ctx.strokeRect(mugX - mugW/2, mugY - mugH/2, mugW, mugH);

  // Coffee Liquid inside
  const liquidH = (mugH - 6) * liquidLevel;
  ctx.fillStyle = "#451a03";
  ctx.fillRect(mugX - mugW/2 + 2, mugY + mugH/2 - 2 - liquidH, mugW - 4, liquidH);
}

function drawOfficeScene(ctx, w, h, brightness) {
  // Ambient fill modified by brightness
  const val = Math.floor(35 * brightness);
  ctx.fillStyle = `rgb(${val}, ${val + 5}, ${val + 10})`;
  ctx.fillRect(0, 0, w, h);

  // Conference window
  ctx.fillStyle = `rgba(100, 150, 220, ${0.15 * brightness})`;
  ctx.fillRect(w * 0.1, h * 0.1, w * 0.8, h * 0.45);
  ctx.strokeStyle = `rgba(150, 180, 240, ${0.3 * brightness})`;
  ctx.strokeRect(w * 0.1, h * 0.1, w * 0.8, h * 0.45);

  // Conference desk
  ctx.fillStyle = `rgb(${Math.floor(50 * brightness)}, ${Math.floor(55 * brightness)}, ${Math.floor(65 * brightness)})`;
  ctx.fillRect(w * 0.15, h * 0.62, w * 0.7, h * 0.38);

  // Laptop
  ctx.fillStyle = `rgb(${Math.floor(180 * brightness)}, ${Math.floor(190 * brightness)}, ${Math.floor(200 * brightness)})`;
  ctx.fillRect(w * 0.45, h * 0.65, 50, 30);
}

function drawKitchenScene(ctx, w, h, lapelFlipped) {
  ctx.fillStyle = "#181e24";
  ctx.fillRect(0, 0, w, h);

  // Counter
  ctx.fillStyle = "#2c3440";
  ctx.fillRect(0, h * 0.7, w, h * 0.3);

  // Chef body
  ctx.fillStyle = "#f3f4f6";
  ctx.fillRect(w * 0.38, h * 0.35, w * 0.24, h * 0.45);

  // Head
  ctx.fillStyle = "#d1d5db";
  ctx.beginPath();
  ctx.arc(w * 0.5, h * 0.25, 36, 0, Math.PI * 2);
  ctx.fill();

  // Lapel
  ctx.fillStyle = "#374151";
  if (!lapelFlipped) {
    // Normal flat collar
    ctx.beginPath();
    ctx.moveTo(w * 0.46, h * 0.36);
    ctx.lineTo(w * 0.49, h * 0.48);
    ctx.lineTo(w * 0.44, h * 0.48);
    ctx.fill();
  } else {
    // Flipped/inverted collar
    ctx.fillStyle = "#ef4444";
    ctx.beginPath();
    ctx.moveTo(w * 0.46, h * 0.36);
    ctx.lineTo(w * 0.52, h * 0.45);
    ctx.lineTo(w * 0.45, h * 0.50);
    ctx.fill();
  }
}

function drawBoundingBox(ctx, box, color, label, w, h) {
  const [ymin, xmin, ymax, xmax] = box;
  const x = xmin * w;
  const y = ymin * h;
  const bw = (xmax - xmin) * w;
  const bh = (ymax - ymin) * h;

  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.strokeRect(x, y, bw, bh);

  // Corner accents
  const len = 6;
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(x, y + len); ctx.lineTo(x, y); ctx.lineTo(x + len, y);
  ctx.moveTo(x + bw - len, y); ctx.lineTo(x + bw, y); ctx.lineTo(x + bw, y + len);
  ctx.moveTo(x, y + bh - len); ctx.lineTo(x, y + bh); ctx.lineTo(x + len, y + bh);
  ctx.moveTo(x + bw - len, y + bh); ctx.lineTo(x + bw, y + bh); ctx.lineTo(x + bw, y + bh - len);
  ctx.stroke();

  // Label tag
  ctx.fillStyle = "rgba(0,0,0,0.8)";
  ctx.fillRect(x, y - 18, bw + 10, 16);
  ctx.fillStyle = color;
  ctx.font = "bold 9px 'JetBrains Mono', monospace";
  ctx.fillText(label, x + 4, y - 6);
}

function drawControlPassBanner(ctx, w, h) {
  ctx.fillStyle = "rgba(16, 185, 129, 0.15)";
  ctx.fillRect(w * 0.1, h * 0.4, w * 0.8, 50);
  ctx.strokeStyle = "rgba(16, 185, 129, 0.6)";
  ctx.lineWidth = 1.5;
  ctx.strokeRect(w * 0.1, h * 0.4, w * 0.8, 50);

  ctx.fillStyle = "#10b981";
  ctx.font = "bold 12px 'JetBrains Mono', monospace";
  ctx.textAlign = "center";
  ctx.fillText("✓ CONTROL INVARIANCE: 0 DEFECTS REPORTED", w * 0.5, h * 0.4 + 28);
  ctx.textAlign = "left";
}

// UI State Manager
function loadPreset(key) {
  const p = PRESETS[key];
  if (!p) return;

  // Toggle active button
  document.querySelectorAll(".preset-card").forEach(c => c.classList.remove("active"));
  const btn = document.getElementById(`btn-preset-${key}`);
  if (btn) btn.classList.add("active");

  // Update labels
  document.getElementById("tag-ref").textContent = p.refLabel;
  document.getElementById("tag-cur").textContent = p.curLabel;
  document.getElementById("verdict-title").textContent = p.category;
  
  const pill = document.getElementById("verdict-pill");
  pill.className = `prov-pill ${p.pillClass}`;
  pill.textContent = p.pillText;

  document.getElementById("verdict-conf").textContent = p.confidence;
  document.getElementById("verdict-desc").textContent = p.desc;
  document.getElementById("verdict-bbox").textContent = p.bbox ? `[${p.bbox.join(", ")}]` : "None (Controlled Invariance)";
  document.getElementById("verdict-lat").textContent = p.latency;
  document.getElementById("verdict-remedy").textContent = p.remediation;

  // Handle canvas vs video playback
  const cRef = document.getElementById("canvas-ref");
  const cCur = document.getElementById("canvas-cur");
  const vVeo = document.getElementById("video-veo-pickup");

  if (p.isVideo) {
    if (cCur) cCur.style.display = "none";
    if (vVeo) {
      vVeo.style.display = "block";
      vVeo.currentTime = 0;
      vVeo.play().catch(() => {});
    }
  } else {
    if (vVeo) {
      vVeo.pause();
      vVeo.style.display = "none";
    }
    if (cCur) cCur.style.display = "block";
  }

  // Redraw canvases
  if (cRef && cCur) {
    const ctxRef = cRef.getContext("2d");
    const ctxCur = cCur.getContext("2d");
    p.draw(ctxRef, ctxCur, cRef.width, cRef.height);
  }
}

// Event Listeners
document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("btn-preset-defect")?.addEventListener("click", () => loadPreset("defect"));
  document.getElementById("btn-preset-control")?.addEventListener("click", () => loadPreset("control"));
  document.getElementById("btn-preset-resample")?.addEventListener("click", () => loadPreset("resample"));
  document.getElementById("btn-preset-veo")?.addEventListener("click", () => loadPreset("veo"));

  // Default to defect
  loadPreset("defect");
});
