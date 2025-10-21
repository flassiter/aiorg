# AIOrg - AI Organizer
## Technical Specification - Proof of Concept

### Overview
Desktop application with split-pane interface: AI chat on left, markdown-based note organizer on right.

---

## Architecture

### Tech Stack
- **Framework**: PyQt6
- **Web Components**: QWebEngineView (both panes)
- **Database**: SQLite with FTS5 (full-text search)
- **Configuration**: TOML format
- **Python**: 3.10+
- **Logging**: Python logging module with configurable levels

### Design Principles
- **Component Separation**: AI viewer and organizer are independent components
- **Testability**: Each component can run and be tested standalone
- **Abstraction**: UI components (markdown editor, etc.) designed to be swappable
- **Simplicity**: POC focuses on core functionality, extensibility for future enhancements

### Project Structure
```
aiorg/
├── main.py                  # Main application (combines components)
├── ai_viewer/
│   ├── __init__.py
│   ├── viewer.py            # Main AI viewer widget with mode switching
│   ├── webview.py           # Commercial AI webview component
│   ├── chat_ui.py           # Native chat UI for local models
│   ├── ollama_client.py     # Ollama API client
│   └── config.py            # Load AI models from config
├── organizer/
│   ├── __init__.py
│   ├── organizer.py         # Note organizer main widget
│   ├── database.py          # SQLite operations
│   └── markdown_renderer.py # Markdown to HTML conversion
├── config.toml              # AI models and application settings
├── requirements.txt
└── aiorg.db                 # Created at runtime in ~/.aiorg/
```

### Core Components
1. **Main Application** (main.py): QMainWindow with QSplitter combining both components
2. **AI Viewer Component** (ai_viewer/): Independent widget with dual-mode support
   - Webview for commercial models (Claude, ChatGPT)
   - Native chat UI for local models (Ollama)
3. **Organizer Component** (organizer/): Independent widget with native PyQt interface
   - QTextEdit for markdown editing
   - QTextBrowser for preview
   - Direct database access (no web channel needed)
4. **Database Layer** (organizer/database.py): SQLite operations abstracted
5. **Ollama Client** (ai_viewer/ollama_client.py): API integration for local models
6. **Configuration** (config.toml): All settings and AI model definitions

### Component Independence
Each component can be developed and tested standalone:
- `python -m ai_viewer.viewer` runs AI viewer independently
- `python -m organizer.organizer` runs organizer independently
- Both expose reusable widgets that main.py integrates

---

## Left Pane: AI Chat

### UI Elements
- **Dropdown**: Model selector (above chat interface)
- **Chat Interface**: Either webview (commercial) or native PyQt chat UI (local)

### Dual-Mode Design

**Commercial Models (Webview Mode)**
- Uses QWebEngineView to load vendor's chat interface
- Full featured UI from vendor (Claude.ai, ChatGPT)
- Authentication handled in webview (persists via cookies)
- No iframe restrictions with native webview

**Local Models (Native Chat Mode)**
- Custom PyQt chat interface calling Ollama API directly
- Components:
  - `QTextBrowser`: Display chat history (read-only, scrollable)
  - `QLineEdit`: User message input
  - `QPushButton`: Send button
  - Status indicator for Ollama connection
- Direct API calls to Ollama (no separate web UI needed)
- Model selection via config file (manual switching)

### Model Configuration
Each AI model has:
- `name` (string): Display name in dropdown
- `type` (string): 'commercial' or 'local'
- `url` (string): URL to load (commercial) or API endpoint (local)
- `model` (string, optional): Specific model name for local (e.g., "llama2", "codellama")

**Storage**: TOML configuration file (`config.toml`)

```toml
[[ai_models]]
name = "Claude"
type = "commercial"
url = "https://claude.ai/chat"

[[ai_models]]
name = "ChatGPT"
type = "commercial"
url = "https://chatgpt.com"

[[ai_models]]
name = "Ollama - Llama 2"
type = "local"
url = "http://localhost:11434"
model = "llama2"

[[ai_models]]
name = "Ollama - CodeLlama"
type = "local"
url = "http://localhost:11434"
model = "codellama"
```

**Management**: Manual editing of config file (no UI for POC)

### Behavior
**When commercial model selected:**
- Swap to webview widget
- Load URL in webview

**When local model selected:**
- Swap to native chat widget
- Connect to Ollama API endpoint
- Use configured model name for generation

### Ollama API Integration
**Endpoint**: POST `/api/chat` (streaming)
**Request format**:
```json
{
  "model": "llama2",
  "messages": [
    {"role": "user", "content": "Hello!"}
  ],
  "stream": true
}
```

