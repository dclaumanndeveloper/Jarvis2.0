"""
Conversation Manager for Jarvis 2.0
Handles conversation state, context retention, and natural dialogue flow
to create Iron Man's Jarvis-like continuous conversation experience.
"""

import asyncio
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import logging
from collections import deque
import re

# Configure logging
# logging.basicConfig(level=logging.INFO) # Controlled by main.py
logger = logging.getLogger(__name__)


class ConversationMode(Enum):
    """Different conversation modes"""
    WAKE_WORD = "wake_word"         # Traditional wake word activation
    CONTINUOUS = "continuous"       # Always listening mode
    SESSION_BASED = "session_based" # Session with timeout
    HYBRID = "hybrid"              # Smart switching between modes

class IntentType(Enum):
    """Types of user intents"""
    DIRECT_COMMAND = "direct_command"
    CONVERSATIONAL_QUERY = "conversational_query"
    CONTEXTUAL_REFERENCE = "contextual_reference"
    CLARIFICATION_REQUEST = "clarification_request"
    EMOTIONAL_EXPRESSION = "emotional_expression"
    FOLLOW_UP = "follow_up"
    UNKNOWN = "unknown"

class ContextType(Enum):
    """Types of conversation context"""
    COMMAND_HISTORY = "command_history"
    USER_PREFERENCES = "user_preferences"
    CURRENT_TASK = "current_task"
    ENVIRONMENTAL = "environmental"
    TEMPORAL = "temporal"

@dataclass
class ConversationTurn:
    """Represents a single turn in conversation"""
    id: str
    timestamp: datetime
    user_input: str
    recognized_text: str
    confidence_score: float
    intent: IntentType
    entities: Dict[str, Any]
    context: Dict[str, Any]
    response: str
    response_time: float
    satisfaction_score: Optional[float] = None
    audio_features: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ConversationContext:
    """Maintains conversation context information"""
    current_topic: Optional[str] = None
    last_command: Optional[str] = None
    user_references: Dict[str, Any] = field(default_factory=dict)
    environmental_state: Dict[str, Any] = field(default_factory=dict)
    conversation_history: deque = field(default_factory=lambda: deque(maxlen=50))
    active_variables: Dict[str, Any] = field(default_factory=dict)
    pending_clarifications: List[str] = field(default_factory=list)

class ConversationState:
    """Manages the current state of conversation"""
    
    def __init__(self, max_context_window: int = 300):
        self.session_id: str = str(uuid.uuid4())
        self.start_time: datetime = datetime.now()
        self.last_activity: datetime = datetime.now()
        self.mode: ConversationMode = ConversationMode.CONTINUOUS
        self.is_active: bool = False
        self.max_context_window: int = max_context_window  # seconds
        
        # Context management
        self.context: ConversationContext = ConversationContext()
        self.turn_history: List[ConversationTurn] = []
        
        # Conversation flow
        self.expecting_response: bool = False
        self.waiting_for_clarification: bool = False
        self.proactive_suggestions_enabled: bool = True
        
    def is_context_valid(self) -> bool:
        """Check if current context is still valid"""
        time_since_activity = (datetime.now() - self.last_activity).total_seconds()
        return time_since_activity <= self.max_context_window
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now()
    
    def add_turn(self, turn: ConversationTurn):
        """Add a conversation turn to history"""
        self.turn_history.append(turn)
        self.context.conversation_history.append({
            'timestamp': turn.timestamp.isoformat(),
            'user_input': turn.user_input,
            'intent': turn.intent.value,
            'response': turn.response
        })
        self.update_activity()

