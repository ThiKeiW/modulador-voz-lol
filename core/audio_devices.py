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


def find_cable_playback(outputs: Optional[List[Device]] = None) -> Optional[int]:
    """Indice del extremo de REPRODUCCION del cable virtual ("CABLE Input").

    Es a DONDE la app debe enviar la voz convertida. Retorna None si no
    hay cable instalado.
    """
    outputs = outputs if outputs is not None else list_output_devices()
    for index, name in outputs:
        low = name.lower()
        # VB-CABLE expone "CABLE Input (VB-Audio Virtual Cable)".
        # Se aceptan variantes (cable a/b/c/d, otros cables virtuales).
        if "cable" in low and "input" in low:
            return index
    return None


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
