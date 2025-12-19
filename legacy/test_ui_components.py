"""
Simple UI Test Script for Jarvis 2.0
Tests both basic and enhanced UI components after syntax fixes
"""

import sys
import os
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

def test_basic_ui():
    """Test basic PyQt6 functionality"""
    print("Testing basic PyQt6 UI...")
    try:
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        window = QWidget()
        window.setWindowTitle("Jarvis 2.0 - Basic Test")
        window.setFixedSize(400, 300)
        
        layout = QVBoxLayout()
        
        # Test label
        label = QLabel("Jarvis 2.0 - Interface Básica OK!")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("""
            color: #00FFFF;
            font-size: 18px;
            font-weight: bold;
            background-color: rgba(0, 50, 100, 200);
            padding: 20px;
            border-radius: 10px;
        """)
        
        layout.addWidget(label)
        window.setLayout(layout)
        
        # Style the window
        window.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 180);
            }
        """)
        
        window.show()
        
        # Close after 3 seconds
        QTimer.singleShot(3000, window.close)
        
        return True, "Basic UI test successful"
        
    except Exception as e:
        return False, f"Basic UI test failed: {str(e)}"

def test_jarvis_ui_import():
    """Test importing JarvisUI"""
    print("Testing JarvisUI import...")
    try:
        from jarvis_ui import JarvisUI
        print("✓ JarvisUI imported successfully")
        return True, "JarvisUI import successful"
    except Exception as e:
        print(f"✗ JarvisUI import failed: {e}")
        return False, f"JarvisUI import failed: {str(e)}"

def test_enhanced_ui_import():
    """Test importing EnhancedJarvisUI"""
    print("Testing EnhancedJarvisUI import...")
    try:
        from enhanced_jarvis_ui import EnhancedJarvisUI
        print("✓ EnhancedJarvisUI imported successfully")
        return True, "EnhancedJarvisUI import successful"
    except Exception as e:
        print(f"✗ EnhancedJarvisUI import failed: {e}")
        return False, f"EnhancedJarvisUI import failed: {str(e)}"

def test_jarvis_ui_creation():
    """Test creating JarvisUI instance"""
    print("Testing JarvisUI creation...")
    try:
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        from jarvis_ui import JarvisUI
        ui = JarvisUI()
        
        # Show briefly
        ui.show()
        QTimer.singleShot(2000, ui.close)
        
        print("✓ JarvisUI created and shown successfully")
        return True, "JarvisUI creation successful"
        
    except Exception as e:
        print(f"✗ JarvisUI creation failed: {e}")
        return False, f"JarvisUI creation failed: {str(e)}"

def test_enhanced_ui_creation():
    """Test creating EnhancedJarvisUI instance"""
    print("Testing EnhancedJarvisUI creation...")
    try:
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        from enhanced_jarvis_ui import EnhancedJarvisUI
        ui = EnhancedJarvisUI()
        
        # Show briefly
        ui.show()
        QTimer.singleShot(2000, ui.close)
        
        print("✓ EnhancedJarvisUI created and shown successfully")
        return True, "EnhancedJarvisUI creation successful"
        
    except Exception as e:
        print(f"✗ EnhancedJarvisUI creation failed: {e}")
        return False, f"EnhancedJarvisUI creation failed: {str(e)}"

def run_comprehensive_ui_test():
    """Run all UI tests"""
    print("="*60)
    print("JARVIS 2.0 UI COMPONENT TEST")
    print("="*60)
    
    tests = [
        ("Basic PyQt6 Test", test_basic_ui),
        ("JarvisUI Import", test_jarvis_ui_import),
        ("Enhanced UI Import", test_enhanced_ui_import),
        ("JarvisUI Creation", test_jarvis_ui_creation),
        ("Enhanced UI Creation", test_enhanced_ui_creation),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            success, message = test_func()
            results.append((test_name, success, message))
            status = "✓ PASS" if success else "✗ FAIL"
            print(f"{status}: {message}")
        except Exception as e:
            results.append((test_name, False, f"Test error: {str(e)}"))
            print(f"✗ FAIL: Test error: {str(e)}")
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for test_name, success, message in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status:>8} | {test_name:<25} | {message}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Interface should work correctly.")
        return True
    elif passed > 0:
        print("⚠️  Some tests passed. Partial functionality available.")
        return False
    else:
        print("❌ All tests failed. Interface needs additional fixes.")
        return False

if __name__ == "__main__":
    success = run_comprehensive_ui_test()
    
    if success:
        print("\n🚀 Ready to test main application!")
        print("Try running: python main.py")
    else:
        print("\n🔧 Additional fixes needed before main application will work.")
    
    sys.exit(0 if success else 1)