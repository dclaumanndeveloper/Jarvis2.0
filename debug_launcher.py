import sys
import traceback
import logging
import time

# Configure logging to file
logging.basicConfig(
    filename='detailed_crash_log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filemode='w'
)

# Also log to stdout
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger('').addHandler(console)

print("--- DEBUG LAUNCHER START ---")
logging.info("Starting Debug Launcher")

try:
    print("Importing main module...")
    import main
    from PyQt6.QtWidgets import QApplication

    print("Checking for existing QApplication...")
    app = QApplication.instance()
    if not app:
        print("Creating QApplication...")
        app = QApplication(sys.argv)
    else:
        print("QApplication already exists.")

    print("Initializing JarvisSystem...")
    jarvis = main.JarvisSystem()
    
    print("Run initialize()...")
    if not jarvis.initialize():
        print("FATAL: JarvisSystem.initialize() returned False")
        logging.error("JarvisSystem.initialize() returned False")
        # Don't exit yet, let's see if we can see why
    else:
        print("JarvisSystem initialized successfully.")

    print("Starting JarvisSystem (executing app loop)...")
    try:
        # Check if sys.exit was intended or just exec
        sys.exit(app.exec())
    except SystemExit:
        print("Application exited via sys.exit()")
    except Exception as e:
        print(f"CRITICAL: Exception during app.exec(): {e}")
        logging.critical(f"Exception during app.exec(): {e}", exc_info=True)
        traceback.print_exc()

except Exception as e:
    print(f"CRITICAL ERROR in Debug Launcher: {e}")
    traceback.print_exc()

print("--- DEBUG LAUNCHER END ---")
print("Press Enter to close window...")
try:
    input()
except:
    pass
