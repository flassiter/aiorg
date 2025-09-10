"""
Comprehensive unit tests for the data access component.
"""
import tempfile
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from src.components.data_access import LoanDataAccess, DataAccessError
from src.models.loan import LoanRecord


@pytest.fixture
def sample_loan_data():
    """Sample loan data for testing."""
    return [
        {
            "Loan Number": "123456",
            "Borrower Name": "John Smith",
            "Principal Balance": 10000.00,
            "Annual Interest Rate": 5.5,
            "Last Payment Date": date.today() - timedelta(days=30)
        },
        {
            "Loan Number": "789012",
            "Borrower Name": "Jane Doe",
            "Principal Balance": 25000.50,
            "Annual Interest Rate": 7.25,
            "Last Payment Date": date.today() - timedelta(days=60)
        },
        {
            "Loan Number": "345678",
            "Borrower Name": "Bob Johnson",
            "Principal Balance": 5000.00,
            "Annual Interest Rate": 12.0,
            "Last Payment Date": date.today() - timedelta(days=90)
        }
    ]


@pytest.fixture
def sample_excel_file(sample_loan_data):
    """Create a temporary Excel file with sample loan data."""
    df = pd.DataFrame(sample_loan_data)
    
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
        df.to_excel(f.name, index=False)
        yield f.name
    
    # Cleanup
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def loan_data_access():
    """Create a fresh LoanDataAccess instance for each test."""
    return LoanDataAccess()


