"""
Advanced NLP Processor for Jarvis 2.0
Integrates Gemini AI 2.0 Flash for enhanced natural language understanding,
contextual processing, and intelligent response generation.
"""

import asyncio
import re
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime

import google.generativeai as genai
from conversation_manager import IntentType, ConversationContext

# Configure logging
# logging.basicConfig(level=logging.INFO) # Controlled by main.py
logger = logging.getLogger(__name__)


class ProcessingMode(Enum):
    """NLP Processing modes"""
    FAST = "fast"           # Quick processing for simple commands
    DETAILED = "detailed"   # Comprehensive analysis for complex queries
    CONTEXTUAL = "contextual"  # Context-aware processing

@dataclass
class NLPResult:
    """Result from NLP processing"""
    original_text: str
    processed_text: str
    intent: IntentType
    confidence: float
    entities: Dict[str, Any]
    context_relevance: float
    response_suggestion: str
    processing_time: float
    gemini_response: Optional[str] = None
    sentiment: Optional[str] = None
    complexity_score: float = 0.0

class EntityExtractor:
    """Enhanced entity extraction with Portuguese language support"""
    
    def __init__(self):
        self.entity_patterns = {
            # Time and date entities
            'datetime': {
                'patterns': [
                    r'\b(hoje|amanhã|ontem|agora|já|depois|antes)\b',
                    r'\b(\d{1,2}):(\d{2})\b',  # Time format
                    r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b',  # Date format
                    r'\b(segunda|terça|quarta|quinta|sexta|sábado|domingo)\b',
                    r'\b(manhã|tarde|noite|madrugada)\b'
                ],
                'type': 'temporal'
            },
            
            # Application entities
            'applications': {
                'patterns': [
                    r'\b(chrome|firefox|edge|navegador)\b',
                    r'\b(vscode|visual studio|código|editor)\b',
                    r'\b(teams|zoom|meet|reunião)\b',
                    r'\b(spotify|youtube|música|player)\b',
                    r'\b(calculadora|calc|calculator)\b',
                    r'\b(explorador|arquivos|pastas|explorer)\b'
                ],
                'type': 'software'
            },
            
            # Action entities
            'actions': {
                'patterns': [
                    r'\b(abrir|abra|abre|iniciar|execute|rodar)\b',
                    r'\b(fechar|feche|parar|pare|finalizar)\b',
                    r'\b(pesquisar|pesquise|buscar|procurar)\b',
                    r'\b(tocar|reproduzir|play|pausar|pausa)\b',
                    r'\b(aumentar|diminuir|ajustar|definir)\b'
                ],
                'type': 'command'
            },
            
            # Volume and numeric entities
            'numbers': {
                'patterns': [
                    r'\b(\d+)%?\b',  # Numbers with optional percentage
                    r'\b(zero|um|dois|três|quatro|cinco|seis|sete|oito|nove|dez)\b',
                    r'\b(vinte|trinta|quarenta|cinquenta|sessenta|setenta|oitenta|noventa|cem)\b'
                ],
                'type': 'numeric'
            },
            
            # Website and service entities
            'websites': {
                'patterns': [
                    r'\b(google|gmail|youtube|facebook|instagram|twitter)\b',
                    r'\b(netflix|spotify|amazon|mercado livre)\b',
                    r'\b(github|stack overflow|wikipedia)\b'
                ],
                'type': 'web_service'
            },
            
            # System entities
            'system': {
                'patterns': [
                    r'\b(volume|som|audio|música)\b',
                    r'\b(tela|monitor|display|brilho)\b',
                    r'\b(sistema|computador|pc|máquina)\b',
                    r'\b(rede|internet|wifi|conexão)\b'
                ],
                'type': 'system_component'
            }
        }
        
        # Portuguese number mapping
        self.number_map = {
            'zero': 0, 'um': 1, 'dois': 2, 'três': 3, 'quatro': 4,
            'cinco': 5, 'seis': 6, 'sete': 7, 'oito': 8, 'nove': 9,
            'dez': 10, 'vinte': 20, 'trinta': 30, 'quarenta': 40,
            'cinquenta': 50, 'sessenta': 60, 'setenta': 70,
            'oitenta': 80, 'noventa': 90, 'cem': 100
        }
    
    def extract_entities(self, text: str, intent: IntentType) -> Dict[str, Any]:
        """Extract entities from text based on intent"""
        entities = {}
        text_lower = text.lower()
        
        # Extract all entity types
        for entity_category, config in self.entity_patterns.items():
            matches = []
            for pattern in config['patterns']:
                found_matches = re.findall(pattern, text_lower)
                if found_matches:
                    matches.extend(found_matches)
            
            if matches:
                entities[entity_category] = {
                    'values': matches,
                    'type': config['type'],
                    'count': len(matches)
                }
        
        # Post-process entities based on intent
        entities = self._post_process_entities(entities, intent, text_lower)
        
        return entities
    
    def _post_process_entities(self, entities: Dict[str, Any], intent: IntentType, text: str) -> Dict[str, Any]:
        """Post-process extracted entities for better accuracy"""
        processed = entities.copy()
        
        # Convert Portuguese numbers to digits
        if 'numbers' in entities:
            converted_numbers = []
            for num_str in entities['numbers']['values']:
                if isinstance(num_str, str) and num_str in self.number_map:
                    converted_numbers.append(self.number_map[num_str])
                else:
                    try:
                        # Extract digits from string
                        digits = re.findall(r'\d+', str(num_str))
                        if digits:
                            converted_numbers.append(int(digits[0]))
                    except (ValueError, TypeError):
                        pass
            
            if converted_numbers:
                processed['numbers']['converted'] = converted_numbers
        
        # Intent-specific processing
        if intent == IntentType.DIRECT_COMMAND:
            processed = self._process_command_entities(processed, text)
        elif intent == IntentType.CONVERSATIONAL_QUERY:
            processed = self._process_query_entities(processed, text)
        
        return processed
    
    def _process_command_entities(self, entities: Dict[str, Any], text: str) -> Dict[str, Any]:
        """Process entities specific to commands"""
        # Extract command targets
        if 'actions' in entities and 'applications' in entities:
            action = entities['actions']['values'][0] if entities['actions']['values'] else None
            app = entities['applications']['values'][0] if entities['applications']['values'] else None
            
            if action and app:
                entities['command_target'] = {
                    'action': action,
                    'target': app,
                    'full_command': f"{action} {app}"
                }
        
        # Extract volume commands
        if 'volume' in text and 'numbers' in entities:
            if 'converted' in entities['numbers']:
                entities['volume_setting'] = {
                    'value': entities['numbers']['converted'][0],
                    'type': 'absolute'
                }
        
        return entities
    
    def _process_query_entities(self, entities: Dict[str, Any], text: str) -> Dict[str, Any]:
        """Process entities specific to queries"""
        # Extract question context
        question_words = re.findall(r'\b(o que|como|quando|onde|por que|qual|quem)\b', text)
        if question_words:
            entities['question_context'] = {
                'type': question_words[0],
                'scope': self._determine_question_scope(text)
            }
        
        return entities
    
    def _determine_question_scope(self, text: str) -> str:
        """Determine the scope of a question"""
        if any(word in text for word in ['tempo', 'clima', 'temperatura']):
            return 'weather'
        elif any(word in text for word in ['hora', 'horas', 'tempo']):
            return 'time'
        elif any(word in text for word in ['notícia', 'notícias', 'novidade']):
            return 'news'
        else:
            return 'general'

class SentimentAnalyzer:
    """Analyze sentiment and emotional context of user input"""
    
    def __init__(self):
        self.positive_indicators = [
            'obrigado', 'obrigada', 'valeu', 'legal', 'ótimo', 'perfeito',
            'maravilhoso', 'excelente', 'fantástico', 'bom', 'boa', 'gostei'
        ]
        
        self.negative_indicators = [
            'ruim', 'péssimo', 'horrível', 'não gostei', 'irritante',
            'chato', 'difícil', 'complicado', 'problema', 'erro'
        ]
        
        self.neutral_indicators = [
            'ok', 'certo', 'beleza', 'tudo bem', 'pode ser', 'talvez'
        ]
    
    def analyze_sentiment(self, text: str) -> Tuple[str, float]:
        """Analyze sentiment of text"""
        text_lower = text.lower()
        
        positive_score = sum(1 for word in self.positive_indicators if word in text_lower)
        negative_score = sum(1 for word in self.negative_indicators if word in text_lower)
        neutral_score = sum(1 for word in self.neutral_indicators if word in text_lower)
        
        total_score = positive_score + negative_score + neutral_score
        
        if total_score == 0:
            return 'neutral', 0.5
        
        if positive_score > negative_score and positive_score > neutral_score:
            confidence = positive_score / (total_score + 1)
            return 'positive', confidence
        elif negative_score > positive_score and negative_score > neutral_score:
            confidence = negative_score / (total_score + 1)
            return 'negative', confidence
        else:
            confidence = neutral_score / (total_score + 1)
            return 'neutral', confidence

