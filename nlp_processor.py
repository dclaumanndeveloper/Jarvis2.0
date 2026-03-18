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

                # Check if model file is valid (not empty placeholder)
                file_size = os.path.getsize(model_path)
                if file_size < 1024 * 1024:  # Less than 1MB = placeholder file
                    logger.warning(f"LocalAIProcessor: Model file {gguf_files[0]} is too small ({file_size} bytes). Likely a placeholder. Skipping llama-cpp.")
                    self.use_llama_cpp = False
                    self.llm = None
                    return

                logger.info(f"LocalAIProcessor: Loading standalone model {model_path} ({file_size/1024/1024:.1f}MB)...")

                # Create the model with safe defaults and error handling
                self.llm = Llama(
                    model_path=model_path,
                    n_ctx=2048,
                    n_threads=min(os.cpu_count() or 4, 8),  # Limit threads
                    verbose=False,
                    seed=-1,
                    n_batch=512,
                    use_mlock=False,
                    use_mmap=True,
                    low_vram=False
                )

                self.use_llama_cpp = True
                logger.info(f"LocalAIProcessor: Successfully loaded model.")

                # Test the model with a simple call
                try:
                    test_response = self.llm("Test", max_tokens=1, temperature=0.1)
                    if test_response and 'choices' in test_response:
                        logger.info(f"LocalAIProcessor: Model test successful.")
                    else:
                        logger.warning(f"LocalAIProcessor: Model test returned unexpected format: {type(test_response)}")
                except Exception as test_e:
                    logger.warning(f"LocalAIProcessor: Model test failed: {test_e}")
                    # Don't fail initialization just because test failed

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
                logger.error(f"LocalAIProcessor: Failed to load Llama-cpp model. Error: {e}")
                if "cannot open file" in str(e) or "Failed to load model" in str(e):
                    logger.info("LocalAIProcessor: Model file may be corrupted or incomplete. Download a proper GGUF model to enable local LLM.")
                self.use_llama_cpp = False
                self.llm = None
        else:
            logger.info("LocalAIProcessor: No .gguf model found in models/. Place a GGUF model file in the models/ directory to enable local LLM.")
            logger.info("LocalAIProcessor: Using intelligent fallback system for conversational queries.")

    async def process_complex_query(self, text: str, context: ConversationContext, stream_callback=None) -> Dict[str, Any]:
        """Process query using local Llama-cpp instance or intelligent fallback"""
        if self.use_llama_cpp and self.llm:
            # Use standalone llama-cpp
            try:
                return await self._process_via_llama_cpp(text, context, stream_callback)
            except Exception as e:
                logger.warning(f"LocalAIProcessor: Llama-cpp failed, using intelligent fallback: {e}")

        # Intelligent fallback - provide smart responses without LLM
        return await self._intelligent_fallback_response(text, context, stream_callback)

    async def _intelligent_fallback_response(self, text: str, context: ConversationContext, stream_callback=None) -> Dict[str, Any]:
        """Generate intelligent responses without requiring LLM"""
        text_lower = text.lower().strip()

        # Knowledge base for common questions
        knowledge_responses = {
            # AI and Technology
            'inteligência artificial': "A Inteligência Artificial é a simulação de processos de inteligência humana por máquinas, especialmente sistemas de computador. Inclui aprendizado, raciocínio e autocorreção.",
            'ia': "IA refere-se à Inteligência Artificial, que permite que máquinas realizem tarefas que normalmente requerem inteligência humana.",
            'machine learning': "Machine Learning é um subconjunto da IA onde algoritmos aprendem padrões nos dados para fazer previsões ou decisões sem serem explicitamente programados.",
            'chatbot': "Um chatbot é um programa de computador projetado para simular conversas com usuários humanos, especialmente pela internet.",

            # Science and General Knowledge
            'computador': "Um computador é uma máquina eletrônica que processa dados através de instruções programadas, realizando cálculos e executando tarefas automaticamente.",
            'internet': "A Internet é uma rede global de computadores interconectados que permite comunicação e compartilhamento de informações em todo o mundo.",
            'programação': "Programação é o processo de criar instruções para computadores executarem através de código, usando linguagens como Python, JavaScript, Java, etc.",

            # Time and Date
            'hora': "hora atual",
            'horas': "horário atual",
            'tempo': "informações temporais",
            'data': "data atual",

            # Jarvis-specific
            'jarvis': "Sou J.A.R.V.I.S., seu assistente de IA pessoal. Estou aqui para ajudar com tarefas, responder perguntas e controlar sistemas.",
            'você': "Sou um assistente de inteligência artificial projetado para ajudar com diversas tarefas e responder suas perguntas.",
        }

        # Find matching knowledge
        for keyword, response in knowledge_responses.items():
            if keyword in text_lower:
                # Special handling for time/date queries
                if response in ["hora atual", "horário atual", "informações temporais"]:
                    import datetime
                    now = datetime.datetime.now()
                    response = f"São {now.strftime('%H:%M:%S')} de {now.strftime('%d de %B de %Y')}."
                elif response == "data atual":
                    import datetime
                    now = datetime.datetime.now()
                    response = f"Hoje é {now.strftime('%d de %B de %Y')}, {now.strftime('%A')}."

                # Stream response if callback provided
                if stream_callback:
                    stream_callback("JARVIS: ")
                    for char in response:
                        stream_callback(char)
                        await asyncio.sleep(0.01)  # Simulate typing

                return {
                    'intent_classification': 'conversational_query',
                    'confidence': 0.85,
                    'suggested_response': response,
                    'parameters': {'knowledge_match': keyword}
                }

        # Question pattern analysis
        question_patterns = [
            (r'o que (?:é|são) (.+)', "buscarei informações sobre %s para você."),
            (r'como (.+)', "Para %s, você pode pesquisar tutoriais específicos ou consultar a documentação relevante."),
            (r'quando (.+)', "Para informações sobre quando %s, recomendo verificar fontes atualizadas."),
            (r'onde (.+)', "Para localizar %s, sugiro usar serviços de busca ou mapas."),
            (r'por que (.+)', "A razão para %s pode ter múltiplas explicações. Posso ajudá-lo a pesquisar mais detalhes."),
            (r'qual (.+)', "Sobre %s, posso ajudá-lo a encontrar informações mais específicas."),
        ]

        import re
        for pattern, template in question_patterns:
            match = re.search(pattern, text_lower)
            if match:
                subject = match.group(1)
                response = template % subject

                if stream_callback:
                    stream_callback("JARVIS: ")
                    for char in response:
                        stream_callback(char)
                        await asyncio.sleep(0.01)

                return {
                    'intent_classification': 'conversational_query',
                    'confidence': 0.75,
                    'suggested_response': response,
                    'parameters': {'pattern_match': pattern}
                }

        # Generic conversational response
        generic_responses = [
            f"Interessante pergunta sobre {text}. Embora eu não tenha uma resposta específica agora, posso ajudá-lo a pesquisar mais informações.",
            f"Sobre {text}, sugiro que consultemos fontes especializadas para uma resposta mais detalhada.",
            f"Sua pergunta sobre {text} é relevante. Você gostaria que eu ajude a pesquisar informações específicas sobre isso?",
        ]

        import random
        response = random.choice(generic_responses)

        if stream_callback:
            stream_callback("JARVIS: ")
            for char in response:
                stream_callback(char)
                await asyncio.sleep(0.01)

        return {
            'intent_classification': 'conversational_query',
            'confidence': 0.6,
            'suggested_response': response,
            'parameters': {'fallback': True}
        }

    def _get_base_system_prompt(self) -> str:
        """Fixed system prompt for token reuse"""
        return "You are J.A.R.V.I.S., a smart AI assistant. Classify the user's intent and return ONLY a valid JSON object."

    async def _process_via_llama_cpp(self, text: str, context: ConversationContext, stream_callback=None) -> Dict[str, Any]:
        """Inference using llama-cpp-python with simple, compatible API calls"""
        try:
            short_mem = str(context.long_term_memory)[:150] if context.long_term_memory else "None"
            # Build a simple, focused prompt
            full_prompt = f"""You are J.A.R.V.I.S., a smart AI assistant. Classify the user's intent and return ONLY a valid JSON object.

EXAMPLES:
User: "o que é inteligência artificial?" -> {{"intent_classification": "conversational_query", "confidence": 0.92, "suggested_response": "IA é a simulação de inteligência humana por máquinas.", "parameters": {{}}}}
User: "abrir youtube" -> {{"intent_classification": "direct_command", "confidence": 0.98, "suggested_response": "Abrindo YouTube agora.", "parameters": {{"target": "youtube", "action": "abrir"}}}}

MEMORY: {short_mem}
TOPIC: {context.current_topic}

User: "{text}"
JSON:"""

            full_text = ""

            def run_inference():
                nonlocal full_text
                try:
                    # Use the simple callable interface (most compatible)
                    if stream_callback:
                        # Simple streaming
                        response = self.llm(
                            full_prompt,
                            max_tokens=150,
                            temperature=0.3,
                            stop=["User:", "\n\n", "JSON:"],
                            stream=True
                        )
                        for chunk in response:
                            if 'choices' in chunk and chunk['choices']:
                                token = chunk['choices'][0].get('text', '')
                                if token:
                                    full_text += token
                                    if stream_callback:
                                        stream_callback(token)
                    else:
                        # Simple non-streaming
                        response = self.llm(
                            full_prompt,
                            max_tokens=150,
                            temperature=0.3,
                            stop=["User:", "\n\n", "JSON:"],
                            echo=False
                        )
                        if 'choices' in response and response['choices']:
                            full_text = response['choices'][0].get('text', '').strip()

                except Exception as inner_e:
                    logger.error(f"Llama-cpp inference error: {inner_e}", exc_info=True)
                    # Fallback response
                    full_text = f'{{"intent_classification": "conversational_query", "confidence": 0.8, "suggested_response": "Entendo que você quer saber sobre {text}.", "parameters": {{}}}}'

            await asyncio.to_thread(run_inference)

            if not full_text:
                logger.warning("Llama-cpp returned empty response")
                return {'intent_classification': 'conversational_query', 'confidence': 0.8, 'suggested_response': f"Entendo que você quer saber sobre {text}.", 'parameters': {}}

            return self._parse_local_response(full_text)
        except Exception as e:
            logger.error(f"Llama-cpp error: {e}", exc_info=True)
            # Return a valid fallback response
            return {'intent_classification': 'conversational_query', 'confidence': 0.8, 'suggested_response': f"Entendo que você quer saber sobre {text}.", 'parameters': {}}

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
                try:
                    # Use simple llama-cpp API without chat format for compatibility
                    response = self.llm(
                        f"<image>{data_uri}</image>\n{prompt}",
                        max_tokens=200,
                        temperature=0.3,
                        stop=["\n\n"]
                    )
                    if 'choices' in response and response['choices']:
                        return response['choices'][0].get('text', 'Não foi possível analisar a imagem.').strip()
                    else:
                        return 'Não foi possível analisar a imagem.'
                except Exception as e:
                    logger.error(f"Vision inference error: {e}")
                    return f'Erro na análise: {e}'

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
        """Parse JSON response, handling potential markdown wrapping and errors"""
        if not response_text.strip():
            logger.warning("Empty response from LLM")
            return {
                'intent_classification': 'conversational_query',
                'confidence': 0.7,
                'suggested_response': "Não consegui processar sua solicitação.",
                'parameters': {}
            }

        try:
            # Try direct parse first
            cleaned = response_text.strip()
            if cleaned.startswith('```json'):
                cleaned = cleaned.replace('```json', '').replace('```', '').strip()
            if cleaned.startswith('```'):
                cleaned = cleaned.replace('```', '').strip()

            parsed = json.loads(cleaned)

            # Validate required fields
            if 'intent_classification' not in parsed:
                parsed['intent_classification'] = 'conversational_query'
            if 'confidence' not in parsed:
                parsed['confidence'] = 0.8
            if 'suggested_response' not in parsed:
                parsed['suggested_response'] = "Processado com sucesso."
            if 'parameters' not in parsed:
                parsed['parameters'] = {}

            return parsed

        except json.JSONDecodeError:
            # Try extracting JSON from text
            patterns = [
                r'\{.*?\}',  # Basic JSON pattern
                r'\{[^}]*\}',  # Simple JSON pattern
                r'(\{(?:[^{}]|(?1))*\})'  # Nested JSON pattern
            ]

            for pattern in patterns:
                matches = re.findall(pattern, response_text, re.DOTALL)
                for match in matches:
                    try:
                        parsed = json.loads(match)
                        # Validate and add missing fields
                        if 'intent_classification' not in parsed:
                            parsed['intent_classification'] = 'conversational_query'
                        if 'confidence' not in parsed:
                            parsed['confidence'] = 0.8
                        if 'suggested_response' not in parsed:
                            # If we have the raw text, use it as suggested response
                            non_json_text = response_text.replace(match, '').strip()
                            if non_json_text and len(non_json_text) > 10:
                                parsed['suggested_response'] = non_json_text[:200]
                            else:
                                parsed['suggested_response'] = "Informação processada."
                        if 'parameters' not in parsed:
                            parsed['parameters'] = {}
                        return parsed
                    except:
                        continue

            # Fallback: treat the entire response as the suggested_response
            logger.warning(f"Failed to parse LLM JSON, using raw text: {response_text[:100]}...")
            return {
                'intent_classification': 'conversational_query',
                'confidence': 0.8,
                'suggested_response': response_text[:500],  # Limit response length
                'parameters': {}
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

        # Test if the AI engine is working
        if hasattr(self.ai_engine, 'use_llama_cpp') and self.ai_engine.use_llama_cpp:
            logger.info(f"NLP initialized with Local AI llama-cpp ({self.local_model}) - ACTIVE")
        else:
            logger.info(f"NLP initialized with intelligent fallback system - LLM unavailable but conversational queries supported")

        logger.info(f"NLP processor ready for all query types")
        
        # Configuration - Threshold to use LLM for complex/conversational queries
        self.complexity_threshold = 0.6

        
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
        
        # Use AI Engine for conversational queries and when it's available
        ai_response = None
        ai_result = {}
        should_use_ai = (
            complexity_score > self.complexity_threshold or
            mode == ProcessingMode.DETAILED or
            refined_intent == IntentType.CONVERSATIONAL_QUERY or  # Always use AI for conversations
            refined_intent == IntentType.TIME_QUERY or
            refined_intent == IntentType.DATE_QUERY or
            refined_intent == IntentType.CLARIFICATION_REQUEST or
            refined_intent == IntentType.EMOTIONAL_EXPRESSION
        )

        if should_use_ai:
            engine_type = "llama-cpp" if (hasattr(self.ai_engine, 'use_llama_cpp') and self.ai_engine.use_llama_cpp) else "intelligent fallback"
            logger.info(f"NLP: Using AI engine ({engine_type}) for query (intent: {refined_intent}, complexity: {complexity_score:.2f})")

            # Emit initial message for conversational queries
            if refined_intent == IntentType.CONVERSATIONAL_QUERY and stream_callback:
                stream_callback("JARVIS: ")

            ai_result = await self.ai_engine.process_complex_query(text, context, stream_callback)
            ai_response = ai_result.get('suggested_response')

            logger.info(f"NLP: AI engine returned: {ai_result.get('suggested_response', 'No response')[:100]}...")

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
        else:
            logger.info(f"NLP: Using rule-based response (intent: {refined_intent}, complexity: {complexity_score:.2f})")
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