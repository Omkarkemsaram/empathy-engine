"""
Emotion Engine - Core sentiment and emotion analysis module.

Uses a multi-layered approach:
1. VADER for fast valence scoring
2. Keyword-based granular emotion detection (10 emotion categories)
3. Intensity scaling based on linguistic markers
4. Emotion → Vocal parameter mapping with SSML generation
"""

import re
import math
from typing import Dict, Tuple


# ─── Emotion Lexicon ──────────────────────────────────────────────────────────

EMOTION_LEXICON = {
    "joyful": {
        "keywords": [
            "amazing", "wonderful", "fantastic", "incredible", "love", "happy",
            "excited", "great", "excellent", "brilliant", "awesome", "delighted",
            "thrilled", "ecstatic", "overjoyed", "elated", "euphoric", "bliss",
            "hooray", "yay", "celebrate", "perfect", "best ever", "outstanding"
        ],
        "intensifiers": ["so", "very", "extremely", "absolutely", "incredibly", "super"],
        "valence": 1.0,
        "color": "#FFD700",
        "emoji": "😄"
    },
    "positive": {
        "keywords": [
            "good", "nice", "glad", "pleased", "satisfied", "fine", "okay",
            "better", "improved", "helpful", "thanks", "thank you", "appreciate",
            "welcome", "sure", "certainly", "of course", "no problem"
        ],
        "intensifiers": ["quite", "pretty", "fairly", "rather"],
        "valence": 0.6,
        "color": "#90EE90",
        "emoji": "🙂"
    },
    "inquisitive": {
        "keywords": [
            "how", "why", "what", "when", "where", "who", "which", "wonder",
            "curious", "interested", "tell me", "explain", "clarify", "understand",
            "could you", "would you", "can you", "is it", "are there", "do you"
        ],
        "intensifiers": ["really", "exactly", "specifically", "precisely"],
        "valence": 0.1,
        "color": "#87CEEB",
        "emoji": "🤔"
    },
    "surprised": {
        "keywords": [
            "wow", "whoa", "oh", "really", "seriously", "no way", "unbelievable",
            "unexpected", "shocking", "astonishing", "remarkable", "suddenly",
            "wait", "hold on", "what!", "really?", "you're kidding"
        ],
        "intensifiers": ["completely", "totally", "utterly", "absolutely"],
        "valence": 0.3,
        "color": "#FF69B4",
        "emoji": "😲"
    },
    "concerned": {
        "keywords": [
            "worried", "concern", "issue", "problem", "trouble", "difficult",
            "challenge", "unfortunately", "however", "but", "although", "though",
            "not sure", "uncertain", "unsure", "risky", "careful", "warning"
        ],
        "intensifiers": ["quite", "rather", "somewhat", "fairly"],
        "valence": -0.3,
        "color": "#FFA500",
        "emoji": "😟"
    },
    "frustrated": {
        "keywords": [
            "frustrated", "annoyed", "angry", "terrible", "horrible", "awful",
            "hate", "worst", "ridiculous", "unacceptable", "impossible",
            "can't", "won't", "refuse", "broken", "failed", "again", "still not"
        ],
        "intensifiers": ["so", "very", "extremely", "absolutely", "completely"],
        "valence": -0.7,
        "color": "#FF4500",
        "emoji": "😠"
    },
    "sad": {
        "keywords": [
            "sad", "sorry", "unfortunate", "miss", "lost", "gone", "regret",
            "disappoint", "heartbroken", "grief", "mourn", "depressed", "unhappy",
            "crying", "tears", "goodbye", "farewell", "alone", "lonely"
        ],
        "intensifiers": ["deeply", "truly", "genuinely", "profoundly"],
        "valence": -0.8,
        "color": "#6495ED",
        "emoji": "😢"
    },
    "urgent": {
        "keywords": [
            "urgent", "immediately", "asap", "right now", "emergency", "critical",
            "must", "need to", "have to", "deadline", "quickly", "fast", "hurry",
            "important", "crucial", "vital", "essential", "time sensitive"
        ],
        "intensifiers": ["very", "extremely", "highly", "absolutely"],
        "valence": -0.1,
        "color": "#DC143C",
        "emoji": "⚡"
    },
    "professional": {
        "keywords": [
            "meeting", "report", "schedule", "project", "team", "client",
            "business", "professional", "strategy", "objective", "agenda",
            "proposal", "quarterly", "budget", "review", "update", "status"
        ],
        "intensifiers": ["formally", "officially", "specifically"],
        "valence": 0.0,
        "color": "#708090",
        "emoji": "💼"
    },
    "neutral": {
        "keywords": [],
        "intensifiers": [],
        "valence": 0.0,
        "color": "#A9A9A9",
        "emoji": "😐"
    }
}


# ─── Intensity Markers ────────────────────────────────────────────────────────

INTENSITY_AMPLIFIERS = {
    "very": 1.2, "so": 1.15, "extremely": 1.5, "absolutely": 1.4,
    "incredibly": 1.45, "unbelievably": 1.5, "super": 1.3, "ultra": 1.4,
    "deeply": 1.35, "truly": 1.25, "completely": 1.4, "totally": 1.35,
    "!!": 1.3, "!!!": 1.6
}

