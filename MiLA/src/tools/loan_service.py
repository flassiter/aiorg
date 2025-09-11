"""
Loan service functions for MiLA system.
Pure, stateless functions for loan operations.
"""
from typing import Optional, Dict, Any
from ..components.data_access import loan_data_access, DataAccessError


class LoanServiceError(Exception):
    """Custom exception for loan service operations."""
    pass


async def find_loan(identifier: str, current_loan_number: Optional[str] = None) -> Dict[str, Any]:
    """
    Find loan information by identifier.
    
    Args:
        identifier: Loan number (6-8 digits) or borrower name (First Last format)
        current_loan_number: Optional current loan number from context
        
    Returns:
        Dictionary containing loan information
        
    Raises:
        LoanServiceError: If loan is not found or other errors occur
    """
    try:
        # If no identifier provided or it's a contextual reference, use current context
        if not identifier or identifier.lower() in ["this", "current", "the loan", "this loan"]:
            if current_loan_number:
                identifier = current_loan_number
            elif not identifier:
                raise LoanServiceError("No loan identifier provided and no current loan in context. Please specify a loan number or borrower name.")
        
        loan_record = await loan_data_access.find_loan_by_identifier(identifier)
        
        if not loan_record:
            raise LoanServiceError(f"Loan not found: {identifier}")
        
        result_data = {
            "loan_number": loan_record.loan_number,
            "borrower_name": loan_record.borrower_name,
            "principal_balance": float(loan_record.principal_balance),
            "annual_interest_rate": float(loan_record.annual_interest_rate),
            "last_payment_date": loan_record.last_payment_date.isoformat()
        }
        
        # Add email address if available
        if loan_record.email_address:
            result_data["email_address"] = loan_record.email_address
        
        return result_data
        
    except DataAccessError as e:
        raise LoanServiceError(str(e)) from e
    except Exception as e:
        raise LoanServiceError(f"Unexpected error finding loan: {str(e)}") from e