**Response**: Server-sent events (newline-delimited JSON)
**Library**: `requests` or `httpx` for HTTP calls

### Native Chat UI Details
**POC features:**
- Simple text input and send
- Display conversation history
- Streaming responses (append chunks as they arrive)
- Clear history button
- Connection status indicator

**Deferred features:**
- System prompts
- Temperature/parameter controls
- Conversation persistence (user can save to organizer instead)
- Model switching UI (use config file)

### Default Models
- Claude (claude.ai/chat) - commercial
- ChatGPT (chatgpt.com) - commercial
- Ollama with Llama2 (localhost:11434) - local, assumes Ollama server running

---

## Right Pane: Note Organizer

### UI Elements
Native PyQt widgets (not webview):
- **Text editor**: QTextEdit for markdown source editing
- **Preview**: QTextBrowser for rendered markdown (toggle view)
- **Save button**: QPushButton to save current note
- **New note button**: QPushButton to clear editor
- **Search bar**: QLineEdit for full-text search
- **Results list**: QListWidget showing search results (hidden when not searching)
- **Toolbar**: QToolBar with common actions

### Note Schema
```sql
notes:
  - id (integer, primary key)
  - content (text)
  - created_at (timestamp)
  - updated_at (timestamp)
```

### Features
- **Edit mode**: QTextEdit with plain text (markdown source)
- **Preview mode**: QTextBrowser showing rendered HTML (read-only)
- **Toggle**: Switch between edit/preview modes
- **Save**: Manual save via button (no auto-save)
- **Search**: SQLite FTS5 for full-text search
- **Results**: Click result in QListWidget → loads note into editor
- **Single note**: One note displayed at a time
- **Timestamps**: Auto-managed on create/update

### Markdown Rendering
**Library**: `markdown` (Python library)
**Process**: 
1. User toggles to preview mode
2. Python converts markdown text to HTML using `markdown.markdown()`
3. Display HTML in QTextBrowser

**Styling**: Can apply CSS to QTextBrowser for consistent look

### Component Design
**Abstraction**: Editor logic separated from widget implementation
- Could swap QTextEdit for QPlainTextEdit or custom widget later
- Markdown library is pluggable
- Database operations abstracted in separate module

---

## Data Storage

### SQLite Schema
```sql
-- Notes storage
CREATE TABLE notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Full-text search index
CREATE VIRTUAL TABLE notes_fts USING fts5(
    content,
    content=notes,
    content_rowid=id
);

-- Triggers to keep FTS in sync
CREATE TRIGGER notes_ai AFTER INSERT ON notes BEGIN
    INSERT INTO notes_fts(rowid, content) VALUES (new.id, new.content);
END;

CREATE TRIGGER notes_ad AFTER DELETE ON notes BEGIN
    DELETE FROM notes_fts WHERE rowid = old.id;
END;

CREATE TRIGGER notes_au AFTER UPDATE ON notes BEGIN
    UPDATE notes_fts SET content = new.content WHERE rowid = new.id;
END;

-- Runtime settings (UI state, not user-editable settings)
CREATE TABLE app_state (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Database Location**: `~/.aiorg/aiorg.db`

**Note**: AI models and user settings stored in `config.toml`, not database

---

## Chat Transfer Feature

### Problem
Automatically capture entire chat conversation from left pane → save to right pane.

### Challenges
- Commercial AI webviews are isolated (cross-origin restrictions)
- Cannot reliably inject JavaScript into claude.ai or chatgpt.com
- No direct property access to webview contents
- Methods would be fragile and break with site updates

### POC Decision: Manual Copy-Paste
- User manually copies chat content from left pane
- Pastes into right pane markdown editor
- Clicks save to store in database
- Simple, reliable, no maintenance burden

### Future Considerations
If demand exists, could explore:
- JavaScript injection via `QWebEngineView.runJavaScript()` (fragile)
- Browser extension companion (complex)
- Screen scraping/OCR (unreliable)
- API integration where available (local models only)

**Recommendation**: Keep manual for POC. Most users comfortable with copy-paste.

---

## Communication Layer

### Direct Python Access
Since organizer uses native PyQt widgets, no special communication layer needed:
- UI widgets directly call database functions
- No web channel, no JavaScript bridge
- Simple Python function calls throughout

### Ollama API Client
For local AI models, direct HTTP communication:

```python
class OllamaClient:
    def chat(self, model: str, messages: list, callback) -> None:
        """
        Stream chat responses from Ollama
        callback(chunk: str) called for each response chunk
        """
