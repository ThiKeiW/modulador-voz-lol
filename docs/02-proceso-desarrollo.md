# 02 - Proceso de desarrollo actual

## Fase 1 completada: estructura base

Archivos creados y funcionales:

- `main.py`: chequeo de dependencias criticas (PyQt6, numpy) y opcionales
  (torch, pyaudio, rvc), arranque de `gui.main_window.MainWindow`.
- `config.py`: paths, audio (40000 Hz, chunk 4096, mono float32),
  RVC (rmvpe, pitch -12/+12), TTS (xtts_v2, es), registro
  `PRETRAINED_MODELS` con Aatrox/Ezreal/Briar/Yuumi.
- `core/audio_capture.py`: captura PyAudio en hilo, cola + callback,
  listado de dispositivos.
- `core/rvc_engine.py`: version actual usa `hf-rvc` + PyTorch directo,
  con fallback `_apply_pitch_shift` si no hay modelo RVC real.
- `core/tts_engine.py`: wrapper Coqui TTS.
- `core/model_manager.py`: registro pretrained + escaneo `models/custom/`,
  descarga zip/pth, guardado de customs con metadata.json.
- `gui/main_window.py`: ventana 1200x700 (min 900x600), panel personajes,
  controles, visualizador, log, ConversionThread, menu y status bar.
- `gui/character_panel.py`, `gui/voice_controls.py`,
  `gui/download_dialog.py`: UI desacoplada y reutilizable.
- `utils/audio_utils.py`: normalize, remove_silence, speed, reverb, echo.
- `scripts/download_models.py`: descarga todos o por id.
- `setup.ps1`, `requirements.txt`, `requirements-core.txt`, `README.md`.

Estado verificado: `MainWindow` se instancia correctamente, engine reporta
`hf_rvc_available: True, torch_available: True`.

## Problemas encontrados y soluciones

### 1. Python 3.13 vs librerias ML

Sintoma: `faiss-cpu==1.7.3 (from rvc-python)` sin distribucion compatible,
y errores `Requires-Python >=3.9,<3.13`.

Solucion:
- `requirements.txt` flexibilizado (>=, sin pins rotos).
- Nuevo `requirements-core.txt` solo con paquetes compatibles 3.10-3.13.
- `setup.ps1` detecta 3.13 e instala version minima, y usa CUDA 11.8
  si hay NVIDIA o CPU si no.
- `main.py` separa dependencias criticas vs opcionales.
- `core/rvc_engine.py` tolera falta de rvc-python.

### 2. `rvc-python` con dependencias rotas

Sintomas:
- `faiss-cpu==1.7.3` inexistente (solo 1.9+).
- `omegaconf==2.0.6` con metadata invalida (`>=5.1.*`).
- `fairseq==0.12.2` sin build en Windows / conflicto omegaconf/hydra.
- `numpy<=1.23.5` incompatible con numpy 2.x ya instalado.

Acciones:
- `pip install faiss-cpu` (1.14.3 OK).
- `pip install rvc-python --no-deps` (0.1.5 OK).
- `pip install librosa omegaconf praat-parselmouth pydantic
  python-multipart pyworld torchcrepe uvicorn av fastapi
  ffmpeg-python loguru` con versiones recientes OK.
- `fairseq` queda pendiente (no bloquea inference basica).

### 3. Migracion a `hf-rvc`

Se instalo `git+https://github.com/esnya/hf-rvc.git` (0.2.1) con
transformers/safetensors, sin legacy pins. `core/rvc_engine.py` se
reescribio para ese backend. Conversion real completa RVC queda para
Fase 2; hoy el engine carga `.pth` y aplica pitch-shift funcional.

### 4. Entorno del usuario

- Globo: tenia `.venv` (3.13) y `.venv311`.
- App corre en Python 3.11.9: `[OK] PyTorch, [OK] PyAudio,
  [--] rvc-python (conversion basica)`.
- Modelos locales ya descargados (no se suben a git por tamano):
  Aatrox .pth 52 MB + .index 189 MB, Ezreal .pth 52 MB + .index 94 MB
  + mp3 8 MB, Briar/Yuumi .pth 52 MB c/u.

## Pendiente (Fase 2 en adelante)

- Conectar `AudioCapture` -> `RVCEngine` -> salida `sounddevice`
  con latencia <200 ms.
- Probar carga de Briar ES latino en GUI.
- Integrar `model_manager` con panel personajes.
- TTS, entrenamiento, efectos, PyInstaller.
