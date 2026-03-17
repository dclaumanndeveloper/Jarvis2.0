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

import aiohttp
import os
from conversation_manager import ConversationContext, IntentType
# Configure logging
# logging.basicConfig(level=logging.INFO) # Controlled by main.py
logger = logging.getLogger(__name__)

class LocalAIProcessor:
    """Processor for local AI using Llama-cpp (standalone) or Ollama API (fallback)"""
    def __init__(self, model_name: str = "qwen2:1.5b"):
        self.ollama_url = "http://localhost:11434/api/generate"
        self.model_name = model_name
        
        # Standalone Config
        self.use_llama_cpp = False
        self.llm = None
        self.clip_model = None # For Vision
        
        # Try to find a local GGUF model in 'models/' directory
        model_dir = os.path.join(os.path.dirname(__file__), "models")
        # Filter out mmproj files (vision projectors) - we only want LLM models
        gguf_files = [f for f in os.listdir(model_dir) if f.endswith(".gguf") and "mmproj" not in f.lower()] if os.path.exists(model_dir) else []
        
        if gguf_files:
            try:
                from llama_cpp import Llama
                model_path = os.path.join(model_dir, gguf_files[0])
                logger.info(f"LocalAIProcessor: Loading standalone model {model_path}...")

                # Suppress warnings about sampler attribute in newer llama-cpp versions
                import warnings
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", category=UserWarning)
                    self.llm = Llama(
                        model_path=model_path,
                        n_ctx=2048,
                        n_threads=os.cpu_count() or 4,
                        verbose=False
                    )

                self.use_llama_cpp = True
                self.system_prompt_tokens = self.llm.tokenize(
                    self._get_base_system_prompt().encode('utf-8')
                )
                
                # Check for Vision Projector (mmproj)
                mmproj_files = [f for f in os.listdir(model_dir) if "mmproj" in f.lower()]
                if mmproj_files:
                    from llama_cpp.llama_chat_format import Llava15ChatHandler
                    self.clip_model = Llava15ChatHandler(
                        clip_model_path=os.path.join(model_dir, mmproj_files[0]),
                        verbose=False
                    )
                    logger.info(f"LocalAIProcessor: Multimodal VLM (Clip) loaded: {mmproj_files[0]}")

                logger.info("LocalAIProcessor: Standalone Llama-cpp with KV Cache active.")
            except Exception as e:
                logger.warning(f"LocalAIProcessor: Failed to load Llama-cpp ({e}). Falling back to Ollama API.")
        else:
            logger.info("LocalAIProcessor: No .gguf model found in models/. Using Ollama API mode.")

    async def process_complex_query(self, text: str, context: ConversationContext, stream_callback=None) -> Dict[str, Any]:
        """Process query using local Llama-cpp instance or Ollama API with optional streaming"""
        if self.use_llama_cpp and self.llm:
            # For standalone, we use a more efficient prompt that reuses cached tokens
            return await self._process_via_llama_cpp(text, context, stream_callback)
        else:
            prompt = self._build_contextual_prompt(text, context)
            return await self._process_via_ollama(prompt)

    def _get_base_system_prompt(self) -> str:
        """Fixed system prompt for token reuse"""
        return "You are J.A.R.V.I.S., a smart AI assistant. Classify the user's intent and return ONLY a valid JSON object."

    async def _process_via_llama_cpp(self, text: str, context: ConversationContext, stream_callback=None) -> Dict[str, Any]:
        """Inference using llama-cpp-python with KV Cache optimization and streaming"""
        try:
            short_mem = str(context.long_term_memory)[:150] if context.long_term_memory else "None"
            # Build prompt suffix (the dynamic part)
            prompt_suffix = f"\n\nMEMORY: {short_mem}\nTOPIC: {context.current_topic}\n\nUser: \"{text}\"\nJSON (ONLY output the JSON, nothing else):\n"
            
            full_text = ""
            
            def run_inference():
                nonlocal full_text
                # If streaming is requested, we iterate over the completion
                if stream_callback:
                    # We need to manually handle the JSON generation stream
                    # Llama-cpp stream returns chunks
                    stream = self.llm(
                        prompt=self._get_base_system_prompt() + prompt_suffix,
                        max_tokens=150,
                        temperature=0.3,
                        stop=["User:", "\n\n"],
                        stream=True
                    )
                    for chunk in stream:
                        token = chunk['choices'][0]['text']
                        if token:
                            full_text += token
                            stream_callback(token)
                else:
                    response = self.llm(
                        prompt=self._get_base_system_prompt() + prompt_suffix,
                        max_tokens=150,
                        temperature=0.3,
                        stop=["User:", "\n\n"],
                        echo=False
                    )
                    full_text = response['choices'][0]['text'].strip()

            await asyncio.to_thread(run_inference)
            return self._parse_local_response(full_text)
        except Exception as e:
            logger.error(f"Llama-cpp error: {e}")
            return {'error': str(e), 'suggested_response': "Erro no processador neural standalone."}

    async def process_image(self, image_path: str, prompt: str) -> str:
        """Analyze an image using a multimodal local model"""
        if not self.clip_model or not self.llm:
            return "Erro: Modelo de visão não carregado. Adicione um arquivo mmproj na pasta models."
        
        try:
            import base64
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            data_uri = f"data:image/png;base64,{base64_image}"
            
            def run_vision():
                response = self.llm.create_chat_completion(
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that can see and describe images."},
                        {"role": "user", "content": [
                            {"type": "image_url", "image_url": {"url": data_uri}},
                            {"type": "text", "text": prompt}
                        ]}
                    ],
                    chat_handler=self.clip_model
                )
                return response['choices'][0]['message']['content']
            
            return await asyncio.to_thread(run_vision)
        except Exception as e:
            logger.error(f"VLM Error: {e}")
            return f"Falha na análise visual: {e}"

    async def extract_coordinates(self, image_path: str, element_description: str) -> Optional[Tuple[int, int]]:
        """Use VLM to find coordinates (x, y) of an element on screen"""
        prompt = f"Find the precise [x, y] coordinates of the following element: '{element_description}'. Return ONLY the coordinates in the format [x, y] as normalized values between 0 and 1000. If not found, return [0, 0]."
        
        result = await self.process_image(image_path, prompt)
        
        # Regex to extract [x, y]
        match = re.search(r'\[(\d+),\s*(\d+)\]', result)
        if match:
            x_norm = int(match.group(1))
            y_norm = int(match.group(2))
            
            # Map back to screen size (using pyautogui size)
            import pyautogui
            screen_w, screen_h = pyautogui.size()
            
            real_x = int((x_norm / 1000) * screen_w)
            real_y = int((y_norm / 1000) * screen_h)
            
            logger.info(f"LocalAIProcessor: Extracted coordinates {real_x}, {real_y} for '{element_description}'")
            return (real_x, real_y)
            
        return None

    async def _process_via_ollama(self, prompt: str) -> Dict[str, Any]:
        """Inference using Ollama API"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "keep_alive": "10m", # Keep model in memory for 10 minutes
                    "options": {
                        "temperature": 0.5,
                        "num_predict": 80,
                        "num_ctx": 2048,
                        "top_k": 10,
                        "num_thread": os.cpu_count() or 4
                    }
                }

                async with session.post(self.ollama_url, json=payload, timeout=240) as response:
                    if response.status == 200:
                        data = await response.json()
                        response_text = data.get('response', '')
                        return self._parse_local_response(response_text)
                    else:
                        return {'error': f'Ollama status: {response.status}', 'suggested_response': "Erro no servidor Ollama."}
        except asyncio.TimeoutError:
            return {'error': 'Timeout', 'suggested_response': "A resposta do cérebro neural demorou demais."}
        except Exception as e:
            return {'error': str(e), 'suggested_response': "Não consegui conectar ao processador local."}

    def _build_contextual_prompt(self, text: str, context: ConversationContext) -> str:
        """Prompt for local models to ensure robust intent classification and JSON output."""
        short_mem = str(context.long_term_memory)[:150] if context.long_term_memory else "None"
        return f"""You are J.A.R.V.I.S., a smart AI assistant. Classify the user's intent and return ONLY a valid JSON object.