class TestLoanDataAccess:
    """Test suite for LoanDataAccess class."""

    @pytest.mark.asyncio
    async def test_load_loan_data_success(self, loan_data_access, sample_excel_file):
        """Test successful loading of loan data from Excel file."""
        loans = await loan_data_access.load_loan_data(sample_excel_file)
        
        assert len(loans) == 3
        assert all(isinstance(loan, LoanRecord) for loan in loans)
        assert loan_data_access.is_data_loaded()
        assert loan_data_access.get_loan_count() == 3
        assert loan_data_access.get_loaded_file() == sample_excel_file

    @pytest.mark.asyncio
    async def test_load_loan_data_file_not_found(self, loan_data_access):
        """Test loading data from non-existent file."""
        with pytest.raises(DataAccessError, match="File not found"):
            await loan_data_access.load_loan_data("/nonexistent/file.xlsx")

    @pytest.mark.asyncio
    async def test_load_loan_data_invalid_file_format(self, loan_data_access):
        """Test loading data from invalid file format."""
        with tempfile.NamedTemporaryFile(suffix='.txt') as f:
            with pytest.raises(DataAccessError, match="Invalid file format"):
                await loan_data_access.load_loan_data(f.name)

    @pytest.mark.asyncio
    async def test_load_loan_data_missing_columns(self, loan_data_access):
        """Test loading data with missing required columns."""
        # Create Excel file with missing columns
        df = pd.DataFrame({
            "Loan Number": ["123456"],
            "Borrower Name": ["John Smith"]
            # Missing required columns
        })
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            df.to_excel(f.name, index=False)
            
            with pytest.raises(DataAccessError, match="Missing required columns"):
                await loan_data_access.load_loan_data(f.name)
        
        Path(f.name).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_load_loan_data_empty_file(self, loan_data_access):
        """Test loading data from empty Excel file."""
        df = pd.DataFrame()
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            df.to_excel(f.name, index=False)
            
            with pytest.raises(DataAccessError):
                await loan_data_access.load_loan_data(f.name)
        
        Path(f.name).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_load_loan_data_invalid_data_types(self, loan_data_access):
        """Test loading data with invalid data types."""
        # Create Excel file with invalid data
        df = pd.DataFrame({
            "Loan Number": ["not_a_number"],
            "Borrower Name": ["John Smith"],
            "Principal Balance": ["invalid_amount"],
            "Annual Interest Rate": ["invalid_rate"],
            "Last Payment Date": ["invalid_date"]
        })
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            df.to_excel(f.name, index=False)
            
            with pytest.raises(DataAccessError, match="No valid loan records found"):
                await loan_data_access.load_loan_data(f.name)
        
        Path(f.name).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_find_loan_by_number_success(self, loan_data_access, sample_excel_file):
        """Test successful loan search by number."""
        await loan_data_access.load_loan_data(sample_excel_file)
        
        loan = await loan_data_access.find_loan_by_number("123456")
        
        assert loan is not None
        assert loan.loan_number == "123456"
        assert loan.borrower_name == "John Smith"

    @pytest.mark.asyncio
    async def test_find_loan_by_number_not_found(self, loan_data_access, sample_excel_file):
        """Test loan search by non-existent number."""
        await loan_data_access.load_loan_data(sample_excel_file)
        
        loan = await loan_data_access.find_loan_by_number("999999")
        
        assert loan is None

    @pytest.mark.asyncio
    async def test_find_loan_by_number_no_data_loaded(self, loan_data_access):
        """Test loan search when no data is loaded."""
        loan = await loan_data_access.find_loan_by_number("123456")
        
        assert loan is None

    @pytest.mark.asyncio
    async def test_find_loan_by_name_success(self, loan_data_access, sample_excel_file):
        """Test successful loan search by name."""
        await loan_data_access.load_loan_data(sample_excel_file)
        
        loan = await loan_data_access.find_loan_by_name("Jane Doe")
        
        assert loan is not None
        assert loan.loan_number == "789012"
        assert loan.borrower_name == "Jane Doe"

    @pytest.mark.asyncio
    async def test_find_loan_by_name_case_insensitive(self, loan_data_access, sample_excel_file):
        """Test case-insensitive loan search by name."""
        await loan_data_access.load_loan_data(sample_excel_file)
        
        loan = await loan_data_access.find_loan_by_name("jane doe")
        
        assert loan is not None
        assert loan.borrower_name == "Jane Doe"

    @pytest.mark.asyncio
    async def test_find_loan_by_name_not_found(self, loan_data_access, sample_excel_file):
        """Test loan search by non-existent name."""
        await loan_data_access.load_loan_data(sample_excel_file)
        
        loan = await loan_data_access.find_loan_by_name("Non Existent")
        
        assert loan is None

    @pytest.mark.asyncio
    async def test_find_loan_by_identifier_loan_number(self, loan_data_access, sample_excel_file):
        """Test loan search by identifier (loan number)."""
        await loan_data_access.load_loan_data(sample_excel_file)
        
        loan = await loan_data_access.find_loan_by_identifier("123456")
        
        assert loan is not None
        assert loan.loan_number == "123456"

    @pytest.mark.asyncio
    async def test_find_loan_by_identifier_borrower_name(self, loan_data_access, sample_excel_file):
        """Test loan search by identifier (borrower name)."""
        await loan_data_access.load_loan_data(sample_excel_file)
        
        loan = await loan_data_access.find_loan_by_identifier("Bob Johnson")
        
        assert loan is not None
        assert loan.borrower_name == "Bob Johnson"

    @pytest.mark.asyncio
    async def test_find_loan_by_identifier_not_found(self, loan_data_access, sample_excel_file):
        """Test loan search by identifier when not found."""
        await loan_data_access.load_loan_data(sample_excel_file)
        
        loan = await loan_data_access.find_loan_by_identifier("999999")
        
        assert loan is None

    def test_get_all_loans(self, loan_data_access, sample_excel_file):
        """Test getting all loaded loans."""
        # Test with no data loaded
        assert loan_data_access.get_all_loans() == []
        
        # Load data and test
        import asyncio
        asyncio.run(loan_data_access.load_loan_data(sample_excel_file))
        
        loans = loan_data_access.get_all_loans()
        assert len(loans) == 3
        assert all(isinstance(loan, LoanRecord) for loan in loans)

    def test_get_loan_count(self, loan_data_access, sample_excel_file):
        """Test getting loan count."""
        # Test with no data loaded
        assert loan_data_access.get_loan_count() == 0
        
        # Load data and test
        import asyncio
        asyncio.run(loan_data_access.load_loan_data(sample_excel_file))
        
        assert loan_data_access.get_loan_count() == 3

    def test_is_data_loaded(self, loan_data_access, sample_excel_file):
        """Test checking if data is loaded."""
        # Test with no data loaded
        assert not loan_data_access.is_data_loaded()
        
        # Load data and test
        import asyncio
        asyncio.run(loan_data_access.load_loan_data(sample_excel_file))
        
        assert loan_data_access.is_data_loaded()

    def test_get_loaded_file(self, loan_data_access, sample_excel_file):
        """Test getting loaded file path."""
        # Test with no data loaded
        assert loan_data_access.get_loaded_file() is None
        
        # Load data and test
        import asyncio
        asyncio.run(loan_data_access.load_loan_data(sample_excel_file))
        
        assert loan_data_access.get_loaded_file() == sample_excel_file

    @pytest.mark.asyncio
    async def test_validate_loan_data_valid(self, loan_data_access):
        """Test validation with valid loan data."""
        valid_data = {
            "loan_number": "123456",
            "borrower_name": "John Smith",
            "principal_balance": Decimal("10000.00"),
            "annual_interest_rate": Decimal("5.5"),
            "last_payment_date": date.today()
        }
        
        is_valid = await loan_data_access.validate_loan_data(valid_data)
        assert is_valid

    @pytest.mark.asyncio
    async def test_validate_loan_data_invalid(self, loan_data_access):
        """Test validation with invalid loan data."""
        invalid_data = {
            "loan_number": "abc",  # Should be digits only
            "borrower_name": "",  # Should not be empty
            "principal_balance": -1000,  # Should be >= 0
            "annual_interest_rate": 150,  # Should be <= 100
            "last_payment_date": "invalid_date"  # Should be a date
        }
        
        is_valid = await loan_data_access.validate_loan_data(invalid_data)
        assert not is_valid

    @pytest.mark.asyncio
    async def test_load_loan_data_partial_invalid_data(self, loan_data_access):
        """Test loading data with some invalid records."""
        # Create mixed valid/invalid data
        mixed_data = [
            {
                "Loan Number": "123456",
                "Borrower Name": "John Smith",
                "Principal Balance": 10000.00,
                "Annual Interest Rate": 5.5,
                "Last Payment Date": date.today() - timedelta(days=30)
            },
            {
                "Loan Number": "invalid",  # Invalid loan number
                "Borrower Name": "Invalid User",
                "Principal Balance": 5000.00,
                "Annual Interest Rate": 7.0,
                "Last Payment Date": date.today() - timedelta(days=60)
            },
            {
                "Loan Number": "789012",
                "Borrower Name": "Jane Doe",
                "Principal Balance": 15000.00,
                "Annual Interest Rate": 6.5,
                "Last Payment Date": date.today() - timedelta(days=45)
            }
        ]
        
        df = pd.DataFrame(mixed_data)
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            df.to_excel(f.name, index=False)
            
            # Should load valid records and skip invalid ones
            loans = await loan_data_access.load_loan_data(f.name)
            assert len(loans) == 2  # Only valid records
            
        Path(f.name).unlink(missing_ok=True)

    @pytest.mark.asyncio 
    async def test_load_loan_data_with_nan_values(self, loan_data_access):
        """Test loading data with NaN values."""
        import numpy as np
        
        data_with_nan = [
            {
                "Loan Number": np.nan,  # NaN loan number
                "Borrower Name": "John Smith",
                "Principal Balance": 10000.00,
                "Annual Interest Rate": 5.5,
                "Last Payment Date": date.today() - timedelta(days=30)
            },
            {
                "Loan Number": "789012",
                "Borrower Name": np.nan,  # NaN borrower name
                "Principal Balance": 15000.00,
                "Annual Interest Rate": 6.5,
                "Last Payment Date": date.today() - timedelta(days=45)
            }
        ]
        
        df = pd.DataFrame(data_with_nan)
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            df.to_excel(f.name, index=False)
            
            # Should raise error as no valid records
            with pytest.raises(DataAccessError, match="No valid loan records found"):
                await loan_data_access.load_loan_data(f.name)
            
        Path(f.name).unlink(missing_ok=True)


# Integration test
class TestDataAccessIntegration:
    """Integration tests for data access with real sample file."""

    @pytest.mark.asyncio
    async def test_load_and_search_sample_data(self):
        """Test loading and searching sample data file."""
        sample_file = Path(__file__).parent.parent / "data" / "sample_loans.xlsx"
        
        if not sample_file.exists():
            pytest.skip("Sample data file not found")
        
        data_access = LoanDataAccess()
        
        # Load data
        loans = await data_access.load_loan_data(str(sample_file))
        
        assert len(loans) > 0
        assert data_access.is_data_loaded()
        
        # Test searching by first loan number
        first_loan = loans[0]
        found_loan = await data_access.find_loan_by_number(first_loan.loan_number)
        
        assert found_loan is not None
        assert found_loan.loan_number == first_loan.loan_number
        
        # Test searching by first borrower name
        found_by_name = await data_access.find_loan_by_name(first_loan.borrower_name)
        
        assert found_by_name is not None
        assert found_by_name.borrower_name == first_loan.borrower_name