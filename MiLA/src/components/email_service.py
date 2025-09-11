"""
Email simulation service for demo purposes.
"""
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

from ..models.session import ContextData

logger = logging.getLogger(__name__)


class EmailSimulationError(Exception):
    """Custom exception for email simulation errors."""
    pass


class EmailMessage:
    """Simulated email message."""
    
    def __init__(
        self, 
        to_address: str, 
        subject: str, 
        body: str, 
        attachment_path: Optional[str] = None
    ):
        self.message_id = str(uuid.uuid4())
        self.to_address = to_address
        self.subject = subject
        self.body = body
        self.attachment_path = attachment_path
        self.sent_at = datetime.now()
        self.status = "sent"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'message_id': self.message_id,
            'to_address': self.to_address,
            'subject': self.subject,
            'body': self.body,
            'attachment_path': self.attachment_path,
            'sent_at': self.sent_at.isoformat(),
            'status': self.status
        }


class EmailService:
    """
    Email simulation service for demo purposes.
    This service simulates sending emails without actually sending them.
    """
    
    def __init__(self):
        self.sent_emails: List[EmailMessage] = []
        self.email_log_path = Path("output/email_log.txt")
        self.email_log_path.parent.mkdir(exist_ok=True)
    
    async def send_payoff_statement(
        self, 
        recipient_email: str, 
        loan_number: str,
        borrower_name: str,
        payoff_amount: float,
        pdf_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Simulate sending a payoff statement email.
        
        Args:
            recipient_email: Email address to send to
            loan_number: Loan number
            borrower_name: Borrower's name
            payoff_amount: Total payoff amount
            pdf_filename: Optional PDF attachment filename
            
        Returns:
            Email send result
        """
        try:
            # Create email content
            subject = f"Loan Payoff Statement - Loan #{loan_number}"
            
            body = self._create_payoff_email_body(
                borrower_name, 
                loan_number, 
                payoff_amount,
                pdf_filename
            )
            
            # Create email message
            email = EmailMessage(
                to_address=recipient_email,
                subject=subject,
                body=body,
                attachment_path=pdf_filename
            )
            
            # "Send" the email (simulate)
            self.sent_emails.append(email)
            
            # Log the email
            await self._log_email(email)
            
            logger.info(f"Simulated email sent to {recipient_email} for loan {loan_number}")
            
            return {
                'success': True,
                'message_id': email.message_id,
                'to_address': recipient_email,
                'subject': subject,
                'sent_at': email.sent_at.isoformat(),
                'has_attachment': pdf_filename is not None,
                'attachment_filename': pdf_filename
            }
            
        except Exception as e:
            logger.error(f"Failed to simulate email send: {str(e)}")
            raise EmailSimulationError(f"Email simulation failed: {str(e)}")
    
    async def send_custom_email(
        self, 
        recipient_email: str, 
        subject: str, 
        body: str,
        attachment_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Simulate sending a custom email.
        
        Args:
            recipient_email: Email address to send to
            subject: Email subject
            body: Email body
            attachment_path: Optional attachment file path
            
        Returns:
            Email send result
        """
        try:
            # Create email message
            email = EmailMessage(
                to_address=recipient_email,
                subject=subject,
                body=body,
                attachment_path=attachment_path
            )
            
            # "Send" the email (simulate)
            self.sent_emails.append(email)
            
            # Log the email
            await self._log_email(email)
            
            logger.info(f"Simulated custom email sent to {recipient_email}")
            
            return {
                'success': True,
                'message_id': email.message_id,
                'to_address': recipient_email,
                'subject': subject,
                'sent_at': email.sent_at.isoformat(),
                'has_attachment': attachment_path is not None
            }
            
        except Exception as e:
            logger.error(f"Failed to simulate custom email send: {str(e)}")
            raise EmailSimulationError(f"Custom email simulation failed: {str(e)}")
    
    def _create_payoff_email_body(
        self, 
        borrower_name: str, 
        loan_number: str, 
        payoff_amount: float,
        pdf_filename: Optional[str] = None
    ) -> str:
        """Create email body for payoff statement."""
        
        attachment_text = ""
        if pdf_filename:
            attachment_text = f"\n\nPlease find your detailed payoff statement attached as {pdf_filename}."
        
        body = f"""Dear {borrower_name},

We have prepared your loan payoff statement for loan #{loan_number}.

PAYOFF AMOUNT: ${payoff_amount:,.2f}

This payoff amount is valid for a limited time. Please refer to the attached statement for the exact good-through date and detailed breakdown.{attachment_text}

To proceed with payoff:
1. Review the attached payoff statement carefully
2. Remit payment for the exact amount shown
3. Include your loan number #{loan_number} as reference

If you have any questions about this payoff statement, please contact us immediately.

Thank you for your business.

Best regards,
MiLA Loan Services
Customer Service Department

---
This is a simulated email for demonstration purposes.
In a real system, this would be sent to the borrower's registered email address.
"""
        return body
    
    async def _log_email(self, email: EmailMessage):
        """Log email to file for demo purposes."""
        try:
            log_entry = f"""
=== EMAIL SENT ===
Date: {email.sent_at}
Message ID: {email.message_id}
To: {email.to_address}
Subject: {email.subject}
Attachment: {email.attachment_path or 'None'}

Body:
{email.body}

==================

"""
            with open(self.email_log_path, 'a', encoding='utf-8') as f:
                f.write(log_entry)
                
        except Exception as e:
            logger.warning(f"Failed to log email: {e}")
    
    def get_sent_emails(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get list of sent emails.
        
        Args:
            limit: Maximum number of emails to return
            
        Returns:
            List of email dictionaries
        """
        return [email.to_dict() for email in self.sent_emails[-limit:]]
    
    def get_email_by_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Get email by message ID.
        
        Args:
            message_id: Email message ID
            
        Returns:
            Email dictionary or None if not found
        """
        for email in self.sent_emails:
            if email.message_id == message_id:
                return email.to_dict()
        return None
    
    def clear_email_log(self):
        """Clear all sent emails (for testing)."""
        self.sent_emails.clear()
        if self.email_log_path.exists():
            self.email_log_path.unlink()
        logger.info("Cleared email log")
    
    async def get_borrower_email(self, loan_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract borrower email from loan data.
        
        Args:
            loan_data: Loan information
            
        Returns:
            Email address or None if not available
        """
        # Try different possible email field names
        email_fields = ['email_address', 'email', 'borrower_email', 'contact_email']
        
        for field in email_fields:
            if field in loan_data and loan_data[field]:
                return loan_data[field]
        
        # If no email in loan data, generate a demo email
        borrower_name = loan_data.get('borrower_name', 'borrower')
        if borrower_name:
            # Convert "John Doe" to "john.doe@email.com"
            email_name = borrower_name.lower().replace(' ', '.')
            demo_email = f"{email_name}@email.com"
            logger.info(f"Generated demo email: {demo_email}")
            return demo_email
        
        return None
    
    async def confirm_email_send(
        self, 
        email_address: str, 
        context: ContextData
    ) -> str:
        """
        Create confirmation message for email sending.
        
        Args:
            email_address: Email address to send to
            context: Session context
            
        Returns:
            Confirmation message
        """
        if context.current_loan_number and context.current_borrower_name:
            return f"Send payoff statement for loan {context.current_loan_number} to {email_address}? (Y/N)"
        else:
            return f"Send email to {email_address}? (Y/N)"
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get email service statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            'total_emails_sent': len(self.sent_emails),
            'last_email_sent': self.sent_emails[-1].sent_at.isoformat() if self.sent_emails else None,
            'log_file_exists': self.email_log_path.exists(),
            'log_file_size': self.email_log_path.stat().st_size if self.email_log_path.exists() else 0
        }


# Global email service instance
email_service = EmailService()