class GeminiProcessor:
    """Enhanced Gemini AI processor for complex language understanding"""
    
    def __init__(self, api_key: str):
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
            self.is_configured = True
            logger.info("Gemini AI configured successfully")
        except Exception as e:
            logger.error(f"Failed to configure Gemini AI: {e}")
            self.is_configured = False
    
    async def process_complex_query(self, text: str, context: ConversationContext) -> Dict[str, Any]:
        """Process complex queries using Gemini AI"""
        if not self.is_configured:
            return {'error': 'Gemini AI not configured'}
        
        try:
            # Construct context-aware prompt
            prompt = self._build_contextual_prompt(text, context)
            
            # Generate response
            response = await self._generate_response(prompt)
            
            # Parse and structure response
            structured_response = self._parse_gemini_response(response)
            
            return structured_response
            
        except Exception as e:
            logger.error(f"Gemini processing error: {e}")
            return {'error': str(e)}
    
    def _build_contextual_prompt(self, text: str, context: ConversationContext) -> str:
        """Build a contextual prompt for Gemini"""
        
        context_info = ""
        if context.current_topic:
            context_info += f"Tópico atual da conversa: {context.current_topic}\n"
        
        if context.last_command:
            context_info += f"Último comando executado: {context.last_command}\n"
        
        if context.conversation_history:
            recent_history = list(context.conversation_history)[-3:]  # Last 3 turns
            context_info += "Histórico recente:\n"
            for turn in recent_history:
                context_info += f"- Usuário: {turn.get('user_input', '')}\n"
        
        prompt = f"""
Você é Jarvis, um assistente virtual inteligente similar ao do Homem de Ferro.
Analise a entrada do usuário e forneça uma resposta estruturada em JSON.

Contexto da conversa:
{context_info}

Entrada do usuário: "{text}"

Forneça uma resposta em JSON com:
1. "intent_classification": classificação da intenção (direct_command, conversational_query, contextual_reference, etc.)
2. "confidence": nível de confiança (0.0 a 1.0)
3. "suggested_response": resposta sugerida para o usuário
4. "action_required": ação específica a ser executada (se aplicável)
5. "context_usage": como o contexto influenciou a interpretação
6. "followup_suggestions": sugestões de próximas ações

Responda apenas em português e mantenha o tom profissional mas amigável do Jarvis.
"""
        
        return prompt
    
    async def _generate_response(self, prompt: str) -> str:
        """Generate response from Gemini AI"""
        try:
            response = await self.model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini generation error: {e}")
            raise
    
    def _parse_gemini_response(self, response_text: str) -> Dict[str, Any]:
        """Parse and validate Gemini response"""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                parsed = json.loads(json_str)
                return parsed
            else:
                # Fallback for non-JSON responses
                return {
                    'suggested_response': response_text,
                    'intent_classification': 'conversational_query',
                    'confidence': 0.7,
                    'action_required': None,
                    'context_usage': 'Limited context processing',
                    'followup_suggestions': []
                }
        except json.JSONDecodeError:
            # Handle malformed JSON
            return {
                'suggested_response': response_text,
                'parsing_error': True,
                'confidence': 0.5
            }

