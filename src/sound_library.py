"""Sound library/catalog system for curated audio samples.

Provides a browsable collection of sounds organized by category,
with metadata for each sound (duration, sample rate, tags, etc.).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterator
import numpy as np
import soundfile as sf

from .utils_audio import load_waveform, to_mono, resample_audio, normalize_wave


@dataclass
class SoundMetadata:
    """Metadata for a sound in the library."""
    id: str
    name: str
    description: str
    category: str
    path: str
    duration: float
    sample_rate: int
    tags: list[str]
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, d: dict) -> SoundMetadata:
        return cls(**d)


# Default curated sounds library - expanded with diverse categories
DEFAULT_LIBRARY = {
    # ═══════════════════════════════════════════════════════════════════════════
    # MECHANICAL / INDUSTRIAL
    # ═══════════════════════════════════════════════════════════════════════════
    "boat_motor": {
        "name": "Boat Motor",
        "description": "Rhythmic mechanical chugging with rich harmonic content",
        "category": "mechanical",
        "tags": ["rhythmic", "mechanical", "engine", "percussive"],
    },
    "helicopter": {
        "name": "Helicopter",
        "description": "Rhythmic helicopter blades with pulsing character",
        "category": "mechanical",
        "tags": ["rhythmic", "mechanical", "pulsing", "heavy"],
    },
    "typewriter": {
        "name": "Typewriter",
        "description": "Mechanical typing with rhythmic percussive clicks",
        "category": "mechanical",
        "tags": ["rhythmic", "mechanical", "clicks", "percussive"],
    },
    "train": {
        "name": "Train",
        "description": "Train wheels on tracks with rhythmic clicking",
        "category": "mechanical",
        "tags": ["rhythmic", "mechanical", "train", "wheels"],
    },
    "clock_ticking": {
        "name": "Clock Ticking",
        "description": "Steady clock mechanism with pendulum swing",
        "category": "mechanical",
        "tags": ["rhythmic", "steady", "ticking", "clock"],
    },
    "gears_grinding": {
        "name": "Gears Grinding",
        "description": "Metal gears meshing and grinding",
        "category": "mechanical",
        "tags": ["grinding", "metal", "industrial", "harsh"],
    },
    "jackhammer": {
        "name": "Jackhammer",
        "description": "Rapid percussive construction tool",
        "category": "mechanical",
        "tags": ["percussive", "rapid", "construction", "noise"],
    },
    "printing_press": {
        "name": "Printing Press",
        "description": "Industrial printing machinery in operation",
        "category": "mechanical",
        "tags": ["rhythmic", "industrial", "printing", "machine"],
    },
    "sewing_machine": {
        "name": "Sewing Machine",
        "description": "Fast rhythmic needle movements",
        "category": "mechanical",
        "tags": ["fast", "rhythmic", "needle", "rapid"],
    },
    "washing_machine": {
        "name": "Washing Machine",
        "description": "Drum rotation with sloshing water",
        "category": "mechanical",
        "tags": ["rotation", "water", "sloshing", "cycle"],
    },
    "vacuum_cleaner": {
        "name": "Vacuum Cleaner",
        "description": "High-speed motor with air suction",
        "category": "mechanical",
        "tags": ["motor", "air", "suction", "whir"],
    },
    "chainsaw": {
        "name": "Chainsaw",
        "description": "Two-stroke engine with chain noise",
        "category": "mechanical",
        "tags": ["engine", "buzzy", "aggressive", "loud"],
    },
    "submarine_sonar": {
        "name": "Submarine Sonar",
        "description": "Underwater ping with reverb decay",
        "category": "mechanical",
        "tags": ["ping", "underwater", "reverb", "naval"],
    },
    
    # ═══════════════════════════════════════════════════════════════════════════
    # INSTRUMENTS - STRINGS
    # ═══════════════════════════════════════════════════════════════════════════
    "piano": {
        "name": "Piano",
        "description": "Clean acoustic piano with rich harmonic overtones",
        "category": "instruments",
        "tags": ["melodic", "acoustic", "harmonic", "musical"],
    },
    "violin": {
        "name": "Violin",
        "description": "String instrument with rich bow harmonics",
        "category": "instruments",
        "tags": ["string", "bowed", "expressive", "harmonic"],
    },
    "cello": {
        "name": "Cello",
        "description": "Deep resonant bowed strings",
        "category": "instruments",
        "tags": ["string", "bowed", "deep", "resonant"],
    },
    "guitar": {
        "name": "Acoustic Guitar",
        "description": "Plucked strings with wooden body resonance",
        "category": "instruments",
        "tags": ["plucked", "string", "wooden", "folk"],
    },
    "electric_guitar": {
        "name": "Electric Guitar",
        "description": "Distorted or clean electric guitar tones",
        "category": "instruments",
        "tags": ["electric", "distorted", "rock", "solo"],
    },
    "harp": {
        "name": "Harp",
        "description": "Plucked strings with celestial quality",
        "category": "instruments",
        "tags": ["plucked", "celestial", "angelic", "glissando"],
    },
    "banjo": {
        "name": "Banjo",
        "description": "Bright plucked strings with resonant head",
        "category": "instruments",
        "tags": ["plucked", "bright", "folk", "country"],
    },
    "sitar": {
        "name": "Sitar",
        "description": "Indian plucked string with sympathetic resonance",
        "category": "instruments",
        "tags": ["plucked", "indian", "exotic", "drone"],
    },
    
    # ═══════════════════════════════════════════════════════════════════════════
    # INSTRUMENTS - WIND
    # ═══════════════════════════════════════════════════════════════════════════
    "flute": {
        "name": "Flute",
        "description": "Breathy woodwind tone with soft attack",
        "category": "instruments",
        "tags": ["breathy", "woodwind", "soft", "airy"],
    },
    "saxophone": {
        "name": "Saxophone",
        "description": "Brassy reed instrument with warm tone",
        "category": "instruments",
        "tags": ["brassy", "reed", "warm", "jazz"],
    },
    "trumpet": {
        "name": "Trumpet",
        "description": "Bright brass with piercing attack",
        "category": "instruments",
        "tags": ["brass", "bright", "piercing", "fanfare"],
    },
    "clarinet": {
        "name": "Clarinet",
        "description": "Warm single-reed woodwind",
        "category": "instruments",
        "tags": ["reed", "woodwind", "warm", "classical"],
    },
    "oboe": {
        "name": "Oboe",
        "description": "Nasal double-reed with distinct timbre",
        "category": "instruments",
        "tags": ["reed", "nasal", "distinct", "classical"],
    },
    "pan_flute": {
        "name": "Pan Flute",
        "description": "Breathy pipes with Andean character",
        "category": "instruments",
        "tags": ["breathy", "pipes", "andean", "world"],
    },
    "didgeridoo": {
        "name": "Didgeridoo",
        "description": "Low drone with complex overtones",
        "category": "instruments",
        "tags": ["drone", "low", "australian", "overtones"],
    },
    "harmonica": {
        "name": "Harmonica",
        "description": "Reed instrument with vocal quality",
        "category": "instruments",
        "tags": ["reed", "blues", "folk", "portable"],
    },
    
    # ═══════════════════════════════════════════════════════════════════════════
    # INSTRUMENTS - KEYS/SYNTH
    # ═══════════════════════════════════════════════════════════════════════════
    "rhodes_piano": {
        "name": "Rhodes Piano",
        "description": "Electric piano with bell-like tone",
        "category": "instruments",
        "tags": ["electric", "bell", "jazz", "funk"],
    },
    "hammond_organ": {
        "name": "Hammond Organ",
        "description": "Vintage tonewheel organ with drawbars",
        "category": "instruments",
        "tags": ["organ", "gospel", "jazz", "classic"],
    },
    "accordion": {
        "name": "Accordion",
        "description": "Squeezing bellows with reeds",
        "category": "instruments",
        "tags": ["bellows", "folk", "polka", "french"],
    },
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SYNTHETIC/ELECTRONIC
    # ═══════════════════════════════════════════════════════════════════════════
    "saw_wave": {
        "name": "Saw Wave",
        "description": "Bright, buzzy sawtooth wave synthesis",
        "category": "synthetic",
        "tags": ["buzzy", "bright", "electronic", "harmonic"],
    },
    "square_wave": {
        "name": "Square Wave",
        "description": "Hollow flute-like synthesizer tone",
        "category": "synthetic",
        "tags": ["hollow", "chiptune", "8-bit", "retro"],
    },
    "sine_wave": {
        "name": "Sine Wave",
        "description": "Pure tone with no harmonics",
        "category": "synthetic",
        "tags": ["pure", "clean", "sub", "bass"],
    },
    "synth_pad": {
        "name": "Synth Pad",
        "description": "Ethereal synthesizer pad with slow attack",
        "category": "synthetic",
        "tags": ["ambient", "electronic", "evolving", "smooth"],
    },
    "fm_bass": {
        "name": "FM Bass",
        "description": "Sharp attack FM synthesis bass",
        "category": "synthetic",
        "tags": ["fm", "bass", "sharp", "digital"],
    },
    "analog_lead": {
        "name": "Analog Lead",
        "description": "Fat analog synthesizer lead",
        "category": "synthetic",
        "tags": ["analog", "fat", "solo", "electronic"],
    },
    "vocoder": {
        "name": "Vocoder",
        "description": "Robot voice effect with carrier",
        "category": "synthetic",
        "tags": ["robot", "voice", "talking", "electronic"],
    },
    "bit_crushed": {
        "name": "Bit Crushed",
        "description": "Low bit-rate digital distortion",
        "category": "synthetic",
        "tags": ["digital", "lo-fi", "distortion", "8-bit"],
    },
    "noise_sweep": {
        "name": "Noise Sweep",
        "description": "Filtered noise riser or fall",
        "category": "synthetic",
        "tags": ["sweep", "riser", "effect", "transition"],
    },
    "laser_zap": {
        "name": "Laser Zap",
        "description": "Descending pitch electronic zap",
        "category": "synthetic",
        "tags": ["zap", "sci-fi", "effect", "descending"],
    },
    "sub_drop": {
        "name": "Sub Drop",
        "description": "Low frequency impact for drops",
        "category": "synthetic",
        "tags": ["sub", "drop", "impact", "edm"],
    },
    "arpeggio": {
        "name": "Arpeggio",
        "description": "Cycling pattern of held notes",
        "category": "synthetic",
        "tags": ["pattern", "cycling", "trance", "electronic"],
    },
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PERCUSSION
    # ═══════════════════════════════════════════════════════════════════════════
    "drums": {
        "name": "Drum Kit",
        "description": "Acoustic drum kit with punchy transients",
        "category": "percussion",
        "tags": ["rhythmic", "percussive", "punchy", "transient"],
    },
    "bongo_drums": {
        "name": "Bongo Drums",
        "description": "Hand drums with hollow tone",
        "category": "percussion",
        "tags": ["hand", "hollow", "latin", "rhythmic"],
    },
    "djembe": {
        "name": "Djembe",
        "description": "African goblet drum with rich tone",
        "category": "percussion",
        "tags": ["african", "goblet", "rich", "hand"],
    },
    "tambourine": {
        "name": "Tambourine",
        "description": "Jingles with struck frame",
        "category": "percussion",
        "tags": ["jingles", "bright", "shaking", "folk"],
    },
    "cymbal_crash": {
        "name": "Cymbal Crash",
        "description": "Metallic crash with long decay",
        "category": "percussion",
        "tags": ["metallic", "crash", "decay", "bright"],
    },
    "gong": {
        "name": "Gong",
        "description": "Large metal plate with complex harmonics",
        "category": "percussion",
        "tags": ["metal", "complex", "asian", "ceremonial"],
    },
    "steel_drums": {
        "name": "Steel Drums",
        "description": "Caribbean tuned percussion",
        "category": "percussion",
        "tags": ["caribbean", "tuned", "island", "melodic"],
    },
    "timbales": {
        "name": "Timbales",
        "description": "Shallow metal drums with rim shots",
        "category": "percussion",
        "tags": ["cuban", "metal", "rim", "latin"],
    },
    "snare_roll": {
        "name": "Snare Roll",
        "description": "Marching snare with buzz roll",
        "category": "percussion",
        "tags": ["marching", "roll", "buzz", "military"],
    },
    "kick_drum": {
        "name": "Kick Drum",
        "description": "Deep bass drum thump",
        "category": "percussion",
        "tags": ["bass", "thump", "beat", "foundation"],
    },
    "hi_hat": {
        "name": "Hi-Hat",
        "description": "Metallic cymbal chick and sizzle",
        "category": "percussion",
        "tags": ["metallic", "chick", "sizzle", "time"],
    },
    "congas": {
        "name": "Congas",
        "description": "Tall narrow Cuban drums",
        "category": "percussion",
        "tags": ["cuban", "tall", "slap", "latin"],
    },
    "maracas": {
        "name": "Maracas",
        "description": "Shaken seeds in hollow container",
        "category": "percussion",
        "tags": ["shaken", "seeds", "rhythmic", "latin"],
    },
    "wood_block": {
        "name": "Wood Block",
        "description": "Hollow wooden percussion",
        "category": "percussion",
        "tags": ["wood", "hollow", "clack", "simple"],
    },
    "triangle": {
        "name": "Triangle",
        "description": "High pitched metallic ring",
        "category": "percussion",
        "tags": ["high", "metallic", "ring", "orchestral"],
    },
    
    # ═══════════════════════════════════════════════════════════════════════════
    # NATURE - WEATHER
    # ═══════════════════════════════════════════════════════════════════════════
    "ocean_waves": {
        "name": "Ocean Waves",
        "description": "Gentle ocean waves with natural white noise",
        "category": "nature",
        "tags": ["ambient", "natural", "calm", "noise"],
    },
    "thunder": {
        "name": "Thunder",
        "description": "Deep rumbling thunder with low-frequency energy",
        "category": "nature",
        "tags": ["rumble", "deep", "impact", "low-freq"],
    },
    "rain": {
        "name": "Rain",
        "description": "Steady rainfall with textured white noise",
        "category": "nature",
        "tags": ["ambient", "natural", "texture", "noise"],
    },
    "wind": {
        "name": "Wind",
        "description": "Howling wind with spectral movement",
        "category": "nature",
        "tags": ["ambient", "natural", "moving", "spectral"],
    },
    "heavy_storm": {
        "name": "Heavy Storm",
        "description": "Intense rain with thunder cracks",
        "category": "nature",
        "tags": ["intense", "thunder", "rain", "dramatic"],
    },
    "snow_blizzard": {
        "name": "Snow Blizzard",
        "description": "Howling wind with snow particles",
        "category": "nature",
        "tags": ["cold", "howling", "winter", "frozen"],
    },
    
    # ═══════════════════════════════════════════════════════════════════════════
    # NATURE - ANIMALS
    # ═══════════════════════════════════════════════════════════════════════════
    "birds": {
        "name": "Birds",
        "description": "Birdsong with melodic chirping patterns",
        "category": "nature",
        "tags": ["melodic", "natural", "light", "airy"],
    },
    "cicadas": {
        "name": "Cicadas",
        "description": "Summer insect drone",
        "category": "nature",
        "tags": ["drone", "summer", "insect", "buzzy"],
    },
    "crickets": {
        "name": "Crickets",
        "description": "Rhythmic night chirping",
        "category": "nature",
        "tags": ["rhythmic", "night", "chirp", "calm"],
    },
    "wolf_howl": {
        "name": "Wolf Howl",
        "description": "Long mournful wolf call",
        "category": "nature",
        "tags": ["mournful", "long", "wild", "spooky"],
    },
    "elephant_trumpet": {
        "name": "Elephant Trumpet",
        "description": "Powerful elephant vocalization",
        "category": "nature",
        "tags": ["powerful", "trumpet", "wild", "massive"],
    },
    "whale_song": {
        "name": "Whale Song",
        "description": "Deep underwater whale vocalizations",
        "category": "nature",
        "tags": ["deep", "underwater", "mysterious", "vast"],
    },
    "dolphin_clicks": {
        "name": "Dolphin Clicks",
        "description": "High frequency echolocation clicks",
        "category": "nature",
        "tags": ["clicks", "echolocation", "marine", "smart"],
    },
    "frogs": {
        "name": "Frogs",
        "description": "Wetland frog chorus",
        "category": "nature",
        "tags": ["wetland", "chorus", "croak", "swamp"],
    },
    "bees": {
        "name": "Bees",
        "description": "Hive buzzing and humming",
        "category": "nature",
        "tags": ["buzzing", "hive", "busy", "harmonic"],
    },
    "horse_gallop": {
        "name": "Horse Gallop",
        "description": "Rhythmic hoof beats",
        "category": "nature",
        "tags": ["rhythmic", "hoof", "western", "fast"],
    },
    
    # ═══════════════════════════════════════════════════════════════════════════
    # NATURE - ENVIRONMENT
    # ═══════════════════════════════════════════════════════════════════════════
    "waterfall": {
        "name": "Waterfall",
        "description": "Rushing water with white noise",
        "category": "nature",
        "tags": ["rushing", "water", "power", "noise"],
    },
    "stream": {
        "name": "Stream",
        "description": "Gentle babbling brook",
        "category": "nature",
        "tags": ["gentle", "babbling", "peaceful", "water"],
    },
    "fire_crackling": {
        "name": "Fire Crackling",
        "description": "Wood fire with snaps and pops",
        "category": "nature",
        "tags": ["crackling", "snaps", "warm", "camp"],
    },
    "leaves_rustling": {
        "name": "Leaves Rustling",
        "description": "Wind through dry leaves",
        "category": "nature",
        "tags": ["rustling", "wind", "autumn", "gentle"],
    },
    "avalanche": {
        "name": "Avalanche",
        "description": "Snow rumbling down mountain",
        "category": "nature",
        "tags": ["rumbling", "snow", "danger", "massive"],
    },
    "earthquake_rumble": {
        "name": "Earthquake Rumble",
        "description": "Deep ground shaking",
        "category": "nature",
        "tags": ["deep", "shaking", "ground", "sub"],
    },
    "volcano_eruption": {
        "name": "Volcano Eruption",
        "description": "Explosive volcanic blast",
        "category": "nature",
        "tags": ["explosive", "blast", "power", "destruction"],
    },
    
    # ═══════════════════════════════════════════════════════════════════════════
    # HUMAN / VOCAL
    # ═══════════════════════════════════════════════════════════════════════════
    "choir_aah": {
        "name": "Choir Aah",
        "description": "Choir singing sustained ah vowel",
        "category": "vocal",
        "tags": ["choir", "sustained", "heavenly", "chord"],
    },
    "whispering": {
        "name": "Whispering",
        "description": "Soft breathy whisper",
        "category": "vocal",
        "tags": ["soft", "breathy", "intimate", "quiet"],
    },
    "beatbox": {
        "name": "Beatbox",
        "description": "Vocal percussion rhythms",
        "category": "vocal",
        "tags": ["percussion", "vocal", "rhythmic", "hip-hop"],
    },
    "opera_singer": {
        "name": "Opera Singer",
        "description": "Trained operatic voice with vibrato",
        "category": "vocal",
        "tags": ["operatic", "vibrato", "classical", "powerful"],
    },
    "tuvan_throat": {
        "name": "Tuvan Throat Singing",
        "description": "Overtone singing with drone",
        "category": "vocal",
        "tags": ["overtone", "drone", "mongolian", "unique"],
    },
    "children_laughing": {
        "name": "Children Laughing",
        "description": "Playful child giggles",
        "category": "vocal",
        "tags": ["playful", "giggles", "happy", "light"],
    },
    "crowd_cheering": {
        "name": "Crowd Cheering",
        "description": "Stadium crowd applause",
        "category": "vocal",
        "tags": ["stadium", "applause", "energy", "celebration"],
    },
    "baby_crying": {
        "name": "Baby Crying",
        "description": "Infant vocal distress",
        "category": "vocal",
        "tags": ["infant", "distress", "high", "emotional"],
    },
    "scream": {
        "name": "Scream",
        "description": "Human scream of terror",
        "category": "vocal",
        "tags": ["terror", "high", "intense", "horror"],
    },
    
    # ═══════════════════════════════════════════════════════════════════════════
    # URBAN / CITY
    # ═══════════════════════════════════════════════════════════════════════════
    "traffic": {
        "name": "City Traffic",
        "description": "Cars passing with Doppler effect",
        "category": "urban",
        "tags": ["cars", "doppler", "city", "busy"],
    },
    "subway_train": {
        "name": "Subway Train",
        "description": "Underground train with screech",
        "category": "urban",
        "tags": ["underground", "screech", "metal", "transit"],
    },
    "construction": {
        "name": "Construction Site",
        "description": "Building with machinery noise",
        "category": "urban",
        "tags": ["building", "machinery", "noise", "industrial"],
    },
    "police_siren": {
        "name": "Police Siren",
        "description": "Emergency vehicle wailing",
        "category": "urban",
        "tags": ["emergency", "wailing", "urgent", "alarm"],
    },
    "street_footsteps": {
        "name": "Street Footsteps",
        "description": "People walking on pavement",
        "category": "urban",
        "tags": ["walking", "pavement", "crowd", "urban"],
    },
    "coffee_shop": {
        "name": "Coffee Shop",
        "description": "Muffled conversation and cups",
        "category": "urban",
        "tags": ["muffled", "conversation", "cafe", "ambient"],
    },
    "skateboard": {
        "name": "Skateboard",
        "description": "Wheels and board tricks",
        "category": "urban",
        "tags": ["wheels", "tricks", "youth", "street"],
    },
    "basketball_dribble": {
        "name": "Basketball Dribble",
        "description": "Ball bouncing on court",
        "category": "urban",
        "tags": ["bouncing", "court", "rhythmic", "sports"],
    },
    
    # ═══════════════════════════════════════════════════════════════════════════
    # FX / ATMOSPHERIC
    # ═══════════════════════════════════════════════════════════════════════════
    "vinyl_scratch": {
        "name": "Vinyl Scratch",
        "description": "Record scratching effect",
        "category": "fx",
        "tags": ["scratch", "dj", "hip-hop", "rhythmic"],
    },
    "tape_rewind": {
        "name": "Tape Rewind",
        "description": "Cassette fast rewind",
        "category": "fx",
        "tags": ["rewind", "cassette", "vintage", "fast"],
    },
    "radio_static": {
        "name": "Radio Static",
        "description": "Tuning between stations",
        "category": "fx",
        "tags": ["static", "tuning", "noise", "vintage"],
    },
    "glass_breaking": {
        "name": "Glass Breaking",
        "description": "Shattering glass shards",
        "category": "fx",
        "tags": ["shattering", "sharp", "impact", "fragile"],
    },
    "sword_clash": {
        "name": "Sword Clash",
        "description": "Metal swords striking",
        "category": "fx",
        "tags": ["metal", "strike", "medieval", "sharp"],
    },
    "gunshot": {
        "name": "Gunshot",
        "description": "Sharp explosive firearm",
        "category": "fx",
        "tags": ["explosive", "sharp", "impact", "violent"],
    },
    "explosion": {
        "name": "Explosion",
        "description": "Large blast with debris",
        "category": "fx",
        "tags": ["blast", "debris", "massive", "impact"],
    },
    "heart_beat": {
        "name": "Heart Beat",
        "description": "Rhythmic pulse thump",
        "category": "fx",
        "tags": ["pulse", "rhythmic", "thump", "body"],
    },
    "breathing": {
        "name": "Breathing",
        "description": "Human breath in and out",
        "category": "fx",
        "tags": ["breath", "rhythmic", "quiet", "life"],
    },
    "phone_vibrate": {
        "name": "Phone Vibrate",
        "description": "Mobile phone buzzing",
        "category": "fx",
        "tags": ["buzzing", "mobile", "modern", "quiet"],
    },
    "door_creak": {
        "name": "Door Creak",
        "description": "Hinge squeak open",
        "category": "fx",
        "tags": ["squeak", "hinge", "horror", "wood"],
    },
    "bubble_pop": {
        "name": "Bubble Pop",
        "description": "Underwater bubble bursting",
        "category": "fx",
        "tags": ["burst", "water", "cartoon", "light"],
    },
    "whoosh": {
        "name": "Whoosh",
        "description": "Fast air movement",
        "category": "fx",
        "tags": ["fast", "air", "transition", "swish"],
    },
    "bell_ring": {
        "name": "Bell Ring",
        "description": "Church or school bell",
        "category": "fx",
        "tags": ["ring", "metal", "decay", "alert"],
    },
    "clock_chime": {
        "name": "Clock Chime",
        "description": "Grandfather clock bell",
        "category": "fx",
        "tags": ["chime", "bell", "time", "classic"],
    },
    "squeaky_toy": {
        "name": "Squeaky Toy",
        "description": "Rubber toy squeeze",
        "category": "fx",
        "tags": ["squeak", "rubber", "cartoon", "funny"],
    },
    "paper_tear": {
        "name": "Paper Tear",
        "description": "Ripping paper sheet",
        "category": "fx",
        "tags": ["rip", "paper", "sharp", "quick"],
    },
    "camera_shutter": {
        "name": "Camera Shutter",
        "description": "Mechanical camera click",
        "category": "fx",
        "tags": ["click", "mechanical", "photo", "precise"],
    },
}


class SoundLibrary:
    """Manages a catalog of curated audio samples."""
    
    def __init__(self, library_dir: Path | str = "data/sound_library"):
        self.library_dir = Path(library_dir)
        self.index_file = self.library_dir / "index.json"
        self._index: dict[str, SoundMetadata] = {}
        self._load_index()
    
    def _load_index(self) -> None:
        """Load the library index from disk."""
        if self.index_file.exists():
            data = json.loads(self.index_file.read_text())
            self._index = {
                k: SoundMetadata.from_dict(v) 
                for k, v in data.get("sounds", {}).items()
            }
    
    def _save_index(self) -> None:
        """Save the library index to disk."""
        self.library_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "sounds": {k: v.to_dict() for k, v in self._index.items()},
            "categories": self.get_categories(),
        }
        self.index_file.write_text(json.dumps(data, indent=2))
    
    def add_sound(
        self,
        sound_id: str,
        audio_path: Path | str,
        name: str | None = None,
        description: str = "",
        category: str = "uncategorized",
        tags: list[str] | None = None,
        target_sr: int = 22050,
    ) -> SoundMetadata:
        """Add a sound to the library.
        
        Args:
            sound_id: Unique identifier for the sound
            audio_path: Path to the audio file
            name: Display name (defaults to sound_id)
            description: Description of the sound
            category: Category for grouping
            tags: List of searchable tags
            target_sr: Target sample rate for storage
            
        Returns:
            SoundMetadata for the added sound
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Load and normalize audio
        audio, sr = sf.read(audio_path, always_2d=False)
        audio = to_mono(audio)
        audio = resample_audio(audio, sr, target_sr)
        audio = normalize_wave(audio)
        
        # Save to library directory
        lib_path = self.library_dir / "audio" / f"{sound_id}.wav"
        lib_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(lib_path, audio, target_sr)
        
        # Create metadata
        duration = len(audio) / target_sr
        meta = SoundMetadata(
            id=sound_id,
            name=name or sound_id.replace("_", " ").title(),
            description=description,
            category=category,
            path=str(lib_path.relative_to(self.library_dir)),
            duration=duration,
            sample_rate=target_sr,
            tags=tags or [],
        )
        
        self._index[sound_id] = meta
        self._save_index()
        return meta
    
    def get_sound(self, sound_id: str) -> SoundMetadata | None:
        """Get metadata for a specific sound."""
        return self._index.get(sound_id)
    
    def load_audio(self, sound_id: str, target_sr: int | None = None) -> np.ndarray:
        """Load the audio data for a sound.
        
        Args:
            sound_id: The sound identifier
            target_sr: Optional target sample rate (defaults to stored rate)
            
        Returns:
            Audio array as float32
        """
        meta = self._index.get(sound_id)
        if meta is None:
            raise KeyError(f"Sound not found: {sound_id}")
        
        # Try library directory first, then relative to repo root
        audio_path = self.library_dir / meta.path
        if not audio_path.exists():
            # Try relative to repo root
            audio_path = Path(meta.path)
        
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        audio, sr = sf.read(audio_path, always_2d=False)
        audio = to_mono(audio)
        
        if target_sr is not None and target_sr != sr:
            audio = resample_audio(audio, sr, target_sr)
            sr = target_sr
        
        return audio.astype(np.float32)
    
    def list_sounds(
        self,
        category: str | None = None,
        tag: str | None = None,
    ) -> list[SoundMetadata]:
        """List sounds with optional filtering.
        
        Args:
            category: Filter by category
            tag: Filter by tag
            
        Returns:
            List of matching SoundMetadata
        """
        results = list(self._index.values())
        
        if category:
            results = [s for s in results if s.category == category]
        
        if tag:
            results = [s for s in results if tag in s.tags]
        
        return results
    
    def get_categories(self) -> list[str]:
        """Get all unique categories in the library."""
        categories = set(s.category for s in self._index.values())
        return sorted(categories)
    
    def get_tags(self) -> list[str]:
        """Get all unique tags in the library."""
        tags = set()
        for s in self._index.values():
            tags.update(s.tags)
        return sorted(tags)
    
    def search(self, query: str) -> list[SoundMetadata]:
        """Search sounds by name, description, or tags.
        
        Args:
            query: Search query string
            
        Returns:
            List of matching SoundMetadata
        """
        query = query.lower()
        results = []
        
        for s in self._index.values():
            if (query in s.name.lower() or 
                query in s.description.lower() or
                any(query in t.lower() for t in s.tags)):
                results.append(s)
        
        return results
    
    def remove_sound(self, sound_id: str) -> bool:
        """Remove a sound from the library.
        
        Args:
            sound_id: The sound to remove
            
        Returns:
            True if removed, False if not found
        """
        if sound_id not in self._index:
            return False
        
        meta = self._index.pop(sound_id)
        audio_path = self.library_dir / meta.path
        
        if audio_path.exists():
            audio_path.unlink()
        
        self._save_index()
        return True
    
    def __len__(self) -> int:
        return len(self._index)
    
    def __iter__(self) -> Iterator[SoundMetadata]:
        return iter(self._index.values())
    
    def __contains__(self, sound_id: str) -> bool:
        return sound_id in self._index


