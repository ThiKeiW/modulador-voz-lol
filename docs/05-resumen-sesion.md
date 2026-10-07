# Resumen — últimas 6 solicitudes y cambios en el proyecto

Repo: https://github.com/ThiKeiW/modulador-voz-lol (`main`).
Periodo: Fase 2 (motor real) → fixes de tiempo real. `AGENTS.md` es la
referencia de estado; este archivo solo resume lo pedido y lo cambiado.

---

## 1. Reconectar al repo y analizar la sesión de Claude

**Pedido**: volver a conectar el repo y analizar la sesión compartida de
Claude (`claude.ai/share/6cdd5943…`) para ver cambios recientes y problemas.

**Hecho**:
- El repo se había movido a `modulador-voz-lol/` (clon fresco con `.git`).
- `git fetch/pull`: 2 commits nuevos ya sincronizados (`45ca3be` vendoriza
  `core/rvc_backend/` + motor real, +4108 líneas; `88f4767` reestructura +
  fixes post-prueba GPU).
- El link de Claude no es legible por máquina (solo shell JS, sin contenido
  en el HTML) — se analizó en su lugar `docs/04-fase2-rvc-real.md` (bitácora
  de 256 líneas de esa sesión) + el código real.
- Verificado en código lo crítico: `SynthesizerTrnMs768NSFsid` hereda de la
  clase 256 y solo reemplaza `enc_p` (768); `get_synthesizer` elige por
  `version` pero con verificación dura (`RuntimeError` ante cualquier
  `missing/unexpected` que no sea `enc_q`), así el fallo silencioso queda
  convertido en error explícito.

**Cambios**: ninguno (solo análisis). Problemas detectados entonces:
`gui/config.py` duplicado muerto (0 imports) y el `CHUNK_SIZE=1024` sin
efecto.

## 2. Actualizar `AGENTS.md` + detallar fases 2–7 para descarte

**Pedido**: poner el `.md` al día y detallar qué corresponde a cada fase
para decidir qué descartar del proyecto final.

**Hecho**:
- `AGENTS.md` reescrito al estado real (commits `584b675`, `85306ac`):
  Fases 2–3 funcionales, arquitectura vendorizada, parámetros de tiempo
  real, dependencias sin `hf-rvc`/`torchcrepe`/`fairseq`.
- Tabla de decisión entregada por fase (costo vs. qué se pierde al
  descartar). Eliminado `gui/config.py` (commit `868d330`).

## 3. Generar el `.exe` (Fase 7) — luego CANCELADA

**Pedido inicial**: generar `.exe` para que otros lo usen.
**Hecho entonces**: `voicemod-lol.spec` (onedir) + `build_exe.ps1`,
entorno `.venv311` (Py3.11 + torch cu118, CUDA visible), build OK
(`dist/VoicemodLoL/`, ~4.9 GB), smoke test 30s sin crashes (commit
`b068379`). Ver punto 4: todo esto se revirtió.

## 4. Cancelar Fase 7 + subir `.gitignore` del usuario

**Pedido**: no se había pedido construir la Fase 7; el proyecto aún tiene
errores (fluidez en vivo) y falta el micrófono virtual. Cancelar Fase 7 y
subir cambios propios a `.gitignore`.

**Hecho** (commit `63cfee6`):
- Revertidos `voicemod-lol.spec` y `build_exe.ps1`; borrados `dist/`,
  `build/` y logs (~5 GB liberados).
- Subido `.gitignore` del usuario: ignora `models/hubert_base/` y
  `models/rmvpe/`.
- `AGENTS.md`: Fase 7 → ❌ CANCELADA + sección de bugs pendientes
  (fluidez en vivo, micrófono virtual del sistema).

## 5. Punto 1 con logs en CPU → silence-gate

**Pedido**: ver el punto 1 (tiempo real no fluido); Claude no encontró
solución. Logs aportados.

**Diagnóstico con los logs**:
- Causa raíz: la prueba corría en `.venv` (Py3.13, torch **CPU**):
  ~660ms de cómputo por bloque de 200ms (3.3x más lento que tiempo real).
  Ningún ajuste de código arregla eso; la solución era `.venv311` (CUDA).
- Causa secundaria (código): ~80% de los bloques eran silencio
  (mic RMS 0.0000–0.0005) y cada uno pagaba el cómputo completo.

**Fix** (commit `bad24d3`): silence-gate en `ConversionThread` — bloque
bajo `SILENCE_RMS_THRESHOLD = 0.002` sale como ceros sin hubert/f0/synth;
al retomar voz, `stream.reset()`. Umbral validado contra los logs
(silencio ≤0.0005 vs voz ≥0.0030).

## 6. Logs en CUDA → warmup del motor

**Pedido**: nueva prueba (mejor que antes, pero tarda en detectar el
micrófono, con delay y poco fluido). Logs con `Device: cuda:0`.

**Diagnóstico con los logs**:
- Estado estable sano: ~135ms/bloque (hubert~20 + f0~45 + synth~65),
  dentro del presupuesto; gate funcionando (`qsize` 0–1 estable).
- Anomalía 1: primer bloque con voz = 38.8s (`f0=34698ms`, construcción
  de RMVPE en pleno vivo). Eso era el "tarda en detectar".
- Anomalía 2: picos de 200–350ms en bloques de inicio de voz (kernels
  fríos tras idle).

**Fix** (commit `f527248`): `RVCEngine.warmup()` — ceros por el pipeline
completo al presionar Iniciar (con estado `"calentando"` en GUI), antes
de abrir el micrófono. Test headless con Aatrox: warmup 1 = 5928ms
(RMVPE + kernels), warmup 2 = 174ms. `WARMUP TEST OK`.

---

## Estado final y pendientes

- ✅ Tiempo real funcional en CUDA (~135ms/bloque) + gate + warmup.
- ⏳ Por medir con warmup puesto: picos residuales en onsets; palancas
  candidatas: bloque/CROSSFADE/`EXTRA_MS`, prints de `PROFILE_RVC`.
- ⏳ Punto 2 sin empezar: micrófono virtual del sistema (VB-CABLE o
  similar + ruteo en `ConversionThread`) para Discord/llamadas.
- ❌ Fuera de alcance: TTS (F4), entrenamiento integrado (F5, se usa
  Ultimate RVC externo), `.exe` (F7, cancelada), efectos salvo slider
  `index_rate` (F6 parcial).
