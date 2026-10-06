"""
core/rvc_backend/gpu_rules.py

get_device_dtype_sm() vendorizado de configs/config.py del repo oficial
RVC-Project/Retrieval-based-Voice-Conversion-WebUI (MIT License). Recorte
de ese archivo (que ademas trae argparse de la WebUI, logging global,
etc. que no necesitamos) a solo la regla que usa core/rvc_backend/rmvpe.py.

Importa: GPUs con menos de 4GiB o SM < 5.3 no se usan (vuelve a CPU).
Pascal SM 6.1 (ej GTX 10xx) y las GTX serie 16 (1650/1660, SM 7.5 pero
SIN tensor cores reales de fp16) se fuerzan a float32 -- en esas tarjetas
float16 anda mal/crashea. El resto de GPUs CUDA mas nuevas usan float16.
"""
import logging
import re

import torch

logger = logging.getLogger(__name__)


def get_device_dtype_sm(idx):
    cpu = torch.device("cpu")
    if not torch.cuda.is_available() or idx < 0 or idx >= torch.cuda.device_count():
        return cpu, torch.float32, 0.0, 0.0

    try:
        cuda = torch.device(f"cuda:{idx}")
        major, minor = torch.cuda.get_device_capability(idx)
        gpu_name = torch.cuda.get_device_name(idx)
        mem_bytes = torch.cuda.get_device_properties(idx).total_memory
    except Exception:
        logger.exception("No se pudo inspeccionar la GPU CUDA %s", idx)
        return cpu, torch.float32, 0.0, 0.0

    mem_gb = mem_bytes / (1024 ** 3) + 0.4
    sm_version = major + minor / 10.0
    is_16_series = bool(re.search(r"16\d{2}", gpu_name)) and sm_version == 7.5
    if mem_gb < 4 or sm_version < 5.3:
        return cpu, torch.float32, 0.0, 0.0
    if sm_version == 6.1 or is_16_series:
        return cuda, torch.float32, sm_version, mem_gb
    if sm_version > 6.1:
        return cuda, torch.float16, sm_version, mem_gb
    return cpu, torch.float32, 0.0, 0.0
