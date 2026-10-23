"""
scripts/diag_cable.py

Diagnostico y evidencia del microfono virtual (VB-CABLE).

Motivo: en una llamada el audio solo lo escucha un tercero, asi que no se
puede comparar ni enviar como prueba. El extremo de GRABACION del cable
("CABLE Output") entrega EXACTAMENTE la misma senal que Discord/la llamada
recibe. Grabandola a WAV se puede escuchar localmente y adjuntar.

Modos:
  tone    Genera un tono de 440 Hz, lo reproduce por el cable y lo vuelve
          a capturar. Aisla driver/cable de Discord: si el tono vuelve
          limpio, el cable esta bien y el problema es el procesamiento de
          la app de llamada (supresion de ruido, cancelacion de eco, AGC).
  record  Graba lo que la llamada "oiria" mientras usas la app. Habla
          normalmente durante la grabacion.
  analyze Revisa un WAV ya grabado y lista los huecos internos, marcando
          los que son cortes duros (silencio digital entre voz fuerte).

Uso:
  python scripts/diag_cable.py --mode tone
  python scripts/diag_cable.py --mode record --seconds 20
  python scripts/diag_cable.py --mode analyze --file diagnostics\\x.wav

Los WAV quedan en diagnostics/ (ignorado por git).
"""
import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.audio_devices import (  # noqa: E402
    find_cable_capture,
    find_cable_playback,
    _device_dict,
    _hostapi_name,
)

SAMPLE_RATE = 48000
OUT_DIR = ROOT / "diagnostics"


def describe(index: int) -> str:
    d = _device_dict(index) or {}
    return f"[{index}] {d.get('name', '?')} ({_hostapi_name(index)})"


def analyze(samples: np.ndarray, sr: int) -> dict:
    """Metricas objetivas de una senal mono float32."""
    if samples.size == 0:
        return {"error": "sin muestras"}
    peak = float(np.max(np.abs(samples)))
    rms = float(np.sqrt(np.mean(np.square(samples))))
    db = lambda v: 20 * np.log10(max(v, 1e-12))  # noqa: E731
    clipping = int(np.count_nonzero(np.abs(samples) >= 0.999))
    dc = float(np.mean(samples))

    # Huecos INTERNOS: rachas de silencio digital de mas de 50 ms entre el
    # primer y el ultimo sonido. El silencio de antes/despues de grabar no
    # es un corte de audio y no debe contarse.
    active = np.flatnonzero(np.abs(samples) >= 1e-4)
    gaps = 0
    longest = 0
    if active.size > 1:
        inner = np.abs(samples[active[0]:active[-1] + 1]) < 1e-4
        run = 0
        for s in inner:
            if s:
                run += 1
                longest = max(longest, run)
            else:
                if run > 0.05 * sr:
                    gaps += 1
                run = 0
        if run > 0.05 * sr:
            gaps += 1

    return {
        "peak_dbfs": round(db(peak), 1),
        "rms_dbfs": round(db(rms), 1),
        "clipping_samples": clipping,
        "clipping_pct": round(100.0 * clipping / samples.size, 4),
        "dc_offset": round(dc, 6),
        "silence_gaps_over_50ms": gaps,
        "longest_gap_ms": round(1000.0 * longest / sr, 1),
        "duration_s": round(samples.size / sr, 2),
    }


def dominant_freq(samples: np.ndarray, sr: int) -> float:
    if samples.size < 1024:
        return 0.0
    window = np.hanning(samples.size)
    spectrum = np.abs(np.fft.rfft(samples * window))
    freqs = np.fft.rfftfreq(samples.size, 1.0 / sr)
    return float(freqs[int(np.argmax(spectrum))])


def save_wav(name: str, data: np.ndarray, sr: int) -> Path:
    OUT_DIR.mkdir(exist_ok=True)
    path = OUT_DIR / name
    sf.write(str(path), data, sr, subtype="PCM_16")
    return path


