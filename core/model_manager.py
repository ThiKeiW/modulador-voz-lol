"""
Gestor de modelos de voz.
Maneja carga, descarga y organizacion de modelos RVC pre-entrenados y custom.
"""
import json
import shutil
import urllib.request
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict

from config import PRETRAINED_DIR, CUSTOM_DIR, PRETRAINED_MODELS


@dataclass
class VoiceModel:
    """Representa un modelo de voz."""
    id: str
    name: str
    game: str
    language: str
    path: str
    pitch_base: int = 0
    description: str = ""
    is_custom: bool = False
    needs_training_es: bool = False
    downloaded: bool = False


class ModelManager:
    """Gestiona los modelos de voz del sistema."""

    def __init__(self):
        self.models: dict[str, VoiceModel] = {}
        self._load_pretrained_registry()
        self._scan_custom_models()

    def _load_pretrained_registry(self):
        """Carga el registro de modelos pre-entrenados."""
        for model_id, info in PRETRAINED_MODELS.items():
            model_dir = PRETRAINED_DIR / model_id
            model_files = list(model_dir.glob("*.pth")) if model_dir.exists() else []

            self.models[model_id] = VoiceModel(
                id=model_id,
                name=info["name"],
                game=info["game"],
                language=info["language"],
                path=str(model_files[0]) if model_files else "",
                pitch_base=info["pitch_base"],
                description=info["description"],
                is_custom=False,
                needs_training_es=info.get("needs_training_es", False),
                downloaded=len(model_files) > 0,
            )

    def _scan_custom_models(self):
        """Escanea modelos personalizados del usuario."""
        if not CUSTOM_DIR.exists():
            return

        for model_dir in CUSTOM_DIR.iterdir():
            if model_dir.is_dir():
                model_files = list(model_dir.glob("*.pth"))
                meta_file = model_dir / "metadata.json"

                if model_files:
                    metadata = {}
                    if meta_file.exists():
                        with open(meta_file, "r", encoding="utf-8") as f:
                            metadata = json.load(f)

                    model_id = f"custom_{model_dir.name}"
                    self.models[model_id] = VoiceModel(
                        id=model_id,
                        name=metadata.get("name", model_dir.name),
                        game=metadata.get("game", "Custom"),
                        language=metadata.get("language", "Unknown"),
                        path=str(model_files[0]),
                        pitch_base=metadata.get("pitch_base", 0),
                        description=metadata.get("description", ""),
                        is_custom=True,
                        downloaded=True,
                    )

    def get_all_models(self) -> list[VoiceModel]:
        """Retorna todos los modelos disponibles."""
        return list(self.models.values())

    def get_downloaded_models(self) -> list[VoiceModel]:
        """Retorna solo modelos descargados/disponibles."""
        return [m for m in self.models.values() if m.downloaded]

    def get_model(self, model_id: str) -> Optional[VoiceModel]:
        """Obtiene un modelo por su ID."""
        return self.models.get(model_id)

    def download_model(self, model_id: str, progress_callback=None) -> bool:
        """
        Descarga un modelo pre-entrenado.

        Args:
            model_id: ID del modelo a descargar
            progress_callback: Funcion de progreso (bytes_downloaded, total_bytes)

        Returns:
            True si la descarga fue exitosa
        """
        model = self.models.get(model_id)
        if not model or model.downloaded:
            return False

        model_info = PRETRAINED_MODELS.get(model_id)
        if not model_info:
            return False

        url = model_info["url"]
        model_dir = PRETRAINED_DIR / model_id
        model_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Determinar nombre del archivo
            filename = url.split("/")[-1].split("?")[0]
            if filename.endswith(".zip"):
                zip_path = model_dir / filename
                self._download_file(url, zip_path, progress_callback)

                # Descomprimir
                import zipfile
                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    zip_ref.extractall(model_dir)
                zip_path.unlink()

                # Actualizar path
                model_files = list(model_dir.glob("*.pth"))
                if model_files:
                    model.path = str(model_files[0])
                    model.downloaded = True
                    return True

            else:
                save_path = model_dir / filename
                self._download_file(url, save_path, progress_callback)
                model.path = str(save_path)
                model.downloaded = True
                return True

        except Exception as e:
            print(f"[ModelManager] Error descargando {model_id}: {e}")
            return False

    def _download_file(self, url: str, save_path: Path, progress_callback=None):
        """Descarga un archivo con progreso."""
        def _reporthook(block_num, block_size, total_size):
            if progress_callback:
                downloaded = block_num * block_size
                progress_callback(downloaded, total_size)

        urllib.request.urlretrieve(url, str(save_path), _reporthook)

    def save_custom_model(
        self,
        model_path: str,
        name: str,
        game: str = "Custom",
        language: str = "Español Latino",
        pitch_base: int = 0,
        description: str = "",
    ) -> str:
        """
        Guarda un modelo entrenado como personalizado.

        Returns:
            ID del modelo guardado
        """
        # Crear directorio
        safe_name = name.lower().replace(" ", "_").replace("/", "_")
        model_dir = CUSTOM_DIR / safe_name
        model_dir.mkdir(parents=True, exist_ok=True)

        # Copiar modelo
        dest_path = model_dir / Path(model_path).name
        shutil.copy2(model_path, dest_path)

        # Guardar metadata
        metadata = {
            "name": name,
            "game": game,
            "language": language,
            "pitch_base": pitch_base,
            "description": description,
        }
        meta_file = model_dir / "metadata.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        # Actualizar registro
        model_id = f"custom_{safe_name}"
        self.models[model_id] = VoiceModel(
            id=model_id,
            name=name,
            game=game,
            language=language,
            path=str(dest_path),
            pitch_base=pitch_base,
            description=description,
            is_custom=True,
            downloaded=True,
        )

        return model_id

    def delete_model(self, model_id: str) -> bool:
        """Elimina un modelo."""
        model = self.models.get(model_id)
        if not model or not model.is_custom:
            return False

        model_dir = CUSTOM_DIR / model_id.replace("custom_", "")
        if model_dir.exists():
            shutil.rmtree(model_dir)

        del self.models[model_id]
        return True
