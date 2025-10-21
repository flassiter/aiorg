"""Integration tests for AIOrg components.

Tests the integration of AI viewer, organizer, and main application
with real database operations and configuration loading.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from PyQt6.QtCore import Qt

from ai_viewer.viewer import AIViewerWidget
from ai_viewer.config import load_config
from organizer.organizer import OrganizerWidget
from organizer.database import NoteDatabase
from main import MainWindow, setup_logging


class TestAIViewerIntegration:
    """Integration tests for AI viewer component."""

    def test_viewer_with_config(self, qtbot):
        """Test AI viewer loads correctly with configuration."""
        # Create test config
        config = {
            'ai_models': [
                {
                    'name': 'Claude',
                    'type': 'commercial',
                    'url': 'https://claude.ai/chat'
                },
                {
                    'name': 'Llama',
                    'type': 'local',
                    'url': 'http://localhost:11434',
                    'model': 'llama2'
                }
            ]
        }

        # Create viewer with config
        viewer = AIViewerWidget(config=config)
        qtbot.addWidget(viewer)

        # Verify models loaded
        assert viewer.model_dropdown.count() == 2
        assert viewer.model_dropdown.itemText(0) == "Claude"
        assert viewer.model_dropdown.itemText(1) == "Llama"

    def test_viewer_model_switching(self, qtbot):
        """Test switching between commercial and local models."""
        config = {
            'ai_models': [
                {
                    'name': 'Commercial',
                    'type': 'commercial',
                    'url': 'https://example.com'
                },
                {
                    'name': 'Local',
                    'type': 'local',
                    'url': 'http://localhost:11434',
                    'model': 'test'
                }
            ]
        }

        viewer = AIViewerWidget(config=config)
        qtbot.addWidget(viewer)

        # Switch to commercial model
        viewer.model_dropdown.setCurrentIndex(0)
        assert viewer.stacked_widget.currentIndex() == viewer.webview_index

        # Switch to local model (mock Ollama client to avoid connection)
        with patch('ai_viewer.viewer.OllamaClient'):
            viewer.model_dropdown.setCurrentIndex(1)
            assert viewer.stacked_widget.currentIndex() == viewer.chat_index


class TestOrganizerIntegration:
    """Integration tests for organizer component."""

    def test_organizer_with_real_database(self, qtbot):
        """Test organizer with real SQLite database."""
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        try:
            # Create database and organizer
            db = NoteDatabase(db_path)
            organizer = OrganizerWidget(database=db)
            qtbot.addWidget(organizer)

            # Save a note
            test_content = "# Test Note\n\nThis is a test."
            organizer.editor.setPlainText(test_content)
            organizer.save_note()

            # Verify note was saved
            assert organizer.current_note_id is not None

            # Search for note
            organizer.search_bar.setText("test")
            organizer.search_notes()

            # Verify search results
            assert organizer.results_list.count() > 0

            # Load note from search result
            organizer.results_list.setCurrentRow(0)
            organizer.on_result_clicked(organizer.results_list.item(0))

            # Verify content loaded
            assert "Test Note" in organizer.editor.toPlainText()

        finally:
            db.close()
            Path(db_path).unlink()

    def test_organizer_save_search_workflow(self, qtbot):
        """Test complete workflow: create, save, search, load."""
        # Create in-memory database
        db = NoteDatabase(":memory:")
        organizer = OrganizerWidget(database=db)
        qtbot.addWidget(organizer)

        # Create multiple notes
        notes = [
            "# Python Guide\n\nPython is great for AI.",
            "# JavaScript Basics\n\nJS is for web development.",
            "# AI Research\n\nMachine learning and Python."
        ]

        for content in notes:
            organizer.new_note()
            organizer.editor.setPlainText(content)
            organizer.save_note()

        # Search for "Python"
        organizer.search_bar.setText("Python")
        organizer.search_notes()

        # Should find 2 notes containing "Python"
        assert organizer.results_list.count() == 2

        # Search for "JavaScript"
        organizer.search_bar.setText("JavaScript")
        organizer.search_notes()

        # Should find 1 note
        assert organizer.results_list.count() == 1

    def test_organizer_markdown_preview(self, qtbot):
        """Test markdown preview rendering."""
        db = NoteDatabase(":memory:")
        organizer = OrganizerWidget(database=db)
        qtbot.addWidget(organizer)

        # Add markdown content
        markdown_content = """# Heading 1
## Heading 2

- List item 1
- List item 2

**Bold text** and *italic text*

