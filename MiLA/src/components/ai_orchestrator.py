"""
AI Orchestration component for processing user messages and executing tool sequences.
"""
import json
import logging
import os
from typing import List, Dict, Any, Optional
from datetime import date
from enum import Enum

import httpx
from pydantic import ValidationError

from ..models.chat import ChatResponse, ToolCall, ToolResult, MessageRole
from ..components.data_access import loan_data_access, DataAccessError
from ..components.calculator import payoff_calculator, CalculationError
from ..components.pdf_generator import pdf_generator, PDFGenerationError
from ..components.email_service import email_service, EmailSimulationError
from ..components.tool_chain import tool_chain_engine, ToolChainEngine
from ..components.session_manager import session_manager, SessionManager
from ..models.payoff import PayoffCalculationRequest
from ..models.pdf_data import PDFGenerationRequest
from ..models.tool_chain import ToolChainPlan, ChainExecutionResult, ProgressUpdate
from ..models.session import ChatSession, ContextData

logger = logging.getLogger(__name__)


class AIOrchestrationError(Exception):
    """Custom exception for AI orchestration operations."""
    pass


class QwenModelSize(str, Enum):
    """Supported Qwen model sizes."""
    SIZE_7B = "qwen2.5-coder:7b-instruct"  # Use available coder variant
    SIZE_14B = "qwen2.5-coder:14b"  # Use available 14b model
    SIZE_32B = "qwen2.5:32b-instruct"
    SIZE_CODER_7B = "qwen2.5-coder:7b-instruct"  # Code-focused variant


class ModelConfig:
    """Configuration for different model sizes."""
    
    CONFIGS = {
        QwenModelSize.SIZE_7B: {
            "temperature": 0.1,
            "max_tokens": 2048,
            "timeout": 15.0,
            "description": "Lightweight 7B model"
        },
        QwenModelSize.SIZE_14B: {
            "temperature": 0.1,
            "max_tokens": 4096,
            "timeout": 20.0,
            "description": "Balanced 14B model"
        },
        QwenModelSize.SIZE_32B: {
            "temperature": 0.1,
            "max_tokens": 8192,
            "timeout": 30.0,
            "description": "High-quality 32B model"
        },
        QwenModelSize.SIZE_CODER_7B: {
            "temperature": 0.1,
            "max_tokens": 2048,
            "timeout": 15.0,
            "description": "Code-focused 7B model"
        }
    }
    
    @classmethod
    def get_config(cls, model_size: QwenModelSize) -> Dict[str, Any]:
        """Get configuration for a specific model size."""
        return cls.CONFIGS.get(model_size, cls.CONFIGS[QwenModelSize.SIZE_14B])


class AIOrchestrator:
    """
    AI orchestration service for processing user messages and coordinating tool execution.
    """
    
    def __init__(
        self, 
        ollama_base_url: str = "http://localhost:11434",
        model_size: Optional[QwenModelSize] = None,
        server_base_url: str = "http://localhost:8000"
    ):
        self.ollama_base_url = ollama_base_url
        self.server_base_url = server_base_url
        
        # Set model size from parameter or environment variable
        if model_size is None:
            env_model = os.getenv("MILA_MODEL_SIZE", "qwen2.5-coder:14b")
            try:
                self.model_size = QwenModelSize(env_model)
                logger.info(f"Using model from environment: {env_model}")
            except ValueError:
                logger.warning(f"Invalid model size in environment: {env_model}, using default")
                self.model_size = QwenModelSize.SIZE_14B
        else:
            self.model_size = model_size
            logger.info(f"Using specified model: {model_size.value}")
            
        # Get model configuration
        self.model_config = ModelConfig.get_config(self.model_size)
        self.model_name = self.model_size.value
        self.temperature = self.model_config["temperature"]
        self.max_tokens = self.model_config["max_tokens"]
        self.timeout = self.model_config["timeout"]
        
        logger.info(f"AI Orchestrator initialized with model: {self.model_name}")
        logger.info(f"Model config: {self.model_config['description']}")
        
        # Setup tools and chain engine
        self._setup_tools()
        self._register_tools_with_chain_engine()
        
        # Progress callbacks for chain execution
        self.progress_callbacks = []
        tool_chain_engine.add_progress_callback(self._handle_chain_progress)

    def set_model_size(self, model_size: QwenModelSize) -> None:
        """
        Change the model size dynamically.
        
        Args:
            model_size: New model size to use
        """
        self.model_size = model_size
        self.model_config = ModelConfig.get_config(model_size)
        self.model_name = model_size.value
        self.temperature = self.model_config["temperature"]
        self.max_tokens = self.model_config["max_tokens"]
        self.timeout = self.model_config["timeout"]
        
        logger.info(f"Model changed to: {self.model_name}")
        logger.info(f"New config: {self.model_config['description']}")

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get current model information.
        
        Returns:
            Dictionary with current model details
        """
        return {
            "model_name": self.model_name,
            "model_size": self.model_size.value,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout,
            "description": self.model_config["description"]
        }

    def get_available_models(self) -> Dict[str, Any]:
        """
        Get information about all available models.
        
        Returns:
            Dictionary with all available model configurations
        """
        return {
            model_size.value: {
                "size": model_size.value,
                "config": ModelConfig.get_config(model_size)
            }
            for model_size in QwenModelSize
        }

    def _setup_tools(self):
        """Setup tool definitions for function calling."""
        self.available_tools = {
            "get_loan_info": {
                "type": "function",
                "function": {
                    "name": "get_loan_info",
                    "description": "Search for loan information by loan number or borrower name",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "identifier": {
                                "type": "string",
                                "description": "Loan number (6-8 digits) or borrower name (First Last format)"
                            }
                        },
                        "required": ["identifier"]
                    }
                }
            },
            "calculate_payoff": {
                "type": "function",
                "function": {
                    "name": "calculate_payoff",
                    "description": "Calculate current payoff amount for a loan",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "loan_number": {
                                "type": "string",
                                "description": "The loan number to calculate payoff for"
                            },
                            "as_of_date": {
                                "type": "string",
                                "description": "Optional calculation date in YYYY-MM-DD format. Defaults to today."
                            }
                        },
                        "required": ["loan_number"]
                    }
                }
            },
            "generate_pdf": {
                "type": "function",
                "function": {
                    "name": "generate_pdf",
                    "description": "Create a payoff statement PDF for a loan",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "loan_number": {
                                "type": "string",
                                "description": "The loan number to generate PDF for"
                            },
                            "statement_date": {
                                "type": "string",
                                "description": "Optional statement date in YYYY-MM-DD format. Defaults to today."
                            }
                        },
                        "required": ["loan_number"]
                    }
                }
            },
            "send_email": {
                "type": "function",
                "function": {
                    "name": "send_email",
                    "description": "Send payoff information via email to borrower",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "email_address": {
                                "type": "string",
                                "description": "Email address to send to (optional, will use address on file)"
                            },
                            "loan_number": {
                                "type": "string",
                                "description": "Loan number for context (optional, will use current context)"
                            }
                        },
                        "required": []
                    }
                }
            },
            "confirm_email": {
                "type": "function",
                "function": {
                    "name": "confirm_email",
                    "description": "Confirm email sending with user",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "email_address": {
                                "type": "string",
                                "description": "Email address to confirm"
                            }
                        },
                        "required": ["email_address"]
                    }
                }
            }
        }
    
    def _register_tools_with_chain_engine(self):
        """Register tools with the chain engine for execution."""
        # Register individual tool executors
        tool_chain_engine.register_tool(
            "get_loan_info", 
            self._execute_get_loan_info,
            "Search for loan information by loan number or borrower name",
            required_context=[],
            provides_context=["current_loan_data", "current_loan_number", "current_borrower_name"]
        )
        
        tool_chain_engine.register_tool(
            "calculate_payoff",
            self._execute_calculate_payoff, 
            "Calculate current payoff amount for a loan",
            required_context=["current_loan_number"],
            provides_context=["current_payoff_data", "total_payoff_amount"]
        )
        
        tool_chain_engine.register_tool(
            "generate_pdf",
            self._execute_generate_pdf,
            "Generate payoff statement PDF for a loan", 
            required_context=["current_loan_number"],
            provides_context=["generated_pdf_filename", "generated_pdf_url"]
        )
        
        tool_chain_engine.register_tool(
            "send_email",
            self._execute_send_email,
            "Send payoff information via email",
            required_context=["current_loan_data"],
            provides_context=[]
        )
        
        tool_chain_engine.register_tool(
            "confirm_email",
            self._execute_confirm_email,
            "Confirm email sending with user",
            required_context=["borrower_email"],
            provides_context=["pending_email_confirmation"]
        )
    
    async def _handle_chain_progress(self, progress: ProgressUpdate):
        """Handle progress updates from chain execution."""
        # Forward to registered callbacks
        for callback in self.progress_callbacks:
            try:
                await callback(progress)
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")
    
    def add_progress_callback(self, callback):
        """Add callback for chain progress updates."""
        self.progress_callbacks.append(callback)

    def _build_system_prompt(self) -> str:
        """Build the system prompt for the AI model."""
        return """You are MiLA (Machine Intelligence Loan Assistant), an AI assistant specialized in loan processing and payoff calculations.

