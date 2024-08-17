import qtawesome as qta
from PyQt5.QtWidgets import (
    QMainWindow, QVBoxLayout, QLabel, QListWidget, QWidget, QStackedWidget, QHBoxLayout, QFrame, QListWidgetItem, QScrollArea, QPushButton
)
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon
from PyQt5.QtCore import Qt, QSize

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
        self.add_menu_item("Overview", qta.icon('fa.home', color='white'))
        self.add_menu_item("Markdown Syntax", qta.icon('fa.file-text-o', color='white'))
        self.add_menu_item("Keyboard Shortcuts", qta.icon('fa.keyboard-o', color='white'))
        self.add_menu_item("Customization", qta.icon('fa.cogs', color='white'))
        self.add_menu_item("Troubleshooting", qta.icon('fa.wrench', color='white'))
        self.add_menu_item("Advanced Features", qta.icon('fa.star', color='white'))
        self.add_menu_item("FAQ", qta.icon('fa.question-circle', color='white'))
        self.add_menu_item("About", qta.icon('fa.info-circle', color='white'))

        self.menu_list.currentRowChanged.connect(self.display_content)

        # Content area using QStackedWidget
        self.content_area = QStackedWidget()

        # Adding different sections to the stacked widget
        self.create_overview_section()
        self.create_markdown_syntax_section()
        self.create_shortcuts_section()
        self.create_customization_section()
        self.create_troubleshooting_section()
        self.create_advanced_features_section()
        self.create_faq_section()
        self.create_about_section()

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

    def create_section_content(self, title, content):
        section = QFrame()
        layout = QVBoxLayout(section)
        title_label = QLabel(f"<h2>{title}</h2>")
        title_label.setFont(QFont("Arial", 18, QFont.Bold))
        content_label = QLabel(content)
        content_label.setWordWrap(True)
        content_label.setFont(QFont("Arial", 12))

        # Add a "Back to Top" button
        back_to_top_button = QPushButton("Back to Top")
        back_to_top_button.setMaximumWidth(150)
        back_to_top_button.clicked.connect(lambda: self.scroll_to_top(layout.parentWidget()))

        layout.addWidget(title_label)
        layout.addWidget(content_label)
        layout.addWidget(back_to_top_button, alignment=Qt.AlignRight)
        layout.addStretch(1)

        return section

    def scroll_to_top(self, content_widget):
        scroll_area = content_widget.parentWidget().parentWidget()
        if isinstance(scroll_area, QScrollArea):
            scroll_area.verticalScrollBar().setValue(0)

    def create_overview_section(self):
        content = (
            "<p>Markiva is a powerful and intuitive Markdown editor designed for developers, "
            "writers, and content creators. It offers a seamless experience for creating and "
            "managing Markdown files with features such as syntax highlighting, customizable themes, "
            "integrated file explorer, and much more.</p>"
            "<h3>Key Features:</h3>"
            "<ul>"
            "<li><b>Markdown Syntax Highlighting:</b> Enjoy a clear and readable Markdown editing experience.</li>"
            "<li><b>Customizable Interface:</b> Toggle between light and dark themes, adjust fonts, and more.</li>"
            "<li><b>Live Preview:</b> See your formatted document in real-time as you write.</li>"
            "<li><b>Integrated File Explorer:</b> Easily manage your Markdown files and folders.</li>"
            "<li><b>Advanced Tools:</b> Use the built-in terminal, version control, and more.</li>"
            "</ul>"
        )
        section = self.create_section_content("Welcome to Markiva!", content)
        scrollable_section = self.create_scrollable_section(section)
        self.content_area.addWidget(scrollable_section)

    def create_markdown_syntax_section(self):
        content = (
            "<p>Markdown is a lightweight markup language for creating formatted text using a plain-text editor. "
            "Here are some of the most commonly used Markdown syntax elements:</p>"
            "<h3>1. Headings</h3>"
            "<p>Use <code>#</code> for headings. The number of <code>#</code> symbols determines the level of the heading.</p>"
            "<ul>"
            "<li><code># Heading 1</code></li>"
            "<li><code>## Heading 2</code></li>"
            "<li><code>### Heading 3</code></li>"
            "<li><code>#### Heading 4</code></li>"
            "<li><code>##### Heading 5</code></li>"
            "<li><code>###### Heading 6</code></li>"
            "</ul>"
            "<h3>2. Text Formatting</h3>"
            "<ul>"
            "<li><b>Bold:</b> <code>**bold text**</code></li>"
            "<li><i>Italic:</i> <code>*italicized text*</code></li>"
            "<li><s>Strikethrough:</s> <code>~~strikethrough~~</code></li>"
            "</ul>"
            "<h3>3. Lists</h3>"
            "<p>Create unordered and ordered lists:</p>"
            "<ul>"
            "<li>Unordered list: <code>- Item 1</code></li>"
            "<li>Ordered list: <code>1. Item 1</code></li>"
            "</ul>"
            "<h3>4. Links and Images</h3>"
            "<ul>"
            "<li>Link: <code>[title](https://www.example.com)</code></li>"
            "<li>Image: <code>![alt text](image.jpg)</code></li>"
            "</ul>"
            "<h3>5. Code</h3>"
            "<ul>"
            "<li>Inline code: <code>`code`</code></li>"
            "<li>Code block:</li>"
            "<pre><code>```<br>def hello_world():<br>&nbsp;&nbsp;&nbsp;print('Hello, World!')<br>```</code></pre>"
            "</ul>"
            "<h3>6. Tables</h3>"
            "<p>Use pipes and dashes to create tables:</p>"
            "<pre><code>| Syntax | Description |<br>| --- | ----------- |<br>| Header | Title |<br>| Paragraph | Text |</code></pre>"
            "<h3>7. Blockquotes</h3>"
            "<p>Use the greater than symbol for blockquotes:</p>"
            "<pre><code>> This is a blockquote</code></pre>"
        )
        section = self.create_section_content("Markdown Syntax Reference", content)
        scrollable_section = self.create_scrollable_section(section)
        self.content_area.addWidget(scrollable_section)

    def create_shortcuts_section(self):
        content = (
            "<h3>Keyboard Shortcuts</h3>"
            "<ul>"
            "<li><b>Bold:</b> Ctrl+B</li>"
            "<li><b>Italic:</b> Ctrl+I</li>"
            "<li><b>Underline:</b> Ctrl+U</li>"
            "<li><b>Strikethrough:</b> Alt+Shift+S</li>"
            "<li><b>Heading 1:</li>"
            "<li>Ctrl+1</li>"
            "<li><b>Heading 2:</b> Ctrl+2</li>"
            "<li><b>Heading 3:</b> Ctrl+3</li>"
            "<li><b>Insert Link:</b> Ctrl+K</li>"
            "<li><b>Insert Image:</b> Ctrl+Shift+I</li>"
            "<li><b>Save:</b> Ctrl+S</li>"
            "<li><b>Open:</b> Ctrl+O</li>"
            "<li><b>Undo:</b> Ctrl+Z</li>"
            "<li><b>Redo:</b> Ctrl+Y</li>"
            "<li><b>Find and Replace:</b> Ctrl+F</li>"
            "<li><b>Insert Code Block:</b> Ctrl+Alt+C</li>"
            "<li><b>Toggle Terminal:</b> Ctrl+T</li>"
            "<li><b>Toggle Dark/Light Mode:</b> Ctrl+D</li>"
            "<li><b>Export as PDF:</b> Ctrl+P</li>"
            "<li><b>Export as HTML:</b> Ctrl+Shift+H</li>"
            "</ul>"
        )
        section = self.create_section_content("Keyboard Shortcuts", content)
        scrollable_section = self.create_scrollable_section(section)
        self.content_area.addWidget(scrollable_section)

    def create_customization_section(self):
        content = (
            "<p>Markiva provides several customization options to suit your workflow:</p>"
            "<h3>1. Themes</h3>"
            "<p>Switch between dark and light modes using the <i>View</i> menu or the toolbar button. "
            "Your preference will be saved for future sessions.</p>"
            "<h3>2. Fonts</h3>"
            "<p>Customize the font family and size from the editor settings toolbar. "
            "Choose from a variety of fonts to make your editing experience comfortable.</p>"
            "<h3>3. Background and Text Colors</h3>"
            "<p>Personalize the background and text colors using the color pickers in the settings toolbar.</p>"
            "<h3>4. Editor Preferences</h3>"
            "<ul>"
            "<li>Toggle line numbers for better navigation through your document.</li>"
            "<li>Enable or disable spell check to catch typos as you type.</li>"
            "<li>Toggle word wrap to fit long lines within the editor window.</li>"
            "</ul>"
            "<h3>5. File Management</h3>"
            "<p>Set a default project folder for easy access to your Markdown files. "
            "Use the integrated file explorer to manage your files efficiently.</p>"
        )
        section = self.create_section_content("Customization Options", content)
        scrollable_section = self.create_scrollable_section(section)
        self.content_area.addWidget(scrollable_section)

    def create_troubleshooting_section(self):
        content = (
            "<h3>1. Markdown Rendering Issues</h3>"
            "<ul>"
            "<li>Ensure that your Markdown syntax is correct.</li>"
            "<li>Use the live preview to spot errors in real-time.</li>"
            "<li>If issues persist, restart the application to refresh the environment.</li>"
            "</ul>"
            "<h3>2. File Saving/Opening Issues</h3>"
            "<ul>"
            "<li>Check that you have the necessary permissions to access the file.</li>"
            "<li>Ensure the file isn't open in another application, which might lock it.</li>"
            "</ul>"
            "<h3>3. Performance Issues</h3>"
            "<ul>"
            "<li>Close unused applications to free up system resources.</li>"
            "<li>Consider using Markiva on a system with sufficient hardware specifications.</li>"
            "</ul>"
            "<h3>4. Auto-Save Issues</h3>"
            "<ul>"
            "<li>If auto-save isn't working, ensure the directory has write permissions.</li>"
            "<li>Check and adjust the auto-save interval in the settings.</li>"
            "</ul>"
            "<h3>5. Application Crashes</h3>"
            "<ul>"
            "<li>Try restarting the application.</li>"
            "<li>If crashes persist, reinstall the application or contact support.</li>"
            "</ul>"
        )
        section = self.create_section_content("Troubleshooting", content)
        scrollable_section = self.create_scrollable_section(section)
        self.content_area.addWidget(scrollable_section)

    def create_advanced_features_section(self):
        content = (
            "<p>Markiva is equipped with advanced features to enhance your productivity:</p>"
            "<h3>1. Integrated Terminal</h3>"
            "<p>Use the built-in terminal to execute commands without leaving the editor. "
            "This is particularly useful for developers working in a Markdown-based environment.</p>"
            "<h3>2. Version Control</h3>"
            "<p>Track changes in your documents with the version control feature. "
            "Automatically save snapshots of your work and compare different versions to see what has changed.</p>"
            "<h3>3. Template Management</h></p>"
            "<p>Save frequently used document structures as templates. Load templates with a single click to quickly start new documents.</p>"
            "<h3>4. Customizable Toolbar</h3>"
            "<p>Customize the toolbar to include the tools you use most frequently. "
            "You can add, remove, or rearrange icons to create a workspace that fits your needs.</p>"
            "<h3>5. Table Editor</h3>"
            "<p>Create and edit tables easily with the built-in table editor. "
            "No need to remember complex Markdown syntax for tables—let the editor do the work for you.</p>"
        )
        section = self.create_section_content("Advanced Features", content)
        scrollable_section = self.create_scrollable_section(section)
        self.content_area.addWidget(scrollable_section)

    def create_faq_section(self):
        content = (
            "<h3>1. How do I toggle between dark and light mode?</h3>"
            "<p>You can switch between dark and light modes using the View menu or the toolbar button. "
            "Your preference will be saved for future sessions.</p>"
            "<h3>2. Can I customize the keyboard shortcuts?</h3>"
            "<p>Currently, Markiva supports a predefined set of keyboard shortcuts. "
            "Future versions may include customizable shortcuts based on user feedback.</p>"
            "<h3>3. How do I export my document as a PDF?</h3>"
            "<p>You can export your document as a PDF by selecting 'Export as PDF' from the File menu or using the shortcut Ctrl+P.</p>"
            "<h3>4. Where are my files saved?</h3>"
            "<p>By default, your files are saved in the selected project folder. "
            "You can set a default project folder in the settings for easier access.</p>"
            "<h3>5. How can I contact support?</h3>"
            "<p>For support, please visit our website at <a href='https://www.example.com'>www.example.com</a> "
            "or send an email to support@example.com.</p>"
        )
        section = self.create_section_content("Frequently Asked Questions (FAQ)", content)
        scrollable_section = self.create_scrollable_section(section)
        self.content_area.addWidget(scrollable_section)

    def create_about_section(self):
        content = (
            "<p><b>Version:</b> 1.0.0</p>"
            "<p><b>Developed by:</b> [Your Name]</p>"
            "<p>Markiva is an advanced Markdown editor designed to provide a seamless experience "
            "for writing and editing Markdown documents. With support for customizable themes, "
            "syntax highlighting, and integrated tools, Markiva is the perfect tool for developers, "
            "writers, and content creators.</p>"
            "<p>For more information and updates, visit <a href='https://www.example.com'>our website</a>.</p>"
            "<h3>License</h3>"
            "<p>Markiva is released under the MIT License. You are free to use, modify, and distribute this software "
            "as long as you include the original license and copyright notice.</p>"
            "<h3>Credits</h3>"
            "<p>This project was developed using the following technologies:</p>"
            "<ul>"
            "<li><b>PyQt5:</b> For the GUI framework.</li>"
            "<li><b>QtAwesome:</b> For toolbar and menu icons.</li>"
            "<li><b>Markdown2:</b> For converting Markdown to HTML.</li>"
            "<li><b>Python:</b> The core programming language used in development.</li>"
            "</ul>"
            "<p>We would like to thank the open-source community for their contributions and support.</p>"
        )
        section = self.create_section_content("About Markiva", content)
        scrollable_section = self.create_scrollable_section(section)
        self.content_area.addWidget(scrollable_section)

    def display_content(self, index):
        self.content_area.setCurrentIndex(index)


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    help_window = HelpWindow()
    help_window.show()
    sys.exit(app.exec_())
