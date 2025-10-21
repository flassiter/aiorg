"""Ollama API client for local model communication.

This module provides the OllamaClient class for communicating with
Ollama's API, with support for streaming responses via QThread.
"""

import json
import logging
import requests
from typing import Callable
from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class OllamaWorker(QThread):
    """Worker thread for Ollama API calls.

    This thread handles the streaming API request in the background
    to avoid blocking the UI thread.
    """

    # Signals for thread-safe communication
    chunk_received = pyqtSignal(str)  # Emitted for each response chunk
    request_complete = pyqtSignal()   # Emitted when request completes
    request_error = pyqtSignal(str)   # Emitted on error with error message

    def __init__(self, base_url: str, model: str, messages: list[dict]):
        """Initialize worker thread.

        Args:
            base_url: Ollama API base URL (e.g., "http://localhost:11434")
            model: Model name (e.g., "llama2")
            messages: List of message dicts with 'role' and 'content'
        """
        super().__init__()
        self.base_url = base_url
        self.model = model
        self.messages = messages
        self._is_cancelled = False

        logger.debug(f"OllamaWorker initialized for model: {model}")

    def cancel(self):
        """Cancel the current request."""
        self._is_cancelled = True
        logger.info("OllamaWorker cancellation requested")

    def run(self):
        """Execute API request in background thread."""
        logger.info(f"Starting Ollama API request to {self.base_url}")
        logger.debug(f"Model: {self.model}, Messages: {len(self.messages)}")

        try:
            # Build API endpoint
            endpoint = f"{self.base_url}/api/chat"

            # Build request payload
            payload = {
                "model": self.model,
                "messages": self.messages,
                "stream": True
            }

            logger.debug(f"Request endpoint: {endpoint}")
            logger.debug(f"Request payload: {json.dumps(payload, indent=2)}")

            # Make streaming request
            response = requests.post(
                endpoint,
                json=payload,
                stream=True,
                timeout=30  # 30 second timeout for initial connection
            )

            # Check response status
            if response.status_code != 200:
                error_msg = f"Ollama API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                self.request_error.emit(error_msg)
                return

            logger.info("Successfully connected to Ollama API, receiving stream...")

            # Process streaming response
            for line in response.iter_lines():
                # Check for cancellation
                if self._is_cancelled:
                    logger.info("Request cancelled by user")
                    return

                if not line:
                    continue

                try:
                    # Parse JSON line
                    data = json.loads(line.decode('utf-8'))

                    # Extract content from message
                    message = data.get('message', {})
                    content = message.get('content', '')

                    # Emit chunk if not empty
                    if content:
                        self.chunk_received.emit(content)
                        logger.debug(f"Received chunk: {content[:50]}...")

                    # Check if done
                    if data.get('done', False):
                        logger.info("Streaming response completed")
                        break

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON response line: {e}")
                    logger.debug(f"Problematic line: {line}")
                    continue

            # Emit completion signal
            self.request_complete.emit()
            logger.info("Ollama API request completed successfully")

        except (requests.exceptions.ConnectionError, ConnectionError) as e:
            error_msg = f"Could not connect to Ollama at {self.base_url}. Make sure Ollama is running."
            logger.error(f"Connection error: {e}")
            self.request_error.emit(error_msg)

        except requests.exceptions.Timeout as e:
            error_msg = "Request timed out. The model may be slow to respond."
            logger.error(f"Timeout error: {e}")
            self.request_error.emit(error_msg)

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Unexpected error in OllamaWorker: {e}", exc_info=True)
            self.request_error.emit(error_msg)


