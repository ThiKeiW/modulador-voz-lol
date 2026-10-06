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

    _READ_CHUNK_DEFAULT = 2048  # ~43ms @48kHz -- granularidad de lectura

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
        self.audio_queue: queue.Queue = queue.Queue(maxsize=2)
        self._stream: Optional[pyaudio.Stream] = None
        self._pa: Optional[pyaudio.PyAudio] = None
        self._thread: Optional[threading.Thread] = None
        self._read_chunk = self._READ_CHUNK_DEFAULT
        self._overflow_count = 0
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

        # frames_per_buffer chico: le dice a PortAudio que use un buffer
        # interno chico (bajo riesgo de overflow por una demora puntual),
        # independiente de self.chunk_size (que puede ser grande, 200ms+).
        # Leemos en pedacitos de este tamano y los vamos juntando hasta
        # completar un bloque -- ver _capture_loop.
        self._read_chunk = min(self._READ_CHUNK_DEFAULT, self.chunk_size)

        kwargs = {
            "format": pyaudio.paFloat32,
            "channels": self.channels,
            "rate": self.sample_rate,
            "input": True,
            "frames_per_buffer": self._read_chunk,
        }
        if device_index is not None:
            kwargs["input_device_index"] = device_index

        self._stream = self._pa.open(**kwargs)
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def _capture_loop(self):
        """Loop de captura de audio en hilo separado. Lee en pedacitos
        chicos (self._read_chunk) y los va juntando hasta completar un
        bloque de self.chunk_size -- mas tolerante a demoras puntuales que
        una sola lectura bloqueante gigante."""
        while self.is_recording:
            try:
                target = self.chunk_size
                pieces = []
                got = 0
                while got < target and self.is_recording:
                    n = min(self._read_chunk, target - got)
                    data = self._stream.read(n, exception_on_overflow=True)
                    pieces.append(np.frombuffer(data, dtype=np.float32))
                    got += n

                if not self.is_recording:
                    break

                audio_chunk = pieces[0] if len(pieces) == 1 else np.concatenate(pieces)

                if self._callback:
                    self._callback(audio_chunk)
                else:
                    # Cola acotada: si ConversionThread va mas lento que
                    # tiempo real, se descarta el chunk MAS VIEJO en vez
                    # de dejar que la cola crezca sin limite (eso haria
                    # que el delay mic->parlante se fuera acumulando solo
                    # cuanto mas tiempo pasa, en vez de quedarse estable).
                    if self.audio_queue.full():
                        try:
                            self.audio_queue.get_nowait()
                        except queue.Empty:
                            pass
                    self.audio_queue.put(audio_chunk)

            except OSError as e:
                if self.is_recording and "overflow" in str(e).lower():
                    self._overflow_count += 1
                    print(
                        f"[AudioCapture] Input overflow #{self._overflow_count} "
                        "-- PortAudio tuvo que descartar audio del microfono "
                        "(el hilo de captura no llego a tiempo). Esto SI "
                        "puede causar los huecos."
                    )
                    continue
                if self.is_recording:
                    print(f"[AudioCapture] Error: {e}")
                break
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
