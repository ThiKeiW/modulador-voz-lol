"""
Modulo de captura de audio desde microfono en tiempo real.
Utiliza PyAudio para capturar audio chunks y proporcionar streaming.
"""
import threading
import queue
import numpy as np
from typing import Optional, Callable

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False

from config import SAMPLE_RATE, CHUNK_SIZE, CHANNELS


class AudioCapture:
    """Captura audio del microfono en tiempo real."""

    def __init__(
        self,
        sample_rate: int = SAMPLE_RATE,
        chunk_size: int = CHUNK_SIZE,
        channels: int = CHANNELS,
    ):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.channels = channels
        self.is_recording = False
        self.audio_queue: queue.Queue = queue.Queue()
        self._stream: Optional[pyaudio.Stream] = None
        self._pa: Optional[pyaudio.PyAudio] = None
        self._thread: Optional[threading.Thread] = None
        self._callback: Optional[Callable] = None

    def _init_pyaudio(self):
        """Inicializa PyAudio."""
        if not PYAUDIO_AVAILABLE:
            raise ImportError(
                "PyAudio no esta instalado. Ejecuta: pip install pyaudio"
            )
        if self._pa is None:
            self._pa = pyaudio.PyAudio()

    def get_input_devices(self) -> list[dict]:
        """Lista dispositivos de entrada disponibles."""
        self._init_pyaudio()
        devices = []
        for i in range(self._pa.get_device_count()):
            info = self._pa.get_device_info_by_index(i)
            if info["maxInputChannels"] > 0:
                devices.append({
                    "index": i,
                    "name": info["name"],
                    "channels": info["maxInputChannels"],
                    "sample_rate": int(info["defaultSampleRate"]),
                })
        return devices

    def start(
        self,
        device_index: Optional[int] = None,
        callback: Optional[Callable[[np.ndarray], None]] = None,
    ):
        """
        Inicia la captura de audio.

        Args:
            device_index: Indice del dispositivo de entrada (None = default)
            callback: Funcion que recibe cada chunk de audio como np.ndarray
        """
        if self.is_recording:
            return

        self._init_pyaudio()
        self._callback = callback
        self.is_recording = True

        kwargs = {
            "format": pyaudio.paFloat32,
            "channels": self.channels,
            "rate": self.sample_rate,
            "input": True,
            "frames_per_buffer": self.chunk_size,
        }
        if device_index is not None:
            kwargs["input_device_index"] = device_index

        self._stream = self._pa.open(**kwargs)
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def _capture_loop(self):
        """Loop de captura de audio en hilo separado."""
        while self.is_recording:
            try:
                data = self._stream.read(self.chunk_size, exception_on_overflow=False)
                audio_chunk = np.frombuffer(data, dtype=np.float32)

                if self._callback:
                    self._callback(audio_chunk)
                else:
                    self.audio_queue.put(audio_chunk)

            except Exception as e:
                if self.is_recording:
                    print(f"[AudioCapture] Error: {e}")
                break

    def stop(self):
        """Detiene la captura de audio."""
        self.is_recording = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None

    def get_chunk(self) -> Optional[np.ndarray]:
        """Obtiene el siguiente chunk de audio de la cola."""
        try:
            return self.audio_queue.get_nowait()
        except queue.Empty:
            return None

    def get_input_device_index(self, name_contains: str) -> Optional[int]:
        """Busca un dispositivo de entrada por nombre."""
        devices = self.get_input_devices()
        for dev in devices:
            if name_contains.lower() in dev["name"].lower():
                return dev["index"]
        return None

    def __del__(self):
        self.stop()
        if self._pa:
            self._pa.terminate()
