# AIOrg - Implementation Instructions for Claude Code

## Overview

This document provides phase-by-phase instructions for building AIOrg using Claude Code. Each phase is designed to be completed independently with verification before moving to the next phase.

**CRITICAL RULES**:
1. ✅ **Only implement features explicitly specified** in PRD and TRD
2. ✅ **Keep implementations simple** - no unnecessary abstractions
3. ✅ **Verify each phase** before moving to the next
4. ✅ **Run all tests** and ensure they pass
5. ❌ **DO NOT add features** not in the requirements
6. ❌ **DO NOT add extra dependencies** unless specified
7. ❌ **DO NOT create GUI for settings** - config file only
8. ❌ **DO NOT implement auto-save** - manual save only

---

## Phase 1: Project Setup & Configuration

### Goals
- Create project structure
- Implement configuration loading
- Set up logging system
- Verify configuration works correctly

### Files to Create
```
aiorg/
├── main.py (stub only)
├── config.toml (example configuration)
├── requirements.txt
├── README.md
├── ai_viewer/
│   ├── __init__.py
│   └── config.py
├── organizer/
│   └── __init__.py
└── tests/
    ├── __init__.py
    └── test_config.py
```

### Prompt for Claude Code

```
Create the initial project structure for AIOrg with configuration loading.

Requirements:
1. Create the directory structure as specified in TRD section 3.1
2. Implement ai_viewer/config.py with these functions:
   - load_config(config_path: str) -> dict
   - get_default_config() -> dict
   - validate_config(config: dict) -> list[str]
3. Create config.toml with example configuration from TRD section 4.1
4. Create requirements.txt with dependencies from TRD section 2.1
5. Set up Python logging in a utility function
6. Create main.py stub that loads config and sets up logging

Implementation notes:
- Use tomli for Python < 3.11, tomllib for 3.11+
- Expand ~ in database_path using pathlib
- Apply default values for missing config keys
- Validate all config values per TRD section 4.2
- DO NOT add any features not specified
- Keep it simple - no unnecessary classes or abstractions

Refer to TRD sections 4.1 and 4.2 for complete specifications.
```

### Unit Tests Required

**File**: `tests/test_config.py`

Tests to implement:
1. `test_load_valid_config()` - Load valid config.toml
2. `test_load_missing_config()` - Handle missing file gracefully
3. `test_load_invalid_toml()` - Handle parse errors
4. `test_default_config()` - Verify default values
5. `test_validate_valid_config()` - Valid config passes validation
6. `test_validate_invalid_split_ratio()` - Detect invalid split_ratio
7. `test_validate_invalid_log_level()` - Detect invalid log_level
8. `test_validate_missing_model_fields()` - Detect missing required fields
9. `test_path_expansion()` - Verify ~ expands to home directory

### Manual Verification

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run unit tests
pytest tests/test_config.py -v

# 3. Test config loading
python -c "from ai_viewer.config import load_config; print(load_config('config.toml'))"

# 4. Verify logging works
python main.py  # Should log startup messages

# 5. Test with invalid config
echo "invalid toml" > bad_config.toml
python -c "from ai_viewer.config import load_config; load_config('bad_config.toml')"
# Should handle error gracefully
```

### Success Criteria
- [ ] All unit tests pass
- [ ] Config loads from TOML file correctly
- [ ] Default values applied when keys missing
- [ ] Validation catches all invalid values
- [ ] Logging outputs to console and file
- [ ] Path expansion works (~ becomes /home/user)
- [ ] No crashes on invalid config

---

## Phase 2: Database Layer

### Goals
- Implement SQLite database with FTS5
- Create database operations module
- Verify CRUD operations work
- Ensure full-text search works

### Files to Create
```
organizer/
├── database.py
└── tests/
    └── test_database.py (move to tests/ directory)
```

### Prompt for Claude Code

```
Implement the database layer for note storage and full-text search.

Requirements:
1. Create organizer/database.py with NoteDatabase class per TRD section 5.2
2. Implement methods:
   - __init__(db_path: str): Create connection and schema
   - save_note(content: str, note_id: int = None) -> int
   - load_note(note_id: int) -> dict | None
   - search_notes(query: str, limit: int = 50) -> list[dict]
   - delete_note(note_id: int) -> bool
   - list_all_notes(limit: int = 100, offset: int = 0) -> list[dict]
   - close(): Close connection
