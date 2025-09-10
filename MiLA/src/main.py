"""
Main FastAPI application for the MiLA API.
"""
import logging
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.auth import (
    login, 
    require_agent_or_above, 
    cleanup_expired_keys,
    get_current_active_user
)
from .api.tools import router as tools_router
from .components.data_access import loan_data_access, DataAccessError
from .models.loan import (
    AuthRequest, 
    AuthResponse, 
    HealthCheckResponse,
    LoanResponse,
    LoanSearchRequest
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    """
    # Startup
    logger.info("Starting MiLA API...")
    
    # Load default sample data if available
    sample_data_path = Path(__file__).parent.parent / "data" / "sample_loans.xlsx"
    if sample_data_path.exists():
        try:
            await loan_data_access.load_loan_data(str(sample_data_path))
            logger.info(f"Loaded {loan_data_access.get_loan_count()} sample loan records")
        except DataAccessError as e:
            logger.warning(f"Could not load sample data: {str(e)}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down MiLA API...")
    await cleanup_expired_keys()


# Create FastAPI application
app = FastAPI(
    title="MiLA API",
    description="API for loan payoff processing system",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(tools_router)


# Exception handlers
@app.exception_handler(DataAccessError)
async def data_access_exception_handler(request, exc: DataAccessError):
    """Handle data access errors."""
    logger.error(f"Data access error: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"success": False, "message": str(exc)}
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unexpected error: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"success": False, "message": "Internal server error"}
    )


# Health check endpoint
@app.get("/api/health", response_model=HealthCheckResponse)
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        HealthCheckResponse with system status
    """
    return HealthCheckResponse(
        status="healthy",
        timestamp=date.today(),
        version="1.0.0"
    )


# Authentication endpoints
@app.post("/api/auth/login", response_model=AuthResponse)
async def login_endpoint(auth_request: AuthRequest):
    """
    User login endpoint.
    
    Args:
        auth_request: Authentication request with username and password
        
    Returns:
        AuthResponse with API key if successful
    """
    logger.info(f"Login attempt for user: {auth_request.username}")
    response = await login(auth_request)
    
    if response.success:
        logger.info(f"Successful login for user: {auth_request.username}")
    else:
        logger.warning(f"Failed login attempt for user: {auth_request.username}")
    
    return response


# Loan data endpoints
@app.get("/api/loan/{identifier}", response_model=LoanResponse)
async def get_loan(
    identifier: str,
    current_user: dict = Depends(require_agent_or_above)
):
    """
    Get loan information by loan number or borrower name.
    
    Args:
        identifier: Loan number or borrower name
        current_user: Current authenticated user
        
    Returns:
        LoanResponse with loan data if found
    """
    logger.info(f"Loan search request: '{identifier}' by user: {current_user['username']}")
    
    if not loan_data_access.is_data_loaded():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Loan data not loaded. Please contact administrator."
        )
    
    # Search for loan
    loan = await loan_data_access.find_loan_by_identifier(identifier)
    
    if loan:
        logger.info(f"Loan found: {loan.loan_number} for {loan.borrower_name}")
        return LoanResponse(
            success=True,
            message="Loan found",
            data=loan
        )
    else:
        logger.info(f"Loan not found for identifier: '{identifier}'")
        return LoanResponse(
            success=False,
            message=f"No loan found for identifier: {identifier}",
            data=None
        )


@app.post("/api/loan/search", response_model=LoanResponse)
async def search_loan(
    search_request: LoanSearchRequest,
    current_user: dict = Depends(require_agent_or_above)
):
    """
    Search for loan information.
    
    Args:
        search_request: Search request with identifier
        current_user: Current authenticated user
        
    Returns:
        LoanResponse with loan data if found
    """
    return await get_loan(search_request.identifier, current_user)


# Data management endpoints (admin only)
@app.post("/api/admin/load-data")
async def load_loan_data(
    file_path: str,
    current_user: dict = Depends(require_agent_or_above)
):
    """
    Load loan data from an Excel file.
    
    Args:
        file_path: Path to Excel file
        current_user: Current authenticated user
        
    Returns:
        Success response with number of records loaded
    """
    logger.info(f"Load data request: {file_path} by user: {current_user['username']}")
    
    try:
        loans = await loan_data_access.load_loan_data(file_path)
        logger.info(f"Successfully loaded {len(loans)} loan records")
        
        return {
            "success": True,
            "message": f"Successfully loaded {len(loans)} loan records",
            "count": len(loans)
        }
        
    except DataAccessError as e:
        logger.error(f"Failed to load data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.get("/api/admin/data-info")
async def get_data_info(current_user: dict = Depends(require_agent_or_above)):
    """
    Get information about currently loaded data.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Data information
    """
    return {
        "success": True,
        "data_loaded": loan_data_access.is_data_loaded(),
        "loan_count": loan_data_access.get_loan_count(),
        "loaded_file": loan_data_access.get_loaded_file()
    }


# User information endpoint
@app.get("/api/user/info")
async def get_user_info(current_user: dict = Depends(get_current_active_user)):
    """
    Get current user information.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User information
    """
    return {
        "success": True,
        "user": {
            "username": current_user["username"],
            "role": current_user["role"]
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )