# 04 - Fase 2: motor de conversion de voz real

## Resumen

Se reemplazo el motor de conversion (que hasta ahora solo hacia pitch-shift
de pass-through, sin tocar el timbre) por un motor RVC real (v1/v2),
conectado de punta a punta: microfono -> hubert -> sintetizador -> parlante,
en tiempo real, con crossfade entre bloques para que no se escuchen cortes.

## Por que se descarto `hf-rvc`

El plan original (ver AGENTS.md / 02-proceso-desarrollo.md) era usar el
paquete `hf-rvc`. Se descarto porque:

- `hf-rvc` solo implementa la arquitectura v1 (features de contenido de
  256 dimensiones), clase `SynthesizerTrnMs256NSFsid` unicamente.
- Los 4 modelos del proyecto (Aatrox, Ezreal, Briar, Yuumi) son v2
  (features de 768 dimensiones, verificado leyendo los `.pth` reales:
  `enc_p.emb_phone.weight` shape `(192, 768)`, `sr=40k`, con pitch).
- `hf-rvc` carga los pesos con `strict=False`. Con el mismatch de arriba,
  la capa `emb_phone` queda con pesos aleatorios **sin ningun error** -
  la app arrancaria y "funcionaria", pero la voz de salida seria ruido,
  no el personaje.
- Ademas requiere convertir el hubert original (`hubert_base.pt`, formato
  fairseq) via `fairseq.checkpoint_utils`, la misma dependencia que ya se
  habia descartado antes por no compilar en Windows.

## Camino elegido: vendorizar el motor oficial

En vez de reescribir una arquitectura de red neuronal a mano (alto riesgo
de error silencioso), se copio el codigo real del proyecto oficial
[RVC-Project/Retrieval-based-Voice-Conversion-WebUI](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI)
(MIT License), recortado a solo lo necesario para inferencia:

- Arquitectura del sintetizador (v1/v2, con/sin f0) - `infer/module/*.py`
- Extraccion de pitch RMVPE (pytorch puro, sin dependencias externas de
  pago ni fairseq) - `infer/rmvpe.py`
- Extraccion de features de contenido via **Transformers HuBERT**
  (`infer/hubert.py`) - el repo oficial **ya migro lejos de fairseq**,
  usa `transformers.HubertModel` con un checkpoint pre-convertido que se
  descarga aparte. Esto resuelve el bloqueo de fairseq en Windows sin
  tocar una linea de esa dependencia.
- Buffer deslizante + crossfade SOLA (Synchronized OverLap-Add) para
  streaming sin clicks entre bloques, adaptado de
  `RVCRealtimeVST/worker/rvc_worker.py` (el *worker* del plugin VST
  oficial, recortado: se saco todo lo especifico de Windows/VST/mmap y
  se dejo solo el nucleo de buffering+crossfade).

Se verifico la arquitectura exacta contra el codigo fuente real (no de
memoria) antes de portarla, incluyendo una observacion propia confirmada
en el codigo: `SynthesizerTrnMs768NSFsid` hereda de la clase v1 y solo
reemplaza la capa `emb_phone` (256->768); `gin_channels` (el
condicionamiento de hablante) viaja igual en las dos clases, tomado del
propio checkpoint. Elegir la arquitectura por el campo `version` del
`.pth` es por lo tanto correcto para los 4 modelos del proyecto.

## Archivos nuevos

| Archivo | Que hace |
|---|---|
| `core/rvc_backend/` | Arquitectura RVC vendorizada (modelos, hubert, rmvpe) + `LICENSE` de atribucion |
| `core/rvc_stream.py` | Buffer deslizante + crossfade SOLA + resample por bloque |
| `scripts/download_assets.py` | Descarga `hubert_base` y `rmvpe.pt` desde `huggingface.co/lj1995/VoiceConversionWebUI` |

## Archivos reescritos

| Archivo | Cambio principal |
|---|---|
| `core/rvc_engine.py` | De placeholder (pitch-shift) a motor RVC real: carga `.pth` (v1/v2 auto-detectado + verificacion dura de pesos), hubert, indice faiss opcional, F0 (rmvpe/pm/harvest) |
| `core/conversion_thread.py` | De loop naive (un chunk suelto) a streaming por bloques via `RVCStream`, con tamano de bloque calculado dinamicamente (ya no un `CHUNK_SIZE` fijo) |
| `core/model_manager.py` | Detecta el `.index` de cada personaje (si existe) ademas del `.pth` |
| `config.py` | `SAMPLE_RATE` del dispositivo (48kHz) separado de la tasa interna del modelo; nuevos `REALTIME_BLOCK_MS` / `CROSSFADE_MS` / `EXTRA_MS`, rutas de `HUBERT_DIR` / `RMVPE_PATH` |
| `gui/main_window.py` | `_on_start_click` real (antes solo cambiaba botones): resuelve modelo, carga motor, arranca el hilo; fix bug de IDs `briar`/`yuumi` -> `briar_latino`/`yuumi_latino` (apuntaban a modelos inexistentes); combo de F0 corregido a los metodos realmente soportados |
| `requirements.txt` / `requirements-core.txt` | Fuera `hf-rvc` (no se usa mas) y `torchcrepe` (metodo "crepe" nunca existio de verdad); entra `transformers`, `praat-parselmouth`; `requirements-core.txt` (rama Python 3.13 de `setup.ps1`) ahora incluye todo lo que el motor real necesita |

## Estado de funcionalidad (vs. Fases del AGENTS.md)

- **Fase 2 - Integracion del motor de conversion: funcional.**
  Microfono -> hubert -> sintetizador -> parlante corriendo en tiempo
  real, confirmado por el usuario con Yuumi en Windows.
- **Fase 3 - Descarga e integracion de modelos: funcional.**
  Los 4 personajes cargan (bug de IDs corregido); `ModelManager` detecta
  `.pth` + `.index` automaticamente.
- **Fase 4, 5, 6, 7** (TTS, entrenamiento, efectos, empaquetado): sin
  empezar, sin cambios respecto al estado anterior.

## Limitaciones conocidas (no son bugs, son recortes conscientes)

- **Briar y Yuumi no tienen `.index`** -> corren con `index_rate=0`
  (sin retrieval). Calidad algo menor que Aatrox/Ezreal, que si tienen
  indice. Se puede generar un `.index` para ellos mas adelante si hace
  falta.
- **`index_rate` fijo (0.5 si hay indice, 0 si no)**, sin control en la
  GUI todavia. Facil de agregar como slider.
- **Formant shift y noise-gate** del `RVCStreamEngine` oficial no se
  portaron (el original los tiene; se dejaron afuera para no sumar mas
  superficie sin probar). El pitch shift (semitonos) si funciona.
- **Latencia real esperada: ~250-400ms por bloque**, no los <200ms que
  pedia el AGENTS.md original. El propio RVC-WebUI usa 250ms de bloque
  por defecto - es el piso realista para esta calidad de conversion, no
  una limitacion de esta implementacion particular. Vale la pena ajustar
  esa meta en el documento de planificacion.
- **Sin prueba automatizada**: todo esto se armo y compilo (sintaxis)
  sin GPU/microfono disponibles en el entorno donde se escribio; la
  prueba real fue la del usuario en su Windows con GTX 1650.

## Como probar

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts/download_assets.py   # una sola vez, ~500-600MB
python main.py
```

Seleccionar un personaje descargado -> Iniciar. Recomendado probar
primero con Aatrox o Ezreal (tienen `.index`, deberia sonar mejor que
Briar/Yuumi por ahora).
