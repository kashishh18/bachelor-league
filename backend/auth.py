import os
import jwt
import bcrypt
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from functools import wraps
import asyncio
from dataclasses import dataclass
from enum import Enum

# Import database and models
from database import get_db
from models import User

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

# Password configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)

class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"
    EMAIL_VERIFICATION = "email_verification"
    PASSWORD_RESET = "password_reset"

@dataclass
class TokenData:
    """Token payload data"""
    user_id: str
    username: Optional[str] = None
    email: Optional[str] = None
    token_type: TokenType = TokenType.ACCESS
    permissions: list = None
    issued_at: datetime = None
    expires_at: datetime = None
    
    def __post_init__(self):
        if self.permissions is None:
            self.permissions = []
        if self.issued_at is None:
            self.issued_at = datetime.utcnow()

class AuthenticationError(Exception):
    """Custom authentication exception"""
    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class PermissionError(Exception):
    """Custom permission exception"""
    def __init__(self, message: str = "Insufficient permissions"):
        self.message = message
        super().__init__(self.message)

# ==================== PASSWORD UTILITIES ====================

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    try:
        # Generate salt and hash password
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    except Exception as e:
        logger.error(f"Error hashing password: {str(e)}")
        raise AuthenticationError("Failed to hash password")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'), 
            hashed_password.encode('utf-8')
        )
    except Exception as e:
        logger.error(f"Error verifying password: {str(e)}")
        return False

def generate_secure_password(length: int = 12) -> str:
    """Generate a secure random password"""
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password

def validate_password_strength(password: str) -> Dict[str, Any]:
    """Validate password strength and return feedback"""
    issues = []
    score = 0
    
    # Length check
    if len(password) < 8:
        issues.append("Password must be at least 8 characters long")
    else:
        score += 1
    
    # Character variety checks
    if not any(c.islower() for c in password):
        issues.append("Password must contain at least one lowercase letter")
    else:
        score += 1
    
    if not any(c.isupper() for c in password):
        issues.append("Password must contain at least one uppercase letter")
    else:
        score += 1
    
    if not any(c.isdigit() for c in password):
        issues.append("Password must contain at least one digit")
    else:
        score += 1
    
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        issues.append("Password must contain at least one special character")
    else:
        score += 1
    
    # Common password check (simplified)
    common_passwords = ["password", "123456", "password123", "admin", "letmein"]
    if password.lower() in common_passwords:
        issues.append("Password is too common")
        score = max(0, score - 2)
    
    strength_levels = ["Very Weak", "Weak", "Fair", "Good", "Strong"]
    strength = strength_levels[min(score, 4)]
    
    return {
        "is_valid": len(issues) == 0,
        "strength": strength,
        "score": score,
        "issues": issues
    }

# ==================== JWT TOKEN UTILITIES ====================

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    try:
        to_encode = data.copy()
        
        # Set expiration
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": TokenType.ACCESS
        })
        
        # Create token
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
        
    except Exception as e:
        logger.error(f"Error creating access token: {str(e)}")
        raise AuthenticationError("Failed to create access token")