3. Implement SQL schema from TRD section 5.1:
   - notes table
   - notes_fts virtual table (FTS5)
   - Triggers for FTS sync
   - app_state table
4. Use parameterized queries (no SQL injection)
5. Add comprehensive error handling
6. Add logging for all operations

Implementation notes:
- Use sqlite3 from standard library
- Create schema in __init__ if tables don't exist
- Automatically set updated_at on UPDATE
- FTS5 syntax: SELECT * FROM notes_fts WHERE notes_fts MATCH ?
- Return dictionaries with id, content, created_at, updated_at
- DO NOT add any methods not specified
- Keep it simple - no ORM, just raw SQL

Refer to TRD section 5 for complete specifications.
```

### Unit Tests Required

**File**: `tests/test_database.py`

Tests to implement:
1. `test_create_database()` - Schema created correctly
2. `test_save_new_note()` - Save returns valid ID
3. `test_save_update_note()` - Update existing note
4. `test_load_note()` - Load note by ID
5. `test_load_nonexistent_note()` - Returns None for invalid ID
6. `test_delete_note()` - Delete works
7. `test_search_notes_simple()` - Simple search query
8. `test_search_notes_phrase()` - Phrase search
9. `test_search_notes_empty()` - Empty results
10. `test_list_all_notes()` - List with pagination
11. `test_fts_triggers()` - FTS stays in sync
12. `test_timestamps()` - created_at and updated_at work

### Manual Verification

```bash
# 1. Run unit tests
pytest tests/test_database.py -v

# 2. Test database manually
python -c "
from organizer.database import NoteDatabase
db = NoteDatabase(':memory:')
id1 = db.save_note('Test note about Python')
id2 = db.save_note('Test note about JavaScript')
print('Saved notes:', id1, id2)
results = db.search_notes('Python')
print('Search results:', results)
note = db.load_note(id1)
print('Loaded note:', note)
"

# 3. Test FTS search
python -c "
from organizer.database import NoteDatabase
db = NoteDatabase(':memory:')
db.save_note('Python programming tutorial')
db.save_note('JavaScript basics')
db.save_note('Python data science')
results = db.search_notes('python')
print(f'Found {len(results)} results:', [r['content'][:30] for r in results])
"

# 4. Check database schema
python -c "
from organizer.database import NoteDatabase
import sqlite3
db = NoteDatabase('test.db')
conn = sqlite3.connect('test.db')
tables = conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()
print('Tables:', tables)
"
```

### Success Criteria
- [ ] All unit tests pass
- [ ] Can create, read, update, delete notes
- [ ] Full-text search returns relevant results
- [ ] FTS index stays in sync with notes table
- [ ] Timestamps are set automatically
- [ ] No SQL injection vulnerabilities
- [ ] Database operations are logged
- [ ] Handles errors gracefully (e.g., disk full)

---

## Phase 3: Organizer Component (Standalone)

### Goals
- Build note organizer UI with PyQt6
- Integrate with database layer
- Implement edit/preview toggle
- Make component testable standalone

### Files to Create
```
organizer/
├── organizer.py
└── markdown_renderer.py
tests/
└── test_organizer.py
```

### Prompt for Claude Code

```
Implement the note organizer component as a standalone PyQt6 widget.

Requirements:
1. Create organizer/organizer.py with OrganizerWidget class per TRD section 7.1
2. Implement UI layout per TRD section 7.1:
   - Toolbar with Save, New, Preview buttons
   - Stacked widget with QTextEdit (edit) and QTextBrowser (preview)
   - Search bar (QLineEdit) with search button
   - Results list (QListWidget, hidden by default)
3. Implement methods:
   - setup_ui(): Create layout
   - save_note(): Save to database, show feedback
   - load_note(note_id): Load into editor
   - new_note(): Clear editor
   - toggle_preview(): Switch edit/preview modes
   - search_notes(): Execute search, show results
4. Create organizer/markdown_renderer.py:
   - render_markdown(text: str) -> str
   - Use markdown library with 'extra' extension
   - Include dark theme CSS per TRD section 7.3
