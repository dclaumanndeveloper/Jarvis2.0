import sys
import os
import asyncio
import logging
import threading
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime

from PyQt6.QtCore import QThread, pyqtSignal, QObject

# Add project root to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nlp_processor import NLPProcessor, NLPResult
from learning_engine import LearningModule
from conversation_manager import ConversationContext, ConversationTurn, IntentType

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

    COMMAND_KEYWORDS = [
        # Original commands
        'abrir', 'fechar', 'tocar', 'aumentar', 'diminuir', 'parar', 'continuar',
        'pesquisar', 'escreva', 'reiniciar', 'desligar', 'horas', 'temperatura',
        'dia', 'print', 'sistema',
        # New media commands
        'próxima', 'anterior', 'mutar', 'silenciar', 'desmutar',
        # New system commands
        'memória', 'cpu', 'disco', 'bloquear', 'lixeira',
        # New utility commands
        'timer', 'traduzir', 'dólar', 'bitcoin', 'calcular', 'quanto é',
        # New file commands
        'pasta', 'download', 'piada'
    ]

    def __init__(self, gemini_key: Optional[str] = None):
        super().__init__()
        self.gemini_key = gemini_key
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
            
            # Initialize NLP Processor
            self.nlp_processor = NLPProcessor(gemini_api_key=self.gemini_key)
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
            text_lower = text.lower()
            if any(kw in text_lower for kw in self.COMMAND_KEYWORDS):
                base_intent = IntentType.DIRECT_COMMAND
                logger.info(f"AIService: Detected potential command keyword, setting base_intent to {base_intent}")
            else:
                base_intent = IntentType.CONVERSATIONAL_QUERY # Default
            
            # 2. Advanced NLP Processing
            result = await self.nlp_processor.process_text(
                text, base_intent, self.context
            )
            
            # 3. Update Context
            self.context.last_command = text
            self.context.conversation_history.append({
                'user_input': text,
                'intent': result.intent.value,
                'timestamp': datetime.now().isoformat(),
                'entities': result.entities,
                'response': result.response_suggestion,
                'confidence': result.confidence
            })
            
            # 4. Emit Result for UI/Execution
            logger.info(f"AIService: Processing finished, emitting result: {result.intent}")
            self.processing_finished.emit(result)
            
            # 5. Check for Proactive Suggestions (Learning)
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