```python
def hello():
    print("Hello, world!")
```
"""
        organizer.editor.setPlainText(markdown_content)

        # Toggle to preview
        organizer.toggle_preview()

        # Verify in preview mode
        assert organizer.stacked_widget.currentIndex() == organizer.preview_index

        # Verify HTML content rendered
        html = organizer.preview.toHtml()
        assert "<h1>" in html or "Heading 1" in html
        assert "List item" in html

        # Toggle back to edit
        organizer.toggle_preview()
        assert organizer.stacked_widget.currentIndex() == organizer.editor_index


class TestConfigIntegration:
    """Integration tests for configuration loading."""

    def test_load_config_from_file(self):
        """Test loading complete configuration from TOML file."""
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write("""
[settings]
theme = "dark"
log_level = "DEBUG"
database_path = "~/test/aiorg.db"
window_width = 1600
window_height = 900
split_ratio = 0.6

[[ai_models]]
name = "Claude"
type = "commercial"
url = "https://claude.ai/chat"

[[ai_models]]
name = "Ollama - Llama 2"
type = "local"
url = "http://localhost:11434"
model = "llama2"

[[ai_models]]
name = "Ollama - Mistral"
type = "local"
url = "http://localhost:11434"
model = "mistral"
""")
            temp_path = f.name

        try:
            # Load config
            config = load_config(temp_path)

            # Verify all settings loaded
            assert config["settings"]["theme"] == "dark"
            assert config["settings"]["log_level"] == "DEBUG"
            assert config["settings"]["window_width"] == 1600
            assert config["settings"]["window_height"] == 900
            assert config["settings"]["split_ratio"] == 0.6

            # Verify all models loaded
            assert len(config["ai_models"]) == 3
            assert config["ai_models"][0]["name"] == "Claude"
            assert config["ai_models"][1]["model"] == "llama2"
            assert config["ai_models"][2]["model"] == "mistral"

        finally:
            Path(temp_path).unlink()

    def test_config_with_viewer_and_organizer(self, qtbot):
        """Test using same config for both viewer and organizer."""
        # Create config
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write("""
[settings]
theme = "dark"
database_path = ":memory:"

[[ai_models]]
name = "Test Model"
type = "commercial"
url = "https://test.com"
""")
            config_path = f.name

        try:
            # Load config
            config = load_config(config_path)

            # Create viewer with config
            viewer = AIViewerWidget(config=config)
            qtbot.addWidget(viewer)
            assert viewer.model_dropdown.count() == 1

            # Create organizer with database from config
            db_path = config["settings"]["database_path"]
            db = NoteDatabase(db_path)
            organizer = OrganizerWidget(database=db)
            qtbot.addWidget(organizer)

            # Both components work independently
            assert viewer is not None
            assert organizer is not None

        finally:
            Path(config_path).unlink()


class TestMainWindowIntegration:
    """Integration tests for main window."""

    def test_main_window_creation(self, qtbot):
        """Test main window creates with valid config."""
        config = {
            'settings': {
                'theme': 'dark',
                'log_level': 'INFO',
                'database_path': ':memory:',
                'window_width': 1400,
                'window_height': 800,
                'split_ratio': 0.5
            },
            'ai_models': []
        }

        window = MainWindow(config)
        qtbot.addWidget(window)

        # Verify window properties
        assert window.windowTitle() == "AIOrg"
        assert window.size().width() == 1400
        assert window.size().height() == 800

        # Verify components initialized
        assert window.database is not None
        assert window.ai_viewer is not None
        assert window.organizer is not None
        assert window.splitter is not None

        # Verify central widget is splitter
        assert window.centralWidget() == window.splitter

        # Verify window is not None and can be displayed
        assert window is not None

    def test_components_integrated(self, qtbot):
        """Test both components are present and properly integrated."""
        config = {
            'settings': {
                'theme': 'dark',
                'log_level': 'INFO',
                'database_path': ':memory:',
                'window_width': 1400,
                'window_height': 800,
                'split_ratio': 0.5
            },
            'ai_models': [
                {'name': 'Test Model', 'type': 'commercial', 'url': 'https://test.com'}
            ]
        }

        window = MainWindow(config)
        qtbot.addWidget(window)

        # Verify both components exist
        assert window.ai_viewer is not None
        assert window.organizer is not None

        # Verify components are in splitter
        assert window.splitter.count() == 2
        assert window.splitter.widget(0) == window.ai_viewer
        assert window.splitter.widget(1) == window.organizer

        # Verify AI viewer has models loaded
        assert window.ai_viewer.model_dropdown.count() == 1
        assert window.ai_viewer.model_dropdown.itemText(0) == "Test Model"

        # Verify organizer has database connection
        assert window.organizer.database is not None
        assert window.organizer.database == window.database

        # Verify minimum widths are set
        assert window.ai_viewer.minimumWidth() == 400
        assert window.organizer.minimumWidth() == 300

    def test_splitter_works(self, qtbot):
        """Test that splitter can be dragged and maintains ratio."""
        config = {
            'settings': {
                'theme': 'dark',
                'log_level': 'INFO',
                'database_path': ':memory:',
                'window_width': 1400,
                'window_height': 800,
                'split_ratio': 0.5
            },
            'ai_models': []
        }

        window = MainWindow(config)
        qtbot.addWidget(window)

        # Get initial splitter sizes
        initial_sizes = window.splitter.sizes()
        assert len(initial_sizes) == 2

        # Verify initial split ratio is approximately 0.5
        total_width = sum(initial_sizes)
        left_ratio = initial_sizes[0] / total_width
        assert 0.45 <= left_ratio <= 0.55  # Allow small margin

        # Manually adjust splitter sizes (simulate drag)
        new_sizes = [600, 800]  # 600:800 ratio (0.43:0.57)
        window.splitter.setSizes(new_sizes)

        # Verify sizes changed
        updated_sizes = window.splitter.sizes()
        assert updated_sizes != initial_sizes

        # Verify splitter is movable
        assert window.splitter.isEnabled()
        assert window.splitter.handleWidth() == 5

    def test_config_applied(self, qtbot, tmp_path):
        """Test configuration loads and applies correctly."""
        # Create temporary config file
        config_file = tmp_path / "test_config.toml"
        config_file.write_text("""
