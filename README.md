# Jarvis 2.0

Assistente virtual pessoal avançado 100% offline desenvolvido em Python, inspirado no J.A.R.V.I.S. do universo Marvel. Possui interface gráfica futurista via HUD interativo, reconhecimento de voz contínuo e processamento descentralizado via IA local.

---

## Principais Funcionalidades

| Funcionalidade | Descrição |
|----------------|-----------|
| **Reconhecimento de Voz Offline** | Transcrição usando Vosk (PT-BR) + Silero VAD (ONNX) para detecção de atividade de voz. Suporte opcional a Whisper via Intel OpenVINO. |
| **IA Neural Local** | Inferência 100% offline via `llama-cpp-python` (modelos GGUF) ou Ollama REST API. Fallback opcional para Gemini API (cloud). |
| **Interface HUD** | Janela translúcida sem bordas renderizada com PyQt6 + QtWebEngine. Front-end em HTML/CSS/JS com Three.js e GSAP. |
| **Text-to-Speech** | Síntese de voz em português com fila thread-safe. Pausa automática do microfone enquanto fala (anti-eco). |
| **Action Controller Modular** | Sistema de roteamento por intenções (`IntentType`) com registro via decorator. Resolução de comandos sem chamar o LLM. |
| **Memória Persistente** | Banco vetorial com histórico de conversas e contexto de longo prazo entre sessões. |
| **Agente Web** | Pesquisa autônoma em tempo real com scraping e síntese de resultados. |
| **Visão Computacional** | Análise de tela e imagens via modelo VLM (LLaVA + mmproj GGUF). Monitoramento visual proativo. |
| **Agente de Código** | Geração e análise de código com contexto de projeto. |
| **Automação de Workflow** | Gravação e reprodução de macros de sistema. |
| **Integração Telegram** | Controle remoto do assistente via bot do Telegram. |
| **Motor de Aprendizado** | Reconhecimento de padrões com SQLite assíncrono; adapta respostas ao longo do tempo. |
| **Skills e Automação** | Controle de mídia, sistema de arquivos, navegação web, timers e comandos de OS (otimizado para Windows). |

---

## Arquitetura do Sistema

```
Jarvis2.0/
├── main.py                          # Ponto de entrada; cria JarvisHUD (PyQt6) e delega QThreads
├── comandos.py                      # Registry de automações (mídia, web, sistema, timers)
├── conversation_manager.py          # IntentType enums, ConversationContext e histórico
├── nlp_processor.py                 # Auto-detecção de modelos GGUF, llama-cpp e Ollama API
├── learning_engine.py               # Módulo de aprendizado com SQLite async
├── database_manager.py              # Utilitários de persistência de dados
├── enhanced_speech.py               # Aprimoramentos de síntese de voz
├── enhanced_voice_recording.py      # Captura de áudio avançada
├── error_recovery.py                # Tolerância a falhas
├── requirements.txt
│
├── services/
│   ├── ai_service.py                # Orquestrador central da IA (QThread)
│   ├── action_controller.py         # Dispara Intenções para callables Python
│   ├── tts_service.py               # Fila de TTS com sinais Qt (speaking_started/finished)
│   ├── voice_processor_v2.py        # Pipeline STT: Vosk + Silero VAD + Whisper OpenVINO
│   ├── optimized_voice_service.py   # Gerenciamento de estado de escuta assíncrono
│   ├── memory_service.py            # Memória persistente e contexto de longo prazo
│   ├── web_agent_service.py         # Agente de pesquisa web com scraping
│   ├── vision_service.py            # Análise de tela/imagem via VLM
│   ├── vision_monitor_service.py    # Monitoramento visual proativo
│   ├── coding_agent_service.py      # Agente de geração e análise de código
│   ├── health_monitor_service.py    # Monitoramento de saúde do sistema
│   ├── workflow_service.py          # Gravação e execução de macros/workflows
│   ├── update_service.py            # Serviço de auto-atualização
│   ├── indexer_service.py           # Indexador de documentos (brain indexer)
│   ├── telegram_service.py          # Integração com bot do Telegram
│   ├── hud_service.py               # HUD holográfico secundário
│   ├── audio_service.py             # Abstração de I/O de áudio
│   ├── audio_device_monitor.py      # Detecção de mudanças de dispositivo de áudio
│   └── path_manager.py              # Resolução de caminhos
│
├── skills/
│   ├── media_skills.py              # Comandos de controle de mídia
│   └── system_skills.py             # Comandos de sistema
│
├── web/
│   ├── index.html                   # Layout do HUD (Three.js + GSAP)
│   ├── style.css                    # Estilização cyberpunk
│   └── hud.js                       # Lógica do HUD, métricas, animações, streaming de tokens
│
├── tests/
│   ├── test_ai_service.py
│   ├── test_audio_service.py
│   ├── test_comandos.py
│   ├── test_conversation_manager.py
│   ├── test_learning_engine.py
│   ├── test_nlp_processor.py
│   └── test_tts_service.py
│
└── models/
    ├── qwen2-0_5b-instruct-q4_k_m.gguf      # LLM local quantizado (llama-cpp)
    ├── mmproj-Qwen2-VL-7B-Instruct-f32.gguf # Projetor de visão (VLM / LLaVA)
    ├── silero_vad.onnx                        # Modelo de detecção de atividade de voz
    ├── vosk-model-small-pt-0.3/              # Modelo STT Vosk (Português)
    ├── whisper_small_ov/                     # Modelo Whisper via Intel OpenVINO
    ├── embedding_model/                      # Modelo de embeddings (brain indexer)
    └── piper_voices/                         # Vozes TTS (Piper)
```