You have access to the following tools:
1. get_loan_info(identifier) - Search by loan number or borrower name
2. calculate_payoff(loan_number, as_of_date=today) - Calculate current payoff amount  
3. generate_pdf(loan_number, statement_date=today) - Create payoff statement PDF
4. send_email(email_address, loan_number) - Send payoff information via email
5. confirm_email(email_address) - Confirm email sending with user

Guidelines:
- Always search for loan information first when given a name or loan number
- Use exact loan numbers when available from context
- When users refer to "this loan", "the loan", or "current loan", use the loan number from the current context
- For complete payoff processing: get loan info → calculate payoff → generate PDF → (optionally) send email
- For email requests, always confirm with user before sending
- Provide clear, professional responses with specific dollar amounts
- Format currency as $X,XXX.XX
- Handle multi-step workflows seamlessly using context from previous steps
- Handle errors gracefully and suggest alternatives

Workflow Examples:
- "Show me loan information for Mark Wilson" → get_loan_info("Mark Wilson")
- "Calculate payoff for loan 69253358" → get_loan_info("69253358") → calculate_payoff()
- "Calculate payoff for this loan" → calculate_payoff() (using current loan from context)
- "Process complete payoff for John Doe" → get_loan_info("John Doe") → calculate_payoff() → generate_pdf()
- "Send payoff info by email" → confirm_email(borrower_email) → (if confirmed) send_email()

Context Awareness:
- Use loan information from previous steps when available
- Carry forward loan numbers, borrower details, and payoff amounts
- Remember generated PDF files for email attachments
- Always confirm email sending with specific address

