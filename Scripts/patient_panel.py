'''import os
import shutil
import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QListWidget, QLabel,
    QInputDialog, QMessageBox, QFileDialog, QListWidgetItem, QMenu
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor
from report_editor import ReportEditor


class PatientPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(280)
        self.setStyleSheet("QListWidget{background:#fff;border:1px solid #ccc;}")

        # Patients data folder
        self.patients_folder = os.path.join(os.getcwd(), "data", "patients")
        os.makedirs(self.patients_folder, exist_ok=True)

        layout = QVBoxLayout()

        title = QLabel("Patients")
        title.setStyleSheet("font-weight:bold;font-size:16px")
        layout.addWidget(title)

        # Patient list
        self.list = QListWidget()
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self.open_patient_context_menu)
        self.list.itemClicked.connect(self.display_patient_files)
        layout.addWidget(self.list)

        # File list for selected patient
        self.file_list = QListWidget()
        self.file_list.setStyleSheet("background:#f1f3f4;border:1px solid #ccc;")
        self.file_list.itemDoubleClicked.connect(self.open_file)
        self.file_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_list.customContextMenuRequested.connect(self.open_file_context_menu)
        layout.addWidget(self.file_list)

        # Add patient button
        add_btn = QPushButton("➕ Add Patient")
        add_btn.clicked.connect(self.add_patient)
        layout.addWidget(add_btn)

        self.setLayout(layout)
        self.load_existing_patients()

    # ---------------- PATIENT MANAGEMENT ----------------
    def add_patient(self):
        name, ok = QInputDialog.getText(self, "New Patient", "Enter patient name:")
        if not ok or not name.strip():
            return

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = f"{name.strip()}_{timestamp}"
        folder = os.path.join(self.patients_folder, safe_name)
        os.makedirs(folder, exist_ok=True)

        self.list.addItem(QListWidgetItem(safe_name))
        QMessageBox.information(self, "Success", f"Patient '{safe_name}' added.")

    def load_existing_patients(self):
        self.list.clear()
        for name in os.listdir(self.patients_folder):
            if os.path.isdir(os.path.join(self.patients_folder, name)):
                self.list.addItem(QListWidgetItem(name))

    # ---------------- PATIENT CONTEXT MENU ----------------
    def open_patient_context_menu(self, pos):
        item = self.list.itemAt(pos)
        if not item:
            return

        selected_name = item.text()
        patient_path = os.path.join(self.patients_folder, selected_name)

        menu = QMenu()
        import_action = menu.addAction("📁 Import Files")
        export_action = menu.addAction("📤 Export Files")
        open_folder_action = menu.addAction("📂 Open Folder")
        report_action = menu.addAction("📝 Generate Report")
        delete_action = menu.addAction("❌ Delete Patient")

        action = menu.exec_(QCursor.pos())

        if action == import_action:
            self.import_files(patient_path)
        elif action == export_action:
            self.export_files(patient_path)
        elif action == open_folder_action:
            self.open_folder(patient_path)
        elif action == report_action:
            self.generate_report(patient_path)
        elif action == delete_action:
            self.delete_patient(patient_path, item)

    # ---------------- FILE CONTEXT MENU ----------------
    def open_file_context_menu(self, pos):
        item = self.file_list.itemAt(pos)
        if not item:
            return

        menu = QMenu()
        open_action = menu.addAction("📂 Open File")
        rename_action = menu.addAction("✏️ Rename File")   # NEW
        delete_action = menu.addAction("🗑️ Delete File")

        action = menu.exec_(QCursor.pos())

        if action == open_action:
            self.open_file(item)
        elif action == rename_action:
            self.rename_file(item)
        elif action == delete_action:
            self.delete_file(item)

    # ---------------- PATIENT FILE OPERATIONS ----------------
    def import_files(self, patient_path):
        files, _ = QFileDialog.getOpenFileNames(self, "Import Files")
        if not files:
            return

        for file in files:
            try:
                shutil.copy(file, patient_path)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to copy {file}: {str(e)}")

        QMessageBox.information(self, "Import Complete", "Files imported successfully.")
        self.display_patient_files()

    def export_files(self, patient_path):
        files = os.listdir(patient_path)
        if not files:
            QMessageBox.information(self, "No files", "No files to export for this patient.")
            return

        dest_folder = QFileDialog.getExistingDirectory(self, "Select Export Folder")
        if not dest_folder:
            return

        for file in files:
            src = os.path.join(patient_path, file)
            dst = os.path.join(dest_folder, file)
            try:
                shutil.copy(src, dst)
            except Exception as e:
                QMessageBox.warning(self, "Export Error", f"Could not export {file}: {e}")

        QMessageBox.information(self, "Export Complete", "Files exported successfully.")

    def open_folder(self, patient_path):
        if os.path.exists(patient_path):
            os.startfile(patient_path)
        else:
            QMessageBox.warning(self, "Error", "Patient folder not found.")

    def delete_patient(self, patient_path, item):
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete patient '{item.text()}' and all files?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                shutil.rmtree(patient_path)
                self.list.takeItem(self.list.row(item))
                self.file_list.clear()
                QMessageBox.information(self, "Deleted", "Patient folder deleted.")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not delete folder: {e}")

    def delete_file(self, item):
        patient_item = self.list.currentItem()
        if not patient_item:
            return

        patient_path = os.path.join(self.patients_folder, patient_item.text())
        file_path = os.path.join(patient_path, item.text())

        reply = QMessageBox.question(
            self, "Confirm File Deletion",
            f"Are you sure you want to delete file '{item.text()}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes and os.path.exists(file_path):
            try:
                os.remove(file_path)
                self.file_list.takeItem(self.file_list.row(item))
                QMessageBox.information(self, "Deleted", "File deleted successfully.")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not delete file: {e}")

    def rename_file(self, item):
        patient_item = self.list.currentItem()
        if not patient_item:
            return

        patient_path = os.path.join(self.patients_folder, patient_item.text())
        file_path = os.path.join(patient_path, item.text())

        new_name, ok = QInputDialog.getText(self, "Rename File", "Enter new file name:")
        if ok and new_name.strip():
            new_path = os.path.join(patient_path, new_name)
            try:
                os.rename(file_path, new_path)
                item.setText(new_name)
                QMessageBox.information(self, "Renamed", "File renamed successfully.")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not rename file: {e}")

    # ---------------- REPORTS ----------------
    def generate_report(self, patient_path):
        self.editor = ReportEditor(patient_path, refresh_callback=lambda: self.display_patient_files())
        self.editor.show()

    # ---------------- DISPLAY ----------------
    def display_patient_files(self, item=None):
        if item is None:
            item = self.list.currentItem()
        if not item:
            return

        patient_path = os.path.join(self.patients_folder, item.text())
        if not os.path.exists(patient_path):
            return

        self.file_list.clear()
        for file in os.listdir(patient_path):
            self.file_list.addItem(QListWidgetItem(file))

    def open_file(self, item):
        patient_item = self.list.currentItem()
        if not patient_item:
            return

        patient_path = os.path.join(self.patients_folder, patient_item.text())
        file_path = os.path.join(patient_path, item.text())

        if os.path.exists(file_path):
            try:
                os.startfile(file_path)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not open file: {e}")
        else:
            QMessageBox.warning(self, "Error", "File not found.")'''



