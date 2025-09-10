"""
Main FastAPI application for the MiLA API.
"""
import logging
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
# CORS middleware removed for PoC simplicity
from fastapi.responses import JSONResponse

# Authentication removed for PoC simplicity
from .api.tools import router as tools_router
from .components.data_access import loan_data_access, DataAccessError
from .models.loan import (
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
    # No cleanup needed without authentication


# Create FastAPI application
app = FastAPI(
    title="MiLA API",
    description="API for loan payoff processing system",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware removed for PoC simplicity

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


# Authentication removed for PoC simplicity


# Loan data endpoints
@app.get("/api/loan/{identifier}", response_model=LoanResponse)
async def get_loan(identifier: str):
    """
    Get loan information by loan number or borrower name.
    
    Args:
        identifier: Loan number or borrower name
        
    Returns:
        LoanResponse with loan data if found
    """
    logger.info(f"Loan search request: '{identifier}'")
    
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
async def search_loan(search_request: LoanSearchRequest):
    """
    Search for loan information.
    
    Args:
        search_request: Search request with identifier
        
    Returns:
        LoanResponse with loan data if found
    """
    return await get_loan(search_request.identifier)


# Data management endpoints (admin only)
@app.post("/api/admin/load-data")
async def load_loan_data(file_path: str):
    """
    Load loan data from an Excel file.
    
    Args:
        file_path: Path to Excel file
        
    Returns:
        Success response with number of records loaded
    """
    logger.info(f"Load data request: {file_path}")
    
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
async def get_data_info():
    """
    Get information about currently loaded data.
    
    Returns:
        Data information
    """
    return {
        "success": True,
        "data_loaded": loan_data_access.is_data_loaded(),
        "loan_count": loan_data_access.get_loan_count(),
        "loaded_file": loan_data_access.get_loaded_file()
    }


# User information endpoint removed (no authentication)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )