# The Empathy Engine
### Emotionally Intelligent Text-to-Speech

> Beyond monotonic delivery — speech that actually feels human.

---

## What It Does

The Empathy Engine is a full-stack service that reads the emotional content of any text and adjusts the synthesized voice to match. It goes well beyond simple positive/negative classification: the system detects 10 distinct emotional categories with intensity scaling, maps them to 5 vocal parameters, generates SSML markup, and serves everything through a real-time web interface.

---

## Features

| Requirement | Status | Notes |
|---|---|---|
| Text input | Done | Web UI + CLI |
| 3+ emotion categories | Done — 10 categories | Joyful, Positive, Inquisitive, Surprised, Concerned, Frustrated, Sad, Urgent, Professional, Neutral |
| 2+ vocal parameters | Done — 5 parameters | Rate, Pitch, Volume, Pause Factor, Emphasis |
| Emotion-to-voice mapping | Done | Per-emotion presets with intensity interpolation |
| Audio output (.wav) | Done | Multi-engine support |
| Intensity scaling | Bonus | "This is good" behaves differently from "This is AMAZING!!!" |
| Granular emotions | Bonus | 10 categories including Inquisitive, Surprised, Urgent |
| Web interface | Bonus | Real-time emotion spectrum, waveform, audio player |
| SSML integration | Bonus | Full SSML output with prosody tags |
| CLI mode | Extra | `python cli.py "text" --style dramatic` |
| Voice style presets | Extra | Auto / Professional / Warm / Dramatic |
| Runner-up emotion | Extra | Detects secondary emotional layer |
| Linguistic signal detection | Extra | Exclamation count, CAPS ratio, question marks |
| Multi-engine fallback | Extra | pyttsx3 → gTTS → Tone synthesis |

---

## Architecture

```
Text Input
    |
    v
EmotionEngine.analyze()
    |-- Keyword scoring (10 emotion lexicons)
    |-- Intensity amplifier/diminisher detection
    |-- Punctuation signals (!!!, CAPS, ???)
    +-- Runner-up detection
    |
    v
EmotionEngine.get_vocal_params()
    |-- Preset lookup (per-emotion base params)
    |-- Intensity scaling (interpolation neutral → preset)
    +-- Voice style overlay (Auto/Professional/Warm/Dramatic)
    |
    v
VoiceSynthesizer.synthesize()
    |-- Engine: pyttsx3 (offline, preferred)
    |-- Engine: gTTS (online, higher quality)
    +-- Engine: Tone Synthesis (always works, no deps)
    |
    v
.wav Audio File
```

---

## Emotion-to-Voice Mapping

Each emotion has a base preset of vocal parameters. The intensity score (0.0–1.0) is used to interpolate between the neutral baseline and the full preset:

```python
scaled_value = neutral_value + (preset_value - neutral_value) * intensity
```

This means:
- `"This is good"` — Positive emotion, low intensity — slight pitch and rate increase
- `"This is ABSOLUTELY INCREDIBLE!!!"` — Joyful emotion, extreme intensity — significant rate and pitch increase

### Emotion Presets

| Emotion | Rate | Pitch | Volume | Pause | Reasoning |
|---|---|---|---|---|---|
| Joyful | 1.20x | 1.15x | 1.10x | 0.8x | Fast, high, energetic |
| Positive | 1.05x | 1.05x | 1.00x | 1.0x | Slightly elevated |
| Inquisitive | 0.95x | 1.10x | 0.95x | 1.1x | Slow-paced, rising tone |
| Surprised | 1.15x | 1.20x | 1.15x | 0.7x | Sharp burst, high pitch |
| Concerned | 0.90x | 0.95x | 0.90x | 1.3x | Careful, measured |
| Frustrated | 1.10x | 0.90x | 1.20x | 0.9x | Clipped, tense, loud |
| Sad | 0.80x | 0.88x | 0.82x | 1.5x | Slow, low, quiet |
| Urgent | 1.30x | 1.05x | 1.15x | 0.6x | Fast, pressing |
| Professional | 1.00x | 1.00x | 1.00x | 1.0x | Measured, neutral |

---

## Setup and Installation

### Prerequisites
- Python 3.9+
- `espeak` on Linux (optional — for pyttsx3 pitch support)
- Internet connection (optional — for gTTS)

### Installation

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/empathy-engine.git
cd empathy-engine

# Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Linux only: install espeak for pyttsx3 pitch support
# sudo apt-get install espeak espeak-data libespeak1

# Run the web app
python app.py
# Visit http://localhost:5000
```

### CLI Mode

```bash
# Analyze and synthesize
python cli.py "I'm absolutely thrilled about this breakthrough!"

# With voice style
python cli.py "This is urgent, we need action immediately" --style dramatic

# Specify output path
python cli.py "Have a wonderful day!" --output happy_output.wav

# Interactive mode
python cli.py --interactive
```

---

## API Reference

### POST /api/analyze
Analyze text emotion without generating audio.

```json
Request:  { "text": "I can't believe this works!" }
Response: {
  "primary_emotion": "surprised",
  "intensity": 0.71,
  "intensity_label": "high",
  "valence": 0.3,
  "emoji": "surprised",
  "runner_up": { "emotion": "positive", "score": 1.2 },
  "all_scores": { "surprised": 2.5, "positive": 1.2 },
  "signals": { "exclamations": 1, "questions": 0, "caps_ratio": 0.0, "word_count": 6 }
}
```

### POST /api/synthesize
Full pipeline: emotion detection, vocal parameter mapping, audio file generation.

```json
Request:  { "text": "...", "voice_style": "auto" }
Response: {
  "audio_url": "/static/audio/empathy_abc123.wav",
  "emotion": { ... },
  "vocal_params": {
    "rate": 1.15,
    "pitch": 1.18,
    "volume": 1.12,
    "pause_factor": 0.72,
    "rate_words_per_minute": 172,
    "pitch_semitones": 2.2,
    "ssml_template": "<speak>...</speak>"
  },
  "synthesis_notes": "Engine: pyttsx3 — rate=1.15 vol=1.12 | Output: empathy_abc123.wav (48200 bytes)"
}
```

### GET /api/history
Returns the last 20 generated audio files.

---

## Design Decisions

### Multi-engine fallback
Different environments have different TTS libraries available. pyttsx3 works fully offline and is suitable for deployment, gTTS produces higher quality output but requires internet access, and the pure tone synthesizer ensures the demo always runs — even in a sandboxed environment.

### Interpolation over fixed presets
Fixed presets create jarring jumps between emotional states. Interpolation produces a smooth, natural spectrum: the same emotion word sounds different depending on how many intensity markers surround it. This is closer to how human vocal expression actually works.

### SSML output
SSML is the industry standard for controlling speech synthesis on Google Cloud TTS, Amazon Polly, Azure Cognitive Services, and ElevenLabs. Even where the local engine does not fully support it, the SSML output means this engine can be dropped in front of any enterprise TTS system with minimal changes.

---

## Potential Extensions

- Hugging Face transformer model (e.g. `j-hartmann/emotion-english-distilroberta-base`) for more accurate classification
- ElevenLabs API for hyper-realistic voices with full parameter control
- Streaming audio via WebSockets for real-time synthesis
- Multi-language emotion detection via multilingual BERT models
- Speaker diarization — different voices for different emotions in dialogue

---

*Built for Darwix AI Challenge 1 — The Empathy Engine*
