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

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from PySide6.QtCore import QBuffer, QIODevice, QObject, QPointF, Qt, Signal
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPen, QPixmap
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
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

LAYER_ORDER = ["background", "character", "logo", "fx"]

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
        self.logo_text_line_spacing = 100
        self.logo_text_color = "#FFFFFF"
        self.logo_shadow_enabled = False
        self.logo_shadow_distance = 16
        self.logo_shadow_blur = 12
        self.logo_shadow_angle = 135
        self.logo_shadow_opacity = 60
        self.logo_shadow_color = "#000000"
        self.upscale_warning_ratio = 1.75
        self.current_preset = "poster"
        self.active_layer = "background"
        self.updating_ui = False
        self.program_root = Path(__file__).resolve().parent
        self.autosave_dir = self.program_root / "autosafe"

        self.state = self._build_default_state()

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
        for layer in ["background", "character", "logo"]:
            item = LayerGraphicsItem(layer)
            item.moved.connect(self._on_layer_moved)
            item.clicked.connect(self._on_layer_clicked)
            item.setParentItem(self.clip_item)
            self.items[layer] = item

        self.frame_item = QGraphicsRectItem()
        frame_pen = QPen(Qt.PenStyle.NoPen)
        self.frame_item.setPen(frame_pen)
        self.frame_item.setBrush(Qt.BrushStyle.NoBrush)
        self.frame_item.setZValue(10_000)
        self.scene.addItem(self.frame_item)

        self._build_ui()
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
            state[preset_id]["logo"]["fit_mode"] = "contain"
            state[preset_id]["logo"]["transform"]["x"] = width * 0.5
            state[preset_id]["logo"]["transform"]["y"] = height * 0.5
            state[preset_id]["logo"]["transform"]["scale"] = 1.0
        return state

    def _build_ui(self):
        root = QWidget(self)
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)

        layout.addWidget(self._build_left_panel(), 1)

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
        layout.addLayout(center, 3)

        layout.addWidget(self._build_right_panel(), 1)

    def _build_left_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)

        resources_box = QGroupBox("Ressources")
        resources_layout = QVBoxLayout(resources_box)
        bg_btn = QPushButton("Importer Background")
        bg_btn.clicked.connect(lambda: self._import_layer("background"))
        char_btn = QPushButton("Importer Character")
        char_btn.clicked.connect(lambda: self._import_layer("character"))
        logo_btn = QPushButton("Importer logo")
        logo_btn.clicked.connect(lambda: self._import_layer("logo"))
        resources_layout.addWidget(bg_btn)
        resources_layout.addWidget(char_btn)
        resources_layout.addWidget(logo_btn)

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
        self.logo_text_line_spacing_spin = QSpinBox()
        self.logo_text_line_spacing_spin.setRange(50, 300)
        self.logo_text_line_spacing_spin.setSingleStep(5)
        self.logo_text_line_spacing_spin.setSuffix(" %")
        self.logo_text_line_spacing_spin.setValue(self.logo_text_line_spacing)
        self.logo_text_line_spacing_spin.valueChanged.connect(self._on_logo_text_line_spacing_changed)
        self.logo_color_btn = QPushButton("Couleur du logo texte")
        self.logo_color_btn.clicked.connect(self._pick_logo_color)
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
        self.logo_shadow_angle_spin = QSpinBox()
        self.logo_shadow_angle_spin.setRange(-180, 180)
        self.logo_shadow_angle_spin.setSuffix(" deg")
        self.logo_shadow_angle_spin.setValue(self.logo_shadow_angle)
        self.logo_shadow_angle_spin.valueChanged.connect(self._on_logo_shadow_angle_changed)
        self.logo_shadow_opacity_spin = QSpinBox()
        self.logo_shadow_opacity_spin.setRange(0, 100)
        self.logo_shadow_opacity_spin.setSuffix(" %")
        self.logo_shadow_opacity_spin.setValue(self.logo_shadow_opacity)
        self.logo_shadow_opacity_spin.valueChanged.connect(self._on_logo_shadow_opacity_changed)
        self.logo_shadow_color_btn = QPushButton("Couleur ombre")
        self.logo_shadow_color_btn.clicked.connect(self._pick_logo_shadow_color)

        form = QFormLayout()
        form.addRow("Contenu", self.logo_text_input)
        form.addRow("Taille", self.logo_text_size_spin)
        form.addRow("Alignement", self.logo_text_align_combo)
        form.addRow("Interligne (%)", self.logo_text_line_spacing_spin)
        form.addRow(self.logo_shadow_check)
        form.addRow("Distance ombre", self.logo_shadow_distance_spin)
        form.addRow("Lissage ombre", self.logo_shadow_blur_spin)
        form.addRow("Angle ombre", self.logo_shadow_angle_spin)
        form.addRow("Opacite ombre", self.logo_shadow_opacity_spin)
        resources_layout.addWidget(self.logo_text_checkbox)
        resources_layout.addLayout(form)
        resources_layout.addWidget(self.logo_color_btn)
        resources_layout.addWidget(self.logo_shadow_color_btn)

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
        self.scale_slider.setRange(0, 100)
        self.scale_slider.setValue(100)
        self.scale_slider.valueChanged.connect(self._on_scale_changed)
        self.scale_value_label = QLabel("100")
        self.scale_value_label.setMinimumWidth(36)
        scale_row = QWidget()
        scale_layout = QHBoxLayout(scale_row)
        scale_layout.setContentsMargins(0, 0, 0, 0)
        scale_layout.addWidget(self.scale_slider, 1)
        scale_layout.addWidget(self.scale_value_label)

        reset_btn = QPushButton("Réinitialiser le calque")
        reset_btn.clicked.connect(self._on_reset_layer)

        layer_layout.addRow("Calque", layer_buttons_row)
        layer_layout.addRow(self.visible_check)
        layer_layout.addRow("Opacite", opacity_row)
        layer_layout.addRow("Echelle", scale_row)
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

    def _on_logo_text_toggle(self, checked: bool):
        self.logo_text_enabled = checked
        self._refresh_preview()

    def _on_logo_text_changed(self):
        self.logo_text = self.logo_text_input.toPlainText().strip()
        self._refresh_preview()

    def _on_logo_text_size_changed(self, value: int):
        self.logo_text_size = value
        self._refresh_preview()

    def _on_logo_text_align_changed(self):
        self.logo_text_align = self.logo_text_align_combo.currentData()
        self._refresh_preview()

    def _on_logo_text_line_spacing_changed(self, value: int):
        self.logo_text_line_spacing = value
        self._refresh_preview()

    def _on_logo_shadow_toggled(self, checked: bool):
        self.logo_shadow_enabled = checked
        self._refresh_preview()

    def _on_logo_shadow_distance_changed(self, value: int):
        self.logo_shadow_distance = value
        self._refresh_preview()

    def _on_logo_shadow_blur_changed(self, value: int):
        self.logo_shadow_blur = value
        self._refresh_preview()

    def _on_logo_shadow_angle_changed(self, value: int):
        self.logo_shadow_angle = value
        self._refresh_preview()

    def _on_logo_shadow_opacity_changed(self, value: int):
        self.logo_shadow_opacity = value
        self._refresh_preview()

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
        return self.logo_text

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

    def _pick_logo_color(self):
        color = QColorDialog.getColor(QColor(self.logo_text_color), self)
        if color.isValid():
            self.logo_text_color = color.name()
            self._refresh_preview()

    def _pick_logo_shadow_color(self):
        color = QColorDialog.getColor(QColor(self.logo_shadow_color), self)
        if color.isValid():
            self.logo_shadow_color = color.name()
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

    def _on_layer_moved(self, layer_id: str, x: float, y: float):
        self._layer_state(self.current_preset, layer_id)["transform"]["x"] = x
        self._layer_state(self.current_preset, layer_id)["transform"]["y"] = y
        self._update_position_info()

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

        self._log(f"Import {layer_id}: {file_path}")
        self._refresh_preview()
        self._sync_layer_controls()

    def _apply_auto_placement(self, layer_id: str, preset_id: str):
        layer_pixmap = self.assets[layer_id].pixmap
        if (layer_pixmap is None or layer_pixmap.isNull()) and layer_id != "logo":
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
        elif layer_id == "logo":
            layer_state["fit_mode"] = "contain"
            layer_state["transform"]["scale"] = 1.0
            layer_state["transform"]["x"] = width * 0.5
            layer_state["transform"]["y"] = height * 0.5
            layer_state["transform"]["anchor"] = "center"

    def _refresh_preview(self):
        preset_meta = PRESETS[self.current_preset]
        canvas_w, canvas_h = preset_meta["size"]

        for layer in ["background", "character", "logo"]:
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

            pos_x = layer_state["transform"]["x"]
            pos_y = layer_state["transform"]["y"]
            if layer == "character":
                item.setOffset(-pixmap.width() / 2, -pixmap.height())
            else:
                item.setOffset(-pixmap.width() / 2, -pixmap.height() / 2)
            item.setPos(pos_x, pos_y)
        self._update_position_info()

    def _preview_pixmap(self, layer_id: str, canvas_w: int, canvas_h: int) -> QPixmap:
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
        self.logo_shadow_angle = max(
            -180,
            min(180, int(round(self._to_float(raw_logo_shadow.get("angle"), self.logo_shadow_angle)))),
        )
        self.logo_shadow_opacity = max(
            0,
            min(100, int(round(self._to_float(raw_logo_shadow.get("opacity"), self.logo_shadow_opacity)))),
        )
        color = raw_logo_shadow.get("color")
        if isinstance(color, str) and color.strip():
            self.logo_shadow_color = color.strip()

        self._sync_logo_controls()

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

        self.logo_shadow_angle_spin.blockSignals(True)
        self.logo_shadow_angle_spin.setValue(self.logo_shadow_angle)
        self.logo_shadow_angle_spin.blockSignals(False)

        self.logo_shadow_opacity_spin.blockSignals(True)
        self.logo_shadow_opacity_spin.setValue(self.logo_shadow_opacity)
        self.logo_shadow_opacity_spin.blockSignals(False)

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
        self._apply_logo_shadow_settings(payload.get("logo_shadow"))
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

        self._set_scene_for_preset(self.current_preset)
        self._refresh_preview()
        self._sync_layer_controls()
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
                "line_spacing": self.logo_text_line_spacing,
                "color": self.logo_text_color,
            },
            "logo_shadow": {
                "enabled": self.logo_shadow_enabled,
                "distance": self.logo_shadow_distance,
                "blur": self.logo_shadow_blur,
                "angle": self.logo_shadow_angle,
                "opacity": self.logo_shadow_opacity,
                "color": self.logo_shadow_color,
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
        self.logo_text_line_spacing = 100
        self.logo_text_color = "#FFFFFF"
        self.logo_shadow_enabled = False
        self.logo_shadow_distance = 16
        self.logo_shadow_blur = 12
        self.logo_shadow_angle = 135
        self.logo_shadow_opacity = 60
        self.logo_shadow_color = "#000000"

        self.base_name_input.setText("Name")
        self._set_all_exports_checked(True)
        self._sync_logo_controls()

        preset_index = self.preset_combo.findData(self.current_preset)
        if preset_index >= 0:
            self.preset_combo.blockSignals(True)
            self.preset_combo.setCurrentIndex(preset_index)
            self.preset_combo.blockSignals(False)

        self._set_active_layer("background", sync=False)
        self._set_scene_for_preset(self.current_preset)
        self._refresh_preview()
        self._sync_layer_controls()
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

        for idx, preset_id in enumerate(selected, start=1):
            try:
                self._export_preset(preset_id, export_dir, base_name)
            except Exception as exc:
                self._log(f"Erreur export {preset_id}: {exc}")
            self.progress.setValue(int((idx / total) * 100))

        self._log("Export terminé.")

    def _export_preset(self, preset_id: str, export_dir: Path, base_name: str):
        preset = PRESETS[preset_id]
        canvas_w, canvas_h = preset["size"]
        canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

        for layer in ["background", "character", "logo"]:
            if not self._is_layer_allowed(preset_id, layer):
                continue

            layer_state = self._layer_state(preset_id, layer)
            if not layer_state["visible"]:
                continue

            rendered = self._render_layer_for_export(layer, preset_id)
            if rendered is None:
                continue

            lw, lh = rendered.size
            x = int(layer_state["transform"]["x"] - lw / 2)
            if layer == "character":
                y = int(layer_state["transform"]["y"] - lh)
            else:
                y = int(layer_state["transform"]["y"] - lh / 2)

            if self.assets[layer].pil and layer != "logo":
                sw, sh = self.assets[layer].pil.size
                upscale_ratio = max(lw / sw, lh / sh)
                if upscale_ratio > self.upscale_warning_ratio:
                    self._log(
                        f"Avertissement upscale ({preset['label']} / {layer}): x{upscale_ratio:.2f}"
                    )

            alpha = rendered.getchannel("A")
            if layer_state["opacity"] < 1.0:
                alpha = alpha.point(lambda px: int(px * layer_state["opacity"]))
            canvas.paste(rendered, (x, y), alpha)

        file_stub = preset["filename"]
        ext = "png" if preset.get("png") else "jpg"
        file_name = f"{file_stub}-{base_name}.{ext}"
        out_path = export_dir / file_name

        if ext == "jpg":
            canvas.convert("RGB").save(out_path, quality=95)
        else:
            canvas.save(out_path)
        self._log(f"Export {preset['label']}: {out_path}")

    def _render_layer_for_export(self, layer_id: str, preset_id: str):
        preset_meta = PRESETS[preset_id]
        canvas_w, canvas_h = preset_meta["size"]
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
        rendered = source.resize(target_size, Image.Resampling.LANCZOS)
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
    window = ARPlusWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

