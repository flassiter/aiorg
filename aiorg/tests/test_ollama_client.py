"""Unit tests for OllamaClient.

Tests the OllamaClient class and OllamaWorker thread for
Ollama API communication.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from ai_viewer.ollama_client import OllamaClient, OllamaWorker


class TestOllamaClient:
    """Test suite for OllamaClient class."""

    def test_init(self):
        """Test OllamaClient initialization."""
        client = OllamaClient("http://localhost:11434")
        assert client.base_url == "http://localhost:11434"
        assert client._current_worker is None

    def test_init_strips_trailing_slash(self):
        """Test that trailing slash is removed from base URL."""
        client = OllamaClient("http://localhost:11434/")
        assert client.base_url == "http://localhost:11434"

    @patch('ai_viewer.ollama_client.requests.get')
    def test_check_connection_success(self, mock_get):
        """Test successful connection check."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"version": "0.1.0"}'
        mock_get.return_value = mock_response

        client = OllamaClient("http://localhost:11434")
        result = client.check_connection()

        assert result is True
        mock_get.assert_called_once_with(
            "http://localhost:11434/api/version",
            timeout=5
        )

    @patch('ai_viewer.ollama_client.requests.get')
    def test_check_connection_failure(self, mock_get):
        """Test failed connection check."""
        # Mock connection error
        mock_get.side_effect = ConnectionError("Connection refused")

        client = OllamaClient("http://localhost:11434")
        result = client.check_connection()

        assert result is False

    @patch('ai_viewer.ollama_client.requests.get')
    def test_list_models_success(self, mock_get):
        """Test successful model listing."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "llama2"},
                {"name": "mistral"}
            ]
        }
        mock_get.return_value = mock_response

        client = OllamaClient("http://localhost:11434")
        models = client.list_models()

        assert models == ["llama2", "mistral"]
        mock_get.assert_called_once_with(
            "http://localhost:11434/api/tags",
            timeout=5
        )

    @patch('ai_viewer.ollama_client.requests.get')
    def test_list_models_failure(self, mock_get):
        """Test failed model listing."""
        # Mock connection error
        mock_get.side_effect = ConnectionError("Connection refused")

        client = OllamaClient("http://localhost:11434")
        models = client.list_models()

        assert models == []

    def test_chat_creates_worker(self):
        """Test that chat() creates a worker thread."""
        client = OllamaClient("http://localhost:11434")

        # Mock callbacks
        on_chunk = Mock()
        on_complete = Mock()
        on_error = Mock()

        messages = [{"role": "user", "content": "Hello"}]

        # Mock the worker to prevent actual thread start
        with patch('ai_viewer.ollama_client.OllamaWorker') as mock_worker_class:
            mock_worker = Mock()
            mock_worker_class.return_value = mock_worker

            client.chat("llama2", messages, on_chunk, on_complete, on_error)

            # Verify worker was created
            mock_worker_class.assert_called_once_with(
                "http://localhost:11434",
                "llama2",
                messages
            )

            # Verify signals were connected
            assert mock_worker.chunk_received.connect.called
            assert mock_worker.request_complete.connect.called
            assert mock_worker.request_error.connect.called

            # Verify worker was started
            mock_worker.start.assert_called_once()

    def test_cancel_current_request(self):
        """Test cancelling current request."""
        client = OllamaClient("http://localhost:11434")

        # Create mock worker
        mock_worker = Mock()
        mock_worker.isRunning.return_value = True
        client._current_worker = mock_worker

        # Cancel request
        client.cancel_current_request()

        # Verify cancel and wait were called
        mock_worker.cancel.assert_called_once()
        mock_worker.wait.assert_called_once()

    @patch('ai_viewer.ollama_client.requests.post')
    def test_chat_request_format(self, mock_post):
        """Test that chat request has correct format."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            b'{"message":{"role":"assistant","content":"Hi"},"done":true}'
        ]
        mock_post.return_value = mock_response

        # Create client and worker
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
            {"role": "user", "content": "How are you?"}
        ]
        worker = OllamaWorker("http://localhost:11434", "llama2", messages)

        # Mock signals
        worker.chunk_received = Mock()
        worker.request_complete = Mock()
        worker.request_error = Mock()

        # Run worker
        worker.run()

        # Verify request was made with correct format
        mock_post.assert_called_once()
        call_args = mock_post.call_args

        # Verify endpoint
        assert call_args[0][0] == "http://localhost:11434/api/chat"

        # Verify payload
        payload = call_args[1]['json']
        assert payload['model'] == "llama2"
        assert payload['messages'] == messages
        assert payload['stream'] is True

        # Verify other parameters
        assert call_args[1]['stream'] is True
        assert call_args[1]['timeout'] == 30


class TestOllamaWorker:
    """Test suite for OllamaWorker class."""

    def test_init(self):
        """Test OllamaWorker initialization."""
        messages = [{"role": "user", "content": "Hello"}]
        worker = OllamaWorker("http://localhost:11434", "llama2", messages)

        assert worker.base_url == "http://localhost:11434"
        assert worker.model == "llama2"
        assert worker.messages == messages
        assert worker._is_cancelled is False

    def test_cancel(self):
        """Test worker cancellation."""
        messages = [{"role": "user", "content": "Hello"}]
        worker = OllamaWorker("http://localhost:11434", "llama2", messages)

        worker.cancel()
        assert worker._is_cancelled is True

    @patch('ai_viewer.ollama_client.requests.post')
    def test_run_streaming_success(self, mock_post):
        """Test successful streaming request."""
        # Mock streaming response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            b'{"message":{"role":"assistant","content":"Hello"},"done":false}',
            b'{"message":{"role":"assistant","content":" there"},"done":false}',
            b'{"message":{"role":"assistant","content":"!"},"done":true}'
        ]
        mock_post.return_value = mock_response

        messages = [{"role": "user", "content": "Hello"}]
        worker = OllamaWorker("http://localhost:11434", "llama2", messages)

        # Mock signals
        worker.chunk_received = Mock()
        worker.request_complete = Mock()
        worker.request_error = Mock()

        # Run worker
        worker.run()

        # Verify chunks were emitted
        assert worker.chunk_received.emit.call_count == 3
        worker.chunk_received.emit.assert_any_call("Hello")
        worker.chunk_received.emit.assert_any_call(" there")
        worker.chunk_received.emit.assert_any_call("!")

        # Verify completion signal
        worker.request_complete.emit.assert_called_once()

        # Verify no error signal
        worker.request_error.emit.assert_not_called()

    @patch('ai_viewer.ollama_client.requests.post')
    def test_run_connection_error(self, mock_post):
        """Test connection error handling."""
        # Mock connection error
        mock_post.side_effect = ConnectionError("Connection refused")

        messages = [{"role": "user", "content": "Hello"}]
        worker = OllamaWorker("http://localhost:11434", "llama2", messages)

        # Mock signals
        worker.chunk_received = Mock()
        worker.request_complete = Mock()
        worker.request_error = Mock()

        # Run worker
        worker.run()

        # Verify error signal was emitted
        worker.request_error.emit.assert_called_once()
        error_msg = worker.request_error.emit.call_args[0][0]
        assert "Could not connect" in error_msg
        assert "http://localhost:11434" in error_msg

        # Verify no other signals
        worker.chunk_received.emit.assert_not_called()
        worker.request_complete.emit.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
