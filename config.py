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
# SAMPLE_RATE es la tasa del dispositivo (mic/parlante), NO la tasa interna
# del modelo RVC (esa sale del propio .pth como tgt_sr y se resamplea sola).
SAMPLE_RATE = 48000
CHANNELS = 1
AUDIO_FORMAT = "float32"

# CHUNK_SIZE ya no se usa para el motor RVC real (ver REALTIME_* abajo,
# el tamano de bloque sale de block_ms). Queda solo como fallback para
# AudioCapture si se usa fuera del pipeline de conversion en tiempo real.
CHUNK_SIZE = 1024

# Streaming RVC en tiempo real (ver core/rvc_stream.py). Mismos defaults
# que RVC-WebUI oficial (realtime_gui.py): block 250ms, crossfade SOLA 50ms,
# contexto extra 2500ms para calidad del hubert/f0 (no es latencia de espera,
# es historial ya cacheado). Latencia real por bloque ~ block_ms + computo.
REALTIME_BLOCK_MS = 250
REALTIME_CROSSFADE_MS = 50
REALTIME_EXTRA_MS = 2500

# RVC settings
DEFAULT_F0_METHOD = "rmvpe"  # rmvpe (recomendado, requiere rmvpe.pt), pm, harvest
DEFAULT_PITCH_SHIFT = 0  # semitones
MAX_PITCH_SHIFT = 12
MIN_PITCH_SHIFT = -12
DEFAULT_INDEX_RATE = 0.5  # 0 = sin retrieval por indice, 1 = maximo

# Assets compartidos de inferencia (no son parte de ningun personaje):
# formato Transformers (NO el .pt original de fairseq), descargar con
# scripts/download_assets.py desde huggingface.co/lj1995/VoiceConversionWebUI
HUBERT_DIR = MODELS_DIR / "hubert_base"
RMVPE_PATH = MODELS_DIR / "rmvpe" / "rmvpe.pt"

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
