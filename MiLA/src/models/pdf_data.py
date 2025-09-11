"""
Pydantic models for PDF generation data structures.
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, validator


class PayoffData(BaseModel):
    """
    Data model for payoff statement PDF generation.
    Contains all information needed to generate a payoff statement.
    """
    borrower_name: str = Field(..., min_length=1, description="Full name of the borrower")
    loan_number: str = Field(..., min_length=6, max_length=8, description="Loan number (6-8 digits)")
    statement_date: date = Field(..., description="Date when the statement is generated")
    principal_balance: Decimal = Field(..., ge=0, decimal_places=2, description="Principal balance in dollars")
    accrued_interest: Decimal = Field(..., ge=0, decimal_places=2, description="Accrued interest in dollars")
    total_payoff_amount: Decimal = Field(..., ge=0, decimal_places=2, description="Total payoff amount in dollars")
    payoff_good_through_date: date = Field(..., description="Date until which the payoff amount is valid")
    
    @validator('loan_number')
    def validate_loan_number(cls, v):
        """Validate loan number contains only digits"""
        if not v.isdigit():
            raise ValueError('Loan number must contain only digits')
        return v
    
    @validator('borrower_name')
    def validate_borrower_name(cls, v):
        """Validate and clean borrower name"""
        v = v.strip()
        if not v:
            raise ValueError('Borrower name cannot be empty')
        return v
    
    @validator('payoff_good_through_date')
    def validate_payoff_good_through_date(cls, v, values):
        """Validate that payoff good through date is after statement date"""
        if 'statement_date' in values and v <= values['statement_date']:
            raise ValueError('Payoff good through date must be after statement date')
        return v
    
    @validator('total_payoff_amount')
    def validate_total_payoff_amount(cls, v, values):
        """Validate that total payoff equals principal plus accrued interest"""
        if 'principal_balance' in values and 'accrued_interest' in values:
            expected_total = values['principal_balance'] + values['accrued_interest']
            # Allow for small rounding differences (within 1 cent)
            if abs(v - expected_total) > Decimal('0.01'):
                raise ValueError('Total payoff amount must equal principal balance plus accrued interest')
        return v
    
    @classmethod
    def from_loan_and_payoff(cls, loan_record, payoff_result, statement_date: Optional[date] = None):
        """
        Create PayoffData from LoanRecord and PayoffResult.
        
        Args:
            loan_record: LoanRecord object containing loan information
            payoff_result: PayoffCalculation or PayoffResult object containing calculation results
            statement_date: Optional statement date (defaults to today)
            
        Returns:
            PayoffData object ready for PDF generation
        """
        if statement_date is None:
            statement_date = date.today()
        
        # Calculate good through date (10 days from statement date)
        good_through_date = statement_date + timedelta(days=10)
        
        # Handle both PayoffCalculation and PayoffResult structures
        if hasattr(payoff_result, 'interest_accrued'):
            # PayoffCalculation structure
            accrued_interest = payoff_result.interest_accrued
            total_payoff = payoff_result.total_payoff
            principal_balance = payoff_result.principal_balance
        else:
            # PayoffResult structure  
            accrued_interest = payoff_result.accrued_interest
            total_payoff = payoff_result.total_payoff_amount
            principal_balance = loan_record.principal_balance
        
        return cls(
            borrower_name=loan_record.borrower_name,
            loan_number=loan_record.loan_number,
            statement_date=statement_date,
            principal_balance=principal_balance,
            accrued_interest=accrued_interest,
            total_payoff_amount=total_payoff,
            payoff_good_through_date=good_through_date
        )
    
    class Config:
        """Pydantic configuration"""
        validate_assignment = True
        json_encoders = {
            Decimal: lambda v: float(v),
            date: lambda v: v.isoformat()
        }


class PDFGenerationRequest(BaseModel):
    """
    Request model for PDF generation API endpoint.
    """
    loan_number: str = Field(..., min_length=6, max_length=8, description="Loan number to generate PDF for")
    statement_date: Optional[date] = Field(None, description="Statement date (defaults to today)")
    
    @validator('loan_number')
    def validate_loan_number(cls, v):
        """Validate loan number contains only digits"""
        if not v.isdigit():
            raise ValueError('Loan number must contain only digits')
        return v


class PDFGenerationResponse(BaseModel):
    """
    Response model for PDF generation API endpoint.
    """
    success: bool
    message: str
    filename: Optional[str] = None
    download_url: Optional[str] = None
    
    class Config:
        """Pydantic configuration"""
        json_encoders = {
            date: lambda v: v.isoformat()
        }