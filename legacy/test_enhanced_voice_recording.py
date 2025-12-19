"""
Test Script for Enhanced Voice Recording Implementation
Tests the enhanced voice recording system with threaded audio processing
and error recovery mechanisms.
"""

import sys
import os
import time
import logging
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget, QLabel
from PyQt6.QtCore import QTimer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_imports():
    """Test if all required modules can be imported"""
    print("=== Testing Imports ===")
    
    try:
        # Test basic audio libraries
        import pyaudio
        print("✅ PyAudio imported successfully")
        
        import librosa
        print("✅ Librosa imported successfully")
        
        import numpy as np
        print("✅ NumPy imported successfully")
        
        # Test enhanced voice recording module
        from enhanced_voice_recording import (
            EnhancedVoiceRegistrationWidget, AudioConfig, RecordingState,
            AudioRecordingThread, AudioProcessingThread, SafeAudioStream
        )
        print("✅ Enhanced voice recording module imported successfully")
        
        # Test error recovery module
        from error_recovery import (
            ErrorRecoveryManager, handle_voice_recording_error,
            ErrorCategory, ErrorSeverity, get_system_health
        )
        print("✅ Error recovery module imported successfully")
        
        # Test unified UI integration
        from unified_jarvis_ui import UnifiedJarvisUI
        print("✅ Unified UI module imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during import: {e}")
        return False

def test_audio_config():
    """Test audio configuration"""
    print("\\n=== Testing Audio Configuration ===")
    
    try:
        from enhanced_voice_recording import AudioConfig
        
        # Test default configuration
        config = AudioConfig()
        assert config.sample_rate == 16000
        assert config.chunk_size == 1024
        assert config.channels == 1
        print("✅ Default audio configuration valid")
        
        # Test custom configuration
        custom_config = AudioConfig(
            sample_rate=22050,
            chunk_size=2048,
            max_recording_duration=15
        )
        assert custom_config.sample_rate == 22050
        assert custom_config.chunk_size == 2048
        assert custom_config.max_recording_duration == 15
        print("✅ Custom audio configuration valid")
        
        return True
        
    except Exception as e:
        print(f"❌ Audio configuration test failed: {e}")
        return False

def test_safe_audio_stream():
    """Test SafeAudioStream without actually opening stream"""
    print("\\n=== Testing SafeAudioStream ===")
    
    try:
        from enhanced_voice_recording import SafeAudioStream, AudioConfig
        
        config = AudioConfig()
        stream = SafeAudioStream(config)
        
        # Test initialization
        assert stream.config == config
        assert stream.stream is None
        assert stream.retry_count == 0
        assert not stream.is_active
        print("✅ SafeAudioStream initialization successful")
        
        # Test cleanup without stream
        stream.cleanup()
        print("✅ SafeAudioStream cleanup successful")
        
        return True
        
    except Exception as e:
        print(f"❌ SafeAudioStream test failed: {e}")
        return False

def test_recording_session():
    """Test RecordingSession class"""
    print("\\n=== Testing RecordingSession ===")
    
    try:
        from enhanced_voice_recording import RecordingSession, RecordingState
        import numpy as np
        
        session = RecordingSession(required_samples=3)
        
        # Test initialization
        assert session.required_samples == 3
        assert session.samples_recorded == 0
        assert session.current_state == RecordingState.IDLE
        print("✅ RecordingSession initialization successful")
        
        # Test session start
        session.start_session()
        assert session.current_state == RecordingState.IDLE
        assert len(session.voice_samples) == 0
        print("✅ RecordingSession start successful")
        
        # Test adding samples
        sample1 = np.random.rand(13)
        session.add_sample(sample1)
        assert session.samples_recorded == 1
        assert len(session.voice_samples) == 1
        print("✅ Sample addition successful")
        
        # Test completion
        session.add_sample(np.random.rand(13))
        session.add_sample(np.random.rand(13))
        assert session.samples_recorded == 3
        assert session.current_state == RecordingState.COMPLETED
        print("✅ RecordingSession completion successful")
        
        # Test average features
        avg_features = session.get_average_features()
        assert avg_features is not None
        assert len(avg_features) == 13
        print("✅ Average features calculation successful")
        
        return True
        
    except Exception as e:
        print(f"❌ RecordingSession test failed: {e}")
        return False

def test_error_recovery():
    """Test error recovery system"""
    print("\\n=== Testing Error Recovery ===")
    
    try:
        from error_recovery import (
            ErrorRecoveryManager, ErrorCategory, ErrorSeverity,
            get_system_health, handle_voice_recording_error
        )
        
        # Test system health
        health = get_system_health()
        assert isinstance(health, dict)
        assert 'system_health' in health
        assert 'total_errors' in health
        print(f"✅ System health check successful: {health['system_health']}")
        
        # Test error handling
        manager = ErrorRecoveryManager()
        test_error = ValueError("Test error")
        
        # Handle a test error
        result = manager.handle_error(
            test_error, 
            ErrorCategory.AUDIO_PROCESSING, 
            ErrorSeverity.LOW
        )
        print(f"✅ Error handling successful: recovery={result}")
        
        # Test voice recording error handler
        def dummy_retry():
            return True
        
        recovery_result = handle_voice_recording_error(test_error, dummy_retry)
        print(f"✅ Voice recording error handler successful: recovery={recovery_result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error recovery test failed: {e}")
        return False

