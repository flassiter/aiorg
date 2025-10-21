# AIOrg - Product Requirements Document (PRD)

## 1. Product Overview

### 1.1 Purpose
AIOrg is a desktop application that provides a unified interface for interacting with multiple AI models (both commercial and local) while maintaining an organized knowledge base of conversations and notes in markdown format.

### 1.2 Problem Statement
Users who work with multiple AI models face several challenges:
- Switching between different browser tabs/windows for different AI services
- No unified way to access both commercial (Claude, ChatGPT) and local (Ollama) models
- Difficulty organizing and saving important AI conversations
- Lack of searchable knowledge base for AI-generated content

### 1.3 Solution
A split-pane desktop application with:
- **Left pane**: Switchable AI chat interface (commercial models via webview, local models via native UI)
- **Right pane**: Markdown-based note organizer with full-text search

### 1.4 Target Users
- Software developers who use multiple AI models
- Knowledge workers who want to organize AI conversations
- Users with local AI infrastructure (Ollama)
- People comfortable with configuration files

### 1.5 Success Metrics
- User can switch between AI models in under 2 clicks
- User can save and retrieve notes in under 3 clicks
- Search returns relevant results in under 1 second
- Application uses less memory than having multiple browser tabs open

---

## 2. MoSCoW Prioritization

### 2.1 MUST HAVE (Phase 1 - POC)

