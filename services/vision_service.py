import base64
import logging
from typing import Optional, Tuple
import cv2
import mss
import numpy as np
import requests
from PIL import Image
import io

logger = logging.getLogger(__name__)

class VisionService:
    """
    Handles local screen and camera capturing, and communicates with
    Ollama Vision Models (like moondream or llava) to describe what Jarvis "sees".
    """
    def __init__(self, ollama_url: str = "http://localhost:11434/api/generate", model: str = "moondream"):
        self.ollama_url = ollama_url
        self.model = model

    def capture_screen_base64(self) -> Optional[str]:
        """Captures the primary screen and returns a base64 encoded JPEG string"""
        try:
            with mss.mss() as sct:
                # Capture the first monitor
                monitor = sct.monitors[1]
                screenshot = sct.grab(monitor)
                
                # Convert to PIL Image
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                
                # Resize to save processing power for local LLM
                img.thumbnail((800, 800))
                
                # Convert to base64
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=80)
                return base64.b64encode(buffer.getvalue()).decode('utf-8')
        except Exception as e:
            logger.error(f"VisionService: Error capturing screen: {e}")
            return None

    def capture_camera_base64(self, camera_index: int = 0) -> Optional[str]:
        """Captures a frame from the webcam and returns a base64 encoded JPEG string"""
        try:
            cap = cv2.VideoCapture(camera_index)
            if not cap.isOpened():
                logger.error("VisionService: Could not open webcam.")
                return None
            
            # Read one frame
            ret, frame = cap.read()
            cap.release()
            
            if not ret:
                logger.error("VisionService: Failed to read from webcam.")
                return None
            
            # Convert BGR (OpenCV) to RGB (PIL)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            img.thumbnail((800, 800))
            
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=80)
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
        except Exception as e:
            logger.error(f"VisionService: Error capturing camera: {e}")
            return None

    def analyze_image(self, base64_image: str, prompt: str = "Descreva detalhadamente o que você vê nesta imagem, responda em português.") -> str:
        """Sends the base64 image to the local Ollama vision model."""
        if not base64_image:
            return "Não consegui capturar nenhuma imagem para analisar."
            
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "images": [base64_image],
                "stream": False
            }
            
            # Increased timeout to 180s (3 minutes) because Vision LLMs (LLaVA/Moondream) 
            # take a long time to load into RAM/VRAM on the first "cold start" via Ollama.
            logger.info(f"VisionService: Sending image to {self.model}. This might take a while on cold start.")
            response = requests.post(self.ollama_url, json=payload, timeout=180)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('response', 'A imagem foi processada, mas não obtive resposta clara.')
            else:
                logger.error(f"VisionService: API Error {response.status_code}")
                return f"Falha ao conectar com o modelo de visão. Erro {response.status_code}."
        except requests.Timeout:
            return "O modelo de visão demorou demais para responder."
        except Exception as e:
            logger.error(f"VisionService: Unexpected error: {e}")
            return "Ocorreu um erro inesperado na análise visual."
