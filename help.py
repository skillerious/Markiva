import qtawesome as qta
import markdown2
from PyQt5.QtWidgets import (
    QMainWindow, QVBoxLayout, QLabel, QListWidget, QWidget, QStackedWidget, QHBoxLayout, QFrame, QListWidgetItem, QScrollArea, QTextEdit, QPushButton
)
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon
from PyQt5.QtCore import Qt, QSize
import os

class HelpWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Markiva Help")
        self.setMinimumSize(1000, 800)

        # Apply dark theme with blue accent to the help window
        self.set_dark_theme()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)

        # Sidebar menu
        self.menu_list = QListWidget()
        self.menu_list.setFixedWidth(250)
        self.menu_list.setStyleSheet("""
            QListWidget {
                background-color: #2c2c2c;
                color: #ffffff;
                border-right: 1px solid #444444;
                padding: 5px;
            }
            QListWidget::item {
                padding: 10px;
                margin: 5px;
            }
            QListWidget::item:selected {
                background-color: #1E90FF;
                border-radius: 10px;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #63B8FF;
                border-radius: 10px;
            }
            QListWidget::item:focus {
                outline: none;
            }
            QListWidget::item:!selected:focus {
                background-color: transparent;
            }
        """)

        # Adding icons and items to the sidebar using QtAwesome icons
        self.add_menu_item("Getting Started", qta.icon('fa.play', color='white'))
        self.add_menu_item("Overview", qta.icon('fa.home', color='white'))
        self.add_menu_item("Markdown Syntax", qta.icon('fa.file-text-o', color='white'))
        self.add_menu_item("Keyboard Shortcuts", qta.icon('fa.keyboard-o', color='white'))
        self.add_menu_item("Customization", qta.icon('fa.cogs', color='white'))
        self.add_menu_item("Troubleshooting", qta.icon('fa.wrench', color='white'))
        self.add_menu_item("Advanced Features", qta.icon('fa.star', color='white'))
        self.add_menu_item("FAQ", qta.icon('fa.question-circle', color='white'))
        self.add_menu_item("About", qta.icon('fa.info-circle', color='white'))
        self.add_menu_item("Installation", qta.icon('fa.download', color='white'))

        self.menu_list.currentRowChanged.connect(self.display_content)

        # Content area using QStackedWidget
        self.content_area = QStackedWidget()

        # Load content from Markdown files
        self.content_sections = [
            "getting_started.md",
            "overview.md",
            "markdown_syntax.md",
            "shortcuts.md",
            "customization.md",
            "troubleshooting.md",
            "advanced_features.md",
            "faq.md",
            "about.md",
            "installation.md"
        ]

        # Ensure all content sections are loaded
        for section in self.content_sections:
            self.load_markdown_section(section)

        # Initial display
        self.menu_list.setCurrentRow(0)

        # Adding sidebar and content area to the layout
        main_layout.addWidget(self.menu_list)
        main_layout.addWidget(self.content_area)

    def set_dark_theme(self):
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
        dark_palette.setColor(QPalette.Link, QColor(30, 144, 255))  # Dodger Blue
        dark_palette.setColor(QPalette.Highlight, QColor(30, 144, 255))  # Dodger Blue
        dark_palette.setColor(QPalette.HighlightedText, Qt.white)
        self.setPalette(dark_palette)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #353535;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
                font-family: Arial;
                font-size: 14px;
            }
            QPushButton {
                background-color: #1E90FF;
                color: white;
                border-radius: 5px;
                padding: 8px 16px;
                font-family: Arial;
                font-size: 14px;
                border: 2px solid #1E90FF;
            }
            QPushButton:focus {
                outline: none;
            }
            QPushButton:hover {
                background-color: #63B8FF;
                border-color: #63B8FF;
            }
            QVBoxLayout, QHBoxLayout {
                background-color: #353535;
            }
            QFrame {
                background-color: #353535;
                color: #ffffff;
            }
            QScrollArea {
                background-color: #353535;
            }
            QScrollBar:vertical {
                background-color: #2c2c2c;
                width: 14px;
                margin: 15px 3px 15px 3px;
                border: 1px solid #444;
                border-radius: 7px;
            }
            QScrollBar::handle:vertical {
                background-color: #1E90FF;
                min-height: 20px;
                border-radius: 7px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background-color: #1E90FF;
                height: 14px;
                subcontrol-origin: margin;
                subcontrol-position: top;
                border-radius: 7px;
            }
            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
                border: none;
                background: none;
            }
        """)

    def add_menu_item(self, name, icon):
        item = QListWidgetItem(icon, name)
        item.setFont(QFont("Arial", 14))
        self.menu_list.addItem(item)

    def create_scrollable_section(self, content_widget):
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(content_widget)
        return scroll_area

    def load_markdown_section(self, filename):
        # Get the directory of the current script file
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # Construct the full path to the markdown file
        file_path = os.path.join(base_dir, "help_files", filename)
        
        try:
            with open(file_path, "r", encoding="utf-8") as file:  # Use utf-8 encoding
                content = file.read()
                html_content = markdown2.markdown(content)
                section = self.create_section_content(html_content)
                scrollable_section = self.create_scrollable_section(section)
                self.content_area.addWidget(scrollable_section)
        except FileNotFoundError:
            print(f"File not found: {file_path}")
        except UnicodeDecodeError as e:
            print(f"Error reading {file_path}: {e}")


    def create_section_content(self, html_content):
        section = QFrame()
        layout = QVBoxLayout(section)
        content_label = QLabel()
        content_label.setText(html_content)
        content_label.setWordWrap(True)
        content_label.setFont(QFont("Arial", 12))
        content_label.setTextFormat(Qt.RichText)
        content_label.setAlignment(Qt.AlignTop)

        # Add a "Back to Top" button
        back_to_top_button = QPushButton("Back to Top")
        back_to_top_button.setMaximumWidth(150)
        back_to_top_button.clicked.connect(lambda: self.scroll_to_top(layout.parentWidget()))

        layout.addWidget(content_label)
        layout.addWidget(back_to_top_button, alignment=Qt.AlignRight)
        layout.addStretch(1)

        return section

    def scroll_to_top(self, content_widget):
        scroll_area = content_widget.parentWidget().parentWidget()
        if isinstance(scroll_area, QScrollArea):
            scroll_area.verticalScrollBar().setValue(0)

    def display_content(self, index):
        self.content_area.setCurrentIndex(index)


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    help_window = HelpWindow()
    help_window.show()
    sys.exit(app.exec_())
