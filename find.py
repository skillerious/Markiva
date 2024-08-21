from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QDialogButtonBox, QMessageBox, QCheckBox, QProgressBar, QTextEdit, QGroupBox, QSpacerItem, QSizePolicy
)
from PyQt5.QtGui import QTextCursor, QIcon, QTextCharFormat, QColor, QCloseEvent, QTextDocument
from PyQt5.QtCore import Qt, QRegularExpression

class FindWindow(QDialog):
    def __init__(self, editor: QTextEdit, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.setWindowTitle("Find and Replace")
        self.setFixedSize(600, 350)
        self.setWindowIcon(QIcon("icon/find_replace.png"))

        layout = QVBoxLayout(self)

        find_replace_group = QGroupBox("Find and Replace")
        find_replace_layout = QVBoxLayout(find_replace_group)

        find_layout = QHBoxLayout()
        self.find_label = QLabel("Find:")
        self.find_input = QLineEdit()
        find_layout.addWidget(self.find_label)
        find_layout.addWidget(self.find_input)
        find_replace_layout.addLayout(find_layout)

        replace_layout = QHBoxLayout()
        self.replace_label = QLabel("Replace:")
        self.replace_input = QLineEdit()
        replace_layout.addWidget(self.replace_label)
        replace_layout.addWidget(self.replace_input)
        find_replace_layout.addLayout(replace_layout)

        layout.addWidget(find_replace_group)

        self.find_input.setMinimumWidth(400)
        self.replace_input.setMinimumWidth(400)

        options_group = QGroupBox("Options")
        options_layout = QHBoxLayout(options_group)
        self.case_sensitive_checkbox = QCheckBox("Match Case")
        self.whole_word_checkbox = QCheckBox("Whole Word")
        self.regex_checkbox = QCheckBox("Use Regular Expression")
        options_layout.addWidget(self.case_sensitive_checkbox)
        options_layout.addWidget(self.whole_word_checkbox)
        options_layout.addWidget(self.regex_checkbox)
        layout.addWidget(options_group)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        buttons_layout = QHBoxLayout()
        self.find_next_button = QPushButton("Find Next")
        self.find_next_button.clicked.connect(self.find_next)
        buttons_layout.addWidget(self.find_next_button)

        self.replace_button = QPushButton("Replace")
        self.replace_button.setToolTip("Preview Replacement")
        self.replace_button.setToolTipDuration(5000)
        self.replace_button.clicked.connect(self.preview_replace)
        buttons_layout.addWidget(self.replace_button)

        self.replace_all_button = QPushButton("Replace All")
        self.replace_all_button.clicked.connect(self.replace_all)
        buttons_layout.addWidget(self.replace_all_button)

        self.find_all_button = QPushButton("Find All")
        self.find_all_button.clicked.connect(self.find_all)
        buttons_layout.addWidget(self.find_all_button)

        self.select_all_button = QPushButton("Select All Matches")
        self.select_all_button.clicked.connect(self.select_all_matches)
        buttons_layout.addWidget(self.select_all_button)

        buttons_layout.addSpacerItem(QSpacerItem(20, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))
        layout.addLayout(buttons_layout)

        self.count_label = QLabel("Matches found: 0")
        self.count_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.count_label)

        navigation_layout = QHBoxLayout()
        self.prev_button = QPushButton("Find Previous")
        self.prev_button.clicked.connect(self.find_previous)
        navigation_layout.addWidget(self.prev_button)

        self.next_button = QPushButton("Find Next")
        self.next_button.clicked.connect(self.find_next)
        navigation_layout.addWidget(self.next_button)

        layout.addLayout(navigation_layout)

        dialog_buttons = QDialogButtonBox(QDialogButtonBox.Close)
        dialog_buttons.rejected.connect(self.reject)
        layout.addWidget(dialog_buttons)

        self.matches = []
        self.current_match_index = -1

    def find_next(self):
        if not self.matches:
            self.find_all()

        if not self.matches:
            QMessageBox.information(self, "No Matches", "No matches found.")
            return

        self.current_match_index += 1
        if self.current_match_index >= len(self.matches):
            self.current_match_index = 0

        match = self.matches[self.current_match_index]
        cursor = self.editor.textCursor()
        cursor.setPosition(match[0])
        cursor.setPosition(match[1], QTextCursor.KeepAnchor)
        self.editor.setTextCursor(cursor)
        self.update_match_counter()

    def find_previous(self):
        if not self.matches:
            self.find_all()

        if not self.matches:
            QMessageBox.information(self, "No Matches", "No matches found.")
            return

        self.current_match_index -= 1
        if self.current_match_index < 0:
            self.current_match_index = len(self.matches) - 1

        match = self.matches[self.current_match_index]
        cursor = self.editor.textCursor()
        cursor.setPosition(match[0])
        cursor.setPosition(match[1], QTextCursor.KeepAnchor)
        self.editor.setTextCursor(cursor)
        self.update_match_counter()

    def update_match_counter(self):
        self.count_label.setText(f"Match {self.current_match_index + 1} of {len(self.matches)}")

    def find_all(self):
        self.clear_highlights()

        find_text = self.find_input.text()
        if not find_text:
            QMessageBox.warning(self, "Warning", "Please enter a search term.")
            return

        case_sensitive = self.case_sensitive_checkbox.isChecked()
        whole_word = self.whole_word_checkbox.isChecked()
        use_regex = self.regex_checkbox.isChecked()

        flags = QTextDocument.FindFlags()
        if case_sensitive:
            flags |= QTextDocument.FindCaseSensitively
        if whole_word:
            find_text = f"\\b{find_text}\\b"

        if use_regex:
            expression = QRegularExpression(find_text)
            if not expression.isValid():
                QMessageBox.warning(self, "Error", f"The search pattern is not valid: {expression.errorString()}")
                return
        else:
            expression = QRegularExpression(QRegularExpression.escape(find_text))

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        document = self.editor.document()
        cursor = QTextCursor(document)
        self.matches = []

        total_length = document.characterCount()

        while True:
            cursor = document.find(expression, cursor, flags)
            if cursor.isNull():
                break
            self.matches.append((cursor.selectionStart(), cursor.selectionEnd()))
            self.highlight_match(cursor)
            progress = int((cursor.position() / total_length) * 100)
            self.progress_bar.setValue(progress)

        self.progress_bar.setVisible(False)
        self.count_label.setText(f"Matches found: {len(self.matches)}")
        self.current_match_index = -1
        if self.matches:
            self.find_next()
        else:
            QMessageBox.information(self, "No Matches", "No matches found.")

    def highlight_match(self, cursor):
        fmt = QTextCharFormat()
        fmt.setBackground(QColor("yellow"))
        cursor.setCharFormat(fmt)

    def clear_highlights(self):
        cursor = QTextCursor(self.editor.document())
        cursor.select(QTextCursor.Document)
        fmt = QTextCharFormat()
        fmt.setBackground(QColor(Qt.transparent))
        cursor.setCharFormat(fmt)

    def preview_replace(self):
        if self.current_match_index == -1:
            self.find_next()

        if self.current_match_index >= 0 and self.current_match_index < len(self.matches):
            cursor = self.editor.textCursor()
            cursor.setPosition(self.matches[self.current_match_index][0])
            cursor.setPosition(self.matches[self.current_match_index][1], QTextCursor.KeepAnchor)
            replacement_preview = f"<u><b>{self.replace_input.text()}</b></u>"
            cursor.insertHtml(replacement_preview)

    def replace(self):
        if self.current_match_index == -1:
            self.find_next()

        if self.current_match_index >= 0 and self.current_match_index < len(self.matches):
            cursor = self.editor.textCursor()
            cursor.setPosition(self.matches[self.current_match_index][0])
            cursor.setPosition(self.matches[self.current_match_index][1], QTextCursor.KeepAnchor)
            cursor.insertText(self.replace_input.text())

            self.matches.pop(self.current_match_index)
            self.current_match_index -= 1
            self.find_next()

    def select_all_matches(self):
        if not self.matches:
            self.find_all()

        cursor = self.editor.textCursor()
        cursor.beginEditBlock()
        for start, end in self.matches:
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.KeepAnchor)
            cursor.mergeCharFormat(self.get_highlight_format())
        cursor.endEditBlock()

    def get_highlight_format(self):
        fmt = QTextCharFormat()
        fmt.setBackground(QColor("yellow"))
        fmt.setForeground(QColor("black"))
        return fmt

    def replace_all(self):
        find_text = self.find_input.text()
        replace_text = self.replace_input.text()

        if not find_text:
            QMessageBox.warning(self, "Warning", "Please enter a search term.")
            return

        case_sensitive = self.case_sensitive_checkbox.isChecked()
        whole_word = self.whole_word_checkbox.isChecked()
        use_regex = self.regex_checkbox.isChecked()

        flags = QTextDocument.FindFlags()
        if case_sensitive:
            flags |= QTextDocument.FindCaseSensitively
        if whole_word:
            find_text = f"\\b{find_text}\\b"

        if use_regex:
            expression = QRegularExpression(find_text)
            if not expression.isValid():
                QMessageBox.warning(self, "Error", f"The search pattern is not valid: {expression.errorString()}")
                return
        else:
            expression = QRegularExpression(QRegularExpression.escape(find_text))

        document = self.editor.document()
        cursor = QTextCursor(document)
        replace_count = 0

        while True:
            cursor = document.find(expression, cursor, flags)
            if cursor.isNull():
                break

            cursor.insertText(replace_text)
            replace_count += 1

        self.count_label.setText(f"Replaced: {replace_count} occurrences")
        if replace_count == 0:
            QMessageBox.information(self, "Replace All", "No matches found to replace.")
        else:
            QMessageBox.information(self, "Replace All", f"Replaced {replace_count} occurrences.")

    def closeEvent(self, event):
        self.clear_highlights()
        super().closeEvent(event)