5. Add keyboard shortcuts (Ctrl+S, Ctrl+N, Ctrl+P, Ctrl+F)
6. Add standalone test with if __name__ == "__main__"
7. Add comprehensive logging

Implementation notes:
- QTextEdit in plain text mode, no rich text
- QTextBrowser for preview (read-only)
- Search results show first 50 chars + timestamp
- Hide results list when search bar is empty
- DO NOT add auto-save
- DO NOT add note tags or folders
- DO NOT add toolbar customization
- Keep it simple

Refer to TRD section 7 for complete specifications.
```

### Unit Tests Required

**File**: `tests/test_organizer.py`

Tests to implement:
1. `test_organizer_creation()` - Widget creates without error
2. `test_save_note(qtbot, tmp_path)` - Save button works
3. `test_load_note(qtbot, tmp_path)` - Load displays content
4. `test_toggle_preview(qtbot)` - Toggle switches views
5. `test_search_notes(qtbot, tmp_path)` - Search populates results
6. `test_new_note(qtbot)` - New button clears editor
7. `test_keyboard_shortcuts(qtbot)` - Ctrl+S, Ctrl+N work
8. `test_markdown_rendering()` - Markdown converts to HTML

### Manual Verification

```bash
# 1. Run unit tests
pytest tests/test_organizer.py -v

# 2. Run standalone organizer
python organizer/organizer.py
# Should open window with editor

# 3. Manual UI test:
# - Type some markdown: "# Hello\n## World\n- Item 1\n- Item 2"
# - Click Save button - should show success feedback
# - Click Preview - should show rendered HTML
# - Click back to edit mode
# - Type search query, press Enter
# - Click search result - should load note

# 4. Test keyboard shortcuts:
# - Ctrl+S should save
# - Ctrl+N should clear editor
# - Ctrl+P should toggle preview
# - Ctrl+F should focus search bar
```

### Success Criteria
- [ ] All unit tests pass
- [ ] Widget displays correctly
- [ ] Can type in editor
- [ ] Save button saves to database
- [ ] Preview shows rendered markdown
- [ ] Toggle switches between edit/preview
- [ ] Search finds and displays results
- [ ] Clicking result loads note
- [ ] New button clears editor
- [ ] Keyboard shortcuts work
- [ ] Component runs standalone
- [ ] Dark theme CSS applied in preview

---

## Phase 4: AI Viewer - Webview Component (Standalone)

### Goals
- Build commercial AI webview component
- Test with actual websites (Claude, ChatGPT)
- Make component testable standalone

### Files to Create
```
ai_viewer/
├── webview_component.py
└── viewer.py (partial - webview only)
tests/
└── test_webview.py
```

### Prompt for Claude Code

```
Implement the webview component for commercial AI models.

Requirements:
1. Create ai_viewer/webview_component.py with WebviewComponent class per TRD section 6.2
2. Use QWebEngineView from PyQt6.QtWebEngineWidgets
3. Implement methods:
   - __init__(parent=None): Initialize webview
   - load_url(url: str): Load URL
   - clear_cache(): Clear cookies and cache (optional for Phase 1)
4. Enable persistent cookies for authentication
5. Set standard desktop user agent
6. Create ai_viewer/viewer.py (partial) with:
   - Dropdown (QComboBox) for model selection
   - Load webview when commercial model selected
   - Standalone test mode
7. Add logging for URL loads

Implementation notes:
- QWebEngineView handles all web rendering
- No JavaScript injection needed
- No custom protocols or handlers
- Cookies automatically persist in default profile
- DO NOT add dev tools or inspector
- DO NOT add custom CSS injection
- Keep it simple

Refer to TRD section 6.1 and 6.2 for complete specifications.
```

### Unit Tests Required

**File**: `tests/test_webview.py`

Tests to implement:
1. `test_webview_creation(qtbot)` - Widget creates
2. `test_load_url(qtbot)` - Can load URL
3. `test_webview_renders(qtbot)` - Webview displays (may need mock)

**Note**: Testing webviews is limited. Focus on manual testing.

### Manual Verification

```bash
# 1. Run unit tests (limited)
pytest tests/test_webview.py -v

