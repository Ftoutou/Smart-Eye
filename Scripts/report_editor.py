from PyQt5.QtCore import Qt, QPoint, QRect
from PyQt5.QtGui import QImage, QPainter, QPixmap, QIcon
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QFileDialog, QMessageBox, QLabel
)
from PyQt5.QtPrintSupport import QPrinter
import os, datetime


class FloatingImage(QLabel):
    def __init__(self, pixmap: QPixmap, parent):
        super().__init__(parent)
        self.original_pix = pixmap
        self.setPixmap(pixmap)
        self.setScaledContents(True)
        self.setFixedSize(pixmap.size())
        self.setCursor(Qt.OpenHandCursor)
        self.dragging = False
        self.resizing = False
        self.offset = QPoint()
        self.corner_size = 12  # pixels for resizing handle
        self.scale_factor = 1.0  # current zoom

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            rect = self.rect()
            if rect.right() - self.corner_size <= event.pos().x() <= rect.right() and \
               rect.bottom() - self.corner_size <= event.pos().y() <= rect.bottom():
                self.resizing = True
                self.setCursor(Qt.SizeFDiagCursor)
            else:
                self.dragging = True
                self.offset = event.pos()
                self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.dragging:
            new_pos = self.mapToParent(event.pos() - self.offset)
            self.move(new_pos)
        elif self.resizing:
            new_w = max(40, event.pos().x())
            new_h = max(40, event.pos().y())
            self.setFixedSize(new_w, new_h)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.dragging = False
        self.resizing = False
        self.setCursor(Qt.OpenHandCursor)
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        angle = event.angleDelta().y()
        factor = 1.1 if angle > 0 else 0.9
        self.scale_factor *= factor
        self.scale_factor = max(0.1, min(5.0, self.scale_factor))  # clamp zoom
        new_size = self.original_pix.size() * self.scale_factor
        self.setFixedSize(new_size)
        scaled_pix = self.original_pix.scaled(
            self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.setPixmap(scaled_pix)
        event.accept()

class ReportEditor(QWidget):
    def __init__(self, patient_path, refresh_callback=None):
        super().__init__()
        self.setWindowTitle("Report Editor")
        self.setMinimumSize(900, 650)

        self.patient_path = patient_path
        self.refresh_callback = refresh_callback
        self.floating_images = []

        root = QVBoxLayout(self)

        # QTextEdit editor
        self.text_edit = QTextEdit()
        root.addWidget(self.text_edit)

        # Buttons
        bar = QHBoxLayout()
        btn_img = QPushButton("🖼️ Insert Image")
        btn_img.clicked.connect(self.insert_image)
        bar.addWidget(btn_img)

        bar.addStretch(1)

        btn_save = QPushButton("💾 Save as PDF")
        btn_save.clicked.connect(self.save_report)
        bar.addWidget(btn_save)
        root.addLayout(bar)

    # ---------------- IMAGE INSERTION ----------------
    def insert_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if not path:
            return

        pix = QPixmap(path)
        if pix.isNull():
            QMessageBox.warning(self, "Error", "Failed to load image.")
            return

        img_widget = FloatingImage(pix, self)
        # place image at center
        img_widget.move(
            (self.width() - img_widget.width()) // 2,
            (self.height() - img_widget.height()) // 2
        )
        img_widget.show()
        self.floating_images.append(img_widget)

    # ---------------- SAVE ----------------
    def save_report(self):
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Report_{ts}.pdf"
        path = os.path.join(self.patient_path, filename)

        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(path)

        painter = QPainter(printer)

        # --- scale factor: widget pixels -> PDF points
        page_rect = printer.pageRect()          # in points (PDF units)
        widget_rect = self.text_edit.viewport().rect()  # in pixels

        scale_x = page_rect.width() / widget_rect.width()
        scale_y = page_rect.height() / widget_rect.height()
        scale = min(scale_x, scale_y)  # keep aspect ratio

        painter.scale(scale, scale)

        # --- draw text
        self.text_edit.document().drawContents(painter)

        # --- draw floating images at correct positions
        for img in self.floating_images:
            pos = img.pos() - self.text_edit.pos()  # position inside editor
            rect = QRect(pos, img.size())
            painter.drawPixmap(rect, img.pixmap())

        painter.end()

        QMessageBox.information(self, "Saved", f"Saved as {filename}")
        if self.refresh_callback:
            self.refresh_callback()
        self.close()
