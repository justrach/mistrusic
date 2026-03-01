import os
import json
from smolagents import Tool
from utils.audio_utils import temp_path


class GenerateSoundEffectTool(Tool):
    name = "generate_sound_effect"
    description = """Generates an audio sound effect from a text description using ElevenLabs Sound Effects API. Returns the file path to the generated audio. Use this when the user describes a sound in text instead of uploading Sound B, or to generate intermediate textures/layers (e.g. 'thunderstorm', 'vinyl crackle', 'ocean waves', 'fire crackling')."""
    inputs = {
        "text": {
            "type": "string",
            "description": "Description of the sound effect to generate (e.g. 'heavy thunderstorm with rain')",
        },
        "duration_seconds": {
            "type": "number",
            "description": "Duration of the sound effect in seconds (0.5 to 22). Default 5.0.",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(self, text: str, duration_seconds: float = 5.0) -> str:
        from elevenlabs import ElevenLabs

        client = ElevenLabs(api_key=os.environ.get("ELEVENLABS_API_KEY"))
        duration_seconds = max(0.5, min(22.0, float(duration_seconds)))

        result = client.text_to_sound_effects.convert(
            text=text,
            duration_seconds=duration_seconds,
        )

        out = temp_path()
        with open(out, "wb") as f:
            for chunk in result:
                f.write(chunk)
        return out


class AudioIsolationTool(Tool):
    name = "isolate_audio"
    description = """Removes background noise from an audio file using ElevenLabs Audio Isolation API. Returns the path to the cleaned audio with vocals/foreground isolated. Use this as a preprocessing step before voice transformation, or to clean up noisy recordings."""
    inputs = {
        "audio_path": {
            "type": "string",
            "description": "Path to the audio file to isolate vocals/foreground from",
        },
    }
    output_type = "string"

    def forward(self, audio_path: str) -> str:
        from elevenlabs import ElevenLabs

        client = ElevenLabs(api_key=os.environ.get("ELEVENLABS_API_KEY"))

        with open(audio_path, "rb") as f:
            audio_data = f.read()

        result = client.audio_isolation.audio_isolation(audio=audio_data)

        out = temp_path()
        with open(out, "wb") as f:
            for chunk in result:
                f.write(chunk)
        return out


VOICE_PRESETS = {
    "deep": "onwK4e9ZLuTAKqWW03F9",       # Daniel
    "warm": "EXAVITQu4vr4xnSDxMaL",        # Sarah
    "dramatic": "TX3LPaxmHKxFdv7VOQHJ",    # Liam
    "narrator": "pFZP5JQG7iQjIQuC4Bku",    # Lily
}


class VoiceChangerTool(Tool):
    name = "change_voice"
    description = """Transforms the voice in a speech audio file to a different voice identity using ElevenLabs Speech-to-Speech API. Preserves the emotion, cadence, and intonation while changing the speaker. Available voice styles: 'deep' (Daniel), 'warm' (Sarah), 'dramatic' (Liam), 'narrator' (Lily). You can also pass an ElevenLabs voice_id directly."""
    inputs = {
        "audio_path": {
            "type": "string",
            "description": "Path to the input speech audio file",
        },
        "voice_style": {
            "type": "string",
            "description": "Voice style preset ('deep', 'warm', 'dramatic', 'narrator') or an ElevenLabs voice_id",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(self, audio_path: str, voice_style: str = "deep") -> str:
        from elevenlabs import ElevenLabs

        client = ElevenLabs(api_key=os.environ.get("ELEVENLABS_API_KEY"))

        voice_id = VOICE_PRESETS.get(voice_style, voice_style)

        with open(audio_path, "rb") as f:
            audio_data = f.read()

        result = client.speech_to_speech.convert(
            voice_id=voice_id,
            audio=audio_data,
            model_id="eleven_english_sts_v2",
        )

        out = temp_path()
        with open(out, "wb") as f:
            for chunk in result:
                f.write(chunk)
        return out
