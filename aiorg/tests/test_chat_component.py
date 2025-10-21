"""Unit tests for ChatComponent.

Tests the ChatComponent widget for the native chat interface
with local AI models.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from PyQt6.QtCore import Qt
from ai_viewer.chat_component import ChatComponent
from ai_viewer.ollama_client import OllamaClient


class TestChatComponent:
    """Test suite for ChatComponent widget."""

    def test_chat_creation(self, qtbot):
        """Test that ChatComponent widget creates successfully."""
        chat = ChatComponent()
        qtbot.addWidget(chat)

        # Verify widget was created
        assert chat is not None
        assert isinstance(chat, ChatComponent)

        # Verify components exist
        assert hasattr(chat, 'chat_display')
        assert hasattr(chat, 'input_field')
        assert hasattr(chat, 'send_button')
        assert hasattr(chat, 'clear_button')

        # Verify initial state
        assert chat.ollama_client is None
        assert chat.current_model is None
        assert chat.conversation_history == []
        assert chat.is_receiving is False
        assert chat.send_button.isEnabled() is False

    def test_append_message_user(self, qtbot):
        """Test appending user message to chat display."""
        chat = ChatComponent()
        qtbot.addWidget(chat)

        # Append user message
        chat.append_message("user", "Hello, AI!")

        # Verify message appears in display
        html = chat.chat_display.toHtml()
        assert "Hello, AI!" in html
        assert "user" in html.lower() or "you" in html.lower()

    def test_append_message_assistant(self, qtbot):
        """Test appending assistant message to chat display."""
        chat = ChatComponent()
        qtbot.addWidget(chat)

        # Append assistant message
        chat.append_message("assistant", "Hello, human!")

        # Verify message appears in display
        html = chat.chat_display.toHtml()
        assert "Hello, human!" in html
        assert "assistant" in html.lower()

    def test_append_system_message(self, qtbot):
        """Test appending system message to chat display."""
        chat = ChatComponent()
        qtbot.addWidget(chat)

        # Append system message
        chat.append_system_message("System notification")

        # Verify message appears in display
        html = chat.chat_display.toHtml()
        assert "System notification" in html
        assert "system" in html.lower()

    def test_append_chunk(self, qtbot):
        """Test appending streaming chunks to chat display."""
        chat = ChatComponent()
        qtbot.addWidget(chat)

        # Start an assistant message
        chat.append_message("assistant", "")

        # Append chunks
        chat.append_chunk("Hello")
        chat.append_chunk(" ")
        chat.append_chunk("world")

        # Verify chunks appear in display
        text = chat.chat_display.toPlainText()
        assert "Hello world" in text

        # Verify conversation history is updated
        assert len(chat.conversation_history) > 0
        assert chat.conversation_history[-1]["role"] == "assistant"
        assert "Hello world" in chat.conversation_history[-1]["content"]

    def test_html_escaping(self, qtbot):
        """Test that HTML special characters are escaped."""
        chat = ChatComponent()
        qtbot.addWidget(chat)

        # Append message with HTML characters
        chat.append_message("user", "<script>alert('xss')</script>")

        # Verify HTML is escaped in the raw HTML
        html = chat.chat_display.toHtml()
        assert "<script>" not in html
        assert "&lt;script&gt;" in html or "alert" in html

    def test_send_button_disabled_initially(self, qtbot):
        """Test that send button is disabled without client."""
        chat = ChatComponent()
        qtbot.addWidget(chat)

        # Verify send button is disabled
        assert chat.send_button.isEnabled() is False

    def test_send_button_enabled_after_client_set(self, qtbot):
        """Test that send button is enabled after setting client."""
        chat = ChatComponent()
        qtbot.addWidget(chat)

        # Create mock client
        mock_client = Mock(spec=OllamaClient)
        mock_client.check_connection.return_value = True

        # Set client
        chat.set_ollama_client(mock_client, "llama2")

        # Verify send button is enabled
        assert chat.send_button.isEnabled() is True

    def test_send_message_with_empty_input(self, qtbot):
        """Test that empty messages are not sent."""
        chat = ChatComponent()
        qtbot.addWidget(chat)

        # Create mock client
        mock_client = Mock(spec=OllamaClient)
        mock_client.check_connection.return_value = True
        chat.set_ollama_client(mock_client, "llama2")

        # Try to send empty message
        chat.input_field.setText("")
        chat.send_message()

        # Verify chat method was not called
        mock_client.chat.assert_not_called()

    def test_send_message_with_text(self, qtbot):
        """Test sending message with text."""
        chat = ChatComponent()
        qtbot.addWidget(chat)

        # Create mock client
        mock_client = Mock(spec=OllamaClient)
        mock_client.check_connection.return_value = True
        chat.set_ollama_client(mock_client, "llama2")

        # Enter text and send
        chat.input_field.setText("Hello, AI!")
        chat.send_message()

        # Verify chat method was called
        mock_client.chat.assert_called_once()

        # Verify message was added to conversation history
        assert len(chat.conversation_history) == 1
        assert chat.conversation_history[0]["role"] == "user"
        assert chat.conversation_history[0]["content"] == "Hello, AI!"

        # Verify input field was cleared
        assert chat.input_field.text() == ""

        # Verify send button is disabled during request
        assert chat.send_button.isEnabled() is False
        assert chat.is_receiving is True

    def test_send_message_return_key(self, qtbot):
        """Test sending message with Return key."""
        chat = ChatComponent()
        qtbot.addWidget(chat)

        # Create mock client
        mock_client = Mock(spec=OllamaClient)
        mock_client.check_connection.return_value = True
        chat.set_ollama_client(mock_client, "llama2")

        # Enter text
        chat.input_field.setText("Test message")

        # Press Return key
        qtbot.keyPress(chat.input_field, Qt.Key.Key_Return)

        # Verify chat method was called
        mock_client.chat.assert_called_once()

    def test_clear_history(self, qtbot):
        """Test clear history button works."""
        chat = ChatComponent()
        qtbot.addWidget(chat)

        # Add some messages
        chat.append_message("user", "Hello")
        chat.append_message("assistant", "Hi there")
        chat.conversation_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"}
        ]

        # Clear history
        chat.clear_history()

        # Verify conversation history is cleared
        assert chat.conversation_history == []

        # Verify display shows system message
        html = chat.chat_display.toHtml()
        assert "cleared" in html.lower() or "ready" in html.lower()

    def test_clear_button_click(self, qtbot):
        """Test clicking clear button."""
        chat = ChatComponent()
        qtbot.addWidget(chat)

        # Add some conversation history
        chat.conversation_history = [{"role": "user", "content": "test"}]

        # Click clear button
        qtbot.mouseClick(chat.clear_button, Qt.MouseButton.LeftButton)

        # Verify history was cleared
        assert chat.conversation_history == []

    def test_set_ollama_client(self, qtbot):
        """Test setting Ollama client."""
        chat = ChatComponent()
        qtbot.addWidget(chat)

        # Create mock client
        mock_client = Mock(spec=OllamaClient)
        mock_client.check_connection.return_value = True

        # Set client
        chat.set_ollama_client(mock_client, "llama2")

        # Verify client and model are set
        assert chat.ollama_client == mock_client
        assert chat.current_model == "llama2"

        # Verify connection check was called
        mock_client.check_connection.assert_called_once()

        # Verify send button is enabled
        assert chat.send_button.isEnabled() is True

    def test_set_ollama_client_connection_failure(self, qtbot):
        """Test setting client when connection fails."""
        chat = ChatComponent()
        qtbot.addWidget(chat)

        # Create mock client that fails connection
        mock_client = Mock(spec=OllamaClient)
        mock_client.check_connection.return_value = False

        # Set client
        chat.set_ollama_client(mock_client, "llama2")

        # Verify warning message appears
        html = chat.chat_display.toHtml()
        assert "warning" in html.lower() or "could not connect" in html.lower()

    def test_handle_chunk(self, qtbot):
        """Test handling streaming chunk callback."""
        chat = ChatComponent()
        qtbot.addWidget(chat)

        # Start assistant message
        chat.append_message("assistant", "")

        # Handle chunks
        chat._handle_chunk("Hello")
        chat._handle_chunk(" world")

        # Verify chunks appear in display
        text = chat.chat_display.toPlainText()
        assert "Hello world" in text

    def test_handle_complete(self, qtbot):
        """Test handling request completion callback."""
        chat = ChatComponent()
        qtbot.addWidget(chat)

        # Create mock client
        mock_client = Mock(spec=OllamaClient)
        mock_client.check_connection.return_value = True
        chat.set_ollama_client(mock_client, "llama2")

        # Simulate active request
        chat.is_receiving = True
        chat.send_button.setEnabled(False)
        chat.input_field.setEnabled(False)

        # Handle completion
        chat._handle_complete()

        # Verify UI is re-enabled
        assert chat.is_receiving is False
        assert chat.send_button.isEnabled() is True
        assert chat.input_field.isEnabled() is True

    def test_handle_error(self, qtbot):
        """Test handling error callback."""
        chat = ChatComponent()
        qtbot.addWidget(chat)

        # Create mock client
        mock_client = Mock(spec=OllamaClient)
        mock_client.check_connection.return_value = True
        chat.set_ollama_client(mock_client, "llama2")

        # Simulate active request
        chat.is_receiving = True
        chat.send_button.setEnabled(False)

        # Handle error
        error_msg = "Connection failed"
        chat._handle_error(error_msg)

        # Verify error message appears
        html = chat.chat_display.toHtml()
        assert error_msg in html

        # Verify UI is re-enabled
        assert chat.is_receiving is False
        assert chat.send_button.isEnabled() is True

    def test_send_message_without_client(self, qtbot):
        """Test that sending without client shows error."""
        chat = ChatComponent()
        qtbot.addWidget(chat)

        # Try to send message without setting client
        chat.input_field.setText("Hello")
        chat.send_message()

        # Verify error message appears
        html = chat.chat_display.toHtml()
        assert "error" in html.lower() or "not configured" in html.lower()

    def test_conversation_history_accumulation(self, qtbot):
        """Test that conversation history accumulates correctly."""
        chat = ChatComponent()
        qtbot.addWidget(chat)

        # Create mock client
        mock_client = Mock(spec=OllamaClient)
        mock_client.check_connection.return_value = True
        chat.set_ollama_client(mock_client, "llama2")

        # Send first message
        chat.input_field.setText("First message")
        chat.send_message()

        # Complete first request
        chat._handle_complete()

        # Send second message
        chat.input_field.setText("Second message")
        chat.send_message()

        # Verify history has both messages
        assert len(chat.conversation_history) >= 2
        assert any("First message" in msg["content"] for msg in chat.conversation_history)
        assert any("Second message" in msg["content"] for msg in chat.conversation_history)

    def test_multiline_message(self, qtbot):
        """Test handling multiline messages."""
        chat = ChatComponent()
        qtbot.addWidget(chat)

        # Append multiline message
        message = "Line 1\nLine 2\nLine 3"
        chat.append_message("user", message)

        # Verify message appears (HTML escaping may convert newlines)
        html = chat.chat_display.toHtml()
        assert "Line 1" in html
        assert "Line 2" in html
        assert "Line 3" in html


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
