"""
core/audio_output.py

Salida de audio desacoplada del computo.

Problema que resuelve: con sd.OutputStream.write() bloqueante, el ciclo
del hilo de conversion era `computo (~150ms) + espera del write()`. El
write() de un bloque de 200ms solo retorna cuando el buffer del
dispositivo (~100ms) deja espacio, asi que la espera ~100ms se SUMA al
computo en vez de solaparse con la reproduccion. Resultado medido:
ciclo ~268ms contra un mic que entrega un bloque cada 200ms ->
  - la cola de entrada se satura y descarta bloques (contenido perdido)
  - el buffer del parlante se vacia ~65ms entre bloques (hueco de silencio)

Aca el hilo de conversion solo hace push() (no bloquea) y es el callback
de PortAudio el que consume. Un colchon inicial (prefill) absorbe el
jitter del computo para que el parlante no se quede sin datos.
"""
import collections
import threading
from typing import Optional

import numpy as np
import sounddevice as sd


class StreamingOutput:
    def __init__(
        self,
        sample_rate: int,
        device: Optional[int] = None,
        prefill_ms: float = 60.0,
        max_buffer_ms: float = 800.0,
        latency: float = 0.05,
    ):
        self.sample_rate = sample_rate
        self.prefill_ms = prefill_ms
        self._prefill_frames = int(prefill_ms * sample_rate / 1000)
        self._max_frames = int(max_buffer_ms * sample_rate / 1000)

        self._lock = threading.Lock()
        self._chunks = collections.deque()  # elementos: [array, audible]
        self._frames = 0
        self._last_audible = False  # el ultimo audio entregado al parlante era voz?
        self._primed = False  # False = hay que (re)armar el colchon en el proximo push

        # Contadores para diagnostico (se leen desde otro hilo, enteros
        # simples: lectura sin lock es suficiente).
        self.underruns = 0         # veces que el parlante se quedo sin datos (total)
        self.audible_underruns = 0  # ...de esas, las que cortaron VOZ (hueco audible real).
                                    # Un underrun mientras suena silencio (p.ej. el pico
                                    # de calculo al arrancar a hablar) es inocuo.
        self.device_underflows = 0  # underflows reportados por PortAudio mismo
        self.dropped_frames = 0    # muestras tiradas por buffer demasiado lleno

        # Canales: SIEMPRE 2 si el dispositivo los soporta, aunque el audio
        # sea mono. Con VB-CABLE (WASAPI) un stream de 1 canal abre sin
        # error pero entrega audio corrompido (medido: tono de 440 Hz sale
        # como ruido ~873 Hz); en 2 canales sale limpio. En altavoces no
        # cambia nada (el mismo mono se copia a ambos canales).
        self._channels = 1
        try:
            info = sd.query_devices(device, "output") if device is not None \
                else sd.query_devices(kind="output")
            if int(info.get("max_output_channels", 0)) >= 2:
                self._channels = 2
        except Exception:
            pass

        self._stream = sd.OutputStream(
            samplerate=sample_rate,
            channels=self._channels,
            dtype="float32",
            device=device,
            latency=latency,
            callback=self._callback,
        )

    # ------------------------------------------------------------------
    def start(self):
        self._stream.start()

    def stop(self):
        try:
            self._stream.stop()
        finally:
            self._stream.close()

    @property
    def buffered_ms(self) -> float:
        return 1000.0 * self._frames / self.sample_rate

    # ------------------------------------------------------------------
    def push(self, samples: np.ndarray, audible: bool = True):
        """Encola audio para reproducir. No bloquea. `audible=False` marca
        relleno de silencio (para no contar sus underruns como cortes de voz)."""
        arr = np.ascontiguousarray(samples, dtype=np.float32)
        if arr.size == 0:
            return
        with self._lock:
            if not self._primed:
                # Primer bloque (o primero tras un underrun): se antepone
                # el colchon de silencio, asi el bloque siguiente llega
                # con margen antes de que este termine de sonar.
                if self._prefill_frames > 0:
                    self._chunks.append([np.zeros(self._prefill_frames, dtype=np.float32), False])
                    self._frames += self._prefill_frames
                self._primed = True

            self._chunks.append([arr, audible])
            self._frames += len(arr)

            # Tope de latencia: si por algun motivo se acumula demasiado
            # (relojes de mic y parlante no son identicos), tirar lo mas
            # viejo en vez de dejar que el retraso crezca sin limite.
            excess = self._frames - self._max_frames
            while excess > 0 and self._chunks:
                head = self._chunks[0][0]
                if len(head) <= excess:
                    self._chunks.popleft()
                    self._frames -= len(head)
                    self.dropped_frames += len(head)
                    excess -= len(head)
                else:
                    self._chunks[0][0] = head[excess:]
                    self._frames -= excess
                    self.dropped_frames += excess
                    excess = 0

    # ------------------------------------------------------------------
    def _callback(self, outdata, frames, time_info, status):
        if status.output_underflow:
            self.device_underflows += 1

        out = np.zeros(frames, dtype=np.float32)
        filled = 0
        with self._lock:
            while filled < frames and self._chunks:
                head, audible = self._chunks[0]
                take = min(frames - filled, len(head))
                out[filled:filled + take] = head[:take]
                self._last_audible = audible
                if take == len(head):
                    self._chunks.popleft()
                else:
                    self._chunks[0][0] = head[take:]
                filled += take
                self._frames -= take

            if filled < frames and self._primed:
                # Estaba reproduciendo y se quedo sin datos.
                self.underruns += 1
                if self._last_audible:
                    self.audible_underruns += 1  # corto voz: hueco audible
                self._primed = False

        outdata[:, 0] = out
        if self._channels > 1:
            # Voz mono replicada: el cable y Windows esperan estereo.
            outdata[:, 1:self._channels] = out[:, None]
