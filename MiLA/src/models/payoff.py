"""
Pydantic models for loan payoff calculations.
"""
from datetime import date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, validator


class PayoffCalculation(BaseModel):
    """
    Loan payoff calculation model representing a single payoff calculation.
    """
    loan_number: str = Field(..., min_length=6, max_length=8, description="Loan number (6-8 digits)")
    principal_balance: Decimal = Field(..., ge=0, decimal_places=2, description="Principal balance in dollars")
    interest_accrued: Decimal = Field(..., ge=0, decimal_places=2, description="Interest accrued since last payment")
    total_payoff: Decimal = Field(..., ge=0, decimal_places=2, description="Total payoff amount")
    calculation_date: date = Field(..., description="Date of calculation")
    days_since_payment: int = Field(..., ge=0, description="Days since last payment")

    @validator('loan_number')
    def validate_loan_number(cls, v):
        """Validate loan number contains only digits"""
        if not v.isdigit():
            raise ValueError('Loan number must contain only digits')
        return v

    @validator('total_payoff')
    def validate_total_payoff(cls, v, values):
        """Validate that total payoff equals principal plus interest"""
        if 'principal_balance' in values and 'interest_accrued' in values:
            expected_total = values['principal_balance'] + values['interest_accrued']
            # Allow for small rounding differences (within 1 cent)
            if abs(v - expected_total) > Decimal('0.01'):
                raise ValueError('Total payoff must equal principal balance plus interest accrued')
        return v

    class Config:
        """Pydantic configuration"""
        validate_assignment = True
        json_encoders = {
            Decimal: lambda v: float(v),
            date: lambda v: v.isoformat()
        }


class PayoffCalculationRequest(BaseModel):
    """
    Request model for payoff calculation.
    """
    loan_number: str = Field(..., min_length=6, max_length=8, description="Loan number to calculate payoff for")
    as_of_date: Optional[date] = Field(None, description="Date to calculate payoff as of (defaults to today)")

    @validator('loan_number')
    def validate_loan_number(cls, v):
        """Validate loan number contains only digits"""
        if not v.isdigit():
            raise ValueError('Loan number must contain only digits')
        return v


class PayoffCalculationResponse(BaseModel):
    """
    Response model for payoff calculation.
    """
    success: bool
    message: str
    data: Optional[PayoffCalculation] = None

    class Config:
        """Pydantic configuration"""
        json_encoders = {
            Decimal: lambda v: float(v),
            date: lambda v: v.isoformat()
        }