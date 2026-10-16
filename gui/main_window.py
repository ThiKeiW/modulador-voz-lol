"""
Ventana principal de la aplicacion Modulador de Voz Virtual.
Interfaz grafica con PyQt6.
"""
import sys
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QSlider, QFrame,
    QStatusBar, QMenuBar, QMessageBox, QSplitter,
    QGroupBox, QProgressBar, QTextEdit,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette, QIcon, QAction

from config import (
    APP_NAME, APP_VERSION, WINDOW_WIDTH, WINDOW_HEIGHT,
    DEFAULT_PITCH_SHIFT, DEFAULT_F0_METHOD, DEFAULT_INDEX_RATE,
)
from core.audio_capture import AudioCapture
from core.rvc_engine import RVCEngine
from core.model_manager import ModelManager
from core.conversion_thread import ConversionThread


class AudioVisualizer(QFrame):
    """Widget de visualizacion de audio simple."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(80)
        self.setMaximumHeight(120)
        self.audio_level = 0.0
        self.setStyleSheet("""
            QFrame {
                background-color: #141414;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
            }
        """)

    def update_level(self, level: float):
        """Actualiza el nivel de audio (0.0 - 1.0)."""
        self.audio_level = min(1.0, max(0.0, level))
        self.update()

    def paintEvent(self, event):
        """Dibuja el visualizador."""
        from PyQt6.QtGui import QPainter, QPen, QLinearGradient
        from PyQt6.QtCore import QRect

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        width = rect.width()
        height = rect.height()

        # Fondo
        painter.fillRect(rect, QColor("#141414"))

        # Barras de audio
        num_bars = 40
        bar_width = max(2, (width - num_bars * 2) // num_bars)
        gap = 2

        for i in range(num_bars):
            x = i * (bar_width + gap)
            # Simular frecuencias
            freq_factor = abs(i - num_bars / 2) / (num_bars / 2)
            bar_height = int(height * self.audio_level * (1 - freq_factor * 0.5))
            bar_height = max(2, bar_height)

            # Rampa fucsia -> morado segun intensidad (siempre visible
            # sobre el fondo carbon).
            intensity = self.audio_level * (1 - freq_factor * 0.3)
            r = int(120 + 135 * intensity)
            g = int(20 + 27 * (1 - intensity))
            b = int(140 + 39 * intensity)

            painter.setBrush(QColor(r, g, b))
            painter.setPen(Qt.PenStyle.NoPen)

            y = (height - bar_height) // 2
            painter.drawRoundedRect(x, y, bar_width, bar_height, 2, 2)

        painter.end()


class MainWindow(QMainWindow):
    """Ventana principal del Modulador de Voz."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setMinimumSize(900, 600)

        # Motor components (lazy init)
        self.model_manager = ModelManager()
        self.rvc_engine = None
        self.tts_engine = None
        self.audio_capture = None
        self.conversion_thread = None
        self.selected_model_id = None
        self.loaded_model_id = None

        self._setup_ui()
        self._setup_menu()
        self._setup_status_bar()

    def _setup_ui(self):
        """Configura la interfaz de usuario."""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Splitter principal
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # Panel izquierdo: Personajes
        left_panel = self._create_character_panel()
        splitter.addWidget(left_panel)

        # Panel derecho: Controles + Visualizador
        right_panel = self._create_right_panel()
        splitter.addWidget(right_panel)

        splitter.setSizes([300, 600])

    # Paleta 60/30/10 — fondo #170B33 (morado oscuro), superficies
    # #282828/#141414 (carbon), acento #FF2FB3 (fucsia neon).
    # Texto siempre claro (#F5F3FF / #B9B1D0). Sin cajas con borde.

    def _create_character_panel(self) -> QFrame:
        """Crea el panel de seleccion de personajes."""
        panel = QFrame()
        panel.setFrameShape(QFrame.Shape.NoFrame)
        panel.setStyleSheet("QFrame { background: transparent; border: none; }")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)

        # Titulo
        title = QLabel("PERSONAJES")
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: #F5F3FF; padding: 5px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Lista de personajes
        self.character_list = QVBoxLayout()
        self.character_list.setSpacing(8)
        layout.addLayout(self.character_list)

        # Agregar personajes demo
        self._add_character_button("Aatrox", "aatrox", "Darkin Blade - EN")
        self._add_character_button("Ezreal", "ezreal", "Prodigal Explorer - EN")
        self._add_character_button("Briar", "briar_latino", "Espanol Latino")
        self._add_character_button("Yuumi", "yuumi_latino", "Espanol Latino")

        # Grupo de personalizados (dinamico, desde ModelManager)
        self.customs_title = QLabel("PERSONALIZADOS")
        self.customs_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.customs_title.setStyleSheet("color: #F5F3FF; padding: 5px;")
        self.customs_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.customs_title)
        self.customs_layout = QVBoxLayout()
        self.customs_layout.setSpacing(8)
        layout.addLayout(self.customs_layout)
        self._refresh_custom_buttons()

        layout.addStretch()

        return panel

    def _refresh_custom_buttons(self):
        """Reconstruye el grupo Personalizados desde el ModelManager."""
        while self.customs_layout.count():
            item = self.customs_layout.takeAt(0)
            w = item.widget() if item is not None else None
            if w is not None:
                w.deleteLater()
            lay = item.layout() if item is not None else None
            if lay is not None:
                while lay.count():
                    sub = lay.takeAt(0)
                    if sub.widget() is not None:
                        sub.widget().deleteLater()
                lay.deleteLater()

        customs = [
            m for m in self.model_manager.get_downloaded_models()
            if m.is_custom
        ]
        self.customs_title.setVisible(bool(customs))
        for m in customs:
            row = QHBoxLayout()
            row.setSpacing(4)
            parts = []
            if m.language:
                parts.append(m.language)
            if not m.index_path:
                parts.append("sin índice")
            sub = " · ".join(parts)
            self._add_character_button(m.name, m.id, sub, target=row)
            delete_btn = QPushButton("✕")
            delete_btn.setFixedSize(32, 50)
            delete_btn.setToolTip(f"Eliminar '{m.name}'")
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #282828;
                    color: #B9B1D0;
                    border: 1px solid #3d3d3d;
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: bold;
                }
                QPushButton:hover { color: #FF2FB3; border-color: #FF2FB3; }
            """)
            delete_btn.clicked.connect(
                lambda checked, mid=m.id, mname=m.name: self._on_delete_custom(mid, mname)
            )
            row.addWidget(delete_btn)
            self.customs_layout.addLayout(row)

    def _on_delete_custom(self, model_id: str, name: str):
        """Elimina un custom con confirmacion."""
        ans = QMessageBox.question(
            self, "Eliminar modelo",
            f"¿Eliminar '{name}'? Se borran sus archivos.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        if self.model_manager.delete_model(model_id):
            if self.selected_model_id == model_id:
                self.selected_model_id = None
                self.character_header.setText("Selecciona un personaje")
            if self.loaded_model_id == model_id:
                self.loaded_model_id = None
                if self.rvc_engine is not None and hasattr(self.rvc_engine, "unload_model"):
                    try:
                        self.rvc_engine.unload_model()
                    except Exception:
                        pass
            self.log(f"Modelo '{name}' eliminado.")
            self._refresh_custom_buttons()

    def _add_character_button(self, name: str, model_id: str, subtitle: str, target=None):
        """Agrega un boton de personaje a la lista."""
        btn = QPushButton(f"  {name}\n  {subtitle}")
        btn.setMinimumHeight(50)
        btn.setText(f"  {name}\n  {subtitle}")
        btn.setStyleSheet("""
            QPushButton {
                background-color: #282828;
                color: #F5F3FF;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                text-align: left;
                padding: 8px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #333333;
                border-color: #FF2FB3;
            }
            QPushButton:pressed {
                background-color: #4B0082;
                color: #FFFFFF;
            }
        """)
        btn.clicked.connect(lambda checked, mid=model_id: self._select_character(mid))
        btn.setObjectName(f"char_{model_id}")
        (target if target is not None else self.character_list).addWidget(btn)
        return btn

    def _create_right_panel(self) -> QFrame:
        """Crea el panel derecho con controles y visualizador."""
        panel = QFrame()
        panel.setFrameShape(QFrame.Shape.NoFrame)
        panel.setStyleSheet("QFrame { background: transparent; border: none; }")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)

        # Header del personaje seleccionado
        self.character_header = QLabel("Selecciona un personaje")
        self.character_header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.character_header.setStyleSheet("color: #F5F3FF; padding: 10px;")
        self.character_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.character_header)

        # Controles de voz
        controls_group = self._create_voice_controls()
        layout.addWidget(controls_group)

        # Salida (microfono virtual para Discord / llamadas)
        output_group = self._create_output_group()
        layout.addWidget(output_group)

        # Visualizador de audio
        vis_label = QLabel("VISUALIZADOR DE AUDIO")
        vis_label.setStyleSheet("color: #B9B1D0; font-size: 10px; padding-top: 5px;")
        layout.addWidget(vis_label)

        self.visualizer = AudioVisualizer()
        layout.addWidget(self.visualizer)

        # Log de actividad
        self.log_area = QTextEdit()
        self.log_area.setMaximumHeight(120)
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("""
            QTextEdit {
                background-color: #141414;
                color: #B9B1D0;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                font-family: 'Consolas', monospace;
                font-size: 10px;
                padding: 5px;
            }
        """)
        layout.addWidget(self.log_area)

        # Botones principales
        buttons_layout = QHBoxLayout()

        self.start_btn = QPushButton("Iniciar Conversion")
        self.start_btn.setMinimumHeight(45)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF2FB3;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #FF5CC8; }
            QPushButton:pressed { background-color: #C4007F; }
            QPushButton:disabled { background-color: #3d3d3d; color: #888888; }
        """)
        self.start_btn.clicked.connect(self._on_start_click)
        buttons_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("Detener")
        self.stop_btn.setMinimumHeight(45)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #4B0082;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #5F0AA8; }
            QPushButton:pressed { background-color: #36005E; }
            QPushButton:disabled { background-color: #3d3d3d; color: #888888; }
        """)
        self.stop_btn.clicked.connect(self._on_stop_click)
        buttons_layout.addWidget(self.stop_btn)

        layout.addLayout(buttons_layout)

        return panel

    def _create_voice_controls(self) -> QGroupBox:
        """Crea el grupo de controles de voz."""
        group = QGroupBox("Controles de Voz")
        group.setFlat(True)
        group.setStyleSheet("""
            QGroupBox {
                background: transparent;
                border: none;
                padding-top: 12px;
                margin-top: 6px;
                color: #F5F3FF;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 0px;
                padding: 0 0px;
            }
        """)

        layout = QVBoxLayout(group)

        # Pitch
        pitch_layout = QHBoxLayout()
        pitch_title = QLabel("Pitch:")
        pitch_title.setStyleSheet("color: #F5F3FF;")
        pitch_layout.addWidget(pitch_title)
        self.pitch_slider = QSlider(Qt.Orientation.Horizontal)
        self.pitch_slider.setRange(-12, 12)
        self.pitch_slider.setValue(0)
        self.pitch_slider.setToolTip(
            "Tono de la voz convertida: a la izquierda mas grave, "
            "a la derecha mas agudo. 0 = tono natural del personaje."
        )
        self.pitch_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.pitch_slider.setTickInterval(1)
        self.pitch_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 6px;
                background: #3d3d3d;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #FF2FB3;
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QSlider::sub-page:horizontal {
                background: #FF2FB3;
                border-radius: 3px;
            }
        """)
        self.pitch_slider.valueChanged.connect(self._on_pitch_changed)
        pitch_layout.addWidget(self.pitch_slider)

        self.pitch_label = QLabel("0")
        self.pitch_label.setMinimumWidth(30)
        self.pitch_label.setStyleSheet("color: #FF2FB3; font-weight: bold;")
        pitch_layout.addWidget(self.pitch_label)

        layout.addLayout(pitch_layout)

        # Metodo de deteccion de tono (los 3 funcionan; cambia calidad/velocidad)
        f0_layout = QHBoxLayout()
        f0_title = QLabel("Calidad de voz:")
        f0_title.setStyleSheet("color: #F5F3FF;")
        f0_layout.addWidget(f0_title)
        self.f0_combo = QComboBox()
        self.f0_combo.addItem("Alta calidad (recomendado)", "rmvpe")
        self.f0_combo.addItem("Rapida (si va lento)", "pm")
        self.f0_combo.addItem("Clasica", "harvest")
        self.f0_combo.setToolTip(
            "Como detecta tu tono de voz. Los 3 funcionan: RMVPE suena "
            "mejor, PM es mas rapido, Harvest es el metodo clasico."
        )
        self.f0_combo.currentIndexChanged.connect(
            lambda _: self._on_f0_method_changed(self.f0_combo.currentData())
        )
        self.f0_combo.setStyleSheet("""
            QComboBox {
                background-color: #282828;
                color: #F5F3FF;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #282828;
                color: #F5F3FF;
                selection-background-color: #4B0082;
            }
        """)
        f0_layout.addWidget(self.f0_combo)
        layout.addLayout(f0_layout)

        return group

    def _create_output_group(self) -> QGroupBox:
        """Selector de salida para usar la voz como microfono virtual
        (Discord/llamadas) via cable virtual (VB-CABLE)."""
        from core.audio_devices import (
            list_output_devices,
            find_cable_playback,
            find_cable_mic,
        )
        self._audio_device_helpers = (list_output_devices, find_cable_playback, find_cable_mic)

        group = QGroupBox("Salida")
        group.setFlat(True)
        group.setStyleSheet("""
            QGroupBox {
                background: transparent;
                border: none;
                padding-top: 12px;
                margin-top: 6px;
                color: #F5F3FF;
                font-weight: bold;
                font-size: 11px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 0px;
                padding: 0 0px;
            }
        """)
        layout = QVBoxLayout(group)

        row = QHBoxLayout()
        out_title = QLabel("Reproducir voz en:")
        out_title.setStyleSheet("color: #F5F3FF;")
        row.addWidget(out_title)
        self.output_combo = QComboBox()
        self.output_combo.setStyleSheet("""
            QComboBox {
                background-color: #282828;
                color: #F5F3FF;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 6px 10px;
                min-height: 20px;
            }
            QComboBox QAbstractItemView {
                background-color: #282828;
                color: #F5F3FF;
                selection-background-color: #4B0082;
            }
        """)
        row.addWidget(self.output_combo, 1)
        layout.addLayout(row)

        self.cable_hint = QLabel("")
        self.cable_hint.setWordWrap(True)
        self.cable_hint.setStyleSheet("color: #B9B1D0; font-size: 10px;")
        layout.addWidget(self.cable_hint)

        btn_row = QHBoxLayout()
        self.use_cable_btn = QPushButton("Usar cable virtual")
        self.use_cable_btn.setStyleSheet("""
            QPushButton {
                background-color: #4B0082;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #5F0AA8; }
            QPushButton:disabled { background-color: #3d3d3d; color: #888888; }
        """)
        self.use_cable_btn.clicked.connect(self._on_use_cable_click)
        btn_row.addWidget(self.use_cable_btn)

        refresh_btn = QPushButton("Refrescar")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #282828;
                color: #B9B1D0;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 10px;
            }
            QPushButton:hover { background-color: #333333; color: #F5F3FF; }
        """)
        refresh_btn.clicked.connect(self._refresh_output_devices)
        btn_row.addWidget(refresh_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._cable_index = None
        self._refresh_output_devices()
        return group

    def _refresh_output_devices(self):
        """Lista salidas y detecta cable virtual instalado."""
        list_outputs, find_playback, find_mic = self._audio_device_helpers
        self.output_combo.clear()
        self.output_combo.addItem("Predeterminado del sistema", None)
        for index, name in list_outputs():
            # Evitar duplicados con distinto host API que confunden.
            if self.output_combo.findText(name) < 0:
                self.output_combo.addItem(name, index)

        self._cable_index = find_playback()
        mic_name = find_mic()
        if self._cable_index is not None:
            self.cable_hint.setStyleSheet("color: #7DE8A8; font-size: 10px;")
            self.cable_hint.setText(
                "Cable virtual detectado. Pulsa 'Usar cable virtual' y en "
                f"Discord/Windows elige como microfono '{mic_name or 'CABLE Output'}'."
            )
            self.use_cable_btn.setEnabled(True)
        else:
            self.cable_hint.setStyleSheet("color: #E8C15A; font-size: 10px;")
            self.cable_hint.setText(
                "Sin cable virtual: instala VB-CABLE (vb-audio.com/Cable) "
                "como administrador y pulsa Refrescar."
            )
            self.use_cable_btn.setEnabled(False)

    def _on_use_cable_click(self):
        """Selecciona el cable virtual como salida."""
        if self._cable_index is None:
            return
        idx = self.output_combo.findData(self._cable_index)
        if idx >= 0:
            self.output_combo.setCurrentIndex(idx)
            self.log(f"Salida -> cable virtual ({self.output_combo.currentText()})")

    def _selected_output_device(self):
        """Indice sounddevice de salida o None (predeterminado)."""
        return self.output_combo.currentData()

    def _setup_menu(self):
        """Configura la barra de menus."""
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #170B33;
                color: #F5F3FF;
                border-bottom: 1px solid #3d3d3d;
            }
            QMenuBar::item:selected { background-color: #4B0082; }
            QMenu {
                background-color: #282828;
                color: #F5F3FF;
                border: 1px solid #3d3d3d;
            }
            QMenu::item:selected { background-color: #4B0082; }
        """)

        # Menu Archivo
        file_menu = menubar.addMenu("Archivo")
        file_menu.addAction("Descargar Modelos...", self._on_download_models)
        file_menu.addAction("Importar Modelo...", self._on_import_model)
        file_menu.addSeparator()
        file_menu.addAction("Salir", self.close)

        # Menu Herramientas
        tools_menu = menubar.addMenu("Herramientas")
        tools_menu.addAction("Configuracion de Audio...", self._on_audio_settings)

        # Menu Ayuda
        help_menu = menubar.addMenu("Ayuda")
        help_menu.addAction("Acerca de...", self._on_about)

    def _setup_status_bar(self):
        """Configura la barra de estado."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #141414;
                color: #B9B1D0;
                border-top: 1px solid #3d3d3d;
            }
        """)
        self.status_bar.showMessage("Listo - Selecciona un personaje para comenzar")

        # Indicador de dispositivo
        self.device_label = QLabel("GPU: GTX 1650")
        self.device_label.setStyleSheet("color: #7DE8A8; padding-right: 10px;")
        self.status_bar.addPermanentWidget(self.device_label)

    def _select_character(self, model_id: str):
        """Selecciona un personaje para usar."""
        self.selected_model_id = model_id
        self.character_header.setText(f"Personaje: {model_id.upper()}")
        self.log(f"Personaje seleccionado: {model_id}")
        self.status_bar.showMessage(f"Modelo: {model_id} - Listo para conversion")

    def _on_pitch_changed(self, value: int):
        """Callback cuando cambia el pitch."""
        sign = "+" if value > 0 else ""
        self.pitch_label.setText(f"{sign}{value}")
        if self.conversion_thread:
            self.conversion_thread.set_pitch_shift(value)

    def _on_f0_method_changed(self, method: str):
        """Callback cuando cambia el algoritmo de extraccion de pitch (F0)."""
        if self.conversion_thread:
            self.conversion_thread.set_f0_method(method)

    def _on_start_click(self):
        """Inicia la conversion de voz."""
        if not self.selected_model_id:
            QMessageBox.warning(
                self, "Sin modelo",
                "Selecciona un personaje primero."
            )
            return

        model = self.model_manager.get_model(self.selected_model_id)
        if not model or not model.downloaded or not model.path:
            QMessageBox.warning(
                self, "Modelo no disponible",
                f"El modelo '{self.selected_model_id}' no esta descargado.\n"
                "Ve a Archivo > Descargar Modelos..."
            )
            return

        if self.rvc_engine is None:
            self.rvc_engine = RVCEngine()
            self.rvc_engine.initialize()

        if self.loaded_model_id != model.id:
            self.log(f"Cargando modelo: {model.name}...")
            ok = self.rvc_engine.load_model(
                model.path, model.name, model.index_path or None
            )
            if not ok:
                QMessageBox.critical(
                    self, "Error al cargar modelo",
                    f"No se pudo cargar '{model.name}'. Revisa que "
                    "models/hubert_base/ y models/rmvpe/rmvpe.pt existan "
                    "(python scripts/download_assets.py) y la consola para mas detalles."
                )
                return
            self.loaded_model_id = model.id

        if self.audio_capture is None:
            self.audio_capture = AudioCapture()

        out_dev = self._selected_output_device()
        self.log(f"Salida de voz -> {self.output_combo.currentText()}")
        self.conversion_thread = ConversionThread(
            audio_capture=self.audio_capture,
            rvc_engine=self.rvc_engine,
            output_device=out_dev,
            pitch_shift=self.pitch_slider.value(),
            f0_method=self.f0_combo.currentData(),
            index_rate=DEFAULT_INDEX_RATE if model.index_path else 0.0,
        )
        self.conversion_thread.status_changed.connect(self._on_conversion_status)
        self.conversion_thread.error_occurred.connect(self._on_conversion_error)
        self.conversion_thread.latency_updated.connect(self._on_latency_updated)
        self.conversion_thread.level_updated.connect(self.visualizer.update_level)
        self.conversion_thread.start()

        self.log(f"Iniciando conversion de voz con {model.name}...")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_bar.showMessage("Convirtiendo voz en tiempo real...")

    def _on_stop_click(self):
        """Detiene la conversion de voz."""
        if self.conversion_thread:
            self.conversion_thread.stop()
            self.conversion_thread = None

        self.visualizer.update_level(0.0)
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_bar.showMessage("Conversion detenida")
        self.log("Conversion detenida")

    def _on_conversion_status(self, status: str):
        self.log(f"[Conversion] {status}")

    def _on_conversion_error(self, message: str):
        self.log(f"[Error] {message}")
        self.status_bar.showMessage("Error en la conversion - ver log")
        self._on_stop_click()

    def _on_latency_updated(self, latency_ms: float):
        self.status_bar.showMessage(f"Convirtiendo voz en tiempo real... ({latency_ms:.0f}ms/bloque)")

    def _on_download_models(self):
        """Descarga modelos pre-entrenados."""
        from gui.download_dialog import DownloadDialog
        dialog = DownloadDialog(self, on_downloaded=self._on_model_downloaded)
        dialog.exec()

    def _on_model_downloaded(self, model_id: str):
        """Refresca el registro tras una descarga para usar el modelo
        sin reiniciar, y lo deja seleccionado."""
        if self.model_manager.refresh_model(model_id):
            self.log(f"Modelo '{model_id}' listo para usar (sin reiniciar).")
            self._select_character(model_id)
        else:
            self.log(f"[Aviso] No se pudo registrar '{model_id}', revisa la descarga.")

    def _on_import_model(self):
        """Abre el dialogo de importacion de customs."""
        from gui.import_dialog import ImportDialog
        dialog = ImportDialog(self, self.model_manager, on_imported=self._on_model_imported)
        dialog.exec()

    def _on_model_imported(self, model_id: str):
        """Refresca el panel tras importar y deja seleccionado el custom."""
        self.log(f"Modelo '{model_id}' importado y listo (sin reiniciar).")
        self._refresh_custom_buttons()
        self._select_character(model_id)

    def _on_audio_settings(self):
        """Configuracion de audio."""
        QMessageBox.information(
            self, "Configuracion",
            "Configuracion de audio - Proximamente."
        )

    def _on_about(self):
        """Muestra informacion de la aplicacion."""
        QMessageBox.about(
            self, f"Acerca de {APP_NAME}",
            f"<h2>{APP_NAME} v{APP_VERSION}</h2>"
            "<p>Modulador de voz virtual con IA para personajes de "
            "League of Legends.</p>"
            "<p>Motor: RVC (Retrieval-based Voice Conversion)</p>"
            "<p>Idioma: Espanol Latino</p>"
            "<p>Plataforma: Windows</p>"
        )

    def log(self, message: str):
        """Agrega un mensaje al log."""
        self.log_area.append(f"> {message}")
        self.log_area.verticalScrollBar().setValue(
            self.log_area.verticalScrollBar().maximum()
        )

    def closeEvent(self, event):
        """Maneja el cierre de la ventana."""
        if self.conversion_thread:
            self.conversion_thread.stop()
        event.accept()
