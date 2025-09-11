"""
Unit tests for calculation service functions.
"""
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.tools.calculation_service import calculate_payoff, CalculationServiceError
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
async def test_calculate_payoff_success(sample_loan_record, sample_payoff_calculation):
    """Test successful payoff calculation."""
    with patch('src.tools.calculation_service.loan_data_access') as mock_data_access, \
         patch('src.tools.calculation_service.payoff_calculator') as mock_calculator:
        
        mock_data_access.find_loan_by_number = AsyncMock(return_value=sample_loan_record)
        mock_calculator.calculate_payoff = MagicMock(return_value=sample_payoff_calculation)
        
        result = await calculate_payoff("123456")
        
        assert result["loan_number"] == "123456"
        assert result["principal_balance"] == 10000.00
        assert result["interest_accrued"] == 45.21
        assert result["total_payoff"] == 10045.21
        assert result["days_since_payment"] == 30
        
        mock_data_access.find_loan_by_number.assert_called_once_with("123456")
        mock_calculator.calculate_payoff.assert_called_once_with(sample_loan_record, None)


@pytest.mark.asyncio
async def test_calculate_payoff_with_date(sample_loan_record, sample_payoff_calculation):
    """Test payoff calculation with specific date."""
    calculation_date = date(2024, 1, 15)
    
    with patch('src.tools.calculation_service.loan_data_access') as mock_data_access, \
         patch('src.tools.calculation_service.payoff_calculator') as mock_calculator:
        
        mock_data_access.find_loan_by_number = AsyncMock(return_value=sample_loan_record)
        mock_calculator.calculate_payoff = MagicMock(return_value=sample_payoff_calculation)
        
        result = await calculate_payoff("123456", calculation_date)
        
        assert result["loan_number"] == "123456"
        mock_calculator.calculate_payoff.assert_called_once_with(sample_loan_record, calculation_date)


@pytest.mark.asyncio
async def test_calculate_payoff_with_current_context(sample_loan_record, sample_payoff_calculation):
    """Test payoff calculation using current loan context."""
    with patch('src.tools.calculation_service.loan_data_access') as mock_data_access, \
         patch('src.tools.calculation_service.payoff_calculator') as mock_calculator:
        
        mock_data_access.find_loan_by_number = AsyncMock(return_value=sample_loan_record)
        mock_calculator.calculate_payoff = MagicMock(return_value=sample_payoff_calculation)
        
        # Test with contextual reference
        result = await calculate_payoff("this", current_loan_number="123456")
        
        assert result["loan_number"] == "123456"
        mock_data_access.find_loan_by_number.assert_called_once_with("123456")


@pytest.mark.asyncio
async def test_calculate_payoff_loan_not_found():
    """Test payoff calculation when loan is not found."""
    with patch('src.tools.calculation_service.loan_data_access') as mock_data_access:
        mock_data_access.find_loan_by_number = AsyncMock(return_value=None)
        
        with pytest.raises(CalculationServiceError, match="Loan not found: 999999"):
            await calculate_payoff("999999")


@pytest.mark.asyncio
async def test_calculate_payoff_no_loan_number_no_context():
    """Test payoff calculation when no loan number and no context provided."""
    with pytest.raises(CalculationServiceError, match="No loan number provided"):
        await calculate_payoff("")


@pytest.mark.asyncio
async def test_calculate_payoff_data_access_error():
    """Test payoff calculation when data access raises an error."""
    from src.components.data_access import DataAccessError
    
    with patch('src.tools.calculation_service.loan_data_access') as mock_data_access:
        mock_data_access.find_loan_by_number = AsyncMock(
            side_effect=DataAccessError("Database connection failed")
        )
        
        with pytest.raises(CalculationServiceError, match="Database connection failed"):
            await calculate_payoff("123456")


@pytest.mark.asyncio
async def test_calculate_payoff_calculation_error(sample_loan_record):
    """Test payoff calculation when calculator raises an error."""
    from src.components.calculator import CalculationError
    
    with patch('src.tools.calculation_service.loan_data_access') as mock_data_access, \
         patch('src.tools.calculation_service.payoff_calculator') as mock_calculator:
        
        mock_data_access.find_loan_by_number = AsyncMock(return_value=sample_loan_record)
        mock_calculator.calculate_payoff = MagicMock(
            side_effect=CalculationError("Invalid calculation parameters")
        )
        
        with pytest.raises(CalculationServiceError, match="Invalid calculation parameters"):
            await calculate_payoff("123456")