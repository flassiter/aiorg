"""
Pydantic models for session management and context retention.
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from enum import Enum

from .loan import LoanRecord
from .payoff import PayoffCalculation
from .tool_chain import ToolChainPlan, ChainExecutionResult


class SessionStatus(str, Enum):
    """Session status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"


class ContextData(BaseModel):
    """
    Context data stored in a session.
    """
    # Current loan context
    current_loan_number: Optional[str] = None
    current_borrower_name: Optional[str] = None
    current_loan_data: Optional[Dict[str, Any]] = None
    current_payoff_data: Optional[Dict[str, Any]] = None
    
    # Generated files
    generated_pdf_filename: Optional[str] = None
    generated_pdf_url: Optional[str] = None
    
    # Email context
    borrower_email: Optional[str] = None
    pending_email_confirmation: bool = False
    pending_email_address: Optional[str] = None
    pending_email_loan_number: Optional[str] = None
    
    # Chain execution context
    active_chain_id: Optional[str] = None
    last_chain_result: Optional[Dict[str, Any]] = None
    
    # Debug mode
    debug_mode: bool = False
    
    # Additional context for tools
    tool_context: Dict[str, Any] = Field(default_factory=dict)
    
    def clear_loan_context(self):
        """Clear all loan-related context data."""
        self.current_loan_number = None
        self.current_borrower_name = None
        self.current_loan_data = None
        self.current_payoff_data = None
        self.generated_pdf_filename = None
        self.generated_pdf_url = None
        self.borrower_email = None
        self.pending_email_confirmation = False
        self.pending_email_address = None
        self.pending_email_loan_number = None
    
    def has_loan_context(self) -> bool:
        """Check if session has active loan context."""
        return self.current_loan_number is not None
    
    def update_from_loan_info(self, loan_data: Dict[str, Any]):
        """Update context from loan information."""
        self.current_loan_number = loan_data.get('loan_number')
        self.current_borrower_name = loan_data.get('borrower_name')
        self.current_loan_data = loan_data
        # Extract email if available
        self.borrower_email = loan_data.get('email_address')
    
    def update_from_payoff_calc(self, payoff_data: Dict[str, Any]):
        """Update context from payoff calculation."""
        self.current_payoff_data = payoff_data
    
    def update_from_pdf_generation(self, pdf_data: Dict[str, Any]):
        """Update context from PDF generation."""
        self.generated_pdf_filename = pdf_data.get('filename')
        self.generated_pdf_url = pdf_data.get('download_url')


class ChatSession(BaseModel):
    """
    Chat session with context and history.
    """
    session_id: str = Field(..., description="Unique session identifier")
    status: SessionStatus = Field(default=SessionStatus.ACTIVE, description="Session status")
    created_at: datetime = Field(default_factory=datetime.now, description="Session creation time")
    last_activity: datetime = Field(default_factory=datetime.now, description="Last activity timestamp")
    expires_at: datetime = Field(..., description="Session expiration time")
    
    # Session context
    context: ContextData = Field(default_factory=ContextData, description="Session context data")
    
    # Conversation history
    message_count: int = Field(default=0, description="Number of messages in session")
    last_user_message: Optional[str] = Field(default=None, description="Last user message")
    last_assistant_message: Optional[str] = Field(default=None, description="Last assistant message")
    
    # Chain execution tracking
    active_chains: List[str] = Field(default_factory=list, description="Active chain IDs")
    completed_chains: List[str] = Field(default_factory=list, description="Completed chain IDs")
    
    # Session metadata
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    
    # Track if session context message has been shown
    context_message_shown: bool = Field(default=False, description="Whether session context message has been shown")
    
    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.now() > self.expires_at
    
    def is_active(self) -> bool:
        """Check if session is active and not expired."""
        return self.status == SessionStatus.ACTIVE and not self.is_expired()
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now()
        if self.is_expired():
            self.status = SessionStatus.EXPIRED
    
    def extend_expiry(self, hours: int = 2):
        """Extend session expiry time."""
        self.expires_at = datetime.now() + timedelta(hours=hours)
        if self.status == SessionStatus.EXPIRED:
            self.status = SessionStatus.ACTIVE
    
    def clear_context(self):
        """Clear session context (but keep session alive)."""
        self.context.clear_loan_context()
        self.active_chains.clear()
        self.context.active_chain_id = None
        self.context_message_shown = False
    
    def should_clear_context(self, message: str) -> bool:
        """Determine if context should be cleared based on message."""
        # For PoC simplicity, only clear context on explicit session clear
        # No automatic clearing based on message content
        return False


class SessionSummary(BaseModel):
    """
    Summary information about a session.
    """
    session_id: str
    status: SessionStatus
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    message_count: int
    has_loan_context: bool
    current_loan_number: Optional[str]
    current_borrower_name: Optional[str]
    active_chains_count: int
    debug_mode: bool


class SessionCreateRequest(BaseModel):
    """
    Request to create a new session.
    """
    expiry_hours: int = Field(default=2, description="Session expiry in hours")
    debug_mode: bool = Field(default=False, description="Enable debug mode")
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None


class SessionUpdateRequest(BaseModel):
    """
    Request to update session settings.
    """
    debug_mode: Optional[bool] = None
    extend_expiry_hours: Optional[int] = None
    clear_context: bool = False