"""
Test suite for Enhanced Main System
Validates the integration and functionality of the enhanced_main.py implementation
"""

import asyncio
import unittest
import sys
import os
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import the enhanced main system
from enhanced_main import (
    EnhancedJarvis,
    SystemConfig,
    SystemState,
    PerformanceMode,
    create_default_config
)

class TestEnhancedJarvisInitialization(unittest.TestCase):
    """Test system initialization and configuration"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = create_default_config()
        
    def test_default_config_creation(self):
        """Test default configuration creation"""
        config = create_default_config()
        
        self.assertIsNotNone(config)
        self.assertEqual(config.performance_mode, PerformanceMode.BALANCED)
        self.assertTrue(config.learning_enabled)
        self.assertTrue(config.pattern_detection)
        
    def test_jarvis_initialization(self):
        """Test EnhancedJarvis initialization"""
        jarvis = EnhancedJarvis(self.config)
        
        self.assertEqual(jarvis.system_state, SystemState.INITIALIZING)
        self.assertIsNotNone(jarvis.config)
        self.assertIsNotNone(jarvis.metrics)
        self.assertEqual(jarvis.error_count, 0)
        
    def test_callback_registration(self):
        """Test callback registration system"""
        jarvis = EnhancedJarvis(self.config)
        
        # Create mock callback
        mock_callback = Mock()
        
        # Register callback
        jarvis.register_callback('on_system_state_change', mock_callback)
        
        # Verify callback is registered
        self.assertIn(mock_callback, jarvis.callbacks['on_system_state_change'])

class TestSystemStateManagement(unittest.TestCase):
    """Test system state management"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = create_default_config()
        self.jarvis = EnhancedJarvis(self.config)
        
    def test_state_change_notification(self):
        """Test state change notifications"""
        # Create mock callback
        mock_callback = Mock()
        self.jarvis.register_callback('on_system_state_change', mock_callback)
        
        # Change state
        self.jarvis._change_system_state(SystemState.READY)
        
        # Verify callback was called
        mock_callback.assert_called_once_with(SystemState.INITIALIZING, SystemState.READY)
        self.assertEqual(self.jarvis.system_state, SystemState.READY)
        
    def test_ui_state_mapping(self):
        """Test system state to UI state mapping"""
        from enhanced_jarvis_ui import UIState
        
        # Test various state mappings
        ui_state = self.jarvis._map_system_to_ui_state(SystemState.READY)
        self.assertEqual(ui_state, UIState.IDLE)
        
        ui_state = self.jarvis._map_system_to_ui_state(SystemState.ACTIVE)
        self.assertEqual(ui_state, UIState.LISTENING)
        
        ui_state = self.jarvis._map_system_to_ui_state(SystemState.ERROR)
        self.assertEqual(ui_state, UIState.ERROR)

class TestComponentIntegration(unittest.TestCase):
    """Test component integration and callbacks"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = create_default_config()
        self.jarvis = EnhancedJarvis(self.config)
        
    @patch('enhanced_main.EnhancedSpeechRecognizer')
    @patch('enhanced_main.ConversationManager')
    @patch('enhanced_main.LearningEngine')
    @patch('enhanced_main.EnhancedJarvisUI')
    @patch('enhanced_main.DatabaseManager')
    async def test_component_initialization_sequence(self, mock_db, mock_ui, mock_learning, mock_conv, mock_speech):
        """Test component initialization sequence"""
        # Setup mocks
        mock_db.return_value.initialize = AsyncMock(return_value=None)
        mock_db.return_value.verify_connection = AsyncMock(return_value=True)
        
        mock_speech.return_value = Mock()
        mock_conv.return_value = Mock()
        mock_learning.return_value.initialize = AsyncMock(return_value=None)
        mock_ui.return_value = Mock()
        
        # Mock Qt application
        with patch('enhanced_main.QApplication') as mock_qapp:
            mock_qapp.instance.return_value = None
            mock_qapp.return_value = Mock()
            
            # Initialize system
            result = await self.jarvis.initialize_system()
            
            # Verify initialization succeeded
            self.assertTrue(result)
            self.assertEqual(self.jarvis.system_state, SystemState.READY)
            
            # Verify components were created
            self.assertIsNotNone(self.jarvis.database_manager)
            self.assertIsNotNone(self.jarvis.speech_recognizer)
            self.assertIsNotNone(self.jarvis.conversation_manager)
            self.assertIsNotNone(self.jarvis.learning_engine)
            self.assertIsNotNone(self.jarvis.ui)

class TestErrorHandlingAndRecovery(unittest.TestCase):
    """Test error handling and recovery mechanisms"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = create_default_config()
        self.jarvis = EnhancedJarvis(self.config)
        
    async def test_error_handling(self):
        """Test system error handling"""
        # Simulate an error
        test_error = Exception("Test error")
        
        # Handle the error
        await self.jarvis.handle_system_error(test_error, "test_component")
        
        # Verify error was tracked
        self.assertEqual(self.jarvis.error_count, 1)
        self.assertIsNotNone(self.jarvis.last_error_time)
        
    async def test_recovery_attempt(self):
        """Test error recovery attempts"""
        test_error = Exception("Test error")
        
        # Mock recovery method
        with patch.object(self.jarvis, '_generic_recovery', return_value=True) as mock_recovery:
            result = await self.jarvis._attempt_error_recovery(test_error, "unknown_component")
            
            # Verify recovery was attempted
            self.assertTrue(result)
            mock_recovery.assert_called_once_with(test_error, "unknown_component")

