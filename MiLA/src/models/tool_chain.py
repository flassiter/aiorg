"""
Pydantic models for tool chaining and execution plans.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class ToolStepStatus(str, Enum):
    """Status of individual tool steps in a chain."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ToolStep(BaseModel):
    """
    Individual step in a tool execution chain.
    """
    step_number: int = Field(..., description="Order of execution (1-based)")
    tool_name: str = Field(..., description="Name of the tool to execute")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters")
    depends_on: Optional[List[int]] = Field(default=None, description="Steps this depends on (step numbers)")
    status: ToolStepStatus = Field(default=ToolStepStatus.PENDING, description="Current status")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Tool execution result")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    execution_time_ms: Optional[int] = Field(default=None, description="Execution time in milliseconds")
    started_at: Optional[datetime] = Field(default=None, description="When step started")
    completed_at: Optional[datetime] = Field(default=None, description="When step completed")
    context_data: Dict[str, Any] = Field(default_factory=dict, description="Data passed from previous steps")


class ToolChainPlan(BaseModel):
    """
    Execution plan for a sequence of tool calls.
    """
    chain_id: str = Field(..., description="Unique identifier for this chain")
    description: str = Field(..., description="Human-readable description of the chain")
    steps: List[ToolStep] = Field(..., description="Ordered list of tool steps")
    total_steps: int = Field(..., description="Total number of steps in chain")
    created_at: datetime = Field(default_factory=datetime.now, description="When plan was created")
    
    @property
    def current_step(self) -> Optional[ToolStep]:
        """Get the currently executing step."""
        for step in self.steps:
            if step.status == ToolStepStatus.IN_PROGRESS:
                return step
        return None
    
    @property
    def completed_steps(self) -> int:
        """Count of completed steps."""
        return len([s for s in self.steps if s.status == ToolStepStatus.COMPLETED])
    
    @property
    def failed_steps(self) -> int:
        """Count of failed steps."""
        return len([s for s in self.steps if s.status == ToolStepStatus.FAILED])
    
    @property
    def is_complete(self) -> bool:
        """Check if all steps are complete or failed."""
        return all(s.status in [ToolStepStatus.COMPLETED, ToolStepStatus.FAILED, ToolStepStatus.SKIPPED] 
                  for s in self.steps)
    
    @property
    def is_successful(self) -> bool:
        """Check if chain completed successfully (no failed steps)."""
        return self.is_complete and self.failed_steps == 0


class ChainExecutionResult(BaseModel):
    """
    Result of executing a tool chain.
    """
    chain_id: str = Field(..., description="Chain identifier")
    plan: ToolChainPlan = Field(..., description="Execution plan with results")
    success: bool = Field(..., description="Overall success status")
    total_execution_time_ms: int = Field(..., description="Total execution time")
    message: str = Field(..., description="Summary message")
    final_result: Optional[Dict[str, Any]] = Field(default=None, description="Final aggregated result")
    context_data: Dict[str, Any] = Field(default_factory=dict, description="Final context state")


class ProgressUpdate(BaseModel):
    """
    Real-time progress update for tool chain execution.
    """
    chain_id: str = Field(..., description="Chain identifier")
    current_step: int = Field(..., description="Current step number (1-based)")
    total_steps: int = Field(..., description="Total number of steps")
    step_name: str = Field(..., description="Name of current step")
    step_status: ToolStepStatus = Field(..., description="Status of current step")
    message: str = Field(..., description="Progress message")
    percentage: float = Field(..., description="Completion percentage (0-100)")
    step_result: Optional[Dict[str, Any]] = Field(default=None, description="Step result if completed")
    timestamp: datetime = Field(default_factory=datetime.now, description="Update timestamp")


class ChainTemplate(BaseModel):
    """
    Template for common tool chain patterns.
    """
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    pattern: str = Field(..., description="Pattern regex or keywords that trigger this chain")
    steps: List[Dict[str, Any]] = Field(..., description="Template step definitions")
    requires_confirmation: bool = Field(default=False, description="Whether chain requires user confirmation")
    
    class Config:
        """Example templates."""
        schema_extra = {
            "examples": [
                {
                    "name": "complete_payoff_processing",
                    "description": "Full loan payoff processing workflow",
                    "pattern": "process.*payoff|complete.*loan|full.*workflow",
                    "steps": [
                        {"tool_name": "get_loan_info", "description": "Retrieve loan information"},
                        {"tool_name": "calculate_payoff", "description": "Calculate current payoff amount"},
                        {"tool_name": "generate_pdf", "description": "Generate payoff statement PDF"},
                        {"tool_name": "prepare_email", "description": "Prepare email confirmation"}
                    ],
                    "requires_confirmation": False
                }
            ]
        }