def open_capture(capture_index: int, seconds: float):
    import sounddevice as sd

    chunks = []
    done = {"flag": False}

    def callback(indata, frames, time_info, status):
        if status:
            print(f"  [captura] {status}")
        chunks.append(indata.copy())

    stream = sd.InputStream(
        device=capture_index,
        samplerate=SAMPLE_RATE,
        channels=2,
        dtype="float32",
        latency=0.05,
        callback=callback,
    )
    stream.start()
    return stream, chunks, done


def collect(chunks, seconds: float) -> np.ndarray:
    time.sleep(seconds)
    if not chunks:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(chunks, axis=0)


def find_gaps(samples: np.ndarray, sr: int) -> list:
    """Huecos internos de silencio digital (>50 ms), con contexto."""
    active = np.flatnonzero(np.abs(samples) >= 1e-3)
    if active.size < 2:
        return []
    a, b = int(active[0]), int(active[-1]) + 1

    def rms(block: np.ndarray) -> float:
        return float(np.sqrt(np.mean(np.square(block)))) if block.size else 0.0

    gaps = []
    run_start = None
    for i in range(b - a):
        silent = abs(samples[a + i]) < 1e-3
        if silent and run_start is None:
            run_start = i
        elif not silent and run_start is not None:
            n = i - run_start
            if n >= 0.05 * sr:
                s, e = a + run_start, a + i
                pre = rms(samples[max(0, s - int(0.1 * sr)):s])
                post = rms(samples[e:e + int(0.1 * sr)])
                gaps.append({
                    "t": round(s / sr, 3),
                    "ms": round(1000.0 * n / sr),
                    "pre_rms": round(pre, 4),
                    "post_rms": round(post, 4),
                    "hard_cut": pre > 0.05 and post > 0.05 and n < 0.6 * sr,
                })
            run_start = None
    return gaps


def mode_analyze(args) -> int:
    if not args.file:
        print("ERROR: --mode analyze requiere --file RUTA.wav")
        return 2
    path = Path(args.file)
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        print(f"ERROR: no existe {path}")
        return 2
    data, sr = sf.read(str(path), dtype="float32", always_2d=True)
    mono = data.mean(axis=1)
    print(f"Archivo: {path.name} | {sr} Hz | {mono.size / sr:.2f}s")
    for key, value in analyze(mono, sr).items():
        print(f"  {key}: {value}")

    gaps = find_gaps(mono, sr)
    hard = [g for g in gaps if g["hard_cut"]]
    print(f"\nHuecos internos >=50ms: {len(gaps)} (cortes duros: {len(hard)})")
    for g in gaps:
        mark = "CORTE DURO" if g["hard_cut"] else "pausa/gate"
        print(f"  t={g['t']:>7.2f}s  {g['ms']:>5}ms  "
              f"rms_antes={g['pre_rms']:.3f} rms_despues={g['post_rms']:.3f}"
              f"  {mark}")
    if hard:
        print("\nVEREDICTO: hay cortes duros -> underrun de salida o "
              "bloque perdido. Subir OUTPUT_PREFILL_MS o revisar el log "
              "diagnostics/diag.log.")
    else:
        print("\nVEREDICTO: sin cortes duros; los huecos son pausas o gate.")
    return 0


