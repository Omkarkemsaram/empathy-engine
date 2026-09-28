"""
Voice Synthesizer - Handles TTS with emotional vocal modulation.

Engine priority:
1. pyttsx3 (offline, fast, supports rate/volume/pitch on some backends)
2. gTTS (online, better quality, we modulate via audio processing)
3. Pure WAV tone synthesis (always works, for demo/testing)

Vocal parameters are applied via:
- Direct engine properties (pyttsx3)
- Audio post-processing via audioop/wave (pitch shift, speed change)
- Silence padding (pause_factor)
"""

import os
import wave
import struct
import math
import time
from typing import Tuple, Dict


class VoiceSynthesizer:
    def __init__(self, audio_dir: str):
        self.audio_dir = audio_dir
        self.engine_available = self._detect_engine()

    def _detect_engine(self) -> str:
        """Detect available TTS engines."""
        # Try pyttsx3
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.stop()
            return "pyttsx3"
        except Exception:
            pass

        # Try gTTS
        try:
            from gtts import gTTS
            return "gtts"
        except Exception:
            pass

        # Fallback: pure tone synthesis (always works)
        return "tone"

    def synthesize(self, text: str, vocal_params: Dict, output_path: str) -> Tuple[bool, str]:
        """
        Synthesize speech with applied vocal parameters.
        Returns (success, notes_string).
        """
        engine = self.engine_available
        notes = []

        if engine == "pyttsx3":
            success, msg = self._synth_pyttsx3(text, vocal_params, output_path)
            notes.append(f"Engine: pyttsx3 — {msg}")
        elif engine == "gtts":
            success, msg = self._synth_gtts(text, vocal_params, output_path)
            notes.append(f"Engine: gTTS — {msg}")
        else:
            success, msg = self._synth_tone(text, vocal_params, output_path)
            notes.append(f"Engine: Tone Synthesis — {msg}")

        if success and os.path.exists(output_path):
            size = os.path.getsize(output_path)
            notes.append(f"Output: {os.path.basename(output_path)} ({size} bytes)")

        return success, " | ".join(notes)

    # ── pyttsx3 ───────────────────────────────────────────────────────────────

    def _synth_pyttsx3(self, text: str, params: Dict, output_path: str) -> Tuple[bool, str]:
        try:
            import pyttsx3
            engine = pyttsx3.init()

            # Set rate (words per minute, default ~200)
            base_rate = engine.getProperty("rate")
            engine.setProperty("rate", int(base_rate * params["rate"]))

            # Set volume (0.0 to 1.0)
            engine.setProperty("volume", min(1.0, params["volume"]))

            # Pitch: pyttsx3 doesn't directly support pitch on all backends
            # On Windows SAPI5, we can try voice selection based on pitch desire
            try:
                voices = engine.getProperty("voices")
                if voices and len(voices) > 1:
                    # Higher pitch → prefer female voice; lower → male
                    if params["pitch"] > 1.05 and len(voices) > 1:
                        engine.setProperty("voice", voices[1].id)
                    else:
                        engine.setProperty("voice", voices[0].id)
            except Exception:
                pass

            # Save to file
            engine.save_to_file(text, output_path)
            engine.runAndWait()
            engine.stop()

            # Post-process: apply pause factor via silence padding
            if os.path.exists(output_path) and output_path.endswith(".wav"):
                self._apply_pause_padding(output_path, params.get("pause_factor", 1.0))

            return True, f"rate={params['rate']:.2f} vol={params['volume']:.2f}"
        except Exception as e:
            return False, f"pyttsx3 error: {e}"

    # ── gTTS ──────────────────────────────────────────────────────────────────

    def _synth_gtts(self, text: str, params: Dict, output_path: str) -> Tuple[bool, str]:
        try:
            from gtts import gTTS
            import io

            # gTTS only supports slow/normal speed directly
            slow = params["rate"] < 0.85
            tts = gTTS(text=text, lang="en", slow=slow)

            # Save to mp3 then convert to wav for post-processing
            mp3_path = output_path.replace(".wav", ".mp3")
            tts.save(mp3_path)

            # Try to convert mp3→wav using available tools
            converted = self._mp3_to_wav(mp3_path, output_path)

            if converted and os.path.exists(output_path):
                self._apply_pause_padding(output_path, params.get("pause_factor", 1.0))
                os.remove(mp3_path)
                return True, f"gTTS OK, slow={slow}"
            else:
                # Return mp3 path instead
                os.rename(mp3_path, output_path.replace(".wav", ".mp3"))
                return True, "gTTS OK (mp3 format)"

        except Exception as e:
            return False, f"gTTS error: {e}"

    def _mp3_to_wav(self, mp3_path: str, wav_path: str) -> bool:
        """Attempt mp3 → wav conversion."""
        try:
            import subprocess
            result = subprocess.run(
                ["ffmpeg", "-y", "-i", mp3_path, wav_path],
                capture_output=True, timeout=30
            )
            return result.returncode == 0
        except Exception:
            pass
        try:
            from pydub import AudioSegment
            sound = AudioSegment.from_mp3(mp3_path)
            sound.export(wav_path, format="wav")
            return True
        except Exception:
            return False

    # ── Tone Synthesis (always works, demo mode) ──────────────────────────────

    def _synth_tone(self, text: str, params: Dict, output_path: str) -> Tuple[bool, str]:
        """
        Generate a synthesized WAV using tone sequences that reflect emotion.
        This always works without any external dependencies.
        The tones represent a "phoneme melody" that encodes emotional character.
        """
        sample_rate = 22050
        duration_per_word = 0.25 / params["rate"]
        words = text.split()

        # Generate frequency melody based on emotional pitch contour
        base_freq = 180 * params["pitch"]  # Base fundamental frequency
        samples = []

        # Intro silence
        intro_silence = int(sample_rate * 0.1 * params["pause_factor"])
        samples.extend([0] * intro_silence)

        for i, word in enumerate(words):
            # Each word gets a tone cluster
            word_len = len(word)
            freq_variation = self._word_to_freq(word, base_freq, params)

            # Tone duration based on word length
            word_duration = duration_per_word * (0.5 + word_len * 0.08)
            num_samples = int(sample_rate * word_duration)

            # Generate tone with ADSR envelope
            word_samples = self._generate_tone_adsr(
                freq=freq_variation,
                num_samples=num_samples,
                volume=params["volume"],
                sample_rate=sample_rate,
                harmonics=True
            )
            samples.extend(word_samples)

            # Inter-word pause
            pause_duration = 0.05 * params["pause_factor"]
            if word.endswith((",", ";", ":")):
                pause_duration *= 1.5
            if word.endswith((".", "!", "?")):
                pause_duration *= 2.5
            pause_samples = int(sample_rate * pause_duration)
            samples.extend([0] * pause_samples)

        # Outro silence
        samples.extend([0] * int(sample_rate * 0.15))

        # Write WAV
        self._write_wav(output_path, samples, sample_rate)

        return True, f"Tone synthesis: {len(words)} words, pitch_mult={params['pitch']:.2f}, rate={params['rate']:.2f}"

    def _word_to_freq(self, word: str, base_freq: float, params: Dict) -> float:
        """Derive a frequency from word characteristics."""
        # Use character codes to vary frequency naturally
        char_sum = sum(ord(c) for c in word.lower()) % 100
        variation = (char_sum - 50) / 100.0  # -0.5 to +0.5
        freq = base_freq * (1.0 + variation * 0.3)

        # Emotional modulation
        pitch = params["pitch"]
        freq *= pitch

        # Question words get rising intonation
        if word.lower() in ["how", "why", "what", "when", "where", "who"]:
            freq *= 1.15

        return max(80, min(500, freq))

    def _generate_tone_adsr(self, freq: float, num_samples: int, volume: float,
                             sample_rate: int, harmonics: bool = True) -> list:
        """Generate a tone with Attack-Decay-Sustain-Release envelope."""
        attack = int(num_samples * 0.08)
        decay = int(num_samples * 0.12)
        sustain_level = 0.7
        release = int(num_samples * 0.15)

        samples = []
        vol = min(1.0, volume) * 28000  # 16-bit max ~32767

        for i in range(num_samples):
            # ADSR envelope
            if i < attack:
                env = i / attack
            elif i < attack + decay:
                env = 1.0 - (1.0 - sustain_level) * ((i - attack) / decay)
            elif i < num_samples - release:
                env = sustain_level
            else:
                env = sustain_level * (1.0 - (i - (num_samples - release)) / release)

            t = i / sample_rate

            # Fundamental + harmonics for richer sound
            sample = math.sin(2 * math.pi * freq * t)
            if harmonics:
                sample += 0.5 * math.sin(2 * math.pi * freq * 2 * t)
                sample += 0.25 * math.sin(2 * math.pi * freq * 3 * t)
                sample += 0.125 * math.sin(2 * math.pi * freq * 4 * t)
                sample /= 1.875  # Normalize

            samples.append(int(sample * env * vol))

        return samples

    def _write_wav(self, path: str, samples: list, sample_rate: int):
        """Write samples to a WAV file."""
        with wave.open(path, "w") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            data = struct.pack(f"<{len(samples)}h", *[
                max(-32767, min(32767, s)) for s in samples
            ])
            wav_file.writeframes(data)

    def _apply_pause_padding(self, wav_path: str, pause_factor: float):
        """Add silence padding to a WAV file based on pause_factor."""
        try:
            with wave.open(wav_path, "r") as wf:
                params = wf.getparams()
                frames = wf.readframes(wf.getnframes())
                sample_rate = wf.getframerate()
                sampwidth = wf.getsampwidth()

            if pause_factor <= 1.0:
                return  # No padding needed

            # Add silence proportional to pause_factor
            extra_silence_duration = 0.2 * (pause_factor - 1.0)
            silence_frames = int(sample_rate * extra_silence_duration)
            silence = b"\x00" * (silence_frames * sampwidth)

            with wave.open(wav_path, "w") as wf:
                wf.setparams(params)
                wf.writeframes(silence + frames + silence)
        except Exception:
            pass  # Non-critical, skip padding
