"""
core/audio_devices.py

Enumeracion de dispositivos de audio y deteccion de cable virtual
(VB-CABLE) para usar la voz convertida como microfono en Discord,
llamadas, etc.

Concepto (Windows):
- La app REPRODUCE la voz convertida en el extremo de reproduccion del
  cable ("CABLE Input (VB-Audio Virtual Cable)").
- Discord/Windows la CAPTA desde el extremo de grabacion del mismo cable
  ("CABLE Output (VB-Audio Virtual Cable)"), que se elige como microfono
  en esas apps. La app NO necesita permiso de microfono extra para esto.

El driver VB-CABLE lo instala el usuario aparte (requiere admin):
https://vb-audio.com/Cable/ (gratis/donationware). Sin el driver no hay
dispositivo virtual que seleccionar; la app lo detecta y lo indica.
"""
from typing import List, Optional, Tuple

Device = Tuple[int, str]  # (indice sounddevice, nombre)


def _query():
    try:
        import sounddevice as sd
    except ImportError:
        return []
    try:
        return list(sd.query_devices())
    except Exception:
        return []


def list_output_devices() -> List[Device]:
    """Dispositivos con al menos 1 canal de salida."""
    return [
        (i, d["name"])
        for i, d in enumerate(_query())
        if d.get("max_output_channels", 0) > 0
    ]


def list_input_devices() -> List[Device]:
    """Dispositivos con al menos 1 canal de entrada."""
    return [
        (i, d["name"])
        for i, d in enumerate(_query())
        if d.get("max_input_channels", 0) > 0
    ]


def _hostapi_name(device_index: int) -> str:
    try:
        import sounddevice as sd
        return sd.query_hostapis(sd.query_devices(device_index)["hostapi"])["name"]
    except Exception:
        return ""


def _device_dict(device_index: int):
    try:
        import sounddevice as sd
        return sd.query_devices(device_index)
    except Exception:
        return None


def _score_cable(index: int, want_input: bool) -> int:
    """Prefiere WASAPI, 2 canales y 48 kHz.

    Windows mezcla MME/DirectSound/WASAPI/WDM-KS y todos exponen el mismo
    cable. El primero de la lista suele ser MME (44100 Hz, 16 canales):
    abrir 48 kHz ahi fuerza un camino de resampleo que en llamadas suena
    con artefactos/cortes. WASAPI stereo 48 kHz es el camino nativo.
    """
    d = _device_dict(index)
    if d is None:
        return 0
    api = _hostapi_name(index).lower()
    score = 0
    if "wasapi" in api:
        score += 4
    if d.get("max_input_channels" if want_input else "max_output_channels") == 2:
        score += 2
    try:
        if int(d.get("default_samplerate", 0)) == 48000:
            score += 1
    except Exception:
        pass
    return score


def find_cable_playback(outputs: Optional[List[Device]] = None) -> Optional[int]:
    """Indice del extremo de REPRODUCCION del cable virtual ("CABLE Input").

    Es a DONDE la app debe enviar la voz convertida. Retorna None si no
    hay cable instalado. Si hay varias APIs con el mismo cable, gana la
    de mejor calidad (WASAPI 2ch 48k), no la primera de la lista.
    """
    outputs = outputs if outputs is not None else list_output_devices()
    matches = [
        index for index, name in outputs
        # VB-CABLE expone "CABLE Input (VB-Audio Virtual Cable)".
        # Se aceptan variantes (cable a/b/c/d, otros cables virtuales).
        if "cable" in name.lower() and "input" in name.lower()
    ]
    if not matches:
        return None
    return max(matches, key=lambda i: _score_cable(i, want_input=False))


def find_cable_capture(inputs: Optional[List[Device]] = None) -> Optional[int]:
    """Indice del extremo de GRABACION del cable ("CABLE Output").

    Grabar de aca equivale a escuchar lo que Discord/la llamada recibe.
    Se usa para diagnostico local (prueba de cable y evidencia en WAV).
    """
    inputs = inputs if inputs is not None else list_input_devices()
    matches = [
        index for index, name in inputs
        if "cable" in name.lower() and "output" in name.lower()
    ]
    if not matches:
        return None
    return max(matches, key=lambda i: _score_cable(i, want_input=True))


def find_cable_mic(inputs: Optional[List[Device]] = None) -> Optional[str]:
    """Nombre del extremo de GRABACION del cable ("CABLE Output").

    Es lo que el usuario debe elegir como MICROFONO en Discord/Windows.
    Solo informativo (la app no lo usa directamente).
    """
    inputs = inputs if inputs is not None else list_input_devices()
    for _, name in inputs:
        low = name.lower()
        if "cable" in low and "output" in low:
            return name
    return None