def mode_tone(args) -> int:
    import sounddevice as sd

    play = args.playback_device or find_cable_playback()
    cap = args.capture_device or find_cable_capture()
    if play is None:
        print("ERROR: no se encontro el extremo de reproduccion del cable (CABLE Input).")
        return 2
    if cap is None:
        print("ERROR: no se encontro el extremo de grabacion del cable (CABLE Output).")
        return 2

    print(f"Reproduccion : {describe(play)}")
    print(f"Captura      : {describe(cap)}")

    duration = 3.0
    t = np.arange(int(duration * SAMPLE_RATE)) / SAMPLE_RATE
    tone = 0.25 * np.sin(2 * np.pi * 440.0 * t)
    fade = int(0.05 * SAMPLE_RATE)
    tone[:fade] *= np.linspace(0.0, 1.0, fade)
    tone[-fade:] *= np.linspace(1.0, 0.0, fade)
    stereo = np.column_stack([tone, tone]).astype(np.float32)

    capture_stream, chunks, _ = open_capture(cap, duration)
    time.sleep(0.2)  # dejar arrancar la captura

    out_stream = sd.OutputStream(
        device=play,
        samplerate=SAMPLE_RATE,
        channels=2,
        dtype="float32",
        latency=0.05,
    )
    out_stream.start()
    out_stream.write(stereo)
    time.sleep(0.3)
    out_stream.stop()
    out_stream.close()

    recorded = collect(chunks, 0.3)
    capture_stream.stop()
    capture_stream.close()

    if recorded.size == 0:
        print("ERROR: la captura no devolvio audio.")
        return 3

    mono = recorded.mean(axis=1).astype(np.float32)
    metrics = analyze(mono, SAMPLE_RATE)
    freq = dominant_freq(mono, SAMPLE_RATE)

    played_path = save_wav("tono_enviado.wav", stereo, SAMPLE_RATE)
    heard_path = save_wav("tono_recibido_por_la_llamada.wav", recorded, SAMPLE_RATE)

    print("\nTono enviado    :", played_path)
    print("Lo que 'oye'    :", heard_path)
    print(f"Frecuencia dominante: {freq:.1f} Hz (esperado 440)")
    for key, value in metrics.items():
        print(f"  {key}: {value}")

    ok = (
        abs(freq - 440.0) < 10
        and metrics["peak_dbfs"] > -20
        and metrics["clipping_pct"] < 0.1
        and metrics["silence_gaps_over_50ms"] == 0
    )
    print("\nVEREDICTO:", "CABLE OK" if ok else "CABLE CON PROBLEMAS")
    if not ok:
        print("  - Frecuencia corrida => el cable corre a otra tasa (revisar "
              "Formato de CABLE Input en Windows: 48000 Hz).")
        print("  - Pico bajo/clipping/huecos => driver o buffer; probar otro "
              "dispositivo 'CABLE Input' (WASAPI).")
    return 0 if ok else 1


def mode_record(args) -> int:
    cap = args.capture_device or find_cable_capture()
    if cap is None:
        print("ERROR: no se encontro CABLE Output (extremo de grabacion).")
        return 2
    print(f"Captura: {describe(cap)}")
    print(f"Grabando {args.seconds}s. Habla ahora (la app debe estar en 'Iniciar').")
    capture_stream, chunks, _ = open_capture(cap, args.seconds)
    recorded = collect(chunks, args.seconds)
    capture_stream.stop()
    capture_stream.close()

    if recorded.size == 0:
        print("ERROR: no se capturo audio. ¿La app esta enviando al cable virtual?")
        return 3

    mono = recorded.mean(axis=1).astype(np.float32)
    metrics = analyze(mono, SAMPLE_RATE)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = save_wav(f"prueba_llamada_{stamp}.wav", recorded, SAMPLE_RATE)

    print("\nEvidencia guardada:", path)
    for key, value in metrics.items():
        print(f"  {key}: {value}")
    if metrics["peak_dbfs"] < -40:
        print("\nAVISO: casi silencio. La app no esta llegando a CABLE Input "
              "(revisa el combo 'Reproducir voz en' y pulsa 'Usar cable virtual').")
    elif metrics["clipping_pct"] > 0.1:
        print("\nAVISO: clipping. Baja el volumen del dispositivo CABLE Input.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnostico del microfono virtual")
    parser.add_argument("--mode", choices=["tone", "record", "analyze"],
                        default="tone")
    parser.add_argument("--seconds", type=float, default=15.0)
    parser.add_argument("--playback-device", type=int, default=None)
    parser.add_argument("--capture-device", type=int, default=None)
    parser.add_argument("--file", default=None, help="WAV para --mode analyze")
    args = parser.parse_args()
    if args.mode == "tone":
        return mode_tone(args)
    if args.mode == "record":
        return mode_record(args)
    return mode_analyze(args)


if __name__ == "__main__":
    raise SystemExit(main())
