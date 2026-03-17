import os
import time
import logging
import asyncio
from pathlib import Path

logger = logging.getLogger(__name__)

class HealthMonitorService:
    """
    Service to monitor Jarvis 2.0 health and perform auto-healing.
    Watches logs for recurring errors and restarts failing components.
    """
    def __init__(self, log_path="error.log"):
        self.log_path = Path(log_path)
        self.running = False
        self.last_pos = 0
        self.ai_service = None # Reference to AIService for emitting insights
        if self.log_path.exists():
            self.last_pos = self.log_path.stat().st_size
        
        self.error_count = {}
        self.RECOVERY_THRESHOLD = 3
        logger.info("HealthMonitorService: Initialized.")

    async def start_monitoring(self, ai_service_ref):
        self.running = True
        self.ai_service = ai_service_ref
        asyncio.create_task(self._watch_logs())
        logger.info("HealthMonitorService: Monitoring started.")

    async def _watch_logs(self):
        while self.running:
            try:
                if self.log_path.exists():
                    current_size = self.log_path.stat().st_size
                    if current_size < self.last_pos:
                        self.last_pos = 0 # Log rotated
                    
                    if current_size > self.last_pos:
                        with open(self.log_path, 'r', encoding='utf-8') as f:
                            f.seek(self.last_pos)
                            new_lines = f.readlines()
                            self.last_pos = f.tell()
                            
                            for line in new_lines:
                                await self._analyze_error(line)
                
                await asyncio.sleep(5) # Check every 5s
            except Exception as e:
                logger.error(f"HealthMonitor: Error in watch loop: {e}")
                await asyncio.sleep(10)

    async def _analyze_error(self, line):
        """Detect recurring errors and trigger healing"""
        # Simple pattern matching for service failures
        if "Ollama" in line and "Connection" in line:
            await self._heal_service("Ollama")
        elif "Whisper" in line and "failed" in line.lower():
            await self._heal_service("STT")
        elif "TTS" in line and "error" in line.lower():
            await self._heal_service("TTS")

    async def _heal_service(self, service_name):
        self.error_count[service_name] = self.error_count.get(service_name, 0) + 1
        
        if self.error_count[service_name] >= self.RECOVERY_THRESHOLD:
            logger.warning(f"HealthMonitor: Service {service_name} failing repeatedly. Attempting auto-recovery...")
            
            # Reset count
            self.error_count[service_name] = 0
            
            # Emit healing event to UI/System if ai_service is set
            if self.ai_service and hasattr(self.ai_service, 'learning_insight'):
                self.ai_service.learning_insight.emit(f"⚙️ Auto-Cura: Detectei falhas no {service_name}. Reiniciando módulo...")
            
            # Implement specific recovery logic
            if service_name == "Ollama":
                # Implementation of recovery for Ollama
                pass
            elif service_name == "STT":
                # Implementation of recovery for STT
                pass

    def stop(self):
        self.running = False
