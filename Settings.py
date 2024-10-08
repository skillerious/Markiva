import json
import os
import qtawesome as qta
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSpinBox, QColorDialog, QFileDialog, QFormLayout, 
    QDialogButtonBox, QGroupBox, QSizePolicy, QAbstractButton, QComboBox, QCheckBox
)
from PyQt5.QtGui import QColor, QPainter, QBrush, QPen, QIcon
from PyQt5.QtCore import Qt, QPropertyAnimation, QRect, pyqtProperty, QEasingCurve, QSize

class Toggle(QAbstractButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._offset = 0
        self._thumb_color = QColor("#ffffff")  # Thumb color (white)
        self._track_color = QColor("#777777")  # Default track color (gray)
        self._thumb_radius = 8  # Smaller thumb radius
        self._track_radius = 10  # Smaller track radius
        self._is_on = False
        self._animation = QPropertyAnimation(self, b"offset", self)
        self._animation.setEasingCurve(QEasingCurve.OutBounce)
        self._animation.setDuration(200)
        self.setFixedSize(40, 20)  # Smaller size for the toggle

    @pyqtProperty(float)
    def offset(self):
        return self._offset

    @offset.setter
    def offset(self, value):
        self._offset = value
        self.update()

    def paintEvent(self, event):
        thumb_rect = QRect(
            int(2 + self._offset),  # Cast to int
            2,
            self._thumb_radius * 2,
            self._thumb_radius * 2
        )

        track_rect = QRect(
            0,
            0,
            self.width(),
            self.height()
        )

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw track
        painter.setBrush(QBrush(self._track_color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(track_rect, self._track_radius, self._track_radius)

        # Draw thumb
        painter.setBrush(QBrush(self._thumb_color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(thumb_rect)

    def sizeHint(self):
        return QSize(40, 20)  # Size hint matches the fixed size

    def enterEvent(self, event):
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.update()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self._is_on = not self._is_on
        self._track_color = QColor("#0078d4") if self._is_on else QColor("#777777")  # Blue when on, gray when off
        self._animation.setStartValue(self.offset)
        self._animation.setEndValue(self.width() - self._thumb_radius * 2 - 2 if self._is_on else 0)
        self._animation.start()

    def toggle(self):
        self._is_on = not self._is_on
        self._track_color = QColor("#0078d4") if self._is_on else QColor("#777777")  # Blue when on, gray when off
        self._animation.setStartValue(self.offset)
        self._animation.setEndValue(self.width() - self._thumb_radius * 2 - 2 if self._is_on else 0)
        self._animation.start()
        super().toggle()

    def isChecked(self):
        return self._is_on


class SettingsWindow(QDialog):
    def __init__(self, settings_file, parent=None):
        super().__init__(parent)
        
        # Set the window icon
        self.setWindowIcon(QIcon("images/MarkivaLogo.png"))
        
        self.setWindowTitle("Application Settings")
        self.setFixedSize(500, 700)

        self.settings_file = settings_file
        self.settings = self.load_settings()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        # Font Settings Group
        font_group = QGroupBox("Font Settings")
        font_layout = QFormLayout()
        font_layout.setSpacing(10)

        # Font Size Setting
        self.font_size_spinbox = QSpinBox(self)
        self.font_size_spinbox.setRange(8, 36)
        self.font_size_spinbox.setValue(self.settings.get("font_size", 14))
        font_layout.addRow("Font Size:", self.font_size_spinbox)

        # Font Family Setting
        self.font_family_combo = QComboBox(self)
        self.font_family_combo.addItems(["Fira Code", "Consolas", "Courier New", "Arial", "Times New Roman"])
        self.font_family_combo.setCurrentText(self.settings.get("font_family", "Consolas"))
        font_layout.addRow("Font Family:", self.font_family_combo)

        # Dark Mode Setting (Animated Toggle Switch)
        self.dark_mode_toggle = Toggle(self)
        self.dark_mode_toggle.setChecked(self.settings.get("dark_mode", True))
        font_layout.addRow("Enable Dark Mode:", self.dark_mode_toggle)

        font_group.setLayout(font_layout)

        # Project Settings Group
        project_group = QGroupBox("Project Settings")
        project_layout = QFormLayout()
        project_layout.setSpacing(10)

        # Default Project Folder
        self.project_folder_line_edit = QLineEdit(self)
        self.project_folder_line_edit.setText(self.settings.get("default_project_folder", os.getcwd()))
        self.choose_folder_button = QPushButton(qta.icon('fa.folder-open'), "")
        self.choose_folder_button.clicked.connect(self.choose_project_folder)
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(self.project_folder_line_edit)
        folder_layout.addWidget(self.choose_folder_button)
        project_layout.addRow("Default Project Folder:", folder_layout)

        # Default Open File
        self.open_file_line_edit = QLineEdit(self)
        self.open_file_line_edit.setText(self.settings.get("default_open_file", ""))
        self.choose_file_button = QPushButton(qta.icon('fa.file'), "")
        self.choose_file_button.clicked.connect(self.choose_default_open_file)
        file_layout = QHBoxLayout()
        file_layout.addWidget(self.open_file_line_edit)
        file_layout.addWidget(self.choose_file_button)
        project_layout.addRow("Default Open File:", file_layout)

        project_group.setLayout(project_layout)

        # Auto Save Settings Group
        autosave_group = QGroupBox("Auto Save Settings")
        autosave_layout = QFormLayout()
        autosave_layout.setSpacing(10)

        # Auto Save Interval
        self.auto_save_interval_spinbox = QSpinBox(self)
        self.auto_save_interval_spinbox.setRange(1, 60)
        self.auto_save_interval_spinbox.setValue(self.settings.get("auto_save_interval", 1))
        autosave_layout.addRow("Auto Save Interval (minutes):", self.auto_save_interval_spinbox)

        autosave_group.setLayout(autosave_layout)

        # Editor Appearance Settings Group
        appearance_group = QGroupBox("Editor Appearance")
        appearance_layout = QFormLayout()
        appearance_layout.setSpacing(10)

        # Text Editor Background Color
        self.background_color_button = QPushButton(qta.icon('fa.paint-brush'), "Choose Color")
        self.background_color_button.clicked.connect(self.choose_background_color)
        self.background_color_label = QLabel()
        self.update_background_color_label(self.settings.get("background_color", "#1e1e1e"))
        color_layout = QHBoxLayout()
        color_layout.addWidget(self.background_color_label)
        color_layout.addWidget(self.background_color_button)
        appearance_layout.addRow("Editor Background Color:", color_layout)

        # Text Editor Foreground (Text) Color
        self.text_color_button = QPushButton(qta.icon('fa.font', color='#ffffff'), "Choose Color")
        self.text_color_button.clicked.connect(self.choose_text_color)
        self.text_color_label = QLabel()
        self.update_text_color_label(self.settings.get("text_color", "#f8f8f2"))
        text_color_layout = QHBoxLayout()
        text_color_layout.addWidget(self.text_color_label)
        text_color_layout.addWidget(self.text_color_button)
        appearance_layout.addRow("Editor Text Color:", text_color_layout)

        # Editor Margin Settings
        margin_group = QGroupBox("Editor Margins")
        margin_layout = QFormLayout()
        self.left_margin_spinbox = QSpinBox(self)
        self.left_margin_spinbox.setRange(0, 100)
        self.left_margin_spinbox.setValue(self.settings.get("left_margin", 5))
        margin_layout.addRow("Left Margin (px):", self.left_margin_spinbox)

        self.right_margin_spinbox = QSpinBox(self)
        self.right_margin_spinbox.setRange(0, 100)
        self.right_margin_spinbox.setValue(self.settings.get("right_margin", 5))
        margin_layout.addRow("Right Margin (px):", self.right_margin_spinbox)

        self.top_margin_spinbox = QSpinBox(self)
        self.top_margin_spinbox.setRange(0, 100)
        self.top_margin_spinbox.setValue(self.settings.get("top_margin", 5))
        margin_layout.addRow("Top Margin (px):", self.top_margin_spinbox)

        self.bottom_margin_spinbox = QSpinBox(self)
        self.bottom_margin_spinbox.setRange(0, 100)
        self.bottom_margin_spinbox.setValue(self.settings.get("bottom_margin", 5))
        margin_layout.addRow("Bottom Margin (px):", self.bottom_margin_spinbox)

        margin_group.setLayout(margin_layout)
        appearance_layout.addRow(margin_group)

        appearance_group.setLayout(appearance_layout)

        # Editor Behavior Settings Group
        behavior_group = QGroupBox("Editor Behavior")
        behavior_layout = QFormLayout()
        behavior_layout.setSpacing(10)

        # Line Numbers Toggle
        self.line_numbers_toggle = Toggle(self)
        self.line_numbers_toggle.setChecked(self.settings.get("show_line_numbers", True))
        behavior_layout.addRow("Show Line Numbers:", self.line_numbers_toggle)

        # Spell Check Toggle
        self.spell_check_toggle = Toggle(self)
        self.spell_check_toggle.setChecked(self.settings.get("enable_spell_check", True))
        behavior_layout.addRow("Enable Spell Check:", self.spell_check_toggle)

        # Word Wrap Toggle
        self.word_wrap_toggle = Toggle(self)
        self.word_wrap_toggle.setChecked(self.settings.get("word_wrap", True))
        behavior_layout.addRow("Enable Word Wrap:", self.word_wrap_toggle)

        # Tab Settings
        tab_group = QGroupBox("Tab Settings")
        tab_layout = QFormLayout()
        self.tab_spaces_spinbox = QSpinBox(self)
        self.tab_spaces_spinbox.setRange(2, 8)
        self.tab_spaces_spinbox.setValue(self.settings.get("tab_spaces", 4))
        tab_layout.addRow("Spaces Per Tab:", self.tab_spaces_spinbox)

        self.use_tabs_toggle = Toggle(self)
        self.use_tabs_toggle.setChecked(self.settings.get("use_tabs", False))
        tab_layout.addRow("Use Tabs Instead of Spaces:", self.use_tabs_toggle)

        tab_group.setLayout(tab_layout)
        behavior_layout.addRow(tab_group)

        behavior_group.setLayout(behavior_layout)

        # Theme Settings Group
        theme_group = QGroupBox("Theme Settings")
        theme_layout = QFormLayout()
        self.theme_combo = QComboBox(self)
        self.theme_combo.addItems(["Dark", "Light", "Solarized"])
        self.theme_combo.setCurrentText(self.settings.get("theme", "Dark"))
        theme_layout.addRow("Editor Theme:", self.theme_combo)
        theme_group.setLayout(theme_layout)

        layout.addWidget(font_group)
        layout.addWidget(project_group)
        layout.addWidget(autosave_group)
        layout.addWidget(appearance_group)
        layout.addWidget(behavior_group)
        layout.addWidget(theme_group)

        # OK and Cancel buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.save_settings)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def load_settings(self):
        if os.path.exists(self.settings_file):
            with open(self.settings_file, 'r') as f:
                return json.load(f)
        return {}

    def save_settings(self):
        self.settings["font_size"] = self.font_size_spinbox.value()
        self.settings["font_family"] = self.font_family_combo.currentText()
        self.settings["dark_mode"] = self.dark_mode_toggle.isChecked()
        self.settings["default_project_folder"] = self.project_folder_line_edit.text()
        self.settings["default_open_file"] = self.open_file_line_edit.text()
        self.settings["auto_save_interval"] = self.auto_save_interval_spinbox.value()
        self.settings["background_color"] = self.background_color_label.text()
        self.settings["text_color"] = self.text_color_label.text()
        self.settings["show_line_numbers"] = self.line_numbers_toggle.isChecked()
        self.settings["enable_spell_check"] = self.spell_check_toggle.isChecked()
        self.settings["word_wrap"] = self.word_wrap_toggle.isChecked()
        self.settings["left_margin"] = self.left_margin_spinbox.value()
        self.settings["right_margin"] = self.right_margin_spinbox.value()
        self.settings["top_margin"] = self.top_margin_spinbox.value()
        self.settings["bottom_margin"] = self.bottom_margin_spinbox.value()
        self.settings["tab_spaces"] = self.tab_spaces_spinbox.value()
        self.settings["use_tabs"] = self.use_tabs_toggle.isChecked()
        self.settings["theme"] = self.theme_combo.currentText()

        with open(self.settings_file, 'w') as f:
            json.dump(self.settings, f)

        self.accept()

    def choose_project_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Default Project Folder")
        if folder:
            self.project_folder_line_edit.setText(folder)

    def choose_default_open_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Select Default Open File", "", "Markdown Files (*.md);;All Files (*)")
        if file_name:
            self.open_file_line_edit.setText(file_name)

    def choose_background_color(self):
        color = QColorDialog.getColor(QColor(self.background_color_label.text()), self, "Choose Background Color")
        if color.isValid():
            self.update_background_color_label(color.name())

    def update_background_color_label(self, color_name):
        self.background_color_label.setText(color_name)
        self.background_color_label.setStyleSheet(f"background-color: {color_name}; border: 1px solid #000;")

    def choose_text_color(self):
        color = QColorDialog.getColor(QColor(self.text_color_label.text()), self, "Choose Text Color")
        if color.isValid():
            self.update_text_color_label(color.name())

    def update_text_color_label(self, color_name):
        self.text_color_label.setText(color_name)
        self.text_color_label.setStyleSheet(f"background-color: {color_name}; border: 1px solid #000;")

if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    settings_file = "settings.json"
    window = SettingsWindow(settings_file)
    window.show()
    sys.exit(app.exec_())

