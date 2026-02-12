import copy
import json
import math
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Dict, Tuple

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
from PySide6.QtCore import QBuffer, QIODevice, QObject, QPointF, Qt, Signal, QTimer
from PySide6.QtGui import QColor, QFontMetrics, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFileDialog,
    QFormLayout,
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
    QVBoxLayout,
    QWidget,
)

LAYER_ORDER = ["background", "character", "gradient", "logo", "fx"]

GUIDE_COLOR_MAP = {
    "background": (254, 67, 218),
    "character": (248, 255, 51),
    "logo": (62, 195, 52),
}
GUIDE_COLOR_TOLERANCE = 40
GUIDE_OPACITY_DEFAULT = 0.25
POSTER_GUIDE_FILES = {
    "1": [
        "visuel-Poster-1600x2400-gabarit-1.jpg",
        "visuel-Poster-1600x2400-gabarit.jpg",
    ],
    "2": [
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
        "FullScreen+Logo-APPTV-3480x876-gabarit.jpg",
        "FullScreen+Logo-3480x876-gabarit.jpg",
    ],
    "hero": [
        "Hero-Banner-2240x672-gabarit.jpg",
    ],
    "background": [
        "visuel-Background-3840x2160-gabarit.jpg",
    ],
    "background_no_logo": [
        "visuel-Background-no-logo-3840x2160-gabarit.jpg",
    ],
}

