"""
Chat API endpoints for AI-orchestrated loan processing.
"""
import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, status

from ..models.chat import ChatRequest, ChatResponse
from ..components.ai_orchestrator import get_ai_orchestrator, AIOrchestrationError, QwenModelSize
from ..components.session_manager import session_manager

logger = logging.getLogger(__name__)

# Create router for chat endpoints
router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/message", response_model=ChatResponse)
async def send_chat_message(chat_request: ChatRequest) -> ChatResponse:
    """
    Send a message to the AI assistant and receive a response with tool execution.
    
    The AI can understand natural language requests and automatically execute
    the appropriate tools for loan processing tasks:
    - Search for loan information by name or number
    - Calculate payoff amounts
    - Generate payoff statement PDFs
    - Execute multi-step workflows
    
    Args:
        chat_request: ChatRequest containing the user's message
        
    Returns:
        ChatResponse with AI response, tool results, and any generated files
        
    Examples:
        - "Show me loan information for Mark Wilson"
        - "Calculate payoff for loan 69253358"  
        - "Get loan info for 69253358, calculate payoff, and create PDF"
        - "Process payoff for Mark Wilson" (implies all steps)
    """
    logger.info(f"Chat message received: {chat_request.message[:100]}...")
    
    try:
        # Process the user message through AI orchestration
        orchestrator = get_ai_orchestrator()
        response = await orchestrator.process_user_message(
            chat_request.message, 
            chat_request.session_id
        )
        
        # Add session ID to response
        response.session_id = chat_request.session_id
        
        # Add debug info if debug mode is enabled
        if chat_request.debug_mode:
            response.debug_info = {
                "debug_mode": True,
                "session_id": chat_request.session_id,
                "tool_count": len(response.tool_calls),
                "files_count": len(response.files_generated)
            }
        
        # Log successful processing
        logger.info(f"Chat message processed successfully. "
                   f"Tools used: {[tc.tool_name for tc in response.tool_calls]}, "
                   f"Files generated: {len(response.files_generated)}")
        
        return response
        
    except AIOrchestrationError as e:
        logger.error(f"AI orchestration error: {str(e)}")
        return ChatResponse(
            message=f"I'm having trouble processing your request: {str(e)}",
            success=False,
            error_message=str(e)
        )
        
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {str(e)}")
        return ChatResponse(
            message="I encountered an unexpected error. Please try again or contact support.",
            success=False,
            error_message="Internal server error"
        )


@router.delete("/session/{session_id}")
async def clear_session(session_id: str) -> Dict[str, str]:
    """
    Clear a specific session, removing all cached loan data.
    
    Args:
        session_id: The session ID to clear
        
    Returns:
        Success message
    """
    try:
        # Get the session if it exists
        session = await session_manager.get_session(session_id)
        if session:
            # Clear the context data
            session.context.current_loan_number = None
            session.context.current_borrower_name = None
            session.context.current_loan_data = None
            session.context.current_payoff_data = None
            session.context.generated_pdf_filename = None
            session.context.borrower_email = None
            session.context.pending_email_confirmation = False
            session.context.pending_email_address = None
            session.context.pending_email_loan_number = None
            session.context_message_shown = False
            
            logger.info(f"Cleared session: {session_id}")
            return {"message": "Session cleared successfully", "session_id": session_id}
        else:
            return {"message": "Session not found or already expired", "session_id": session_id}
            
    except Exception as e:
        logger.error(f"Error clearing session {session_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear session: {str(e)}"
        )


@router.get("/session/{session_id}/status")
async def get_session_status(session_id: str) -> Dict[str, Any]:
    """
    Get the current status and cached data for a session.
    
    Args:
        session_id: The session ID to check
        
    Returns:
        Session status and cached loan information
    """
    try:
        session = await session_manager.get_session(session_id)
        if session:
            return {
                "session_id": session_id,
                "status": session.status.value,
                "cached_loan": {
                    "loan_number": session.context.current_loan_number,
                    "borrower_name": session.context.current_borrower_name,
                    "has_payoff_data": session.context.current_payoff_data is not None,
                    "has_pdf": session.context.generated_pdf_filename is not None
                },
                "created_at": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat()
            }
        else:
            return {
                "session_id": session_id,
                "status": "not_found",
                "message": "Session not found or expired"
            }
            
    except Exception as e:
        logger.error(f"Error getting session status {session_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session status: {str(e)}"
        )


@router.get("/health")
async def check_chat_health() -> Dict[str, Any]:
    """
    Health check for the chat API and AI orchestration service.
    
    Returns:
        Health status of chat functionality and dependencies
    """
    try:
        # Test basic AI orchestrator connectivity
        health_status = {
            "chat_api": "healthy",
            "ai_orchestrator": "healthy",
            "ollama_connection": "unknown"  # Would need actual test
        }
        
        # Test if loan data is available for AI operations
        from ..components.data_access import loan_data_access
        health_status["loan_data"] = "available" if loan_data_access.is_data_loaded() else "not_loaded"
        
        overall_status = "healthy" if health_status["loan_data"] == "available" else "degraded"
        
        orchestrator = get_ai_orchestrator()
        return {
            "status": overall_status,
            "components": health_status,
            "available_tools": list(orchestrator.available_tools.keys())
        }
        
    except Exception as e:
        logger.error(f"Error checking chat health: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


@router.get("/tools")
async def get_available_chat_tools() -> Dict[str, Any]:
    """
    Get information about available AI tools for chat interactions.
    
    Returns:
        Dictionary of available tools and their descriptions
    """
    try:
        tools_info = {}
        
        orchestrator = get_ai_orchestrator()
        for tool_name, tool_def in orchestrator.available_tools.items():
            function_def = tool_def["function"]
            tools_info[tool_name] = {
                "name": function_def["name"],
                "description": function_def["description"],
                "parameters": function_def["parameters"]
            }
        
        return {
            "success": True,
            "available_tools": tools_info,
            "usage_examples": [
                "Show me loan information for Mark Wilson",
                "Calculate payoff for loan 69253358",
                "Get loan info for 69253358, calculate payoff, and create PDF",
                "Process payoff for Mark Wilson"
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting chat tools: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving tool information"
        )


@router.get("/models")
async def get_available_models() -> Dict[str, Any]:
    """
    Get information about available AI models and current configuration.
    
    Returns:
        Dictionary with available models and current model info
    """
    try:
        orchestrator = get_ai_orchestrator()
        return {
            "success": True,
            "current_model": orchestrator.get_model_info(),
            "available_models": orchestrator.get_available_models()
        }
    except Exception as e:
        logger.error(f"Error getting model information: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving model information"
        )


@router.post("/models/set/{model_size}")
async def set_model_size(model_size: str) -> Dict[str, Any]:
    """
    Set the AI model size for chat interactions.
    
    Args:
        model_size: Model size to use (8b, 14b, 30b, 32b)
        
    Returns:
        Success message with new model info
    """
    try:
        # Map string to enum
        model_mapping = {
            "8b": QwenModelSize.SIZE_8B,
            "14b": QwenModelSize.SIZE_14B, 
            "30b": QwenModelSize.SIZE_30B,
            "32b": QwenModelSize.SIZE_32B
        }
        
        if model_size not in model_mapping:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid model size. Available: {list(model_mapping.keys())}"
            )
        
        new_model = model_mapping[model_size]
        orchestrator = get_ai_orchestrator()
        orchestrator.set_model_size(new_model)
        
        return {
            "success": True,
            "message": f"Model changed to {new_model.value}",
            "model_info": orchestrator.get_model_info()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting model size: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error setting model size"
        )


