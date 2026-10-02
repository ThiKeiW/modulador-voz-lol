"""
Controles de ajuste de voz (pitch, efectos, etc.).
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSlider, QComboBox, QCheckBox, QGroupBox,
    QPushButton, QSpinBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from config import DEFAULT_PITCH_SHIFT, DEFAULT_F0_METHOD


class VoiceControls(QWidget):
    """Widget de controles de ajuste de voz."""

    settings_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Grupo: Pitch
        pitch_group = QGroupBox("Pitch")
        pitch_group.setStyleSheet(self._group_style())
        pitch_layout = QVBoxLayout(pitch_group)

        # Slider de pitch
        slider_layout = QHBoxLayout()
        self.pitch_slider = QSlider(Qt.Orientation.Horizontal)
        self.pitch_slider.setRange(-12, 12)
        self.pitch_slider.setValue(DEFAULT_PITCH_SHIFT)
        self.pitch_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.pitch_slider.setTickInterval(1)
        self.pitch_slider.setStyleSheet(self._slider_style())
        self.pitch_slider.valueChanged.connect(self._on_settings_changed)
        slider_layout.addWidget(self.pitch_slider)

        self.pitch_value = QLabel("0")
        self.pitch_value.setFixedSize(35, 25)
        self.pitch_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pitch_value.setStyleSheet("""
            color: #e94560;
            font-weight: bold;
            font-size: 12px;
            background-color: #1a1a2e;
            border-radius: 4px;
        """)
        slider_layout.addWidget(self.pitch_value)

        pitch_layout.addLayout(slider_layout)

        # Labels de pitch
        labels_layout = QHBoxLayout()
        labels_layout.addWidget(QLabel("-12 (grave)"))
        labels_layout.addStretch()
        labels_layout.addWidget(QLabel("+12 (agudo)"))
        for lbl in labels_layout.findChildren(QLabel):
            lbl.setStyleSheet("color: #7b7b9e; font-size: 9px;")
        pitch_layout.addLayout(labels_layout)

        layout.addWidget(pitch_group)

        # Grupo: Algoritmo F0
        algo_group = QGroupBox("Algoritmo de Pitch Detection")
        algo_group.setStyleSheet(self._group_style())
        algo_layout = QVBoxLayout(algo_group)

        self.f0_combo = QComboBox()
        self.f0_combo.addItems(["rmvpe", "harvest", "crepe", "fcpe"])
        self.f0_combo.setCurrentText(DEFAULT_F0_METHOD)
        self.f0_combo.setStyleSheet(self._combo_style())
        self.f0_combo.currentTextChanged.connect(self._on_settings_changed)
        algo_layout.addWidget(self.f0_combo)

        # Descripcion del algoritmo
        self.algo_desc = QLabel("RMVPE: Mejor calidad, recomendado")
        self.algo_desc.setStyleSheet("color: #7b7b9e; font-size: 9px; font-style: italic;")
        self.algo_desc.setWordWrap(True)
        algo_layout.addWidget(self.algo_desc)

        layout.addWidget(algo_group)

        # Grupo: Efectos
        effects_group = QGroupBox("Efectos de Audio")
        effects_group.setStyleSheet(self._group_style())
        effects_layout = QVBoxLayout(effects_group)

        self.reverb_cb = QCheckBox("Reverberacion")
        self.reverb_cb.setStyleSheet(self._checkbox_style())
        self.reverb_cb.stateChanged.connect(self._on_settings_changed)
        effects_layout.addWidget(self.reverb_cb)

        self.echo_cb = QCheckBox("Eco / Delay")
        self.echo_cb.setStyleSheet(self._checkbox_style())
        self.echo_cb.stateChanged.connect(self._on_settings_changed)
        effects_layout.addWidget(self.echo_cb)

        self.normalize_cb = QCheckBox("Normalizar volumen")
        self.normalize_cb.setChecked(True)
        self.normalize_cb.setStyleSheet(self._checkbox_style())
        self.normalize_cb.stateChanged.connect(self._on_settings_changed)
        effects_layout.addWidget(self.normalize_cb)

        layout.addWidget(effects_group)

        # Grupo: Dispositivo de audio
        device_group = QGroupBox("Dispositivo de Audio")
        device_group.setStyleSheet(self._group_style())
        device_layout = QVBoxLayout(device_group)

        self.device_combo = QComboBox()
        self.device_combo.setStyleSheet(self._combo_style())
        self.device_combo.currentTextChanged.connect(self._on_settings_changed)
        device_layout.addWidget(self.device_combo)

        # Boton refrescar dispositivos
        refresh_btn = QPushButton("Refrescar dispositivos")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a1a2e;
                color: #7b7b9e;
                border: 1px solid #16213e;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 9px;
            }
            QPushButton:hover { background-color: #16213e; color: #e0e0e0; }
        """)
        refresh_btn.clicked.connect(self._refresh_devices)
        device_layout.addWidget(refresh_btn)

        layout.addWidget(device_group)

        # Cargar dispositivos iniciales
        self._refresh_devices()

    def _refresh_devices(self):
        """Refresca la lista de dispositivos de audio."""
        self.device_combo.clear()
        self.device_combo.addItems(["Predeterminado del sistema"])

        try:
            import pyaudio
            pa = pyaudio.PyAudio()
            for i in range(pa.get_device_count()):
                info = pa.get_device_info_by_index(i)
                if info["maxInputChannels"] > 0:
                    self.device_combo.addItem(info["name"])
            pa.terminate()
        except Exception:
            pass

    def get_settings(self) -> dict:
        """Retorna los ajustes actuales."""
        return {
            "pitch_shift": self.pitch_slider.value(),
            "f0_method": self.f0_combo.currentText(),
            "reverb": self.reverb_cb.isChecked(),
            "echo": self.echo_cb.isChecked(),
            "normalize": self.normalize_cb.isChecked(),
            "device": self.device_combo.currentText(),
        }

    def _on_settings_changed(self, *args):
        """Emite la senal de cambio de ajustes."""
        self.settings_changed.emit(self.get_settings())

    def _group_style(self) -> str:
        return """
            QGroupBox {
                background-color: #16213e;
                border: 1px solid #1a1a3e;
                border-radius: 6px;
                padding: 12px;
                margin-top: 8px;
                color: #e0e0e0;
                font-weight: bold;
                font-size: 11px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 5px;
            }
        """

    def _slider_style(self) -> str:
        return """
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
        """

    def _combo_style(self) -> str:
        return """
            QComboBox {
                background-color: #1a1a2e;
                color: #e0e0e0;
                border: 1px solid #1a1a3e;
                border-radius: 4px;
                padding: 6px 10px;
                min-height: 20px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox QAbstractItemView {
                background-color: #1a1a2e;
                color: #e0e0e0;
                selection-background-color: #e94560;
                border: 1px solid #1a1a3e;
            }
        """

    def _checkbox_style(self) -> str:
        return """
            QCheckBox {
                color: #e0e0e0;
                spacing: 8px;
                font-size: 11px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 2px solid #1a1a3e;
                background-color: #1a1a2e;
            }
            QCheckBox::indicator:checked {
                background-color: #e94560;
                border-color: #e94560;
            }
        """