PRESETS = {
    "poster": {"label": "Poster", "size": (1600, 2400), "filename": "Poster_1600x2400"},
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


@dataclass
class LayerAsset:
    path: str = ""
    pixmap: QPixmap | None = None
    pil: Image.Image | None = None


class SignalEmitter(QObject):
    moved = Signal(str, float, float)
    clicked = Signal(str)


class LayerGraphicsItem(QGraphicsPixmapItem):
    def __init__(self, layer_id: str):
        super().__init__()
        self.layer_id = layer_id
        self.signal_emitter = SignalEmitter()
        self.moved = self.signal_emitter.moved
        self.clicked = self.signal_emitter.clicked
        self.setFlag(QGraphicsPixmapItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsPixmapItem.GraphicsItemFlag.ItemSendsScenePositionChanges, True)
        self.setTransformationMode(Qt.TransformationMode.SmoothTransformation)

    def itemChange(self, change, value):
        if change == QGraphicsPixmapItem.GraphicsItemChange.ItemPositionHasChanged:
            pos = self.pos()
            self.signal_emitter.moved.emit(self.layer_id, pos.x(), pos.y())
        return super().itemChange(change, value)

    def mousePressEvent(self, event):
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
        self.logo_text_size = 300
        self.logo_text_align = "center"
        self.logo_text_force_upper = True
        self.logo_text_line_spacing = 100
        self.logo_text_color = "#FFFFFF"
        self.poster_textbox_enabled = True
        self.poster_textbox_text = "TEXTE BOX"
        self.logo_shadow_enabled = False
        self.logo_shadow_distance = 16
        self.logo_shadow_blur = 12
        self.logo_shadow_angle = 135
        self.logo_shadow_opacity = 60
        self.logo_shadow_color = "#000000"
        self.gradient_enabled = False
        self.gradient_mode = "single"
        self.gradient_direction = "top"
        self.gradient_color_a = "#000000"
        self.gradient_color_b = "#FFFFFF"
        self.gradient_distance = 40
        self.gradient_stretch = 100
        self.guides_visible = True
        self.guides_opacity = GUIDE_OPACITY_DEFAULT
        self.poster_guide_variant = "1"
        self.upscale_warning_ratio = 1.75
        self.presets_preview_interval_ms = 2400
        self.presets_preview_worker_interval_ms = 12
        self.presets_preview_box_width = 300
        self.presets_preview_box_height = 170
        self.presets_preview_quality_scale = 0.45
        self.current_preset = "poster"
        self.active_layer = "background"
        self.updating_ui = False
        self.program_root = Path(__file__).resolve().parent
        self.autosave_dir = self.program_root / "autosafe"
        self.guide_pixmaps: Dict[str, QPixmap] = {}
        self.guide_regions: Dict[str, Dict[str, Tuple[float, float, float, float]]] = {}
        self.preset_preview_dirty: set[str] = set(PRESETS.keys())
        self.preset_preview_queue: list[str] = []
        app_icon_path = self.program_root / "asset" / "icon.ico"
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
        for layer in ["background", "character", "gradient", "logo"]:
            item = LayerGraphicsItem(layer)
            if layer == "gradient":
                item.setFlag(QGraphicsPixmapItem.GraphicsItemFlag.ItemIsMovable, False)
            item.moved.connect(self._on_layer_moved)
            item.clicked.connect(self._on_layer_clicked)
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

        self.frame_item = QGraphicsRectItem()
        frame_pen = QPen(Qt.PenStyle.NoPen)
        self.frame_item.setPen(frame_pen)
        self.frame_item.setBrush(Qt.BrushStyle.NoBrush)
        self.frame_item.setZValue(10_000)
        self.scene.addItem(self.frame_item)

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

    def _build_default_state(self):
        state = {}
        for preset_id, meta in PRESETS.items():
            width, height = meta["size"]
            state[preset_id] = {layer: self._build_default_layer() for layer in LAYER_ORDER}
            state[preset_id]["background"]["fit_mode"] = "crop"
            state[preset_id]["character"]["fit_mode"] = "contain"
            state[preset_id]["character"]["transform"]["anchor"] = "bottom"
            state[preset_id]["gradient"]["fit_mode"] = "stretch"
            state[preset_id]["gradient"]["transform"]["x"] = width * 0.5
            state[preset_id]["gradient"]["transform"]["y"] = height * 0.5
            state[preset_id]["gradient"]["transform"]["scale"] = 1.0
            state[preset_id]["logo"]["fit_mode"] = "contain"
            state[preset_id]["logo"]["transform"]["x"] = width * 0.5
            state[preset_id]["logo"]["transform"]["y"] = height * 0.5
            state[preset_id]["logo"]["transform"]["scale"] = 1.0
        return state

    def _build_ui(self):
        root = QWidget(self)
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        top_layout = QHBoxLayout()

        self.left_panel = self._build_left_panel()
        self.left_panel.setMinimumWidth(380)
        self.left_scroll = QScrollArea()
        self.left_scroll.setWidgetResizable(True)
        self.left_scroll.setWidget(self.left_panel)
        self.left_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        top_layout.addWidget(self.left_scroll, 1)

        center = QVBoxLayout()
        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Preset en aperçu:"))
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
        side_width = max(300, min(460, int(total_width * 0.24)))
        self.left_scroll.setMinimumWidth(side_width)
        self.left_scroll.setMaximumWidth(side_width)
        self.right_scroll.setMinimumWidth(side_width)
        self.right_scroll.setMaximumWidth(side_width)

    def _build_left_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)

        resources_box = QGroupBox("Ressources")
        resources_layout = QVBoxLayout(resources_box)
        import_box = QGroupBox("Importer")
        import_layout = QVBoxLayout(import_box)
        bg_btn = QPushButton("Importer Background")
        bg_btn.clicked.connect(lambda: self._import_layer("background"))
        char_btn = QPushButton("Importer Personnage")
        char_btn.clicked.connect(lambda: self._import_layer("character"))
        logo_btn = QPushButton("Importer Logo")
        logo_btn.clicked.connect(lambda: self._import_layer("logo"))
        import_layout.addWidget(bg_btn)
        import_layout.addWidget(char_btn)
        import_layout.addWidget(logo_btn)
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
        self.logo_text_size_spin = QSpinBox()
        self.logo_text_size_spin.setRange(12, 600)
        self.logo_text_size_spin.setValue(self.logo_text_size)
        self.logo_text_size_spin.valueChanged.connect(self._on_logo_text_size_changed)
        self.logo_text_align_combo = QComboBox()
        self.logo_text_align_combo.addItem("Gauche", "left")
        self.logo_text_align_combo.addItem("Centre", "center")
        self.logo_text_align_combo.addItem("Droite", "right")
        self.logo_text_align_combo.currentIndexChanged.connect(self._on_logo_text_align_changed)
        self.logo_text_upper_check = QCheckBox("Majuscule")
        self.logo_text_upper_check.toggled.connect(self._on_logo_text_upper_toggled)
        self.logo_text_line_spacing_spin = QSpinBox()
        self.logo_text_line_spacing_spin.setRange(50, 300)
        self.logo_text_line_spacing_spin.setSingleStep(5)
        self.logo_text_line_spacing_spin.setSuffix(" %")
        self.logo_text_line_spacing_spin.setValue(self.logo_text_line_spacing)
        self.logo_text_line_spacing_spin.valueChanged.connect(self._on_logo_text_line_spacing_changed)
        self.poster_textbox_check = QCheckBox("TextBox poster")
        self.poster_textbox_check.setChecked(self.poster_textbox_enabled)
        self.poster_textbox_check.toggled.connect(self._on_poster_textbox_toggled)
        self.poster_textbox_input = QLineEdit(self.poster_textbox_text)
        self.poster_textbox_input.setPlaceholderText("Texte text box (poster)")
        self.poster_textbox_input.textChanged.connect(self._on_poster_textbox_changed)
        
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
        self.gradient_distance_spin = QSpinBox()
        self.gradient_distance_spin.setRange(1, 100)
        self.gradient_distance_spin.setSuffix(" %")
        self.gradient_distance_spin.setValue(self.gradient_distance)
        self.gradient_distance_spin.valueChanged.connect(self._on_gradient_distance_changed)
        self.gradient_stretch_spin = QSpinBox()
        self.gradient_stretch_spin.setRange(20, 300)
        self.gradient_stretch_spin.setSuffix(" %")
        self.gradient_stretch_spin.setValue(self.gradient_stretch)
        self.gradient_stretch_spin.valueChanged.connect(self._on_gradient_stretch_changed)
        self.gradient_color_a_btn = QPushButton("Couleur degrade A")
        self.gradient_color_a_btn.clicked.connect(self._pick_gradient_color_a)
        self.gradient_color_b_btn = QPushButton("Couleur degrade B")
        self.gradient_color_b_btn.clicked.connect(self._pick_gradient_color_b)

        self.logo_shadow_check = QCheckBox("Ombre portee logo")
        self.logo_shadow_check.toggled.connect(self._on_logo_shadow_toggled)
        self.logo_shadow_distance_spin = QSpinBox()
        self.logo_shadow_distance_spin.setRange(0, 500)
        self.logo_shadow_distance_spin.setSuffix(" px")
        self.logo_shadow_distance_spin.setValue(self.logo_shadow_distance)
        self.logo_shadow_distance_spin.valueChanged.connect(self._on_logo_shadow_distance_changed)
        self.logo_shadow_blur_spin = QSpinBox()
        self.logo_shadow_blur_spin.setRange(0, 150)
        self.logo_shadow_blur_spin.setSuffix(" px")
        self.logo_shadow_blur_spin.setValue(self.logo_shadow_blur)
        self.logo_shadow_blur_spin.valueChanged.connect(self._on_logo_shadow_blur_changed)
        self.logo_shadow_angle_slider = QSlider(Qt.Orientation.Horizontal)
        self.logo_shadow_angle_slider.setRange(0, 359)
        self.logo_shadow_angle_slider.setValue(int(self.logo_shadow_angle) % 360)
        self.logo_shadow_angle_slider.valueChanged.connect(self._on_logo_shadow_angle_changed)
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
        text_form.addRow("Taille", self.logo_text_size_spin)
        text_form.addRow("Alignement", self.logo_text_align_combo)
        text_form.addRow(self.logo_text_upper_check)
        text_form.addRow("Interligne (%)", self.logo_text_line_spacing_spin)
        text_form.addRow(self.poster_textbox_check)
        text_form.addRow("Textebox", self.poster_textbox_input)
        text_layout.addLayout(text_form)
        resources_layout.addWidget(text_box)

        shadow_box = QGroupBox("Ombre")
        shadow_layout = QVBoxLayout(shadow_box)
        shadow_form = QFormLayout()
        shadow_form.addRow(self.logo_shadow_check)
        shadow_form.addRow("Distance", self.logo_shadow_distance_spin)
        shadow_form.addRow("Lissage", self.logo_shadow_blur_spin)
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
        gradient_form.addRow("Distance", self.gradient_distance_spin)
        gradient_form.addRow("Etirement", self.gradient_stretch_spin)
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
        layer_buttons_row = QHBoxLayout()
        self.layer_buttons: Dict[str, QPushButton] = {}
        for layer, label in [("character", "Personnage"), ("background", "Background"), ("logo", "Logo")]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.clicked.connect(lambda _checked, lid=layer: self._set_active_layer(lid))
            self.layer_buttons[layer] = btn
            layer_buttons_row.addWidget(btn)

        self.visible_check = QCheckBox("Visible")
        self.visible_check.setChecked(True)
        self.visible_check.toggled.connect(self._on_visible_changed)

        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
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

        layer_layout.addRow("Calque", layer_buttons_row)
        layer_layout.addRow(self.visible_check)
        layer_layout.addRow("Opacite", opacity_row)
        layer_layout.addRow("Echelle", scale_row)
        layer_layout.addRow(center_btn)
        layer_layout.addRow(reset_btn)
        self._set_active_layer(self.active_layer, sync=False)
        layout.addWidget(layer_box)
        layout.addStretch(1)
        return panel

    def _build_right_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)

        exports = QGroupBox("Exports")
        exports_layout = QVBoxLayout(exports)
        self.export_list = QListWidget()
        for preset_id, meta in PRESETS.items():
            item = QListWidgetItem(meta["label"])
            item.setData(Qt.ItemDataRole.UserRole, preset_id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.export_list.addItem(item)
        exports_layout.addWidget(self.export_list)

        self.export_dir = QLineEdit(str(Path.cwd() / "exports"))
        self.export_dir_btn = QPushButton("Dossier d'export")
        self.export_dir_btn.clicked.connect(self._select_export_dir)
        self.base_name_input = QLineEdit("Name")
        self.save_project_btn = QPushButton("Sauvegarde projet...")
        self.save_project_btn.clicked.connect(self._save_project_snapshot_as)
        self.load_project_btn = QPushButton("Charger sauvegarde...")
        self.load_project_btn.clicked.connect(self._load_project_snapshot)
        self.new_project_btn = QPushButton("Nouveau projet")
        self.new_project_btn.clicked.connect(self._new_project)

        self.export_btn = QPushButton("Exporter")
        self.export_btn.clicked.connect(self._export_selected)

        self.progress = QProgressBar()
        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)

        exports_layout.addWidget(QLabel("Dossier"))
        exports_layout.addWidget(self.export_dir)
        exports_layout.addWidget(self.export_dir_btn)
        exports_layout.addWidget(QLabel("Nom de base"))
        exports_layout.addWidget(self.base_name_input)
        exports_layout.addWidget(self.save_project_btn)
        exports_layout.addWidget(self.load_project_btn)
        exports_layout.addWidget(self.new_project_btn)
        exports_layout.addWidget(self.export_btn)
        exports_layout.addWidget(self.progress)
        exports_layout.addWidget(QLabel("Logs"))
        exports_layout.addWidget(self.log_box)

        layout.addWidget(exports)
        pos_box = QGroupBox("Positions (px)")
        pos_layout = QVBoxLayout(pos_box)
        self.position_labels: Dict[str, QLabel] = {}
        for layer_id, label in [("background", "Background"), ("character", "Personnage"), ("logo", "Logo")]:
            row = QLabel()
            self.position_labels[layer_id] = row
            pos_layout.addWidget(row)
        layout.addWidget(pos_box)
        self._update_position_info()
        return panel

    def _build_presets_preview_strip(self):
        box = QGroupBox("Preview presets (mise a jour auto)")
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
        self.log_box.appendPlainText(message)

    def _on_preset_changed(self):
        self.current_preset = self.preset_combo.currentData()
        if not self._is_layer_allowed(self.current_preset, self.active_layer):
            fallback = "logo" if self.current_preset == "logo" else "background"
            self._set_active_layer(fallback, sync=False)
        self._set_scene_for_preset(self.current_preset)
        self._refresh_preview()
        self._sync_layer_controls()
        self._sync_poster_textbox_controls()
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
        self.guides_visible = checked
        self._refresh_preview()

    def _on_poster_guide_variant_changed(self):
        if not hasattr(self, "poster_guide_combo"):
            return
        selected = self.poster_guide_combo.currentData()
        if selected not in POSTER_GUIDE_FILES:
            return
        self.poster_guide_variant = selected
        self._load_guides()
        for layer_id in ["character", "logo"]:
            layer_pixmap = self.assets[layer_id].pixmap
            if layer_pixmap is None or layer_pixmap.isNull():
                continue
            self._apply_auto_placement(layer_id, "poster")
        self._invalidate_presets_preview(["poster"])
        self._refresh_preview()
        self._sync_layer_controls()

    def _on_logo_text_toggle(self, checked: bool):
        self.logo_text_enabled = checked
        self._invalidate_presets_preview()
        self._refresh_preview()

    def _on_logo_text_changed(self):
        self.logo_text = self.logo_text_input.toPlainText().strip()
        self._invalidate_presets_preview()
        self._refresh_preview()

    def _on_logo_text_size_changed(self, value: int):
        self.logo_text_size = value
        self._invalidate_presets_preview()
        self._refresh_preview()

    def _on_logo_text_align_changed(self):
        self.logo_text_align = self.logo_text_align_combo.currentData()
        self._invalidate_presets_preview()
        self._refresh_preview()

    def _on_logo_text_upper_toggled(self, checked: bool):
        self.logo_text_force_upper = checked
        self._invalidate_presets_preview()
        self._refresh_preview()

    def _on_logo_text_line_spacing_changed(self, value: int):
        self.logo_text_line_spacing = value
        self._invalidate_presets_preview()
        self._refresh_preview()

    def _on_poster_textbox_toggled(self, checked: bool):
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
        self.logo_shadow_enabled = checked
        self._invalidate_presets_preview()
        self._refresh_preview()

    def _on_logo_shadow_distance_changed(self, value: int):
        self.logo_shadow_distance = value
        self._invalidate_presets_preview()
        self._refresh_preview()

    def _on_logo_shadow_blur_changed(self, value: int):
        self.logo_shadow_blur = value
        self._invalidate_presets_preview()
        self._refresh_preview()

    def _on_logo_shadow_angle_changed(self, value: int):
        self.logo_shadow_angle = value % 360
        self._update_shadow_slider_labels()
        self._invalidate_presets_preview()
        self._refresh_preview()

    def _on_logo_shadow_opacity_changed(self, value: int):
        self.logo_shadow_opacity = value
        self._update_shadow_slider_labels()
        self._invalidate_presets_preview()
        self._refresh_preview()

    def _on_gradient_enabled_toggled(self, checked: bool):
        self.gradient_enabled = checked
        self._sync_gradient_controls()
        self._invalidate_presets_preview()
        self._refresh_preview()

    def _on_gradient_mode_changed(self):
        self.gradient_mode = self.gradient_mode_combo.currentData()
        self._sync_gradient_controls()
        self._invalidate_presets_preview()
        self._refresh_preview()

    def _on_gradient_direction_changed(self):
        self.gradient_direction = self.gradient_direction_combo.currentData()
        self._invalidate_presets_preview()
        self._refresh_preview()

    def _on_gradient_distance_changed(self, value: int):
        self.gradient_distance = value
        self._invalidate_presets_preview()
        self._refresh_preview()

    def _on_gradient_stretch_changed(self, value: int):
        self.gradient_stretch = value
        self._invalidate_presets_preview()
        self._refresh_preview()

    def _update_shadow_slider_labels(self):
        if hasattr(self, "logo_shadow_angle_label"):
            self.logo_shadow_angle_label.setText(f"{int(self.logo_shadow_angle)} deg")
        if hasattr(self, "logo_shadow_opacity_label"):
            self.logo_shadow_opacity_label.setText(f"{int(self.logo_shadow_opacity)} %")

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

        min_x = min(0, shadow_x)
        min_y = min(0, shadow_y)
        max_x = max(src.width, shadow_x + shadow_img.width)
        max_y = max(src.height, shadow_y + shadow_img.height)

        canvas = Image.new("RGBA", (max_x - min_x, max_y - min_y), (0, 0, 0, 0))
        canvas.alpha_composite(shadow_img, (shadow_x - min_x, shadow_y - min_y))
        canvas.alpha_composite(src, (-min_x, -min_y))
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

    def _build_gradient_image(self, canvas_w: int, canvas_h: int):
        if not self.gradient_enabled:
            return None
        if canvas_w <= 0 or canvas_h <= 0:
            return None

        vertical = self.gradient_direction in {"top", "bottom"}
        axis_size = canvas_h if vertical else canvas_w
        distance_px = max(1, int(axis_size * (self.gradient_distance / 100)))
        stretch_ratio = max(0.2, self.gradient_stretch / 100)

        color_a = self._gradient_color_rgb(self.gradient_color_a, "#000000")
        color_b = self._gradient_color_rgb(self.gradient_color_b, "#FFFFFF")
        ramp_data = []
        for idx in range(axis_size):
            if self.gradient_direction in {"top", "left"}:
                axis_pos = idx
            else:
                axis_pos = (axis_size - 1) - idx
            t = min(1.0, axis_pos / distance_px)
            t = min(1.0, max(0.0, t ** (1.0 / stretch_ratio)))

            if self.gradient_mode == "double":
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

    def _build_poster_textbox_render(self, preset_id: str, canvas_w: int, canvas_h: int):
        if preset_id != "poster" or not self.poster_textbox_enabled:
            return None
        text = self._poster_textbox_display_text()
        if not text:
            return None

        base = POSTER_TEXTBOX_BASE
        scale = canvas_w / 1600.0
        x = int(round(base["x"] * scale))
        y = int(round(base["y"] * scale))
        height = max(36, int(round(base["height"] * scale)))
        min_width = max(120, int(round(base["min_width"] * scale)))
        padding_left = max(10, int(round(base["padding_left"] * scale)))
        radius = max(4, int(round(base["radius"] * scale)))
        font_size = max(20, int(round(base["font_size"] * scale)))
        max_width = max(100, canvas_w - x)

        probe = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        probe_draw = ImageDraw.Draw(probe)
        font = self._load_poster_textbox_font(font_size)
        bbox = probe_draw.textbbox((0, 0), text, font=font)
        text_w = max(1, bbox[2] - bbox[0])
        text_h = max(1, bbox[3] - bbox[1])
        spaces_bbox = probe_draw.textbbox((0, 0), "  ", font=font)
        padding_right = max(8, spaces_bbox[2] - spaces_bbox[0])

        width = max(min_width, text_w + padding_left + padding_right)
        width = min(max_width, width)
        while (text_w + padding_left + padding_right) > width and font_size > 20:
            font_size -= 2
            font = self._load_poster_textbox_font(font_size)
            bbox = probe_draw.textbbox((0, 0), text, font=font)
            text_w = max(1, bbox[2] - bbox[0])
            text_h = max(1, bbox[3] - bbox[1])
            spaces_bbox = probe_draw.textbbox((0, 0), "  ", font=font)
            padding_right = max(8, spaces_bbox[2] - spaces_bbox[0])

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
            self.logo_text_color = color.name()
            self._invalidate_presets_preview()
            self._refresh_preview()

    def _pick_logo_shadow_color(self):
        color = QColorDialog.getColor(QColor(self.logo_shadow_color), self)
        if color.isValid():
            self.logo_shadow_color = color.name()
            self._invalidate_presets_preview()
            self._refresh_preview()

    def _pick_gradient_color_a(self):
        color = QColorDialog.getColor(QColor(self.gradient_color_a), self)
        if color.isValid():
            self.gradient_color_a = color.name()
            self._invalidate_presets_preview()
            self._refresh_preview()

    def _pick_gradient_color_b(self):
        color = QColorDialog.getColor(QColor(self.gradient_color_b), self)
        if color.isValid():
            self.gradient_color_b = color.name()
            self._invalidate_presets_preview()
            self._refresh_preview()

    def _on_visible_changed(self, checked: bool):
        layer = self._selected_layer()
        self._layer_state(self.current_preset, layer)["visible"] = checked
        self._refresh_preview()

    def _on_opacity_changed(self, value: int):
        layer = self._selected_layer()
        self._layer_state(self.current_preset, layer)["opacity"] = value / 100
        self._update_slider_value_labels()
        self._refresh_preview()

    def _on_scale_changed(self, value: int):
        layer = self._selected_layer()
        self._layer_state(self.current_preset, layer)["transform"]["scale"] = value / 100
        self._update_slider_value_labels()
        self._refresh_preview()

    def _on_reset_layer(self):
        layer = self._selected_layer()
        self.state[self.current_preset][layer] = self._build_default_layer()
        if layer == "background":
            self.state[self.current_preset][layer]["fit_mode"] = "crop"
        self._apply_auto_placement(layer, self.current_preset)
        self._refresh_preview()
        self._sync_layer_controls()

    def _on_center_layer(self):
        layer = self._selected_layer()
        if not self._is_layer_allowed(self.current_preset, layer):
            return

        width, height = PRESETS[self.current_preset]["size"]
        layer_state = self._layer_state(self.current_preset, layer)
        layer_state["transform"]["x"] = width * 0.5
        if layer == "character":
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
        self._update_position_info()
        self._request_presets_preview_refresh(preset_ids=[self.current_preset])

    def _on_wheel_scaled(self, delta: float):
        layer = self._selected_layer()
        layer_state = self._layer_state(self.current_preset, layer)
        layer_state["transform"]["scale"] = max(0.0, min(1.0, layer_state["transform"]["scale"] + delta))
        self._refresh_preview()
        self._sync_layer_controls()

    def _on_layer_clicked(self, layer_id: str):
        self._set_active_layer(layer_id)

    def _set_active_layer(self, layer_id: str, sync: bool = True):
        if layer_id not in {"background", "character", "logo"}:
            return
        self.active_layer = layer_id
        for lid, btn in self.layer_buttons.items():
            btn.setChecked(lid == layer_id)
        if sync:
            self._sync_layer_controls()

    def _is_layer_allowed(self, preset_id: str, layer_id: str) -> bool:
        if preset_id == "logo":
            return layer_id == "logo"
        if layer_id == "logo" and PRESETS[preset_id].get("skip_logo"):
            return False
        return True

    def _sync_layer_controls(self):
        if self.updating_ui:
            return
        self.updating_ui = True
        layer = self._selected_layer()
        if not self._is_layer_allowed(self.current_preset, layer):
            for fallback in ["logo", "background", "character"]:
                if self._is_layer_allowed(self.current_preset, fallback):
                    self._set_active_layer(fallback, sync=False)
                    layer = fallback
                    break
        for lid, btn in self.layer_buttons.items():
            btn.setEnabled(self._is_layer_allowed(self.current_preset, lid))
        layer_state = self._layer_state(self.current_preset, layer)
        self.visible_check.setChecked(layer_state["visible"])
        self.opacity_slider.setValue(int(layer_state["opacity"] * 100))
        self.scale_slider.setValue(int(layer_state["transform"]["scale"] * 100))
        self._update_slider_value_labels()
        self.updating_ui = False

    def _import_layer(self, layer_id: str):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Sélectionner une image",
            "",
            "Images (*.png *.jpg *.jpeg *.webp)",
        )
        if not file_path:
            return

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

        self._invalidate_presets_preview()
        self._log(f"Import {layer_id}: {file_path}")
        self._refresh_preview()
        self._sync_layer_controls()

    def _apply_auto_placement(self, layer_id: str, preset_id: str):
        layer_pixmap = self.assets[layer_id].pixmap
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
        elif layer_id == "character":
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
            layer_state["transform"]["scale"] = 1.0
            layer_state["transform"]["anchor"] = "center"
            if preset_id == "logo":
                if layer_pixmap is not None and not layer_pixmap.isNull():
                    src_w = max(1, layer_pixmap.width())
                    src_h = max(1, layer_pixmap.height())
                    ratio = min(width / src_w, height / src_h)
                    rendered_w = src_w * ratio
                    rendered_h = src_h * ratio
                else:
                    rendered_w = width * 0.5
                    rendered_h = height * 0.5
                # In logo preset, default position is bottom-left.
                layer_state["transform"]["x"] = rendered_w * 0.5
                layer_state["transform"]["y"] = height - (rendered_h * 0.5)
            else:
                layer_state["transform"]["x"] = width * 0.5
                layer_state["transform"]["y"] = height * 0.5

    def _refresh_preview(self):
        preset_meta = PRESETS[self.current_preset]
        canvas_w, canvas_h = preset_meta["size"]
        self._refresh_guide_overlay(canvas_w, canvas_h)

        for layer in ["background", "character", "gradient", "logo"]:
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

            if layer == "character":
                pos_x = layer_state["transform"]["x"]
                pos_y = layer_state["transform"]["y"]
                item.setOffset(-pixmap.width() / 2, -pixmap.height())
                item.setPos(pos_x, pos_y)
            elif layer == "gradient":
                item.setOffset(0, 0)
                item.setPos(0, 0)
            else:
                pos_x = layer_state["transform"]["x"]
                pos_y = layer_state["transform"]["y"]
                item.setOffset(-pixmap.width() / 2, -pixmap.height() / 2)
                item.setPos(pos_x, pos_y)
        self._refresh_poster_textbox_overlay(canvas_w, canvas_h)
        self._update_position_info()
        self._request_presets_preview_refresh(preset_ids=[self.current_preset])

    def _compose_preset_canvas(
        self,
        preset_id: str,
        log_upscale: bool = False,
        render_scale: float = 1.0,
        resample=Image.Resampling.LANCZOS,
    ):
        preset = PRESETS[preset_id]
        base_w, base_h = preset["size"]
        scale = max(0.02, min(1.0, float(render_scale)))
        canvas_w = max(1, int(round(base_w * scale)))
        canvas_h = max(1, int(round(base_h * scale)))
        canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

        for layer in ["background", "character", "gradient", "logo"]:
            if not self._is_layer_allowed(preset_id, layer):
                continue
            layer_state = self._layer_state(preset_id, layer)
            if not layer_state["visible"]:
                continue

            rendered = self._render_layer_for_export(
                layer,
                preset_id,
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
                tx = layer_state["transform"]["x"] * scale
                ty = layer_state["transform"]["y"] * scale
                x = int(tx - lw / 2)
                if layer == "character":
                    y = int(ty - lh)
                else:
                    y = int(ty - lh / 2)

            if log_upscale and self.assets[layer].pil and layer not in {"logo", "gradient"}:
                sw, sh = self.assets[layer].pil.size
                upscale_ratio = max(lw / sw, lh / sh)
                if upscale_ratio > self.upscale_warning_ratio:
                    self._log(f"Avertissement upscale ({preset['label']} / {layer}): x{upscale_ratio:.2f}")

            alpha = rendered.getchannel("A")
            if layer_state["opacity"] < 1.0:
                alpha = alpha.point(lambda px: int(px * layer_state["opacity"]))
            canvas.paste(rendered, (x, y), alpha)

        textbox_draw = self._build_poster_textbox_render(preset_id, canvas_w, canvas_h)
        if textbox_draw is not None:
            textbox_img, textbox_x, textbox_y = textbox_draw
            canvas.alpha_composite(textbox_img, (textbox_x, textbox_y))
        return canvas

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
            image = self._compose_preset_canvas(
                preset_id,
                log_upscale=False,
                render_scale=render_ratio,
                resample=Image.Resampling.BILINEAR,
            )
        except Exception:
            return QPixmap()
        if image.size != (target_w, target_h):
            image = image.resize((target_w, target_h), Image.Resampling.BILINEAR)
        return self._pil_to_qpixmap(image)

    def _invalidate_presets_preview(self, preset_ids=None):
        if preset_ids is None:
            preset_ids = PRESETS.keys()
        for preset_id in preset_ids:
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
            gradient_img = self._build_gradient_image(canvas_w, canvas_h)
            if gradient_img is None:
                return QPixmap()
            return self._pil_to_qpixmap(gradient_img)

        layer_state = self._layer_state(self.current_preset, layer_id)
        fit_mode = layer_state["fit_mode"]
        scale = layer_state["transform"]["scale"]

        if layer_id == "logo" and self.logo_text_enabled and self.logo_text:
            logo_text = self._logo_display_text()
            base = self._build_logo_preview_pixmap(logo_text)
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
        path = QFileDialog.getExistingDirectory(self, "Dossier d'export")
        if path:
            self.export_dir.setText(path)

    def _selected_exports(self):
        selected = []
        for i in range(self.export_list.count()):
            item = self.export_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected.append(item.data(Qt.ItemDataRole.UserRole))
        return selected

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

    def _update_position_info(self):
        if not hasattr(self, "position_labels"):
            return
        labels = {
            "background": "Background",
            "character": "Personnage",
            "logo": "Logo",
        }
        for layer_id, label_widget in self.position_labels.items():
            layer_state = self._layer_state(self.current_preset, layer_id)
            transform = layer_state.get("transform", {})
            x = int(round(self._to_float(transform.get("x"), 0.0)))
            y = int(round(self._to_float(transform.get("y"), 0.0)))
            allowed = self._is_layer_allowed(self.current_preset, layer_id)
            suffix = "" if allowed else " (non actif sur ce preset)"
            label_widget.setText(f"{labels[layer_id]}: X={x}px  Y={y}px{suffix}")

    def _merge_state_from_snapshot(self, raw_state):
        merged = self._build_default_state()
        if not isinstance(raw_state, dict):
            return merged

        for preset_id in PRESETS:
            preset_data = raw_state.get(preset_id)
            if not isinstance(preset_data, dict):
                continue
            for layer_id in LAYER_ORDER:
                layer_data = preset_data.get(layer_id)
                if not isinstance(layer_data, dict):
                    continue
                target = merged[preset_id][layer_id]
                target["visible"] = bool(layer_data.get("visible", target["visible"]))
                target["opacity"] = max(
                    0.0,
                    min(1.0, self._to_float(layer_data.get("opacity"), target["opacity"])),
                )
                fit_mode = layer_data.get("fit_mode")
                if isinstance(fit_mode, str):
                    target["fit_mode"] = fit_mode

                transform_data = layer_data.get("transform")
                if not isinstance(transform_data, dict):
                    continue
                transform = target["transform"]
                transform["x"] = self._to_float(transform_data.get("x"), transform["x"])
                transform["y"] = self._to_float(transform_data.get("y"), transform["y"])
                transform["scale"] = max(
                    0.0,
                    min(1.0, self._to_float(transform_data.get("scale"), transform["scale"])),
                )
                transform["rotation"] = self._to_float(
                    transform_data.get("rotation"),
                    transform["rotation"],
                )
                anchor = transform_data.get("anchor")
                if isinstance(anchor, str):
                    transform["anchor"] = anchor
        return merged

    def _apply_selected_exports(self, selected_exports):
        if not isinstance(selected_exports, list):
            return
        selected_ids = {item for item in selected_exports if isinstance(item, str)}
        for i in range(self.export_list.count()):
            item = self.export_list.item(i)
            preset_id = item.data(Qt.ItemDataRole.UserRole)
            check_state = Qt.CheckState.Checked if preset_id in selected_ids else Qt.CheckState.Unchecked
            item.setCheckState(check_state)

    def _apply_logo_text_settings(self, raw_logo_text):
        if not isinstance(raw_logo_text, dict):
            return

        text = raw_logo_text.get("text")
        if isinstance(text, str):
            self.logo_text = text

        align = raw_logo_text.get("align")
        if align in {"left", "center", "right"}:
            self.logo_text_align = align

        color = raw_logo_text.get("color")
        if isinstance(color, str) and color.strip():
            self.logo_text_color = color.strip()

        self.logo_text_enabled = bool(raw_logo_text.get("enabled", self.logo_text_enabled))
        self.logo_text_force_upper = bool(
            raw_logo_text.get("force_upper", self.logo_text_force_upper)
        )
        self.logo_text_size = max(
            12,
            min(600, int(round(self._to_float(raw_logo_text.get("size"), self.logo_text_size)))),
        )
        self.logo_text_line_spacing = max(
            50,
            min(
                300,
                int(round(self._to_float(raw_logo_text.get("line_spacing"), self.logo_text_line_spacing))),
            ),
        )

        self._sync_logo_controls()

    def _apply_poster_textbox_settings(self, raw_textbox):
        if not isinstance(raw_textbox, dict):
            self._sync_poster_textbox_controls()
            return
        enabled = raw_textbox.get("enabled")
        if isinstance(enabled, bool):
            self.poster_textbox_enabled = enabled
        text = raw_textbox.get("text")
        if isinstance(text, str):
            self.poster_textbox_text = text.upper()
        self._sync_poster_textbox_controls()

    def _apply_logo_shadow_settings(self, raw_logo_shadow):
        if not isinstance(raw_logo_shadow, dict):
            self.logo_shadow_enabled = False
            self.logo_shadow_distance = 16
            self.logo_shadow_blur = 12
            self.logo_shadow_angle = 135
            self.logo_shadow_opacity = 60
            self.logo_shadow_color = "#000000"
            self._sync_logo_controls()
            return

        self.logo_shadow_enabled = bool(raw_logo_shadow.get("enabled", self.logo_shadow_enabled))
        self.logo_shadow_distance = max(
            0,
            min(500, int(round(self._to_float(raw_logo_shadow.get("distance"), self.logo_shadow_distance)))),
        )
        self.logo_shadow_blur = max(
            0,
            min(150, int(round(self._to_float(raw_logo_shadow.get("blur"), self.logo_shadow_blur)))),
        )
        raw_angle = int(round(self._to_float(raw_logo_shadow.get("angle"), self.logo_shadow_angle)))
        self.logo_shadow_angle = raw_angle % 360
        self.logo_shadow_opacity = max(
            0,
            min(100, int(round(self._to_float(raw_logo_shadow.get("opacity"), self.logo_shadow_opacity)))),
        )
        color = raw_logo_shadow.get("color")
        if isinstance(color, str) and color.strip():
            self.logo_shadow_color = color.strip()

        self._sync_logo_controls()

    def _apply_gradient_settings(self, raw_gradient):
        if not isinstance(raw_gradient, dict):
            self.gradient_enabled = False
            self.gradient_mode = "single"
            self.gradient_direction = "top"
            self.gradient_color_a = "#000000"
            self.gradient_color_b = "#FFFFFF"
            self.gradient_distance = 40
            self.gradient_stretch = 100
            self._sync_gradient_controls()
            return

        self.gradient_enabled = bool(raw_gradient.get("enabled", self.gradient_enabled))
        mode = raw_gradient.get("mode")
        if mode in {"single", "double"}:
            self.gradient_mode = mode
        direction = raw_gradient.get("direction")
        if direction in {"top", "bottom", "left", "right"}:
            self.gradient_direction = direction
        color_a = raw_gradient.get("color_a")
        if isinstance(color_a, str) and color_a.strip():
            self.gradient_color_a = color_a.strip()
        color_b = raw_gradient.get("color_b")
        if isinstance(color_b, str) and color_b.strip():
            self.gradient_color_b = color_b.strip()
        self.gradient_distance = max(
            1,
            min(100, int(round(self._to_float(raw_gradient.get("distance"), self.gradient_distance)))),
        )
        self.gradient_stretch = max(
            20,
            min(300, int(round(self._to_float(raw_gradient.get("stretch"), self.gradient_stretch)))),
        )
        self._sync_gradient_controls()

    def _apply_guide_settings(self, raw_guides):
        if not isinstance(raw_guides, dict):
            return
        visible = raw_guides.get("visible")
        if isinstance(visible, bool):
            self.guides_visible = visible
        opacity = raw_guides.get("opacity")
        if isinstance(opacity, (int, float)):
            self.guides_opacity = max(0.1, min(0.6, float(opacity)))
        poster_variant = raw_guides.get("poster_variant")
        if isinstance(poster_variant, str) and poster_variant in POSTER_GUIDE_FILES:
            self.poster_guide_variant = poster_variant
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
        if hasattr(self, "guide_item"):
            self.guide_item.setOpacity(self.guides_opacity)
        self._load_guides()

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

    def _sync_logo_controls(self):
        self.logo_text_checkbox.blockSignals(True)
        self.logo_text_checkbox.setChecked(self.logo_text_enabled)
        self.logo_text_checkbox.blockSignals(False)

        self.logo_text_input.blockSignals(True)
        self.logo_text_input.setPlainText(self.logo_text)
        self.logo_text_input.blockSignals(False)

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

        self.logo_shadow_check.blockSignals(True)
        self.logo_shadow_check.setChecked(self.logo_shadow_enabled)
        self.logo_shadow_check.blockSignals(False)

        self.logo_shadow_distance_spin.blockSignals(True)
        self.logo_shadow_distance_spin.setValue(self.logo_shadow_distance)
        self.logo_shadow_distance_spin.blockSignals(False)

        self.logo_shadow_blur_spin.blockSignals(True)
        self.logo_shadow_blur_spin.setValue(self.logo_shadow_blur)
        self.logo_shadow_blur_spin.blockSignals(False)

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

        self.gradient_enable_check.blockSignals(True)
        self.gradient_enable_check.setChecked(self.gradient_enabled)
        self.gradient_enable_check.blockSignals(False)

        self.gradient_mode_combo.blockSignals(True)
        mode_idx = self.gradient_mode_combo.findData(self.gradient_mode)
        if mode_idx >= 0:
            self.gradient_mode_combo.setCurrentIndex(mode_idx)
        self.gradient_mode_combo.blockSignals(False)

        self.gradient_direction_combo.blockSignals(True)
        dir_idx = self.gradient_direction_combo.findData(self.gradient_direction)
        if dir_idx >= 0:
            self.gradient_direction_combo.setCurrentIndex(dir_idx)
        self.gradient_direction_combo.blockSignals(False)

        self.gradient_distance_spin.blockSignals(True)
        self.gradient_distance_spin.setValue(self.gradient_distance)
        self.gradient_distance_spin.blockSignals(False)

        self.gradient_stretch_spin.blockSignals(True)
        self.gradient_stretch_spin.setValue(self.gradient_stretch)
        self.gradient_stretch_spin.blockSignals(False)

        controls_enabled = self.gradient_enabled
        self.gradient_mode_combo.setEnabled(controls_enabled)
        self.gradient_direction_combo.setEnabled(controls_enabled)
        self.gradient_distance_spin.setEnabled(controls_enabled)
        self.gradient_stretch_spin.setEnabled(controls_enabled)
        self.gradient_color_a_btn.setEnabled(controls_enabled)
        self.gradient_color_b_btn.setEnabled(controls_enabled and self.gradient_mode == "double")

    def _guide_path_for_preset(self, preset_id: str):
        asset_dir = self.program_root / "asset"
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
                candidate = asset_dir / candidate_name
                if candidate.exists():
                    return candidate
            return None
        for candidate_name in GUIDE_FILE_PATTERNS.get(preset_id, []):
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
            if preset_id == "logo":
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
        return regions.get(layer_id)

    def _refresh_guide_overlay(self, canvas_w: int, canvas_h: int):
        if not hasattr(self, "guide_item"):
            return
        if not self.guides_visible or self.current_preset == "logo":
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
        canvas_w, canvas_h = PRESETS[preset_id]["size"]
        base_ratio = min(canvas_w / src_w, canvas_h / src_h)
        if base_ratio <= 0:
            return False
        region_ratio = min(box_w / src_w, box_h / src_h)
        layer_state = self._layer_state(preset_id, layer_id)
        layer_state["fit_mode"] = "contain"
        layer_state["transform"]["x"] = box_x + (box_w * 0.5)
        if layer_id == "character":
            # Keep character top at yellow-circle top and force bottom to touch canvas bottom.
            target_height = max(1.0, canvas_h - box_y)
            target_scale = max(0.01, target_height / (src_h * base_ratio))
            layer_state["transform"]["anchor"] = "bottom"
            layer_state["transform"]["scale"] = target_scale
            layer_state["transform"]["y"] = canvas_h
        else:
            target_scale = max(0.01, region_ratio / base_ratio)
            layer_state["transform"]["anchor"] = "center"
            layer_state["transform"]["scale"] = target_scale
            layer_state["transform"]["y"] = box_y + (box_h * 0.5)
        return True

    def _resolve_snapshot_asset_path(
        self,
        raw_path: str,
        snapshot_file: Path,
        snapshot_program_root: Path | None,
    ):
        source_path = Path(raw_path).expanduser()
        candidates = []
        if source_path.is_absolute():
            candidates.append(source_path)
        else:
            candidates.append(source_path)
            candidates.append(snapshot_file.parent / source_path)
            if snapshot_program_root is not None:
                candidates.append(snapshot_program_root / source_path)

        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def _load_layer_asset_from_file(self, layer_id: str, file_path: Path) -> Tuple[bool, str]:
        try:
            pil_img = Image.open(file_path).convert("RGBA")
        except Exception as exc:
            return False, f"lecture PIL impossible ({exc})"

        pixmap = QPixmap(str(file_path))
        if pixmap.isNull():
            return False, "pixmap invalide"

        self.assets[layer_id] = LayerAsset(path=str(file_path), pixmap=pixmap, pil=pil_img)
        return True, ""

    def _load_project_snapshot(self):
        default_dir = self.autosave_dir if self.autosave_dir.exists() else self.program_root
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Charger une sauvegarde projet",
            str(default_dir),
            "ARPlus Save (*.arplus.json *.json);;JSON (*.json)",
        )
        if not file_path:
            return

        snapshot_file = Path(file_path).expanduser()
        try:
            payload = json.loads(snapshot_file.read_text(encoding="utf-8"))
        except Exception as exc:
            self._log(f"Erreur lecture sauvegarde: {exc}")
            QMessageBox.critical(self, "Erreur", f"Impossible de lire la sauvegarde: {exc}")
            return

        if not isinstance(payload, dict):
            QMessageBox.critical(self, "Erreur", "Format de sauvegarde invalide.")
            return

        raw_program_root = payload.get("program_root")
        snapshot_program_root = None
        if isinstance(raw_program_root, str) and raw_program_root.strip():
            snapshot_program_root = Path(raw_program_root).expanduser()

        self.state = self._merge_state_from_snapshot(payload.get("state"))
        self._apply_logo_text_settings(payload.get("logo_text"))
        self._apply_poster_textbox_settings(payload.get("poster_textbox"))
        self._apply_logo_shadow_settings(payload.get("logo_shadow"))
        self._apply_gradient_settings(payload.get("gradient"))
        self._apply_guide_settings(payload.get("guides"))
        self._apply_selected_exports(payload.get("selected_exports"))

        base_name = payload.get("base_name")
        if isinstance(base_name, str):
            self.base_name_input.setText(base_name)

        current_preset = payload.get("current_preset")
        if isinstance(current_preset, str) and current_preset in PRESETS:
            self.current_preset = current_preset

        for layer_id in LAYER_ORDER:
            self.assets[layer_id] = LayerAsset()

        missing_assets = []
        load_errors = []
        assets_data = payload.get("assets")
        if isinstance(assets_data, dict):
            for layer_id in LAYER_ORDER:
                layer_entry = assets_data.get(layer_id)
                if not isinstance(layer_entry, dict):
                    continue
                raw_path = layer_entry.get("path")
                if not isinstance(raw_path, str) or not raw_path.strip():
                    continue
                raw_path = raw_path.strip()
                resolved_path = self._resolve_snapshot_asset_path(
                    raw_path,
                    snapshot_file,
                    snapshot_program_root,
                )
                if resolved_path is None:
                    self.assets[layer_id] = LayerAsset(path=raw_path)
                    missing_assets.append((layer_id, raw_path))
                    continue

                ok, error = self._load_layer_asset_from_file(layer_id, resolved_path)
                if not ok:
                    self.assets[layer_id] = LayerAsset(path=raw_path)
                    load_errors.append((layer_id, raw_path, error))

        preset_index = self.preset_combo.findData(self.current_preset)
        if preset_index >= 0:
            self.preset_combo.blockSignals(True)
            self.preset_combo.setCurrentIndex(preset_index)
            self.preset_combo.blockSignals(False)
        self._refresh_presets_preview_borders()

        self._invalidate_presets_preview()
        self._set_scene_for_preset(self.current_preset)
        self._refresh_preview()
        self._sync_layer_controls()
        self._sync_poster_textbox_controls()
        self._update_position_info()
        self._log(f"Sauvegarde chargee: {snapshot_file}")

        if missing_assets:
            detail_lines = []
            for layer_id, raw_path in missing_assets:
                detail_lines.append(f"{layer_id}: {raw_path} | fichier: {Path(raw_path).name}")
            details = "\n".join(detail_lines)
            self._log("Visuels introuvables (chemins originaux):")
            for line in detail_lines:
                self._log(f"  {line}")
            QMessageBox.warning(
                self,
                "Fichiers introuvables",
                "Certains visuels sont manquants.\nChemins originaux et noms:\n" + details,
            )

        if load_errors:
            self._log("Erreurs de chargement de visuels:")
            detail_lines = []
            for layer_id, raw_path, error in load_errors:
                self._log(f"  {layer_id}: {raw_path} ({error})")
                detail_lines.append(
                    f"{layer_id}: {raw_path} | fichier: {Path(raw_path).name} | erreur: {error}"
                )
            QMessageBox.warning(
                self,
                "Fichiers non chargeables",
                "Certains visuels n'ont pas pu etre charges.\nChemins originaux et noms:\n"
                + "\n".join(detail_lines),
            )

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
            "base_name": self.base_name_input.text(),
            "selected_exports": self._selected_exports(),
            "assets": {
                layer: {"path": asset.path, "loaded": bool(asset.path)}
                for layer, asset in self.assets.items()
            },
            "logo_text": {
                "enabled": self.logo_text_enabled,
                "text": self.logo_text,
                "size": self.logo_text_size,
                "align": self.logo_text_align,
                "force_upper": self.logo_text_force_upper,
                "line_spacing": self.logo_text_line_spacing,
                "color": self.logo_text_color,
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
                "enabled": self.gradient_enabled,
                "mode": self.gradient_mode,
                "direction": self.gradient_direction,
                "color_a": self.gradient_color_a,
                "color_b": self.gradient_color_b,
                "distance": self.gradient_distance,
                "stretch": self.gradient_stretch,
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
        default_dir = Path(self.export_dir.text()).expanduser()
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
        try:
            saved_path = self._write_project_snapshot(out_path)
        except Exception as exc:
            self._log(f"Erreur sauvegarde projet: {exc}")
            QMessageBox.critical(self, "Erreur", f"Impossible de sauvegarder: {exc}")
            return
        self._log(f"Sauvegarde projet: {saved_path}")

    def _set_all_exports_checked(self, checked: bool):
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for i in range(self.export_list.count()):
            self.export_list.item(i).setCheckState(state)

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
        self.poster_textbox_enabled = True
        self.poster_textbox_text = "TEXTE BOX"
        self.logo_shadow_enabled = False
        self.logo_shadow_distance = 16
        self.logo_shadow_blur = 12
        self.logo_shadow_angle = 135
        self.logo_shadow_opacity = 60
        self.logo_shadow_color = "#000000"
        self.gradient_enabled = False
        self.gradient_mode = "single"
        self.gradient_direction = "top"
        self.gradient_color_a = "#000000"
        self.gradient_color_b = "#FFFFFF"
        self.gradient_distance = 40
        self.gradient_stretch = 100
        self.guides_visible = True
        self.guides_opacity = GUIDE_OPACITY_DEFAULT
        self.poster_guide_variant = "1"

        self.base_name_input.setText("Name")
        self._set_all_exports_checked(True)
        self._sync_logo_controls()
        self._sync_gradient_controls()
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
        self._update_position_info()
        self._log("Nouveau projet initialise (visuels supprimes).")

    def _export_selected(self):
        selected = self._selected_exports()
        if not selected:
            QMessageBox.warning(self, "Attention", "Sélectionnez au moins un preset d'export.")
            return

        export_dir = Path(self.export_dir.text()).expanduser()
        export_dir.mkdir(parents=True, exist_ok=True)

        base_name = self._sanitize_base_name(self.base_name_input.text())
        self.progress.setValue(0)
        total = len(selected)
        try:
            autosafe_path = self._autosave_project_snapshot(base_name)
            self._log(f"Autosafe projet: {autosafe_path}")
        except Exception as exc:
            self._log(f"Erreur autosafe projet: {exc}")

        transparent_presets: list[str] = []
        for idx, preset_id in enumerate(selected, start=1):
            try:
                has_transparency = self._export_preset(preset_id, export_dir, base_name)
                if has_transparency and preset_id != "logo":
                    transparent_presets.append(PRESETS[preset_id]["label"])
            except Exception as exc:
                self._log(f"Erreur export {preset_id}: {exc}")
            self.progress.setValue(int((idx / total) * 100))

        if transparent_presets:
            warning_lines = "\n".join(f"- {label}" for label in transparent_presets)
            self._log("Avertissement: transparence restante detectee sur certains presets.")
            QMessageBox.warning(
                self,
                "Transparence detectee",
                "Une partie du canvas reste transparente sur:\n" + warning_lines,
            )

        self._log("Export terminé.")

    def _export_preset(self, preset_id: str, export_dir: Path, base_name: str):
        preset = PRESETS[preset_id]
        canvas = self._compose_preset_canvas(preset_id, log_upscale=True)

        file_stub = preset["filename"]
        ext = "png" if preset.get("png") else "jpg"
        file_name = f"{file_stub}-{base_name}.{ext}"
        out_path = export_dir / file_name

        if ext == "jpg":
            canvas.convert("RGB").save(out_path, quality=95)
        else:
            canvas.save(out_path)
        self._log(f"Export {preset['label']}: {out_path}")

        if preset_id == "logo":
            return False
        alpha_extrema = canvas.getchannel("A").getextrema()
        return alpha_extrema[0] < 255
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
            return self._build_gradient_image(canvas_w, canvas_h)

        state = self._layer_state(preset_id, layer_id)
        fit_mode = state["fit_mode"]
        scale = state["transform"]["scale"]

        if layer_id == "logo" and self.logo_text_enabled and self.logo_text:
            logo_text = self._logo_display_text()
            source = self._build_logo_export_image(logo_text)
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


    def _sanitize_base_name(self, raw_name: str) -> str:
        name = (raw_name or "").strip()
        cleaned = "".join(ch for ch in name if ch not in '<>:"/\\|?*')
        cleaned = cleaned.strip().strip(".")
        return cleaned or "Name"


def main():
    app = QApplication(sys.argv)
    app_icon_path = Path(__file__).resolve().parent / "asset" / "icon.ico"
    if app_icon_path.exists():
        app_icon = QIcon(str(app_icon_path))
        if not app_icon.isNull():
            app.setWindowIcon(app_icon)
    window = ARPlusWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

