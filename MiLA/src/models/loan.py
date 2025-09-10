"""
Pydantic models for loan data structures.
"""
from datetime import date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, validator


class LoanRecord(BaseModel):
    """
    Loan record model representing a single loan entry.
    """
    loan_number: str = Field(..., min_length=6, max_length=8, description="Loan number (6-8 digits)")
    borrower_name: str = Field(..., min_length=1, description="Borrower full name")
    principal_balance: Decimal = Field(..., ge=0, decimal_places=2, description="Principal balance in dollars")
    annual_interest_rate: Decimal = Field(..., ge=0, le=100, decimal_places=2, description="Annual interest rate as percentage")
    last_payment_date: date = Field(..., description="Date of last payment")

    @validator('loan_number')
    def validate_loan_number(cls, v):
        """Validate loan number contains only digits"""
        if not v.isdigit():
            raise ValueError('Loan number must contain only digits')
        return v

    @validator('borrower_name')
    def validate_borrower_name(cls, v):
        """Validate borrower name format"""
        v = v.strip()
        if not v:
            raise ValueError('Borrower name cannot be empty')
        return v

    class Config:
        """Pydantic configuration"""
        validate_assignment = True
        json_encoders = {
            Decimal: lambda v: float(v),
            date: lambda v: v.isoformat()
        }


class PayoffResult(BaseModel):
    """
    Result of payoff calculation.
    """
    loan_record: LoanRecord
    calculation_date: date
    days_since_last_payment: int
    accrued_interest: Decimal = Field(..., decimal_places=2)
    total_payoff_amount: Decimal = Field(..., decimal_places=2)

    class Config:
        """Pydantic configuration"""
        json_encoders = {
            Decimal: lambda v: float(v),
            date: lambda v: v.isoformat()
        }


class LoanSearchRequest(BaseModel):
    """
    Request model for loan search operations.
    """
    identifier: str = Field(..., min_length=1, description="Loan number or borrower name")


class LoanResponse(BaseModel):
    """
    Response model for loan API endpoints.
    """
    success: bool
    message: str
    data: Optional[LoanRecord] = None


class PayoffCalculationRequest(BaseModel):
    """
    Request model for payoff calculation.
    """
    loan_number: str = Field(..., min_length=6, max_length=8)
    as_of_date: Optional[date] = None


class PayoffCalculationResponse(BaseModel):
    """
    Response model for payoff calculation.
    """
    success: bool
    message: str
    data: Optional[PayoffResult] = None


class HealthCheckResponse(BaseModel):
    """
    Response model for health check endpoint.
    """
    status: str
    timestamp: date
    version: str = "1.0.0"


# Authentication models removed for PoC simplicity