# 2. Run standalone webview
python ai_viewer/viewer.py
# Should open window with dropdown and webview

# 3. Manual UI test:
# - Select "Claude" from dropdown
# - Should load claude.ai/chat
# - Log in if needed
# - Verify can interact with Claude normally
# - Close and reopen - should still be logged in (cookies persist)

# 4. Test ChatGPT:
# - Select "ChatGPT" from dropdown
# - Should load chatgpt.com
# - Log in if needed
# - Verify can interact normally

# 5. Test switching:
# - Switch between Claude and ChatGPT
# - Both should maintain login state
```

### Success Criteria
- [ ] Unit tests pass
- [ ] Webview loads URLs correctly
- [ ] Can access claude.ai/chat
- [ ] Can access chatgpt.com
- [ ] Authentication persists (cookies work)
- [ ] Can interact with AI models normally
- [ ] Can copy text from chat
- [ ] Dropdown switches between models
- [ ] Component runs standalone
- [ ] No crashes or errors

---

## Phase 5: AI Viewer - Native Chat Component (Standalone)

### Goals
- Build native PyQt chat UI for local models
- Implement Ollama API integration
- Test with actual Ollama instance
- Support streaming responses

### Files to Create
```
ai_viewer/
├── chat_component.py
├── ollama_client.py
└── viewer.py (complete)
tests/
├── test_ollama_client.py
└── test_chat_component.py
```

### Prompt for Claude Code

```
Implement the native chat component and Ollama API client.

Requirements:
1. Create ai_viewer/ollama_client.py per TRD section 6.4:
   - OllamaClient class with chat() method
   - Support streaming responses
   - Use QThread for API calls (non-blocking)
   - Implement OllamaWorker(QThread) with signals
   - check_connection() method
   - Error handling for connection failures
2. Create ai_viewer/chat_component.py per TRD section 6.3:
   - ChatComponent widget with QTextBrowser and QLineEdit
   - send_message() method
   - append_message(role, content) for display
   - append_chunk(chunk) for streaming
   - clear_history() button
   - Message format with styling (user/assistant)
3. Complete ai_viewer/viewer.py:
   - Add native chat mode
   - Switch between webview and chat based on model type
   - Use QStackedWidget for mode switching
4. Add comprehensive logging
5. Add standalone test modes

Implementation notes:
- Ollama API endpoint: POST /api/chat
- Stream format: newline-delimited JSON
- Parse each line as JSON, extract message.content
- Use QThread to avoid blocking UI
- Emit signals for: chunk_received, request_complete, request_error
- HTML formatting in QTextBrowser for messages
- DO NOT add conversation history persistence (Phase 1)
- DO NOT add temperature/parameter controls
- Keep it simple

Refer to TRD section 6.3 and 6.4 for complete specifications.
```

### Unit Tests Required

**File**: `tests/test_ollama_client.py`

Tests to implement:
1. `test_ollama_client_creation()` - Client creates
2. `test_check_connection_success()` - Connection check (mock)
3. `test_check_connection_failure()` - Connection failure (mock)
4. `test_chat_request_format()` - Request format correct (mock)
5. `test_chat_streaming_response()` - Parse streaming JSON (mock)
6. `test_chat_error_handling()` - Handle errors gracefully (mock)

**File**: `tests/test_chat_component.py`

Tests to implement:
1. `test_chat_creation(qtbot)` - Widget creates
2. `test_append_message(qtbot)` - Messages display
3. `test_send_button(qtbot)` - Send button works
4. `test_clear_history(qtbot)` - Clear button works

### Manual Verification

```bash
# 0. Prerequisites: Have Ollama running
# ollama serve
# ollama pull llama2

# 1. Run unit tests
pytest tests/test_ollama_client.py -v
pytest tests/test_chat_component.py -v

# 2. Test Ollama client standalone
python -c "
from ai_viewer.ollama_client import OllamaClient
client = OllamaClient('http://localhost:11434')
print('Connection:', client.check_connection())
"

# 3. Run standalone chat component
python ai_viewer/viewer.py
# Select "Ollama - Llama 2" from dropdown

