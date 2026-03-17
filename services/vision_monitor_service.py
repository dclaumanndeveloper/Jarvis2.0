import asyncio
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class VisionMonitorService:
    """
    The 'Eyes' of Jarvis. Periodically analyzes the screen to provide
    proactive insights (detecting errors, offering help).
    """
    def __init__(self, ai_service, interval=60):
        self.ai_service = ai_service
        self.interval = interval
        self.running = False
        self.last_analysis = None
        
        # PROMPT for proactive detection
        self.PROMPT = (
            "Analise esta imagem da tela do computador. "
            "Se houver mensagens de erro gritantes, falhas de build em terminais, "
            "ou janelas de notificação importantes, descreva-as brevemente. "
            "Caso contrário, apenas diga 'NADA RELEVANTE'."
        )

    async def start(self):
        self.running = True
        logger.info(f"VisionMonitor: Started with interval {self.interval}s")
        asyncio.create_task(self._monitor_loop())

    async def _monitor_loop(self):
        while self.running:
            try:
                # Wait for the next interval
                await asyncio.sleep(self.interval)
                
                # Take screenshot
                logger.debug("VisionMonitor: Capturando tela para análise proativa...")
                screenshot_path = self.ai_service.vision_service.capture_screen()
                
                if screenshot_path:
                    # Process with VLM
                    # Note: LocalAIProcessor.process_image handles the VLM inference
                    result = await self.ai_service.processor.process_image(screenshot_path, self.PROMPT)
                    
                    if "NADA RELEVANTE" not in result.upper() and len(result) > 10:
                        logger.info(f"VisionMonitor: Insight detectado: {result}")
                        
                        # Emit insight to HUD and TTS
                        if hasattr(self.ai_service, 'learning_insight'):
                            self.ai_service.learning_insight.emit(f"👁️ Sugestão Proativa: {result}")
                        
                        # Add to memory as a contextual event
                        self.ai_service.memory.store_fact(f"Visual Insight proativo: {result}", category="vision_monitor")
                
                # Cleanup screenshot
                if screenshot_path and os.path.exists(screenshot_path):
                    os.remove(screenshot_path)
                    
            except Exception as e:
                logger.error(f"VisionMonitor: Loop error: {e}")
                await asyncio.sleep(self.interval)

    def stop(self):
        self.running = False
