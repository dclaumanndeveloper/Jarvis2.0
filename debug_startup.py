import sys
import traceback
import logging

# Configure logging to stdout
logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

print("--- DIAGNOSTIC START ---")
try:
    print("Importing main...")
    import main
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    print("Initializing JarvisSystem...")
    # Manually initialize to catch the specific error
    jarvis = main.JarvisSystem()
    print("Calling initialize()...")
    success = jarvis.initialize()
    if not success:
        print("Initialize returned False. Check logs above.")
    else:
        print("Initialization successful!")
        
except Exception:
    print("CRITICAL EXCEPTION CAUGHT:")
    traceback.print_exc()
print("--- DIAGNOSTIC END ---")
