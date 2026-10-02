"""
Dialogo de descarga de modelos pre-entrenados.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QCheckBox, QListWidget,
    QListWidgetItem, QMessageBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from config import PRETRAINED_MODELS


class DownloadThread(QThread):
    """Hilo de descarga de modelos."""
    progress = pyqtSignal(str, int, int)  # model_id, current, total
    finished = pyqtSignal(str, bool)  # model_id, success

    def __init__(self, model_id: str, url: str, save_dir: str):
        super().__init__()
        self.model_id = model_id
        self.url = url
        self.save_dir = save_dir

    def run(self):
        import os
        import urllib.request
        from pathlib import Path

        try:
            save_path = Path(self.save_dir) / self.model_id
            save_path.mkdir(parents=True, exist_ok=True)

            filename = self.url.split("/")[-1].split("?")[0]
            filepath = save_path / filename

            def hook(block_num, block_size, total):
                self.progress.emit(self.model_id, block_num * block_size, total)

            urllib.request.urlretrieve(self.url, str(filepath), hook)

            # Si es zip, extraer
            if filename.endswith(".zip"):
                import zipfile
                with zipfile.ZipFile(filepath, "r") as z:
                    z.extractall(save_path)
                os.remove(filepath)

            self.finished.emit(self.model_id, True)

        except Exception as e:
            print(f"Error descargando {self.model_id}: {e}")
            self.finished.emit(self.model_id, False)


class DownloadDialog(QDialog):
    """Dialogo para descargar modelos pre-entrenados."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Descargar Modelos Pre-entrenados")
        self.setMinimumSize(500, 400)
        self.setStyleSheet("""
            QDialog { background-color: #0f0f23; color: #e0e0e0; }
            QLabel { color: #e0e0e0; }
            QPushButton { color: white; }
        """)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Titulo
        title = QLabel("Modelos Disponibles para Descarga")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #e94560;")
        layout.addWidget(title)

        # Lista de modelos
        self.model_list = QListWidget()
        self.model_list.setStyleSheet("""
            QListWidget {
                background-color: #1a1a2e;
                border: 1px solid #16213e;
                border-radius: 4px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #16213e;
            }
            QListWidget::item:hover { background-color: #16213e; }
            QListWidget::item:selected { background-color: #533483; }
        """)

        for model_id, info in PRETRAINED_MODELS.items():
            text = (
                f"{info['name']} - {info['game']}\n"
                f"  Idioma: {info['language']}\n"
                f"  {info['description']}"
            )
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, model_id)
            self.model_list.addItem(item)

        self.model_list.setCurrentRow(0)
        layout.addWidget(self.model_list)

        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1a1a2e;
                border: 1px solid #16213e;
                border-radius: 4px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #e94560;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_label)

        # Botones
        btn_layout = QHBoxLayout()

        self.download_btn = QPushButton("Descargar Seleccionado")
        self.download_btn.setMinimumHeight(35)
        self.download_btn.setStyleSheet("""
            QPushButton {
                background-color: #e94560;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                padding: 8px 20px;
            }
            QPushButton:hover { background-color: #ff6b81; }
        """)
        self.download_btn.clicked.connect(self._on_download)
        btn_layout.addWidget(self.download_btn)

        close_btn = QPushButton("Cerrar")
        close_btn.setMinimumHeight(35)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #533483;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
            }
            QPushButton:hover { background-color: #7b2cbf; }
        """)
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _on_download(self):
        """Inicia la descarga del modelo seleccionado."""
        item = self.model_list.currentItem()
        if not item:
            QMessageBox.warning(self, "Sin seleccion", "Selecciona un modelo primero.")
            return

        model_id = item.data(Qt.ItemDataRole.UserRole)
        model_info = PRETRAINED_MODELS.get(model_id)

        if not model_info:
            return

        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.download_btn.setEnabled(False)

        from config import PRETRAINED_DIR
        self.download_thread = DownloadThread(
            model_id,
            model_info["url"],
            str(PRETRAINED_DIR),
        )
        self.download_thread.progress.connect(self._on_progress)
        self.download_thread.finished.connect(self._on_finished)
        self.download_thread.start()

    def _on_progress(self, model_id: str, current: int, total: int):
        """Actualiza la barra de progreso."""
        if total > 0:
            percent = int((current / total) * 100)
            self.progress_bar.setValue(percent)
            self.progress_label.setText(
                f"Descargando {model_id}... {percent}%"
            )

    def _on_finished(self, model_id: str, success: bool):
        """Maneja la finalizacion de la descarga."""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.download_btn.setEnabled(True)

        if success:
            QMessageBox.information(
                self, "Exito",
                f"Modelo {model_id} descargado correctamente."
            )
        else:
            QMessageBox.critical(
                self, "Error",
                f"Error descargando el modelo {model_id}."
            )
