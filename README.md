# 🤖 Jarvis 2.0

Assistente virtual pessoal avançado 100% offline desenvolvido em Python, inspirado no J.A.R.V.I.S. do universo Marvel. Possui uma interface gráfica futurista via HUD interativo, reconhecimento de voz contínuo e processamento descentralizado e inteligente via IA Local.

![Interface Jarvis 2.0](web/assets/hud_preview.png) *(Exemplo do painel de métricas e status)*

---

## ✨ Principais Funcionalidades

| Funcionalidade | Descrição |
|----------------|-----------|
| 🎤 **Reconhecimento de Voz Offline** | Transcrição ultra-rápida usando modelos Whisper e detecção de wake word via Silero VAD. |
| 🧠 **IA Neural Local** | Processamento de comandos complexos e contexto operando 100% offline via **Ollama** (Modelo otimizado: `qwen2:1.5b`). |
| 🖥️ **Interface HUD Assíncrona** | Janela translúcida, sem bordas, com design futurista operando sobre o PyQt6 e WebEngine. |
| 🔊 **Text-to-Speech Fluido** | Síntese de voz em português estruturada em Threads assíncronas (Thread-safe) para evitar bloqueios de UI. |
| ⚡ **Action Controller Modular** | Execução rápida de comandos usando um sistema de rotas (Registry) e intenções (`IntentType`). |
| 🎵 **Controles e Automação** | Automação de mídia corporativa, navegação web, sistema de arquivos e comandos nativos de OS (Windows otimizado). |

---

## 🏗️ Arquitetura do Sistema

O sistema difere de assistentes tradicionais por rodar serviços pesados localmente sem onerar a interface de usuário.

```text
Jarvis2.0/
├── main.py                      # Ponto de entrada; Inicializa UI HUD e delega as Threads.
├── web/                         # Front-end da interface (HTML/CSS/JS renderizado via QtWebEngine).
├── comandos.py                  # Registry de automações (Abrir sites, mídia, informações do sistema).
├── services/
│   ├── ai_service.py            # Orquestrador da IA Local; gerencia Memória e Aprendizado de máquina.
│   ├── tts_service.py           # Gestor da Fila Falada de respostas.
│   ├── voice_processor_v2.py    # Pipeline acústico avançado usando processamento nativo VAD.
│   ├── optimized_voice_service.py # Lida com Listening-state assíncrono.
│   └── action_controller.py     # Disparador final: Resolve Intenções para chamadas de sistema (Callables).
├── nlp_processor.py             # Formata Prompts e comunica com Ollama/LocalAI API em formato JSON.
├── conversation_manager.py      # Mantém janela de história contextual do usuário e os Enum Types.
└── ...
```

---

## 🎙️ Exemplos de Comandos (Em Português)

O `AIService` classifica as requisições em Intenções para disparo rápido ou passa pela IA Local para processamento semântico complexo.

### Utilitários e Sistema
```text
"Jarvis, que horas são?"               → `TIME_QUERY` (Responde instantaneamente)
"Qual a data de hoje?"                 → `DATE_QUERY` (Responde sem chamar modelo LLM pesado)
"Bloquear a tela."                     → Trava a sessão do Windows
"Uso de memória / Espaço em disco."    → Obtém métricas via `psutil`
```

### Automação (Zero-Shot & Registrados)
```text
"Abrir [Google Chrome / VSCode]."      → Dispara executáveis de sistema ou injeta busca via GUI.
"Fechar [Aplicativo]."                 → Encerra processos no Task Manager silenciosamente.
"Tocar [Nome da Música]."              → Abre o vídeo no YouTube automaticamente.
"Criar timer de 5 minutos."             → Agenda processos background usando Regex e Threads.
"Pesquisar sobre buracos negros."      → Encaminha buscas estruturadas web.
```

### Inteligência Contextual (`CONVERSATIONAL_QUERY`)
Qualquer pergunta complexa é redirecionada silenciosamente para o LLM. A API local retorna uma rota semântica do que fazer ou o que dizer de volta ao usuário.

---

## 📋 Pré-requisitos e Setup

### 1. Requisitos de Sistema
- **Sistema Operacional:** Recomendado Windows 10/11 (Devido aos bindings de Audio/PyCAW otimizados).
- **Processador local AI:** Placa de vídeo adequada ou CPU com boas threads (Recomendado OpenVINO support).
- **Python:** 3.10+
- **Motor Offline (Ollama):** O Ollama deve estar instalado globalmente e rodando o `qwen2:1.5b`.

### 2. Preparando a IA
Baixe o [Ollama](https://ollama.com/) e, no terminal de sua máquina, rode:
```bash
ollama run qwen2:1.5b
```

### 3. Instalação do Projeto
Clone e instale dependências via Virtual Environment (recomendado):
```bash
git clone https://github.com/dclaumanndeveloper/Jarvis2.0.git
cd Jarvis2.0
python -m venv .venv
.venv\Scripts\activate  # No macOS/Linux use: source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Variavéis de Ambiente (.env)
Se for utilizar provedores em nuvem (Fallback fallback), configure seu `.env`. Caso contrário, o sistema focará na porta local `11434` (Ollama).
```env
LOCAL_MODEL_NAME=qwen2:1.5b
# GEMINI_API_KEY=sua_chave (legado, opcional)
```

### 5. Execução
Execute com o interpretador nativo da venv (não utilize terminais bloqueantes):
```bash
python main.py
```

---

## ⚠️ Known Issues e Troubleshooting

- **Crash 0xc0000005 (Access Violation):** O projeto forçou o *import bypass* na `main.py` para injetar pacotes C++ da GPU `openvino_genai` antes das bibliotecas nativas do `PyQt6` para evitar colisão de alocadores de DLL no Windows.
- **Portas e Microfone:** O script necessita usar a porta padrão de gravação `44100Hz`, libere permissões nas Configurações de Privacidade do microfone.
- **Performance TTS:** Para prevenir loops de feedback (eco), a gravação entra automaticamente em estado *Paused* assíncrono via conexão de sinais Qt quando o serviço `TTS` entra na fila de fala.

---

## 🤝 Contribuindo

Ideias empolgantes ou correções? Abra um Pull Request! Modifique ou adicione comandos criando funções em `comandos.py` e marcando-as com:
```python
@registry.register(intents=[IntentType.DIRECT_COMMAND], category=CommandCategory.UTILITY)
def seu_comando():
    return "Resposta falada."
```

## 📄 Licença
Licença MIT. Livre para uso pessoal, inspirar devkits neurais locais privados, mas modifique os reposiórios de origem se realizar um fork produtivo.

<p align="center">
  <b>⭐ Desenvolvido por <a href="https://github.com/dclaumanndeveloper">dclaumanndeveloper</a></b>
</p>
