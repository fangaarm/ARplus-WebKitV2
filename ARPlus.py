import copy
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

from PIL import Image, ImageDraw, ImageFont
from PySide6.QtCore import QObject, QPointF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
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
        self.logo_text_size = 84
        self.logo_text_align = "center"
        self.logo_text_case = "normal"
        self.logo_text_color = "#FFFFFF"
        self.upscale_warning_ratio = 1.75
        self.current_preset = "poster"
        self.active_layer = "background"
        self.updating_ui = False

        self.state = self._build_default_state()

        self.scene = QGraphicsScene(self)
        self.view = CanvasView(self)
        self.view.setScene(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self.view.wheelScaled.connect(self._on_wheel_scaled)

        self.clip_item = QGraphicsRectItem()
        self.clip_item.setPen(QPen(Qt.PenStyle.NoPen))
        self.clip_item.setBrush(Qt.BrushStyle.NoBrush)
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
        for preset_id in PRESETS:
            state[preset_id] = {layer: self._build_default_layer() for layer in LAYER_ORDER}
            state[preset_id]["background"]["fit_mode"] = "crop"
            state[preset_id]["character"]["fit_mode"] = "contain"
            state[preset_id]["logo"]["fit_mode"] = "contain"
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
        self.logo_text_case_combo = QComboBox()
        self.logo_text_case_combo.addItem("Normal", "normal")
        self.logo_text_case_combo.addItem("TOUT EN MAJUSCULES", "upper")
        self.logo_text_case_combo.addItem("TOUT EN PETITES MAJUSCULES", "small_caps")
        self.logo_text_case_combo.currentIndexChanged.connect(self._on_logo_text_case_changed)
        self.logo_color_btn = QPushButton("Couleur du logo texte")
        self.logo_color_btn.clicked.connect(self._pick_logo_color)

        form = QFormLayout()
        form.addRow("Contenu", self.logo_text_input)
        form.addRow("Taille", self.logo_text_size_spin)
        form.addRow("Alignement", self.logo_text_align_combo)
        form.addRow("Casse", self.logo_text_case_combo)
        resources_layout.addWidget(self.logo_text_checkbox)
        resources_layout.addLayout(form)
        resources_layout.addWidget(self.logo_color_btn)

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

        self.scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.scale_slider.setRange(10, 300)
        self.scale_slider.setValue(100)
        self.scale_slider.valueChanged.connect(self._on_scale_changed)

        reset_btn = QPushButton("Réinitialiser le calque")
        reset_btn.clicked.connect(self._on_reset_layer)

        layer_layout.addRow("Calque", layer_buttons_row)
        layer_layout.addRow(self.visible_check)
        layer_layout.addRow("Opacité", self.opacity_slider)
        layer_layout.addRow("Échelle", self.scale_slider)
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
        exports_layout.addWidget(self.export_btn)
        exports_layout.addWidget(self.progress)
        exports_layout.addWidget(QLabel("Logs"))
        exports_layout.addWidget(self.log_box)

        layout.addWidget(exports)
        return panel

    def _set_scene_for_preset(self, preset_id: str):
        width, height = PRESETS[preset_id]["size"]
        self.scene.setSceneRect(0, 0, width, height)
        self.clip_item.setRect(0, 0, width, height)
        self.frame_item.setRect(0, 0, width, height)
        self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

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

    def _on_logo_text_case_changed(self):
        self.logo_text_case = self.logo_text_case_combo.currentData()
        self._refresh_preview()

    def _logo_effective_size(self) -> int:
        if self.logo_text_case == "small_caps":
            return max(12, int(self.logo_text_size * 0.82))
        return self.logo_text_size

    def _logo_preview_point_size(self) -> int:
        effective_size = self._logo_effective_size()
        return max(16, int(effective_size / 3))

    def _logo_export_spacing(self) -> int:
        effective_size = self._logo_effective_size()
        return max(6, effective_size // 8)

    def _logo_font_for_export(self):
        return self._load_logo_font(self._logo_effective_size())

    def _logo_display_text(self) -> str:
        text = self.logo_text
        if self.logo_text_case in {"upper", "small_caps"}:
            return text.upper()
        return text

    def _pick_logo_color(self):
        color = QColorDialog.getColor(QColor(self.logo_text_color), self)
        if color.isValid():
            self.logo_text_color = color.name()
            self._refresh_preview()

    def _on_visible_changed(self, checked: bool):
        layer = self._selected_layer()
        self._layer_state(self.current_preset, layer)["visible"] = checked
        self._refresh_preview()

    def _on_opacity_changed(self, value: int):
        layer = self._selected_layer()
        self._layer_state(self.current_preset, layer)["opacity"] = value / 100
        self._refresh_preview()

    def _on_scale_changed(self, value: int):
        layer = self._selected_layer()
        self._layer_state(self.current_preset, layer)["transform"]["scale"] = value / 100
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

    def _on_wheel_scaled(self, delta: float):
        layer = self._selected_layer()
        layer_state = self._layer_state(self.current_preset, layer)
        layer_state["transform"]["scale"] = max(0.1, min(4.0, layer_state["transform"]["scale"] + delta))
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
        elif layer_id == "character":
            layer_state["fit_mode"] = "contain"
            layer_state["transform"]["x"] = width * 0.5
            layer_state["transform"]["y"] = height * 0.5
            layer_state["transform"]["scale"] = 1.0
        elif layer_id == "logo":
            layer_state["fit_mode"] = "contain"
            layer_state["transform"]["scale"] = 0.2
            if preset_id == "poster":
                layer_state["transform"]["x"] = width * 0.5
                layer_state["transform"]["y"] = height * 0.1
            else:
                layer_state["transform"]["x"] = width * 0.14
                layer_state["transform"]["y"] = height * 0.15

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
            item.setOffset(-pixmap.width() / 2, -pixmap.height() / 2)
            item.setPos(pos_x, pos_y)

    def _preview_pixmap(self, layer_id: str, canvas_w: int, canvas_h: int) -> QPixmap:
        layer_state = self._layer_state(self.current_preset, layer_id)
        fit_mode = layer_state["fit_mode"]
        scale = layer_state["transform"]["scale"]

        if layer_id == "logo" and self.logo_text_enabled and self.logo_text:
            logo_text = self._logo_display_text()
            pixmap = QPixmap(1200, 300)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setPen(QColor(self.logo_text_color))
            font = painter.font()
            font.setBold(True)
            font.setPointSize(self._logo_preview_point_size())
            painter.setFont(font)
            align_map = {
                "left": Qt.AlignmentFlag.AlignLeft,
                "center": Qt.AlignmentFlag.AlignHCenter,
                "right": Qt.AlignmentFlag.AlignRight,
            }
            text_align = align_map.get(self.logo_text_align, Qt.AlignmentFlag.AlignHCenter)
            flags = text_align | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap
            painter.drawText(pixmap.rect().adjusted(30, 0, -30, 0), flags, logo_text)
            painter.end()
            base = pixmap
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
        return base.scaled(target_w, target_h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)

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
            img = Image.new("RGBA", (2400, 600), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            font = self._logo_font_for_export()
            spacing = self._logo_export_spacing()
            pil_align = self.logo_text_align
            bbox = draw.multiline_textbbox((0, 0), logo_text, font=font, align=pil_align, spacing=spacing)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            if pil_align == "left":
                x = int(img.width * 0.08)
            elif pil_align == "right":
                x = int(img.width * 0.92) - text_w
            else:
                x = (img.width - text_w) // 2
            y = (img.height - text_h) // 2
            draw.multiline_text(
                (x, y),
                logo_text,
                fill=self.logo_text_color,
                font=font,
                align=pil_align,
                spacing=spacing,
            )
            source = img
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
        return source.resize(target_size, Image.Resampling.LANCZOS)

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
