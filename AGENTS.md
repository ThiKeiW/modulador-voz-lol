# AGENTS.md - Voicemod LoL

## Descripcion del Proyecto

Aplicacion de escritorio para Windows que permite generar salidas de voz virtuales usando un modulador de voz con personajes entrenados con IA de League of Legends. Motor de conversion basado en RVC (Retrieval-based Voice Conversion) con soporte para Espanol Latino.

---

## Como Ejecutar el Programa

### Instalacion (Primera vez)

```powershell
# 1. Navegar al directorio del proyecto
cd "D:\ciclo 7\Proyecto-modulador"

# 2. Ejecutar script de instalacion
.\setup.ps1

# 3. Activar entorno virtual
.\.venv\Scripts\Activate.ps1

# 4. Instalar dependencias adicionales (si no se instalaron automaticamente)
pip install -r requirements.txt
```

### Ejecucion Diaria

```powershell
# 1. Navegar al directorio
cd "D:\ciclo 7\Proyecto-modulador"

# 2. Activar entorno virtual
.\.venv\Scripts\Activate.ps1

# 3. Ejecutar la aplicacion
python main.py
```

### Descarga de Modelos Pre-entrenados

```powershell
# Descargar todos los modelos
python scripts/download_models.py

# Descargar uno especifico
python scripts/download_models.py aatrox
python scripts/download_models.py briar_latino
```

---

## Estado Actual de la Implementacion

### Fase 1: Estructura Base ✅ COMPLETADA

| Archivo | Estado | Descripcion |
|---------|--------|-------------|
| `main.py` | ✅ | Punto de entrada, verificacion de dependencias |
| `config.py` | ✅ | Configuracion global (paths, audio, ML, GUI) |
| `requirements.txt` | ✅ | Dependencias del proyecto |
| `setup.ps1` | ✅ | Script de instalacion automatica |
| `README.md` | ✅ | Documentacion del proyecto |

### Core (Logica del Negocio) ✅ COMPLETADA

| Archivo | Estado | Descripcion |
|---------|--------|-------------|
| `core/__init__.py` | ✅ | Package init |
| `core/audio_capture.py` | ✅ | Captura de audio desde microfono con PyAudio |
| `core/rvc_engine.py` | ✅ | Motor de conversion RVC (hf-rvc + fallback PyTorch) |
| `core/tts_engine.py` | ✅ | Motor Text-to-Speech (Coqui TTS) |
| `core/model_manager.py` | ✅ | Gestion de modelos pre-entrenados y custom |

### GUI (Interfaz Grafica) ✅ COMPLETADA

| Archivo | Estado | Descripcion |
|---------|--------|-------------|
| `gui/__init__.py` | ✅ | Package init |
| `gui/main_window.py` | ✅ | Ventana principal con panel de personajes y controles |
| `gui/character_panel.py` | ✅ | Panel de seleccion de personajes con cards |
| `gui/voice_controls.py` | ✅ | Controles de pitch, efectos, dispositivos |
| `gui/download_dialog.py` | ✅ | Dialogo de descarga de modelos |

### Utilidades ✅ COMPLETADAS

| Archivo | Estado | Descripcion |
|---------|--------|-------------|
| `utils/__init__.py` | ✅ | Package init |
| `utils/audio_utils.py` | ✅ | Funciones de procesamiento de audio |

### Scripts ✅ COMPLETADOS

| Archivo | Estado | Descripcion |
|---------|--------|-------------|
| `scripts/download_models.py` | ✅ | Descarga de modelos pre-entrenados |

---

## Implementaciones Pendientes

### Fase 2: Integracion del Motor de Conversion (PRIORIDAD ALTA)

- [ ] **Conectar audio_capture con rvc_engine**: Integrar la captura de microfono con el motor de conversion para procesamiento en tiempo real
- [ ] **Implementar ConversionThread**: Hilo separado para conversion sin bloquear la GUI
- [ ] **Reproducir audio convertido**: Agregar salida de audio con sounddevice para escuchar la voz convertida
- [ ] **Latencia objetivo**: <200ms entre entrada y salida

### Fase 3: Descarga e Integracion de Modelos (PRIORIDAD ALTA)

- [ ] **Descargar modelo Briar ES Latino**: `huggingface.co/Parampino/BriarLatino`
- [ ] **Descargar modelo Aatrox EN**: `huggingface.co/trinitytf/Aatrox`
- [ ] **Descargar modelo Ezreal EN**: `huggingface.co/LilYoda/ezrealLOL`
- [ ] **Probar carga de modelos** en la GUI
- [ ] **Integrar model_manager** con la GUI de personajes

### Fase 4: Motor TTS (PRIORIDAD MEDIA)

- [ ] **Instalar Coqui TTS**: Requiere Python 3.10-3.12
- [ ] **Integrar modo texto-a-voz** en la GUI
- [ ] **Agregar campo de texto** para modo TTS
- [ ] **Conectar TTS con modelos RVC** para clonacion de voz

### Fase 5: GUI de Entrenamiento (PRIORIDAD MEDIA)

- [ ] **Crear ventana de entrenamiento** (`gui/training_widget.py`)
- [ ] **Formulario de carga de audio** (WAV/MP3, 10-30 min)
- [ ] **Configuracion de epochs**, batch size, algoritmo F0
- [ ] **Barra de progreso** durante entrenamiento
- [ ] **Guardar modelo entrenado** en `models/custom/`

### Fase 6: Efectos de Audio (PRIORIDAD BAJA)

