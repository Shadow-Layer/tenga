"""Password hashing and verification utilities."""
import bcrypt


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
    """
    if not password:
        raise ValueError("Password cannot be empty")
    
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash.
    
    Args:
        password: Plain text password to verify
        password_hash: Hash to verify against
        
    Returns:
        True if password matches hash, False otherwise
    """
    if not password or not password_hash:
        return False
    
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except (ValueError, TypeError):
        return False
