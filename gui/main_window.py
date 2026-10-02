"""
Ventana principal de la aplicacion Modulador de Voz Virtual.
Interfaz grafica con PyQt6.
"""
import sys
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QSlider, QFrame,
    QStatusBar, QMenuBar, QMessageBox, QSplitter,
    QGroupBox, QCheckBox, QProgressBar, QTextEdit,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette, QIcon, QAction

from config import (
    APP_NAME, APP_VERSION, WINDOW_WIDTH, WINDOW_HEIGHT,
    DEFAULT_PITCH_SHIFT, DEFAULT_F0_METHOD,
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
                background-color: #1a1a2e;
                border: 1px solid #16213e;
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
        painter.fillRect(rect, QColor("#1a1a2e"))

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

            # Color basado en intensidad
            intensity = self.audio_level * (1 - freq_factor * 0.3)
            r = int(100 + 155 * intensity)
            g = int(50 + 100 * (1 - intensity))
            b = int(200 * (1 - intensity))

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

    def _create_character_panel(self) -> QFrame:
        """Crea el panel de seleccion de personajes."""
        panel = QFrame()
        panel.setFrameShape(QFrame.Shape.StyledPanel)
        panel.setStyleSheet("""
            QFrame {
                background-color: #0f0f23;
                border: 1px solid #1a1a3e;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)

        # Titulo
        title = QLabel("PERSONAJES")
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: #e94560; padding: 5px;")
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

        layout.addStretch()

        # Boton entrenar
        train_btn = QPushButton("Entrenar Nuevo Personaje")
        train_btn.setMinimumHeight(40)
        train_btn.setStyleSheet("""
            QPushButton {
                background-color: #533483;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #7b2cbf; }
            QPushButton:pressed { background-color: #3c096c; }
        """)
        train_btn.clicked.connect(self._on_train_click)
        layout.addWidget(train_btn)

        return panel

    def _add_character_button(self, name: str, model_id: str, subtitle: str):
        """Agrega un boton de personaje a la lista."""
        btn = QPushButton(f"  {name}\n  {subtitle}")
        btn.setMinimumHeight(50)
        btn.setText(f"  {name}\n  {subtitle}")
        btn.setStyleSheet("""
            QPushButton {
                background-color: #16213e;
                color: #e0e0e0;
                border: 2px solid #1a1a3e;
                border-radius: 6px;
                text-align: left;
                padding: 8px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #1a1a3e;
                border-color: #e94560;
            }
            QPushButton:pressed {
                background-color: #e94560;
                color: white;
            }
        """)
        btn.clicked.connect(lambda checked, mid=model_id: self._select_character(mid))
        btn.setObjectName(f"char_{model_id}")
        self.character_list.addWidget(btn)

    def _create_right_panel(self) -> QFrame:
        """Crea el panel derecho con controles y visualizador."""
        panel = QFrame()
        panel.setFrameShape(QFrame.Shape.StyledPanel)
        panel.setStyleSheet("""
            QFrame {
                background-color: #0f0f23;
                border: 1px solid #1a1a3e;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)

        # Header del personaje seleccionado
        self.character_header = QLabel("Selecciona un personaje")
        self.character_header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.character_header.setStyleSheet("color: #e94560; padding: 10px;")
        self.character_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.character_header)

        # Controles de voz
        controls_group = self._create_voice_controls()
        layout.addWidget(controls_group)

        # Visualizador de audio
        vis_label = QLabel("VISUALIZADOR DE AUDIO")
        vis_label.setStyleSheet("color: #7b7b9e; font-size: 10px; padding-top: 5px;")
        layout.addWidget(vis_label)

        self.visualizer = AudioVisualizer()
        layout.addWidget(self.visualizer)

        # Log de actividad
        self.log_area = QTextEdit()
        self.log_area.setMaximumHeight(120)
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a2e;
                color: #7b7b9e;
                border: 1px solid #16213e;
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
                background-color: #e94560;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #ff6b81; }
            QPushButton:pressed { background-color: #c0392b; }
            QPushButton:disabled { background-color: #444; color: #888; }
        """)
        self.start_btn.clicked.connect(self._on_start_click)
        buttons_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("Detener")
        self.stop_btn.setMinimumHeight(45)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #533483;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #7b2cbf; }
            QPushButton:pressed { background-color: #3c096c; }
            QPushButton:disabled { background-color: #444; color: #888; }
        """)
        self.stop_btn.clicked.connect(self._on_stop_click)
        buttons_layout.addWidget(self.stop_btn)

        layout.addLayout(buttons_layout)

        return panel

    def _create_voice_controls(self) -> QGroupBox:
        """Crea el grupo de controles de voz."""
        group = QGroupBox("Controles de Voz")
        group.setStyleSheet("""
            QGroupBox {
                background-color: #16213e;
                border: 1px solid #1a1a3e;
                border-radius: 6px;
                padding: 15px;
                margin-top: 10px;
                color: #e0e0e0;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
            }
        """)

        layout = QVBoxLayout(group)

        # Pitch
        pitch_layout = QHBoxLayout()
        pitch_layout.addWidget(QLabel("Pitch:"))
        self.pitch_slider = QSlider(Qt.Orientation.Horizontal)
        self.pitch_slider.setRange(-12, 12)
        self.pitch_slider.setValue(0)
        self.pitch_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.pitch_slider.setTickInterval(1)
        self.pitch_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 6px;
                background: #1a1a2e;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #e94560;
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QSlider::sub-page:horizontal {
                background: #e94560;
                border-radius: 3px;
            }
        """)
        self.pitch_slider.valueChanged.connect(self._on_pitch_changed)
        pitch_layout.addWidget(self.pitch_slider)

        self.pitch_label = QLabel("0")
        self.pitch_label.setMinimumWidth(30)
        self.pitch_label.setStyleSheet("color: #e94560; font-weight: bold;")
        pitch_layout.addWidget(self.pitch_label)

        layout.addLayout(pitch_layout)

        # Metodo F0
        f0_layout = QHBoxLayout()
        f0_layout.addWidget(QLabel("Algoritmo F0:"))
        self.f0_combo = QComboBox()
        self.f0_combo.addItems(["rmvpe", "harvest", "crepe"])
        self.f0_combo.setCurrentText("rmvpe")
        self.f0_combo.currentTextChanged.connect(self._on_f0_method_changed)
        self.f0_combo.setStyleSheet("""
            QComboBox {
                background-color: #1a1a2e;
                color: #e0e0e0;
                border: 1px solid #1a1a3e;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #1a1a2e;
                color: #e0e0e0;
                selection-background-color: #e94560;
            }
        """)
        f0_layout.addWidget(self.f0_combo)
        layout.addLayout(f0_layout)

        # Efectos
        effects_layout = QHBoxLayout()
        effects_layout.addWidget(QLabel("Efectos:"))

        self.reverb_cb = QCheckBox("Reverb")
        self.reverb_cb.setStyleSheet("color: #e0e0e0;")
        effects_layout.addWidget(self.reverb_cb)

        self.echo_cb = QCheckBox("Eco")
        self.echo_cb.setStyleSheet("color: #e0e0e0;")
        effects_layout.addWidget(self.echo_cb)

        layout.addLayout(effects_layout)

        return group

    def _setup_menu(self):
        """Configura la barra de menus."""
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #0f0f23;
                color: #e0e0e0;
                border-bottom: 1px solid #1a1a3e;
            }
            QMenuBar::item:selected { background-color: #1a1a3e; }
            QMenu {
                background-color: #16213e;
                color: #e0e0e0;
                border: 1px solid #1a1a3e;
            }
            QMenu::item:selected { background-color: #e94560; }
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
        tools_menu.addAction("Entrenar Modelo...", self._on_train_click)

        # Menu Ayuda
        help_menu = menubar.addMenu("Ayuda")
        help_menu.addAction("Acerca de...", self._on_about)

    def _setup_status_bar(self):
        """Configura la barra de estado."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #0f0f23;
                color: #7b7b9e;
                border-top: 1px solid #1a1a3e;
            }
        """)
        self.status_bar.showMessage("Listo - Selecciona un personaje para comenzar")

        # Indicador de dispositivo
        self.device_label = QLabel("GPU: GTX 1650")
        self.device_label.setStyleSheet("color: #4ecca3; padding-right: 10px;")
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
            if not self.rvc_engine.load_model(model.path, model.name):
                QMessageBox.critical(
                    self, "Error al cargar modelo",
                    f"No se pudo cargar '{model.name}'. Revisa la consola para mas detalles."
                )
                return
            self.loaded_model_id = model.id

        if self.audio_capture is None:
            self.audio_capture = AudioCapture()

        self.conversion_thread = ConversionThread(
            audio_capture=self.audio_capture,
            rvc_engine=self.rvc_engine,
            pitch_shift=self.pitch_slider.value(),
            f0_method=self.f0_combo.currentText(),
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
        """Reacciona a cambios de estado del ConversionThread."""
        self.log(f"[Conversion] {status}")

    def _on_conversion_error(self, message: str):
        """Muestra errores del ConversionThread y detiene la conversion."""
        self.log(f"[Error] {message}")
        self.status_bar.showMessage("Error en la conversion - ver log")
        self._on_stop_click()

    def _on_latency_updated(self, latency_ms: float):
        """Actualiza la barra de estado con la latencia del ultimo chunk."""
        self.status_bar.showMessage(f"Convirtiendo voz en tiempo real... ({latency_ms:.0f}ms)")

    def _on_train_click(self):
        """Abre la ventana de entrenamiento."""
        QMessageBox.information(
            self, "Entrenamiento",
            "GUI de entrenamiento - Proximamente.\n\n"
            "Para entrenar un modelo RVC:\n"
            "1. Recopila 10-30 min de audio del personaje\n"
            "2. Usa RVC WebUI o Ultimate RVC\n"
            "3. Coloca el modelo .pth en models/custom/"
        )

    def _on_download_models(self):
        """Descarga modelos pre-entrenados."""
        from gui.download_dialog import DownloadDialog
        dialog = DownloadDialog(self)
        dialog.exec()

    def _on_import_model(self):
        """Importa un modelo externo."""
        QMessageBox.information(
            self, "Importar Modelo",
            "Selecciona un archivo .pth para importar como modelo custom."
        )

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
