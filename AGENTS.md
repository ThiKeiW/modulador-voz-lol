# AGENTS.md - Voicemod LoL

## Descripcion del Proyecto

Aplicacion de escritorio para Windows que permite generar salidas de voz virtuales usando un modulador de voz con personajes entrenados con IA de League of Legends. Motor de conversion RVC real (vendorizado del proyecto oficial) con soporte para Espanol Latino.

Repo: https://github.com/ThiKeiW/modulador-voz-lol (rama `main`).
Directorio local: `D:\ciclo 7\Proyecto-modulador\modulador-voz-lol\`.

---

## Como Ejecutar el Programa

### Instalacion (Primera vez)

```powershell
# 1. Navegar al directorio del proyecto
cd "D:\ciclo 7\Proyecto-modulador\modulador-voz-lol"

# 2. Ejecutar script de instalacion
.\setup.ps1

# 3. Activar entorno virtual
.\.venv\Scripts\Activate.ps1

# 4. Instalar dependencias
pip install -r requirements.txt

# 5. Descargar assets del motor (UNA sola vez, ~500-600MB: hubert + rmvpe)
python scripts/download_assets.py

# 6. Descargar modelos de personajes
python scripts/download_models.py
```

### Ejecucion Diaria

```powershell
cd "D:\ciclo 7\Proyecto-modulador\modulador-voz-lol"
.\.venv\Scripts\Activate.ps1
python main.py
```

Seleccionar un personaje descargado -> Iniciar. Recomendado probar primero
con Aatrox o Ezreal (tienen `.index`, suenan mejor que Briar/Yuumi).

### Descarga de Modelos Pre-entrenados

```powershell
# Todos los modelos
python scripts/download_models.py

