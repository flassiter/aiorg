"""
Tool chaining engine for executing sequences of related tools.
"""
import re
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass

from ..models.tool_chain import (
    ToolStep, ToolChainPlan, ChainExecutionResult, ProgressUpdate, 
    ChainTemplate, ToolStepStatus
)

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    """Tool definition for chain execution."""
    name: str
    execute_func: Callable
    description: str
    required_context: List[str] = None
    provides_context: List[str] = None


class ToolChainEngine:
    """
    Engine for executing tool chains with dependency management and context passing.
    """
    
    def __init__(self):
        self.available_tools: Dict[str, ToolDefinition] = {}
        self.chain_templates: List[ChainTemplate] = []
        self.progress_callbacks: List[Callable] = []
        self._setup_default_templates()
    
    def register_tool(
        self, 
        name: str, 
        execute_func: Callable, 
        description: str,
        required_context: List[str] = None,
        provides_context: List[str] = None
    ):
        """
        Register a tool for use in chains.
        
        Args:
            name: Tool name
            execute_func: Async function to execute the tool
            description: Tool description
            required_context: Context keys this tool needs
            provides_context: Context keys this tool provides
        """
        self.available_tools[name] = ToolDefinition(
            name=name,
            execute_func=execute_func,
            description=description,
            required_context=required_context or [],
            provides_context=provides_context or []
        )
        logger.info(f"Registered tool: {name}")
        logger.debug(f"Total registered tools: {len(self.available_tools)}")
    
    def add_progress_callback(self, callback: Callable):
        """Add callback for progress updates."""
        self.progress_callbacks.append(callback)
    
    def detect_chain_pattern(self, user_message: str) -> Optional[ChainTemplate]:
        """
        Detect if user message matches a known chain pattern.
        
        Args:
            user_message: User's message
            
        Returns:
            Matching chain template or None
        """
        message_lower = user_message.lower()
        
        for template in self.chain_templates:
            if re.search(template.pattern, message_lower, re.IGNORECASE):
                logger.info(f"Detected chain pattern: {template.name}")
                return template
        
        return None
    
    def create_chain_plan(
        self, 
        template: ChainTemplate, 
        context: Dict[str, Any] = None
    ) -> ToolChainPlan:
        """
        Create an execution plan from a template.
        
        Args:
            template: Chain template
            context: Initial context data
            
        Returns:
            Tool chain execution plan
        """
        chain_id = str(uuid.uuid4())
        context = context or {}
        
        steps = []
        for i, step_def in enumerate(template.steps, 1):
            step = ToolStep(
                step_number=i,
                tool_name=step_def["tool_name"],
                parameters=step_def.get("parameters", {}),
                depends_on=step_def.get("depends_on"),
                context_data=context.copy()
            )
            steps.append(step)
        
        plan = ToolChainPlan(
            chain_id=chain_id,
            description=template.description,
            steps=steps,
            total_steps=len(steps)
        )
        
        logger.info(f"Created chain plan: {chain_id} with {len(steps)} steps")
        return plan
    
    def create_custom_chain(
        self, 
        description: str, 
        tool_sequence: List[str],
        context: Dict[str, Any] = None
    ) -> ToolChainPlan:
        """
        Create a custom tool chain.
        
        Args:
            description: Chain description
            tool_sequence: List of tool names to execute in order
            context: Initial context
            
        Returns:
            Tool chain execution plan
        """
        chain_id = str(uuid.uuid4())
        context = context or {}
        
        steps = []
        for i, tool_name in enumerate(tool_sequence, 1):
            if tool_name not in self.available_tools:
                raise ValueError(f"Unknown tool: {tool_name}")
            
            step = ToolStep(
                step_number=i,
                tool_name=tool_name,
                parameters={},
                context_data=context.copy()
            )
            steps.append(step)
        
        plan = ToolChainPlan(
            chain_id=chain_id,
            description=description,
            steps=steps,
            total_steps=len(steps)
        )
        
        return plan
    
    async def execute_chain(
        self, 
        plan: ToolChainPlan, 
        session_context: Dict[str, Any] = None
    ) -> ChainExecutionResult:
        """
        Execute a tool chain plan.
        
        Args:
            plan: Tool chain plan to execute
            session_context: Session-level context data
            
        Returns:
            Chain execution result
        """
        logger.info(f"Starting chain execution: {plan.chain_id}")
        start_time = datetime.now()
        session_context = session_context or {}
        
        # Merge session context into plan context
        for step in plan.steps:
            step.context_data.update(session_context)
        
        try:
            # Execute steps in order
            for step in plan.steps:
                await self._execute_step(step, plan)
                
                # Break on failure if step is critical
                if step.status == ToolStepStatus.FAILED:
                    logger.error(f"Step {step.step_number} failed: {step.error_message}")
                    break
            
            # Calculate results
            end_time = datetime.now()
            total_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            success = plan.is_successful
            message = self._generate_summary_message(plan)
            final_result = self._aggregate_results(plan)
            
            result = ChainExecutionResult(
                chain_id=plan.chain_id,
                plan=plan,
                success=success,
                total_execution_time_ms=total_time_ms,
                message=message,
                final_result=final_result,
                context_data=self._extract_final_context(plan)
            )
            
            logger.info(f"Chain execution completed: {plan.chain_id}, success: {success}")
            return result
            
        except Exception as e:
            logger.error(f"Chain execution failed: {str(e)}")
            end_time = datetime.now()
            total_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return ChainExecutionResult(
                chain_id=plan.chain_id,
                plan=plan,
                success=False,
                total_execution_time_ms=total_time_ms,
                message=f"Chain execution failed: {str(e)}",
                final_result=None,
                context_data={}
            )
    
    async def _execute_step(self, step: ToolStep, plan: ToolChainPlan):
        """Execute a single step in the chain."""
        logger.info(f"Executing step {step.step_number}: {step.tool_name}")
        logger.debug(f"Available tools: {list(self.available_tools.keys())}")
        
        # Check if tool is available
        if step.tool_name not in self.available_tools:
            step.status = ToolStepStatus.FAILED
            step.error_message = f"Tool not available: {step.tool_name}. Available: {list(self.available_tools.keys())}"
            logger.error(step.error_message)
            return
        
        # Update status and send progress
        step.status = ToolStepStatus.IN_PROGRESS
        step.started_at = datetime.now()
        await self._send_progress_update(step, plan)
        
        try:
            # Get tool definition
            tool_def = self.available_tools[step.tool_name]
            
            # Prepare parameters with context
            parameters = step.parameters.copy()
            parameters.update(step.context_data)
            
            # Execute tool
            start_time = datetime.now()
            result = await tool_def.execute_func(parameters)
            end_time = datetime.now()
            
            # Update step with results
            step.result = result
            step.execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
            step.completed_at = datetime.now()
            step.status = ToolStepStatus.COMPLETED
            
            # Update context for subsequent steps
            if hasattr(result, 'success') and result.success:
                logger.debug(f"Updating context from {step.tool_name} result")
                self._update_context_from_result(step, result, plan)
            else:
                logger.debug(f"Not updating context from {step.tool_name}: success={getattr(result, 'success', 'N/A')}")
            
            logger.info(f"Step {step.step_number} completed in {step.execution_time_ms}ms")
            
        except Exception as e:
            step.status = ToolStepStatus.FAILED
            step.error_message = str(e)
            step.completed_at = datetime.now()
            logger.error(f"Step {step.step_number} failed: {str(e)}")
        
        # Send progress update
        await self._send_progress_update(step, plan)
    
    def _update_context_from_result(self, step: ToolStep, result: Any, plan: ToolChainPlan):
        """Update context for subsequent steps based on step result."""
        tool_def = self.available_tools[step.tool_name]
        
        # Extract context data based on tool type
        if step.tool_name == "get_loan_info" and result.success:
            loan_data = result.result or {}
            context_updates = {
                'current_loan_number': loan_data.get('loan_number'),
                'current_borrower_name': loan_data.get('borrower_name'),
                'current_loan_data': loan_data
            }
        elif step.tool_name == "calculate_payoff" and result.success:
            payoff_data = result.result or {}
            context_updates = {
                'current_payoff_data': payoff_data,
                'total_payoff_amount': payoff_data.get('total_payoff')
            }
        elif step.tool_name == "generate_pdf" and result.success:
            pdf_data = result.result or {}
            context_updates = {
                'generated_pdf_filename': pdf_data.get('filename'),
                'generated_pdf_url': pdf_data.get('download_url')
            }
        else:
            context_updates = {}
        
        # Update all subsequent steps
        logger.debug(f"Applying context updates to subsequent steps: {context_updates}")
        for future_step in plan.steps[step.step_number:]:
            future_step.context_data.update(context_updates)
            logger.debug(f"Step {future_step.step_number} context now includes: {list(future_step.context_data.keys())}")
    
    async def _send_progress_update(self, step: ToolStep, plan: ToolChainPlan):
        """Send progress update to registered callbacks."""
        percentage = (step.step_number / plan.total_steps) * 100
        if step.status == ToolStepStatus.COMPLETED:
            percentage = (step.step_number / plan.total_steps) * 100
        elif step.status == ToolStepStatus.IN_PROGRESS:
            percentage = ((step.step_number - 1) / plan.total_steps) * 100 + 10  # Add 10% for in-progress
        
        step_result = None
        if step.status == ToolStepStatus.COMPLETED and step.result:
            # Convert ToolResult to dict if needed
            if hasattr(step.result, 'dict'):
                step_result = step.result.dict()
            elif isinstance(step.result, dict):
                step_result = step.result
        
        update = ProgressUpdate(
            chain_id=plan.chain_id,
            current_step=step.step_number,
            total_steps=plan.total_steps,
            step_name=step.tool_name,
            step_status=step.status,
            message=self._get_progress_message(step),
            percentage=min(percentage, 100),
            step_result=step_result
        )
        
        for callback in self.progress_callbacks:
            try:
                await callback(update)
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")
    
    def _get_progress_message(self, step: ToolStep) -> str:
        """Generate progress message for a step."""
        messages = {
            ToolStepStatus.PENDING: f"Waiting to execute {step.tool_name}...",
            ToolStepStatus.IN_PROGRESS: f"Executing {step.tool_name}...",
            ToolStepStatus.COMPLETED: f"Completed {step.tool_name}",
            ToolStepStatus.FAILED: f"Failed {step.tool_name}: {step.error_message}",
            ToolStepStatus.SKIPPED: f"Skipped {step.tool_name}"
        }
        return messages.get(step.status, f"Unknown status for {step.tool_name}")
    
    def _generate_summary_message(self, plan: ToolChainPlan) -> str:
        """Generate summary message for chain execution."""
        if plan.is_successful:
            return f"Chain '{plan.description}' completed successfully in {plan.completed_steps}/{plan.total_steps} steps"
        else:
            return f"Chain '{plan.description}' completed with {plan.failed_steps} failed steps"
    
    def _aggregate_results(self, plan: ToolChainPlan) -> Dict[str, Any]:
        """Aggregate results from all completed steps."""
        aggregated = {
            'steps_executed': plan.completed_steps,
            'total_steps': plan.total_steps,
            'success_rate': plan.completed_steps / plan.total_steps if plan.total_steps > 0 else 0,
            'step_results': {}
        }
        
        for step in plan.steps:
            if step.status == ToolStepStatus.COMPLETED and step.result:
                aggregated['step_results'][step.tool_name] = step.result
        
        return aggregated
    
    def _extract_final_context(self, plan: ToolChainPlan) -> Dict[str, Any]:
        """Extract final context state from the last step."""
        if plan.steps:
            return plan.steps[-1].context_data.copy()
        return {}
    
    def _setup_default_templates(self):
        """Setup default chain templates."""
        # Complete payoff processing workflow
        complete_payoff = ChainTemplate(
            name="complete_payoff_processing",
            description="Complete loan payoff processing workflow",
            pattern=r"process.*payoff|complete.*payoff|full.*payoff|process.*loan",
            steps=[
                {
                    "tool_name": "get_loan_info",
                    "description": "Retrieve loan information"
                },
                {
                    "tool_name": "calculate_payoff", 
                    "description": "Calculate current payoff amount"
                },
                {
                    "tool_name": "generate_pdf",
                    "description": "Generate payoff statement PDF"
                }
            ],
            requires_confirmation=False
        )
        
        # Quick loan lookup and calculation
        quick_payoff = ChainTemplate(
            name="quick_payoff_calc",
            description="Quick payoff calculation and display",
            pattern=r"calculate.*payoff|payoff.*calculation|how much.*payoff",
            steps=[
                {
                    "tool_name": "get_loan_info",
                    "description": "Retrieve loan information"
                },
                {
                    "tool_name": "calculate_payoff",
                    "description": "Calculate current payoff amount"
                }
            ],
            requires_confirmation=False
        )
        
        # PDF generation with current context
        pdf_with_context = ChainTemplate(
            name="pdf_with_context",
            description="Generate PDF with current loan context",
            pattern=r"create.*(?:loan.*)?payoff.*document|generate.*(?:loan.*)?payoff.*pdf|create.*pdf.*document|generate.*pdf.*payoff",
            steps=[
                {
                    "tool_name": "generate_pdf",
                    "description": "Generate payoff statement PDF using current context"
                }
            ],
            requires_confirmation=False
        )
        
        self.chain_templates = [complete_payoff, quick_payoff, pdf_with_context]
        logger.info(f"Setup {len(self.chain_templates)} default chain templates")


# Global tool chain engine instance
tool_chain_engine = ToolChainEngine()