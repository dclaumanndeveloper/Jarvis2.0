
import logging
import threading
import random
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from conversation_manager import IntentType, CommandCategory

logger = logging.getLogger(__name__)

@dataclass
class CommandMetadata:
    func: Callable
    intents: List[IntentType]
    description: str
    priority: int = 0
    category: CommandCategory = CommandCategory.UTILITY

class CommandRegistry:
    """Modular registry for Jarvis system commands using decorators."""
    def __init__(self):
        self._commands: Dict[IntentType, List[CommandMetadata]] = {}

    def register(self, intents: List[IntentType], category: CommandCategory = CommandCategory.UTILITY, description: str = "", priority: int = 0):
        def decorator(func):
            metadata = CommandMetadata(func, intents, description, priority, category)
            for intent in intents:
                if intent not in self._commands:
                    self._commands[intent] = []
                self._commands[intent].append(metadata)
            # Sort by priority (higher first)
            for intent in intents:
                self._commands[intent].sort(key=lambda x: x.priority, reverse=True)
            return func
        return decorator

    def get_command(self, intent: IntentType, text: str = "") -> Optional[CommandMetadata]:
        cmds = self._commands.get(intent)
        if not cmds: return None
        
        # If it's a direct command, try to find the specific function based on the action verb
        if intent == IntentType.DIRECT_COMMAND and text:
            text_lower = text.lower()
            
            verb_mapping = {
                # More specific verbs FIRST (longer matches win over shorter ones)
                "aumentar": "aumentar_volume",
                "diminuir": "diminuir_volume",
                "abrir": "abrir", "abri": "abrir", "abre": "abrir",
                "fechar": "fechar", "fecha": "fechar",
                "tocar": "tocar", "toca": "tocar",
                "pausar": "pausar", "pausa": "pausar",
                "pesquisar": "pesquisar", "pesquisa": "pesquisar",
                "buscar": "pesquisar", "busca": "pesquisar",
                "procurar": "pesquisar",
                "volume": "definir_volume",
                "desligar": "desligar_computador",
                "reiniciar": "reiniciar_computador",
                "print": "tirar_print", "screenshot": "tirar_print",
                "calcular": "calcular", "calcula": "calcular",
                "timer": "criar_timer",
                "escreva": "escreva", "digite": "escreva",
            }
            
            for verb, func_name in verb_mapping.items():
                # Check for standalone verbs to avoid false positives inside words
                if f" {verb} " in f" {text_lower} ":
                    for cmd in cmds:
                        if cmd.func.__name__ == func_name:
                            return cmd
                            
            # If no mapping matched, see if the raw function name itself is in the text
            for cmd in cmds:
                if cmd.func.__name__.replace("_", " ") in text_lower:
                    return cmd
        
        return cmds[0]

# Global registry instance
registry = CommandRegistry()

