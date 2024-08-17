import sys
import qtawesome as qta
import os
import time
import json  # For saving and loading settings
import mimetypes  # For identifying file types
import shutil  # For file operations during drag-and-drop
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QPlainTextEdit, QSplitter, QAction,
    QToolBar, QFileDialog, QMessageBox, QStatusBar, QTextEdit, QStyleFactory, QDialog,
    QGridLayout, QPushButton, QMenuBar, QMenu, QInputDialog, QLineEdit, QLabel, QPlainTextDocumentLayout,
    QTreeView, QFileSystemModel, QHBoxLayout, QDesktopWidget, QDialogButtonBox, QListWidget, QSizePolicy, QAbstractItemView, QComboBox, QSpinBox, QColorDialog, QCheckBox, QToolButton, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar, QSpinBox
)
from PyQt5.QtCore import Qt, QRect, QSize, QTimer, QRegularExpression, QModelIndex, QDir, QFileInfo, QUrl, QItemSelectionModel, pyqtSlot
from PyQt5.QtGui import QFont, QColor, QPainter, QTextFormat, QPalette, QTextCursor, QTextCharFormat, QSyntaxHighlighter, QIcon, QDesktopServices, QStandardItemModel, QStandardItem, QStandardItemModel
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtPrintSupport import QPrinter
import subprocess  # For integrated terminal
from spellchecker import SpellChecker
import markdown2
import difflib
from startup import StartupDialog  # Import the new startup dialog
from Settings import SettingsWindow  # Import SettingsWindow
from about import AboutDialog


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


class MarkdownHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self._highlighting_rules = []

        # Define formats for different parts of Markdown syntax
        header_format = QTextCharFormat()
        header_format.setForeground(Qt.blue)
        self._highlighting_rules.append((r'(^|\s)#{1,6}(?=\s)', header_format))  # Headers

        bold_format = QTextCharFormat()
        bold_format.setFontWeight(QFont.Bold)
        self._highlighting_rules.append((r'\*\*.*?\*\*', bold_format))  # Bold

        italic_format = QTextCharFormat()
        italic_format.setFontItalic(True)
        self._highlighting_rules.append((r'\*.*?\*', italic_format))  # Italic

        code_format = QTextCharFormat()
        code_format.setFontFamily('Courier')
        code_format.setForeground(Qt.darkCyan)
        self._highlighting_rules.append((r'[^]+', code_format))  # Inline code

        blockquote_format = QTextCharFormat()
        blockquote_format.setForeground(Qt.darkGray)
        self._highlighting_rules.append((r'^>\s.*', blockquote_format))  # Blockquotes

        # Add more formats here for different Markdown syntax

    def highlightBlock(self, text):
        for pattern, fmt in self._highlighting_rules:
            expression = QRegularExpression(pattern)
            iterator = expression.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)


