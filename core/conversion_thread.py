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
    PROFILE_RVC,
    SILENCE_GATE_ENABLED,
    SILENCE_RMS_THRESHOLD,
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
        silence_gate_enabled: bool = SILENCE_GATE_ENABLED,
        silence_threshold: float = SILENCE_RMS_THRESHOLD,
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
        self.silence_gate_enabled = silence_gate_enabled
        self.silence_threshold = silence_threshold

        self.running = False
        self.stream: Optional[RVCStream] = None
        self._was_silent = False

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

            # Warmup: la primera inferencia (construccion de RMVPE + kernels
            # CUDA frios) tarda decenas de segundos. Se paga aca --con la
            # GUI avisando via status-- en vez de en el primer bloque con
            # voz, donde se sentiria como "tarda en detectar el microfono".
            self.status_changed.emit("calentando")
            self.rvc_engine.warmup(
                len(self.stream.input_wav_res),
                self.stream.block_frame_16k,
                self.stream.skip_head,
                self.stream.return_length,
                f0_method=self.f0_method,
                index_rate=self.index_rate,
            )

            self.audio_capture.start(device_index=self.device_index)

            out_stream = sd.OutputStream(
                samplerate=self.audio_capture.sample_rate,
                channels=1,
                dtype="float32",
                device=self.output_device,
                # "low" le pide a WASAPI el buffer MAS CHICO posible --
                # practicamente cero margen entre un write() y el
                # siguiente. Con el loop entero (poll de cola + write +
                # GIL) compitiendo por CPU con el computo real, eso es
                # casi garantia de underrun justo en el borde de cada
                # bloque (coincide con los cortes medidos en el waveform,
                # uno por bloque). 100ms de buffer le da a PortAudio
                # colchon real sin agregar latencia perceptible.
                latency=0.1,
            )
            out_stream.start()

            self.status_changed.emit("corriendo")

            while self.running:
                chunk = self.audio_capture.get_chunk()
                if chunk is None:
                    self.msleep(5)
                    continue

                # RMS siempre (barato: ~9600 muestras) porque lo usa el
                # silence gate; el print sigue solo con PROFILE_RVC.
                rms_in = float(np.sqrt(np.mean(np.square(chunk)))) if len(chunk) else 0.0
                if PROFILE_RVC:
                    print(f"[RMS entrada] mic={rms_in:.4f} qsize~={self.audio_capture.audio_queue.qsize()}")

                # Silence gate: bloque silencioso -> ceros directos al
                # parlante SIN pasar por hubert/f0/synth. Se escribe
                # exactamente un bloque (mismo largo que process()
                # devolveria), asi el pacing del stream no se rompe.
                if self.silence_gate_enabled and rms_in < self.silence_threshold:
                    out_stream.write(np.zeros(len(chunk), dtype=np.float32))
                    self.latency_updated.emit(0.0)
                    self.level_updated.emit(0.0)
                    self._was_silent = True
                    continue

                if self._was_silent:
                    # Volvio la voz: limpiar estado viejo del stream
                    # (buffers de entrada + sola_buffer + caches de pitch)
                    # para que el primer bloque con voz no mezcle audio
                    # rancio en el crossfade.
                    self.stream.reset()
                    self._was_silent = False

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

                # Medir SOLO el computo (process()) para decidir si vamos
                # atrasados -- lo que sigue (write) bloquea esperando que
                # el parlante tenga espacio, eso es pacing normal, no
                # computo de mas, y mezclarlo en la misma metrica confunde
                # (processing real puede ir sobrado y este numero igual
                # da por encima de block_ms).
                compute_ms = (time.perf_counter() - t_start) * 1000

                converted = np.ascontiguousarray(converted, dtype=np.float32)

                if PROFILE_RVC:
                    # Para saber si el silencio ya viene DENTRO del audio
                    # que arma el motor (bug de DSP, se arregla en
                    # rvc_stream/rvc_engine) o lo mete el dispositivo de
                    # salida despues (bug de audio I/O, se arregla en el
                    # OutputStream). Partido en tercios del bloque.
                    n = len(converted)
                    third = max(1, n // 3)
                    rms_start = float(np.sqrt(np.mean(np.square(converted[:third]))))
                    rms_mid = float(np.sqrt(np.mean(np.square(converted[third:2*third]))))
                    rms_end = float(np.sqrt(np.mean(np.square(converted[2*third:]))))
                    print(f"[RMS bloque] inicio={rms_start:.4f} medio={rms_mid:.4f} fin={rms_end:.4f}")

                out_stream.write(converted)

                self.latency_updated.emit(compute_ms)
                if compute_ms > self.block_ms:
                    # Esto si importa: el computo solo ya no entra en el
                    # tiempo del bloque -> se va a acumular atraso de
                    # verdad (el write ya no alcanza a compensarlo).
                    print(f"[ConversionThread] Computo {compute_ms:.0f}ms > block {self.block_ms:.0f}ms (vas atras)")

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
