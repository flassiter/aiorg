"""
Data access component for loading and searching loan data from Excel files.
"""
import logging
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import List, Optional

import pandas as pd
from pydantic import ValidationError

from ..models.loan import LoanRecord

logger = logging.getLogger(__name__)


class DataAccessError(Exception):
    """Custom exception for data access operations."""
    pass


class LoanDataAccess:
    """
    Data access layer for loan records stored in Excel files.
    """
    
    def __init__(self):
        self._loans: List[LoanRecord] = []
        self._loaded_file: Optional[str] = None

    async def load_loan_data(self, file_path: str) -> List[LoanRecord]:
        """
        Load loan data from an Excel file.
        
        Args:
            file_path: Path to the Excel file containing loan data
            
        Returns:
            List of validated LoanRecord objects
            
        Raises:
            DataAccessError: If file cannot be loaded or data is invalid
        """
        try:
            # Validate file exists
            path = Path(file_path)
            if not path.exists():
                raise DataAccessError(f"File not found: {file_path}")
            
            if not path.suffix.lower() in ['.xlsx', '.xls']:
                raise DataAccessError(f"Invalid file format. Expected Excel file (.xlsx or .xls): {file_path}")
            
            logger.info(f"Loading loan data from {file_path}")
            
            # Load Excel file
            df = pd.read_excel(file_path)
            
            # Validate required columns
            required_columns = [
                'Loan Number', 'Borrower Name', 'Principal Balance', 
                'Annual Interest Rate', 'Last Payment Date'
            ]
            
            # Optional columns
            optional_columns = ['Email Address']
            
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise DataAccessError(f"Missing required columns: {missing_columns}")
            
            # Convert and validate data
            loans = []
            validation_errors = []
            
            for index, row in df.iterrows():
                try:
                    # Handle potential NaN values
                    if pd.isna(row['Loan Number']) or pd.isna(row['Borrower Name']):
                        validation_errors.append(f"Row {index + 1}: Missing loan number or borrower name")
                        continue
                    
                    # Convert data types
                    loan_data = {
                        'loan_number': str(int(row['Loan Number'])) if not pd.isna(row['Loan Number']) else '',
                        'borrower_name': str(row['Borrower Name']).strip(),
                        'principal_balance': Decimal(str(row['Principal Balance'])),
                        'annual_interest_rate': Decimal(str(row['Annual Interest Rate'])),
                        'last_payment_date': pd.to_datetime(row['Last Payment Date']).date()
                    }
                    
                    # Add optional email address if available
                    if 'Email Address' in df.columns and not pd.isna(row['Email Address']):
                        loan_data['email_address'] = str(row['Email Address']).strip()
                    
                    # Validate with Pydantic model
                    loan = LoanRecord(**loan_data)
                    loans.append(loan)
                    
                except (ValueError, ValidationError, TypeError) as e:
                    validation_errors.append(f"Row {index + 1}: {str(e)}")
                    continue
            
            if validation_errors:
                error_msg = "Data validation errors:\n" + "\n".join(validation_errors)
                logger.warning(error_msg)
                if len(loans) == 0:
                    raise DataAccessError(f"No valid loan records found. {error_msg}")
            
            # Store loaded data
            self._loans = loans
            self._loaded_file = file_path
            
            logger.info(f"Successfully loaded {len(loans)} loan records from {file_path}")
            return loans
            
        except pd.errors.EmptyDataError:
            raise DataAccessError(f"Excel file is empty: {file_path}")
        except pd.errors.ParserError as e:
            raise DataAccessError(f"Failed to parse Excel file: {str(e)}")
        except Exception as e:
            if isinstance(e, DataAccessError):
                raise
            raise DataAccessError(f"Unexpected error loading data: {str(e)}")

    async def find_loan_by_number(self, loan_number: str) -> Optional[LoanRecord]:
        """
        Find a loan record by loan number.
        
        Args:
            loan_number: The loan number to search for
            
        Returns:
            LoanRecord if found, None otherwise
        """
        # Auto-load default data if no data is loaded
        if not self.is_data_loaded():
            sample_data_path = Path(__file__).parent.parent.parent / "data" / "sample_loans.xlsx"
            if sample_data_path.exists():
                try:
                    await self.load_loan_data(str(sample_data_path))
                    logger.info(f"Auto-loaded {self.get_loan_count()} loan records for search")
                except DataAccessError as e:
                    logger.warning(f"Could not auto-load sample data: {str(e)}")
                    return None
            else:
                logger.warning(f"Sample data file not found at {sample_data_path}")
                return None
        
        # Normalize input
        loan_number = loan_number.strip()
        
        # Search for exact match
        for loan in self._loans:
            if loan.loan_number == loan_number:
                logger.debug(f"Found loan by number: {loan_number}")
                return loan
        
        logger.debug(f"Loan not found by number: {loan_number}")
        return None

    async def find_loan_by_name(self, borrower_name: str) -> Optional[LoanRecord]:
        """
        Find a loan record by borrower name (case-insensitive).
        
        Args:
            borrower_name: The borrower name to search for
            
        Returns:
            LoanRecord if found, None otherwise
        """
        # Auto-load default data if no data is loaded
        if not self.is_data_loaded():
            sample_data_path = Path(__file__).parent.parent.parent / "data" / "sample_loans.xlsx"
            if sample_data_path.exists():
                try:
                    await self.load_loan_data(str(sample_data_path))
                    logger.info(f"Auto-loaded {self.get_loan_count()} loan records for search")
                except DataAccessError as e:
                    logger.warning(f"Could not auto-load sample data: {str(e)}")
                    return None
            else:
                logger.warning(f"Sample data file not found at {sample_data_path}")
                return None
        
        # Normalize input
        borrower_name = borrower_name.strip().lower()
        
        # Search for case-insensitive match
        for loan in self._loans:
            if loan.borrower_name.lower() == borrower_name:
                logger.debug(f"Found loan by name: {borrower_name}")
                return loan
        
        logger.debug(f"Loan not found by name: {borrower_name}")
        return None

    async def find_loan_by_identifier(self, identifier: str) -> Optional[LoanRecord]:
        """
        Find a loan record by either loan number or borrower name.
        
        Args:
            identifier: Either a loan number or borrower name
            
        Returns:
            LoanRecord if found, None otherwise
        """
        # Try loan number first (if it's all digits)
        identifier = identifier.strip()
        
        if identifier.isdigit():
            loan = await self.find_loan_by_number(identifier)
            if loan:
                return loan
        
        # Try borrower name
        return await self.find_loan_by_name(identifier)

    def get_all_loans(self) -> List[LoanRecord]:
        """
        Get all loaded loan records.
        
        Returns:
            List of all LoanRecord objects
        """
        return self._loans.copy()

    def get_loan_count(self) -> int:
        """
        Get the number of loaded loan records.
        
        Returns:
            Number of loan records
        """
        return len(self._loans)

    def is_data_loaded(self) -> bool:
        """
        Check if loan data has been loaded.
        
        Returns:
            True if data is loaded, False otherwise
        """
        return len(self._loans) > 0

    def get_loaded_file(self) -> Optional[str]:
        """
        Get the path of the currently loaded file.
        
        Returns:
            File path if data is loaded, None otherwise
        """
        return self._loaded_file

    async def validate_loan_data(self, loan_data: dict) -> bool:
        """
        Validate loan data against the LoanRecord model.
        
        Args:
            loan_data: Dictionary containing loan data
            
        Returns:
            True if valid, False otherwise
        """
        try:
            LoanRecord(**loan_data)
            return True
        except ValidationError:
            return False


# Global instance for dependency injection
loan_data_access = LoanDataAccess()