class ContextualIntentAnalyzer:
    """Analyzes intent with conversation context"""
    
    def __init__(self):
        self.context_patterns = {
            'continuation': [
                r'\b(continuar|continua|seguir|próximo|e depois)\b',
                r'\b(também|ainda|mais|além disso)\b'
            ],
            'reference': [
                r'\b(isso|aquilo|anterior|último|esse|essa)\b',
                r'\b(novamente|de novo|outra vez)\b'
            ],
            'clarification': [
                r'\b(não entendi|repita|como assim|explique melhor|não compreendi)\b',
                r'\b(o que você disse|o que você falou|pode repetir)\b',
                r'^(que|o que|hein)\?$'
            ]
        }
    
    def analyze_contextual_intent(self, text: str, context: ConversationContext, 
                                 base_intent: IntentType) -> Tuple[IntentType, float]:
        """Analyze intent considering conversation context"""
        
        text_lower = text.lower()
        context_score = 0.0
        
        # Check for contextual patterns
        if self._matches_pattern(text_lower, 'continuation'):
            if context.last_command:
                return IntentType.CONTEXTUAL_REFERENCE, 0.9
            context_score += 0.3
        
        if self._matches_pattern(text_lower, 'reference'):
            if len(context.conversation_history) > 0:
                return IntentType.CONTEXTUAL_REFERENCE, 0.8
            context_score += 0.2
        
        if self._matches_pattern(text_lower, 'clarification'):
            return IntentType.CLARIFICATION_REQUEST, 0.9
        
        # Adjust base intent confidence based on context
        confidence = 0.7 + context_score
        
        return base_intent, min(confidence, 1.0)
    
    def _matches_pattern(self, text: str, pattern_type: str) -> bool:
        """Check if text matches contextual patterns"""
        patterns = self.context_patterns.get(pattern_type, [])
        return any(re.search(pattern, text) for pattern in patterns)

class NLPProcessor:
    """
    Main NLP Processor that orchestrates all NLP components
    for enhanced natural language understanding in Jarvis 2.0
    """
    
    def __init__(self, gemini_api_key: str = None):
        self.entity_extractor = EntityExtractor()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.contextual_analyzer = ContextualIntentAnalyzer()
        
        # Initialize Gemini processor if API key provided
        self.gemini_processor = None
        if gemini_api_key:
            self.gemini_processor = GeminiProcessor(gemini_api_key)
        
        # Configuration
        self.use_gemini_for_complex = True
        self.complexity_threshold = 0.7
        
    async def process_text(self, text: str, base_intent: IntentType, 
                          context: ConversationContext, 
                          mode: ProcessingMode = ProcessingMode.DETAILED) -> NLPResult:
        """Main text processing method"""
        
        start_time = time.time()
        
        # Analyze sentiment
        sentiment, sentiment_confidence = self.sentiment_analyzer.analyze_sentiment(text)
        
        # Extract entities
        entities = self.entity_extractor.extract_entities(text, base_intent)
        
        # Refine intent with context
        refined_intent, intent_confidence = self.contextual_analyzer.analyze_contextual_intent(
            text, context, base_intent
        )
        
        # Calculate complexity score
        complexity_score = self._calculate_complexity(text, entities)
        
        # Generate response suggestion
        response_suggestion = await self._generate_response_suggestion(
            text, refined_intent, entities, context, complexity_score
        )
        
        # Use Gemini for complex queries if available
        gemini_response = None
        if (self.gemini_processor and 
            complexity_score > self.complexity_threshold and 
            mode != ProcessingMode.FAST):
            
            gemini_result = await self.gemini_processor.process_complex_query(text, context)
            gemini_response = gemini_result.get('suggested_response')
            
            # Override response if Gemini provides better suggestion
            if gemini_response and 'error' not in gemini_result:
                response_suggestion = gemini_response
                intent_confidence = min(intent_confidence + 0.1, 1.0)
        
        processing_time = time.time() - start_time
        
        return NLPResult(
            original_text=text,
            processed_text=text.strip().lower(),
            intent=refined_intent,
            confidence=intent_confidence,
            entities=entities,
            context_relevance=self._calculate_context_relevance(text, context),
            response_suggestion=response_suggestion,
            processing_time=processing_time,
            gemini_response=gemini_response,
            sentiment=sentiment,
            complexity_score=complexity_score
        )
    
    def _calculate_complexity(self, text: str, entities: Dict[str, Any]) -> float:
        """Calculate complexity score for text"""
        complexity = 0.0
        
        # Length factor
        complexity += min(len(text.split()) / 20, 0.3)
        
        # Entity count factor
        entity_count = sum(len(entity_data.get('values', [])) for entity_data in entities.values())
        complexity += min(entity_count / 10, 0.3)
        
        # Question words factor
        question_words = ['o que', 'como', 'quando', 'onde', 'por que', 'qual', 'quem']
        if any(qw in text.lower() for qw in question_words):
            complexity += 0.2
        
        # Negation and conditionals
        if any(word in text.lower() for word in ['não', 'mas', 'porém', 'se', 'caso']):
            complexity += 0.2
        
        return min(complexity, 1.0)
    
    def _calculate_context_relevance(self, text: str, context: ConversationContext) -> float:
        """Calculate how relevant the current context is to the text"""
        relevance = 0.0
        
        if not context:
            return 0.0
        
        text_lower = text.lower()
        
        # Topic relevance
        if context.current_topic:
            topic_words = context.current_topic.split()
            if any(word in text_lower for word in topic_words):
                relevance += 0.4
        
        # Reference words
        reference_words = ['isso', 'aquilo', 'anterior', 'último', 'esse', 'essa']
        if any(word in text_lower for word in reference_words):
            relevance += 0.3
        
        # Recent history relevance
        if context.conversation_history:
            recent_turn = list(context.conversation_history)[-1]
            if recent_turn and 'user_input' in recent_turn:
                recent_words = recent_turn['user_input'].lower().split()
                common_words = set(text_lower.split()) & set(recent_words)
                if common_words:
                    relevance += min(len(common_words) / 5, 0.3)
        
        return min(relevance, 1.0)
    
    async def _generate_response_suggestion(self, text: str, intent: IntentType, 
                                          entities: Dict[str, Any], context: ConversationContext,
                                          complexity: float) -> str:
        """Generate response suggestion based on analysis"""
        
        # Simple rule-based responses for common intents
        if intent == IntentType.DIRECT_COMMAND:
            if 'command_target' in entities:
                action = entities['command_target']['action']
                target = entities['command_target']['target']
                return f"Entendido. Vou {action} {target} agora."
            else:
                return "Comando reconhecido. Executando..."
        
        elif intent == IntentType.CONVERSATIONAL_QUERY:
            if complexity > 0.6:
                return "Deixe-me processar essa questão complexa para você."
            else:
                return "Vou buscar essas informações."
        
        elif intent == IntentType.CONTEXTUAL_REFERENCE:
            if context.last_command:
                return f"Entendi. Continuando com {context.last_command}."
            else:
                return "Baseado no que conversamos anteriormente..."
        
        elif intent == IntentType.CLARIFICATION_REQUEST:
            return "Poderia ser mais específico? Estou aqui para ajudar."
        
        elif intent == IntentType.EMOTIONAL_EXPRESSION:
            sentiment = entities.get('sentiment', 'neutral')
            if sentiment == 'positive':
                return "Fico feliz em ajudar! Sempre à disposição."
            elif sentiment == 'negative':
                return "Lamento se algo não saiu como esperado. Como posso melhorar?"
            else:
                return "Entendido. Posso ajudar com mais alguma coisa?"
        
        else:
            return "Compreendo. Como posso ajudar?"

