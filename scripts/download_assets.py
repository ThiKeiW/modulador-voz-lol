"""
scripts/download_assets.py

Descarga los assets compartidos que necesita el motor RVC real y que NO
son parte de ningun personaje (por eso no viven en models/pretrained/):

- models/hubert_base/{config.json, preprocessor_config.json, pytorch_model.bin}
    Extractor de features de contenido (HuBERT/ContentVec), formato
    Transformers -- NO el .pt original de fairseq. Esto es justo lo que
    evita la dependencia de fairseq que ya habiamos descartado por no
    compilar en Windows (ver docs/02-proceso-desarrollo.md).

- models/rmvpe/rmvpe.pt
    Modelo de extraccion de pitch (F0) recomendado, PyTorch puro.

Fuente: https://huggingface.co/lj1995/VoiceConversionWebUI (el mismo
repo que usa RVC-WebUI oficial para estos dos assets).

Uso:
    python scripts/download_assets.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import HUBERT_DIR, RMVPE_PATH

REPO_ID = "lj1995/VoiceConversionWebUI"
HUBERT_FILES = ["hubert_base/config.json", "hubert_base/preprocessor_config.json", "hubert_base/pytorch_model.bin"]
RMVPE_FILE = "rmvpe.pt"


def main():
    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        print("Falta huggingface_hub. Instala con: pip install huggingface_hub")
        sys.exit(1)

    HUBERT_DIR.mkdir(parents=True, exist_ok=True)
    RMVPE_PATH.parent.mkdir(parents=True, exist_ok=True)

    print(f"Descargando hubert_base en {HUBERT_DIR} ...")
    for filename in HUBERT_FILES:
        dest_name = Path(filename).name
        if (HUBERT_DIR / dest_name).is_file():
            print(f"  ya existe: {dest_name}")
            continue
        local_path = hf_hub_download(repo_id=REPO_ID, filename=filename)
        (HUBERT_DIR / dest_name).write_bytes(Path(local_path).read_bytes())
        print(f"  OK: {dest_name}")

    print(f"\nDescargando rmvpe.pt en {RMVPE_PATH} ...")
    if RMVPE_PATH.is_file():
        print("  ya existe")
    else:
        local_path = hf_hub_download(repo_id=REPO_ID, filename=RMVPE_FILE)
        RMVPE_PATH.write_bytes(Path(local_path).read_bytes())
        print("  OK")

    print("\nListo. Ya se puede cargar un modelo real con RVCEngine.load_model(...).")


if __name__ == "__main__":
    main()