import os
import shutil
import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QListWidget, QLabel,
    QInputDialog, QMessageBox, QFileDialog, QListWidgetItem, QMenu,
    QLineEdit, QHBoxLayout, QComboBox, QTabWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor, QIcon
from report_editor import ReportEditor


class PatientPanel(QWidget):
    IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif"}
    PDF_EXTS = {".pdf"}
    REPORT_PREFIX = "Report_"

    def __init__(self):
        super().__init__()
        self.setFixedWidth(340)
        self.setStyleSheet("""
            QWidget { background: #f7f9fb; font-family: 'Segoe UI'; }
            QListWidget { background:#fff;border:1px solid #e0e0e0; }
            QLineEdit { background: #fff; border: 1px solid #ddd; padding: 6px; border-radius: 6px; }
            QComboBox { background: #fff; border: 1px solid #ddd; padding: 4px; border-radius: 6px; }
            QPushButton { background: #2e86de; color: #fff; border-radius: 6px; padding: 6px; }
            QPushButton.secondary { background: #6c757d; }
        """)

        self.patients_folder = os.path.join(os.getcwd(), "data", "patients")
        os.makedirs(self.patients_folder, exist_ok=True)

        self._patients_cache = []
        self.editor = None

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        title = QLabel("Patients")
        title.setStyleSheet("font-weight:bold;font-size:16px")
        layout.addWidget(title)

        # === Patient search ===
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search patients...")
        self.search_input.textChanged.connect(self.filter_patients)
        search_layout.addWidget(self.search_input)

        refresh_btn = QPushButton("⟳")
        refresh_btn.setFixedWidth(34)
        refresh_btn.setToolTip("Refresh patients")
        refresh_btn.setProperty("class", "secondary")
        refresh_btn.clicked.connect(self.load_existing_patients)
        search_layout.addWidget(refresh_btn)

        layout.addLayout(search_layout)

        # Patient list
        self.list = QListWidget()
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self.open_patient_context_menu)
        self.list.itemClicked.connect(self.display_patient_files)
        layout.addWidget(self.list, stretch=2)

        # Tabs for Files / Timeline
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("QTabWidget::pane { border: 1px solid #ccc; }")
        layout.addWidget(self.tabs, stretch=3)

        # === Files tab ===
        files_tab = QWidget()
        files_layout = QVBoxLayout(files_tab)
        files_layout.setContentsMargins(4, 4, 4, 4)

        file_filter_layout = QHBoxLayout()
        self.file_search = QLineEdit()
        self.file_search.setPlaceholderText("Filter files...")
        self.file_search.textChanged.connect(self.filter_files)
        file_filter_layout.addWidget(self.file_search)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All", "Images", "PDFs", "Reports", "Other"])
        self.filter_combo.currentIndexChanged.connect(self.filter_files)
        self.filter_combo.setFixedWidth(110)
        file_filter_layout.addWidget(self.filter_combo)

        files_layout.addLayout(file_filter_layout)

        self.file_list = QListWidget()
        self.file_list.setStyleSheet("background:#fff;border:1px solid #ccc;")
        self.file_list.itemDoubleClicked.connect(self.open_file)
        self.file_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_list.customContextMenuRequested.connect(self.open_file_context_menu)
        files_layout.addWidget(self.file_list)

        self.tabs.addTab(files_tab, "📂 Files")

        # === Timeline tab ===
        self.timeline_list = QListWidget()
        self.timeline_list.setStyleSheet("background:#fff;border:1px solid #ccc;")
        self.timeline_list.itemDoubleClicked.connect(self.open_file)
        self.timeline_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.timeline_list.customContextMenuRequested.connect(self.open_file_context_menu)

        self.tabs.addTab(self.timeline_list, "📅 Timeline")
        self.tabs.currentChanged.connect(self.refresh_timeline)

        # Buttons
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("➕ Add Patient")
        add_btn.clicked.connect(self.add_patient)
        btn_layout.addWidget(add_btn)

        import_btn = QPushButton("📁 Import Files")
        import_btn.clicked.connect(self.import_files_to_selected)
        btn_layout.addWidget(import_btn)

        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.load_existing_patients()

    # ---------------- PATIENTS ----------------
    def add_patient(self):
        name, ok = QInputDialog.getText(self, "New Patient", "Enter patient name:")
        if not ok or not name.strip():
            return
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = f"{name.strip()}_{timestamp}"
        folder = os.path.join(self.patients_folder, safe_name)
        try:
            os.makedirs(folder, exist_ok=False)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to create folder: {e}")
            return
        self._patients_cache.append(safe_name)
        self.filter_patients()
        QMessageBox.information(self, "Success", f"Patient '{safe_name}' added.")

    def load_existing_patients(self):
        self._patients_cache = []
        for name in sorted(os.listdir(self.patients_folder), reverse=True):
            if os.path.isdir(os.path.join(self.patients_folder, name)):
                self._patients_cache.append(name)
        self.filter_patients()

    def filter_patients(self):
        q = self.search_input.text().strip().lower()
        self.list.clear()
        for name in self._patients_cache:
            if not q or q in name.lower():
                self.list.addItem(QListWidgetItem(name))

    # ---------------- FILES ----------------
    def display_patient_files(self, item=None):
        if item is None:
            item = self.list.currentItem()
        if not item:
            self.file_list.clear()
            self.timeline_list.clear()
            return
        patient_path = os.path.join(self.patients_folder, item.text())
        if not os.path.exists(patient_path):
            return
        self._current_files = sorted(os.listdir(patient_path), reverse=True)
        self._apply_file_filters()
        self.refresh_timeline()

    def _apply_file_filters(self):
        self.file_list.clear()
        if not hasattr(self, "_current_files"):
            return
        query = self.file_search.text().strip().lower()
        type_choice = self.filter_combo.currentText()
        for fname in self._current_files:
            if query and query not in fname.lower():
                continue
            if not self._file_matches_filter(fname, type_choice):
                continue
            self.file_list.addItem(QListWidgetItem(fname))

    def filter_files(self):
        self._apply_file_filters()

    def _file_matches_filter(self, fname, type_choice):
        ext = os.path.splitext(fname)[1].lower()
        if type_choice == "All":
            return True
        if type_choice == "Images":
            return ext in self.IMAGE_EXTS
        if type_choice == "PDFs":
            return ext in self.PDF_EXTS
        if type_choice == "Reports":
            return fname.startswith(self.REPORT_PREFIX) or "report" in fname.lower()
        if type_choice == "Other":
            return (ext not in self.IMAGE_EXTS) and (ext not in self.PDF_EXTS)
        return True

    # ---------------- TIMELINE ----------------
    def refresh_timeline(self, idx=None):
        if self.tabs.currentWidget() != self.timeline_list:
            return
        self.timeline_list.clear()
        patient_item = self.list.currentItem()
        if not patient_item:
            return
        patient_path = os.path.join(self.patients_folder, patient_item.text())
        if not os.path.exists(patient_path):
            return
        files = os.listdir(patient_path)
        # sort by last modified date (newest first)
        files = sorted(files, key=lambda f: os.path.getmtime(os.path.join(patient_path, f)), reverse=True)
        for f in files:
            fpath = os.path.join(patient_path, f)
            ts = datetime.datetime.fromtimestamp(os.path.getmtime(fpath)).strftime("%Y-%m-%d %H:%M")
            ext = os.path.splitext(f)[1].lower()
            icon = "📄"
            if ext in self.IMAGE_EXTS:
                icon = "🖼️"
            elif ext in self.PDF_EXTS:
                icon = "📕"
            elif f.startswith(self.REPORT_PREFIX):
                icon = "📝"
            item = QListWidgetItem(f"{icon} {f}   ({ts})")
            item.setData(Qt.UserRole, f)  # store filename
            self.timeline_list.addItem(item)

    # ---------------- FILE OPS (reuse) ----------------
    def open_patient_context_menu(self, pos):
        item = self.list.itemAt(pos)
        if not item:
            return
        selected_name = item.text()
        patient_path = os.path.join(self.patients_folder, selected_name)
        menu = QMenu()
        import_action = menu.addAction("📁 Import Files")
        export_action = menu.addAction("📤 Export Files")
        open_folder_action = menu.addAction("📂 Open Folder")
        report_action = menu.addAction("📝 Generate Report")
        delete_action = menu.addAction("❌ Delete Patient")
        action = menu.exec_(QCursor.pos())
        if action == import_action:
            self.import_files(patient_path)
        elif action == export_action:
            self.export_files(patient_path)
        elif action == open_folder_action:
            self.open_folder(patient_path)
        elif action == report_action:
            self.generate_report(patient_path)
        elif action == delete_action:
            self.delete_patient(patient_path, item)

    def open_file_context_menu(self, pos):
        list_widget = self.sender()
        item = list_widget.itemAt(pos)
        if not item:
            return
        fname = item.text() if list_widget == self.file_list else item.data(Qt.UserRole)
        menu = QMenu()
        open_action = menu.addAction("📂 Open File")
        rename_action = menu.addAction("✏️ Rename File")
        delete_action = menu.addAction("🗑️ Delete File")
        action = menu.exec_(QCursor.pos())
        if action == open_action:
            self.open_file(item)
        elif action == rename_action:
            self.rename_file(item)
        elif action == delete_action:
            self.delete_file(item)

    def import_files(self, patient_path):
        files, _ = QFileDialog.getOpenFileNames(self, "Import Files")
        if not files:
            return
        for file in files:
            try:
                shutil.copy(file, patient_path)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to copy {file}: {str(e)}")
        self.display_patient_files()
        QMessageBox.information(self, "Import Complete", "Files imported successfully.")

    def import_files_to_selected(self):
        item = self.list.currentItem()
        if not item:
            QMessageBox.information(self, "Select patient", "Please select a patient first.")
            return
        patient_path = os.path.join(self.patients_folder, item.text())
        self.import_files(patient_path)

    def export_files(self, patient_path):
        files = os.listdir(patient_path)
        if not files:
            QMessageBox.information(self, "No files", "No files to export for this patient.")
            return
        dest_folder = QFileDialog.getExistingDirectory(self, "Select Export Folder")
        if not dest_folder:
            return
        for file in files:
            try:
                shutil.copy(os.path.join(patient_path, file), os.path.join(dest_folder, file))
            except Exception as e:
                QMessageBox.warning(self, "Export Error", f"Could not export {file}: {e}")
        QMessageBox.information(self, "Export Complete", "Files exported successfully.")

    def open_folder(self, patient_path):
        if os.path.exists(patient_path):
            os.startfile(patient_path)

    def delete_patient(self, patient_path, item):
        reply = QMessageBox.question(self, "Confirm Delete",
                                     f"Delete patient '{item.text()}' and all files?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            shutil.rmtree(patient_path)
            self.list.takeItem(self.list.row(item))
            self.file_list.clear()
            self.timeline_list.clear()
            QMessageBox.information(self, "Deleted", "Patient folder deleted.")

    def delete_file(self, item):
        patient_item = self.list.currentItem()
        if not patient_item:
            return
        patient_path = os.path.join(self.patients_folder, patient_item.text())
        fname = item.text() if item.listWidget() == self.file_list else item.data(Qt.UserRole)
        fpath = os.path.join(patient_path, fname)
        reply = QMessageBox.question(self, "Confirm File Deletion",
                                     f"Delete file '{fname}'?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes and os.path.exists(fpath):
            os.remove(fpath)
            self.display_patient_files()
            QMessageBox.information(self, "Deleted", "File deleted successfully.")

    def rename_file(self, item):
        patient_item = self.list.currentItem()
        if not patient_item:
            return
        patient_path = os.path.join(self.patients_folder, patient_item.text())
        fname = item.text() if item.listWidget() == self.file_list else item.data(Qt.UserRole)
        fpath = os.path.join(patient_path, fname)
        new_name, ok = QInputDialog.getText(self, "Rename File", "Enter new file name:")
        if ok and new_name.strip():
            new_path = os.path.join(patient_path, new_name)
            os.rename(fpath, new_path)
            self.display_patient_files()
            QMessageBox.information(self, "Renamed", "File renamed successfully.")

    # ---------------- REPORT ----------------
    def generate_report(self, patient_path):
        self.editor = ReportEditor(patient_path, refresh_callback=lambda: self.display_patient_files())
        self.editor.show()

    def open_file(self, item):
        patient_item = self.list.currentItem()
        if not patient_item:
            return
        patient_path = os.path.join(self.patients_folder, patient_item.text())
        fname = item.text() if item.listWidget() == self.file_list else item.data(Qt.UserRole)
        fpath = os.path.join(patient_path, fname)
        if os.path.exists(fpath):
            try:
                os.startfile(fpath)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not open file: {e}")

