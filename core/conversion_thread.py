"""
core/conversion_thread.py

Hilo de conversion de voz en tiempo real (Fase 2 del AGENTS.md).
Conecta AudioCapture -> RVCEngine -> salida de audio (sounddevice).

Este hilo asume que el modelo YA fue cargado en rvc_engine (via
rvc_engine.load_model(...)) antes de llamar a start(). No carga modelos
por si mismo para mantener responsabilidades separadas: la GUI decide
que modelo usar, este hilo solo mueve el audio.

NOTA IMPORTANTE: RVCEngine.convert() actualmente es un placeholder que
solo aplica pitch-shift (resample simple), NO corre inferencia real del
modelo .pth cargado. Este hilo ya queda listo para cuando esa inferencia
se implemente; hoy escucharas tu propia voz con el pitch ajustado, no la
voz del personaje.
"""
import time
import traceback
from typing import Optional

import numpy as np
import sounddevice as sd
from PyQt6.QtCore import QThread, pyqtSignal

from config import DEFAULT_PITCH_SHIFT, DEFAULT_F0_METHOD


class ConversionThread(QThread):
    """
    Hilo dedicado a la conversion de voz en tiempo real.

    Flujo:
        AudioCapture (su propio hilo interno, con cola) -> get_chunk()
        -> RVCEngine.convert() -> sounddevice.OutputStream.write()

    Señales para la GUI:
        status_changed(str)     -> "iniciando" | "corriendo" | "detenido"
        error_occurred(str)     -> mensaje de error si algo falla
        latency_updated(float)  -> latencia de procesamiento del ultimo chunk, en ms
        level_updated(float)    -> nivel RMS del audio convertido (0.0-1.0), para el visualizador
    """

    status_changed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    latency_updated = pyqtSignal(float)
    level_updated = pyqtSignal(float)

    LATENCY_WARNING_MS = 200  # objetivo de Fase 2 en AGENTS.md
    POLL_SLEEP_MS = 5         # espera cuando la cola de audio esta vacia

    def __init__(
        self,
        audio_capture,
        rvc_engine,
        device_index: Optional[int] = None,
        output_device: Optional[int] = None,
        pitch_shift: int = DEFAULT_PITCH_SHIFT,
        f0_method: str = DEFAULT_F0_METHOD,
        parent=None,
    ):
        super().__init__(parent)
        self.audio_capture = audio_capture
        self.rvc_engine = rvc_engine
        self.device_index = device_index
        self.output_device = output_device
        self.pitch_shift = pitch_shift
        self.f0_method = f0_method

        self.running = False

    def run(self):
        if not self.rvc_engine.is_loaded():
            self.error_occurred.emit("No hay ningun modelo cargado en el motor RVC.")
            return

        self.running = True
        self.status_changed.emit("iniciando")

        out_stream = None
        try:
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
                    self.msleep(self.POLL_SLEEP_MS)
                    continue

                t_start = time.perf_counter()
                try:
                    converted = self.rvc_engine.convert(
                        chunk,
                        pitch_shift=self.pitch_shift,
                        f0_method=self.f0_method,
                    )
                except Exception as exc:
                    self.error_occurred.emit(f"Error en conversion: {exc}")
                    continue

                if converted is None or len(converted) == 0:
                    continue

                converted = np.ascontiguousarray(converted, dtype=np.float32)
                out_stream.write(converted)

                latency_ms = (time.perf_counter() - t_start) * 1000
                self.latency_updated.emit(latency_ms)

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

    def stop(self):
        self.running = False
        self.wait(2000)