Always respond professionally and include specific details from tool results."""

    async def process_user_message(
        self, 
        message: str, 
        session_id: Optional[str] = None
    ) -> ChatResponse:
        """
        Process a user message with enhanced chain execution and session support.
        
        Args:
            message: User's natural language request
            session_id: Optional session ID for context
            
        Returns:
            ChatResponse with results and any generated files
        """
        try:
            # Get or create session
            session = await session_manager.get_or_create_session(session_id)
            
            # For now, use simplified direct execution to bypass chain complexity
            # This ensures results are returned properly
            return await self._execute_simplified(message, session)
            
        except Exception as e:
            logger.error(f"Error processing user message: {str(e)}")
            return ChatResponse(
                message=f"I encountered an error processing your request: {str(e)}",
                success=False,
                error_message=str(e)
            )
    
    async def _execute_simplified(self, message: str, session: ChatSession) -> ChatResponse:
        """
        Simplified execution that directly processes common requests.
        This bypasses the complex chain logic for immediate functionality.
        """
        try:
            message_lower = message.lower()
            tool_results = []
            response_parts = []
            files_generated = []
            
            # Extract loan identifier from message
            import re
            loan_number = None
            borrower_name = None
            
            # Check for loan number
            loan_match = re.search(r'\b(\d{6,8})\b', message)
            if loan_match:
                loan_number = loan_match.group(1)
            
            # Check for borrower name
            name_patterns = [
                r'for\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
                r'([A-Z][a-z]+\s+[A-Z][a-z]+)(?:\s+loan)?',
            ]
            for pattern in name_patterns:
                name_match = re.search(pattern, message)
                if name_match:
                    borrower_name = name_match.group(1)
                    break
            
            # Use context if no identifier found
            if not loan_number and not borrower_name:
                if session.context.current_loan_number:
                    loan_number = session.context.current_loan_number
                    logger.info(f"Using cached loan from session: {loan_number}")
                elif do_payoff or do_pdf:
                    # User wants to do something but no loan is loaded
                    return ChatResponse(
                        message="❌ **No loan in context**\n\n"
                               "Please load a loan first before calculating payoff or generating PDFs.\n\n"
                               "Try one of these:\n"
                               "- 'Show loan info for [borrower name]'\n"
                               "- 'Load loan [loan number]'\n"
                               "- 'Find loan for Mark Wilson'",
                        success=False,
                        session_id=session.session_id
                    )
            
            # Check if this is a response to email confirmation
            if session.context.pending_email_confirmation:
                if message_lower.strip() in ['y', 'yes', 'ok', 'confirm', 'send']:
                    # User confirmed, send email
                    result = await self._execute_send_email({
                        "email_address": session.context.pending_email_address,
                        "loan_number": session.context.pending_email_loan_number,
                        "current_loan_data": session.context.current_loan_data,
                        "current_payoff_data": session.context.current_payoff_data,
                        "generated_pdf_filename": session.context.generated_pdf_filename
                    })
                    
                    # Clear pending state
                    session.context.pending_email_confirmation = False
                    session.context.pending_email_address = None
                    session.context.pending_email_loan_number = None
                    
                    if result.success:
                        return ChatResponse(
                            message=f"✅ **Email Sent Successfully**\n\n"
                                   f"Payoff statement has been sent to {result.result['data']['to_address']}.\n\n"
                                   f"Email ID: {result.result['data']['message_id']}",
                            success=True,
                            session_id=session.session_id
                        )
                    else:
                        return ChatResponse(
                            message=f"❌ **Failed to send email**: {result.error_message}",
                            success=False,
                            session_id=session.session_id
                        )
                elif message_lower.strip() in ['n', 'no', 'cancel', 'stop']:
                    # User cancelled
                    session.context.pending_email_confirmation = False
                    session.context.pending_email_address = None
                    session.context.pending_email_loan_number = None
                    
                    return ChatResponse(
                        message="✅ Email cancelled. The payoff statement was not sent.",
                        success=True,
                        session_id=session.session_id
                    )
                else:
                    # Invalid response
                    return ChatResponse(
                        message=f"Please respond with **Y** to send the email or **N** to cancel.\n\n"
                               f"Send payoff statement for loan {session.context.pending_email_loan_number} to {session.context.pending_email_address}? (Y/N)",
                        success=True,
                        session_id=session.session_id
                    )
            
            # Determine which operations to perform
            do_lookup = any(x in message_lower for x in ['loan info', 'loan information', 'search', 'find', 'lookup', 'show', 'get loan', 'retrieve'])
            do_payoff = any(x in message_lower for x in ['payoff', 'calculate', 'payment', 'how much', 'amount'])
            do_pdf = any(x in message_lower for x in ['pdf', 'document', 'statement', 'generate', 'create'])
            do_email = any(x in message_lower for x in ['email', 'send', 'mail'])
            
            # Smart chaining based on keywords
            if 'process' in message_lower or 'complete' in message_lower or 'full' in message_lower:
                # Full workflow
                do_lookup = True
                do_payoff = True
                do_pdf = True
            elif 'and' in message_lower:
                # Chain operations if "and" is used
                if 'payoff' in message_lower and 'pdf' in message_lower:
                    do_payoff = True
                    do_pdf = True
                    do_lookup = True  # Need loan info first
            
            # If nothing specific requested but we have an identifier, assume lookup
            if (loan_number or borrower_name) and not (do_lookup or do_payoff or do_pdf):
                do_lookup = True
            
            # Step 1: Get loan info if needed (check cache first)
            loan_data = None
            if do_lookup or do_payoff or do_pdf:
                # Check if we have cached loan data for this loan number
                if loan_number and session.context.current_loan_number == loan_number and session.context.current_loan_data:
                    loan_data = session.context.current_loan_data
                    logger.info(f"Using cached loan data for {loan_number}")
                    # Still append to response if explicitly requested
                    if do_lookup:
                        response_parts.append(
                            f"## 📋 Loan Information (Cached)\n\n"
                            f"**Loan Number:** {loan_data['loan_number']}\n"
                            f"**Borrower:** {loan_data['borrower_name']}\n"
                            f"**Principal Balance:** ${loan_data['principal_balance']:,.2f}\n"
                            f"**Interest Rate:** {loan_data['annual_interest_rate']:.2f}%\n"
                            f"**Last Payment:** {loan_data['last_payment_date']}"
                        )
                # Otherwise fetch fresh data
                elif loan_number:
                    result = await self._execute_get_loan_info({"identifier": loan_number})
                elif borrower_name:
                    result = await self._execute_get_loan_info({"identifier": borrower_name})
                else:
                    return ChatResponse(
                        message="Please provide a loan number or borrower name.",
                        success=False
                    )
                
                # Only process result if we fetched fresh data
                if loan_data is None:
                    if result.success:
                        loan_data = result.result
                        loan_number = loan_data['loan_number']
                        tool_results.append(result)
                        
                        # Update session context with fresh data
                        session.context.current_loan_number = loan_number
                        session.context.current_borrower_name = loan_data['borrower_name']
                        session.context.current_loan_data = loan_data
                        
                        response_parts.append(
                            f"## 📋 Loan Information\n\n"
                            f"**Loan Number:** {loan_data['loan_number']}\n"
                            f"**Borrower:** {loan_data['borrower_name']}\n"
                            f"**Principal Balance:** ${loan_data['principal_balance']:,.2f}\n"
                            f"**Interest Rate:** {loan_data['annual_interest_rate']:.2f}%\n"
                            f"**Last Payment:** {loan_data['last_payment_date']}"
                        )
                    else:
                        return ChatResponse(
                            message=f"❌ Could not find loan: {result.error_message}",
                            success=False,
                            error_message=result.error_message
                        )
            
            # Step 2: Calculate payoff if requested
            payoff_data = None
            if do_payoff and loan_number:
                result = await self._execute_calculate_payoff({"loan_number": loan_number})
                if result.success:
                    payoff_data = result.result
                    tool_results.append(result)
                    
                    # Update session context
                    session.context.current_payoff_data = payoff_data
                    
                    response_parts.append(
                        f"## 💰 Payoff Calculation\n\n"
                        f"**Principal Balance:** ${payoff_data['principal_balance']:,.2f}\n"
                        f"**Interest Accrued:** ${payoff_data['interest_accrued']:,.2f}\n"
                        f"**Total Payoff Amount:** ${payoff_data['total_payoff']:,.2f}\n"
                        f"**Calculation Date:** {payoff_data['calculation_date']}\n"
                        f"**Good Through Date:** {payoff_data.get('good_through_date', 'N/A')}\n"
                        f"**Days Since Last Payment:** {payoff_data['days_since_payment']}"
                    )
            
            # Step 3: Generate PDF if requested
            if do_pdf and loan_number:
                result = await self._execute_generate_pdf({"loan_number": loan_number})
                if result.success:
                    pdf_data = result.result
                    tool_results.append(result)
                    files_generated.append(pdf_data['filename'])
                    
                    # Update session context
                    session.context.generated_pdf_filename = pdf_data['filename']
                    
                    # Create full download URL
                    full_download_url = f"{self.server_base_url}{pdf_data['download_url']}"
                    
                    response_parts.append(
                        f"## 📄 PDF Generated\n\n"
                        f"**Filename:** {pdf_data['filename']}\n"
                        f"**Download:** [Click here to download]({full_download_url})\n\n"
                        f"✅ Payoff statement PDF has been generated successfully!"
                    )
            
            # Step 4: Handle email request
            if do_email:
                # Get email address
                email_address = None
                if session.context.current_loan_data:
                    email_address = session.context.current_loan_data.get('email_address')
                    if not email_address:
                        # Generate demo email from borrower name
                        borrower_name = session.context.current_borrower_name
                        if borrower_name:
                            email_name = borrower_name.lower().replace(' ', '.')
                            email_address = f"{email_name}@email.com"
                
                if email_address and session.context.current_loan_number:
                    # Set pending email confirmation
                    session.context.pending_email_confirmation = True
                    session.context.pending_email_address = email_address
                    session.context.pending_email_loan_number = session.context.current_loan_number
                    
                    response_parts.append(
                        f"## 📧 Email Confirmation\n\n"
                        f"Send payoff statement for loan {session.context.current_loan_number} to {email_address}?\n\n"
                        f"**Reply with Y to send or N to cancel**"
                    )
                else:
                    response_parts.append(
                        f"❌ **Cannot send email**\n\n"
                        f"No loan loaded or email address not available. Please load a loan first."
                    )
            
            # Create response
            if response_parts:
                # Add session context hint only if first time with cached data
                if session.context.current_loan_number and not session.context_message_shown and not session.context.pending_email_confirmation:
                    response_parts.append(
                        f"\n💡 *Session Context: Loan {session.context.current_loan_number} is now cached. "
                        f"You can run additional commands without specifying the loan number.*"
                    )
                    session.context_message_shown = True
                
                return ChatResponse(
                    message="\n\n".join(response_parts),
                    tool_calls=[ToolCall(
                        tool_name=r.tool_name, 
                        parameters=r.parameters, 
                        result=r.result
                    ) for r in tool_results],
                    files_generated=files_generated,
                    success=True,
                    session_id=session.session_id
                )
            else:
                # Check if we have context to suggest next actions
                if session.context.current_loan_number:
                    return ChatResponse(
                        message=f"You have loan {session.context.current_loan_number} ({session.context.current_borrower_name}) in context.\n\n"
                               f"You can:\n"
                               f"- 'Calculate payoff' - Calculate the current payoff amount\n"
                               f"- 'Generate PDF' - Create a payoff statement PDF\n"
                               f"- 'Clear session' - Start fresh with a new loan",
                        success=True,
                        session_id=session.session_id
                    )
                else:
                    return ChatResponse(
                        message="I'm not sure what you'd like me to do. Please ask me to:\n"
                               "- Look up loan information (by loan number or borrower name)\n"
                               "- Calculate a payoff amount\n"
                               "- Generate a payoff statement PDF\n\n"
                               "Examples:\n"
                               "- 'Show loan info for Mark Wilson'\n"
                               "- 'Calculate payoff for loan 69253358'\n"
                               "- 'Process complete payoff for 69253358' (does everything)",
                        success=True,
                        session_id=session.session_id
                    )
                
        except Exception as e:
            logger.error(f"Simplified execution failed: {str(e)}")
            
            # Provide user-friendly error messages
            error_msg = str(e).lower()
            if 'connection' in error_msg or 'network' in error_msg:
                message = "❌ **Connection Error**\n\n" \
                         "Unable to connect to the MiLA service. Please check:\n" \
                         "- The server is running\n" \
                         "- Your network connection is working\n" \
                         "- The server URL is correct"
            elif 'not found' in error_msg:
                message = f"❌ **Not Found**\n\n{str(e)}\n\n" \
                         "Please verify the loan number or borrower name and try again."
            elif 'session' in error_msg and 'expired' in error_msg:
                message = "❌ **Session Expired**\n\n" \
                         "Your session has expired. Click 'Clear Session' to start fresh."
            else:
                message = f"❌ **Error Processing Request**\n\n{str(e)}\n\n" \
                         "Please try again or click 'Clear Session' if the problem persists."
            
            return ChatResponse(
                message=message,
                success=False,
                error_message=str(e),
                session_id=session.session_id if session else None
            )
    
    async def _execute_as_chain(
        self, 
        message: str, 
        chain_template, 
        session: ChatSession
    ) -> ChatResponse:
        """Execute message as a tool chain."""
        try:
            # Extract parameters from the user message using LLM
            extracted_params = await self._extract_parameters_from_message(message, session.context)
            
            # Create chain plan with extracted parameters
            plan = tool_chain_engine.create_chain_plan(
                chain_template, 
                context=session.context.dict()
            )
            
            # Apply extracted parameters to the first step (typically get_loan_info)
            if extracted_params and plan.steps:
                for key, value in extracted_params.items():
                    plan.steps[0].parameters[key] = value
            
            # Update session with chain start
            await session_manager.start_chain_execution(session.session_id, plan.chain_id)
            
            # Execute chain
            session_context_dict = session.context.dict()
            logger.info(f"Chain execution session context: {session_context_dict}")
            chain_result = await tool_chain_engine.execute_chain(
                plan, 
                session_context=session_context_dict
            )
            
            # Update session with chain completion
            await session_manager.complete_chain_execution(
                session.session_id, 
                plan.chain_id, 
                chain_result.dict()
            )
            
            # Format response with chain results
            response_text = self._format_chain_response(chain_result, session.context.debug_mode)
            
            # Extract files and tool calls
            files_generated = []
            tool_calls = []
            
            for step in plan.steps:
                if step.result and step.result.success:
                    tool_calls.append(ToolCall(
                        tool_name=step.tool_name,
                        parameters=step.parameters,
                        result=step.result.result
                    ))
                    
                    # Extract PDF files
                    if step.tool_name == "generate_pdf" and step.result.result:
                        filename = step.result.result.get('filename')
                        if filename:
                            files_generated.append(filename)
            
            # Update session context from chain results
            await self._update_session_from_chain_result(session, chain_result)
            
            return ChatResponse(
                message=response_text,
                tool_calls=tool_calls,
                files_generated=files_generated,
                success=chain_result.success
            )
            
        except Exception as e:
            logger.error(f"Chain execution failed: {str(e)}")
            return ChatResponse(
                message=f"Chain execution failed: {str(e)}",
                success=False,
                error_message=str(e)
            )
    
    async def _execute_as_individual_tools(
        self, 
        message: str, 
        session: ChatSession
    ) -> ChatResponse:
        """Execute message as individual tools (original behavior)."""
        try:
            # Use the hardware-optimized model for processing
            ai_response = await self._call_ollama_api_with_context(message, session.context)
            
            # Parse tool calls from AI response
            tool_calls = self.parse_tool_calls(ai_response)
            
            # Execute tool sequence with session context
            tool_results = await self.execute_tool_sequence(tool_calls, session.context)
            
            # Update session context from tool results
            for result in tool_results:
                await session_manager.update_context_from_tool_result(
                    session.session_id, 
                    result.tool_name, 
                    result.dict()
                )
            
            # Format final response
            response_text = self.format_markdown_response(
                tool_results, 
                ai_response.get("message", {}).get("content", ""),
                debug_mode=session.context.debug_mode
            )
            
            # Extract generated files
            files_generated = []
            for result in tool_results:
                if result.tool_name == "generate_pdf" and result.success and result.result:
                    files_generated.append(result.result.get("filename", ""))
            
            # Update conversation history
            await session_manager.update_context_from_message(
                session.session_id,
                message,
                response_text
            )
            
            return ChatResponse(
                message=response_text,
                tool_calls=[ToolCall(tool_name=r.tool_name, parameters=r.parameters, result=r.result) for r in tool_results],
                files_generated=files_generated,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Individual tool execution failed: {str(e)}")
            return ChatResponse(
                message=f"I encountered an error processing your request: {str(e)}",
                success=False,
                error_message=str(e)
            )
    
    async def _extract_parameters_from_message(self, message: str, context: ContextData) -> Dict[str, Any]:
        """Extract parameters from user message for tool chain execution."""
        import re
        
        params = {}
        
        # Extract loan number patterns
        loan_patterns = [
            r'loan\s+(?:number\s+)?(\d{6,8})',  # "loan 69253358" or "loan number 69253358"
            r'(\d{6,8})',  # standalone numbers (6-8 digits)
        ]
        
        for pattern in loan_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                params['identifier'] = match.group(1)
                break
        
        # Extract borrower names (when no loan number found)
        if 'identifier' not in params:
            # Look for patterns like "for John Doe" or "for Mark Wilson"
            name_pattern = r'for\s+([A-Z][a-z]+\s+[A-Z][a-z]+)'
            match = re.search(name_pattern, message)
            if match:
                params['identifier'] = match.group(1)
        
        # If no explicit identifier found, try to use context
        if 'identifier' not in params and context.current_loan_number:
            params['identifier'] = context.current_loan_number
        
        logger.debug(f"Extracted parameters from '{message}': {params}")
        return params

    async def _call_ollama_api(self, message: str) -> Dict[str, Any]:
        """
        Call the Ollama API with function calling support.
        
        Args:
            message: User message to process
            
        Returns:
            Ollama API response
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload = {
                    "model": self.model_name,
                    "messages": [
                        {
                            "role": "system",
                            "content": self._build_system_prompt()
                        },
                        {
                            "role": "user",
                            "content": message
                        }
                    ],
                    "tools": list(self.available_tools.values()),
                    "temperature": self.temperature,
                    "stream": False
                }
                
                # Add max_tokens if supported by the model
                if self.max_tokens:
                    payload["options"] = {"num_predict": self.max_tokens}
                
                response = await client.post(
                    f"{self.ollama_base_url}/api/chat",
                    json=payload
                )
                response.raise_for_status()
                return response.json()
                
        except httpx.RequestError as e:
            logger.error(f"Error calling Ollama API: {str(e)}")
            raise AIOrchestrationError(f"Failed to connect to Ollama: {str(e)}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama API error: {e.response.status_code} - {e.response.text}")
            raise AIOrchestrationError(f"Ollama API error: {e.response.status_code}")

    def parse_tool_calls(self, ai_response: Dict[str, Any]) -> List[ToolCall]:
        """
        Parse tool calls from AI response.
        
        Args:
            ai_response: Response from Ollama API
            
        Returns:
            List of ToolCall objects
        """
        tool_calls = []
        
        try:
            logger.info(f"AI Response structure: {ai_response}")
            message = ai_response.get("message", {})
            logger.info(f"Message content: {message}")
            tool_calls_data = message.get("tool_calls", [])
            logger.info(f"Tool calls data: {tool_calls_data}")
            
            # If no tool_calls in message, try to parse from content
            if not tool_calls_data:
                content = message.get("content", "")
                logger.info(f"No tool_calls found, trying to parse from content: {content}")
                parsed_calls = self._parse_tool_calls_from_content(content)
                if parsed_calls:
                    tool_calls_data = parsed_calls
                    logger.info(f"Parsed tool calls from content: {tool_calls_data}")
            
            for tool_call_data in tool_calls_data:
                function_data = tool_call_data.get("function", {})
                tool_name = function_data.get("name", "")
                
                # Parse parameters
                parameters = {}
                if "arguments" in function_data:
                    if isinstance(function_data["arguments"], str):
                        parameters = json.loads(function_data["arguments"])
                    else:
                        parameters = function_data["arguments"]
                
                tool_calls.append(ToolCall(
                    tool_name=tool_name,
                    parameters=parameters
                ))
                
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error parsing tool calls: {str(e)}")
            logger.error(f"Full AI response: {ai_response}")
            
        logger.info(f"Parsed {len(tool_calls)} tool calls")
        return tool_calls

    def _parse_tool_calls_from_content(self, content: str) -> List[Dict[str, Any]]:
        """
        Parse tool calls from content text when model doesn't use proper tool_calls format.
        
        Args:
            content: Message content that may contain JSON function calls
            
        Returns:
            List of tool call dictionaries
        """
        tool_calls = []
        
        try:
            # Look for JSON blocks in content
            import re
            
            # Extract JSON from code blocks
            json_pattern = r'```(?:json)?\s*\n({[^`]+})\s*\n```'
            matches = re.findall(json_pattern, content, re.DOTALL)
            
            for match in matches:
                try:
                    parsed_json = json.loads(match.strip())
                    if "name" in parsed_json:
                        # Convert to expected format
                        tool_call = {
                            "function": {
                                "name": parsed_json["name"],
                                "arguments": parsed_json.get("arguments", {})
                            }
                        }
                        tool_calls.append(tool_call)
                        logger.info(f"Extracted tool call from content: {tool_call}")
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSON from content: {e}")
                    
            # Also try to parse direct JSON (no code blocks)
            if not tool_calls:
                try:
                    # Try parsing entire content as JSON
                    parsed_json = json.loads(content.strip())
                    if "name" in parsed_json:
                        tool_call = {
                            "function": {
                                "name": parsed_json["name"],
                                "arguments": parsed_json.get("arguments", {})
                            }
                        }
                        tool_calls.append(tool_call)
                        logger.info(f"Parsed entire content as tool call: {tool_call}")
                except json.JSONDecodeError:
                    logger.info("Content is not valid JSON")
                    
        except Exception as e:
            logger.error(f"Error parsing tool calls from content: {e}")
            
        return tool_calls

    async def execute_tool_sequence(self, tool_calls: List[ToolCall], session_context: Optional[ContextData] = None) -> List[ToolResult]:
        """
        Execute a sequence of tool calls.
        
        Args:
            tool_calls: List of tool calls to execute
            
        Returns:
            List of ToolResult objects
        """
        results = []
        
        for tool_call in tool_calls:
            try:
                # Add session context to tool parameters
                if session_context:
                    tool_call.parameters["session_context"] = session_context.dict()
                result = await self._execute_single_tool(tool_call)
                results.append(result)
                
            except Exception as e:
                logger.error(f"Error executing tool {tool_call.tool_name}: {str(e)}")
                results.append(ToolResult(
                    tool_name=tool_call.tool_name,
                    parameters=tool_call.parameters,
                    success=False,
                    error_message=str(e)
                ))
                
        return results

    async def _execute_single_tool(self, tool_call: ToolCall) -> ToolResult:
        """
        Execute a single tool call.
        
        Args:
            tool_call: Tool call to execute
            
        Returns:
            ToolResult with execution results
        """
        tool_name = tool_call.tool_name
        parameters = tool_call.parameters
        
        if tool_name == "get_loan_info":
            return await self._execute_get_loan_info(parameters)
        elif tool_name == "calculate_payoff":
            return await self._execute_calculate_payoff(parameters)
        elif tool_name == "generate_pdf":
            return await self._execute_generate_pdf(parameters)
        else:
            raise AIOrchestrationError(f"Unknown tool: {tool_name}")

    async def _execute_get_loan_info(self, parameters: Dict[str, Any]) -> ToolResult:
        """Execute get_loan_info tool."""
        try:
            identifier = parameters.get("identifier", "")
            
            # If no identifier provided, try to use current loan from context
            if not identifier or identifier.lower() in ["this", "current", "the loan", "this loan"]:
                current_loan_number = parameters.get("current_loan_number")
                if current_loan_number:
                    identifier = current_loan_number
                    logger.info(f"Using loan number from context: {identifier}")
                elif not identifier:
                    return ToolResult(
                        tool_name="get_loan_info",
                        parameters=parameters,
                        success=False,
                        error_message="No loan identifier provided and no current loan in context. Please specify a loan number or borrower name."
                    )
            
            loan_record = await loan_data_access.find_loan_by_identifier(identifier)
            
            if not loan_record:
                return ToolResult(
                    tool_name="get_loan_info",
                    parameters=parameters,
                    success=False,
                    error_message=f"Loan not found: {identifier}"
                )
            
            result_data = {
                "loan_number": loan_record.loan_number,
                "borrower_name": loan_record.borrower_name,
                "principal_balance": float(loan_record.principal_balance),
                "annual_interest_rate": float(loan_record.annual_interest_rate),
                "last_payment_date": loan_record.last_payment_date.isoformat()
            }
            
            # Add email address if available
            if loan_record.email_address:
                result_data["email_address"] = loan_record.email_address
            
            return ToolResult(
                tool_name="get_loan_info",
                parameters=parameters,
                success=True,
                result=result_data
            )
            
        except DataAccessError as e:
            return ToolResult(
                tool_name="get_loan_info",
                parameters=parameters,
                success=False,
                error_message=str(e)
            )

    async def _execute_calculate_payoff(self, parameters: Dict[str, Any]) -> ToolResult:
        """Execute calculate_payoff tool."""
        try:
            loan_number = parameters.get("loan_number", "")
            as_of_date_str = parameters.get("as_of_date")
            
            # If no loan number provided or it's a contextual reference, use current context
            if not loan_number or loan_number.lower() in ["this", "current", "the loan", "this loan"]:
                # Try to get from current session context (for individual tool execution)
                session_context = parameters.get("session_context")
                if session_context and session_context.get("current_loan_number"):
                    loan_number = session_context["current_loan_number"]
                # Try to get from chain context (for chain execution)
                elif parameters.get("current_loan_number"):
                    loan_number = parameters["current_loan_number"]
                elif not loan_number:
                    return ToolResult(
                        tool_name="calculate_payoff",
                        parameters=parameters,
                        success=False,
                        error_message="No loan number provided and no current loan in context"
                    )
            
            # Parse date if provided
            as_of_date = None
            if as_of_date_str:
                as_of_date = date.fromisoformat(as_of_date_str)
            
            # Get loan record
            loan_record = await loan_data_access.find_loan_by_number(loan_number)
            if not loan_record:
                return ToolResult(
                    tool_name="calculate_payoff",
                    parameters=parameters,
                    success=False,
                    error_message=f"Loan not found: {loan_number}"
                )
            
            # Calculate payoff
            payoff_calculation = payoff_calculator.calculate_payoff(loan_record, as_of_date)
            
            return ToolResult(
                tool_name="calculate_payoff",
                parameters=parameters,
                success=True,
                result={
                    "loan_number": loan_number,
                    "principal_balance": float(payoff_calculation.principal_balance),
                    "interest_accrued": float(payoff_calculation.interest_accrued),
                    "total_payoff": float(payoff_calculation.total_payoff),
                    "calculation_date": payoff_calculation.calculation_date.isoformat(),
                    "good_through_date": payoff_calculation.good_through_date.isoformat(),
                    "days_since_payment": payoff_calculation.days_since_payment
                }
            )
            
        except CalculationError as e:
            return ToolResult(
                tool_name="calculate_payoff",
                parameters=parameters,
                success=False,
                error_message=str(e)
            )

    async def _execute_generate_pdf(self, parameters: Dict[str, Any]) -> ToolResult:
        """Execute generate_pdf tool."""
        try:
            loan_number = parameters.get("loan_number", "")
            statement_date_str = parameters.get("statement_date")
            
            logger.debug(f"PDF generation parameters: {list(parameters.keys())}")
            logger.debug(f"Initial loan_number: '{loan_number}'")
            
            # If no loan number provided or it's a contextual reference, use current context
            if not loan_number or loan_number.lower() in ["this", "current", "the loan", "this loan"]:
                # Try to get from current session context (for individual tool execution)
                session_context = parameters.get("session_context")
                if session_context and session_context.get("current_loan_number"):
                    loan_number = session_context["current_loan_number"]
                    logger.info(f"Using loan number from session context: {loan_number}")
                # Try to get from chain context (for chain execution)
                elif parameters.get("current_loan_number"):
                    loan_number = parameters["current_loan_number"]
                    logger.info(f"Using loan number from chain context: {loan_number}")
                else:
                    # Log available context for debugging
                    logger.warning(f"No loan number found in context. Available parameters: {list(parameters.keys())}")
                    logger.warning(f"Session context keys: {list(session_context.keys()) if session_context else 'None'}")
                    return ToolResult(
                        tool_name="generate_pdf",
                        parameters=parameters,
                        success=False,
                        error_message="No loan number provided and no current loan in context. Please specify a loan number or calculate payoff first."
                    )
            
            # Parse date if provided
            statement_date = None
            if statement_date_str:
                statement_date = date.fromisoformat(statement_date_str)
            
            # Get loan record
            loan_record = await loan_data_access.find_loan_by_number(loan_number)
            if not loan_record:
                return ToolResult(
                    tool_name="generate_pdf",
                    parameters=parameters,
                    success=False,
                    error_message=f"Loan not found: {loan_number}"
                )
            
            # Calculate payoff for PDF
            payoff_calculation = payoff_calculator.calculate_payoff(loan_record, statement_date)
            
            # Generate PDF
            pdf_path = pdf_generator.generate_payoff_statement(
                loan_record, 
                payoff_calculation, 
                statement_date
            )
            
            # Extract filename and create download URL
            from pathlib import Path
            filename = Path(pdf_path).name
            download_url = f"/api/files/{filename}"
            
            return ToolResult(
                tool_name="generate_pdf",
                parameters=parameters,
                success=True,
                result={
                    "loan_number": loan_number,
                    "filename": filename,
                    "download_url": download_url,
                    "file_path": pdf_path
                }
            )
            
        except (CalculationError, PDFGenerationError) as e:
            return ToolResult(
                tool_name="generate_pdf",
                parameters=parameters,
                success=False,
                error_message=str(e)
            )

    def format_markdown_response(self, results: List[ToolResult], ai_message: str = "", debug_mode: bool = False) -> str:
        """
        Format tool results into a markdown response.
        
        Args:
            results: List of tool execution results
            ai_message: Original AI response message
            debug_mode: Whether to include debug information
            
        Returns:
            Formatted markdown string
        """
        if not results:
            return ai_message or "I couldn't process your request. Please try again."
        
        response_parts = []
        
        # Add AI message if available (only in debug mode to hide JSON responses)
        if debug_mode and ai_message and ai_message.strip():
            response_parts.append(ai_message.strip())
        
        # Process each tool result
        for result in results:
            if not result.success:
                response_parts.append(f"❌ **Error in {result.tool_name}**: {result.error_message}")
                continue
                
            if result.tool_name == "get_loan_info" and result.result:
                loan_data = result.result
                response_parts.append(
                    f"## 📋 Loan Information\n\n"
                    f"**Loan Number:** {loan_data['loan_number']}\n"
                    f"**Borrower:** {loan_data['borrower_name']}\n"
                    f"**Principal Balance:** ${loan_data['principal_balance']:,.2f}\n"
                    f"**Interest Rate:** {loan_data['annual_interest_rate']:.2f}%\n"
                    f"**Last Payment:** {loan_data['last_payment_date']}"
                )
                
            elif result.tool_name == "calculate_payoff" and result.result:
                calc_data = result.result
                response_parts.append(
                    f"## 💰 Payoff Calculation\n\n"
                    f"**Principal Balance:** ${calc_data['principal_balance']:,.2f}\n"
                    f"**Interest Accrued:** ${calc_data['interest_accrued']:,.2f}\n"
                    f"**Total Payoff Amount:** ${calc_data['total_payoff']:,.2f}\n"
                    f"**Calculation Date:** {calc_data['calculation_date']}\n"
                    f"**Good Through Date:** {calc_data.get('good_through_date', 'N/A')}\n"
                    f"**Days Since Last Payment:** {calc_data['days_since_payment']}"
                )
                
            elif result.tool_name == "generate_pdf" and result.result:
                pdf_data = result.result
                # Create full download URL
                full_download_url = f"{self.server_base_url}{pdf_data['download_url']}"
                response_parts.append(
                    f"## 📄 PDF Generated\n\n"
                    f"**Filename:** {pdf_data['filename']}\n"
                    f"**Download:** [Click here to download]({full_download_url})\n\n"
                    f"✅ Payoff statement PDF has been generated successfully!"
                )
        
        return "\n\n".join(response_parts) if response_parts else "Request completed successfully."
    
    async def _call_ollama_api_with_context(self, message: str, context: ContextData) -> Dict[str, Any]:
        """Call Ollama API with session context."""
        try:
            # Build context-aware system prompt
            system_prompt = self._build_system_prompt()
            
            # Add context information to the prompt
            if context.has_loan_context():
                context_info = f"\n\nCurrent Context:\n"
                context_info += f"- Current Loan: {context.current_loan_number} ({context.current_borrower_name})\n"
                if context.current_payoff_data:
                    context_info += f"- Last Payoff: ${context.current_payoff_data.get('total_payoff', 0):,.2f}\n"
                if context.generated_pdf_filename:
                    context_info += f"- Generated PDF: {context.generated_pdf_filename}\n"
                if context.borrower_email:
                    context_info += f"- Email on file: {context.borrower_email}\n"
                
                system_prompt += context_info
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload = {
                    "model": self.model_name,
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt
                        },
                        {
                            "role": "user",
                            "content": message
                        }
                    ],
                    "tools": list(self.available_tools.values()),
                    "temperature": self.temperature,
                    "stream": False
                }
                
                if self.max_tokens:
                    payload["options"] = {"num_predict": self.max_tokens}
                
                response = await client.post(
                    f"{self.ollama_base_url}/api/chat",
                    json=payload
                )
                response.raise_for_status()
                return response.json()
                
        except httpx.RequestError as e:
            logger.error(f"Error calling Ollama API with context: {str(e)}")
            raise AIOrchestrationError(f"Failed to connect to Ollama: {str(e)}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama API error with context: {e.response.status_code} - {e.response.text}")
            raise AIOrchestrationError(f"Ollama API error: {e.response.status_code}")
    
    def _format_chain_response(self, chain_result: ChainExecutionResult, debug_mode: bool = False) -> str:
        """Format chain execution result into markdown response."""
        response_parts = []
        
        # Always show debug info for now to diagnose the issue
        logger.info(f"Formatting chain response. Success: {chain_result.success}, Steps: {len(chain_result.plan.steps)}")
        
        if debug_mode:
            # Add chain execution debug info
            response_parts.append(f"🔧 **Chain Execution: {chain_result.plan.description}**")
            response_parts.append(f"⏱️ **Total Time:** {chain_result.total_execution_time_ms}ms")
            response_parts.append(f"✅ **Success:** {chain_result.success}")
            response_parts.append("")
        
        # Add step-by-step results
        for step in chain_result.plan.steps:
            # Log step details for debugging
            logger.info(f"Processing step {step.step_number}: {step.tool_name}, status: {step.status.value}, has_result: {bool(step.result)}, success: {step.result.success if step.result else 'N/A'}")
            if step.result:
                logger.info(f"Step result data: {step.result.result if hasattr(step.result, 'result') else 'No result attribute'}")
            
            if debug_mode:
                status_emoji = "✅" if step.status.value == "completed" else "❌" if step.status.value == "failed" else "⏳"
                response_parts.append(f"{status_emoji} **Step {step.step_number}/{chain_result.plan.total_steps}:** {step.tool_name}")
                if step.execution_time_ms:
                    response_parts.append(f"   ⏱️ {step.execution_time_ms}ms")
            
            # Check if step completed successfully and has result
            if step.status.value == "completed" and step.result:
                # Get the result data - handle different result formats
                result_data = None
                if hasattr(step.result, 'result'):
                    result_data = step.result.result
                elif isinstance(step.result, dict):
                    result_data = step.result
                
                if result_data:
                    if step.tool_name == "get_loan_info":
                        response_parts.append(
                            f"## 📋 Loan Information\n\n"
                            f"**Loan Number:** {result_data.get('loan_number')}\n"
                            f"**Borrower:** {result_data.get('borrower_name')}\n"
                            f"**Principal Balance:** ${result_data.get('principal_balance', 0):,.2f}\n"
                            f"**Interest Rate:** {result_data.get('annual_interest_rate', 0):.2f}%\n"
                            f"**Last Payment:** {result_data.get('last_payment_date')}"
                        )
                    elif step.tool_name == "calculate_payoff":
                        response_parts.append(
                            f"## 💰 Payoff Calculation\n\n"
                            f"**Principal Balance:** ${result_data.get('principal_balance', 0):,.2f}\n"
                            f"**Interest Accrued:** ${result_data.get('interest_accrued', 0):,.2f}\n"
                            f"**Total Payoff Amount:** ${result_data.get('total_payoff', 0):,.2f}\n"
                            f"**Calculation Date:** {result_data.get('calculation_date')}\n"
                            f"**Good Through Date:** {result_data.get('good_through_date', 'N/A')}\n"
                            f"**Days Since Last Payment:** {result_data.get('days_since_payment')}"
                        )
                    elif step.tool_name == "generate_pdf":
                        # Create full download URL
                        full_download_url = f"{self.server_base_url}{result_data.get('download_url')}"
                        response_parts.append(
                            f"## 📄 PDF Generated\n\n"
                            f"**Filename:** {result_data.get('filename')}\n"
                            f"**Download:** [Click here to download]({full_download_url})\n\n"
                            f"✅ Payoff statement PDF has been generated successfully!"
                        )
                    elif step.tool_name == "send_email":
                        response_parts.append(
                            f"## 📧 Email Sent\n\n"
                            f"**To:** {result_data.get('to_address')}\n"
                            f"**Subject:** {result_data.get('subject')}\n"
                            f"**Sent At:** {result_data.get('sent_at')}\n\n"
                            f"✅ Email sent successfully!"
                        )
                    else:
                        # Generic result display for unknown tools
                        response_parts.append(f"## Tool: {step.tool_name}\n\nResult: {result_data}")
            elif step.status.value == "failed":
                response_parts.append(f"❌ **Error in {step.tool_name}:** {step.error_message}")
        
        if not response_parts:
            logger.warning(f"No response parts generated for chain {chain_result.plan.chain_id}")
            logger.warning(f"Chain steps details:")
            for step in chain_result.plan.steps:
                logger.warning(f"  - {step.tool_name}: status={step.status.value}, has_result={bool(step.result)}, result={step.result}")
            
            # Return a more informative message when debugging
            return f"Chain completed but no results were formatted. Check logs for details. Chain ID: {chain_result.plan.chain_id}"
        
        return "\n\n".join(response_parts)
    
    async def _update_session_from_chain_result(self, session: ChatSession, chain_result: ChainExecutionResult):
        """Update session context from chain execution results."""
        for step in chain_result.plan.steps:
            if step.result and step.result.success:
                await session_manager.update_context_from_tool_result(
                    session.session_id,
                    step.tool_name,
                    step.result.dict()
                )
    
    async def _execute_send_email(self, parameters: Dict[str, Any]) -> ToolResult:
        """Execute send_email tool."""
        try:
            email_address = parameters.get("email_address")
            loan_number = parameters.get("loan_number")
            
            # Get context data
            current_loan_data = parameters.get("current_loan_data", {})
            current_payoff_data = parameters.get("current_payoff_data", {})
            generated_pdf_filename = parameters.get("generated_pdf_filename")
            
            # Use email from context if not provided
            if not email_address:
                email_address = await email_service.get_borrower_email(current_loan_data)
                if not email_address:
                    return ToolResult(
                        tool_name="send_email",
                        parameters=parameters,
                        success=False,
                        error_message="No email address available for borrower"
                    )
            
            # Send email
            result = await email_service.send_payoff_statement(
                email_address,
                current_loan_data.get('loan_number', loan_number),
                current_loan_data.get('borrower_name', 'Borrower'),
                current_payoff_data.get('total_payoff', 0),
                generated_pdf_filename
            )
            
            return ToolResult(
                tool_name="send_email",
                parameters=parameters,
                success=True,
                result={'data': result}
            )
            
        except EmailSimulationError as e:
            return ToolResult(
                tool_name="send_email",
                parameters=parameters,
                success=False,
                error_message=str(e)
            )
    
    async def _execute_confirm_email(self, parameters: Dict[str, Any]) -> ToolResult:
        """Execute confirm_email tool."""
        try:
            email_address = parameters.get("email_address")
            context_data = ContextData(**{k: v for k, v in parameters.items() if k != "email_address"})
            
            confirmation_message = await email_service.confirm_email_send(email_address, context_data)
            
            return ToolResult(
                tool_name="confirm_email",
                parameters=parameters,
                success=True,
                result={
                    'data': {
                        'confirmation_message': confirmation_message,
                        'email_address': email_address,
                        'requires_user_response': True
                    }
                }
            )
            
        except Exception as e:
            return ToolResult(
                tool_name="confirm_email", 
                parameters=parameters,
                success=False,
                error_message=str(e)
            )


# Create singleton instance - will be initialized lazily
ai_orchestrator = None

def get_ai_orchestrator() -> AIOrchestrator:
    """Get or create the AI orchestrator singleton."""
    global ai_orchestrator
    if ai_orchestrator is None:
        ai_orchestrator = AIOrchestrator()
    return ai_orchestrator