# Example usage and testing
async def main():
    """Example usage of NLP Processor"""
    
    # Initialize processor (use actual Gemini API key in production)
    processor = NLPProcessor(gemini_api_key="AIzaSyBuOScNR-FI818vE_JIZTx3J0X8YVgVpKw")
    
    # Create sample context
    from conversation_manager import ConversationContext
    context = ConversationContext()
    context.current_topic = "música"
    context.last_command = "tocar spotify"
    
    # Test utterances
    test_utterances = [
        ("abrir chrome e pesquisar sobre python", IntentType.DIRECT_COMMAND),
        ("o que você sabe sobre inteligência artificial?", IntentType.CONVERSATIONAL_QUERY),
        ("isso está muito lento", IntentType.CONTEXTUAL_REFERENCE),
        ("não entendi o que você disse", IntentType.CLARIFICATION_REQUEST),
        ("obrigado pela ajuda", IntentType.EMOTIONAL_EXPRESSION)
    ]
    
    print("🧠 Testing NLP Processor...")
    
    for utterance, base_intent in test_utterances:
        print(f"\n👤 Input: {utterance}")
        print(f"🎯 Base Intent: {base_intent.value}")
        
        result = await processor.process_text(utterance, base_intent, context)
        
        print(f"🔍 Refined Intent: {result.intent.value} (confidence: {result.confidence:.2f})")
        print(f"📊 Entities: {list(result.entities.keys())}")
        print(f"🎭 Sentiment: {result.sentiment}")
        print(f"🧮 Complexity: {result.complexity_score:.2f}")
        print(f"🔗 Context Relevance: {result.context_relevance:.2f}")
        print(f"💬 Response: {result.response_suggestion}")
        if result.gemini_response:
            print(f"🤖 Gemini: {result.gemini_response[:100]}...")
        print(f"⏱️  Processing Time: {result.processing_time:.3f}s")

if __name__ == "__main__":
    asyncio.run(main())