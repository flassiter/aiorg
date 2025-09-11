"""
Email service functions for MiLA system.
Pure, stateless functions for email operations.
"""
from typing import Optional, Dict, Any

from ..components.email_service import email_service, EmailSimulationError
from ..models.session import ContextData


class EmailServiceError(Exception):
    """Custom exception for email service operations."""
    pass


async def send_payoff_email(
    email_address: Optional[str] = None,
    loan_number: Optional[str] = None,
    current_loan_data: Optional[Dict[str, Any]] = None,
    current_payoff_data: Optional[Dict[str, Any]] = None,
    generated_pdf_filename: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send payoff information via email to borrower.
    
    Args:
        email_address: Email address to send to (optional, will use address on file)
        loan_number: Loan number for context (optional, will use current context)
        current_loan_data: Current loan data from context
        current_payoff_data: Current payoff data from context
        generated_pdf_filename: Generated PDF filename for attachment
        
    Returns:
        Dictionary containing email send results
        
    Raises:
        EmailServiceError: If email sending fails
    """
    try:
        # Use email from context if not provided
        if not email_address:
            email_address = await email_service.get_borrower_email(current_loan_data or {})
            if not email_address:
                raise EmailServiceError("No email address available for borrower")
        
        # Send email
        result = await email_service.send_payoff_statement(
            email_address,
            (current_loan_data or {}).get('loan_number', loan_number),
            (current_loan_data or {}).get('borrower_name', 'Borrower'),
            (current_payoff_data or {}).get('total_payoff', 0),
            generated_pdf_filename
        )
        
        return {'data': result}
        
    except EmailSimulationError as e:
        raise EmailServiceError(str(e)) from e
    except Exception as e:
        raise EmailServiceError(f"Unexpected error sending email: {str(e)}") from e


async def confirm_email_send(email_address: str, context_data: ContextData) -> Dict[str, Any]:
    """
    Confirm email sending with user.
    
    Args:
        email_address: Email address to confirm
        context_data: Current context data
        
    Returns:
        Dictionary containing confirmation results
        
    Raises:
        EmailServiceError: If confirmation fails
    """
    try:
        confirmation_message = await email_service.confirm_email_send(email_address, context_data)
        
        return {
            'data': {
                'confirmation_message': confirmation_message,
                'email_address': email_address,
                'requires_user_response': True
            }
        }
        
    except Exception as e:
        raise EmailServiceError(f"Unexpected error confirming email: {str(e)}") from e