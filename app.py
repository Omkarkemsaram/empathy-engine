"""
The Empathy Engine - Darwix AI Challenge 1
Emotionally intelligent Text-to-Speech service with dynamic vocal modulation.
"""

import os
import uuid
import json
import math
import wave
import struct
import time
from flask import Flask, request, jsonify, render_template, send_from_directory
from emotion_engine import EmotionEngine
from voice_synthesizer import VoiceSynthesizer

app = Flask(__name__)
AUDIO_DIR = os.path.join(os.path.dirname(__file__), "static", "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

emotion_engine = EmotionEngine()
voice_synth = VoiceSynthesizer(audio_dir=AUDIO_DIR)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze():
    """Analyze text and return emotion data without generating audio."""
    data = request.get_json()
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "No text provided"}), 400

    result = emotion_engine.analyze(text)
    return jsonify(result)


@app.route("/api/synthesize", methods=["POST"])
def synthesize():
    """Full pipeline: emotion detection → voice modulation → audio generation."""
    data = request.get_json()
    text = data.get("text", "").strip()
    voice_style = data.get("voice_style", "auto")  # auto, professional, warm, dramatic

    if not text:
        return jsonify({"error": "No text provided"}), 400

    # Step 1: Detect emotion with granularity + intensity
    emotion_data = emotion_engine.analyze(text)

    # Step 2: Map emotion → vocal parameters
    vocal_params = emotion_engine.get_vocal_params(emotion_data, voice_style)

    # Step 3: Generate audio with modulated params
    filename = f"empathy_{uuid.uuid4().hex[:8]}.wav"
    filepath = os.path.join(AUDIO_DIR, filename)

    success, synthesis_notes = voice_synth.synthesize(text, vocal_params, filepath)

    if not success:
        return jsonify({"error": "Audio synthesis failed", "detail": synthesis_notes}), 500

    return jsonify({
        "audio_url": f"/static/audio/{filename}",
        "emotion": emotion_data,
        "vocal_params": vocal_params,
        "synthesis_notes": synthesis_notes,
        "text": text
    })


@app.route("/api/history", methods=["GET"])
def history():
    """Return list of generated audio files."""
    files = []
    for f in os.listdir(AUDIO_DIR):
        if f.endswith(".wav"):
            path = os.path.join(AUDIO_DIR, f)
            files.append({
                "filename": f,
                "url": f"/static/audio/{f}",
                "size": os.path.getsize(path),
                "created": os.path.getctime(path)
            })
    files.sort(key=lambda x: x["created"], reverse=True)
    return jsonify(files[:20])


@app.route("/static/audio/<filename>")
def serve_audio(filename):
    return send_from_directory(AUDIO_DIR, filename)


if __name__ == "__main__":
    print("🎙 The Empathy Engine is starting...")
    print("📍 Visit: http://localhost:5000")
    app.run(debug=True, port=5000)
