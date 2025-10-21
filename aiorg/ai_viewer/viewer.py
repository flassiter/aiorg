"""AI Viewer widget with mode switching.

This module provides the main AI viewer widget that manages switching
between webview (commercial models) and native chat UI (local models).
"""

import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
    QStackedWidget, QLabel
)
from PyQt6.QtCore import Qt

from ai_viewer.webview_component import WebviewComponent
from ai_viewer.chat_component import ChatComponent
from ai_viewer.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


class AIViewerWidget(QWidget):
    """Main AI viewer widget with mode switching.

    Manages switching between webview (commercial models) and
    native chat UI (local models) based on selected AI model type.
    """

    def __init__(self, config: dict = None, parent=None):
        """Initialize AI viewer with configuration.

        Args:
            config: Configuration dictionary with 'ai_models' key
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        logger.info("Initializing AIViewerWidget")

        # Store configuration
        self.config = config or {}
        self.models = []
        self.current_model = None

        # Initialize UI
        self.setup_ui()

        # Load models from config if provided
        if self.config.get('ai_models'):
            self.load_models(self.config['ai_models'])

        logger.info("AIViewerWidget initialized successfully")

    def setup_ui(self):
        """Create UI layout with dropdown and stacked widget."""
        logger.debug("Setting up AIViewerWidget UI")

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Top bar with model selector
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)

        # Label for dropdown
        model_label = QLabel("AI Model:")
        top_bar.addWidget(model_label)

        # Dropdown for model selection
        self.model_dropdown = QComboBox()
        self.model_dropdown.currentIndexChanged.connect(self.on_model_changed)
        top_bar.addWidget(self.model_dropdown, stretch=1)

        layout.addLayout(top_bar)

        # Stacked widget for different modes
        self.stacked_widget = QStackedWidget()

        # Create webview component for commercial models
        self.webview_component = WebviewComponent(self)
        self.webview_index = self.stacked_widget.addWidget(self.webview_component)

        # Create native chat component for local models
        self.chat_component = ChatComponent(self)
        self.chat_index = self.stacked_widget.addWidget(self.chat_component)

        layout.addWidget(self.stacked_widget, stretch=1)

        logger.debug("AIViewerWidget UI setup complete")

    def load_models(self, models: list[dict]):
        """Populate dropdown with AI models from config.

        Args:
            models: List of model dictionaries with keys:
                    - name: Display name
                    - type: "commercial" or "local"
                    - url: Model URL or API endpoint
                    - model: (optional) Model name for local models
        """
        logger.info(f"Loading {len(models)} AI models")

        self.models = models

        # Clear existing items
        self.model_dropdown.clear()

        # Add models to dropdown
        for model in models:
            name = model.get('name', 'Unknown')
            self.model_dropdown.addItem(name)
            logger.debug(f"Added model to dropdown: {name} (type: {model.get('type')})")

        # Select first model if available
        if models:
            self.model_dropdown.setCurrentIndex(0)
            logger.info(f"Selected default model: {models[0].get('name')}")

    def on_model_changed(self, index: int):
        """Handle model selection change - switch modes.

        Args:
            index: Index of selected model in dropdown
        """
        if index < 0 or index >= len(self.models):
            logger.warning(f"Invalid model index: {index}")
            return

        model = self.models[index]
        self.current_model = model
        model_name = model.get('name', 'Unknown')
        model_type = model.get('type', 'unknown')

        logger.info(f"Model changed to: {model_name} (type: {model_type})")

        # Switch mode based on model type
        if model_type == 'commercial':
            # Switch to webview
            self.stacked_widget.setCurrentIndex(self.webview_index)
            logger.debug("Switched to webview mode")

            # Load URL
            url = model.get('url', '')
            if url:
                self.webview_component.load_url(url)
                logger.info(f"Loading commercial model URL: {url}")
            else:
                logger.error(f"No URL specified for commercial model: {model_name}")

        elif model_type == 'local':
            # Switch to native chat
            self.stacked_widget.setCurrentIndex(self.chat_index)
            logger.debug("Switched to native chat mode")

            # Configure Ollama client
            base_url = model.get('url', 'http://localhost:11434')
            model_name_param = model.get('model', 'llama2')

            logger.info(f"Configuring local model: {model_name}")
            logger.debug(f"Ollama URL: {base_url}, Model: {model_name_param}")

            # Create Ollama client and configure chat component
            ollama_client = OllamaClient(base_url)
            self.chat_component.set_ollama_client(ollama_client, model_name_param)

        else:
            logger.error(f"Unknown model type: {model_type}")

    def get_current_model(self) -> dict:
        """Return currently selected model configuration.

        Returns:
            dict: Current model configuration or empty dict if none selected
        """
        return self.current_model or {}


# Standalone test mode
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    # Setup logging for test mode
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger.info("Starting AIViewerWidget standalone test")

    # Create test configuration
    test_config = {
        'ai_models': [
            {
                'name': 'Claude',
                'type': 'commercial',
                'url': 'https://claude.ai/chat'
            },
            {
                'name': 'ChatGPT',
                'type': 'commercial',
                'url': 'https://chatgpt.com'
            },
            {
                'name': 'Ollama - Llama 2',
                'type': 'local',
                'url': 'http://localhost:11434',
                'model': 'llama2'
            }
        ]
    }

    # Create application
    app = QApplication(sys.argv)

    # Create viewer widget
    viewer = AIViewerWidget(config=test_config)
    viewer.setWindowTitle("AIViewerWidget Test")
    viewer.resize(1200, 800)

    # Show window
    viewer.show()

    logger.info("AIViewerWidget test window displayed")
    logger.info("Use dropdown to switch between models")

    # Run application
    sys.exit(app.exec())
