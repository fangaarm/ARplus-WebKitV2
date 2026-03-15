import os
import re
import sys
from datetime import datetime

from PySide6.QtCore import (
    Qt, QRectF, QSettings, QTimer
)
from PySide6.QtGui import (
    QPixmap, QImage, QPainter, QPainterPath, QTransform, QIcon,
    QColor, QPen, QBrush
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QLabel, QSlider, QFormLayout, QSpinBox,
    QTabWidget, QGraphicsView, QGraphicsScene,
    QGraphicsPixmapItem, QGraphicsPathItem, QGraphicsItem,
    QAbstractSpinBox, QCheckBox
)

# ==================================================
# PATHS
# ==================================================
def resource_path(relative_path: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.abspath(os.path.dirname(__file__)))
    return os.path.join(base, relative_path)

# ==================================================
# APP
# ==================================================
APP_TITLE = "TOP-AR+"
ICON_ICO = resource_path("assets/icon.ico")
ICON_PNG = resource_path("assets/icon.png")

# ==================================================
# CANVAS
# ==================================================
CANVAS_W = 1600
CANVAS_H = 2400

# ==================================================
# VIGNETTE
# ==================================================
VIGNETTE_X = 680
VIGNETTE_Y = 570
VIGNETTE_W = 869
VIGNETTE_H = 1346
VIGNETTE_RADIUS = 120

# ==================================================
# DEFAULTS
# ==================================================
DEFAULT_OFFSET_X = 0
DEFAULT_OFFSET_Y = 0
DEFAULT_ZOOM = 100
DEFAULT_STRETCH_X = 100
DEFAULT_STRETCH_Y = 100

IMPORT_PREFIX = "visuel-Poster-1600x2400-"

# ==================================================
# EXPORT SETTINGS
# ==================================================
JPEG_QUALITY = 95  # "haute qualité" (0-100)

# ==================================================
# THEME
# ==================================================
def apply_theme(app: QApplication):
    app.setStyleSheet("""
    QWidget {
        background: #2B2B2B;
        color: #F2F2F2;
        font-size: 13px;
    }

    QPushButton {
        background: #3A3A3A;
        border: 1px solid #4A4A4A;
        padding: 6px 10px;
    }

    QSlider::groove:horizontal {
        height: 6px;
        background: #4A4A4A;
    }

    QSlider::handle:horizontal {
        width: 12px;
        margin: -5px 0;
        background: #EDEDED;
    }

    QSpinBox {
        background: #333;
        border: 1px solid #4A4A4A;
        padding: 2px 6px;
    }

    QCheckBox {
        padding: 4px 6px;
    }
    """)

# ==================================================
# VIEW
# ==================================================
class View(QGraphicsView):
    def wheelEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            self.scale(factor, factor)
        else:
            super().wheelEvent(event)

