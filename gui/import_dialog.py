"""
gui/import_dialog.py

Dialogo unico para importar modelos custom (ej. entrenados en Ultimate
RVC): .pth obligatorio (validado como checkpoint RVC real) + .index
opcional (retrieval; sin el funciona igual con algo menos de calidad,
como Briar/Yuumi).
"""
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QFileDialog, QMessageBox,
)
from PyQt6.QtCore import Qt


class ImportDialog(QDialog):
    """Importar un .pth (+ .index opcional) como personaje personalizado."""

    def __init__(self, parent=None, model_manager=None, on_imported=None):
        super().__init__(parent)
        self.model_manager = model_manager
        self._on_imported = on_imported
        self._pth_ok = False

        self.setWindowTitle("Importar Modelo Personalizado")
        self.setMinimumSize(520, 340)
        self.setStyleSheet("""
            QDialog { background-color: #170B33; color: #F5F3FF; }
            QLabel { color: #F5F3FF; }
            QLineEdit {
                background-color: #282828;
                color: #F5F3FF;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 6px 10px;
            }
            QPushButton { color: white; }
        """)
        self._setup_ui()

    # ------------------------------------------------------------------
    def _setup_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("Importar modelo (.pth de Ultimate RVC, RVC-WebUI, etc.)")
        title.setStyleSheet("font-size: 13px; font-weight: bold; color: #F5F3FF;")
        layout.addWidget(title)

        # .pth obligatorio
        layout.addWidget(QLabel("Archivo .pth (obligatorio):"))
        row_pth = QHBoxLayout()
        self.pth_edit = QLineEdit()
        self.pth_edit.setReadOnly(True)
        self.pth_edit.setPlaceholderText("Selecciona el .pth del personaje...")
        row_pth.addWidget(self.pth_edit, 1)
        btn_pth = QPushButton("Examinar...")
        btn_pth.clicked.connect(self._browse_pth)
        row_pth.addWidget(btn_pth)
        layout.addLayout(row_pth)

        self.pth_status = QLabel("")
        self.pth_status.setStyleSheet("font-size: 10px;")
        layout.addWidget(self.pth_status)

        # .index opcional
        layout.addWidget(QLabel("Archivo .index (opcional):"))
        row_idx = QHBoxLayout()
        self.index_edit = QLineEdit()
        self.index_edit.setReadOnly(True)
        self.index_edit.setPlaceholderText("Sin indice funciona igual (como Briar/Yuumi)...")
        row_idx.addWidget(self.index_edit, 1)
        btn_idx = QPushButton("Examinar...")
        btn_idx.clicked.connect(self._browse_index)
        row_idx.addWidget(btn_idx)
        btn_clear = QPushButton("Quitar")
        btn_clear.clicked.connect(lambda: self.index_edit.clear())
        row_idx.addWidget(btn_clear)
        layout.addLayout(row_idx)

        # Nombre + descripcion
        layout.addWidget(QLabel("Nombre del personaje:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Ej: Garen Latino")
        self.name_edit.textChanged.connect(self._update_import_enabled)
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("Descripcion (opcional):"))
        self.desc_edit = QLineEdit()
        layout.addWidget(self.desc_edit)

        # Botones
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.import_btn = QPushButton("Importar")
        self.import_btn.setMinimumHeight(35)
        self.import_btn.setEnabled(False)
        self.import_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF2FB3;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                padding: 8px 24px;
            }
            QPushButton:hover { background-color: #FF5CC8; }
            QPushButton:disabled { background-color: #3d3d3d; color: #888888; }
        """)
        self.import_btn.clicked.connect(self._on_import)
        btn_row.addWidget(self.import_btn)

        close_btn = QPushButton("Cerrar")
        close_btn.setMinimumHeight(35)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #4B0082;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
            }
            QPushButton:hover { background-color: #5F0AA8; }
        """)
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    def _browse_pth(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar modelo .pth", "",
            "Modelos RVC (*.pth);;Todos (*.*)",
        )
        if not path:
            return
        self.pth_edit.setText(path)
        self._validate_pth(path)
        self._update_import_enabled()

    def _validate_pth(self, path: str):
        """Chequeo rapido: ¿es checkpoint RVC real?"""
        try:
            info = self.model_manager.inspect_rvc_checkpoint(path)
        except Exception as e:
            self._pth_ok = False
            self.pth_status.setStyleSheet("color: #FF6B6B; font-size: 10px;")
            self.pth_status.setText(f"Archivo no valido: {e}")
            return
        self._pth_ok = True
        f0_txt = "con pitch" if info.get("f0") == 1 else "sin pitch"
        self.pth_status.setStyleSheet("color: #7DE8A8; font-size: 10px;")
        self.pth_status.setText(
            f"Modelo RVC valido: version {info.get('version')} · "
            f"{f0_txt} · {info.get('sr')} Hz"
        )
        # Sugerir nombre desde el archivo si esta vacio.
        if not self.name_edit.text().strip():
            self.name_edit.setText(Path(path).stem)

    def _browse_index(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar indice .index (opcional)", "",
            "Indices faiss (*.index);;Todos (*.*)",
        )
        if path:
            self.index_edit.setText(path)

    def _update_import_enabled(self):
        self.import_btn.setEnabled(
            self._pth_ok and bool(self.name_edit.text().strip())
        )

    def _on_import(self):
        name = self.name_edit.text().strip()
        try:
            model_id = self.model_manager.save_custom_model(
                model_path=self.pth_edit.text(),
                name=name,
                description=self.desc_edit.text().strip(),
                index_path=self.index_edit.text().strip(),
            )
        except Exception as e:
            QMessageBox.critical(self, "Error al importar", str(e))
            return
        if self._on_imported is not None:
            try:
                self._on_imported(model_id)
            except Exception as e:
                print(f"[ImportDialog] Error en callback: {e}")
        QMessageBox.information(
            self, "Exito",
            f"'{name}' importado correctamente.\n"
            "Ya puedes seleccionarlo en Personalizados.",
        )
        self.accept()
