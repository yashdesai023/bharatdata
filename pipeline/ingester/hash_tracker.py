import hashlib
import os
import psycopg2
from utils.db_connection import get_connection
from utils.logger_config import pipeline_logger as logger

class HashTracker:
    """Tracks which files have been ingested using SHA-256 hashes."""
    
    def calculate_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of a file."""
        sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate hash for {file_path}: {e}")
            return None
    
    def is_file_ingested(self, file_path: str) -> bool:
        """Check if a file has already been fully ingested."""
        file_hash = self.calculate_hash(file_path)
        if not file_hash:
            return False
            
        try:
            with get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id FROM ingested_files WHERE file_hash_sha256 = %s",
                        (file_hash,)
                    )
                    result = cursor.fetchone()
                    return result is not None
        except Exception as e:
            logger.error(f"Error checking ingestion status for {file_path}: {e}")
            return False
    
    def mark_file_ingested(
        self, 
        file_path: str, 
        year: int, 
        table_type: str,
        geographic_level: str,
        records_extracted: int
    ):
        """Mark a file as fully ingested."""
        file_hash = self.calculate_hash(file_path)
        if not file_hash:
            return
            
        file_size = os.path.getsize(file_path)
        
        try:
            with get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO ingested_files 
                            (file_path, file_hash_sha256, file_size_bytes, 
                             year, table_type, geographic_level, records_extracted)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (file_hash_sha256) DO NOTHING
                    """, (
                        file_path, file_hash, file_size,
                        year, table_type, geographic_level, records_extracted
                    ))
                    conn.commit()
                    logger.info(f"Marked file as ingested: {os.path.basename(file_path)}")
        except Exception as e:
            logger.error(f"Error marking file as ingested {file_path}: {e}")
    
    def get_ingestion_status(self) -> dict:
        """Get summary of ingested files."""
        try:
            with get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT year, geographic_level, COUNT(*), SUM(records_extracted)
                        FROM ingested_files
                        GROUP BY year, geographic_level
                        ORDER BY year, geographic_level
                    """)
                    
                    status = {}
                    for row in cursor.fetchall():
                        year, level, file_count, record_count = row
                        status[f"{year}_{level}"] = {
                            "files": file_count,
                            "records": record_count
                        }
                    return status
        except Exception as e:
            logger.error(f"Error fetching ingestion status: {e}")
            return {}
