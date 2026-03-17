"""
test_commands.py - Script de teste para todos os comandos do Jarvis 2.0

Testa o pipeline completo: NLPResult -> ActionController -> Comando
Sem necessidade de áudio, microfone ou UI.

Uso: python test_commands.py
"""

import sys
import os
import time
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from enum import Enum

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configura encoding para Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# ──────────────────────────────────────────────────────────────────────────────
# Mock NLPResult (replica a estrutura usada pelo AIService)
# ──────────────────────────────────────────────────────────────────────────────
from conversation_manager import IntentType, CommandCategory

@dataclass
class MockNLPResult:
    intent: IntentType
    original_text: str
    response_suggestion: str = "Executando comando."
    entities: Dict[str, Any] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.95

# ──────────────────────────────────────────────────────────────────────────────
# Mock TTS (imprime em vez de falar)
# ──────────────────────────────────────────────────────────────────────────────
class MockTTS:
    def speak(self, text: str):
        print(f"  🔊 TTS: {text}")

# ──────────────────────────────────────────────────────────────────────────────
# Inicialização dos módulos Jarvis
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "="*65)
print("  J.A.R.V.I.S. 2.0  —  TESTE DE COMANDOS")
print("="*65)

print("\n[INIT] Carregando registro de comandos...")
import comandos   # registra todos os @registry.register
import skills     # registra skills adicionais

from services.action_controller import ActionController, registry

mock_tts = MockTTS()
controller = ActionController(tts_service=mock_tts)

print(f"[INIT] {sum(len(v) for v in registry._commands.values())} comandos registrados em {len(registry._commands)} intenções.\n")

# ──────────────────────────────────────────────────────────────────────────────
# Utilitário de teste
# ──────────────────────────────────────────────────────────────────────────────
PASS = "✅ PASS"
FAIL = "❌ FAIL"
SKIP = "⏭️  SKIP"
results = []

def run_test(name: str, nlp_result: MockNLPResult, skip: bool = False):
    """Executa um teste e registra o resultado."""
    if skip:
        print(f"\n  {SKIP}  [{name}] (pulado — pode causar efeito colateral real)")
        results.append((name, "SKIP", ""))
        return

    print(f"\n{'─'*55}")
    print(f"  TESTE: {name}")
    print(f"  Texto: '{nlp_result.original_text}'")
    print(f"  Intent: {nlp_result.intent.name}")

    try:
        response = controller.execute_nlp_result(nlp_result)
        time.sleep(0.3)  # aguarda thread de background
        status = PASS if response else FAIL
        results.append((name, "PASS" if response else "FAIL", str(response)))
        print(f"  Resposta: '{response}'")
        print(f"  Status: {status}")
    except Exception as e:
        results.append((name, "FAIL", str(e)))
        print(f"  Status: {FAIL}")
        print(f"  Erro: {e}")

# ──────────────────────────────────────────────────────────────────────────────
# BATERIA DE TESTES
# ──────────────────────────────────────────────────────────────────────────────

# ── Informações de Tempo ──
run_test(
    "Que horas são",
    MockNLPResult(
        intent=IntentType.TIME_QUERY,
        original_text="que horas são agora",
        response_suggestion="Verificando o horário.",
    )
)

run_test(
    "Qual é a data de hoje",
    MockNLPResult(
        intent=IntentType.DATE_QUERY,
        original_text="qual é a data de hoje",
        response_suggestion="Verificando a data.",
    )
)

# ── Sistema ──
run_test(
    "Informações do sistema",
    MockNLPResult(
        intent=IntentType.INFORMATION_QUERY,
        original_text="informações do sistema",
        response_suggestion="Coletando métricas do sistema.",
    )
)

run_test(
    "Uso de memória RAM",
    MockNLPResult(
        intent=IntentType.INFORMATION_QUERY,
        original_text="qual o uso de memória",
        response_suggestion="Verificando memória.",
    )
)

run_test(
    "Uso do processador",
    MockNLPResult(
        intent=IntentType.INFORMATION_QUERY,
        original_text="qual o uso do processador",
        response_suggestion="Verificando CPU.",
    )
)

run_test(
    "Espaço em disco",
    MockNLPResult(
        intent=IntentType.INFORMATION_QUERY,
        original_text="quanto espaço tenho no disco",
        response_suggestion="Verificando disco.",
    )
)

# ── Aplicativos ──
run_test(
    "Abrir Google",
    MockNLPResult(
        intent=IntentType.DIRECT_COMMAND,
        original_text="abrir google",
        response_suggestion="Abrindo Google.",
        entities={"websites": {"values": ["google"]}},
    )
)

run_test(
    "Abrir YouTube",
    MockNLPResult(
        intent=IntentType.DIRECT_COMMAND,
        original_text="abrir youtube",
        response_suggestion="Abrindo YouTube.",
        entities={"websites": {"values": ["youtube"]}},
    )
)

run_test(
    "Abrir GitHub",
    MockNLPResult(
        intent=IntentType.DIRECT_COMMAND,
        original_text="abrir github",
        response_suggestion="Abrindo GitHub.",
        entities={"websites": {"values": ["github"]}},
    )
)