```

**Implementation**: Uses `requests` or `httpx` with streaming
**Threading**: API calls run in QThread to avoid blocking UI

---

## UI Layout

### Window Structure
- **Splitter**: QSplitter (adjustable divider)
- **Initial split**: 50/50 (configurable in config.toml)
- **Minimum sizes**: Left pane min 400px, right pane min 300px
- **Window size**: 1400x800 default (configurable in config.toml)

### Styling
- **Theme**: Dark theme preferred (use system default if easy to implement)
- **Theme switching**: Include if PyQt provides out-of-the-box, otherwise defer
- **Consistency**: Both webviews styled similarly via CSS

### Settings Storage
All user-configurable settings in `config.toml`:
```toml
[settings]
theme = "dark"              # "dark", "light", or "system"
log_level = "DEBUG"         # DEBUG, INFO, WARNING, ERROR, CRITICAL
database_path = "~/.aiorg/aiorg.db"
window_width = 1400
window_height = 800
split_ratio = 0.5           # Left pane ratio (0.0-1.0)
```

**No settings UI**: All configuration via manual TOML editing

---

## POC Scope

### Must Have (Phase 1)
- [ ] Project structure with separated components (ai_viewer, organizer)
- [ ] TOML configuration file with AI models and settings
- [ ] Comprehensive logging system (DEBUG, INFO, WARNING, ERROR, CRITICAL levels)
- [ ] Main window with QSplitter combining both components
- [ ] AI Viewer: dropdown for model selection
- [ ] AI Viewer: webview component for commercial models
- [ ] AI Viewer: native chat UI component for local models (QTextBrowser + QLineEdit)
- [ ] AI Viewer: mode switching based on model type
- [ ] AI Viewer: Ollama API client with streaming support
- [ ] AI Viewer: standalone test mode
- [ ] Organizer: native PyQt widget with QTextEdit for editing
- [ ] Organizer: QTextBrowser for markdown preview
- [ ] Organizer: toggle between edit/preview modes
- [ ] Organizer: standalone test mode
- [ ] SQLite database with notes table and FTS5
- [ ] Save note functionality (manual save button)
- [ ] Load/display single note
- [ ] Full-text search across all notes
- [ ] Search results list (QListWidget, click to load note)
- [ ] Default AI models pre-configured (Claude, ChatGPT, Ollama)

### Nice to Have (Phase 2)
- [ ] Delete note functionality
- [ ] Clear editor / new note button
- [ ] Note list view (browse all notes with titles/previews)
- [ ] Export notes (to .md files)
- [ ] Theme switching (if PyQt makes it easy)
- [ ] Better error handling and user feedback
- [ ] Connection status for Ollama (visual indicator)
- [ ] Conversation history persistence for local models
- [ ] System prompt configuration for local models

### Explicitly Deferred
- ❌ Auto-save (manual save only)
- ❌ Syntax highlighting in editor (plain QTextEdit, but designed for easy component swap)
- ❌ Chat transfer/capture from commercial models (manual copy-paste)
- ❌ Note versioning
- ❌ Multiple notes open simultaneously (single note at a time)
- ❌ Settings UI (TOML file editing only)
- ❌ AI model configuration UI (TOML file editing only)
- ❌ Application packaging/distribution
- ❌ Separate web UI for local models (native chat UI instead)
- ❌ Temperature/parameter controls for local models

### Future Considerations
- [ ] Advanced chat capture methods
- [ ] Note tagging or folder organization
- [ ] Sync across devices
- [ ] Web clipper functionality
- [ ] Code block syntax highlighting in markdown
- [ ] Attachments/images in notes
- [ ] Note templates

---

## Decisions Made

### Architecture
✅ **Component separation**: AI viewer and organizer are independent, testable components
✅ **Configuration format**: TOML for all settings and AI model definitions
✅ **No settings UI**: Manual TOML editing only for POC
✅ **Logging**: Extensive logging with configurable levels from Phase 1
✅ **Native PyQt for organizer**: No webview, direct widget access, simpler implementation
✅ **Dual-mode AI viewer**: Webview for commercial, native chat UI for local models

### AI Viewer
✅ **Model configuration**: TOML file, no UI for add/edit/remove
✅ **Default models**: Claude, ChatGPT, Ollama (assumes user has Ollama running)
✅ **Commercial models**: QWebEngineView with direct authentication
✅ **Local models**: Native PyQt chat interface (QTextBrowser + QLineEdit)
✅ **No separate web UI**: Self-contained, calls Ollama API directly
✅ **Model switching**: Automatic based on model type in config

### Organizer
✅ **Save mechanism**: Manual save button only (no auto-save)
✅ **Editor**: QTextEdit (native PyQt widget)
✅ **Preview**: QTextBrowser with markdown-to-HTML conversion
✅ **Syntax highlighting**: Deferred (not needed for POC)
✅ **Note management**: Single note at a time (no tabs or multiple notes)
✅ **Versioning**: No version history (just created/updated timestamps)
✅ **Direct database access**: No web channel needed

### Features
✅ **Chat transfer**: Manual copy-paste (no automatic capture)
✅ **Theme**: Dark theme preferred, system default acceptable
✅ **Theme switching**: Include only if PyQt makes it trivial
✅ **Markdown preview**: Toggle between edit mode and rendered view

### Development
✅ **Packaging**: Not needed for POC (source code distribution)
✅ **Testing**: Both components must be runnable standalone
✅ **Design pattern**: Abstract UI components for future swapping (markdown editor, etc.)

---

## Configuration File

### Complete config.toml Example
```toml
# Application settings
[settings]
theme = "dark"                          # "dark", "light", or "system"
log_level = "DEBUG"                     # DEBUG, INFO, WARNING, ERROR, CRITICAL
database_path = "~/.aiorg/aiorg.db"    # Can use ~ for home directory
window_width = 1400
window_height = 800
split_ratio = 0.5                       # Left pane ratio (0.0-1.0)