class OllamaClient:
    """Client for Ollama API communication.

    Provides methods to interact with Ollama's API for chat
    with local AI models, including streaming responses.
    """

    def __init__(self, base_url: str):
        """Initialize Ollama client.

        Args:
            base_url: Base URL for Ollama API (e.g., "http://localhost:11434")
        """
        self.base_url = base_url.rstrip('/')
        self._current_worker = None

        logger.info(f"OllamaClient initialized with base URL: {self.base_url}")

    def chat(
        self,
        model: str,
        messages: list[dict],
        on_chunk: Callable[[str], None],
        on_complete: Callable[[], None],
        on_error: Callable[[str], None]
    ):
        """Send chat request with streaming response.

        This method starts a background thread to handle the API request
        and connects the provided callbacks to the appropriate signals.

        Args:
            model: Model name (e.g., "llama2", "mistral")
            messages: List of message dicts with 'role' and 'content' keys
            on_chunk: Callback function for each response chunk (receives str)
            on_complete: Callback function when response completes (no args)
            on_error: Callback function for errors (receives error message str)

        Example:
            client = OllamaClient("http://localhost:11434")
            messages = [{"role": "user", "content": "Hello!"}]

            def handle_chunk(text):
                print(text, end='', flush=True)

            def handle_complete():
                print("\\nDone!")

            def handle_error(error):
                print(f"Error: {error}")

            client.chat("llama2", messages, handle_chunk, handle_complete, handle_error)
        """
        logger.info(f"Starting chat request for model: {model}")

        # Cancel any existing request
        if self._current_worker and self._current_worker.isRunning():
            logger.warning("Cancelling previous request before starting new one")
            self._current_worker.cancel()
            self._current_worker.wait()

        # Create new worker thread
        self._current_worker = OllamaWorker(self.base_url, model, messages)

        # Connect signals to callbacks
        self._current_worker.chunk_received.connect(on_chunk)
        self._current_worker.request_complete.connect(on_complete)
        self._current_worker.request_error.connect(on_error)

        # Start worker thread
        self._current_worker.start()
        logger.info("Worker thread started")

    def check_connection(self) -> bool:
        """Check if Ollama server is reachable.

        Returns:
            bool: True if server is reachable, False otherwise
        """
        logger.debug(f"Checking connection to Ollama at {self.base_url}")

        try:
            # Try to access the version endpoint
            response = requests.get(
                f"{self.base_url}/api/version",
                timeout=5
            )

            if response.status_code == 200:
                logger.info("Successfully connected to Ollama")
                logger.debug(f"Ollama response: {response.text}")
                return True
            else:
                logger.warning(f"Ollama returned status code: {response.status_code}")
                return False

        except requests.exceptions.ConnectionError:
            logger.warning(f"Could not connect to Ollama at {self.base_url}")
            return False

        except requests.exceptions.Timeout:
            logger.warning("Connection to Ollama timed out")
            return False

        except Exception as e:
            logger.error(f"Unexpected error checking Ollama connection: {e}", exc_info=True)
            return False

    def list_models(self) -> list[str]:
        """List available models from Ollama.

        This is an optional method for future use to dynamically
        discover available models.

        Returns:
            list[str]: List of available model names, or empty list on error
        """
        logger.debug("Fetching list of available models from Ollama")

        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                models = [model['name'] for model in data.get('models', [])]
                logger.info(f"Found {len(models)} available models: {models}")
                return models
            else:
                logger.warning(f"Failed to list models, status code: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Error listing models: {e}", exc_info=True)
            return []

    def cancel_current_request(self):
        """Cancel the currently running request if any."""
        if self._current_worker and self._current_worker.isRunning():
            logger.info("Cancelling current Ollama request")
            self._current_worker.cancel()
            self._current_worker.wait()
        else:
            logger.debug("No active request to cancel")


# Standalone test mode
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit

    # Setup logging for test mode
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger.info("Starting OllamaClient standalone test")

    class TestWindow(QWidget):
        """Simple test window for OllamaClient."""

        def __init__(self):
            super().__init__()
            self.setWindowTitle("OllamaClient Test")
            self.resize(600, 400)

            # Create layout
            layout = QVBoxLayout(self)

            # Text display
            self.text_display = QTextEdit()
            self.text_display.setReadOnly(True)
            layout.addWidget(self.text_display)

            # Test button
            self.test_button = QPushButton("Test Ollama Connection")
            self.test_button.clicked.connect(self.test_connection)
            layout.addWidget(self.test_button)

            # Send message button
            self.send_button = QPushButton("Send Test Message")
            self.send_button.clicked.connect(self.send_message)
            layout.addWidget(self.send_button)

            # Create client
            self.client = OllamaClient("http://localhost:11434")

        def test_connection(self):
            """Test connection to Ollama."""
            self.text_display.append("Testing connection to Ollama...")
            if self.client.check_connection():
                self.text_display.append("✓ Connected successfully!")

                # List models
                models = self.client.list_models()
                if models:
                    self.text_display.append(f"Available models: {', '.join(models)}")
                else:
                    self.text_display.append("No models found or couldn't fetch model list")
            else:
                self.text_display.append("✗ Connection failed!")

        def send_message(self):
            """Send a test message."""
            self.text_display.append("\n--- Sending test message ---")
            self.text_display.append("You: Hello!")
            self.text_display.append("Assistant: ")

            messages = [{"role": "user", "content": "Hello! Please respond with a short greeting."}]

            def on_chunk(text):
                # Append chunk without newline
                cursor = self.text_display.textCursor()
                cursor.movePosition(cursor.MoveOperation.End)
                cursor.insertText(text)
                self.text_display.setTextCursor(cursor)

            def on_complete():
                self.text_display.append("\n--- Request completed ---")

            def on_error(error):
                self.text_display.append(f"\n✗ Error: {error}")

            self.client.chat("llama2", messages, on_chunk, on_complete, on_error)

    # Create application
    app = QApplication(sys.argv)

    # Create test window
    window = TestWindow()
    window.show()

    logger.info("OllamaClient test window displayed")
    logger.info("Click 'Test Ollama Connection' to check if Ollama is running")
    logger.info("Click 'Send Test Message' to send a test chat message")

    # Run application
    sys.exit(app.exec())
