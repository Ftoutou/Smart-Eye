import os
import sys
import webbrowser
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import (
    QFont, QPixmap, QImage, QWheelEvent,
    QPainter, QPen, QColor
)
from PyQt5.QtWidgets import (
    QApplication, QFileDialog, QLabel, QHBoxLayout, QMainWindow,
    QPushButton, QVBoxLayout, QWidget, QScrollArea
)
import napari

from patient_panel import PatientPanel

class ZoomableImageViewer(QScrollArea):
    def __init__(self):
        super().__init__()
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.setWidget(self.image_label)
        self.setWidgetResizable(True)

        self.scale_factor = 1.0
        self._drag_position = None
        self._drawing = False
        self.pen_color = QColor("red")
        self.eraser_mode = False

        self.base_image = None
        self.drawing_layer = None
        self.last_point = None

        self._setup_tools()

    def _setup_tools(self):
        self.tool_bar = QWidget(self)
        layout = QHBoxLayout(self.tool_bar)
        layout.setSpacing(4)
        layout.setContentsMargins(4, 4, 4, 4)

        colors = ["black", "white", "red", "blue", "green", "yellow"]

        for color_name in colors:
            btn = QPushButton()
            btn.setFixedSize(20, 20)
            btn.setStyleSheet(f"background-color:{color_name};border-radius:10px;")
            btn.clicked.connect(lambda _, col=color_name: self.set_pen_color(col))
            layout.addWidget(btn)

        eraser_btn = QPushButton("🧽 Eraser")
        eraser_btn.clicked.connect(self.toggle_eraser)
        eraser_btn.setStyleSheet("background:#ddd; padding:4px 10px; border-radius:6px;")
        layout.addWidget(eraser_btn)

        save_btn = QPushButton("📂 Save")
        save_btn.clicked.connect(self.save_image)
        save_btn.setStyleSheet("background:#2ecc71;color:white; padding:4px 10px; border-radius:6px;")
        layout.addWidget(save_btn)

        self.tool_bar.setStyleSheet("background: #eee; border-radius: 8px;")
        self.tool_bar.setFixedHeight(40)
        self.tool_bar.move(10, 10)
        self.tool_bar.show()

    def set_pen_color(self, color_name):
        self.pen_color = QColor(color_name)
        self.eraser_mode = False

    def toggle_eraser(self):
        self.eraser_mode = not self.eraser_mode

    def save_image(self):
        if not self.base_image:
            return

        output = QPixmap(self.base_image.size())
        output.fill(Qt.transparent)
        painter = QPainter(output)
        painter.drawPixmap(0, 0, self.base_image)
        painter.drawPixmap(0, 0, self.drawing_layer)
        painter.end()

        save_path, _ = QFileDialog.getSaveFileName(self, "Save Image", "", "PNG (*.png)")
        if save_path:
            output.save(save_path, "PNG")

    def set_image(self, image_path):
        image = QImage(image_path)
        if image.isNull():
            self.image_label.setText("Failed to load image.")
            return

        self.base_image = QPixmap.fromImage(image)
        self.drawing_layer = QPixmap(self.base_image.size())
        self.drawing_layer.fill(Qt.transparent)
        self.scale_factor = 1.0
        self.update_view()

    def update_view(self):
        if not self.base_image:
            return

        combined = QPixmap(self.base_image.size())
        combined.fill(Qt.transparent)

        painter = QPainter(combined)
        painter.drawPixmap(0, 0, self.base_image)
        painter.drawPixmap(0, 0, self.drawing_layer)
        painter.end()

        scaled = combined.scaled(
            self.scale_factor * combined.size(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )

        self.image_label.setPixmap(scaled)
        self.image_label.resize(scaled.size())

    def wheelEvent(self, event: QWheelEvent):
        if not self.base_image:
            return

        angle = event.angleDelta().y()
        factor = 1.15 if angle > 0 else 0.85

        cursor_pos = event.pos()
        cursor_img = self.image_label.mapFrom(self.viewport(), cursor_pos)

        rel_x = cursor_img.x() / max(1, self.image_label.width())
        rel_y = cursor_img.y() / max(1, self.image_label.height())

        self.scale_factor *= factor
        self.update_view()

        new_x = int(self.image_label.width() * rel_x - self.viewport().width() / 2)
        new_y = int(self.image_label.height() * rel_y - self.viewport().height() / 2)
        self.horizontalScrollBar().setValue(new_x)
        self.verticalScrollBar().setValue(new_y)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drawing = True
            self.setCursor(Qt.CrossCursor)
            self.last_point = self._get_image_pos(event.pos())
        elif event.button() == Qt.RightButton:
            self.setCursor(Qt.ClosedHandCursor)
            self._drag_position = event.pos()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self._drawing:
            current_point = self._get_image_pos(event.pos())

            if self.drawing_layer and self.last_point and current_point:
                painter = QPainter(self.drawing_layer)
                if self.eraser_mode:
                    pen = QPen(Qt.transparent, 10 / self.scale_factor, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                    painter.setCompositionMode(QPainter.CompositionMode_Clear)
                else:
                    pen = QPen(self.pen_color, 3 / self.scale_factor, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)

                painter.setPen(pen)
                painter.drawLine(self.last_point, current_point)
                painter.end()

                self.last_point = current_point
                self.update_view()

        elif event.buttons() & Qt.RightButton and self._drag_position:
            delta = self._drag_position - event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() + delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() + delta.y())
            self._drag_position = event.pos()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setCursor(Qt.ArrowCursor)
            self._drawing = False
            self.last_point = None
        elif event.button() == Qt.RightButton:
            self.setCursor(Qt.ArrowCursor)
            self._drag_position = None

    def _get_image_pos(self, widget_pos):
        if not self.image_label.pixmap():
            return None

        label_pos = self.image_label.mapFrom(self.viewport(), widget_pos)
        scaled_size = self.image_label.pixmap().size()
        base_size = self.base_image.size()

        if scaled_size.width() == 0 or scaled_size.height() == 0:
            return None

        scale_x = base_size.width() / scaled_size.width()
        scale_y = base_size.height() / scaled_size.height()

        img_x = int(label_pos.x() * scale_x)
        img_y = int(label_pos.y() * scale_y)

        if 0 <= img_x < base_size.width() and 0 <= img_y < base_size.height():
            return QPoint(img_x, img_y)
        return None


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smart Eye")
        self.setMinimumSize(1200, 800)
        self.setStyleSheet("background:#f5f7fa;font-family:'Segoe UI';")

        self.viewer = None
        self.napari_widget = None
        self.image_viewer = ZoomableImageViewer()
        self.patient_panel = None

        load_napari_btn = self._make_btn("📁 Load Medical Image", self.load_napari_image)
        load_basic_img_btn = self._make_btn("🖼️ Open Image Viewer", self.load_basic_image)
        teams_btn = self._make_btn("💬 Open Teams", self.open_teams)
        self.patient_toggle_btn = self._make_btn("👤 Patient Management", self.toggle_patient_panel)

        top_bar = QHBoxLayout()
        top_bar.addWidget(load_napari_btn)
        top_bar.addWidget(load_basic_img_btn)
        top_bar.addWidget(teams_btn)
        top_bar.addWidget(self.patient_toggle_btn)

        title = QLabel("Ophthalmology Assistant")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))

        self.central = QWidget()
        self.main_v = QVBoxLayout()
        self.main_v.addWidget(title)
        self.main_v.addLayout(top_bar)
        self.main_v.addWidget(self.image_viewer, stretch=1)
        self.image_viewer.hide()

        self.main_layout = QHBoxLayout(self.central)
        self.main_layout.addLayout(self.main_v, stretch=1)

        self.setCentralWidget(self.central)

    def _make_btn(self, text, slot):
        btn = QPushButton(text)
        btn.clicked.connect(slot)
        btn.setFixedHeight(36)
        btn.setStyleSheet(
            "QPushButton{background:#2e86de;color:#fff;border-radius:6px;font-size:14px;padding:6px 12px}"
            "QPushButton:hover{background:#1e6ab3;}"
        )
        return btn

    def _remove_old_napari(self):
        if self.napari_widget:
            try:
                self.main_v.removeWidget(self.napari_widget)
                self.napari_widget.setParent(None)
                self.napari_widget.deleteLater()
                self.napari_widget = None
                self.viewer = None
            except Exception as e:
                print(f"Failed to delete old Napari widget: {e}")

    def load_napari_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Medical Image", "", "Images (*.dcm *.nii *.nii.gz)"
        )
        if not file_path:
            return

        self._remove_old_napari()
        self.image_viewer.hide()

        try:
            self.viewer = napari.Viewer(show=False)
            self.napari_widget = self.viewer.window._qt_window
            self.napari_widget.setWindowFlag(Qt.Widget, True)
            self.napari_widget.setParent(self)
            self.main_v.addWidget(self.napari_widget, stretch=1)
            self.napari_widget.show()

            ext = os.path.splitext(file_path)[1].lower()
            if ext == '.gz' and file_path.endswith('.nii.gz'):
                ext = '.nii.gz'

            if ext == ".dcm":
                import pydicom
                img = pydicom.dcmread(file_path).pixel_array
                self.viewer.add_image(img, name="DICOM")
            elif ext in {".nii", ".nii.gz"}:
                import nibabel as nib
                img = nib.load(file_path).get_fdata()
                self.viewer.add_image(img, name="NIfTI")

            self._patch_napari_file_menu()
        except Exception as e:
            print(f"Could not load {file_path}: {e}")

    def load_basic_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Image File", "", "Images (*.jpg *.jpeg *.png)"
        )
        if not file_path:
            return

        self._remove_old_napari()
        self.image_viewer.show()

        try:
            self.image_viewer.set_image(file_path)
        except Exception as e:
            print(f"Could not load image viewer: {e}")

    def open_teams(self):
        webbrowser.open("https://teams.microsoft.com")

    def _patch_napari_file_menu(self):
        try:
            main_window = self.viewer.window._qt_window
            for action in main_window.menuBar().actions():
                if action.text() == "&File":
                    file_menu = action.menu()
                    for sub_action in file_menu.actions():
                        if "Open File" in sub_action.text():
                            sub_action.triggered.disconnect()
                            sub_action.triggered.connect(self.load_napari_image)
                            return
        except Exception as e:
            print(f"⚠️ Failed to patch Napari menu: {e}")

    def toggle_patient_panel(self):
        if self.patient_panel is None:
            self.patient_panel = PatientPanel()
            self.main_layout.insertWidget(0, self.patient_panel)
        else:
            is_visible = self.patient_panel.isVisible()
            self.patient_panel.setVisible(not is_visible)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
