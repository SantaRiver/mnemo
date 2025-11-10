"""History lookup service for action templates and time estimation."""

import sqlite3
from pathlib import Path
from typing import Dict, Optional

from nlp_service.services.preprocessor import TextPreprocessor


class SQLiteHistoryService:
    """SQLite-based history lookup service."""

    def __init__(self, db_path: str = "./nlp_service.db") -> None:
        """Initialize history service.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.preprocessor = TextPreprocessor(enabled=False)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS action_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    normalized_text TEXT NOT NULL,
                    avg_time_minutes REAL NOT NULL,
                    occurrences INTEGER NOT NULL DEFAULT 1,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, normalized_text)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_action 
                ON action_templates(user_id, normalized_text)
            """)
            conn.commit()

    def get_average_time(self, user_id: int, action_normalized: str) -> Optional[int]:
        """Get average time for an action from history.
        
        Args:
            user_id: User ID
            action_normalized: Normalized action text
            
        Returns:
            Average time in minutes or None
        """
        normalized = self.preprocessor.normalize_text(action_normalized)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT avg_time_minutes 
                FROM action_templates 
                WHERE (user_id = ? OR user_id IS NULL) 
                  AND normalized_text = ?
                ORDER BY user_id DESC NULLS LAST
                LIMIT 1
                """,
                (user_id, normalized)
            )
            row = cursor.fetchone()
            
            if row:
                return int(row[0])
            
            return None

    def record_action(
        self, user_id: int, action_normalized: str, time_minutes: int
    ) -> None:
        """Record an action for future reference.
        
        Args:
            user_id: User ID
            action_normalized: Normalized action text
            time_minutes: Time in minutes
        """
        normalized = self.preprocessor.normalize_text(action_normalized)
        
        with sqlite3.connect(self.db_path) as conn:
            # Try to get existing record
            cursor = conn.execute(
                """
                SELECT avg_time_minutes, occurrences 
                FROM action_templates 
                WHERE user_id = ? AND normalized_text = ?
                """,
                (user_id, normalized)
            )
            row = cursor.fetchone()
            
            if row:
                # Update with incremental average
                avg_time, occurrences = row
                new_avg = (avg_time * occurrences + time_minutes) / (occurrences + 1)
                new_occurrences = occurrences + 1
                
                conn.execute(
                    """
                    UPDATE action_templates 
                    SET avg_time_minutes = ?, 
                        occurrences = ?,
                        last_seen = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND normalized_text = ?
                    """,
                    (new_avg, new_occurrences, user_id, normalized)
                )
            else:
                # Insert new record
                conn.execute(
                    """
                    INSERT INTO action_templates 
                        (user_id, normalized_text, avg_time_minutes, occurrences)
                    VALUES (?, ?, ?, 1)
                    """,
                    (user_id, normalized, time_minutes)
                )
            
            conn.commit()

    def get_user_stats(self, user_id: int) -> Dict[str, int]:
        """Get statistics for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT 
                    COUNT(*) as total_templates,
                    SUM(occurrences) as total_actions
                FROM action_templates 
                WHERE user_id = ?
                """,
                (user_id,)
            )
            row = cursor.fetchone()
            
            return {
                "total_templates": row[0] or 0,
                "total_actions": row[1] or 0
            }


class InMemoryHistoryService:
    """In-memory history service for testing."""

    def __init__(self) -> None:
        """Initialize in-memory service."""
        self.data: Dict[tuple[int, str], tuple[float, int]] = {}
        self.preprocessor = TextPreprocessor(enabled=False)

    def get_average_time(self, user_id: int, action_normalized: str) -> Optional[int]:
        """Get average time for an action.
        
        Args:
            user_id: User ID
            action_normalized: Normalized action text
            
        Returns:
            Average time in minutes or None
        """
        normalized = self.preprocessor.normalize_text(action_normalized)
        key = (user_id, normalized)
        
        if key in self.data:
            avg_time, _ = self.data[key]
            return int(avg_time)
        
        # Check global templates (user_id = 0)
        global_key = (0, normalized)
        if global_key in self.data:
            avg_time, _ = self.data[global_key]
            return int(avg_time)
        
        return None

    def record_action(
        self, user_id: int, action_normalized: str, time_minutes: int
    ) -> None:
        """Record an action.
        
        Args:
            user_id: User ID
            action_normalized: Normalized action text
            time_minutes: Time in minutes
        """
        normalized = self.preprocessor.normalize_text(action_normalized)
        key = (user_id, normalized)
        
        if key in self.data:
            avg_time, occurrences = self.data[key]
            new_avg = (avg_time * occurrences + time_minutes) / (occurrences + 1)
            self.data[key] = (new_avg, occurrences + 1)
        else:
            self.data[key] = (float(time_minutes), 1)
