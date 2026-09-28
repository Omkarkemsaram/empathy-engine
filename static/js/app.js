/* ─── Empathy Engine Frontend ─── */

const EMOTION_COLORS = {
  joyful: '#FFD700',
  positive: '#22c55e',
  inquisitive: '#38bdf8',
  surprised: '#f472b6',
  concerned: '#fb923c',
  frustrated: '#ef4444',
  sad: '#6366f1',
  urgent: '#dc2626',
  professional: '#94a3b8',
  neutral: '#6b7280'
};

const PARAM_LABELS = {
  rate: { label: 'Speech Rate', unit: 'x', baseline: 1.0, min: 0.6, max: 1.5 },
  pitch: { label: 'Pitch', unit: 'x', baseline: 1.0, min: 0.7, max: 1.3 },
  volume: { label: 'Volume', unit: 'x', baseline: 1.0, min: 0.6, max: 1.3 },
  pause_factor: { label: 'Pause Factor', unit: 'x', baseline: 1.0, min: 0.5, max: 1.8 },
};

let selectedStyle = 'auto';
let lastResult = null;

// ─── DOM Ready ───────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initPills();
  initExampleChips();
  initButtons();
  initCharCount();
  loadHistory();
});

// ─── Style Pills ─────────────────────────────────────────────────────────────
function initPills() {
  document.querySelectorAll('.pill').forEach(pill => {
    pill.addEventListener('click', () => {
      document.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      selectedStyle = pill.dataset.style;
    });
  });
}

// ─── Example Chips ───────────────────────────────────────────────────────────
function initExampleChips() {
  document.querySelectorAll('.example-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const textInput = document.getElementById('textInput');
      textInput.value = chip.dataset.text;
      updateCharCount();
      textInput.focus();
    });
  });
}

// ─── Buttons ─────────────────────────────────────────────────────────────────
function initButtons() {
  document.getElementById('analyzeBtn').addEventListener('click', analyzeOnly);
  document.getElementById('synthesizeBtn').addEventListener('click', synthesize);
  document.getElementById('refreshHistory').addEventListener('click', loadHistory);
}

function initCharCount() {
  document.getElementById('textInput').addEventListener('input', updateCharCount);
}

function updateCharCount() {
  const len = document.getElementById('textInput').value.length;
  document.getElementById('charCount').textContent = len;
}

// ─── Analyze Only ─────────────────────────────────────────────────────────────
async function analyzeOnly() {
  const text = document.getElementById('textInput').value.trim();
  if (!text) { toast('Please enter some text first', 'error'); return; }

  setStatus('Analyzing...', 'warning');
  try {
    const res = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    renderEmotionResult(data);
    toast(`Detected: ${data.primary_emotion} (${data.intensity_label})`, 'success');
    setStatus('Analyzed', 'success');
  } catch (err) {
    toast('Analysis failed: ' + err.message, 'error');
    setStatus('Error', 'error');
  }
}

// ─── Full Synthesis Pipeline ──────────────────────────────────────────────────
async function synthesize() {
  const text = document.getElementById('textInput').value.trim();
  if (!text) { toast('Please enter some text first', 'error'); return; }

  const btn = document.getElementById('synthesizeBtn');
  btn.disabled = true;

  showProcessing(true, 'Detecting emotion...');
  setStatus('Processing...', 'warning');

  try {
    await sleep(300);
    setProcessingLabel('Mapping vocal parameters...');
    await sleep(200);
    setProcessingLabel('Synthesizing speech...');

    const res = await fetch('/api/synthesize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, voice_style: selectedStyle })
    });
    const data = await res.json();

    if (data.error) throw new Error(data.error);

    lastResult = data;

    // Render all panels
    renderEmotionResult(data.emotion);
    renderVocalParams(data.vocal_params, data.emotion);
    renderAudio(data.audio_url, data.emotion, data.vocal_params, data.synthesis_notes);

    // Apply global theme color
    applyEmotionTheme(data.emotion.color);

    toast(`✓ Synthesized as "${data.emotion.primary_emotion}" · ${data.emotion.intensity_label} intensity`, 'success');
    setStatus('Complete', 'success');

    setTimeout(loadHistory, 1000);
  } catch (err) {
    toast('Synthesis failed: ' + err.message, 'error');
    setStatus('Error', 'error');
    console.error(err);
  } finally {
    showProcessing(false);
    btn.disabled = false;
  }
}

