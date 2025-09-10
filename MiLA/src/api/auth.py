"""
Authentication system for the MiLA API.
"""
import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..models.loan import AuthRequest, AuthResponse

logger = logging.getLogger(__name__)

# Security configuration
security = HTTPBearer()

# In-memory storage for demo purposes
# In production, this would be a proper database
USERS_DB = {
    "loan_agent": {
        "password_hash": hashlib.sha256("agent123".encode()).hexdigest(),
        "role": "agent",
        "active": True
    },
    "loan_supervisor": {
        "password_hash": hashlib.sha256("supervisor456".encode()).hexdigest(),
        "role": "supervisor", 
        "active": True
    },
    "admin": {
        "password_hash": hashlib.sha256("admin789".encode()).hexdigest(),
        "role": "admin",
        "active": True
    }
}

# Active API keys with expiration
API_KEYS: Dict[str, Dict] = {}

# API key expiration time (1 hour for demo)
API_KEY_EXPIRY_HOURS = 1


class AuthenticationError(Exception):
    """Custom exception for authentication errors."""
    pass


def hash_password(password: str) -> str:
    """
    Hash a password using SHA-256.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password
    """
    return hashlib.sha256(password.encode()).hexdigest()


def generate_api_key() -> str:
    """
    Generate a secure random API key.
    
    Returns:
        Random API key string
    """
    return secrets.token_urlsafe(32)


async def authenticate_user(username: str, password: str) -> Optional[Dict]:
    """
    Authenticate a user with username and password.
    
    Args:
        username: User's username
        password: User's password
        
    Returns:
        User information dict if authenticated, None otherwise
    """
    user = USERS_DB.get(username)
    if not user:
        return None
    
    if not user.get("active", False):
        return None
    
    password_hash = hash_password(password)
    if password_hash != user["password_hash"]:
        return None
    
    return {
        "username": username,
        "role": user["role"],
        "active": user["active"]
    }


async def create_api_key(user_info: Dict) -> tuple[str, datetime]:
    """
    Create an API key for an authenticated user.
    
    Args:
        user_info: User information dictionary
        
    Returns:
        Tuple of (api_key, expiration_datetime)
    """
    api_key = generate_api_key()
    expiry_time = datetime.utcnow() + timedelta(hours=API_KEY_EXPIRY_HOURS)
    
    API_KEYS[api_key] = {
        "username": user_info["username"],
        "role": user_info["role"],
        "expires_at": expiry_time,
        "created_at": datetime.utcnow()
    }
    
    logger.info(f"API key created for user: {user_info['username']}")
    return api_key, expiry_time


async def validate_api_key(api_key: str) -> Optional[Dict]:
    """
    Validate an API key and return user information.
    
    Args:
        api_key: API key to validate
        
    Returns:
        User information dict if valid, None otherwise
    """
    key_info = API_KEYS.get(api_key)
    if not key_info:
        return None
    
    # Check if key has expired
    if datetime.utcnow() > key_info["expires_at"]:
        # Remove expired key
        del API_KEYS[api_key]
        logger.info(f"Expired API key removed for user: {key_info['username']}")
        return None
    
    return key_info


async def revoke_api_key(api_key: str) -> bool:
    """
    Revoke an API key.
    
    Args:
        api_key: API key to revoke
        
    Returns:
        True if key was revoked, False if key didn't exist
    """
    if api_key in API_KEYS:
        username = API_KEYS[api_key]["username"]
        del API_KEYS[api_key]
        logger.info(f"API key revoked for user: {username}")
        return True
    return False


async def login(auth_request: AuthRequest) -> AuthResponse:
    """
    Perform user login and return API key.
    
    Args:
        auth_request: Authentication request with username and password
        
    Returns:
        AuthResponse with success status and API key if successful
    """
    try:
        # Authenticate user
        user_info = await authenticate_user(auth_request.username, auth_request.password)
        if not user_info:
            return AuthResponse(
                success=False,
                message="Invalid username or password",
                api_key=None
            )
        
        # Create API key
        api_key, expiry_time = await create_api_key(user_info)
        
        return AuthResponse(
            success=True,
            message="Login successful",
            api_key=api_key,
            expires_in=int(API_KEY_EXPIRY_HOURS * 3600)  # seconds
        )
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return AuthResponse(
            success=False,
            message="Authentication failed",
            api_key=None
        )


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    """
    Dependency to get current authenticated user from API key.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        User information dictionary
        
    Raises:
        HTTPException: If authentication fails
    """
    api_key = credentials.credentials
    
    user_info = await validate_api_key(api_key)
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_info


async def get_current_active_user(current_user: Dict = Depends(get_current_user)) -> Dict:
    """
    Dependency to get current active user.
    
    Args:
        current_user: Current user from get_current_user
        
    Returns:
        User information dictionary
        
    Raises:
        HTTPException: If user is not active
    """
    username = current_user["username"]
    user = USERS_DB.get(username)
    
    if not user or not user.get("active", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled"
        )
    
    return current_user


def require_role(required_roles: list):
    """
    Decorator to require specific user roles.
    
    Args:
        required_roles: List of required roles
        
    Returns:
        Dependency function that checks user role
    """
    def role_checker(current_user: Dict = Depends(get_current_active_user)) -> Dict:
        user_role = current_user.get("role")
        if user_role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {required_roles}"
            )
        return current_user
    
    return role_checker


# Convenience role dependencies
require_agent_or_above = require_role(["agent", "supervisor", "admin"])
require_supervisor_or_above = require_role(["supervisor", "admin"])
require_admin = require_role(["admin"])


async def cleanup_expired_keys():
    """
    Clean up expired API keys from memory.
    """
    current_time = datetime.utcnow()
    expired_keys = [
        key for key, info in API_KEYS.items()
        if current_time > info["expires_at"]
    ]
    
    for key in expired_keys:
        username = API_KEYS[key]["username"]
        del API_KEYS[key]
        logger.info(f"Expired API key cleaned up for user: {username}")
    
    return len(expired_keys)