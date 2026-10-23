# 08 - Cable virtual (VB-CABLE) por WASAPI

Fecha: 2026-10-20

## Hechos comprobados

1. **La app abria la salida en mono (1 canal).** Con VB-CABLE por WASAPI
   el stream abre sin error pero entrega audio corrupto. Medido con un
   tono de 440 Hz reproducido por el cable y capturado en `CABLE Output`:
   - `channels=1`: frecuencia dominante ~873 Hz (ruido), aunque el pico
     era correcto (0.2).
   - `channels=2`: 440.0 Hz limpio, 0 clipping, 0 huecos.
   Correccion aplicada en `core/audio_output.py`: abrir 2 canales cuando
   el dispositivo los soporta y replicar la voz mono en ambos. Validado
   con el `StreamingOutput` real: 440.0 Hz, pico -12 dBFS, 0 huecos.

2. **Preferencia de dispositivo.** Windows publica el mismo "CABLE Input"
   en MME, DirectSound, WASAPI y WDM-KS. El primero de la lista es MME
   (44100 Hz, 16 canales). `find_cable_playback()` ahora puntua y elige
   WASAPI + 2 canales + 48000 (el indice cambia entre arranques; en la
   ultima medicion: salida WASAPI = 29, captura WASAPI = 31), no el
   primero.

3. **Por que no aparece el WASAPI en el combo.** `_refresh_output_devices`
   deduplica por nombre (`findText(name) < 0`). Como MME aparece primero
   con el mismo nombre, la entrada WASAPI se descarta. Resultado: el combo
   solo ofrece el cable MME, y "Usar cable virtual" (que apunta al indice
   WASAPI) no encuentra el indice y no hace nada.

4. **Evidencia local.** `CABLE Output` entrega exactamente lo que recibe
   Discord/la llamada. `scripts/diag_cable.py` graba eso a WAV y valida el
   cable con un tono, sin necesidad de un tercero.

## Cambio cancelado

Se habia implementado `list_output_devices_best()` (deduplicacion global
por nombre conservando la mejor API) y el combo etiquetado con la API.
Fue revertido a pedido del usuario; el combo vuelve a deduplicar por
nombre.

## Fix aplicado

`_ensure_cable_entry()` en `gui/main_window.py`: tras detectar el cable,
reapunta la entrada visible "CABLE Input" al indice WASAPI y la etiqueta
`· WASAPI`; si no existe (MME trunca el nombre a 32 caracteres), agrega
una entrada nueva. Verificado con el combo real: la entrada queda como
`CABLE Input (VB-Audio Virtual Cable) · WASAPI` y `findData` la resuelve,
asi que "Usar cable virtual" ya puede seleccionarla.

## Prueba en llamada real (2026-10-23)

Grabacion `prueba_llamada_20261023_165920.wav` (20 s, 48 kHz; ya no esta
en disco, la reemplazo la segunda prueba):
pico -2.9 dBFS, RMS -18.7 dBFS, 0 clipping, sin DC. Un unico **corte
duro** medido:

- t=13.92 s, 80 ms de cero digital exacto entre voz fuerte
  (RMS 0.157 antes, 0.139 despues).

Los demas huecos (5.45 s, 12.95 s, 14.80 s, 16.32 s) tienen caida/rampa y
coinciden con pausas o el silence gate. Interpretacion: el **colchon de
salida de 60 ms era insuficiente**; un pico de computo vaciaba el buffer
y el callback rellenaba con ceros.

Correcciones aplicadas:

- `OUTPUT_PREFILL_MS`: 60 -> **250 ms** (absorbe picos de computo; suma
  ~190 ms de latencia).
- `core/conversion_thread.py`: las lineas `[Diag]` ahora tambien se
  anexan a `diagnostics/diag.log` (antes solo consola), para revisar
  `huecos_en_voz`, `bloques_descartados` y `buffer` tras cada prueba.
- `scripts/diag_cable.py --mode analyze --file RUTA.wav`: lista huecos
  internos y marca los cortes duros automaticamente.

## Segunda prueba (2026-10-23 17:09, colchon 250 ms)

`diagnostics/prueba_llamada_20261023_170946.wav`: pico -3.2 dBFS, RMS
-19.4 dBFS, 0 clipping y **0 cortes duros**. Los cuatro huecos medidos
(0.9-1.7 s) son pausas/gate: el audio posterior queda bajo (RMS 0.001-
0.039), no voz fuerte interrumpida.

