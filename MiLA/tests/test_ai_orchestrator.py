"""
Tests for AI orchestration component.
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import date, datetime
from decimal import Decimal

from src.components.ai_orchestrator import AIOrchestrator, AIOrchestrationError, QwenModelSize, ModelConfig
from src.models.chat import ChatResponse, ToolCall, ToolResult
from src.models.loan import LoanRecord
from src.models.payoff import PayoffCalculation


@pytest.fixture
def orchestrator():
    """Create AI orchestrator instance for testing."""
    return AIOrchestrator(ollama_base_url="http://localhost:11434")


@pytest.fixture
def orchestrator_8b():
    """Create AI orchestrator with 8B model for testing."""
    return AIOrchestrator(
        ollama_base_url="http://localhost:11434", 
        model_size=QwenModelSize.SIZE_8B
    )


@pytest.fixture
def sample_loan():
    """Create sample loan record for testing."""
    return LoanRecord(
        loan_number="69253358",
        borrower_name="Mark Wilson",
        principal_balance=Decimal("15000.00"),
        annual_interest_rate=Decimal("5.50"),
        last_payment_date=date(2024, 1, 1)
    )


@pytest.fixture
def sample_payoff():
    """Create sample payoff calculation for testing."""
    return PayoffCalculation(
        loan_number="69253358",
        principal_balance=Decimal("15000.00"),
        interest_accrued=Decimal("678.75"),
        total_payoff=Decimal("15678.75"),
        calculation_date=date.today(),
        days_since_payment=30
    )


class TestAIOrchestrator:
    """Test cases for AI orchestrator functionality."""

    def test_setup_tools(self, orchestrator):
        """Test that tools are properly configured."""
        assert "get_loan_info" in orchestrator.available_tools
        assert "calculate_payoff" in orchestrator.available_tools
        assert "generate_pdf" in orchestrator.available_tools
        
        # Check tool structure
        get_loan_tool = orchestrator.available_tools["get_loan_info"]
        assert get_loan_tool["type"] == "function"
        assert get_loan_tool["function"]["name"] == "get_loan_info"
        assert "identifier" in get_loan_tool["function"]["parameters"]["properties"]

    def test_build_system_prompt(self, orchestrator):
        """Test system prompt generation."""
        prompt = orchestrator._build_system_prompt()
        
        assert "MiLA" in prompt
        assert "get_loan_info" in prompt
        assert "calculate_payoff" in prompt
        assert "generate_pdf" in prompt
        assert "Mark Wilson" in prompt  # Example name

    def test_parse_tool_calls_single_call(self, orchestrator):
        """Test parsing single tool call from AI response."""
        ai_response = {
            "message": {
                "tool_calls": [
                    {
                        "function": {
                            "name": "get_loan_info",
                            "arguments": '{"identifier": "Mark Wilson"}'
                        }
                    }
                ]
            }
        }
        
        tool_calls = orchestrator.parse_tool_calls(ai_response)
        
        assert len(tool_calls) == 1
        assert tool_calls[0].tool_name == "get_loan_info"
        assert tool_calls[0].parameters == {"identifier": "Mark Wilson"}

    def test_parse_tool_calls_multiple_calls(self, orchestrator):
        """Test parsing multiple tool calls from AI response."""
        ai_response = {
            "message": {
                "tool_calls": [
                    {
                        "function": {
                            "name": "get_loan_info",
                            "arguments": '{"identifier": "69253358"}'
                        }
                    },
                    {
                        "function": {
                            "name": "calculate_payoff",
                            "arguments": '{"loan_number": "69253358"}'
                        }
                    }
                ]
            }
        }
        
        tool_calls = orchestrator.parse_tool_calls(ai_response)
        
        assert len(tool_calls) == 2
        assert tool_calls[0].tool_name == "get_loan_info"
        assert tool_calls[1].tool_name == "calculate_payoff"

    def test_parse_tool_calls_empty_response(self, orchestrator):
        """Test parsing empty AI response."""
        ai_response = {"message": {}}
        tool_calls = orchestrator.parse_tool_calls(ai_response)
        assert len(tool_calls) == 0

    @pytest.mark.asyncio
    async def test_execute_get_loan_info_success(self, orchestrator, sample_loan):
        """Test successful loan info retrieval."""
        with patch('src.components.ai_orchestrator.loan_data_access') as mock_data_access:
            mock_data_access.find_loan_by_identifier.return_value = sample_loan
            
            tool_call = ToolCall(
                tool_name="get_loan_info",
                parameters={"identifier": "Mark Wilson"}
            )
            
            result = await orchestrator._execute_single_tool(tool_call)
            
            assert result.success is True
            assert result.tool_name == "get_loan_info"
            assert result.result["loan_number"] == "69253358"
            assert result.result["borrower_name"] == "Mark Wilson"

    @pytest.mark.asyncio
    async def test_execute_get_loan_info_not_found(self, orchestrator):
        """Test loan info retrieval when loan not found."""
        with patch('src.components.ai_orchestrator.loan_data_access') as mock_data_access:
            mock_data_access.find_loan_by_identifier.return_value = None
            
            tool_call = ToolCall(
                tool_name="get_loan_info",
                parameters={"identifier": "Unknown Person"}
            )
            
            result = await orchestrator._execute_single_tool(tool_call)
            
            assert result.success is False
            assert "not found" in result.error_message

    @pytest.mark.asyncio
    async def test_execute_calculate_payoff_success(self, orchestrator, sample_loan, sample_payoff):
        """Test successful payoff calculation."""
        with patch('src.components.ai_orchestrator.loan_data_access') as mock_data_access, \
             patch('src.components.ai_orchestrator.payoff_calculator') as mock_calculator:
            
            mock_data_access.find_loan_by_number.return_value = sample_loan
            mock_calculator.calculate_payoff.return_value = sample_payoff
            
            tool_call = ToolCall(
                tool_name="calculate_payoff",
                parameters={"loan_number": "69253358"}
            )
            
            result = await orchestrator._execute_single_tool(tool_call)
            
            assert result.success is True
            assert result.tool_name == "calculate_payoff"
            assert result.result["total_payoff"] == 15678.75

    @pytest.mark.asyncio
    async def test_execute_generate_pdf_success(self, orchestrator, sample_loan, sample_payoff):
        """Test successful PDF generation."""
        with patch('src.components.ai_orchestrator.loan_data_access') as mock_data_access, \
             patch('src.components.ai_orchestrator.payoff_calculator') as mock_calculator, \
             patch('src.components.ai_orchestrator.pdf_generator') as mock_pdf_gen:
            
            mock_data_access.find_loan_by_number.return_value = sample_loan
            mock_calculator.calculate_payoff.return_value = sample_payoff
            mock_pdf_gen.generate_payoff_statement.return_value = "/tmp/payoff_69253358.pdf"
            
            tool_call = ToolCall(
                tool_name="generate_pdf",
                parameters={"loan_number": "69253358"}
            )
            
            result = await orchestrator._execute_single_tool(tool_call)
            
            assert result.success is True
            assert result.tool_name == "generate_pdf"
            assert "payoff_69253358.pdf" in result.result["filename"]
            assert "/api/files/" in result.result["download_url"]

    @pytest.mark.asyncio
    async def test_execute_tool_sequence_success(self, orchestrator, sample_loan, sample_payoff):
        """Test executing a sequence of tools successfully."""
        with patch('src.components.ai_orchestrator.loan_data_access') as mock_data_access, \
             patch('src.components.ai_orchestrator.payoff_calculator') as mock_calculator, \
             patch('src.components.ai_orchestrator.pdf_generator') as mock_pdf_gen:
            
            mock_data_access.find_loan_by_identifier.return_value = sample_loan
            mock_data_access.find_loan_by_number.return_value = sample_loan
            mock_calculator.calculate_payoff.return_value = sample_payoff
            mock_pdf_gen.generate_payoff_statement.return_value = "/tmp/payoff_69253358.pdf"
            
            tool_calls = [
                ToolCall(tool_name="get_loan_info", parameters={"identifier": "Mark Wilson"}),
                ToolCall(tool_name="calculate_payoff", parameters={"loan_number": "69253358"}),
                ToolCall(tool_name="generate_pdf", parameters={"loan_number": "69253358"})
            ]
            
            results = await orchestrator.execute_tool_sequence(tool_calls)
            
            assert len(results) == 3
            assert all(r.success for r in results)
            assert results[0].tool_name == "get_loan_info"
            assert results[1].tool_name == "calculate_payoff"
            assert results[2].tool_name == "generate_pdf"

    @pytest.mark.asyncio
    async def test_execute_tool_sequence_with_failure(self, orchestrator):
        """Test tool sequence execution with one failure."""
        with patch('src.components.ai_orchestrator.loan_data_access') as mock_data_access:
            mock_data_access.find_loan_by_identifier.return_value = None
            
            tool_calls = [
                ToolCall(tool_name="get_loan_info", parameters={"identifier": "Unknown"}),
                ToolCall(tool_name="calculate_payoff", parameters={"loan_number": "12345"})
            ]
            
            results = await orchestrator.execute_tool_sequence(tool_calls)
            
            assert len(results) == 2
            assert results[0].success is False
            assert results[1].success is False  # Should still execute

    def test_format_markdown_response_loan_info(self, orchestrator):
        """Test formatting loan info results."""
        results = [
            ToolResult(
                tool_name="get_loan_info",
                parameters={"identifier": "Mark Wilson"},
                success=True,
                result={
                    "loan_number": "69253358",
                    "borrower_name": "Mark Wilson",
                    "principal_balance": 15000.00,
                    "annual_interest_rate": 5.50,
                    "last_payment_date": "2024-01-01"
                }
            )
        ]
        
        response = orchestrator.format_markdown_response(results)
        
        assert "## 📋 Loan Information" in response
        assert "**Loan Number:** 69253358" in response
        assert "**Borrower:** Mark Wilson" in response
        assert "$15,000.00" in response

    def test_format_markdown_response_payoff_calculation(self, orchestrator):
        """Test formatting payoff calculation results."""
        results = [
            ToolResult(
                tool_name="calculate_payoff",
                parameters={"loan_number": "69253358"},
                success=True,
                result={
                    "principal_balance": 15000.00,
                    "interest_accrued": 678.75,
                    "total_payoff": 15678.75,
                    "calculation_date": "2024-01-31",
                    "days_since_payment": 30
                }
            )
        ]
        
        response = orchestrator.format_markdown_response(results)
        
        assert "## 💰 Payoff Calculation" in response
        assert "**Principal Balance:** $15,000.00" in response
        assert "**Interest Accrued:** $678.75" in response
        assert "**Total Payoff Amount:** $15,678.75" in response

    def test_format_markdown_response_pdf_generation(self, orchestrator):
        """Test formatting PDF generation results."""
        results = [
            ToolResult(
                tool_name="generate_pdf",
                parameters={"loan_number": "69253358"},
                success=True,
                result={
                    "filename": "payoff_69253358_20240131.pdf",
                    "download_url": "/api/files/payoff_69253358_20240131.pdf"
                }
            )
        ]
        
        response = orchestrator.format_markdown_response(results)
        
        assert "## 📄 PDF Generated" in response
        assert "payoff_69253358_20240131.pdf" in response
        assert "/api/files/" in response
        assert "✅ Payoff statement PDF has been generated successfully!" in response

    def test_format_markdown_response_error(self, orchestrator):
        """Test formatting error results."""
        results = [
            ToolResult(
                tool_name="get_loan_info",
                parameters={"identifier": "Unknown"},
                success=False,
                error_message="Loan not found: Unknown"
            )
        ]
        
        response = orchestrator.format_markdown_response(results)
        
        assert "❌ **Error in get_loan_info**" in response
        assert "Loan not found: Unknown" in response

    @pytest.mark.asyncio
    async def test_process_user_message_mock_success(self, orchestrator):
        """Test complete user message processing with mocked AI response."""
        mock_ai_response = {
            "message": {
                "content": "I'll help you get loan information for Mark Wilson.",
                "tool_calls": [
                    {
                        "function": {
                            "name": "get_loan_info",
                            "arguments": '{"identifier": "Mark Wilson"}'
                        }
                    }
                ]
            }
        }
        
        with patch.object(orchestrator, '_call_ollama_api', return_value=mock_ai_response), \
             patch('src.components.ai_orchestrator.loan_data_access') as mock_data_access:
            
            mock_loan = LoanRecord(
                loan_number="69253358",
                borrower_name="Mark Wilson",
                principal_balance=Decimal("15000.00"),
                annual_interest_rate=Decimal("5.50"),
                last_payment_date=date(2024, 1, 1)
            )
            mock_data_access.find_loan_by_identifier.return_value = mock_loan
            
            response = await orchestrator.process_user_message("Show me loan info for Mark Wilson")
            
            assert response.success is True
            assert len(response.tool_calls) == 1
            assert response.tool_calls[0].tool_name == "get_loan_info"
            assert "Mark Wilson" in response.message

    @pytest.mark.asyncio
    async def test_call_ollama_api_connection_error(self, orchestrator):
        """Test handling of Ollama API connection errors."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.side_effect = Exception("Connection failed")
            
            with pytest.raises(AIOrchestrationError):
                await orchestrator._call_ollama_api("test message")

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self, orchestrator):
        """Test handling of unknown tool execution."""
        tool_call = ToolCall(
            tool_name="unknown_tool",
            parameters={"param": "value"}
        )
        
        with pytest.raises(AIOrchestrationError):
            await orchestrator._execute_single_tool(tool_call)