INTENSITY_DIMINISHERS = {
    "slightly": 0.7, "a bit": 0.75, "somewhat": 0.8, "kind of": 0.75,
    "kinda": 0.75, "rather": 0.85, "fairly": 0.85, "a little": 0.75
}


# ─── Vocal Parameter Presets ──────────────────────────────────────────────────

VOCAL_PRESETS = {
    "joyful": {
        "rate": 1.20,       # Faster, energetic
        "pitch": 1.15,      # Higher pitch
        "volume": 1.10,     # Slightly louder
        "pause_factor": 0.8, # Shorter pauses
        "emphasis": "strong",
        "ssml_prosody": 'rate="fast" pitch="+2st" volume="loud"'
    },
    "positive": {
        "rate": 1.05,
        "pitch": 1.05,
        "volume": 1.0,
        "pause_factor": 1.0,
        "emphasis": "moderate",
        "ssml_prosody": 'rate="medium" pitch="+1st" volume="medium"'
    },
    "inquisitive": {
        "rate": 0.95,       # Slightly slower, thoughtful
        "pitch": 1.10,      # Rising intonation
        "volume": 0.95,
        "pause_factor": 1.1,
        "emphasis": "moderate",
        "ssml_prosody": 'rate="medium" pitch="+1.5st" volume="medium"'
    },
    "surprised": {
        "rate": 1.15,       # Quick burst
        "pitch": 1.20,      # High pitch for surprise
        "volume": 1.15,
        "pause_factor": 0.7,
        "emphasis": "strong",
        "ssml_prosody": 'rate="fast" pitch="+3st" volume="loud"'
    },
    "concerned": {
        "rate": 0.90,       # Slower, careful
        "pitch": 0.95,      # Slightly lower
        "volume": 0.90,
        "pause_factor": 1.3,
        "emphasis": "moderate",
        "ssml_prosody": 'rate="slow" pitch="-0.5st" volume="soft"'
    },
    "frustrated": {
        "rate": 1.10,       # Clipped, sharp
        "pitch": 0.90,      # Lower, tense
        "volume": 1.20,     # Louder
        "pause_factor": 0.9,
        "emphasis": "strong",
        "ssml_prosody": 'rate="medium" pitch="-1st" volume="x-loud"'
    },
    "sad": {
        "rate": 0.80,       # Slow, heavy
        "pitch": 0.88,      # Lower pitch
        "volume": 0.82,     # Quieter
        "pause_factor": 1.5,
        "emphasis": "reduced",
        "ssml_prosody": 'rate="x-slow" pitch="-2st" volume="soft"'
    },
    "urgent": {
        "rate": 1.30,       # Fast, pressing
        "pitch": 1.05,
        "volume": 1.15,
        "pause_factor": 0.6,
        "emphasis": "strong",
        "ssml_prosody": 'rate="x-fast" pitch="+0.5st" volume="loud"'
    },
    "professional": {
        "rate": 1.00,       # Measured
        "pitch": 1.00,      # Neutral
        "volume": 1.00,
        "pause_factor": 1.0,
        "emphasis": "none",
        "ssml_prosody": 'rate="medium" pitch="0st" volume="medium"'
    },
    "neutral": {
        "rate": 1.00,
        "pitch": 1.00,
        "volume": 1.00,
        "pause_factor": 1.0,
        "emphasis": "none",
        "ssml_prosody": 'rate="medium" pitch="0st" volume="medium"'
    }
}


