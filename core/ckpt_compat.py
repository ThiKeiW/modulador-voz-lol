"""
core/ckpt_compat.py

Carga tolerante de checkpoints RVC (.pth).

Ultimate RVC incrusta clases propias pickladas en el checkpoint (caso
real medido: `sr` como `ultimate_rvc.typing_extra.TrainingSampleRate` en
vez del int 40000), asi que `torch.load` normal falla con
ModuleNotFoundError si ese paquete no esta instalado/importable (y en
Python <=3.11 ni siquiera se puede importar: usa sintaxis 3.12+).

Estrategia: primero carga normal; si falla por modulo ajeno, se reabre
con el mismo `torch.load` pero con un `pickle_module` de compatibilidad
cuyo Unpickler mapea esas clases a builtins con el mismo valor. Si
aparece otra clase ajena no mapeada, el error la nombra explicito para
agregarla (no se inventa mapeo silencioso).
"""
from typing import Any, Dict
import pickle as _stdlib_pickle

import torch

# (modulo, clase) -> builtin equivalente (mismo valor).
_COMPAT_CLASSES = {
    ("ultimate_rvc.typing_extra", "TrainingSampleRate"): int,
}


class _CompatUnpickler(_stdlib_pickle.Unpickler):
    def find_class(self, module, name):
        key = (module, name)
        if key in _COMPAT_CLASSES:
            return _COMPAT_CLASSES[key]
        if module == "ultimate_rvc" or module.startswith("ultimate_rvc."):
            raise ModuleNotFoundError(
                f"Clase no mapeada en checkpoint: {module}.{name}. "
                "Agregala a _COMPAT_CLASSES en core/ckpt_compat.py"
            )
        return super().find_class(module, name)


class _CompatPickleModule:
    """Namespaces como el modulo pickle pero con nuestro Unpickler."""

    Unpickler = _CompatUnpickler
    Pickler = _stdlib_pickle.Pickler

    def __getattr__(self, name):
        return getattr(_stdlib_pickle, name)


def load_ckpt_tolerant(pth_path) -> Dict[str, Any]:
    """Equivalente a torch.load(map_location=cpu) pero tolera checkpoints
    de Ultimate RVC con clases propias pickladas. Lanza la excepcion
    original si ni el fallback puede abrirlo."""
    try:
        return torch.load(pth_path, map_location=torch.device("cpu"), weights_only=False)
    except ModuleNotFoundError:
        pass
    return torch.load(
        pth_path,
        map_location=torch.device("cpu"),
        weights_only=False,
        pickle_module=_CompatPickleModule(),
    )


def normalize_ckpt_meta(ck: Dict[str, Any]) -> dict:
    """Extrae version/f0/sr como primitivos limpios (int/str), sin objetos
    ajenos. `f0` puede venir como bool (Ultimate RVC) o int (oficial)."""
    cfg = ck.get("config") or []
    sr = ck.get("sr", cfg[-1] if cfg else "?")
    try:
        sr = int(sr)
    except (TypeError, ValueError):
        pass
    return {
        "version": ck.get("version", "v1"),
        "f0": 1 if ck.get("f0", 1) else 0,
        "sr": sr,
    }