# Global library instance
_library: SoundLibrary | None = None


def get_library(library_dir: Path | str | None = None) -> SoundLibrary:
    """Get the global sound library instance.
    
    Args:
        library_dir: Optional directory path (uses default if not specified)
        
    Returns:
        SoundLibrary instance
    """
    global _library
    if _library is None or library_dir is not None:
        _library = SoundLibrary(library_dir or "data/sound_library")
    return _library


def load_instrument_dataset(data_dir: Path | str = "data/good_sounds_pairs") -> SoundLibrary:
    """Load the instrument recordings dataset as a sound library.
    
    This reads the metadata.json from the good_sounds_pairs dataset
    and creates a sound library from the unique instrument styles.
    
    Args:
        data_dir: Directory containing metadata.json
        
    Returns:
        SoundLibrary populated with instrument recordings
    """
    data_dir = Path(data_dir)
    lib = get_library("data/sound_library")
    
    metadata_file = data_dir / "metadata.json"
    if not metadata_file.exists():
        print(f"Warning: Metadata file not found at {metadata_file}")
        return lib
    
    try:
        data = json.loads(metadata_file.read_text())
        
        # Extract unique styles and their file paths
        styles: dict[str, list[str]] = {}
        for entry in data:
            style = entry.get("style", "unknown")
            output_path = entry.get("output", "")
            
            if style not in styles:
                styles[style] = []
            if output_path and output_path not in styles[style]:
                styles[style].append(output_path)
        
        # Create metadata for each unique style
        for style, files in styles.items():
            if style not in lib:
                # Clean up style name for display
                name = style.replace("_", " ").title()
                
                # Determine category based on style
                category = "instruments"
                if any(x in style.lower() for x in ["drum", "perc", "kick", "snare"]):
                    category = "percussion"
                elif any(x in style.lower() for x in ["synth", "pad", "bass"]):
                    category = "synthetic"
                
                # Create metadata pointing to the first available file
                # Note: actual file paths are relative to the data directory
                meta = SoundMetadata(
                    id=style,
                    name=name,
                    description=f"Recorded {name} samples from instrument dataset",
                    category=category,
                    path=str(data_dir / files[0]) if files else f"audio/{style}.wav",
                    duration=0.0,  # Will be calculated when loaded
                    sample_rate=22050,
                    tags=[style.lower(), "recorded", category],
                )
                lib._index[style] = meta
        
        lib._save_index()
        print(f"Loaded {len(styles)} instrument styles from dataset")
        
    except Exception as e:
        print(f"Error loading instrument dataset: {e}")
    
    return lib


def init_default_library(library_dir: Path | str | None = None) -> SoundLibrary:
    """Initialize the library with default sounds and instrument dataset.
    
    This creates placeholder entries for the default library and also
    attempts to load the instrument recordings dataset if available.
    
    Args:
        library_dir: Optional directory path
        
    Returns:
        Initialized SoundLibrary
    """
    lib = get_library(library_dir)
    
    # Add default curated sounds
    for sound_id, info in DEFAULT_LIBRARY.items():
        if sound_id not in lib:
            meta = SoundMetadata(
                id=sound_id,
                name=info["name"],
                description=info["description"],
                category=info["category"],
                path=f"audio/{sound_id}.wav",
                duration=0.0,
                sample_rate=22050,
                tags=info["tags"],
            )
            lib._index[sound_id] = meta
    
    # Try to load instrument dataset
    lib = load_instrument_dataset("data/good_sounds_pairs")
    
    lib._save_index()
    return lib