class TestPerformanceMonitoring(unittest.TestCase):
    """Test performance monitoring features"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = create_default_config()
        self.jarvis = EnhancedJarvis(self.config)
        
    @patch('enhanced_main.psutil.Process')
    def test_performance_metrics_update(self, mock_process):
        """Test performance metrics updating"""
        # Mock psutil
        mock_process.return_value.memory_info.return_value.rss = 100 * 1024 * 1024  # 100MB
        mock_process.return_value.cpu_percent.return_value = 25.0
        
        # Update metrics
        self.jarvis._update_performance_metrics()
        
        # Verify metrics were updated
        self.assertEqual(self.jarvis.metrics.memory_usage_mb, 100.0)
        self.assertEqual(self.jarvis.metrics.cpu_usage_percent, 25.0)
        
    def test_system_status(self):
        """Test system status reporting"""
        status = self.jarvis.get_system_status()
        
        # Verify status structure
        self.assertIn('system_state', status)
        self.assertIn('uptime_seconds', status)
        self.assertIn('components_status', status)
        
        # Verify component status tracking
        components = status['components_status']
        self.assertIn('database', components)
        self.assertIn('speech_recognition', components)
        self.assertIn('conversation_manager', components)
        self.assertIn('learning_engine', components)
        self.assertIn('ui', components)

class TestGracefulShutdown(unittest.TestCase):
    """Test graceful shutdown procedures"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = create_default_config()
        self.jarvis = EnhancedJarvis(self.config)
        
    async def test_graceful_shutdown(self):
        """Test graceful system shutdown"""
        # Setup mock components
        self.jarvis.learning_engine = Mock()
        self.jarvis.learning_engine.save_learning_state = AsyncMock()
        
        self.jarvis.conversation_manager = Mock()
        self.jarvis.conversation_manager.save_conversation_history = AsyncMock()
        
        self.jarvis.speech_recognizer = Mock()
        self.jarvis.speech_recognizer.stop_listening = AsyncMock()
        
        self.jarvis.ui = Mock()
        self.jarvis.database_manager = Mock()
        self.jarvis.database_manager.close_connection = AsyncMock()
        
        # Perform shutdown
        await self.jarvis.shutdown()
        
        # Verify shutdown state
        self.assertEqual(self.jarvis.system_state, SystemState.OFFLINE)
        self.assertTrue(self.jarvis.shutdown_event.is_set())
        
        # Verify component shutdown methods were called
        self.jarvis.learning_engine.save_learning_state.assert_called_once()
        self.jarvis.conversation_manager.save_conversation_history.assert_called_once()
        self.jarvis.speech_recognizer.stop_listening.assert_called_once()
        self.jarvis.database_manager.close_connection.assert_called_once()

async def run_async_tests():
    """Run async test cases"""
    # Create test suite for async tests
    suite = unittest.TestSuite()
    
    # Add async test cases
    test_integration = TestComponentIntegration()
    test_integration.setUp()
    
    test_error = TestErrorHandlingAndRecovery()
    test_error.setUp()
    
    test_shutdown = TestGracefulShutdown()
    test_shutdown.setUp()
    
    # Run async tests manually
    try:
        await test_integration.test_component_initialization_sequence()
        print("✓ Component initialization test passed")
    except Exception as e:
        print(f"✗ Component initialization test failed: {e}")
    
    try:
        await test_error.test_error_handling()
        print("✓ Error handling test passed")
    except Exception as e:
        print(f"✗ Error handling test failed: {e}")
    
    try:
        await test_error.test_recovery_attempt()
        print("✓ Recovery attempt test passed")
    except Exception as e:
        print(f"✗ Recovery attempt test failed: {e}")
    
    try:
        await test_shutdown.test_graceful_shutdown()
        print("✓ Graceful shutdown test passed")
    except Exception as e:
        print(f"✗ Graceful shutdown test failed: {e}")

def main():
    """Main test execution"""
    print("=== Enhanced Jarvis Main System Tests ===")
    
    # Run synchronous tests
    print("\n--- Running Synchronous Tests ---")
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add synchronous test classes
    suite.addTests(loader.loadTestsFromTestCase(TestEnhancedJarvisInitialization))
    suite.addTests(loader.loadTestsFromTestCase(TestSystemStateManagement))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformanceMonitoring))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Run asynchronous tests
    print("\n--- Running Asynchronous Tests ---")
    asyncio.run(run_async_tests())
    
    # Summary
    print(f"\n=== Test Summary ===")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    return len(result.failures) + len(result.errors) == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)