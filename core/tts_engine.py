"""
Motor de Text-to-Speech basado en Coqui TTS (XTTS v2).
Permite generar voz a partir de texto usando modelos de personajes.
"""
import threading
import numpy as np
from pathlib import Path
from typing import Optional

from config import TTS_MODEL, DEFAULT_LANGUAGE, TTS_SAMPLE_RATE


class TTSEngine:
    """Motor de sintesis de voz texto-a-voz."""

    def __init__(self):
        self.model = None
        self._lock = threading.Lock()
        self._initialized = False

    def initialize(self):
        """Inicializa el motor TTS."""
        if self._initialized:
            return

        try:
            from TTS.api import TTS as CoquiTTS
            self.model = CoquiTTS(TTS_MODEL)
            self._initialized = True
            print("[TTSEngine] Inicializado con XTTS v2")

        except ImportError:
            print(
                "[TTSEngine] Coqui TTS no disponible. "
                "Instala con: pip install coqui-tts"
            )
        except Exception as e:
            print(f"[TTSEngine] Error inicializando: {e}")

    def synthesize(
        self,
        text: str,
        speaker_wav: Optional[str] = None,
        language: str = DEFAULT_LANGUAGE,
        output_path: Optional[str] = None,
    ) -> Optional[np.ndarray]:
        """
        Sintetiza voz a partir de texto.

        Args:
            text: Texto a convertir en voz
            speaker_wav: Ruta a audio de referencia para clonacion
            language: Codigo de idioma (es, en, fr, etc.)
            output_path: Ruta para guardar el audio generado

        Returns:
            Array numpy con el audio generado, o None si hay error
        """
        if not self._initialized or self.model is None:
            print("[TTSEngine] Motor no inicializado")
            return None

        with self._lock:
            try:
                if output_path:
                    self.model.tts_to_file(
                        text=text,
                        file_path=output_path,
                        speaker_wav=speaker_wav,
                        language=language,
                    )
                    import soundfile as sf
                    audio, sr = sf.read(output_path)
                    return audio.astype(np.float32)

                else:
                    audio = self.model.tts(
                        text=text,
                        speaker_wav=speaker_wav,
                        language=language,
                    )
                    return np.array(audio, dtype=np.float32)

            except Exception as e:
                print(f"[TTSEngine] Error en sintesis: {e}")
                return None

    def synthesize_with_model(
        self,
        text: str,
        model_path: str,
        language: str = DEFAULT_LANGUAGE,
    ) -> Optional[np.ndarray]:
        """
        Sintetiza usando un modelo RVC especifico como referencia.

        Args:
            text: Texto a sintetizar
            model_path: Ruta al modelo RVC .pth
            language: Codigo de idioma

        Returns:
            Array numpy con el audio generado
        """
        if not self._initialized or self.model is None:
            return None

        with self._lock:
            try:
                audio = self.model.tts(
                    text=text,
                    language=language,
                )
                return np.array(audio, dtype=np.float32)

            except Exception as e:
                print(f"[TTSEngine] Error: {e}")
                return None

    def is_available(self) -> bool:
        """Verifica si el motor TTS esta disponible."""
        return self._initialized and self.model is not None

    def get_info(self) -> dict:
        """Retorna informacion del motor TTS."""
        return {
            "available": self.is_available(),
            "model": TTS_MODEL if self._initialized else None,
        }
