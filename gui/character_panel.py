"""
Panel de seleccion de personajes con iconos y metadata.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame, QGridLayout,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from config import PRETRAINED_MODELS


class CharacterCard(QFrame):
    """Tarjeta de personaje individual."""

    clicked = pyqtSignal(str)  # model_id

    def __init__(
        self,
        model_id: str,
        name: str,
        subtitle: str,
        is_es_latino: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.model_id = model_id
        self.is_selected = False

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumHeight(70)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._update_style(is_es_latino)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)

        # Indicador de idioma
        lang_label = QLabel("ES" if is_es_latino else "EN")
        lang_label.setFixedSize(30, 30)
        lang_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lang_label.setStyleSheet(f"""
            background-color: {"#4ecca3" if is_es_latino else "#e94560"};
            color: {"#0f0f23" if is_es_latino else "white"};
            border-radius: 15px;
            font-size: 9px;
            font-weight: bold;
        """)
        layout.addWidget(lang_label)

        # Info del personaje
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        name_label = QLabel(name)
        name_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        name_label.setStyleSheet("color: #e0e0e0;")
        info_layout.addWidget(name_label)

        subtitle_label = QLabel(subtitle)
        subtitle_label.setStyleSheet("color: #7b7b9e; font-size: 9px;")
        info_layout.addWidget(subtitle_label)

        layout.addLayout(info_layout)
        layout.addStretch()

    def _update_style(self, is_es_latino: bool):
        """Actualiza el estilo de la tarjeta."""
        border = "#4ecca3" if is_es_latino else "#1a1a3e"
        self.setStyleSheet(f"""
            CharacterCard {{
                background-color: #16213e;
                border: 2px solid {border};
                border-radius: 6px;
            }}
            CharacterCard:hover {{
                background-color: #1a1a3e;
                border-color: #e94560;
            }}
        """)

    def mousePressEvent(self, event):
        """Maneja el clic en la tarjeta."""
        self.clicked.emit(self.model_id)
        super().mousePressEvent(event)

    def set_selected(self, selected: bool):
        """Marca la tarjeta como seleccionada."""
        self.is_selected = selected
        if selected:
            self.setStyleSheet("""
                CharacterCard {
                    background-color: #e94560;
                    border: 2px solid #e94560;
                    border-radius: 6px;
                }
            """)
        else:
            self._update_style("latino" in self.model_id.lower())


class CharacterPanel(QWidget):
    """Panel de seleccion de personajes."""

    character_selected = pyqtSignal(str)  # model_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cards: dict[str, CharacterCard] = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #0f0f23;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #533483;
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        self.cards_layout = QVBoxLayout(container)
        self.cards_layout.setSpacing(8)
        self.cards_layout.setContentsMargins(5, 5, 5, 5)

        # Agregar personajes
        self._add_characters()

        self.cards_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

    def _add_characters(self):
        """Agrega las tarjetas de personajes."""
        characters = [
            ("aatrox", "Aatrox", "The Darkin Blade - EN", False),
            ("ezreal", "Ezreal", "The Prodigal Explorer - EN", False),
            ("briar_latino", "Briar", "Espanol Latino - RVC v2", True),
            ("yuumi_latino", "Yuumi", "Espanol Latino - RVC v2", True),
        ]

        for model_id, name, subtitle, is_latino in characters:
            card = CharacterCard(model_id, name, subtitle, is_latino)
            card.clicked.connect(self._on_card_clicked)
            self.cards[model_id] = card
            self.cards_layout.addWidget(card)

    def _on_card_clicked(self, model_id: str):
        """Maneja el clic en una tarjeta."""
        # Desseleccionar anterior
        for card in self.cards.values():
            card.set_selected(False)

        # Seleccionar nueva
        if model_id in self.cards:
            self.cards[model_id].set_selected(True)

        self.character_selected.emit(model_id)
