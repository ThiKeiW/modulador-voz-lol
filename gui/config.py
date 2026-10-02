"""
Configuracion global del Modulador de Voz Virtual
"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent
MODELS_DIR = BASE_DIR / "models"
PRETRAINED_DIR = MODELS_DIR / "pretrained"
CUSTOM_DIR = MODELS_DIR / "custom"
ASSETS_DIR = BASE_DIR / "assets"
ICONS_DIR = ASSETS_DIR / "icons"
SOUNDS_DIR = ASSETS_DIR / "sounds"

# Audio settings
SAMPLE_RATE = 40000
CHUNK_SIZE = 1024  # ~25ms @ 40kHz. Antes era 4096 (~102ms), muy alto para el objetivo <200ms
CHANNELS = 1
AUDIO_FORMAT = "float32"

# RVC settings
DEFAULT_F0_METHOD = "rmvpe"  # rmvpe, harvest, crepe
DEFAULT_PITCH_SHIFT = 0  # semitones
MAX_PITCH_SHIFT = 12
MIN_PITCH_SHIFT = -12

# TTS settings
TTS_MODEL = "tts_models/multilingual/multi-dataset/xtts_v2"
DEFAULT_LANGUAGE = "es"  # Spanish
TTS_SAMPLE_RATE = 24000

# Device settings
DEVICE = "cuda:0" if os.environ.get("CUDA_VISIBLE_DEVICES") else "cpu"

# Pre-trained model URLs (League of Legends)
PRETRAINED_MODELS = {
    "aatrox": {
        "name": "Aatrox",
        "game": "League of Legends",
        "language": "English",
        "url": "https://huggingface.co/trinitytf/Aatrox/resolve/main/Aatrox.zip",
        "pitch_base": 0,
        "description": "Aatrox - The Darkin Blade (English RVC v2)",
        "needs_training_es": True,
    },
    "ezreal": {
        "name": "Ezreal",
        "game": "League of Legends",
        "language": "English",
        "url": "https://huggingface.co/LilYoda/ezrealLOL/resolve/main/Ezreal.zip",
        "pitch_base": 0,
        "description": "Ezreal - The Prodigal Explorer (English RVC v2)",
        "needs_training_es": True,
    },
    "briar_latino": {
        "name": "Briar",
        "game": "League of Legends",
        "language": "Español Latino",
        "url": "https://huggingface.co/Parampino/BriarLatino/resolve/main/model.pth?download=true",
        "pitch_base": 7,
        "description": "Briar - Español Latino (RVC v2, 300 epochs)",
        "needs_training_es": False,
    },
    "yuumi_latino": {
        "name": "Yuumi",
        "game": "League of Legends",
        "language": "Español Latino",
        "url": "https://huggingface.co/Parampino/BriarLatino/resolve/main/model.pth?download=true",
        "pitch_base": 0,
        "description": "Yuumi - Español Latino (RVC v2)",
        "needs_training_es": False,
    },
}

# Character metadata for GUI
CHARACTER_ICONS = {
    "aatrox": "aatrox.png",
    "ezreal": "ezreal.png",
    "briar": "briar.png",
    "yuumi": "yuumi.png",
}

# GUI settings
APP_NAME = "Voicemod LoL"
APP_VERSION = "1.0.0"
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 700
THEME_DARK = True

# Training defaults
DEFAULT_EPOCHS = 300
MIN_AUDIO_DURATION = 600  # 10 minutes recommended
MAX_AUDIO_DURATION = 1800  # 30 minutes max
TRAINING_BATCH_SIZE = 8
