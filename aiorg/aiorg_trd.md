# AIOrg - Technical Requirements Document (TRD)

## 1. Architecture Overview

### 1.1 High-Level Architecture
```
┌─────────────────────────────────────────────────────┐
│                   Main Window                        │
│                  (QMainWindow)                       │
│  ┌───────────────────────┬──────────────────────┐  │
│  │   AI Viewer Widget    │  Organizer Widget    │  │
│  │    (QWidget)          │    (QWidget)         │  │
│  │  ┌────────────────┐   │  ┌────────────────┐ │  │
│  │  │   Dropdown     │   │  │   Toolbar      │ │  │
│  │  └────────────────┘   │  └────────────────┘ │  │
│  │  ┌────────────────┐   │  ┌────────────────┐ │  │
│  │  │ Mode: Webview  │   │  │  Text Editor   │ │  │
│  │  │   or Native    │   │  │  (QTextEdit)   │ │  │
│  │  │   Chat UI      │   │  └────────────────┘ │  │
│  │  └────────────────┘   │  ┌────────────────┐ │  │
│  │                        │  │  Search Bar    │ │  │
│  │                        │  └────────────────┘ │  │
│  │                        │  ┌────────────────┐ │  │
│  │                        │  │ Results List   │ │  │
│  │                        │  └────────────────┘ │  │
│  └───────────────────────┴──────────────────────┘  │
└─────────────────────────────────────────────────────┘
         │                            │
         ├── config.py ───────────────┤
         │   (TOML parsing)           │
         │                            │
         ├── ollama_client.py         │
         │   (API calls via QThread)  │
         │                            │
         └────────────────── database.py
                             (SQLite + FTS5)
```

### 1.2 Component Architecture