- [ ] **Implementar reverb** en `utils/audio_utils.py`
- [ ] **Implementar eco/delay**
- [ ] **Normalizacion de volumen** en tiempo real
- [ ] **Conectar efectos** con checkboxes de la GUI

### Fase 7: Pulido y Empaquetado (PRIORIDAD BAJA)

- [ ] **Optimizar rendimiento** de la GUI
- [ ] **Crear iconos** de personajes
- [ ] **Empaquetar con PyInstaller** para distribucion
- [ ] **Testing** en multiples configuraciones de hardware

---

## Dependencias Instaladas

```
PyQt6           6.11.0    - GUI
torch           2.7.1     - ML engine (CUDA 11.8)
torchaudio      2.7.1     - Audio ML
numpy           2.4.6     - Numeros
scipy           1.18.0    - Audio processing
soundfile       0.14.0    - Audio I/O
sounddevice     0.5.5     - Audio I/O
librosa         0.11.0    - Audio analysis
hf-rvc          0.2.1     - RVC voice conversion
faiss-cpu       1.14.3    - Vector search
PyAudio         0.2.14    - Microphone capture
huggingface-hub 1.22.0    - Model downloads
omegaconf       2.3.1     - Config
pydantic        2.13.4    - Data validation
loguru          0.7.3     - Logging
torchcrepe      0.0.24    - Pitch detection
pyworld         0.3.5     - Audio analysis
```

---

## Estructura del Proyecto

```
Proyecto-modulador/
├── main.py                    # Punto de entrada
├── config.py                  # Configuracion global
├── requirements.txt           # Dependencias
├── setup.ps1                  # Script de instalacion
├── README.md                  # Documentacion
├── AGENTS.md                  # Este archivo
│
├── core/
│   ├── __init__.py
│   ├── audio_capture.py       # Captura de microfono (PyAudio)
│   ├── rvc_engine.py          # Motor de conversion RVC (hf-rvc)
│   ├── tts_engine.py          # Motor Text-to-Speech (Coqui TTS)
│   └── model_manager.py       # Gestion de modelos
│
├── gui/
│   ├── __init__.py
│   ├── main_window.py         # Ventana principal PyQt6
│   ├── character_panel.py     # Panel de personajes
│   ├── voice_controls.py      # Controles de pitch/efectos
│   └── download_dialog.py     # Dialogo de descarga
│
├── models/
│   ├── pretrained/            # Modelos de LoL (descargados)
│   │   ├── aatrox/
│   │   ├── ezreal/
│   │   ├── briar_latino/
│   │   └── yuumi_latino/
│   └── custom/                # Modelos entrenados por usuario
│
├── scripts/
│   └── download_models.py     # Descarga de modelos
│
├── utils/
│   ├── __init__.py
│   └── audio_utils.py         # Utilidades de audio
│
└── assets/
    ├── icons/                 # Iconos de personajes
    └── sounds/                # Sonidos del sistema
```

---

## Modelos de League of Legends

### Pre-entrenados (Descargables)

| ID | Personaje | Idioma | Fuente | URL |
|----|-----------|--------|--------|-----|
| `aatrox` | Aatrox | English | HuggingFace | `huggingface.co/trinitytf/Aatrox` |
| `ezreal` | Ezreal | English | HuggingFace | `huggingface.co/LilYoda/ezrealLOL` |
| `briar_latino` | Briar | ES Latino | HuggingFace | `huggingface.co/Parampino/BriarLatino` |
| `yuumi_latino` | Yuumi | ES Latino | Weights.com | `weights.com/models/clm73bkvd22evcctcst9h87ke` |

### Notas de Idioma

- **Aatrox y Ezreal**: Modelos en ingles. Para usar en ES Latino se requiere entrenamiento adicional con audio del doblaje latino
- **Briar y Yuumi**: Modelos en Espanol Latino listos para usar

---

## Comandos Utiles

```powershell
# Verificar entorno
python --version
pip list

# Ejecutar aplicacion
python main.py

# Descargar modelos
python scripts/download_models.py

# Instalar nueva dependencia
pip install <paquete>

# Actualizar dependencias
pip install --upgrade -r requirements.txt

# Verificar GPU
nvidia-smi

# Verificar torch con CUDA
python -c "import torch; print(torch.cuda.is_available())"
```

---

## Solucion de Problemas

### Error: "No module named 'pyaudio'"
```powershell
pip install PyAudio
# Si falla en Windows:
pip install pipwin
pipwin install pyaudio
```

### Error: "No module named 'torch'"
```powershell
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Error: "rvc-python requires faiss-cpu==1.7.3"
```powershell
pip install faiss-cpu  # Instala version mas reciente
pip install rvc-python --no-deps  # Sin dependencias
```

### La GUI no se inicia
```powershell
# Verificar PyQt6
pip install PyQt6
python -c "from PyQt6.QtWidgets import QApplication; print('OK')"
```

### El microfono no funciona
1. Verificar permisos de Windows para microfono
2. Probar con `python -c "import pyaudio; pa=pyaudio.PyAudio(); print(pa.get_device_count(), 'devices')"`
3. Cambiar dispositivo en la GUI (Controles de Voz > Dispositivo)

---

## Proximo Paso Recomendado

**Fase 2: Integrar conversion de voz en tiempo real**

1. Conectar `AudioCapture` con `RVCEngine`
2. Implementar `ConversionThread` para procesamiento async
3. Agregar salida de audio con `sounddevice`
4. Probar con modelo de Briar (ES Latino)

Comando para iniciar:
```powershell
cd "D:\ciclo 7\Proyecto-modulador"
.\.venv\Scripts\Activate.ps1
python main.py
```