class EmotionEngine:
    """
    Multi-layer emotion detection with intensity scaling.

    Pipeline:
    1. Preprocessing (lowercase, punctuation normalization)
    2. Keyword scoring across 10 emotion categories
    3. Intensity marker detection and scaling
    4. Punctuation/capitalization signals
    5. Confidence scoring and runner-up detection
    """

    def analyze(self, text: str) -> Dict:
        """Full emotion analysis returning structured data."""
        text_lower = text.lower()
        words = re.findall(r"\b\w+\b", text_lower)

        # Score each emotion
        scores = {}
        for emotion, config in EMOTION_LEXICON.items():
            if emotion == "neutral":
                continue
            score = self._score_emotion(text_lower, words, config)
            if score > 0:
                scores[emotion] = score

        # Determine primary emotion
        if not scores:
            primary = "neutral"
            primary_score = 0.0
        else:
            primary = max(scores, key=scores.get)
            primary_score = scores[primary]

        # Compute intensity (0.0 - 1.0)
        intensity = self._compute_intensity(text_lower, primary_score)

        # Punctuation signals
        exclamations = text.count("!")
        questions = text.count("?")
        caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)

        # Adjust intensity based on punctuation
        if exclamations >= 2:
            intensity = min(1.0, intensity * 1.3)
        if caps_ratio > 0.4:
            intensity = min(1.0, intensity * 1.2)

        # Runner-up emotion
        runner_up = None
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        if len(sorted_scores) >= 2:
            runner_up = {"emotion": sorted_scores[1][0], "score": round(sorted_scores[1][1], 3)}

        return {
            "primary_emotion": primary,
            "intensity": round(intensity, 3),
            "intensity_label": self._intensity_label(intensity),
            "valence": EMOTION_LEXICON[primary]["valence"],
            "color": EMOTION_LEXICON[primary]["color"],
            "emoji": EMOTION_LEXICON[primary]["emoji"],
            "runner_up": runner_up,
            "all_scores": {k: round(v, 3) for k, v in scores.items()},
            "signals": {
                "exclamations": exclamations,
                "questions": questions,
                "caps_ratio": round(caps_ratio, 3),
                "word_count": len(words)
            }
        }

    def _score_emotion(self, text_lower: str, words: list, config: dict) -> float:
        """Score a single emotion based on keyword matches."""
        score = 0.0
        for kw in config["keywords"]:
            if kw in text_lower:
                # Phrase keywords get more weight
                weight = 1.5 if " " in kw else 1.0
                score += weight

        # Check if intensifiers precede emotion keywords
        for intensifier in config.get("intensifiers", []):
            if intensifier in text_lower:
                score *= 1.15

        return score

    def _compute_intensity(self, text_lower: str, base_score: float) -> float:
        """Compute 0-1 intensity score using amplifiers/diminishers."""
        multiplier = 1.0

        for word, factor in INTENSITY_AMPLIFIERS.items():
            if word in text_lower:
                multiplier *= factor
                break  # Only apply strongest

        for phrase, factor in INTENSITY_DIMINISHERS.items():
            if phrase in text_lower:
                multiplier *= factor
                break

        # Normalize: base_score 1-5 → 0.2-0.9
        raw = min(base_score / 6.0, 1.0)
        return min(1.0, raw * multiplier + 0.1)

    def _intensity_label(self, intensity: float) -> str:
        if intensity >= 0.85:
            return "extreme"
        elif intensity >= 0.65:
            return "high"
        elif intensity >= 0.40:
            return "moderate"
        elif intensity >= 0.20:
            return "low"
        else:
            return "minimal"

    def get_vocal_params(self, emotion_data: Dict, voice_style: str = "auto") -> Dict:
        """
        Map emotion + intensity → vocal parameter set.
        Intensity scaling is the key differentiator: 
        'This is good' vs 'This is ABSOLUTELY INCREDIBLE!!!' get different param values.
        """
        emotion = emotion_data["primary_emotion"]
        intensity = emotion_data["intensity"]

        base = VOCAL_PRESETS.get(emotion, VOCAL_PRESETS["neutral"]).copy()

        # Intensity scaling: interpolate between neutral and full preset
        neutral = VOCAL_PRESETS["neutral"]

        def scale(base_val, neutral_val, intensity):
            delta = base_val - neutral_val
            return neutral_val + (delta * intensity)

        scaled_rate = scale(base["rate"], neutral["rate"], intensity)
        scaled_pitch = scale(base["pitch"], neutral["pitch"], intensity)
        scaled_volume = scale(base["volume"], neutral["volume"], intensity)
        scaled_pause = scale(base["pause_factor"], neutral["pause_factor"], intensity)

        # Voice style override
        if voice_style == "professional":
            scaled_rate = min(scaled_rate, 1.05)
            scaled_pitch = min(scaled_pitch, 1.05)
        elif voice_style == "dramatic":
            scaled_rate *= 1.1
            scaled_pitch = scaled_pitch * 1.1 if scaled_pitch > 1 else scaled_pitch * 0.9
        elif voice_style == "warm":
            scaled_volume = min(scaled_volume, 1.05)
            scaled_rate = max(scaled_rate, 0.9)

        # Generate SSML with computed params
        pitch_semitones = round((scaled_pitch - 1.0) * 12, 1)  # Convert to semitones
        rate_pct = round(scaled_rate * 100)
        ssml = self._generate_ssml(
            "{TEXT}",
            pitch_st=pitch_semitones,
            rate_pct=rate_pct,
            volume=scaled_volume,
            pause_factor=scaled_pause,
            emphasis=base["emphasis"]
        )

        return {
            "rate": round(scaled_rate, 3),
            "pitch": round(scaled_pitch, 3),
            "volume": round(scaled_volume, 3),
            "pause_factor": round(scaled_pause, 3),
            "emphasis": base["emphasis"],
            "ssml_template": ssml,
            "voice_style": voice_style,
            "pitch_semitones": pitch_semitones,
            "rate_words_per_minute": round(150 * scaled_rate),  # baseline 150wpm
        }

    def _generate_ssml(self, text: str, pitch_st: float, rate_pct: int,
                       volume: float, pause_factor: float, emphasis: str) -> str:
        """Generate SSML markup for advanced TTS engines."""
        vol_str = "loud" if volume > 1.1 else "soft" if volume < 0.9 else "medium"
        rate_str = f"{rate_pct}%"
        pitch_str = f"{pitch_st:+.1f}st"

        ssml = f"""<speak>
  <prosody rate="{rate_str}" pitch="{pitch_str}" volume="{vol_str}">
    {text}
  </prosody>
</speak>"""
        return ssml
