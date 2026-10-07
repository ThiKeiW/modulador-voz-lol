"""
Motor de conversion de voz RVC real (v1/v2), adaptado de
infer/rtrvc.py::RVC del proyecto oficial RVC-Project/Retrieval-based-Voice-
Conversion-WebUI (MIT License), vendorizado en core/rvc_backend/.

Diferencias vs el original:
- Sin objeto `config` de la WebUI: device/is_half se pasan directo.
- Sin i18n (solo logging).
- Sin fcpe (no vendorizado). F0: rmvpe (recomendado), pm, harvest.
- Sin formant shift en vivo (queda en 0; se puede agregar despues).

Este motor NO procesa un chunk suelto: necesita que quien lo llame (ver
core/rvc_stream.py) le pase una ventana de audio a 16kHz ya armada con
contexto (skip_head/return_length), igual que el pipeline real-time
oficial. Llamar a .infer() con un chunk aislado sin contexto da resultados
pobres/con clicks; para eso existe RVCStream.
"""
import logging
import time
from pathlib import Path
from typing import Optional

import numpy as np
import torch

from config import DEVICE, HUBERT_DIR, RMVPE_PATH, PROFILE_RVC

from core.rvc_backend.hubert import extract_hubert_features, load_hubert_model
from core.rvc_backend.cuda_graph import run_cuda_graph
from core.rvc_backend.models import (
    SynthesizerTrnMs256NSFsid,
    SynthesizerTrnMs256NSFsid_nono,
    SynthesizerTrnMs768NSFsid,
    SynthesizerTrnMs768NSFsid_nono,
)

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

try:
    import parselmouth
    PARSELMOUTH_AVAILABLE = True
except ImportError:
    PARSELMOUTH_AVAILABLE = False

try:
    import pyworld
    PYWORLD_AVAILABLE = True
except ImportError:
    PYWORLD_AVAILABLE = False

logger = logging.getLogger(__name__)


def get_synthesizer(pth_path, device=torch.device("cpu")):
    """Carga un .pth original de RVC y arma la arquitectura correcta
    (v1/256 vs v2/768, con/sin f0) segun los metadatos del propio checkpoint.
    Identico a infer/rtrvc.py::get_synthesizer del repo oficial."""
    cpt = torch.load(pth_path, map_location=torch.device("cpu"), weights_only=False)
    cpt["config"][-3] = cpt["weight"]["emb_g.weight"].shape[0]
    if_f0 = cpt.get("f0", 1)
    version = cpt.get("version", "v1")
    if version == "v1":
        if if_f0 == 1:
            net_g = SynthesizerTrnMs256NSFsid(*cpt["config"], is_half=False)
        else:
            net_g = SynthesizerTrnMs256NSFsid_nono(*cpt["config"])
    elif version == "v2":
        if if_f0 == 1:
            net_g = SynthesizerTrnMs768NSFsid(*cpt["config"], is_half=False)
        else:
            net_g = SynthesizerTrnMs768NSFsid_nono(*cpt["config"])
    else:
        raise ValueError(f"Version de modelo RVC desconocida: {version!r}")

    if hasattr(net_g, "enc_q"):
        del net_g.enc_q
    result = net_g.load_state_dict(cpt["weight"], strict=False)
    # strict=False es necesario: enc_q.* vive en el checkpoint (es solo para
    # entrenamiento) y ya lo borramos arriba, asi que SIEMPRE va a aparecer
    # como unexpected_key. Lo que NO toleramos es cualquier otra cosa: eso
    # es exactamente el modo de falla silenciosa (capa real con pesos
    # aleatorios, sale ruido sin ningun error) que hf-rvc tiene con estos
    # checkpoints. Mejor reventar aca que descubrirlo escuchando ruido.
    bad_missing = list(result.missing_keys)
    bad_unexpected = [k for k in result.unexpected_keys if not k.startswith("enc_q.")]
    if bad_missing or bad_unexpected:
        raise RuntimeError(
            f"Arquitectura RVC no coincide con el checkpoint {pth_path}: "
            f"missing_keys={bad_missing[:10]} unexpected_keys={bad_unexpected[:10]} "
            "(version/f0 del checkpoint probablemente mal detectados)"
        )
    net_g = net_g.float()
    net_g.eval().to(device)
    net_g.remove_weight_norm()
    return net_g, cpt