**Core Application**
- Split-pane desktop window with adjustable divider
- Load configuration from TOML file on startup
- Comprehensive logging system (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Both components must be independently testable

**AI Viewer (Left Pane)**
- Dropdown selector for AI models
- Webview component for commercial models (Claude, ChatGPT)
- Native PyQt chat interface for local models (Ollama)
- Automatic mode switching based on model type
- Direct Ollama API integration with streaming responses
- Clear chat history button for local models
- Pre-configured default models (Claude, ChatGPT, Ollama)

**Note Organizer (Right Pane)**
- Native PyQt text editor (QTextEdit) for markdown editing
- Manual save button to persist notes to database
- Full-text search across all saved notes
- Search results list (click to load note)
- Toggle between source (edit) and rendered (preview) modes
- SQLite database with FTS5 for fast search
- Automatic timestamps (created_at, updated_at)

**Configuration**
- TOML configuration file for all settings
- AI model definitions (name, type, url, model parameter)
- Application settings (theme, window size, logging level)
- Path expansion support (~ for home directory)

### 2.2 SHOULD HAVE (Phase 2)

**Note Management**
- Delete note functionality
- New note button (clear editor)
- Note list view with previews
- Export notes to .md files

**UI Improvements**
- Connection status indicator for Ollama
- Better error messages and user feedback
- Dark/light theme switching (if trivial to implement)

**Local Model Features**
- Conversation history persistence for local chats
- System prompt configuration
- Multiple Ollama models in config

### 2.3 COULD HAVE (Future)

**Advanced Features**
- Auto-save for local model conversations
- Note tagging or folder organization
- Code block syntax highlighting in markdown preview
- Attachments/images in notes
- Note templates
- Export entire database

**Integration**
- Browser extension for web clipping
- Sync across devices
- API for external tools

### 2.4 WON'T HAVE (Explicitly Out of Scope)

**Not Implementing**
- ❌ Auto-save for notes (manual save only keeps it simple)
- ❌ Syntax highlighting in markdown editor (adds complexity, can swap later)
- ❌ Automatic chat capture from commercial models (cross-origin restrictions, fragile)
- ❌ Note version history (just timestamps)
- ❌ Multiple notes open simultaneously (tabs/split views add complexity)
- ❌ GUI for settings (TOML file editing is sufficient)
- ❌ GUI for adding/removing AI models (TOML file editing is sufficient)
- ❌ Application packaging/installers (source code distribution for POC)
- ❌ Separate web UI for Ollama (native chat UI is self-contained)
- ❌ LLM parameter controls (temperature, top_p, etc.) - use Ollama defaults
- ❌ Custom themes/styling (system default is sufficient)
- ❌ Conversation branching or threading
- ❌ Multi-user support or authentication
- ❌ Cloud storage integration
- ❌ Mobile versions

---

## 3. Functional Requirements

### 3.1 AI Viewer - Commercial Models

**FR-AI-C1**: User can select a commercial AI model from dropdown
- Dropdown shows all commercial models from config
- Selection loads model URL in webview

**FR-AI-C2**: Webview loads commercial AI interface
- Must support claude.ai/chat
- Must support chatgpt.com
- Authentication handled within webview (cookies persist)

**FR-AI-C3**: User can interact with commercial AI
- Full functionality of original website
- Copy/paste works normally
- User can manually copy conversations to organizer

### 3.2 AI Viewer - Local Models

**FR-AI-L1**: User can select a local AI model from dropdown
- Dropdown shows all local models from config
- Selection switches to native chat interface

**FR-AI-L2**: Native chat interface for Ollama
- Text input field for user messages
- Send button to submit messages
- Chat history display (QTextBrowser)
- Streaming response display (text appears as it's generated)
- Clear history button

**FR-AI-L3**: Ollama API integration
- Connect to configured Ollama endpoint
- Send messages using /api/chat endpoint
- Handle streaming responses
- Display error if Ollama not reachable
- Use model name from configuration

**FR-AI-L4**: User can copy conversations
- Select text in chat history
- Copy to clipboard using Ctrl+C or right-click menu
- Paste into organizer

### 3.3 Note Organizer

**FR-NO-1**: User can edit markdown notes
- QTextEdit provides plain text editing
- No auto-save (user must click save)
- Full keyboard shortcuts (Ctrl+C, Ctrl+V, Ctrl+Z)

**FR-NO-2**: User can save notes
- Save button writes content to database
- New note gets created_at timestamp
- Existing note gets updated_at timestamp
- User feedback on successful save

**FR-NO-3**: User can preview rendered markdown
- Toggle button switches between edit and preview modes
- Preview displays HTML-rendered markdown in QTextBrowser
- Preview is read-only
- Can toggle back to edit mode

**FR-NO-4**: User can search notes
- Search bar accepts text query
- Search executes on Enter key or search button
- Results appear in list widget below search bar
- Each result shows note snippet/preview
- Click result to load note into editor

**FR-NO-5**: User can create new notes
- New note button clears editor
- No unsaved changes warning (keep simple)
- Ready for new content

**FR-NO-6**: Notes are searchable
- Full-text search across all note content
- SQLite FTS5 provides search functionality
- Search is case-insensitive
- Results ranked by relevance

### 3.4 Configuration

**FR-CF-1**: Application loads configuration on startup
- Read config.toml from application directory
- Parse AI model definitions
- Parse application settings
- Provide sensible defaults for missing values
- Log configuration errors

**FR-CF-2**: AI models are configurable
- Commercial models require: name, type, url
- Local models require: name, type, url, model
- Support multiple models of each type
- Models appear in dropdown in config order

**FR-CF-3**: Application settings are configurable
- Window dimensions (width, height)
- Splitter ratio (left/right pane split)
- Theme preference (dark, light, system)
- Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Database path (with ~ expansion)

---

## 4. Non-Functional Requirements

### 4.1 Performance
- **NFR-P1**: Application startup time < 3 seconds
- **NFR-P2**: Search results return in < 1 second for 1000+ notes
- **NFR-P3**: UI remains responsive during Ollama API calls (use threading)
- **NFR-P4**: Ollama streaming responses appear with < 100ms latency

### 4.2 Usability
- **NFR-U1**: UI follows standard desktop conventions (familiar keyboard shortcuts)
- **NFR-U2**: Error messages are clear and actionable
- **NFR-U3**: Configuration file has inline comments explaining options
- **NFR-U4**: Both components can be tested independently

### 4.3 Reliability
- **NFR-R1**: Application handles Ollama connection failures gracefully
- **NFR-R2**: Database operations are atomic (no partial saves)
- **NFR-R3**: Configuration errors don't crash application (fall back to defaults)
- **NFR-R4**: Logging captures all errors with stack traces

### 4.4 Maintainability
- **NFR-M1**: Code is modular with clear component boundaries
- **NFR-M2**: Components can be swapped (e.g., different editor widget)
- **NFR-M3**: Database schema supports migrations
- **NFR-M4**: Comprehensive logging aids debugging

### 4.5 Portability
- **NFR-PO1**: Runs on Windows, macOS, Linux
- **NFR-PO2**: Dependencies are standard Python packages
- **NFR-PO3**: Configuration uses portable paths (~ expansion)

### 4.6 Simplicity
- **NFR-S1**: No feature creep - stick to specified requirements
- **NFR-S2**: Prefer simple solutions over complex ones
- **NFR-S3**: Manual configuration over GUI when reasonable
- **NFR-S4**: No unnecessary abstractions or frameworks

---

## 5. User Stories

### 5.1 AI Interaction
**US-1**: As a developer, I want to switch between Claude and local Llama2 without opening different applications, so I can choose the best model for each task.

**US-2**: As a user, I want to chat with Ollama directly in the app without running a separate web UI, so I have fewer dependencies to manage.

**US-3**: As a user, I want to see Ollama responses stream in real-time, so I know the model is working and can read partial responses.

### 5.2 Note Management
**US-4**: As a researcher, I want to save important AI-generated insights to my knowledge base, so I can reference them later.

**US-5**: As a writer, I want to search my saved conversations by keyword, so I can quickly find specific information.

**US-6**: As a user, I want to preview my markdown notes with proper formatting, so I can verify they look correct.

### 5.3 Configuration
**US-7**: As a power user, I want to add custom Ollama models to the dropdown by editing a config file, so I can work with specialized models.

**US-8**: As a developer, I want comprehensive logs when things go wrong, so I can debug issues quickly.

---

## 6. Data Requirements

### 6.1 Data Storage
- Notes stored in SQLite database (~/.aiorg/aiorg.db)
- Full-text search index maintained automatically
- No conversation history stored for commercial models
- No conversation history for local models (Phase 1)

### 6.2 Data Schema
```sql
notes:
  - id (integer, primary key, auto-increment)
  - content (text, not null)
  - created_at (timestamp, default current_timestamp)
  - updated_at (timestamp, default current_timestamp)

notes_fts (FTS5 virtual table):
  - content (indexed)
  - rowid (linked to notes.id)
```

### 6.3 Data Retention
- Notes persist indefinitely unless manually deleted
- No automatic cleanup or archiving
- User responsible for managing database size

### 6.4 Data Export
- Database is standard SQLite (can be backed up manually)
- Individual note export to .md files (Phase 2)

---

## 7. Security & Privacy

### 7.1 Local Data
- All notes stored locally on user's machine
- No cloud sync or external transmission
- User controls database location via config

### 7.2 Commercial AI Authentication
- Authentication happens in webview (cookies)
- Application does not access or store credentials
- User logs in directly to AI services

### 7.3 Ollama Communication
- Local HTTP communication (localhost)
- No authentication assumed (Ollama default)
- User responsible for Ollama security configuration

---

## 8. Assumptions & Dependencies

### 8.1 Assumptions
- User has Python 3.10+ installed
- User has Ollama installed and running (for local models)
- User has active subscriptions to commercial AI services (if using them)
- User is comfortable editing TOML files
- User is on desktop environment (not mobile)

### 8.2 Dependencies
- PyQt6 (GUI framework)
- markdown (Python library for rendering)
- requests or httpx (HTTP client for Ollama)
- SQLite (included with Python)
- tomli or toml (TOML parsing)

### 8.3 External Services
- Claude.ai (commercial, optional)
- ChatGPT.com (commercial, optional)
- Ollama API (local, optional)

---

## 9. Constraints

### 9.1 Technical Constraints
- Must use PyQt6 (not PyQt5, PySide, or other frameworks)
- Must use SQLite for persistence (no PostgreSQL, MongoDB, etc.)
- Must use TOML for configuration (not JSON, YAML, etc.)
- Cannot access DOM of commercial AI websites (cross-origin restrictions)

### 9.2 Design Constraints
- Keep it simple - no unnecessary features
- Components must be independently testable
- Configuration via files only (no settings GUI in Phase 1)
- Manual save only (no auto-save in Phase 1)

### 9.3 Business Constraints
- POC only - no packaging or distribution
- No marketing or user documentation (just technical docs)
- Developer is primary user (optimize for technical users)

---

## 10. Testing Requirements

### 10.1 Unit Testing
- All database operations must have unit tests
- Configuration parsing must have unit tests
- Markdown rendering must have unit tests
- Ollama client must have unit tests (with mocking)

### 10.2 Integration Testing
- Component integration (AI viewer + organizer in main window)
- Database operations with real SQLite database
- Config loading with sample TOML files

### 10.3 Manual Testing
- Each AI model type loads correctly
- Chat interface responds to user input
- Notes save and load correctly
- Search returns expected results
- Both components work independently

---

## 11. Acceptance Criteria

### 11.1 Phase 1 (POC) Complete When:
- [ ] Application starts without errors
- [ ] Can select commercial model and webview loads
- [ ] Can select local model and native chat appears
- [ ] Can send message to Ollama and see streamed response
- [ ] Can type markdown in editor
- [ ] Can save note and it persists to database
- [ ] Can search notes and results appear
- [ ] Can click search result and note loads
- [ ] Can toggle to preview mode and see rendered markdown
- [ ] Configuration loads from TOML file
- [ ] Logging works at all levels
- [ ] Both components run independently for testing
- [ ] All unit tests pass
- [ ] All integration tests pass

### 11.2 Quality Gates
- No crashes during normal operation
- No data loss (saves are atomic)
- Search is accurate (no false positives in top 10 results)
- UI is responsive (no freezing during operations)
- Logs capture all errors with sufficient context

---

## 12. Out of Scope (Detailed)

These items will **NOT** be implemented to keep the project simple and focused:

### 12.1 Advanced AI Features
- Custom system prompts for local models
- Temperature, top_p, or other LLM parameters
- Conversation branching or forking
- Model comparison (side-by-side)
- Cost tracking for commercial APIs
- Token counting

### 12.2 Advanced Note Features
- Rich text editing (bold, italic, links in editor)
- Syntax highlighting in markdown editor
- Live markdown preview (split view showing both)
- Note templates
- Folders or hierarchical organization
- Tags or categories
- Note linking (wiki-style)
- Version history or undo beyond session
- Collaborative editing

### 12.3 UI Enhancements
- Customizable themes or styling
- Multiple window support
- Drag and drop between panes
- Keyboard shortcuts customization
- Toolbar customization
- Status bar
- Notifications or alerts

### 12.4 Data Features
- Cloud sync
- Database encryption
- Automatic backups
- Import from other formats
- Export to PDF or HTML
- Data compression

### 12.5 Integration Features
- Browser extension
- REST API for external tools
- Plugin system
- Webhooks
- Email integration
- Calendar integration

### 12.6 Enterprise Features
- Multi-user support
- User authentication
- Role-based access control
- Audit logging
- Compliance features

---

## 13. Success Criteria Summary

**The POC is successful if:**
1. A developer can use it daily to interact with multiple AI models
2. Notes can be saved, searched, and retrieved reliably
3. The application is simpler to use than browser tabs
4. Both components work independently for testing
5. Code is maintainable and well-documented
6. No unnecessary features were added

**The POC is NOT successful if:**
- It crashes frequently
- Search is slow or inaccurate
- UI is confusing or non-standard
- Code is monolithic or hard to test
- Features were added beyond the spec
- Ollama integration requires separate web UI