class TestModelConfiguration:
    """Test cases for simple model configuration."""

    def test_model_config_default(self):
        """Test default model configuration."""
        orchestrator = AIOrchestrator()
        assert orchestrator.model_size == QwenModelSize.SIZE_14B
        assert orchestrator.model_name == "qwen3:14b-instruct"
        assert orchestrator.temperature == 0.1

    def test_model_config_8b(self, orchestrator_8b):
        """Test 8B model configuration."""
        assert orchestrator_8b.model_size == QwenModelSize.SIZE_8B
        assert orchestrator_8b.model_name == "qwen3:8b-instruct"
        assert orchestrator_8b.max_tokens == 2048
        assert orchestrator_8b.timeout == 15.0

    def test_model_config_from_env(self):
        """Test model configuration from environment variable."""
        with patch.dict('os.environ', {'MILA_MODEL_SIZE': 'qwen3:30b-instruct'}):
            orchestrator = AIOrchestrator()
            assert orchestrator.model_size == QwenModelSize.SIZE_30B

    def test_model_config_invalid_env(self):
        """Test handling of invalid environment model size."""
        with patch.dict('os.environ', {'MILA_MODEL_SIZE': 'invalid-model'}):
            orchestrator = AIOrchestrator()
            assert orchestrator.model_size == QwenModelSize.SIZE_14B  # Should fallback

    def test_set_model_size(self, orchestrator):
        """Test changing model size dynamically."""
        orchestrator.set_model_size(QwenModelSize.SIZE_30B)
        
        assert orchestrator.model_size == QwenModelSize.SIZE_30B
        assert orchestrator.model_name == "qwen3:30b-instruct"
        assert orchestrator.max_tokens == 8192
        assert orchestrator.timeout == 30.0

    def test_get_model_info(self, orchestrator_8b):
        """Test getting current model information."""
        info = orchestrator_8b.get_model_info()
        
        assert info["model_name"] == "qwen3:8b-instruct"
        assert info["model_size"] == "qwen3:8b-instruct"
        assert info["temperature"] == 0.1
        assert info["max_tokens"] == 2048
        assert info["timeout"] == 15.0
        assert "description" in info

    def test_get_available_models(self, orchestrator):
        """Test getting available models."""
        models = orchestrator.get_available_models()
        
        assert "qwen3:8b-instruct" in models
        assert "qwen3:14b-instruct" in models
        assert "qwen3:30b-instruct" in models
        assert "qwen3:32b-instruct" in models
        
        for model_name, model_data in models.items():
            assert "size" in model_data
            assert "config" in model_data


class TestModelConfig:
    """Test cases for ModelConfig class."""

    def test_get_config_8b(self):
        """Test getting 8B model configuration."""
        config = ModelConfig.get_config(QwenModelSize.SIZE_8B)
        assert config["temperature"] == 0.1
        assert config["max_tokens"] == 2048
        assert config["timeout"] == 15.0
        assert config["description"] == "Lightweight 8B model"

    def test_get_config_30b(self):
        """Test getting 30B model configuration."""
        config = ModelConfig.get_config(QwenModelSize.SIZE_30B)
        assert config["temperature"] == 0.1
        assert config["max_tokens"] == 8192
        assert config["timeout"] == 30.0
        assert config["description"] == "High-quality 30B model"