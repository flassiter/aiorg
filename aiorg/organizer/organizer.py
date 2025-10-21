"""
Note organizer widget with editor, preview, and search functionality.

This module provides the main organizer widget that combines markdown editing,
preview rendering, and full-text search capabilities.
"""

import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit,
    QTextBrowser, QLineEdit, QListWidget, QListWidgetItem,
    QStackedWidget, QToolBar, QMessageBox, QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QShortcut, QKeySequence

from organizer.database import NoteDatabase
from organizer.markdown_renderer import render_markdown


logger = logging.getLogger(__name__)


class OrganizerWidget(QWidget):
    """Note organizer with editor, preview, and search."""

    # Signal emitted when a note is saved
    note_saved = pyqtSignal(int)  # note_id

    def __init__(self, database: NoteDatabase, parent=None):
        """
        Initialize organizer widget.

        Args:
            database: NoteDatabase instance for persistence
            parent: Parent widget (optional)
        """
        super().__init__(parent)

        self.database = database
        self.current_note_id: Optional[int] = None
        self.is_preview_mode = False

        logger.info("Initializing OrganizerWidget")

        # Setup UI
        self.setup_ui()

        # Setup keyboard shortcuts
        self.setup_shortcuts()

        logger.info("OrganizerWidget initialized successfully")

    def setup_ui(self):
        """Create UI layout."""
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # Toolbar
        toolbar = self.create_toolbar()
        main_layout.addWidget(toolbar)

        # Stacked widget for editor/preview
        self.stacked_widget = QStackedWidget()

        # Editor (plain text, no rich text)
        self.editor = QTextEdit()
        self.editor.setAcceptRichText(False)
        self.editor.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)

        # Set monospace font
        font = QFont("Courier New", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.editor.setFont(font)

        self.stacked_widget.addWidget(self.editor)

        # Preview (read-only browser)
        self.preview = QTextBrowser()
        self.preview.setReadOnly(True)
        self.preview.setOpenExternalLinks(True)
        self.stacked_widget.addWidget(self.preview)

        main_layout.addWidget(self.stacked_widget, stretch=1)

        # Search section
        search_layout = QHBoxLayout()
        search_layout.setSpacing(5)

        search_label = QLabel("Search:")
        search_layout.addWidget(search_label)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Enter search query...")
        self.search_bar.returnPressed.connect(self.search_notes)
        search_layout.addWidget(self.search_bar)

        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_notes)
        search_layout.addWidget(self.search_button)

        main_layout.addLayout(search_layout)

        # Results list (hidden by default)
        self.results_list = QListWidget()
        self.results_list.itemClicked.connect(self.on_result_clicked)
        self.results_list.setVisible(False)
        main_layout.addWidget(self.results_list)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #888; font-size: 10pt;")
        main_layout.addWidget(self.status_label)

        self.setLayout(main_layout)

        logger.debug("UI layout created")

    def create_toolbar(self) -> QWidget:
        """
        Create toolbar with action buttons.

        Returns:
            QWidget: Toolbar widget
        """
        toolbar_widget = QWidget()
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(5)

        # Save button
        self.save_button = QPushButton("Save")
        self.save_button.setToolTip("Save note (Ctrl+S)")
        self.save_button.clicked.connect(self.save_note)
        toolbar_layout.addWidget(self.save_button)

        # New button
        self.new_button = QPushButton("New")
        self.new_button.setToolTip("Create new note (Ctrl+N)")
        self.new_button.clicked.connect(self.new_note)
        toolbar_layout.addWidget(self.new_button)

        # Preview toggle button
        self.preview_button = QPushButton("Preview")
        self.preview_button.setToolTip("Toggle preview mode (Ctrl+P)")
        self.preview_button.setCheckable(True)
        self.preview_button.clicked.connect(self.toggle_preview)
        toolbar_layout.addWidget(self.preview_button)

        # Add stretch to push buttons to the left
        toolbar_layout.addStretch()

        toolbar_widget.setLayout(toolbar_layout)
        return toolbar_widget

    def setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        # Ctrl+S: Save note
        save_shortcut = QShortcut(QKeySequence.StandardKey.Save, self)
        save_shortcut.activated.connect(self.save_note)

        # Ctrl+N: New note
        new_shortcut = QShortcut(QKeySequence.StandardKey.New, self)
        new_shortcut.activated.connect(self.new_note)

        # Ctrl+P: Toggle preview
        preview_shortcut = QShortcut(QKeySequence("Ctrl+P"), self)
        preview_shortcut.activated.connect(self.toggle_preview)

        # Ctrl+F: Focus search bar
        search_shortcut = QShortcut(QKeySequence.StandardKey.Find, self)
        search_shortcut.activated.connect(self.focus_search)

        logger.debug("Keyboard shortcuts configured")

    def save_note(self):
        """Save current note to database."""
        try:
            # Get content from editor
            content = self.editor.toPlainText()

            if not content.strip():
                logger.warning("Attempted to save empty note")
                self.show_status("Cannot save empty note", error=True)
                return

            # Save to database
            note_id = self.database.save_note(content, self.current_note_id)

            # Update current note ID
            self.current_note_id = note_id

            # Show success feedback
            action = "updated" if note_id == self.current_note_id else "created"
            self.show_status(f"Note {action} successfully (ID: {note_id})")

            # Emit signal
            self.note_saved.emit(note_id)

            logger.info(f"Note saved successfully (ID: {note_id}, {len(content)} chars)")

        except Exception as e:
            logger.error(f"Failed to save note: {e}", exc_info=True)
            self.show_status(f"Error saving note: {str(e)}", error=True)
            QMessageBox.critical(
                self,
                "Save Error",
                f"Failed to save note:\n{str(e)}"
            )

    def load_note(self, note_id: int):
        """
        Load note into editor.

        Args:
            note_id: Note ID to load
        """
        try:
            # Load from database
            note = self.database.load_note(note_id)

            if note is None:
                logger.warning(f"Note ID {note_id} not found")
                self.show_status(f"Note ID {note_id} not found", error=True)
                return

            # Set content in editor
            self.editor.setPlainText(note['content'])

            # Update current note ID
            self.current_note_id = note_id

            # Switch to edit mode if in preview
            if self.is_preview_mode:
                self.toggle_preview()

            # Show success feedback
            created_at = note['created_at'][:19] if note['created_at'] else "Unknown"
            self.show_status(f"Loaded note ID {note_id} (Created: {created_at})")

            logger.info(f"Loaded note ID {note_id} ({len(note['content'])} chars)")

        except Exception as e:
            logger.error(f"Failed to load note {note_id}: {e}", exc_info=True)
            self.show_status(f"Error loading note: {str(e)}", error=True)
            QMessageBox.critical(
                self,
                "Load Error",
                f"Failed to load note:\n{str(e)}"
            )

    def new_note(self):
        """Clear editor for new note."""
        # Clear editor
        self.editor.clear()

        # Reset current note ID
        self.current_note_id = None

        # Switch to edit mode if in preview
        if self.is_preview_mode:
            self.toggle_preview()

        # Clear search results
        self.results_list.clear()
        self.results_list.setVisible(False)
        self.search_bar.clear()

        # Show feedback
        self.show_status("New note ready")

        logger.info("New note created")

    def toggle_preview(self):
        """Switch between edit and preview modes."""
        if self.is_preview_mode:
            # Switch to edit mode
            self.stacked_widget.setCurrentWidget(self.editor)
            self.preview_button.setChecked(False)
            self.is_preview_mode = False
            self.show_status("Edit mode")
            logger.debug("Switched to edit mode")

        else:
            # Switch to preview mode
            content = self.editor.toPlainText()

            if not content.strip():
                logger.debug("Cannot preview empty note")
                self.show_status("Nothing to preview", error=True)
                return

            # Render markdown
            html = render_markdown(content)
            self.preview.setHtml(html)

            # Switch view
            self.stacked_widget.setCurrentWidget(self.preview)
            self.preview_button.setChecked(True)
            self.is_preview_mode = True
            self.show_status("Preview mode")
            logger.debug("Switched to preview mode")

    def search_notes(self):
        """Execute search and display results."""
        query = self.search_bar.text().strip()

        if not query:
            # Hide results if search is empty
            self.results_list.clear()
            self.results_list.setVisible(False)
            self.show_status("")
            return

        try:
            # Execute search
            results = self.database.search_notes(query, limit=50)

            # Clear previous results
            self.results_list.clear()

            if not results:
                self.show_status(f"No results found for '{query}'")
                self.results_list.setVisible(False)
                logger.info(f"Search '{query}' returned no results")
                return

            # Populate results list
            for note in results:
                item = self.create_result_item(note)
                self.results_list.addItem(item)

            # Show results
            self.results_list.setVisible(True)
            self.show_status(f"Found {len(results)} result(s) for '{query}'")

            # Focus first result
            if self.results_list.count() > 0:
                self.results_list.setCurrentRow(0)

            logger.info(f"Search '{query}' returned {len(results)} results")

        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}", exc_info=True)
            self.show_status(f"Search error: {str(e)}", error=True)
            QMessageBox.critical(
                self,
                "Search Error",
                f"Failed to search notes:\n{str(e)}"
            )

    def create_result_item(self, note: dict) -> QListWidgetItem:
        """
        Create list item for search result.

        Args:
            note: Note dictionary from database

        Returns:
            QListWidgetItem: Formatted result item
        """
        # Get first 50 chars of content as preview
        content_preview = note['content'][:50].replace('\n', ' ')
        if len(note['content']) > 50:
            content_preview += "..."

        # Format timestamp
        created_at = note['created_at'][:19] if note['created_at'] else "Unknown"

        # Create display text
        display_text = f"{content_preview}\nCreated: {created_at}"

        # Create item
        item = QListWidgetItem(display_text)

        # Store note ID in item data
        item.setData(Qt.ItemDataRole.UserRole, note['id'])

        return item

    def on_result_clicked(self, item: QListWidgetItem):
        """
        Handle search result click.

        Args:
            item: Clicked list item
        """
        # Get note ID from item data
        note_id = item.data(Qt.ItemDataRole.UserRole)

        if note_id is not None:
            # Load the note
            self.load_note(note_id)

    def focus_search(self):
        """Focus search bar (Ctrl+F shortcut)."""
        self.search_bar.setFocus()
        self.search_bar.selectAll()
        logger.debug("Search bar focused")

    def show_status(self, message: str, error: bool = False):
        """
        Show status message.

        Args:
            message: Status message to display
            error: Whether this is an error message
        """
        if error:
            self.status_label.setStyleSheet("color: #ff6b6b; font-size: 10pt;")
        else:
            self.status_label.setStyleSheet("color: #51cf66; font-size: 10pt;")

        self.status_label.setText(message)

    def get_current_content(self) -> str:
        """
        Get current editor content.

        Returns:
            str: Current text in editor
        """
        return self.editor.toPlainText()

    def set_content(self, content: str):
        """
        Set editor content.

        Args:
            content: Text to set in editor
        """
        self.editor.setPlainText(content)
        self.current_note_id = None


if __name__ == "__main__":
    """Standalone test for OrganizerWidget."""
    import sys
    from PyQt6.QtWidgets import QApplication

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger.info("Starting OrganizerWidget standalone test")

    # Create application
    app = QApplication(sys.argv)

    # Create test database (in-memory)
    db = NoteDatabase(":memory:")

    # Add some test notes
    db.save_note("# Test Note 1\n\nThis is a **test** note with markdown.")
    db.save_note("# Python Tutorial\n\nHere's some Python code:\n\n```python\ndef hello():\n    print('Hello!')\n```")
    db.save_note("# Shopping List\n\n- Milk\n- Eggs\n- Bread\n- Coffee")

    logger.info("Test database populated with 3 notes")

    # Create widget
    widget = OrganizerWidget(database=db)
    widget.setWindowTitle("Organizer Widget - Standalone Test")
    widget.resize(800, 600)
    widget.show()

    logger.info("OrganizerWidget window displayed")

    # Run application
    exit_code = app.exec()

    # Cleanup
    db.close()

    logger.info(f"Application exited with code {exit_code}")
    sys.exit(exit_code)
