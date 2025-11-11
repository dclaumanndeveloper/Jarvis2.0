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
    
    async def save_conversation_turn(self, turn: ConversationTurn, session_id: str = None):
        """Save a conversation turn to database"""
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
    
    async def get_conversation_history(self, session_id: str = None, 
                                     limit: int = 50, 
                                     since: datetime = None) -> List[ConversationTurn]:
        """Get conversation history from database"""
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
                    )\n                    turns.append(turn)\n                \n                return turns\n                \n        except Exception as e:\n            logger.error(f\"Error getting conversation history: {e}\")\n            return []\n    \n    async def create_conversation_session(self, session_id: str, mode: str) -> bool:\n        \"\"\"Create a new conversation session\"\"\"\n        try:\n            with self._get_connection() as conn:\n                conn.execute(\"\"\"\n                    INSERT OR REPLACE INTO conversation_sessions \n                    (session_id, start_time, mode)\n                    VALUES (?, ?, ?)\n                \"\"\", (session_id, datetime.now(), mode))\n                conn.commit()\n                \n                logger.info(f\"Created conversation session: {session_id}\")\n                return True\n                \n        except Exception as e:\n            logger.error(f\"Error creating conversation session: {e}\")\n            return False\n    \n    async def end_conversation_session(self, session_id: str, \n                                     total_turns: int = 0, \n                                     avg_confidence: float = 0.0) -> bool:\n        \"\"\"End a conversation session\"\"\"\n        try:\n            with self._get_connection() as conn:\n                conn.execute(\"\"\"\n                    UPDATE conversation_sessions \n                    SET end_time = ?, total_turns = ?, avg_confidence = ?\n                    WHERE session_id = ?\n                \"\"\", (datetime.now(), total_turns, avg_confidence, session_id))\n                conn.commit()\n                \n                logger.info(f\"Ended conversation session: {session_id}\")\n                return True\n                \n        except Exception as e:\n            logger.error(f\"Error ending conversation session: {e}\")\n            return False\n    \n    # Learning Data Management\n    \n    async def save_user_pattern(self, pattern: UserPattern) -> bool:\n        \"\"\"Save a user pattern to database\"\"\"\n        try:\n            with self._get_connection() as conn:\n                conn.execute(\"\"\"\n                    INSERT OR REPLACE INTO user_patterns \n                    (pattern_id, pattern_type, pattern_data, frequency, confidence,\n                     first_observed, last_used, success_rate, context_conditions, metadata)\n                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)\n                \"\"\", (\n                    pattern.pattern_id,\n                    pattern.pattern_type.value,\n                    json.dumps(pattern.pattern_data, ensure_ascii=False),\n                    pattern.frequency,\n                    pattern.confidence,\n                    pattern.first_observed,\n                    pattern.last_used,\n                    pattern.success_rate,\n                    json.dumps(pattern.context_conditions, ensure_ascii=False),\n                    json.dumps(pattern.metadata, ensure_ascii=False)\n                ))\n                conn.commit()\n                \n                logger.debug(f\"Saved user pattern: {pattern.pattern_id}\")\n                return True\n                \n        except Exception as e:\n            logger.error(f\"Error saving user pattern: {e}\")\n            return False\n    \n    async def get_user_patterns(self, pattern_type: LearningType = None, \n                              active_only: bool = True) -> List[UserPattern]:\n        \"\"\"Get user patterns from database\"\"\"\n        try:\n            with self._get_connection() as conn:\n                query = \"SELECT * FROM user_patterns WHERE 1=1\"\n                params = []\n                \n                if pattern_type:\n                    query += \" AND pattern_type = ?\"\n                    params.append(pattern_type.value)\n                \n                if active_only:\n                    query += \" AND is_active = TRUE\"\n                \n                query += \" ORDER BY frequency DESC, last_used DESC\"\n                \n                cursor = conn.execute(query, params)\n                rows = cursor.fetchall()\n                \n                patterns = []\n                for row in rows:\n                    pattern = UserPattern(\n                        pattern_id=row['pattern_id'],\n                        pattern_type=LearningType(row['pattern_type']),\n                        pattern_data=json.loads(row['pattern_data']),\n                        frequency=row['frequency'],\n                        confidence=row['confidence'],\n                        first_observed=datetime.fromisoformat(row['first_observed']),\n                        last_used=datetime.fromisoformat(row['last_used']),\n                        success_rate=row['success_rate'],\n                        context_conditions=json.loads(row['context_conditions'] or '{}'),\n                        metadata=json.loads(row['metadata'] or '{}')\n                    )\n                    patterns.append(pattern)\n                \n                return patterns\n                \n        except Exception as e:\n            logger.error(f\"Error getting user patterns: {e}\")\n            return []\n    \n    async def update_pattern_usage(self, pattern_id: str) -> bool:\n        \"\"\"Update pattern usage statistics\"\"\"\n        try:\n            with self._get_connection() as conn:\n                conn.execute(\"\"\"\n                    UPDATE user_patterns \n                    SET frequency = frequency + 1, last_used = ?, updated_at = ?\n                    WHERE pattern_id = ?\n                \"\"\", (datetime.now(), datetime.now(), pattern_id))\n                conn.commit()\n                \n                return conn.total_changes > 0\n                \n        except Exception as e:\n            logger.error(f\"Error updating pattern usage: {e}\")\n            return False\n    \n    # User Preferences Management\n    \n    async def save_user_preference(self, category: str, key: str, \n                                 value: Any, confidence: float = 1.0, \n                                 weight: float = 1.0) -> bool:\n        \"\"\"Save user preference to database\"\"\"\n        try:\n            with self._get_connection() as conn:\n                conn.execute(\"\"\"\n                    INSERT OR REPLACE INTO user_preferences \n                    (category, preference_key, preference_value, confidence, weight, last_updated)\n                    VALUES (?, ?, ?, ?, ?, ?)\n                \"\"\", (\n                    category,\n                    key,\n                    json.dumps(value, ensure_ascii=False),\n                    confidence,\n                    weight,\n                    datetime.now()\n                ))\n                conn.commit()\n                \n                logger.debug(f\"Saved user preference: {category}.{key}\")\n                return True\n                \n        except Exception as e:\n            logger.error(f\"Error saving user preference: {e}\")\n            return False\n    \n    async def get_user_preferences(self, category: str = None) -> Dict[str, Any]:\n        \"\"\"Get user preferences from database\"\"\"\n        try:\n            with self._get_connection() as conn:\n                query = \"SELECT * FROM user_preferences\"\n                params = []\n                \n                if category:\n                    query += \" WHERE category = ?\"\n                    params.append(category)\n                \n                query += \" ORDER BY category, preference_key\"\n                \n                cursor = conn.execute(query, params)\n                rows = cursor.fetchall()\n                \n                preferences = {}\n                for row in rows:\n                    cat = row['category']\n                    key = row['preference_key']\n                    value = json.loads(row['preference_value'])\n                    \n                    if cat not in preferences:\n                        preferences[cat] = {}\n                    \n                    preferences[cat][key] = {\n                        'value': value,\n                        'confidence': row['confidence'],\n                        'weight': row['weight'],\n                        'last_updated': row['last_updated'],\n                        'usage_count': row['usage_count']\n                    }\n                \n                return preferences\n                \n        except Exception as e:\n            logger.error(f\"Error getting user preferences: {e}\")\n            return {}\n    \n    # Command Logging\n    \n    async def log_command(self, command: str, intent: str = None, \n                        success: bool = True, execution_time: float = None, \n                        context: Dict[str, Any] = None) -> bool:\n        \"\"\"Log command execution for analysis\"\"\"\n        try:\n            with self._get_connection() as conn:\n                conn.execute(\"\"\"\n                    INSERT INTO command_log \n                    (timestamp, command, intent, success, execution_time, context)\n                    VALUES (?, ?, ?, ?, ?, ?)\n                \"\"\", (\n                    datetime.now(),\n                    command,\n                    intent,\n                    success,\n                    execution_time,\n                    json.dumps(context or {}, ensure_ascii=False)\n                ))\n                conn.commit()\n                \n                return True\n                \n        except Exception as e:\n            logger.error(f\"Error logging command: {e}\")\n            return False\n    \n    async def get_command_statistics(self, days: int = 30) -> Dict[str, Any]:\n        \"\"\"Get command usage statistics\"\"\"\n        try:\n            with self._get_connection() as conn:\n                since = datetime.now() - timedelta(days=days)\n                \n                # Most used commands\n                cursor = conn.execute(\"\"\"\n                    SELECT command, COUNT(*) as count, AVG(execution_time) as avg_time\n                    FROM command_log \n                    WHERE timestamp >= ? AND success = TRUE\n                    GROUP BY command \n                    ORDER BY count DESC \n                    LIMIT 10\n                \"\"\", (since,))\n                \n                most_used = [dict(row) for row in cursor.fetchall()]\n                \n                # Success rate\n                cursor = conn.execute(\"\"\"\n                    SELECT \n                        SUM(CASE WHEN success = TRUE THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate,\n                        COUNT(*) as total_commands\n                    FROM command_log \n                    WHERE timestamp >= ?\n                \"\"\", (since,))\n                \n                stats_row = cursor.fetchone()\n                \n                # Daily usage pattern\n                cursor = conn.execute(\"\"\"\n                    SELECT \n                        strftime('%H', timestamp) as hour,\n                        COUNT(*) as count\n                    FROM command_log \n                    WHERE timestamp >= ?\n                    GROUP BY hour\n                    ORDER BY hour\n                \"\"\", (since,))\n                \n                hourly_usage = {row['hour']: row['count'] for row in cursor.fetchall()}\n                \n                return {\n                    'most_used_commands': most_used,\n                    'success_rate': stats_row['success_rate'] if stats_row else 0.0,\n                    'total_commands': stats_row['total_commands'] if stats_row else 0,\n                    'hourly_usage': hourly_usage\n                }\n                \n        except Exception as e:\n            logger.error(f\"Error getting command statistics: {e}\")\n            return {}\n    \n    # System Metrics\n    \n    async def save_system_metric(self, metric_name: str, metric_value: float, \n                               metric_unit: str = None, metadata: Dict[str, Any] = None) -> bool:\n        \"\"\"Save system metric to database\"\"\"\n        try:\n            with self._get_connection() as conn:\n                conn.execute(\"\"\"\n                    INSERT INTO system_metrics \n                    (timestamp, metric_name, metric_value, metric_unit, metadata)\n                    VALUES (?, ?, ?, ?, ?)\n                \"\"\", (\n                    datetime.now(),\n                    metric_name,\n                    metric_value,\n                    metric_unit,\n                    json.dumps(metadata or {}, ensure_ascii=False)\n                ))\n                conn.commit()\n                \n                return True\n                \n        except Exception as e:\n            logger.error(f\"Error saving system metric: {e}\")\n            return False\n    \n    # Database Maintenance\n    \n    async def cleanup_old_data(self, days_to_keep: int = 90) -> bool:\n        \"\"\"Clean up old data from database\"\"\"\n        try:\n            cutoff_date = datetime.now() - timedelta(days=days_to_keep)\n            \n            with self._get_connection() as conn:\n                # Clean old conversation turns\n                conn.execute(\n                    \"DELETE FROM conversation_turns WHERE timestamp < ?\",\n                    (cutoff_date,)\n                )\n                \n                # Clean old command logs\n                conn.execute(\n                    \"DELETE FROM command_log WHERE timestamp < ?\",\n                    (cutoff_date,)\n                )\n                \n                # Clean old system metrics\n                conn.execute(\n                    \"DELETE FROM system_metrics WHERE timestamp < ?\",\n                    (cutoff_date,)\n                )\n                \n                # Deactivate very old patterns\n                old_pattern_date = datetime.now() - timedelta(days=days_to_keep * 2)\n                conn.execute(\"\"\"\n                    UPDATE user_patterns \n                    SET is_active = FALSE \n                    WHERE last_used < ? AND frequency < 3\n                \"\"\", (old_pattern_date,))\n                \n                conn.commit()\n                \n                # Vacuum database\n                conn.execute(\"PRAGMA incremental_vacuum\")\n                \n                logger.info(f\"Database cleanup completed: removed data older than {days_to_keep} days\")\n                return True\n                \n        except Exception as e:\n            logger.error(f\"Error during database cleanup: {e}\")\n            return False\n    \n    async def get_database_stats(self) -> Dict[str, Any]:\n        \"\"\"Get database statistics\"\"\"\n        try:\n            with self._get_connection() as conn:\n                stats = {}\n                \n                # Table row counts\n                tables = [\n                    'conversation_sessions', 'conversation_turns', 'user_patterns',\n                    'user_preferences', 'learning_sessions', 'command_log', 'system_metrics'\n                ]\n                \n                for table in tables:\n                    cursor = conn.execute(f\"SELECT COUNT(*) as count FROM {table}\")\n                    stats[f\"{table}_count\"] = cursor.fetchone()['count']\n                \n                # Database size\n                cursor = conn.execute(\"PRAGMA page_count\")\n                page_count = cursor.fetchone()[0]\n                \n                cursor = conn.execute(\"PRAGMA page_size\")\n                page_size = cursor.fetchone()[0]\n                \n                stats['database_size_mb'] = (page_count * page_size) / (1024 * 1024)\n                \n                return stats\n                \n        except Exception as e:\n            logger.error(f\"Error getting database stats: {e}\")\n            return {}\n\n# Example usage and testing\nasync def main():\n    \"\"\"Example usage of Database Manager\"\"\"\n    \n    # Create database manager\n    db_manager = DatabaseManager()\n    \n    # Create a test conversation session\n    session_id = \"test_session_123\"\n    await db_manager.create_conversation_session(session_id, \"continuous\")\n    \n    # Create a test conversation turn\n    turn = ConversationTurn(\n        id=\"test_turn_1\",\n        timestamp=datetime.now(),\n        user_input=\"abrir chrome\",\n        recognized_text=\"abrir chrome\",\n        confidence_score=0.9,\n        intent=IntentType.DIRECT_COMMAND,\n        entities={'applications': ['chrome']},\n        context={'topic': 'navigation'},\n        response=\"Abrindo Chrome...\",\n        response_time=1.2,\n        satisfaction_score=0.8\n    )\n    \n    # Save conversation turn\n    await db_manager.save_conversation_turn(turn, session_id)\n    \n    # Log a command\n    await db_manager.log_command(\"abrir chrome\", \"DIRECT_COMMAND\", True, 1.2)\n    \n    # Save a user preference\n    await db_manager.save_user_preference(\n        \"response_style\", \"verbosity\", \"medium\", confidence=0.8\n    )\n    \n    # Get conversation history\n    history = await db_manager.get_conversation_history(session_id)\n    print(f\"💾 Retrieved {len(history)} conversation turns\")\n    \n    # Get command statistics\n    stats = await db_manager.get_command_statistics()\n    print(f\"📊 Command stats: {stats}\")\n    \n    # Get database statistics\n    db_stats = await db_manager.get_database_stats()\n    print(f\"🗄️  Database stats: {db_stats}\")\n    \n    # End conversation session\n    await db_manager.end_conversation_session(session_id, total_turns=1, avg_confidence=0.9)\n    \n    print(\"Database manager test completed!\")\n\nif __name__ == \"__main__\":\n    asyncio.run(main())"