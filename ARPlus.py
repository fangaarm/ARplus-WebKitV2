import copy
import json
import hashlib
import html
import math
import os
import re
import shutil
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
import unicodedata
import zipfile
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path, PurePosixPath
from typing import Dict, Tuple

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
from PySide6.QtCore import QBuffer, QIODevice, QObject, QPointF, Qt, Signal, QTimer
from PySide6.QtGui import QBitmap, QColor, QFontMetrics, QIcon, QKeySequence, QPainter, QPainterPath, QPen, QPixmap, QRegion, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QFormLayout,
    QGridLayout,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QProgressBar,
    QScrollArea,
    QSlider,
    QSpinBox,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

PROGRAM_ROOT = Path(__file__).resolve().parent
ASSET_DIR = PROGRAM_ROOT / "asset"
ASSET_GUIDES_DIR = ASSET_DIR / "gabarits"
ASSET_LOGO_DIR = ASSET_DIR / "logo"
ASSET_TOP_DIR = ASSET_DIR / "TOP"
ASSET_TYPO_DIR = ASSET_DIR / "Typographie"

CHARACTER_LAYERS = ["character", "character2", "character3", "character4"]
EXTRA_CHARACTER_LAYERS = CHARACTER_LAYERS[1:]
RENDER_LAYER_ORDER = ["background", *CHARACTER_LAYERS, "gradient", "logo"]
CONTROL_LAYER_ORDER = [*CHARACTER_LAYERS, "background", "logo"]
LAYER_ORDER = ["background", *CHARACTER_LAYERS, "gradient", "logo", "fx"]

GUIDE_COLOR_MAP = {
    "background": (254, 67, 218),
    "character": (248, 255, 51),
    "logo": (62, 195, 52),
}
GUIDE_COLOR_TOLERANCE = 40
GUIDE_OPACITY_DEFAULT = 0.25
DAFONT_BASE_URL = "https://www.dafont.com"
DAFONT_FR_BASE_URL = f"{DAFONT_BASE_URL}/fr"
DAFONT_THEMES_URL = f"{DAFONT_FR_BASE_URL}/themes.php"
DAFONT_RESULTS_PER_PAGE = 25
DAFONT_SITE_PAGE_SCAN_LIMIT = 24
DAFONT_THEME_GROUPS = [
    ("Fantaisie", [
        "Cartoon",
        "BD, Comic",
        "Groovy",
        "Old School",
        "Spirales",
        "Western",
        "Usé",
        "Destructuré",
        "Destroy",
        "Horreur",
        "Feu, Glace",
        "Déco",
        "Typewriter",
        "Stencil, Armée",
        "Rétro",
        "Lettrines",
        "Grille",
        "Divers",
    ]),
    ("Etranger", [
        "Chinois, Jap.",
        "Arabe",
        "Mexicain",
        "Romain, Grec",
        "Russe",
        "Divers",
    ]),
    ("Techno", [
        "Carré",
        "LCD",
        "Science-fiction",
        "Divers",
    ]),
    ("Bitmap", [
        "Pixel, Bitmap",
    ]),
    ("Gothique", [
        "Médiéval",
        "Moderne",
        "Celtique",
        "Lettrines",
        "Divers",
    ]),
    ("Basique", [
        "Sans serif",
        "Serif",
        "Largeur fixe",
        "Divers",
    ]),
    ("Script", [
        "Calligraphie",
        "Scolaire",
        "Manuscrit",
        "Brush",
        "Trash",
        "Graffiti",
        "Old School",
        "Divers",
    ]),
    ("Symboles", [
        "Alien",
        "Animaux",
        "Asiatique",
        "Ancien",
        "Runes, Elfique",
        "Ésotérique",
        "Fantastique",
        "Horreur",
        "Jeux",
        "Formes",
        "Codes barres",
        "Nature",
        "Sport",
        "Têtes",
        "Enfants",
        "TV, Cinéma",
        "Logos",
        "Sexy",
        "Armée",
        "Musique",
        "Divers",
    ]),
    ("Fêtes", [
        "St Valentin",
        "Pâques",
        "Halloween",
        "Noël",
        "Divers",
    ]),
]
LOCAL_LOGO_FONT_LIBRARY = [
    {"name": "Coolvetica", "style": "moderne", "files": ["Coolvetica Rg.otf"]},
    {"name": "Ruby Ring", "style": "serif chic", "files": ["RubyRingDemoRegular.ttf"]},
    {"name": "Pixel Operator Mono", "style": "technique", "files": ["PixelOperatorMono.ttf"]},
    {"name": "Tempting", "style": "calligraphique", "files": ["Tempting - PERSONAL USE ONLY.otf"]},
    {"name": "Welcome Darling", "style": "manuscrite", "files": ["Welcome Darling.otf"]},
    {"name": "Draw Sketch", "style": "brush", "files": ["drawersketches.ttf"]},
    {"name": "Arabilla Signature", "style": "signature", "files": ["ArabillaSignature-Regular.ttf"]},
    {"name": "Lacheyard Script", "style": "retro script", "files": ["LacheyardScript_PERSONAL_USE_ONLY.otf"]},
    {"name": "Swinston Sans", "style": "techno", "files": ["SwinstonSansDemo-Regular.ttf"]},
    {"name": "Patriotics", "style": "sci-fi", "files": ["PatrioticsDemoRegular.ttf"]},
    {"name": "Kingsguard Calligraphy", "style": "medieval", "files": ["KingsguardCalligraphy_PERSONAL_USE_ONLY.otf"]},
    {"name": "Naughty Monster", "style": "cartoon", "files": ["NaughtyMonster.ttf", "NaughtyMonster.otf"]},
    {"name": "Porky's", "style": "western", "files": ["PORKYS_.TTF"]},
]
POSTER_GUIDE_FILES = {
    "1": [
        "gabarit-poster-1600x2400-1.jpg",
        "visuel-Poster-1600x2400-gabarit-1.jpg",
        "visuel-Poster-1600x2400-gabarit.jpg",
    ],
    "2": [
        "gabarit-poster-1600x2400-2.jpg",
        "visuel-Poster-1600x2400-gabarit-2.jpg",
    ],
}
POSTER_TEXTBOX_BASE = {
    "x": 0,
    "y": 36,
    "height": 118,
    "min_width": 120,
    "padding_left": 28,
    "radius": 12,
    "font_size": 72,
    "fill_color": "#0B5FA6",
    "text_color": "#F2F3EE",
}
GUIDE_FILE_PATTERNS = {
    "fullscreen": [
        "gabarit-fullscreen-3480x876.jpg",
        "FullScreen+Logo-APPTV-3480x876-gabarit.jpg",
        "FullScreen+Logo-3480x876-gabarit.jpg",
    ],
    "hero": [
        "gabarit-hero-banner-2240x672.jpg",
        "Hero-Banner-2240x672-gabarit.jpg",
    ],
    "background": [
        "gabarit-background-3840x2160.jpg",
        "visuel-Background-3840x2160-gabarit.jpg",
    ],
    "background_no_logo": [
        "gabarit-background-no-logo-3840x2160.jpg",
        "visuel-Background-no-logo-3840x2160-gabarit.jpg",
    ],
}
TOP_CANVAS_SIZE = (1600, 2400)
TOP_VIGNETTE_X = 680
TOP_VIGNETTE_Y = 570
TOP_VIGNETTE_W = 869
TOP_VIGNETTE_H = 1346
TOP_VIGNETTE_RADIUS = 120
TOP_PRESET_IDS = [f"top_{index}" for index in range(1, 6)]
TOP_EXPORT_IDS = list(TOP_PRESET_IDS)
TOP_TEXTBOX_GUIDE_FILES = {
    "1": "gabarit-poster-1600x2400-1-textbox.jpg",
    "2": "gabarit-poster-1600x2400-2-textbox.jpg",
}
TOP_DEFAULT_CONFIG = {
    "offset_x": 0,
    "offset_y": 0,
    "zoom": 100,
    "stretch_x": 100,
    "stretch_y": 100,
}

PRESETS = {
    "poster": {"label": "Poster", "size": (1600, 2400), "filename": "Poster_1600x2400"},
    "top_1": {"label": "TOP 1", "size": TOP_CANVAS_SIZE, "filename": "TOP_1_1600x2400", "top_number": 1},
    "top_2": {"label": "TOP 2", "size": TOP_CANVAS_SIZE, "filename": "TOP_2_1600x2400", "top_number": 2},
    "top_3": {"label": "TOP 3", "size": TOP_CANVAS_SIZE, "filename": "TOP_3_1600x2400", "top_number": 3},
    "top_4": {"label": "TOP 4", "size": TOP_CANVAS_SIZE, "filename": "TOP_4_1600x2400", "top_number": 4},
    "top_5": {"label": "TOP 5", "size": TOP_CANVAS_SIZE, "filename": "TOP_5_1600x2400", "top_number": 5},
    "fullscreen": {
        "label": "FullScreen+Logo",
        "size": (3480, 876),
        "filename": "FullScreen_3480x876",
    },
    "hero": {"label": "Hero Banner", "size": (2240, 672), "filename": "Hero_2240x672"},
    "logo": {"label": "Logo", "size": (800, 300), "filename": "Logo_800x300", "png": True},
    "background": {
        "label": "Background",
        "size": (3840, 2160),
        "filename": "Background_3840x2160",
    },
    "background_no_logo": {
        "label": "Background (no logo)",
        "size": (3840, 2160),
        "filename": "Background-no-logo_3840x2160",
        "skip_logo": True,
    },
}

EXPORT_TARGETS = {
    "poster": {
        "label": "Poster",
        "source_preset": "poster",
        "size": PRESETS["poster"]["size"],
        "file_stub": "poster-1600x2400",
        "metadata_key": "poster",
    },
    "poster_no_logo": {
        "label": "Poster (sans logo)",
        "source_preset": "poster",
        "size": PRESETS["poster"]["size"],
        "file_stub": "poster-nologo-1600x2400",
        "metadata_key": "poster-nologo",
        "skip_logo": True,
    },
    "top_1": {
        "label": "TOP 1",
        "source_preset": "top_1",
        "size": PRESETS["top_1"]["size"],
        "file_stub": "top-1-1600x2400",
        "metadata_key": "top-1",
    },
    "top_2": {
        "label": "TOP 2",
        "source_preset": "top_2",
        "size": PRESETS["top_2"]["size"],
        "file_stub": "top-2-1600x2400",
        "metadata_key": "top-2",
    },
    "top_3": {
        "label": "TOP 3",
        "source_preset": "top_3",
        "size": PRESETS["top_3"]["size"],
        "file_stub": "top-3-1600x2400",
        "metadata_key": "top-3",
    },
    "top_4": {
        "label": "TOP 4",
        "source_preset": "top_4",
        "size": PRESETS["top_4"]["size"],
        "file_stub": "top-4-1600x2400",
        "metadata_key": "top-4",
    },
    "top_5": {
        "label": "TOP 5",
        "source_preset": "top_5",
        "size": PRESETS["top_5"]["size"],
        "file_stub": "top-5-1600x2400",
        "metadata_key": "top-5",
    },
    "fullscreen": {
        "label": "Full Screen",
        "source_preset": "fullscreen",
        "size": PRESETS["fullscreen"]["size"],
        "file_stub": "full-screen-3480x876",
        "metadata_key": "full-screen",
    },
    "hero": {
        "label": "Hero Banner",
        "source_preset": "hero",
        "size": PRESETS["hero"]["size"],
        "file_stub": "hero-banner-2240x672",
        "metadata_key": "hero-banner",
    },
    "banner": {
        "label": "Banner",
        "source_preset": "hero",
        "size": (3840, 1152),
        "file_stub": "banner-3840x1152",
        "metadata_key": "banner",
    },
    "logo": {
        "label": "Logo",
        "source_preset": "logo",
        "size": PRESETS["logo"]["size"],
        "file_stub": "logo-800x300",
        "metadata_key": "logo",
        "png": True,
    },
    "background": {
        "label": "Background",
        "source_preset": "background",
        "size": PRESETS["background"]["size"],
        "file_stub": "background-3840x2160",
        "metadata_key": "background",
    },
    "background_no_logo": {
        "label": "Background (sans logo)",
        "source_preset": "background_no_logo",
        "size": PRESETS["background_no_logo"]["size"],
        "file_stub": "background-no-logo-3840x2160",
        "metadata_key": "background-no-logo",
        "skip_logo": True,
    },
}

TRANSPARENCY_VALIDATE_EXPORTS = [
    export_id for export_id in EXPORT_TARGETS if export_id != "logo"
]


@dataclass
class LayerAsset:
    path: str = ""
    pixmap: QPixmap | None = None
    pil: Image.Image | None = None


@dataclass
class DaFontTheme:
    name: str
    url: str


@dataclass
class DaFontFontEntry:
    name: str
    page_url: str
    preview_url: str = ""
    download_url: str = ""
    local_font_path: str = ""
    license_label: str = ""
    theme_group: str = ""
    theme_name: str = ""
    font_file_name: str = ""
    author_note: str = ""


@dataclass
class LocalFontLibraryEntry:
    name: str
    style: str
    file_path: str


class SignalEmitter(QObject):
    moved = Signal(str, float, float)
    clicked = Signal(str)
    pressed = Signal(str)


class DaFontHealthEmitter(QObject):
    completed = Signal(object)


