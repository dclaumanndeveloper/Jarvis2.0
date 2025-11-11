"""
Enhanced Main System for Jarvis 2.0
Integrates all advanced components into a cohesive intelligent assistant
with sophisticated event-driven architecture and comprehensive state management.
"""

import asyncio
import sys
import os
import time
import threading
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

# PyQt6 imports for UI
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, QThread, pyqtSignal

# Jarvis components
from enhanced_speech import (
    EnhancedSpeechRecognizer, 
    AudioConfig, 
    ConversationState as SpeechState,
    RecognitionResult
)
from conversation_manager import (
    ConversationManager, 
    ConversationMode, 
    ConversationTurn,
    IntentType
)
from learning_engine import (
    LearningEngine, 
    UserPattern, 
    LearningType
)
from enhanced_jarvis_ui import (
    EnhancedJarvisUI, 
    UIState, 
    ConversationMode as UIConversationMode
)
from database_manager import DatabaseManager
from nlp_processor import NLPProcessor

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('jarvis_enhanced.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class SystemState(Enum):
    """Overall system state enumeration"""
    INITIALIZING = "initializing"
    STARTING_UP = "starting_up"
    READY = "ready"
    ACTIVE = "active"
    LEARNING = "learning"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"
    OFFLINE = "offline"

class PerformanceMode(Enum):
    """System performance modes"""
    POWER_SAVER = "power_saver"
    BALANCED = "balanced"
    HIGH_PERFORMANCE = "high_performance"
    ULTRA_PERFORMANCE = "ultra_performance"

@dataclass
class SystemConfig:
    """Enhanced system configuration"""
    # Audio configuration
    audio_config: AudioConfig = field(default_factory=lambda: AudioConfig(
        sample_rate=16000,
        chunk_size=1024,
        channels=1,
        vad_aggressiveness=2,
        silence_timeout=2.0,
        phrase_timeout=1.0,
        confidence_threshold=0.7
    ))
    
    # Conversation configuration
    conversation_mode: ConversationMode = ConversationMode.HYBRID
    context_window_seconds: int = 300
    max_history_turns: int = 50
    proactive_suggestions: bool = True
    learning_enabled: bool = True
    
    # Learning configuration
    pattern_detection: bool = True
    min_pattern_frequency: int = 3
    adaptation_rate: float = 0.1
    feedback_weight: float = 0.3
    performance_tracking: bool = True
    
    # Performance configuration
    performance_mode: PerformanceMode = PerformanceMode.BALANCED
    max_concurrent_threads: int = 4
    memory_threshold_mb: int = 512
    cpu_threshold_percent: float = 80.0
    
    # UI configuration
    animations_enabled: bool = True
    transparency_enabled: bool = True
    always_on_top: bool = False
    minimize_to_tray: bool = True

@dataclass
class SystemMetrics:
    """System performance metrics"""
    startup_time: float = 0.0
    audio_latency_ms: float = 0.0
    recognition_accuracy: float = 0.0
    response_time_ms: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    active_threads: int = 0
    commands_processed: int = 0
    learning_patterns_count: int = 0
    uptime_seconds: float = 0.0

class EnhancedJarvis:
    """
    Enhanced Jarvis 2.0 Main System
    Integrates all components with sophisticated coordination and management
    """
    
    def __init__(self, config: SystemConfig = None):
        """Initialize the enhanced Jarvis system"""
        self.config = config or SystemConfig()
        self.system_state = SystemState.INITIALIZING
        self.startup_time = time.time()
        
        # Performance metrics
        self.metrics = SystemMetrics()
        self.performance_monitor = None
        
        # Component references
        self.database_manager: Optional[DatabaseManager] = None
        self.speech_recognizer: Optional[EnhancedSpeechRecognizer] = None
        self.conversation_manager: Optional[ConversationManager] = None
        self.learning_engine: Optional[LearningEngine] = None
        self.nlp_processor: Optional[NLPProcessor] = None
        self.ui: Optional[EnhancedJarvisUI] = None
        self.qt_app: Optional[QApplication] = None
        
        # Threading and synchronization
        self.main_thread = threading.current_thread()
        self.speech_thread: Optional[QThread] = None
        self.learning_thread: Optional[QThread] = None
        self.shutdown_event = threading.Event()
        
        # Callback management
        self.callbacks = {
            'on_system_state_change': [],
            'on_recognition_result': [],
            'on_conversation_turn': [],
            'on_learning_insight': [],
            'on_error': [],
            'on_performance_alert': []
        }
        
        # Error tracking
        self.error_count = 0
        self.last_error_time = None
        self.recovery_attempts = 0
        
        logger.info("Enhanced Jarvis system initialized")
    
    async def initialize_system(self) -> bool:
        """
        Initialize all system components in proper sequence
        Returns True if initialization successful, False otherwise
        """
        try:
            logger.info("Starting enhanced Jarvis system initialization...")
            self._change_system_state(SystemState.STARTING_UP)
            
            # Phase 1: Core infrastructure
            if not await self._initialize_database():
                logger.error("Database initialization failed")
                return False
            
            if not await self._initialize_qt_application():
                logger.error("Qt application initialization failed")
                return False
            
            # Phase 2: Processing components
            if not await self._initialize_nlp_processor():
                logger.error("NLP processor initialization failed")
                return False
            
            if not await self._initialize_speech_recognition():
                logger.error("Speech recognition initialization failed")
                return False
            
            # Phase 3: Intelligence components
            if not await self._initialize_conversation_manager():
                logger.error("Conversation manager initialization failed")
                return False
            
            if not await self._initialize_learning_engine():
                logger.error("Learning engine initialization failed")
                return False
            
            # Phase 4: User interface
            if not await self._initialize_ui():
                logger.error("UI initialization failed")
                return False
            
            # Phase 5: System integration
            if not await self._setup_component_integration():
                logger.error("Component integration failed")
                return False
            
            # Phase 6: Performance monitoring
            if not await self._initialize_performance_monitoring():
                logger.error("Performance monitoring initialization failed")
                return False
            
            # Calculate startup time
            self.metrics.startup_time = time.time() - self.startup_time
            logger.info(f"System initialization completed in {self.metrics.startup_time:.2f} seconds")
            
            self._change_system_state(SystemState.READY)
            return True
            
        except Exception as e:
            logger.error(f"System initialization failed: {e}")
            self._change_system_state(SystemState.ERROR)
            return False
    
    async def _initialize_database(self) -> bool:
        """Initialize database manager"""
        try:
            logger.info("Initializing database manager...")
            self.database_manager = DatabaseManager()
            await self.database_manager.initialize()
            
            # Verify database connection
            if not await self.database_manager.verify_connection():
                raise Exception("Database connection verification failed")
            
            logger.info("Database manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            return False
    
    async def _initialize_qt_application(self) -> bool:
        """Initialize Qt application"""
        try:
            logger.info("Initializing Qt application...")
            
            # Create QApplication if it doesn't exist
            if not QApplication.instance():
                self.qt_app = QApplication(sys.argv)
                self.qt_app.setQuitOnLastWindowClosed(False)  # Keep running in background
            else:
                self.qt_app = QApplication.instance()
            
            logger.info("Qt application initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Qt application initialization error: {e}")
            return False
    
    async def _initialize_nlp_processor(self) -> bool:
        """Initialize NLP processor"""
        try:
            logger.info("Initializing NLP processor...")
            self.nlp_processor = NLPProcessor()
            await self.nlp_processor.initialize()
            
            logger.info("NLP processor initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"NLP processor initialization error: {e}")
            return False
    
    async def _initialize_speech_recognition(self) -> bool:
        """Initialize enhanced speech recognition"""
        try:
            logger.info("Initializing speech recognition...")
            self.speech_recognizer = EnhancedSpeechRecognizer(self.config.audio_config)
            
            # Test audio devices
            if not await self._test_audio_devices():
                logger.warning("Audio device test failed, but continuing...")
            
            logger.info("Speech recognition initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Speech recognition initialization error: {e}")
            return False
    
    async def _initialize_conversation_manager(self) -> bool:
        """Initialize conversation manager"""
        try:
            logger.info("Initializing conversation manager...")
            self.conversation_manager = ConversationManager(
                mode=self.config.conversation_mode,
                max_context_window=self.config.context_window_seconds
            )
            
            # Connect to NLP processor
            if self.nlp_processor:
                self.conversation_manager.set_nlp_processor(self.nlp_processor)
            
            logger.info("Conversation manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Conversation manager initialization error: {e}")
            return False
    
    async def _initialize_learning_engine(self) -> bool:
        """Initialize learning engine"""
        try:
            logger.info("Initializing learning engine...")
            self.learning_engine = LearningEngine(
                database_manager=self.database_manager,
                min_pattern_frequency=self.config.min_pattern_frequency
            )
            
            await self.learning_engine.initialize()
            
            logger.info("Learning engine initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Learning engine initialization error: {e}")
            return False
    
    async def _initialize_ui(self) -> bool:
        """Initialize enhanced UI"""
        try:
            logger.info("Initializing enhanced UI...")
            self.ui = EnhancedJarvisUI()
            
            # Configure UI based on system settings
            self.ui.set_animations_enabled(self.config.animations_enabled)
            self.ui.set_transparency_enabled(self.config.transparency_enabled)
            
            # Show UI
            self.ui.show()
            if self.config.always_on_top:
                self.ui.setWindowFlag(self.ui.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
            
            logger.info("Enhanced UI initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"UI initialization error: {e}")
            return False
    
    async def _setup_component_integration(self) -> bool:
        """Setup observer pattern callbacks between components"""
        try:
            logger.info("Setting up component integration...")
            
            # Setup speech recognition callbacks
            if self.speech_recognizer:
                self.speech_recognizer.set_callbacks(
                    on_speech_start=self._on_speech_start,
                    on_speech_end=self._on_speech_end,
                    on_recognition_result=self._on_recognition_result,
                    on_state_change=self._on_speech_state_change
                )
            
            # Setup conversation manager callbacks
            if self.conversation_manager:
                self.conversation_manager.set_callbacks(
                    on_intent_classified=self._on_intent_classified,
                    on_response_generated=self._on_response_generated,
                    on_context_updated=self._on_context_updated,
                    on_proactive_suggestion=self._on_proactive_suggestion
                )
            
            # Setup learning engine callbacks
            if self.learning_engine:
                self.learning_engine.set_callbacks(
                    on_pattern_detected=self._on_pattern_detected,
                    on_insight_generated=self._on_insight_generated,
                    on_adaptation_made=self._on_adaptation_made
                )
            
            # Setup UI signal connections
            if self.ui:
                self.ui.state_changed.connect(self._on_ui_state_change)
                self.ui.mode_changed.connect(self._on_ui_mode_change)
            
            logger.info("Component integration setup completed")
            return True
            
        except Exception as e:
            logger.error(f"Component integration setup error: {e}")
            return False
    
    async def _initialize_performance_monitoring(self) -> bool:
        """Initialize performance monitoring system"""
        try:
            logger.info("Initializing performance monitoring...")
            
            # Create performance monitoring timer
            self.performance_monitor = QTimer()
            self.performance_monitor.timeout.connect(self._update_performance_metrics)
            self.performance_monitor.start(5000)  # Update every 5 seconds
            
            logger.info("Performance monitoring initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Performance monitoring initialization error: {e}")
            return False
    
    async def _test_audio_devices(self) -> bool:
        """Test audio input/output devices"""
        try:
            import pyaudio
            audio = pyaudio.PyAudio()
            
            # Test input device
            input_device_count = audio.get_device_count()
            default_input = audio.get_default_input_device_info()
            
            logger.info(f"Audio devices available: {input_device_count}")
            logger.info(f"Default input device: {default_input['name']}")
            
            audio.terminate()
            return True
            
        except Exception as e:
            logger.warning(f"Audio device test failed: {e}")
            return False
    
    def _change_system_state(self, new_state: SystemState):
        """Change system state and notify callbacks"""
        if self.system_state != new_state:
            old_state = self.system_state
            self.system_state = new_state
            logger.info(f"System state changed: {old_state.value} -> {new_state.value}")
            
            # Notify callbacks
            self._trigger_callbacks('on_system_state_change', old_state, new_state)
            
            # Update UI if available
            if self.ui:
                ui_state = self._map_system_to_ui_state(new_state)
                self.ui._change_state(ui_state)
    
    def _map_system_to_ui_state(self, system_state: SystemState) -> UIState:
        """Map system state to UI state"""
        mapping = {
            SystemState.INITIALIZING: UIState.STARTUP,
            SystemState.STARTING_UP: UIState.STARTUP,
            SystemState.READY: UIState.IDLE,
            SystemState.ACTIVE: UIState.LISTENING,
            SystemState.LEARNING: UIState.LEARNING,
            SystemState.ERROR: UIState.ERROR,
            SystemState.SHUTTING_DOWN: UIState.IDLE,
            SystemState.OFFLINE: UIState.ERROR
        }
        return mapping.get(system_state, UIState.IDLE)
    
    # === CALLBACK HANDLERS ===
    
    def _on_speech_start(self):
        """Handle speech start event"""
        logger.debug("Speech detection started")
        self._change_system_state(SystemState.ACTIVE)
        
        if self.ui:
            self.ui.show_listening()
    
    def _on_speech_end(self):
        """Handle speech end event"""
        logger.debug("Speech detection ended")
        
        if self.ui:
            self.ui.show_processing()
    
    def _on_recognition_result(self, result: RecognitionResult):
        """Handle speech recognition result"""
        logger.info(f"Recognition result: '{result.text}' (confidence: {result.confidence:.2f})")
        
        # Update metrics
        self.metrics.commands_processed += 1
        
        # Trigger callback
        self._trigger_callbacks('on_recognition_result', result)
        
        # Pass to conversation manager
        if self.conversation_manager and result.success:
            asyncio.create_task(self.conversation_manager.process_user_input(
                result.text, 
                result.confidence,
                result.audio_features
            ))
        
        # Update UI
        if self.ui:
            self.ui.update_user_query(result.text, result.confidence)
    
    def _on_speech_state_change(self, old_state: SpeechState, new_state: SpeechState):
        """Handle speech recognition state change"""
        logger.debug(f"Speech state changed: {old_state.value} -> {new_state.value}")
        
        # Map to system state
        if new_state == SpeechState.LISTENING:
            self._change_system_state(SystemState.ACTIVE)
        elif new_state == SpeechState.PROCESSING:
            pass  # Keep current state
        elif new_state == SpeechState.IDLE:
            self._change_system_state(SystemState.READY)
    
    def _on_intent_classified(self, intent: IntentType, entities: Dict[str, Any], confidence: float):
        """Handle intent classification result"""
        logger.info(f"Intent classified: {intent.value} (confidence: {confidence:.2f})")
        
        if self.ui:
            self.ui.update_conversation_state(
                f"Intent: {intent.value}",
                confidence,
                f"Entities: {list(entities.keys())}"
            )
    
    def _on_response_generated(self, response: str, response_time: float):
        """Handle response generation"""
        logger.info(f"Response generated in {response_time:.2f}ms: '{response[:50]}...'")
        
        # Update metrics
        self.metrics.response_time_ms = response_time
        
        # Update UI
        if self.ui:
            self.ui.update_response(response)
            self.ui.show_responding()
        
        # Speak response if TTS is available
        self._speak_response(response)
    
    def _on_context_updated(self, context: Dict[str, Any]):
        """Handle conversation context update"""
        logger.debug(f"Context updated: {list(context.keys())}")
        
        if self.ui:
            context_summary = self._create_context_summary(context)
            self.ui.update_conversation_state(
                "Context Updated",
                1.0,
                context_summary
            )
    
    def _on_proactive_suggestion(self, suggestion: str, confidence: float):
        """Handle proactive suggestion from conversation manager"""
        logger.info(f"Proactive suggestion: '{suggestion}' (confidence: {confidence:.2f})")
        
        if self.ui and confidence > 0.8:  # Only show high-confidence suggestions
            self.ui.show_proactive_suggestion(suggestion)
    
    def _on_pattern_detected(self, pattern: UserPattern):
        """Handle learning pattern detection"""
        logger.info(f"Pattern detected: {pattern.pattern_type.value} (confidence: {pattern.confidence:.2f})")
        
        self.metrics.learning_patterns_count += 1
        
        if self.ui:
            self.ui.update_learning_info(
                f"Pattern: {pattern.pattern_type.value}",
                pattern.frequency,
                f"Confidence: {pattern.confidence:.2f}"
            )
    
    def _on_insight_generated(self, insight: str, insight_type: str):
        """Handle learning insight generation"""
        logger.info(f"Learning insight ({insight_type}): {insight}")
        
        if self.ui:
            self.ui.update_learning_info(
                f"Insight: {insight_type}",
                0,
                insight[:50] + "..." if len(insight) > 50 else insight
            )
    
    def _on_adaptation_made(self, adaptation_type: str, details: Dict[str, Any]):
        """Handle system adaptation"""
        logger.info(f"System adapted: {adaptation_type} - {details}")
    
    def _on_ui_state_change(self, new_state: UIState):
        """Handle UI state change"""
        logger.debug(f"UI state changed to: {new_state.value}")
    
    def _on_ui_mode_change(self, new_mode: UIConversationMode):
        """Handle UI conversation mode change"""
        logger.info(f"UI conversation mode changed to: {new_mode.value}")
        
        # Update conversation manager mode
        if self.conversation_manager:
            # Map UI mode to conversation manager mode
            mode_mapping = {
                UIConversationMode.WAKE_WORD: ConversationMode.WAKE_WORD,
                UIConversationMode.CONTINUOUS: ConversationMode.CONTINUOUS,
                UIConversationMode.SESSION_BASED: ConversationMode.SESSION_BASED,
                UIConversationMode.HYBRID: ConversationMode.HYBRID
            }
            conv_mode = mode_mapping.get(new_mode, ConversationMode.HYBRID)
            asyncio.create_task(self.conversation_manager.set_conversation_mode(conv_mode))
    
    # === UTILITY METHODS ===
    
    def _trigger_callbacks(self, callback_type: str, *args):
        """Trigger registered callbacks"""
        for callback in self.callbacks.get(callback_type, []):
            try:
                callback(*args)
            except Exception as e:
                logger.error(f"Callback error ({callback_type}): {e}")
    
    def _speak_response(self, response: str):
        """Speak response using TTS (placeholder for now)"""
        # TODO: Implement TTS integration
        logger.debug(f"TTS: {response}")
    
    def _create_context_summary(self, context: Dict[str, Any]) -> str:
        """Create a summary of conversation context"""
        summary_parts = []
        
        if 'current_topic' in context and context['current_topic']:
            summary_parts.append(f"Topic: {context['current_topic']}")
        
        if 'last_command' in context and context['last_command']:
            summary_parts.append(f"Last: {context['last_command'][:20]}...")
        
        if 'active_variables' in context and context['active_variables']:
            var_count = len(context['active_variables'])
            summary_parts.append(f"Variables: {var_count}")
        
        return " | ".join(summary_parts) if summary_parts else "No active context"
    
    def _update_performance_metrics(self):
        """Update system performance metrics"""
        try:
            import psutil
            import threading
            
            # Update basic metrics
            self.metrics.uptime_seconds = time.time() - self.startup_time
            self.metrics.memory_usage_mb = psutil.Process().memory_info().rss / 1024 / 1024
            self.metrics.cpu_usage_percent = psutil.Process().cpu_percent()
            self.metrics.active_threads = threading.active_count()
            
            # Check thresholds and trigger alerts if needed
            self._check_performance_thresholds()
            
        except Exception as e:
            logger.warning(f"Performance metrics update failed: {e}")
    
    def _check_performance_thresholds(self):
        """Check performance thresholds and trigger alerts"""
        alerts = []
        
        if self.metrics.memory_usage_mb > self.config.memory_threshold_mb:
            alerts.append(f"High memory usage: {self.metrics.memory_usage_mb:.1f}MB")
        
        if self.metrics.cpu_usage_percent > self.config.cpu_threshold_percent:
            alerts.append(f"High CPU usage: {self.metrics.cpu_usage_percent:.1f}%")
        
        if alerts:
            self._trigger_callbacks('on_performance_alert', alerts)
    
    # === SYSTEM CONTROL METHODS ===
    
    async def start_conversation_loop(self):
        """Start the main conversation loop"""
        try:
            logger.info("Starting conversation loop...")
            self._change_system_state(SystemState.ACTIVE)
            
            if self.speech_recognizer:
                await self.speech_recognizer.start_continuous_listening()
            
            logger.info("Conversation loop started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start conversation loop: {e}")
            self._change_system_state(SystemState.ERROR)
    
    async def stop_conversation_loop(self):
        """Stop the conversation loop"""
        try:
            logger.info("Stopping conversation loop...")
            
            if self.speech_recognizer:
                await self.speech_recognizer.stop_listening()
            
            self._change_system_state(SystemState.READY)
            logger.info("Conversation loop stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop conversation loop: {e}")
    
    def register_callback(self, callback_type: str, callback: Callable):
        """Register a callback function"""
        if callback_type in self.callbacks:
            self.callbacks[callback_type].append(callback)
        else:
            logger.warning(f"Unknown callback type: {callback_type}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            'system_state': self.system_state.value,
            'uptime_seconds': self.metrics.uptime_seconds,
            'startup_time': self.metrics.startup_time,
            'commands_processed': self.metrics.commands_processed,
            'learning_patterns': self.metrics.learning_patterns_count,
            'memory_usage_mb': self.metrics.memory_usage_mb,
            'cpu_usage_percent': self.metrics.cpu_usage_percent,
            'active_threads': self.metrics.active_threads,
            'components_status': {
                'database': self.database_manager is not None,
                'speech_recognition': self.speech_recognizer is not None,
                'conversation_manager': self.conversation_manager is not None,
                'learning_engine': self.learning_engine is not None,
                'ui': self.ui is not None and self.ui.isVisible()
            }
        }
    
    # === ERROR HANDLING AND RECOVERY ===
    
    async def handle_system_error(self, error: Exception, component: str = "unknown"):
        """Handle system errors with recovery attempts"""
        self.error_count += 1
        self.last_error_time = time.time()
        
        logger.error(f"System error in {component}: {error}")
        
        # Trigger error callbacks
        self._trigger_callbacks('on_error', error, component)
        
        # Attempt recovery based on error type and component
        recovery_success = await self._attempt_error_recovery(error, component)
        
        if not recovery_success:
            self._change_system_state(SystemState.ERROR)
            
            # If too many errors, consider shutdown
            if self.error_count > 10 and self.last_error_time - self.startup_time < 300:
                logger.critical("Too many errors during startup, initiating shutdown")
                await self.shutdown()
    
    async def _attempt_error_recovery(self, error: Exception, component: str) -> bool:
        """Attempt to recover from specific errors"""
        try:
            self.recovery_attempts += 1
            logger.info(f"Attempting error recovery for {component} (attempt {self.recovery_attempts})")
            
            # Component-specific recovery strategies
            if component == "speech_recognition":
                return await self._recover_speech_recognition(error)
            elif component == "conversation_manager":
                return await self._recover_conversation_manager(error)
            elif component == "learning_engine":
                return await self._recover_learning_engine(error)
            elif component == "ui":
                return await self._recover_ui(error)
            elif component == "database":
                return await self._recover_database(error)
            else:
                # Generic recovery attempt
                return await self._generic_recovery(error, component)
        
        except Exception as recovery_error:
            logger.error(f"Recovery attempt failed: {recovery_error}")
            return False
    
    async def _recover_speech_recognition(self, error: Exception) -> bool:
        """Recover speech recognition component"""
        try:
            logger.info("Recovering speech recognition...")
            
            # Stop current recognition
            if self.speech_recognizer:
                await self.speech_recognizer.stop_listening()
            
            # Reinitialize with fallback settings
            fallback_config = AudioConfig(
                sample_rate=16000,
                chunk_size=2048,  # Larger chunk size
                vad_aggressiveness=1,  # Less aggressive VAD
                confidence_threshold=0.5  # Lower threshold
            )
            
            self.speech_recognizer = EnhancedSpeechRecognizer(fallback_config)
            
            # Reestablish callbacks
            self.speech_recognizer.set_callbacks(
                on_speech_start=self._on_speech_start,
                on_speech_end=self._on_speech_end,
                on_recognition_result=self._on_recognition_result,
                on_state_change=self._on_speech_state_change
            )
            
            logger.info("Speech recognition recovery successful")
            return True
            
        except Exception as e:
            logger.error(f"Speech recognition recovery failed: {e}")
            return False
    
    async def _recover_conversation_manager(self, error: Exception) -> bool:
        """Recover conversation manager component"""
        try:
            logger.info("Recovering conversation manager...")
            
            # Reset conversation state
            if self.conversation_manager:
                await self.conversation_manager.reset_context()
            
            logger.info("Conversation manager recovery successful")
            return True
            
        except Exception as e:
            logger.error(f"Conversation manager recovery failed: {e}")
            return False
    
    async def _recover_learning_engine(self, error: Exception) -> bool:
        """Recover learning engine component"""
        try:
            logger.info("Recovering learning engine...")
            
            # Reinitialize learning engine with basic settings
            if self.learning_engine:
                await self.learning_engine.reset_learning_state()
            
            logger.info("Learning engine recovery successful")
            return True
            
        except Exception as e:
            logger.error(f"Learning engine recovery failed: {e}")
            return False
    
    async def _recover_ui(self, error: Exception) -> bool:
        """Recover UI component"""
        try:
            logger.info("Recovering UI...")
            
            # Hide and show UI to reset state
            if self.ui:
                self.ui.hide()
                await asyncio.sleep(0.5)
                self.ui.show()
                self.ui._change_state(UIState.IDLE)
            
            logger.info("UI recovery successful")
            return True
            
        except Exception as e:
            logger.error(f"UI recovery failed: {e}")
            return False
    
    async def _recover_database(self, error: Exception) -> bool:
        """Recover database connection"""
        try:
            logger.info("Recovering database connection...")
            
            # Attempt database reconnection
            if self.database_manager:
                await self.database_manager.reconnect()
            
            logger.info("Database recovery successful")
            return True
            
        except Exception as e:
            logger.error(f"Database recovery failed: {e}")
            return False
    
    async def _generic_recovery(self, error: Exception, component: str) -> bool:
        """Generic recovery strategy"""
        try:
            logger.info(f"Attempting generic recovery for {component}...")
            
            # Wait a moment for transient issues to resolve
            await asyncio.sleep(1.0)
            
            # Reset component state if possible
            # This is a placeholder for component-specific reset logic
            
            logger.info(f"Generic recovery for {component} completed")
            return True
            
        except Exception as e:
            logger.error(f"Generic recovery failed: {e}")
            return False
    
    # === GRACEFUL SHUTDOWN ===
    
    async def shutdown(self, force: bool = False):
        """Gracefully shutdown the enhanced Jarvis system"""
        try:
            logger.info("Starting system shutdown...")
            self._change_system_state(SystemState.SHUTTING_DOWN)
            
            # Set shutdown event
            self.shutdown_event.set()
            
            # Stop conversation loop
            await self.stop_conversation_loop()
            
            # Stop performance monitoring
            if self.performance_monitor:
                self.performance_monitor.stop()
            
            # Shutdown components in reverse order
            await self._shutdown_learning_engine()
            await self._shutdown_conversation_manager()
            await self._shutdown_speech_recognition()
            await self._shutdown_ui()
            await self._shutdown_database()
            
            # Calculate final metrics
            self.metrics.uptime_seconds = time.time() - self.startup_time
            
            logger.info(f"System shutdown completed. Total uptime: {self.metrics.uptime_seconds:.2f} seconds")
            logger.info(f"Commands processed: {self.metrics.commands_processed}")
            logger.info(f"Patterns learned: {self.metrics.learning_patterns_count}")
            
            self._change_system_state(SystemState.OFFLINE)
            
        except Exception as e:
            logger.error(f"Shutdown error: {e}")
            if force:
                logger.warning("Forcing immediate shutdown")
                sys.exit(1)
    
    async def _shutdown_learning_engine(self):
        """Shutdown learning engine"""
        try:
            if self.learning_engine:
                await self.learning_engine.save_learning_state()
                logger.info("Learning engine shutdown completed")
        except Exception as e:
            logger.error(f"Learning engine shutdown error: {e}")
    
    async def _shutdown_conversation_manager(self):
        """Shutdown conversation manager"""
        try:
            if self.conversation_manager:
                await self.conversation_manager.save_conversation_history()
                logger.info("Conversation manager shutdown completed")
        except Exception as e:
            logger.error(f"Conversation manager shutdown error: {e}")
    
    async def _shutdown_speech_recognition(self):
        """Shutdown speech recognition"""
        try:
            if self.speech_recognizer:
                await self.speech_recognizer.stop_listening()
                logger.info("Speech recognition shutdown completed")
        except Exception as e:
            logger.error(f"Speech recognition shutdown error: {e}")
    
    async def _shutdown_ui(self):
        """Shutdown UI"""
        try:
            if self.ui:
                self.ui.close()
                logger.info("UI shutdown completed")
        except Exception as e:
            logger.error(f"UI shutdown error: {e}")
    
    async def _shutdown_database(self):
        """Shutdown database"""
        try:
            if self.database_manager:
                await self.database_manager.close_connection()
                logger.info("Database shutdown completed")
        except Exception as e:
            logger.error(f"Database shutdown error: {e}")


def create_default_config() -> SystemConfig:
    """Create default system configuration"""
    return SystemConfig(
        audio_config=AudioConfig(),
        conversation_mode=ConversationMode.HYBRID,
        learning_enabled=True,
        performance_mode=PerformanceMode.BALANCED
    )


async def main():
    """Main entry point for Enhanced Jarvis 2.0"""
    try:
        logger.info("=== Enhanced Jarvis 2.0 Starting ===")
        
        # Create system configuration
        config = create_default_config()
        
        # Initialize enhanced Jarvis system
        jarvis = EnhancedJarvis(config)
        
        # Initialize all components
        if not await jarvis.initialize_system():
            logger.error("System initialization failed")
            return 1
        
        # Start conversation loop
        await jarvis.start_conversation_loop()
        
        # Keep the system running
        try:
            if jarvis.qt_app:
                # Run Qt event loop
                logger.info("Starting Qt application event loop")
                jarvis.qt_app.exec()
            else:
                # Fallback: simple event loop
                logger.info("Starting simple event loop")
                while not jarvis.shutdown_event.is_set():
                    await asyncio.sleep(1)
        
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        
        finally:
            # Graceful shutdown
            await jarvis.shutdown()
        
        return 0
        
    except Exception as e:
        logger.critical(f"Critical system error: {e}")
        return 1


if __name__ == "__main__":
    try:
        # Set up asyncio event loop
        if sys.platform == "win32":
            # Windows-specific event loop policy
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        # Run the main function
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        sys.exit(1)