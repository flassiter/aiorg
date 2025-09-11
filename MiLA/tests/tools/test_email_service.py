"""
Unit tests for email service functions.
"""
from unittest.mock import AsyncMock, patch

import pytest

from src.tools.email_service import send_payoff_email, confirm_email_send, EmailServiceError
from src.models.session import ContextData


@pytest.fixture
def sample_loan_data():
    """Sample loan data for testing."""
    return {
        "loan_number": "123456",
        "borrower_name": "John Smith",
        "principal_balance": 10000.00,
        "annual_interest_rate": 5.5,
        "email_address": "john.smith@example.com"
    }


@pytest.fixture
def sample_payoff_data():
    """Sample payoff data for testing."""
    return {
        "principal_balance": 10000.00,
        "interest_accrued": 45.21,
        "total_payoff": 10045.21,
        "calculation_date": "2024-01-15",
        "good_through_date": "2024-02-14"
    }


@pytest.fixture
def sample_context_data():
    """Sample context data for testing."""
    return ContextData(
        current_loan_number="123456",
        current_borrower_name="John Smith",
        borrower_email="john.smith@example.com"
    )


@pytest.mark.asyncio
async def test_send_payoff_email_success(sample_loan_data, sample_payoff_data):
    """Test successful email sending."""
    mock_result = {"status": "sent", "message_id": "12345"}
    
    with patch('src.tools.email_service.email_service') as mock_email_service:
        mock_email_service.send_payoff_statement = AsyncMock(return_value=mock_result)
        
        result = await send_payoff_email(
            email_address="john.smith@example.com",
            loan_number="123456",
            current_loan_data=sample_loan_data,
            current_payoff_data=sample_payoff_data,
            generated_pdf_filename="statement.pdf"
        )
        
        assert result["data"] == mock_result
        mock_email_service.send_payoff_statement.assert_called_once_with(
            "john.smith@example.com",
            "123456",
            "John Smith",
            10045.21,
            "statement.pdf"
        )


@pytest.mark.asyncio
async def test_send_payoff_email_no_address_use_context(sample_loan_data, sample_payoff_data):
    """Test email sending when no address provided, using context."""
    mock_result = {"status": "sent", "message_id": "12345"}
    
    with patch('src.tools.email_service.email_service') as mock_email_service:
        mock_email_service.get_borrower_email = AsyncMock(return_value="john.smith@example.com")
        mock_email_service.send_payoff_statement = AsyncMock(return_value=mock_result)
        
        result = await send_payoff_email(
            current_loan_data=sample_loan_data,
            current_payoff_data=sample_payoff_data
        )
        
        assert result["data"] == mock_result
        mock_email_service.get_borrower_email.assert_called_once_with(sample_loan_data)
        mock_email_service.send_payoff_statement.assert_called_once_with(
            "john.smith@example.com",
            "123456",
            "John Smith",
            10045.21,
            None
        )


@pytest.mark.asyncio
async def test_send_payoff_email_no_address_not_available():
    """Test email sending when no address is available."""
    with patch('src.tools.email_service.email_service') as mock_email_service:
        mock_email_service.get_borrower_email = AsyncMock(return_value=None)
        
        with pytest.raises(EmailServiceError, match="No email address available for borrower"):
            await send_payoff_email()


@pytest.mark.asyncio
async def test_send_payoff_email_service_error():
    """Test email sending when email service raises an error."""
    from src.components.email_service import EmailSimulationError
    
    with patch('src.tools.email_service.email_service') as mock_email_service:
        mock_email_service.send_payoff_statement = AsyncMock(
            side_effect=EmailSimulationError("Email service unavailable")
        )
        
        with pytest.raises(EmailServiceError, match="Email service unavailable"):
            await send_payoff_email(email_address="test@example.com")


@pytest.mark.asyncio
async def test_confirm_email_send_success(sample_context_data):
    """Test successful email confirmation."""
    confirmation_msg = "Email will be sent to john.smith@example.com. Proceed?"
    
    with patch('src.tools.email_service.email_service') as mock_email_service:
        mock_email_service.confirm_email_send = AsyncMock(return_value=confirmation_msg)
        
        result = await confirm_email_send("john.smith@example.com", sample_context_data)
        
        assert result["data"]["confirmation_message"] == confirmation_msg
        assert result["data"]["email_address"] == "john.smith@example.com"
        assert result["data"]["requires_user_response"] is True
        
        mock_email_service.confirm_email_send.assert_called_once_with(
            "john.smith@example.com", sample_context_data
        )


@pytest.mark.asyncio
async def test_confirm_email_send_error(sample_context_data):
    """Test email confirmation when service raises an error."""
    with patch('src.tools.email_service.email_service') as mock_email_service:
        mock_email_service.confirm_email_send = AsyncMock(
            side_effect=Exception("Confirmation service error")
        )
        
        with pytest.raises(EmailServiceError, match="Unexpected error confirming email"):
            await confirm_email_send("test@example.com", sample_context_data)


@pytest.mark.asyncio
async def test_send_payoff_email_with_defaults():
    """Test email sending with minimal parameters using defaults."""
    mock_result = {"status": "sent", "message_id": "12345"}
    
    with patch('src.tools.email_service.email_service') as mock_email_service:
        mock_email_service.send_payoff_statement = AsyncMock(return_value=mock_result)
        
        result = await send_payoff_email(email_address="test@example.com")
        
        assert result["data"] == mock_result
        mock_email_service.send_payoff_statement.assert_called_once_with(
            "test@example.com",
            None,
            "Borrower",
            0,
            None
        )