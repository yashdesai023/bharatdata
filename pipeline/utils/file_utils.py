import hashlib
import os
import re

def calculate_sha256(file_path: str) -> str:
    """Calculates the SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except FileNotFoundError:
        return ""

def calculate_sha256_bytes(content: bytes) -> str:
    """Calculates the SHA-256 hash of byte content."""
    sha256_hash = hashlib.sha256()
    sha256_hash.update(content)
    return sha256_hash.hexdigest()

def clean_filename(filename: str) -> str:
    """Removes timestamp prefixes commonly found in 2021 NCRB files."""
    # E.g., '1668480351797_Table 1.1.xlsx' -> 'Table 1.1.xlsx'
    return re.sub(r'^\d{10,}_', '', filename)
    
