"""
API tools endpoints for loan payoff calculations.
"""
import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from .auth import require_agent_or_above
from ..components.data_access import loan_data_access, DataAccessError
from ..components.calculator import payoff_calculator, CalculationError
from ..models.payoff import PayoffCalculationRequest, PayoffCalculationResponse

logger = logging.getLogger(__name__)

# Create router for tools endpoints
router = APIRouter(prefix="/api", tags=["tools"])


@router.post("/calculate-payoff", response_model=PayoffCalculationResponse)
async def calculate_payoff(
    calculation_request: PayoffCalculationRequest,
    current_user: dict = Depends(require_agent_or_above)
):
    """
    Calculate payoff amount for a loan.
    
    Accepts loan data and returns payoff calculation with:
    - Principal balance
    - Interest accrued since last payment
    - Total payoff amount
    - Calculation date
    - Days since last payment
    
    Args:
        calculation_request: Request containing loan number and optional calculation date
        current_user: Current authenticated user
        
    Returns:
        PayoffCalculationResponse with calculation results
    """
    logger.info(f"Payoff calculation request for loan {calculation_request.loan_number} "
               f"by user: {current_user['username']}")
    
    try:
        # Check if loan data is loaded
        if not loan_data_access.is_data_loaded():
            logger.error("Loan data not loaded")
            return PayoffCalculationResponse(
                success=False,
                message="Loan data not loaded. Please contact administrator.",
                data=None
            )
        
        # Find the loan record
        loan_record = await loan_data_access.find_loan_by_number(calculation_request.loan_number)
        
        if not loan_record:
            logger.info(f"Loan not found: {calculation_request.loan_number}")
            return PayoffCalculationResponse(
                success=False,
                message=f"Loan not found: {calculation_request.loan_number}",
                data=None
            )
        
        # Validate calculation inputs
        payoff_calculator.validate_calculation_inputs(loan_record, calculation_request.as_of_date)
        
        # Calculate payoff
        payoff_calculation = payoff_calculator.calculate_payoff(
            loan_record, 
            calculation_request.as_of_date
        )
        
        logger.info(f"Payoff calculation completed for loan {calculation_request.loan_number}: "
                   f"principal=${payoff_calculation.principal_balance}, "
                   f"interest=${payoff_calculation.interest_accrued}, "
                   f"total=${payoff_calculation.total_payoff}")
        
        return PayoffCalculationResponse(
            success=True,
            message=f"Payoff calculation completed for loan {calculation_request.loan_number}",
            data=payoff_calculation
        )
        
    except CalculationError as e:
        logger.error(f"Calculation error for loan {calculation_request.loan_number}: {str(e)}")
        return PayoffCalculationResponse(
            success=False,
            message=f"Calculation error: {str(e)}",
            data=None
        )
        
    except DataAccessError as e:
        logger.error(f"Data access error during payoff calculation: {str(e)}")
        return PayoffCalculationResponse(
            success=False,
            message=f"Data access error: {str(e)}",
            data=None
        )
        
    except Exception as e:
        logger.error(f"Unexpected error during payoff calculation: {str(e)}")
        return PayoffCalculationResponse(
            success=False,
            message="Internal server error during calculation",
            data=None
        )


@router.get("/calculate-payoff/{loan_number}", response_model=PayoffCalculationResponse)
async def calculate_payoff_by_number(
    loan_number: str,
    as_of_date: Optional[str] = None,
    current_user: dict = Depends(require_agent_or_above)
):
    """
    Calculate payoff amount for a loan by loan number (GET endpoint).
    
    Args:
        loan_number: Loan number to calculate payoff for
        as_of_date: Optional calculation date in YYYY-MM-DD format
        current_user: Current authenticated user
        
    Returns:
        PayoffCalculationResponse with calculation results
    """
    # Parse optional date parameter
    calculation_date = None
    if as_of_date:
        try:
            calculation_date = date.fromisoformat(as_of_date)
        except ValueError:
            return PayoffCalculationResponse(
                success=False,
                message="Invalid date format. Use YYYY-MM-DD format.",
                data=None
            )
    
    # Create request object and delegate to POST endpoint
    request = PayoffCalculationRequest(
        loan_number=loan_number,
        as_of_date=calculation_date
    )
    
    return await calculate_payoff(request, current_user)


@router.get("/tools/available")
async def get_available_tools(current_user: dict = Depends(require_agent_or_above)):
    """
    Get list of available tools for the current user based on their role.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Dictionary of available tools and their descriptions
    """
    user_role = current_user.get('role', 'agent')
    
    # Base tools available to all authenticated users (agent and above)
    tools = {
        "loan_search": {
            "name": "Loan Search",
            "description": "Search for loan information by loan number or borrower name",
            "endpoints": [
                "GET /api/loan/{identifier}",
                "POST /api/loan/search"
            ],
            "required_role": "agent"
        },
        "payoff_calculation": {
            "name": "Payoff Calculation",
            "description": "Calculate current payoff amount for a loan",
            "endpoints": [
                "POST /api/calculate-payoff",
                "GET /api/calculate-payoff/{loan_number}"
            ],
            "required_role": "agent"
        }
    }
    
    # Additional tools for supervisors and admins
    if user_role in ['supervisor', 'admin']:
        tools.update({
            "data_management": {
                "name": "Data Management",
                "description": "Load and manage loan data files",
                "endpoints": [
                    "POST /api/admin/load-data",
                    "GET /api/admin/data-info"
                ],
                "required_role": "supervisor"
            }
        })
    
    # Admin-only tools
    if user_role == 'admin':
        tools.update({
            "user_management": {
                "name": "User Management",
                "description": "Manage user accounts and permissions",
                "endpoints": [
                    "GET /api/admin/users",
                    "POST /api/admin/users"
                ],
                "required_role": "admin"
            }
        })
    
    return {
        "success": True,
        "user_role": user_role,
        "available_tools": tools
    }


@router.get("/tools/health")
async def check_tools_health():
    """
    Health check for tools API endpoints.
    
    Returns:
        Health status of tools and dependencies
    """
    health_status = {
        "calculator": "healthy",
        "data_access": "healthy" if loan_data_access.is_data_loaded() else "no_data",
        "loan_count": loan_data_access.get_loan_count(),
        "loaded_file": loan_data_access.get_loaded_file()
    }
    
    overall_status = "healthy" if health_status["data_access"] == "healthy" else "degraded"
    
    return {
        "status": overall_status,
        "timestamp": date.today().isoformat(),
        "components": health_status
    }