EXAMPLES:
User: "abrir youtube" -> {{"intent_classification": "direct_command", "confidence": 0.98, "suggested_response": "Abrindo YouTube agora.", "parameters": {{"target": "youtube", "action": "abrir"}}}}
User: "que horas são?" -> {{"intent_classification": "time_query", "confidence": 0.99, "suggested_response": "Verificando o horário.", "parameters": {{}}}}
User: "meu PC está lento" -> {{"intent_classification": "indirect_suggestion", "confidence": 0.85, "suggested_response": "Notei que mencionou lentidão. Posso verificar o uso de memória para você.", "parameters": {{"recommended_action": "uso_cpu_ram", "reason": "pc lento"}}}}
User: "está muito barulhento aqui" -> {{"intent_classification": "indirect_suggestion", "confidence": 0.8, "suggested_response": "Posso diminuir o volume para você, senhor.", "parameters": {{"recommended_action": "diminuir_volume", "reason": "barulho"}}}}
User: "o que é inteligência artificial?" -> {{"intent_classification": "conversational_query", "confidence": 0.92, "suggested_response": "IA é a simulação de inteligência humana por máquinas.", "parameters": {{}}}}

MEMORY: {short_mem}
TOPIC: {context.current_topic}

Now classify:
User: "{text}"