# AI Model definitions
[[ai_models]]
name = "Claude"
type = "commercial"
url = "https://claude.ai/chat"

[[ai_models]]
name = "ChatGPT"
type = "commercial"
url = "https://chatgpt.com"

[[ai_models]]
name = "Ollama - Llama 2"
type = "local"
url = "http://localhost:11434"
model = "llama2"

[[ai_models]]
name = "Ollama - CodeLlama"
type = "local"
url = "http://localhost:11434"
model = "codellama"

# Users can add more models by adding additional [[ai_models]] sections
# For commercial: only name, type="commercial", and url required
# For local: name, type="local", url (API endpoint), and model required
```

**Location**: `./config.toml` (same directory as application)
**Loading**: Application reads on startup, validates, and provides sensible defaults for missing values

---

## Development Phases

### Phase 1: Core Functionality (POC)
- Basic UI skeleton
- Webview integration
- Simple note save/load
- Search implementation

### Phase 2: Polish
- Markdown preview
- Better search UI
- Note management
- Configuration UI

### Phase 3: Advanced
- Chat capture
- Advanced organization
- Export/import
- Additional features

---

## Implementation Notes

### Ready for Development
- All key architectural decisions have been made
- Component boundaries are clear and testable
- Configuration structure is defined
- Database schema is finalized
- POC scope is well-defined
- Native PyQt implementation simplifies architecture significantly

### Development Priority
1. **Setup**: Project structure, config loading, logging
2. **Database**: SQLite schema and basic operations
3. **Organizer component**: Build and test standalone (native PyQt widgets)
4. **AI Viewer - Webview**: Build commercial model support (test standalone)
5. **AI Viewer - Native Chat**: Build Ollama integration (test standalone)
6. **Integration**: Combine components in main application
7. **Testing**: Verify both components work together and mode switching works

### Key Technical Points
- **Ollama streaming**: Use QThread for API calls, emit signals for UI updates
- **TOML parsing**: Use `tomli` (Python 3.11+) or `toml` library
- **Logging**: Use Python's `logging` module with file and console handlers
- **Path expansion**: Handle `~` in config paths properly
- **Component abstraction**: Keep editor logic separate for easy widget swapping
- **Mode switching**: AI viewer must cleanly swap between webview and native chat widgets
- **Markdown rendering**: Use Python `markdown` library, style HTML output for QTextBrowser

### Technical Advantages of Native PyQt
- **Simpler**: No web channel, no JS/Python bridge
- **Lighter**: Less resource usage than multiple Chromium instances
- **Direct access**: Database and file operations are straightforward
- **Better integration**: Native keyboard shortcuts, copy/paste, etc.
- **Easier debugging**: Standard Python debugging, no multi-process complexity

### Success Criteria for POC
- [ ] Can load and switch between AI models in left pane
- [ ] Webview loads for commercial models, native chat for local
- [ ] Can send messages to Ollama and receive streaming responses
- [ ] Can create, save, and search notes in right pane
- [ ] Can toggle between markdown source and rendered preview
- [ ] Both components work independently for testing
- [ ] Configuration loads from TOML file correctly
- [ ] Logging provides useful debugging information
- [ ] Application state persists (window size, splitter position)
- [ ] Full-text search returns relevant results quickly
