"""
Database Manager for Jarvis 2.0
Manages SQLite database for conversation history, learning data,
and user preferences with efficient querying and data persistence.
"""

import sqlite3
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import threading
from contextlib import contextmanager

from conversation_manager import ConversationTurn, IntentType, ConversationContext
from learning_engine import UserPattern, LearningType
from services.path_manager import PathManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    """Database configuration"""
    db_path: str = "jarvis_data.db"
    max_connections: int = 10
    timeout: float = 30.0
    auto_vacuum: bool = True
    journal_mode: str = "WAL"  # Write-Ahead Logging for better performance

class DatabaseManager:
    """
    Manages SQLite database operations for Jarvis 2.0
    with conversation history, learning data, and user preferences
    """
    
    def __init__(self, config: DatabaseConfig = None):
        self.config = config or DatabaseConfig()

        if self.config.db_path == "jarvis_data.db":
            self.db_path = PathManager.get_database_path()
        else:
            self.db_path = Path(self.config.db_path)

        self.lock = threading.RLock()
        
        # Initialize database
        self._init_database()
        
    def _init_database(self):
        """Initialize database with required tables"""
        try:
            with self._get_connection() as conn:
                # Enable foreign keys
                conn.execute("PRAGMA foreign_keys = ON")
                
                # Set journal mode for better concurrency
                conn.execute(f"PRAGMA journal_mode = {self.config.journal_mode}")
                
                # Enable auto vacuum
                if self.config.auto_vacuum:
                    conn.execute("PRAGMA auto_vacuum = INCREMENTAL")
                
                # Create tables
                self._create_tables(conn)
                
                logger.info(f"Database initialized: {self.db_path}")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def _create_tables(self, conn: sqlite3.Connection):
        """Create all required database tables"""
        
        # Conversation sessions table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversation_sessions (
                session_id TEXT PRIMARY KEY,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                mode TEXT NOT NULL,
                total_turns INTEGER DEFAULT 0,
                avg_confidence REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Conversation turns table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversation_turns (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                timestamp TIMESTAMP NOT NULL,
                user_input TEXT NOT NULL,
                recognized_text TEXT NOT NULL,
                confidence_score REAL NOT NULL,
                intent TEXT NOT NULL,
                entities TEXT,  -- JSON
                context TEXT,   -- JSON
                response TEXT,
                response_time REAL,
                satisfaction_score REAL,
                audio_features TEXT,  -- JSON
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES conversation_sessions (session_id)
            )
        """)
        
        # User patterns table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_patterns (
                pattern_id TEXT PRIMARY KEY,
                pattern_type TEXT NOT NULL,
                pattern_data TEXT NOT NULL,  -- JSON
                frequency INTEGER DEFAULT 1,
                confidence REAL NOT NULL,
                first_observed TIMESTAMP NOT NULL,
                last_used TIMESTAMP NOT NULL,
                success_rate REAL DEFAULT 1.0,
                context_conditions TEXT,  -- JSON
                metadata TEXT,  -- JSON
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # User preferences table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                preference_key TEXT NOT NULL,
                preference_value TEXT NOT NULL,  -- JSON
                confidence REAL DEFAULT 1.0,
                weight REAL DEFAULT 1.0,
                learned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                usage_count INTEGER DEFAULT 0,
                UNIQUE(category, preference_key)
            )
        """)
        
        # Learning sessions table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS learning_sessions (
                session_id TEXT PRIMARY KEY,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                interactions_count INTEGER DEFAULT 0,
                patterns_discovered INTEGER DEFAULT 0,
                insights_generated TEXT,  -- JSON
                performance_metrics TEXT,  -- JSON
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Command log table (for pattern analysis)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS command_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP NOT NULL,
                command TEXT NOT NULL,
                intent TEXT,
                success BOOLEAN DEFAULT TRUE,
                execution_time REAL,
                context TEXT,  -- JSON
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # System metrics table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                metric_unit TEXT,
                metadata TEXT,  -- JSON
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for better performance
        self._create_indexes(conn)
        
        conn.commit()
    
    def _create_indexes(self, conn: sqlite3.Connection):
        """Create database indexes for better query performance"""
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_turns_session_id ON conversation_turns(session_id)",
            "CREATE INDEX IF NOT EXISTS idx_turns_timestamp ON conversation_turns(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_turns_intent ON conversation_turns(intent)",
            "CREATE INDEX IF NOT EXISTS idx_patterns_type ON user_patterns(pattern_type)",
            "CREATE INDEX IF NOT EXISTS idx_patterns_active ON user_patterns(is_active)",
            "CREATE INDEX IF NOT EXISTS idx_patterns_last_used ON user_patterns(last_used)",
            "CREATE INDEX IF NOT EXISTS idx_preferences_category ON user_preferences(category)",
            "CREATE INDEX IF NOT EXISTS idx_command_log_timestamp ON command_log(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_command_log_command ON command_log(command)",
            "CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON system_metrics(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_metrics_name ON system_metrics(metric_name)"
        ]
        
        for index_sql in indexes:
            try:
                conn.execute(index_sql)
            except sqlite3.OperationalError as e:
                logger.warning(f"Index creation warning: {e}")
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with proper error handling"""
        conn = None
        try:
            with self.lock:
                conn = sqlite3.connect(
                    self.db_path,
                    timeout=self.config.timeout,
                    check_same_thread=False
                )
                conn.row_factory = sqlite3.Row  # Enable dict-like access
                yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    # Conversation Management
    
    def _save_conversation_turn_sync(self, turn: ConversationTurn, session_id: str = None):
        """Synchronous implementation of save_conversation_turn"""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO conversation_turns 
                    (id, session_id, timestamp, user_input, recognized_text, confidence_score,
                     intent, entities, context, response, response_time, satisfaction_score, audio_features)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    turn.id,
                    session_id,
                    turn.timestamp,
                    turn.user_input,
                    turn.recognized_text,
                    turn.confidence_score,
                    turn.intent.value,
                    json.dumps(turn.entities, ensure_ascii=False),
                    json.dumps(turn.context, ensure_ascii=False),
                    turn.response,
                    turn.response_time,
                    turn.satisfaction_score,
                    json.dumps(turn.audio_features, ensure_ascii=False)
                ))
                conn.commit()
                
                logger.debug(f"Saved conversation turn: {turn.id}")
                
        except Exception as e:
            logger.error(f"Error saving conversation turn: {e}")
            raise

    async def save_conversation_turn(self, turn: ConversationTurn, session_id: str = None):
        """Save a conversation turn to database"""
        await asyncio.to_thread(self._save_conversation_turn_sync, turn, session_id)
    
    def _get_conversation_history_sync(self, session_id: str = None,
                                     limit: int = 50, 
                                     since: datetime = None) -> List[ConversationTurn]:
        """Synchronous implementation of get_conversation_history"""
        try:
            with self._get_connection() as conn:
                query = """
                    SELECT * FROM conversation_turns 
                    WHERE 1=1
                """
                params = []
                
                if session_id:
                    query += " AND session_id = ?"
                    params.append(session_id)
                
                if since:
                    query += " AND timestamp >= ?"
                    params.append(since)
                
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                
                turns = []
                for row in rows:
                    turn = ConversationTurn(
                        id=row['id'],
                        timestamp=datetime.fromisoformat(row['timestamp']),
                        user_input=row['user_input'],
                        recognized_text=row['recognized_text'],
                        confidence_score=row['confidence_score'],
                        intent=IntentType(row['intent']),
                        entities=json.loads(row['entities'] or '{}'),
                        context=json.loads(row['context'] or '{}'),
                        response=row['response'],
                        response_time=row['response_time'],
                        satisfaction_score=row['satisfaction_score'],
                        audio_features=json.loads(row['audio_features'] or '{}')
                    )
                    turns.append(turn)

                return turns

        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return []

    async def get_conversation_history(self, session_id: str = None,
                                     limit: int = 50,
                                     since: datetime = None) -> List[ConversationTurn]:
        """Get conversation history from database"""
        return await asyncio.to_thread(self._get_conversation_history_sync, session_id, limit, since)

    def _create_conversation_session_sync(self, session_id: str, mode: str) -> bool:
        """Synchronous implementation of create_conversation_session"""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO conversation_sessions
                    (session_id, start_time, mode)
                    VALUES (?, ?, ?)
                """, (session_id, datetime.now(), mode))
                conn.commit()

                logger.info(f"Created conversation session: {session_id}")
                return True

        except Exception as e:
            logger.error(f"Error creating conversation session: {e}")
            return False

    async def create_conversation_session(self, session_id: str, mode: str) -> bool:
        """Create a new conversation session"""
        return await asyncio.to_thread(self._create_conversation_session_sync, session_id, mode)

    def _end_conversation_session_sync(self, session_id: str,
                                     total_turns: int = 0,
                                     avg_confidence: float = 0.0) -> bool:
        """Synchronous implementation of end_conversation_session"""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    UPDATE conversation_sessions
                    SET end_time = ?, total_turns = ?, avg_confidence = ?
                    WHERE session_id = ?
                """, (datetime.now(), total_turns, avg_confidence, session_id))
                conn.commit()

                logger.info(f"Ended conversation session: {session_id}")
                return True

        except Exception as e:
            logger.error(f"Error ending conversation session: {e}")
            return False

    async def end_conversation_session(self, session_id: str,
                                     total_turns: int = 0,
                                     avg_confidence: float = 0.0) -> bool:
        """End a conversation session"""
        return await asyncio.to_thread(self._end_conversation_session_sync, session_id, total_turns, avg_confidence)

    # Learning Data Management

    def _save_user_pattern_sync(self, pattern: UserPattern) -> bool:
        """Synchronous implementation of save_user_pattern"""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO user_patterns
                    (pattern_id, pattern_type, pattern_data, frequency, confidence,
                     first_observed, last_used, success_rate, context_conditions, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pattern.pattern_id,
                    pattern.pattern_type.value,
                    json.dumps(pattern.pattern_data, ensure_ascii=False),
                    pattern.frequency,
                    pattern.confidence,
                    pattern.first_observed,
                    pattern.last_used,
                    pattern.success_rate,
                    json.dumps(pattern.context_conditions, ensure_ascii=False),
                    json.dumps(pattern.metadata, ensure_ascii=False)
                ))
                conn.commit()

                logger.debug(f"Saved user pattern: {pattern.pattern_id}")
                return True

        except Exception as e:
            logger.error(f"Error saving user pattern: {e}")
            return False

    async def save_user_pattern(self, pattern: UserPattern) -> bool:
        """Save a user pattern to database"""
        return await asyncio.to_thread(self._save_user_pattern_sync, pattern)

    def _get_user_patterns_sync(self, pattern_type: LearningType = None,
                              active_only: bool = True) -> List[UserPattern]:
        """Synchronous implementation of get_user_patterns"""
        try:
            with self._get_connection() as conn:
                query = "SELECT * FROM user_patterns WHERE 1=1"
                params = []

                if pattern_type:
                    query += " AND pattern_type = ?"
                    params.append(pattern_type.value)

                if active_only:
                    query += " AND is_active = TRUE"

                query += " ORDER BY frequency DESC, last_used DESC"

                cursor = conn.execute(query, params)
                rows = cursor.fetchall()

                patterns = []
                for row in rows:
                    pattern = UserPattern(
                        pattern_id=row['pattern_id'],
                        pattern_type=LearningType(row['pattern_type']),
                        pattern_data=json.loads(row['pattern_data']),
                        frequency=row['frequency'],
                        confidence=row['confidence'],
                        first_observed=datetime.fromisoformat(row['first_observed']),
                        last_used=datetime.fromisoformat(row['last_used']),
                        success_rate=row['success_rate'],
                        context_conditions=json.loads(row['context_conditions'] or '{}'),
                        metadata=json.loads(row['metadata'] or '{}')
                    )
                    patterns.append(pattern)

                return patterns

        except Exception as e:
            logger.error(f"Error getting user patterns: {e}")
            return []

    async def get_user_patterns(self, pattern_type: LearningType = None,
                              active_only: bool = True) -> List[UserPattern]:
        """Get user patterns from database"""
        return await asyncio.to_thread(self._get_user_patterns_sync, pattern_type, active_only)

    def _update_pattern_usage_sync(self, pattern_id: str) -> bool:
        """Synchronous implementation of update_pattern_usage"""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    UPDATE user_patterns
                    SET frequency = frequency + 1, last_used = ?, updated_at = ?
                    WHERE pattern_id = ?
                """, (datetime.now(), datetime.now(), pattern_id))
                conn.commit()

                return conn.total_changes > 0

        except Exception as e:
            logger.error(f"Error updating pattern usage: {e}")
            return False

    async def update_pattern_usage(self, pattern_id: str) -> bool:
        """Update pattern usage statistics"""
        return await asyncio.to_thread(self._update_pattern_usage_sync, pattern_id)

    # User Preferences Management

    def _save_user_preference_sync(self, category: str, key: str,
                                 value: Any, confidence: float = 1.0,
                                 weight: float = 1.0) -> bool:
        """Synchronous implementation of save_user_preference"""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO user_preferences
                    (category, preference_key, preference_value, confidence, weight, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    category,
                    key,
                    json.dumps(value, ensure_ascii=False),
                    confidence,
                    weight,
                    datetime.now()
                ))
                conn.commit()

                logger.debug(f"Saved user preference: {category}.{key}")
                return True

        except Exception as e:
            logger.error(f"Error saving user preference: {e}")
            return False

    async def save_user_preference(self, category: str, key: str,
                                 value: Any, confidence: float = 1.0,
                                 weight: float = 1.0) -> bool:
        """Save user preference to database"""
        return await asyncio.to_thread(self._save_user_preference_sync, category, key, value, confidence, weight)

    def _get_user_preferences_sync(self, category: str = None) -> Dict[str, Any]:
        """Synchronous implementation of get_user_preferences"""
        try:
            with self._get_connection() as conn:
                query = "SELECT * FROM user_preferences"
                params = []

                if category:
                    query += " WHERE category = ?"
                    params.append(category)

                query += " ORDER BY category, preference_key"

                cursor = conn.execute(query, params)
                rows = cursor.fetchall()

                preferences = {}
                for row in rows:
                    cat = row['category']
                    key = row['preference_key']
                    value = json.loads(row['preference_value'])

                    if cat not in preferences:
                        preferences[cat] = {}

                    preferences[cat][key] = {
                        'value': value,
                        'confidence': row['confidence'],
                        'weight': row['weight'],
                        'last_updated': row['last_updated'],
                        'usage_count': row['usage_count']
                    }

                return preferences

        except Exception as e:
            logger.error(f"Error getting user preferences: {e}")
            return {}

    async def get_user_preferences(self, category: str = None) -> Dict[str, Any]:
        """Get user preferences from database"""
        return await asyncio.to_thread(self._get_user_preferences_sync, category)

    # Command Logging

    def _log_command_sync(self, command: str, intent: str = None,
                        success: bool = True, execution_time: float = None,
                        context: Dict[str, Any] = None) -> bool:
        """Synchronous implementation of log_command"""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO command_log
                    (timestamp, command, intent, success, execution_time, context)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    datetime.now(),
                    command,
                    intent,
                    success,
                    execution_time,
                    json.dumps(context or {}, ensure_ascii=False)
                ))
                conn.commit()

                return True

        except Exception as e:
            logger.error(f"Error logging command: {e}")
            return False

    async def log_command(self, command: str, intent: str = None,
                        success: bool = True, execution_time: float = None,
                        context: Dict[str, Any] = None) -> bool:
        """Log command execution for analysis"""
        return await asyncio.to_thread(self._log_command_sync, command, intent, success, execution_time, context)

    def _get_command_statistics_sync(self, days: int = 30) -> Dict[str, Any]:
        """Synchronous implementation of get_command_statistics"""
        try:
            with self._get_connection() as conn:
                since = datetime.now() - timedelta(days=days)

                # Most used commands
                cursor = conn.execute("""
                    SELECT command, COUNT(*) as count, AVG(execution_time) as avg_time
                    FROM command_log
                    WHERE timestamp >= ? AND success = TRUE
                    GROUP BY command
                    ORDER BY count DESC
                    LIMIT 10
                """, (since,))

                most_used = [dict(row) for row in cursor.fetchall()]

                # Success rate
                cursor = conn.execute("""
                    SELECT
                        SUM(CASE WHEN success = TRUE THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate,
                        COUNT(*) as total_commands
                    FROM command_log
                    WHERE timestamp >= ?
                """, (since,))

                stats_row = cursor.fetchone()

                # Daily usage pattern
                cursor = conn.execute("""
                    SELECT
                        strftime('%H', timestamp) as hour,
                        COUNT(*) as count
                    FROM command_log
                    WHERE timestamp >= ?
                    GROUP BY hour
                    ORDER BY hour
                """, (since,))

                hourly_usage = {row['hour']: row['count'] for row in cursor.fetchall()}

                return {
                    'most_used_commands': most_used,
                    'success_rate': stats_row['success_rate'] if stats_row else 0.0,
                    'total_commands': stats_row['total_commands'] if stats_row else 0,
                    'hourly_usage': hourly_usage
                }

        except Exception as e:
            logger.error(f"Error getting command statistics: {e}")
            return {}

    async def get_command_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get command usage statistics"""
        return await asyncio.to_thread(self._get_command_statistics_sync, days)

    # System Metrics

    def _save_system_metric_sync(self, metric_name: str, metric_value: float,
                               metric_unit: str = None, metadata: Dict[str, Any] = None) -> bool:
        """Synchronous implementation of save_system_metric"""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO system_metrics
                    (timestamp, metric_name, metric_value, metric_unit, metadata)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    datetime.now(),
                    metric_name,
                    metric_value,
                    metric_unit,
                    json.dumps(metadata or {}, ensure_ascii=False)
                ))
                conn.commit()

                return True

        except Exception as e:
            logger.error(f"Error saving system metric: {e}")
            return False

    async def save_system_metric(self, metric_name: str, metric_value: float,
                               metric_unit: str = None, metadata: Dict[str, Any] = None) -> bool:
        """Save system metric to database"""
        return await asyncio.to_thread(self._save_system_metric_sync, metric_name, metric_value, metric_unit, metadata)

    # Database Maintenance

    def _cleanup_old_data_sync(self, days_to_keep: int = 90) -> bool:
        """Synchronous implementation of cleanup_old_data"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)

            with self._get_connection() as conn:
                # Clean old conversation turns
                conn.execute(
                    "DELETE FROM conversation_turns WHERE timestamp < ?",
                    (cutoff_date,)
                )

                # Clean old command logs
                conn.execute(
                    "DELETE FROM command_log WHERE timestamp < ?",
                    (cutoff_date,)
                )

                # Clean old system metrics
                conn.execute(
                    "DELETE FROM system_metrics WHERE timestamp < ?",
                    (cutoff_date,)
                )

                # Deactivate very old patterns
                old_pattern_date = datetime.now() - timedelta(days=days_to_keep * 2)
                conn.execute("""
                    UPDATE user_patterns
                    SET is_active = FALSE
                    WHERE last_used < ? AND frequency < 3
                """, (old_pattern_date,))

                conn.commit()

                # Vacuum database
                conn.execute("PRAGMA incremental_vacuum")

                logger.info(f"Database cleanup completed: removed data older than {days_to_keep} days")
                return True

        except Exception as e:
            logger.error(f"Error during database cleanup: {e}")
            return False

    async def cleanup_old_data(self, days_to_keep: int = 90) -> bool:
        """Clean up old data from database"""
        return await asyncio.to_thread(self._cleanup_old_data_sync, days_to_keep)

    def _get_database_stats_sync(self) -> Dict[str, Any]:
        """Synchronous implementation of get_database_stats"""
        try:
            with self._get_connection() as conn:
                stats = {}

                # Table row counts
                tables = [
                    'conversation_sessions', 'conversation_turns', 'user_patterns',
                    'user_preferences', 'learning_sessions', 'command_log', 'system_metrics'
                ]

                for table in tables:
                    cursor = conn.execute(f"SELECT COUNT(*) as count FROM {table}")
                    stats[f"{table}_count"] = cursor.fetchone()['count']

                # Database size
                cursor = conn.execute("PRAGMA page_count")
                page_count = cursor.fetchone()[0]

                cursor = conn.execute("PRAGMA page_size")
                page_size = cursor.fetchone()[0]

                stats['database_size_mb'] = (page_count * page_size) / (1024 * 1024)

                return stats

        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}

    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        return await asyncio.to_thread(self._get_database_stats_sync)

