# Database Security Configuration
# Apply these settings to harden your SQLite databases

import sqlite3
import os
import stat
from pathlib import Path

def secure_database_permissions():
    """Set secure permissions on database files."""
    db_files = [
        "data/api_server.db",
        "data/production.db", 
        "context.db"
    ]
    
    for db_file in db_files:
        if os.path.exists(db_file):
            # Set read/write for owner only (600)
            os.chmod(db_file, stat.S_IRUSR | stat.S_IWUSR)
            print(f"Secured permissions for {db_file}")

def create_secure_database_connection(db_path: str) -> sqlite3.Connection:
    """Create a secure database connection with proper settings."""
    # Ensure database directory exists with secure permissions
    db_dir = Path(db_path).parent
    db_dir.mkdir(mode=0o700, exist_ok=True)
    
    # Create connection with security settings
    conn = sqlite3.connect(
        db_path,
        check_same_thread=False,
        isolation_level='IMMEDIATE'  # Prevent race conditions
    )
    
    # Enable security features
    conn.execute("PRAGMA foreign_keys = ON")  # Enforce foreign key constraints
    conn.execute("PRAGMA secure_delete = ON")  # Securely delete data
    conn.execute("PRAGMA journal_mode = WAL")  # Write-ahead logging for integrity
    
    return conn

def hash_sensitive_data(data: str) -> str:
    """Hash sensitive data before storing in database."""
    import hashlib
    import secrets
    
    # Generate a random salt
    salt = secrets.token_hex(16)
    
    # Hash the data with salt
    hash_obj = hashlib.pbkdf2_hmac('sha256', data.encode(), salt.encode(), 100000)
    
    # Return salt + hash
    return salt + hash_obj.hex()

def verify_hashed_data(data: str, stored_hash: str) -> bool:
    """Verify hashed data."""
    import hashlib
    
    # Extract salt (first 32 characters)
    salt = stored_hash[:32]
    original_hash = stored_hash[32:]
    
    # Hash the input data with the same salt
    hash_obj = hashlib.pbkdf2_hmac('sha256', data.encode(), salt.encode(), 100000)
    
    # Compare hashes
    return hash_obj.hex() == original_hash

# Database Security Best Practices:
# 1. Use parameterized queries to prevent SQL injection
# 2. Encrypt sensitive data before storage
# 3. Set restrictive file permissions (600 for database files)
# 4. Enable WAL mode for better concurrency and integrity
# 5. Regular security audits and backups
# 6. Monitor database access logs
