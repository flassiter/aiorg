# AIOrg

A desktop application for interacting with multiple AI models (commercial and local) while maintaining an organized knowledge base of conversations and notes in markdown format.

## Features

- **AI Viewer**: Switch between commercial AI models (Claude, ChatGPT) and local models (Ollama)
- **Note Organizer**: Markdown-based note editor with full-text search
- **Flexible Configuration**: TOML-based configuration for easy customization

## Requirements

- Python 3.10 or higher
- For local AI models: Ollama installed and running

## Installation

1. Clone or download this repository

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

Edit `config.toml` to customize:
- Application settings (theme, window size, log level)
- AI models (add/remove commercial and local models)
- Database location

Example configuration is provided in `config.toml`.

## Running the Application

```bash
python main.py
```

## Project Structure

```
aiorg/
├── main.py                 # Application entry point
├── config.toml             # Configuration file
├── requirements.txt        # Python dependencies
├── ai_viewer/              # AI chat component
│   ├── config.py          # Configuration loading
│   └── ...
├── organizer/              # Note organizer component
│   └── ...
├── tests/                  # Test suite
└── logs/                   # Application logs (created at runtime)
```

## Development Status

This is a proof-of-concept implementation. Components are being built incrementally.

## License

TBD
