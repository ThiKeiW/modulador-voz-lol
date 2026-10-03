"""
core/rvc_backend/cuda_graph.py

Stub de run_cuda_graph. El RVC-WebUI oficial usa CUDA graphs para acelerar
inferencia repetitiva en GPU NVIDIA (captura el grafo de ejecucion una vez
y lo reusa). Es una optimizacion, no un requisito funcional: aqui se omite
y se llama la funcion directo. Mas lento que el original en GPU, pero
identico en resultado y funciona igual en CPU.

Si mas adelante se necesita exprimir latencia en la GTX 1650, se puede
reemplazar este stub por el tools/cuda_graph.py real de RVC-WebUI
(RVC-Project/Retrieval-based-Voice-Conversion-WebUI, MIT license).
"""
from typing import Any, Callable


def run_cuda_graph(model: Any, key: str, fn: Callable, *args, **kwargs):
    """Ejecuta fn(*args, **kwargs) directamente, sin cache de grafo CUDA."""
    return fn(*args, **kwargs)