def test_audio_devices():
    """Test audio device availability"""
    print("\\n=== Testing Audio Devices ===")
    
    try:
        import pyaudio
        
        audio = pyaudio.PyAudio()
        device_count = audio.get_device_count()
        
        print(f"✅ Found {device_count} audio devices")
        
        if device_count > 0:
            try:
                default_input = audio.get_default_input_device_info()
                print(f"✅ Default input device: {default_input['name']}")
                
                # Test if we can get input device info
                input_devices = []
                for i in range(device_count):
                    device_info = audio.get_device_info_by_index(i)
                    if device_info['maxInputChannels'] > 0:
                        input_devices.append(device_info['name'])
                
                print(f"✅ Found {len(input_devices)} input devices")
                
            except Exception as device_error:
                print(f"⚠️  Default input device error: {device_error}")
        
        audio.terminate()
        return device_count > 0
        
    except Exception as e:
        print(f"❌ Audio device test failed: {e}")
        return False

class TestVoiceRegistrationWidget(QWidget):
    """Test widget to manually test the enhanced voice registration"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test Enhanced Voice Registration")
        self.resize(400, 300)
        
        layout = QVBoxLayout(self)
        
        # Status label
        self.status_label = QLabel("Clique no botão para testar o registro de voz aprimorado")
        layout.addWidget(self.status_label)
        
        # Test button
        self.test_button = QPushButton("Testar Registro de Voz Aprimorado")
        self.test_button.clicked.connect(self.test_voice_registration)
        layout.addWidget(self.test_button)
        
        # System health button
        self.health_button = QPushButton("Verificar Saúde do Sistema")
        self.health_button.clicked.connect(self.check_system_health)
        layout.addWidget(self.health_button)
        
        # Exit button
        self.exit_button = QPushButton("Sair")
        self.exit_button.clicked.connect(self.close)
        layout.addWidget(self.exit_button)
    
    def test_voice_registration(self):
        """Test the enhanced voice registration widget"""
        try:
            from enhanced_voice_recording import EnhancedVoiceRegistrationWidget
            
            self.status_label.setText("Abrindo diálogo de registro de voz...")
            
            # Create and show enhanced registration dialog
            registration_dialog = EnhancedVoiceRegistrationWidget(self)
            registration_dialog.registration_completed.connect(self.on_registration_completed)
            registration_dialog.exec()
            
        except Exception as e:
            self.status_label.setText(f"Erro ao abrir registro de voz: {e}")
            logger.error(f"Voice registration test error: {e}")
    
    def on_registration_completed(self, profile):
        """Handle registration completion"""
        self.status_label.setText(
            f"Registro concluído! Amostras: {profile.sample_count}, "
            f"Threshold: {profile.threshold:.2f}"
        )
        logger.info("Voice registration test completed successfully")
    
    def check_system_health(self):
        """Check and display system health"""
        try:
            from error_recovery import get_system_health
            
            health = get_system_health()
            health_text = (
                f"Saúde: {health['system_health']} | "
                f"Erros: {health['total_errors']} | "
                f"Taxa de Recuperação: {health['recovery_rate']:.1f}%"
            )
            
            if health['system_stressed']:
                health_text += " | SISTEMA SOB ESTRESSE"
            
            self.status_label.setText(health_text)
            
        except Exception as e:
            self.status_label.setText(f"Erro ao verificar saúde: {e}")

def run_comprehensive_tests():
    """Run all tests"""
    print("🚀 Starting Enhanced Voice Recording Tests\\n")
    
    tests = [
        ("Imports", test_imports),
        ("Audio Configuration", test_audio_config),
        ("SafeAudioStream", test_safe_audio_stream),
        ("RecordingSession", test_recording_session),
        ("Error Recovery", test_error_recovery),
        ("Audio Devices", test_audio_devices),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} test failed")
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
    
    print(f"\\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Enhanced voice recording is ready.")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
    
    return passed == total

def main():
    """Main test application"""
    
    # Run comprehensive tests first
    tests_passed = run_comprehensive_tests()
    
    if not tests_passed:
        print("\\n❌ Critical tests failed. Manual testing may not work properly.")
        return
    
    # Create Qt application for manual testing
    app = QApplication(sys.argv)
    
    print("\\n🖥️  Starting manual test interface...")
    test_widget = TestVoiceRegistrationWidget()
    test_widget.show()
    
    # Add auto-close timer for automated testing
    if "--auto-close" in sys.argv:
        timer = QTimer()
        timer.timeout.connect(app.quit)
        timer.start(10000)  # Close after 10 seconds
        print("Auto-close mode: Application will close in 10 seconds")
    
    try:
        app.exec()
    except KeyboardInterrupt:
        print("\\n⏹️  Test interrupted by user")

if __name__ == "__main__":
    main()