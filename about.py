from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QFrame, QSpacerItem, QSizePolicy
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor, QPalette, QPixmap, QIcon

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About")
        self.setFixedSize(500, 450)

        # Set the dark theme palette
        self.set_dark_theme()

        # Set the main layout with custom margins and spacing
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Logo at the top
        logo_label = QLabel(self)
        pixmap = QPixmap("images/logo.png")
        pixmap = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        logo_label.setPixmap(pixmap)
        logo_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo_label)

        # App title
        title_label = QLabel("Markdown Editor")
        title_label.setFont(QFont("Arial", 24, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #FFD700;")
        layout.addWidget(title_label)

        # Version and author information
        version_label = QLabel("Version 1.0.0")
        version_label.setFont(QFont("Arial", 14))
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet("color: #FFD700;")
        layout.addWidget(version_label)

        author_label = QLabel("Developed by Robin Doak")
        author_label.setFont(QFont("Arial", 14))
        author_label.setAlignment(Qt.AlignCenter)
        author_label.setStyleSheet("color: #FFD700;")
        layout.addWidget(author_label)

        # Separator line with custom styling
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #FFD700; height: 2px;")
        layout.addWidget(line)

        # Additional information with improved formatting
        info_label = QLabel(
            "This Markdown Editor offers a modern, user-friendly interface for creating and editing Markdown files. "
            "It includes features such as live preview, syntax highlighting, and customizable settings to suit your needs."
        )
        info_label.setFont(QFont("Arial", 12))
        info_label.setWordWrap(True)
        info_label.setAlignment(Qt.AlignJustify)
        info_label.setStyleSheet("color: #EDEDED; padding: 10px;")
        layout.addWidget(info_label)

        # Add spacing before the button
        layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Add OK button to close the dialog with rounded corners and hover effect
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.setFont(QFont("Arial", 12, QFont.Bold))
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #FFD700;
                color: #333;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #E5C100;
            }
        """)
        ok_button.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addStretch()

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def set_dark_theme(self):
        """Set a dark theme for the dialog."""
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(40, 40, 40))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        self.setPalette(palette)
