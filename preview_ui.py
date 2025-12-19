import sys
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

# Configure dummy logging
logging.basicConfig(level=logging.INFO)

# Mock dependencies to prevent import errors in jarvis_ui if they are missing
import sys
from unittest.mock import MagicMock

# Create a clean UI preview environment
def preview():
    print("--- UI PREVIEW LAUNCH ---")
    
    try:
        from jarvis_ui import UnifiedJarvisUI, UIState
        
        app = QApplication(sys.argv)
        ui = UnifiedJarvisUI()
        
        # Force a state that shows the Arc Reactor clearly
        ui.change_state(UIState.LISTENING)
        
        print("Showing UI...")
        ui.show()
        
        print("Application loop started. Close window to exit.")
        sys.exit(app.exec())
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"CRITICAL UI ERROR: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    preview()
