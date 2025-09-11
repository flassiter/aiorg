"""
Unit tests for loan service functions.
"""
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from src.tools.loan_service import find_loan, LoanServiceError
from src.models.loan import LoanRecord


@pytest.fixture
def sample_loan_record():
    """Sample loan record for testing."""
    return LoanRecord(
        loan_number="123456",
        borrower_name="John Smith",
        principal_balance=Decimal("10000.00"),
        annual_interest_rate=Decimal("5.5"),
        last_payment_date=date.today() - timedelta(days=30),
        email_address="john.smith@example.com"
    )


@pytest.mark.asyncio
async def test_find_loan_by_identifier_success(sample_loan_record):
    """Test successful loan lookup by identifier."""
    with patch('src.tools.loan_service.loan_data_access') as mock_data_access:
        mock_data_access.find_loan_by_identifier = AsyncMock(return_value=sample_loan_record)
        
        result = await find_loan("123456")
        
        assert result["loan_number"] == "123456"
        assert result["borrower_name"] == "John Smith"
        assert result["principal_balance"] == 10000.00
        assert result["annual_interest_rate"] == 5.5
        assert result["email_address"] == "john.smith@example.com"
        mock_data_access.find_loan_by_identifier.assert_called_once_with("123456")


@pytest.mark.asyncio
async def test_find_loan_with_current_context():
    """Test loan lookup using current loan context."""
    sample_record = LoanRecord(
        loan_number="789012",
        borrower_name="Jane Doe",
        principal_balance=Decimal("25000.00"),
        annual_interest_rate=Decimal("7.25"),
        last_payment_date=date.today() - timedelta(days=60)
    )
    
    with patch('src.tools.loan_service.loan_data_access') as mock_data_access:
        mock_data_access.find_loan_by_identifier = AsyncMock(return_value=sample_record)
        
        # Test with contextual reference
        result = await find_loan("this", current_loan_number="789012")
        
        assert result["loan_number"] == "789012"
        assert result["borrower_name"] == "Jane Doe"
        mock_data_access.find_loan_by_identifier.assert_called_once_with("789012")


@pytest.mark.asyncio
async def test_find_loan_not_found():
    """Test loan lookup when loan is not found."""
    with patch('src.tools.loan_service.loan_data_access') as mock_data_access:
        mock_data_access.find_loan_by_identifier = AsyncMock(return_value=None)
        
        with pytest.raises(LoanServiceError, match="Loan not found: 999999"):
            await find_loan("999999")


@pytest.mark.asyncio
async def test_find_loan_no_identifier_no_context():
    """Test loan lookup when no identifier and no context provided."""
    with pytest.raises(LoanServiceError, match="No loan identifier provided"):
        await find_loan("")


@pytest.mark.asyncio
async def test_find_loan_data_access_error():
    """Test loan lookup when data access raises an error."""
    from src.components.data_access import DataAccessError
    
    with patch('src.tools.loan_service.loan_data_access') as mock_data_access:
        mock_data_access.find_loan_by_identifier = AsyncMock(
            side_effect=DataAccessError("Database connection failed")
        )
        
        with pytest.raises(LoanServiceError, match="Database connection failed"):
            await find_loan("123456")


@pytest.mark.asyncio
async def test_find_loan_without_email_address():
    """Test loan lookup for record without email address."""
    sample_record = LoanRecord(
        loan_number="123456",
        borrower_name="John Smith",
        principal_balance=Decimal("10000.00"),
        annual_interest_rate=Decimal("5.5"),
        last_payment_date=date.today() - timedelta(days=30)
    )
    
    with patch('src.tools.loan_service.loan_data_access') as mock_data_access:
        mock_data_access.find_loan_by_identifier = AsyncMock(return_value=sample_record)
        
        result = await find_loan("123456")
        
        assert result["loan_number"] == "123456"
        assert result["borrower_name"] == "John Smith"
        assert "email_address" not in result