 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/ARPlus.py b/ARPlus.py
index 5335d09d68465f75ca14371f2f952396f9d24b32..66c39eb3e8216646d6ae46399d9ec829c5c3bd46 100644
--- a/ARPlus.py
+++ b/ARPlus.py
@@ -125,52 +125,52 @@ class ARPlusWindow(QMainWindow):
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
-            state[preset_id]["background"]["fit_mode"] = "cover"
-            state[preset_id]["character"]["fit_mode"] = "contain"
+            state[preset_id]["background"]["fit_mode"] = "crop"
+            state[preset_id]["character"]["fit_mode"] = "crop"
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
 
@@ -212,51 +212,51 @@ class ARPlusWindow(QMainWindow):
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
-        self.fit_combo.addItems(["cover", "contain", "free"])
+        self.fit_combo.addItems(["crop", "contain", "free"])
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
@@ -330,51 +330,51 @@ class ARPlusWindow(QMainWindow):
 
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
-            self.state[self.current_preset][layer]["fit_mode"] = "cover"
+            self.state[self.current_preset][layer]["fit_mode"] = "crop"
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
@@ -399,59 +399,59 @@ class ARPlusWindow(QMainWindow):
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
-            layer_state["fit_mode"] = "cover"
+            layer_state["fit_mode"] = "crop"
             layer_state["transform"]["x"] = 0
             layer_state["transform"]["y"] = 0
             layer_state["transform"]["scale"] = 1.0
         elif layer_id == "character":
-            layer_state["fit_mode"] = "contain"
+            layer_state["fit_mode"] = "crop"
             layer_state["transform"]["x"] = width * 0.5
-            layer_state["transform"]["y"] = height * 0.95
-            layer_state["transform"]["scale"] = 0.85
+            layer_state["transform"]["y"] = height * 0.8
+            layer_state["transform"]["scale"] = 1.0
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
@@ -480,51 +480,51 @@ class ARPlusWindow(QMainWindow):
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
 
         if base is None or base.isNull():
             return QPixmap()
 
         src_w = base.width()
         src_h = base.height()
         if src_w == 0 or src_h == 0:
             return QPixmap()
 
-        if fit_mode == "cover":
+        if fit_mode in {"cover", "crop"}:
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
@@ -604,51 +604,51 @@ class ARPlusWindow(QMainWindow):
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
 
-        if fit_mode == "cover":
+        if fit_mode in {"cover", "crop"}:
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
 
 
EOF
)