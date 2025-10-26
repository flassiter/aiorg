"""
Biweekly payment calculation service functions for MiLA system.
Pure, stateless functions for biweekly payoff calculations.
"""
from typing import Optional, Dict, Any
from datetime import date

from ..components.data_access import loan_data_access, DataAccessError
from ..components.calculator import payoff_calculator, CalculationError


class BiweeklyServiceError(Exception):
    """Custom exception for biweekly service operations."""
    pass


async def calculate_biweekly_payoff(
    loan_identifier: Optional[str] = None,
    loan_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Calculate biweekly payment schedule and savings for a loan.
    
    Args:
        loan_identifier: The loan identifier (number or name) to calculate for
        loan_data: Optional loan data dict if already available
        
    Returns:
        Dictionary containing biweekly calculation results
        
    Raises:
        BiweeklyServiceError: If loan is not found or calculation fails
    """
    try:
        # Get loan record
        if loan_data:
            # Use provided loan data - assume it's already in the correct format
            loan_record = loan_data
        elif loan_identifier:
            loan_record = await loan_data_access.find_loan_by_identifier(loan_identifier)
            if not loan_record:
                raise BiweeklyServiceError(f"Loan not found: {loan_identifier}")
        else:
            raise BiweeklyServiceError("Either loan_identifier or loan_data must be provided")
        
        # Get current loan balance
        current_balance = getattr(loan_record, 'current_balance', None)
        if current_balance is None:
            raise BiweeklyServiceError("Loan record missing current balance")
        
        monthly_payment = getattr(loan_record, 'monthly_payment', None)
        if monthly_payment is None:
            raise BiweeklyServiceError("Loan record missing monthly payment")
        
        interest_rate = getattr(loan_record, 'interest_rate', None) 
        if interest_rate is None:
            raise BiweeklyServiceError("Loan record missing interest rate")
        
        # Calculate biweekly payment (half of monthly payment)
        biweekly_payment = monthly_payment / 2
        
        # Calculate payoff comparison
        monthly_years = _calculate_payoff_time(current_balance, monthly_payment, interest_rate, 12)
        biweekly_years = _calculate_payoff_time(current_balance, biweekly_payment, interest_rate, 26)
        
        # Calculate total interest savings
        total_monthly_payments = monthly_years * 12 * monthly_payment
        total_biweekly_payments = biweekly_years * 26 * biweekly_payment
        interest_savings = total_monthly_payments - total_biweekly_payments
        
        return {
            "loan_number": getattr(loan_record, 'loan_number', 'N/A'),
            "current_balance": float(current_balance),
            "monthly_payment": float(monthly_payment),
            "biweekly_payment": float(biweekly_payment),
            "monthly_payoff_time_years": round(monthly_years, 2),
            "biweekly_payoff_time_years": round(biweekly_years, 2),
            "time_savings_years": round(monthly_years - biweekly_years, 2),
            "interest_savings": round(interest_savings, 2),
            "calculation_date": date.today().isoformat()
        }
        
    except (DataAccessError, AttributeError) as e:
        raise BiweeklyServiceError(str(e)) from e
    except Exception as e:
        raise BiweeklyServiceError(f"Unexpected error calculating biweekly payoff: {str(e)}") from e


def _calculate_payoff_time(balance: float, payment: float, annual_rate: float, payments_per_year: int) -> float:
    """
    Calculate the time in years to pay off a loan.
    
    Args:
        balance: Current loan balance
        payment: Payment amount per period
        annual_rate: Annual interest rate (as decimal, e.g., 0.05 for 5%)
        payments_per_year: Number of payments per year
        
    Returns:
        Number of years to pay off the loan
    """
    import math
    
    # Convert annual rate to period rate
    period_rate = annual_rate / payments_per_year
    
    # Handle edge case where payment is too small
    if payment <= balance * period_rate:
        # Payment doesn't cover interest, loan will never be paid off
        return float('inf')
    
    # Calculate number of payments using loan amortization formula
    numerator = math.log(1 + (balance * period_rate) / payment)
    denominator = math.log(1 + period_rate)
    
    num_payments = numerator / denominator
    
    # Convert to years
    return num_payments / payments_per_year