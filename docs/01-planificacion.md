# 01 - Planificacion: Modulador de Voz LoL

Fecha: 2026-10-02
Repo: https://github.com/ThiKeiW/modulador-voz-lol
Plataforma objetivo: solo Windows, app de escritorio, espanol latino.

## 1. Objetivo

Generar una salida de voz virtual usando un modulador de voz con
personajes de League of Legends entrenados con IA.

Requisitos del usuario:
1. Solo Windows.
2. Aplicacion de escritorio (PyQt6).
3. Usar modelos pre-entrenados de LoL en espanol latino; si no existen,
   incluir GUI para entrenar nuevos personajes.
4. Espanol latino como idioma principal.
5. Personajes de interes: Aatrox y Ezreal (+ Briar y Yuumi como base ES latino).
6. Hardware disponible: GTX 1650, sin presupuesto extra.

## 2. Analisis de factibilidad

| Aspecto | Resultado |
|---|---|
| Modulacion en tiempo real | Alta (RVC + PyAudio) |
| Clonacion / TTS | Alta (Coqui XTTS v2, 17 idiomas) |
| GUI escritorio | Alta (PyQt6) |
| Proceso local sin nube | Media-Alta (GPU recomendada) |
| Calidad profesional | Alta (modelos SOTA) |

Conclusion: proyecto totalmente factible. Inferencia puede correr en CPU,
entrenamiento requiere GPU NVIDIA con CUDA.

## 3. Modelos encontrados

| Personaje | Idioma real | Fuente |
|---|---|---|
| Aatrox | English (RVC v2, 300 epochs) | `huggingface.co/trinitytf/Aatrox` |
| Ezreal | English (RVC v2, 500 epochs, RMVPE) | `huggingface.co/LilYoda/ezrealLOL` |
| Briar | Espanol Latino (RVC v2, 300 epochs) | `huggingface.co/Parampino/BriarLatino` |
| Yuumi | Espanol Latino (RVC v2) | weights.com / voice-models.com |
| Repo extra ES-LATAM | Personajes animados RVC v2 | `huggingface.co/JackAICovers/RVC` |

Implicacion: Aatrox y Ezreal solo tienen modelo EN hoy. Se incluyen igual,
y la GUI de entrenamiento queda como via para crear sus versiones ES latino.

## 4. Stack elegido

- RVC: `rvc-python` (intentado) -> `hf-rvc` (adoptado, ver proceso).
- TTS: Coqui TTS XTTS v2.
- ML: torch + torchaudio.
- Audio: PyAudio (captura), sounddevice/soundfile/scipy/librosa (I/O y DSP),
  pyworld + torchcrepe (pitch).
- GUI: PyQt6.
- Descarga modelos: huggingface-hub + urllib.

## 5. Arquitectura

```
GUI PyQt6 (main_window, character_panel, voice_controls, download_dialog)
  -> core/audio_capture.py (PyAudio, chunks 4096, 40 kHz)
  -> core/rvc_engine.py (hf-rvc + fallback pitch-shift)
  -> core/tts_engine.py (Coqui XTTS v2)
  -> core/model_manager.py (pretrained + custom)
  -> utils/audio_utils.py (normalize, reverb, echo)
```

## 6. Fases

1. Estructura base + modulos core + GUI (completada).
2. Integracion conversion tiempo real (pendiente).
3. Descarga e integracion modelos (modelos ya descargados en local,
   pendientes de versionar solo metadata, no binarios).
4. Motor TTS en GUI.
5. GUI de entrenamiento.
6. Efectos de audio.
7. Pulido y empaquetado PyInstaller.
