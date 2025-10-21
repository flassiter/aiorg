"""Native chat interface for local AI models.

This module provides the ChatComponent widget for interacting with
local AI models through Ollama, with streaming response support.
"""

import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QTextBrowser
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextCursor

from ai_viewer.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


class ChatComponent(QWidget):
    """Native chat interface for local AI models.

    Provides a chat UI with message display, input field, and buttons
    for interacting with Ollama API. Supports streaming responses.
    """

    def __init__(self, parent=None):
        """Initialize chat component."""
        super().__init__(parent)

        logger.info("Initializing ChatComponent")

        # State
        self.ollama_client = None
        self.current_model = None
        self.conversation_history = []  # List of message dicts
        self.is_receiving = False  # Flag to track if currently receiving response

        # Initialize UI
        self.setup_ui()

        logger.info("ChatComponent initialized successfully")

    def setup_ui(self):
        """Create chat interface layout."""
        logger.debug("Setting up ChatComponent UI")

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Chat history display (read-only, HTML-enabled)
        self.chat_display = QTextBrowser()
        self.chat_display.setOpenExternalLinks(False)
        self.chat_display.setReadOnly(True)

        # Set initial welcome message
        self._set_initial_html()

        layout.addWidget(self.chat_display, stretch=1)

        # Input area
        input_layout = QHBoxLayout()
        input_layout.setSpacing(5)

        # Text input field
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type your message here...")
        self.input_field.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.input_field, stretch=1)

        # Send button
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)
        self.send_button.setEnabled(False)  # Disabled until model is set
        input_layout.addWidget(self.send_button)

        # Clear button
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_history)
        input_layout.addWidget(self.clear_button)

        layout.addLayout(input_layout)

        logger.debug("ChatComponent UI setup complete")

    def _set_initial_html(self):
        """Set initial HTML content for chat display."""
        html = """
        <html>
        <head>
            <style>
                body {
                    font-family: sans-serif;
                    line-height: 1.6;
                    padding: 10px;
                    color: #e0e0e0;
                    background-color: #2b2b2b;
                }
                .message {
                    margin: 10px 0;
                    padding: 10px;
                    border-radius: 5px;
                }
                .message.user {
                    background-color: #1e3a5f;
                    border-left: 4px solid #4a90e2;
                }
                .message.assistant {
                    background-color: #2d3a2d;
                    border-left: 4px solid #5fa15f;
                }
                .message.system {
                    background-color: #3a2d2d;
                    border-left: 4px solid #a15f5f;
                    font-style: italic;
                }
                .message strong {
                    display: block;
                    margin-bottom: 5px;
                    font-weight: bold;
                }
                .content {
                    white-space: pre-wrap;
                    word-wrap: break-word;
                }
            </style>
        </head>
        <body>
            <div class="message system">
                <strong>System</strong>
                <div class="content">Chat interface ready. Select a local model and start chatting!</div>
            </div>
        </body>
        </html>
        """
        self.chat_display.setHtml(html)

    def set_ollama_client(self, client: OllamaClient, model_name: str):
        """Set Ollama client and model for API communication.

        Args:
            client: OllamaClient instance
            model_name: Name of the model to use (e.g., "llama2")
        """
        logger.info(f"Setting Ollama client with model: {model_name}")

        self.ollama_client = client
        self.current_model = model_name

        # Enable send button now that we have a client
        self.send_button.setEnabled(True)

        # Clear conversation history for new model
        self.conversation_history = []

        # Show connection status
        if client.check_connection():
            self.append_system_message(f"Connected to Ollama. Model: {model_name}")
            logger.info("Ollama connection verified")
        else:
            self.append_system_message(
                f"Warning: Could not connect to Ollama. Model: {model_name}\n"
                "Make sure Ollama is running."
            )
            logger.warning("Ollama connection check failed")

    def send_message(self):
        """Send user message to Ollama API."""
        # Get message text
        message_text = self.input_field.text().strip()

        if not message_text:
            logger.debug("Empty message, ignoring send request")
            return

        if not self.ollama_client or not self.current_model:
            logger.error("Cannot send message: Ollama client not configured")
            self.append_system_message("Error: Ollama client not configured")
            return

        if self.is_receiving:
            logger.warning("Already receiving a response, ignoring send request")
            return

        logger.info(f"Sending message to Ollama: {message_text[:50]}...")

        # Clear input field
        self.input_field.clear()

        # Add user message to display and history
        self.append_message("user", message_text)
        self.conversation_history.append({
            "role": "user",
            "content": message_text
        })

        # Disable send button while receiving
        self.is_receiving = True
        self.send_button.setEnabled(False)
        self.input_field.setEnabled(False)

        # Start assistant message
        self.append_message("assistant", "")

        # Send request to Ollama
        self.ollama_client.chat(
            model=self.current_model,
            messages=self.conversation_history,
            on_chunk=self._handle_chunk,
            on_complete=self._handle_complete,
            on_error=self._handle_error
        )

    def _handle_chunk(self, chunk: str):
        """Handle streaming response chunk.

        Args:
            chunk: Text chunk from streaming response
        """
        logger.debug(f"Received chunk: {chunk[:50]}...")
        self.append_chunk(chunk)

    def _handle_complete(self):
        """Handle request completion."""
        logger.info("Ollama request completed")

        # Get the complete assistant message from the display
        # We'll extract it from the last message in history
        # For now, we'll just mark as complete

        # Re-enable input
        self.is_receiving = False
        self.send_button.setEnabled(True)
        self.input_field.setEnabled(True)
        self.input_field.setFocus()

        # Note: We don't add to conversation_history here because
        # we need to accumulate the chunks first. For simplicity,
        # we'll handle this in append_chunk

    def _handle_error(self, error: str):
        """Handle request error.

        Args:
            error: Error message
        """
        logger.error(f"Ollama request error: {error}")
        self.append_system_message(f"Error: {error}")

        # Re-enable input
        self.is_receiving = False
        self.send_button.setEnabled(True)
        self.input_field.setEnabled(True)

    def append_message(self, role: str, content: str):
        """Append message to chat history display.

        Args:
            role: Message role ("user", "assistant", or "system")
            content: Message content
        """
        logger.debug(f"Appending {role} message: {content[:50]}...")

        # Escape HTML in content
        escaped_content = self._escape_html(content)

        # Build message HTML
        css_class = role
        role_label = role.capitalize()

        message_html = f"""
        <div class="message {css_class}">
            <strong>{role_label}:</strong>
            <div class="content" id="msg-{role}-last">{escaped_content}</div>
        </div>
        """

        # Move cursor to end and insert HTML
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.chat_display.setTextCursor(cursor)
        self.chat_display.insertHtml(message_html)

        # Scroll to bottom
        self.chat_display.ensureCursorVisible()

    def append_system_message(self, content: str):
        """Append system message to chat display.

        Args:
            content: System message content
        """
        self.append_message("system", content)

    def append_chunk(self, chunk: str):
        """Append streaming response chunk to last assistant message.

        Args:
            chunk: Text chunk to append
        """
        # Escape HTML
        escaped_chunk = self._escape_html(chunk)

        # Get current HTML
        current_html = self.chat_display.toHtml()

        # Find the last assistant message content div
        # This is a simple approach - we'll append to the current HTML
        # by finding the last occurrence of a content div and inserting before the closing tags

        # For simplicity, we'll move cursor to end and insert text
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.chat_display.setTextCursor(cursor)
        self.chat_display.insertPlainText(chunk)

        # Scroll to bottom
        self.chat_display.ensureCursorVisible()

        # Update conversation history with accumulated response
        # Find the last assistant message in history and update it
        if self.conversation_history and self.conversation_history[-1]["role"] == "assistant":
            self.conversation_history[-1]["content"] += chunk
        else:
            # Create new assistant message in history
            self.conversation_history.append({
                "role": "assistant",
                "content": chunk
            })

    def clear_history(self):
        """Clear chat history display and conversation state."""
        logger.info("Clearing chat history")

        # Reset state
        self.conversation_history = []

        # Reset display
        self._set_initial_html()

        # Show system message
        if self.current_model:
            self.append_system_message(f"Chat history cleared. Model: {self.current_model}")
        else:
            self.append_system_message("Chat history cleared.")

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters.

        Args:
            text: Text to escape

        Returns:
            str: HTML-escaped text
        """
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#x27;'))


# Standalone test mode
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    # Setup logging for test mode
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger.info("Starting ChatComponent standalone test")

    # Create application
    app = QApplication(sys.argv)

    # Create chat component
    chat = ChatComponent()
    chat.setWindowTitle("ChatComponent Test")
    chat.resize(800, 600)

    # Configure with Ollama client
    client = OllamaClient("http://localhost:11434")
    chat.set_ollama_client(client, "llama2")

    # Show window
    chat.show()

    logger.info("ChatComponent test window displayed")
    logger.info("Type a message and press Enter or click Send to test")
    logger.info("Make sure Ollama is running with llama2 model available")

    # Run application
    sys.exit(app.exec())
