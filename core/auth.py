import hashlib
import os
import secrets
import time
import sqlite3
from core.db import get_db_connection

# Session expiration time (24 hours)
SESSION_DURATION_SECONDS = 24 * 3600

def hash_password(password: str) -> str:
    """Hashes a password using SHA-256 with a random salt."""
    salt = os.urandom(16).hex()
    pwd_hash = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()
    return f"{salt}:{pwd_hash}"

def verify_password(password: str, hashed_value: str) -> bool:
    """Verifies a password against its salt-hashed value."""
    try:
        salt, pwd_hash = hashed_value.split(":")
        check_hash = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()
        return check_hash == pwd_hash
    except Exception:
        return False

def create_session(user_id: int) -> str:
    """Generates a secure session token and stores it in the database."""
    token = secrets.token_hex(32)
    expires_at = time.time() + SESSION_DURATION_SECONDS
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Clean expired sessions
    cursor.execute("DELETE FROM sessions WHERE expires_at < ?", (time.time(),))
    
    # Store new session
    cursor.execute("""
    INSERT INTO sessions (token, user_id, expires_at)
    VALUES (?, ?, ?)
    """, (token, user_id, expires_at))
    
    conn.commit()
    conn.close()
    return token

def validate_session(token: str) -> int:
    """
    Validates a session token. 
    Returns the user_id if valid, or None if expired/invalid.
    """
    if not token:
        return None
        
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT user_id FROM sessions 
    WHERE token = ? AND expires_at > ?
    """, (token, time.time()))
    row = cursor.fetchone()
    
    user_id = row[0] if row else None
    
    conn.close()
    return user_id

def delete_session(token: str):
    """Deletes a session token on user logout."""
    if not token:
        return
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()
    conn.close()
