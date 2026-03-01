import numpy as np
import librosa
from smolagents import Tool


class ScoreAudioQualityTool(Tool):
    name = "score_audio_quality"
    description = """Scores and ranks multiple audio candidates against a text description AND the original audio.
Returns a JSON string with ranked scores. Uses CLAP for text-audio similarity and spectral analysis for diversity/quality.
Pass the original audio path so the scorer can measure how much each candidate actually transformed the sound.
Higher combined_score = better match + more distinct transformation + better audio quality."""
    inputs = {
        "candidate_paths": {
            "type": "string",
            "description": "Comma-separated paths to candidate audio files (e.g., '/path/c1.wav,/path/c2.wav,/path/c3.wav')",
        },
        "original_path": {
            "type": "string",
            "description": "Path to the original (untransformed) audio file for comparison",
        },
        "description": {
            "type": "string",
            "description": "Text description of the desired audio quality/character (e.g., 'underwater piano with reverb')",
        },
    }
    output_type = "string"

    _model = None
    _processor = None

    def setup(self):
        from transformers import ClapModel, ClapProcessor
        self._processor = ClapProcessor.from_pretrained("laion/clap-htsat-unfused")
        self._model = ClapModel.from_pretrained("laion/clap-htsat-unfused")
        self._model.eval()

    def forward(self, candidate_paths: str, original_path: str, description: str) -> str:
        if self._model is None:
            self.setup()

        import torch
        import json

        paths = [p.strip() for p in candidate_paths.split(",")]

        # Load all audio at 48kHz
        def load_clip(path):
            y, _ = librosa.load(path, sr=48000, mono=True)
            max_samples = 48000 * 10
            if len(y) > max_samples:
                y = y[:max_samples]
            return y

        original_audio = load_clip(original_path)
        candidate_audios = [load_clip(p) for p in paths]

        # --- Dimension 1: CLAP text-audio similarity (intent match) ---
        # Score with multiple text prompts for better discrimination
        text_prompts = [
            description,
            f"high quality {description}",
            f"professional sounding {description}",
        ]

        all_audios = candidate_audios
        inputs = self._processor(
            text=text_prompts,
            audios=all_audios,
            sampling_rate=48000,
            return_tensors="pt",
            padding=True,
        )

        with torch.no_grad():
            outputs = self._model(**inputs)
            audio_embeds = outputs.audio_embeds  # [n_candidates, dim]
            text_embeds = outputs.text_embeds    # [n_prompts, dim]

            # Average similarity across all text prompts for each candidate
            # shape: [n_candidates, n_prompts]
            sim_matrix = torch.nn.functional.cosine_similarity(
                audio_embeds.unsqueeze(1), text_embeds.unsqueeze(0), dim=2
            )
            clap_scores = sim_matrix.mean(dim=1).cpu().numpy()  # [n_candidates]

            # Also get original's CLAP score for reference
            orig_inputs = self._processor(
                text=text_prompts,
                audios=[original_audio],
                sampling_rate=48000,
                return_tensors="pt",
                padding=True,
            )
            orig_outputs = self._model(**orig_inputs)
            orig_audio_embed = orig_outputs.audio_embeds
            orig_sim = torch.nn.functional.cosine_similarity(
                orig_audio_embed.unsqueeze(1), text_embeds.unsqueeze(0), dim=2
            )
            orig_clap = float(orig_sim.mean().item())

            # --- Dimension 2: Audio embedding distance from original ---
            # Measures how much transformation actually happened
            orig_embed_for_dist = self._model.get_audio_features(
                **self._processor(audios=[original_audio], sampling_rate=48000, return_tensors="pt")
            )
            distances = []
            for i in range(len(candidate_audios)):
                dist = float((1 - torch.nn.functional.cosine_similarity(
                    audio_embeds[i:i+1], orig_embed_for_dist
                )).item())
                distances.append(dist)

        distances = np.array(distances)

        # --- Dimension 3: Spectral quality metrics ---
        quality_scores = []
        for audio in candidate_audios:
            score = _spectral_quality(audio, 48000)
            quality_scores.append(score)
        quality_scores = np.array(quality_scores)

        # --- Combine scores ---
        # Normalize each dimension to [0, 1] range relative to candidates
        def normalize(arr):
            mn, mx = arr.min(), arr.max()
            if mx - mn < 1e-8:
                return np.ones_like(arr) * 0.5
            return (arr - mn) / (mx - mn)

        clap_norm = normalize(clap_scores)
        dist_norm = normalize(distances)
        quality_norm = normalize(quality_scores)

        # Weighted combination: intent match (50%) + transformation distance (25%) + quality (25%)
        combined = 0.50 * clap_norm + 0.25 * dist_norm + 0.25 * quality_norm

        results = {}
        for i, path in enumerate(paths):
            label = f"candidate_{i+1}"
            results[label] = {
                "combined_score": round(float(combined[i]), 4),
                "clap_similarity": round(float(clap_scores[i]), 4),
                "transformation_distance": round(float(distances[i]), 4),
                "spectral_quality": round(float(quality_scores[i]), 4),
            }

        best_idx = int(np.argmax(combined))
        results["best"] = f"candidate_{best_idx + 1}"
        results["best_path"] = paths[best_idx]
        results["original_clap_score"] = round(orig_clap, 4)

        return json.dumps(results)


def _spectral_quality(y: np.ndarray, sr: int) -> float:
    """Heuristic audio quality score based on spectral properties."""
    # Spectral flatness — higher = more noise-like, moderate is musical
    flatness = float(np.mean(librosa.feature.spectral_flatness(y=y)))

    # Spectral rolloff — higher = more high-frequency content (brighter)
    rolloff = float(np.mean(librosa.feature.spectral_rolloff(y=y, sr=sr)))
    rolloff_norm = min(rolloff / (sr / 2), 1.0)

    # Dynamic range — ratio of peak to RMS (higher = more dynamic)
    rms = np.sqrt(np.mean(y ** 2) + 1e-10)
    peak = np.max(np.abs(y)) + 1e-10
    crest_factor = peak / rms
    crest_norm = min(crest_factor / 10.0, 1.0)  # normalize, typical range 3-10

    # Penalize near-silence or clipping
    silence_penalty = 1.0 if rms > 0.001 else 0.1
    clip_penalty = 1.0 if np.mean(np.abs(y) > 0.99) < 0.01 else 0.5

    # Moderate flatness is good (not pure tone, not pure noise)
    flatness_score = 1.0 - abs(flatness - 0.15) * 3  # peak around 0.15
    flatness_score = max(0.0, min(1.0, flatness_score))

    quality = (
        0.3 * flatness_score +
        0.3 * rolloff_norm +
        0.2 * crest_norm +
        0.1 * silence_penalty +
        0.1 * clip_penalty
    )

    return quality
