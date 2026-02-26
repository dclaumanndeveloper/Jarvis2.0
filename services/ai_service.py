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
from services.memory_service import MemoryService

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

    # Commands loaded dynamically from ActionController registry

    def __init__(self):
        super().__init__()
        self.loop = None
        self.running = True
        
        # AI Components
        self.nlp_processor: Optional[NLPProcessor] = None
        self.learning_module: Optional[LearningModule] = None
        
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

    def process_command(self, text: str):
        """Public method to queue a command for processing"""
        with self.task_lock:
            self.pending_tasks.append({'type': 'command', 'data': text})

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
                'print', 'screenshot', 'calcular', 'calcula'
            ]
            VISION_KEYWORDS = [
                'tela', 'câmera', 'camera', 'olhe', 'analise', 'veja', 'o que tem na'
            ]
            
            if any(kw in text_lower for kw in ['horas', 'que horas', 'horário']):
                base_intent = IntentType.TIME_QUERY
            elif any(kw in text_lower for kw in ['data', 'dia é hoje', 'que dia']):
                base_intent = IntentType.DATE_QUERY
            elif any(kw in text_lower for kw in DIRECT_CMD_KEYWORDS):
                base_intent = IntentType.DIRECT_COMMAND
            elif any(kw in text_lower for kw in VISION_KEYWORDS):
                base_intent = IntentType.VISION_QUERY
            else:
                # Only send to Ollama (DETAILED) when we truly can't classify quickly
                base_intent = IntentType.CONVERSATIONAL_QUERY
            # ─────────────────────────────────────────────────────────────────────────────
            
            logger.info(f"AIService: Analysis results: detected base_intent as {base_intent}")
            
            # 2. Retrieve Past Context/Facts via RAG
            if hasattr(self, 'memory_service') and self.memory_service:
                self.context.long_term_memory = self.memory_service.retrieve_relevant_context(text)
            
            # 3. Advanced NLP Processing
            # Use FAST mode for all pre-classified intents, DETAILED only for unknowns
            process_mode = ProcessingMode.FAST if base_intent in [
                IntentType.TIME_QUERY, IntentType.DATE_QUERY,
                IntentType.DIRECT_COMMAND, IntentType.VISION_QUERY
            ] else ProcessingMode.DETAILED
            
            result = await self.nlp_processor.process_text(
                text, base_intent, self.context, mode=process_mode
            )
            
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
            
    def stop(self):
        self.running = False
        self.wait()

