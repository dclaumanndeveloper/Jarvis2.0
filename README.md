# 🤖 Jarvis 2.0

Assistente virtual pessoal desenvolvido em Python, inspirado no Jarvis do Homem de Ferro. Interface gráfica futurista com comandos de voz em português e integração com **Gemini AI**.

![Interface Jarvis 2.0](interface_bg.webp)

---

## ✨ Principais Funcionalidades

| Funcionalidade | Descrição |
|----------------|-----------|
| 🎤 **Comandos de voz** | Reconhecimento de voz em português brasileiro |
| 🖥️ **Interface HUD** | UI futurista estilo Iron Man com PyQt6 |
| 🤖 **IA Integrada** | Processamento de linguagem natural com Gemini 2.0 Flash |
| 🔊 **Text-to-Speech** | Respostas faladas com voz sintetizada |
| 📚 **Aprendizado** | Motor de aprendizado adaptativo |
| 🎵 **Controle de mídia** | Tocar músicas, controlar volume |
| 🌐 **Automação** | Abrir sites/apps, pesquisar na web |

---

## 🏗️ Arquitetura

```
Jarvis2.0/
├── main.py                      # Ponto de entrada principal
├── jarvis_ui.py                 # Interface gráfica (PyQt6)
├── comandos.py                  # Módulo de comandos de voz
├── services/
│   ├── ai_service.py            # Serviço de IA em background
│   ├── tts_service.py           # Text-to-Speech em thread separada
│   └── audio_service.py         # Controle de volume (ducking)
├── nlp_processor.py             # Processador NLP com Gemini
├── conversation_manager.py      # Gerenciador de contexto
├── learning_engine.py           # Motor de aprendizado adaptativo
├── enhanced_voice_recording.py  # Gravação de voz aprimorada
└── tests/                       # Testes unitários
```

---

## 🎙️ Comandos Disponíveis

### Controle de Mídia
```
"Jarvis, tocar [nome da música]"    → Toca no YouTube
"aumentar volume"                    → Aumenta volume do sistema
"diminuir volume"                    → Diminui volume do sistema
"pausar" / "continuar"               → Controla reprodução
"próxima música"                     → Pula para próxima faixa
"música anterior"                    → Volta para faixa anterior
"mutar" / "silenciar"                → Muta o áudio
"desmutar"                           → Desmuta o áudio
```

### Aplicativos e Sites
```
"abrir [chrome/vscode/calculadora]"  → Abre aplicativos
"abrir [youtube/github/whatsapp]"    → Abre sites
"fechar [aplicativo]"                → Fecha aplicativos
"abrir pasta [documentos/downloads]" → Abre pastas do usuário
"último download"                    → Abre arquivo mais recente
```

### Informações
```
"que horas são"                      → Informa as horas
"que dia é hoje"                     → Informa a data
"temperatura"                        → Busca clima local
"verificar sistema"                  → Info do sistema
"verificar internet"                 → Velocidade da conexão
"cotação do dólar"                   → Cotação USD/BRL
"cotação do bitcoin"                 → Preço do Bitcoin
```

### Produtividade
```
"pesquisar [termo]"                  → Pesquisa no Google
"escreva [texto]"                    → Digita texto automaticamente
"tirar print"                        → Captura tela
"iniciar dia"                        → Rotina de início do dia
"finalizar dia"                      → Rotina de fim do dia
"criar timer 5 minutos"              → Cria um temporizador
"traduzir [texto] para [idioma]"     → Traduz texto (via Gemini)
"calcular 5 mais 3"                  → Calculadora por voz
```

### Sistema
```
"desligar computador"                → Desliga o PC
"reiniciar computador"               → Reinicia o PC
"minimizar"                          → Minimiza a interface
"bloquear tela"                      → Bloqueia o Windows
"limpar lixeira"                     → Esvazia a lixeira
"uso de memória"                     → Mostra RAM em uso
"uso do processador"                 → Mostra CPU em uso
"espaço em disco"                    → Mostra armazenamento
```

### Entretenimento
```
"contar piada"                       → Conta uma piada
"parar" / "sair"                     → Encerra conversa
```

---

## 📋 Pré-requisitos

- **Python 3.9+**
- **Windows 10/11** (otimizado para Windows)
- **Microfone** funcional
- **Chave API Gemini** (opcional, para IA avançada)

---

## 🚀 Instalação

### 1. Clone o repositório
```bash
git clone https://github.com/dclaumanndeveloper/Jarvis2.0.git
cd Jarvis2.0
```

### 2. Crie o ambiente virtual
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
```

### 3. Instale as dependências
```bash
pip install -r requirements.txt
```

### 4. Configure as variáveis de ambiente
Crie um arquivo `.env` na raiz do projeto:
```env
GEMINI_API_KEY=sua_chave_api_aqui
```

### 5. Execute o Jarvis
```bash
python main.py
```

---

## 🧪 Testes

Execute os testes unitários:
```bash
# Todos os testes
python -m pytest tests/ -v

# Testes específicos
python -m pytest tests/test_audio_service.py -v
python -m pytest tests/test_tts_service.py -v
python -m pytest tests/test_ai_service.py -v
python -m pytest tests/test_comandos.py -v
```

---

## 📁 Estrutura de Serviços

### AIService
Serviço em background para processamento de IA:
- Processamento de linguagem natural (NLP)
- Integração com Gemini 2.0 Flash
- Contexto de conversação
- Aprendizado adaptativo

### TTSService
Serviço de Text-to-Speech em thread separada:
- Fila de mensagens thread-safe
- Configuração de voz em português
- Integração COM para Windows (SAPI5)

### AudioService
Controle de volume do sistema:
- Ducking automático durante fala
- Restauração de volume original
- Integração com Windows Core Audio API

---

## 🔧 Tecnologias Utilizadas

| Categoria | Tecnologia |
|-----------|------------|
| Interface | PyQt6 |
| Reconhecimento de voz | SpeechRecognition, SoundDevice |
| Text-to-Speech | pyttsx3 (SAPI5) |
| IA | Google Gemini 2.0 Flash |
| Automação | pyautogui, pywhatkit |
| Áudio | pycaw, librosa |

---

## ⚠️ Avisos

- **Compatibilidade**: Desenvolvido para Windows. Algumas funções podem não funcionar em outros sistemas.
- **Permissões**: Algumas automações requerem permissões administrativas.
- **Microfone**: Certifique-se de que o microfone está configurado corretamente.

---

## 🤝 Contribuindo

1. Fork o repositório
2. Crie uma branch (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

---

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

---

## 👨‍💻 Autor

Desenvolvido por [dclaumanndeveloper](https://github.com/dclaumanndeveloper)

---

<p align="center">
  <b>⭐ Se este projeto te ajudou, deixe uma estrela!</b>
</p>
