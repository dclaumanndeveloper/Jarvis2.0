"""
Enhanced Error Handling and Recovery Module for Jarvis 2.0
Provides comprehensive error handling, recovery mechanisms, and performance monitoring
for the voice recording and audio processing systems.
"""

import sys
import time
import traceback
import psutil
import threading
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
import logging

from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QMessageBox, QApplication

# Configure logging
logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """Error categories for classification"""
    AUDIO_DEVICE = "audio_device"
    AUDIO_PROCESSING = "audio_processing"
    MEMORY = "memory"
    THREAD = "thread"
    UI = "ui"
    DATABASE = "database"
    NETWORK = "network"
    SYSTEM = "system"

@dataclass
class ErrorContext:
    """Context information for errors"""
    error_type: str
    category: ErrorCategory
    severity: ErrorSeverity
    timestamp: float
    message: str
    traceback_info: str
    system_state: Dict[str, Any]
    recovery_attempted: bool = False
    recovery_successful: bool = False

class ErrorRecoveryManager:
    """Manages error recovery strategies"""
    
    def __init__(self):
        self.recovery_strategies = {}
        self.error_history = []
        self.recovery_callbacks = {}
        self.max_error_history = 50
        
        # Register default recovery strategies
        self._register_default_strategies()
    
    def _register_default_strategies(self):
        """Register default error recovery strategies"""
        
        # Audio device errors
        self.register_recovery_strategy(
            ErrorCategory.AUDIO_DEVICE,
            self._recover_audio_device
        )
        
        # Audio processing errors
        self.register_recovery_strategy(
            ErrorCategory.AUDIO_PROCESSING,
            self._recover_audio_processing
        )
        
        # Memory errors
        self.register_recovery_strategy(
            ErrorCategory.MEMORY,
            self._recover_memory_issues
        )
        
        # Thread errors
        self.register_recovery_strategy(
            ErrorCategory.THREAD,
            self._recover_thread_issues
        )
        
        # UI errors
        self.register_recovery_strategy(
            ErrorCategory.UI,
            self._recover_ui_issues
        )
    
    def register_recovery_strategy(self, category: ErrorCategory, strategy: Callable):
        """Register a recovery strategy for an error category"""
        self.recovery_strategies[category] = strategy
    
    def register_recovery_callback(self, category: ErrorCategory, callback: Callable):
        """Register a callback to be notified of recovery attempts"""
        if category not in self.recovery_callbacks:
            self.recovery_callbacks[category] = []
        self.recovery_callbacks[category].append(callback)
    
    def handle_error(self, error: Exception, category: ErrorCategory, 
                    severity: ErrorSeverity, context: Dict[str, Any] = None) -> bool:
        """Handle an error with appropriate recovery strategy"""
        
        # Get system state
        try:
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent()
            system_state = {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_mb': memory.available / 1024 / 1024,
            }
        except:
            system_state = {}
        
        # Create error context
        error_context = ErrorContext(
            error_type=type(error).__name__,
            category=category,
            severity=severity,
            timestamp=time.time(),
            message=str(error),
            traceback_info=traceback.format_exc(),
            system_state=system_state
        )
        
        # Add to error history
        self.error_history.append(error_context)
        if len(self.error_history) > self.max_error_history:
            self.error_history.pop(0)
        
        # Log the error
        logger.error(f"Error in {category.value}: {error}")
        
        # Attempt recovery if strategy exists
        recovery_successful = False
        if category in self.recovery_strategies:
            try:
                error_context.recovery_attempted = True
                recovery_successful = self.recovery_strategies[category](error, error_context)
                error_context.recovery_successful = recovery_successful
                
                if recovery_successful:
                    logger.info(f"Recovery successful for {category.value} error")
                else:
                    logger.warning(f"Recovery failed for {category.value} error")
                    
            except Exception as recovery_error:
                logger.error(f"Recovery strategy failed: {recovery_error}")
        
        # Notify callbacks
        if category in self.recovery_callbacks:
            for callback in self.recovery_callbacks[category]:
                try:
                    callback(error_context, recovery_successful)
                except Exception as callback_error:
                    logger.error(f"Recovery callback failed: {callback_error}")
        
        # Handle critical errors
        if severity == ErrorSeverity.CRITICAL and not recovery_successful:
            self._handle_critical_error(error_context)
        
        return recovery_successful
    
    def _recover_audio_device(self, error: Exception, context: ErrorContext) -> bool:
        """Recover from audio device errors"""
        try:
            logger.info("Attempting audio device recovery...")
            
            # Wait for device to become available
            time.sleep(1.0)
            
            # Try to reinitialize PyAudio
            import pyaudio
            test_audio = pyaudio.PyAudio()
            
            # Test device availability
            device_count = test_audio.get_device_count()
            if device_count > 0:
                default_input = test_audio.get_default_input_device_info()
                logger.info(f"Audio device recovery successful. Found {device_count} devices")
                test_audio.terminate()
                return True
            else:
                logger.warning("No audio devices found during recovery")
                test_audio.terminate()
                return False
                
        except Exception as recovery_error:
            logger.error(f"Audio device recovery failed: {recovery_error}")
            return False
    
    def _recover_audio_processing(self, error: Exception, context: ErrorContext) -> bool:
        """Recover from audio processing errors"""
        try:
            logger.info("Attempting audio processing recovery...")
            
            # Check if it's a memory issue
            if "memory" in str(error).lower() or "allocation" in str(error).lower():
                # Try garbage collection
                import gc
                gc.collect()
                time.sleep(0.5)
                return True
            
            # Check if it's a librosa issue
            if "librosa" in str(error).lower():
                # Try reloading librosa
                try:
                    import importlib
                    import librosa
                    importlib.reload(librosa)
                    return True
                except Exception:
                    pass
            
            return False
            
        except Exception as recovery_error:
            logger.error(f"Audio processing recovery failed: {recovery_error}")
            return False
    
    def _recover_memory_issues(self, error: Exception, context: ErrorContext) -> bool:
        """Recover from memory-related errors"""
        try:
            logger.info("Attempting memory recovery...")
            
            # Force garbage collection
            import gc
            gc.collect()
            
            # Check memory usage after cleanup
            import psutil
            memory = psutil.virtual_memory()
            
            if memory.percent < 90:  # If memory usage is now reasonable
                logger.info(f"Memory recovery successful. Usage: {memory.percent}%")
                return True
            else:
                logger.warning(f"Memory still high after recovery: {memory.percent}%")
                return False
                
        except Exception as recovery_error:
            logger.error(f"Memory recovery failed: {recovery_error}")
            return False
    
    def _recover_thread_issues(self, error: Exception, context: ErrorContext) -> bool:
        """Recover from thread-related errors"""
        try:
            logger.info("Attempting thread recovery...")
            
            # Give threads time to cleanup
            time.sleep(1.0)
            
            # Check if thread count is reasonable
            import psutil
            process = psutil.Process()
            thread_count = process.num_threads()
            
            if thread_count < 50:  # Reasonable thread count
                logger.info(f"Thread recovery successful. Count: {thread_count}")
                return True
            else:
                logger.warning(f"Thread count still high: {thread_count}")
                return False
                
        except Exception as recovery_error:
            logger.error(f"Thread recovery failed: {recovery_error}")
            return False
    
    def _recover_ui_issues(self, error: Exception, context: ErrorContext) -> bool:
        """Recover from UI-related errors"""
        try:
            logger.info("Attempting UI recovery...")
            
            # Process pending events
            QApplication.processEvents()
            
            # Small delay for UI to stabilize
            time.sleep(0.1)
            
            return True
            
        except Exception as recovery_error:
            logger.error(f"UI recovery failed: {recovery_error}")
            return False
    
    def _handle_critical_error(self, context: ErrorContext):
        """Handle critical errors that couldn't be recovered"""
        logger.critical(f"Critical error in {context.category.value}: {context.message}")
        
        # Show user notification for critical errors
        try:
            if QApplication.instance():
                QMessageBox.critical(
                    None,
                    "Erro Crítico - Jarvis",
                    f"Um erro crítico ocorreu em {context.category.value}:\\n\\n"
                    f"{context.message}\\n\\n"
                    f"O sistema pode estar instável. Considere reiniciar o Jarvis."
                )
        except Exception as msg_error:
            logger.error(f"Failed to show critical error message: {msg_error}")
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics and health metrics"""
        if not self.error_history:
            return {
                'total_errors': 0,
                'recovery_rate': 100.0,
                'error_categories': {},
                'recent_errors': 0,
                'system_health': 'excellent',
                'system_stressed': False
            }
        
        # Calculate statistics
        total_errors = len(self.error_history)
        recovery_attempts = sum(1 for e in self.error_history if e.recovery_attempted)
        successful_recoveries = sum(1 for e in self.error_history if e.recovery_successful)
        
        recovery_rate = (successful_recoveries / recovery_attempts * 100) if recovery_attempts > 0 else 100.0
        
        # Recent errors (last 5 minutes)
        recent_threshold = time.time() - 300
        recent_errors = sum(1 for e in self.error_history if e.timestamp > recent_threshold)
        
        # Error categories
        category_counts = {}
        for error in self.error_history:
            cat = error.category.value
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        # Determine system health
        if recent_errors == 0 and recovery_rate > 90:
            health = 'excellent'
        elif recent_errors < 3 and recovery_rate > 70:
            health = 'good'
        elif recent_errors < 5 and recovery_rate > 50:
            health = 'fair'
        else:
            health = 'poor'
        
        # Check if system is stressed
        system_stressed = False
        try:
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent()
            system_stressed = memory.percent > 85 or cpu_percent > 80
        except:
            pass
        
        return {
            'total_errors': total_errors,
            'recovery_rate': recovery_rate,
            'error_categories': category_counts,
            'recent_errors': recent_errors,
            'system_health': health,
            'system_stressed': system_stressed
        }

class AudioErrorRecovery:
    """Specialized error recovery for audio systems"""
    
    def __init__(self, error_manager: ErrorRecoveryManager):
        self.error_manager = error_manager
        self.audio_retry_count = 0
        self.max_audio_retries = 3
        self.last_audio_error = None
        
        # Register audio-specific callbacks
        error_manager.register_recovery_callback(
            ErrorCategory.AUDIO_DEVICE, 
            self.on_audio_device_recovery
        )
        error_manager.register_recovery_callback(
            ErrorCategory.AUDIO_PROCESSING, 
            self.on_audio_processing_recovery
        )
    
    def handle_recording_error(self, error: Exception, retry_callback: Callable = None) -> bool:
        """Handle recording-specific errors with retry logic"""
        self.audio_retry_count += 1
        
        if self.audio_retry_count > self.max_audio_retries:
            logger.error(f"Maximum audio retries exceeded ({self.max_audio_retries})")
            return False
        
        # Determine error category
        error_str = str(error).lower()
        if "device" in error_str or "stream" in error_str:
            category = ErrorCategory.AUDIO_DEVICE
        else:
            category = ErrorCategory.AUDIO_PROCESSING
        
        # Handle the error
        recovery_successful = self.error_manager.handle_error(
            error, category, ErrorSeverity.HIGH
        )
        
        if recovery_successful and retry_callback:
            # Try the operation again
            try:
                retry_callback()
                self.audio_retry_count = 0  # Reset on success
                return True
            except Exception as retry_error:
                logger.warning(f"Retry after recovery failed: {retry_error}")
                return False
        
        return recovery_successful
    
    def on_audio_device_recovery(self, context: ErrorContext, success: bool):
        """Callback for audio device recovery attempts"""
        if success:
            self.audio_retry_count = 0
            logger.info("Audio device recovery successful, resetting retry count")
        else:
            logger.warning(f"Audio device recovery failed, retry count: {self.audio_retry_count}")
    
    def on_audio_processing_recovery(self, context: ErrorContext, success: bool):
        """Callback for audio processing recovery attempts"""
        if success:
            logger.info("Audio processing recovery successful")
        else:
            logger.warning("Audio processing recovery failed")

# Global error recovery manager instance
global_error_manager = ErrorRecoveryManager()

def handle_voice_recording_error(error: Exception, retry_callback: Callable = None) -> bool:
    """Convenience function for handling voice recording errors"""
    audio_recovery = AudioErrorRecovery(global_error_manager)
    return audio_recovery.handle_recording_error(error, retry_callback)

def get_system_health() -> Dict[str, Any]:
    """Get current system health statistics"""
    return global_error_manager.get_error_statistics()