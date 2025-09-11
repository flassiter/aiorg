from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


class ToolCall(BaseModel):
    tool_name: str
    parameters: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None


class ToolResult(BaseModel):
    tool_name: str
    parameters: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    success: bool = True
    error_message: Optional[str] = None


class ChatResponse(BaseModel):
    message: str
    tool_calls: List[ToolCall] = Field(default_factory=list)
    files_generated: List[str] = Field(default_factory=list)
    success: bool = True
    error_message: Optional[str] = None
    # Enhanced fields for progressive responses
    session_id: Optional[str] = None
    chain_id: Optional[str] = None
    progress_updates: List[Dict[str, Any]] = Field(default_factory=list)
    debug_info: Optional[Dict[str, Any]] = None


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    debug_mode: bool = False


class OllamaToolCall(BaseModel):
    function: Dict[str, Any]


class OllamaResponse(BaseModel):
    message: Dict[str, Any]
    done: bool
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    prompt_eval_duration: Optional[int] = None
    eval_count: Optional[int] = None
    eval_duration: Optional[int] = None


class ProgressiveResponse(BaseModel):
    """Response for real-time progress updates."""
    response_type: str = Field(..., description="Type of response: progress, result, error")
    session_id: str = Field(..., description="Session identifier")
    step_number: Optional[int] = None
    total_steps: Optional[int] = None
    current_action: Optional[str] = None
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    is_final: bool = False


class EmailConfirmationRequest(BaseModel):
    """Request for email confirmation."""
    session_id: str
    email_address: str
    loan_number: Optional[str] = None
    confirmation_message: str


class EmailConfirmationResponse(BaseModel):
    """Response to email confirmation."""
    session_id: str
    confirmed: bool
    message: str