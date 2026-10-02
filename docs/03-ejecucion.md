# 03 - Ejecucion del programa

## Requisitos

- Windows 10/11 64-bit.
- Python 3.10-3.11 recomendado (3.13 solo modo basico).
- GPU NVIDIA GTX 1650 o superior recomendada.
- 8 GB RAM minimo, 15 GB disco.

## Instalacion primera vez

```powershell
cd "D:\ciclo 7\Proyecto-modulador"
.\setup.ps1
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Si usas Python 3.13 o falla `rvc-python`, usa el nucleo compatible:

```powershell
pip install -r requirements-core.txt
```

## Ejecucion diaria

```powershell
cd "D:\ciclo 7\Proyecto-modulador"
.\.venv\Scripts\Activate.ps1
python main.py
```

Salida esperada:

```
============================================================
  Voicemod LoL - Modulador de Voz Virtual con IA
  v1.0.0 | Espanol Latino | Windows
============================================================
[OK] PyTorch disponible
[OK] PyAudio disponible
...
  Aplicacion iniciada correctamente.
  Selecciona un personaje para comenzar.
```

## Descarga de modelos

```powershell
python scripts/download_models.py
python scripts/download_models.py aatrox
python scripts/download_models.py briar_latino
```

Los binarios `.pth/.index/.mp3` estan ignorados en git por tamano
(ver `.gitignore`). Cada usuario los descarga localmente.

Modelos configurados en `config.py:PRETRAINED_MODELS`:
Aatrox EN, Ezreal EN, Briar ES latino, Yuumi ES latino.

## Verificaciones utiles

```powershell
python --version
pip list
python -c "import torch; print(torch.cuda.is_available())"
nvidia-smi
python -c "from PyQt6.QtWidgets import QApplication; print('OK')"
python -c "import pyaudio; pa=pyaudio.PyAudio(); print(pa.get_device_count(), 'devices')"
```

## Solucion de problemas

- `No module named 'pyaudio'`: `pip install PyAudio` (o pipwin en Windows).
- `No module named 'torch'`: instalar con indice CUDA cu118 o CPU.
- `rvc-python requires faiss-cpu==1.7.3`: instalar `faiss-cpu` reciente
  y luego `pip install rvc-python --no-deps`.
- `fairseq` sin build: omitir por ahora, usar `hf-rvc`.
- GUI no inicia: verificar PyQt6.
- Microfono: permisos Windows + probar device count + cambiar
  dispositivo en Controles de Voz.
