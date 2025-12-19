"""
Command Executor for Jarvis 2.0
Provides a unified interface for executing commands using structured entities.
Replaces the legacy string-based command execution with a more robust system.
"""

import re
import logging
from typing import Dict, Any, Optional, Callable, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class CommandCategory(Enum):
    """Categories of commands"""
    MEDIA = "media"
    SYSTEM = "system"
    APPLICATION = "application"
    UTILITY = "utility"
    INFORMATION = "information"
    FILE = "file"
    AI = "ai"


@dataclass
class CommandResult:
    """Result of a command execution"""
    success: bool
    response: str
    action_taken: Optional[str] = None
    requires_speech: bool = True
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CommandDefinition:
    """Definition of a registered command"""
    keywords: List[str]
    handler: Callable
    category: CommandCategory
    requires_target: bool = False
    target_param: Optional[str] = None
    description: str = ""


class CommandRegistry:
    """Registry for all available commands"""
    
    def __init__(self):
        self._commands: Dict[str, CommandDefinition] = {}
        self._keyword_map: Dict[str, str] = {}  # keyword -> command_id
    
    def register(
        self,
        command_id: str,
        keywords: List[str],
        handler: Callable,
        category: CommandCategory,
        requires_target: bool = False,
        target_param: Optional[str] = None,
        description: str = ""
    ):
        """Register a command handler"""
        self._commands[command_id] = CommandDefinition(
            keywords=keywords,
            handler=handler,
            category=category,
            requires_target=requires_target,
            target_param=target_param,
            description=description
        )
        
        # Map keywords to command_id
        for keyword in keywords:
            self._keyword_map[keyword.lower()] = command_id
        
        logger.debug(f"Registered command: {command_id} with keywords {keywords}")
    
    def find_command(self, text: str, entities: Dict[str, Any] = None) -> Optional[Tuple[CommandDefinition, Dict[str, Any]]]:
        """Find matching command and extract parameters"""
        text_lower = text.lower()
        
        # First try to match by entities if available
        if entities and 'action' in entities:
            action = entities['action']
            if action in self._keyword_map:
                cmd_id = self._keyword_map[action]
                cmd = self._commands[cmd_id]
                params = self._extract_params_from_entities(cmd, entities)
                return (cmd, params)
        
        # Fallback to keyword matching in text
        for keyword, cmd_id in self._keyword_map.items():
            if keyword in text_lower:
                cmd = self._commands[cmd_id]
                params = self._extract_params_from_text(cmd, text_lower, keyword)
                return (cmd, params)
        
        return None
    
    def _extract_params_from_entities(self, cmd: CommandDefinition, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Extract parameters from structured entities"""
        params = {}
        
        if cmd.requires_target and cmd.target_param:
            if 'target' in entities:
                params[cmd.target_param] = entities['target']
            elif 'target_lang' in entities:
                params['target_lang'] = entities['target_lang']
        
        # Copy all relevant entities
        for key in ['level', 'duration', 'unit', 'expression', 'text', 'query']:
            if key in entities:
                params[key] = entities[key]
        
        return params
    
    def _extract_params_from_text(self, cmd: CommandDefinition, text: str, keyword: str) -> Dict[str, Any]:
        """Extract parameters from text (legacy fallback)"""
        params = {}
        
        if cmd.requires_target and cmd.target_param:
            # Extract what comes after the keyword
            parts = text.split(keyword, 1)
            if len(parts) > 1:
                target = parts[1].strip()
                if target:
                    params[cmd.target_param] = target
        
        # Include the full text for legacy commands
        params['_text'] = text
        
        return params
    
    def get_all_commands(self) -> Dict[str, CommandDefinition]:
        """Get all registered commands"""
        return self._commands.copy()
    
    def get_commands_by_category(self, category: CommandCategory) -> List[CommandDefinition]:
        """Get commands by category"""
        return [cmd for cmd in self._commands.values() if cmd.category == category]


class CommandExecutor:
    """
    Main command executor that routes commands to appropriate handlers.
    Uses structured entities when available, falls back to text parsing.
    """
    
    def __init__(self):
        self.registry = CommandRegistry()
        self._register_all_commands()
        logger.info("CommandExecutor initialized with all commands registered")
    
    def _register_all_commands(self):
        """Register all available commands"""
        # Import command functions
        from comandos import (
            # Application commands
            abrir, fechar,
            # Media commands
            tocar, pausar, play, proxima_musica, musica_anterior,
            aumentar_volume, diminuir_volume, definir_volume, mutar, desmutar,
            # Information commands
            horas, data, buscar_temperatura, get_system_info, verificar_internet,
            uso_memoria, uso_cpu, espaco_disco,
            # System commands
            desligar_computador, reiniciar_computador, bloquear_tela, limpar_lixeira,
            tirar_print,
            # Utility commands
            pesquisar, escreva, criar_timer, traduzir,
            cotacao_dolar, cotacao_bitcoin, calcular, contar_piada,
            # File commands
            abrir_pasta, abrir_ultimo_download,
            # Routine commands
            start_day, finish_day,
            # AI commands
            pesquisar_gemini
        )
        
        # ===== APPLICATION COMMANDS =====
        self.registry.register(
            "abrir", ["abrir", "abra", "iniciar", "inicie", "abre"],
            handler=lambda **kw: abrir(target=kw.get('target')) if kw.get('target') else abrir(kw.get('_text', '')),
            category=CommandCategory.APPLICATION,
            requires_target=True,
            target_param="target",
            description="Abre um aplicativo ou site"
        )
        
        self.registry.register(
            "fechar", ["fechar", "feche", "encerrar", "encerre"],
            handler=lambda **kw: fechar(target=kw.get('target')) if kw.get('target') else fechar(kw.get('_text', '')),
            category=CommandCategory.APPLICATION,
            requires_target=True,
            target_param="target",
            description="Fecha um aplicativo"
        )
        
        # ===== MEDIA COMMANDS =====
        self.registry.register(
            "tocar", ["tocar", "toque", "reproduzir", "reproduza"],
            handler=lambda **kw: tocar(song=kw.get('target')) if kw.get('target') else tocar(kw.get('_text', '')),
            category=CommandCategory.MEDIA,
            requires_target=True,
            target_param="target",
            description="Toca uma música no YouTube"
        )
        
        self.registry.register(
            "pausar", ["pausar", "pause", "parar", "pare"],
            handler=lambda **kw: pausar(),
            category=CommandCategory.MEDIA,
            description="Pausa a mídia atual"
        )
        
        self.registry.register(
            "continuar", ["continuar", "continue", "play", "retomar"],
            handler=lambda **kw: play(),
            category=CommandCategory.MEDIA,
            description="Continua a mídia pausada"
        )
        
        self.registry.register(
            "proxima_musica", ["próxima música", "próxima", "pular", "skip"],
            handler=lambda **kw: proxima_musica(),
            category=CommandCategory.MEDIA,
            description="Pula para próxima música"
        )
        
        self.registry.register(
            "musica_anterior", ["música anterior", "anterior", "voltar música"],
            handler=lambda **kw: musica_anterior(),
            category=CommandCategory.MEDIA,
            description="Volta para música anterior"
        )
        
        self.registry.register(
            "aumentar_volume", ["aumentar volume", "aumentar o volume", "mais alto", "volume mais alto"],
            handler=lambda **kw: aumentar_volume(),
            category=CommandCategory.MEDIA,
            description="Aumenta o volume do sistema"
        )
        
        self.registry.register(
            "diminuir_volume", ["diminuir volume", "diminuir o volume", "mais baixo", "volume mais baixo"],
            handler=lambda **kw: diminuir_volume(),
            category=CommandCategory.MEDIA,
            description="Diminui o volume do sistema"
        )
        
        self.registry.register(
            "definir_volume", ["definir volume", "volume em", "volume para", "colocar volume"],
            handler=lambda **kw: definir_volume(level=kw.get('level')) if kw.get('level') else definir_volume(kw.get('_text', '')),
            category=CommandCategory.MEDIA,
            requires_target=True,
            target_param="level",
            description="Define o volume para um valor específico"
        )
        
        self.registry.register(
            "mutar", ["mutar", "mute", "silenciar", "silêncio"],
            handler=lambda **kw: mutar(),
            category=CommandCategory.MEDIA,
            description="Muta o áudio do sistema"
        )
        
        self.registry.register(
            "desmutar", ["desmutar", "unmute", "tirar mudo", "ativar som"],
            handler=lambda **kw: desmutar(),
            category=CommandCategory.MEDIA,
            description="Remove o mudo do áudio"
        )
        
        # ===== INFORMATION COMMANDS =====
        self.registry.register(
            "horas", ["que horas são", "horas", "que horas", "hora atual"],
            handler=lambda **kw: horas(),
            category=CommandCategory.INFORMATION,
            description="Informa as horas atuais"
        )
        
        self.registry.register(
            "data", ["que dia é hoje", "data", "dia de hoje", "qual a data"],
            handler=lambda **kw: data(),
            category=CommandCategory.INFORMATION,
            description="Informa a data atual"
        )
        
        self.registry.register(
            "temperatura", ["temperatura", "clima", "previsão do tempo"],
            handler=lambda **kw: buscar_temperatura(),
            category=CommandCategory.INFORMATION,
            description="Busca a temperatura atual"
        )
        
        self.registry.register(
            "sistema", ["informações do sistema", "info do sistema", "status do sistema", "verificar sistema"],
            handler=lambda **kw: get_system_info(),
            category=CommandCategory.INFORMATION,
            description="Mostra informações do sistema"
        )
        
        self.registry.register(
            "internet", ["verificar internet", "testar internet", "velocidade da internet"],
            handler=lambda **kw: verificar_internet(),
            category=CommandCategory.INFORMATION,
            description="Verifica a velocidade da internet"
        )
        
        self.registry.register(
            "uso_memoria", ["uso de memória", "memória", "ram", "uso da memória"],
            handler=lambda **kw: uso_memoria(),
            category=CommandCategory.INFORMATION,
            description="Mostra uso de memória RAM"
        )
        
        self.registry.register(
            "uso_cpu", ["uso do processador", "uso de cpu", "cpu", "processador"],
            handler=lambda **kw: uso_cpu(),
            category=CommandCategory.INFORMATION,
            description="Mostra uso do processador"
        )
        
        self.registry.register(
            "espaco_disco", ["espaço em disco", "espaço do disco", "disco", "armazenamento"],
            handler=lambda **kw: espaco_disco(),
            category=CommandCategory.INFORMATION,
            description="Mostra espaço em disco"
        )
        
        # ===== SYSTEM COMMANDS =====
        self.registry.register(
            "desligar", ["desligar", "desligar computador", "shutdown"],
            handler=lambda **kw: desligar_computador(),
            category=CommandCategory.SYSTEM,
            description="Desliga o computador"
        )
        
        self.registry.register(
            "reiniciar", ["reiniciar", "reiniciar computador", "restart", "reboot"],
            handler=lambda **kw: reiniciar_computador(),
            category=CommandCategory.SYSTEM,
            description="Reinicia o computador"
        )
        
        self.registry.register(
            "bloquear", ["bloquear tela", "bloquear", "bloquear computador", "lock"],
            handler=lambda **kw: bloquear_tela(),
            category=CommandCategory.SYSTEM,
            description="Bloqueia a tela"
        )
        
        self.registry.register(
            "limpar_lixeira", ["limpar lixeira", "esvaziar lixeira", "lixeira"],
            handler=lambda **kw: limpar_lixeira(),
            category=CommandCategory.SYSTEM,
            description="Esvazia a lixeira"
        )
        
        self.registry.register(
            "tirar_print", ["tirar print", "capturar tela", "screenshot", "print screen"],
            handler=lambda **kw: tirar_print(),
            category=CommandCategory.SYSTEM,
            description="Captura a tela"
        )
        
        # ===== UTILITY COMMANDS =====
        self.registry.register(
            "pesquisar", ["pesquisar", "pesquise", "buscar", "busque", "procurar"],
            handler=lambda **kw: pesquisar(query=kw.get('target')) if kw.get('target') else pesquisar(kw.get('_text', '')),
            category=CommandCategory.UTILITY,
            requires_target=True,
            target_param="target",
            description="Pesquisa no Google"
        )
        
        self.registry.register(
            "escreva", ["escreva", "escrever", "digite", "digitar"],
            handler=lambda **kw: escreva(text=kw.get('target')) if kw.get('target') else escreva(kw.get('_text', '')),
            category=CommandCategory.UTILITY,
            requires_target=True,
            target_param="target",
            description="Digita um texto"
        )
        
        self.registry.register(
            "criar_timer", ["criar timer", "timer", "temporizador", "alarme"],
            handler=lambda **kw: criar_timer(duration=kw.get('duration'), unit=kw.get('unit')) if kw.get('duration') else criar_timer(kw.get('_text', '')),
            category=CommandCategory.UTILITY,
            requires_target=True,
            target_param="duration",
            description="Cria um timer"
        )
        
        self.registry.register(
            "traduzir", ["traduzir", "traduza", "tradução"],
            handler=lambda **kw: traduzir(text=kw.get('target'), target_lang=kw.get('target_lang')) if kw.get('target') else traduzir(kw.get('_text', '')),
            category=CommandCategory.UTILITY,
            requires_target=True,
            target_param="target",
            description="Traduz texto"
        )
        
        self.registry.register(
            "cotacao_dolar", ["cotação do dólar", "dólar", "preço do dólar", "valor do dólar"],
            handler=lambda **kw: cotacao_dolar(),
            category=CommandCategory.UTILITY,
            description="Mostra cotação do dólar"
        )
        
        self.registry.register(
            "cotacao_bitcoin", ["cotação do bitcoin", "bitcoin", "preço do bitcoin", "btc"],
            handler=lambda **kw: cotacao_bitcoin(),
            category=CommandCategory.UTILITY,
            description="Mostra cotação do Bitcoin"
        )
        
        self.registry.register(
            "calcular", ["calcular", "calcule", "quanto é", "qual o resultado"],
            handler=lambda **kw: calcular(expression=kw.get('target')) if kw.get('target') else calcular(kw.get('_text', '')),
            category=CommandCategory.UTILITY,
            requires_target=True,
            target_param="target",
            description="Calcula uma expressão"
        )
        
        self.registry.register(
            "contar_piada", ["contar piada", "piada", "conte uma piada", "me faça rir"],
            handler=lambda **kw: contar_piada(),
            category=CommandCategory.UTILITY,
            description="Conta uma piada"
        )
        
        # ===== FILE COMMANDS =====
        self.registry.register(
            "abrir_pasta", ["abrir pasta", "abrir a pasta", "mostrar pasta"],
            handler=lambda **kw: abrir_pasta(folder=kw.get('target')) if kw.get('target') else abrir_pasta(kw.get('_text', '')),
            category=CommandCategory.FILE,
            requires_target=True,
            target_param="target",
            description="Abre uma pasta do usuário"
        )
        
        self.registry.register(
            "abrir_ultimo_download", ["último download", "abrir último download", "download recente"],
            handler=lambda **kw: abrir_ultimo_download(),
            category=CommandCategory.FILE,
            description="Abre o último arquivo baixado"
        )
        
        # ===== ROUTINE COMMANDS =====
        self.registry.register(
            "start_day", ["iniciar dia", "começar dia", "rotina matinal", "bom dia"],
            handler=lambda **kw: start_day(),
            category=CommandCategory.SYSTEM,
            description="Inicia rotina do dia"
        )
        
        self.registry.register(
            "finish_day", ["finalizar dia", "terminar dia", "fim do dia", "encerrar dia"],
            handler=lambda **kw: finish_day(),
            category=CommandCategory.SYSTEM,
            description="Finaliza rotina do dia"
        )
        
        # ===== AI COMMANDS =====
        self.registry.register(
            "gemini", ["gemini", "perguntar", "pergunta ao gemini"],
            handler=lambda **kw: pesquisar_gemini(kw.get('target', kw.get('_text', ''))),
            category=CommandCategory.AI,
            requires_target=True,
            target_param="target",
            description="Pergunta ao Gemini AI"
        )
    
    def execute(self, entities: Dict[str, Any], text: str) -> CommandResult:
        """
        Execute a command based on entities or text.
        
        Args:
            entities: Structured entities extracted by NLP
            text: Original text command (fallback)
        
        Returns:
            CommandResult with success status and response
        """
        try:
            logger.info(f"CommandExecutor: Executing with entities={entities}, text='{text}'")
            
            # Find matching command
            result = self.registry.find_command(text, entities)
            
            if result:
                cmd, params = result
                logger.info(f"CommandExecutor: Found command handler, executing with params={params}")
                
                # Execute the handler
                response = cmd.handler(**params)
                
                if response:
                    return CommandResult(
                        success=True,
                        response=response,
                        action_taken=cmd.description
                    )
                else:
                    return CommandResult(
                        success=True,
                        response="Comando executado.",
                        action_taken=cmd.description
                    )
            
            # No command found - return None to indicate fallback to AI
            logger.info("CommandExecutor: No matching command found, falling back to AI")
            return CommandResult(
                success=False,
                response="",
                action_taken=None
            )
            
        except Exception as e:
            logger.error(f"CommandExecutor: Error executing command: {e}")
            return CommandResult(
                success=False,
                response=f"Erro ao executar comando: {e}",
                action_taken=None
            )
    
    def get_available_commands(self) -> List[str]:
        """Get list of available command descriptions"""
        commands = self.registry.get_all_commands()
        return [f"{cmd_id}: {cmd.description}" for cmd_id, cmd in commands.items()]