// ─── Render Emotion Panel ─────────────────────────────────────────────────────
function renderEmotionResult(emotion) {
  document.getElementById('emotionPlaceholder').classList.add('hidden');
  const resultEl = document.getElementById('emotionResult');
  resultEl.classList.remove('hidden');

  const color = EMOTION_COLORS[emotion.primary_emotion] || '#7c6af7';
  const intensityPct = Math.round(emotion.intensity * 100);

  // Primary card
  document.getElementById('emotionEmoji').textContent = emotion.emoji;
  document.getElementById('emotionName').textContent = emotion.primary_emotion;
  document.getElementById('emotionIntensityLabel').textContent =
    `${emotion.intensity_label} intensity · valence ${emotion.valence >= 0 ? '+' : ''}${emotion.valence.toFixed(1)}`;

  const card = document.getElementById('primaryCard');
  card.style.setProperty('--emotion-color', color);
  card.style.borderColor = color;
  card.style.boxShadow = `0 0 24px ${color}30`;

  document.getElementById('gaugeFill').style.width = intensityPct + '%';
  document.getElementById('gaugeFill').style.background = `linear-gradient(90deg, ${color}, #fff)`;
  document.getElementById('gaugeValue').textContent = intensityPct + '%';
  document.getElementById('gaugeValue').style.color = color;
  document.getElementById('emotionName').style.color = color;

  // Spectrum bars
  const spectrum = document.getElementById('emotionSpectrum');
  spectrum.innerHTML = '';
  const scores = emotion.all_scores || {};
  const maxScore = Math.max(...Object.values(scores), 0.1);
  Object.entries(scores).sort((a, b) => b[1] - a[1]).slice(0, 8).forEach(([em, score]) => {
    const c = EMOTION_COLORS[em] || '#6b7280';
    const pct = (score / maxScore) * 100;
    spectrum.innerHTML += `
      <div class="spectrum-row">
        <div class="spectrum-label">${em}</div>
        <div class="spectrum-bar-track">
          <div class="spectrum-bar-fill" style="width:${pct}%;background:${c}"></div>
        </div>
        <div class="spectrum-score">${score.toFixed(1)}</div>
      </div>`;
  });

  // Signals
  const signals = emotion.signals || {};
  const signalsRow = document.getElementById('signalsRow');
  signalsRow.innerHTML = `
    <div class="signal-chip">! × ${signals.exclamations || 0}</div>
    <div class="signal-chip">? × ${signals.questions || 0}</div>
    <div class="signal-chip">CAPS ${((signals.caps_ratio || 0) * 100).toFixed(0)}%</div>
    <div class="signal-chip">${signals.word_count || 0} words</div>
  `;

  // Runner-up
  const runnerUpEl = document.getElementById('runnerUp');
  if (emotion.runner_up) {
    runnerUpEl.textContent = `Runner-up: ${emotion.runner_up.emotion} (${emotion.runner_up.score.toFixed(2)})`;
  } else {
    runnerUpEl.textContent = 'No significant secondary emotion detected';
  }
}

// ─── Render Vocal Params ──────────────────────────────────────────────────────
function renderVocalParams(params, emotion) {
  document.getElementById('vocalPlaceholder').classList.add('hidden');
  const resultEl = document.getElementById('vocalResult');
  resultEl.classList.remove('hidden');

  const color = EMOTION_COLORS[emotion.primary_emotion] || '#7c6af7';
  const grid = document.getElementById('paramGrid');
  grid.innerHTML = '';

  const displayParams = ['rate', 'pitch', 'volume', 'pause_factor'];
  displayParams.forEach(key => {
    const meta = PARAM_LABELS[key];
    const val = params[key];
    const pct = ((val - meta.min) / (meta.max - meta.min)) * 100;
    const displayVal = key === 'rate' ? params.rate_words_per_minute : val.toFixed(2);
    const unit = key === 'rate' ? 'wpm' : meta.unit;

    grid.innerHTML += `
      <div class="param-card">
        <div class="param-name">${meta.label}</div>
        <div class="param-value" style="color:${color}">
          ${displayVal}<span class="param-unit">${unit}</span>
        </div>
        <div class="param-bar-track">
          <div class="param-bar-fill" style="width:${Math.max(5, pct)}%;background:${color}"></div>
        </div>
      </div>`;
  });

  // Additional params
  grid.innerHTML += `
    <div class="param-card">
      <div class="param-name">Emphasis</div>
      <div class="param-value" style="color:${color};font-size:16px;text-transform:capitalize">
        ${params.emphasis}
      </div>
    </div>
    <div class="param-card">
      <div class="param-name">Voice Style</div>
      <div class="param-value" style="color:${color};font-size:16px;text-transform:capitalize">
        ${params.voice_style}
      </div>
    </div>`;

  // SSML
  const ssml = (params.ssml_template || '').replace('{TEXT}', '[your text]');
  document.getElementById('ssmlCode').textContent = ssml;
}