**Separation of Concerns**
- **main.py**: Application entry point, window setup, component integration
- **ai_viewer/**: Complete AI interaction component (webview + native chat)
- **organizer/**: Complete note management component (editor + database)
- **Shared**: Configuration parsing, logging setup

**Component Independence**
- Each component exposes a QWidget that can be embedded
- Each component can run standalone via `if __name__ == "__main__"`
- Components communicate only through main.py, not directly
- No circular dependencies

---

## 2. Technology Stack

### 2.1 Core Technologies
| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.10+ | Language runtime |
| PyQt6 | 6.4+ | GUI framework |
| PyQt6-WebEngine | 6.4+ | Web browser component |
| SQLite | 3.35+ | Database (included with Python) |
| tomli | 2.0+ | TOML parsing (Python < 3.11) |
| markdown | 3.4+ | Markdown to HTML conversion |
| requests | 2.31+ | HTTP client for Ollama API |

**Note**: For Python 3.11+, use built-in `tomllib` instead of `tomli`.

### 2.2 Development Tools
- pytest: Unit and integration testing
- pytest-qt: Qt-specific testing utilities
- pytest-mock: Mocking for tests
- black: Code formatting (optional)
- mypy: Type checking (optional)

### 2.3 Standard Library Usage
- `logging`: Application logging
- `sqlite3`: Database interface
- `pathlib`: Path handling
- `json`: JSON parsing (for Ollama responses)
- `threading`: For Ollama API calls (via QThread)

---

## 3. Project Structure

### 3.1 Directory Layout
```
aiorg/
├── main.py                      # Application entry point
├── config.toml                  # User configuration file
├── requirements.txt             # Python dependencies
├── README.md                    # Setup and usage instructions
│
├── ai_viewer/                   # AI chat component
│   ├── __init__.py
│   ├── viewer.py                # Main widget with mode switching
│   ├── webview_component.py     # Commercial AI webview
│   ├── chat_component.py        # Native chat UI for local models
│   ├── ollama_client.py         # Ollama API integration
│   └── config.py                # Configuration loading
│
├── organizer/                   # Note organizer component
│   ├── __init__.py
│   ├── organizer.py             # Main widget
│   ├── database.py              # Database operations
│   └── markdown_renderer.py     # Markdown to HTML
│
├── tests/                       # Test suite
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_database.py
│   ├── test_ollama_client.py
│   ├── test_organizer.py
│   └── test_integration.py
│
└── logs/                        # Created at runtime
    └── aiorg.log                # Application log file
```

### 3.2 Configuration File Location
- Development: `./config.toml` (same directory as main.py)
- Production: Can be specified via environment variable `AIORG_CONFIG`

### 3.3 Database File Location
- Default: `~/.aiorg/aiorg.db`
- Configurable via `settings.database_path` in config.toml
- Directory created automatically if it doesn't exist

---

## 4. Configuration Specification

### 4.1 TOML Schema

```toml
# Application Settings
[settings]
theme = "dark"                          # "dark" | "light" | "system"
log_level = "DEBUG"                     # "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"
database_path = "~/.aiorg/aiorg.db"    # Path to SQLite database
window_width = 1400                     # Initial window width (pixels)
window_height = 800                     # Initial window height (pixels)
split_ratio = 0.5                       # Left pane width ratio (0.0-1.0)

# AI Model Definitions
[[ai_models]]
name = "Claude"                         # Display name in dropdown
type = "commercial"                     # "commercial" | "local"
url = "https://claude.ai/chat"          # URL to load (commercial) or API endpoint (local)

[[ai_models]]
name = "ChatGPT"
type = "commercial"
url = "https://chatgpt.com"

[[ai_models]]
name = "Ollama - Llama 2"
type = "local"
url = "http://localhost:11434"          # Ollama API base URL
model = "llama2"                        # Model name for Ollama
```

### 4.2 Configuration Loading

**Module**: `ai_viewer/config.py`

**Functions**:
```python
def load_config(config_path: str = "config.toml") -> dict:
    """
    Load and parse TOML configuration file.
    
    Returns:
        dict: Parsed configuration with defaults applied
    
    Raises:
        FileNotFoundError: If config file doesn't exist
        tomli.TOMLDecodeError: If config file is invalid
    """

def get_default_config() -> dict:
    """Return default configuration values."""

def validate_config(config: dict) -> list[str]:
    """
    Validate configuration structure and values.
    
    Returns:
        list[str]: List of validation errors (empty if valid)
    """
```

**Default Values**:
- theme: "system"
- log_level: "INFO"
- database_path: "~/.aiorg/aiorg.db"
- window_width: 1400
- window_height: 800
- split_ratio: 0.5
- ai_models: [] (empty list with warning)

**Validation Rules**:
- `split_ratio` must be between 0.0 and 1.0
- `log_level` must be valid Python logging level
- `theme` must be "dark", "light", or "system"
- `window_width` and `window_height` must be positive integers
- Each `ai_model` must have required fields based on type
- Commercial models: name, type, url
- Local models: name, type, url, model

---

## 5. Database Specification

### 5.1 SQLite Schema

```sql
-- Notes table
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Full-text search virtual table
CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
    content,
    content='notes',
    content_rowid='id'
);

-- Trigger: Sync FTS on INSERT
CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN
    INSERT INTO notes_fts(rowid, content) VALUES (new.id, new.content);
END;

-- Trigger: Sync FTS on DELETE
CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN
    DELETE FROM notes_fts WHERE rowid = old.id;
END;

-- Trigger: Sync FTS on UPDATE
CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN
    UPDATE notes_fts SET content = new.content WHERE rowid = new.id;
    UPDATE notes SET updated_at = CURRENT_TIMESTAMP WHERE id = new.id;
END;

-- App state table (for future use - window position, last selected model, etc.)
CREATE TABLE IF NOT EXISTS app_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 5.2 Database Module

**Module**: `organizer/database.py`

**Class**: `NoteDatabase`

```python
class NoteDatabase:
    """Manages SQLite database operations for notes."""
    
    def __init__(self, db_path: str):
        """Initialize database connection and create schema."""
    
    def save_note(self, content: str, note_id: int = None) -> int:
        """
        Save note to database.
        
        Args:
            content: Markdown content
            note_id: If provided, update existing note; otherwise create new
        
        Returns:
            int: Note ID
        """
    
    def load_note(self, note_id: int) -> dict | None:
        """
        Load note by ID.
        
        Returns:
            dict: {'id', 'content', 'created_at', 'updated_at'} or None
        """
    
    def search_notes(self, query: str, limit: int = 50) -> list[dict]:
        """
        Full-text search across notes.
        
        Args:
            query: Search query
            limit: Maximum results to return
        
        Returns:
            list[dict]: List of note dictionaries with search ranking
        """
    
    def delete_note(self, note_id: int) -> bool:
        """Delete note by ID."""
    
    def list_all_notes(self, limit: int = 100, offset: int = 0) -> list[dict]:
        """List all notes with pagination."""
    
    def close(self):
        """Close database connection."""
```

**Thread Safety**: 
- Database connections are NOT shared across threads
- Each thread that needs database access should create its own connection
- For this application, all database operations happen in the main thread

---

## 6. AI Viewer Component

### 6.1 Component Structure

**Main Widget**: `ai_viewer/viewer.py`

```python
class AIViewerWidget(QWidget):
    """
    Main AI viewer widget with mode switching.
    
    Manages switching between webview (commercial) and native chat (local).
    """
    
    def __init__(self, config: dict, parent=None):
        """Initialize with configuration."""
    
    def setup_ui(self):
        """Create UI layout with dropdown and stacked widget."""
    
    def load_models(self, models: list[dict]):
        """Populate dropdown with AI models from config."""
    
    def on_model_changed(self, index: int):
        """Handle model selection change - switch modes."""
    
    def get_current_model(self) -> dict:
        """Return currently selected model configuration."""
```

**Layout**:
```
┌────────────────────────────┐
│  Model Dropdown (QComboBox)│
├────────────────────────────┤
│  Stacked Widget            │
│  ├─ Webview (commercial)   │
│  └─ Chat UI (local)        │
└────────────────────────────┘
```

### 6.2 Webview Component

**Module**: `ai_viewer/webview_component.py`

```python
class WebviewComponent(QWidget):
    """Webview component for commercial AI models."""
    
    def __init__(self, parent=None):
        """Initialize webview."""
    
    def load_url(self, url: str):
        """Load AI model URL in webview."""
    
    def clear_cache(self):
        """Clear webview cache and cookies."""
```

**Implementation Details**:
- Use `QWebEngineView` from PyQt6.QtWebEngineWidgets
- Enable persistent cookies for authentication
- Set user agent to standard desktop browser
- No special JavaScript injection (keep simple)

### 6.3 Native Chat Component

**Module**: `ai_viewer/chat_component.py`

```python
class ChatComponent(QWidget):
    """Native chat interface for local AI models."""
    
    def __init__(self, parent=None):
        """Initialize chat UI."""
    
    def setup_ui(self):
        """Create chat interface layout."""
    
    def send_message(self):
        """Send user message to Ollama API."""
    
    def append_message(self, role: str, content: str):
        """Append message to chat history."""
    
    def append_chunk(self, chunk: str):
        """Append streaming response chunk."""
    
    def clear_history(self):
        """Clear chat history display."""
    
    def set_ollama_client(self, client: OllamaClient):
        """Set Ollama client for API communication."""
```

**Layout**:
```
┌────────────────────────────┐
│  Chat History              │
│  (QTextBrowser)            │
│  [scrollable, read-only]   │
├────────────────────────────┤
│  Input Field (QLineEdit)   │
│  [Send Button]             │
│  [Clear Button]            │
└────────────────────────────┘
```

**Message Format**:
```html
<div class="message user">
    <strong>You:</strong> {content}
</div>
<div class="message assistant">
    <strong>Assistant:</strong> {content}
</div>
```

### 6.4 Ollama Client

**Module**: `ai_viewer/ollama_client.py`

```python
class OllamaClient:
    """Client for Ollama API communication."""
    
    def __init__(self, base_url: str):
        """Initialize client with API base URL."""
    
    def chat(
        self, 
        model: str, 
        messages: list[dict],
        on_chunk: callable,
        on_complete: callable,
        on_error: callable
    ):
        """
        Send chat request with streaming response.
        
        Args:
            model: Model name (e.g., "llama2")
            messages: List of message dicts with 'role' and 'content'
            on_chunk: Callback for each response chunk
            on_complete: Callback when response completes
            on_error: Callback for errors
        """
    
    def check_connection(self) -> bool:
        """Check if Ollama server is reachable."""
    
    def list_models(self) -> list[str]:
        """List available models (optional, for future)."""
```

**Threading**:
- API calls run in `QThread` to avoid blocking UI
- Use signals/slots for thread-safe communication
- Example:
```python
class OllamaWorker(QThread):
    chunk_received = pyqtSignal(str)
    request_complete = pyqtSignal()
    request_error = pyqtSignal(str)
    
    def run(self):
        """Execute API request in background thread."""
```

**API Endpoint**: `/api/chat`

**Request Format**:
```json
{
  "model": "llama2",
  "messages": [
    {"role": "user", "content": "Hello!"},
    {"role": "assistant", "content": "Hi there!"},
    {"role": "user", "content": "How are you?"}
  ],
  "stream": true
}
```

**Response Format** (streaming, newline-delimited JSON):
```json
{"model":"llama2","created_at":"...","message":{"role":"assistant","content":"I"},"done":false}
{"model":"llama2","created_at":"...","message":{"role":"assistant","content":"'m"},"done":false}
...
{"model":"llama2","created_at":"...","message":{"role":"assistant","content":""},"done":true}
```

**Error Handling**:
- Connection refused: Show error message in chat
- Timeout: Show timeout message after 30 seconds
- Invalid model: Show model not found error
- Parse error: Log error and show generic message

---

## 7. Organizer Component

### 7.1 Component Structure

**Main Widget**: `organizer/organizer.py`

```python
class OrganizerWidget(QWidget):
    """Note organizer with editor, preview, and search."""
    
    def __init__(self, database: NoteDatabase, parent=None):
        """Initialize with database instance."""
    
    def setup_ui(self):
        """Create UI layout."""
    
    def save_note(self):
        """Save current note to database."""
    
    def load_note(self, note_id: int):
        """Load note into editor."""
    
    def toggle_preview(self):
        """Switch between edit and preview modes."""
    
    def search_notes(self):
        """Execute search and display results."""
    
    def new_note(self):
        """Clear editor for new note."""
```

**Layout**:
```
┌────────────────────────────┐
│  Toolbar                   │
│  [Save] [New] [Preview]    │
├────────────────────────────┤
│  Editor / Preview          │
│  (Stacked Widget)          │
│  ├─ QTextEdit (edit mode)  │
│  └─ QTextBrowser (preview) │
├────────────────────────────┤
│  Search Bar (QLineEdit)    │
│  [Search Button]           │
├────────────────────────────┤
│  Results (QListWidget)     │
│  [Hidden when not searching│
└────────────────────────────┘
```

### 7.2 Editor Component

**Widget**: `QTextEdit`

**Configuration**:
- Plain text mode (not rich text)
- Word wrap enabled
- Accept rich text: False
- Line wrap mode: WidgetWidth
- Font: Monospace, 11pt

**Keyboard Shortcuts**:
- Ctrl+S: Save note
- Ctrl+N: New note
- Ctrl+F: Focus search bar
- Ctrl+P: Toggle preview

### 7.3 Preview Component

**Widget**: `QTextBrowser`

**Configuration**:
- Read-only: True
- Open external links: False (or True, user preference)
- HTML rendering enabled

**Markdown Rendering**:

**Module**: `organizer/markdown_renderer.py`

```python
def render_markdown(text: str) -> str:
    """
    Convert markdown text to HTML.
    
    Args:
        text: Markdown source
    
    Returns:
        str: HTML output with CSS styling
    """
```

**Markdown Extensions** (using `markdown` library):
- `extra`: Tables, fenced code blocks, etc.
- `codehilite`: Syntax highlighting in code blocks (optional)
- `toc`: Table of contents (optional)

**CSS Styling**:
```html
<style>
body { 
    font-family: sans-serif; 
    line-height: 1.6; 
    padding: 10px;
    color: #e0e0e0;  /* Dark theme */
    background-color: #2b2b2b;
}
code { 
    background-color: #3a3a3a; 
    padding: 2px 4px; 
    border-radius: 3px;
}
pre {
    background-color: #3a3a3a;
    padding: 10px;
    border-radius: 5px;
    overflow-x: auto;
}
/* Add more styling as needed */
</style>
```

### 7.4 Search Component

**Search Execution**:
```python
def execute_search(self, query: str):
    """
    Execute full-text search and display results.
    
    Implementation:
    1. Query database using FTS5
    2. Clear results list
    3. Populate with results
    4. Show results widget
    5. Focus first result
    """
