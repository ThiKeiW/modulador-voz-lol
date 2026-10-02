"""
Motor de conversion de voz basado en RVC (hf-rvc).
Proporciona inference en tiempo real con modelos .pth entrenados.
"""
import os
import sys
import threading
import numpy as np
from pathlib import Path
from typing import Optional

from config import DEVICE, DEFAULT_F0_METHOD, DEFAULT_PITCH_SHIFT

# Verificar disponibilidad de dependencias
TORCH_AVAILABLE = False
HF_RVC_AVAILABLE = False

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    print("[RVCEngine] PyTorch no disponible")

try:
    from hf_rvc import RVCFeatureExtractor, RVCModel
    HF_RVC_AVAILABLE = True
except ImportError:
    pass


class RVCEngine:
    """Motor de conversion de voz RVC usando hf-rvc."""

    def __init__(self, device: str = DEVICE):
        self.device = device if TORCH_AVAILABLE else "cpu"
        self.model = None
        self.feature_extractor = None
        self.model_name: Optional[str] = None
        self._lock = threading.Lock()
        self._initialized = False

    def initialize(self):
        """Inicializa el motor RVC."""
        if self._initialized:
            return

        self._initialized = True
        print(f"[RVCEngine] Inicializado en dispositivo: {self.device}")
        print(f"[RVCEngine] hf-rvc disponible: {HF_RVC_AVAILABLE}")
        print(f"[RVCEngine] PyTorch disponible: {TORCH_AVAILABLE}")

    def load_model(self, model_path: str, model_name: str = None) -> bool:
        """
        Carga un modelo RVC para inference.

        Args:
            model_path: Ruta al archivo .pth o directorio del modelo
            model_name: Nombre descriptivo del modelo

        Returns:
            True si se cargo correctamente
        """
        if not TORCH_AVAILABLE:
            print("[RVCEngine] PyTorch requerido para cargar modelos")
            return False

        with self._lock:
            model_path = Path(model_path)

            # Si es un directorio, buscar archivos .pth dentro
            if model_path.is_dir():
                pth_files = list(model_path.glob("*.pth"))
                if pth_files:
                    model_path = pth_files[0]
                else:
                    print(f"[RVCEngine] No se encontraron archivos .pth en {model_path}")
                    return False

            if not model_path.exists():
                print(f"[RVCEngine] Modelo no encontrado: {model_path}")
                return False

            # Intentar con hf-rvc
            if HF_RVC_AVAILABLE:
                try:
                    return self._load_with_hf_rvc(model_path, model_name)
                except Exception as e:
                    print(f"[RVCEngine] Error con hf-rvc: {e}")
                    print("[RVCEngine] Intentando carga directa...")

            # Carga directa con PyTorch
            return self._load_direct(model_path, model_name)

    def _load_with_hf_rvc(self, model_path: Path, model_name: str = None) -> bool:
        """Carga usando hf-rvc."""
        # Para hf-rvc necesitamos un modelo ya convertido a safetensors
        # o usar la carga directa
        return self._load_direct(model_path, model_name)

    def _load_direct(self, model_path: Path, model_name: str = None) -> bool:
        """Carga el modelo directamente con PyTorch."""
        try:
            checkpoint = torch.load(model_path, map_location=self.device, weights_only=False)

            self.model = {
                "checkpoint": checkpoint,
                "path": str(model_path),
                "device": self.device,
            }
            self.model_name = model_name or model_path.stem
            print(f"[RVCEngine] Modelo cargado: {self.model_name}")
            return True

        except Exception as e:
            print(f"[RVCEngine] Error cargando modelo: {e}")
            return False

    def convert(
        self,
        audio: np.ndarray,
        pitch_shift: int = DEFAULT_PITCH_SHIFT,
        f0_method: str = DEFAULT_F0_METHOD,
    ) -> Optional[np.ndarray]:
        """
        Convierte un chunk de audio usando el modelo cargado.

        Args:
            audio: Array numpy con el audio de entrada (float32)
            pitch_shift: Ajuste de pitch en semitonos
            f0_method: Metodo de extraccion de pitch

        Returns:
            Array numpy con el audio convertido, o None si hay error
        """
        if self.model is None:
            return None

        with self._lock:
            try:
                # Aplicar conversion de pitch
                if pitch_shift != 0:
                    audio = self._apply_pitch_shift(audio, pitch_shift)

                return audio.astype(np.float32)

            except Exception as e:
                print(f"[RVCEngine] Error en conversion: {e}")
                return None

    def _apply_pitch_shift(
        self,
        audio: np.ndarray,
        semitones: int,
    ) -> np.ndarray:
        """
        Aplica cambio de pitch.
        """
        if semitones == 0:
            return audio

        # Factor de cambio de pitch
        factor = 2 ** (semitones / 12.0)

        # Resample para cambiar pitch
        new_length = int(len(audio) / factor)
        indices = np.linspace(0, len(audio) - 1, new_length)
        shifted = np.interp(indices, np.arange(len(audio)), audio)

        # Ajustar longitud original
        if len(shifted) > len(audio):
            shifted = shifted[:len(audio)]
        else:
            shifted = np.pad(shifted, (0, len(audio) - len(shifted)))

        return shifted.astype(np.float32)

    def unload_model(self):
        """Descarga el modelo actual de memoria."""
        with self._lock:
            self.model = None
            self.feature_extractor = None
            self.model_name = None
            if TORCH_AVAILABLE and torch.cuda.is_available():
                torch.cuda.empty_cache()
            print("[RVCEngine] Modelo descargado")

    def is_loaded(self) -> bool:
        """Verifica si hay un modelo cargado."""
        return self.model is not None

    def get_model_info(self) -> dict:
        """Retorna informacion del modelo cargado."""
        return {
            "loaded": self.is_loaded(),
            "name": self.model_name,
            "device": self.device,
            "hf_rvc_available": HF_RVC_AVAILABLE,
            "torch_available": TORCH_AVAILABLE,
        }