def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create a JWT refresh token"""
    try:
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": TokenType.REFRESH
        })
        
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
        
    except Exception as e:
        logger.error(f"Error creating refresh token: {str(e)}")
        raise AuthenticationError("Failed to create refresh token")

def create_verification_token(user_id: str, token_type: TokenType, 
                            expires_hours: int = 24) -> str:
    """Create a verification token (email verification, password reset)"""
    try:
        expire = datetime.utcnow() + timedelta(hours=expires_hours)
        
        to_encode = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": token_type,
            "nonce": secrets.token_urlsafe(16)  # Prevent token reuse
        }
        
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
        
    except Exception as e:
        logger.error(f"Error creating verification token: {str(e)}")
        raise AuthenticationError("Failed to create verification token")

def verify_token(token: str, expected_type: TokenType = TokenType.ACCESS) -> TokenData:
    """Verify and decode a JWT token"""
    try:
        # Decode token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Validate token type
        token_type = payload.get("type")
        if token_type != expected_type:
            raise AuthenticationError(f"Invalid token type. Expected {expected_type}")
        
        # Extract data
        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationError("Token missing user ID")
        
        # Create token data
        token_data = TokenData(
            user_id=user_id,
            username=payload.get("username"),
            email=payload.get("email"),
            token_type=TokenType(token_type),
            permissions=payload.get("permissions", []),
            issued_at=datetime.fromtimestamp(payload.get("iat", 0)),
            expires_at=datetime.fromtimestamp(payload.get("exp", 0))
        )
        
        return token_data
        
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired", 401)
    except jwt.InvalidTokenError as e:
        raise AuthenticationError(f"Invalid token: {str(e)}", 401)
    except Exception as e:
        logger.error(f"Error verifying token: {str(e)}")
        raise AuthenticationError("Token verification failed", 401)

def refresh_access_token(refresh_token: str) -> Dict[str, str]:
    """Create new access token from refresh token"""
    try:
        # Verify refresh token
        token_data = verify_token(refresh_token, TokenType.REFRESH)
        
        # Create new access token
        new_access_token = create_access_token({"sub": token_data.user_id})
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer"
        }
        
    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}")
        raise AuthenticationError("Failed to refresh token")

# ==================== AUTHENTICATION DEPENDENCIES ====================

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    try:
        # Check if credentials provided
        if not credentials:
            raise AuthenticationError("Authentication credentials required")
        
        # Verify token
        token_data = verify_token(credentials.credentials)
        
        # Get user from database
        user = await db.get_user_by_id(token_data.user_id)
        if not user:
            raise AuthenticationError("User not found")
        
        # Check if user is active
        if not user.is_active:
            raise AuthenticationError("User account is deactivated")
        
        # Update last login
        user.last_login = datetime.utcnow()
        await db.commit()
        
        return user
        
    except AuthenticationError:
        raise
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user (alias for compatibility)"""
    return current_user

async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current user and verify admin permissions"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

def require_permissions(*required_permissions: str):
    """Decorator to require specific permissions"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract current user from kwargs (FastAPI dependency injection)
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Check permissions (simplified - in production, implement proper RBAC)
            user_permissions = getattr(current_user, 'permissions', [])
            if not all(perm in user_permissions for perm in required_permissions):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# ==================== RATE LIMITING ====================

class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        self.attempts = {}
        self.blocked = {}
    
    def is_allowed(self, identifier: str, max_attempts: int = 5, 
                  window_minutes: int = 15) -> bool:
        """Check if request is allowed based on rate limits"""
        now = datetime.utcnow()
        
        # Check if currently blocked
        if identifier in self.blocked:
            if now < self.blocked[identifier]:
                return False
            else:
                # Unblock expired blocks
                del self.blocked[identifier]
        
        # Initialize or get attempts for identifier
        if identifier not in self.attempts:
            self.attempts[identifier] = []
        
        # Clean old attempts outside window
        window_start = now - timedelta(minutes=window_minutes)
        self.attempts[identifier] = [
            attempt for attempt in self.attempts[identifier] 
            if attempt > window_start
        ]
        
        # Check if over limit
        if len(self.attempts[identifier]) >= max_attempts:
            # Block for window duration
            self.blocked[identifier] = now + timedelta(minutes=window_minutes)
            return False
        
        # Record this attempt
        self.attempts[identifier].append(now)
        return True
    
    def record_failure(self, identifier: str):
        """Record a failed attempt"""
        # Already recorded in is_allowed, but can be used for additional tracking
        pass

# Global rate limiter instance
rate_limiter = RateLimiter()

def check_rate_limit(identifier: str, max_attempts: int = 5, window_minutes: int = 15):
    """Dependency to check rate limits"""
    if not rate_limiter.is_allowed(identifier, max_attempts, window_minutes):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many attempts. Try again in {window_minutes} minutes."
        )

# ==================== SESSION MANAGEMENT ====================

class SessionManager:
    """Manage user sessions and token blacklisting"""
    
    def __init__(self):
        self.blacklisted_tokens = set()
        self.user_sessions = {}  # user_id -> list of active tokens
    
    def blacklist_token(self, token: str):
        """Add token to blacklist"""
        self.blacklisted_tokens.add(token)
    
    def is_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted"""
        return token in self.blacklisted_tokens
    
    def add_user_session(self, user_id: str, token: str):
        """Add session for user"""
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = []
        self.user_sessions[user_id].append(token)
    
    def revoke_user_sessions(self, user_id: str):
        """Revoke all sessions for user"""
        if user_id in self.user_sessions:
            for token in self.user_sessions[user_id]:
                self.blacklisted_tokens.add(token)
            del self.user_sessions[user_id]
    
    def cleanup_expired_tokens(self):
        """Clean up expired tokens (should be run periodically)"""
        # In production, this would check token expiration times
        # For now, just limit the size of blacklisted tokens
        if len(self.blacklisted_tokens) > 10000:
            # Keep only the most recent 5000 tokens
            recent_tokens = list(self.blacklisted_tokens)[-5000:]
            self.blacklisted_tokens = set(recent_tokens)

