"""
core/conversion_thread.py

Hilo de conversion de voz en tiempo real (Fase 2, AGENTS.md). Conecta
AudioCapture -> RVCStream (buffer+SOLA sobre RVCEngine) -> salida de audio.

Requiere que el RVCEngine YA tenga un modelo cargado (via
RVCEngine.load_model(...)) antes de instanciar este hilo: la GUI decide
que personaje usar y carga el modelo; este hilo solo mueve el audio.

El tamano de chunk que AudioCapture debe entregar NO es libre: tiene que
ser exactamente RVCStream.block_frame (se fija aca mismo, en run(), antes
de audio_capture.start()). Pasar chunks de otro tamano rompe el streaming.
"""
import time
import traceback
from typing import Optional

import numpy as np
import sounddevice as sd
from PyQt6.QtCore import QThread, pyqtSignal

from config import (
    DEFAULT_PITCH_SHIFT,
    DEFAULT_F0_METHOD,
    DEFAULT_INDEX_RATE,
    REALTIME_BLOCK_MS,
    REALTIME_CROSSFADE_MS,
    REALTIME_EXTRA_MS,
)
from core.rvc_stream import RVCStream


class ConversionThread(QThread):
    """Hilo dedicado a la conversion de voz en tiempo real."""

    status_changed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    latency_updated = pyqtSignal(float)
    level_updated = pyqtSignal(float)

    LATENCY_WARNING_MS = 200  # referencia del AGENTS.md; con block=250ms+computo
                               # es normal superarlo, ver nota en el reporte

    def __init__(
        self,
        audio_capture,
        rvc_engine,
        device_index: Optional[int] = None,
        output_device: Optional[int] = None,
        pitch_shift: int = DEFAULT_PITCH_SHIFT,
        f0_method: str = DEFAULT_F0_METHOD,
        index_rate: float = DEFAULT_INDEX_RATE,
        block_ms: float = REALTIME_BLOCK_MS,
        crossfade_ms: float = REALTIME_CROSSFADE_MS,
        extra_ms: float = REALTIME_EXTRA_MS,
        parent=None,
    ):
        super().__init__(parent)
        self.audio_capture = audio_capture
        self.rvc_engine = rvc_engine
        self.device_index = device_index
        self.output_device = output_device
        self.pitch_shift = pitch_shift
        self.f0_method = f0_method
        self.index_rate = index_rate
        self.block_ms = block_ms
        self.crossfade_ms = crossfade_ms
        self.extra_ms = extra_ms

        self.running = False
        self.stream: Optional[RVCStream] = None

    def run(self):
        if not self.rvc_engine.is_loaded():
            self.error_occurred.emit("No hay ningun modelo cargado en el motor RVC.")
            return

        self.running = True
        self.status_changed.emit("iniciando")

        out_stream = None
        try:
            self.stream = RVCStream(
                self.rvc_engine,
                sample_rate=self.audio_capture.sample_rate,
                block_ms=self.block_ms,
                crossfade_ms=self.crossfade_ms,
                extra_ms=self.extra_ms,
            )
            # El chunk que pida AudioCapture tiene que calzar exacto con el
            # bloque que espera RVCStream (depende de block_ms y de la
            # tasa del dispositivo, no es un numero fijo).
            self.audio_capture.chunk_size = self.stream.block_frame

            self.audio_capture.start(device_index=self.device_index)

            out_stream = sd.OutputStream(
                samplerate=self.audio_capture.sample_rate,
                channels=1,
                dtype="float32",
                device=self.output_device,
                latency="low",
            )
            out_stream.start()

            self.status_changed.emit("corriendo")

            while self.running:
                chunk = self.audio_capture.get_chunk()
                if chunk is None:
                    self.msleep(5)
                    continue

                t_start = time.perf_counter()
                try:
                    converted = self.stream.process(
                        chunk,
                        f0_up_key=self.pitch_shift,
                        index_rate=self.index_rate,
                        f0_method=self.f0_method,
                    )
                except Exception as exc:
                    self.error_occurred.emit(f"Error en conversion: {exc}\n{traceback.format_exc()}")
                    continue

                if converted is None or len(converted) == 0:
                    continue

                converted = np.ascontiguousarray(converted, dtype=np.float32)
                out_stream.write(converted)

                latency_ms = (time.perf_counter() - t_start) * 1000
                self.latency_updated.emit(latency_ms)
                if latency_ms > self.block_ms:
                    # Mas lento que el bloque que hay que producir: se va a
                    # ir acumulando retraso. Con GPU deberia ir sobrado;
                    # en CPU puro probablemente haya que subir block_ms.
                    print(f"[ConversionThread] Latencia {latency_ms:.0f}ms > block {self.block_ms:.0f}ms")

                rms = float(np.sqrt(np.mean(np.square(converted)))) if converted.size else 0.0
                self.level_updated.emit(min(rms * 4, 1.0))

        except Exception as exc:
            self.error_occurred.emit(f"{exc}\n{traceback.format_exc()}")
        finally:
            if out_stream is not None:
                try:
                    out_stream.stop()
                    out_stream.close()
                except Exception:
                    pass
            try:
                self.audio_capture.stop()
            except Exception:
                pass
            self.running = False
            self.status_changed.emit("detenido")

    def set_pitch_shift(self, semitones: int):
        self.pitch_shift = semitones

    def set_f0_method(self, method: str):
        self.f0_method = method

    def set_index_rate(self, rate: float):
        self.index_rate = rate

    def stop(self):
        self.running = False
        self.wait(2000)
