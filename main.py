"""
Punto de entrada de la aplicacion Voicemod LoL.
Modulador de Voz Virtual con IA para personajes de League of Legends.
"""
import sys
import os
import logging

# Agregar directorio raiz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Sin esto los logger.info() (ej. que device uso RVCEngine: cpu o cuda)
# no se ven en consola -- nivel por defecto de logging es WARNING.
logging.basicConfig(level=logging.INFO, format="%(message)s")


def check_dependencies():
    """Verifica que las dependencias criticas esten instaladas."""
    missing_critical = []
    missing_optional = []

    # Dependencias criticas (requeridas)
    try:
        import PyQt6
    except ImportError:
        missing_critical.append("PyQt6")

    try:
        import numpy
    except ImportError:
        missing_critical.append("numpy")

    if missing_critical:
        print("=" * 60)
        print("  ERROR: Faltan dependencias criticas")
        print("=" * 60)
        print(f"\n  Paquetes faltantes: {', '.join(missing_critical)}")
        print("\n  Instala con:")
        print(f"    pip install {' '.join(missing_critical)}")
        print("\n  O instala todo con:")
        print("    pip install -r requirements.txt")
        print("=" * 60)
        sys.exit(1)

    # Dependencias opcionales (advertencias)
    try:
        import torch
        print("[OK] PyTorch disponible")
    except ImportError:
        missing_optional.append("torch")
        print("[--] PyTorch no disponible (modo limitado)")

    try:
        import pyaudio
        print("[OK] PyAudio disponible")
    except ImportError:
        missing_optional.append("pyaudio")
        print("[--] PyAudio no disponible (captura de audio deshabilitada)")

    # El motor real ya no usa el paquete rvc-python (se descarto, ver
    # docs/04-fase2-rvc-real.md) -- lo que de verdad hace falta son los
    # assets de hubert_base/rmvpe que no van en el repo por peso.
    try:
        import transformers  # noqa: F401
        print("[OK] transformers disponible")
    except ImportError:
        missing_optional.append("transformers")
        print("[--] transformers no disponible (conversion de voz deshabilitada)")

    from pathlib import Path
    from config import HUBERT_DIR, RMVPE_PATH
    if (Path(HUBERT_DIR) / "config.json").is_file() and Path(RMVPE_PATH).is_file():
        print("[OK] Assets RVC (hubert_base, rmvpe) presentes")
    else:
        missing_optional.append("assets-rvc")
        print("[--] Faltan assets RVC. Correr: python scripts/download_assets.py")

    if missing_optional:
        print(f"\n[Info] Paquetes opcionales no instalados: {', '.join(missing_optional)}")
        print("  La aplicacion funcionara con funcionalidad limitada.\n")


def main():
    """Funcion principal de la aplicacion."""
    print("=" * 60)
    print("  Voicemod LoL - Modulador de Voz Virtual con IA")
    print("  v1.0.0 | Espanol Latino | Windows")
    print("=" * 60)

    # Verificar dependencias
    check_dependencies()

    # Verificar Python
    print(f"\n  Python: {sys.version}")
    print(f"  Plataforma: {sys.platform}")

    # Iniciar GUI
    from PyQt6.QtWidgets import QApplication, QMessageBox
    from PyQt6.QtGui import QFont

    app = QApplication(sys.argv)
    app.setApplicationName("Voicemod LoL")
    app.setApplicationVersion("1.0.0")

    # Estilo global oscuro
    app.setStyleSheet("""
        * {
            font-family: 'Segoe UI', 'Arial', sans-serif;
        }
        QMainWindow {
            background-color: #0a0a1a;
        }
        QToolTip {
            background-color: #16213e;
            color: #e0e0e0;
            border: 1px solid #1a1a3e;
            padding: 4px;
        }
    """)

    # Crear y mostrar ventana principal
    from gui.main_window import MainWindow
    window = MainWindow()
    window.show()

    print("\n  Aplicacion iniciada correctamente.")
    print("  Selecciona un personaje para comenzar.\n")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