# Example usage and testing
async def main():
    """Example usage of Database Manager"""

    # Create database manager
    db_manager = DatabaseManager()

    # Create a test conversation session
    session_id = "test_session_123"
    await db_manager.create_conversation_session(session_id, "continuous")

    # Create a test conversation turn
    turn = ConversationTurn(
        id="test_turn_1",
        timestamp=datetime.now(),
        user_input="abrir chrome",
        recognized_text="abrir chrome",
        confidence_score=0.9,
        intent=IntentType.DIRECT_COMMAND,
        entities={'applications': ['chrome']},
        context={'topic': 'navigation'},
        response="Abrindo Chrome...",
        response_time=1.2,
        satisfaction_score=0.8
    )

    # Save conversation turn
    await db_manager.save_conversation_turn(turn, session_id)

    # Log a command
    await db_manager.log_command("abrir chrome", "DIRECT_COMMAND", True, 1.2)

    # Save a user preference
    await db_manager.save_user_preference(
        "response_style", "verbosity", "medium", confidence=0.8
    )

    # Get conversation history
    history = await db_manager.get_conversation_history(session_id)
    print(f"💾 Retrieved {len(history)} conversation turns")

    # Get command statistics
    stats = await db_manager.get_command_statistics()
    print(f"📊 Command stats: {stats}")

    # Get database statistics
    db_stats = await db_manager.get_database_stats()
    print(f"🗄️  Database stats: {db_stats}")

    # End conversation session
    await db_manager.end_conversation_session(session_id, total_turns=1, avg_confidence=0.9)

    print("Database manager test completed!")

if __name__ == "__main__":
    asyncio.run(main())