---

## Fluxo de Processamento

```
Microfone → VoiceProcessorV2 (Vosk + VAD)
         → OptimizedVoiceService (estado de escuta)
         → AIService (orquestrador)
              ├── IntentType de alta prioridade → ActionController → comandos.py / skills/
              ├── CONVERSATIONAL_QUERY → NLPProcessor → llama-cpp / Ollama / Gemini
              ├── VISION_QUERY → VisionService (VLM)
              ├── AGENT_RESEARCH_QUERY → WebAgentService
              └── Resultado → TTSService → HUD (via QWebChannel)
```

---

## Exemplos de Comandos (Português)

### Sistema e Utilitários
```
"Que horas são?"              → TIME_QUERY  (resposta instantânea)
"Qual a data de hoje?"        → DATE_QUERY
"Uso de memória / CPU"        → métricas via psutil
"Bloquear a tela"             → trava a sessão do Windows
"Verificar saúde do sistema"  → HealthMonitorService
```

### Automação
```
"Abrir Chrome / VSCode"       → abre executáveis ou injeta busca via PyAutoGUI
"Fechar [aplicativo]"         → encerra processos silenciosamente
"Tocar [nome da música]"      → abre vídeo no YouTube
"Criar timer de 5 minutos"    → agenda processo em background
"Copiar para área de transferência" → pyperclip
```

### Pesquisa e Web
```
"Pesquisar sobre [tema]"      → WebAgentService (scraping + síntese)
"Resumir esta página"         → agente web com contexto
```

### Visão e Tela
```
"O que está na tela?"         → VisionService (análise via VLM)
"Descreva esta imagem"        → VisionService
```

### Código
```
"Analise este código"         → CodingAgentService
"Gere uma função para [X]"    → CodingAgentService
```

### Conversa Contextual
Qualquer pergunta complexa é roteada para o LLM local automaticamente (`CONVERSATIONAL_QUERY`). O histórico de conversa é mantido pelo `ConversationContext`.

---

## Pré-requisitos e Setup

### 1. Requisitos de Sistema

- **OS:** Windows 10/11 (pycaw e bindings de áudio otimizados para Windows)
- **Python:** 3.10 ou superior (testado até 3.14)
- **RAM:** 8 GB mínimo (16 GB recomendado para VLM)
- **GPU/CPU:** Suporte a OpenVINO recomendado para aceleração de Whisper

### 2. Motor de IA Local

**Opção A — Ollama (mais simples):**
```bash
# Instale o Ollama: https://ollama.com/
ollama run qwen2:1.5b
```

**Opção B — GGUF local via llama-cpp (offline total):**
Coloque o arquivo `.gguf` na pasta `models/`. O `NLPProcessor` detecta automaticamente.

### 3. Instalação do Projeto

```bash
git clone https://github.com/dclaumanndeveloper/Jarvis2.0.git
cd Jarvis2.0
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

> **Nota (Python 3.14+):** Instale o PyAudio separadamente antes:
> ```bash
> pip install pipwin
> pipwin install pyaudio
> ```

### 4. Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto:
```env
LOCAL_MODEL_NAME=qwen2:1.5b

# Fallback cloud (opcional)
# GEMINI_API_KEY=sua_chave_aqui
```

### 5. Modelos de Voz (STT)

Baixe o modelo Vosk para Português e extraia em `models/vosk-model-small-pt-0.3/`:
- [vosk-model-small-pt-0.3](https://alphacephei.com/vosk/models)

### 6. Execução

```bash
python main.py
```

---

## Adicionando Comandos (Skills)

Registre novas funções em `comandos.py` ou crie um arquivo em `skills/`:

```python
from services.action_controller import registry
from conversation_manager import IntentType, CommandCategory

@registry.register(intents=[IntentType.DIRECT_COMMAND], category=CommandCategory.UTILITY)
def meu_comando() -> str:
    return "Resposta falada pelo Jarvis."
```

---

## Testes

```bash
python -m pytest tests/
```

Os testes cobrem: `AIService`, `AudioService`, `Comandos`, `ConversationManager`, `LearningEngine`, `NLPProcessor` e `TTSService`.

---

## Known Issues e Troubleshooting

| Problema | Solução |
|----------|---------|
| **Crash 0xc0000005 (Access Violation)** | O `main.py` importa `openvino_genai` antes do PyQt6 para evitar colisão de alocadores de DLL no Windows. Não altere a ordem de imports. |
| **Microfone não reconhecido** | Verifique permissões em Configurações > Privacidade > Microfone. O pipeline usa `44100 Hz` por padrão. |
| **Eco / feedback de voz** | O `TTSService` emite `speaking_started`/`speaking_finished` para pausar o microfone automaticamente. |
| **Ollama não responde** | Certifique-se de que o serviço Ollama está rodando: `ollama serve` e o modelo foi baixado: `ollama pull qwen2:1.5b`. |
| **Modelo GGUF não carregado** | Verifique se o arquivo `.gguf` está em `models/` e se `llama-cpp-python` está instalado corretamente para sua plataforma. |

---

## Contribuindo

Pull Requests são bem-vindos! Para contribuir:

1. Faça um fork do repositório
2. Crie uma branch: `git checkout -b feat/minha-feature`
3. Adicione seu código seguindo os padrões existentes
4. Execute os testes: `python -m pytest tests/`
5. Abra um Pull Request

---

## Licença

MIT — Livre para uso pessoal e projetos derivados. Se realizar um fork produtivo, mantenha a referência ao repositório original.

---

<p align="center">
  Desenvolvido por <a href="https://github.com/dclaumanndeveloper">dclaumanndeveloper</a>
</p>