class CodeEditor(QPlainTextEdit):
    def __init__(self, font_size=14):
        super().__init__()
        self.lineNumberArea = LineNumberArea(self)
        self.spellchecker = SpellChecker()

        self.setFont(QFont("Fira Code", font_size))
        self.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: #1e1e1e;
                color: #ffffff;
                padding: 10px;
                border: 1px solid #3e3e3e;
            }}
        """)

        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.textChanged.connect(self.check_spelling)

        self.update_line_number_area_width(0)

        self.highlighter = MarkdownHighlighter(self.document())
        self.setAcceptDrops(True)
        self.document().modificationChanged.connect(self.on_modification_changed)

    def set_font_size(self, font_size):
        self.setFont(QFont(self.font().family(), font_size))

    def set_font_family(self, font_family):
        self.setFont(QFont(font_family, self.font().pointSize()))

    def set_background_color(self, color):
        self.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {color};
                color: #ffffff;
                padding: 10px;
                border: 1px solid #3e3e3e;
            }}
        """)

    def set_text_color(self, color):
        self.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {self.styleSheet().split('background-color: ')[1].split(';')[0]};
                color: {color};
                padding: 10px;
                border: 1px solid #3e3e3e;
            }}
        """)

    def line_number_area_width(self):
        digits = 1
        max_block = max(1, self.blockCount())
        while max_block >= 10:
            max_block //= 10
            digits += 1
        space = 4 + self.fontMetrics().width('9') * digits
        return space

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.lineNumberArea)

        # Gutter background
        painter.fillRect(event.rect(), QColor(30, 30, 30))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        # Line number text color and font
        painter.setPen(QColor(180, 180, 180))
        painter.setFont(QFont("Fira Code", 10, QFont.Bold))

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.drawText(0, top, self.lineNumberArea.width() - 5, self.fontMetrics().height(), Qt.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

        # Optional enhancement: Draw a border between the gutter and the editor
        painter.setPen(QColor(60, 60, 60))  # Border color
        painter.drawLine(self.lineNumberArea.width() - 1, event.rect().top(), self.lineNumberArea.width() - 1, event.rect().bottom())

    def highlight_current_line(self):
        extra_selections = []

        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()

            line_color = QColor(50, 50, 50).lighter(130)  # Slightly lighter color for the line highlight
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)

        self.setExtraSelections(extra_selections)

    def check_spelling(self):
        cursor = self.textCursor()
        cursor.select(QTextCursor.WordUnderCursor)
        word = cursor.selectedText().strip()

        # Clear previous highlights
        self.clear_highlight()

        if word and not word.isspace():
            # Check spelling
            if word.lower() not in self.spellchecker:
                self.highlight_word(cursor)

    def highlight_word(self, cursor):
        # Apply red underline to misspelled words
        extra_selections = self.extraSelections()
        selection = QTextEdit.ExtraSelection()
        selection.cursor = cursor
        selection.format.setUnderlineColor(QColor("red"))
        selection.format.setUnderlineStyle(QTextCharFormat.SpellCheckUnderline)
        extra_selections.append(selection)
        self.setExtraSelections(extra_selections)

    def clear_highlight(self):
        # Clear all previous highlights
        self.setExtraSelections([])

    def insert_markdown(self, prefix, suffix, block=False):
        cursor = self.textCursor()
        selected_text = cursor.selectedText()

        if block:  # For block-level elements like code blocks
            if not selected_text.strip():
                formatted_text = f"{prefix}\n{suffix}"
            else:
                lines = selected_text.split('\n')
                formatted_text = f"{prefix}\n{selected_text}\n{suffix}"
        else:
            formatted_text = f"{prefix}{selected_text}{suffix}"

        cursor.insertText(formatted_text)

    def insert_html(self, tag, attributes=""):
        cursor = self.textCursor()
        selected_text = cursor.selectedText()

        if not selected_text.strip():
            formatted_text = f"<{tag} {attributes}></{tag}>"
        else:
            formatted_text = f"<{tag} {attributes}>{selected_text}</{tag}>"

        cursor.insertText(formatted_text)

    def insert_list(self, list_type):
        cursor = self.textCursor()
        cursor.movePosition(cursor.StartOfLine, cursor.KeepAnchor)
        selected_text = cursor.selectedText()

        if list_type == "bullet":
            cursor.insertText(f"- {selected_text}")
        elif list_type == "numbered":
            cursor.insertText(f"1. {selected_text}")
        elif list_type == "checkbox":
            cursor.insertText(f"- [ ] {selected_text}")  # Inserts an unchecked checkbox

    def indent(self):
        cursor = self.textCursor()
        cursor.movePosition(cursor.StartOfLine, cursor.KeepAnchor)
        selected_text = cursor.selectedText()
        cursor.insertText("    " + selected_text)  # Adds four spaces for indentation

    def outdent(self):
        cursor = self.textCursor()
        cursor.movePosition(cursor.StartOfLine, cursor.KeepAnchor)
        selected_text = cursor.selectedText()
        if selected_text.startswith("    "):
            cursor.insertText(selected_text[4:])  # Removes four spaces (one level of indent)

    def dragEnterEvent(self, event):
        if event.mimeData().hasImage():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        image_path = event.mimeData().urls()[0].toLocalFile()
        if image_path:
            self.insertPlainText(f"![Image]({image_path})")

    def keyPressEvent(self, event):
        # Implement bracket matching with improved logic
        opening_brackets = {Qt.Key_ParenLeft: '()', Qt.Key_BraceLeft: '{}', Qt.Key_BracketLeft: '[]', Qt.Key_QuoteDbl: '""', Qt.Key_Apostrophe: "''"}
        if event.key() in opening_brackets:
            pair = opening_brackets[event.key()]
            self.insertPlainText(pair)
            self.moveCursor(QTextCursor.Left)  # Move the cursor between the brackets
        else:
            super().keyPressEvent(event)

    def contextMenuEvent(self, event):
        # Create a context menu for spell-check suggestions
        menu = self.createStandardContextMenu()
        cursor = self.textCursor()
        cursor.select(QTextCursor.WordUnderCursor)
        word = cursor.selectedText().strip()

        if word and word.lower() not in self.spellchecker:
            suggestions = self.spellchecker.candidates(word)
            if suggestions:  # Only proceed if suggestions are not None and not empty
                suggestions = list(suggestions)  # Convert to list for iteration
                menu.addSeparator()
                for suggestion in suggestions:
                    action = menu.addAction(f"Replace with '{suggestion}'")
                    action.triggered.connect(lambda _, s=suggestion: self.replace_word(s))

        menu.exec_(event.globalPos())

    def replace_word(self, replacement):
        cursor = self.textCursor()
        cursor.select(QTextCursor.WordUnderCursor)
        cursor.insertText(replacement)

    def on_modification_changed(self, modified):
        window = self.window()
        if window.current_file and modified:
            window.setWindowTitle(f"{os.path.basename(window.current_file)}* - Markiva")
        elif window.current_file:
            window.setWindowTitle(f"{os.path.basename(window.current_file)} - Markiva")


class LinkDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Insert Link")
        self.setFixedSize(400, 200)

        layout = QVBoxLayout(self)

        self.text_label = QLabel("Text to display:", self)
        self.text_input = QLineEdit(self)
        layout.addWidget(self.text_label)
        layout.addWidget(self.text_input)

        self.url_label = QLabel("URL:", self)
        self.url_input = QLineEdit(self)
        layout.addWidget(self.url_label)
        layout.addWidget(self.url_input)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def get_link_data(self):
        return self.text_input.text(), self.url_input.text()


class EmojiPicker(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Emoji Picker")
        self.setFixedSize(300, 200)

        # Create a grid layout
        layout = QGridLayout()
        self.setLayout(layout)

        # List of sample emojis
        emojis = ["😀", "😁", "😂", "😃", "😄", "😅", "😆", "😉", "😊", "😋"]

        # Add buttons for each emoji
        positions = [(i, j) for i in range(2) for j in range(5)]
        for position, emoji in zip(positions, emojis):
            button = QPushButton(emoji)
            button.clicked.connect(lambda _, e=emoji: self.select_emoji(e))
            layout.addWidget(button, *position)

    def select_emoji(self, emoji):
        # Emit a signal to insert the selected emoji
        self.parent().editor.insertPlainText(emoji)
        self.close()


class CustomFileSystemModel(QFileSystemModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.default_open_file = None

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DecorationRole and index.column() == 0:
            file_path = self.filePath(index)
            if file_path == self.default_open_file:
                return QIcon("images/tick.png")  # Path to the tick icon
        return super().data(index, role)

    def set_default_open_file(self, file_path):
        self.default_open_file = file_path
        self.layoutChanged.emit()  # Refresh the view to reflect the icon change

    def canDropMimeData(self, data, action, row, column, parent):
        # Check if the target is a directory or if dropped in the root (invalid parent)
        if not parent.isValid() or self.isDir(parent):
            if data.hasUrls():
                for url in data.urls():
                    if url.toLocalFile().endswith('.md'):
                        return True
        return False

    def dropMimeData(self, data, action, row, column, parent):
        if not parent.isValid():
            # If the parent is not valid (dropped in the main area), use the root path
            parent_dir = self.rootPath()
        else:
            # Otherwise, get the directory of the parent item (which should be a folder)
            parent_dir = self.filePath(parent)

        if data.hasUrls():
            for url in data.urls():
                file_path = url.toLocalFile()
                if file_path.endswith('.md'):  # Check if the file is a .md file
                    target_path = os.path.join(parent_dir, os.path.basename(file_path))

                    # Skip the move if the file is being moved to the same directory
                    if file_path == target_path:
                        continue

                    if os.path.exists(target_path):
                        QMessageBox.warning(None, "Error", f"File {os.path.basename(file_path)} already exists in the target directory.")
                        return False

                    try:
                        shutil.move(file_path, target_path)
                        print(f"Moved file {file_path} to {target_path}")  # Debugging output
                    except Exception as e:
                        QMessageBox.warning(None, "Error", f"Could not move file: {str(e)}")
                        return False

            # Explicitly reset the model's root path to refresh the view
            self.setRootPath(self.rootPath())
            return True

        return False

    def mimeTypes(self):
        return ['text/uri-list']

    def mimeData(self, indexes):
        mime_data = super().mimeData(indexes)
        urls = []
        for index in indexes:
            if index.isValid():
                urls.append(QUrl.fromLocalFile(self.filePath(index)))
        mime_data.setUrls(urls)
        return mime_data


class CustomTreeView(QTreeView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            # Highlight the item under the cursor
            index = self.indexAt(event.pos())
            if index.isValid():
                self.setCurrentIndex(index)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        model = self.model()
        if isinstance(model, CustomFileSystemModel):
            # Drop the mime data at the specified location
            model.dropMimeData(event.mimeData(), event.dropAction(), -1, -1, self.indexAt(event.pos()))
        else:
            super().dropEvent(event)


class TableEditorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Table Editor")
        self.setMinimumSize(600, 400)

        # Layouts
        self.layout = QVBoxLayout(self)
        
        # Table widget
        self.table_widget = QTableWidget(3, 3, self)  # Default 3x3 table
        self.layout.addWidget(self.table_widget)

        # Check box for headers
        self.header_checkbox = QCheckBox("Include Header Row", self)
        self.header_checkbox.setChecked(True)
        self.layout.addWidget(self.header_checkbox)

        # Buttons for adding/removing rows and columns
        button_layout = QHBoxLayout()
        add_row_btn = QPushButton("Add Row")
        add_col_btn = QPushButton("Add Column")
        remove_row_btn = QPushButton("Remove Row")
        remove_col_btn = QPushButton("Remove Column")

        add_row_btn.clicked.connect(self.add_row)
        add_col_btn.clicked.connect(self.add_column)
        remove_row_btn.clicked.connect(self.remove_row)
        remove_col_btn.clicked.connect(self.remove_column)

        button_layout.addWidget(add_row_btn)
        button_layout.addWidget(add_col_btn)
        button_layout.addWidget(remove_row_btn)
        button_layout.addWidget(remove_col_btn)

        self.layout.addLayout(button_layout)

        # Dialog buttons
        self.dialog_buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.dialog_buttons.accepted.connect(self.accept)
        self.dialog_buttons.rejected.connect(self.reject)

        self.layout.addWidget(self.dialog_buttons)

    def add_row(self):
        row_position = self.table_widget.rowCount()
        self.table_widget.insertRow(row_position)

    def add_column(self):
        col_position = self.table_widget.columnCount()
        self.table_widget.insertColumn(col_position)

    def remove_row(self):
        if self.table_widget.rowCount() > 1:
            self.table_widget.removeRow(self.table_widget.rowCount() - 1)

    def remove_column(self):
        if self.table_widget.columnCount() > 1:
            self.table_widget.removeColumn(self.table_widget.columnCount() - 1)

    def get_table_markdown(self):
        headers = []
        rows = []

        # If header checkbox is checked, include the first row as headers
        if self.header_checkbox.isChecked():
            for col in range(self.table_widget.columnCount()):
                header_item = self.table_widget.item(0, col)
                headers.append(header_item.text() if header_item else "Header")
            data_start_row = 1  # Data starts from the second row
        else:
            headers = ["Header"] * self.table_widget.columnCount()
            data_start_row = 0  # Data starts from the first row

        for row in range(data_start_row, self.table_widget.rowCount()):
            row_data = []
            for col in range(self.table_widget.columnCount()):
                item = self.table_widget.item(row, col)
                row_data.append(item.text() if item else "")
            rows.append(row_data)

        # Convert to Markdown table
        markdown_table = "| " + " | ".join(headers) + " |\n"
        markdown_table += "| " + " | ".join(["---"] * len(headers)) + " |\n"

        for row in rows:
            markdown_table += "| " + " | ".join(row) + " |\n"

        return markdown_table

    def accept(self):
        # Insert the table markdown into the editor
        table_markdown = self.get_table_markdown()
        self.parent().editor.insertPlainText(table_markdown)
        super().accept()


class TemplateDialog(QDialog):
    def __init__(self, templates_dir, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Templates")
        self.setFixedSize(800, 600)  # Adjust size to accommodate both the list and preview

        self.templates_dir = templates_dir

        # Main layout (horizontal to place list and preview side by side)
        main_layout = QHBoxLayout(self)

        # List layout (vertical to hold the search bar and template list)
        list_layout = QVBoxLayout()

        # Search bar
        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText("Search templates...")
        self.search_bar.textChanged.connect(self.filter_templates)
        list_layout.addWidget(self.search_bar)

        # List widget to display templates
        self.list_widget = QListWidget(self)
        self.list_widget.itemClicked.connect(self.show_template_preview)
        list_layout.addWidget(self.list_widget)

        # Add the list layout to the main layout
        main_layout.addLayout(list_layout)

        # Web view to display rendered markdown (this will be placed next to the list)
        self.preview_area = QWebEngineView(self)
        self.preview_area.setMinimumWidth(400)  # Ensure the preview area has enough space
        main_layout.addWidget(self.preview_area)

        # Button layout
        button_layout = QHBoxLayout()

        # Load button
        load_button = QPushButton("Load Template", self)
        load_button.clicked.connect(self.load_selected_template)
        button_layout.addWidget(load_button)

        # Rename button
        rename_button = QPushButton("Rename Template", self)
        rename_button.clicked.connect(self.rename_selected_template)
        button_layout.addWidget(rename_button)

        # Delete button
        delete_button = QPushButton("Delete Template", self)
        delete_button.clicked.connect(self.delete_selected_template)
        button_layout.addWidget(delete_button)

        # Add the button layout below the preview area
        list_layout.addLayout(button_layout)

        # Load templates initially
        self.load_templates()

    def load_templates(self):
        """Load the list of templates from the directory."""
        self.templates = [f for f in os.listdir(self.templates_dir) if f.endswith('.md')]
        self.list_widget.clear()
        self.list_widget.addItems(self.templates)

    def filter_templates(self, text):
        """Filter the templates in the list widget based on the search text."""
        self.list_widget.clear()
        filtered_templates = [t for t in self.templates if text.lower() in t.lower()]
        self.list_widget.addItems(filtered_templates)

    def show_template_preview(self, item):
        """Display the selected template's content rendered as HTML in the preview area."""
        template_path = os.path.join(self.templates_dir, item.text())
        with open(template_path, 'r') as file:
            content = file.read()

        # Convert Markdown to HTML using markdown2
        html = markdown2.markdown(content, extras=["fenced-code-blocks", "tables", "strike"])

        # Add dark theme CSS and dark scrollbar
        css = """
        <style>
            body { font-family: Arial, sans-serif; padding: 15px; background-color: #2e2e2e; color: #f8f8f2; }
            pre { background-color: #444; color: #f8f8f2; padding: 10px; border-radius: 8px; }
            code { background-color: #444; color: #f8f8f2; padding: 2px 4px; border-radius: 4px; }
            blockquote { border-left: 5px solid #888; padding-left: 10px; color: #aaa; }
            table { width: 100%; border-collapse: collapse; }
            th, td { padding: 8px 12px; border: 1px solid #444; }
            th { background-color: #555; color: #f8f8f2; }
            ::-webkit-scrollbar {
                width: 12px;
            }
            ::-webkit-scrollbar-track {
                background: #2e2e2e;
            }
            ::-webkit-scrollbar-thumb {
                background-color: #888;
                border-radius: 10px;
            }
            ::-webkit-scrollbar-thumb:hover {
                background-color: #555;
            }
        </style>
        """

        # Set the HTML content in the web view
        self.preview_area.setHtml(css + html)

    def load_selected_template(self):
        """Load the selected template into the main editor and create a new .md file with a unique name if necessary."""
        selected_item = self.list_widget.currentItem()
        if selected_item:
            template_name = selected_item.text()
            template_path = os.path.join(self.templates_dir, template_name)
            
            with open(template_path, 'r') as file:
                content = file.read()
            
            # Get the project folder from settings or use a default path
            project_folder = self.parent().settings.get("default_project_folder", QDir.currentPath() + "/projectfolder/mymd")
            if not os.path.exists(project_folder):
                os.makedirs(project_folder)
            
            # Create a unique file name
            base_name, extension = os.path.splitext(template_name)
            new_file_name = template_name
            counter = 1
            while os.path.exists(os.path.join(project_folder, new_file_name)):
                new_file_name = f"{base_name}_{counter}{extension}"
                counter += 1
            
            new_file_path = os.path.join(project_folder, new_file_name)
            
            # Write the content to the new file
            with open(new_file_path, 'w', encoding='utf-8') as new_file:
                new_file.write(content)
            
            # Load the new file into the editor
            self.parent().open_file_by_path(new_file_path)
            self.accept()

    def rename_selected_template(self):
        """Rename the selected template file."""
        selected_item = self.list_widget.currentItem()
        if selected_item:
            old_name = selected_item.text()
            new_name, ok = QInputDialog.getText(self, "Rename Template", "Enter new name:", text=old_name)
            if ok and new_name:
                old_path = os.path.join(self.templates_dir, old_name)
                new_path = os.path.join(self.templates_dir, f"{new_name}.md")
                if os.path.exists(new_path):
                    QMessageBox.warning(self, "Error", f"A template named '{new_name}' already exists.")
                else:
                    os.rename(old_path, new_path)
                    self.load_templates()  # Refresh the list
                    QMessageBox.information(self, "Template Renamed", f"Template '{old_name}' renamed to '{new_name}'.")

    def delete_selected_template(self):
        """Delete the selected template file."""
        selected_item = self.list_widget.currentItem()
        if selected_item:
            template_name = selected_item.text()
            confirm = QMessageBox.question(self, "Delete Template", f"Are you sure you want to delete '{template_name}'?", QMessageBox.Yes | QMessageBox.No)
            if confirm == QMessageBox.Yes:
                os.remove(os.path.join(self.templates_dir, template_name))
                self.load_templates()  # Refresh the list
                self.preview_area.setHtml("")  # Clear the preview area
                QMessageBox.information(self, "Template Deleted", f"Template '{template_name}' has been deleted.")


class ProgressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Insert Progress")
        self.setFixedSize(250, 120)

        layout = QVBoxLayout(self)

        self.label = QLabel("Select Progress Value:", self)
        layout.addWidget(self.label)

        self.spin_box = QSpinBox(self)
        self.spin_box.setRange(1, 100)
        self.spin_box.setValue(50)
        layout.addWidget(self.spin_box)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def get_progress_value(self):
        return self.spin_box.value()


class MarkdownEditor(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Markiva")
        self.setGeometry(100, 100, 1200, 800)
        self.dark_mode = True  # Start with dark mode by default

        # Load settings
        self.settings_file = "user_settings.json"
        self.settings = self.load_settings()

        self.check_startup_dialog()  # Check and possibly show the startup dialog

        self.current_file = None  # Track the currently open file

        # Set up the preview panel with QWebEngineView (initializing preview here)
        self.preview = QWebEngineView()

        # Now set up the web channel
        self.setup_web_channel()

        # Initialize the rest of the UI
        self.initUI()

        self.apply_settings()  # Apply settings after loading UI

    def setup_web_channel(self):
        # Setup the channel for JavaScript to PyQt communication
        self.channel = QWebChannel()
        self.preview.page().setWebChannel(self.channel)
        self.channel.registerObject('external', self)

    def load_settings(self):
        if os.path.exists(self.settings_file):
            with open(self.settings_file, 'r') as f:
                return json.load(f)
        return {}

    def save_settings(self):
        with open(self.settings_file, 'w') as f:
            json.dump(self.settings, f)

    def check_startup_dialog(self):
        if self.settings.get("show_startup", True):
            dialog = StartupDialog(self.settings_file)
            if dialog.exec_() != QDialog.Accepted:
                sys.exit()

    def initUI(self):
        # Set up the editor panel first
        font_size = self.settings.get("font_size", 14)
        self.editor = CodeEditor(font_size=font_size)
        self.editor.textChanged.connect(self.update_preview)
        self.editor.textChanged.connect(self.update_status_bar)  # Update status bar on text change
        self.editor.cursorPositionChanged.connect(self.update_cursor_position)

        # Connect scroll event to preview synchronization
        self.editor.verticalScrollBar().valueChanged.connect(self.update_preview_scroll_position)

        # Create status bar
        self.create_status_bar()

        # Create menu bar
        self.createMenuBar()

        # Create the main toolbar
        self.toolbar = QToolBar("Markdown Toolbar", self)
        self.toolbar.setObjectName("MarkdownToolbar")
        self.addToolBar(self.toolbar)

        # Create the settings toolbar
        self.settings_toolbar = QToolBar("Editor Settings", self)
        self.settings_toolbar.setObjectName("EditorSettingsToolbar")
        self.addToolBar(self.settings_toolbar)

        # Add actions to the toolbars
        self.update_toolbar_icons()
        self.createEditorSettingsToolbar()

        # Set up file explorer
        self.setup_file_explorer()

        # Set up main layout and splitter
        main_layout = QVBoxLayout()
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(8)

        # Set up the preview panel with QWebEngineView
        self.preview = QWebEngineView()

        # Enable access to remote content
        self.preview.settings().setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        self.preview.settings().setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        self.preview.settings().setAttribute(QWebEngineSettings.AutoLoadImages, True)

        self.preview.setStyleSheet("background-color: #1e1e1e; border-left: 2px solid #3e3e3e;")

        # Set an initial empty content with the correct background
        self.set_initial_preview_content()

        # Add widgets to the splitter
        splitter.addWidget(self.file_tree_view)
        splitter.addWidget(self.editor)
        splitter.addWidget(self.preview)
        splitter.setSizes([200, 500, 500])  # Adjust sizes of the file explorer, editor, and preview

        # Set the layout
        main_widget = QWidget()
        main_layout.addWidget(splitter)
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        # Maximize the window
        self.showMaximized()

        # Set the initial stylesheet for a modern dark theme
        self.set_dark_theme()

        # Open default file if set in settings
        self.open_default_file()

        # Restore window state (including toolbar positions)
        self.restore_window_state()

    def apply_settings(self):
        self.editor.set_font_size(self.settings.get("font_size", 14))
        self.editor.set_font_family(self.settings.get("font_family", "Fira Code"))
        self.editor.set_background_color(self.settings.get("background_color", "#1e1e1e"))
        self.editor.set_text_color(self.settings.get("text_color", "#ffffff"))
        if self.settings.get("dark_mode", True):
            self.set_dark_theme()
        else:
            self.set_light_theme()
        self.update_toolbar_icons()  # Update toolbar icons when settings are applied
        self.update_preview()  # Update preview pane when settings are applied

    def create_status_bar(self):
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #333333;  /* Darker background */
                color: #ffffff;              /* White text */
                font-family: Consolas, "Courier New", monospace;
                font-size: 14px;
                padding: 5px;                /* More padding for a better appearance */
                border-top: 1px solid #007acc;  /* Thinner blue border at the top */
            }
            QLabel {
                margin-right: 20px;          /* Space between different labels */
            }
        """)

        # Add an icon to the far left of the status bar
        self.icon_label = QLabel()
        icon = QIcon(qta.icon('fa.info-circle', color='white').pixmap(16, 16))  # Using qtawesome for the icon
        self.icon_label.setPixmap(icon.pixmap(16, 16))
        self.icon_label.mousePressEvent = self.show_status_info  # Connect to a method when clicked

        # Status bar widgets
        self.file_name_label = QLabel("No file open")
        self.word_count_label = QLabel("Words: 0")
        self.char_count_label = QLabel("Characters: 0")
        self.reading_time_label = QLabel("Reading Time: 0 min")
        self.cursor_position_label = QLabel("Line: 1, Col: 1")
        self.modified_label = QLabel("Modified: No")
        self.syntax_label = QLabel("Syntax: Markdown")
        self.zoom_level_label = QLabel("Zoom: 100%")
        self.date_time_label = QLabel()

        # Add the icon and widgets to the status bar
        self.status_bar.addWidget(self.icon_label)
        self.status_bar.addPermanentWidget(self.file_name_label)
        self.status_bar.addPermanentWidget(self.word_count_label)
        self.status_bar.addPermanentWidget(self.char_count_label)
        self.status_bar.addPermanentWidget(self.reading_time_label)
        self.status_bar.addPermanentWidget(self.cursor_position_label)
        self.status_bar.addPermanentWidget(self.modified_label)
        self.status_bar.addPermanentWidget(self.syntax_label)
        self.status_bar.addPermanentWidget(self.zoom_level_label)
        self.status_bar.addPermanentWidget(self.date_time_label)

        # Adding a progress bar to the status bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)

        self.setStatusBar(self.status_bar)

        # Update date and time every second
        self.update_date_time()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_date_time)
        self.timer.start(1000)

    def update_status_bar(self):
        text = self.editor.toPlainText()
        word_count = len(text.split()) if text.strip() else 0
        char_count = len(text) if text.strip() else 0
        reading_time = round(word_count / 200)  # Assuming 200 words per minute reading speed

        self.word_count_label.setText(f"Words: {word_count}")
        self.char_count_label.setText(f"Characters: {char_count}")
        self.reading_time_label.setText(f"Reading Time: {reading_time} min")

        if self.current_file:
            file_name = os.path.basename(self.current_file)
            self.file_name_label.setText(f"File: {file_name}")
        else:
            self.file_name_label.setText("No file open")

        modified_status = "Yes" if self.editor.document().isModified() else "No"
        self.modified_label.setText(f"Modified: {modified_status}")

        # Update syntax label (assuming Markdown, but could be extended for other formats)
        syntax = "Markdown"  # You could detect other formats if necessary
        self.syntax_label.setText(f"Syntax: {syntax}")

        # Update zoom level
        zoom_level = int(self.editor.font().pointSize() / self.settings.get("font_size", 14) * 100)  # Assuming font size is related to zoom
        self.zoom_level_label.setText(f"Zoom: {zoom_level}%")

    def update_cursor_position(self):
        cursor = self.editor.textCursor()  # Corrected this line to use self.editor
        line = cursor.blockNumber() + 1
        column = cursor.columnNumber() + 1
        self.cursor_position_label.setText(f"Line: {line}, Col: {column}")


    def update_date_time(self):
        current_date_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.date_time_label.setText(f"{current_date_time}")

    def show_status_info(self, event):
        """Display a dialog with information about the status bar items."""
        info_text = """
        - **File**: Name of the currently opened file.
        - **Words**: Number of words in the document.
        - **Characters**: Number of characters in the document.
        - **Reading Time**: Estimated reading time based on word count.
        - **Line, Col**: Current line and column number.
        - **Modified**: Indicates if the document has unsaved changes.
        - **Word**: Current word under the cursor.
        - **Syntax**: Syntax highlighting mode (e.g., Markdown).
        - **Zoom**: Current zoom level of the editor.
        - **Date & Time**: Current system date and time.
        """
        QMessageBox.information(self, "Status Bar Information", info_text)


    def update_preview(self):
        raw_markdown = self.editor.toPlainText()

        # Replace Markdown checkboxes with HTML checkboxes
        raw_markdown = raw_markdown.replace('- [ ]', '<input type="checkbox">').replace('- [x]', '<input type="checkbox" checked>')

        # Use markdown2 with extras to support tables, fenced-code-blocks, and other features
        html = markdown2.markdown(
            raw_markdown,
            extras=["fenced-code-blocks", "tables", "strike"]
        )

        # JavaScript to make checkboxes functional
        js_code = """
        <script>
        document.addEventListener('DOMContentLoaded', function() {
            document.querySelectorAll('input[type="checkbox"]').forEach(function(checkbox) {
                checkbox.addEventListener('change', function() {
                    if (checkbox.checked) {
                        checkbox.nextElementSibling.style.textDecoration = 'line-through';
                    } else {
                        checkbox.nextElementSibling.style.textDecoration = 'none';
                    }
                });
            });
        });
        </script>
        """

        # Add custom CSS for code blocks, blockquotes, and scrollbar
        custom_css = """
        <style>
            body {
                font-family: Consolas, "Courier New", monospace;
                color: #f8f8f2;
                background-color: #1e1e1e;
                padding: 15px;
                margin: 0;
            }
            pre {
                background-color: #2b2b2b;
                color: #f8f8f2;
                padding: 8px 12px;
                border-left: 5px solid #00cc66;  /* Green accent for code blocks */
                border-radius: 8px;
                display: block;
                overflow-x: auto;
                margin-bottom: 20px;
                font-size: 14px;
                white-space: pre-wrap; /* Ensure code block retains formatting */
                word-wrap: break-word; /* Ensure long lines wrap */
            }
            blockquote {
                background-color: #2e2e2e;
                color: #dddddd;
                border-left: 5px solid #ffcc00;  /* Yellow accent for blockquotes */
                padding: 10px 20px;
                margin: 20px 0;
                border-radius: 8px;
                font-style: italic;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 20px;
                background-color: #2b2b2b;
                color: #f8f8f2;
            }
            th, td {
                border: 1px solid #444;
                padding: 8px 12px;
                text-align: left;
            }
            th {
                background-color: #333;
                font-weight: bold;
            }
            img {
                max-width: 100%;
                height: auto;
            }
            /* Custom scrollbar styling */
            ::-webkit-scrollbar {
                width: 8px;
                height: 8px;
            }
            ::-webkit-scrollbar-track {
                background: #1e1e1e;
            }
            ::-webkit-scrollbar-thumb {
                background-color: #444;
                border-radius: 4px;
            }
            ::-webkit-scrollbar-thumb:hover {
                background-color: #555;
            }
            /* Checkbox styling */
            input[type="checkbox"] {
                margin-right: 8px;
            }
            input[type="checkbox"]:checked + label {
                text-decoration: line-through;
            }
        </style>
        """

        if not self.dark_mode:
            custom_css = custom_css.replace('#1e1e1e', '#ffffff').replace('#f8f8f2', '#000000').replace('#2b2b2b', '#f0f0f0').replace('#2e2e2e', '#e0e0e0')

        # Ensure newlines within code blocks are treated as literal
        html = html.replace('<pre><code>', '<pre style="white-space:pre-wrap;"><code style="white-space:pre-wrap;">')

        # Insert the CSS and JS into the HTML
        full_html = custom_css + html + js_code

        # Set the HTML content in the preview pane
        self.preview.page().setHtml(full_html)

    def update_preview_scroll_position(self):
        """
        Synchronize the scroll position between the editor and the preview pane.
        """
        # Calculate the percentage of scroll in the editor
        editor_scroll_position = self.editor.verticalScrollBar().value()
        editor_scroll_range = self.editor.verticalScrollBar().maximum()
        editor_scroll_percentage = editor_scroll_position / editor_scroll_range if editor_scroll_range else 0

        # Apply the same percentage to the preview pane
        preview_scroll_range = self.preview.page().contentsSize().height() - self.preview.height()
        preview_scroll_position = preview_scroll_range * editor_scroll_percentage
        self.preview.page().runJavaScript(f"window.scrollTo(0, {preview_scroll_position});")

    def set_initial_preview_content(self):
        # This sets the initial content of the preview pane with the correct background style
        initial_html = """
        <html>
        <head>
        <style>
            body {
                font-family: Consolas, "Courier New", monospace;
                color: #f8f8f2;
                background-color: #1e1e1e;
                padding: 15px;
            }
        </style>
        </head>
        <body>
        </body>
        </html>
        """
        self.preview.setHtml(initial_html)

    def setup_file_explorer(self):
        self.file_model = CustomFileSystemModel()
        default_folder = self.settings.get("default_project_folder", QDir.currentPath() + "/projectfolder/mymd")
        self.file_model.setRootPath(default_folder)
        self.file_model.setNameFilters(["*.md"])
        self.file_model.setNameFilterDisables(False)

        # Setting the default open file for the model
        default_file = self.settings.get("default_open_file")
        if default_file:
            self.file_model.set_default_open_file(default_file)

        self.tree = CustomTreeView()  # Use CustomTreeView instead of QTreeView
        self.tree.setModel(self.file_model)
        self.tree.setRootIndex(self.file_model.index(default_folder))
        self.tree.setHeaderHidden(False)
        self.tree.setSortingEnabled(True)  # Enable sorting
        self.tree.sortByColumn(0, Qt.AscendingOrder)  # Sort by the first column (name) in ascending order
        self.tree.setDragDropMode(QTreeView.InternalMove)  # Enable drag and drop within the tree
        self.tree.setDefaultDropAction(Qt.MoveAction)

        # Hide unnecessary columns
        self.tree.setColumnHidden(1, True)  # Hide size column
        self.tree.setColumnHidden(2, True)  # Hide type column
        self.tree.setColumnHidden(3, True)  # Hide date modified column

        # Handle file selection
        self.tree.clicked.connect(self.open_selected_file)

        # Set up the contextual menu
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_context_menu)

        # Add buttons to the file explorer layout
        explorer_layout = QVBoxLayout()
        button_layout = QHBoxLayout()

        add_file_button = QPushButton("Add File")
        delete_file_button = QPushButton("Delete File")

        add_file_button.clicked.connect(self.add_file)
        delete_file_button.clicked.connect(self.delete_file)

        button_layout.addWidget(add_file_button)
        button_layout.addWidget(delete_file_button)

        choose_folder_button = QPushButton("Choose Project Folder")
        choose_folder_button.clicked.connect(self.set_default_project_folder)

        # Ensure the button spans the entire width
        choose_folder_button.setSizePolicy(QSizePolicy.Expanding, add_file_button.sizePolicy().verticalPolicy())

        explorer_layout.addWidget(choose_folder_button)
        explorer_layout.addLayout(button_layout)
        explorer_layout.addWidget(self.tree)

        explorer_widget = QWidget()
        explorer_widget.setLayout(explorer_layout)

        self.file_tree_view = explorer_widget

    def open_default_file(self):
        default_file = self.settings.get("default_open_file")
        if default_file and os.path.exists(default_file):
            self.open_file_by_path(default_file)

    def add_file(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Create Markdown File", self.settings.get("default_project_folder", "projectfolder/mymd/"), "Markdown Files (*.md);;All Files (*)")
        if file_name:
            open(file_name, 'w').close()  # Create an empty file
            self.file_model.setRootPath(QDir.currentPath())  # Refresh the file model

    def delete_file(self):
        index = self.tree.currentIndex()
        if index.isValid():
            file_path = self.file_model.filePath(index)
            if os.path.isdir(file_path):
                confirm = QMessageBox.question(self, "Delete Folder", f"Are you sure you want to delete the folder {file_path} and all its contents?", QMessageBox.Yes | QMessageBox.No)
                if confirm == QMessageBox.Yes:
                    try:
                        os.rmdir(file_path)
                    except OSError:
                        QMessageBox.warning(self, "Error", f"Could not delete the folder {file_path}. It may not be empty.")
            else:
                confirm = QMessageBox.question(self, "Delete File", f"Are you sure you want to delete {file_path}?", QMessageBox.Yes | QMessageBox.No)
                if confirm == QMessageBox.Yes:
                    try:
                        os.remove(file_path)
                    except PermissionError:
                        QMessageBox.warning(self, "Error", f"Permission denied: Could not delete {file_path}.")

            self.file_model.setRootPath(QDir.currentPath())  # Refresh the file model

    def open_selected_file(self, index):
        file_path = self.file_model.filePath(index)
        if file_path.endswith('.md'):
            self.open_file_by_path(file_path)

    def open_file_by_path(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                self.editor.setPlainText(file.read())
                self.current_file = file_path
                self.setWindowTitle(f"{os.path.basename(self.current_file)} - Markiva")
                self.editor.document().setModified(False)  # Reset modified status
                self.update_status_bar()  # Ensure status bar is updated after file is opened

                # Highlight the file in the tree view
                index = self.file_model.index(file_path)
                self.tree.setCurrentIndex(index)
                self.tree.scrollTo(index)  # Ensure the file is visible
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open file: {str(e)}")



    def open_context_menu(self, position):
        index = self.tree.indexAt(position)

        menu = QMenu(self)

        if index.isValid():
            open_action = QAction("Open", self)
            open_action.triggered.connect(lambda: self.open_selected_file(index))
            menu.addAction(open_action)

            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(self.delete_file)
            menu.addAction(delete_action)

            rename_action = QAction("Rename", self)
            rename_action.triggered.connect(lambda: self.rename_file(index))
            menu.addAction(rename_action)

            properties_action = QAction("Properties", self)
            properties_action.triggered.connect(lambda: self.show_file_properties(index))
            menu.addAction(properties_action)

            set_default_open_action = QAction("Set as Default Open File", self)
            set_default_open_action.triggered.connect(lambda: self.set_default_open_file(index))
            menu.addAction(set_default_open_action)
        else:
            add_file_action = QAction("Add File", self)
            add_file_action.triggered.connect(self.add_file)
            menu.addAction(add_file_action)

            create_folder_action = QAction("Create Folder", self)
            create_folder_action.triggered.connect(self.create_folder)
            menu.addAction(create_folder_action)

        menu.exec_(self.tree.viewport().mapToGlobal(position))

    def create_folder(self):
        folder_name, ok = QInputDialog.getText(self, "Create Folder", "Folder name:")
        if ok and folder_name:
            current_dir = self.file_model.rootPath()
            new_folder_path = os.path.join(current_dir, folder_name)
            try:
                os.mkdir(new_folder_path)
                self.file_model.setRootPath(QDir.currentPath())  # Refresh the file model
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not create folder: {str(e)}")

    def rename_file(self, index):
        file_path = self.file_model.filePath(index)
        new_name, ok = QInputDialog.getText(self, "Rename File", "New file name:", text=QFileInfo(file_path).fileName())
        if ok and new_name:
            new_path = os.path.join(QFileInfo(file_path).absolutePath(), new_name)
            if os.path.exists(new_path):
                QMessageBox.warning(self, "Error", f"A file named '{new_name}' already exists.")
            else:
                os.rename(file_path, new_path)
                self.file_model.setRootPath(QDir.currentPath())  # Refresh the file model

    def show_file_properties(self, index):
        file_path = self.file_model.filePath(index)
        file_info = QFileInfo(file_path)
        file_size = file_info.size()
        file_type, _ = mimetypes.guess_type(file_path)
        if not file_type:
            file_type = "Unknown"

        properties = f"""
        File: {file_info.fileName()}
        Size: {file_size} bytes
        Type: {file_type}
        Last Modified: {file_info.lastModified().toString()}
        """

        QMessageBox.information(self, "File Properties", properties)

    def set_default_open_file(self, index):
        file_path = self.file_model.filePath(index)
        self.settings["default_open_file"] = file_path
        self.save_settings()
        self.file_model.set_default_open_file(file_path)

    def createMenuBar(self):
        menubar = QMenuBar(self)
        self.setMenuBar(menubar)

        # File menu
        file_menu = QMenu("File", self)
        menubar.addMenu(file_menu)

        save_file_action = QAction("Save", self)
        save_file_action.triggered.connect(self.save_file)
        file_menu.addAction(save_file_action)

        export_pdf_action = QAction("Export as PDF", self)
        export_pdf_action.triggered.connect(self.export_to_pdf)
        file_menu.addAction(export_pdf_action)

        export_html_action = QAction("Export as HTML", self)
        export_html_action.triggered.connect(self.export_to_html)
        file_menu.addAction(export_html_action)

        file_menu.addSeparator()

        auto_save_action = QAction("Auto-save", self)
        auto_save_action.triggered.connect(self.auto_save)
        file_menu.addAction(auto_save_action)

        version_control_action = QAction("Version Control", self)
        version_control_action.triggered.connect(self.show_version_control)
        file_menu.addAction(version_control_action)

        # Edit menu
        edit_menu = QMenu("Edit", self)
        menubar.addMenu(edit_menu)

        find_replace_action = QAction("Find and Replace", self)
        find_replace_action.triggered.connect(self.find_replace)
        edit_menu.addAction(find_replace_action)

        # View menu
        view_menu = QMenu("View", self)
        menubar.addMenu(view_menu)

        toggle_theme_action = QAction("Toggle Dark/Light Mode", self)
        toggle_theme_action.triggered.connect(self.toggle_theme)
        view_menu.addAction(toggle_theme_action)

        generate_toc_action = QAction("Generate Table of Contents", self)
        generate_toc_action.triggered.connect(self.generate_toc)
        view_menu.addAction(generate_toc_action)

        show_terminal_action = QAction("Show Terminal", self)
        show_terminal_action.triggered.connect(self.show_terminal)
        view_menu.addAction(show_terminal_action)

        # Settings menu
        settings_menu = QMenu("Settings", self)
        menubar.addMenu(settings_menu)
        settings_menu.addAction("Application Settings", self.open_settings_window)

        # Templates menu
        template_menu = QMenu("Templates", self)
        menubar.addMenu(template_menu)

        load_template_action = QAction("Load Template", self)
        load_template_action.triggered.connect(self.load_template)
        template_menu.addAction(load_template_action)

        save_template_action = QAction("Save as Template", self)
        save_template_action.triggered.connect(self.save_as_template)
        template_menu.addAction(save_template_action)

        # Help menu with the About action
        help_menu = QMenu("Help", self)
        menubar.addMenu(help_menu)

        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def createToolbar(self):
        self.update_toolbar_icons()

    def update_toolbar_icons(self):
        self.toolbar.clear()

        icon_color = 'white' if self.dark_mode else 'black'

        bold_icon = qta.icon('fa.bold', color=icon_color)
        italic_icon = qta.icon('fa.italic', color=icon_color)
        underline_icon = qta.icon('fa.underline', color=icon_color)
        strikethrough_icon = qta.icon('fa.strikethrough', color=icon_color)
        heading_icon = qta.icon('fa.header', color=icon_color)
        superscript_icon = qta.icon('fa.superscript', color=icon_color)
        subscript_icon = qta.icon('fa.subscript', color=icon_color)
        checkbox_icon = qta.icon('fa.check-square', color=icon_color)
        highlight_icon = qta.icon('fa.paint-brush', color=icon_color)
        emoji_icon = qta.icon('fa.smile-o', color=icon_color)
        link_icon = qta.icon('fa.link', color=icon_color)
        image_icon = qta.icon('fa.picture-o', color=icon_color)
        code_icon = qta.icon('fa.code', color=icon_color)
        bullet_list_icon = qta.icon('fa.list-ul', color=icon_color)
        numbered_list_icon = qta.icon('fa.list-ol', color=icon_color)
        blockquote_icon = qta.icon('fa.quote-right', color=icon_color)
        hr_icon = qta.icon('fa.minus', color=icon_color)
        table_icon = qta.icon('fa.table', color=icon_color)
        save_icon = qta.icon('fa.save', color=icon_color)
        open_icon = qta.icon('fa.folder-open', color=icon_color)
        undo_icon = qta.icon('fa.undo', color=icon_color)
        redo_icon = qta.icon('fa.repeat', color=icon_color)
        indent_icon = qta.icon('fa.indent', color=icon_color)
        outdent_icon = qta.icon('fa.outdent', color=icon_color)
        settings_icon = qta.icon('fa.cog', color=icon_color)
        misc_icon = qta.icon('fa.bars', color=icon_color)  # Icon for Misc dropdown

        # Icons for H1, H2, and Images
        h1_icon = qta.icon('fa.header', color=icon_color)
        h2_icon = qta.icon('fa.header', color=icon_color)
        img_icon = qta.icon('fa.image', color=icon_color)

        # Add actions to toolbar with separators for better organization
        bold_action = QAction(bold_icon, "Bold", self)
        bold_action.triggered.connect(lambda: self.editor.insert_markdown("**", "**"))
        self.toolbar.addAction(bold_action)

        italic_action = QAction(italic_icon, "Italic", self)
        italic_action.triggered.connect(lambda: self.editor.insert_markdown("*", "*"))
        self.toolbar.addAction(italic_action)

        underline_action = QAction(underline_icon, "Underline", self)
        underline_action.triggered.connect(lambda: self.editor.insert_markdown("<u>", "</u>"))
        self.toolbar.addAction(underline_action)

        strikethrough_action = QAction(strikethrough_icon, "Strikethrough", self)
        strikethrough_action.triggered.connect(lambda: self.editor.insert_markdown("~~", "~~"))
        self.toolbar.addAction(strikethrough_action)

        self.toolbar.addSeparator()

        heading_action = QAction(heading_icon, "Heading", self)
        heading_action.triggered.connect(lambda: self.editor.insert_markdown("# ", ""))
        self.toolbar.addAction(heading_action)

        superscript_action = QAction(superscript_icon, "Superscript", self)
        superscript_action.triggered.connect(lambda: self.editor.insert_markdown("<sup>", "</sup>"))
        self.toolbar.addAction(superscript_action)

        subscript_action = QAction(subscript_icon, "Subscript", self)
        subscript_action.triggered.connect(lambda: self.editor.insert_markdown("<sub>", "</sub>"))
        self.toolbar.addAction(subscript_action)

        checkbox_action = QAction(checkbox_icon, "Checkbox", self)
        checkbox_action.triggered.connect(lambda: self.editor.insert_list("checkbox"))
        self.toolbar.addAction(checkbox_action)

        highlight_action = QAction(highlight_icon, "Highlight", self)
        highlight_action.triggered.connect(lambda: self.editor.insert_markdown("<mark>", "</mark>"))
        self.toolbar.addAction(highlight_action)

        emoji_action = QAction(emoji_icon, "Emoji", self)
        emoji_action.triggered.connect(self.insert_emoji)  # Connect to the emoji insertion method
        self.toolbar.addAction(emoji_action)

        self.toolbar.addSeparator()

        blockquote_action = QAction(blockquote_icon, "Blockquote", self)
        blockquote_action.triggered.connect(lambda: self.editor.insert_markdown("> ", ""))
        self.toolbar.addAction(blockquote_action)

        code_action = QAction(code_icon, "Code", self)
        code_action.triggered.connect(lambda: self.editor.insert_markdown("```", "```", block=True))
        self.toolbar.addAction(code_action)


        hr_action = QAction(hr_icon, "Horizontal Rule", self)
        hr_action.triggered.connect(lambda: self.editor.insert_markdown("\n---\n", ""))
        self.toolbar.addAction(hr_action)

        self.toolbar.addSeparator()

        bullet_list_action = QAction(bullet_list_icon, "Bullet List", self)
        bullet_list_action.triggered.connect(lambda: self.editor.insert_list("bullet"))
        self.toolbar.addAction(bullet_list_action)

        numbered_list_action = QAction(numbered_list_icon, "Numbered List", self)
        numbered_list_action.triggered.connect(lambda: self.editor.insert_list("numbered"))
        self.toolbar.addAction(numbered_list_action)

        indent_action = QAction(indent_icon, "Indent", self)
        indent_action.triggered.connect(self.editor.indent)
        self.toolbar.addAction(indent_action)

        outdent_action = QAction(outdent_icon, "Outdent", self)
        outdent_action.triggered.connect(self.editor.outdent)
        self.toolbar.addAction(outdent_action)

        self.toolbar.addSeparator()

        link_action = QAction(link_icon, "Link", self)
        link_action.triggered.connect(self.insert_link)
        self.toolbar.addAction(link_action)

        image_action = QAction(image_icon, "Image", self)
        image_action.triggered.connect(lambda: self.editor.insert_markdown("![", "](image_url)"))
        self.toolbar.addAction(image_action)

        self.toolbar.addSeparator()

        table_action = QAction(table_icon, "Table", self)
        table_action.triggered.connect(self.show_table_editor)
        self.toolbar.addAction(table_action)
        
        # Misc dropdown button
        misc_menu = QMenu(self)
        insert_progress_action = QAction("Insert Progress", self)
        insert_progress_action.triggered.connect(self.insert_progress)
        misc_menu.addAction(insert_progress_action)

        misc_button = QToolButton(self)
        misc_button.setIcon(misc_icon)
        misc_button.setMenu(misc_menu)
        misc_button.setPopupMode(QToolButton.InstantPopup)
        self.toolbar.addWidget(misc_button)

        # HTML elements insertion
        self.toolbar.addSeparator()

        h1_action = QAction(h1_icon, "H1", self)
        h1_action.triggered.connect(lambda: self.editor.insert_html("h1"))
        self.toolbar.addAction(h1_action)

        h2_action = QAction(h2_icon, "H2", self)
        h2_action.triggered.connect(lambda: self.editor.insert_html("h2"))
        self.toolbar.addAction(h2_action)

        img_action = QAction(img_icon, "HTML Image", self)
        img_action.triggered.connect(lambda: self.editor.insert_html("img", 'src="image_url"'))
        self.toolbar.addAction(img_action)

        self.toolbar.addSeparator()

        undo_action = QAction(undo_icon, "Undo", self)
        undo_action.triggered.connect(self.editor.undo)
        self.toolbar.addAction(undo_action)

        redo_action = QAction(redo_icon, "Redo", self)
        redo_action.triggered.connect(self.editor.redo)
        self.toolbar.addAction(redo_action)

        self.toolbar.addSeparator()

        save_action = QAction(save_icon, "Save", self)
        save_action.triggered.connect(self.save_file)
        self.toolbar.addAction(save_action)

        open_action = QAction(open_icon, "Open", self)
        open_action.triggered.connect(self.open_file)
        self.toolbar.addAction(open_action)

        settings_action = QAction(settings_icon, "Settings", self)
        settings_action.triggered.connect(self.open_settings_window)
        self.toolbar.addAction(settings_action)


    def createEditorSettingsToolbar(self):
        # Font Family
        font_family_combo = QComboBox(self)
        font_family_combo.addItems(["Fira Code", "Consolas", "Courier New", "Arial", "Times New Roman"])
        font_family_combo.setCurrentText(self.editor.font().family())
        font_family_combo.currentTextChanged.connect(lambda text: self.editor.set_font_family(text))
        self.settings_toolbar.addWidget(QLabel("Font:"))
        self.settings_toolbar.addWidget(font_family_combo)

        # Add a spacer
        self.settings_toolbar.addSeparator()

        # Font Size
        font_size_spinbox = QSpinBox(self)
        font_size_spinbox.setRange(8, 36)
        font_size_spinbox.setValue(self.editor.font().pointSize())
        font_size_spinbox.valueChanged.connect(self.editor.set_font_size)
        self.settings_toolbar.addWidget(QLabel("Size:"))
        self.settings_toolbar.addWidget(font_size_spinbox)

        # Add a spacer
        self.settings_toolbar.addSeparator()

        # Background Color
        background_color_button = QPushButton("Background Color", self)
        background_color_button.clicked.connect(self.choose_background_color)
        self.settings_toolbar.addWidget(background_color_button)

        # Add a spacer
        self.settings_toolbar.addSeparator()

        # Text Color
        text_color_button = QPushButton("Text Color", self)
        text_color_button.clicked.connect(self.choose_text_color)
        self.settings_toolbar.addWidget(text_color_button)

        # Add a spacer
        self.settings_toolbar.addSeparator()

        # Line Numbers
        line_numbers_checkbox = QCheckBox("Show Line Numbers", self)
        line_numbers_checkbox.setChecked(True)
        line_numbers_checkbox.toggled.connect(self.toggle_line_numbers)
        self.settings_toolbar.addWidget(line_numbers_checkbox)

        # Add a spacer
        self.settings_toolbar.addSeparator()

        # Spell Check
        spell_check_checkbox = QCheckBox("Enable Spell Check", self)
        spell_check_checkbox.setChecked(True)
        spell_check_checkbox.toggled.connect(self.toggle_spell_check)
        self.settings_toolbar.addWidget(spell_check_checkbox)

        # Add a spacer
        self.settings_toolbar.addSeparator()

        # Word Wrap
        word_wrap_checkbox = QCheckBox("Enable Word Wrap", self)
        word_wrap_checkbox.setChecked(True)
        word_wrap_checkbox.toggled.connect(self.toggle_word_wrap)
        self.settings_toolbar.addWidget(word_wrap_checkbox)

    def choose_background_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.editor.set_background_color(color.name())

    def choose_text_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.editor.set_text_color(color.name())

    def toggle_line_numbers(self, checked):
        self.editor.lineNumberArea.setVisible(checked)

    def toggle_spell_check(self, checked):
        if checked:
            self.editor.textChanged.connect(self.editor.check_spelling)
        else:
            self.editor.textChanged.disconnect(self.editor.check_spelling)

    def toggle_word_wrap(self, checked):
        self.editor.setLineWrapMode(QPlainTextEdit.WidgetWidth if checked else QPlainTextEdit.NoWrap)

    def insert_emoji(self):
        self.emoji_picker = EmojiPicker(self)
        self.emoji_picker.exec_()

    def show_table_editor(self):
        table_editor = TableEditorDialog(self)
        table_editor.exec_()

    def insert_progress(self):
        dialog = ProgressDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            progress_value = dialog.get_progress_value()
            progress_markdown = f"![](https://geps.dev/progress/{progress_value})"
            self.editor.insertPlainText(progress_markdown)

    def open_settings_window(self):
        settings_dialog = SettingsWindow(self.settings_file, self)
        if settings_dialog.exec_() == QDialog.Accepted:
            self.apply_settings()

    def acceptNavigationRequest(self, url, _, __):
        # Open hyperlinks in the default web browser
        if url.scheme() in ["http", "https"]:
            QDesktopServices.openUrl(url)
            return False
        return True

    def export_to_pdf(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(self, "Export as PDF", "", "PDF Files (*.pdf);;All Files (*)", options=options)
        if file_name:
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(file_name)
            self.preview.page().print(printer)

    def export_to_html(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(self, "Export as HTML", "", "HTML Files (*.html);;All Files (*)", options=options)
        if file_name:
            with open(file_name, 'w') as file:
                self.preview.page().toHtml(lambda content: file.write(content))

    def generate_toc(self):
        # Generate a table of contents based on the headings in the Markdown document
        raw_markdown = self.editor.toPlainText()
        lines = raw_markdown.splitlines()
        toc = []

        for line in lines:
            if line.startswith("#"):
                level = line.count('#')
                title = line.replace('#', '').strip()
                anchor = title.lower().replace(' ', '-').replace('.', '')
                toc.append(f'{" " * (level - 1) * 2}- [{title}](#{anchor})')

        toc_markdown = "\n".join(toc)
        self.editor.insertPlainText("\n\n" + toc_markdown + "\n\n")

    def toggle_theme(self):
        if self.dark_mode:
            self.set_light_theme()
        else:
            self.set_dark_theme()
        self.dark_mode = not self.dark_mode
        self.update_toolbar_icons()  # Update toolbar icons when theme is toggled
        self.update_preview()  # Update preview pane when theme is toggled

    def set_light_theme(self):
        light_palette = QPalette()
        light_palette.setColor(QPalette.Window, Qt.white)
        light_palette.setColor(QPalette.WindowText, Qt.black)
        light_palette.setColor(QPalette.Base, Qt.white)
        light_palette.setColor(QPalette.AlternateBase, Qt.lightGray)
        light_palette.setColor(QPalette.ToolTipBase, Qt.white)
        light_palette.setColor(QPalette.ToolTipText, Qt.black)
        light_palette.setColor(QPalette.Text, Qt.black)
        light_palette.setColor(QPalette.Button, Qt.lightGray)
        light_palette.setColor(QPalette.ButtonText, Qt.black)
        light_palette.setColor(QPalette.BrightText, Qt.red)
        light_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        light_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        light_palette.setColor(QPalette.HighlightedText, Qt.white)
        self.setPalette(light_palette)

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
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, Qt.black)
        self.setPalette(dark_palette)

    def auto_save(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.save_snapshot)
        self.timer.start(60000)  # Auto-save every 60 seconds

    def save_snapshot(self):
        if not self.current_file:
            self.status_bar.showMessage("No file is currently open to create a snapshot.", 3000)
            return

        snapshots_dir = os.path.join(os.path.dirname(self.current_file), "snapshots")
        if not os.path.exists(snapshots_dir):
            os.makedirs(snapshots_dir)

        snapshot_name = os.path.join(snapshots_dir, f"{os.path.basename(self.current_file)}_{time.strftime('%Y%m%d%H%M%S')}.md")
        with open(snapshot_name, 'w') as file:
            file.write(self.editor.toPlainText())

        self.status_bar.showMessage(f"Snapshot saved as {snapshot_name}", 3000)

    def show_about_dialog(self):
        about_dialog = AboutDialog(self)
        about_dialog.exec_()

    def show_version_control(self):
        if not self.current_file:
            QMessageBox.warning(self, "Error", "No file is currently open to manage versions.")
            return

        snapshots_dir = os.path.join(os.path.dirname(self.current_file), "snapshots")
        if not os.path.exists(snapshots_dir):
            QMessageBox.warning(self, "No Snapshots", "No snapshots are available for this file.")
            return

        snapshots = [f for f in os.listdir(snapshots_dir) if f.endswith('.md')]

        dialog = QDialog(self)
        dialog.setWindowTitle("Version Control")
        dialog.setGeometry(100, 100, 600, 400)

        layout = QVBoxLayout(dialog)

        list_widget = QListWidget(dialog)
        list_widget.addItems(snapshots)
        layout.addWidget(list_widget)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Help, dialog)
        layout.addWidget(button_box)

        def on_ok():
            selected_snapshot = list_widget.currentItem().text()
            with open(os.path.join(snapshots_dir, selected_snapshot), 'r') as file:
                self.editor.setPlainText(file.read())
            dialog.accept()

        def on_compare():
            selected_snapshot = list_widget.currentItem().text()
            with open(os.path.join(snapshots_dir, selected_snapshot), 'r') as file:
                snapshot_text = file.read()

            current_text = self.editor.toPlainText()
            diff = difflib.unified_diff(
                current_text.splitlines(keepends=True),
                snapshot_text.splitlines(keepends=True),
                lineterm='',
                fromfile='Current Version',
                tofile=selected_snapshot
            )

            diff_output = ''.join(diff)

            diff_dialog = QDialog(self)
            diff_dialog.setWindowTitle(f"Comparison with {selected_snapshot}")
            diff_dialog.setGeometry(150, 150, 800, 600)

            diff_layout = QVBoxLayout(diff_dialog)
            diff_text = QTextEdit(diff_dialog)
            diff_text.setPlainText(diff_output)
            diff_text.setReadOnly(True)
            diff_layout.addWidget(diff_text)

            diff_dialog.exec_()

        def on_delete():
            selected_snapshot = list_widget.currentItem().text()
            confirm = QMessageBox.question(self, "Delete Snapshot", f"Are you sure you want to delete {selected_snapshot}?", QMessageBox.Yes | QMessageBox.No)
            if confirm == QMessageBox.Yes:
                os.remove(os.path.join(snapshots_dir, selected_snapshot))
                list_widget.takeItem(list_widget.currentRow())

        def on_help():
            QMessageBox.information(self, "Help", "To use version control, select a snapshot and click OK to revert to it, or use Compare to see differences.")

        button_box.accepted.connect(on_ok)
        button_box.rejected.connect(dialog.reject)

        compare_button = QPushButton("Compare", dialog)
        compare_button.clicked.connect(on_compare)
        button_box.addButton(compare_button, QDialogButtonBox.ActionRole)

        delete_button = QPushButton("Delete", dialog)
        delete_button.clicked.connect(on_delete)
        button_box.addButton(delete_button, QDialogButtonBox.ActionRole)

        help_button = QPushButton("Help", dialog)
        help_button.clicked.connect(on_help)
        button_box.addButton(help_button, QDialogButtonBox.HelpRole)

        dialog.exec_()

    def find_replace(self):
        find_replace_dialog = QInputDialog.getText(self, 'Find and Replace', 'Enter text to find:')
        if find_replace_dialog[1]:
            find_text = find_replace_dialog[0]
            replace_text, ok = QInputDialog.getText(self, 'Replace With', f'Replace "{find_text}" with:')
            if ok:
                text = self.editor.toPlainText()
                updated_text = text.replace(find_text, replace_text)
                self.editor.setPlainText(updated_text)

    def show_terminal(self):
        self.terminal = QDialog(self)
        self.terminal.setWindowTitle("Terminal")
        self.terminal.setGeometry(100, 100, 800, 400)
        self.terminal_layout = QVBoxLayout()
        self.terminal.setLayout(self.terminal_layout)

        self.output = QTextEdit(self.terminal)
        self.output.setReadOnly(True)
        self.output.setStyleSheet("background-color: black; color: white; font-family: Consolas, monospace;")
        self.terminal_layout.addWidget(self.output)

        self.command_input = QLineEdit(self.terminal)
        self.command_input.setPlaceholderText("Enter command...")
        self.command_input.returnPressed.connect(self.run_command)
        self.terminal_layout.addWidget(self.command_input)

        self.clear_button = QPushButton("Clear", self.terminal)
        self.clear_button.clicked.connect(self.clear_terminal)
        self.terminal_layout.addWidget(self.clear_button)

        self.terminal.show()

    def run_command(self):
        command = self.command_input.text()
        if command:
            try:
                output = subprocess.check_output(command, shell=True, text=True, stderr=subprocess.STDOUT)
                self.output.append(f"> {command}\n{output}")
            except subprocess.CalledProcessError as e:
                self.output.append(f"> {command}\nError: {e.output}")
            self.command_input.clear()

    def clear_terminal(self):
        self.output.clear()

    def save_file(self):
        if self.current_file:
            file_name = self.current_file
        else:
            options = QFileDialog.Options()
            file_name, _ = QFileDialog.getSaveFileName(self, "Save Markdown File", "", "Markdown Files (*.md);;All Files (*)", options=options)
            if not file_name:
                return

        try:
            with open(file_name, 'w') as file:
                file.write(self.editor.toPlainText())
            self.current_file = file_name
            self.setWindowTitle(f"{os.path.basename(self.current_file)} - Markiva")
            self.editor.document().setModified(False)  # Reset modified status
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not save file: {str(e)}")

    def restore_window_state(self):
        """Restore the state of the window, including toolbar positions."""
        window_state = self.settings.get("window_state")
        if window_state:
            self.restoreState(bytes.fromhex(window_state))

    def save_window_state(self):
        """Save the state of the window, including toolbar positions."""
        self.settings["window_state"] = self.saveState().toHex().data().decode()
        self.save_settings()

    def closeEvent(self, event):
        if self.editor.document().isModified():
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save before exiting?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Cancel
            )
            if reply == QMessageBox.Yes:
                self.save_file()
            elif reply == QMessageBox.Cancel:
                event.ignore()
                return
        self.save_window_state()
        event.accept()

    def open_file(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Markdown File", "", "Markdown Files (*.md);;All Files (*)", options=options)
        if file_name:
            self.open_file_by_path(file_name)

    def set_default_project_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Default Project Folder")
        if folder:
            self.settings["default_project_folder"] = folder
            self.file_model.setRootPath(folder)
            self.tree.setRootIndex(self.file_model.index(folder))
            self.save_settings()

    def save_as_template(self):
        template_name, ok = QInputDialog.getText(self, "Save as Template", "Template name:")
        if ok and template_name:
            templates_dir = "templates"
            if not os.path.exists(templates_dir):
                os.makedirs(templates_dir)
            template_path = os.path.join(templates_dir, f"{template_name}.md")
            with open(template_path, 'w', encoding='utf-8') as file:
                file.write(self.editor.toPlainText())
            QMessageBox.information(self, "Template Saved", f"Template '{template_name}' saved successfully.")

    def load_template(self):
        templates_dir = "templates"
        if not os.path.exists(templates_dir):
            QMessageBox.warning(self, "No Templates", "No templates found. Please save a template first.")
            return
        dialog = TemplateDialog(templates_dir, self)
        dialog.exec_()

    def insert_link(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Insert Link")

        layout = QVBoxLayout(dialog)

        # Input fields
        text_label = QLabel("Text:", dialog)
        layout.addWidget(text_label)
        text_input = QLineEdit(dialog)
        layout.addWidget(text_input)

        url_label = QLabel("URL:", dialog)
        layout.addWidget(url_label)
        url_input = QLineEdit(dialog)
        layout.addWidget(url_input)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dialog)
        layout.addWidget(button_box)

        def on_ok():
            text = text_input.text()
            url = url_input.text()
            if text and url:
                self.editor.insertPlainText(f"[{text}]({url})")
            dialog.accept()

        button_box.accepted.connect(on_ok)
        button_box.rejected.connect(dialog.reject)

        dialog.exec_()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create('Fusion'))

    # Apply a dark palette to the entire app for a consistent look
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

    window = MarkdownEditor()
    window.show()
    sys.exit(app.exec_())
