"""
Calculation service functions for MiLA system.
Pure, stateless functions for payoff calculations.
"""
from typing import Optional, Dict, Any
from datetime import date

from ..components.data_access import loan_data_access, DataAccessError
from ..components.calculator import payoff_calculator, CalculationError


class CalculationServiceError(Exception):
    """Custom exception for calculation service operations."""
    pass


async def calculate_payoff(
    loan_number: str, 
    as_of_date: Optional[date] = None,
    current_loan_number: Optional[str] = None
) -> Dict[str, Any]:
    """
    Calculate payoff amount for a loan.
    
    Args:
        loan_number: The loan number to calculate payoff for
        as_of_date: Optional calculation date. Defaults to today.
        current_loan_number: Optional current loan number from context
        
    Returns:
        Dictionary containing payoff calculation results
        
    Raises:
        CalculationServiceError: If loan is not found or calculation fails
    """
    try:
        # If no loan number provided or it's a contextual reference, use current context
        if not loan_number or loan_number.lower() in ["this", "current", "the loan", "this loan"]:
            if current_loan_number:
                loan_number = current_loan_number
            elif not loan_number:
                raise CalculationServiceError("No loan number provided and no current loan in context")
        
        # Get loan record
        loan_record = await loan_data_access.find_loan_by_number(loan_number)
        if not loan_record:
            raise CalculationServiceError(f"Loan not found: {loan_number}")
        
        # Calculate payoff
        payoff_calculation = payoff_calculator.calculate_payoff(loan_record, as_of_date)
        
        return {
            "loan_number": loan_number,
            "principal_balance": float(payoff_calculation.principal_balance),
            "interest_accrued": float(payoff_calculation.interest_accrued),
            "total_payoff": float(payoff_calculation.total_payoff),
            "calculation_date": payoff_calculation.calculation_date.isoformat(),
            "good_through_date": payoff_calculation.good_through_date.isoformat(),
            "days_since_payment": payoff_calculation.days_since_payment
        }
        
    except (CalculationError, DataAccessError) as e:
        raise CalculationServiceError(str(e)) from e
    except Exception as e:
        raise CalculationServiceError(f"Unexpected error calculating payoff: {str(e)}") from e