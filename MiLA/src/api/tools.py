"""
API tools endpoints for loan payoff calculations.
"""
import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

# Authentication removed for PoC simplicity
from ..components.data_access import loan_data_access, DataAccessError
from ..components.calculator import payoff_calculator, CalculationError
from ..models.payoff import PayoffCalculationRequest, PayoffCalculationResponse

logger = logging.getLogger(__name__)

# Create router for tools endpoints
router = APIRouter(prefix="/api", tags=["tools"])


@router.post("/calculate-payoff", response_model=PayoffCalculationResponse)
async def calculate_payoff(calculation_request: PayoffCalculationRequest):
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
        
    Returns:
        PayoffCalculationResponse with calculation results
    """
    logger.info(f"Payoff calculation request for loan {calculation_request.loan_number}")
    
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
    as_of_date: Optional[str] = None
):
    """
    Calculate payoff amount for a loan by loan number (GET endpoint).
    
    Args:
        loan_number: Loan number to calculate payoff for
        as_of_date: Optional calculation date in YYYY-MM-DD format
        
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
    
    return await calculate_payoff(request)


@router.get("/tools/available")
async def get_available_tools():
    """
    Get list of all available tools (no authentication required).
    
    Returns:
        Dictionary of available tools and their descriptions
    """
    # All tools available in PoC without role restrictions
    tools = {
        "loan_search": {
            "name": "Loan Search",
            "description": "Search for loan information by loan number or borrower name",
            "endpoints": [
                "GET /api/loan/{identifier}",
                "POST /api/loan/search"
            ]
        },
        "payoff_calculation": {
            "name": "Payoff Calculation",
            "description": "Calculate current payoff amount for a loan",
            "endpoints": [
                "POST /api/calculate-payoff",
                "GET /api/calculate-payoff/{loan_number}"
            ]
        },
        "data_management": {
            "name": "Data Management",
            "description": "Load and manage loan data files",
            "endpoints": [
                "POST /api/admin/load-data",
                "GET /api/admin/data-info"
            ]
        }
    }
    
    return {
        "success": True,
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