# 4. Manual chat test:
# - Type "Hello!" and press Enter or click Send
# - Should see streaming response appear
# - Type another message
# - Should continue conversation
# - Click Clear button
# - History should clear

# 5. Test error handling:
# - Stop Ollama (Ctrl+C in ollama serve)
# - Try to send message
# - Should show error message
# - Start Ollama again
# - Should work again

# 6. Test model switching:
# - Chat with Ollama
# - Switch to Claude (webview)
# - Switch back to Ollama
# - Should show cleared chat (no persistence)
```

### Success Criteria
- [ ] All unit tests pass
- [ ] Can connect to Ollama API
- [ ] Can send messages to Ollama
- [ ] Streaming responses display in real-time
- [ ] Messages formatted correctly (user/assistant)
- [ ] Clear button works
- [ ] Connection errors handled gracefully
- [ ] Non-blocking (UI responsive during API calls)
- [ ] Component runs standalone
- [ ] Switching between models works
- [ ] No crashes on Ollama errors

---

## Phase 6: Main Application Integration

### Goals
- Integrate both components in main window
- Set up window layout with splitter
- Load configuration and apply settings
- Verify both components work together

### Files to Update
```
main.py (complete implementation)
```

### Prompt for Claude Code

```
Implement the main application window integrating both components.

Requirements:
1. Complete main.py per TRD section 8:
   - MainWindow class inheriting QMainWindow
   - setup_ui() method creating layout
   - load_configuration() method
   - setup_logging() method
   - create_components() method
2. Create QSplitter (horizontal) layout:
   - Left pane: AIViewerWidget
   - Right pane: OrganizerWidget
   - Apply split_ratio from config
   - Set minimum widths (400px left, 300px right)
3. Apply window settings from config:
   - Window width and height
   - Theme (dark/light/system)
4. Pass configuration to components
5. Handle application shutdown (close database connection)
6. Create main() function as entry point
7. Add comprehensive logging

Implementation notes:
- Create single database instance, pass to organizer
- Load config on startup
- Apply theme using QApplication.setStyle() if needed
- Save window state on close (future - skip for Phase 1)
- DO NOT add menu bar
- DO NOT add status bar
- DO NOT add toolbar in main window
- Keep it simple

Refer to TRD section 8 for complete specifications.
```

### Integration Tests Required

**File**: `tests/test_integration.py`

Tests to implement:
1. `test_main_window_creation(qtbot)` - Window creates
2. `test_components_integrated(qtbot)` - Both components present
3. `test_splitter_works(qtbot)` - Splitter can be dragged
4. `test_config_applied(qtbot, tmp_path)` - Config loads and applies
5. `test_note_workflow(qtbot, tmp_path)` - Save and search note
6. `test_model_switching(qtbot)` - Switch AI models

### Manual Verification

```bash
# 1. Run integration tests
pytest tests/test_integration.py -v

# 2. Run full application
python main.py

# 3. Manual integration test:
# LEFT PANE (AI Viewer):
# - Verify dropdown shows all configured models
# - Select commercial model (Claude or ChatGPT)
# - Verify webview loads
# - Select local model (Ollama)
# - Verify native chat appears
# - Send message to Ollama
# - Verify response streams in

# RIGHT PANE (Organizer):
# - Type some markdown content
# - Click Save
# - Verify saved (feedback message)
# - Click New
# - Type different content
# - Click Save
# - Enter search query
# - Verify results appear
# - Click result
# - Verify note loads

# 4. Test copy-paste between panes:
# - Chat with AI (either type)
# - Select and copy response
# - Paste into organizer editor
# - Save note
# - Search for content
# - Verify found

# 5. Test splitter:
# - Drag splitter left and right
# - Verify both panes resize
# - Verify minimum sizes respected

# 6. Test window resize:
# - Resize window
# - Verify both panes scale proportionally