class IntentClassifier:
    """Classifies user intents from conversation"""
    
    def __init__(self):
        # Intent patterns for Portuguese
        self.intent_patterns = {
            IntentType.DIRECT_COMMAND: [
                r'\b(abrir|fechar|tocar|parar|aumentar|diminuir|definir)\b',
                r'\b(pesquisar|buscar|procurar)\b',
                r'\b(ligar|desligar|ativar|desativar)\b',
                r'\b(executar|rodar|iniciar|finalizar)\b'
            ],
            IntentType.CONVERSATIONAL_QUERY: [
                r'\b(o que é|como|quando|onde|por que|qual)\b',
                r'\b(me fale sobre|explique|conte)\b',
                r'\b(você sabe|você conhece)\b'
            ],
            IntentType.CONTEXTUAL_REFERENCE: [
                r'\b(isso|aquilo|anterior|último|passado)\b',
                r'\b(continuar|continua|seguir|próximo)\b',
                r'\b(novamente|de novo|outra vez)\b'
            ],
            IntentType.CLARIFICATION_REQUEST: [
                r'\b(não entendi|repita|como assim|o que)\b',
                r'\b(pode repetir|não compreendi)\b'
            ],
            IntentType.EMOTIONAL_EXPRESSION: [
                r'\b(obrigado|valeu|legal|ótimo|perfeito)\b',
                r'\b(ruim|péssimo|não gostei|irritante)\b'
            ]
        }
    
    def classify_intent(self, text: str, context: ConversationContext) -> IntentType:
        """Classify user intent based on text and context"""
        text_lower = text.lower()
        
        # Check for contextual references first
        if self._has_recent_context(context) and self._matches_patterns(text_lower, IntentType.CONTEXTUAL_REFERENCE):
            return IntentType.CONTEXTUAL_REFERENCE
        
        # Check other intent types
        for intent_type, patterns in self.intent_patterns.items():
            if self._matches_patterns(text_lower, intent_type):
                return intent_type
        
        # Check if it's a follow-up based on context
        if self._is_follow_up(text_lower, context):
            return IntentType.FOLLOW_UP
        
        return IntentType.UNKNOWN
    
    def _matches_patterns(self, text: str, intent_type: IntentType) -> bool:
        """Check if text matches intent patterns"""
        patterns = self.intent_patterns.get(intent_type, [])
        return any(re.search(pattern, text) for pattern in patterns)
    
    def _has_recent_context(self, context: ConversationContext) -> bool:
        """Check if there's recent conversation context"""
        return len(context.conversation_history) > 0
    
    def _is_follow_up(self, text: str, context: ConversationContext) -> bool:
        """Determine if this is a follow-up to previous conversation"""
        follow_up_indicators = ['sim', 'não', 'ok', 'certo', 'beleza', 'pode ser']
        return any(indicator in text for indicator in follow_up_indicators)

class ContextAnalyzer:
    """Analyzes and maintains conversation context"""
    
    def __init__(self):
        self.entity_patterns = {
            'time_references': r'\b(agora|hoje|amanhã|ontem|manhã|tarde|noite)\b',
            'applications': r'\b(chrome|vscode|teams|calculadora|arquivos)\b',
            'actions': r'\b(abrir|fechar|tocar|parar|pesquisar)\b',
            'volumes': r'\b(\d+%?|alto|baixo|médio)\b'
        }
    
    def extract_entities(self, text: str, intent: IntentType) -> Dict[str, Any]:
        """Extract entities from user input"""
        entities = {}
        text_lower = text.lower()
        
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.findall(pattern, text_lower)
            if matches:
                entities[entity_type] = matches
        
        # Intent-specific entity extraction
        if intent == IntentType.DIRECT_COMMAND:
            entities.update(self._extract_command_entities(text_lower))
        elif intent == IntentType.CONVERSATIONAL_QUERY:
            entities.update(self._extract_query_entities(text_lower))
        
        return entities
    
    def _extract_command_entities(self, text: str) -> Dict[str, Any]:
        """Extract entities specific to commands"""
        entities = {}
        
        # Extract target objects for commands
        if 'abrir' in text:
            # Extract what to open
            after_abrir = text.split('abrir', 1)[-1].strip()
            if after_abrir:
                entities['target'] = after_abrir
        
        # Extract volume levels
        volume_match = re.search(r'volume\s+(\d+)', text)
        if volume_match:
            entities['volume_level'] = int(volume_match.group(1))
        
        return entities
    
    def _extract_query_entities(self, text: str) -> Dict[str, Any]:
        """Extract entities from queries"""
        entities = {}
        
        # Extract question words
        question_words = re.findall(r'\b(o que|como|quando|onde|por que|qual)\b', text)
        if question_words:
            entities['question_type'] = question_words[0]
        
        return entities
    
    def update_context(self, context: ConversationContext, turn: ConversationTurn):
        """Update conversation context based on latest turn"""
        # Update current topic
        if turn.intent in [IntentType.DIRECT_COMMAND, IntentType.CONVERSATIONAL_QUERY]:
            context.current_topic = self._extract_topic(turn.user_input)
        
        # Update last command
        if turn.intent == IntentType.DIRECT_COMMAND:
            context.last_command = turn.user_input
        
        # Update user references for contextual commands
        if 'target' in turn.entities:
            context.user_references['last_target'] = turn.entities['target']
        
        # Update environmental state
        context.environmental_state['last_interaction'] = turn.timestamp.isoformat()
    
    def _extract_topic(self, text: str) -> str:
        """Extract main topic from user input"""
        # Simple topic extraction - can be enhanced with NLP
        words = text.lower().split()
        # Remove common words and extract potential topics
        stop_words = {'o', 'a', 'os', 'as', 'um', 'uma', 'de', 'do', 'da', 'em', 'no', 'na'}
        meaningful_words = [w for w in words if w not in stop_words and len(w) > 2]
        return ' '.join(meaningful_words[:3]) if meaningful_words else 'geral'

