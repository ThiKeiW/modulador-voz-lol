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
REALTIME_BLOCK_MS = 200  # 150 dejaba el COMPUTO sobrado (130-140ms) pero
                          # el LOOP completo (poll de cola + write() +
                          # overhead de Python/GIL, no solo el modelo) con
                          # margen casi cero contra el budget -> cortes
                          # medidos uno por bloque (ver waveform). 200 es
                          # punto medio entre el 250 que se sentia lento y
                          # el 150 que cortaba.
REALTIME_CROSSFADE_MS = 80  # subido de 50; mas blend entre bloques =
                             # transiciones menos abruptas/roboticas
# OJO: esto NO es "esperar 2500ms" -- es cuanto historial de audio se le
# vuelve a pasar a hubert+sintetizador en CADA bloque (no hay cache
# incremental, se reprocesa toda la ventana extra+crossfade+block de
# nuevo cada vez). Mas extra = mejor calidad/continuidad, pero el costo
# de computo escala con esto. En una GPU de gama baja (ej. GTX 16xx,
# fp16 deshabilitado por gpu_rules.py) es el primer lugar para bajar
# latencia. Valores tipicos 1000-1500ms en GPUs chicas, hasta 2500-5000ms
# en GPUs grandes. Si sigue lento, probar bajar a 500-800.
REALTIME_EXTRA_MS = 1000

# RVC settings
DEFAULT_F0_METHOD = "rmvpe"  # rmvpe (recomendado, requiere rmvpe.pt), pm, harvest
DEFAULT_PITCH_SHIFT = 0  # semitones
MAX_PITCH_SHIFT = 12
MIN_PITCH_SHIFT = -12
DEFAULT_INDEX_RATE = 0.5  # 0 = sin retrieval por indice, 1 = maximo

# Silence gate (VAD simple por RMS) en ConversionThread: si el bloque de
# entrada esta por debajo del umbral, se emite silencio directo SIN pasar
# por hubert/f0/synth. En una prueba tipica ~80% de los bloques son
# silencio (mic RMS 0.0000-0.0005 vs voz 0.003-0.015); sin gate cada uno
# cuesta el computo completo (~660ms en CPU) y el atraso se acumula.
# Al retomar voz se hace stream.reset() para no arrastrar estado viejo.
SILENCE_GATE_ENABLED = True
SILENCE_RMS_THRESHOLD = 0.002  # subir si el micro tiene mas ruido de fondo

# Imprime cuanto tarda cada etapa (hubert/f0/sintetizador/indice) por
# bloque en consola. Prender mientras se ajusta latencia, apagar despues
# (agrega print() por bloque).
PROFILE_RVC = False

# Salida de audio (core/audio_output.py). El hilo de conversion hace push()
# sin bloquear y un callback de PortAudio consume.
# - OUTPUT_PREFILL_MS: colchon de silencio antes del primer bloque (y
#   tras cada underrun). Absorbe el jitter del computo (~135-200ms por
#   bloque de 200ms). Mas alto = menos huecos, pero suma latencia 1:1.
#   Medido en llamada real: con 60ms aparecian huecos de 80-120ms en
#   mitad de palabra (picos de computo). 250ms los absorbe.
# - OUTPUT_MAX_BUFFER_MS: tope; si se acumula mas, se tira lo mas viejo.
# - OUTPUT_LATENCY: buffer interno de PortAudio (s).
OUTPUT_PREFILL_MS = 250
OUTPUT_MAX_BUFFER_MS = 800
OUTPUT_LATENCY = 0.05

# Drenaje de latencia (core/conversion_thread.py): si el buffer de salida
# acumula mas de OUTPUT_PREFILL_MS + OUTPUT_TRIM_SLACK_MS (pasa cuando un
# pico de calculo hace que el hilo "se ponga al dia" mas rapido que tiempo
# real), se acorta el silencio de las pausas hasta volver al colchon. Solo
# toca bloques que el silence-gate ya marco como silencio: no altera voz.
OUTPUT_TRIM_SLACK_MS = 40

# torch.backends.cudnn.benchmark: elige el algoritmo de convolucion mas
# rapido para los tamanos fijos de nuestras ventanas (se calibra en el
# warmup). Resultado numerico equivalente. Si no mejora el computo por
# bloque (medir con PROFILE_RVC=True) se puede apagar.
CUDNN_BENCHMARK = True

# EXPERIMENTO (opt-in): durante el silencio el gate no usa la GPU y el
# primer bloque con voz tras una pausa tarda ~300-415ms (vs ~135 en
# regimen). Hipotesis: la GPU baja de reloj en idle. Con esto se lanza un
# matmul chico cada ~30ms mientras hay silencio para mantenerla despierta.
# Costo: algo de consumo en pausas. Para validar: comparar cuantas lineas
# "Computo Xms > block" salen al empezar a hablar con y sin esto.
GPU_KEEPALIVE = False
GPU_KEEPALIVE_INTERVAL_MS = 30


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
# OJO: CUDA_VISIBLE_DEVICES casi nunca esta seteado por default en una PC
# normal (es una var para RESTRINGIR que GPU se ve, no para indicar que
# hay una) -- con la condicion vieja esto daba "cpu" siempre, aunque haya
# una GTX 1650 de sobra. Se detecta con torch.cuda.is_available() posta.
try:
    import torch as _torch
    DEVICE = "cuda:0" if _torch.cuda.is_available() else "cpu"
except ImportError:
    DEVICE = "cpu"

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
