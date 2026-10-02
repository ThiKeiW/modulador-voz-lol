"""
Script para descargar modelos pre-entrenados de League of Legends.
Ejecutar: python scripts/download_models.py
"""
import os
import sys
import urllib.request
import zipfile
from pathlib import Path

# Agregar directorio raiz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import PRETRAINED_DIR, PRETRAINED_MODELS


def download_file(url: str, dest: Path, desc: str = ""):
    """Descarga un archivo con barra de progreso."""
    def hook(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            percent = min(100, (downloaded * 100) // total_size)
            mb_downloaded = downloaded / (1024 * 1024)
            mb_total = total_size / (1024 * 1024)
            print(f"\r  {desc}: {percent}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)", end="", flush=True)

    urllib.request.urlretrieve(url, str(dest), hook)
    print()  # Nueva linea despues de la descarga


def download_all():
    """Descarga todos los modelos pre-entrenados."""
    print("=" * 60)
    print("  Descargando modelos pre-entrenados de LoL")
    print("=" * 60)
    print()

    PRETRAINED_DIR.mkdir(parents=True, exist_ok=True)

    for model_id, info in PRETRAINED_MODELS.items():
        print(f"\n[{model_id.upper()}] {info['name']} - {info['language']}")
        print(f"  {info['description']}")

        model_dir = PRETRAINED_DIR / model_id
        model_dir.mkdir(parents=True, exist_ok=True)

        # Verificar si ya existe
        existing = list(model_dir.glob("*.pth"))
        if existing:
            print(f"  Ya descargado: {existing[0].name}")
            continue

        url = info["url"]
        filename = url.split("/")[-1].split("?")[0]
        save_path = model_dir / filename

        try:
            print(f"  Descargando desde: {url[:60]}...")
            download_file(url, save_path, info["name"])

            # Descomprimir si es zip
            if filename.endswith(".zip"):
                print("  Descomprimiendo...")
                with zipfile.ZipFile(save_path, "r") as z:
                    z.extractall(model_dir)
                save_path.unlink()

            print(f"  OK: Modelo guardado en {model_dir}")

        except Exception as e:
            print(f"  ERROR: {e}")

    print()
    print("=" * 60)
    print("  Descarga completada!")
    print("=" * 60)


def download_specific(model_id: str):
    """Descarga un modelo especifico."""
    info = PRETRAINED_MODELS.get(model_id)
    if not info:
        print(f"Modelo no encontrado: {model_id}")
        print(f"Modelos disponibles: {', '.join(PRETRAINED_MODELS.keys())}")
        return

    print(f"Descargando {info['name']}...")

    model_dir = PRETRAINED_DIR / model_id
    model_dir.mkdir(parents=True, exist_ok=True)

    url = info["url"]
    filename = url.split("/")[-1].split("?")[0]
    save_path = model_dir / filename

    try:
        download_file(url, save_path, info["name"])

        if filename.endswith(".zip"):
            with zipfile.ZipFile(save_path, "r") as z:
                z.extractall(model_dir)
            save_path.unlink()

        print("OK!")

    except Exception as e:
        print(f"ERROR: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        for model_id in sys.argv[1:]:
            download_specific(model_id)
    else:
        download_all()