# 7. Test close:
# - Close application
# - Verify no errors
# - Verify database closed properly
# - Check logs for any errors
```

### Success Criteria
- [ ] All integration tests pass
- [ ] Application starts without errors
- [ ] Both components visible and functional
- [ ] Configuration loads and applies correctly
- [ ] Can switch between AI models
- [ ] Can chat with commercial and local AI
- [ ] Can save and search notes
- [ ] Can copy from AI chat to organizer
- [ ] Splitter works smoothly
- [ ] Window resizes properly
- [ ] Application closes cleanly
- [ ] Logs show all operations
- [ ] No crashes or hangs

---

## Phase 7: Final Testing & Polish

### Goals
- Run full test suite
- Fix any remaining bugs
- Verify all requirements met
- Clean up code and comments

### Tasks

#### 7.1 Complete Test Suite

```bash
# Run all tests
pytest tests/ -v --cov=. --cov-report=html

# Should see:
# - tests/test_config.py: 9 tests PASSED
# - tests/test_database.py: 12 tests PASSED
# - tests/test_organizer.py: 8 tests PASSED
# - tests/test_webview.py: 3 tests PASSED
# - tests/test_ollama_client.py: 6 tests PASSED
# - tests/test_chat_component.py: 4 tests PASSED
# - tests/test_integration.py: 6 tests PASSED

# Target: >80% code coverage
```

#### 7.2 Requirements Verification

Create checklist file and verify each requirement:

**File**: `REQUIREMENTS_CHECK.md`

```markdown
# AIOrg Requirements Verification

## Phase 1 POC - Must Have Features

### Core Application
- [ ] Split-pane desktop window with adjustable divider
- [ ] Load configuration from TOML file on startup
- [ ] Comprehensive logging system (all levels work)
- [ ] Both components independently testable

### AI Viewer (Left Pane)
- [ ] Dropdown selector for AI models
- [ ] Webview component for commercial models works
- [ ] Native PyQt chat interface for local models works
- [ ] Automatic mode switching based on model type
- [ ] Ollama API integration with streaming
- [ ] Clear chat history button
- [ ] Pre-configured default models

### Note Organizer (Right Pane)
- [ ] Native PyQt text editor (QTextEdit)
- [ ] Manual save button
- [ ] Full-text search works
- [ ] Search results list (click to load)
- [ ] Toggle between edit and preview modes
- [ ] SQLite database with FTS5
- [ ] Automatic timestamps

### Configuration
- [ ] TOML configuration file loads
- [ ] AI model definitions work
- [ ] Application settings apply
- [ ] Path expansion works (~)

## Functional Requirements

### AI Viewer - Commercial
- [ ] FR-AI-C1: Select commercial model from dropdown
- [ ] FR-AI-C2: Webview loads commercial AI interface
- [ ] FR-AI-C3: Can interact with commercial AI

### AI Viewer - Local
- [ ] FR-AI-L1: Select local model from dropdown
- [ ] FR-AI-L2: Native chat interface displays
- [ ] FR-AI-L3: Ollama API integration works
- [ ] FR-AI-L4: Can copy conversations

### Note Organizer
- [ ] FR-NO-1: Can edit markdown notes
- [ ] FR-NO-2: Can save notes
- [ ] FR-NO-3: Can preview rendered markdown
- [ ] FR-NO-4: Can search notes
- [ ] FR-NO-5: Can create new notes
- [ ] FR-NO-6: Notes are searchable (FTS)

### Configuration
- [ ] FR-CF-1: Application loads configuration
- [ ] FR-CF-2: AI models are configurable
- [ ] FR-CF-3: Application settings work

## Non-Functional Requirements

### Performance
- [ ] NFR-P1: Startup < 3 seconds
- [ ] NFR-P2: Search < 1 second (1000 notes)
- [ ] NFR-P3: UI responsive during operations
- [ ] NFR-P4: Streaming latency < 100ms

### Usability
- [ ] NFR-U1: Standard keyboard shortcuts work
- [ ] NFR-U2: Error messages are clear
- [ ] NFR-U3: Config has inline comments
- [ ] NFR-U4: Components testable independently

### Reliability
- [ ] NFR-R1: Handles Ollama failures gracefully
- [ ] NFR-R2: Database operations are atomic
- [ ] NFR-R3: Config errors don't crash app
- [ ] NFR-R4: Logging captures all errors

## Quality Gates
- [ ] No crashes during normal operation
- [ ] No data loss
- [ ] Search is accurate
- [ ] UI is responsive
- [ ] Logs capture errors with context
```

#### 7.3 Manual Testing Checklist

**File**: `MANUAL_TESTING.md`

```markdown
# Manual Testing Checklist

