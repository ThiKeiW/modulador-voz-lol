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

## Fix post-prueba: GPU nunca se usaba

Primera prueba real dio ~1000-1240ms por bloque (vs. objetivo ~250-400ms).
Causa: `config.DEVICE` detectaba GPU mirando la variable de entorno
`CUDA_VISIBLE_DEVICES`, que no esta seteada por defecto en una PC normal
aunque haya GPU -- siempre caia a `"cpu"`. Todo el pipeline (hubert +
sintetizador + RMVPE) corria en CPU en vez de la GTX 1650. Corregido para
detectar con `torch.cuda.is_available()` (en `config.py` y como red de
seguridad adicional en `RVCEngine.__init__`). Tambien se agrego
`logging.basicConfig` en `main.py`: antes los `logger.info(...)`
(incluido el que hubiera mostrado `device=cpu`) no se veian en consola.

Despues de este fix, el log de carga de modelo muestra el device usado:
`[RVCEngine] Modelo cargado: ... device=cuda:0` (o `cpu` si de verdad no
hay GPU disponible para torch). Si sigue en `cpu` con GPU presente, el
wheel de torch instalado no tiene soporte CUDA -- hay que reinstalar con
el index de CUDA correspondiente.

## Fix post-prueba 2: `ModuleNotFoundError: No module named 'configs'`

`infer/rmvpe.py` del oficial importa `configs.config.get_device_dtype_sm`
en caliente (dentro de `RMVPE.__init__`), modulo de la WebUI que no se
vendorizo. Esa funcion no es cosmetica: en GPUs serie 16 (como la GTX
1650 del usuario, SM 7.5 pero sin tensor cores de fp16 reales) fuerza
`float32` en vez de `float16` -- con fp16 esas tarjetas tipicamente
crashean o dan basura. Se vendorizo esa funcion sola en
`core/rvc_backend/gpu_rules.py` y se repararon los dos imports en
`rmvpe.py` (`from configs.config import ...` -> `from .gpu_rules import
...`).

## Tuning de latencia (GTX 1650, ~300-350ms medido)

- `REALTIME_EXTRA_MS` bajado de 2500 a 1000 en `config.py`. Es el lever
  real: hubert+sintetizador reprocesan esa ventana ENTERA cada bloque
  (sin cache incremental), asi que el costo escala con esto. Probar
  bajar mas (500-800) si sigue lento; subir si se degrada la calidad
  (menos contexto = pitch/timbre menos estable).
- `fp16` NO es un lever disponible en esta GPU: `gpu_rules.py` lo
  deshabilita a proposito en tarjetas serie 16 (sin tensor cores fp16
  reales, crashea/da ruido con eso prendido).
- Bug aparte encontrado de paso: `AudioCapture.audio_queue` no tenia
  limite. Si el computo no alcanzaba tiempo real, el delay mic->parlante
  se iba acumulando SOLO mientras mas tiempo pasaba (no se quedaba fijo
  en ~300ms). Cola acotada a 2 bloques, descarta el mas viejo si se
  llena -- convierte "atraso creciente" en "frame salteado ocasional".

## Profiling real (GTX 1650, con fixes de device+extra_ms aplicados)

Instrumentado `RVCEngine.infer()` y `RVCStream.process()` por etapa
(`config.PROFILE_RVC`, con `torch.cuda.synchronize()` en cada punto --
sin eso los tiempos entre etapas no significan nada porque CUDA es
asincrono). Resultado en estado estable:

```
[Profile] hubert=18ms index=2ms f0=47ms synth=65ms total=132ms
[Profile stream] resample_in=2ms engine=132ms resample_out+sola+copy=2ms TOTAL_bloque=136ms
```

Computo real ~130-140ms, bien por debajo del presupuesto de 250ms --
**no es cuello de botella**. El primer bloque de la sesion da ~2500ms
(carga de pesos de RMVPE, costo unico, no se repite).

Hallazgo importante: el log `[ConversionThread] Latencia Xms > block
250ms` (que mostraba ~310-320ms) estaba midiendo computo + el bloqueo de
`sounddevice.write()` esperando espacio en el buffer del parlante --
pacing normal, no computo de mas. Mezclar las dos cosas en una sola
metrica confundia (parecia que el motor iba atrasado cuando en realidad
sobraba margen). Separado en `conversion_thread.py`: ahora el warning
solo dispara si el COMPUTO solo (sin el `write`) supera `block_ms`, que
es la condicion que de verdad indica que se va a acumular atraso.