# Uno especifico
python scripts/download_models.py aatrox
python scripts/download_models.py briar_latino
```

Los binarios `.pth` / `.index` / audios estan ignorados en git por tamano
(ver `.gitignore`); cada clon los descarga localmente.

---

## Estado Actual de la Implementacion

### Fase 1: Estructura Base ✅ COMPLETADA

Base del proyecto: `main.py`, `config.py`, `requirements*.txt`, `setup.ps1`,
`README.md`, GUI inicial PyQt6.

### Fase 2: Motor de Conversion Real ✅ FUNCIONAL

El placeholder de pitch-shift fue reemplazado por inferencia RVC real
(microfono -> HuBERT -> sintetizador -> parlante, con crossfade SOLA).
Probado por el usuario en Windows + GTX 1650 con Yuumi.

| Archivo | Estado | Descripcion |
|---------|--------|-------------|
| `core/rvc_backend/` | ✅ | Arquitectura RVC vendorizada del repo oficial (MIT): `models.py` (sintetizador v1/v2 con/sin f0), `hubert.py` (features via `transformers`, sin fairseq), `rmvpe.py` (pitch), `gpu_rules.py`, `transforms/modules/attentions/commons`, `LICENSE` |
| `core/rvc_engine.py` | ✅ | Motor real: carga `.pth` (v1/v2 auto-detectado + verificacion dura de pesos que revienta en vez de ruido silencioso), hubert, indice faiss opcional, F0 (rmvpe/pm/harvest) |
| `core/rvc_stream.py` | ✅ | Buffer deslizante + crossfade SOLA + resample por bloque |
| `core/conversion_thread.py` | ✅ | Hilo tiempo real: `AudioCapture` -> `RVCEngine` -> `sounddevice`, con senales de estado/error; warning solo si el COMPUTO supera el bloque |
| `core/audio_capture.py` | ✅ | Captura PyAudio con lecturas chicas (2048) y cola acotada a 2 bloques; overflows logueados, no matan el hilo |
| `scripts/download_assets.py` | ✅ | Descarga `hubert_base` y `rmvpe.pt` |
| `docs/04-fase2-rvc-real.md` | ✅ | Bitacora completa de la fase (decision hf-rvc, fixes, profiling) |

**Decision arquitectonica clave**: `hf-rvc` descartado — solo implementa
v1/256-dim y los 4 modelos son v2/768-dim en contenido (`emb_phone`
`(192,768)` medido en los `.pth`); con su `strict=False` la salida seria
ruido sin error. Ver `docs/04-fase2-rvc-real.md`.

### Fase 3: Descarga e Integracion de Modelos ✅ FUNCIONAL

| Archivo | Estado | Descripcion |
|---------|--------|-------------|
| `core/model_manager.py` | ✅ | Registro pretrained + escaneo `models/custom/`; detecta `.pth` + `.index` por personaje |
| `scripts/download_models.py` | ✅ | Descarga todos o por ID |
| `gui/download_dialog.py` | ✅ | Descarga desde la GUI con progreso |
| `gui/main_window.py` | ✅ | Arranque real (resuelve modelo, carga motor, arranca hilo); IDs `briar_latino`/`yuumi_latino` corregidos |

### Fase 4: Motor TTS ❌ DESCARTADA (alcance final: solo voz en vivo)

Decision del usuario (2026-10-06): la app es solo conversion en vivo.
`core/tts_engine.py` queda como referencia sin cablear; no integrar a GUI.

### Fase 5: GUI de Entrenamiento ❌ DESCARTADA (entrenamiento externo)

Decision del usuario (2026-10-06): el entrenamiento se hace fuera de la app
con **Ultimate RVC**. Flujo oficial: entrenar ahi -> copiar `.pth` (+`.index`
si hay) a `models/custom/` -> autodetectado por `ModelManager`. No se
implementara `gui/training_widget.py`.

### Fase 6: Efectos de Audio 🔶 PARCIAL (solo slider `index_rate`)

Reverb/eco (`utils/audio_utils.py`), formant shift y noise-gate: descartados
(recorte consciente, voz "seca" del sintetizador es aceptable).
Pendiente minimo: exponer `index_rate` (hoy fijo 0.5 con indice / 0 sin el)
como slider en la GUI.

### Fase 7: Empaquetado 🔄 EN CURSO (`.exe` para compartir)

Alcance final: uso personal + distribuir `.exe` a terceros. Ver
`voicemod-lol.spec` + `build_exe.ps1`. Iconos de personajes y tests
automatizados: descartados.

---

## Parametros de Tiempo Real Actuales (`config.py`)

| Parametro | Valor | Nota |
|-----------|-------|------|
| `SAMPLE_RATE` (dispositivo) | 48000 | Separado de la tasa interna del modelo (40k) |
| `REALTIME_BLOCK_MS` | 200 | 150 daba cortes; el computo va sobrado (~136ms) |
| `REALTIME_CROSSFADE_MS` | 80 | Subido de 50 (transiciones menos roboticas) |
| `REALTIME_EXTRA_MS` | 1000 | Lever principal de costo (reproceso sin cache) |
| `DEVICE` | `cuda:0` si `torch.cuda.is_available()` | La deteccion vieja por `CUDA_VISIBLE_DEVICES` siempre caia a CPU |
| `PROFILE_RVC` | True | Profiling por etapa con `cuda.synchronize()` |
| OutputStream | `latency=0.1` | `"low"` daba underruns en WASAPI |

Latencia realista: ~250-400ms por bloque (el propio RVC-WebUI usa 250ms).
La meta original <200ms del plan inicial no es alcanzable con esta calidad.

## Limitaciones Conocidas (recortes conscientes, no bugs)

- **Briar y Yuumi sin `.index`** -> `index_rate=0`, algo menos de calidad.
- Sin `index_rate` en GUI (pendiente minimo de Fase 6), sin formant
  shift/noise-gate, sin tests. `gui/config.py` (duplicado muerto, 0 imports)
  eliminado el 2026-10-06.

---

## Dependencias Instaladas

```
PyQt6               - GUI
torch + torchaudio  - ML engine (CUDA 11.8; fp32 forzado en GTX serie 16)
transformers        - HuBERT (reemplaza a fairseq, que no compila en Windows)
faiss-cpu           - Retrieval del .index
numpy / scipy / soundfile / sounddevice / librosa - Audio
PyAudio             - Captura de microfono
praat-parselmouth   - f0_method="pm" | pyworld - f0_method="harvest"
huggingface-hub     - Descargas | omegaconf / pydantic / loguru - utils
```

Fuera: `hf-rvc` (incompatible v1-only), `torchcrepe` (metodo "crepe" nunca
existio de verdad), `fairseq` (no compila en Windows).

---

## Estructura del Proyecto

```
modulador-voz-lol/
├── main.py                    # Punto de entrada (+ logging.basicConfig)
├── config.py                  # Configuracion global y tiempo real
├── requirements.txt           # Full (Python 3.10-3.12)
├── requirements-core.txt      # Rama Python 3.13 de setup.ps1
├── setup.ps1                  # Instalacion (detecta GPU/CUDA)
├── README.md / AGENTS.md
│
├── core/
│   ├── audio_capture.py       # Captura PyAudio (lecturas chicas, cola acotada)
│   ├── conversion_thread.py   # Hilo tiempo real + metricas separadas
│   ├── rvc_engine.py          # Motor RVC real + verificacion dura de pesos
│   ├── rvc_stream.py          # Buffer deslizante + SOLA + resample
│   ├── rvc_backend/           # Vendorizado oficial (MIT): models, hubert,
│   │                          # rmvpe, gpu_rules, modules, LICENSE
│   ├── model_manager.py       # Registro pretrained + custom (.pth + .index)
│   └── tts_engine.py          # ⚠️ SIN USO (Fase 4 descartada, solo referencia)
│
├── gui/
│   ├── main_window.py         # Arranque real + visualizador + log
│   ├── character_panel.py     # Cards ES/EN por personaje
│   ├── voice_controls.py     # Pitch, F0, efectos, dispositivos
│   └── download_dialog.py     # Descarga con progreso
│
├── models/
│   ├── pretrained/            # .pth + .index (IGNORADOS en git) + README.md
│   └── custom/                # Customs del usuario (ignorado, autodetectado)
│
├── scripts/
│   ├── download_models.py     # Personajes (Aatrox/Ezreal/Briar/Yuumi)
│   └── download_assets.py     # hubert + rmvpe (~500-600MB, una vez)
│
├── utils/audio_utils.py       # DSP suelto (SIN conectar a pipeline vivo)
├── docs/                      # 01-plan · 02-proceso · 03-ejecucion · 04-fase2
└── assets/                    # icons/, sounds/ (vacios)
```

---

## Modelos de League of Legends

| ID | Personaje | Idioma | `.index` | Notas |
|----|-----------|--------|----------|-------|
| `aatrox` | Aatrox | English | ✅ 189MB | RVC v2, f0, 40k |
| `ezreal` | Ezreal | English | ✅ 94MB | RVC v2, f0, 40k |
| `briar_latino` | Briar | ES Latino | ❌ | RVC v2, f0, 40k, `index_rate=0` |
| `yuumi_latino` | Yuumi | ES Latino | ❌ | RVC v2, f0, 40k, `index_rate=0` |

Arquitectura medida en los 4 `.pth`: contenido 768-dim + gin 256-dim
(hibrido comunitario v2, no oficial puro). El `version: "v2"` del checkpoint
selecciona la clase 768 vendorizada, cuyo `gin_channels` viene del propio
checkpoint — verificado clave-por-clave (456/457 coinciden).

---

## Comandos Utiles

```powershell
# App
python main.py

