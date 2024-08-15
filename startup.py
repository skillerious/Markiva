import sys
import os
import json
from PyQt5.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QLabel, QCheckBox, QPushButton,
    QHBoxLayout, QLineEdit, QFileDialog, QGridLayout, QSpacerItem, QSizePolicy
)
from PyQt5.QtCore import Qt, QDir
from PyQt5.QtGui import QIcon, QPalette, QColor, QFont

class StartupDialog(QDialog):
    def __init__(self, settings_file):
        super().__init__()
        self.settings_file = settings_file
        self.settings = self.load_settings()
        self.initUI()

    def load_settings(self):
        if os.path.exists(self.settings_file):
            with open(self.settings_file, 'r') as f:
                return json.load(f)
        return {}

    def save_settings(self):
        with open(self.settings_file, 'w') as f:
            json.dump(self.settings, f)

    def initUI(self):
        self.setWindowTitle("Welcome to My Markdown")
        self.setFixedSize(500, 370)  # Adjusted height to accommodate the new grid
        self.setWindowIcon(QIcon("images/logo.png"))

        layout = QVBoxLayout()

        # Welcome message
        welcome_label = QLabel("Welcome to My Markdown!")
        welcome_label.setFont(QFont("Arial", 16, QFont.Bold))
        welcome_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(welcome_label)

        # Application logo
        logo_label = QLabel()
        logo_label.setPixmap(QIcon("images/logo.png").pixmap(100, 100))
        logo_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo_label)

        # Instructions
        instruction_label = QLabel("Please select the default project folder:")
        instruction_label.setFont(QFont("Arial", 12))
        instruction_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(instruction_label)

        # Folder selection layout
        folder_layout = QHBoxLayout()

        self.folder_edit = QLineEdit()
        self.folder_edit.setReadOnly(True)
        self.folder_edit.setText(self.settings.get("default_project_folder", ""))
        self.folder_edit.setStyleSheet("""
            QLineEdit {
                border: 1px solid #666;
                border-radius: 10px;
                padding: 8px;
                background-color: #292929;
                color: #d3d3d3;
            }
        """)
        folder_layout.addWidget(self.folder_edit)

        folder_button = QPushButton()
        folder_button.setIcon(QIcon("images/folder.png"))
        folder_button.setStyleSheet("""
            QPushButton {
                background-color: #0078d7;
                border: none;
                border-radius: 10px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
        """)
        folder_button.clicked.connect(self.select_folder)
        folder_layout.addWidget(folder_button)

        layout.addLayout(folder_layout)

        # OK Button
        self.ok_button = QPushButton("OK")
        self.ok_button.setStyleSheet("""
            QPushButton {
                background-color: #0078d7;
                color: white;
                font-size: 14px;
                padding: 10px;
                border-radius: 10px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
        """)
        self.ok_button.clicked.connect(self.save_and_close)
        layout.addWidget(self.ok_button, alignment=Qt.AlignCenter)

        # Bottom grid layout for developer text and checkbox
        grid_layout = QGridLayout()

        developer_label = QLabel("Developer: Robin Doak")
        developer_label.setFont(QFont("Arial", 10))
        developer_label.setStyleSheet("color: #d3d3d3;")
        grid_layout.addWidget(developer_label, 0, 0, alignment=Qt.AlignLeft)

        spacer = QSpacerItem(20, 10, QSizePolicy.MinimumExpanding, QSizePolicy.Minimum)
        grid_layout.addItem(spacer, 0, 1)

        self.show_checkbox = QCheckBox("Do not show again")
        self.show_checkbox.setChecked(self.settings.get("show_startup", True) is False)
        grid_layout.addWidget(self.show_checkbox, 0, 2, alignment=Qt.AlignRight)

        layout.addLayout(grid_layout)
        layout.setContentsMargins(10, 10, 10, 10)

        self.setLayout(layout)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Default Project Folder", QDir.homePath())
        if folder:
            self.folder_edit.setText(folder)

    def save_and_close(self):
        self.settings["default_project_folder"] = self.folder_edit.text()
        self.settings["show_startup"] = not self.show_checkbox.isChecked()
        self.save_settings()
        self.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Apply dark theme
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.WindowText, Qt.white)
    dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
    dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
    dark_palette.setColor(QPalette.ToolTipText, Qt.white)
    dark_palette.setColor(QPalette.Text, Qt.white)
    dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ButtonText, Qt.white)
    dark_palette.setColor(QPalette.BrightText, Qt.red)
    dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(dark_palette)

    settings_file = "user_settings.json"
    window = StartupDialog(settings_file)
    if window.exec_() == QDialog.Accepted:
        # After the startup dialog, launch the markdown editor
        os.system('py markdown_editor.py')
