"""
PDF service functions for MiLA system.
Pure, stateless functions for PDF generation.
"""
from typing import Optional, Dict, Any
from datetime import date
from pathlib import Path

from ..components.data_access import loan_data_access, DataAccessError
from ..components.calculator import payoff_calculator, CalculationError
from ..components.pdf_generator import pdf_generator, PDFGenerationError


class PDFServiceError(Exception):
    """Custom exception for PDF service operations."""
    pass


async def generate_pdf(
    loan_number: str,
    statement_date: Optional[date] = None,
    current_loan_number: Optional[str] = None,
    server_base_url: str = "http://localhost:8000"
) -> Dict[str, Any]:
    """
    Generate a payoff statement PDF for a loan.
    
    Args:
        loan_number: The loan number to generate PDF for
        statement_date: Optional statement date. Defaults to today.
        current_loan_number: Optional current loan number from context
        server_base_url: Base URL for download links
        
    Returns:
        Dictionary containing PDF generation results
        
    Raises:
        PDFServiceError: If loan is not found or PDF generation fails
    """
    try:
        # If no loan number provided or it's a contextual reference, use current context
        if not loan_number or loan_number.lower() in ["this", "current", "the loan", "this loan"]:
            if current_loan_number:
                loan_number = current_loan_number
            else:
                raise PDFServiceError("No loan number provided and no current loan in context. Please specify a loan number or calculate payoff first.")
        
        # Get loan record
        loan_record = await loan_data_access.find_loan_by_number(loan_number)
        if not loan_record:
            raise PDFServiceError(f"Loan not found: {loan_number}")
        
        # Calculate payoff for PDF
        payoff_calculation = payoff_calculator.calculate_payoff(loan_record, statement_date)
        
        # Generate PDF
        pdf_path = pdf_generator.generate_payoff_statement(
            loan_record, 
            payoff_calculation, 
            statement_date
        )
        
        # Extract filename and create download URL
        filename = Path(pdf_path).name
        download_url = f"/api/files/{filename}"
        
        return {
            "loan_number": loan_number,
            "filename": filename,
            "download_url": download_url,
            "file_path": pdf_path
        }
        
    except (CalculationError, PDFGenerationError, DataAccessError) as e:
        raise PDFServiceError(str(e)) from e
    except Exception as e:
        raise PDFServiceError(f"Unexpected error generating PDF: {str(e)}") from e