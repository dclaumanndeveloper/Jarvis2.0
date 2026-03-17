import sys
import os
import asyncio
import logging
import threading
import uuid
import time
from typing import Optional, Dict, Any, List
from datetime import datetime

from PyQt6.QtCore import QThread, pyqtSignal, QObject

# Add project root to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nlp_processor import NLPProcessor, NLPResult, ProcessingMode
from learning_engine import LearningModule
from conversation_manager import ConversationContext, ConversationTurn, IntentType
from services.web_agent_service import WebAgentService
from services.vision_service import VisionService
from services.health_monitor_service import HealthMonitorService
from services.workflow_service import WorkflowService
from services.update_service import AutoUpdateService
from services.indexer_service import BrainIndexerService
from services.vision_monitor_service import VisionMonitorService
from services.coding_agent_service import CodingAgentService
from services.memory_service import MemoryService
from services.telegram_service import TelegramService

logger = logging.getLogger(__name__)

class AIService(QThread):
    """
    Background service for handling AI tasks:
    - Natural Language Processing (Gemini/Local)
    - Self-Learning (Pattern Recognition)
    - Context Management
    """
    
    # Signals to communicate with Main Request Thread
    processing_finished = pyqtSignal(object) # Emits NLPResult
    learning_insight = pyqtSignal(str)       # Emits proactive suggestions
    error_occurred = pyqtSignal(str)
    stream_token_received = pyqtSignal(str)  # Emits individual tokens/chunks

    # Commands loaded dynamically from ActionController registry

    def __init__(self):
        super().__init__()
        self.loop = None
        self.running = True
        
        # AI Components
        self.learning_module = None
        self.web_agent = WebAgentService()
        self.vision_service = VisionService()
        self.health_monitor = HealthMonitorService()
        self.workflow_manager = WorkflowService()
        self.updater = AutoUpdateService()
        self.coding_agent = CodingAgentService()
        self.indexer = None # Initialized in run() after memory_service
        self.vision_monitor = None # Initialized in run() after processor
        self.telegram = TelegramService()
        
        # Runtime Context
        self.context = ConversationContext()
        self.pending_tasks = []
        self.task_lock = threading.Lock()

    def run(self):
        """Main thread loop"""
        try:
            # Clear any stale tasks from previous session
            self.clear_pending_tasks()
            
            # Initialize Async Loop for this thread
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            # Initialize Memory and NLP Processor
            self.memory_service = MemoryService()
            self.nlp_processor = NLPProcessor()
            try:
                self.learning_module = LearningModule()
                logger.info("LearningModule initialized successfully")
                # Start background learning
                self.loop.run_until_complete(self.learning_module.start_learning())
            except Exception as e:
                logger.error(f"Failed to initialize LearningModule: {e}")
                self.learning_module = None
            
            # Start background perception loop
            asyncio.create_task(self._perception_loop())
            
            # Start Health Monitor
            asyncio.create_task(self.health_monitor.start_monitoring(self))
            
            # Start Brain Indexer
            self.indexer = BrainIndexerService(self.memory_service)
            self.indexer.start()
            
            # Start Vision Monitor (every 60s)
            self.vision_monitor = VisionMonitorService(self)
            asyncio.create_task(self.vision_monitor.start())
            
            # Start periodic update check (every 24h)
            asyncio.create_task(self._update_check_loop())
            
            # Start Telegram Service
            self.telegram.command_received.connect(self.process_command)
            # Connect proactivity to Telegram
            self.learning_insight.connect(self.telegram.send_message)
            self.telegram.start()
            
            logger.info("AIService: God Mode pipeline started (Mobile Bridge active).")
            
            logger.info("AI Service initialized successfully")
            
            # Process Loop
            while self.running:
                # Check for pending tasks
                task = None
                with self.task_lock:
                    if self.pending_tasks:
                        task = self.pending_tasks.pop(0)
                
                if task:
                    self.loop.run_until_complete(self._process_task(task))
                else:
                    # Sleep briefly to avoid CPU hogging
                    self.msleep(100)
                    
            # Cleanup
            if self.learning_module:
                self.loop.run_until_complete(self.learning_module.stop_learning())
            self.loop.close()
            
        except Exception as e:
            logger.error(f"AI Service crashed: {e}")
            self.error_occurred.emit(str(e))

    def process_command(self, command: str):
        """Entry point for processing a text command (voice or manual)"""
        # Workflow recording logic
        if self.workflow_manager.is_recording:
            if "parar gravação" in command.lower() or "encerrar macro" in command.lower():
                name = self.workflow_manager.stop_recording()
                self.learning_insight.emit(f"✅ Workflow '{name}' gravado e salvo com sucesso.")
                return
            else:
                self.workflow_manager.add_to_recording(command)
                # Still process it so the user sees it working during record
        
        # Queue the command for async processing in the AI service's event loop
        # Note: _async_process_command is not defined in the provided context,
        # but this line is part of the requested change.
        # For now, we'll queue it as before, but the instruction implies a change to an async call.
        # To make it syntactically correct and functional with existing _process_task:
        with self.task_lock:
            self.pending_tasks.append({'type': 'command', 'data': command})


    def update_feedback(self, success: bool):
        """Public method to provide feedback on last action"""
        with self.task_lock:
            self.pending_tasks.append({'type': 'feedback', 'data': success})

    async def _process_task(self, task: Dict[str, Any]):
        """Internal task processor"""
        task_type = task.get('type')
        data = task.get('data')
        
        if task_type == 'command':
            text = data
            logger.info(f"AIService: Processing command task: {text}")
            
            # 1. Base Intent Analysis (Fast)
            # Simple keyword match to get started or rely on NLP for everything
            # Simple intent checking to bypass LLM for fast execution
            text_lower = text.lower()
            
            # Fast keyword matching — avoids Ollama for predictable commands ──────────────
            DIRECT_CMD_KEYWORDS = [
                'abrir', 'abri', 'abre', 'fechar', 'fecha', 'tocar', 'toca',
                'pausar', 'pausa', 'aumentar', 'diminuir', 'volume', 'pesquisar',
                'pesquisa', 'buscar', 'busca', 'procurar', 'desligar', 'reiniciar',
                'print', 'screenshot', 'calcular', 'calcula', 'escreva', 'digite'
            ]
            VISION_KEYWORDS = [
                'tela', 'câmera', 'camera', 'olhe', 'analise', 'veja', 'o que tem na'
            ]
            
            process_mode = ProcessingMode.FAST # Default to fast
            
            if any(kw in text_lower for kw in ['horas', 'que horas', 'horário']):
                base_intent = IntentType.TIME_QUERY
            elif any(kw in text_lower for kw in ['data', 'dia é hoje', 'que dia']):
                base_intent = IntentType.DATE_QUERY
            elif any(kw in text_lower for kw in DIRECT_CMD_KEYWORDS):
                base_intent = IntentType.DIRECT_COMMAND
            elif any(kw in text_lower for kw in VISION_KEYWORDS):
                base_intent = IntentType.VISION_QUERY
            elif any(kw in text_lower for kw in ['pesquisa profunda', 'agente', 'investigue', 'preço de']):
                base_intent = IntentType.AGENT_RESEARCH_QUERY
                process_mode = ProcessingMode.DETAILED
            elif any(kw in text_lower for kw in ['aprenda da pasta', 'leia os arquivos', 'ingerir']):
                base_intent = IntentType.DOC_LEARNING_QUERY
                process_mode = ProcessingMode.DETAILED
            else:
                # Only send to Ollama (DETAILED) when we truly can't classify quickly
                base_intent = IntentType.CONVERSATIONAL_QUERY
                process_mode = ProcessingMode.DETAILED
            # ─────────────────────────────────────────────────────────────────────────────

            
            logger.info(f"AIService: Analysis results: detected base_intent as {base_intent}")
            
            # 2. Retrieve Past Context/Facts via RAG
            if hasattr(self, 'memory_service') and self.memory_service:
                self.context.long_term_memory = self.memory_service.retrieve_relevant_context(text)
            
            # 3. Handle Special Deep Intelligence Intents
            if base_intent == IntentType.AGENT_RESEARCH_QUERY:
                self.stream_token_received.emit("JARVIS: Iniciando pesquisa profunda via agente autônomo. Por favor, aguarde...")
                research_results = await self.web_agent.research_topic(text)
                self.context.long_term_memory += f"\nRecent Research: {research_results}"
                text = f"Resuma e me explique os seguintes resultados de pesquisa sobre {text}: {research_results}"
                # Switch to detailed for explanation
                process_mode = ProcessingMode.DETAILED
            
            elif base_intent == IntentType.DOC_LEARNING_QUERY:
                self.stream_token_received.emit("JARVIS: Analisando e aprendendo com os documentos locais...")
                # Extract path or use default
                target_dir = os.path.join(os.getcwd(), "documents")
                await asyncio.to_thread(self.memory_service.ingest_directory, target_dir)
                self.stream_token_received.emit("JARVIS: Aprendizado concluído. Agora conheço o conteúdo dos seus documentos.")
                return

            result = await self.nlp_processor.process_text(
                text, 
                base_intent, 
                self.context, 
                mode=process_mode,
                stream_callback=lambda token: self.stream_token_received.emit(token)
            )
            
            # 3.5 JARVIS CODER FALLBACK (God Mode)
            # If LLM doesn't know how to handle and it's a direct command, try coding agent
            if result.intent == IntentType.UNKNOWN and base_intent == IntentType.DIRECT_COMMAND:
                self.stream_token_received.emit("JARVIS: Não tenho um comando pré-definido para isso. Ativando Agente de Codificação Autônomo...")
                code_result = await self.coding_agent.execute_task(text, self.nlp_processor)
                result.response_suggestion = code_result
                result.intent = IntentType.DIRECT_COMMAND # Override
            
            # 4. Store memory
            if hasattr(self, 'memory_service') and self.memory_service:
                self.memory_service.store_interaction(
                    user_text=text,
                    ai_response=result.response_suggestion,
                    intent=result.intent.name,
                    timestamp=str(time.time())
                )
            
            # 5. Update Context
            self.context.last_command = text
            self.context.conversation_history.append({
                'user_input': text,
                'intent': result.intent.value,
                'timestamp': datetime.now().isoformat(),
                'entities': result.entities,
                'response': result.response_suggestion,
                'confidence': result.confidence
            })
            # 6. Silent Perception Learning (Learn from every interaction)
            if self.learning_module:
                try:
                    turn = ConversationTurn(
                        id=str(uuid.uuid4()),
                        timestamp=datetime.now(),
                        user_input=text,
                        recognized_text=text,
                        confidence_score=result.confidence,
                        intent=result.intent,
                        entities=result.entities,
                        context={},
                        response=result.response_suggestion,
                        response_time=result.processing_time,
                        satisfaction_score=0.8 # Default successful baseline
                    )
                    await self.learning_module.learn_from_interaction(turn, self.context)
                except Exception as e:
                    logger.error(f"Error passing interaction to learning module: {e}")
                    
            # 7. Emit Result for UI/Execution
            self.processing_finished.emit(result)
            
            # 8. Check for Proactive Suggestions (Learning)
            if self.learning_module:
                try:
                    suggestions = await self.learning_module.generate_proactive_suggestions(self.context)
                    for suggestion in suggestions:
                        self.learning_insight.emit(suggestion)
                except Exception as e:
                    logger.error(f"Error generating suggestions: {e}")
                
        elif task_type == 'feedback':
            # Implement Learning from feedback
            success = data
            logger.info(f"AIService: Processing feedback task: success={success}")

            if self.learning_module and self.context.conversation_history:
                try:
                    last_interaction = self.context.conversation_history[-1]

                    # Reconstruct intent enum
                    try:
                        intent = IntentType(last_interaction.get('intent'))
                    except ValueError:
                        intent = IntentType.UNKNOWN

                    turn = ConversationTurn(
                        id=str(uuid.uuid4()),
                        timestamp=datetime.fromisoformat(last_interaction['timestamp']),
                        user_input=last_interaction['user_input'],
                        recognized_text=last_interaction['user_input'],
                        confidence_score=last_interaction.get('confidence', 0.0),
                        intent=intent,
                        entities=last_interaction.get('entities', {}),
                        context={},  # Current context is passed separately
                        response=last_interaction.get('response', ""),
                        response_time=0.0,  # Not tracked in history currently
                        satisfaction_score=1.0 if success else 0.0
                    )

                    await self.learning_module.learn_from_interaction(turn, self.context)
                    logger.info("AIService: Feedback processed and sent to learning module")

                except Exception as e:
                    logger.error(f"Error processing feedback: {e}")
    
    def clear_pending_tasks(self):
        """Clear any pending tasks from the queue"""
        with self.task_lock:
            count = len(self.pending_tasks)
            self.pending_tasks.clear()
            if count > 0:
                logger.info(f"AIService: Cleared {count} stale pending tasks")
        
        # Also reset conversation context to avoid old command influence
        self.context = ConversationContext()
        logger.info("AIService: Reset conversation context")
            
    async def _perception_loop(self):
        """Periodically check environment (active window) for proactive suggestions"""
        while self.running:
            try:
                await asyncio.sleep(60) # Every minute
                if self.vision_service and self.learning_module:
                    window_info = self.vision_service.get_active_window_info()
                    self.context.environmental_state['active_window'] = window_info
                    
                    suggestions = await self.learning_module.generate_proactive_suggestions(self.context)
                    for suggestion in suggestions:
                        # Only emit if it's a "fresh" suggestion (heuristic)
                        if not hasattr(self, '_last_suggestion') or self._last_suggestion != suggestion:
                            self.learning_insight.emit(f"JARVIS (Proativo): {suggestion}")
                            self._last_suggestion = suggestion
                            break # One at a time
            except Exception as e:
                logger.error(f"Error in perception loop: {e}")

    async def _update_check_loop(self):
        while self.running:
            if await self.updater.check_for_updates():
                self.learning_insight.emit("🚀 Uma nova versão do Jarvis está disponível. Gostaria de atualizar?")
            await asyncio.sleep(86400) # 24 hours

    def stop(self):
        self.running = False
        self.wait()