class ResponseGenerator:
    """Generates contextual responses for different conversation scenarios"""
    
    def __init__(self):
        self.response_templates = {
            IntentType.DIRECT_COMMAND: [
                "Executando {action}...",
                "Claro, vou {action} agora.",
                "Entendido. {action} em andamento."
            ],
            IntentType.CONVERSATIONAL_QUERY: [
                "Deixe-me pesquisar isso para você.",
                "Vou buscar essas informações.",
                "Interessante pergunta. Vou investigar."
            ],
            IntentType.CONTEXTUAL_REFERENCE: [
                "Continuando com {context}...",
                "Baseado no que conversamos antes...",
                "Entendi a referência ao {context}."
            ],
            IntentType.CLARIFICATION_REQUEST: [
                "Poderia ser mais específico?",
                "Não entendi completamente. Pode reformular?",
                "Preciso de mais detalhes para ajudar melhor."
            ],
            IntentType.EMOTIONAL_EXPRESSION: [
                "Fico feliz em ajudar!",
                "Sempre à disposição!",
                "É um prazer ser útil."
            ]
        }
    
    def generate_response(self, intent: IntentType, entities: Dict[str, Any], 
                         context: ConversationContext) -> str:
        """Generate appropriate response based on intent and context"""
        
        templates = self.response_templates.get(intent, ["Entendido."])
        
        # Select template based on context
        template = self._select_template(templates, context)
        
        # Fill template with entities
        response = self._fill_template(template, entities, context)
        
        return response
    
    def _select_template(self, templates: List[str], context: ConversationContext) -> str:
        """Select appropriate template based on context"""
        # Simple selection - can be enhanced with ML
        if len(context.conversation_history) > 5:
            # Use more conversational templates for longer conversations
            return templates[-1] if len(templates) > 1 else templates[0]
        else:
            return templates[0]
    
    def _fill_template(self, template: str, entities: Dict[str, Any], 
                      context: ConversationContext) -> str:
        """Fill template with appropriate values"""
        response = template
        
        # Replace placeholders
        if '{action}' in response and 'actions' in entities:
            response = response.replace('{action}', entities['actions'][0])
        
        if '{context}' in response and context.current_topic:
            response = response.replace('{context}', context.current_topic)
        
        return response