# Modelos y assets
python scripts/download_models.py
python scripts/download_assets.py

# Entorno
python --version; pip list
nvidia-smi
python -c "import torch; print(torch.cuda.is_available())"
```

---

## Solucion de Problemas

### La conversion suena a ruido / no al personaje
Revisar el log de carga: `get_synthesizer` revienta con `RuntimeError` si
la arquitectura no calza. Si cargo sin error, verificar `device=cuda:0`
en el log; si dice `cpu` con GPU presente, reinstalar torch con CUDA.

### Latencia ~1000ms+ por bloque
Causa conocida: todo en CPU. Verificar `device=cuda:0` en el log de carga.
Si la GPU existe pero torch no la ve, reinstalar torch del index CUDA.

### Cortes cada ~200ms / palabras separadas
Ver: `latency=0.1` en OutputStream, `REALTIME_BLOCK_MS=200`,
overflows `[AudioCapture] Input overflow #N` en log (indican que la
captura, no el motor, pierde audio).

### `ModuleNotFoundError: configs`
Ya corregido via `gpu_rules.py`. Si reaparece, revisar imports de
`core/rvc_backend/rmvpe.py`.

### Microfono no funciona
1. Permisos de Windows para microfono
2. `python -c "import pyaudio; pa=pyaudio.PyAudio(); print(pa.get_device_count())"`
3. Cambiar dispositivo en Controles de Voz
