"""
Diagnostic Script for Jarvis 2.0 Interface Issues
Comprehensive system check to identify why the interface is not opening
"""

import sys
import os
import importlib
import traceback
from pathlib import Path
from typing import Dict, List, Tuple, Any

def print_section(title: str):
    """Print a section header"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def print_result(test_name: str, success: bool, message: str = ""):
    """Print test result with formatting"""
    status = "✓ PASS" if success else "✗ FAIL"
    print(f"{status:>8} | {test_name:<40} | {message}")

def check_python_version() -> Tuple[bool, str]:
    """Check if Python version is compatible"""
    version = sys.version_info
    required_major, required_minor = 3, 9
    
    if version.major >= required_major and version.minor >= required_minor:
        return True, f"Python {version.major}.{version.minor}.{version.micro}"
    else:
        return False, f"Python {version.major}.{version.minor}.{version.micro} - Required: {required_major}.{required_minor}+"

def check_dependencies() -> Dict[str, Tuple[bool, str]]:
    """Check all required dependencies"""
    dependencies = {
        # Core UI dependencies
        'PyQt6': ['PyQt6.QtWidgets', 'PyQt6.QtCore', 'PyQt6.QtGui'],
        'PyQt6.QtWidgets.QApplication': ['PyQt6.QtWidgets'],
        
        # Speech dependencies
        'speech_recognition': ['speech_recognition'],
        'pyttsx3': ['pyttsx3'],
        'pyaudio': ['pyaudio'],
        
        # Enhanced features
        'transformers': ['transformers'],
        'torch': ['torch'],
        'sqlalchemy': ['sqlalchemy'],
        'nltk': ['nltk'],
        
        # System dependencies
        'threading': ['threading'],
        'ctypes': ['ctypes'],
        'datetime': ['datetime'],
        'json': ['json'],
        'pathlib': ['pathlib'],
    }
    
    results = {}
    
    for dep_name, modules in dependencies.items():
        try:
            for module in modules:
                importlib.import_module(module)
            results[dep_name] = (True, "Available")
        except ImportError as e:
            results[dep_name] = (False, f"Missing: {str(e)}")
        except Exception as e:
            results[dep_name] = (False, f"Error: {str(e)}")
    
    return results

def check_resources() -> Dict[str, Tuple[bool, str]]:
    """Check for required resource files"""
    base_path = Path(__file__).parent
    
    resources = {
        'jarvis.gif': 'Animation file for main interface',
        'Orbitron-Regular.ttf': 'Custom font for UI',
        'interface_bg.webp': 'Background image',
        '7RRt.gif': 'Additional animation resource',
        'yx9.gif': 'Additional animation resource',
    }
    
    results = {}
    
    for resource, description in resources.items():
        resource_path = base_path / resource
        if resource_path.exists():
            file_size = resource_path.stat().st_size
            results[resource] = (True, f"Found ({file_size} bytes)")
        else:
            results[resource] = (False, f"Missing - {description}")
    
    return results

def test_pyqt6_basic() -> Tuple[bool, str]:
    """Test basic PyQt6 functionality"""
    try:
        from PyQt6.QtWidgets import QApplication, QWidget
        from PyQt6.QtCore import QTimer
        
        # Test creating QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        # Test creating a basic widget
        widget = QWidget()
        widget.setWindowTitle("Test Widget")
        
        # Clean up
        app.quit() if hasattr(app, 'quit') else None
        
        return True, "PyQt6 basic functionality working"
        
    except Exception as e:
        return False, f"PyQt6 error: {str(e)}"

def test_dpi_awareness() -> Tuple[bool, str]:
    """Test DPI awareness setting"""
    try:
        import ctypes
        
        if sys.platform == "win32":
            ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)
            return True, "DPI awareness set successfully"
        else:
            return True, "Non-Windows platform - DPI awareness not required"
            
    except Exception as e:
        return False, f"DPI awareness failed: {str(e)}"

def test_speech_components() -> Tuple[bool, str]:
    """Test speech recognition components"""
    try:
        import speech_recognition as sr
        import pyttsx3
        
        # Test speech recognition
        r = sr.Recognizer()
        
        # Test text-to-speech
        engine = pyttsx3.init('sapi5')
        voices = engine.getProperty('voices')
        
        if voices and len(voices) > 0:
            return True, f"Speech components working - {len(voices)} voices available"
        else:
            return False, "No TTS voices available"
            
    except Exception as e:
        return False, f"Speech components error: {str(e)}"

def test_ui_imports() -> Tuple[bool, str]:
    """Test importing UI components"""
    try:
        # Test basic UI import
        from jarvis_ui import JarvisUI
        
        return True, "UI imports successful"
        
    except ImportError as e:
        return False, f"UI import failed: {str(e)}"
    except Exception as e:
        return False, f"UI import error: {str(e)}"

def test_enhanced_ui_imports() -> Tuple[bool, str]:
    """Test importing enhanced UI components"""
    try:
        from enhanced_jarvis_ui import EnhancedJarvisUI
        
        return True, "Enhanced UI imports successful"
        
    except ImportError as e:
        return False, f"Enhanced UI import failed: {str(e)}"
    except Exception as e:
        return False, f"Enhanced UI import error: {str(e)}"

def test_command_imports() -> Tuple[bool, str]:
    """Test importing command components"""
    try:
        from comandos import abrir, aumentar_volume, buscar_temperatura
        
        return True, "Command imports successful"
        
    except ImportError as e:
        return False, f"Command import failed: {str(e)}"
    except Exception as e:
        return False, f"Command import error: {str(e)}"

def test_enhanced_components() -> Dict[str, Tuple[bool, str]]:
    """Test enhanced system components"""
    components = {
        'enhanced_speech': 'Enhanced speech recognition',
        'conversation_manager': 'Conversation management',
        'learning_engine': 'Learning and adaptation',
        'database_manager': 'Database operations',
        'nlp_processor': 'Natural language processing'
    }
    
    results = {}
    
    for component, description in components.items():
        try:
            importlib.import_module(component)
            results[component] = (True, f"{description} - Available")
        except ImportError as e:
            results[component] = (False, f"{description} - Missing: {str(e)}")
        except Exception as e:
            results[component] = (False, f"{description} - Error: {str(e)}")
    
    return results

def run_minimal_ui_test() -> Tuple[bool, str]:
    """Run a minimal UI test"""
    try:
        from PyQt6.QtWidgets import QApplication, QWidget, QLabel
        from PyQt6.QtCore import QTimer
        
        # Create minimal application
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        # Create minimal window
        window = QWidget()
        window.setWindowTitle("Jarvis 2.0 - Test")
        window.setFixedSize(300, 200)
        
        label = QLabel("Interface Test - OK")
        label.setParent(window)
        label.move(50, 50)
        
        # Show window briefly
        window.show()
        
        # Process events for a moment
        app.processEvents()
        
        # Close window
        window.close()
        
        return True, "Minimal UI test passed"
        
    except Exception as e:
        return False, f"Minimal UI test failed: {str(e)}"

def analyze_main_script() -> Tuple[bool, str]:
    """Analyze main.py for potential issues"""
    try:
        main_path = Path(__file__).parent / "main.py"
        
        if not main_path.exists():
            return False, "main.py file not found"
        
        with open(main_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        issues = []
        
        # Check for common problematic patterns
        if "app = QApplication([])" in content and "app.exec()" in content:
            if content.count("QApplication") > 1:
                issues.append("Multiple QApplication instances")
        
        if "ui.show()" in content:
            # Check if UI is shown in correct context
            if "threading.Thread" in content:
                issues.append("UI shown in threaded context - may cause issues")
        
        if issues:
            return False, f"Potential issues found: {', '.join(issues)}"
        else:
            return True, "Main script structure looks correct"
            
    except Exception as e:
        return False, f"Main script analysis failed: {str(e)}"

def main():
    """Run comprehensive diagnostic"""
    print("JARVIS 2.0 INTERFACE DIAGNOSTIC TOOL")
    print("Analyzing system for interface opening issues...")
    
    # System Information
    print_section("SYSTEM INFORMATION")
    python_ok, python_msg = check_python_version()
    print_result("Python Version", python_ok, python_msg)
    print_result("Platform", True, sys.platform)
    print_result("Working Directory", True, os.getcwd())
    
    # Dependency Check
    print_section("DEPENDENCY CHECK")
    deps = check_dependencies()
    for dep, (success, msg) in deps.items():
        print_result(dep, success, msg)
    
    # Resource Check
    print_section("RESOURCE FILES CHECK")
    resources = check_resources()
    for resource, (success, msg) in resources.items():
        print_result(resource, success, msg)
    
    # Component Tests
    print_section("COMPONENT TESTS")
    
    dpi_ok, dpi_msg = test_dpi_awareness()
    print_result("DPI Awareness", dpi_ok, dpi_msg)
    
    pyqt_ok, pyqt_msg = test_pyqt6_basic()
    print_result("PyQt6 Basic", pyqt_ok, pyqt_msg)
    
    speech_ok, speech_msg = test_speech_components()
    print_result("Speech Components", speech_ok, speech_msg)
    
    ui_ok, ui_msg = test_ui_imports()
    print_result("UI Imports", ui_ok, ui_msg)
    
    enhanced_ui_ok, enhanced_ui_msg = test_enhanced_ui_imports()
    print_result("Enhanced UI Imports", enhanced_ui_ok, enhanced_ui_msg)
    
    cmd_ok, cmd_msg = test_command_imports()
    print_result("Command Imports", cmd_ok, cmd_msg)
    
    # Enhanced Components
    print_section("ENHANCED COMPONENTS")
    enhanced_components = test_enhanced_components()
    for component, (success, msg) in enhanced_components.items():
        print_result(component, success, msg)
    
    # UI Tests
    print_section("UI FUNCTIONALITY TESTS")
    
    minimal_ui_ok, minimal_ui_msg = run_minimal_ui_test()
    print_result("Minimal UI Test", minimal_ui_ok, minimal_ui_msg)
    
    main_analysis_ok, main_analysis_msg = analyze_main_script()
    print_result("Main Script Analysis", main_analysis_ok, main_analysis_msg)
    
    # Summary
    print_section("DIAGNOSTIC SUMMARY")
    
    critical_issues = []
    warnings = []
    
    # Check critical dependencies
    if not deps.get('PyQt6', (False, ""))[0]:
        critical_issues.append("PyQt6 not available - UI cannot initialize")
    
    if not pyqt_ok:
        critical_issues.append("PyQt6 basic functionality failed")
    
    if not ui_ok and not enhanced_ui_ok:
        critical_issues.append("No UI components can be imported")
    
    # Check warnings
    if not speech_ok:
        warnings.append("Speech components not working - voice features disabled")
    
    if not resources.get('jarvis.gif', (False, ""))[0]:
        warnings.append("Missing jarvis.gif - interface may look different")
    
    if critical_issues:
        print("\nCRITICAL ISSUES (must be fixed):")
        for issue in critical_issues:
            print(f"  • {issue}")
    
    if warnings:
        print("\nWARNINGS (may affect functionality):")
        for warning in warnings:
            print(f"  • {warning}")
    
    if not critical_issues and not warnings:
        print("\n✓ No critical issues found. Interface should work.")
    elif not critical_issues:
        print("\n⚠ Interface should work but with reduced functionality.")
    else:
        print("\n✗ Critical issues found. Interface will not work properly.")
    
    # Recommendations
    print_section("RECOMMENDATIONS")
    
    if critical_issues:
        print("1. Install missing dependencies:")
        print("   pip install -r requirements_enhanced.txt")
        print("2. Verify PyQt6 installation:")
        print("   pip install PyQt6==6.9.1")
        print("3. Check graphics drivers are up to date")
    
    if warnings:
        print("4. Install optional dependencies for full functionality")
        print("5. Verify resource files are present")
    
    print("\n6. Try running the minimal UI test:")
    print("   python -c \"from diagnostic_script import run_minimal_ui_test; print(run_minimal_ui_test())\"")

if __name__ == "__main__":
    main()