class ConversationManager:
    """
    Main conversation manager that orchestrates all conversation components
    to provide Iron Man's Jarvis-like continuous conversation experience
    """
    
    def __init__(self, max_context_window: int = 300):
        self.state = ConversationState(max_context_window)
        self.intent_classifier = IntentClassifier()
        self.context_analyzer = ContextAnalyzer()
        self.response_generator = ResponseGenerator()
        
        # Callbacks for external integration
        self.on_intent_classified: Optional[Callable] = None
        self.on_response_generated: Optional[Callable] = None
        self.on_context_updated: Optional[Callable] = None
        self.on_proactive_suggestion: Optional[Callable] = None
        
        # Configuration
        self.proactive_suggestion_delay = 10.0  # seconds
        self.context_cleanup_interval = 60.0    # seconds
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._suggestion_task: Optional[asyncio.Task] = None
    
    async def start_conversation_session(self, mode: ConversationMode = ConversationMode.CONTINUOUS):
        """Start a new conversation session"""
        logger.info(f"Starting conversation session in {mode.value} mode")
        
        self.state.mode = mode
        self.state.is_active = True
        self.state.session_id = str(uuid.uuid4())
        self.state.start_time = datetime.now()
        self.state.update_activity()
        
        # Start background tasks
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        if self.state.proactive_suggestions_enabled:
            self._suggestion_task = asyncio.create_task(self._proactive_suggestions())
    
    async def end_conversation_session(self):
        """End the current conversation session"""
        logger.info("Ending conversation session")
        
        self.state.is_active = False
        
        # Cancel background tasks
        if self._cleanup_task:
            self._cleanup_task.cancel()
        if self._suggestion_task:
            self._suggestion_task.cancel()
        
        # Save conversation history if needed
        await self._save_conversation_history()
    
    async def process_utterance(self, text: str, confidence: float, 
                               audio_features: Dict[str, Any] = None) -> ConversationTurn:
        """Process a user utterance and generate appropriate response"""
        
        if not self.state.is_active:
            await self.start_conversation_session()
        
        # Create conversation turn
        turn_id = str(uuid.uuid4())
        timestamp = datetime.now()
        
        # Classify intent
        intent = self.intent_classifier.classify_intent(text, self.state.context)
        
        # Extract entities
        entities = self.context_analyzer.extract_entities(text, intent)
        
        # Generate response
        response = self.response_generator.generate_response(
            intent, entities, self.state.context
        )
        
        # Create conversation turn
        turn = ConversationTurn(
            id=turn_id,
            timestamp=timestamp,
            user_input=text,
            recognized_text=text,
            confidence_score=confidence,
            intent=intent,
            entities=entities,
            context=self._serialize_context(),
            response=response,
            response_time=time.time(),
            audio_features=audio_features or {}
        )
        
        # Update conversation state
        self.state.add_turn(turn)
        self.context_analyzer.update_context(self.state.context, turn)
        
        # Trigger callbacks
        if self.on_intent_classified:
            self.on_intent_classified(intent, entities)
        
        if self.on_response_generated:
            self.on_response_generated(response, turn)
        
        if self.on_context_updated:
            self.on_context_updated(self.state.context)
        
        logger.info(f"Processed utterance: '{text}' -> Intent: {intent.value}")
        
        return turn
    
    def should_continue_listening(self) -> bool:
        """Determine if conversation should continue"""
        if not self.state.is_active:
            return False
        
        if self.state.mode == ConversationMode.CONTINUOUS:
            return True
        elif self.state.mode == ConversationMode.SESSION_BASED:
            return self.state.is_context_valid()
        elif self.state.mode == ConversationMode.WAKE_WORD:
            return False  # Always stop after one interaction
        
        return True
    
    def get_conversation_context(self) -> ConversationContext:
        """Get current conversation context"""
        return self.state.context
    
    def get_conversation_history(self) -> List[ConversationTurn]:
        """Get conversation history"""
        return self.state.turn_history
    
    async def _periodic_cleanup(self):
        """Periodically clean up old context and optimize memory"""
        while self.state.is_active:
            try:
                await asyncio.sleep(self.context_cleanup_interval)
                
                # Clean up old context if needed
                if not self.state.is_context_valid():
                    self._cleanup_old_context()
                
                # Optimize conversation history
                self._optimize_conversation_history()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
    
    async def _proactive_suggestions(self):
        """Generate proactive suggestions based on patterns"""
        while self.state.is_active:
            try:
                await asyncio.sleep(self.proactive_suggestion_delay)
                
                if len(self.state.turn_history) > 0:
                    suggestion = self._generate_proactive_suggestion()
                    if suggestion and self.on_proactive_suggestion:
                        self.on_proactive_suggestion(suggestion)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in proactive suggestions: {e}")
    
    def _cleanup_old_context(self):
        """Clean up old context data"""
        logger.debug("Cleaning up old conversation context")
        
        # Clear old references
        cutoff_time = datetime.now() - timedelta(seconds=self.state.max_context_window)
        
        # Keep only recent turns
        self.state.turn_history = [
            turn for turn in self.state.turn_history 
            if turn.timestamp > cutoff_time
        ]
        
        # Clear old environmental state
        self.state.context.environmental_state.clear()
    
    def _optimize_conversation_history(self):
        """Optimize conversation history for memory efficiency"""
        # Keep only essential information for older turns
        if len(self.state.turn_history) > 20:
            # Compress older turns
            for turn in self.state.turn_history[:-10]:  # Keep last 10 full
                # Remove audio features from older turns
                turn.audio_features = {}
    
    def _generate_proactive_suggestion(self) -> Optional[str]:
        """Generate proactive suggestions based on conversation patterns"""
        if len(self.state.turn_history) < 2:
            return None
        
        recent_turns = self.state.turn_history[-3:]
        
        # Check for patterns
        if self._detect_routine_pattern(recent_turns):
            return "Notei que você sempre executa esses comandos em sequência. Gostaria que eu criasse uma rotina?"
        
        return None
    
    def _detect_routine_pattern(self, turns: List[ConversationTurn]) -> bool:
        """Detect if recent turns form a routine pattern"""
        # Simple pattern detection - can be enhanced
        command_turns = [t for t in turns if t.intent == IntentType.DIRECT_COMMAND]
        return len(command_turns) >= 2
    
    def _serialize_context(self) -> Dict[str, Any]:
        """Serialize current context for storage"""
        return {
            'current_topic': self.state.context.current_topic,
            'last_command': self.state.context.last_command,
            'user_references': dict(self.state.context.user_references),
            'environmental_state': dict(self.state.context.environmental_state),
            'timestamp': datetime.now().isoformat()
        }
    
    def _write_history_to_file(self, filename: str, session_data: Dict[str, Any], turns: List[ConversationTurn]):
        """Write history data to file synchronously"""
        # Construct history_data here to offload CPU work
        history_data = {
            **session_data,
            'end_time': datetime.now().isoformat(),
            'turns': [
                {
                    'timestamp': turn.timestamp.isoformat(),
                    'user_input': turn.user_input,
                    'intent': turn.intent.value,
                    'entities': turn.entities,
                    'response': turn.response,
                    'confidence': turn.confidence_score
                }
                for turn in turns
            ]
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)

    async def _save_conversation_history(self):
        """Save conversation history for learning purposes"""
        try:
            # Prepare basic session data
            session_data = {
                'session_id': self.state.session_id,
                'start_time': self.state.start_time.isoformat(),
                'mode': self.state.mode.value,
            }
            
            # Save to file (can be enhanced to use database)
            filename = f"conversation_{self.state.session_id}.json"

            # Create a shallow copy of turns to ensure thread safety
            turns_copy = list(self.state.turn_history)

            # Run blocking I/O and data processing in a separate thread
            await asyncio.to_thread(self._write_history_to_file, filename, session_data, turns_copy)
            
            logger.info(f"Conversation history saved: {filename}")
            
        except Exception as e:
            logger.error(f"Failed to save conversation history: {e}")
    
    def set_callbacks(self,
                     on_intent_classified: Callable = None,
                     on_response_generated: Callable = None,
                     on_context_updated: Callable = None,
                     on_proactive_suggestion: Callable = None):
        """Set callback functions for events"""
        self.on_intent_classified = on_intent_classified
        self.on_response_generated = on_response_generated
        self.on_context_updated = on_context_updated
        self.on_proactive_suggestion = on_proactive_suggestion

