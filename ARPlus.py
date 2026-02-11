import copy
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

from PIL import Image, ImageDraw, ImageFont
from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGraphicsPixmapItem,
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
    pixmap: QPixmap = QPixmap()
    pil: Image.Image | None = None


class LayerGraphicsItem(QGraphicsPixmapItem):
    moved = Signal(str, float, float)

    def __init__(self, layer_id: str):
        super().__init__()
        self.layer_id = layer_id
        self.setFlag(QGraphicsPixmapItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsPixmapItem.GraphicsItemFlag.ItemSendsScenePositionChanges, True)
        self.setTransformationMode(Qt.TransformationMode.SmoothTransformation)

    def itemChange(self, change, value):
        if change == QGraphicsPixmapItem.GraphicsItemChange.ItemPositionHasChanged:
            pos = self.pos()
            self.moved.emit(self.layer_id, pos.x(), pos.y())
        return super().itemChange(change, value)


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
        self.logo_text_color = "#FFFFFF"
        self.upscale_warning_ratio = 1.75
        self.current_preset = "poster"
        self.updating_ui = False

        self.state = self._build_default_state()

        self.scene = QGraphicsScene(self)
        self.view = CanvasView(self)
        self.view.setScene(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self.view.wheelScaled.connect(self._on_wheel_scaled)

        self.items: Dict[str, LayerGraphicsItem] = {}
        for layer in ["background", "character", "logo"]:
            item = LayerGraphicsItem(layer)
            item.moved.connect(self._on_layer_moved)
            self.scene.addItem(item)
            self.items[layer] = item

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
            state[preset_id]["background"]["fit_mode"] = "cover"
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
        logo_btn = QPushButton("Importer Logo image")
        logo_btn.clicked.connect(lambda: self._import_layer("logo"))
        resources_layout.addWidget(bg_btn)
        resources_layout.addWidget(char_btn)
        resources_layout.addWidget(logo_btn)

        self.logo_text_checkbox = QCheckBox("Logo texte")
        self.logo_text_checkbox.toggled.connect(self._on_logo_text_toggle)
        self.logo_text_input = QLineEdit()
        self.logo_text_input.setPlaceholderText("Texte du logo")
        self.logo_text_input.textChanged.connect(self._on_logo_text_changed)
        self.logo_text_size_spin = QSpinBox()
        self.logo_text_size_spin.setRange(12, 600)
        self.logo_text_size_spin.setValue(self.logo_text_size)
        self.logo_text_size_spin.valueChanged.connect(self._on_logo_text_size_changed)
        self.logo_color_btn = QPushButton("Couleur du logo texte")
        self.logo_color_btn.clicked.connect(self._pick_logo_color)

        form = QFormLayout()
        form.addRow("Contenu", self.logo_text_input)
        form.addRow("Taille", self.logo_text_size_spin)
        resources_layout.addWidget(self.logo_text_checkbox)
        resources_layout.addLayout(form)
        resources_layout.addWidget(self.logo_color_btn)

        layout.addWidget(resources_box)

        layer_box = QGroupBox("Contrôles de calque")
        layer_layout = QFormLayout(layer_box)
        self.layer_combo = QComboBox()
        for layer in ["background", "character", "logo"]:
            layer_layout_label = {"background": "Background", "character": "Character", "logo": "Logo"}[layer]
            self.layer_combo.addItem(layer_layout_label, layer)
        self.layer_combo.currentIndexChanged.connect(self._sync_layer_controls)

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

        self.fit_combo = QComboBox()
        self.fit_combo.addItems(["cover", "contain", "free"])
        self.fit_combo.currentTextChanged.connect(self._on_fit_mode_changed)

        reset_btn = QPushButton("Réinitialiser le calque")
        reset_btn.clicked.connect(self._on_reset_layer)

        layer_layout.addRow("Calque", self.layer_combo)
        layer_layout.addRow(self.visible_check)
        layer_layout.addRow("Opacité", self.opacity_slider)
        layer_layout.addRow("Échelle", self.scale_slider)
        layer_layout.addRow("Mode", self.fit_combo)
        layer_layout.addRow(reset_btn)
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
        self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def _selected_layer(self) -> str:
        return self.layer_combo.currentData()

    def _layer_state(self, preset_id: str, layer_id: str):
        return self.state[preset_id][layer_id]

    def _log(self, message: str):
        self.log_box.appendPlainText(message)

    def _on_preset_changed(self):
        self.current_preset = self.preset_combo.currentData()
        self._set_scene_for_preset(self.current_preset)
        self._refresh_preview()
        self._sync_layer_controls()

    def _on_logo_text_toggle(self, checked: bool):
        self.logo_text_enabled = checked
        self._refresh_preview()

    def _on_logo_text_changed(self, text: str):
        self.logo_text = text
        self._refresh_preview()

    def _on_logo_text_size_changed(self, value: int):
        self.logo_text_size = value
        self._refresh_preview()

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

    def _on_fit_mode_changed(self, text: str):
        layer = self._selected_layer()
        self._layer_state(self.current_preset, layer)["fit_mode"] = text
        self._refresh_preview()

    def _on_reset_layer(self):
        layer = self._selected_layer()
        self.state[self.current_preset][layer] = self._build_default_layer()
        if layer == "background":
            self.state[self.current_preset][layer]["fit_mode"] = "cover"
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

    def _sync_layer_controls(self):
        if self.updating_ui:
            return
        self.updating_ui = True
        layer = self._selected_layer()
        layer_state = self._layer_state(self.current_preset, layer)
        self.visible_check.setChecked(layer_state["visible"])
        self.opacity_slider.setValue(int(layer_state["opacity"] * 100))
        self.scale_slider.setValue(int(layer_state["transform"]["scale"] * 100))
        fit_idx = self.fit_combo.findText(layer_state["fit_mode"])
        if fit_idx >= 0:
            self.fit_combo.setCurrentIndex(fit_idx)
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
        if self.assets[layer_id].pixmap.isNull() and layer_id != "logo":
            return

        width, height = PRESETS[preset_id]["size"]
        layer_state = self._layer_state(preset_id, layer_id)

        if layer_id == "background":
            layer_state["fit_mode"] = "cover"
            layer_state["transform"]["x"] = 0
            layer_state["transform"]["y"] = 0
            layer_state["transform"]["scale"] = 1.0
        elif layer_id == "character":
            layer_state["fit_mode"] = "contain"
            layer_state["transform"]["x"] = width * 0.5
            layer_state["transform"]["y"] = height * 0.95
            layer_state["transform"]["scale"] = 0.85
        elif layer_id == "logo":
            layer_state["fit_mode"] = "contain"
            layer_state["transform"]["scale"] = 0.2
            if preset_id == "poster":
                layer_state["transform"]["x"] = width * 0.5
                layer_state["transform"]["y"] = height * 0.1
            elif preset_id == "hero":
                layer_state["transform"]["x"] = width * 0.22
                layer_state["transform"]["y"] = height * 0.18
            else:
                layer_state["transform"]["x"] = width * 0.5
                layer_state["transform"]["y"] = height * 0.15

    def _refresh_preview(self):
        preset_meta = PRESETS[self.current_preset]
        canvas_w, canvas_h = preset_meta["size"]

        for layer in ["background", "character", "logo"]:
            item = self.items[layer]
            layer_state = self._layer_state(self.current_preset, layer)
            if not layer_state["visible"]:
                item.setVisible(False)
                continue
            if layer == "logo" and self.current_preset == "background_no_logo":
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
            if layer == "background":
                item.setPos(pos_x, pos_y)
            else:
                item.setOffset(-pixmap.width() / 2, -pixmap.height() / 2)
                item.setPos(pos_x, pos_y)

    def _preview_pixmap(self, layer_id: str, canvas_w: int, canvas_h: int) -> QPixmap:
        layer_state = self._layer_state(self.current_preset, layer_id)
        fit_mode = layer_state["fit_mode"]
        scale = layer_state["transform"]["scale"]

        if layer_id == "logo" and self.logo_text_enabled and self.logo_text:
            pixmap = QPixmap(1200, 300)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setPen(QColor(self.logo_text_color))
            font = painter.font()
            font.setBold(True)
            font.setPointSize(max(16, int(self.logo_text_size / 3)))
            painter.setFont(font)
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, self.logo_text)
            painter.end()
            base = pixmap
        else:
            base = self.assets[layer_id].pixmap

        if base.isNull():
            return QPixmap()

        src_w = base.width()
        src_h = base.height()
        if src_w == 0 or src_h == 0:
            return QPixmap()

        if fit_mode == "cover":
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

        base_name = self.base_name_input.text().strip() or "Name"
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
            if layer == "logo" and preset.get("skip_logo"):
                continue

            layer_state = self._layer_state(preset_id, layer)
            if not layer_state["visible"]:
                continue

            rendered = self._render_layer_for_export(layer, preset_id)
            if rendered is None:
                continue

            lw, lh = rendered.size
            if layer == "background":
                x = int(layer_state["transform"]["x"])
                y = int(layer_state["transform"]["y"])
            else:
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
        file_name = f'{file_stub}-"{base_name}".{ext}'
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
            img = Image.new("RGBA", (2400, 600), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            font = self._load_logo_font()
            bbox = draw.textbbox((0, 0), self.logo_text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            x = (img.width - text_w) // 2
            y = (img.height - text_h) // 2
            draw.text((x, y), self.logo_text, fill=self.logo_text_color, font=font)
            source = img
        else:
            source = self.assets[layer_id].pil

        if source is None:
            return None

        sw, sh = source.size
        if sw == 0 or sh == 0:
            return None

        if fit_mode == "cover":
            ratio = max(canvas_w / sw, canvas_h / sh)
        elif fit_mode == "contain":
            ratio = min(canvas_w / sw, canvas_h / sh)
        else:
            ratio = 1.0
        ratio *= scale

        target_size = (max(1, int(sw * ratio)), max(1, int(sh * ratio)))
        return source.resize(target_size, Image.Resampling.LANCZOS)

    def _load_logo_font(self):
        font_candidates = [
            "Montserrat-Bold.ttf",
            "/usr/share/fonts/truetype/montserrat/Montserrat-Bold.ttf",
            "/Library/Fonts/Montserrat-Bold.ttf",
            "C:/Windows/Fonts/montserrat-bold.ttf",
        ]
        for candidate in font_candidates:
            try:
                return ImageFont.truetype(candidate, self.logo_text_size)
            except OSError:
                continue
        self._log("Avertissement: Montserrat Bold introuvable, police de secours utilisée.")
        return ImageFont.load_default()


def main():
    app = QApplication(sys.argv)
    window = ARPlusWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
