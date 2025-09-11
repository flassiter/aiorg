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
from ..components.session_manager import session_manager, SessionManager
from ..models.session import ChatSession, ContextData
from ..tools.loan_service import find_loan, LoanServiceError
from ..tools.calculation_service import calculate_payoff as calc_payoff, CalculationServiceError
from ..tools.pdf_service import generate_pdf as gen_pdf, PDFServiceError
from ..tools.email_service import send_payoff_email, confirm_email_send, EmailServiceError
from ..tools.biweekly_service import calculate_biweekly_payoff as calc_biweekly, BiweeklyServiceError

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
        
        # Setup tools
        self._setup_tools()

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
                    "description": "Send payoff information via email to borrower (ONLY use after confirm_email and user approval)",
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
            },
            "calculate_biweekly_payoff": {
                "type": "function",
                "function": {
                    "name": "calculate_biweekly_payoff",
                    "description": "Calculate bi-weekly payment scenario showing time and interest savings compared to monthly payments",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "loan_identifier": {
                                "type": "string",
                                "description": "Loan number or borrower name (optional if using current loan context)"
                            }
                        },
                        "required": []
                    }
                }
            }
        }
    

    def _build_system_prompt(self) -> str:
        """Build the system prompt for the AI model."""
        return """You are MiLA (Machine Intelligence Loan Assistant), an AI assistant specialized in loan processing and payoff calculations.

You have access to the following tools:
1. get_loan_info(identifier) - Search by loan number or borrower name
2. calculate_payoff(loan_number, as_of_date=today) - Calculate current payoff amount  
3. generate_pdf(loan_number, statement_date=today) - Create payoff statement PDF
4. confirm_email(email_address) - ALWAYS use this first to confirm before sending emails
5. send_email(email_address, loan_number) - Send payoff information via email (ONLY after confirmation)
6. calculate_biweekly_payoff(loan_identifier) - Calculate bi-weekly payment scenario with time and interest savings

Response Guidelines:
- Use tools when you need to retrieve, calculate, or generate new information
- Answer directly from context when you already have the information
- For simple questions about current loan details (like "what email address is on that loan"), respond directly if you have the information in context
- Always search for loan information first when given a name or loan number
- Use exact loan numbers when available from context
- When users refer to "this loan", "the loan", or "current loan", use the loan number from the current context

Email Confirmation Rules:
- ALWAYS use confirm_email() before send_email() - never send emails without confirmation
- When user requests to send an email, first call confirm_email() with the recipient address
- Only proceed with send_email() after user confirms with "Y" or "Yes"
- If user responds "N" or "No" to confirmation, do not send the email

Tool Usage Examples:
- "Show me loan information for Mark Wilson" → get_loan_info("Mark Wilson")
- "Calculate payoff for loan 69253358" → get_loan_info("69253358") → calculate_payoff()
- "Calculate payoff for this loan" → calculate_payoff() (using current loan from context)
- "Process complete payoff for John Doe" → get_loan_info("John Doe") → calculate_payoff() → generate_pdf()
- "What if John Doe switched to bi-weekly payments?" → get_loan_info("John Doe") → calculate_biweekly_payoff()
- "Email payoff statement to borrower" → confirm_email() → (wait for Y/N) → send_email()
- "Calculate bi-weekly scenario for loan 69253358 and email results" → get_loan_info("69253358") → calculate_biweekly_payoff() → confirm_email() → (wait for Y/N) → send_email()

Direct Response Examples:
- "What email address is on that loan?" → Answer directly if you have the borrower email in context
- "What's the borrower's name?" → Answer directly if you have the loan information in context
- "What loan number are we working with?" → Answer directly if you have the current loan number in context

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
        Process a user message with AI orchestration and session support.
        
        Args:
            message: User's natural language request
            session_id: Optional session ID for context
            
        Returns:
            ChatResponse with results and any generated files
        """
        try:
            # Get or create session
            session = await session_manager.get_or_create_session(session_id)
            
            # Use AI orchestration to let the model decide which tools to call
            return await self._execute_as_individual_tools(message, session)
            
        except Exception as e:
            logger.error(f"Error processing user message: {str(e)}")
            return ChatResponse(
                message=f"I encountered an error processing your request: {str(e)}",
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
            
            # Check if AI provided a direct response without tools
            ai_content = ai_response.get("message", {}).get("content", "")
            if not tool_calls and ai_content.strip():
                # AI answered from context without needing tools
                await session_manager.update_context_from_message(
                    session.session_id,
                    message,
                    ai_content.strip()
                )
                
                return ChatResponse(
                    message=ai_content.strip(),
                    tool_calls=[],
                    files_generated=[],
                    success=True,
                    session_id=session.session_id
                )
            
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
                ai_content,
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
                success=True,
                session_id=session.session_id
            )
            
        except Exception as e:
            logger.error(f"Individual tool execution failed: {str(e)}")
            return ChatResponse(
                message=f"I encountered an error processing your request: {str(e)}",
                success=False,
                error_message=str(e),
                session_id=session.session_id
            )
    

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
        elif tool_name == "send_email":
            return await self._execute_send_email(parameters)
        elif tool_name == "confirm_email":
            return await self._execute_confirm_email(parameters)
        elif tool_name == "calculate_biweekly_payoff":
            return await self._execute_calculate_biweekly_payoff(parameters)
        else:
            raise AIOrchestrationError(f"Unknown tool: {tool_name}")

    async def _execute_get_loan_info(self, parameters: Dict[str, Any]) -> ToolResult:
        """Execute get_loan_info tool."""
        try:
            identifier = parameters.get("identifier", "")
            current_loan_number = parameters.get("current_loan_number")
            
            result_data = await find_loan(identifier, current_loan_number)
            
            return ToolResult(
                tool_name="get_loan_info",
                parameters=parameters,
                success=True,
                result=result_data
            )
            
        except LoanServiceError as e:
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
            
            # Get current loan number from context if needed
            current_loan_number = None
            session_context = parameters.get("session_context")
            if session_context and session_context.get("current_loan_number"):
                current_loan_number = session_context["current_loan_number"]
            elif parameters.get("current_loan_number"):
                current_loan_number = parameters["current_loan_number"]
            
            # Parse date if provided
            as_of_date = None
            if as_of_date_str:
                as_of_date = date.fromisoformat(as_of_date_str)
            
            result_data = await calc_payoff(loan_number, as_of_date, current_loan_number)
            
            return ToolResult(
                tool_name="calculate_payoff",
                parameters=parameters,
                success=True,
                result=result_data
            )
            
        except CalculationServiceError as e:
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
            
            # Get current loan number from context if needed
            current_loan_number = None
            session_context = parameters.get("session_context")
            if session_context and session_context.get("current_loan_number"):
                current_loan_number = session_context["current_loan_number"]
            elif parameters.get("current_loan_number"):
                current_loan_number = parameters["current_loan_number"]
            
            # Parse date if provided
            statement_date = None
            if statement_date_str:
                statement_date = date.fromisoformat(statement_date_str)
            
            result_data = await gen_pdf(
                loan_number, 
                statement_date, 
                current_loan_number, 
                self.server_base_url
            )
            
            return ToolResult(
                tool_name="generate_pdf",
                parameters=parameters,
                success=True,
                result=result_data
            )
            
        except PDFServiceError as e:
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
                response_parts.append(f"**Error in {result.tool_name}**: {result.error_message}")
                continue
                
            if result.tool_name == "get_loan_info" and result.result:
                loan_data = result.result
                response_parts.append(
                    f"## Loan Information\n\n"
                    f"**Loan Number:** {loan_data['loan_number']}\n"
                    f"**Borrower:** {loan_data['borrower_name']}\n"
                    f"**Principal Balance:** ${loan_data['principal_balance']:,.2f}\n"
                    f"**Interest Rate:** {loan_data['annual_interest_rate']:.2f}%\n"
                    f"**Last Payment:** {loan_data['last_payment_date']}"
                )
                
            elif result.tool_name == "calculate_payoff" and result.result:
                calc_data = result.result
                response_parts.append(
                    f"## Payoff Calculation\n\n"
                    f"**Principal Balance:** ${calc_data['principal_balance']:,.2f}\n"
                    f"**Interest Accrued:** ${calc_data['interest_accrued']:,.2f}\n"
                    f"**Total Payoff Amount:** ${calc_data['total_payoff']:,.2f}\n"
                    f"**Calculation Date:** {calc_data['calculation_date']}\n"
                    f"**Good Through Date:** {calc_data.get('good_through_date', 'N/A')}\n"
                    f"**Days Since Last Payment:** {calc_data['days_since_payment']}"
                )
                
            elif result.tool_name == "calculate_biweekly_payoff" and result.result:
                biweekly_data = result.result
                response_parts.append(
                    f"## Bi-Weekly Payment Analysis\n\n"
                    f"**Current Monthly Payment:** ${biweekly_data['current_monthly_payment']:,.2f}\n"
                    f"**Proposed Bi-Weekly Payment:** ${biweekly_data['biweekly_payment_amount']:,.2f}\n\n"
                    f"**Current Payoff Date:** {biweekly_data['current_payoff_date']}\n"
                    f"**Bi-Weekly Payoff Date:** {biweekly_data['biweekly_payoff_date']}\n\n"
                    f"**Time Savings:** {biweekly_data['time_savings_months']} months\n"
                    f"**Interest Savings:** ${biweekly_data['interest_savings_dollars']:,.2f}\n\n"
                    f"*By switching to bi-weekly payments, you could save {biweekly_data['time_savings_months']} months and ${biweekly_data['interest_savings_dollars']:,.2f} in interest!*"
                )
                
            elif result.tool_name == "generate_pdf" and result.result:
                pdf_data = result.result
                # Create full download URL
                full_download_url = f"{self.server_base_url}{pdf_data['download_url']}"
                response_parts.append(
                    f"## PDF Generated\n\n"
                    f"**Filename:** {pdf_data['filename']}\n"
                    f"**Download:** [Click here to download]({full_download_url})\n\n"
                    f"Payoff statement PDF has been generated successfully!"
                )
                
            elif result.tool_name == "confirm_email" and result.result:
                email_data = result.result.get('data', {})
                confirmation_msg = email_data.get('confirmation_message', '')
                email_address = email_data.get('email_address', '')
                
                if confirmation_msg:
                    response_parts.append(f"## Email Confirmation\n\n{confirmation_msg}")
                else:
                    # Fallback formatting if confirmation_message is not available
                    response_parts.append(f"## Email Confirmation\n\nSend email to {email_address} (Y/N)?")
                    
            elif result.tool_name == "send_email" and result.result:
                email_data = result.result.get('data', {})
                response_parts.append(
                    f"## Email Sent\n\n"
                    f"Email has been sent successfully!"
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
    
    
    async def _execute_send_email(self, parameters: Dict[str, Any]) -> ToolResult:
        """Execute send_email tool."""
        try:
            email_address = parameters.get("email_address")
            loan_number = parameters.get("loan_number")
            current_loan_data = parameters.get("current_loan_data", {})
            current_payoff_data = parameters.get("current_payoff_data", {})
            generated_pdf_filename = parameters.get("generated_pdf_filename")
            
            result_data = await send_payoff_email(
                email_address,
                loan_number,
                current_loan_data,
                current_payoff_data,
                generated_pdf_filename
            )
            
            return ToolResult(
                tool_name="send_email",
                parameters=parameters,
                success=True,
                result=result_data
            )
            
        except EmailServiceError as e:
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
            
            result_data = await confirm_email_send(email_address, context_data)
            
            return ToolResult(
                tool_name="confirm_email",
                parameters=parameters,
                success=True,
                result=result_data
            )
            
        except EmailServiceError as e:
            return ToolResult(
                tool_name="confirm_email", 
                parameters=parameters,
                success=False,
                error_message=str(e)
            )

    async def _execute_calculate_biweekly_payoff(self, parameters: Dict[str, Any]) -> ToolResult:
        """Execute calculate_biweekly_payoff tool."""
        try:
            loan_identifier = parameters.get("loan_identifier", "")
            
            # Get current loan data from context if no identifier provided
            current_loan_data = None
            session_context = parameters.get("session_context")
            if session_context and session_context.get("current_loan_data"):
                current_loan_data = session_context["current_loan_data"]
            
            # If no identifier and no context data, use current loan number from context
            if not loan_identifier and session_context and session_context.get("current_loan_number"):
                loan_identifier = session_context["current_loan_number"]
            
            result_data = await calc_biweekly(
                loan_identifier=loan_identifier if loan_identifier else None,
                loan_data=current_loan_data
            )
            
            return ToolResult(
                tool_name="calculate_biweekly_payoff",
                parameters=parameters,
                success=True,
                result=result_data
            )
            
        except BiweeklyServiceError as e:
            return ToolResult(
                tool_name="calculate_biweekly_payoff",
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