# Example usage
async def main():
    """Example usage of Conversation Manager"""
    
    def on_intent_classified(intent, entities):
        print(f"🎯 Intent: {intent.value}, Entities: {entities}")
    
    def on_response_generated(response, turn):
        print(f"🤖 Response: {response}")
    
    def on_context_updated(context):
        print(f"📝 Context updated: Topic={context.current_topic}")
    
    def on_proactive_suggestion(suggestion):
        print(f"💡 Suggestion: {suggestion}")
    
    # Create conversation manager
    manager = ConversationManager()
    
    # Set callbacks
    manager.set_callbacks(
        on_intent_classified=on_intent_classified,
        on_response_generated=on_response_generated,
        on_context_updated=on_context_updated,
        on_proactive_suggestion=on_proactive_suggestion
    )
    
    # Start conversation session
    await manager.start_conversation_session(ConversationMode.CONTINUOUS)
    
    # Simulate conversation
    test_utterances = [
        "abrir chrome",
        "pesquisar sobre python",
        "aumentar volume",
        "isso está muito baixo",
        "obrigado pela ajuda"
    ]
    
    print("🗣️  Simulating conversation...")
    for utterance in test_utterances:
        print(f"\n👤 User: {utterance}")
        turn = await manager.process_utterance(utterance, 0.9)
        await asyncio.sleep(1)
    
    # End session
    await manager.end_conversation_session()

if __name__ == "__main__":
    asyncio.run(main())