# ==================================================
# TOP PANEL
# ==================================================
class TopPanel(QWidget):
    def __init__(self, top_number: int, settings: QSettings):
        super().__init__()
        self.top_number = top_number
        self.settings = settings

        self.template_path = resource_path(f"assets/{top_number}.png")
        self.last_import_path = None
        self._pm_cover = None

        main = QVBoxLayout(self)

        # ===== Toolbar
        bar = QHBoxLayout()
        self.btn_import = QPushButton("📥 Importer")
        self.btn_export = QPushButton("💾 Exporter")
        self.btn_fit = QPushButton("🔎 Centrer la vue")
        self.info = QLabel(f"TOP {top_number} prêt")
        self.info.setStyleSheet("color:#aaa;")

        bar.addWidget(self.btn_import)
        bar.addWidget(self.btn_export)
        bar.addWidget(self.btn_fit)
        bar.addStretch()
        bar.addWidget(self.info)
        main.addLayout(bar)

        # ===== Scene
        self.scene = QGraphicsScene(0, 0, CANVAS_W, CANVAS_H)
        self.view = View(self.scene)

        content = QHBoxLayout()
        main.addLayout(content, 1)

        # ===== Controls
        left = QVBoxLayout()
        content.addLayout(left, 0)

        controls = QWidget()
        controls.setFixedWidth(430)
        left.addWidget(controls)

        form = QFormLayout(controls)

        def make_slider(minv, maxv, val, step):
            row = QHBoxLayout()
            s = QSlider(Qt.Horizontal)
            s.setRange(minv, maxv)
            s.setValue(val)
            sp = QSpinBox()
            sp.setRange(minv, maxv)
            sp.setValue(val)
            sp.setSingleStep(step)
            sp.setButtonSymbols(QAbstractSpinBox.PlusMinus)

            s.valueChanged.connect(sp.setValue)
            sp.valueChanged.connect(s.setValue)
            s.valueChanged.connect(self.apply_transform)

            row.addWidget(s)
            row.addWidget(sp)
            return s, sp, row

        self.sx, self.nx, r = make_slider(-5000, 5000, DEFAULT_OFFSET_X, 10)
        form.addRow("Offset X", r)
        self.sy, self.ny, r = make_slider(-5000, 5000, DEFAULT_OFFSET_Y, 10)
        form.addRow("Offset Y", r)
        self.szoom, self.nzoom, r = make_slider(10, 400, DEFAULT_ZOOM, 5)
        form.addRow("Zoom %", r)
        self.sstretchx, self.nstretchx, r = make_slider(10, 400, DEFAULT_STRETCH_X, 5)
        form.addRow("Stretch X %", r)
        self.sstretchy, self.nstretchy, r = make_slider(10, 400, DEFAULT_STRETCH_Y, 5)
        form.addRow("Stretch Y %", r)

        content.addWidget(self.view, 1)

        # ===== Graphics
        clip = QRectF(VIGNETTE_X, VIGNETTE_Y, VIGNETTE_W, VIGNETTE_H)
        path = QPainterPath()
        path.addRoundedRect(clip, VIGNETTE_RADIUS, VIGNETTE_RADIUS)

        # rose derrière l’image (overlay d'aide)
        self.overlay_hole = QGraphicsPathItem(path)
        self.overlay_hole.setBrush(QBrush(QColor(255, 60, 180, 60)))
        self.overlay_hole.setPen(QPen(QColor(255, 60, 180), 2))
        self.overlay_hole.setZValue(5)
        self.scene.addItem(self.overlay_hole)

        self.mask_item = QGraphicsPathItem(path)
        self.mask_item.setFlag(QGraphicsItem.ItemClipsChildrenToShape)
        self.mask_item.setZValue(10)
        self.scene.addItem(self.mask_item)

        self.import_item = QGraphicsPixmapItem(self.mask_item)
        self.import_item.setZValue(11)

        self.template_item = QGraphicsPixmapItem()
        self.template_item.setZValue(100)
        self.scene.addItem(self.template_item)

        # ===== Info bar (sans estimation)
        self.info_bar = QLabel("📥 Aucun import")
        self.info_bar.setStyleSheet("color:#9a9a9a; font-size:12px;")
        main.addWidget(self.info_bar)

        # ===== Connect
        self.btn_import.clicked.connect(self.import_image)
        self.btn_export.clicked.connect(self.on_export_clicked)
        self.btn_fit.clicked.connect(self.fit_view)

        self.load_template()

    # ==================================================
    # HELPERS
    # ==================================================
    def _format_size(self, size: int) -> str:
        for unit in ("o", "Ko", "Mo", "Go"):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} To"

    def _export_basename_from_import(self) -> str:
        date_suffix = datetime.now().strftime("%Y-%m-%d")
        prefix = f"TOP {self.top_number} - "

        if not self.last_import_path:
            return f"{prefix}export - {date_suffix}"

        name = os.path.splitext(os.path.basename(self.last_import_path))[0]
        if name.startswith(IMPORT_PREFIX):
            name = name[len(IMPORT_PREFIX):]

        name = re.sub(r'[\\/:*?"<>|]', "-", name).strip()
        title = name if name else "export"
        return f"{prefix}{title} - {date_suffix}"

    def set_import_path(self, fp: str):
        """Charge une image depuis un chemin (utilisé aussi pour sync-all)."""
        if not fp:
            return

        self.last_import_path = fp

        pm = QPixmap(fp)
        self._pm_cover = pm.scaled(
            VIGNETTE_W, VIGNETTE_H,
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation
        )
        self.apply_transform()

    def export_to_jpeg(self, out: str) -> bool:
        """Export sans dialog en JPEG HQ (utilisé pour export-all)."""
        if not out:
            return False

        # Render direct en RGB (JPEG = pas d'alpha).
        # Comme ton trou est rempli par l'image importée + cadre par-dessus,
        # ça sort exactement comme l'affichage.
        img = QImage(CANVAS_W, CANVAS_H, QImage.Format_RGB32)

        painter = QPainter(img)
        self.overlay_hole.setVisible(False)
        self.scene.render(painter)
        painter.end()
        self.overlay_hole.setVisible(True)

        ok = img.save(out, "JPEG", JPEG_QUALITY)
        self.info.setText("✅ Export OK" if ok else "❌ Export échoué")
        return ok

    # ==================================================
    # VIEW
    # ==================================================
    def load_template(self):
        pm = QPixmap(self.template_path)
        if not pm.isNull():
            self.template_item.setPixmap(
                pm.scaled(CANVAS_W, CANVAS_H, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            )

    def fit_view(self):
        self.view.fitInView(QRectF(0, 0, CANVAS_W, CANVAS_H), Qt.KeepAspectRatio)

    # ==================================================
    # ACTIONS
    # ==================================================
    def import_image(self):
        last_dir = self.settings.value("last_dir", os.getcwd())
        fp, _ = QFileDialog.getOpenFileName(
            self, "Importer image", last_dir, "Images (*.png *.jpg *.jpeg)"
        )
        if not fp:
            return

        self.settings.setValue("last_dir", os.path.dirname(fp))

        mw = self.window()
        if hasattr(mw, "sync_all") and mw.sync_all():
            mw.import_to_all(fp)
        else:
            self.set_import_path(fp)

    def apply_transform(self):
        if not self._pm_cover:
            return

        zoom = self.nzoom.value() / 100.0
        sx = self.nstretchx.value() / 100.0
        sy = self.nstretchy.value() / 100.0

        self.import_item.setPixmap(self._pm_cover)
        self.import_item.setTransform(QTransform().scale(zoom * sx, zoom * sy))
        self.import_item.setPos(
            VIGNETTE_X + self.nx.value(),
            VIGNETTE_Y + self.ny.value()
        )

        # Info bar (sans estimation)
        try:
            sz = os.path.getsize(self.last_import_path) if self.last_import_path else None
        except OSError:
            sz = None

        if self.last_import_path and sz is not None:
            self.info_bar.setText(
                f"📥 Import : {os.path.basename(self.last_import_path)} "
                f"({self._format_size(sz)})"
            )
        elif self.last_import_path:
            self.info_bar.setText(f"📥 Import : {os.path.basename(self.last_import_path)}")
        else:
            self.info_bar.setText("📥 Aucun import")

    def on_export_clicked(self):
        mw = self.window()
        if hasattr(mw, "sync_all") and mw.sync_all():
            mw.export_all()
        else:
            self.export_jpeg_dialog()

    def export_jpeg_dialog(self):
        default_name = self._export_basename_from_import() + ".jpg"
        last_export_dir = self.settings.value("last_export_dir", os.getcwd())
        default_path = os.path.join(last_export_dir, default_name)

        out, _ = QFileDialog.getSaveFileName(
            self, f"Exporter TOP {self.top_number}", default_path, "JPEG (*.jpg *.jpeg)"
        )
        if not out:
            return

        self.settings.setValue("last_export_dir", os.path.dirname(out))

        # Export du TOP courant en JPEG HQ
        ok = self.export_to_jpeg(out)
        if ok:
            self.info.setText("✅ Export JPEG OK")

# ==================================================
# MAIN WINDOW
# ==================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1500, 950)

        self.settings = QSettings("TOP-AR", "TOP-ARPLUS")

        # Root + topbar (checkbox sync)
        root = QWidget()
        root_layout = QVBoxLayout(root)

        topbar = QHBoxLayout()
        self.cb_sync = QCheckBox("🔁 Appliquer à tous les TOP (import + export)")
        self.cb_sync.setChecked(False)
        topbar.addWidget(self.cb_sync)
        topbar.addStretch()
        root_layout.addLayout(topbar)

        self.tabs = QTabWidget()
        root_layout.addWidget(self.tabs, 1)
        self.setCentralWidget(root)

        for i in range(1, 6):
            self.tabs.addTab(TopPanel(i, self.settings), f"TOP {i}")

        self.tabs.currentChanged.connect(self.on_tab_changed)
        QTimer.singleShot(0, lambda: self.on_tab_changed(self.tabs.currentIndex()))

        # statusbar pour feedback export-all
        self.statusBar().showMessage("Prêt")

    def sync_all(self) -> bool:
        return self.cb_sync.isChecked()

    def on_tab_changed(self, index):
        panel = self.tabs.widget(index)
        if hasattr(panel, "fit_view"):
            QTimer.singleShot(0, panel.fit_view)

    def import_to_all(self, fp: str):
        if not fp:
            return
        self.settings.setValue("last_dir", os.path.dirname(fp))

        for i in range(self.tabs.count()):
            panel = self.tabs.widget(i)
            if hasattr(panel, "set_import_path"):
                panel.set_import_path(fp)

        self.statusBar().showMessage("📥 Import appliqué à tous les TOP", 4000)

    def export_all(self):
        last_export_dir = self.settings.value("last_export_dir", os.getcwd())
        folder = QFileDialog.getExistingDirectory(
            self, "Choisir un dossier d'export (tous les TOP)", last_export_dir
        )
        if not folder:
            return

        self.settings.setValue("last_export_dir", folder)

        ok_count = 0
        total = self.tabs.count()

        for i in range(total):
            panel = self.tabs.widget(i)
            if not hasattr(panel, "_export_basename_from_import") or not hasattr(panel, "export_to_jpeg"):
                continue

            filename = panel._export_basename_from_import() + ".jpg"
            out = os.path.join(folder, filename)

            if panel.export_to_jpeg(out):
                ok_count += 1

        self.statusBar().showMessage(f"💾 Export terminé : {ok_count}/{total} JPEG", 6000)

# ==================================================
# MAIN
# ==================================================
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    apply_theme(app)

    if os.path.exists(ICON_ICO):
        app.setWindowIcon(QIcon(ICON_ICO))
    elif os.path.exists(ICON_PNG):
        app.setWindowIcon(QIcon(ICON_PNG))

    w = MainWindow()
    w.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
