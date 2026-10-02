# Voicemod LoL - Modulador de Voz Virtual con IA

Aplicacion de escritorio para Windows que permite generar salidas de voz virtuales usando un modulador de voz con personajes entrenados con IA de League of Legends.

## Caracteristicas

- **Modulacion de voz en tiempo real** con modelos RVC (Retrieval-based Voice Conversion)
- **Personajes de League of Legends** con modelos pre-entrenados
- **Soporte para Espanol Latino** con modelos entrenados especificamente
- **Interfaz grafica moderna** con tema oscuro
- **Ajustes de pitch** (+/- 12 semitonos)
- **Efectos de audio** (reverb, eco, normalizacion)
- **GUI de entrenamiento** para crear nuevos personajes

## Requisitos

- **OS**: Windows 10/11 (64-bit)
- **Python**: 3.10 - 3.11
- **GPU**: NVIDIA GTX 1650 o superior (recomendado)
- **RAM**: 8 GB minimo, 16 GB recomendado
- **Disco**: 15 GB de espacio libre

## Instalacion

### Opcion 1: Script automatico (recomendado)

```powershell
# Ejecutar en PowerShell
.\setup.ps1
```

### Opcion 2: Instalacion manual

```bash
# 1. Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate

# 2. Instalar PyTorch con CUDA
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118

# 3. Instalar dependencias
pip install -r requirements.txt
```

## Descarga de Modelos

```bash
# Descargar todos los modelos pre-entrenados
python scripts/download_models.py

# Descargar un modelo especifico
python scripts/download_models.py aatrox
python scripts/download_models.py briar_latino
```

## Uso

```bash
# Iniciar la aplicacion
python main.py
```

### Modelos Pre-entrenados

| Personaje | Idioma | Notas |
|-----------|--------|-------|
| Aatrox | English | RVC v2, 300 epochs |
| Ezreal | English | RVC v2, 500 epochs |
| Briar | Espanol Latino | RVC v2, 300 epochs |
| Yuumi | Espanol Latino | RVC v2 |

### Entrenar Nuevo Personaje

Para personajes sin modelo pre-entrenado en Espanol Latino:

1. Recopilar 10-30 minutos de audio del personaje
2. Usar [RVC WebUI](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI) o [Ultimate RVC](https://github.com/JackismyShephard/ultimate-rvc)
3. Colocar el modelo `.pth` en `models/custom/`
4. La aplicacion lo detectara automaticamente

## Estructura del Proyecto

```
Proyecto-modulador/
├── main.py                 # Punto de entrada
├── config.py               # Configuracion global
├── requirements.txt        # Dependencias
├── setup.ps1               # Script de instalacion
│
├── core/
│   ├── audio_capture.py    # Captura de microfono
│   ├── rvc_engine.py       # Motor de conversion RVC
│   ├── tts_engine.py       # Motor Text-to-Speech
│   └── model_manager.py    # Gestion de modelos
│
├── gui/
│   ├── main_window.py      # Ventana principal
│   ├── character_panel.py  # Panel de personajes
│   ├── voice_controls.py   # Controles de voz
│   └── download_dialog.py  # Dialogo de descarga
│
├── models/
│   ├── pretrained/         # Modelos pre-entrenados
│   └── custom/             # Modelos del usuario
│
├── scripts/
│   └── download_models.py  # Script de descarga
│
└── assets/
    ├── icons/              # Iconos de personajes
    └── sounds/             # Sonidos del sistema
```

## Tecnologias

- **Python 3.10+**
- **PyQt6** - Interfaz grafica
- **PyTorch** - Framework de ML
- **RVC** - Conversion de voz
- **Coqui TTS** - Text-to-Speech
- **PyAudio** - Captura de audio
- **librosa** - Procesamiento de audio

## Licencia

Proyecto educativo - Solo para fines de estudio.

## Creditos

- [RVC Project](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion)
- [Coqui TTS](https://github.com/coqui-ai/TTS)
- Modelos de voz de la comunidad RVC
