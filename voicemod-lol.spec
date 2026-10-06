# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec - Voicemod LoL (Fase 7).
Build: .\.venv311\Scripts\pyinstaller.exe --clean --noconfirm voicemod-lol.spec
Salida: dist/VoicemodLoL/ (modo onedir: carpeta con VoicemodLoL.exe dentro).

NOTAS:
- Los modelos (.pth/.index) y assets (hubert/rmvpe) NO se empaquetan por peso;
  el usuario los descarga con scripts/download_models.py y download_assets.py.
- console=True en el primer build para ver errores; pasar a False cuando este
  estable (solo cambiar esa linea y reconstruir).
- upx=False: UPX suele romper las DLLs CUDA de torch.
"""

block_cipher = None

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        "sounddevice",
        "soundfile",
        "faiss",
        "librosa",
        "numba",
        "llvmlite",
        "pyworld",
        "praat_parselmouth",
        "transformers",
        "tokenizers",
        "huggingface_hub",
        "scipy.special.cython_special",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "unittest",
        "pydoc",
        "doctest",
        "matplotlib",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="VoicemodLoL",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,  # <- False para build final sin consola
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="VoicemodLoL",
)
