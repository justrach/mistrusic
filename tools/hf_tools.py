import json
import numpy as np
import librosa
from smolagents import Tool
from utils.audio_utils import DEFAULT_SR


class AudioClassifierTool(Tool):
    name = "classify_audio"
    description = """Classifies an audio file using a HuggingFace audio classification model (MIT/ast-finetuned-audioset). Returns the top-5 predicted labels with confidence scores as JSON. Use this to understand what kind of audio you're working with (speech, guitar, rain, piano, etc.) before selecting a transformation strategy."""
    inputs = {
        "audio_path": {
            "type": "string",
            "description": "Path to the audio file to classify",
        },
    }
    output_type = "string"

    _pipeline = None

    def setup(self):
        from transformers import pipeline
        self._pipeline = pipeline(
            "audio-classification",
            model="MIT/ast-finetuned-audioset-10-10-0.4593",
            device="cpu",
        )

    def forward(self, audio_path: str) -> str:
        if self._pipeline is None:
            self.setup()

        y, sr = librosa.load(audio_path, sr=16000, mono=True)
        # Truncate to 10 seconds max for speed
        max_samples = 16000 * 10
        if len(y) > max_samples:
            y = y[:max_samples]

        results = self._pipeline({"raw": y, "sampling_rate": 16000}, top_k=5)
        classifications = [
            {"label": r["label"], "confidence": round(r["score"], 4)}
            for r in results
        ]
        return json.dumps(classifications)


class AudioFeatureExtractorTool(Tool):
    name = "extract_audio_features"
    description = """Extracts quantitative audio features from a file using librosa. Returns a JSON dict with: duration_seconds, sample_rate, rms_mean, spectral_centroid_mean, spectral_centroid_std, tempo, zero_crossing_rate_mean, and mfcc_means (first 13 coefficients). Use this to compare original vs. morphed audio features during evaluation."""
    inputs = {
        "audio_path": {
            "type": "string",
            "description": "Path to the audio file to extract features from",
        },
    }
    output_type = "string"

    def forward(self, audio_path: str) -> str:
        y, sr = librosa.load(audio_path, sr=DEFAULT_SR, mono=True)

        rms = librosa.feature.rms(y=y)[0]
        centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        zcr = librosa.feature.zero_crossing_rate(y=y)[0]
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)

        features = {
            "duration": round(len(y) / sr, 2),
            "rms": round(float(np.mean(rms)), 4),
            "centroid": round(float(np.mean(centroid)), 1),
            "tempo": round(float(tempo) if np.isscalar(tempo) else float(tempo[0]), 1),
            "zcr": round(float(np.mean(zcr)), 4),
        }
        return json.dumps(features)
