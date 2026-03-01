import json
from smolagents import Tool
import librosa
import soundfile as sf


class AudioInfoTool(Tool):
    name = "get_audio_info"
    description = """Returns metadata about an audio file: duration in seconds, sample rate, number of channels, and format. Use this to quickly check audio properties before processing."""
    inputs = {
        "audio_path": {
            "type": "string",
            "description": "Path to the audio file",
        }
    }
    output_type = "string"

    def forward(self, audio_path: str) -> str:
        info = sf.info(audio_path)
        y, sr = librosa.load(audio_path, sr=None, mono=False)
        channels = 1 if y.ndim == 1 else y.shape[0]
        result = {
            "duration_seconds": round(info.duration, 2),
            "sample_rate": info.samplerate,
            "channels": channels,
            "format": info.format,
            "subtype": info.subtype,
        }
        return json.dumps(result)