```

**Result Item Format**:
```python
class SearchResultItem(QListWidgetItem):
    """Custom list item for search results."""
    
    def __init__(self, note: dict):
        """
        Initialize with note data.
        
        Display format:
        [Line 1] First 50 chars of note
        [Line 2] Created: YYYY-MM-DD HH:MM
        """
```

**Search Query Syntax** (SQLite FTS5):
- Simple query: `"python programming"` (searches for both words)
- Phrase query: `'"exact phrase"'` (searches for exact match)
- Prefix query: `"program*"` (searches for program, programming, etc.)

---

## 8. Main Application

### 8.1 Entry Point

**Module**: `main.py`

```python
class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        """Initialize application."""
    
    def setup_ui(self):
        """Create main window layout."""
    
    def load_configuration(self):
        """Load and apply configuration."""
    
    def setup_logging(self):
        """Configure logging system."""
    
    def create_components(self):
        """Initialize AI viewer and organizer components."""
    
    def closeEvent(self, event):
        """Handle application shutdown."""

def main():
    """Application entry point."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
```

### 8.2 Window Layout

**Layout**: `QSplitter` (horizontal)
- Left pane: `AIViewerWidget`
- Right pane: `OrganizerWidget`
- Splitter ratio: From config (default 0.5)
- Minimum left pane width: 400px
- Minimum right pane width: 300px

### 8.3 Application State

**State Persistence** (future):
- Window size and position
- Splitter position
- Last selected AI model
- Last opened note

**Storage**: `app_state` table in database

---

## 9. Logging System

### 9.1 Configuration

**Log Levels**:
- DEBUG: Detailed diagnostic information
- INFO: General informational messages
- WARNING: Warning messages (non-critical issues)
- ERROR: Error messages (recoverable errors)
- CRITICAL: Critical errors (application may crash)

**Log Format**:
```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

Example:
```
2025-10-19 14:30:45,123 - ai_viewer.ollama_client - INFO - Connected to Ollama at http://localhost:11434
2025-10-19 14:30:50,456 - organizer.database - DEBUG - Saved note ID 42 (250 chars)
```

### 9.2 Log Destinations

**Console** (sys.stderr):
- Log level: From config (default INFO)
- Format: Simple format without timestamp for readability

**File** (`logs/aiorg.log`):
- Log level: DEBUG (always capture everything)
- Format: Full format with timestamp
- Rotation: Not implemented in POC (can add later)
- Max size: Not implemented in POC

### 9.3 Logger Names

**Convention**: Use `__name__` in each module

Examples:
- `main`: Main application
- `ai_viewer.viewer`: AI viewer widget
- `ai_viewer.ollama_client`: Ollama client
- `organizer.organizer`: Organizer widget
- `organizer.database`: Database operations

### 9.4 Logging Best Practices

**What to Log**:
- Application startup/shutdown
- Configuration loading
- Component initialization
- User actions (model switch, note save, search)
- API calls (URL, model, success/failure)
- Database operations (queries, results)
- Errors with full stack traces

**What NOT to Log**:
- Note content (privacy)
- Passwords or credentials
- Large data dumps

**Example Usage**:
```python
import logging

logger = logging.getLogger(__name__)

logger.info("Application started")
logger.debug(f"Loaded {len(models)} AI models from config")
logger.warning("Ollama not reachable at http://localhost:11434")
logger.error("Failed to save note", exc_info=True)
```

---

## 10. Error Handling

### 10.1 Error Categories

**Configuration Errors**:
- Missing config file: Use defaults, warn user
- Invalid TOML syntax: Show error dialog, exit
- Invalid config values: Use defaults, log warning

**Database Errors**:
- Database locked: Retry after short delay
- Disk full: Show error dialog
- Corrupted database: Show error with recovery instructions

**Network Errors** (Ollama):
- Connection refused: Show message in chat UI
- Timeout: Show timeout message
- Invalid response: Log error, show generic message

**UI Errors**:
- Widget creation failure: Log error, try to continue
- File dialog errors: Show error message

### 10.2 User-Facing Error Messages

**Guidelines**:
- Clear and actionable
- No technical jargon
- Suggest solution when possible

**Examples**:

Good:
```
"Could not connect to Ollama. Make sure Ollama is running and accessible at http://localhost:11434"
```

Bad:
```
"ConnectionRefusedError: [Errno 111] Connection refused"
```

### 10.3 Error Recovery

**Graceful Degradation**:
- If Ollama unavailable: AI viewer still works for commercial models
- If config invalid: Use defaults and continue
- If database error: Inform user but don't crash

**No Crashes**:
- Catch all exceptions in event handlers
- Log full stack trace
- Show user-friendly error message
- Continue running when possible

---

## 11. Testing Strategy

### 11.1 Unit Tests

**Coverage Targets**:
- Configuration parsing: 100%
- Database operations: 100%
- Markdown rendering: 100%
- Ollama client: 80% (mocked API calls)

**Test Structure**:
```python
# tests/test_database.py
import pytest
from organizer.database import NoteDatabase

def test_save_new_note():
    """Test saving a new note returns valid ID."""
    db = NoteDatabase(":memory:")
    note_id = db.save_note("Test content")
    assert note_id > 0

def test_search_notes():
    """Test full-text search returns relevant results."""
    db = NoteDatabase(":memory:")
    db.save_note("Python programming tutorial")
    db.save_note("JavaScript basics")
    results = db.search_notes("python")
    assert len(results) == 1
    assert "Python" in results[0]['content']
```

### 11.2 Integration Tests

**Test Scenarios**:
- Load config and initialize components
- Save note and search for it
- Switch between AI models
- Ollama API integration (with mock server)

**Example**:
```python
# tests/test_integration.py
def test_note_workflow(qtbot):
    """Test complete note creation and search workflow."""
    # Create main window
    window = MainWindow()
    qtbot.addWidget(window)
    
    # Get organizer widget
    organizer = window.organizer_widget
    
    # Type content
    organizer.editor.setPlainText("Test note content")
    
    # Save note
    qtbot.mouseClick(organizer.save_button, Qt.LeftButton)
    
    # Search for note
    organizer.search_bar.setText("test")
    qtbot.keyClick(organizer.search_bar, Qt.Key_Return)
    
    # Verify result
    assert organizer.results_list.count() == 1
```

### 11.3 Manual Testing Checklist

**AI Viewer**:
- [ ] Commercial model loads in webview
- [ ] Can authenticate in webview
- [ ] Can interact with AI normally
- [ ] Local model loads native chat UI
- [ ] Can send message to Ollama
- [ ] Streaming responses display correctly
- [ ] Clear history button works
- [ ] Switching models works smoothly

**Organizer**:
- [ ] Can type in editor
- [ ] Save button saves note
- [ ] Toggle to preview shows rendered markdown
- [ ] Toggle back to edit mode works
- [ ] Search finds saved notes
- [ ] Clicking result loads note
- [ ] New note clears editor

**Integration**:
- [ ] Both panes visible side by side
- [ ] Splitter can be dragged
- [ ] Can copy from AI chat and paste to organizer
- [ ] Application starts without errors
- [ ] Configuration loads correctly
- [ ] Logs are written to file

---

## 12. Performance Requirements

### 12.1 Benchmarks

**Application Startup**:
- Cold start: < 3 seconds
- Warm start: < 1 second

**Database Operations**:
- Save note: < 100ms (synchronous is acceptable)
- Load note: < 50ms
- Search 1000 notes: < 500ms
- Search 10000 notes: < 2 seconds

**UI Responsiveness**:
- Button clicks: Immediate visual feedback
- Ollama API calls: Run in background thread
- No UI freezing during any operation

### 12.2 Resource Usage

**Memory**:
- Idle: < 200 MB
- With webview loaded: < 400 MB
- Acceptable since webviews are Chromium-based

**CPU**:
- Idle: < 1%
- During Ollama streaming: < 20%
- During search: Spike acceptable, quick return to idle

**Disk**:
- Database growth: ~1 KB per note (estimate)
- Logs: Unbounded for POC (can add rotation later)

---

## 13. Security Considerations

### 13.1 Local Data Security

**Database**:
- Stored in user's home directory
- SQLite file permissions: User read/write only
- No encryption (user can encrypt filesystem)

**Logs**:
- Do not log note content
- Do not log credentials
- Logs readable by user only

### 13.2 Network Security

**Ollama Communication**:
- HTTP only (localhost, no TLS needed)
- No authentication expected
- User responsible for Ollama security

**Commercial AI Webviews**:
- HTTPS handled by sites
- Cookies isolated per webview
- No credential storage by application

### 13.3 Code Security

**Input Validation**:
- Validate all user inputs
- Sanitize database queries (use parameterized queries)
- Validate configuration values

**Dependency Security**:
- Use well-known, maintained libraries
- Keep dependencies updated
- No eval() or exec() of user input

---

## 14. Deployment

### 14.1 Installation

**Requirements**:
```
Python 3.10+
PyQt6>=6.4.0
PyQt6-WebEngine>=6.4.0
markdown>=3.4.0
requests>=2.31.0
tomli>=2.0.0; python_version < '3.11'
```

**Installation Steps**:
```bash
# Clone or download source
git clone <repo-url> aiorg
cd aiorg

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run application
python main.py
```

### 14.2 Configuration Setup

**First Run**:
1. Application looks for `config.toml` in current directory
2. If not found, uses default configuration
3. User should create `config.toml` based on example
4. Restart application to load custom config

**Example Config** (include in README):
```toml
[settings]
theme = "dark"
log_level = "INFO"
database_path = "~/.aiorg/aiorg.db"

[[ai_models]]
name = "Claude"
type = "commercial"
url = "https://claude.ai/chat"

[[ai_models]]
name = "Ollama - Llama 2"
type = "local"
url = "http://localhost:11434"
model = "llama2"
```

### 14.3 No Packaging (POC)

**POC Deployment**:
- Source code distribution only
- No PyInstaller or other packaging
- No installers or app bundles
- Users run from source with Python

---

## 15. Maintenance & Extensibility

### 15.1 Component Swapping

**Editor Widget**:
- Currently: QTextEdit
- Future options: QPlainTextEdit, QScintilla, custom widget
- Swap by changing widget type in `organizer.py`
- Interface: `setText()`, `toPlainText()`, signals

**Markdown Renderer**:
- Currently: Python `markdown` library
- Future options: mistletoe, markdown-it-py
- Swap by changing import in `markdown_renderer.py`
- Interface: `render_markdown(text: str) -> str`

**Ollama Client**:
- Currently: requests library with custom client
- Future options: official SDK (if released)
- Swap by changing import in `chat_component.py`
- Interface: `chat()` method with callbacks

### 15.2 Adding Features

**New AI Model Type** (e.g., API-based):
1. Add new type to config schema
2. Create new component in `ai_viewer/`
3. Update `viewer.py` to handle new type
4. No changes to organizer needed

**New Database Field**:
1. Create migration script
2. Update schema in `database.py`
3. Update database methods
4. Update UI if needed

**New Note Feature** (e.g., tags):
1. Update database schema
2. Add UI elements in `organizer.py`
3. Update save/load/search methods
4. Add tests

### 15.3 Code Style Guidelines

**Consistency**:
- Use type hints for function signatures
- Use docstrings for all public functions
- Follow PEP 8 style guide
- Keep functions small and focused
- One class per file (generally)

**Simplicity**:
- Prefer simple over clever
- Avoid premature optimization
- No unnecessary abstractions
- Clear naming over comments

---

## 16. Known Limitations

### 16.1 Technical Limitations

- **Single instance**: No protection against multiple instances
- **No conversation history**: Local model chats not persisted (Phase 1)
- **No undo/redo**: Editor has session undo only, not persisted
- **No note encryption**: Database is plain SQLite
- **No concurrent editing**: Single-user application

### 16.2 Platform Limitations

- **macOS webview**: May have different behavior than Linux/Windows
- **HiDPI scaling**: May need manual adjustment on some systems
- **Wayland**: May have issues with certain Qt features

### 16.3 Design Limitations

- **No commercial AI capture**: Cannot programmatically extract chats
- **Config file only**: No GUI for settings in Phase 1
- **Manual model switching**: Must edit config to add models

---

## 17. Future Considerations

### 17.1 Phase 2 Features (If Implemented)

- Conversation history persistence for local models
- Note tagging and filtering
- Export to multiple formats
- Improved search with filters
- Custom themes

### 17.2 Architecture Evolution

**If Scaling Beyond POC**:
- Add plugin system for AI model providers
- Separate database layer into ORM
- Add settings GUI
- Add application packaging
- Add update mechanism

**Not Planned**:
- Web version
- Mobile version
- Multi-user support
- Cloud sync
