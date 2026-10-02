"""
Utilidades de procesamiento de audio.
Funciones helper para manipulacion y conversion de audio.
"""
import numpy as np
from pathlib import Path
from typing import Optional


def normalize_audio(audio: np.ndarray, target_db: float = -20.0) -> np.ndarray:
    """
    Normaliza el nivel de volumen del audio.

    Args:
        audio: Array numpy con el audio
        target_db: Nivel objetivo en decibelios

    Returns:
        Audio normalizado
    """
    if len(audio) == 0:
        return audio

    rms = np.sqrt(np.mean(audio ** 2))
    if rms == 0:
        return audio

    current_db = 20 * np.log10(rms)
    gain_db = target_db - current_db
    gain = 10 ** (gain_db / 20)

    return audio * gain


def remove_silence(
    audio: np.ndarray,
    threshold: float = 0.01,
    sample_rate: int = 40000,
) -> np.ndarray:
    """
    Elimina silencios del audio.

    Args:
        audio: Array numpy con el audio
        threshold: Umbral de amplitud para considerar silencio
        sample_rate: Tasa de muestreo

    Returns:
        Audio sin silencios
    """
    if len(audio) == 0:
        return audio

    # Encontrar indices con audio
    mask = np.abs(audio) > threshold
    return audio[mask]


def change_speed(
    audio: np.ndarray,
    speed: float = 1.0,
) -> np.ndarray:
    """
    Cambia la velocidad del audio.

    Args:
        audio: Array numpy con el audio
        speed: Factor de velocidad (1.0 = normal)

    Returns:
        Audio con velocidad modificada
    """
    if speed == 1.0 or len(audio) == 0:
        return audio

    indices = np.linspace(0, len(audio) - 1, int(len(audio) / speed))
    return np.interp(indices, np.arange(len(audio)), audio)


def apply_reverb(
    audio: np.ndarray,
    decay: float = 0.3,
    delay_ms: float = 50.0,
    sample_rate: int = 40000,
) -> np.ndarray:
    """
    Aplica efecto de reverberacion simple.

    Args:
        audio: Array numpy con el audio
        decay: Factor de decaimiento (0.0 - 1.0)
        delay_ms: Retardo en milisegundos
        sample_rate: Tasa de muestreo

    Returns:
        Audio con reverberacion
    """
    if len(audio) == 0:
        return audio

    delay_samples = int(sample_rate * delay_ms / 1000)
    output = audio.copy()

    for i in range(delay_samples, len(audio)):
        output[i] += output[i - delay_samples] * decay

    return normalize_audio(output)


def apply_echo(
    audio: np.ndarray,
    delay_ms: float = 200.0,
    decay: float = 0.4,
    sample_rate: int = 40000,
) -> np.ndarray:
    """
    Aplica efecto de eco.

    Args:
        audio: Array numpy con el audio
        delay_ms: Retardo del eco en milisegundos
        decay: Factor de atenuacion del eco
        sample_rate: Tasa de muestreo

    Returns:
        Audio con eco
    """
    if len(audio) == 0:
        return audio

    delay_samples = int(sample_rate * delay_ms / 1000)
    output = np.zeros(len(audio) + delay_samples)
    output[:len(audio)] = audio

    for i in range(delay_samples, len(output)):
        output[i] += output[i - delay_samples] * decay

    return normalize_audio(output[:len(audio)])


def audio_to_float32(audio) -> np.ndarray:
    """Convierte audio a formato float32."""
    if isinstance(audio, np.ndarray):
        if audio.dtype == np.float32:
            return audio
        elif audio.dtype == np.float64:
            return audio.astype(np.float32)
        elif audio.dtype == np.int16:
            return audio.astype(np.float32) / 32768.0
        elif audio.dtype == np.int32:
            return audio.astype(np.float32) / 2147483648.0
    return np.array(audio, dtype=np.float32)


def get_audio_duration(audio: np.ndarray, sample_rate: int = 40000) -> float:
    """Retorna la duracion del audio en segundos."""
    return len(audio) / sample_rate


def split_audio(
    audio: np.ndarray,
    chunk_size: int = 4096,
) -> list[np.ndarray]:
    """Divide el audio en chunks de tamano fijo."""
    chunks = []
    for i in range(0, len(audio), chunk_size):
        chunk = audio[i:i + chunk_size]
        if len(chunk) == chunk_size:
            chunks.append(chunk)
    return chunks


def load_audio_file(path: str) -> tuple[np.ndarray, int]:
    """
    Carga un archivo de audio.

    Returns:
        Tupla de (audio_array, sample_rate)
    """
    try:
        import soundfile as sf
        audio, sr = sf.read(path, dtype="float32")
        return audio, sr
    except ImportError:
        pass

    try:
        import librosa
        audio, sr = librosa.load(path, sr=None, mono=True)
        return audio.astype(np.float32), sr
    except ImportError:
        pass

    raise ImportError("Se necesita soundfile o librosa para cargar archivos de audio")


def save_audio_file(
    audio: np.ndarray,
    path: str,
    sample_rate: int = 40000,
):
    """Guarda audio en archivo."""
    import soundfile as sf
    sf.write(path, audio, sample_rate)