Con computo sobrando margen, el lever que realmente mueve la aguja de
"se siente lento" pasa a ser `REALTIME_BLOCK_MS` (cuanto audio hay que
juntar antes de ni empezar a procesar) -- bajado de 250 a 150ms.
RMVPE redondea su ventana interna a multiplos de 5120 muestras
(~320ms a 16kHz), asi que el stage `f0` no baja mucho mas alla de
~45-50ms aunque `block_ms` siga bajando -- ya esta en el piso de esa
cuantizacion.

## Cortes de audio reales (no solo "se siente lento")

Con `block_ms=150` el usuario reporto audio cortado. Se analizo el video
de prueba con ffmpeg (`silencedetect` + waveform): huecos de silencio
reales de ~70-100ms cada ~150-230ms **durante habla continua**, alineados
con el periodo de `block_ms` -- un corte por bloque, visible a ojo en el
waveform como cada palabra separada en su propio segmento. No es
percepcion, es un corte real en el audio de salida.

Causa: a `block_ms=150` el COMPUTO del modelo iba sobrado (130-140ms,
confirmado por el profiling), pero `latency="low"` en el
`sd.OutputStream` le pide a WASAPI el buffer mas chico posible -- casi
cero margen entre un `write()` y el siguiente. El resto del loop (poll de
la cola, el propio `write()`, overhead de Python/GIL compitiendo con el
computo) alcanzaba para comerse ese margen minimo y producir underrun
justo en el borde de cada bloque.

Dos cambios:
- `sd.OutputStream(..., latency=0.1)` en vez de `"low"` -- 100ms de
  colchon real en PortAudio/WASAPI.
- `REALTIME_BLOCK_MS` 150 -> 200 -- mas margen para el loop completo, no
  solo para el modelo.

## Cortes reales confirmados (contenido perdido, no solo textura)

Usuario confirmo: "las dos cosas mezcladas" -- falta contenido Y suena
robotico en transiciones. Se midio con ffmpeg a -50dB (silencio digital
real, no solo consonantes sordas bajas) y el espaciado de los huecos
cambio entre pruebas (200ms en una, 260ms en otra) sin relacion fija con
`block_ms` -- eso descarto la teoria de "un corte por bloque" de la
vuelta anterior.

Causa mas probable encontrada por inspeccion de codigo, no por descarte:
`AudioCapture._capture_loop` hacia **una sola lectura bloqueante gigante**
de `self._stream.read(self.chunk_size, exception_on_overflow=False)` --
todo el bloque (200ms+) de una. Si cualquier cosa demoraba un toque en el
medio (GIL, GC, Game DVR grabando en paralelo, scheduling de Windows),
PortAudio se quedaba sin buffer y **descartaba audio en silencio**
(`exception_on_overflow=False` tapaba el sintoma). Ademas, si alguna vez
se llegaba a lanzar esa excepcion, el `except` hacia `break` -- mataba el
hilo de captura entero, no solo perdia un chunk.

Dos fixes en `core/audio_capture.py`:
- Lectura en pedacitos chicos (`_READ_CHUNK_DEFAULT=2048`, ~43ms) que se
  van juntando hasta completar el bloque, en vez de una lectura gigante
  de una. Mucho menos margen de overflow por demora puntual.
- `exception_on_overflow=True` + manejo explicito: cuenta y loggea
  `[AudioCapture] Input overflow #N` en vez de tragarselo en silencio, y
  ya NO mata el hilo (seguia descartando ese pedacito y continua).

Si el log muestra overflows, es la causa confirmada. Si no aparece
ninguno y los huecos siguen, el origen esta en otro lado (motor o
salida), no en la captura.

Tambien se subio `REALTIME_CROSSFADE_MS` 50->80 y se relajo el clamp
interno de `sola_buffer_frame` (el original RVC-WebUI lo topeaba duro a
40ms) para permitir mas blend entre bloques -- apunta a la parte
"robotico en las transiciones" de lo que describio el usuario.

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