JSON (ONLY output the JSON, nothing else):
"""

    def _parse_local_response(self, response_text: str) -> Dict[str, Any]:
        """Parse JSON response, handling potential markdown wrapping"""
        try:
            # Try direct parse
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try extracting from markdown/text
            json_match = re.search(r'(\{.*\})', response_text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except:
                    pass
            
            # Fallback
            logger.warning(f"Failed to parse AI JSON response: {response_text[:100]}...")
            return {
                'suggested_response': response_text, 
                'intent_classification': 'conversational_query', 
                'confidence': 0.8
            }


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
    ai_response: Optional[str] = None
    sentiment: Optional[str] = None
    complexity_score: float = 0.0
    parameters: Dict[str, Any] = None

    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}

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
        
        # Compile regex patterns for performance
        for config in self.entity_patterns.values():
            config['compiled'] = [re.compile(p) for p in config['patterns']]

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
            for pattern in config['compiled']:
                found_matches = pattern.findall(text_lower)
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
        
        self.joy_indicators = ['feliz', 'alegre', 'ótimo', 'incrível', 'uhul', 'eita', 'viva']
        self.anger_indicators = ['raiva', 'ódio', 'droga', 'merda', 'caramba', 'aff', 'maluco']
        self.sadness_indicators = ['triste', 'chateado', 'pena', 'lamento', 'infelizmente', 'puxa']
    
    def analyze_sentiment(self, text: str) -> Tuple[str, float]:
        """Analyze sentiment of text"""
        text_lower = text.lower()
        
        positive_score = sum(1 for word in self.positive_indicators if word in text_lower)
        negative_score = sum(1 for word in self.negative_indicators if word in text_lower)
        neutral_score = sum(1 for word in self.neutral_indicators if word in text_lower)
        
        total_score = positive_score + negative_score + neutral_score
        
        if total_score == 0:
            return 'neutral', 0.5
        
        # Extended scoring
        joy_score = sum(1 for word in self.joy_indicators if word in text_lower)
        anger_score = sum(1 for word in self.anger_indicators if word in text_lower)
        sadness_score = sum(1 for word in self.sadness_indicators if word in text_lower)
        
        scores = {
            'positive': positive_score,
            'negative': negative_score,
            'neutral': neutral_score,
            'joy': joy_score,
            'anger': anger_score,
            'sadness': sadness_score
        }
        
        best_mood = max(scores, key=scores.get)
        confidence = scores[best_mood] / (total_score + 1)
        
        return best_mood, confidence



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
    
    def __init__(self):
        self.entity_extractor = EntityExtractor()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.contextual_analyzer = ContextualIntentAnalyzer()
        
        # Provider selection mapped to Local AI always
        self.local_model = os.getenv("LOCAL_MODEL_NAME", "qwen2:1.5b")
        
        # Initialize selected processor
        self.ai_engine = LocalAIProcessor(self.local_model)
        logger.info(f"NLP initialized with Local AI ({self.local_model})")
        
        # Configuration - High threshold to bypass LLM for simple/direct commands
        self.complexity_threshold = 0.95

        
    async def process_text(self, text: str, base_intent: IntentType, 
                           context: ConversationContext, 
                           mode: ProcessingMode = ProcessingMode.DETAILED,
                           stream_callback=None) -> NLPResult:
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
        
        # Use selected AI Engine for complex queries or when fast mode is off
        ai_response = None
        ai_result = {}
        if (self.ai_engine and 
            (complexity_score > self.complexity_threshold or mode == ProcessingMode.DETAILED)):
            
            ai_result = await self.ai_engine.process_complex_query(text, context, stream_callback)
            ai_response = ai_result.get('suggested_response')
            
            # Override response and intent if engine provides better suggestion
            if ai_response and 'error' not in ai_result:
                response_suggestion = ai_response
                
                # Propagate intent from AI
                ai_intent_str = ai_result.get('intent_classification')
                if ai_intent_str:
                    try:
                        # Ensure it's a valid IntentType member
                        refined_intent = IntentType(ai_intent_str)
                        logger.info(f"NLP: AI refined intent to {refined_intent}")
                    except ValueError:
                        logger.warning(f"NLP: AI returned unknown intent string: {ai_intent_str}")
                
                intent_confidence = max(intent_confidence, ai_result.get('confidence', 0.0))
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
            ai_response=ai_response,
            sentiment=sentiment,
            complexity_score=complexity_score,
            parameters=ai_result.get('parameters', {}) if ai_result else {}
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
        
        elif intent == IntentType.TIME_QUERY:
            return "Verificando o horário atual, senhor."
            
        elif intent == IntentType.DATE_QUERY:
            return "Um momento, vou verificar a data de hoje."
        
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
    
    # Initialize local processor 
    processor = NLPProcessor()
    
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
        if result.ai_response:
            print(f"🤖 Local AI: {result.ai_response[:100]}...")
        print(f"⏱️  Processing Time: {result.processing_time:.3f}s")

if __name__ == "__main__":
    asyncio.run(main())