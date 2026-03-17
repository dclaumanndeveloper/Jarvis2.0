import os
import time
import logging
import pyautogui
import pygetwindow as gw
from typing import Optional, Dict, Any, Tuple
from PIL import Image

logger = logging.getLogger(__name__)

class VisionService:
    """
    Service to handle local computer vision tasks:
    - Screen capture
    - Image preprocessing
    - Vision model inference (GGUF via llama-cpp)
    """
    def __init__(self, storage_path="media/vision", nlp_processor=None):
        self.storage_path = storage_path
        self.nlp_processor = nlp_processor
        os.makedirs(self.storage_path, exist_ok=True)
        logger.info("VisionService: Initialized.")

    def capture_screen(self, monitor_index=0) -> Optional[str]:
        """Capture a screenshot of a specific monitor and return the file path"""
        try:
            monitors = get_monitors()
            if monitor_index >= len(monitors):
                monitor_index = 0
            
            # Using pyautogui to capture
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            filepath = os.path.join(self.storage_path, filename)
            
            screenshot = pyautogui.screenshot()
            screenshot.save(filepath)
            
            logger.info(f"VisionService: Screenshot saved to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"VisionService: Screenshot failed: {e}")
            return None

    async def perform_click(self, x: int, y: int):
        """Perform a mouse click at specified coordinates"""
        try:
            pyautogui.moveTo(x, y, duration=0.5)
            pyautogui.click()
            logger.info(f"VisionService: Click performed at ({x}, {y})")
        except Exception as e:
            logger.error(f"VisionService: Click failed: {e}")

    async def perform_typing(self, text: str):
        """Type text using keyboard simulation"""
        try:
            pyautogui.write(text, interval=0.1)
            logger.info(f"VisionService: Typed text: {text[:20]}...")
        except Exception as e:
            logger.error(f"VisionService: Typing failed: {e}")

    def capture_active_window(self) -> Optional[str]:
        """Capture the current active window"""
        try:
            active_window = gw.getActiveWindow()
            if not active_window: return self.capture_screen()
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"active_window_{timestamp}.png"
            filepath = os.path.join(self.storage_path, filename)
            
            screenshot = pyautogui.screenshot(region=(active_window.left, active_window.top, 
                                                    active_window.width, active_window.height))
            screenshot.save(filepath)
            return filepath
        except Exception as e:
            logger.error(f"VisionService: Active window capture failed: {e}")
            return self.capture_screen()

    def get_active_window_info(self) -> Dict[str, str]:
        """Get the title and application name of the current active window"""
        try:
            active_window = gw.getActiveWindow()
            if active_window:
                return {
                    "title": active_window.title,
                    "app": active_window.title.split('-')[-1].strip() if '-' in active_window.title else active_window.title
                }
        except Exception as e:
            logger.error(f"VisionService: Failed to get window info: {e}")
        return {"title": "Unknown", "app": "Unknown"}

    def process_with_vision_model(self, image_path: str, prompt: str) -> str:
        """Analyze image using local GGUF vision model via NLPProcessor"""
        if self.nlp_processor:
            # Check if it has the local engine
            if hasattr(self.nlp_processor, 'ai_engine'):
                return asyncio.run(self.nlp_processor.ai_engine.process_image(image_path, prompt))
        
        return "Visão computacional local não disponível ou não inicializada."