class ActionController:
    """
    Dispatcher that bridges NLP results to system actions and voice feedback.
    Handles non-blocking execution and response templating.
    """
    def __init__(self, tts_service=None):
        self.tts = tts_service
        self.response_templates = {
            "success": [
                "Imediatamente, senhor.",
                "Sim, senhor. Protocolos iniciados.",
                "Como desejar. Executando agora.",
                "Com certeza. Já estou providenciando.",
                "Deixe comigo, senhor.",
                "Processado com sucesso."
            ],
            "searching": [
                "Buscando as informações agora.",
                "Um momento enquanto acesso o mainframe.",
                "Pesquisando na rede global.",
                "Acessando bancos de dados.",
                "Iniciando varredura de dados."
            ],
            "error": [
                "Sinto muito, senhor. Encontrei um erro ao processar o comando.",
                "Houve uma falha na execução. Verificando logs.",
                "Não foi possível completar a ação no momento.",
                "Falha crítica na execução, senhor."
            ]
        }

    def execute_nlp_result(self, nlp_result):
        """Dispatches an action based on NLP intent and entities."""
        intent = nlp_result.intent
        entities = nlp_result.entities
        
        logger.info(f"ActionController: Dispatching intent {intent}")
        
        # 1. Handle Proactive Indirect Suggestions
        if intent == IntentType.INDIRECT_SUGGESTION:
            recommended_action = nlp_result.parameters.get("recommended_action") if hasattr(nlp_result, 'parameters') and nlp_result.parameters else None
            
            if recommended_action:
                # Find the specific tool in the registry by function name
                target_cmd_meta = None
                for intent_key, cmds in registry._commands.items():
                    for c in cmds:
                        if c.func.__name__ == recommended_action:
                            target_cmd_meta = c
                            break
                    if target_cmd_meta: break
                
                if target_cmd_meta:
                    if self.tts:
                        mood = nlp_result.sentiment if hasattr(nlp_result, 'sentiment') else 'neutral'
                        self.tts.speak(nlp_result.response_suggestion or "Acredito que precise disso.", mood=mood)
                    
                    thread = threading.Thread(
                        target=self._run_command,
                        args=(target_cmd_meta.func, nlp_result),
                        daemon=True
                    )
                    thread.start()
                    return nlp_result.response_suggestion
                else:
                    logger.warning(f"ActionController: Proactive action not found: {recommended_action}")
        
        # 2. Look for a directly registered command
        cmd_meta = registry.get_command(intent, nlp_result.original_text)
        
        if cmd_meta:
            # 2. Execute in a background thread to prevent UI freezing
            thread = threading.Thread(
                target=self._run_command,
                args=(cmd_meta.func, nlp_result),
                daemon=True
            )
            thread.start()
            
            # 3. Handle Voice Feedback
            response = nlp_result.response_suggestion
            if not response or response == "Comando reconhecido. Executando...":
                response = random.choice(self.response_templates["success"])
            
            if self.tts:
                mood = nlp_result.sentiment if hasattr(nlp_result, 'sentiment') else 'neutral'
                self.tts.speak(response, mood=mood)
            
            return response
        else:
            # No specific command registered, just speak the AI response
            if self.tts:
                mood = nlp_result.sentiment if hasattr(nlp_result, 'sentiment') else 'neutral'
                self.tts.speak(nlp_result.response_suggestion, mood=mood)
            return nlp_result.response_suggestion

    def _run_command(self, func, nlp_result):
        """Internal runner for commands."""
        try:
            logger.info(f"ActionController: Executing {func.__name__}")
            # Map entities to function arguments if necessary, or just pass nlp_result
            # For simplicity, we'll try to pass kwargs based on entities
            
            # Simple entity mapping logic
            kwargs = {}
            kwargs['command'] = nlp_result.original_text

            # Strip action verb from query to avoid searching "pesquisar X" instead of "X"
            import re
            _verb_prefixes = [
                'pesquisar', 'pesquisa', 'buscar', 'busca', 'procurar',
                'tocar', 'toca', 'abrir', 'abri', 'abre', 'calcular', 'calcula',
                'escreva', 'digite'
            ]
            _query_text = nlp_result.original_text
            for vp in sorted(_verb_prefixes, key=len, reverse=True):
                _query_text = re.sub(r'^\s*' + re.escape(vp) + r'\s+', '', _query_text, count=1, flags=re.IGNORECASE)
            kwargs['query'] = _query_text.strip() or nlp_result.original_text
            
            if 'applications' in nlp_result.entities:
                kwargs['target'] = nlp_result.entities['applications']['values'][0]
            if 'numbers' in nlp_result.entities and 'converted' in nlp_result.entities['numbers']:
                kwargs['level'] = nlp_result.entities['numbers']['converted'][0]
            if 'websites' in nlp_result.entities:
                kwargs['target'] = nlp_result.entities['websites']['values'][0]
                 
            # Merge AI Function Calling parameters directly into kwargs
            if hasattr(nlp_result, 'parameters') and isinstance(nlp_result.parameters, dict):
                kwargs.update(nlp_result.parameters)

            import inspect
            sig = inspect.signature(func)
            
            # Filter kwargs to only those the function accepts
            allowed_kwargs = {
                k: v for k, v in kwargs.items() 
                if k in sig.parameters or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
            }

            # Call the function with safe signature
            result = func(**allowed_kwargs)
            logger.info(f"ActionController: Command {func.__name__} returned: {result}")
            
            # If the command returned a specific result text, we might want to say it
            if result and self.tts and "Abrindo" not in result: # Avoid "Abrindo Google" twice if already said
                self.tts.speak(result)
                
        except Exception as e:
            logger.error(f"ActionController: Error in command {func.__name__}: {e}")
            if self.tts:
                self.tts.speak(random.choice(self.response_templates["error"]))