`diagnostics/diag.log` durante la prueba: `huecos_en_voz=0`,
`bloques_descartados=0`, `muestras_tiradas_por_tope=0`, buffer 240-550 ms.
`underruns_totales` sube, pero solo en silencio (no audibles).

El criterio de `--mode analyze` se afino para no dar falsos positivos:
ignora ruido de fondo (<-60 dBFS) y exige voz fuerte a ambos lados
(RMS > 0.05) y hueco < 600 ms para marcar un corte duro.

## Tercera prueba (2026-10-23 17:40, fade de 10 ms)

`diagnostics/prueba_llamada_20261023_174035.wav`: pico -3.0 dBFS, RMS
-18.5 dBFS, 0 clipping, 5 huecos y **0 cortes duros**. Las 4 pausas
internas tienen `borde=0.001` (contra 0.138 de la prueba sin fade): la
rampa del gate esta funcionando y ya no hay escalon a cero. El unico
borde alto (0.164 a los 0.02 s) es el arranque de la grabacion, con
audio previo casi mudo (`rms_antes=0.005`), no audible.

El `diag.log` de esa sesion arranca a las 17:41 (despues de que el WAV
cerrara a las 17:40:36), asi que no cubre la grabacion. Como contexto:
`huecos_en_voz=0`, `bloques_descartados=0`,
`muestras_tiradas_por_tope=0`, buffer 260-280 ms y un underrun en
silencio (7 a 8 en 46 s).

## Bordes duros del silence gate

En la misma grabacion, todos los ceros exactos empiezan en la misma fase
del bloque (77 ms mod 200 ms), duran multiplos de 200 ms y el sample
anterior no es cero (hasta 0.138). No eran underruns (`huecos_en_voz=0`):
era el gate emitiendo el bloque completo en cero, con un escalon seco en
cada pausa.

Fix aplicado: `GATE_FADE_MS = 10` en `config.py`.
`ConversionThread` hace ahora una rampa de 10 ms al cerrar el gate
(partiendo de la ultima muestra, no de cero) y otra al reabrirlo con voz.
No cambia CPU, ni pausas, ni latencia. El analizador tambien verifica el
sample del borde, para no confundir un gate suavizado con un corte real.

## Cambios restantes por hacer

1. **Latencia**: el colchon de 250 ms anade ~190 ms. Si en llamada se
   siente lenta, bajar `OUTPUT_PREFILL_MS` a 180-200 y repetir la prueba
   (objetivo: seguir en 0 cortes duros).
2. **Ajustes de Discord si el WAV suena bien pero la llamada no:**
   desactivar supresion de ruido (Krisp), cancelacion de eco y control
   automatico de ganancia; microfono = `CABLE Output (VB-Audio Virtual
   Cable)`.
3. **Opcional:** exponer `index_rate` como slider (pendiente de Fase 6).

## Aclaracion de dispositivos

- Elegir en la app: `CABLE Input (VB-Audio Virtual Cable) · WASAPI`.
  **No** elegir `CABLE In 16ch` (es otro endpoint, de 16 canales).
- Elegir en Discord/Windows como microfono:
  `CABLE Output (VB-Audio Virtual Cable)` (WASAPI).

## Estado del repositorio

- Ultimo commit: `ce695c4` (estilos).
- Sin commitear: `core/audio_output.py` (estereo), `core/audio_devices.py`
  (preferencia WASAPI + `find_cable_capture`), `scripts/diag_cable.py`,
  `.gitignore` (`diagnostics/`), `gui/main_window.py`, `config.py`
  (`OUTPUT_PREFILL_MS=250`, `GATE_FADE_MS=10`) y
  `core/conversion_thread.py` (log a archivo + rampas del gate).
- `diagnostics/` contiene los WAV de prueba y `diag.log` (ignorado por git).

## Comandos

```powershell
# Validar el cable aislado (tono 440 Hz de ida y vuelta)
.\.venv311\Scripts\python.exe scripts\diag_cable.py --mode tone

# Grabar lo que "oiria" la llamada mientras hablas
.\.venv311\Scripts\python.exe scripts\diag_cable.py --mode record --seconds 20

# Analizar una grabacion: huecos internos y cortes duros
.\.venv311\Scripts\python.exe scripts\diag_cable.py --mode analyze --file "diagnostics\prueba_llamada_XXXX.wav"
```