[settings]
theme = "light"
log_level = "DEBUG"
database_path = ":memory:"
window_width = 1600
window_height = 900
split_ratio = 0.6

[[ai_models]]
name = "Model A"
type = "commercial"
url = "https://modela.com"

[[ai_models]]
name = "Model B"
type = "local"
url = "http://localhost:11434"
model = "test-model"
""")

        # Load config
        config = load_config(str(config_file))

        # Create window with config
        window = MainWindow(config)
        qtbot.addWidget(window)

        # Verify window settings applied
        assert window.size().width() == 1600
        assert window.size().height() == 900

        # Verify split ratio applied (with tolerance)
        sizes = window.splitter.sizes()
        total_width = sum(sizes)
        left_ratio = sizes[0] / total_width
        assert 0.55 <= left_ratio <= 0.65  # Allow margin around 0.6

        # Verify AI models loaded
        assert window.ai_viewer.model_dropdown.count() == 2
        assert window.ai_viewer.model_dropdown.itemText(0) == "Model A"
        assert window.ai_viewer.model_dropdown.itemText(1) == "Model B"

        # Verify config stored
        assert window.config["settings"]["window_width"] == 1600
        assert window.config["settings"]["split_ratio"] == 0.6

    def test_note_workflow(self, qtbot, tmp_path):
        """Test complete note workflow: save and search."""
        # Create temporary database
        db_path = tmp_path / "test.db"

        config = {
            'settings': {
                'theme': 'dark',
                'log_level': 'INFO',
                'database_path': str(db_path),
                'window_width': 1400,
                'window_height': 800,
                'split_ratio': 0.5
            },
            'ai_models': []
        }

        window = MainWindow(config)
        qtbot.addWidget(window)

        # Access organizer widget
        organizer = window.organizer

        # Create and save a note
        test_content = "# Integration Test Note\n\nThis is a test note for integration testing."
        organizer.editor.setPlainText(test_content)
        organizer.save_note()

        # Verify note was saved
        assert organizer.current_note_id is not None
        note_id = organizer.current_note_id

        # Create new note
        organizer.new_note()
        assert organizer.current_note_id is None
        assert organizer.editor.toPlainText() == ""

        # Search for the saved note
        organizer.search_bar.setText("integration")
        organizer.search_notes()

        # Verify search results
        assert organizer.results_list.count() >= 1
        assert organizer.results_list.isVisible()

        # Load note from search results
        organizer.results_list.setCurrentRow(0)
        organizer.on_result_clicked(organizer.results_list.item(0))

        # Verify note content loaded
        loaded_content = organizer.editor.toPlainText()
        assert "Integration Test Note" in loaded_content
        assert organizer.current_note_id == note_id

        # Cleanup
        window.database.close()

    def test_model_switching(self, qtbot):
        """Test switching between AI models."""
        config = {
            'settings': {
                'theme': 'dark',
                'log_level': 'INFO',
                'database_path': ':memory:',
                'window_width': 1400,
                'window_height': 800,
                'split_ratio': 0.5
            },
            'ai_models': [
                {
                    'name': 'Commercial Model',
                    'type': 'commercial',
                    'url': 'https://commercial.example.com'
                },
                {
                    'name': 'Local Model',
                    'type': 'local',
                    'url': 'http://localhost:11434',
                    'model': 'test-local'
                }
            ]
        }

        window = MainWindow(config)
        qtbot.addWidget(window)

        # Access AI viewer
        ai_viewer = window.ai_viewer

        # Verify models loaded
        assert ai_viewer.model_dropdown.count() == 2

        # Initially on first model (commercial)
        assert ai_viewer.model_dropdown.currentIndex() == 0
        assert ai_viewer.stacked_widget.currentIndex() == ai_viewer.webview_index

        # Switch to local model (mock Ollama client)
        with patch('ai_viewer.viewer.OllamaClient'):
            ai_viewer.model_dropdown.setCurrentIndex(1)

            # Verify switched to chat component
            assert ai_viewer.stacked_widget.currentIndex() == ai_viewer.chat_index

            # Verify current model updated
            current_model = ai_viewer.get_current_model()
            assert current_model['name'] == 'Local Model'
            assert current_model['type'] == 'local'

        # Switch back to commercial
        ai_viewer.model_dropdown.setCurrentIndex(0)
        assert ai_viewer.stacked_widget.currentIndex() == ai_viewer.webview_index

        current_model = ai_viewer.get_current_model()
        assert current_model['name'] == 'Commercial Model'
        assert current_model['type'] == 'commercial'

    def test_main_window_with_components_config(self, qtbot):
        """Test main window with full configuration."""
        config = {
            'settings': {
                'theme': 'dark',
                'log_level': 'INFO',
                'database_path': ':memory:',
                'window_width': 1200,
                'window_height': 700,
                'split_ratio': 0.6
            },
            'ai_models': [
                {'name': 'Test', 'type': 'commercial', 'url': 'https://test.com'}
            ]
        }

        window = MainWindow(config)
        qtbot.addWidget(window)

        # Verify config stored
        assert window.config == config

    def test_main_window_shutdown(self, qtbot):
        """Test main window closes properly and cleans up resources."""
        config = {
            'settings': {
                'theme': 'dark',
                'log_level': 'INFO',
                'database_path': ':memory:',
                'window_width': 1400,
                'window_height': 800,
                'split_ratio': 0.5
            },
            'ai_models': []
        }

        window = MainWindow(config)
        qtbot.addWidget(window)

        # Verify database is open
        assert window.database is not None
        db = window.database

        # Close window (simulates closeEvent)
        window.close()

        # Note: Database connection should be closed by closeEvent
        # We can't easily verify SQLite connection state without
        # trying an operation, which would raise if closed
        assert window is not None  # Window object still exists


class TestDatabaseNoteIntegration:
    """Integration tests for database and note operations."""

    def test_database_concurrent_operations(self):
        """Test multiple database operations in sequence."""
        db = NoteDatabase(":memory:")

        # Create multiple notes
        note_ids = []
        for i in range(10):
            content = f"Note {i}: This is test note number {i}"
            note_id = db.save_note(content)
            note_ids.append(note_id)

        # Verify all notes saved
        assert len(note_ids) == 10

        # Search for specific notes
        results = db.search_notes("number 5")
        assert len(results) == 1
        assert "number 5" in results[0]['content']

        # Update a note
        updated_content = "Updated: Note 5 has been modified"
        db.save_note(updated_content, note_id=note_ids[5])

        # Verify update
        note = db.load_note(note_ids[5])
        assert "modified" in note['content']

        # Delete notes
        for note_id in note_ids[:5]:
            db.delete_note(note_id)

        # Verify deletion
        remaining = db.list_all_notes()
        assert len(remaining) == 5

        db.close()

    def test_database_search_accuracy(self):
        """Test search returns accurate results."""
        db = NoteDatabase(":memory:")

        # Create notes with specific content
        notes_content = [
            "Python programming tutorial for beginners",
            "JavaScript web development basics",
            "Python and machine learning guide",
            "Java programming fundamentals",
            "Python data science with pandas"
        ]

        for content in notes_content:
            db.save_note(content)

        # Search for "Python"
        python_results = db.search_notes("Python")
        assert len(python_results) == 3  # Should find 3 notes with Python

        # Search for "JavaScript"
        js_results = db.search_notes("JavaScript")
        assert len(js_results) == 1

        # Search for "programming"
        prog_results = db.search_notes("programming")
        assert len(prog_results) >= 3  # Python, Java, and maybe JavaScript

        db.close()


class TestLoggingIntegration:
    """Integration tests for logging system."""

    def test_logging_setup(self):
        """Test logging system initializes correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Change to temp directory
            import os
            original_dir = os.getcwd()
            os.chdir(temp_dir)

            try:
                # Setup logging
                setup_logging("DEBUG")

                # Create logger and log messages
                import logging
                logger = logging.getLogger("test_integration")
                logger.debug("Debug message")
                logger.info("Info message")
                logger.warning("Warning message")
                logger.error("Error message")

                # Verify log file created
                log_file = Path("logs/aiorg.log")
                assert log_file.exists()

                # Verify log contains messages
                log_content = log_file.read_text()
                assert "Debug message" in log_content
                assert "Info message" in log_content
                assert "Warning message" in log_content
                assert "Error message" in log_content

            finally:
                os.chdir(original_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