## Pre-Testing Setup
- [ ] Ollama is running: `ollama serve`
- [ ] Llama2 model is available: `ollama pull llama2`
- [ ] Config file exists with all models
- [ ] Virtual environment activated
- [ ] Dependencies installed

## Application Startup
- [ ] Application starts without errors
- [ ] Window appears at configured size
- [ ] Both panes visible
- [ ] Splitter at correct ratio
- [ ] Dropdown populated with models
- [ ] Logs created in logs/ directory

## AI Viewer - Commercial Models
- [ ] Select "Claude" from dropdown
- [ ] Webview loads claude.ai/chat
- [ ] Can log in to Claude
- [ ] Can chat with Claude normally
- [ ] Can select and copy responses
- [ ] Select "ChatGPT" from dropdown
- [ ] Webview loads chatgpt.com
- [ ] Can log in to ChatGPT
- [ ] Authentication persists on reload

## AI Viewer - Local Models
- [ ] Select "Ollama - Llama 2"
- [ ] Native chat UI appears
- [ ] Input field and buttons visible
- [ ] Type message and click Send
- [ ] Response streams in real-time
- [ ] Can send multiple messages
- [ ] Chat history displays correctly
- [ ] Clear button clears history
- [ ] Can select and copy messages

## AI Viewer - Error Handling
- [ ] Stop Ollama server
- [ ] Try to send message
- [ ] Error message displays
- [ ] UI doesn't freeze
- [ ] Restart Ollama
- [ ] Chat works again

## Note Organizer - Basic Operations
- [ ] Can type in editor
- [ ] Click Save button
- [ ] Success feedback appears
- [ ] Click New button
- [ ] Editor clears
- [ ] Type new content
- [ ] Click Save