run_test(
    "Abrir Calculadora",
    MockNLPResult(
        intent=IntentType.DIRECT_COMMAND,
        original_text="abrir calculadora",
        response_suggestion="Abrindo calculadora.",
        entities={"applications": {"values": ["calculadora"]}},
    )
)

# ── Captura de Tela ──
run_test(
    "Tirar print",
    MockNLPResult(
        intent=IntentType.DIRECT_COMMAND,
        original_text="tirar print da tela",
        response_suggestion="Capturando tela.",
    )
)

# ── Cálculos ──
run_test(
    "Calcular 15 mais 27",
    MockNLPResult(
        intent=IntentType.DIRECT_COMMAND,
        original_text="calcular 15 mais 27",
        response_suggestion="Calculando.",
        parameters={"expression": "15 + 27"}
    )
)

run_test(
    "Calcular 100 dividido por 4",
    MockNLPResult(
        intent=IntentType.DIRECT_COMMAND,
        original_text="calcular 100 dividido por 4",
        response_suggestion="Calculando.",
        parameters={"expression": "100 / 4"}
    )
)

# ── Timer ──
run_test(
    "Criar timer de 5 segundos",
    MockNLPResult(
        intent=IntentType.DIRECT_COMMAND,
        original_text="criar timer 5 segundos",
        response_suggestion="Criando timer.",
        parameters={"duration": 5, "unit": "segundos"}
    )
)

# ── Volume ──
run_test(
    "Aumentar volume",
    MockNLPResult(
        intent=IntentType.DIRECT_COMMAND,
        original_text="aumentar volume",
        response_suggestion="Aumentando volume.",
    )
)

run_test(
    "Diminuir volume",
    MockNLPResult(
        intent=IntentType.DIRECT_COMMAND,
        original_text="diminuir volume",
        response_suggestion="Diminuindo volume.",
    )
)

run_test(
    "Definir volume para 50%",
    MockNLPResult(
        intent=IntentType.DIRECT_COMMAND,
        original_text="definir volume 50",
        response_suggestion="Definindo volume.",
        parameters={"level": 50}
    )
)

# ── Mídia ──
run_test(
    "Pausar mídia",
    MockNLPResult(
        intent=IntentType.DIRECT_COMMAND,
        original_text="pausar",
        response_suggestion="Pausando.",
    )
)

run_test(
    "Próxima música",
    MockNLPResult(
        intent=IntentType.DIRECT_COMMAND,
        original_text="próxima música",
        response_suggestion="Próxima faixa.",
    )
)

run_test(
    "Música anterior",
    MockNLPResult(
        intent=IntentType.DIRECT_COMMAND,
        original_text="música anterior",
        response_suggestion="Faixa anterior.",
    )
)

run_test(
    "Mutar áudio",
    MockNLPResult(
        intent=IntentType.DIRECT_COMMAND,
        original_text="mutar",
        response_suggestion="Áudio mutado.",
    )
)

# ── Cotações ──
run_test(
    "Cotação do dólar",
    MockNLPResult(
        intent=IntentType.DIRECT_COMMAND,
        original_text="qual a cotação do dólar",
        response_suggestion="Verificando cotação.",
    )
)

run_test(
    "Cotação do Bitcoin",
    MockNLPResult(
        intent=IntentType.DIRECT_COMMAND,
        original_text="qual a cotação do bitcoin",
        response_suggestion="Verificando Bitcoin.",
    )
)

# ── Comandos Perigosos (pulados por segurança) ──
run_test(
    "Desligar computador",
    MockNLPResult(
        intent=IntentType.DIRECT_COMMAND,
        original_text="desligar computador",
        response_suggestion="Desligando.",
    ),
    skip=True
)

run_test(
    "Reiniciar computador",
    MockNLPResult(
        intent=IntentType.DIRECT_COMMAND,
        original_text="reiniciar computador",
        response_suggestion="Reiniciando.",
    ),
    skip=True
)

run_test(
    "Bloquear tela",
    MockNLPResult(
        intent=IntentType.DIRECT_COMMAND,
        original_text="bloquear tela",
        response_suggestion="Bloqueando.",
    ),
    skip=True
)

# Aguarda threads de background
time.sleep(1.0)

# ──────────────────────────────────────────────────────────────────────────────
# RELATÓRIO FINAL
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "="*65)
print("  RELATÓRIO FINAL DE TESTES")
print("="*65)

passed = sum(1 for _, s, _ in results if s == "PASS")
failed = sum(1 for _, s, _ in results if s == "FAIL")
skipped = sum(1 for _, s, _ in results if s == "SKIP")
total = len(results)

print(f"\n  Total: {total} | ✅ Passou: {passed} | ❌ Falhou: {failed} | ⏭️  Pulado: {skipped}")
print()

for name, status, response in results:
    icon = "✅" if status == "PASS" else ("❌" if status == "FAIL" else "⏭️ ")
    print(f"  {icon}  {name}")
    if status == "FAIL" and response:
        print(f"       └─ Erro: {response}")

print()
if failed == 0:
    print("  🎉 Todos os comandos executados com sucesso!")
else:
    print(f"  ⚠️  {failed} comando(s) falharam. Verifique os logs acima.")
print("="*65 + "\n")
