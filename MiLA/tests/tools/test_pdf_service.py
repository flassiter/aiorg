"""
Unit tests for PDF service functions.
"""
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.tools.pdf_service import generate_pdf, PDFServiceError
from src.models.loan import LoanRecord
from src.models.payoff import PayoffCalculation


@pytest.fixture
def sample_loan_record():
    """Sample loan record for testing."""
    return LoanRecord(
        loan_number="123456",
        borrower_name="John Smith",
        principal_balance=Decimal("10000.00"),
        annual_interest_rate=Decimal("5.5"),
        last_payment_date=date.today() - timedelta(days=30)
    )


@pytest.fixture
def sample_payoff_calculation():
    """Sample payoff calculation for testing."""
    calculation_date = date.today()
    return PayoffCalculation(
        loan_number="123456",
        principal_balance=Decimal("10000.00"),
        interest_accrued=Decimal("45.21"),
        total_payoff=Decimal("10045.21"),
        calculation_date=calculation_date,
        good_through_date=calculation_date + timedelta(days=30),
        days_since_payment=30
    )


@pytest.mark.asyncio
async def test_generate_pdf_success(sample_loan_record, sample_payoff_calculation):
    """Test successful PDF generation."""
    pdf_path = "/tmp/payoff_statement_123456_John_Smith_20240101_123456_abcdef12.pdf"
    
    with patch('src.tools.pdf_service.loan_data_access') as mock_data_access, \
         patch('src.tools.pdf_service.payoff_calculator') as mock_calculator, \
         patch('src.tools.pdf_service.pdf_generator') as mock_pdf_gen:
        
        mock_data_access.find_loan_by_number = AsyncMock(return_value=sample_loan_record)
        mock_calculator.calculate_payoff = MagicMock(return_value=sample_payoff_calculation)
        mock_pdf_gen.generate_payoff_statement = MagicMock(return_value=pdf_path)
        
        result = await generate_pdf("123456")
        
        assert result["loan_number"] == "123456"
        assert result["filename"] == "payoff_statement_123456_John_Smith_20240101_123456_abcdef12.pdf"
        assert result["download_url"] == "/api/files/payoff_statement_123456_John_Smith_20240101_123456_abcdef12.pdf"
        assert result["file_path"] == pdf_path
        
        mock_data_access.find_loan_by_number.assert_called_once_with("123456")
        mock_calculator.calculate_payoff.assert_called_once_with(sample_loan_record, None)
        mock_pdf_gen.generate_payoff_statement.assert_called_once_with(
            sample_loan_record, sample_payoff_calculation, None
        )


@pytest.mark.asyncio
async def test_generate_pdf_with_date(sample_loan_record, sample_payoff_calculation):
    """Test PDF generation with specific date."""
    statement_date = date(2024, 1, 15)
    pdf_path = "/tmp/test.pdf"
    
    with patch('src.tools.pdf_service.loan_data_access') as mock_data_access, \
         patch('src.tools.pdf_service.payoff_calculator') as mock_calculator, \
         patch('src.tools.pdf_service.pdf_generator') as mock_pdf_gen:
        
        mock_data_access.find_loan_by_number = AsyncMock(return_value=sample_loan_record)
        mock_calculator.calculate_payoff = MagicMock(return_value=sample_payoff_calculation)
        mock_pdf_gen.generate_payoff_statement = MagicMock(return_value=pdf_path)
        
        result = await generate_pdf("123456", statement_date)
        
        assert result["loan_number"] == "123456"
        mock_calculator.calculate_payoff.assert_called_once_with(sample_loan_record, statement_date)


@pytest.mark.asyncio
async def test_generate_pdf_with_current_context(sample_loan_record, sample_payoff_calculation):
    """Test PDF generation using current loan context."""
    pdf_path = "/tmp/test.pdf"
    
    with patch('src.tools.pdf_service.loan_data_access') as mock_data_access, \
         patch('src.tools.pdf_service.payoff_calculator') as mock_calculator, \
         patch('src.tools.pdf_service.pdf_generator') as mock_pdf_gen:
        
        mock_data_access.find_loan_by_number = AsyncMock(return_value=sample_loan_record)
        mock_calculator.calculate_payoff = MagicMock(return_value=sample_payoff_calculation)
        mock_pdf_gen.generate_payoff_statement = MagicMock(return_value=pdf_path)
        
        # Test with contextual reference
        result = await generate_pdf("this", current_loan_number="123456")
        
        assert result["loan_number"] == "123456"
        mock_data_access.find_loan_by_number.assert_called_once_with("123456")