## Note Organizer - Preview
- [ ] Type markdown with formatting
  - Headers (#, ##)
  - Lists (-, *)
  - Code blocks (```)
  - Bold, italic
- [ ] Click Preview button
- [ ] Markdown renders correctly
- [ ] Toggle back to Edit
- [ ] Content unchanged

## Note Organizer - Search
- [ ] Save several notes with distinct content
- [ ] Type search query
- [ ] Press Enter or click Search
- [ ] Results appear
- [ ] Results show preview text
- [ ] Click a result
- [ ] Note loads in editor
- [ ] Search for non-existent term
- [ ] No results message appears

## Integration Tests
- [ ] Chat with Claude
- [ ] Copy response
- [ ] Paste into organizer
- [ ] Save note
- [ ] Search for content
- [ ] Note found
- [ ] Switch to Ollama
- [ ] Chat with Ollama
- [ ] Copy response
- [ ] Paste into organizer
- [ ] Save note

## Keyboard Shortcuts
- [ ] Ctrl+S saves note
- [ ] Ctrl+N creates new note
- [ ] Ctrl+P toggles preview
- [ ] Ctrl+F focuses search bar
- [ ] Ctrl+C copies text
- [ ] Ctrl+V pastes text

## UI Behavior
- [ ] Drag splitter left and right
- [ ] Both panes resize
- [ ] Minimum widths respected
- [ ] Resize window
- [ ] Panes scale proportionally
- [ ] Close application
- [ ] No errors on close
- [ ] Reopen application
- [ ] Saved notes still present

## Configuration
- [ ] Edit config.toml
- [ ] Change window size
- [ ] Restart application
- [ ] New window size applied
- [ ] Add new Ollama model
- [ ] Restart application
- [ ] New model in dropdown
- [ ] Change log level to DEBUG
- [ ] Restart application
- [ ] More detailed logs

## Error Scenarios
- [ ] Delete database file while running
- [ ] Try to save note
- [ ] Error handled gracefully
- [ ] Corrupt config.toml
- [ ] Start application
- [ ] Defaults used, error logged
- [ ] Fill disk (if possible)
- [ ] Try to save note
- [ ] Error message shown

## Performance
- [ ] Create 100+ notes (script or manual)
- [ ] Search notes
- [ ] Results < 1 second
- [ ] Application remains responsive
- [ ] Open multiple Ollama conversations
- [ ] No UI freezing
```

#### 7.4 Code Review Checklist

```markdown
# Code Review Checklist

## General
- [ ] No TODO or FIXME comments
- [ ] No commented-out code
- [ ] No debug print() statements
- [ ] All imports used
- [ ] No unused variables
- [ ] Consistent naming conventions

## Documentation
- [ ] All functions have docstrings
- [ ] README.md exists with setup instructions
- [ ] requirements.txt is complete
- [ ] config.toml has inline comments
- [ ] Type hints on all function signatures

## Error Handling
- [ ] All exceptions caught appropriately
- [ ] User-friendly error messages
- [ ] Errors logged with context
- [ ] No bare except: clauses
- [ ] Database operations in try/except

## Security
- [ ] No SQL injection (parameterized queries)
- [ ] No eval() or exec()
- [ ] No hardcoded credentials
- [ ] User input validated

## Testing
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Test coverage > 80%
- [ ] No skipped tests without reason
- [ ] Mock used for external services

## Simplicity
- [ ] No unnecessary abstractions
- [ ] No premature optimization
- [ ] Code is readable
- [ ] Functions are small and focused
- [ ] No features beyond spec
```

#### 7.5 Final Cleanup

```bash
# 1. Run linter (if using)
# black .  # Format code
# flake8 . # Check style

# 2. Remove any debug code
# grep -r "print(" --include="*.py" .
# Remove any found

# 3. Check for TODOs
# grep -r "TODO\|FIXME" --include="*.py" .
# Address or remove

# 4. Update README.md with:
# - Installation instructions
# - Configuration guide
# - Usage examples
# - Troubleshooting

# 5. Verify requirements.txt
# pip freeze > requirements.txt.tmp
# Compare with requirements.txt
# Ensure all needed, no extra

# 6. Test from clean environment
# deactivate
# rm -rf venv
# python -m venv venv
# source venv/bin/activate
# pip install -r requirements.txt
# python main.py
```

### Success Criteria - Final
- [ ] All 48+ unit/integration tests pass
- [ ] All manual tests pass
- [ ] All requirements from PRD verified
- [ ] Code review checklist complete
- [ ] No crashes or data loss
- [ ] Performance meets NFRs
- [ ] Clean code (no debug statements, TODOs)
- [ ] Documentation complete
- [ ] Application usable for daily work

---

## Common Issues & Solutions

### Issue: Ollama connection fails
**Solution**: 
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not, start it
ollama serve

# Check firewall/port
netstat -an | grep 11434
```

### Issue: Database locked
**Solution**: Ensure only one instance of application running. Close database connection properly in closeEvent().

### Issue: Webview doesn't load
**Solution**: Check PyQt6-WebEngine is installed. Verify URL is correct. Check network connection.

### Issue: Tests fail with Qt errors
**Solution**: Install pytest-qt. Use qtbot fixture. Ensure QApplication created in tests.

### Issue: Import errors
**Solution**: Verify virtual environment activated. Check requirements.txt. Run `pip install -r requirements.txt`.

### Issue: Config not loading
**Solution**: Check config.toml syntax with online validator. Verify file path. Check file permissions.

---

## Post-Implementation

### Documentation to Create

1. **README.md** - Setup and usage
2. **ARCHITECTURE.md** - Code structure overview  
3. **CONTRIBUTING.md** - If open-sourcing
4. **CHANGELOG.md** - Version history
5. **LICENSE** - If open-sourcing

### Future Enhancements (Not in POC)

When extending beyond POC, consider:
- Conversation history persistence for local models
- Note tagging system
- Export to multiple formats
- Settings GUI
- Application packaging
- Auto-update mechanism

**But remember**: Keep it simple. Only add features with clear user benefit.

---

## Final Reminder

✅ **DO**:
- Follow specifications exactly
- Keep code simple and readable
- Write tests for everything
- Log important operations
- Handle errors gracefully
- Verify each phase before moving on

❌ **DON'T**:
- Add features not in requirements
- Over-engineer solutions
- Skip tests
- Leave debug code
- Ignore errors
- Rush integration

**Success is building exactly what's specified, nothing more, nothing less.**