// ─── Render Audio ─────────────────────────────────────────────────────────────
function renderAudio(audioUrl, emotion, params, notes) {
  document.getElementById('audioPlaceholder').classList.add('hidden');
  const resultEl = document.getElementById('audioResult');
  resultEl.classList.remove('hidden');

  const player = document.getElementById('audioPlayer');
  player.src = audioUrl;
  player.load();

  const downloadBtn = document.getElementById('downloadBtn');
  downloadBtn.href = audioUrl;
  downloadBtn.download = `empathy_${emotion.primary_emotion}.wav`;

  // Draw waveform visualization (decorative, emotion-reactive)
  drawWaveform(emotion, params);

  // Meta
  document.getElementById('audioMeta').innerHTML = `
    Engine notes: ${notes}<br>
    Pitch: ${params.pitch_semitones > 0 ? '+' : ''}${params.pitch_semitones}st &nbsp;|&nbsp;
    Rate: ${params.rate_words_per_minute} wpm &nbsp;|&nbsp;
    Volume: ${(params.volume * 100).toFixed(0)}%
  `;
}

function drawWaveform(emotion, params) {
  const canvas = document.getElementById('waveformCanvas');
  const ctx = canvas.getContext('2d');
  const W = canvas.width, H = canvas.height;
  ctx.clearRect(0, 0, W, H);

  const color = EMOTION_COLORS[emotion.primary_emotion] || '#7c6af7';
  const intensity = emotion.intensity;
  const rate = params.rate;

  // Create gradient
  const grad = ctx.createLinearGradient(0, 0, W, 0);
  grad.addColorStop(0, color + '20');
  grad.addColorStop(0.5, color);
  grad.addColorStop(1, color + '20');

  ctx.strokeStyle = grad;
  ctx.lineWidth = 1.5;

  // Draw emotion-shaped waveform
  ctx.beginPath();
  const segments = Math.floor(W / 3);
  for (let i = 0; i <= segments; i++) {
    const x = (i / segments) * W;
    const progress = i / segments;

    // Amplitude varies with intensity and emotion
    const baseAmp = H * 0.3 * intensity;
    const freq = 6 + rate * 4;
    const noise = Math.random() * H * 0.04 * intensity;

    const amp = baseAmp * (0.5 + 0.5 * Math.abs(Math.sin(progress * Math.PI)));
    const y = H / 2 + Math.sin(progress * freq * Math.PI) * amp + noise;

    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.stroke();

  // Mirror below
  ctx.globalAlpha = 0.3;
  ctx.beginPath();
  for (let i = 0; i <= segments; i++) {
    const x = (i / segments) * W;
    const progress = i / segments;
    const baseAmp = H * 0.25 * intensity;
    const freq = 6 + rate * 4;
    const amp = baseAmp * (0.5 + 0.5 * Math.abs(Math.sin(progress * Math.PI)));
    const y = H / 2 - Math.sin(progress * freq * Math.PI) * amp;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.stroke();
  ctx.globalAlpha = 1;
}

// ─── Global Theme ─────────────────────────────────────────────────────────────
function applyEmotionTheme(color) {
  document.documentElement.style.setProperty('--emotion-color', color);
  document.documentElement.style.setProperty('--accent-glow', color + '30');
}

// ─── History ──────────────────────────────────────────────────────────────────
async function loadHistory() {
  try {
    const res = await fetch('/api/history');
    const files = await res.json();
    const list = document.getElementById('historyList');
    if (!files.length) {
      list.innerHTML = '<div class="history-empty">No audio generated yet</div>';
      return;
    }
    list.innerHTML = files.map(f => `
      <div class="history-item" onclick="playHistoryItem('${f.url}')">
        <div class="history-icon">🎵</div>
        <div class="history-info">
          <div class="history-name">${f.filename}</div>
          <div class="history-size">${(f.size / 1024).toFixed(1)} KB</div>
        </div>
      </div>
    `).join('');
  } catch (e) {
    console.error('History load failed', e);
  }
}

function playHistoryItem(url) {
  const player = document.getElementById('audioPlayer');
  document.getElementById('audioPlaceholder').classList.add('hidden');
  document.getElementById('audioResult').classList.remove('hidden');
  player.src = url;
  player.play();
}

// ─── Processing UI ────────────────────────────────────────────────────────────
function showProcessing(show, label) {
  const overlay = document.getElementById('processingOverlay');
  overlay.classList.toggle('hidden', !show);
  if (label) setProcessingLabel(label);
}

function setProcessingLabel(text) {
  document.getElementById('processingLabel').textContent = text;
}

// ─── Status ───────────────────────────────────────────────────────────────────
function setStatus(label, type) {
  document.getElementById('statusLabel').textContent = label;
  const dot = document.getElementById('statusDot');
  dot.style.background = type === 'success' ? '#22c55e' : type === 'error' ? '#ef4444' : '#f59e0b';
  dot.style.boxShadow = `0 0 8px ${dot.style.background}`;
}

// ─── Toast ────────────────────────────────────────────────────────────────────
function toast(msg, type = 'info') {
  const container = document.getElementById('toastContainer');
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = msg;
  container.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