@pytest.mark.asyncio
async def test_generate_pdf_custom_server_url(sample_loan_record, sample_payoff_calculation):
    """Test PDF generation with custom server base URL."""
    pdf_path = "/tmp/test.pdf"
    server_url = "https://example.com:8080"
    
    with patch('src.tools.pdf_service.loan_data_access') as mock_data_access, \
         patch('src.tools.pdf_service.payoff_calculator') as mock_calculator, \
         patch('src.tools.pdf_service.pdf_generator') as mock_pdf_gen:
        
        mock_data_access.find_loan_by_number = AsyncMock(return_value=sample_loan_record)
        mock_calculator.calculate_payoff = MagicMock(return_value=sample_payoff_calculation)
        mock_pdf_gen.generate_payoff_statement = MagicMock(return_value=pdf_path)
        
        result = await generate_pdf("123456", server_base_url=server_url)
        
        assert result["download_url"] == "/api/files/test.pdf"


@pytest.mark.asyncio
async def test_generate_pdf_loan_not_found():
    """Test PDF generation when loan is not found."""
    with patch('src.tools.pdf_service.loan_data_access') as mock_data_access:
        mock_data_access.find_loan_by_number = AsyncMock(return_value=None)
        
        with pytest.raises(PDFServiceError, match="Loan not found: 999999"):
            await generate_pdf("999999")


@pytest.mark.asyncio
async def test_generate_pdf_no_loan_number_no_context():
    """Test PDF generation when no loan number and no context provided."""
    with pytest.raises(PDFServiceError, match="No loan number provided"):
        await generate_pdf("")


@pytest.mark.asyncio
async def test_generate_pdf_data_access_error():
    """Test PDF generation when data access raises an error."""
    from src.components.data_access import DataAccessError
    
    with patch('src.tools.pdf_service.loan_data_access') as mock_data_access:
        mock_data_access.find_loan_by_number = AsyncMock(
            side_effect=DataAccessError("Database connection failed")
        )
        
        with pytest.raises(PDFServiceError, match="Database connection failed"):
            await generate_pdf("123456")


@pytest.mark.asyncio
async def test_generate_pdf_calculation_error(sample_loan_record):
    """Test PDF generation when calculator raises an error."""
    from src.components.calculator import CalculationError
    
    with patch('src.tools.pdf_service.loan_data_access') as mock_data_access, \
         patch('src.tools.pdf_service.payoff_calculator') as mock_calculator:
        
        mock_data_access.find_loan_by_number = AsyncMock(return_value=sample_loan_record)
        mock_calculator.calculate_payoff = MagicMock(
            side_effect=CalculationError("Invalid calculation parameters")
        )
        
        with pytest.raises(PDFServiceError, match="Invalid calculation parameters"):
            await generate_pdf("123456")


@pytest.mark.asyncio
async def test_generate_pdf_generation_error(sample_loan_record, sample_payoff_calculation):
    """Test PDF generation when PDF generator raises an error."""
    from src.components.pdf_generator import PDFGenerationError
    
    with patch('src.tools.pdf_service.loan_data_access') as mock_data_access, \
         patch('src.tools.pdf_service.payoff_calculator') as mock_calculator, \
         patch('src.tools.pdf_service.pdf_generator') as mock_pdf_gen:
        
        mock_data_access.find_loan_by_number = AsyncMock(return_value=sample_loan_record)
        mock_calculator.calculate_payoff = MagicMock(return_value=sample_payoff_calculation)
        mock_pdf_gen.generate_payoff_statement = MagicMock(
            side_effect=PDFGenerationError("PDF generation failed")
        )
        
        with pytest.raises(PDFServiceError, match="PDF generation failed"):
            await generate_pdf("123456")