"""
core/rvc_backend/

Arquitectura de inferencia RVC v1/v2 vendorizada desde el proyecto oficial
RVC-Project/Retrieval-based-Voice-Conversion-WebUI (MIT License), recortada
a solo lo necesario para inferencia (sin entrenamiento, sin webui, sin
fcpe/onnx). Codigo copiado tal cual salvo imports internos reescritos a
paquete relativo y el stub de cuda_graph (ver cuda_graph.py).

No editar la logica de models.py/attentions.py/commons.py/modules.py/
transforms.py/rmvpe.py a mano: si hace falta un fix, traerlo del repo
oficial de nuevo para no romper la compatibilidad de pesos con los .pth
entrenados externamente.
"""