class LocalFontPickerDialog(QDialog):
    def __init__(self, owner, parent=None):
        super().__init__(parent or owner)
        self.owner = owner
        self.font_entries: list[LocalFontLibraryEntry] = []
        self.filtered_font_entries: list[LocalFontLibraryEntry] = []
        self.current_entry: LocalFontLibraryEntry | None = None

        self.setWindowTitle("Choisir une typographie")
        self.resize(980, 620)

        root_layout = QVBoxLayout(self)

        header_row = QWidget()
        header_layout = QHBoxLayout(header_row)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        header_layout.addWidget(QLabel("Bibliotheque"))
        self.source_value_label = QLabel(str(owner.typo_dir))
        self.source_value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.source_value_label.setWordWrap(True)
        header_layout.addWidget(self.source_value_label, 1)
        self.refresh_btn = QPushButton("Actualiser")
        header_layout.addWidget(self.refresh_btn)
        root_layout.addWidget(header_row)

        search_row = QWidget()
        search_layout = QHBoxLayout(search_row)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(8)
        search_layout.addWidget(QLabel("Recherche"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Nom, style ou fichier")
        search_layout.addWidget(self.search_input, 1)
        root_layout.addWidget(search_row)

        body_row = QWidget()
        body_layout = QHBoxLayout(body_row)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(12)

        self.font_list = QListWidget()
        self.font_list.setMinimumWidth(340)
        body_layout.addWidget(self.font_list, 1)

        details_panel = QWidget()
        details_layout = QVBoxLayout(details_panel)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(10)

        self.preview_label = QLabel("Selectionne une typographie")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumHeight(220)
        self.preview_label.setWordWrap(True)
        self.preview_label.setStyleSheet(
            "border: 1px solid #4A4A4A; background-color: #1F1F24; color: #D0D0D0;"
        )
        details_layout.addWidget(self.preview_label)

        self.selection_title = QLabel("Aucune typographie selectionnee")
        self.selection_title.setWordWrap(True)
        self.selection_title.setStyleSheet("font-size: 15px; font-weight: 600;")
        details_layout.addWidget(self.selection_title)

        self.selection_status = QLabel("")
        self.selection_status.setWordWrap(True)
        details_layout.addWidget(self.selection_status)

        self.selection_info = QLabel("")
        self.selection_info.setWordWrap(True)
        details_layout.addWidget(self.selection_info)
        details_layout.addStretch(1)

        actions_row = QWidget()
        actions_layout = QHBoxLayout(actions_row)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(8)
        self.delete_btn = QPushButton("Supprimer cette typo")
        self.delete_btn.setEnabled(False)
        actions_layout.addWidget(self.delete_btn)
        self.use_btn = QPushButton("Utiliser cette typo")
        self.use_btn.setEnabled(False)
        actions_layout.addWidget(self.use_btn)
        actions_layout.addStretch(1)
        self.close_btn = QPushButton("Fermer")
        actions_layout.addWidget(self.close_btn)
        details_layout.addWidget(actions_row)

        body_layout.addWidget(details_panel, 1)
        root_layout.addWidget(body_row, 1)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        root_layout.addWidget(self.status_label)

        self.refresh_btn.clicked.connect(self._load_fonts)
        self.search_input.textChanged.connect(self._apply_filter)
        self.font_list.currentItemChanged.connect(self._on_font_selection_changed)
        self.font_list.itemDoubleClicked.connect(lambda _item: self._use_selected())
        self.delete_btn.clicked.connect(self._delete_selected)
        self.use_btn.clicked.connect(self._use_selected)
        self.close_btn.clicked.connect(self.reject)

        self._load_fonts()

    def _set_busy(self, busy: bool, status: str = ""):
        widgets = [
            self.refresh_btn,
            self.font_list,
            self.use_btn,
        ]
        for widget in widgets:
            widget.setEnabled(not busy)
        if busy:
            self.setCursor(Qt.CursorShape.WaitCursor)
        else:
            self.unsetCursor()
        self.status_label.setText(status)
        QApplication.processEvents()

    def _load_fonts(self):
        self._set_busy(True, "Chargement des typographies locales...")
        self.font_entries = self.owner._local_logo_font_entries()
        self._apply_filter()
        self._set_busy(False, f"{len(self.filtered_font_entries)} typographies disponibles.")

    def _apply_filter(self):
        search_value = self.owner._normalize_dafont_label(self.search_input.text())
        if search_value:
            self.filtered_font_entries = [
                entry
                for entry in self.font_entries
                if search_value in self.owner._normalize_dafont_label(
                    f"{entry.name} {entry.style} {Path(entry.file_path).name}"
                )
            ]
        else:
            self.filtered_font_entries = list(self.font_entries)

        self.font_list.blockSignals(True)
        self.font_list.clear()
        for entry in self.filtered_font_entries:
            item = QListWidgetItem(f"{entry.name} — {entry.style}")
            item.setData(Qt.ItemDataRole.UserRole, entry.file_path)
            item.setToolTip(entry.file_path)
            self.font_list.addItem(item)
        self.font_list.blockSignals(False)

        self.status_label.setText(f"{len(self.filtered_font_entries)} typographies affichees.")

        if not self.filtered_font_entries:
            self._set_current_entry(None)
            return
        self._restore_current_selection()

    def _restore_current_selection(self):
        wanted_path = self.owner.logo_text_font_file.strip()
        wanted_name = self.owner.logo_text_font_name.strip()
        for row in range(self.font_list.count()):
            item = self.font_list.item(row)
            item_path = str(item.data(Qt.ItemDataRole.UserRole) or "")
            if wanted_path and item_path == wanted_path:
                    self.font_list.setCurrentRow(row)
                    return
        for row, entry in enumerate(self.filtered_font_entries):
            if wanted_name and entry.name == wanted_name:
                self.font_list.setCurrentRow(row)
                return
        self.font_list.setCurrentRow(0)

    def _on_font_selection_changed(self, current, _previous):
        if current is None:
            self._set_current_entry(None)
            return
        file_path = str(current.data(Qt.ItemDataRole.UserRole) or "")
        selected = next((entry for entry in self.font_entries if entry.file_path == file_path), None)
        self._set_current_entry(selected)

    def _set_current_entry(self, entry: LocalFontLibraryEntry | None):
        self.current_entry = entry
        if entry is None:
            self.selection_title.setText("Aucune typographie selectionnee")
            self.selection_status.setText("")
            self.selection_info.setText("")
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText("Selectionne une typographie")
            self.delete_btn.setEnabled(False)
            self.use_btn.setEnabled(False)
            return

        self.selection_title.setText(entry.name)
        file_path = Path(entry.file_path)
        self.selection_status.setText(entry.style.capitalize())
        self.selection_info.setText(f"Fichier: {file_path.name}")

        pixmap = self.owner._local_font_preview_pixmap(entry)
        if pixmap.isNull():
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText(entry.name)
        else:
            scaled = pixmap.scaled(
                430,
                240,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.preview_label.setText("")
            self.preview_label.setPixmap(scaled)
        self.delete_btn.setEnabled(True)
        self.use_btn.setEnabled(True)

    def _use_selected(self):
        if self.current_entry is None:
            return
        self.owner._apply_logo_font_selection(self.current_entry)
        self.accept()

    def _delete_selected(self):
        if self.current_entry is None:
            return
        file_name = Path(self.current_entry.file_path).name
        answer = QMessageBox.question(
            self,
            "Supprimer la typo",
            f"Supprimer '{self.current_entry.name}' ({file_name}) de asset/Typographie ?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.owner._delete_local_logo_font_entry(self.current_entry)
        except Exception as exc:
            QMessageBox.warning(self, "Typographie", str(exc))
            return
        self.status_label.setText("Typographie supprimee.")
        self._load_fonts()


class DaFontPickerDialog(QDialog):
    def __init__(self, owner, parent=None):
        super().__init__(parent or owner)
        self.owner = owner
        self.theme_groups: list[tuple[str, list[DaFontTheme]]] = []
        self.font_entries: list[DaFontFontEntry] = []
        self.filtered_font_entries: list[DaFontFontEntry] = []
        self.current_entry: DaFontFontEntry | None = None
        self.health_thread: threading.Thread | None = None
        self.health_emitter = DaFontHealthEmitter()

        self.setWindowTitle("Ajouter une typo")
        self.resize(1020, 660)
        self.health_emitter.completed.connect(self._on_health_check_completed)

        root_layout = QVBoxLayout(self)

        header_row = QWidget()
        header_layout = QHBoxLayout(header_row)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        header_layout.addWidget(QLabel("Source"))
        self.source_value_label = QLabel("DaFont FR")
        self.source_value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        header_layout.addWidget(self.source_value_label)
        header_layout.addStretch(1)
        root_layout.addWidget(header_row)

        self.health_label = QLabel(self.owner._dafont_health_summary_text())
        self.health_label.setWordWrap(True)
        root_layout.addWidget(self.health_label)

        filters_row = QWidget()
        filters_layout = QHBoxLayout(filters_row)
        filters_layout.setContentsMargins(0, 0, 0, 0)
        filters_layout.setSpacing(8)
        filters_layout.addWidget(QLabel("Categorie"))
        self.group_combo = QComboBox()
        filters_layout.addWidget(self.group_combo, 2)
        filters_layout.addWidget(QLabel("Sous-theme"))
        self.theme_combo = QComboBox()
        filters_layout.addWidget(self.theme_combo, 3)
        filters_layout.addWidget(QLabel("Page"))
        self.page_spin = QSpinBox()
        self.page_spin.setRange(1, 999)
        self.page_spin.setValue(max(1, int(owner.dafont_last_theme_page or 1)))
        filters_layout.addWidget(self.page_spin)
        self.refresh_btn = QPushButton("Actualiser")
        filters_layout.addWidget(self.refresh_btn)
        root_layout.addWidget(filters_row)

        body_row = QWidget()
        body_layout = QHBoxLayout(body_row)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(12)

        self.font_list = QListWidget()
        self.font_list.setMinimumWidth(360)
        body_layout.addWidget(self.font_list, 1)

        details_panel = QWidget()
        details_layout = QVBoxLayout(details_panel)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(10)

        self.preview_label = QLabel("Selectionne une typographie")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumHeight(220)
        self.preview_label.setWordWrap(True)
        self.preview_label.setStyleSheet(
            "border: 1px solid #4A4A4A; background-color: #1F1F24; color: #D0D0D0;"
        )
        details_layout.addWidget(self.preview_label)

        self.selection_title = QLabel("Aucune typographie selectionnee")
        self.selection_title.setWordWrap(True)
        self.selection_title.setStyleSheet("font-size: 15px; font-weight: 600;")
        details_layout.addWidget(self.selection_title)

        self.selection_status = QLabel("")
        self.selection_status.setWordWrap(True)
        details_layout.addWidget(self.selection_status)

        self.selection_info = QLabel("")
        self.selection_info.setWordWrap(True)
        details_layout.addWidget(self.selection_info)
        details_layout.addStretch(1)

        actions_row = QWidget()
        actions_layout = QHBoxLayout(actions_row)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(8)
        self.add_btn = QPushButton("Ajouter et utiliser")
        self.add_btn.setEnabled(False)
        actions_layout.addWidget(self.add_btn)
        actions_layout.addStretch(1)
        self.close_btn = QPushButton("Fermer")
        actions_layout.addWidget(self.close_btn)
        details_layout.addWidget(actions_row)

        body_layout.addWidget(details_panel, 1)
        root_layout.addWidget(body_row, 1)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        root_layout.addWidget(self.status_label)

        self.refresh_btn.clicked.connect(self._refresh_remote_data)
        self.group_combo.currentIndexChanged.connect(self._on_group_changed)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        self.page_spin.valueChanged.connect(self._on_page_changed)
        self.font_list.currentItemChanged.connect(self._on_font_selection_changed)
        self.font_list.itemDoubleClicked.connect(lambda _item: self._download_or_use_selected())
        self.add_btn.clicked.connect(self._download_or_use_selected)
        self.close_btn.clicked.connect(self.reject)

        self._load_theme_catalog()
        QTimer.singleShot(120, self._start_background_health_check)

    def _set_busy(self, busy: bool, status: str = ""):
        widgets = [
            self.refresh_btn,
            self.group_combo,
            self.theme_combo,
            self.page_spin,
            self.font_list,
            self.add_btn,
        ]
        for widget in widgets:
            widget.setEnabled(not busy)
        if busy:
            self.setCursor(Qt.CursorShape.WaitCursor)
        else:
            self.unsetCursor()
        self.status_label.setText(status)
        QApplication.processEvents()

    def _refresh_remote_data(self):
        self.owner.dafont_themes_cache = None
        self.owner.dafont_theme_site_fonts_cache.clear()
        self.owner.dafont_theme_fonts_cache.clear()
        self.owner.dafont_font_details_cache.clear()
        self.owner.dafont_font_compatibility_cache.clear()
        self._load_theme_catalog()
        self._start_background_health_check(force=True)

    def _start_background_health_check(self, force: bool = False):
        if self.health_thread is not None and self.health_thread.is_alive():
            return
        cached_status = self.owner.dafont_health_status if isinstance(self.owner.dafont_health_status, dict) else {}
        if force or not cached_status:
            self.health_label.setText("Verification DaFont: en cours...")

        def worker():
            payload = self.owner._perform_dafont_health_check()
            self.health_emitter.completed.emit(payload)

        self.health_thread = threading.Thread(target=worker, daemon=True)
        self.health_thread.start()

    def _on_health_check_completed(self, payload):
        self.health_label.setText(self.owner._dafont_health_summary_text(payload))

    def _load_theme_catalog(self):
        self._set_busy(True, "Chargement des themes DaFont...")
        try:
            themes = self.owner._dafont_fetch_themes()
            self.theme_groups = self.owner._group_dafont_themes(themes)
        except Exception as exc:
            self.theme_groups = []
            self._set_busy(False, f"Impossible de charger DaFont: {exc}")
            return

        preferred_url = self.owner.dafont_last_theme_url.strip()
        preferred_group_index = 0
        for group_index, (_group_name, group_themes) in enumerate(self.theme_groups):
            if any(theme.url == preferred_url for theme in group_themes):
                preferred_group_index = group_index
                break

        self.group_combo.blockSignals(True)
        self.group_combo.clear()
        for group_name, _group_themes in self.theme_groups:
            self.group_combo.addItem(group_name)
        self.group_combo.setCurrentIndex(preferred_group_index)
        self.group_combo.blockSignals(False)

        self.page_spin.blockSignals(True)
        self.page_spin.setValue(max(1, int(self.owner.dafont_last_theme_page or 1)))
        self.page_spin.blockSignals(False)

        self._populate_theme_combo(preferred_url)
        self._set_busy(False, "Themes DaFont charges.")

    def _populate_theme_combo(self, preferred_url: str = ""):
        if not self.theme_groups:
            self.theme_combo.clear()
            self._set_current_entry(None)
            return
        group_index = max(0, self.group_combo.currentIndex())
        if group_index >= len(self.theme_groups):
            group_index = 0
        _group_name, themes = self.theme_groups[group_index]
        themes = sorted(themes, key=lambda theme: self.owner._normalize_dafont_label(theme.name))
        self.theme_combo.blockSignals(True)
        self.theme_combo.clear()
        target_index = 0
        for theme_index, theme in enumerate(themes):
            self.theme_combo.addItem(theme.name, theme.url)
            if preferred_url and theme.url == preferred_url:
                target_index = theme_index
        if themes:
            self.theme_combo.setCurrentIndex(target_index)
        self.theme_combo.blockSignals(False)
        self._load_fonts()

    def _selected_theme(self) -> DaFontTheme | None:
        group_index = self.group_combo.currentIndex()
        theme_index = self.theme_combo.currentIndex()
        if group_index < 0 or theme_index < 0 or group_index >= len(self.theme_groups):
            return None
        _group_name, themes = self.theme_groups[group_index]
        if theme_index >= len(themes):
            return None
        return themes[theme_index]

    def _load_fonts(self):
        theme = self._selected_theme()
        if theme is None:
            self.font_entries = []
            self.font_list.clear()
            self._set_current_entry(None)
            return
        group_name = self.group_combo.currentText().strip()
        theme_name = self.theme_combo.currentText().strip()
        page_number = self.page_spin.value()
        self.owner.dafont_last_theme_url = theme.url
        self.owner.dafont_last_theme_page = page_number

        self._set_busy(True, f"Chargement DaFont: {group_name} / {theme_name} (page {page_number})...")
        try:
            self.font_entries = self.owner._dafont_fetch_theme_fonts(
                theme.url,
                page_number,
                theme_group=group_name,
                theme_name=theme_name,
            )
            self.font_entries = sorted(
                self.font_entries,
                key=lambda entry: self.owner._normalize_dafont_label(entry.name),
            )
        except Exception as exc:
            self.font_entries = []
            self.font_list.clear()
            self._set_current_entry(None)
            self._set_busy(False, f"Impossible de charger les typos: {exc}")
            return

        self._apply_filter()
        self._set_busy(False, f"{len(self.filtered_font_entries)} typos DaFont compatibles.")

        if not self.filtered_font_entries:
            self._set_current_entry(None)
            return
        self._restore_current_selection()

    def _apply_filter(self):
        self.filtered_font_entries = list(self.font_entries)

        self.font_list.blockSignals(True)
        self.font_list.clear()
        for entry in self.filtered_font_entries:
            item = QListWidgetItem(entry.name)
            item.setData(Qt.ItemDataRole.UserRole, entry.page_url)
            item.setToolTip(entry.page_url)
            self.font_list.addItem(item)
        self.font_list.blockSignals(False)
        self.status_label.setText(f"{len(self.filtered_font_entries)} typos DaFont affichees.")

    def _restore_current_selection(self):
        wanted_page_url = self.owner.logo_text_font_page_url.strip()
        for row, entry in enumerate(self.filtered_font_entries):
            if wanted_page_url and entry.page_url == wanted_page_url:
                self.font_list.setCurrentRow(row)
                return
        self.font_list.setCurrentRow(0)

    def _on_group_changed(self):
        self._populate_theme_combo("")

    def _on_theme_changed(self):
        self._load_fonts()

    def _on_page_changed(self, value: int):
        self.owner.dafont_last_theme_page = max(1, int(value))
        self._load_fonts()

    def _on_font_selection_changed(self, current, _previous):
        if current is None:
            self._set_current_entry(None)
            return
        page_url = str(current.data(Qt.ItemDataRole.UserRole) or "")
        selected = next((entry for entry in self.font_entries if entry.page_url == page_url), None)
        self._set_current_entry(selected)

    def _set_current_entry(self, entry: DaFontFontEntry | None):
        self.current_entry = entry
        if entry is None:
            self.selection_title.setText("Aucune typographie selectionnee")
            self.selection_status.setText("")
            self.selection_info.setText("")
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText("Selectionne une typographie")
            self.add_btn.setEnabled(False)
            return

        self.selection_title.setText(entry.name)
        status_parts = []
        if entry.local_font_path:
            status_parts.append("Deja ajoutee dans asset/Typographie")
            self.add_btn.setText("Utiliser cette typo")
        else:
            self.add_btn.setText("Ajouter et utiliser")
        self.selection_status.setText(" | ".join(status_parts))

        info_parts = []
        if entry.theme_group or entry.theme_name:
            info_parts.append(f"Theme: {entry.theme_group} / {entry.theme_name}".strip(" /"))
        info_parts.append(f"Page: {self.page_spin.value()}")
        self.selection_info.setText("\n".join(info_parts))

        pixmap = self.owner._dafont_fetch_preview_pixmap(entry.preview_url, entry.page_url)
        if pixmap.isNull():
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText(entry.name)
        else:
            scaled = pixmap.scaled(
                430,
                240,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.preview_label.setText("")
            self.preview_label.setPixmap(scaled)
        self.add_btn.setEnabled(True)

    def _download_or_use_selected(self):
        if self.current_entry is None:
            return
        if self.current_entry.local_font_path:
            self.owner._apply_logo_font_selection(self.current_entry)
            self.accept()
            return

        self._set_busy(True, f"Ajout de {self.current_entry.name} depuis DaFont...")
        try:
            resolved_entry = self.owner._dafont_resolve_compatible_entry(self.current_entry)
            if resolved_entry is None:
                self._set_busy(False, "")
                self._remove_current_incompatible_entry()
                return
            installed = self.owner._download_and_install_dafont_font(resolved_entry)
        except Exception as exc:
            self._set_busy(False, "")
            lowered = str(exc).lower()
            if any(token in lowered for token in ["ignoree", "usage personnel", "non compatible", "euro"]):
                self._remove_current_incompatible_entry()
                return
            QMessageBox.warning(self, "DaFont", str(exc))
            return
        self._set_busy(False, f"Typographie ajoutee: {installed.name}")
        self.owner._apply_logo_font_selection(installed)
        self.accept()

    def _remove_current_incompatible_entry(self):
        if self.current_entry is None:
            return
        current_page_url = self.current_entry.page_url
        self.owner.dafont_font_compatibility_cache[current_page_url] = False
        self.font_entries = [entry for entry in self.font_entries if entry.page_url != current_page_url]
        self.status_label.setText("Typographie retiree de la liste car non compatible.")
        self._apply_filter()
        if self.filtered_font_entries:
            self.font_list.setCurrentRow(0)
        else:
            self._set_current_entry(None)


class LayerGraphicsItem(QGraphicsPixmapItem):
    def __init__(self, layer_id: str):
        super().__init__()
        self.layer_id = layer_id
        self.signal_emitter = SignalEmitter()
        self.moved = self.signal_emitter.moved
        self.clicked = self.signal_emitter.clicked
        self.pressed = self.signal_emitter.pressed
        self._alpha_hit_threshold = 8
        self._shape_path = QPainterPath()
        self._alpha_image = None
        self.setFlag(QGraphicsPixmapItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsPixmapItem.GraphicsItemFlag.ItemSendsScenePositionChanges, True)
        self.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)

    def setPixmap(self, pixmap):
        super().setPixmap(pixmap)
        self._rebuild_hit_shape()

    def _rebuild_hit_shape(self):
        self._shape_path = QPainterPath()
        self._alpha_image = None
        pixmap = self.pixmap()
        if pixmap.isNull():
            return

        image = pixmap.toImage()
        self._alpha_image = image
        try:
            alpha_mask = image.createAlphaMask()
            if not alpha_mask.isNull():
                self._shape_path.addRegion(QRegion(QBitmap.fromImage(alpha_mask)))
        except Exception:
            self._shape_path = QPainterPath()

        if self._shape_path.isEmpty():
            self._shape_path.addRect(0, 0, pixmap.width(), pixmap.height())

    def shape(self):
        path = QPainterPath(self._shape_path)
        path.translate(self.offset())
        return path

    def contains(self, point):
        pixmap = self.pixmap()
        if pixmap.isNull():
            return False

        local_x = point.x() - self.offset().x()
        local_y = point.y() - self.offset().y()
        if local_x < 0 or local_y < 0:
            return False
        if local_x >= pixmap.width() or local_y >= pixmap.height():
            return False

        if self._alpha_image is None:
            return True
        return self._alpha_image.pixelColor(int(local_x), int(local_y)).alpha() > self._alpha_hit_threshold

    def itemChange(self, change, value):
        if change == QGraphicsPixmapItem.GraphicsItemChange.ItemPositionHasChanged:
            pos = self.pos()
            self.signal_emitter.moved.emit(self.layer_id, pos.x(), pos.y())
        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        if not self.contains(event.pos()):
            event.ignore()
            return
        self.signal_emitter.pressed.emit(self.layer_id)
        self.signal_emitter.clicked.emit(self.layer_id)
        super().mousePressEvent(event)


class CanvasView(QGraphicsView):
    wheelScaled = Signal(float)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = 0.05 if event.angleDelta().y() > 0 else -0.05
            self.wheelScaled.emit(delta)
            event.accept()
            return
        super().wheelEvent(event)


class PresetPreviewLabel(QLabel):
    clicked = Signal(str)

    def __init__(self, preset_id: str, text: str = "", parent=None):
        super().__init__(text, parent)
        self.preset_id = preset_id
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.preset_id)
            event.accept()
            return
        super().mousePressEvent(event)


class ARPlusWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ARPlus")
        self.resize(1600, 900)

        self.assets: Dict[str, LayerAsset] = {layer: LayerAsset() for layer in LAYER_ORDER}
        self.logo_text_enabled = False
        self.logo_text = ""
        self.logo_text_pending = ""
        self.logo_text_size = 300
        self.logo_text_align = "center"
        self.logo_text_force_upper = True
        self.logo_text_line_spacing = 100
        self.logo_text_color = "#FFFFFF"
        self.logo_text_font_name = ""
        self.logo_text_font_page_url = ""
        self.logo_text_font_download_url = ""
        self.logo_text_font_file = ""
        self.logo_text_input_delay_ms = 220
        self.poster_textbox_enabled = True
        self.poster_textbox_text = "TEXTE BOX"
        self.logo_shadow_enabled = False
        self.logo_shadow_distance = 5
        self.logo_shadow_blur = 5
        self.logo_shadow_angle = 135
        self.logo_shadow_opacity = 60
        self.logo_shadow_color = "#000000"
        self.gradient_settings = {
            preset_id: self._default_gradient_config() for preset_id in PRESETS
        }
        self.top_settings = {
            preset_id: dict(TOP_DEFAULT_CONFIG) for preset_id in TOP_PRESET_IDS
        }
        self.top_sync_all = False
        self.guides_visible = True
        self.guides_opacity = GUIDE_OPACITY_DEFAULT
        self.poster_guide_variant = "1"
        self.upscale_warning_ratio = 1.75
        self.presets_preview_interval_ms = 2400
        self.presets_preview_worker_interval_ms = 12
        self.presets_preview_box_width = 300
        self.presets_preview_box_height = 170
        self.presets_preview_quality_scale = 0.65
        self.live_refresh_interval_ms = 70
        self.layer_move_preview_interval_ms = 180
        self.live_refresh_pending = False
        self.layer_move_refresh_pending = False
        self.current_preset = "poster"
        self.active_layer = "background"
        self.updating_ui = False
        self.program_root = PROGRAM_ROOT
        self.typo_dir = ASSET_TYPO_DIR
        self.data_dir = self.program_root / "data"
        self.preview_cache_dir = self.data_dir / "cache" / "dafont_preview"
        self.autosave_dir = self.program_root / "autosafe"
        self.ui_state_path = self.data_dir / "ui_state.json"
        self.dafont_health_path = self.data_dir / "dafont_health.json"
        self.recent_dirs = self._default_recent_dirs()
        self._load_ui_state()
        self.undo_stack: list[dict] = []
        self.undo_limit = 40
        self.undo_in_progress = False
        self.guide_pixmaps: Dict[str, QPixmap] = {}
        self.guide_regions: Dict[str, Dict[str, Tuple[float, float, float, float]]] = {}
        self.dafont_themes_cache: list[DaFontTheme] | None = None
        self.dafont_theme_site_fonts_cache: dict[str, list[DaFontFontEntry]] = {}
        self.dafont_theme_fonts_cache: dict[str, list[DaFontFontEntry]] = {}
        self.dafont_font_details_cache: dict[str, DaFontFontEntry] = {}
        self.dafont_font_compatibility_cache: dict[str, bool] = {}
        self.dafont_preview_cache: dict[str, QPixmap] = {}
        self.local_font_preview_cache: dict[str, QPixmap] = {}
        self.top_template_cache: dict[str, Image.Image] = {}
        self.dafont_last_theme_url = ""
        self.dafont_last_theme_page = 1
        self.dafont_health_status = self._load_dafont_health_status()
        self.preset_preview_dirty: set[str] = set(PRESETS.keys())
        self.preset_preview_queue: list[str] = []
        app_icon_path = self._app_icon_path()
        if app_icon_path.exists():
            app_icon = QIcon(str(app_icon_path))
            if not app_icon.isNull():
                self.setWindowIcon(app_icon)

        self.state = self._build_default_state()
        self.presets_preview_timer = QTimer(self)
        self.presets_preview_timer.setSingleShot(True)
        self.presets_preview_timer.timeout.connect(self._refresh_presets_preview_strip)
        self.presets_preview_worker_timer = QTimer(self)
        self.presets_preview_worker_timer.setSingleShot(True)
        self.presets_preview_worker_timer.timeout.connect(self._process_next_preset_preview)
        self.logo_text_input_timer = QTimer(self)
        self.logo_text_input_timer.setSingleShot(True)
        self.logo_text_input_timer.timeout.connect(self._flush_logo_text_input)
        self.live_refresh_timer = QTimer(self)
        self.live_refresh_timer.setSingleShot(True)
        self.live_refresh_timer.timeout.connect(self._flush_live_preview_refresh)
        self.layer_move_preview_timer = QTimer(self)
        self.layer_move_preview_timer.setSingleShot(True)
        self.layer_move_preview_timer.timeout.connect(self._flush_layer_move_preview_refresh)

        self.scene = QGraphicsScene(self)
        self.view = CanvasView(self)
        self.view.setScene(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self.view.setBackgroundBrush(QColor("#F3F1F3"))
        self.view.wheelScaled.connect(self._on_wheel_scaled)

        self.clip_item = QGraphicsRectItem()
        self.clip_item.setPen(QPen(Qt.PenStyle.NoPen))
        self.clip_item.setBrush(QColor("#FFDDEB"))
        self.clip_item.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemClipsChildrenToShape, True)
        self.clip_item.setZValue(-1)
        self.scene.addItem(self.clip_item)

        self.items: Dict[str, LayerGraphicsItem] = {}
        for layer in RENDER_LAYER_ORDER:
            item = LayerGraphicsItem(layer)
            if layer == "gradient":
                item.setFlag(QGraphicsPixmapItem.GraphicsItemFlag.ItemIsMovable, False)
            item.moved.connect(self._on_layer_moved)
            item.clicked.connect(self._on_layer_clicked)
            item.pressed.connect(self._on_layer_pressed)
            item.setParentItem(self.clip_item)
            self.items[layer] = item

        self.guide_item = QGraphicsPixmapItem()
        self.guide_item.setParentItem(self.clip_item)
        self.guide_item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.guide_item.setFlag(QGraphicsPixmapItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.guide_item.setOpacity(self.guides_opacity)
        self.guide_item.setZValue(5_000)
        self.guide_item.setVisible(False)

        self.poster_textbox_item = QGraphicsPixmapItem()
        self.poster_textbox_item.setParentItem(self.clip_item)
        self.poster_textbox_item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.poster_textbox_item.setFlag(QGraphicsPixmapItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.poster_textbox_item.setZValue(7_000)
        self.poster_textbox_item.setVisible(False)

        self.special_preset_item = QGraphicsPixmapItem()
        self.special_preset_item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.special_preset_item.setFlag(QGraphicsPixmapItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.special_preset_item.setZValue(8_000)
        self.special_preset_item.setVisible(False)
        self.scene.addItem(self.special_preset_item)

        self.frame_item = QGraphicsRectItem()
        frame_pen = QPen(Qt.PenStyle.NoPen)
        self.frame_item.setPen(frame_pen)
        self.frame_item.setBrush(Qt.BrushStyle.NoBrush)
        self.frame_item.setZValue(10_000)
        self.scene.addItem(self.frame_item)

        self.undo_shortcut = QShortcut(QKeySequence.StandardKey.Undo, self)
        self.undo_shortcut.activated.connect(self._on_undo_shortcut)

        self._build_ui()
        self._load_guides()
        self._set_scene_for_preset(self.current_preset)
        self._refresh_preview()

    def _build_default_layer(self):
        return {
            "visible": True,
            "opacity": 1.0,
            "fit_mode": "contain",
            "transform": {"x": 0.0, "y": 0.0, "scale": 1.0, "rotation": 0.0, "anchor": "center"},
        }

    def _default_gradient_config(self):
        return {
            "enabled": False,
            "mode": "single",
            "direction": "top",
            "color_a": "#000000",
            "color_b": "#FFFFFF",
            "distance": 40,
            "stretch": 100,
        }

    def _gradient_config(self, preset_id: str | None = None):
        if preset_id is None:
            preset_id = self.current_preset
        config = self.gradient_settings.get(preset_id)
        if not isinstance(config, dict):
            config = self._default_gradient_config()
            self.gradient_settings[preset_id] = config
        return config

    def _default_top_config(self):
        return dict(TOP_DEFAULT_CONFIG)

    def _top_config(self, preset_id: str | None = None):
        if preset_id is None:
            preset_id = self.current_preset
        config = self.top_settings.get(preset_id)
        if not isinstance(config, dict):
            config = self._default_top_config()
            self.top_settings[preset_id] = config
        return config

    def _is_top_preset(self, preset_id: str | None = None) -> bool:
        if preset_id is None:
            preset_id = self.current_preset
        return preset_id in TOP_PRESET_IDS

    def _asset_candidates(self, *relative_paths: str) -> list[Path]:
        return [ASSET_DIR / relative_path for relative_path in relative_paths if relative_path]

    def _first_existing_asset_path(self, *relative_paths: str) -> Path | None:
        for candidate in self._asset_candidates(*relative_paths):
            if candidate.exists():
                return candidate
        return None

    def _app_icon_path(self) -> Path:
        icon_path = self._first_existing_asset_path(
            "logo/arplus.ico",
            "logo/arplus.png",
            "icon.ico",
            "icon.png",
        )
        if icon_path is not None:
            return icon_path
        return ASSET_LOGO_DIR / "arplus.ico"

    def _top_template_path(self, preset_id: str) -> Path | None:
        top_number = PRESETS.get(preset_id, {}).get("top_number")
        if top_number is None:
            return None
        return self._first_existing_asset_path(
            f"TOP/top-{top_number}.png",
            f"{top_number}.png",
        )

    def _build_default_state(self):
        state = {}
        for preset_id, meta in PRESETS.items():
            width, height = meta["size"]
            state[preset_id] = {layer: self._build_default_layer() for layer in LAYER_ORDER}
            state[preset_id]["background"]["fit_mode"] = "crop"
            for layer_id in CHARACTER_LAYERS:
                state[preset_id][layer_id]["fit_mode"] = "contain"
                state[preset_id][layer_id]["transform"]["anchor"] = "bottom"
            state[preset_id]["gradient"]["fit_mode"] = "stretch"
            state[preset_id]["gradient"]["transform"]["x"] = width * 0.5
            state[preset_id]["gradient"]["transform"]["y"] = height * 0.5
            state[preset_id]["gradient"]["transform"]["scale"] = 1.0
            state[preset_id]["logo"]["fit_mode"] = "contain"
            state[preset_id]["logo"]["transform"]["x"] = width * 0.5
            state[preset_id]["logo"]["transform"]["y"] = height * 0.5
            state[preset_id]["logo"]["transform"]["scale"] = 1.0
        return state

    def _default_recent_dirs(self):
        export_dir = self.program_root / "exports"
        return {
            "import": str(self.program_root),
            "export": str(export_dir),
            "save_project": str(self.program_root),
            "load_project": str(self.program_root),
        }

    def _load_ui_state(self):
        if not self.ui_state_path.exists():
            return
        try:
            payload = json.loads(self.ui_state_path.read_text(encoding="utf-8"))
        except Exception:
            return
        if not isinstance(payload, dict):
            return
        raw_recent_dirs = payload.get("recent_dirs")
        if not isinstance(raw_recent_dirs, dict):
            return
        for key, fallback in self._default_recent_dirs().items():
            value = raw_recent_dirs.get(key)
            if isinstance(value, str) and value.strip():
                self.recent_dirs[key] = value.strip()
            else:
                self.recent_dirs[key] = fallback

    def _save_ui_state(self):
        payload = {
            "recent_dirs": self.recent_dirs,
        }
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self.ui_state_path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            return

    def _load_dafont_health_status(self):
        if not self.dafont_health_path.exists():
            return {}
        try:
            payload = json.loads(self.dafont_health_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return payload if isinstance(payload, dict) else {}

    def _save_dafont_health_status(self, payload: dict):
        if not isinstance(payload, dict):
            return
        self.dafont_health_status = dict(payload)
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self.dafont_health_path.write_text(
                json.dumps(self.dafont_health_status, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            return

    def _recent_dir(self, key: str) -> Path:
        fallback = Path(self._default_recent_dirs().get(key, str(self.program_root))).expanduser()
        raw_value = self.recent_dirs.get(key, str(fallback))
        path = Path(raw_value).expanduser()
        if path.exists():
            if path.is_dir():
                return path
            return path.parent
        if path.parent.exists():
            return path.parent
        return fallback

    def _remember_recent_dir(self, key: str, value: str | Path):
        path = Path(value).expanduser()
        if path.exists() and not path.is_dir():
            path = path.parent
        self.recent_dirs[key] = str(path)
        self._save_ui_state()

    def _logo_font_status_text(self) -> str:
        local_path = self._selected_logo_font_path()
        if local_path is not None:
            return f"{self.logo_text_font_name or local_path.stem} ({local_path.name})"
        if self.logo_text_font_name.strip():
            return f"{self.logo_text_font_name} (fichier introuvable, police par defaut)"
        return "Montserrat Bold (defaut du programme)"

    def _has_custom_logo_font(self) -> bool:
        return any(
            value.strip()
            for value in [
                self.logo_text_font_name,
                self.logo_text_font_page_url,
                self.logo_text_font_download_url,
                self.logo_text_font_file,
            ]
        )

    def _selected_logo_font_path(self) -> Path | None:
        if not self.logo_text_font_file.strip():
            return None
        font_path = Path(self.logo_text_font_file).expanduser()
        if font_path.exists() and font_path.is_file():
            return font_path
        return None

    def _local_font_display_name(self, font_path: Path) -> str:
        raw_name = font_path.stem
        cleaned = raw_name.replace("_", " ").replace("-", " ")
        cleaned = re.sub(r"\b(personal use only|personal use|demo|regular|bold|italic|condensed|compressed)\b", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"([a-z])([A-Z])", r"\1 \2", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if not cleaned:
            cleaned = raw_name.strip() or "Typographie locale"
        return cleaned.title()

    def _local_font_family_key(self, display_name: str) -> str:
        normalized = self._normalize_dafont_label(display_name)
        cleaned_tokens = []
        for token in normalized.split():
            trimmed = re.sub(r"\d+$", "", token)
            if trimmed in {"", "regular", "bold", "italic", "condensed", "compressed", "demo", "use", "only"}:
                continue
            if trimmed in {"hv", "rg", "it", "comp", "cram", "hb", "sc", "mono"}:
                continue
            if re.fullmatch(r"(hb|mono|sc)?\d*", trimmed):
                continue
            cleaned_tokens.append(trimmed)
        tokens = cleaned_tokens
        if not tokens:
            return normalized
        if len(tokens) > 2:
            tokens = tokens[:2]
        return " ".join(tokens)

    def _local_font_style_from_path(self, font_path: Path) -> str:
        try:
            relative = font_path.resolve().relative_to(self.typo_dir.resolve())
        except Exception:
            return "ajout local"
        parts = relative.parts
        if len(parts) >= 4 and parts[0].lower() == "dafont":
            return parts[2]
        if len(parts) >= 2:
            return parts[-2]
        return "ajout local"

    def _local_logo_font_entries(self) -> list[LocalFontLibraryEntry]:
        if not self.typo_dir.exists():
            return []

        all_font_files = [
            path
            for path in self.typo_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in {".ttf", ".otf", ".ttc"}
        ]
        available_files_by_name: dict[str, list[Path]] = {}
        for path in all_font_files:
            available_files_by_name.setdefault(path.name.lower(), []).append(path)
        entries: list[LocalFontLibraryEntry] = []
        for spec in LOCAL_LOGO_FONT_LIBRARY:
            selected_path = None
            for candidate_name in spec["files"]:
                matched_paths = available_files_by_name.get(candidate_name.lower(), [])
                selected_path = self._pick_best_font_file(matched_paths)
                if selected_path is not None:
                    break
            if selected_path is None:
                continue
            entries.append(
                LocalFontLibraryEntry(
                    name=str(spec["name"]),
                    style=str(spec["style"]),
                    file_path=str(selected_path),
                )
            )
        known_paths = {Path(entry.file_path).resolve() for entry in entries}
        known_name_keys = {self._normalize_dafont_label(entry.name) for entry in entries}
        known_family_keys = {self._local_font_family_key(entry.name) for entry in entries}
        extra_buckets: dict[str, list[Path]] = {}
        for path in all_font_files:
            resolved = path.resolve()
            if resolved in known_paths:
                continue
            display_name = self._local_font_display_name(path)
            display_key = self._normalize_dafont_label(display_name)
            family_key = self._local_font_family_key(display_name)
            if any(
                display_key == known_key
                or display_key.startswith(f"{known_key} ")
                or known_key.startswith(f"{display_key} ")
                for known_key in known_name_keys
            ):
                continue
            if family_key and family_key in known_family_keys:
                continue
            extra_buckets.setdefault(display_name, []).append(path)

        for display_name in sorted(extra_buckets):
            picked_path = self._pick_best_font_file(extra_buckets[display_name])
            if picked_path is None:
                continue
            known_name_keys.add(self._normalize_dafont_label(display_name))
            known_family_keys.add(self._local_font_family_key(display_name))
            entries.append(
                LocalFontLibraryEntry(
                    name=display_name,
                    style=self._local_font_style_from_path(picked_path),
                    file_path=str(picked_path),
                )
            )
        return entries

    def _delete_local_logo_font_entry(self, entry: LocalFontLibraryEntry):
        target_path = Path(entry.file_path).expanduser()
        if not target_path.exists():
            raise RuntimeError("Le fichier de typographie est introuvable.")
        if self.typo_dir.resolve() not in target_path.resolve().parents:
            raise RuntimeError("La typographie selectionnee est hors du dossier asset/Typographie.")

        deletion_root = None
        try:
            relative = target_path.resolve().relative_to(self.typo_dir.resolve())
        except Exception as exc:
            raise RuntimeError("Impossible de localiser la typographie dans asset/Typographie.") from exc

        if len(relative.parts) >= 4 and relative.parts[0].lower() == "dafont":
            deletion_root = self.typo_dir.joinpath(*relative.parts[:4])

        if deletion_root is not None and deletion_root.exists() and deletion_root.is_dir():
            shutil.rmtree(deletion_root)
        else:
            target_path.unlink()
            parent = target_path.parent
            typo_root = self.typo_dir.resolve()
            while parent.exists() and parent.resolve() != typo_root:
                try:
                    parent.rmdir()
                except OSError:
                    break
                parent = parent.parent

        selected_font_path = self._selected_logo_font_path()
        if selected_font_path is not None:
            try:
                selected_resolved = selected_font_path.resolve()
                deleted_root = (deletion_root or target_path).resolve()
                if selected_resolved == deleted_root or deleted_root in selected_resolved.parents:
                    self._reset_logo_font_selection()
            except Exception:
                pass

        self.local_font_preview_cache.clear()
        self.dafont_font_details_cache.clear()
        self.dafont_theme_site_fonts_cache.clear()
        self.dafont_theme_fonts_cache.clear()
        self.dafont_font_compatibility_cache.clear()

    def _fit_local_preview_font(
        self,
        draw: ImageDraw.ImageDraw,
        font_path: Path,
        text: str,
        start_size: int,
        max_width: int,
        min_size: int = 18,
    ):
        current_size = max(min_size, start_size)
        best_font = None
        best_bbox = None
        while current_size >= min_size:
            font = ImageFont.truetype(str(font_path), current_size)
            bbox = draw.textbbox((0, 0), text, font=font)
            width = bbox[2] - bbox[0]
            best_font = font
            best_bbox = bbox
            if width <= max_width:
                break
            current_size -= 4
        return best_font, best_bbox

    def _local_font_preview_pixmap(self, entry: LocalFontLibraryEntry) -> QPixmap:
        font_path = Path(entry.file_path)
        if not font_path.exists():
            return QPixmap()

        cache_key = f"{font_path.resolve()}|{font_path.stat().st_mtime_ns}"
        cached = self.local_font_preview_cache.get(cache_key)
        if cached is not None:
            return cached

        canvas_w, canvas_h = 1320, 560
        preview = Image.new("RGBA", (canvas_w, canvas_h), (31, 31, 36, 255))
        draw = ImageDraw.Draw(preview)
        text_color = (243, 243, 239, 255)
        accent_color = (186, 166, 199, 255)
        sample_lines = [
            ("ABCDEFGHIJKLMNOPQRSTUVWXYZ", 84),
            ("abcdefghijklmnopqrstuvwxyz", 76),
            ("0123456789  !?&+-", 64),
        ]

        try:
            y = 70
            for line_text, initial_size in sample_lines:
                font, bbox = self._fit_local_preview_font(
                    draw,
                    font_path,
                    line_text,
                    initial_size,
                    canvas_w - 120,
                )
                if font is None or bbox is None:
                    continue
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                x = int((canvas_w - text_width) / 2) - bbox[0]
                draw.text((x, y - bbox[1]), line_text, fill=text_color, font=font)
                y += text_height + 28

            info_font = ImageFont.load_default()
            info_text = f"{entry.name}  —  {entry.style}"
            info_bbox = draw.textbbox((0, 0), info_text, font=info_font)
            info_x = max(20, int((canvas_w - (info_bbox[2] - info_bbox[0])) / 2) - info_bbox[0])
            draw.text((info_x, canvas_h - 42 - info_bbox[1]), info_text, fill=accent_color, font=info_font)
        except OSError:
            return QPixmap()

        pixmap = self._pil_to_qpixmap(preview)
        if not pixmap.isNull():
            self.local_font_preview_cache[cache_key] = pixmap
        return pixmap

    def _dafont_headers(self) -> dict[str, str]:
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ARPlus/1.0",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.7",
        }

    def _fetch_remote_bytes(self, url: str, extra_headers: dict[str, str] | None = None) -> bytes:
        headers = dict(self._dafont_headers())
        if extra_headers:
            headers.update(extra_headers)
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.read()

    def _fetch_remote_text(self, url: str) -> str:
        raw = self._fetch_remote_bytes(url)
        head = raw[:4096].decode("ascii", errors="ignore")
        encodings = []
        charset_match = re.search(r"charset\s*=\s*([a-zA-Z0-9._-]+)", head, re.IGNORECASE)
        if charset_match is not None:
            encodings.append(charset_match.group(1).strip())
        encodings.extend(["utf-8", "iso-8859-1", "cp1252"])
        tried: set[str] = set()
        for encoding in encodings:
            normalized = (encoding or "").strip().lower()
            if not normalized or normalized in tried:
                continue
            tried.add(normalized)
            try:
                return raw.decode(encoding)
            except (LookupError, UnicodeDecodeError):
                continue
        return raw.decode("utf-8", errors="ignore")

    def _dafont_normalize_url(self, raw_url: str, base_url: str = DAFONT_BASE_URL) -> str:
        candidate = (raw_url or "").strip()
        if not candidate:
            return ""
        if candidate.startswith("//"):
            candidate = f"https:{candidate}"
        normalized = urllib.parse.urljoin(base_url, candidate)
        return self._dafont_force_french_page_url(normalized)

    def _dafont_force_french_page_url(self, url: str) -> str:
        parsed = urllib.parse.urlparse(url)
        if not parsed.netloc or "dafont.com" not in parsed.netloc.lower():
            return url
        if parsed.netloc.lower().startswith("dl."):
            return url

        path = parsed.path or "/"
        lowered_path = path.lower()
        if lowered_path.startswith("/img/") or lowered_path.startswith("/css/") or lowered_path.startswith("/js/"):
            return url
        if lowered_path.startswith("/fr/"):
            return urllib.parse.urlunparse(parsed._replace(path="/fr/" + path[4:]))
        if lowered_path.endswith(".font") or lowered_path.endswith("themes.php"):
            return urllib.parse.urlunparse(parsed._replace(path=f"/fr{path}"))
        return url

    def _normalize_dafont_label(self, value: str) -> str:
        ascii_value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
        return re.sub(r"[^a-z0-9]+", " ", ascii_value.lower()).strip()

    def _strip_html_fragment(self, value: str) -> str:
        if not value:
            return ""
        stripped = re.sub(r"<[^>]+>", " ", value, flags=re.IGNORECASE | re.DOTALL)
        return " ".join(html.unescape(stripped).split())

    def _html_attribute(self, source: str, attr_name: str) -> str:
        if not source:
            return ""
        pattern = rf'\b{re.escape(attr_name)}\s*=\s*["\']([^"\']+)["\']'
        match = re.search(pattern, source, flags=re.IGNORECASE | re.DOTALL)
        return html.unescape(match.group(1).strip()) if match else ""

    def _first_image_src(self, source: str, base_url: str = DAFONT_BASE_URL) -> str:
        if not source:
            return ""
        match = re.search(r'<img\b[^>]*\bsrc\s*=\s*["\']([^"\']+)["\']', source, re.IGNORECASE)
        if match is None:
            return ""
        return self._dafont_normalize_url(match.group(1), base_url)

    def _dafont_slug_from_page_url(self, page_url: str) -> str:
        parsed = urllib.parse.urlparse(page_url)
        slug = Path(parsed.path).name
        if slug.lower().endswith(".font"):
            slug = slug[:-5]
        return slug.strip()

    def _dafont_slug_from_download_url(self, download_url: str) -> str:
        parsed = urllib.parse.urlparse(download_url)
        query = urllib.parse.parse_qs(parsed.query)
        return str(query.get("f", [""])[0]).strip()

    def _pretty_dafont_name(self, slug: str) -> str:
        chunks = [chunk for chunk in re.split(r"[-_]+", slug.strip()) if chunk]
        if not chunks:
            return "Typographie"
        return " ".join(chunk[:1].upper() + chunk[1:] for chunk in chunks)

    def _dafont_theme_page_url(self, theme_url: str, page_number: int) -> str:
        parsed = urllib.parse.urlparse(self._dafont_force_french_page_url(theme_url))
        query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        if page_number > 1:
            query["page"] = [str(page_number)]
        else:
            query.pop("page", None)
        return urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(query, doseq=True)))

    def _dafont_preview_url_for_slug(self, slug: str) -> str:
        cleaned = re.sub(r"[^a-z0-9_-]+", "", slug.strip().lower())
        if not cleaned:
            return ""
        chars = [ch for ch in cleaned if ch.isalnum()]
        if not chars:
            return ""
        first_char = chars[0]
        second_char = chars[1] if len(chars) > 1 else chars[0]
        return f"{DAFONT_BASE_URL}/img/preview/{first_char}/{second_char}/{cleaned}.png"

    def _dafont_preview_url_for_entry(self, page_url: str, download_url: str = "") -> str:
        slug = self._dafont_slug_from_download_url(download_url) or self._dafont_slug_from_page_url(page_url)
        return self._dafont_preview_url_for_slug(slug)

    def _safe_typo_folder_name(self, label: str, fallback: str) -> str:
        cleaned = re.sub(r'[<>:"/\\|?*]+', "-", (label or "").strip())
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
        return cleaned or fallback

    def _dafont_is_personal_use_only(self, *texts: str) -> bool:
        normalized = self._normalize_dafont_label(" ".join(texts))
        if not normalized:
            return False
        blocked_tokens = [
            "gratuit pour un usage personnel",
            "usage personnel",
            "personal use only",
            "personal use",
            "personnal use",
        ]
        return any(token in normalized for token in blocked_tokens)

    def _dafont_has_blocked_display_text(self, *texts: str) -> bool:
        joined = " ".join(texts)
        return "€" in joined or self._dafont_is_personal_use_only(*texts)

    def _dafont_health_summary_text(self, payload: dict | None = None) -> str:
        status = payload if isinstance(payload, dict) else self.dafont_health_status
        if not isinstance(status, dict) or not status:
            return "Verification DaFont: en attente"
        checked_at = str(status.get("checked_at", "")).strip()
        if status.get("ok"):
            suffix = f" ({checked_at})" if checked_at else ""
            return f"Verification DaFont: OK{suffix}"
        error = str(status.get("error", "")).strip()
        if checked_at:
            return f"Verification DaFont: attention ({checked_at}) {error}".strip()
        return f"Verification DaFont: attention {error}".strip()

    def _perform_dafont_health_check(self) -> dict:
        checked_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        payload = {
            "ok": False,
            "checked_at": checked_at,
            "results_per_page": DAFONT_RESULTS_PER_PAGE,
        }
        try:
            themes = self._dafont_fetch_themes()
            grouped = self._group_dafont_themes(themes)
            group_names = [group_name for group_name, _themes in grouped]
            expected_groups = [group_name for group_name, _themes in DAFONT_THEME_GROUPS]
            missing_groups = [group_name for group_name in expected_groups if group_name not in group_names]
            payload["groups_found"] = group_names
            payload["missing_groups"] = missing_groups

            sample_group_name = ""
            sample_theme_name = ""
            sample_theme_url = ""
            for group_name, group_themes in grouped:
                if group_themes:
                    sample_group_name = group_name
                    sample_theme_name = group_themes[0].name
                    sample_theme_url = group_themes[0].url
                    break
            if not sample_theme_url:
                raise RuntimeError("Aucun sous-theme DaFont exploitable.")

            entries = self._dafont_fetch_theme_fonts(
                sample_theme_url,
                1,
                theme_group=sample_group_name,
                theme_name=sample_theme_name,
            )
            if not entries:
                raise RuntimeError("Aucune typographie compatible sur le sous-theme de test.")

            details = None
            for sample_entry in entries[:8]:
                details = self._dafont_resolve_compatible_entry(sample_entry)
                if details is not None:
                    break
            if details is None:
                raise RuntimeError("Aucune typographie DaFont compatible pour le controle.")
            preview_ok = bool(details.preview_url)
            if preview_ok:
                preview_ok = not self._dafont_fetch_preview_pixmap(details.preview_url, details.page_url).isNull()

            download_ready = bool(details.local_font_path)
            if not download_ready and details.download_url:
                sample_bytes = self._fetch_remote_bytes(
                    details.download_url,
                    {"Range": "bytes=0-63"},
                )
                download_ready = sample_bytes.startswith(b"PK")

            payload.update(
                {
                    "sample_theme": f"{sample_group_name} / {sample_theme_name}",
                    "sample_font": details.name,
                    "preview_ok": preview_ok,
                    "download_ready": download_ready,
                    "ok": not missing_groups and preview_ok and download_ready,
                }
            )
            if not payload["ok"]:
                payload["error"] = "Verification incomplete des previews ou du telechargement."
        except Exception as exc:
            payload["error"] = str(exc)
            payload["ok"] = False

        self._save_dafont_health_status(payload)
        return payload

    def _dafont_resolve_compatible_entry(self, entry: DaFontFontEntry) -> DaFontFontEntry | None:
        page_url = self._dafont_force_french_page_url(entry.page_url)
        cached_compatibility = self.dafont_font_compatibility_cache.get(page_url)
        if cached_compatibility is False:
            return None
        if cached_compatibility is True:
            cached_details = self.dafont_font_details_cache.get(page_url)
            if cached_details is not None:
                return self._with_local_font_path(cached_details)
            return self._with_local_font_path(entry)
        if self._dafont_has_blocked_display_text(entry.name, entry.license_label):
            self.dafont_font_compatibility_cache[page_url] = False
            return None
        try:
            detailed = self._dafont_fetch_font_details(page_url, seed=entry)
        except RuntimeError as exc:
            lowered = str(exc).lower()
            if any(token in lowered for token in ["ignoree", "usage personnel", "non compatible", "euro"]):
                self.dafont_font_compatibility_cache[page_url] = False
                return None
            raise
        self.dafont_font_compatibility_cache[page_url] = True
        return self._with_local_font_path(detailed)

    def _local_typo_dir_for_slug(self, slug: str, theme_group: str = "", theme_name: str = "") -> Path:
        safe_slug = self._safe_typo_folder_name(slug, "font")
        target_dir = self.typo_dir
        if theme_group or theme_name:
            target_dir = target_dir / "DaFont"
            if theme_group:
                target_dir = target_dir / self._safe_typo_folder_name(theme_group, "Theme")
            if theme_name:
                target_dir = target_dir / self._safe_typo_folder_name(theme_name, "Sous-theme")
        return target_dir / safe_slug

    def _font_files_in_dir(self, target_dir: Path) -> list[Path]:
        extensions = {".ttf", ".otf", ".ttc"}
        return sorted(
            [path for path in target_dir.rglob("*") if path.is_file() and path.suffix.lower() in extensions]
        )

    def _pick_best_font_file(self, candidates: list[Path]) -> Path | None:
        if not candidates:
            return None

        def sort_key(path: Path):
            name = path.stem.lower()
            penalty = 0
            if "italic" in name or "oblique" in name:
                penalty += 40
            if "thin" in name or "light" in name:
                penalty += 20
            if "condensed" in name:
                penalty += 10
            if "regular" in name:
                penalty -= 10
            if "bold" in name or "black" in name:
                penalty -= 4
            return (penalty, len(name), name)

        return sorted(candidates, key=sort_key)[0]

    def _local_font_path_for_entry(self, entry: DaFontFontEntry) -> Path | None:
        slug = self._dafont_slug_from_download_url(entry.download_url) or self._dafont_slug_from_page_url(
            entry.page_url
        )
        if not slug:
            return None
        target_dir = self._local_typo_dir_for_slug(slug, entry.theme_group, entry.theme_name)
        font_file = self._pick_best_font_file(self._font_files_in_dir(target_dir))
        return font_file

    def _with_local_font_path(self, entry: DaFontFontEntry) -> DaFontFontEntry:
        local_font_path = self._local_font_path_for_entry(entry)
        if local_font_path is None:
            return entry
        return DaFontFontEntry(
            name=entry.name,
            page_url=entry.page_url,
            preview_url=entry.preview_url,
            download_url=entry.download_url,
            local_font_path=str(local_font_path),
            license_label=entry.license_label,
            theme_group=entry.theme_group,
            theme_name=entry.theme_name,
            font_file_name=entry.font_file_name,
            author_note=entry.author_note,
        )

    def _group_dafont_themes(self, themes: list[DaFontTheme]) -> list[tuple[str, list[DaFontTheme]]]:
        grouped: list[tuple[str, list[DaFontTheme]]] = []
        extras: list[DaFontTheme] = []
        index = 0
        total = len(themes)

        for group_name, expected_subthemes in DAFONT_THEME_GROUPS:
            bucket: list[DaFontTheme] = []
            for expected_name in expected_subthemes:
                if index >= total:
                    break
                expected_normalized = self._normalize_dafont_label(expected_name)
                matched_index = None
                search_limit = min(total, index + 4)
                for probe_index in range(index, search_limit):
                    candidate_name = self._normalize_dafont_label(themes[probe_index].name)
                    if candidate_name == expected_normalized:
                        matched_index = probe_index
                        break
                if matched_index is None:
                    break
                while index < matched_index:
                    extras.append(themes[index])
                    index += 1
                bucket.append(themes[index])
                index += 1
            if bucket:
                grouped.append((group_name, bucket))

        if index < total:
            extras.extend(themes[index:])
        if extras:
            grouped.append(("Autres", extras))
        if not grouped:
            grouped.append(("Tous", list(themes)))
        return grouped

    def _preview_cache_path(self, preview_url: str) -> Path:
        parsed = urllib.parse.urlparse(preview_url)
        suffix = Path(parsed.path).suffix.lower()
        if suffix not in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}:
            suffix = ".png"
        cache_name = hashlib.sha1(preview_url.encode("utf-8")).hexdigest() + suffix
        return self.preview_cache_dir / cache_name

    def _dafont_parse_themes(self, page_html: str) -> list[DaFontTheme]:
        themes: list[DaFontTheme] = []
        seen_cats: set[str] = set()
        pattern = re.compile(
            r'<a\b(?P<attrs>[^>]*)href=["\'](?P<href>[^"\']*(?:theme\.php\?[^"\']+|bitmap\.php))["\'][^>]*>(?P<body>.*?)</a>',
            re.IGNORECASE | re.DOTALL,
        )
        for match in pattern.finditer(page_html):
            full_url = self._dafont_normalize_url(match.group("href"))
            parsed_url = urllib.parse.urlparse(full_url)
            query = urllib.parse.parse_qs(parsed_url.query)
            if parsed_url.path.lower().endswith("bitmap.php"):
                category = "bitmap"
            else:
                category = str(query.get("cat", [""])[0]).strip()
            if not category or category in seen_cats:
                continue
            name = self._strip_html_fragment(match.group("body"))
            if not name:
                name = self._html_attribute(match.group("attrs"), "title")
            if not name or len(name) > 80:
                continue
            if category == "bitmap" and self._normalize_dafont_label(name) == "bitmap":
                continue
            seen_cats.add(category)
            themes.append(DaFontTheme(name=name, url=full_url))
        return themes

    def _dafont_parse_theme_fonts(
        self,
        page_html: str,
        base_url: str,
        theme_group: str = "",
        theme_name: str = "",
    ) -> list[DaFontFontEntry]:
        entries: list[DaFontFontEntry] = []
        seen_urls: set[str] = set()
        block_pattern = re.compile(
            r'<a name=["\']?\d+["\']?>\s*</a>(?P<block>.*?)(?=<a name=["\']?\d+["\']?>\s*</a>|$)',
            re.IGNORECASE | re.DOTALL,
        )
        for block_match in block_pattern.finditer(page_html):
            block = block_match.group("block")
            header_match = re.search(
                r'<div class="lv1left[^"]*"[^>]*>.*?<a href=["\'](?P<href>[^"\']+?\.font(?:\?[^"\']*)?)["\'][^>]*>\s*<strong>(?P<name>.*?)</strong>\s*</a>',
                block,
                re.IGNORECASE | re.DOTALL,
            )
            if header_match is None:
                continue
            page_url = self._dafont_normalize_url(header_match.group("href"), base_url)
            if not page_url or page_url in seen_urls:
                continue
            parsed = urllib.parse.urlparse(page_url)
            if not parsed.path.lower().endswith(".font"):
                continue

            name = self._strip_html_fragment(header_match.group("name"))
            if not name:
                name = self._pretty_dafont_name(self._dafont_slug_from_page_url(page_url))

            license_label = ""
            license_match = re.search(
                r'class=["\'][^"\']*help black[^"\']*["\'][^>]*>(?P<label>.*?)</a>',
                block,
                re.IGNORECASE | re.DOTALL,
            )
            if license_match is not None:
                license_label = self._strip_html_fragment(license_match.group("label"))
            if self._dafont_has_blocked_display_text(name, license_label, block):
                continue

            download_url = ""
            download_match = re.search(
                r'href=["\']([^"\']*(?:dl\.dafont\.com/dl/\?f=|/dl/\?f=)[^"\']+)["\']',
                block,
                re.IGNORECASE | re.DOTALL,
            )
            if download_match is not None:
                raw_download_url = download_match.group(1)
                if raw_download_url.startswith("/dl/"):
                    download_url = f"https://dl.dafont.com{raw_download_url}"
                else:
                    download_url = self._dafont_normalize_url(raw_download_url, page_url)

            preview_url = ""
            preview_match = re.search(r'background-image:url\((?P<url>[^)]+)\)', block, re.IGNORECASE)
            if preview_match is not None:
                preview_url = self._dafont_normalize_url(
                    preview_match.group("url").strip().strip("'\""),
                    base_url,
                )
            if not preview_url:
                preview_url = self._dafont_preview_url_for_entry(page_url, download_url)
            seen_urls.add(page_url)
            entries.append(
                DaFontFontEntry(
                    name=name,
                    page_url=page_url,
                    preview_url=preview_url,
                    download_url=download_url,
                    license_label=license_label,
                    theme_group=theme_group,
                    theme_name=theme_name,
                )
            )
        return entries

    def _dafont_fetch_themes(self) -> list[DaFontTheme]:
        if self.dafont_themes_cache is not None:
            return list(self.dafont_themes_cache)

        sources = [
            DAFONT_THEMES_URL,
        ]
        last_error = None
        for source_url in sources:
            try:
                page_html = self._fetch_remote_text(source_url)
                parsed = self._dafont_parse_themes(page_html)
                if parsed:
                    self.dafont_themes_cache = parsed
                    return list(parsed)
            except Exception as exc:
                last_error = exc
        if last_error is not None:
            raise last_error
        raise RuntimeError("Aucun theme exploitable trouve sur DaFont.")

    def _dafont_fetch_theme_site_fonts(
        self,
        theme_url: str,
        site_page_number: int = 1,
        theme_group: str = "",
        theme_name: str = "",
    ) -> list[DaFontFontEntry]:
        page_url = self._dafont_theme_page_url(theme_url, site_page_number)
        cache_key = f"{page_url}|site_page={site_page_number}"
        cached = self.dafont_theme_site_fonts_cache.get(cache_key)
        if cached is not None:
            return [self._with_local_font_path(entry) for entry in cached]

        page_html = self._fetch_remote_text(page_url)
        entries = self._dafont_parse_theme_fonts(page_html, page_url, theme_group, theme_name)
        self.dafont_theme_site_fonts_cache[cache_key] = entries
        return [self._with_local_font_path(entry) for entry in entries]

    def _dafont_fetch_theme_fonts(
        self,
        theme_url: str,
        page_number: int = 1,
        theme_group: str = "",
        theme_name: str = "",
    ) -> list[DaFontFontEntry]:
        logical_page = max(1, int(page_number))
        cache_key = f"{theme_url}|logical_page={logical_page}|per_page={DAFONT_RESULTS_PER_PAGE}"
        cached = self.dafont_theme_fonts_cache.get(cache_key)
        if cached is not None:
            return [self._with_local_font_path(entry) for entry in cached]

        start_index = (logical_page - 1) * DAFONT_RESULTS_PER_PAGE
        end_index = start_index + DAFONT_RESULTS_PER_PAGE
        collected: list[DaFontFontEntry] = []
        seen_urls: set[str] = set()
        consecutive_empty_pages = 0

        for site_page_number in range(1, DAFONT_SITE_PAGE_SCAN_LIMIT + 1):
            site_entries = self._dafont_fetch_theme_site_fonts(
                theme_url,
                site_page_number,
                theme_group=theme_group,
                theme_name=theme_name,
            )
            new_count = 0
            for entry in site_entries:
                if entry.page_url in seen_urls:
                    continue
                seen_urls.add(entry.page_url)
                collected.append(entry)
                new_count += 1
            if new_count == 0:
                consecutive_empty_pages += 1
            else:
                consecutive_empty_pages = 0
            if len(collected) >= end_index:
                break
            if consecutive_empty_pages >= 2:
                break

        page_entries = collected[start_index:end_index]
        if not page_entries:
            raise RuntimeError("Aucune typographie compatible detectee pour cette page logique.")
        page_entries = sorted(page_entries, key=lambda entry: self._normalize_dafont_label(entry.name))
        self.dafont_theme_fonts_cache[cache_key] = list(page_entries)
        return [self._with_local_font_path(entry) for entry in page_entries]

    def _dafont_fetch_font_details(
        self,
        page_url: str,
        seed: DaFontFontEntry | None = None,
    ) -> DaFontFontEntry:
        page_url = self._dafont_force_french_page_url(page_url)
        cached = self.dafont_font_details_cache.get(page_url)
        if cached is not None:
            return self._with_local_font_path(cached)

        page_html = self._fetch_remote_text(page_url)
        name = seed.name if seed is not None else self._pretty_dafont_name(self._dafont_slug_from_page_url(page_url))
        license_label = seed.license_label if seed is not None else ""
        theme_group = seed.theme_group if seed is not None else ""
        theme_name = seed.theme_name if seed is not None else ""
        font_file_name = seed.font_file_name if seed is not None else ""
        author_note = seed.author_note if seed is not None else ""
        title_match = re.search(r"<title>\s*(.*?)\s*(?:\||-)\s*dafont\.com", page_html, re.IGNORECASE | re.DOTALL)
        if title_match:
            parsed_title = self._strip_html_fragment(title_match.group(1))
            if parsed_title:
                name = parsed_title

        if not license_label:
            license_match = re.search(
                r'class=["\'][^"\']*help black[^"\']*["\'][^>]*>(?P<label>.*?)</a>',
                page_html,
                re.IGNORECASE | re.DOTALL,
            )
            if license_match is not None:
                license_label = self._strip_html_fragment(license_match.group("label"))

        download_url = seed.download_url if seed is not None else ""
        if not download_url:
            download_match = re.search(
                r'href=["\']([^"\']*(?:dl\.dafont\.com/dl/\?f=|/dl/\?f=)[^"\']+)["\']',
                page_html,
                re.IGNORECASE | re.DOTALL,
            )
            if download_match:
                raw_download_url = download_match.group(1)
                if raw_download_url.startswith("/dl/"):
                    download_url = f"https://dl.dafont.com{raw_download_url}"
                else:
                    download_url = self._dafont_normalize_url(raw_download_url, page_url)

        preview_url = self._dafont_preview_url_for_entry(page_url, download_url)
        if not preview_url and seed is not None:
            preview_url = seed.preview_url
        if not preview_url:
            for img_match in re.finditer(
                r'<img\b[^>]*\bsrc\s*=\s*["\']([^"\']+)["\'][^>]*>',
                page_html,
                re.IGNORECASE | re.DOTALL,
            ):
                candidate = self._dafont_normalize_url(img_match.group(1), page_url)
                lowered = candidate.lower()
                if any(token in lowered for token in ["preview", "fontpreview", "img.dafont.com"]):
                    preview_url = candidate
                    break

        if not font_file_name:
            file_match = re.search(
                r'<span class="filename">\s*(?P<filename>.*?)\s*</span>',
                page_html,
                re.IGNORECASE | re.DOTALL,
            )
            if file_match is not None:
                font_file_name = self._strip_html_fragment(file_match.group("filename"))

        if not author_note:
            note_match = re.search(
                r"Note de l'auteur.*?</div>\s*<div>(?P<note>.*?)</div>\s*</div>",
                page_html,
                re.IGNORECASE | re.DOTALL,
            )
            if note_match is not None:
                author_note = self._strip_html_fragment(note_match.group("note"))

        if self._dafont_has_blocked_display_text(name, license_label, font_file_name, author_note):
            raise RuntimeError("Typographie DaFont ignoree car marquee usage personnel ou non compatible.")

        resolved = self._with_local_font_path(
            DaFontFontEntry(
                name=name,
                page_url=page_url,
                preview_url=preview_url,
                download_url=download_url,
                license_label=license_label,
                theme_group=theme_group,
                theme_name=theme_name,
                font_file_name=font_file_name,
                author_note=author_note,
            )
        )
        self.dafont_font_details_cache[page_url] = resolved
        return resolved

    def _dafont_fetch_preview_pixmap(self, preview_url: str, page_url: str = "") -> QPixmap:
        preview_candidates: list[str] = []
        if preview_url:
            preview_candidates.append(preview_url)

        detail_url = self._dafont_force_french_page_url(page_url) if page_url else ""
        if detail_url:
            fallback_preview = self._dafont_preview_url_for_entry(detail_url)
            if fallback_preview and fallback_preview not in preview_candidates:
                preview_candidates.append(fallback_preview)

        for candidate_url in preview_candidates:
            cached = self.dafont_preview_cache.get(candidate_url)
            if cached is not None:
                return cached

            cache_path = self._preview_cache_path(candidate_url)
            if cache_path.exists():
                pixmap = QPixmap(str(cache_path))
                if not pixmap.isNull():
                    self.dafont_preview_cache[candidate_url] = pixmap
                    return pixmap

            try:
                raw = self._fetch_remote_bytes(
                    candidate_url,
                    {
                        "Referer": detail_url or DAFONT_THEMES_URL,
                        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                    },
                )
            except Exception:
                continue

            self.preview_cache_dir.mkdir(parents=True, exist_ok=True)
            try:
                cache_path.write_bytes(raw)
            except Exception:
                pass

            pixmap = QPixmap()
            if not pixmap.loadFromData(raw):
                pixmap = QPixmap(str(cache_path))
            if pixmap.isNull():
                continue

            self.dafont_preview_cache[candidate_url] = pixmap
            return pixmap

        if detail_url:
            try:
                page_html = self._fetch_remote_text(detail_url)
            except Exception:
                return QPixmap()
            for img_match in re.finditer(
                r'<img\b[^>]*\bsrc\s*=\s*["\']([^"\']+)["\'][^>]*>',
                page_html,
                re.IGNORECASE | re.DOTALL,
            ):
                candidate = self._dafont_normalize_url(img_match.group(1), detail_url)
                lowered = candidate.lower()
                if not any(token in lowered for token in ["preview", "/img/preview/", "img.dafont.com"]):
                    continue
                pixmap = self._dafont_fetch_preview_pixmap(candidate, "")
                if not pixmap.isNull():
                    return pixmap
        return QPixmap()

    def _extract_zip_member_name(self, raw_name: str) -> PurePosixPath | None:
        member_path = PurePosixPath(raw_name)
        safe_parts = [part for part in member_path.parts if part not in ("", ".", "..")]
        if not safe_parts:
            return None
        return PurePosixPath(*safe_parts)

    def _extract_zip_to_dir(self, archive: zipfile.ZipFile, target_dir: Path):
        for member in archive.infolist():
            safe_name = self._extract_zip_member_name(member.filename)
            if safe_name is None:
                continue
            destination = target_dir.joinpath(*safe_name.parts)
            if member.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as src_file, destination.open("wb") as dest_file:
                dest_file.write(src_file.read())

    def _download_and_install_dafont_font(self, entry: DaFontFontEntry) -> DaFontFontEntry:
        detailed = self._dafont_fetch_font_details(entry.page_url, seed=entry)
        if detailed.local_font_path:
            return detailed
        if self._dafont_has_blocked_display_text(
            detailed.name,
            detailed.license_label,
            detailed.font_file_name,
            detailed.author_note,
        ):
            raise RuntimeError("Cette typographie DaFont est reservee a un usage personnel et a ete ignoree.")
        if not detailed.download_url:
            raise RuntimeError("Lien de telechargement DaFont introuvable pour cette typographie.")

        slug = self._dafont_slug_from_download_url(detailed.download_url) or self._dafont_slug_from_page_url(
            detailed.page_url
        )
        if not slug:
            raise RuntimeError("Impossible d'identifier le dossier cible pour cette typographie.")

        self.typo_dir.mkdir(parents=True, exist_ok=True)
        target_dir = self._local_typo_dir_for_slug(slug, detailed.theme_group, detailed.theme_name)
        target_dir.mkdir(parents=True, exist_ok=True)

        zip_bytes = self._fetch_remote_bytes(detailed.download_url)
        zip_path = target_dir / f"{slug}.zip"
        zip_path.write_bytes(zip_bytes)

        try:
            with zipfile.ZipFile(BytesIO(zip_bytes)) as archive:
                self._extract_zip_to_dir(archive, target_dir)
        except zipfile.BadZipFile as exc:
            raise RuntimeError("Archive DaFont invalide ou non reconnue.") from exc

        font_file = self._pick_best_font_file(self._font_files_in_dir(target_dir))
        if font_file is None:
            raise RuntimeError("Aucun fichier .ttf/.otf exploitable n'a ete trouve dans l'archive.")

        try:
            ImageFont.truetype(str(font_file), self._logo_effective_size())
        except OSError as exc:
            raise RuntimeError("La police extraite n'est pas exploitable par le programme.") from exc

        installed = DaFontFontEntry(
            name=detailed.name,
            page_url=detailed.page_url,
            preview_url=detailed.preview_url,
            download_url=detailed.download_url,
            local_font_path=str(font_file),
            license_label=detailed.license_label,
            theme_group=detailed.theme_group,
            theme_name=detailed.theme_name,
            font_file_name=detailed.font_file_name,
            author_note=detailed.author_note,
        )
        self.dafont_font_details_cache[detailed.page_url] = installed
        self._log(f"Typographie DaFont telechargee : {installed.name} -> {font_file}")
        return installed

    def _apply_logo_font_selection(self, entry):
        self._flush_logo_text_input()
        self._push_undo_state()
        self.logo_text_font_name = str(getattr(entry, "name", ""))
        self.logo_text_font_page_url = str(getattr(entry, "page_url", ""))
        self.logo_text_font_download_url = str(getattr(entry, "download_url", ""))
        self.logo_text_font_file = str(
            getattr(entry, "local_font_path", getattr(entry, "file_path", ""))
        )
        self._reapply_logo_auto_placement()
        self._invalidate_presets_preview()
        self._refresh_preview()
        self._sync_layer_controls()
        self._sync_logo_controls()

    def _reset_logo_font_selection(self):
        if not self._has_custom_logo_font():
            return
        self._flush_logo_text_input()
        self._push_undo_state()
        self.logo_text_font_name = ""
        self.logo_text_font_page_url = ""
        self.logo_text_font_download_url = ""
        self.logo_text_font_file = ""
        self._reapply_logo_auto_placement()
        self._invalidate_presets_preview()
        self._refresh_preview()
        self._sync_layer_controls()
        self._sync_logo_controls()

    def _snapshot_asset_paths(self):
        return {layer_id: asset.path for layer_id, asset in self.assets.items()}

    def _capture_undo_snapshot(self):
        return {
            "current_preset": self.current_preset,
            "active_layer": self.active_layer,
            "state": copy.deepcopy(self.state),
            "assets": self._snapshot_asset_paths(),
            "selected_exports": list(self._selected_exports()) if hasattr(self, "export_checks") else [],
            "export_dir": self.export_dir.text() if hasattr(self, "export_dir") else "",
            "guides": {
                "visible": self.guides_visible,
                "opacity": self.guides_opacity,
                "poster_variant": self.poster_guide_variant,
            },
            "gradient": copy.deepcopy(self.gradient_settings),
            "top": {
                "sync_all": self.top_sync_all,
                "settings": copy.deepcopy(self.top_settings),
            },
            "logo_text": {
                "enabled": self.logo_text_enabled,
                "text": self.logo_text,
                "size": self.logo_text_size,
                "align": self.logo_text_align,
                "force_upper": self.logo_text_force_upper,
                "line_spacing": self.logo_text_line_spacing,
                "color": self.logo_text_color,
                "font_name": self.logo_text_font_name,
                "font_page_url": self.logo_text_font_page_url,
                "font_download_url": self.logo_text_font_download_url,
                "font_file": self.logo_text_font_file,
            },
            "poster_textbox": {
                "enabled": self.poster_textbox_enabled,
                "text": self.poster_textbox_text,
            },
            "logo_shadow": {
                "enabled": self.logo_shadow_enabled,
                "distance": self.logo_shadow_distance,
                "blur": self.logo_shadow_blur,
                "angle": self.logo_shadow_angle,
                "opacity": self.logo_shadow_opacity,
                "color": self.logo_shadow_color,
            },
            "metadata_id": self.metadata_id_input.text() if hasattr(self, "metadata_id_input") else "",
            "base_name": self.base_name_input.text() if hasattr(self, "base_name_input") else "Name",
        }

    def _push_undo_state(self):
        if self.undo_in_progress:
            return
        self.undo_stack.append(self._capture_undo_snapshot())
        if len(self.undo_stack) > self.undo_limit:
            self.undo_stack = self.undo_stack[-self.undo_limit :]

    def _load_asset_from_path(self, file_path: Path):
        try:
            pil_img = Image.open(file_path).convert("RGBA")
        except Exception:
            return None
        pixmap = QPixmap(str(file_path))
        if pixmap.isNull():
            return None
        return LayerAsset(path=str(file_path), pixmap=pixmap, pil=pil_img)

    def _apply_selected_exports(self, selected_exports):
        if not hasattr(self, "export_checks"):
            return
        selected_ids = {
            item for item in selected_exports if isinstance(item, str) and item in self.export_checks
        }
        for export_id, check in self.export_checks.items():
            check.setChecked(export_id in selected_ids)

    def _restore_assets_from_snapshot(self, asset_paths):
        if not isinstance(asset_paths, dict):
            return
        restored_assets: Dict[str, LayerAsset] = {}
        for layer_id in LAYER_ORDER:
            raw_path = asset_paths.get(layer_id, "")
            if not isinstance(raw_path, str) or not raw_path.strip():
                restored_assets[layer_id] = LayerAsset()
                continue
            target_path = str(Path(raw_path).expanduser())
            current_asset = self.assets.get(layer_id)
            if (
                current_asset is not None
                and current_asset.path == target_path
                and current_asset.pixmap is not None
                and not current_asset.pixmap.isNull()
                and current_asset.pil is not None
            ):
                restored_assets[layer_id] = current_asset
                continue
            loaded_asset = self._load_asset_from_path(Path(target_path))
            restored_assets[layer_id] = loaded_asset if loaded_asset is not None else LayerAsset(path=target_path)
        self.assets = restored_assets

    def _restore_undo_snapshot(self, snapshot):
        if not isinstance(snapshot, dict):
            return
        self.undo_in_progress = True
        try:
            state_payload = snapshot.get("state")
            if isinstance(state_payload, dict):
                self.state = copy.deepcopy(state_payload)

            guides_payload = snapshot.get("guides", {})
            if isinstance(guides_payload, dict):
                self.guides_visible = bool(guides_payload.get("visible", self.guides_visible))
                self.guides_opacity = float(guides_payload.get("opacity", self.guides_opacity))
                poster_variant = guides_payload.get("poster_variant")
                if poster_variant in POSTER_GUIDE_FILES:
                    self.poster_guide_variant = poster_variant

            gradient_payload = snapshot.get("gradient")
            if isinstance(gradient_payload, dict):
                self.gradient_settings = copy.deepcopy(gradient_payload)

            top_payload = snapshot.get("top", {})
            if isinstance(top_payload, dict):
                self.top_sync_all = bool(top_payload.get("sync_all", self.top_sync_all))
                top_settings_payload = top_payload.get("settings")
                if isinstance(top_settings_payload, dict):
                    merged_top_settings = {
                        preset_id: self._default_top_config() for preset_id in TOP_PRESET_IDS
                    }
                    for preset_id in TOP_PRESET_IDS:
                        raw_config = top_settings_payload.get(preset_id)
                        if isinstance(raw_config, dict):
                            merged_top_settings[preset_id].update(raw_config)
                    self.top_settings = merged_top_settings

            logo_text_payload = snapshot.get("logo_text", {})
            if isinstance(logo_text_payload, dict):
                self.logo_text_enabled = bool(logo_text_payload.get("enabled", self.logo_text_enabled))
                self.logo_text = str(logo_text_payload.get("text", self.logo_text))
                self.logo_text_size = int(logo_text_payload.get("size", self.logo_text_size))
                self.logo_text_align = logo_text_payload.get("align", self.logo_text_align)
                self.logo_text_force_upper = bool(
                    logo_text_payload.get("force_upper", self.logo_text_force_upper)
                )
                self.logo_text_line_spacing = int(
                    logo_text_payload.get("line_spacing", self.logo_text_line_spacing)
                )
                self.logo_text_color = str(logo_text_payload.get("color", self.logo_text_color))
                self.logo_text_font_name = str(
                    logo_text_payload.get("font_name", self.logo_text_font_name)
                )
                self.logo_text_font_page_url = str(
                    logo_text_payload.get("font_page_url", self.logo_text_font_page_url)
                )
                self.logo_text_font_download_url = str(
                    logo_text_payload.get("font_download_url", self.logo_text_font_download_url)
                )
                self.logo_text_font_file = str(
                    logo_text_payload.get("font_file", self.logo_text_font_file)
                )

            poster_textbox_payload = snapshot.get("poster_textbox", {})
            if isinstance(poster_textbox_payload, dict):
                self.poster_textbox_enabled = bool(
                    poster_textbox_payload.get("enabled", self.poster_textbox_enabled)
                )
                self.poster_textbox_text = str(
                    poster_textbox_payload.get("text", self.poster_textbox_text)
                )

            logo_shadow_payload = snapshot.get("logo_shadow", {})
            if isinstance(logo_shadow_payload, dict):
                self.logo_shadow_enabled = bool(
                    logo_shadow_payload.get("enabled", self.logo_shadow_enabled)
                )
                self.logo_shadow_distance = int(
                    logo_shadow_payload.get("distance", self.logo_shadow_distance)
                )
                self.logo_shadow_blur = int(logo_shadow_payload.get("blur", self.logo_shadow_blur))
                self.logo_shadow_angle = float(
                    logo_shadow_payload.get("angle", self.logo_shadow_angle)
                )
                self.logo_shadow_opacity = int(
                    logo_shadow_payload.get("opacity", self.logo_shadow_opacity)
                )
                self.logo_shadow_color = str(
                    logo_shadow_payload.get("color", self.logo_shadow_color)
                )

            self._restore_assets_from_snapshot(snapshot.get("assets", {}))

            if hasattr(self, "metadata_id_input"):
                self.metadata_id_input.setText(str(snapshot.get("metadata_id", "")))
            if hasattr(self, "base_name_input"):
                self.base_name_input.setText(str(snapshot.get("base_name", "Name")))
            if hasattr(self, "export_dir"):
                self.export_dir.setText(str(snapshot.get("export_dir", self.export_dir.text())))

            self._apply_selected_exports(snapshot.get("selected_exports", []))

            current_preset = snapshot.get("current_preset")
            if current_preset in PRESETS:
                self.current_preset = current_preset
            else:
                self.current_preset = "poster"

            active_layer = snapshot.get("active_layer")
            if active_layer in CONTROL_LAYER_ORDER:
                self.active_layer = active_layer
            else:
                self.active_layer = "background"

            if hasattr(self, "preset_combo"):
                preset_index = self.preset_combo.findData(self.current_preset)
                if preset_index >= 0:
                    self.preset_combo.blockSignals(True)
                    self.preset_combo.setCurrentIndex(preset_index)
                    self.preset_combo.blockSignals(False)

            if hasattr(self, "show_guides_check"):
                self.show_guides_check.blockSignals(True)
                self.show_guides_check.setChecked(self.guides_visible)
                self.show_guides_check.blockSignals(False)
            if hasattr(self, "poster_guide_combo"):
                guide_idx = self.poster_guide_combo.findData(self.poster_guide_variant)
                if guide_idx >= 0:
                    self.poster_guide_combo.blockSignals(True)
                    self.poster_guide_combo.setCurrentIndex(guide_idx)
                    self.poster_guide_combo.blockSignals(False)

            self._sync_logo_controls()
            self._sync_poster_textbox_controls()
            self._sync_gradient_controls()
            self._sync_top_controls()
            self._update_shadow_slider_labels()
            self._load_guides()
            self._refresh_presets_preview_borders()
            self._invalidate_presets_preview()
            self._set_scene_for_preset(self.current_preset)
            self._set_active_layer(self.active_layer, sync=False)
            self._refresh_preview()
            self._sync_layer_controls()
        finally:
            self.undo_in_progress = False

    def _undo_project_state(self):
        if not self.undo_stack:
            return
        snapshot = self.undo_stack.pop()
        self._restore_undo_snapshot(snapshot)

    def _on_undo_shortcut(self):
        focus_widget = QApplication.focusWidget()
        if isinstance(focus_widget, (QLineEdit, QPlainTextEdit)):
            try:
                focus_widget.undo()
                return
            except Exception:
                pass
        self._undo_project_state()

    def _build_ui(self):
        root = QWidget(self)
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        top_layout = QHBoxLayout()

        self.left_panel = self._build_left_panel()
        self.left_panel.setMinimumWidth(280)
        self.left_scroll = QScrollArea()
        self.left_scroll.setWidgetResizable(True)
        self.left_scroll.setWidget(self.left_panel)
        self.left_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        top_layout.addWidget(self.left_scroll, 1)

        center = QVBoxLayout()
        center.setSpacing(8)
        center.addWidget(self._build_import_toolbar())
        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Gabarit en apercu:"))
        self.preset_combo = QComboBox()
        for preset_id, meta in PRESETS.items():
            self.preset_combo.addItem(f"{meta['label']} ({meta['size'][0]}x{meta['size'][1]})", preset_id)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        top_row.addWidget(self.preset_combo)
        top_row.addStretch(1)
        center.addLayout(top_row)
        center.addWidget(self.view, 1)
        top_layout.addLayout(center, 3)

        self.right_panel = self._build_right_panel()
        self.right_panel.setMinimumWidth(360)
        self.right_scroll = QScrollArea()
        self.right_scroll.setWidgetResizable(True)
        self.right_scroll.setWidget(self.right_panel)
        self.right_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        top_layout.addWidget(self.right_scroll, 1)

        layout.addLayout(top_layout, 1)
        layout.addWidget(self._build_presets_preview_strip())
        self._apply_responsive_side_widths()
        self._request_presets_preview_refresh(force=True)

    def _apply_responsive_side_widths(self):
        if not hasattr(self, "left_scroll") or not hasattr(self, "right_scroll"):
            return
        total_width = max(1, self.width())
        left_width = max(240, min(320, int(total_width * 0.18)))
        right_width = max(320, min(460, int(total_width * 0.28)))
        self.left_scroll.setMinimumWidth(left_width)
        self.left_scroll.setMaximumWidth(left_width)
        self.right_scroll.setMinimumWidth(right_width)
        self.right_scroll.setMaximumWidth(right_width)
        self._apply_compact_ui_labels()

    def _apply_compact_ui_labels(self):
        if not hasattr(self, "layer_buttons"):
            return
        panel_width = 0
        if hasattr(self, "right_scroll"):
            panel_width = self.right_scroll.width()
        compact = panel_width > 0 and panel_width < 380

        layer_labels_normal = {
            "character": "Perso",
            "character2": "2",
            "character3": "3",
            "character4": "4",
            "background": "Fond",
            "logo": "Logo",
        }
        layer_labels_compact = {
            "character": "Perso",
            "character2": "2",
            "character3": "3",
            "character4": "4",
            "background": "BG",
            "logo": "Logo",
        }
        target = layer_labels_compact if compact else layer_labels_normal
        for layer_id, btn in self.layer_buttons.items():
            btn.setText(target.get(layer_id, btn.text()))

    def _build_left_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)

        resources_box = QGroupBox("Ressources")
        resources_layout = QVBoxLayout(resources_box)
        import_box = QGroupBox("Importer")
        import_layout = QVBoxLayout(import_box)
        self.bg_import_btn = QPushButton("Importer Background")
        self.bg_import_btn.clicked.connect(lambda: self._import_layer("background"))
        self.char_import_btn = QPushButton("Importer Perso")
        self.char_import_btn.clicked.connect(lambda: self._import_layer("character"))
        char2_btn = QPushButton("2")
        char2_btn.clicked.connect(lambda: self._import_layer("character2"))
        char3_btn = QPushButton("3")
        char3_btn.clicked.connect(lambda: self._import_layer("character3"))
        char4_btn = QPushButton("4")
        char4_btn.clicked.connect(lambda: self._import_layer("character4"))
        for btn in [char2_btn, char3_btn, char4_btn]:
            btn.setMinimumWidth(40)
            btn.setMaximumWidth(50)
        char_row = QWidget()
        char_row_layout = QHBoxLayout(char_row)
        char_row_layout.setContentsMargins(0, 0, 0, 0)
        char_row_layout.setSpacing(4)
        char_row_layout.addWidget(self.char_import_btn, 1)
        char_row_layout.addWidget(char2_btn)
        char_row_layout.addWidget(char3_btn)
        char_row_layout.addWidget(char4_btn)
        self.logo_import_btn = QPushButton("Importer Logo")
        self.logo_import_btn.clicked.connect(lambda: self._import_layer("logo"))
        import_layout.addWidget(self.bg_import_btn)
        import_layout.addWidget(char_row)
        import_layout.addWidget(self.logo_import_btn)
        self.show_guides_check = QCheckBox("Afficher gabarits (25%)")
        self.show_guides_check.setChecked(self.guides_visible)
        self.show_guides_check.toggled.connect(self._on_guides_visible_toggled)
        import_layout.addWidget(self.show_guides_check)
        self.poster_guide_combo = QComboBox()
        self.poster_guide_combo.addItem("Poster gabarit 1", "1")
        self.poster_guide_combo.addItem("Poster gabarit 2", "2")
        poster_guide_idx = self.poster_guide_combo.findData(self.poster_guide_variant)
        if poster_guide_idx >= 0:
            self.poster_guide_combo.setCurrentIndex(poster_guide_idx)
        self.poster_guide_combo.currentIndexChanged.connect(self._on_poster_guide_variant_changed)
        import_layout.addWidget(QLabel("Choix gabarit poster"))
        import_layout.addWidget(self.poster_guide_combo)
        resources_layout.addWidget(import_box)

        self.logo_text_checkbox = QCheckBox("Logo texte")
        self.logo_text_checkbox.toggled.connect(self._on_logo_text_toggle)
        self.logo_text_input = QPlainTextEdit()
        self.logo_text_input.setPlaceholderText("Texte du logo (retour ligne possible)")
        self.logo_text_input.setFixedHeight(70)
        self.logo_text_input.textChanged.connect(self._on_logo_text_changed)
        self.logo_text_align_combo = QComboBox()
        self.logo_text_align_combo.addItem("Gauche", "left")
        self.logo_text_align_combo.addItem("Centre", "center")
        self.logo_text_align_combo.addItem("Droite", "right")
        self.logo_text_align_combo.currentIndexChanged.connect(self._on_logo_text_align_changed)
        self.logo_text_upper_check = QCheckBox("Majuscule")
        self.logo_text_upper_check.setChecked(self.logo_text_force_upper)
        self.logo_text_upper_check.toggled.connect(self._on_logo_text_upper_toggled)
        self.logo_text_line_spacing_spin = QSpinBox()
        self.logo_text_line_spacing_spin.setRange(50, 300)
        self.logo_text_line_spacing_spin.setSingleStep(5)
        self.logo_text_line_spacing_spin.setSuffix(" %")
        self.logo_text_line_spacing_spin.setValue(self.logo_text_line_spacing)
        self.logo_text_line_spacing_spin.valueChanged.connect(self._on_logo_text_line_spacing_changed)
        self.logo_text_color_btn = QPushButton("Couleur texte")
        self.logo_text_color_btn.clicked.connect(self._pick_logo_color)
        self.poster_textbox_check = QCheckBox("TextBox poster")
        self.poster_textbox_check.setChecked(self.poster_textbox_enabled)
        self.poster_textbox_check.toggled.connect(self._on_poster_textbox_toggled)
        self.poster_textbox_input = QLineEdit(self.poster_textbox_text)
        self.poster_textbox_input.setPlaceholderText("Texte text box (poster)")
        self.poster_textbox_input.textChanged.connect(self._on_poster_textbox_changed)
        
        gradient_cfg = self._gradient_config()

        self.gradient_enable_check = QCheckBox("Activer degrade")
        self.gradient_enable_check.toggled.connect(self._on_gradient_enabled_toggled)
        self.gradient_mode_combo = QComboBox()
        self.gradient_mode_combo.addItem("Couleur unique", "single")
        self.gradient_mode_combo.addItem("Deux couleurs", "double")
        self.gradient_mode_combo.currentIndexChanged.connect(self._on_gradient_mode_changed)
        self.gradient_direction_combo = QComboBox()
        self.gradient_direction_combo.addItem("Haut", "top")
        self.gradient_direction_combo.addItem("Bas", "bottom")
        self.gradient_direction_combo.addItem("Gauche", "left")
        self.gradient_direction_combo.addItem("Droite", "right")
        self.gradient_direction_combo.currentIndexChanged.connect(self._on_gradient_direction_changed)
        self.gradient_distance_slider = QSlider(Qt.Orientation.Horizontal)
        self.gradient_distance_slider.setRange(1, 100)
        self.gradient_distance_slider.setValue(int(gradient_cfg["distance"]))
        self.gradient_distance_slider.sliderPressed.connect(self._push_undo_state)
        self.gradient_distance_slider.valueChanged.connect(self._on_gradient_distance_changed)
        self.gradient_distance_slider.sliderReleased.connect(self._refresh_preview_now)
        self.gradient_distance_label = QLabel()
        self.gradient_distance_label.setMinimumWidth(54)
        gradient_distance_row = QWidget()
        gradient_distance_layout = QHBoxLayout(gradient_distance_row)
        gradient_distance_layout.setContentsMargins(0, 0, 0, 0)
        gradient_distance_layout.addWidget(self.gradient_distance_slider, 1)
        gradient_distance_layout.addWidget(self.gradient_distance_label)

        self.gradient_stretch_slider = QSlider(Qt.Orientation.Horizontal)
        self.gradient_stretch_slider.setRange(20, 300)
        self.gradient_stretch_slider.setValue(int(gradient_cfg["stretch"]))
        self.gradient_stretch_slider.sliderPressed.connect(self._push_undo_state)
        self.gradient_stretch_slider.valueChanged.connect(self._on_gradient_stretch_changed)
        self.gradient_stretch_slider.sliderReleased.connect(self._refresh_preview_now)
        self.gradient_stretch_label = QLabel()
        self.gradient_stretch_label.setMinimumWidth(54)
        gradient_stretch_row = QWidget()
        gradient_stretch_layout = QHBoxLayout(gradient_stretch_row)
        gradient_stretch_layout.setContentsMargins(0, 0, 0, 0)
        gradient_stretch_layout.addWidget(self.gradient_stretch_slider, 1)
        gradient_stretch_layout.addWidget(self.gradient_stretch_label)
        self.gradient_color_a_btn = QPushButton("Couleur degrade A")
        self.gradient_color_a_btn.clicked.connect(self._pick_gradient_color_a)
        self.gradient_color_b_btn = QPushButton("Couleur degrade B")
        self.gradient_color_b_btn.clicked.connect(self._pick_gradient_color_b)

        self.logo_shadow_check = QCheckBox("Ombre portee logo")
        self.logo_shadow_check.toggled.connect(self._on_logo_shadow_toggled)
        self.logo_shadow_distance_slider = QSlider(Qt.Orientation.Horizontal)
        self.logo_shadow_distance_slider.setRange(0, 50)
        self.logo_shadow_distance_slider.setValue(self.logo_shadow_distance)
        self.logo_shadow_distance_slider.sliderPressed.connect(self._push_undo_state)
        self.logo_shadow_distance_slider.valueChanged.connect(self._on_logo_shadow_distance_changed)
        self.logo_shadow_distance_slider.sliderReleased.connect(self._refresh_preview_now)
        self.logo_shadow_distance_label = QLabel()
        self.logo_shadow_distance_label.setMinimumWidth(54)
        distance_row = QWidget()
        distance_layout = QHBoxLayout(distance_row)
        distance_layout.setContentsMargins(0, 0, 0, 0)
        distance_layout.addWidget(self.logo_shadow_distance_slider, 1)
        distance_layout.addWidget(self.logo_shadow_distance_label)

        self.logo_shadow_blur_slider = QSlider(Qt.Orientation.Horizontal)
        self.logo_shadow_blur_slider.setRange(0, 50)
        self.logo_shadow_blur_slider.setValue(self.logo_shadow_blur)
        self.logo_shadow_blur_slider.sliderPressed.connect(self._push_undo_state)
        self.logo_shadow_blur_slider.valueChanged.connect(self._on_logo_shadow_blur_changed)
        self.logo_shadow_blur_slider.sliderReleased.connect(self._refresh_preview_now)
        self.logo_shadow_blur_label = QLabel()
        self.logo_shadow_blur_label.setMinimumWidth(54)
        blur_row = QWidget()
        blur_layout = QHBoxLayout(blur_row)
        blur_layout.setContentsMargins(0, 0, 0, 0)
        blur_layout.addWidget(self.logo_shadow_blur_slider, 1)
        blur_layout.addWidget(self.logo_shadow_blur_label)

        self.logo_shadow_angle_slider = QSlider(Qt.Orientation.Horizontal)
        self.logo_shadow_angle_slider.setRange(0, 359)
        self.logo_shadow_angle_slider.setValue(int(self.logo_shadow_angle) % 360)
        self.logo_shadow_angle_slider.sliderPressed.connect(self._push_undo_state)
        self.logo_shadow_angle_slider.valueChanged.connect(self._on_logo_shadow_angle_changed)
        self.logo_shadow_angle_slider.sliderReleased.connect(self._refresh_preview_now)
        self.logo_shadow_angle_label = QLabel()
        self.logo_shadow_angle_label.setMinimumWidth(54)
        angle_row = QWidget()
        angle_layout = QHBoxLayout(angle_row)
        angle_layout.setContentsMargins(0, 0, 0, 0)
        angle_layout.addWidget(self.logo_shadow_angle_slider, 1)
        angle_layout.addWidget(self.logo_shadow_angle_label)
        self.logo_shadow_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.logo_shadow_opacity_slider.setRange(0, 100)
        self.logo_shadow_opacity_slider.setValue(self.logo_shadow_opacity)
        self.logo_shadow_opacity_slider.sliderPressed.connect(self._push_undo_state)
        self.logo_shadow_opacity_slider.valueChanged.connect(self._on_logo_shadow_opacity_changed)
        self.logo_shadow_opacity_slider.sliderReleased.connect(self._refresh_preview_now)
        self.logo_shadow_opacity_label = QLabel()
        self.logo_shadow_opacity_label.setMinimumWidth(54)
        shadow_opacity_row = QWidget()
        shadow_opacity_layout = QHBoxLayout(shadow_opacity_row)
        shadow_opacity_layout.setContentsMargins(0, 0, 0, 0)
        shadow_opacity_layout.addWidget(self.logo_shadow_opacity_slider, 1)
        shadow_opacity_layout.addWidget(self.logo_shadow_opacity_label)
        self.logo_shadow_color_btn = QPushButton("Couleur ombre")
        self.logo_shadow_color_btn.clicked.connect(self._pick_logo_shadow_color)

        text_box = QGroupBox("Texte")
        text_layout = QVBoxLayout(text_box)
        text_form = QFormLayout()
        text_form.addRow(self.logo_text_checkbox)
        text_form.addRow("Contenu", self.logo_text_input)
        text_form.addRow("Alignement", self.logo_text_align_combo)
        text_form.addRow(self.logo_text_upper_check)
        text_form.addRow("Interligne (%)", self.logo_text_line_spacing_spin)
        text_form.addRow(self.logo_text_color_btn)
        text_layout.addLayout(text_form)
        resources_layout.addWidget(text_box)

        textbox_box = QGroupBox("TextBox poster")
        textbox_layout = QVBoxLayout(textbox_box)
        textbox_form = QFormLayout()
        textbox_form.addRow(self.poster_textbox_check)
        textbox_form.addRow("Textebox", self.poster_textbox_input)
        textbox_layout.addLayout(textbox_form)
        resources_layout.addWidget(textbox_box)

        shadow_box = QGroupBox("Ombre")
        shadow_layout = QVBoxLayout(shadow_box)
        shadow_form = QFormLayout()
        shadow_form.addRow(self.logo_shadow_check)
        shadow_form.addRow("Distance", distance_row)
        shadow_form.addRow("Lissage", blur_row)
        shadow_form.addRow("Angle", angle_row)
        shadow_form.addRow("Opacite", shadow_opacity_row)
        shadow_layout.addLayout(shadow_form)
        shadow_layout.addWidget(self.logo_shadow_color_btn)
        resources_layout.addWidget(shadow_box)

        gradient_box = QGroupBox("Degrade")
        gradient_layout = QVBoxLayout(gradient_box)
        gradient_form = QFormLayout()
        gradient_form.addRow(self.gradient_enable_check)
        gradient_form.addRow("Mode", self.gradient_mode_combo)
        gradient_form.addRow("Direction", self.gradient_direction_combo)
        gradient_form.addRow("Distance", gradient_distance_row)
        gradient_form.addRow("Etirement", gradient_stretch_row)
        gradient_layout.addLayout(gradient_form)
        gradient_layout.addWidget(self.gradient_color_a_btn)
        gradient_layout.addWidget(self.gradient_color_b_btn)
        resources_layout.addWidget(gradient_box)
        self._sync_gradient_controls()
        self._sync_poster_textbox_controls()
        self._update_shadow_slider_labels()

        layout.addWidget(resources_box)

        layer_box = QGroupBox("Contrôles de calque")
        layer_layout = QFormLayout(layer_box)
        layer_buttons_top_row = QHBoxLayout()
        layer_buttons_top_row.setContentsMargins(0, 0, 0, 0)
        layer_buttons_top_row.setSpacing(6)
        layer_buttons_bottom_row = QHBoxLayout()
        layer_buttons_bottom_row.setContentsMargins(0, 0, 0, 0)
        layer_buttons_bottom_row.setSpacing(6)
        self.layer_buttons: Dict[str, QPushButton] = {}
        layer_labels = {
            "character": "Perso",
            "character2": "2",
            "character3": "3",
            "character4": "4",
            "background": "Fond",
            "logo": "Logo",
        }
        for layer in CONTROL_LAYER_ORDER:
            label = layer_labels[layer]
            btn = QPushButton(label)
            btn.setCheckable(True)
            if layer in EXTRA_CHARACTER_LAYERS:
                btn.setMinimumWidth(36)
                btn.setMaximumWidth(50)
                btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
                stretch = 0
            else:
                btn.setMinimumWidth(68)
                btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                stretch = 1
            btn.clicked.connect(lambda _checked, lid=layer: self._set_active_layer(lid))
            self.layer_buttons[layer] = btn
            target_row = layer_buttons_bottom_row if layer in {"background", "logo"} else layer_buttons_top_row
            target_row.addWidget(btn, stretch)
        layer_buttons_widget = QWidget()
        layer_buttons_col = QVBoxLayout(layer_buttons_widget)
        layer_buttons_col.setContentsMargins(0, 0, 0, 0)
        layer_buttons_col.setSpacing(4)
        layer_buttons_col.addLayout(layer_buttons_top_row)
        layer_buttons_col.addLayout(layer_buttons_bottom_row)

        self.visible_check = QCheckBox("Visible")
        self.visible_check.setChecked(True)
        self.visible_check.toggled.connect(self._on_visible_changed)

        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.sliderPressed.connect(self._push_undo_state)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        self.opacity_slider.sliderReleased.connect(self._refresh_preview_now)
        self.opacity_value_label = QLabel("100")
        self.opacity_value_label.setMinimumWidth(36)
        opacity_row = QWidget()
        opacity_layout = QHBoxLayout(opacity_row)
        opacity_layout.setContentsMargins(0, 0, 0, 0)
        opacity_layout.addWidget(self.opacity_slider, 1)
        opacity_layout.addWidget(self.opacity_value_label)

        self.scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.scale_slider.setRange(0, 300)
        self.scale_slider.setValue(300)
        self.scale_slider.sliderPressed.connect(self._push_undo_state)
        self.scale_slider.valueChanged.connect(self._on_scale_changed)
        self.scale_slider.sliderReleased.connect(self._refresh_preview_now)
        self.scale_value_label = QLabel("300")
        self.scale_value_label.setMinimumWidth(36)
        scale_row = QWidget()
        scale_layout = QHBoxLayout(scale_row)
        scale_layout.setContentsMargins(0, 0, 0, 0)
        scale_layout.addWidget(self.scale_slider, 1)
        scale_layout.addWidget(self.scale_value_label)

        reset_btn = QPushButton("Réinitialiser le calque")
        center_btn = QPushButton("Centrer le calque")
        center_btn.clicked.connect(self._on_center_layer)
        reset_btn.clicked.connect(self._on_reset_layer)

        layer_layout.addRow("Calque", layer_buttons_widget)
        layer_layout.addRow(self.visible_check)
        layer_layout.addRow("Opacite", opacity_row)
        layer_layout.addRow("Echelle", scale_row)
        layer_layout.addRow(center_btn)
        layer_layout.addRow(reset_btn)
        self._set_active_layer(self.active_layer, sync=False)
        layout.addWidget(layer_box)
        layout.addStretch(1)
        self._apply_compact_ui_labels()
        return panel

    def _build_right_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)

        exports = QGroupBox("Exports")
        exports_layout = QVBoxLayout(exports)
        self.export_list = QListWidget()
        for export_id, meta in EXPORT_TARGETS.items():
            item = QListWidgetItem(meta["label"])
            item.setData(Qt.ItemDataRole.UserRole, export_id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.export_list.addItem(item)
        exports_layout.addWidget(self.export_list)

        self.export_dir = QLineEdit(str(self._recent_dir("export")))
        self.export_dir_btn = QPushButton("Dossier d'export")
        self.export_dir_btn.clicked.connect(self._select_export_dir)
        self.metadata_id_input = QLineEdit()
        self.metadata_id_input.setPlaceholderText("Numero ID")
        self.base_name_input = QLineEdit("Name")
        self.save_project_btn = QPushButton("Sauvegarde projet...")
        self.save_project_btn.clicked.connect(self._save_project_snapshot_as)
        self.new_project_btn = QPushButton("Nouveau projet")
        self.new_project_btn.clicked.connect(self._new_project)

        self.export_btn = QPushButton("Exporter")
        self.export_btn.clicked.connect(self._export_selected)

        self.progress = QProgressBar()

        exports_layout.addWidget(QLabel("Dossier"))
        exports_layout.addWidget(self.export_dir)
        exports_layout.addWidget(self.export_dir_btn)
        exports_layout.addWidget(QLabel("ID"))
        exports_layout.addWidget(self.metadata_id_input)
        exports_layout.addWidget(QLabel("Nom de base"))
        exports_layout.addWidget(self.base_name_input)
        exports_layout.addWidget(self.save_project_btn)
        exports_layout.addWidget(self.new_project_btn)
        exports_layout.addWidget(self.export_btn)
        exports_layout.addWidget(self.progress)

        layout.addWidget(exports)
        return panel

    def _build_import_button(self, label: str, layer_id: str, tooltip: str = ""):
        btn = QPushButton(label)
        btn.clicked.connect(lambda: self._import_layer(layer_id))
        btn.setMinimumHeight(38)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if tooltip:
            btn.setToolTip(tooltip)
        btn.setStyleSheet(
            """
            QPushButton {
                background-color: #0B5FA6;
                color: white;
                border: 1px solid #084A82;
                border-radius: 8px;
                font-weight: 600;
                padding: 8px 12px;
            }
            QPushButton:hover {
                background-color: #1374C7;
            }
            QPushButton:pressed {
                background-color: #084A82;
            }
            """
        )
        return btn

    def _build_import_toolbar_separator(self):
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Plain)
        separator.setLineWidth(1)
        separator.setMidLineWidth(0)
        separator.setStyleSheet("color: #3A3A42; background-color: #3A3A42;")
        separator.setFixedHeight(26)
        return separator

    def _build_import_toolbar(self):
        toolbar = QWidget()
        row = QHBoxLayout(toolbar)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        self.bg_import_btn = self._build_import_button(
            "Importer fond",
            "background",
            "Importer le fond principal",
        )
        self.char_import_btn = self._build_import_button(
            "Importer perso",
            "character",
            "Importer le personnage principal",
        )
        char2_btn = self._build_import_button("2", "character2", "Importer le personnage 2")
        char3_btn = self._build_import_button("3", "character3", "Importer le personnage 3")
        char4_btn = self._build_import_button("4", "character4", "Importer le personnage 4")
        self.logo_import_btn = self._build_import_button(
            "Importer logo",
            "logo",
            "Importer le logo",
        )

        for btn in [char2_btn, char3_btn, char4_btn]:
            btn.setMinimumWidth(46)
            btn.setMaximumWidth(56)

        row.addWidget(self.bg_import_btn, 2)
        row.addWidget(self._build_import_toolbar_separator())
        row.addWidget(self.char_import_btn, 2)
        row.addWidget(char2_btn)
        row.addWidget(char3_btn)
        row.addWidget(char4_btn)
        row.addWidget(self._build_import_toolbar_separator())
        row.addWidget(self.logo_import_btn, 2)
        return toolbar

    def _build_guides_manager_box(self):
        guides_box = QGroupBox("Gestionnaire des gabarits")
        guides_layout = QVBoxLayout(guides_box)
        guide_form = QFormLayout()

        self.show_guides_check = QCheckBox("Afficher gabarits (25%)")
        self.show_guides_check.setChecked(self.guides_visible)
        self.show_guides_check.toggled.connect(self._on_guides_visible_toggled)

        self.poster_guide_combo = QComboBox()
        self.poster_guide_combo.addItem("Poster gabarit 1", "1")
        self.poster_guide_combo.addItem("Poster gabarit 2", "2")
        poster_guide_idx = self.poster_guide_combo.findData(self.poster_guide_variant)
        if poster_guide_idx >= 0:
            self.poster_guide_combo.setCurrentIndex(poster_guide_idx)
        self.poster_guide_combo.currentIndexChanged.connect(self._on_poster_guide_variant_changed)

        guide_form.addRow(self.show_guides_check)
        guide_form.addRow("Gabarit poster", self.poster_guide_combo)
        guides_layout.addLayout(guide_form)
        return guides_box

    def _build_logo_text_box(self):
        self.logo_text_checkbox = QCheckBox("Logo texte")
        self.logo_text_checkbox.toggled.connect(self._on_logo_text_toggle)
        self.logo_text_input = QPlainTextEdit()
        self.logo_text_input.setPlaceholderText("Texte du logo (retour ligne possible)")
        self.logo_text_input.setFixedHeight(70)
        self.logo_text_input.textChanged.connect(self._on_logo_text_changed)
        self.logo_text_align_combo = QComboBox()
        self.logo_text_align_combo.addItem("Gauche", "left")
        self.logo_text_align_combo.addItem("Centre", "center")
        self.logo_text_align_combo.addItem("Droite", "right")
        self.logo_text_align_combo.currentIndexChanged.connect(self._on_logo_text_align_changed)
        self.logo_text_upper_check = QCheckBox("Majuscule")
        self.logo_text_upper_check.setChecked(self.logo_text_force_upper)
        self.logo_text_upper_check.toggled.connect(self._on_logo_text_upper_toggled)
        self.logo_text_line_spacing_spin = QSpinBox()
        self.logo_text_line_spacing_spin.setRange(50, 300)
        self.logo_text_line_spacing_spin.setSingleStep(5)
        self.logo_text_line_spacing_spin.setSuffix(" %")
        self.logo_text_line_spacing_spin.setValue(self.logo_text_line_spacing)
        self.logo_text_line_spacing_spin.valueChanged.connect(self._on_logo_text_line_spacing_changed)
        self.logo_text_color_btn = QPushButton("Couleur texte")
        self.logo_text_color_btn.clicked.connect(self._pick_logo_color)
        self.logo_font_value_label = QLabel(self._logo_font_status_text())
        self.logo_font_value_label.setWordWrap(True)
        self.logo_font_pick_btn = QPushButton("Choisir typo")
        self.logo_font_pick_btn.clicked.connect(self._choose_logo_font)
        self.logo_font_dafont_btn = QPushButton("Ajouter typo")
        self.logo_font_dafont_btn.clicked.connect(self._add_logo_font_from_dafont)
        self.logo_font_default_btn = QPushButton("Police par defaut")
        self.logo_font_default_btn.clicked.connect(self._reset_logo_font_selection)
        font_buttons_row = QWidget()
        font_buttons_layout = QGridLayout(font_buttons_row)
        font_buttons_layout.setContentsMargins(0, 0, 0, 0)
        font_buttons_layout.setHorizontalSpacing(6)
        font_buttons_layout.setVerticalSpacing(6)
        font_buttons_layout.setColumnStretch(0, 1)
        font_buttons_layout.setColumnStretch(1, 1)
        for btn in [self.logo_font_pick_btn, self.logo_font_dafont_btn, self.logo_font_default_btn]:
            btn.setMinimumHeight(28)
        font_buttons_layout.addWidget(self.logo_font_pick_btn, 0, 0)
        font_buttons_layout.addWidget(self.logo_font_dafont_btn, 0, 1)
        font_buttons_layout.addWidget(self.logo_font_default_btn, 1, 0, 1, 2)
        font_row = QWidget()
        font_row_layout = QVBoxLayout(font_row)
        font_row_layout.setContentsMargins(0, 0, 0, 0)
        font_row_layout.setSpacing(6)
        font_row_layout.addWidget(self.logo_font_value_label)
        font_row_layout.addWidget(font_buttons_row)

        text_box = QGroupBox("Texte logo")
        text_layout = QVBoxLayout(text_box)
        text_form = QFormLayout()
        text_form.addRow(self.logo_text_checkbox)
        text_form.addRow("Contenu", self.logo_text_input)
        text_form.addRow("Alignement", self.logo_text_align_combo)
        text_form.addRow(self.logo_text_upper_check)
        text_form.addRow("Interligne (%)", self.logo_text_line_spacing_spin)
        text_form.addRow(self.logo_text_color_btn)
        text_form.addRow("Typo", font_row)
        text_layout.addLayout(text_form)
        return text_box

    def _build_top_value_row(self, min_value: int, max_value: int, value: int, step: int, handler):
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(6)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(min_value, max_value)
        slider.setValue(value)
        spin = QSpinBox()
        spin.setRange(min_value, max_value)
        spin.setValue(value)
        spin.setSingleStep(step)
        slider.valueChanged.connect(spin.setValue)
        spin.valueChanged.connect(slider.setValue)
        slider.sliderPressed.connect(self._push_undo_state)
        slider.valueChanged.connect(handler)
        spin.valueChanged.connect(handler)
        row_layout.addWidget(slider, 1)
        row_layout.addWidget(spin)
        return slider, spin, row_widget

    def _build_top_box(self):
        base_config = self._top_config(TOP_PRESET_IDS[0])
        self.top_sync_check = QCheckBox("Appliquer a tous les TOP")
        self.top_sync_check.setChecked(self.top_sync_all)
        self.top_sync_check.toggled.connect(self._on_top_sync_all_toggled)

        self.top_offset_x_slider, self.top_offset_x_spin, offset_x_row = self._build_top_value_row(
            -5000,
            5000,
            int(base_config["offset_x"]),
            10,
            self._on_top_offset_x_changed,
        )
        self.top_offset_y_slider, self.top_offset_y_spin, offset_y_row = self._build_top_value_row(
            -5000,
            5000,
            int(base_config["offset_y"]),
            10,
            self._on_top_offset_y_changed,
        )
        self.top_zoom_slider, self.top_zoom_spin, zoom_row = self._build_top_value_row(
            10,
            400,
            int(base_config["zoom"]),
            5,
            self._on_top_zoom_changed,
        )
        self.top_stretch_x_slider, self.top_stretch_x_spin, stretch_x_row = self._build_top_value_row(
            10,
            400,
            int(base_config["stretch_x"]),
            5,
            self._on_top_stretch_x_changed,
        )
        self.top_stretch_y_slider, self.top_stretch_y_spin, stretch_y_row = self._build_top_value_row(
            10,
            400,
            int(base_config["stretch_y"]),
            5,
            self._on_top_stretch_y_changed,
        )
        self.top_reset_btn = QPushButton("Reinitialiser TOP")
        self.top_reset_btn.clicked.connect(self._reset_current_top_config)

        top_box = QGroupBox("TOP poster")
        top_layout = QVBoxLayout(top_box)
        top_form = QFormLayout()
        top_form.addRow(self.top_sync_check)
        top_form.addRow("Offset X", offset_x_row)
        top_form.addRow("Offset Y", offset_y_row)
        top_form.addRow("Zoom %", zoom_row)
        top_form.addRow("Stretch X %", stretch_x_row)
        top_form.addRow("Stretch Y %", stretch_y_row)
        top_layout.addLayout(top_form)
        top_layout.addWidget(self.top_reset_btn)
        return top_box

    def _build_poster_textbox_box(self):
        self.poster_textbox_check = QCheckBox("TextBox poster")
        self.poster_textbox_check.setChecked(self.poster_textbox_enabled)
        self.poster_textbox_check.toggled.connect(self._on_poster_textbox_toggled)
        self.poster_textbox_input = QLineEdit(self.poster_textbox_text)
        self.poster_textbox_input.setPlaceholderText("Texte text box (poster)")
        self.poster_textbox_input.textChanged.connect(self._on_poster_textbox_changed)

        textbox_box = QGroupBox("TextBox poster")
        textbox_layout = QVBoxLayout(textbox_box)
        textbox_form = QFormLayout()
        textbox_form.addRow(self.poster_textbox_check)
        textbox_form.addRow("Textebox", self.poster_textbox_input)
        textbox_layout.addLayout(textbox_form)
        return textbox_box

    def _build_gradient_box(self):
        gradient_cfg = self._gradient_config()

        self.gradient_enable_check = QCheckBox("Activer degrade")
        self.gradient_enable_check.toggled.connect(self._on_gradient_enabled_toggled)
        self.gradient_mode_combo = QComboBox()
        self.gradient_mode_combo.addItem("Couleur unique", "single")
        self.gradient_mode_combo.addItem("Deux couleurs", "double")
        self.gradient_mode_combo.currentIndexChanged.connect(self._on_gradient_mode_changed)
        self.gradient_direction_combo = QComboBox()
        self.gradient_direction_combo.addItem("Haut", "top")
        self.gradient_direction_combo.addItem("Bas", "bottom")
        self.gradient_direction_combo.addItem("Gauche", "left")
        self.gradient_direction_combo.addItem("Droite", "right")
        self.gradient_direction_combo.currentIndexChanged.connect(self._on_gradient_direction_changed)
        self.gradient_distance_slider = QSlider(Qt.Orientation.Horizontal)
        self.gradient_distance_slider.setRange(1, 100)
        self.gradient_distance_slider.setValue(int(gradient_cfg["distance"]))
        self.gradient_distance_slider.valueChanged.connect(self._on_gradient_distance_changed)
        self.gradient_distance_slider.sliderReleased.connect(self._refresh_preview_now)
        self.gradient_distance_label = QLabel()
        self.gradient_distance_label.setMinimumWidth(54)
        gradient_distance_row = QWidget()
        gradient_distance_layout = QHBoxLayout(gradient_distance_row)
        gradient_distance_layout.setContentsMargins(0, 0, 0, 0)
        gradient_distance_layout.addWidget(self.gradient_distance_slider, 1)
        gradient_distance_layout.addWidget(self.gradient_distance_label)

        self.gradient_stretch_slider = QSlider(Qt.Orientation.Horizontal)
        self.gradient_stretch_slider.setRange(20, 300)
        self.gradient_stretch_slider.setValue(int(gradient_cfg["stretch"]))
        self.gradient_stretch_slider.valueChanged.connect(self._on_gradient_stretch_changed)
        self.gradient_stretch_slider.sliderReleased.connect(self._refresh_preview_now)
        self.gradient_stretch_label = QLabel()
        self.gradient_stretch_label.setMinimumWidth(54)
        gradient_stretch_row = QWidget()
        gradient_stretch_layout = QHBoxLayout(gradient_stretch_row)
        gradient_stretch_layout.setContentsMargins(0, 0, 0, 0)
        gradient_stretch_layout.addWidget(self.gradient_stretch_slider, 1)
        gradient_stretch_layout.addWidget(self.gradient_stretch_label)

        self.gradient_color_a_btn = QPushButton("Couleur degrade A")
        self.gradient_color_a_btn.clicked.connect(self._pick_gradient_color_a)
        self.gradient_color_b_btn = QPushButton("Couleur degrade B")
        self.gradient_color_b_btn.clicked.connect(self._pick_gradient_color_b)

        gradient_box = QGroupBox("Degrade")
        gradient_layout = QVBoxLayout(gradient_box)
        gradient_form = QFormLayout()
        gradient_form.addRow(self.gradient_enable_check)
        gradient_form.addRow("Mode", self.gradient_mode_combo)
        gradient_form.addRow("Direction", self.gradient_direction_combo)
        gradient_form.addRow("Distance", gradient_distance_row)
        gradient_form.addRow("Etirement", gradient_stretch_row)
        gradient_layout.addLayout(gradient_form)
        gradient_layout.addWidget(self.gradient_color_a_btn)
        gradient_layout.addWidget(self.gradient_color_b_btn)
        return gradient_box

    def _build_shadow_box(self):
        self.logo_shadow_check = QCheckBox("Ombre portee logo")
        self.logo_shadow_check.toggled.connect(self._on_logo_shadow_toggled)
        self.logo_shadow_distance_slider = QSlider(Qt.Orientation.Horizontal)
        self.logo_shadow_distance_slider.setRange(0, 50)
        self.logo_shadow_distance_slider.setValue(self.logo_shadow_distance)
        self.logo_shadow_distance_slider.valueChanged.connect(self._on_logo_shadow_distance_changed)
        self.logo_shadow_distance_slider.sliderReleased.connect(self._refresh_preview_now)
        self.logo_shadow_distance_label = QLabel()
        self.logo_shadow_distance_label.setMinimumWidth(54)
        distance_row = QWidget()
        distance_layout = QHBoxLayout(distance_row)
        distance_layout.setContentsMargins(0, 0, 0, 0)
        distance_layout.addWidget(self.logo_shadow_distance_slider, 1)
        distance_layout.addWidget(self.logo_shadow_distance_label)

        self.logo_shadow_blur_slider = QSlider(Qt.Orientation.Horizontal)
        self.logo_shadow_blur_slider.setRange(0, 50)
        self.logo_shadow_blur_slider.setValue(self.logo_shadow_blur)
        self.logo_shadow_blur_slider.valueChanged.connect(self._on_logo_shadow_blur_changed)
        self.logo_shadow_blur_slider.sliderReleased.connect(self._refresh_preview_now)
        self.logo_shadow_blur_label = QLabel()
        self.logo_shadow_blur_label.setMinimumWidth(54)
        blur_row = QWidget()
        blur_layout = QHBoxLayout(blur_row)
        blur_layout.setContentsMargins(0, 0, 0, 0)
        blur_layout.addWidget(self.logo_shadow_blur_slider, 1)
        blur_layout.addWidget(self.logo_shadow_blur_label)

        self.logo_shadow_angle_slider = QSlider(Qt.Orientation.Horizontal)
        self.logo_shadow_angle_slider.setRange(0, 359)
        self.logo_shadow_angle_slider.setValue(int(self.logo_shadow_angle) % 360)
        self.logo_shadow_angle_slider.valueChanged.connect(self._on_logo_shadow_angle_changed)
        self.logo_shadow_angle_slider.sliderReleased.connect(self._refresh_preview_now)
        self.logo_shadow_angle_label = QLabel()
        self.logo_shadow_angle_label.setMinimumWidth(54)
        angle_row = QWidget()
        angle_layout = QHBoxLayout(angle_row)
        angle_layout.setContentsMargins(0, 0, 0, 0)
        angle_layout.addWidget(self.logo_shadow_angle_slider, 1)
        angle_layout.addWidget(self.logo_shadow_angle_label)

        self.logo_shadow_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.logo_shadow_opacity_slider.setRange(0, 100)
        self.logo_shadow_opacity_slider.setValue(self.logo_shadow_opacity)
        self.logo_shadow_opacity_slider.valueChanged.connect(self._on_logo_shadow_opacity_changed)
        self.logo_shadow_opacity_slider.sliderReleased.connect(self._refresh_preview_now)
        self.logo_shadow_opacity_label = QLabel()
        self.logo_shadow_opacity_label.setMinimumWidth(54)
        shadow_opacity_row = QWidget()
        shadow_opacity_layout = QHBoxLayout(shadow_opacity_row)
        shadow_opacity_layout.setContentsMargins(0, 0, 0, 0)
        shadow_opacity_layout.addWidget(self.logo_shadow_opacity_slider, 1)
        shadow_opacity_layout.addWidget(self.logo_shadow_opacity_label)

        self.logo_shadow_color_btn = QPushButton("Couleur ombre")
        self.logo_shadow_color_btn.clicked.connect(self._pick_logo_shadow_color)

        shadow_box = QGroupBox("Ombre logo")
        shadow_layout = QVBoxLayout(shadow_box)
        shadow_form = QFormLayout()
        shadow_form.addRow(self.logo_shadow_check)
        shadow_form.addRow("Distance", distance_row)
        shadow_form.addRow("Lissage", blur_row)
        shadow_form.addRow("Angle", angle_row)
        shadow_form.addRow("Opacite", shadow_opacity_row)
        shadow_layout.addLayout(shadow_form)
        shadow_layout.addWidget(self.logo_shadow_color_btn)
        return shadow_box

    def _build_layer_controls_box(self):
        layer_box = QGroupBox("Controles de calque")
        layer_layout = QFormLayout(layer_box)
        layer_buttons_top_row = QHBoxLayout()
        layer_buttons_top_row.setContentsMargins(0, 0, 0, 0)
        layer_buttons_top_row.setSpacing(6)
        layer_buttons_bottom_row = QHBoxLayout()
        layer_buttons_bottom_row.setContentsMargins(0, 0, 0, 0)
        layer_buttons_bottom_row.setSpacing(6)
        self.layer_buttons: Dict[str, QPushButton] = {}
        layer_labels = {
            "character": "Perso",
            "character2": "2",
            "character3": "3",
            "character4": "4",
            "background": "Fond",
            "logo": "Logo",
        }
        for layer in CONTROL_LAYER_ORDER:
            label = layer_labels[layer]
            btn = QPushButton(label)
            btn.setCheckable(True)
            if layer in EXTRA_CHARACTER_LAYERS:
                btn.setMinimumWidth(36)
                btn.setMaximumWidth(50)
                btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
                stretch = 0
            else:
                btn.setMinimumWidth(68)
                btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                stretch = 1
            btn.clicked.connect(lambda _checked, lid=layer: self._set_active_layer(lid))
            self.layer_buttons[layer] = btn
            target_row = layer_buttons_bottom_row if layer in {"background", "logo"} else layer_buttons_top_row
            target_row.addWidget(btn, stretch)

        layer_buttons_widget = QWidget()
        layer_buttons_col = QVBoxLayout(layer_buttons_widget)
        layer_buttons_col.setContentsMargins(0, 0, 0, 0)
        layer_buttons_col.setSpacing(4)
        layer_buttons_col.addLayout(layer_buttons_top_row)
        layer_buttons_col.addLayout(layer_buttons_bottom_row)

        self.visible_check = QCheckBox("Visible")
        self.visible_check.setChecked(True)
        self.visible_check.toggled.connect(self._on_visible_changed)

        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        self.opacity_slider.sliderReleased.connect(self._refresh_preview_now)
        self.opacity_value_label = QLabel("100")
        self.opacity_value_label.setMinimumWidth(36)
        opacity_row = QWidget()
        opacity_layout = QHBoxLayout(opacity_row)
        opacity_layout.setContentsMargins(0, 0, 0, 0)
        opacity_layout.addWidget(self.opacity_slider, 1)
        opacity_layout.addWidget(self.opacity_value_label)

        self.scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.scale_slider.setRange(0, 300)
        self.scale_slider.setValue(300)
        self.scale_slider.valueChanged.connect(self._on_scale_changed)
        self.scale_slider.sliderReleased.connect(self._refresh_preview_now)
        self.scale_value_label = QLabel("300")
        self.scale_value_label.setMinimumWidth(36)
        scale_row = QWidget()
        scale_layout = QHBoxLayout(scale_row)
        scale_layout.setContentsMargins(0, 0, 0, 0)
        scale_layout.addWidget(self.scale_slider, 1)
        scale_layout.addWidget(self.scale_value_label)

        self.reset_layer_btn = QPushButton("Reinitialiser le calque")
        self.center_layer_btn = QPushButton("Centrer le calque")
        self.center_layer_btn.clicked.connect(self._on_center_layer)
        self.reset_layer_btn.clicked.connect(self._on_reset_layer)

        layer_layout.addRow("Calque", layer_buttons_widget)
        layer_layout.addRow(self.visible_check)
        layer_layout.addRow("Opacite", opacity_row)
        layer_layout.addRow("Echelle", scale_row)
        layer_layout.addRow(self.center_layer_btn)
        layer_layout.addRow(self.reset_layer_btn)
        self._set_active_layer(self.active_layer, sync=False)
        return layer_box

    def _build_exports_box(self):
        exports = QGroupBox("Exports")
        exports_layout = QVBoxLayout(exports)
        exports_grid_widget = QWidget()
        exports_grid = QGridLayout(exports_grid_widget)
        exports_grid.setContentsMargins(0, 0, 0, 0)
        exports_grid.setHorizontalSpacing(12)
        exports_grid.setVerticalSpacing(6)
        exports_grid.setColumnStretch(0, 1)
        exports_grid.setColumnStretch(1, 1)
        self.export_checks: Dict[str, QCheckBox] = {}
        for index, (export_id, meta) in enumerate(EXPORT_TARGETS.items()):
            check = QCheckBox(meta["label"])
            check.setChecked(True)
            self.export_checks[export_id] = check
            exports_grid.addWidget(check, index // 2, index % 2)
        exports_layout.addWidget(exports_grid_widget)

        self.export_dir = QLineEdit(str(Path.cwd() / "exports"))
        self.export_dir_btn = QPushButton("Dossier d'export")
        self.export_dir_btn.clicked.connect(self._select_export_dir)
        self.metadata_id_input = QLineEdit()
        self.metadata_id_input.setPlaceholderText("Numero ID")
        self.base_name_input = QLineEdit("Name")
        self.load_project_btn = QPushButton("Importer projet...")
        self.load_project_btn.clicked.connect(self._load_project_snapshot_from_dialog)
        self.save_project_btn = QPushButton("Sauvegarde projet...")
        self.save_project_btn.clicked.connect(self._save_project_snapshot_as)
        self.new_project_btn = QPushButton("Nouveau projet")
        self.new_project_btn.clicked.connect(self._new_project)

        self.export_btn = QPushButton("Exporter")
        self.export_btn.clicked.connect(self._export_selected)

        self.progress = QProgressBar()

        exports_layout.addWidget(QLabel("Dossier"))
        exports_layout.addWidget(self.export_dir)
        exports_layout.addWidget(self.export_dir_btn)
        exports_layout.addWidget(QLabel("ID"))
        exports_layout.addWidget(self.metadata_id_input)
        exports_layout.addWidget(QLabel("Nom de base"))
        exports_layout.addWidget(self.base_name_input)
        exports_layout.addWidget(self.load_project_btn)
        exports_layout.addWidget(self.save_project_btn)
        exports_layout.addWidget(self.new_project_btn)
        exports_layout.addWidget(self.export_btn)
        exports_layout.addWidget(self.progress)
        return exports

    def _build_left_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.addWidget(self._build_guides_manager_box())
        layout.addWidget(self._build_top_box())
        layout.addWidget(self._build_logo_text_box())
        layout.addWidget(self._build_shadow_box())
        layout.addWidget(self._build_poster_textbox_box())
        layout.addWidget(self._build_gradient_box())
        layout.addStretch(1)
        self._sync_logo_controls()
        self._sync_gradient_controls()
        self._sync_poster_textbox_controls()
        self._sync_top_controls()
        self._update_shadow_slider_labels()
        return panel

    def _build_right_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.addWidget(self._build_layer_controls_box())
        layout.addWidget(self._build_exports_box())
        layout.addStretch(1)
        return panel

    def _build_presets_preview_strip(self):
        box = QGroupBox("Apercu des gabarits")
        box_layout = QVBoxLayout(box)
        self.presets_preview_scroll = QScrollArea()
        self.presets_preview_scroll.setWidgetResizable(True)
        self.presets_preview_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.presets_preview_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(8, 8, 8, 8)
        row.setSpacing(12)
        self.preset_preview_labels: Dict[str, QLabel] = {}

        for preset_id, meta in PRESETS.items():
            card = QWidget()
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(0, 0, 0, 0)
            card_layout.setSpacing(4)
            thumb = PresetPreviewLabel(preset_id, "...")
            thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            thumb.setFixedSize(self.presets_preview_box_width, self.presets_preview_box_height)
            thumb.setStyleSheet("border: 1px solid #5E5E66; background-color: #1F1F24;")
            thumb.clicked.connect(self._on_preset_preview_clicked)
            title = PresetPreviewLabel(preset_id, meta["label"])
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            title.clicked.connect(self._on_preset_preview_clicked)
            card_layout.addWidget(thumb)
            card_layout.addWidget(title)
            row.addWidget(card)
            self.preset_preview_labels[preset_id] = thumb

        row.addStretch(1)
        self.presets_preview_scroll.setWidget(container)
        box_layout.addWidget(self.presets_preview_scroll)
        return box

    def _set_scene_for_preset(self, preset_id: str):
        width, height = PRESETS[preset_id]["size"]
        self.scene.setSceneRect(0, 0, width, height)
        self.clip_item.setRect(0, 0, width, height)
        self.frame_item.setRect(0, 0, width, height)
        self._fit_view_to_scene()

    def _fit_view_to_scene(self):
        scene_rect = self.scene.sceneRect()
        if scene_rect.width() <= 0 or scene_rect.height() <= 0:
            return
        self.view.resetTransform()
        self.view.fitInView(scene_rect, Qt.AspectRatioMode.KeepAspectRatio)
        self.view.centerOn(scene_rect.center())

    def showEvent(self, event):
        super().showEvent(event)
        self._fit_view_to_scene()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_responsive_side_widths()
        self._fit_view_to_scene()

    def closeEvent(self, event):
        try:
            base_name = self._sanitize_base_name(self.base_name_input.text())
            self._autosave_project_snapshot(f"{base_name}-exit")
        except Exception:
            pass
        super().closeEvent(event)

    def _selected_layer(self) -> str:
        return self.active_layer

    def _layer_state(self, preset_id: str, layer_id: str):
        return self.state[preset_id][layer_id]

    def _log(self, message: str):
        _ = message

    def _schedule_live_preview_refresh(self):
        self.live_refresh_pending = True
        if hasattr(self, "live_refresh_timer"):
            self.live_refresh_timer.start(self.live_refresh_interval_ms)

    def _flush_live_preview_refresh(self):
        if not self.live_refresh_pending:
            return
        self.live_refresh_pending = False
        self._refresh_preview()

    def _refresh_preview_now(self):
        self.live_refresh_pending = False
        if hasattr(self, "live_refresh_timer"):
            self.live_refresh_timer.stop()
        self._refresh_preview()

    def _schedule_layer_move_preview_refresh(self):
        self.layer_move_refresh_pending = True
        if hasattr(self, "layer_move_preview_timer"):
            self.layer_move_preview_timer.start(self.layer_move_preview_interval_ms)

    def _flush_layer_move_preview_refresh(self):
        if not self.layer_move_refresh_pending:
            return
        self.layer_move_refresh_pending = False
        self._request_presets_preview_refresh(preset_ids=[self.current_preset])

    def _on_preset_changed(self):
        self.current_preset = self.preset_combo.currentData()
        if not self._is_layer_allowed(self.current_preset, self.active_layer):
            fallback = "logo" if self.current_preset == "logo" else "background"
            self._set_active_layer(fallback, sync=False)
        self._set_scene_for_preset(self.current_preset)
        self._refresh_preview()
        self._sync_layer_controls()
        self._sync_poster_textbox_controls()
        self._sync_gradient_controls()
        self._sync_top_controls()
        self._refresh_presets_preview_borders()

    def _on_preset_preview_clicked(self, preset_id: str):
        index = self.preset_combo.findData(preset_id)
        if index < 0:
            return
        if self.preset_combo.currentIndex() != index:
            self.preset_combo.setCurrentIndex(index)
        else:
            self._on_preset_changed()
        self._refresh_presets_preview_borders()

    def _on_guides_visible_toggled(self, checked: bool):
        self._push_undo_state()
        self.guides_visible = checked
        self._refresh_preview()

    def _on_poster_guide_variant_changed(self):
        if not hasattr(self, "poster_guide_combo"):
            return
        selected = self.poster_guide_combo.currentData()
        if selected not in POSTER_GUIDE_FILES:
            return
        self._push_undo_state()
        self.poster_guide_variant = selected
        self._load_guides()
        for layer_id in CHARACTER_LAYERS:
            layer_pixmap = self.assets[layer_id].pixmap
            if layer_pixmap is None or layer_pixmap.isNull():
                continue
            self._apply_auto_placement(layer_id, "poster")
        self._reapply_logo_auto_placement(["poster"])
        self._invalidate_presets_preview(["poster"])
        self._refresh_preview()
        self._sync_layer_controls()

    def _top_target_preset_ids(self):
        if not self._is_top_preset():
            return []
        if self.top_sync_all:
            return list(TOP_PRESET_IDS)
        return [self.current_preset]

    def _apply_top_setting_change(self, key: str, value: int):
        if self.updating_ui:
            return
        target_ids = self._top_target_preset_ids()
        if not target_ids:
            return
        changed = False
        for preset_id in target_ids:
            config = self._top_config(preset_id)
            if int(config.get(key, TOP_DEFAULT_CONFIG[key])) == int(value):
                continue
            config[key] = int(value)
            changed = True
        if not changed:
            return
        self._request_presets_preview_refresh(preset_ids=target_ids)
        if self._is_top_preset():
            self._schedule_live_preview_refresh()

    def _on_top_sync_all_toggled(self, checked: bool):
        self.top_sync_all = checked
        if checked and self._is_top_preset():
            self._push_undo_state()
            source_config = copy.deepcopy(self._top_config(self.current_preset))
            for preset_id in TOP_PRESET_IDS:
                self.top_settings[preset_id] = copy.deepcopy(source_config)
            self._invalidate_presets_preview(TOP_PRESET_IDS)
            self._refresh_preview()

    def _on_top_offset_x_changed(self, value: int):
        self._apply_top_setting_change("offset_x", value)

    def _on_top_offset_y_changed(self, value: int):
        self._apply_top_setting_change("offset_y", value)

    def _on_top_zoom_changed(self, value: int):
        self._apply_top_setting_change("zoom", value)

    def _on_top_stretch_x_changed(self, value: int):
        self._apply_top_setting_change("stretch_x", value)

    def _on_top_stretch_y_changed(self, value: int):
        self._apply_top_setting_change("stretch_y", value)

    def _reset_current_top_config(self):
        if not self._is_top_preset():
            return
        self._push_undo_state()
        target_ids = self._top_target_preset_ids()
        for preset_id in target_ids:
            self.top_settings[preset_id] = self._default_top_config()
        self._sync_top_controls()
        self._invalidate_presets_preview(target_ids)
        self._refresh_preview()

    def _on_logo_text_toggle(self, checked: bool):
        self._flush_logo_text_input()
        self._push_undo_state()
        self.logo_text_enabled = checked
        self._reapply_logo_auto_placement()
        self._invalidate_presets_preview()
        self._refresh_preview()
        self._sync_layer_controls()

    def _on_logo_text_changed(self):
        self.logo_text_pending = self.logo_text_input.toPlainText()
        if hasattr(self, "logo_text_input_timer"):
            self.logo_text_input_timer.start(self.logo_text_input_delay_ms)

    def _flush_logo_text_input(self):
        if hasattr(self, "logo_text_input_timer") and self.logo_text_input_timer.isActive():
            self.logo_text_input_timer.stop()
        pending_value = self.logo_text_pending.strip()
        if pending_value == self.logo_text:
            return
        self._push_undo_state()
        self.logo_text = pending_value
        self._reapply_logo_auto_placement()
        self._invalidate_presets_preview()
        self._refresh_preview()
        self._sync_layer_controls()

    def _on_logo_text_size_changed(self, value: int):
        self._flush_logo_text_input()
        self._push_undo_state()
        self.logo_text_size = value
        self._reapply_logo_auto_placement()
        self._invalidate_presets_preview()
        self._refresh_preview()
        self._sync_layer_controls()

    def _on_logo_text_align_changed(self):
        self._flush_logo_text_input()
        self._push_undo_state()
        self.logo_text_align = self.logo_text_align_combo.currentData()
        self._reapply_logo_auto_placement()
        self._invalidate_presets_preview()
        self._refresh_preview()
        self._sync_layer_controls()

    def _on_logo_text_upper_toggled(self, checked: bool):
        self._flush_logo_text_input()
        self._push_undo_state()
        self.logo_text_force_upper = checked
        self._reapply_logo_auto_placement()
        self._invalidate_presets_preview()
        self._refresh_preview()
        self._sync_layer_controls()

    def _on_logo_text_line_spacing_changed(self, value: int):
        self._flush_logo_text_input()
        self._push_undo_state()
        self.logo_text_line_spacing = value
        self._reapply_logo_auto_placement()
        self._invalidate_presets_preview()
        self._refresh_preview()
        self._sync_layer_controls()

    def _choose_logo_font(self):
        dialog = LocalFontPickerDialog(self, self)
        dialog.exec()

    def _add_logo_font_from_dafont(self):
        dialog = DaFontPickerDialog(self, self)
        dialog.exec()

    def _on_poster_textbox_toggled(self, checked: bool):
        self._push_undo_state()
        self.poster_textbox_enabled = checked
        self._sync_poster_textbox_controls()
        self._invalidate_presets_preview(["poster"])
        self._refresh_preview()

    def _on_poster_textbox_changed(self, value: str):
        upper_value = value.upper()
        if hasattr(self, "poster_textbox_input") and upper_value != value:
            self.poster_textbox_input.blockSignals(True)
            self.poster_textbox_input.setText(upper_value)
            self.poster_textbox_input.blockSignals(False)
        self.poster_textbox_text = upper_value
        self._invalidate_presets_preview(["poster"])
        self._refresh_preview()

    def _on_logo_shadow_toggled(self, checked: bool):
        self._push_undo_state()
        self.logo_shadow_enabled = checked
        self._reapply_logo_auto_placement()
        self._invalidate_presets_preview()
        self._refresh_preview()

    def _on_logo_shadow_distance_changed(self, value: int):
        self.logo_shadow_distance = max(0, min(50, value))
        self._update_shadow_slider_labels()
        self._reapply_logo_auto_placement()
        self._invalidate_presets_preview()
        self._schedule_live_preview_refresh()

    def _on_logo_shadow_blur_changed(self, value: int):
        self.logo_shadow_blur = max(0, min(50, value))
        self._update_shadow_slider_labels()
        self._reapply_logo_auto_placement()
        self._invalidate_presets_preview()
        self._schedule_live_preview_refresh()

    def _on_logo_shadow_angle_changed(self, value: int):
        self.logo_shadow_angle = value % 360
        self._update_shadow_slider_labels()
        self._reapply_logo_auto_placement()
        self._invalidate_presets_preview()
        self._schedule_live_preview_refresh()

    def _on_logo_shadow_opacity_changed(self, value: int):
        self.logo_shadow_opacity = value
        self._update_shadow_slider_labels()
        self._reapply_logo_auto_placement()
        self._invalidate_presets_preview()
        self._schedule_live_preview_refresh()

    def _on_gradient_enabled_toggled(self, checked: bool):
        self._push_undo_state()
        self._gradient_config()["enabled"] = checked
        self._sync_gradient_controls()
        self._invalidate_presets_preview([self.current_preset])
        self._refresh_preview()

    def _on_gradient_mode_changed(self):
        self._push_undo_state()
        self._gradient_config()["mode"] = self.gradient_mode_combo.currentData()
        self._sync_gradient_controls()
        self._invalidate_presets_preview([self.current_preset])
        self._refresh_preview()

    def _on_gradient_direction_changed(self):
        self._push_undo_state()
        self._gradient_config()["direction"] = self.gradient_direction_combo.currentData()
        self._invalidate_presets_preview([self.current_preset])
        self._refresh_preview()

    def _on_gradient_distance_changed(self, value: int):
        self._gradient_config()["distance"] = value
        self._update_gradient_slider_labels()
        self._invalidate_presets_preview([self.current_preset])
        self._schedule_live_preview_refresh()

    def _on_gradient_stretch_changed(self, value: int):
        self._gradient_config()["stretch"] = value
        self._update_gradient_slider_labels()
        self._invalidate_presets_preview([self.current_preset])
        self._schedule_live_preview_refresh()

    def _update_shadow_slider_labels(self):
        if hasattr(self, "logo_shadow_distance_label"):
            self.logo_shadow_distance_label.setText(f"{int(self.logo_shadow_distance)} px")
        if hasattr(self, "logo_shadow_blur_label"):
            self.logo_shadow_blur_label.setText(f"{int(self.logo_shadow_blur)} px")
        if hasattr(self, "logo_shadow_angle_label"):
            self.logo_shadow_angle_label.setText(f"{int(self.logo_shadow_angle)} deg")
        if hasattr(self, "logo_shadow_opacity_label"):
            self.logo_shadow_opacity_label.setText(f"{int(self.logo_shadow_opacity)} %")

    def _update_gradient_slider_labels(self):
        config = self._gradient_config()
        if hasattr(self, "gradient_distance_label"):
            self.gradient_distance_label.setText(f"{int(config['distance'])} %")
        if hasattr(self, "gradient_stretch_label"):
            self.gradient_stretch_label.setText(f"{int(config['stretch'])} %")

    def _logo_effective_size(self) -> int:
        return self.logo_text_size

    def _logo_text_lines(self, logo_text: str) -> list[str]:
        lines = logo_text.splitlines()
        return lines if lines else [logo_text]

    def _logo_line_spacing_ratio(self) -> float:
        return max(0.5, min(3.0, self.logo_text_line_spacing / 100))

    def _logo_preview_point_size(self) -> int:
        effective_size = self._logo_effective_size()
        return max(16, int(effective_size / 3))

    def _logo_export_spacing(self) -> int:
        effective_size = self._logo_effective_size()
        base_spacing = max(6, effective_size // 8)
        ratio = self._logo_line_spacing_ratio()
        return max(0, int(base_spacing * ratio))

    def _logo_font_for_export(self):
        return self._load_logo_font(self._logo_effective_size())

    def _logo_display_text(self) -> str:
        return self.logo_text.upper() if self.logo_text_force_upper else self.logo_text

    def _has_logo_text_source(self) -> bool:
        return self.logo_text_enabled and bool(self.logo_text.strip())

    def _build_logo_text_source_image(self):
        if not self._has_logo_text_source():
            return None
        return self._build_logo_export_image(self._logo_display_text())

    def _logo_source_image(self):
        if self._has_logo_text_source():
            return self._build_logo_text_source_image()
        asset = self.assets.get("logo")
        if asset is None:
            return None
        if asset.pil is not None:
            return asset.pil
        if asset.pixmap is None or asset.pixmap.isNull():
            return None
        try:
            return self._qpixmap_to_pil(asset.pixmap)
        except Exception:
            return None

    def _build_logo_text_source_pixmap(self) -> QPixmap:
        image = self._build_logo_text_source_image()
        if image is None:
            return QPixmap()
        return self._pil_to_qpixmap(image)

    def _logo_layout_source_pixmap(self) -> QPixmap:
        if self._has_logo_text_source():
            return self._build_logo_text_source_pixmap()
        logo_asset = self.assets.get("logo")
        if logo_asset is None or logo_asset.pixmap is None:
            return QPixmap()
        return logo_asset.pixmap

    def _render_logo_fit_candidate(
        self,
        canvas_w: int,
        canvas_h: int,
        scale: float,
        resample=Image.Resampling.LANCZOS,
    ):
        source = self._logo_source_image()
        if source is None:
            return None
        src_w, src_h = source.size
        if src_w <= 0 or src_h <= 0:
            return None
        ratio = min(canvas_w / src_w, canvas_h / src_h)
        ratio *= max(0.01, float(scale))
        target_size = (
            max(1, int(round(src_w * ratio))),
            max(1, int(round(src_h * ratio))),
        )
        rendered = source.resize(target_size, resample)
        return self._apply_logo_shadow_pil(rendered)

    def _fit_logo_scale_to_canvas(self, canvas_w: int, canvas_h: int) -> float:
        def visible_size(candidate_scale: float):
            rendered = self._render_logo_fit_candidate(canvas_w, canvas_h, candidate_scale)
            if rendered is None:
                return None
            bbox = self._alpha_bbox_for_pil_image(rendered)
            if bbox is None:
                return float(rendered.width), float(rendered.height)
            left, top, right, bottom = bbox
            return max(1.0, right - left), max(1.0, bottom - top)

        def fits(candidate_scale: float) -> bool:
            size = visible_size(candidate_scale)
            if size is None:
                return False
            visible_w, visible_h = size
            return visible_w <= (canvas_w + 0.5) and visible_h <= (canvas_h + 0.5)

        min_scale = 0.01
        if not fits(min_scale):
            return min_scale

        if fits(1.0):
            low = 1.0
            high = 2.0
            while high < 32.0 and fits(high):
                low = high
                high *= 2.0
            if high >= 32.0 and fits(high):
                return high
        else:
            low = min_scale
            high = 1.0

        for _ in range(12):
            mid = (low + high) * 0.5
            if fits(mid):
                low = mid
            else:
                high = mid
        return max(min_scale, low)

    def _reapply_logo_auto_placement(self, preset_ids=None):
        if preset_ids is None:
            preset_ids = PRESETS.keys()
        source_pixmap = self._logo_layout_source_pixmap()
        if source_pixmap.isNull():
            return
        for preset_id in preset_ids:
            if self._is_layer_allowed(preset_id, "logo"):
                self._apply_auto_placement("logo", preset_id)

    def _logo_shadow_offset(self) -> Tuple[int, int]:
        angle_rad = math.radians(self.logo_shadow_angle)
        dx = int(round(math.cos(angle_rad) * self.logo_shadow_distance))
        dy = int(round(math.sin(angle_rad) * self.logo_shadow_distance))
        return dx, dy

    def _logo_shadow_rgba(self) -> Tuple[int, int, int, int]:
        color = QColor(self.logo_shadow_color)
        if not color.isValid():
            color = QColor("#000000")
        alpha = max(0, min(255, int(round((self.logo_shadow_opacity / 100) * 255))))
        return color.red(), color.green(), color.blue(), alpha

    def _apply_logo_shadow_pil(self, source: Image.Image):
        if not self.logo_shadow_enabled:
            return source

        src = source.convert("RGBA")
        blur = max(0, int(self.logo_shadow_blur))
        dx, dy = self._logo_shadow_offset()
        red, green, blue, alpha = self._logo_shadow_rgba()

        alpha_mask = src.getchannel("A").point(lambda px: int((px * alpha) / 255))
        shadow_core = Image.new("RGBA", src.size, (red, green, blue, 0))
        shadow_core.putalpha(alpha_mask)

        shadow_img = shadow_core
        shadow_shift_x = 0
        shadow_shift_y = 0
        if blur > 0:
            pad = blur * 2
            shadow_padded = Image.new(
                "RGBA",
                (src.width + (pad * 2), src.height + (pad * 2)),
                (0, 0, 0, 0),
            )
            shadow_padded.alpha_composite(shadow_core, (pad, pad))
            shadow_img = shadow_padded.filter(ImageFilter.GaussianBlur(radius=blur))
            shadow_shift_x = -pad
            shadow_shift_y = -pad

        shadow_x = dx + shadow_shift_x
        shadow_y = dy + shadow_shift_y

        # Keep logo anchor stable: enlarge symmetrically around source so only shadow appears to move.
        left_over = max(0, -shadow_x)
        right_over = max(0, shadow_x + shadow_img.width - src.width)
        top_over = max(0, -shadow_y)
        bottom_over = max(0, shadow_y + shadow_img.height - src.height)
        pad_x = int(max(left_over, right_over))
        pad_y = int(max(top_over, bottom_over))

        canvas = Image.new(
            "RGBA",
            (src.width + (pad_x * 2), src.height + (pad_y * 2)),
            (0, 0, 0, 0),
        )
        canvas.alpha_composite(shadow_img, (pad_x + shadow_x, pad_y + shadow_y))
        canvas.alpha_composite(src, (pad_x, pad_y))
        return canvas

    def _qpixmap_to_pil(self, pixmap: QPixmap):
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        pixmap.save(buffer, "PNG")
        return Image.open(BytesIO(bytes(buffer.data()))).convert("RGBA")

    def _pil_to_qpixmap(self, image: Image.Image) -> QPixmap:
        png_bytes = BytesIO()
        image.save(png_bytes, format="PNG")
        pixmap = QPixmap()
        pixmap.loadFromData(png_bytes.getvalue(), "PNG")
        return pixmap

    def _apply_logo_shadow_preview(self, pixmap: QPixmap) -> QPixmap:
        if not self.logo_shadow_enabled:
            return pixmap
        try:
            source = self._qpixmap_to_pil(pixmap)
            shadowed = self._apply_logo_shadow_pil(source)
            return self._pil_to_qpixmap(shadowed)
        except Exception:
            return pixmap

    def _gradient_color_rgb(self, hex_color: str, fallback: str) -> Tuple[int, int, int]:
        color = QColor(hex_color)
        if not color.isValid():
            color = QColor(fallback)
        return color.red(), color.green(), color.blue()

    def _build_gradient_image(self, canvas_w: int, canvas_h: int, preset_id: str | None = None):
        config = self._gradient_config(preset_id)
        if not config["enabled"]:
            return None
        if canvas_w <= 0 or canvas_h <= 0:
            return None

        direction = config["direction"]
        mode = config["mode"]
        vertical = direction in {"top", "bottom"}
        axis_size = canvas_h if vertical else canvas_w
        distance_px = max(1, int(axis_size * (config["distance"] / 100)))
        stretch_ratio = max(0.2, config["stretch"] / 100)

        color_a = self._gradient_color_rgb(config["color_a"], "#000000")
        color_b = self._gradient_color_rgb(config["color_b"], "#FFFFFF")
        ramp_data = []
        for idx in range(axis_size):
            if direction in {"top", "left"}:
                axis_pos = idx
            else:
                axis_pos = (axis_size - 1) - idx
            t = min(1.0, axis_pos / distance_px)
            t = min(1.0, max(0.0, t ** (1.0 / stretch_ratio)))

            if mode == "double":
                red = int(round(color_a[0] + ((color_b[0] - color_a[0]) * t)))
                green = int(round(color_a[1] + ((color_b[1] - color_a[1]) * t)))
                blue = int(round(color_a[2] + ((color_b[2] - color_a[2]) * t)))
                alpha = 255
            else:
                red, green, blue = color_a
                alpha = int(round((1.0 - t) * 255))
            ramp_data.append((red, green, blue, alpha))

        if vertical:
            ramp = Image.new("RGBA", (1, axis_size), (0, 0, 0, 0))
            ramp.putdata(ramp_data)
        else:
            ramp = Image.new("RGBA", (axis_size, 1), (0, 0, 0, 0))
            ramp.putdata(ramp_data)
        return ramp.resize((canvas_w, canvas_h), Image.Resampling.BILINEAR)

    def _draw_logo_preview_text(self, painter: QPainter, draw_rect, logo_text: str):
        metrics = QFontMetrics(painter.font())
        lines = self._logo_text_lines(logo_text)
        ratio = self._logo_line_spacing_ratio()
        line_step = max(1, int(metrics.height() * ratio))
        block_height = metrics.height() + (line_step * max(0, len(lines) - 1))
        y = draw_rect.center().y() - (block_height // 2) + metrics.ascent()

        for line in lines:
            text_w = metrics.horizontalAdvance(line)
            if self.logo_text_align == "left":
                x = draw_rect.left()
            elif self.logo_text_align == "right":
                x = draw_rect.right() - text_w
            else:
                x = draw_rect.center().x() - (text_w // 2)
            painter.drawText(int(x), int(y), line)
            y += line_step

    def _build_logo_preview_pixmap(self, logo_text: str) -> QPixmap:
        probe = QPixmap(1, 1)
        probe.fill(Qt.GlobalColor.transparent)
        probe_painter = QPainter(probe)
        font = probe_painter.font()
        font.setBold(True)
        font.setPointSize(self._logo_preview_point_size())
        probe_painter.setFont(font)
        metrics = QFontMetrics(font)
        lines = self._logo_text_lines(logo_text)
        line_widths = [
            max(1, metrics.horizontalAdvance(line) if line else metrics.horizontalAdvance(" "))
            for line in lines
        ]
        text_w = max(line_widths)
        line_step = max(1, int(metrics.height() * self._logo_line_spacing_ratio()))
        text_h = metrics.height() + (line_step * max(0, len(lines) - 1))
        pad_x = max(12, metrics.horizontalAdvance("M") // 2)
        pad_y = max(12, metrics.height() // 3)
        probe_painter.end()

        pixmap = QPixmap(max(1, text_w + (pad_x * 2)), max(1, text_h + (pad_y * 2)))
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setPen(QColor(self.logo_text_color))
        painter.setFont(font)
        self._draw_logo_preview_text(
            painter,
            pixmap.rect().adjusted(pad_x, pad_y, -pad_x, -pad_y),
            logo_text,
        )
        painter.end()
        return pixmap

    def _build_logo_export_image(self, logo_text: str):
        font = self._logo_font_for_export()
        spacing = self._logo_export_spacing()
        lines = self._logo_text_lines(logo_text)

        probe = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        measure = ImageDraw.Draw(probe)
        sample_bbox = measure.textbbox((0, 0), "Ag", font=font)
        line_height = max(1, sample_bbox[3] - sample_bbox[1])

        line_boxes = []
        max_width = 1
        for line in lines:
            token = line if line else " "
            bbox = measure.textbbox((0, 0), token, font=font)
            width = max(1, bbox[2] - bbox[0])
            line_boxes.append((line, bbox, width))
            max_width = max(max_width, width)

        text_h = (line_height * len(lines)) + (spacing * max(0, len(lines) - 1))
        pad_x = max(16, int(self._logo_effective_size() * 0.45))
        pad_y = max(12, int(line_height * 0.35))
        img = Image.new(
            "RGBA",
            (max(1, max_width + (pad_x * 2)), max(1, text_h + (pad_y * 2))),
            (0, 0, 0, 0),
        )
        draw = ImageDraw.Draw(img)

        y = pad_y
        for line, bbox, line_w in line_boxes:
            if self.logo_text_align == "left":
                x = pad_x
            elif self.logo_text_align == "right":
                x = pad_x + (max_width - line_w)
            else:
                x = pad_x + ((max_width - line_w) // 2)
            if line:
                draw.text(
                    (x - bbox[0], y - bbox[1]),
                    line,
                    fill=self.logo_text_color,
                    font=font,
                )
            y += line_height + spacing
        return img

    def _poster_textbox_display_text(self):
        text = self.poster_textbox_text.strip()
        return (text if text else "TEXTE BOX").upper()

    def _load_poster_textbox_font(self, size: int):
        font_candidates = [
            "Montserrat-Bold.ttf",
            "Arialbd.ttf",
            "/usr/share/fonts/truetype/montserrat/Montserrat-Bold.ttf",
            "/Library/Fonts/Montserrat-Bold.ttf",
            "C:/Windows/Fonts/montserrat-bold.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
        ]
        for candidate in font_candidates:
            try:
                return ImageFont.truetype(candidate, size)
            except OSError:
                continue
        return ImageFont.load_default()

    def _build_poster_textbox_render(
        self,
        preset_id: str,
        canvas_w: int,
        canvas_h: int,
        size_factor: float = 1.0,
    ):
        if preset_id != "poster" or not self.poster_textbox_enabled:
            return None
        text = self._poster_textbox_display_text()
        if not text:
            return None

        base = POSTER_TEXTBOX_BASE
        scale = canvas_w / 1600.0
        size_factor = max(0.1, min(2.0, float(size_factor)))
        x = int(round(base["x"] * scale))
        y = int(round(base["y"] * scale))
        height = max(18, int(round(base["height"] * scale * size_factor)))
        max_width = max(1, canvas_w - x)
        min_width = max(20, int(round(base["min_width"] * scale * size_factor)))
        min_width = min(min_width, max_width)
        padding_left = max(4, int(round(base["padding_left"] * scale * size_factor)))
        radius = max(2, int(round(base["radius"] * scale * size_factor)))
        min_font_size = 8
        font_size = max(min_font_size, int(round(base["font_size"] * scale * size_factor)))

        probe = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        probe_draw = ImageDraw.Draw(probe)
        font = self._load_poster_textbox_font(font_size)
        bbox = probe_draw.textbbox((0, 0), text, font=font)
        text_w = max(1, bbox[2] - bbox[0])
        text_h = max(1, bbox[3] - bbox[1])
        spaces_bbox = probe_draw.textbbox((0, 0), "  ", font=font)
        padding_right = max(4, spaces_bbox[2] - spaces_bbox[0])

        width = max(min_width, text_w + padding_left + padding_right)
        width = min(max_width, width)
        while (text_w + padding_left + padding_right) > width and font_size > min_font_size:
            font_size -= 2
            font = self._load_poster_textbox_font(font_size)
            bbox = probe_draw.textbbox((0, 0), text, font=font)
            text_w = max(1, bbox[2] - bbox[0])
            text_h = max(1, bbox[3] - bbox[1])
            spaces_bbox = probe_draw.textbbox((0, 0), "  ", font=font)
            padding_right = max(4, spaces_bbox[2] - spaces_bbox[0])

        box_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(box_img)
        fill_color = POSTER_TEXTBOX_BASE["fill_color"]
        draw.rounded_rectangle(
            (0, 0, width - 1, height - 1),
            radius=radius,
            fill=fill_color,
        )
        # Keep the right side rounded but force a straight left edge.
        draw.rectangle((0, 0, min(radius, width - 1), height - 1), fill=fill_color)
        draw = ImageDraw.Draw(box_img)
        text_x = padding_left
        text_y = int(round((height - text_h) * 0.5 - bbox[1]))
        draw.text(
            (text_x, text_y),
            text,
            fill=POSTER_TEXTBOX_BASE["text_color"],
            font=font,
        )
        return box_img, x, y

    def _refresh_poster_textbox_overlay(self, canvas_w: int, canvas_h: int):
        if not hasattr(self, "poster_textbox_item"):
            return
        draw_data = self._build_poster_textbox_render(self.current_preset, canvas_w, canvas_h)
        if draw_data is None:
            self.poster_textbox_item.setVisible(False)
            return
        box_img, x, y = draw_data
        pixmap = self._pil_to_qpixmap(box_img)
        if pixmap.isNull():
            self.poster_textbox_item.setVisible(False)
            return
        self.poster_textbox_item.setPixmap(pixmap)
        self.poster_textbox_item.setOffset(0, 0)
        self.poster_textbox_item.setPos(x, y)
        self.poster_textbox_item.setVisible(True)

    def _pick_logo_color(self):
        color = QColorDialog.getColor(QColor(self.logo_text_color), self)
        if color.isValid():
            self._push_undo_state()
            self.logo_text_color = color.name()
            self._invalidate_presets_preview()
            self._refresh_preview()

    def _pick_logo_shadow_color(self):
        color = QColorDialog.getColor(QColor(self.logo_shadow_color), self)
        if color.isValid():
            self._push_undo_state()
            self.logo_shadow_color = color.name()
            self._invalidate_presets_preview()
            self._refresh_preview()

    def _pick_gradient_color_a(self):
        color = QColorDialog.getColor(QColor(self._gradient_config()["color_a"]), self)
        if color.isValid():
            self._push_undo_state()
            self._gradient_config()["color_a"] = color.name()
            self._invalidate_presets_preview([self.current_preset])
            self._refresh_preview()

    def _pick_gradient_color_b(self):
        color = QColorDialog.getColor(QColor(self._gradient_config()["color_b"]), self)
        if color.isValid():
            self._push_undo_state()
            self._gradient_config()["color_b"] = color.name()
            self._invalidate_presets_preview([self.current_preset])
            self._refresh_preview()

    def _on_visible_changed(self, checked: bool):
        self._push_undo_state()
        layer = self._selected_layer()
        self._layer_state(self.current_preset, layer)["visible"] = checked
        self._refresh_preview()

    def _on_opacity_changed(self, value: int):
        layer = self._selected_layer()
        self._layer_state(self.current_preset, layer)["opacity"] = value / 100
        self._update_slider_value_labels()
        self._schedule_live_preview_refresh()

    def _on_scale_changed(self, value: int):
        layer = self._selected_layer()
        self._layer_state(self.current_preset, layer)["transform"]["scale"] = value / 100
        self._update_slider_value_labels()
        self._schedule_live_preview_refresh()

    def _on_reset_layer(self):
        self._push_undo_state()
        layer = self._selected_layer()
        self.state[self.current_preset][layer] = self._build_default_layer()
        if layer == "background":
            self.state[self.current_preset][layer]["fit_mode"] = "crop"
        self._apply_auto_placement(layer, self.current_preset)
        self._refresh_preview()
        self._sync_layer_controls()

    def _on_center_layer(self):
        self._push_undo_state()
        layer = self._selected_layer()
        if not self._is_layer_allowed(self.current_preset, layer):
            return

        width, height = PRESETS[self.current_preset]["size"]
        layer_state = self._layer_state(self.current_preset, layer)
        layer_state["transform"]["x"] = width * 0.5
        if layer in CHARACTER_LAYERS:
            pixmap = self._preview_pixmap(layer, width, height)
            if pixmap.isNull():
                layer_state["transform"]["y"] = height * 0.5
            else:
                layer_state["transform"]["y"] = (height * 0.5) + (pixmap.height() * 0.5)
        else:
            layer_state["transform"]["y"] = height * 0.5
        self._refresh_preview()
        self._sync_layer_controls()

    def _on_layer_moved(self, layer_id: str, x: float, y: float):
        self._layer_state(self.current_preset, layer_id)["transform"]["x"] = x
        self._layer_state(self.current_preset, layer_id)["transform"]["y"] = y
        self._schedule_layer_move_preview_refresh()

    def _on_wheel_scaled(self, delta: float):
        self._push_undo_state()
        layer = self._selected_layer()
        layer_state = self._layer_state(self.current_preset, layer)
        layer_state["transform"]["scale"] = max(0.0, min(1.0, layer_state["transform"]["scale"] + delta))
        self._schedule_live_preview_refresh()
        self._sync_layer_controls()

    def _on_layer_pressed(self, layer_id: str):
        if not self._is_control_layer_available(self.current_preset, layer_id):
            return
        self._push_undo_state()

    def _on_layer_clicked(self, layer_id: str):
        self._set_active_layer(layer_id)

    def _set_active_layer(self, layer_id: str, sync: bool = True):
        if layer_id not in CONTROL_LAYER_ORDER:
            return
        self.active_layer = layer_id
        for lid, btn in self.layer_buttons.items():
            btn.setChecked(lid == layer_id)
        if sync:
            self._sync_layer_controls()

    def _is_layer_allowed(self, preset_id: str, layer_id: str) -> bool:
        if self._is_top_preset(preset_id):
            return False
        if preset_id == "logo":
            return layer_id == "logo"
        if layer_id == "logo" and PRESETS[preset_id].get("skip_logo"):
            return False
        return True

    def _layer_has_loaded_asset(self, layer_id: str) -> bool:
        asset = self.assets.get(layer_id)
        if asset is None:
            return False
        if asset.pixmap is not None and not asset.pixmap.isNull():
            return True
        return asset.pil is not None

    def _loaded_character_layers(self) -> list[str]:
        return [layer_id for layer_id in CHARACTER_LAYERS if self._layer_has_loaded_asset(layer_id)]

    def _alpha_bbox_for_pil_image(self, image: Image.Image | None):
        if image is None:
            return None
        try:
            if "A" in image.getbands():
                bbox = image.getchannel("A").getbbox()
                if bbox is not None:
                    left, top, right, bottom = bbox
                    if right > left and bottom > top:
                        return (float(left), float(top), float(right), float(bottom))
        except Exception:
            return None
        try:
            width, height = image.size
        except Exception:
            return None
        return (0.0, 0.0, float(width), float(height))

    def _alpha_bbox_for_qpixmap(self, pixmap: QPixmap):
        if pixmap.isNull():
            return None
        try:
            image = self._qpixmap_to_pil(pixmap)
        except Exception:
            return None
        return self._alpha_bbox_for_pil_image(image)

    def _layer_visible_box(self, layer_id: str):
        if layer_id == "logo" and self._has_logo_text_source():
            bbox = self._alpha_bbox_for_pil_image(self._build_logo_text_source_image())
            if bbox is not None:
                return bbox
        asset = self.assets.get(layer_id)
        if asset is None:
            return None
        bbox = self._alpha_bbox_for_pil_image(asset.pil)
        if bbox is not None:
            return bbox
        if asset.pixmap is None or asset.pixmap.isNull():
            return None
        return (0.0, 0.0, float(asset.pixmap.width()), float(asset.pixmap.height()))

    def _is_control_layer_available(self, preset_id: str, layer_id: str) -> bool:
        if not self._is_layer_allowed(preset_id, layer_id):
            return False
        if layer_id in EXTRA_CHARACTER_LAYERS and not self._layer_has_loaded_asset(layer_id):
            return False
        return True

    def _sync_extra_character_layer_buttons(self):
        if not hasattr(self, "layer_buttons"):
            return
        for layer_id in EXTRA_CHARACTER_LAYERS:
            button = self.layer_buttons.get(layer_id)
            if button is None:
                continue
            button.setVisible(self._layer_has_loaded_asset(layer_id))

    def _sync_layer_controls(self):
        if self.updating_ui:
            return
        self.updating_ui = True
        self._sync_extra_character_layer_buttons()
        layer = self._selected_layer()
        if not self._is_control_layer_available(self.current_preset, layer):
            for fallback in CONTROL_LAYER_ORDER:
                if self._is_control_layer_available(self.current_preset, fallback):
                    self._set_active_layer(fallback, sync=False)
                    layer = fallback
                    break
        for lid, btn in self.layer_buttons.items():
            btn.setEnabled(self._is_control_layer_available(self.current_preset, lid))
        layer_state = self._layer_state(self.current_preset, layer)
        self.visible_check.setChecked(layer_state["visible"])
        self.opacity_slider.setValue(int(layer_state["opacity"] * 100))
        self.scale_slider.setValue(int(layer_state["transform"]["scale"] * 100))
        has_available_layer = any(
            self._is_control_layer_available(self.current_preset, lid) for lid in CONTROL_LAYER_ORDER
        )
        self.visible_check.setEnabled(has_available_layer)
        self.opacity_slider.setEnabled(has_available_layer)
        self.scale_slider.setEnabled(has_available_layer)
        if hasattr(self, "center_layer_btn"):
            self.center_layer_btn.setEnabled(has_available_layer)
        if hasattr(self, "reset_layer_btn"):
            self.reset_layer_btn.setEnabled(has_available_layer)
        self._update_slider_value_labels()
        self.updating_ui = False

    def _import_layer(self, layer_id: str):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Sélectionner une image",
            str(self._recent_dir("import")),
            "Images (*.png *.jpg *.jpeg *.webp)",
        )
        if not file_path:
            return
        self._remember_recent_dir("import", Path(file_path).parent)
        self._push_undo_state()

        try:
            pil_img = Image.open(file_path).convert("RGBA")
        except Exception as exc:
            self._log(f"Erreur import {layer_id}: {exc}")
            QMessageBox.critical(self, "Erreur", f"Impossible d'ouvrir l'image: {exc}")
            return

        pixmap = QPixmap(file_path)
        if pixmap.isNull():
            self._log(f"Erreur import {layer_id}: pixmap invalide")
            return

        self.assets[layer_id] = LayerAsset(path=file_path, pixmap=pixmap, pil=pil_img)
        for preset_id in PRESETS:
            self._apply_auto_placement(layer_id, preset_id)

        if self._is_control_layer_available(self.current_preset, layer_id):
            self._set_active_layer(layer_id, sync=False)
        self._invalidate_presets_preview()
        self._log(f"Import {layer_id}: {file_path}")
        self._refresh_preview()
        self._sync_layer_controls()

    def _apply_auto_placement(self, layer_id: str, preset_id: str):
        layer_pixmap = self.assets[layer_id].pixmap
        if layer_id == "logo":
            layout_logo_pixmap = self._logo_layout_source_pixmap()
            if not layout_logo_pixmap.isNull():
                layer_pixmap = layout_logo_pixmap
        if (layer_pixmap is None or layer_pixmap.isNull()) and layer_id not in {"logo", "gradient"}:
            return

        width, height = PRESETS[preset_id]["size"]
        layer_state = self._layer_state(preset_id, layer_id)

        if layer_id == "background":
            layer_state["fit_mode"] = "crop"
            layer_state["transform"]["x"] = width * 0.5
            layer_state["transform"]["y"] = height * 0.5
            layer_state["transform"]["scale"] = 1.0
            layer_state["transform"]["anchor"] = "center"
        elif layer_id in CHARACTER_LAYERS:
            if layer_pixmap is not None and self._apply_guide_auto_placement(layer_id, preset_id, layer_pixmap):
                return
            layer_state["fit_mode"] = "contain"
            layer_state["transform"]["anchor"] = "bottom"
            layer_state["transform"]["x"] = width * 0.5
            layer_state["transform"]["scale"] = 1.0
            src_w = max(1, layer_pixmap.width())
            src_h = max(1, layer_pixmap.height())
            ratio = min(width / src_w, height / src_h)
            rendered_h = src_h * ratio
            # Keep initial placement visually centered while using a bottom anchor for scaling.
            layer_state["transform"]["y"] = (height * 0.5) + (rendered_h * 0.5)
        elif layer_id == "gradient":
            layer_state["fit_mode"] = "stretch"
            layer_state["transform"]["anchor"] = "center"
            layer_state["transform"]["x"] = width * 0.5
            layer_state["transform"]["y"] = height * 0.5
            layer_state["transform"]["scale"] = 1.0
        elif layer_id == "logo":
            if layer_pixmap is not None and self._apply_guide_auto_placement(layer_id, preset_id, layer_pixmap):
                return
            layer_state["fit_mode"] = "contain"
            if preset_id == "logo":
                if layer_pixmap is not None and not layer_pixmap.isNull():
                    target_scale = self._fit_logo_scale_to_canvas(width, height)
                    layer_state["transform"]["anchor"] = "bottom_left_visible"
                    layer_state["transform"]["scale"] = target_scale
                    layer_state["transform"]["x"] = 0.0
                    layer_state["transform"]["y"] = float(height)
                else:
                    layer_state["transform"]["anchor"] = "center"
                    layer_state["transform"]["scale"] = 1.0
                    layer_state["transform"]["x"] = width * 0.5
                    layer_state["transform"]["y"] = height * 0.5
            else:
                layer_state["transform"]["anchor"] = "center"
                layer_state["transform"]["scale"] = 1.0
                layer_state["transform"]["x"] = width * 0.5
                layer_state["transform"]["y"] = height * 0.5

    def _refresh_preview(self):
        preset_meta = PRESETS[self.current_preset]
        canvas_w, canvas_h = preset_meta["size"]
        self._refresh_guide_overlay(canvas_w, canvas_h)

        if self._is_top_preset():
            for layer in RENDER_LAYER_ORDER:
                self.items[layer].setVisible(False)
            self.clip_item.setVisible(False)
            self.guide_item.setVisible(False)
            self.poster_textbox_item.setVisible(False)
            preview_canvas = self._compose_preset_canvas(self.current_preset, render_scale=1.0)
            preview_pixmap = self._pil_to_qpixmap(preview_canvas) if preview_canvas is not None else QPixmap()
            if preview_pixmap.isNull():
                self.special_preset_item.setVisible(False)
            else:
                self.special_preset_item.setPixmap(preview_pixmap)
                self.special_preset_item.setOffset(0, 0)
                self.special_preset_item.setPos(0, 0)
                self.special_preset_item.setVisible(True)
            self._request_presets_preview_refresh(preset_ids=[self.current_preset])
            return

        self.special_preset_item.setVisible(False)
        self.clip_item.setVisible(True)

        for layer in RENDER_LAYER_ORDER:
            item = self.items[layer]
            layer_state = self._layer_state(self.current_preset, layer)
            if not self._is_layer_allowed(self.current_preset, layer):
                item.setVisible(False)
                continue
            if not layer_state["visible"]:
                item.setVisible(False)
                continue

            pixmap = self._preview_pixmap(layer, canvas_w, canvas_h)
            if pixmap.isNull():
                item.setVisible(False)
                continue

            item.setVisible(True)
            item.setOpacity(layer_state["opacity"])
            item.setPixmap(pixmap)
            anchor = layer_state["transform"].get("anchor", "center")

            if layer in CHARACTER_LAYERS:
                pos_x = layer_state["transform"]["x"]
                pos_y = layer_state["transform"]["y"]
                item.setOffset(-pixmap.width() / 2, -pixmap.height())
                item.setPos(pos_x, pos_y)
            elif layer == "gradient":
                item.setOffset(0, 0)
                item.setPos(0, 0)
            elif anchor == "bottom_left_visible":
                pos_x = layer_state["transform"]["x"]
                pos_y = layer_state["transform"]["y"]
                bbox = self._alpha_bbox_for_qpixmap(pixmap)
                if bbox is None:
                    bbox_left = 0.0
                    bbox_bottom = float(pixmap.height())
                else:
                    bbox_left, _bbox_top, _bbox_right, bbox_bottom = bbox
                item.setOffset(-bbox_left, -bbox_bottom)
                item.setPos(pos_x, pos_y)
            else:
                pos_x = layer_state["transform"]["x"]
                pos_y = layer_state["transform"]["y"]
                item.setOffset(-pixmap.width() / 2, -pixmap.height() / 2)
                item.setPos(pos_x, pos_y)
        self._refresh_poster_textbox_overlay(canvas_w, canvas_h)
        self._request_presets_preview_refresh(preset_ids=[self.current_preset])

    def _top_template_image(self, preset_id: str):
        if preset_id in self.top_template_cache:
            return self.top_template_cache[preset_id].copy()
        template_path = self._top_template_path(preset_id)
        if template_path is None or not template_path.exists():
            return None
        try:
            template = Image.open(template_path).convert("RGBA")
        except Exception:
            return None
        self.top_template_cache[preset_id] = template.copy()
        return template

    def _compose_top_canvas(
        self,
        preset_id: str,
        *,
        render_scale: float = 1.0,
        resample=Image.Resampling.LANCZOS,
    ):
        scale = max(0.02, min(1.0, float(render_scale)))
        canvas_w = max(1, int(round(TOP_CANVAS_SIZE[0] * scale)))
        canvas_h = max(1, int(round(TOP_CANVAS_SIZE[1] * scale)))
        poster_canvas = self._compose_preset_canvas(
            "poster",
            log_upscale=False,
            render_scale=scale,
            resample=resample,
            textbox_scale_factor=1.0,
        )
        top_config = self._top_config(preset_id)
        vignette_x = int(round(TOP_VIGNETTE_X * scale))
        vignette_y = int(round(TOP_VIGNETTE_Y * scale))
        vignette_w = max(1, int(round(TOP_VIGNETTE_W * scale)))
        vignette_h = max(1, int(round(TOP_VIGNETTE_H * scale)))
        vignette_radius = max(1, int(round(TOP_VIGNETTE_RADIUS * scale)))
        canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

        if poster_canvas is not None:
            src_w, src_h = poster_canvas.size
            cover_ratio = max(vignette_w / max(1, src_w), vignette_h / max(1, src_h))
            base_w = max(1, int(round(src_w * cover_ratio)))
            base_h = max(1, int(round(src_h * cover_ratio)))
            covered = poster_canvas.resize((base_w, base_h), resample)
            scale_x = max(0.1, float(top_config["zoom"]) / 100.0) * max(0.1, float(top_config["stretch_x"]) / 100.0)
            scale_y = max(0.1, float(top_config["zoom"]) / 100.0) * max(0.1, float(top_config["stretch_y"]) / 100.0)
            final_w = max(1, int(round(base_w * scale_x)))
            final_h = max(1, int(round(base_h * scale_y)))
            transformed = covered.resize((final_w, final_h), resample)
            poster_layer = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
            paste_x = vignette_x + int(round(float(top_config["offset_x"]) * scale))
            paste_y = vignette_y + int(round(float(top_config["offset_y"]) * scale))
            poster_layer.paste(transformed, (paste_x, paste_y), transformed.getchannel("A"))
            clip_mask = Image.new("L", (canvas_w, canvas_h), 0)
            clip_draw = ImageDraw.Draw(clip_mask)
            clip_draw.rounded_rectangle(
                (vignette_x, vignette_y, vignette_x + vignette_w - 1, vignette_y + vignette_h - 1),
                radius=vignette_radius,
                fill=255,
            )
            poster_alpha = poster_layer.getchannel("A")
            poster_layer.putalpha(ImageChops.multiply(poster_alpha, clip_mask))
            canvas.alpha_composite(poster_layer)

        template = self._top_template_image(preset_id)
        if template is not None:
            if template.size != (canvas_w, canvas_h):
                template = template.resize((canvas_w, canvas_h), resample)
            canvas.alpha_composite(template)
        return canvas

    def _compose_canvas_from_preset(
        self,
        source_preset_id: str,
        target_size: Tuple[int, int],
        *,
        skip_logo: bool = False,
        log_upscale: bool = False,
        render_scale: float = 1.0,
        resample=Image.Resampling.LANCZOS,
        textbox_scale_factor: float = 1.0,
    ):
        if self._is_top_preset(source_preset_id):
            return self._compose_top_canvas(
                source_preset_id,
                render_scale=render_scale,
                resample=resample,
            )
        source_w, source_h = PRESETS[source_preset_id]["size"]
        preset_label = PRESETS[source_preset_id]["label"]
        target_w, target_h = target_size
        scale = max(0.02, min(1.0, float(render_scale)))
        canvas_w = max(1, int(round(target_w * scale)))
        canvas_h = max(1, int(round(target_h * scale)))
        pos_scale_x = canvas_w / max(1, source_w)
        pos_scale_y = canvas_h / max(1, source_h)
        canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

        for layer in RENDER_LAYER_ORDER:
            if skip_logo and layer == "logo":
                continue
            if not self._is_layer_allowed(source_preset_id, layer):
                continue
            layer_state = self._layer_state(source_preset_id, layer)
            if not layer_state["visible"]:
                continue

            rendered = self._render_layer_for_export(
                layer,
                source_preset_id,
                canvas_w=canvas_w,
                canvas_h=canvas_h,
                resample=resample,
            )
            if rendered is None:
                continue

            lw, lh = rendered.size
            if layer == "gradient":
                x = 0
                y = 0
            else:
                anchor = layer_state["transform"].get("anchor", "center")
                tx = layer_state["transform"]["x"] * pos_scale_x
                ty = layer_state["transform"]["y"] * pos_scale_y
                if anchor == "bottom_left_visible":
                    bbox = self._alpha_bbox_for_pil_image(rendered)
                    if bbox is None:
                        bbox_left = 0.0
                        bbox_bottom = float(lh)
                    else:
                        bbox_left, _bbox_top, _bbox_right, bbox_bottom = bbox
                    x = int(tx - bbox_left)
                    y = int(ty - bbox_bottom)
                else:
                    x = int(tx - lw / 2)
                    y = int(ty - lh / 2)
                if layer in CHARACTER_LAYERS:
                    x = int(tx - lw / 2)
                    y = int(ty - lh)

            if log_upscale and self.assets[layer].pil and layer not in {"logo", "gradient"}:
                sw, sh = self.assets[layer].pil.size
                upscale_ratio = max(lw / sw, lh / sh)
                if upscale_ratio > self.upscale_warning_ratio:
                    self._log(f"Avertissement upscale ({preset_label} / {layer}): x{upscale_ratio:.2f}")

            rendered_layer = rendered
            if layer_state["opacity"] < 1.0:
                rendered_layer = rendered.copy()
                alpha = rendered_layer.getchannel("A").point(
                    lambda px: int(px * layer_state["opacity"])
                )
                rendered_layer.putalpha(alpha)

            # Compose through an isolated layer then alpha-composite on canvas.
            # This keeps canvas alpha fully opaque when an opaque background already covers the preset.
            composed_layer = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
            composed_layer.paste(
                rendered_layer,
                (x, y),
                rendered_layer.getchannel("A"),
            )
            canvas.alpha_composite(composed_layer)

        textbox_draw = self._build_poster_textbox_render(
            source_preset_id,
            canvas_w,
            canvas_h,
            size_factor=textbox_scale_factor,
        )
        if textbox_draw is not None:
            textbox_img, textbox_x, textbox_y = textbox_draw
            canvas.alpha_composite(textbox_img, (textbox_x, textbox_y))
        return canvas

    def _compose_preset_canvas(
        self,
        preset_id: str,
        log_upscale: bool = False,
        render_scale: float = 1.0,
        resample=Image.Resampling.LANCZOS,
        textbox_scale_factor: float = 1.0,
    ):
        preset = PRESETS[preset_id]
        return self._compose_canvas_from_preset(
            preset_id,
            preset["size"],
            skip_logo=bool(preset.get("skip_logo")),
            log_upscale=log_upscale,
            render_scale=render_scale,
            resample=resample,
            textbox_scale_factor=textbox_scale_factor,
        )

    def _compose_export_target_canvas(self, export_id: str, log_upscale: bool = False):
        export_meta = EXPORT_TARGETS[export_id]
        source_preset = export_meta["source_preset"]
        if self._is_top_preset(source_preset):
            return self._compose_preset_canvas(
                source_preset,
                log_upscale=log_upscale,
            )
        return self._compose_canvas_from_preset(
            source_preset,
            export_meta["size"],
            skip_logo=bool(export_meta.get("skip_logo")),
            log_upscale=log_upscale,
        )

    def _build_preset_thumbnail_pixmap(
        self,
        preset_id: str,
        max_w: int | None = None,
        max_h: int | None = None,
    ):
        if max_w is None:
            max_w = max(80, self.presets_preview_box_width - 8)
        if max_h is None:
            max_h = max(50, self.presets_preview_box_height - 8)
        src_w, src_h = PRESETS[preset_id]["size"]
        if src_w <= 0 or src_h <= 0:
            return QPixmap()
        ratio = min(max_w / src_w, max_h / src_h)
        ratio = max(0.02, min(1.0, ratio))
        quality_scale = max(0.1, min(1.0, float(self.presets_preview_quality_scale)))
        render_ratio = max(0.01, min(1.0, ratio * quality_scale))
        target_w = max(1, int(round(src_w * ratio)))
        target_h = max(1, int(round(src_h * ratio)))
        try:
            textbox_scale = 0.25 if preset_id == "poster" else 1.0
            image = self._compose_preset_canvas(
                preset_id,
                log_upscale=False,
                render_scale=render_ratio,
                resample=Image.Resampling.BICUBIC,
                textbox_scale_factor=textbox_scale,
            )
        except Exception:
            return QPixmap()
        if image.size != (target_w, target_h):
            image = image.resize((target_w, target_h), Image.Resampling.BICUBIC)
        return self._pil_to_qpixmap(image)

    def _expanded_preset_ids(self, preset_ids):
        expanded: list[str] = []
        for preset_id in preset_ids:
            if preset_id not in PRESETS:
                continue
            expanded.append(preset_id)
            if preset_id == "poster":
                expanded.extend(TOP_PRESET_IDS)
        seen = set()
        ordered = []
        for preset_id in expanded:
            if preset_id in seen:
                continue
            seen.add(preset_id)
            ordered.append(preset_id)
        return ordered

    def _invalidate_presets_preview(self, preset_ids=None):
        if preset_ids is None:
            preset_ids = PRESETS.keys()
        for preset_id in self._expanded_preset_ids(preset_ids):
            if preset_id in PRESETS:
                self.preset_preview_dirty.add(preset_id)

    def _request_presets_preview_refresh(self, force: bool = False, preset_ids=None):
        if not hasattr(self, "preset_preview_labels"):
            return
        self._invalidate_presets_preview(preset_ids)
        if force:
            self.presets_preview_timer.stop()
            self.presets_preview_timer.start(0)
            return
        self.presets_preview_timer.start(self.presets_preview_interval_ms)

    def _refresh_presets_preview_borders(self):
        if not hasattr(self, "preset_preview_labels"):
            return
        for preset_id, label in self.preset_preview_labels.items():
            border_color = "#D78EF1" if preset_id == self.current_preset else "#5E5E66"
            label.setStyleSheet(
                f"border: 2px solid {border_color}; background-color: #1F1F24;"
            )

    def _refresh_presets_preview_strip(self):
        if not hasattr(self, "preset_preview_labels"):
            return
        if not self.preset_preview_dirty:
            self._refresh_presets_preview_borders()
            return
        if not self.preset_preview_queue:
            ordered_ids = [preset_id for preset_id in PRESETS if preset_id in self.preset_preview_dirty]
            if self.current_preset in ordered_ids:
                ordered_ids.remove(self.current_preset)
                ordered_ids.insert(0, self.current_preset)
            self.preset_preview_queue = ordered_ids
        if not self.presets_preview_worker_timer.isActive():
            self.presets_preview_worker_timer.start(0)

    def _process_next_preset_preview(self):
        if not hasattr(self, "preset_preview_labels"):
            return
        if not self.preset_preview_queue:
            self._refresh_presets_preview_borders()
            return
        preset_id = self.preset_preview_queue.pop(0)
        label = self.preset_preview_labels.get(preset_id)
        if label is None:
            self.preset_preview_dirty.discard(preset_id)
        else:
            pixmap = self._build_preset_thumbnail_pixmap(preset_id)
            if pixmap.isNull():
                label.setPixmap(QPixmap())
                label.setText("N/A")
            else:
                label.setText("")
                label.setPixmap(pixmap)
            self.preset_preview_dirty.discard(preset_id)
            border_color = "#D78EF1" if preset_id == self.current_preset else "#5E5E66"
            label.setStyleSheet(
                f"border: 2px solid {border_color}; background-color: #1F1F24;"
            )
        if self.preset_preview_queue:
            self.presets_preview_worker_timer.start(self.presets_preview_worker_interval_ms)

    def _preview_pixmap(self, layer_id: str, canvas_w: int, canvas_h: int) -> QPixmap:
        if layer_id == "gradient":
            gradient_img = self._build_gradient_image(canvas_w, canvas_h, self.current_preset)
            if gradient_img is None:
                return QPixmap()
            return self._pil_to_qpixmap(gradient_img)

        layer_state = self._layer_state(self.current_preset, layer_id)
        fit_mode = layer_state["fit_mode"]
        scale = layer_state["transform"]["scale"]

        if layer_id == "logo" and self._has_logo_text_source():
            base = self._build_logo_text_source_pixmap()
        else:
            base = self.assets[layer_id].pixmap

        if base is None or base.isNull():
            return QPixmap()

        src_w = base.width()
        src_h = base.height()
        if src_w == 0 or src_h == 0:
            return QPixmap()

        if fit_mode in {"cover", "crop"}:
            ratio = max(canvas_w / src_w, canvas_h / src_h)
        elif fit_mode == "contain":
            ratio = min(canvas_w / src_w, canvas_h / src_h)
        else:
            ratio = 1.0

        ratio *= scale
        target_w = max(1, int(src_w * ratio))
        target_h = max(1, int(src_h * ratio))
        rendered = base.scaled(
            target_w,
            target_h,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        if layer_id == "logo":
            return self._apply_logo_shadow_preview(rendered)
        return rendered

    def _select_export_dir(self):
        path = QFileDialog.getExistingDirectory(
            self,
            "Dossier d'export",
            str(self._recent_dir("export")),
        )
        if path:
            self.export_dir.setText(path)
            self._remember_recent_dir("export", path)

    def _selected_exports(self):
        if not hasattr(self, "export_checks"):
            return []
        return [
            export_id for export_id, check in self.export_checks.items() if check.isChecked()
        ]

    def _to_float(self, value, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _update_slider_value_labels(self):
        if hasattr(self, "opacity_value_label"):
            self.opacity_value_label.setText(str(int(self.opacity_slider.value())))
        if hasattr(self, "scale_value_label"):
            self.scale_value_label.setText(str(int(self.scale_slider.value())))

    def _sync_poster_textbox_controls(self):
        if not hasattr(self, "poster_textbox_check"):
            return
        self.poster_textbox_check.blockSignals(True)
        self.poster_textbox_check.setChecked(self.poster_textbox_enabled)
        self.poster_textbox_check.blockSignals(False)
        self.poster_textbox_input.blockSignals(True)
        self.poster_textbox_input.setText(self.poster_textbox_text)
        self.poster_textbox_input.blockSignals(False)

        allowed = self.current_preset == "poster"
        self.poster_textbox_check.setEnabled(allowed)
        self.poster_textbox_input.setEnabled(allowed and self.poster_textbox_enabled)

    def _sync_top_controls(self):
        if not hasattr(self, "top_sync_check"):
            return
        display_preset_id = self.current_preset if self._is_top_preset() else TOP_PRESET_IDS[0]
        config = self._top_config(display_preset_id)
        self.updating_ui = True
        try:
            self.top_sync_check.blockSignals(True)
            self.top_sync_check.setChecked(self.top_sync_all)
            self.top_sync_check.blockSignals(False)

            slider_pairs = [
                (self.top_offset_x_slider, self.top_offset_x_spin, int(config["offset_x"])),
                (self.top_offset_y_slider, self.top_offset_y_spin, int(config["offset_y"])),
                (self.top_zoom_slider, self.top_zoom_spin, int(config["zoom"])),
                (self.top_stretch_x_slider, self.top_stretch_x_spin, int(config["stretch_x"])),
                (self.top_stretch_y_slider, self.top_stretch_y_spin, int(config["stretch_y"])),
            ]
            for slider, spin, value in slider_pairs:
                slider.blockSignals(True)
                spin.blockSignals(True)
                slider.setValue(value)
                spin.setValue(value)
                slider.blockSignals(False)
                spin.blockSignals(False)
        finally:
            self.updating_ui = False

        enabled = self._is_top_preset()
        self.top_sync_check.setEnabled(enabled)
        for widget in [
            self.top_offset_x_slider,
            self.top_offset_x_spin,
            self.top_offset_y_slider,
            self.top_offset_y_spin,
            self.top_zoom_slider,
            self.top_zoom_spin,
            self.top_stretch_x_slider,
            self.top_stretch_x_spin,
            self.top_stretch_y_slider,
            self.top_stretch_y_spin,
            self.top_reset_btn,
        ]:
            widget.setEnabled(enabled)

    def _sync_logo_controls(self):
        self.logo_text_pending = self.logo_text
        if hasattr(self, "logo_text_input_timer"):
            self.logo_text_input_timer.stop()
        self.logo_text_checkbox.blockSignals(True)
        self.logo_text_checkbox.setChecked(self.logo_text_enabled)
        self.logo_text_checkbox.blockSignals(False)

        self.logo_text_input.blockSignals(True)
        self.logo_text_input.setPlainText(self.logo_text)
        self.logo_text_input.blockSignals(False)

        if hasattr(self, "logo_text_size_spin"):
            self.logo_text_size_spin.blockSignals(True)
            self.logo_text_size_spin.setValue(self.logo_text_size)
            self.logo_text_size_spin.blockSignals(False)

        self.logo_text_align_combo.blockSignals(True)
        align_idx = self.logo_text_align_combo.findData(self.logo_text_align)
        if align_idx >= 0:
            self.logo_text_align_combo.setCurrentIndex(align_idx)
        self.logo_text_align_combo.blockSignals(False)

        self.logo_text_upper_check.blockSignals(True)
        self.logo_text_upper_check.setChecked(self.logo_text_force_upper)
        self.logo_text_upper_check.blockSignals(False)

        self.logo_text_line_spacing_spin.blockSignals(True)
        self.logo_text_line_spacing_spin.setValue(self.logo_text_line_spacing)
        self.logo_text_line_spacing_spin.blockSignals(False)
        if hasattr(self, "logo_font_value_label"):
            self.logo_font_value_label.setText(self._logo_font_status_text())
        if hasattr(self, "logo_font_default_btn"):
            self.logo_font_default_btn.setEnabled(self._has_custom_logo_font())

        self.logo_shadow_check.blockSignals(True)
        self.logo_shadow_check.setChecked(self.logo_shadow_enabled)
        self.logo_shadow_check.blockSignals(False)

        self.logo_shadow_distance_slider.blockSignals(True)
        self.logo_shadow_distance_slider.setValue(self.logo_shadow_distance)
        self.logo_shadow_distance_slider.blockSignals(False)

        self.logo_shadow_blur_slider.blockSignals(True)
        self.logo_shadow_blur_slider.setValue(self.logo_shadow_blur)
        self.logo_shadow_blur_slider.blockSignals(False)

        self.logo_shadow_angle_slider.blockSignals(True)
        self.logo_shadow_angle_slider.setValue(int(self.logo_shadow_angle) % 360)
        self.logo_shadow_angle_slider.blockSignals(False)

        self.logo_shadow_opacity_slider.blockSignals(True)
        self.logo_shadow_opacity_slider.setValue(self.logo_shadow_opacity)
        self.logo_shadow_opacity_slider.blockSignals(False)

        if hasattr(self, "show_guides_check"):
            self.show_guides_check.blockSignals(True)
            self.show_guides_check.setChecked(self.guides_visible)
            self.show_guides_check.blockSignals(False)
        if hasattr(self, "poster_guide_combo"):
            self.poster_guide_combo.blockSignals(True)
            guide_idx = self.poster_guide_combo.findData(self.poster_guide_variant)
            if guide_idx >= 0:
                self.poster_guide_combo.setCurrentIndex(guide_idx)
            self.poster_guide_combo.blockSignals(False)
        self._sync_poster_textbox_controls()
        self._update_shadow_slider_labels()

    def _sync_gradient_controls(self):
        if not hasattr(self, "gradient_enable_check"):
            return

        config = self._gradient_config()

        self.gradient_enable_check.blockSignals(True)
        self.gradient_enable_check.setChecked(config["enabled"])
        self.gradient_enable_check.blockSignals(False)

        self.gradient_mode_combo.blockSignals(True)
        mode_idx = self.gradient_mode_combo.findData(config["mode"])
        if mode_idx >= 0:
            self.gradient_mode_combo.setCurrentIndex(mode_idx)
        self.gradient_mode_combo.blockSignals(False)

        self.gradient_direction_combo.blockSignals(True)
        dir_idx = self.gradient_direction_combo.findData(config["direction"])
        if dir_idx >= 0:
            self.gradient_direction_combo.setCurrentIndex(dir_idx)
        self.gradient_direction_combo.blockSignals(False)

        self.gradient_distance_slider.blockSignals(True)
        self.gradient_distance_slider.setValue(int(config["distance"]))
        self.gradient_distance_slider.blockSignals(False)

        self.gradient_stretch_slider.blockSignals(True)
        self.gradient_stretch_slider.setValue(int(config["stretch"]))
        self.gradient_stretch_slider.blockSignals(False)

        controls_enabled = config["enabled"]
        self.gradient_mode_combo.setEnabled(controls_enabled)
        self.gradient_direction_combo.setEnabled(controls_enabled)
        self.gradient_distance_slider.setEnabled(controls_enabled)
        self.gradient_stretch_slider.setEnabled(controls_enabled)
        self.gradient_color_a_btn.setEnabled(controls_enabled)
        self.gradient_color_b_btn.setEnabled(controls_enabled and config["mode"] == "double")
        self._update_gradient_slider_labels()

    def _guide_path_for_preset(self, preset_id: str):
        asset_dirs = [ASSET_GUIDES_DIR, ASSET_DIR]
        if preset_id == "poster":
            ordered = []
            for name in POSTER_GUIDE_FILES.get(self.poster_guide_variant, []):
                if name not in ordered:
                    ordered.append(name)
            for variant in ["1", "2"]:
                for name in POSTER_GUIDE_FILES.get(variant, []):
                    if name not in ordered:
                        ordered.append(name)
            for candidate_name in ordered:
                for asset_dir in asset_dirs:
                    candidate = asset_dir / candidate_name
                    if candidate.exists():
                        return candidate
            return None
        for candidate_name in GUIDE_FILE_PATTERNS.get(preset_id, []):
            for asset_dir in asset_dirs:
                candidate = asset_dir / candidate_name
                if candidate.exists():
                    return candidate
        return None

    def _color_bbox(self, image_rgb: Image.Image, rgb: Tuple[int, int, int], tolerance: int):
        color_layer = Image.new("RGB", image_rgb.size, rgb)
        diff = ImageChops.difference(image_rgb, color_layer)
        channel_r, channel_g, channel_b = diff.split()
        mask_r = channel_r.point(lambda value: 255 if value <= tolerance else 0)
        mask_g = channel_g.point(lambda value: 255 if value <= tolerance else 0)
        mask_b = channel_b.point(lambda value: 255 if value <= tolerance else 0)
        mask = ImageChops.multiply(mask_r, ImageChops.multiply(mask_g, mask_b))
        bbox = mask.getbbox()
        if bbox is None:
            return None
        x0, y0, x1, y1 = bbox
        if x1 <= x0 or y1 <= y0:
            return None
        return bbox

    def _extract_guide_regions(self, image_rgb: Image.Image):
        width, height = image_rgb.size
        regions: Dict[str, Tuple[float, float, float, float]] = {}
        for layer_id, color in GUIDE_COLOR_MAP.items():
            bbox = self._color_bbox(image_rgb, color, GUIDE_COLOR_TOLERANCE)
            if bbox is None:
                continue
            x0, y0, x1, y1 = bbox
            regions[layer_id] = (float(x0), float(y0), float(x1 - x0), float(y1 - y0))
        if "background" not in regions:
            regions["background"] = (0.0, 0.0, float(width), float(height))
        return regions

    def _load_guides(self):
        self.guide_pixmaps = {}
        self.guide_regions = {}
        for preset_id, meta in PRESETS.items():
            if preset_id == "logo" or self._is_top_preset(preset_id):
                continue
            guide_path = self._guide_path_for_preset(preset_id)
            if guide_path is None:
                continue
            try:
                canvas_w, canvas_h = meta["size"]
                guide_rgb = Image.open(guide_path).convert("RGB")
                if guide_rgb.size != (canvas_w, canvas_h):
                    guide_rgb = guide_rgb.resize((canvas_w, canvas_h), Image.Resampling.LANCZOS)
                self.guide_regions[preset_id] = self._extract_guide_regions(guide_rgb)
                self.guide_pixmaps[preset_id] = self._pil_to_qpixmap(guide_rgb.convert("RGBA"))
            except Exception as exc:
                self._log(f"Avertissement: gabarit non charge ({guide_path.name}): {exc}")
        self._refresh_guide_overlay(*PRESETS[self.current_preset]["size"])

    def _guide_region_for_layer(self, preset_id: str, layer_id: str):
        regions = self.guide_regions.get(preset_id, {})
        key = "character" if layer_id in CHARACTER_LAYERS else layer_id
        return regions.get(key)

    def _refresh_guide_overlay(self, canvas_w: int, canvas_h: int):
        if not hasattr(self, "guide_item"):
            return
        if not self.guides_visible or self.current_preset == "logo" or self._is_top_preset():
            self.guide_item.setVisible(False)
            return
        guide_pixmap = self.guide_pixmaps.get(self.current_preset)
        if guide_pixmap is None or guide_pixmap.isNull():
            self.guide_item.setVisible(False)
            return
        if guide_pixmap.width() != canvas_w or guide_pixmap.height() != canvas_h:
            draw_pixmap = guide_pixmap.scaled(
                canvas_w,
                canvas_h,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        else:
            draw_pixmap = guide_pixmap
        self.guide_item.setPixmap(draw_pixmap)
        self.guide_item.setOffset(0, 0)
        self.guide_item.setPos(0, 0)
        self.guide_item.setOpacity(self.guides_opacity)
        self.guide_item.setVisible(True)

    def _apply_guide_auto_placement(
        self,
        layer_id: str,
        preset_id: str,
        layer_pixmap: QPixmap,
    ) -> bool:
        region = self._guide_region_for_layer(preset_id, layer_id)
        if region is None:
            return False
        box_x, box_y, box_w, box_h = region
        if box_w <= 1 or box_h <= 1:
            return False
        src_w = max(1, layer_pixmap.width())
        src_h = max(1, layer_pixmap.height())
        visible_box = self._layer_visible_box(layer_id)
        if visible_box is None:
            visible_left = 0.0
            visible_top = 0.0
            visible_right = float(src_w)
            visible_bottom = float(src_h)
        else:
            visible_left, visible_top, visible_right, visible_bottom = visible_box
        visible_w = max(1.0, visible_right - visible_left)
        visible_h = max(1.0, visible_bottom - visible_top)
        canvas_w, canvas_h = PRESETS[preset_id]["size"]
        base_ratio = min(canvas_w / src_w, canvas_h / src_h)
        if base_ratio <= 0:
            return False
        if layer_id in CHARACTER_LAYERS:
            target_height = max(1.0, canvas_h - box_y)
            loaded_layers = self._loaded_character_layers()
            if len(loaded_layers) > 1:
                layout_items = []
                for loaded_layer_id in loaded_layers:
                    loaded_pixmap = self.assets[loaded_layer_id].pixmap
                    if loaded_pixmap is None or loaded_pixmap.isNull():
                        continue
                    loaded_w = max(1, loaded_pixmap.width())
                    loaded_h = max(1, loaded_pixmap.height())
                    loaded_visible_box = self._layer_visible_box(loaded_layer_id)
                    if loaded_visible_box is None:
                        loaded_left = 0.0
                        loaded_top = 0.0
                        loaded_right = float(loaded_w)
                        loaded_bottom = float(loaded_h)
                    else:
                        loaded_left, loaded_top, loaded_right, loaded_bottom = loaded_visible_box
                    loaded_visible_w = max(1.0, loaded_right - loaded_left)
                    loaded_visible_h = max(1.0, loaded_bottom - loaded_top)
                    loaded_ratio = min(canvas_w / loaded_w, canvas_h / loaded_h)
                    if loaded_ratio <= 0:
                        continue
                    loaded_scale = max(0.01, target_height / (loaded_visible_h * loaded_ratio))
                    visible_rendered_w = loaded_visible_w * loaded_ratio * loaded_scale
                    visible_center_offset_x = (
                        (((loaded_left + loaded_right) * 0.5) - (loaded_w * 0.5))
                        * loaded_ratio
                        * loaded_scale
                    )
                    bottom_gap = (loaded_h - loaded_bottom) * loaded_ratio * loaded_scale
                    layout_items.append(
                        {
                            "layer_id": loaded_layer_id,
                            "base_scale": loaded_scale,
                            "visible_rendered_w": visible_rendered_w,
                            "visible_center_offset_x": visible_center_offset_x,
                            "bottom_gap": bottom_gap,
                        }
                    )

                if len(layout_items) > 1:
                    spacing_factor = max(0.56, 0.84 - (0.07 * len(layout_items)))
                    centers = [0.0]
                    for prev_item, next_item in zip(layout_items, layout_items[1:]):
                        distance = (
                            (prev_item["visible_rendered_w"] + next_item["visible_rendered_w"]) * 0.5
                        ) * spacing_factor
                        centers.append(centers[-1] + distance)

                    span_left = min(
                        center - (item["visible_rendered_w"] * 0.5)
                        for center, item in zip(centers, layout_items)
                    )
                    span_right = max(
                        center + (item["visible_rendered_w"] * 0.5)
                        for center, item in zip(centers, layout_items)
                    )
                    span_width = max(1.0, span_right - span_left)
                    max_span = max(box_w * 2.6, canvas_w * 1.15)
                    shrink_ratio = min(1.0, max_span / span_width)

                    scaled_centers = [center * shrink_ratio for center in centers]
                    scaled_left = min(
                        center - ((item["visible_rendered_w"] * shrink_ratio) * 0.5)
                        for center, item in zip(scaled_centers, layout_items)
                    )
                    scaled_right = max(
                        center + ((item["visible_rendered_w"] * shrink_ratio) * 0.5)
                        for center, item in zip(scaled_centers, layout_items)
                    )
                    group_center = (scaled_left + scaled_right) * 0.5
                    x_shift = (box_x + (box_w * 0.5)) - group_center

                    for center, item in zip(scaled_centers, layout_items):
                        state = self._layer_state(preset_id, item["layer_id"])
                        scaled_offset_x = item["visible_center_offset_x"] * shrink_ratio
                        scaled_bottom_gap = item["bottom_gap"] * shrink_ratio
                        state["fit_mode"] = "contain"
                        state["transform"]["anchor"] = "bottom"
                        state["transform"]["scale"] = max(
                            0.01,
                            item["base_scale"] * shrink_ratio,
                        )
                        state["transform"]["x"] = (center + x_shift) - scaled_offset_x
                        state["transform"]["y"] = canvas_h + scaled_bottom_gap
                    return True

            # Keep character top at yellow-circle top and force bottom to touch canvas bottom.
            layer_state = self._layer_state(preset_id, layer_id)
            target_scale = max(0.01, target_height / (visible_h * base_ratio))
            visible_center_offset_x = (((visible_left + visible_right) * 0.5) - (src_w * 0.5)) * base_ratio * target_scale
            bottom_gap = (src_h - visible_bottom) * base_ratio * target_scale
            layer_state["fit_mode"] = "contain"
            layer_state["transform"]["x"] = (box_x + (box_w * 0.5)) - visible_center_offset_x
            layer_state["transform"]["anchor"] = "bottom"
            layer_state["transform"]["scale"] = target_scale
            layer_state["transform"]["y"] = canvas_h + bottom_gap
            return True

        layer_state = self._layer_state(preset_id, layer_id)
        if layer_id == "logo":
            target_total_ratio = min(box_w / visible_w, box_h / visible_h)
            target_scale = max(0.01, target_total_ratio / base_ratio)
            visible_center_offset_x = (
                (((visible_left + visible_right) * 0.5) - (src_w * 0.5))
                * base_ratio
                * target_scale
            )
            visible_center_offset_y = (
                (((visible_top + visible_bottom) * 0.5) - (src_h * 0.5))
                * base_ratio
                * target_scale
            )
            layer_state["fit_mode"] = "contain"
            layer_state["transform"]["anchor"] = "center"
            layer_state["transform"]["scale"] = target_scale
            layer_state["transform"]["x"] = (box_x + (box_w * 0.5)) - visible_center_offset_x
            layer_state["transform"]["y"] = (box_y + (box_h * 0.5)) - visible_center_offset_y
            return True

        region_ratio = min(box_w / src_w, box_h / src_h)
        layer_state["fit_mode"] = "contain"
        layer_state["transform"]["x"] = box_x + (box_w * 0.5)
        target_scale = max(0.01, region_ratio / base_ratio)
        layer_state["transform"]["anchor"] = "center"
        layer_state["transform"]["scale"] = target_scale
        layer_state["transform"]["y"] = box_y + (box_h * 0.5)
        return True

    def _snapshot_file_name(self, base_name: str | None = None) -> str:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        if base_name is None:
            safe_base = self._sanitize_base_name(self.base_name_input.text())
        else:
            safe_base = self._sanitize_base_name(base_name)
        return f"{stamp}-{safe_base}.arplus.json"

    def _project_snapshot_payload(self):
        return {
            "schema_version": 1,
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "program_root": str(self.program_root),
            "current_preset": self.current_preset,
            "export_id": self._metadata_id(),
            "export_dir": self.export_dir.text() if hasattr(self, "export_dir") else "",
            "base_name": self.base_name_input.text(),
            "selected_exports": self._selected_exports(),
            "assets": {
                layer: {"path": asset.path, "loaded": bool(asset.path)}
                for layer, asset in self.assets.items()
            },
            "top": {
                "sync_all": self.top_sync_all,
                "settings": copy.deepcopy(self.top_settings),
            },
            "logo_text": {
                "enabled": self.logo_text_enabled,
                "text": self.logo_text,
                "size": self.logo_text_size,
                "align": self.logo_text_align,
                "force_upper": self.logo_text_force_upper,
                "line_spacing": self.logo_text_line_spacing,
                "color": self.logo_text_color,
                "font_name": self.logo_text_font_name,
                "font_page_url": self.logo_text_font_page_url,
                "font_download_url": self.logo_text_font_download_url,
                "font_file": self.logo_text_font_file,
            },
            "poster_textbox": {
                "enabled": self.poster_textbox_enabled,
                "text": self.poster_textbox_text,
            },
            "logo_shadow": {
                "enabled": self.logo_shadow_enabled,
                "distance": self.logo_shadow_distance,
                "blur": self.logo_shadow_blur,
                "angle": self.logo_shadow_angle,
                "opacity": self.logo_shadow_opacity,
                "color": self.logo_shadow_color,
            },
            "gradient": {
                preset_id: dict(self._gradient_config(preset_id))
                for preset_id in PRESETS
            },
            "guides": {
                "visible": self.guides_visible,
                "opacity": self.guides_opacity,
                "poster_variant": self.poster_guide_variant,
            },
            "state": copy.deepcopy(self.state),
        }

    def _write_project_snapshot(self, save_path: Path) -> Path:
        payload = self._project_snapshot_payload()
        out_path = save_path.expanduser()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return out_path

    def _autosave_project_snapshot(self, base_name: str) -> Path:
        self.autosave_dir.mkdir(parents=True, exist_ok=True)
        return self._write_project_snapshot(self.autosave_dir / self._snapshot_file_name(base_name))

    def _save_project_snapshot_as(self):
        default_dir = self._recent_dir("save_project")
        if not default_dir.exists():
            default_dir = self.program_root
        suggested = default_dir / self._snapshot_file_name()
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Sauvegarder l'etat projet",
            str(suggested),
            "ARPlus Save (*.arplus.json);;JSON (*.json)",
        )
        if not file_path:
            return
        out_path = Path(file_path).expanduser()
        if out_path.suffix.lower() != ".json":
            out_path = out_path.with_suffix(".json")
        self._remember_recent_dir("save_project", out_path.parent)
        self._remember_recent_dir("load_project", out_path.parent)
        try:
            saved_path = self._write_project_snapshot(out_path)
        except Exception as exc:
            self._log(f"Erreur sauvegarde projet: {exc}")
            QMessageBox.critical(self, "Erreur", f"Impossible de sauvegarder: {exc}")
            return
        self._log(f"Sauvegarde projet: {saved_path}")

    def _snapshot_payload_to_restore_snapshot(self, payload):
        if not isinstance(payload, dict):
            raise RuntimeError("Fichier projet invalide.")

        payload_assets = payload.get("assets", {})
        asset_paths = {}
        if isinstance(payload_assets, dict):
            for layer_id in LAYER_ORDER:
                raw_asset = payload_assets.get(layer_id, "")
                if isinstance(raw_asset, dict):
                    asset_paths[layer_id] = str(raw_asset.get("path", "") or "")
                elif isinstance(raw_asset, str):
                    asset_paths[layer_id] = raw_asset
                else:
                    asset_paths[layer_id] = ""

        return {
            "current_preset": payload.get("current_preset", "poster"),
            "active_layer": payload.get("active_layer", self.active_layer),
            "state": copy.deepcopy(payload.get("state", self.state)),
            "assets": asset_paths,
            "selected_exports": payload.get("selected_exports", []),
            "export_dir": payload.get("export_dir", self.export_dir.text() if hasattr(self, "export_dir") else ""),
            "guides": payload.get("guides", {}),
            "gradient": copy.deepcopy(payload.get("gradient", self.gradient_settings)),
            "top": copy.deepcopy(payload.get("top", {})),
            "logo_text": copy.deepcopy(payload.get("logo_text", {})),
            "poster_textbox": copy.deepcopy(payload.get("poster_textbox", {})),
            "logo_shadow": copy.deepcopy(payload.get("logo_shadow", {})),
            "metadata_id": payload.get("metadata_id", payload.get("export_id", "")),
            "base_name": payload.get("base_name", "Name"),
        }

    def _load_project_snapshot_from_path(self, file_path: Path):
        snapshot_path = file_path.expanduser()
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
        restore_snapshot = self._snapshot_payload_to_restore_snapshot(payload)

        base_name = self._sanitize_base_name(self.base_name_input.text())
        try:
            autosafe_path = self._autosave_project_snapshot(f"{base_name}-before-import")
            self._log(f"Autosafe avant import projet: {autosafe_path}")
        except Exception as exc:
            self._log(f"Erreur autosafe avant import projet: {exc}")

        self._push_undo_state()
        self._restore_undo_snapshot(restore_snapshot)
        self._remember_recent_dir("load_project", snapshot_path.parent)
        self._log(f"Projet importe: {snapshot_path}")

    def _load_project_snapshot_from_dialog(self):
        default_dir = self._recent_dir("load_project")
        if not default_dir.exists():
            default_dir = self._recent_dir("save_project")
        if not default_dir.exists():
            default_dir = self.program_root
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Importer un projet ARPlus",
            str(default_dir),
            "ARPlus Save (*.arplus.json *.json);;JSON (*.json)",
        )
        if not file_path:
            return
        try:
            self._load_project_snapshot_from_path(Path(file_path))
        except Exception as exc:
            self._log(f"Erreur import projet: {exc}")
            QMessageBox.critical(self, "Erreur", f"Impossible d'importer le projet: {exc}")

    def _set_all_exports_checked(self, checked: bool):
        if not hasattr(self, "export_checks"):
            return
        for check in self.export_checks.values():
            check.setChecked(checked)

    def _new_project(self):
        answer = QMessageBox.question(
            self,
            "Nouveau projet",
            "Creer un nouveau projet ?\nUne sauvegarde autosafe sera faite avant de vider les visuels.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._push_undo_state()

        base_name = self._sanitize_base_name(self.base_name_input.text())
        try:
            autosafe_path = self._autosave_project_snapshot(f"{base_name}-new-project")
            self._log(f"Autosafe avant nouveau projet: {autosafe_path}")
        except Exception as exc:
            self._log(f"Erreur autosafe avant nouveau projet: {exc}")

        self.assets = {layer: LayerAsset() for layer in LAYER_ORDER}
        self.state = self._build_default_state()
        self.current_preset = "poster"
        self.active_layer = "background"

        self.logo_text_enabled = False
        self.logo_text = ""
        self.logo_text_size = 300
        self.logo_text_align = "center"
        self.logo_text_force_upper = True
        self.logo_text_line_spacing = 100
        self.logo_text_color = "#FFFFFF"
        self.logo_text_font_name = ""
        self.logo_text_font_page_url = ""
        self.logo_text_font_download_url = ""
        self.logo_text_font_file = ""
        self.poster_textbox_enabled = True
        self.poster_textbox_text = "TEXTE BOX"
        self.logo_shadow_enabled = False
        self.logo_shadow_distance = 5
        self.logo_shadow_blur = 5
        self.logo_shadow_angle = 135
        self.logo_shadow_opacity = 60
        self.logo_shadow_color = "#000000"
        self.gradient_settings = {
            preset_id: self._default_gradient_config() for preset_id in PRESETS
        }
        self.top_settings = {
            preset_id: self._default_top_config() for preset_id in TOP_PRESET_IDS
        }
        self.top_sync_all = False
        self.guides_visible = True
        self.guides_opacity = GUIDE_OPACITY_DEFAULT
        self.poster_guide_variant = "1"

        self.metadata_id_input.setText("")
        self.base_name_input.setText("Name")
        self._set_all_exports_checked(True)
        self._sync_logo_controls()
        self._sync_gradient_controls()
        self._sync_top_controls()
        self._load_guides()

        preset_index = self.preset_combo.findData(self.current_preset)
        if preset_index >= 0:
            self.preset_combo.blockSignals(True)
            self.preset_combo.setCurrentIndex(preset_index)
            self.preset_combo.blockSignals(False)
        self._refresh_presets_preview_borders()

        self._set_active_layer("background", sync=False)
        self._invalidate_presets_preview()
        self._set_scene_for_preset(self.current_preset)
        self._refresh_preview()
        self._sync_layer_controls()
        self._sync_poster_textbox_controls()
        self._log("Nouveau projet initialise (visuels supprimes).")

    def _alpha_has_transparent_edge(self, alpha_channel: Image.Image) -> bool:
        width, height = alpha_channel.size
        if width <= 0 or height <= 0:
            return False
        edges = [
            alpha_channel.crop((0, 0, width, 1)),
            alpha_channel.crop((0, height - 1, width, height)),
            alpha_channel.crop((0, 0, 1, height)),
            alpha_channel.crop((width - 1, 0, width, height)),
        ]
        return any(edge.getextrema()[0] < 255 for edge in edges)

    def _collect_transparency_issues(self, export_ids: list[str]) -> list[str]:
        issues: list[str] = []
        for export_id in export_ids:
            if export_id == "logo":
                continue
            export_meta = EXPORT_TARGETS[export_id]
            try:
                canvas = self._compose_export_target_canvas(export_id, log_upscale=False)
            except Exception as exc:
                self._log(f"Erreur controle transparence ({export_id}): {exc}")
                issues.append(f"{export_meta['label']} (analyse impossible)")
                continue

            alpha_channel = canvas.getchannel("A")
            if alpha_channel.getextrema()[0] >= 255:
                continue
            if self._alpha_has_transparent_edge(alpha_channel):
                issues.append(f"{export_meta['label']} (bords/cadre transparents)")
            else:
                issues.append(f"{export_meta['label']} (zone transparente)")
        return issues

    def _export_selected(self):
        selected = self._selected_exports()
        if not selected:
            QMessageBox.warning(self, "Attention", "Sélectionnez au moins un preset d'export.")
            return

        exports_to_validate = [
            export_id for export_id in selected if export_id in TRANSPARENCY_VALIDATE_EXPORTS
        ]
        transparency_issues = self._collect_transparency_issues(exports_to_validate)
        if transparency_issues:
            warning_lines = "\n".join(f"- {label}" for label in transparency_issues)
            self._log("Export annule: transparence detectee sur presets non-logo.")
            QMessageBox.warning(
                self,
                "Transparence detectee",
                "Export annule.\nUne partie du canvas est transparente sur:\n"
                + warning_lines
                + "\n\nCorrigez le background ou le cadrage, puis relancez.",
            )
            self.progress.setValue(0)
            return

        export_dir = Path(self.export_dir.text()).expanduser()
        export_dir.mkdir(parents=True, exist_ok=True)
        self._remember_recent_dir("export", export_dir)

        base_name = self._sanitize_base_name(self.base_name_input.text())
        self.progress.setValue(0)
        total = len(selected)
        exported_paths: dict[str, Path] = {}
        try:
            autosafe_path = self._autosave_project_snapshot(base_name)
            self._log(f"Autosafe projet: {autosafe_path}")
        except Exception as exc:
            self._log(f"Erreur autosafe projet: {exc}")

        for idx, export_id in enumerate(selected, start=1):
            try:
                exported_paths[export_id] = self._export_target(export_id, export_dir, base_name)
            except Exception as exc:
                self._log(f"Erreur export {export_id}: {exc}")
            self.progress.setValue(int((idx / total) * 100))

        if exported_paths:
            try:
                self._write_metadata_file(export_dir, exported_paths)
            except Exception as exc:
                self._log(f"Erreur metadata.json: {exc}")
        self._log("Export terminé.")

    def _export_target_output_path(self, export_id: str, export_dir: Path, base_name: str) -> Path:
        export_meta = EXPORT_TARGETS[export_id]
        ext = "png" if export_meta.get("png") else "jpg"
        if export_id in TOP_EXPORT_IDS:
            top_number = PRESETS[export_meta["source_preset"]]["top_number"]
            safe_title = re.sub(r'[\\/:*?"<>|]', "-", base_name).strip() or "export"
            date_suffix = datetime.now().strftime("%Y-%m-%d")
            return export_dir / f"TOP {top_number} - {safe_title} - {date_suffix}.{ext}"
        return export_dir / f"{export_meta['file_stub']}-{base_name}.{ext}"

    def _export_target(self, export_id: str, export_dir: Path, base_name: str) -> Path:
        export_meta = EXPORT_TARGETS[export_id]
        canvas = self._compose_export_target_canvas(export_id, log_upscale=True)
        out_path = self._export_target_output_path(export_id, export_dir, base_name)
        ext = "png" if export_meta.get("png") else "jpg"
        if ext == "jpg":
            canvas.convert("RGB").save(out_path, quality=95)
        else:
            canvas.save(out_path)
        self._log(f"Export {export_meta['label']}: {out_path}")
        return out_path

    def _render_layer_for_export(
        self,
        layer_id: str,
        preset_id: str,
        canvas_w: int | None = None,
        canvas_h: int | None = None,
        resample=Image.Resampling.LANCZOS,
    ):
        if canvas_w is None or canvas_h is None:
            preset_meta = PRESETS[preset_id]
            canvas_w, canvas_h = preset_meta["size"]
        if layer_id == "gradient":
            return self._build_gradient_image(canvas_w, canvas_h, preset_id)

        state = self._layer_state(preset_id, layer_id)
        fit_mode = state["fit_mode"]
        scale = state["transform"]["scale"]

        if layer_id == "logo" and self._has_logo_text_source():
            source = self._build_logo_text_source_image()
        else:
            source = self.assets[layer_id].pil

        if source is None:
            return None

        sw, sh = source.size
        if sw == 0 or sh == 0:
            return None

        if fit_mode in {"cover", "crop"}:
            ratio = max(canvas_w / sw, canvas_h / sh)
        elif fit_mode == "contain":
            ratio = min(canvas_w / sw, canvas_h / sh)
        else:
            ratio = 1.0
        ratio *= scale

        target_size = (max(1, int(sw * ratio)), max(1, int(sh * ratio)))
        rendered = source.resize(target_size, resample)
        if layer_id == "logo":
            return self._apply_logo_shadow_pil(rendered)
        return rendered

    def _load_logo_font(self, size: int | None = None):
        font_size = size if size is not None else self.logo_text_size
        selected_font_path = self._selected_logo_font_path()
        if selected_font_path is not None:
            try:
                return ImageFont.truetype(str(selected_font_path), font_size)
            except OSError:
                pass
        font_candidates = [
            "Montserrat-Bold.ttf",
            "/usr/share/fonts/truetype/montserrat/Montserrat-Bold.ttf",
            "/Library/Fonts/Montserrat-Bold.ttf",
            "C:/Windows/Fonts/montserrat-bold.ttf",
        ]
        for candidate in font_candidates:
            try:
                return ImageFont.truetype(candidate, font_size)
            except OSError:
                continue
        self._log("Avertissement: Montserrat Bold introuvable, police de secours utilisée.")
        return ImageFont.load_default()

    def _metadata_title(self) -> str:
        title = self.base_name_input.text().strip()
        return title or "Name"

    def _metadata_id(self) -> str:
        if not hasattr(self, "metadata_id_input"):
            return ""
        return self.metadata_id_input.text().strip()

    def _write_metadata_file(self, export_dir: Path, exported_paths: dict[str, Path]) -> Path:
        exports_payload = {}
        for export_id, out_path in exported_paths.items():
            export_meta = EXPORT_TARGETS[export_id]
            exports_payload[export_meta["metadata_key"]] = str(out_path.resolve())

        payload = {
            "id": self._metadata_id(),
            "title": self._metadata_title(),
            "exports": exports_payload,
        }
        metadata_path = export_dir / "metadata.json"
        metadata_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return metadata_path


    def _sanitize_base_name(self, raw_name: str) -> str:
        name = (raw_name or "").strip()
        cleaned = "".join(ch for ch in name if ch not in '<>:"/\\|?*')
        cleaned = cleaned.strip().strip(".")
        return cleaned or "Name"


def main():
    app = QApplication(sys.argv)
    app_icon_path = next(
        (
            path
            for path in [
                ASSET_LOGO_DIR / "arplus.ico",
                ASSET_LOGO_DIR / "arplus.png",
                ASSET_DIR / "icon.ico",
                ASSET_DIR / "icon.png",
            ]
            if path.exists()
        ),
        ASSET_LOGO_DIR / "arplus.ico",
    )
    if app_icon_path.exists():
        app_icon = QIcon(str(app_icon_path))
        if not app_icon.isNull():
            app.setWindowIcon(app_icon)
    window = ARPlusWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

