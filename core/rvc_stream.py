"""
core/rvc_stream.py

Envoltorio de streaming para RVCEngine: mantiene un buffer deslizante de
audio con contexto extra (para que el hubert/f0 tengan historial de
calidad) y aplica crossfade SOLA (Synchronized OverLap-Add) entre bloques
consecutivos para que no se escuchen "clicks" en los cortes.

Adaptado de RVCRealtimeVST/worker/rvc_worker.py::RVCStreamEngine.process()
del proyecto oficial RVC-Project/Retrieval-based-Voice-Conversion-WebUI
(MIT License). Se quito todo lo especifico de Windows/VST (mmap, ctypes,
WinEvent) y el noise-gate/rms-mix opcional, para quedarnos con el nucleo:
buffer + SOLA + resample. Esto es lo que core/conversion_thread.py llama
por cada chunk que entrega AudioCapture.

IMPORTANTE: el tamano de chunk que debe pedirsele a AudioCapture es
exactamente `RVCStream.block_frame` (en muestras, a la tasa del
dispositivo). Pasarle un chunk de otro tamano rompe el alineamiento del
buffer.
"""
import logging

import numpy as np
import torch
import torch.nn.functional as F
import torchaudio.transforms as tat

from core.rvc_engine import RVCEngine

logger = logging.getLogger(__name__)


class RVCStream:
    def __init__(
        self,
        engine: RVCEngine,
        sample_rate: int,
        block_ms: float = 250.0,
        crossfade_ms: float = 50.0,
        extra_ms: float = 2500.0,
    ):
        if not engine.is_loaded():
            raise RuntimeError("RVCEngine sin modelo cargado")

        self.engine = engine
        self.device = engine.device
        self.sample_rate = sample_rate

        self.zc = max(1, sample_rate // 100)
        self.block_frame = int(round(block_ms / 1000 * sample_rate / self.zc) * self.zc)
        self.block_frame_16k = 160 * self.block_frame // self.zc
        crossfade_frame = int(round(crossfade_ms / 1000 * sample_rate / self.zc) * self.zc)
        self.sola_buffer_frame = min(crossfade_frame, 4 * self.zc)
        self.sola_search_frame = self.zc
        self.extra_frame = int(round(extra_ms / 1000 * sample_rate / self.zc) * self.zc)

        total_frames = self.extra_frame + self.sola_buffer_frame + self.sola_search_frame + self.block_frame
        self.input_wav = torch.zeros(total_frames, device=self.device, dtype=torch.float32)
        self.input_wav_res = torch.zeros(160 * total_frames // self.zc, device=self.device, dtype=torch.float32)
        self.sola_buffer = torch.zeros(self.sola_buffer_frame, device=self.device, dtype=torch.float32)
        self.sola_den_kernel = torch.ones(1, 1, self.sola_buffer_frame, device=self.device, dtype=torch.float32)

        self.skip_head = self.extra_frame // self.zc
        self.return_length = (self.block_frame + self.sola_buffer_frame + self.sola_search_frame) // self.zc

        self.fade_in_window = torch.sin(
            0.5 * np.pi * torch.linspace(0.0, 1.0, steps=self.sola_buffer_frame, device=self.device)
        ) ** 2
        self.fade_out_window = 1 - self.fade_in_window

        self.resampler = tat.Resample(orig_freq=sample_rate, new_freq=16000, dtype=torch.float32).to(self.device)
        self.resampler2 = None
        if engine.tgt_sr != sample_rate:
            self.resampler2 = tat.Resample(orig_freq=engine.tgt_sr, new_freq=sample_rate, dtype=torch.float32).to(self.device)

        logger.info(
            f"[RVCStream] block={self.block_frame}fr ({block_ms:.0f}ms) "
            f"crossfade={self.sola_buffer_frame}fr extra={self.extra_frame}fr "
            f"tgt_sr={engine.tgt_sr} device_sr={sample_rate}"
        )

    def reset(self):
        self.input_wav.zero_()
        self.input_wav_res.zero_()
        self.sola_buffer.zero_()
        self.engine.cache_pitch.zero_()
        self.engine.cache_pitchf.zero_()

    def process(
        self,
        audio_block: np.ndarray,
        f0_up_key: float = 0,
        index_rate: float = 0.0,
        f0_method: str = "rmvpe",
    ) -> np.ndarray:
        """audio_block: float32 mono, largo == self.block_frame, a self.sample_rate.
        Devuelve audio convertido, mismo largo y misma tasa, listo para reproducir."""
        if len(audio_block) != self.block_frame:
            raise ValueError(
                f"Chunk de tamano incorrecto: se recibieron {len(audio_block)} "
                f"muestras, se esperaban {self.block_frame} (RVCStream.block_frame)"
            )

        indata = np.asarray(audio_block, dtype=np.float32)

        self.input_wav[:-self.block_frame] = self.input_wav[self.block_frame:].clone()
        self.input_wav[-self.block_frame:] = torch.from_numpy(indata).to(self.device)

        self.input_wav_res[:-self.block_frame_16k] = self.input_wav_res[self.block_frame_16k:].clone()
        resample_input = self.input_wav[-self.block_frame - 2 * self.zc:]
        resampled = self.resampler(resample_input)[160:]
        self.input_wav_res[-self.block_frame_16k:] = resampled[-self.block_frame_16k:]

        infer_wav = self.engine.infer(
            self.input_wav_res,
            self.block_frame_16k,
            self.skip_head,
            self.return_length,
            f0_method=f0_method,
            f0_up_key=f0_up_key,
            index_rate=index_rate,
        )

        if self.resampler2 is not None:
            infer_wav = self.resampler2(infer_wav)

        # SOLA: busca el mejor punto de empalme entre el final del bloque
        # anterior (sola_buffer) y el principio del nuevo, para que el
        # crossfade no tenga un salto de fase audible.
        conv_input = infer_wav[None, None, : self.sola_buffer_frame + self.sola_search_frame]
        cor_nom = F.conv1d(conv_input, self.sola_buffer[None, None, :])
        cor_den = torch.sqrt(F.conv1d(conv_input ** 2, self.sola_den_kernel) + 1e-8)
        sola_offset = int(torch.argmax(cor_nom[0, 0] / cor_den[0, 0]))

        infer_wav = infer_wav[sola_offset:]
        infer_wav[: self.sola_buffer_frame] *= self.fade_in_window
        infer_wav[: self.sola_buffer_frame] += self.sola_buffer * self.fade_out_window
        self.sola_buffer[:] = infer_wav[self.block_frame: self.block_frame + self.sola_buffer_frame]

        return infer_wav[: self.block_frame].float().cpu().numpy()