class RVCEngine:
    """Motor de conversion de voz RVC (v1/v2) listo para tiempo real."""

    F0_METHODS = ("rmvpe", "pm", "harvest")

    def __init__(self, device: str = DEVICE, is_half: bool = False):
        cuda_ok = torch.cuda.is_available()
        wants_cuda = device not in (None, "cpu")
        self.device = torch.device(device if (wants_cuda and cuda_ok) else ("cuda:0" if cuda_ok else "cpu"))
        self.is_half = is_half and self.device.type == "cuda"

        self.hubert_model = None  # compartido entre personajes, se carga 1 vez
        self.net_g = None
        self.model_name: Optional[str] = None
        self.model_path: Optional[str] = None
        self.tgt_sr: Optional[int] = None
        self.if_f0: int = 1
        self.version: str = "v2"

        self.index = None
        self.big_npy = None
        self.index_path: Optional[str] = None

        self.f0_up_key = 0
        self.f0_min = 50
        self.f0_max = 1100
        self.f0_mel_min = 1127 * np.log(1 + self.f0_min / 700)
        self.f0_mel_max = 1127 * np.log(1 + self.f0_max / 700)

        self.cache_pitch = torch.zeros(1024, device=self.device, dtype=torch.long)
        self.cache_pitchf = torch.zeros(1024, device=self.device, dtype=torch.float32)

        self._model_rmvpe = None
        self._initialized = False

    def initialize(self):
        if self._initialized:
            return
        self._initialized = True
        logger.info(f"[RVCEngine] Device: {self.device}, half: {self.is_half}")
        logger.info(f"[RVCEngine] faiss: {FAISS_AVAILABLE}, parselmouth: {PARSELMOUTH_AVAILABLE}, pyworld: {PYWORLD_AVAILABLE}")

    # ------------------------------------------------------------------
    # Carga de modelo
    # ------------------------------------------------------------------

    def load_model(self, model_path: str, model_name: str = None, index_path: Optional[str] = None) -> bool:
        """Carga un .pth de personaje (v1 o v2, con o sin f0) + su .index
        opcional. El hubert_base se carga una sola vez y se reusa entre
        personajes (es independiente del personaje)."""
        try:
            if self.hubert_model is None:
                if not (Path(HUBERT_DIR) / "config.json").is_file():
                    logger.error(
                        f"[RVCEngine] Falta hubert_base en {HUBERT_DIR}. "
                        "Corre: python scripts/download_assets.py"
                    )
                    return False
                self.hubert_model = load_hubert_model(self.device, self.is_half)

            self.net_g, cpt = get_synthesizer(model_path, self.device)
            self.tgt_sr = cpt["config"][-1]
            self.if_f0 = cpt.get("f0", 1)
            self.version = cpt.get("version", "v1")
            if self.is_half:
                self.net_g = self.net_g.half()
            else:
                self.net_g = self.net_g.float()

            self.model_name = model_name or Path(model_path).stem
            self.model_path = str(model_path)

            self.index = None
            self.big_npy = None
            self.index_path = index_path
            if index_path and Path(index_path).is_file():
                if FAISS_AVAILABLE:
                    self.index = faiss.read_index(str(index_path))
                    self.big_npy = self.index.reconstruct_n(0, self.index.ntotal)
                    logger.info(f"[RVCEngine] Indice cargado: {index_path}")
                else:
                    logger.warning("[RVCEngine] faiss no disponible, se ignora el indice")

            self.cache_pitch.zero_()
            self.cache_pitchf.zero_()

            logger.info(
                f"[RVCEngine] Modelo cargado: {self.model_name} "
                f"(version={self.version}, f0={self.if_f0}, sr={self.tgt_sr}, device={self.device})"
            )
            return True

        except Exception as e:
            logger.error(f"[RVCEngine] Error cargando modelo: {e}")
            return False

    def unload_model(self):
        self.net_g = None
        self.model_name = None
        self.model_path = None
        self.index = None
        self.big_npy = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def is_loaded(self) -> bool:
        return self.net_g is not None

    def get_model_info(self) -> dict:
        return {
            "loaded": self.is_loaded(),
            "name": self.model_name,
            "device": str(self.device),
            "version": self.version,
            "f0": self.if_f0,
            "target_sample_rate": self.tgt_sr,
            "has_index": self.index is not None,
            "faiss_available": FAISS_AVAILABLE,
        }

    def change_index_rate(self, new_index_rate: float):
        if new_index_rate != 0 and self.index is None and self.index_path:
            if FAISS_AVAILABLE and Path(self.index_path).is_file():
                self.index = faiss.read_index(str(self.index_path))
                self.big_npy = self.index.reconstruct_n(0, self.index.ntotal)

    # ------------------------------------------------------------------
    # F0 (pitch)
    # ------------------------------------------------------------------

    def _f0_post(self, f0):
        if not torch.is_tensor(f0):
            f0 = torch.from_numpy(f0)
        f0 = f0.float().to(self.device).squeeze()
        f0_mel = 1127 * torch.log(1 + f0 / 700)
        f0_mel[f0_mel > 0] = (f0_mel[f0_mel > 0] - self.f0_mel_min) * 254 / (
            self.f0_mel_max - self.f0_mel_min
        ) + 1
        f0_mel[f0_mel <= 1] = 1
        f0_mel[f0_mel > 255] = 255
        f0_coarse = torch.round(f0_mel).long()
        return f0_coarse, f0

    def get_f0(self, audio_16k: torch.Tensor, f0_up_key: float, method: str = "rmvpe"):
        if method == "rmvpe":
            return self._get_f0_rmvpe(audio_16k, f0_up_key)
        if method == "harvest":
            return self._get_f0_harvest(audio_16k, f0_up_key)
        if method == "pm":
            return self._get_f0_pm(audio_16k, f0_up_key)
        raise ValueError(f"f0_method no soportado: {method}")

    def _get_f0_rmvpe(self, x: torch.Tensor, f0_up_key: float):
        if self._model_rmvpe is None:
            if not Path(RMVPE_PATH).is_file():
                raise FileNotFoundError(
                    f"Falta {RMVPE_PATH}. Corre: python scripts/download_assets.py"
                )
            from core.rvc_backend.rmvpe import RMVPE
            logger.info("[RVCEngine] Cargando RMVPE...")
            self._model_rmvpe = RMVPE(str(RMVPE_PATH), is_half=self.is_half, device=self.device)
        f0 = self._model_rmvpe.infer_from_audio(x, thred=0.03)
        uv = f0 == 0
        if np.any(~uv):
            f0[uv] = np.interp(np.where(uv)[0], np.where(~uv)[0], f0[~uv])
        f0 *= pow(2, f0_up_key / 12)
        return self._f0_post(f0)

    def _get_f0_pm(self, x: torch.Tensor, f0_up_key: float):
        if not PARSELMOUTH_AVAILABLE:
            raise ImportError("praat-parselmouth requerido para f0_method='pm'")
        xn = x.cpu().numpy()
        p_len = xn.shape[0] // 160 + 1
        f0_min = 65
        l_pad = int(np.ceil(1.5 / f0_min * 16000))
        r_pad = l_pad + 1
        s = parselmouth.Sound(np.pad(xn, (l_pad, r_pad)), 16000).to_pitch_ac(
            time_step=0.01, voicing_threshold=0.6, pitch_floor=f0_min, pitch_ceiling=1100,
        )
        f0 = s.selected_array["frequency"]
        if len(f0) < p_len:
            f0 = np.pad(f0, (0, p_len - len(f0)))
        f0 = f0[:p_len]
        uv = f0 == 0
        if np.any(~uv):
            f0[uv] = np.interp(np.where(uv)[0], np.where(~uv)[0], f0[~uv])
        f0 *= pow(2, f0_up_key / 12)
        return self._f0_post(f0)

    def _get_f0_harvest(self, x: torch.Tensor, f0_up_key: float):
        if not PYWORLD_AVAILABLE:
            raise ImportError("pyworld requerido para f0_method='harvest'")
        import scipy.signal as signal
        xn = x.cpu().numpy().astype(np.double)
        f0, t = pyworld.harvest(xn, fs=16000, f0_ceil=1100, f0_floor=50, frame_period=10)
        f0 = pyworld.stonemask(xn, f0, t, 16000)
        f0 = signal.medfilt(f0, 3)
        f0 *= pow(2, f0_up_key / 12)
        return self._f0_post(f0)

    # ------------------------------------------------------------------
    # Inferencia (llamada por core/rvc_stream.py con la ventana ya armada)
    # ------------------------------------------------------------------

    def warmup(
        self,
        input_len_16k: int,
        block_frame_16k: int,
        skip_head,
        return_length,
        f0_method: str = "rmvpe",
        index_rate: float = 0.0,
    ) -> float:
        """Pasa ceros por el pipeline completo UNA vez: construye RMVPE
        (carga de pesos lenta la primera vez) y calienta kernels CUDA, para
        que el primer bloque con voz real no pague ese costo en vivo
        (medido: ~35-39s en el primer bloque con voz sin esto).
        Llamar despues de crear el RVCStream, con SU geometria
        (ver core/rvc_stream.py). Devuelve los ms que tardo."""
        if not self.is_loaded():
            raise RuntimeError("No hay modelo RVC cargado")
        t0 = time.perf_counter()
        logger.info("[RVCEngine] Warmup: primera inferencia (tarda solo esta vez)...")
        dummy = torch.zeros(input_len_16k, device=self.device, dtype=torch.float32)
        self.infer(
            dummy,
            block_frame_16k,
            skip_head,
            return_length,
            f0_method=f0_method,
            f0_up_key=0,
            index_rate=index_rate,
        )
        ms = (time.perf_counter() - t0) * 1000
        logger.info(f"[RVCEngine] Warmup OK en {ms:.0f}ms")
        # Caches limpios para que la sesion real arranque sin arrastrar
        # el pitch del dummy.
        self.cache_pitch.zero_()
        self.cache_pitchf.zero_()
        return ms

    def infer(
        self,
        input_wav_16k: torch.Tensor,
        block_frame_16k: int,
        skip_head,
        return_length,
        f0_method: str = "rmvpe",
        f0_up_key: float = 0,
        index_rate: float = 0.0,
    ) -> torch.Tensor:
        """Convierte una ventana de audio a 16kHz (con contexto) en audio
        a self.tgt_sr. Mantiene cache de pitch entre llamadas para que el
        streaming no tenga discontinuidades. Ver core/rvc_stream.py para
        como se arma input_wav_16k/skip_head/return_length por bloque."""
        if not self.is_loaded():
            raise RuntimeError("No hay modelo RVC cargado")

        def _sync():
            # CUDA es asincrono: sin esto, los tiempos entre etapas no
            # significan nada (el compute real queda flotando y aparece
            # recien en el siguiente punto que fuerza sincronizacion).
            if self.device.type == "cuda":
                torch.cuda.synchronize(self.device)

        prof = PROFILE_RVC
        t0 = time.perf_counter() if prof else 0

        with torch.no_grad():
            feats = input_wav_16k.half().view(1, -1) if self.is_half else input_wav_16k.float().view(1, -1)
            padding_mask = torch.BoolTensor(feats.shape).to(self.device).fill_(False)
            feats = extract_hubert_features(self.hubert_model, feats, self.version, padding_mask=padding_mask)
            feats = torch.cat((feats, feats[:, -1:, :]), 1)

            if prof:
                _sync()
                t_hubert = time.perf_counter()

            if self.index is not None and index_rate != 0:
                try:
                    npy = feats[0][skip_head // 2:].cpu().numpy().astype("float32")
                    score, ix = self.index.search(npy, k=8)
                    if (ix >= 0).all():
                        weight = np.square(1 / score)
                        weight /= weight.sum(axis=1, keepdims=True)
                        npy = np.sum(self.big_npy[ix] * np.expand_dims(weight, axis=2), axis=1)
                        if self.is_half:
                            npy = npy.astype("float16")
                        feats[0][skip_head // 2:] = (
                            torch.from_numpy(npy).unsqueeze(0).to(self.device) * index_rate
                            + (1 - index_rate) * feats[0][skip_head // 2:]
                        )
                except Exception:
                    logger.exception("[RVCEngine] Error en retrieval por indice")

            if prof:
                _sync()
                t_index = time.perf_counter()

            p_len = input_wav_16k.shape[0] // 160
            return_length2 = int(return_length)
            if self.if_f0 == 1:
                f0_extractor_frame = block_frame_16k + 800
                if f0_method == "rmvpe":
                    f0_extractor_frame = 5120 * ((f0_extractor_frame - 1) // 5120 + 1) - 160
                pitch, pitchf = self.get_f0(input_wav_16k[-f0_extractor_frame:], f0_up_key, f0_method)
                shift = block_frame_16k // 160
                self.cache_pitch[:-shift] = self.cache_pitch[shift:].clone()
                self.cache_pitchf[:-shift] = self.cache_pitchf[shift:].clone()
                self.cache_pitch[4 - pitch.shape[0]:] = pitch[3:-1]
                self.cache_pitchf[4 - pitch.shape[0]:] = pitchf[3:-1]
                cache_pitch = self.cache_pitch[None, -p_len:]
                cache_pitchf = self.cache_pitchf[None, -p_len:]

            if prof:
                _sync()
                t_f0 = time.perf_counter()

            feats = torch.nn.functional.interpolate(feats.permute(0, 2, 1), scale_factor=2).permute(0, 2, 1)
            feats = feats[:, :p_len, :]
            p_len_tensor = torch.LongTensor([p_len]).to(self.device)
            sid = torch.LongTensor([0]).to(self.device)
            skip_head_value = int(skip_head)
            return_length_value = int(return_length)

            if self.if_f0 == 1:
                infered_audio = run_cuda_graph(
                    self.net_g, "rvc-infer-f0",
                    lambda phone, lengths, coarse, continuous, speaker: self.net_g.infer(
                        phone, lengths, coarse, continuous, speaker,
                        skip_head_value, return_length_value, return_length2,
                    )[0],
                    feats, p_len_tensor, cache_pitch, cache_pitchf, sid,
                )
            else:
                infered_audio = run_cuda_graph(
                    self.net_g, "rvc-infer-no-f0",
                    lambda phone, lengths, speaker: self.net_g.infer(
                        phone, lengths, speaker,
                        skip_head_value, return_length_value, return_length2,
                    )[0],
                    feats, p_len_tensor, sid,
                )

            if prof:
                _sync()
                t_synth = time.perf_counter()
                print(
                    f"[Profile] hubert={1000*(t_hubert-t0):.0f}ms "
                    f"index={1000*(t_index-t_hubert):.0f}ms "
                    f"f0={1000*(t_f0-t_index):.0f}ms "
                    f"synth={1000*(t_synth-t_f0):.0f}ms "
                    f"total={1000*(t_synth-t0):.0f}ms"
                )

            return infered_audio.squeeze(1).float().squeeze()
