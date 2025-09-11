"""
Session management service for handling chat sessions and context retention.
"""
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import asyncio

from ..models.session import (
    ChatSession, SessionStatus, ContextData, SessionSummary,
    SessionCreateRequest, SessionUpdateRequest
)

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages chat sessions with context retention and automatic cleanup.
    """
    
    def __init__(self, cleanup_interval_minutes: int = 30):
        self.sessions: Dict[str, ChatSession] = {}
        self.cleanup_interval = cleanup_interval_minutes
        self._cleanup_task = None
        self._cleanup_started = False
    
    def _start_cleanup_task(self):
        """Start the automatic cleanup task."""
        if self._cleanup_task is None and not self._cleanup_started:
            try:
                self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
                self._cleanup_started = True
            except RuntimeError:
                # No event loop running, will start later
                pass
    
    async def _periodic_cleanup(self):
        """Periodically clean up expired sessions."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval * 60)
                await self.cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in session cleanup: {e}")
    
    async def create_session(self, request: SessionCreateRequest = None) -> ChatSession:
        """
        Create a new chat session.
        
        Args:
            request: Session creation parameters
            
        Returns:
            New chat session
        """
        if request is None:
            request = SessionCreateRequest()
        
        session_id = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(hours=request.expiry_hours)
        
        session = ChatSession(
            session_id=session_id,
            expires_at=expires_at,
            user_agent=request.user_agent,
            ip_address=request.ip_address
        )
        
        # Set debug mode if requested
        session.context.debug_mode = request.debug_mode
        
        self.sessions[session_id] = session
        
        logger.info(f"Created new session: {session_id}, expires: {expires_at}")
        return session
    
    async def create_session_with_id(self, session_id: Optional[str] = None, request: SessionCreateRequest = None) -> ChatSession:
        """
        Create a new chat session with an optional explicit session ID.
        
        Args:
            session_id: Optional explicit session ID to use
            request: Session creation parameters
            
        Returns:
            New chat session
        """
        if request is None:
            request = SessionCreateRequest()
        
        # Use provided session_id or generate a new UUID
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        expires_at = datetime.now() + timedelta(hours=request.expiry_hours)
        
        session = ChatSession(
            session_id=session_id,
            expires_at=expires_at,
            user_agent=request.user_agent,
            ip_address=request.ip_address
        )
        
        # Set debug mode if requested
        session.context.debug_mode = request.debug_mode
        
        self.sessions[session_id] = session
        
        logger.info(f"Created new session: {session_id}, expires: {expires_at}")
        return session
    
    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        """
        Get a session by ID.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Chat session or None if not found/expired
        """
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        
        # Check if expired
        if session.is_expired():
            session.status = SessionStatus.EXPIRED
            logger.info(f"Session expired: {session_id}")
            return None
        
        # Update activity
        session.update_activity()
        return session
    
    async def update_session(
        self, 
        session_id: str, 
        request: SessionUpdateRequest
    ) -> Optional[ChatSession]:
        """
        Update session settings.
        
        Args:
            session_id: Session identifier
            request: Update parameters
            
        Returns:
            Updated session or None if not found
        """
        session = await self.get_session(session_id)
        if session is None:
            return None
        
        # Update debug mode
        if request.debug_mode is not None:
            session.context.debug_mode = request.debug_mode
            logger.info(f"Session {session_id} debug mode: {request.debug_mode}")
        
        # Extend expiry
        if request.extend_expiry_hours is not None:
            session.extend_expiry(request.extend_expiry_hours)
            logger.info(f"Extended session {session_id} expiry by {request.extend_expiry_hours}h")
        
        # Clear context
        if request.clear_context:
            session.clear_context()
            logger.info(f"Cleared context for session {session_id}")
        
        return session
    
    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session was deleted, False if not found
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Deleted session: {session_id}")
            return True
        return False
    
    async def get_or_create_session(self, session_id: Optional[str] = None) -> ChatSession:
        """
        Get existing session or create new one.
        
        Args:
            session_id: Optional session ID
            
        Returns:
            Chat session (existing or new)
        """
        # Start cleanup task if not already started
        if not self._cleanup_started:
            self._start_cleanup_task()
        
        if session_id:
            session = await self.get_session(session_id)
            if session:
                return session
        
        # Create new session with provided session_id
        return await self.create_session_with_id(session_id)
    
    async def update_context_from_message(
        self, 
        session_id: str, 
        user_message: str, 
        assistant_message: str
    ) -> Optional[ChatSession]:
        """
        Update session context based on conversation.
        
        Args:
            session_id: Session identifier
            user_message: User's message
            assistant_message: Assistant's response
            
        Returns:
            Updated session or None if not found
        """
        session = await self.get_session(session_id)
        if session is None:
            return None
        
        # Check if we should clear context
        if session.should_clear_context(user_message):
            session.clear_context()
            logger.info(f"Cleared context for session {session_id} based on message")
        
        # Update message history
        session.message_count += 1
        session.last_user_message = user_message
        session.last_assistant_message = assistant_message
        
        return session
    
    async def update_context_from_tool_result(
        self, 
        session_id: str, 
        tool_name: str, 
        tool_result: Dict
    ) -> Optional[ChatSession]:
        """
        Update session context from tool execution result.
        
        Args:
            session_id: Session identifier
            tool_name: Name of executed tool
            tool_result: Tool execution result
            
        Returns:
            Updated session or None if not found
        """
        session = await self.get_session(session_id)
        if session is None:
            return None
        
        if not tool_result.get('success'):
            return session
        
        # Update context based on tool type
        if tool_name == "get_loan_info":
            # ToolResult structure has 'result' field, not 'data'
            loan_data = tool_result.get('result', tool_result.get('data', {}))
            session.context.update_from_loan_info(loan_data)
            logger.info(f"Updated loan context for session {session_id}: {loan_data.get('loan_number')}")
        
        elif tool_name == "calculate_payoff":
            # ToolResult structure has 'result' field, not 'data'
            payoff_data = tool_result.get('result', tool_result.get('data', {}))
            session.context.update_from_payoff_calc(payoff_data)
            logger.info(f"Updated payoff context for session {session_id}")
        
        elif tool_name == "generate_pdf":
            # ToolResult structure has 'result' field, not 'data'
            pdf_data = tool_result.get('result', tool_result.get('data', {}))
            session.context.update_from_pdf_generation(pdf_data)
            logger.info(f"Updated PDF context for session {session_id}: {pdf_data.get('filename')}")
        
        return session
    
    async def start_chain_execution(
        self, 
        session_id: str, 
        chain_id: str
    ) -> Optional[ChatSession]:
        """
        Mark start of chain execution in session.
        
        Args:
            session_id: Session identifier
            chain_id: Chain identifier
            
        Returns:
            Updated session or None if not found
        """
        session = await self.get_session(session_id)
        if session is None:
            return None
        
        session.context.active_chain_id = chain_id
        if chain_id not in session.active_chains:
            session.active_chains.append(chain_id)
        
        logger.info(f"Started chain {chain_id} for session {session_id}")
        return session
    
    async def complete_chain_execution(
        self, 
        session_id: str, 
        chain_id: str, 
        result: Dict
    ) -> Optional[ChatSession]:
        """
        Mark completion of chain execution in session.
        
        Args:
            session_id: Session identifier
            chain_id: Chain identifier
            result: Chain execution result
            
        Returns:
            Updated session or None if not found
        """
        session = await self.get_session(session_id)
        if session is None:
            return None
        
        # Move from active to completed
        if chain_id in session.active_chains:
            session.active_chains.remove(chain_id)
        
        if chain_id not in session.completed_chains:
            session.completed_chains.append(chain_id)
        
        # Clear active chain if this was it
        if session.context.active_chain_id == chain_id:
            session.context.active_chain_id = None
        
        # Store result
        session.context.last_chain_result = result
        
        logger.info(f"Completed chain {chain_id} for session {session_id}")
        return session
    
    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            if session.is_expired():
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
        
        return len(expired_sessions)
    
    async def get_session_summary(self, session_id: str) -> Optional[SessionSummary]:
        """
        Get session summary information.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session summary or None if not found
        """
        session = await self.get_session(session_id)
        if session is None:
            return None
        
        return SessionSummary(
            session_id=session.session_id,
            status=session.status,
            created_at=session.created_at,
            last_activity=session.last_activity,
            expires_at=session.expires_at,
            message_count=session.message_count,
            has_loan_context=session.context.has_loan_context(),
            current_loan_number=session.context.current_loan_number,
            current_borrower_name=session.context.current_borrower_name,
            active_chains_count=len(session.active_chains),
            debug_mode=session.context.debug_mode
        )
    
    async def list_sessions(self) -> List[SessionSummary]:
        """
        List all active sessions.
        
        Returns:
            List of session summaries
        """
        summaries = []
        
        for session_id in list(self.sessions.keys()):
            summary = await self.get_session_summary(session_id)
            if summary:
                summaries.append(summary)
        
        return summaries
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get session manager statistics.
        
        Returns:
            Statistics dictionary
        """
        total_sessions = len(self.sessions)
        active_sessions = len([s for s in self.sessions.values() 
                              if s.status == SessionStatus.ACTIVE and not s.is_expired()])
        expired_sessions = len([s for s in self.sessions.values() if s.is_expired()])
        
        return {
            'total_sessions': total_sessions,
            'active_sessions': active_sessions,
            'expired_sessions': expired_sessions
        }


# Global session manager instance
session_manager = SessionManager()