# Global session manager
session_manager = SessionManager()

# ==================== UTILITY FUNCTIONS ====================

def generate_api_key(length: int = 32) -> str:
    """Generate a secure API key"""
    return secrets.token_urlsafe(length)

def mask_email(email: str) -> str:
    """Mask email for privacy (user@domain.com -> u***@d***.com)"""
    try:
        local, domain = email.split('@')
        masked_local = local[0] + '*' * (len(local) - 1)
        domain_parts = domain.split('.')
        masked_domain = domain_parts[0][0] + '*' * (len(domain_parts[0]) - 1)
        if len(domain_parts) > 1:
            masked_domain += '.' + '.'.join(domain_parts[1:])
        return f"{masked_local}@{masked_domain}"
    except:
        return "***@***.***"

def validate_email(email: str) -> bool:
    """Basic email validation"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def generate_username_suggestions(preferred_name: str, existing_usernames: list) -> list:
    """Generate username suggestions if preferred name is taken"""
    suggestions = []
    base_name = preferred_name.lower().replace(' ', '_')
    
    # Try variations
    for i in range(1, 6):
        suggestion = f"{base_name}_{i}"
        if suggestion not in existing_usernames:
            suggestions.append(suggestion)
    
    # Try with random numbers
    for _ in range(3):
        random_num = secrets.randbelow(9999)
        suggestion = f"{base_name}_{random_num}"
        if suggestion not in existing_usernames:
            suggestions.append(suggestion)
    
    return suggestions[:5]  # Return top 5 suggestions

# ==================== PASSWORD RESET UTILITIES ====================

async def initiate_password_reset(email: str, db: AsyncSession) -> Optional[str]:
    """Initiate password reset process"""
    try:
        # Find user
        user = await db.get_user_by_email(email)
        if not user:
            # Don't reveal if email exists or not
            logger.info(f"Password reset attempted for non-existent email: {mask_email(email)}")
            return None
        
        # Generate reset token
        reset_token = create_verification_token(
            user.id, 
            TokenType.PASSWORD_RESET, 
            expires_hours=1  # 1 hour expiry for security
        )
        
        logger.info(f"Password reset token generated for user: {user.username}")
        return reset_token
        
    except Exception as e:
        logger.error(f"Error initiating password reset: {str(e)}")
        return None

async def reset_password_with_token(token: str, new_password: str, 
                                  db: AsyncSession) -> bool:
    """Reset password using reset token"""
    try:
        # Verify reset token
        token_data = verify_token(token, TokenType.PASSWORD_RESET)
        
        # Validate new password
        validation = validate_password_strength(new_password)
        if not validation["is_valid"]:
            raise AuthenticationError("Password does not meet security requirements")
        
        # Get user and update password
        user = await db.get_user_by_id(token_data.user_id)
        if not user:
            raise AuthenticationError("User not found")
        
        # Hash and update password
        user.password_hash = hash_password(new_password)
        user.updated_at = datetime.utcnow()
        
        # Revoke all existing sessions for security
        session_manager.revoke_user_sessions(user.id)
        
        await db.commit()
        
        logger.info(f"Password reset completed for user: {user.username}")
        return True
        
    except AuthenticationError:
        raise
    except Exception as e:
        logger.error(f"Error resetting password: {str(e)}")
        return False

# ==================== EXPORT ====================

__all__ = [
    # Password utilities
    'hash_password', 'verify_password', 'validate_password_strength',
    
    # Token utilities  
    'create_access_token', 'create_refresh_token', 'verify_token', 'refresh_access_token',
    
    # Dependencies
    'get_current_user', 'get_current_active_user', 'get_admin_user',
    
    # Rate limiting
    'RateLimiter', 'rate_limiter', 'check_rate_limit',
    
    # Session management
    'SessionManager', 'session_manager',
    
    # Password reset
    'initiate_password_reset', 'reset_password_with_token',
    
    # Utilities
    'generate_secure_password', 'validate_email', 'mask_email',
    
    # Exceptions
    'AuthenticationError', 'PermissionError'
]
