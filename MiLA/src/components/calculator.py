"""
Calculation engine for loan payoff calculations.
"""
import logging
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from ..models.loan import LoanRecord
from ..models.payoff import PayoffCalculation

logger = logging.getLogger(__name__)


class CalculationError(Exception):
    """Custom exception for calculation operations."""
    pass


class PayoffCalculator:
    """
    Calculator for loan payoff amounts and related calculations.
    """
    
    @staticmethod
    def calculate_daily_interest(balance: Decimal, annual_rate: Decimal) -> Decimal:
        """
        Calculate daily interest amount based on principal balance and annual rate.
        
        Args:
            balance: Principal balance
            annual_rate: Annual interest rate as percentage (e.g., 5.50 for 5.5%)
            
        Returns:
            Daily interest amount rounded to 2 decimal places
            
        Raises:
            CalculationError: If inputs are invalid
        """
        try:
            if balance < 0:
                raise CalculationError("Principal balance cannot be negative")
            
            if annual_rate < 0:
                raise CalculationError("Annual interest rate cannot be negative")
                
            # Convert percentage to decimal and calculate daily rate
            daily_rate = (annual_rate / Decimal('100')) / Decimal('365')
            daily_interest = balance * daily_rate
            
            # Round to 2 decimal places using banker's rounding
            daily_interest = daily_interest.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            logger.debug(f"Daily interest calculation: balance={balance}, rate={annual_rate}%, daily_interest={daily_interest}")
            return daily_interest
            
        except (TypeError, ValueError) as e:
            raise CalculationError(f"Invalid input for daily interest calculation: {str(e)}")

    @staticmethod
    def days_between_payments(last_payment: date, current_date: date) -> int:
        """
        Calculate number of days between last payment and current date.
        
        Args:
            last_payment: Date of last payment
            current_date: Current calculation date
            
        Returns:
            Number of days (non-negative integer)
            
        Raises:
            CalculationError: If current date is before last payment date
        """
        try:
            if current_date < last_payment:
                raise CalculationError(f"Calculation date ({current_date}) cannot be before last payment date ({last_payment})")
            
            delta = current_date - last_payment
            days = delta.days
            
            logger.debug(f"Days between payments: last={last_payment}, current={current_date}, days={days}")
            return days
            
        except (TypeError, ValueError) as e:
            raise CalculationError(f"Invalid dates for days calculation: {str(e)}")

    @classmethod
    def calculate_payoff(cls, loan: LoanRecord, as_of_date: Optional[date] = None) -> PayoffCalculation:
        """
        Calculate the total payoff amount for a loan.
        
        Formula: Payoff Amount = Principal Balance + (Principal Balance × Annual Rate × Days Since Last Payment / 365)
        
        Args:
            loan: Loan record to calculate payoff for
            as_of_date: Date to calculate payoff as of (defaults to today)
            
        Returns:
            PayoffCalculation with all calculation details
            
        Raises:
            CalculationError: If calculation cannot be performed
        """
        try:
            calculation_date = as_of_date or date.today()
            
            # Handle edge case: zero balance
            if loan.principal_balance == 0:
                logger.info(f"Zero balance loan {loan.loan_number}, returning zero payoff")
                return PayoffCalculation(
                    loan_number=loan.loan_number,
                    principal_balance=Decimal('0.00'),
                    interest_accrued=Decimal('0.00'),
                    total_payoff=Decimal('0.00'),
                    calculation_date=calculation_date,
                    days_since_payment=cls.days_between_payments(loan.last_payment_date, calculation_date)
                )
            
            # Calculate days since last payment
            days_since_payment = cls.days_between_payments(loan.last_payment_date, calculation_date)
            
            # Handle edge case: same day as payment (no accrued interest)
            if days_since_payment == 0:
                logger.info(f"Same day calculation for loan {loan.loan_number}, no accrued interest")
                return PayoffCalculation(
                    loan_number=loan.loan_number,
                    principal_balance=loan.principal_balance,
                    interest_accrued=Decimal('0.00'),
                    total_payoff=loan.principal_balance,
                    calculation_date=calculation_date,
                    days_since_payment=0
                )
            
            # Calculate daily interest
            daily_interest = cls.calculate_daily_interest(loan.principal_balance, loan.annual_interest_rate)
            
            # Calculate total accrued interest
            interest_accrued = daily_interest * days_since_payment
            
            # Round to 2 decimal places
            interest_accrued = interest_accrued.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            # Calculate total payoff
            total_payoff = loan.principal_balance + interest_accrued
            
            # Round to 2 decimal places
            total_payoff = total_payoff.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            logger.info(f"Payoff calculated for loan {loan.loan_number}: principal={loan.principal_balance}, "
                       f"interest={interest_accrued}, total={total_payoff}, days={days_since_payment}")
            
            return PayoffCalculation(
                loan_number=loan.loan_number,
                principal_balance=loan.principal_balance,
                interest_accrued=interest_accrued,
                total_payoff=total_payoff,
                calculation_date=calculation_date,
                days_since_payment=days_since_payment
            )
            
        except CalculationError:
            raise
        except Exception as e:
            raise CalculationError(f"Unexpected error in payoff calculation: {str(e)}")

    @staticmethod
    def validate_calculation_inputs(loan: LoanRecord, as_of_date: Optional[date] = None) -> None:
        """
        Validate inputs for payoff calculation.
        
        Args:
            loan: Loan record to validate
            as_of_date: Calculation date to validate
            
        Raises:
            CalculationError: If inputs are invalid
        """
        if not loan:
            raise CalculationError("Loan record is required")
        
        if loan.principal_balance < 0:
            raise CalculationError("Principal balance cannot be negative")
            
        if loan.annual_interest_rate < 0:
            raise CalculationError("Annual interest rate cannot be negative")
            
        if as_of_date and as_of_date < loan.last_payment_date:
            raise CalculationError(f"Calculation date ({as_of_date}) cannot be before last payment date ({loan.last_payment_date})")

    @classmethod
    def calculate_interest_for_period(cls, principal: Decimal, annual_rate: Decimal, days: int) -> Decimal:
        """
        Calculate interest for a specific number of days.
        
        Args:
            principal: Principal amount
            annual_rate: Annual interest rate as percentage
            days: Number of days to calculate interest for
            
        Returns:
            Interest amount for the specified period
            
        Raises:
            CalculationError: If inputs are invalid
        """
        if days < 0:
            raise CalculationError("Days cannot be negative")
            
        daily_interest = cls.calculate_daily_interest(principal, annual_rate)
        total_interest = daily_interest * days
        
        return total_interest.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @staticmethod
    def is_leap_year(year: int) -> bool:
        """
        Check if a year is a leap year.
        
        Args:
            year: Year to check
            
        Returns:
            True if leap year, False otherwise
        """
        return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)

    @classmethod
    def calculate_daily_interest_leap_aware(cls, balance: Decimal, annual_rate: Decimal, calculation_year: int) -> Decimal:
        """
        Calculate daily interest with leap year awareness.
        For leap years, uses 366 days instead of 365.
        
        Args:
            balance: Principal balance
            annual_rate: Annual interest rate as percentage
            calculation_year: Year for leap year calculation
            
        Returns:
            Daily interest amount adjusted for leap year
            
        Raises:
            CalculationError: If inputs are invalid
        """
        try:
            if balance < 0:
                raise CalculationError("Principal balance cannot be negative")
            
            if annual_rate < 0:
                raise CalculationError("Annual interest rate cannot be negative")
                
            # Use 366 days for leap years, 365 otherwise
            days_in_year = 366 if cls.is_leap_year(calculation_year) else 365
            
            # Convert percentage to decimal and calculate daily rate
            daily_rate = (annual_rate / Decimal('100')) / Decimal(str(days_in_year))
            daily_interest = balance * daily_rate
            
            # Round to 2 decimal places using banker's rounding
            daily_interest = daily_interest.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            logger.debug(f"Leap-aware daily interest: balance={balance}, rate={annual_rate}%, "
                        f"year={calculation_year}, days_in_year={days_in_year}, daily_interest={daily_interest}")
            return daily_interest
            
        except (TypeError, ValueError) as e:
            raise CalculationError(f"Invalid input for leap-aware daily interest calculation: {str(e)}")


# Global instance for dependency injection
payoff_calculator = PayoffCalculator()