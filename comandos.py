import pyautogui
import pyttsx3
import pywhatkit
from datetime import datetime, time
import webbrowser
import platform
import os
import subprocess
import subprocess
import psutil
import geocoder
import google.generativeai as genai
import json
import threading
from collections import defaultdict
from itertools import tee


# --- Platform Detection ---
IS_WINDOWS = platform.system() == "Windows"
IS_MACOS = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"

# --- Conditional Imports and Initializations ---
engine = pyttsx3.init()

volume = None

if IS_WINDOWS:
    try: 
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
    except (ImportError, OSError):
        print("pycaw not found or failed to initialize. Windows volume control will be unavailable.")
        IS_WINDOWS = False # Treat as if not windows for volume control

# --- Dicionários para Comandos (acesso mais rápido) ---
SITES = {
    # Redes Sociais e Comunicação
    "google": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "facebook": "https://www.facebook.com",
    "whatsapp": "https://web.whatsapp.com",
    "instagram": "https://www.instagram.com",
    "twitter": "https://www.twitter.com",
    "x": "https://www.x.com",
    "linkedin": "https://www.linkedin.com",
    "reddit": "https://www.reddit.com",
    "pinterest": "https://www.pinterest.com",
    "tiktok": "https://www.tiktok.com",
    "discord": "https://www.discord.com/app",
    "telegram": "https://web.telegram.org",

    # Streaming e Mídia
    "spotify": "https://www.spotify.com",
    "netflix": "https://www.netflix.com",
    "twitch": "https://www.twitch.tv",
    "prime video": "https://www.primevideo.com",
    "disney plus": "https://www.disneyplus.com",

    # Compras e Vendas
    "amazon": "https://www.amazon.com",
    "mercado livre": "https://www.mercadolivre.com.br",
    "ebay": "https://www.ebay.com",
    "aliexpress": "https://www.aliexpress.com",

    # Ferramentas e Produtividade
    "github": "https://www.github.com",
    "chatgpt": "https://chat.openai.com",
    "notion": "https://www.notion.so",
    "gmail": "https://mail.google.com",
    "outlook": "https://outlook.live.com",
    "google drive": "https://drive.google.com",
    "canva": "https://www.canva.com",

    # Notícias e Informação
    "g1": "https://g1.globo.com/",
    "uol": "https://www.uol.com.br/",
    "cnn": "https://www.cnnbrasil.com.br/",
    "folha": "https://www.folha.uol.com.br/",
    "estadão": "https://www.estadao.com.br/",

    # Educação e Referência
    "wikipedia": "https://www.wikipedia.org",
    "stack overflow": "https://stackoverflow.com",
    
    # Jogos
    "tribal wars": "https://br128.tribalwars.com.br/game.php?village=13497&screen=overview",
}

# Application paths/commands per OS
APLICATIVOS = {
    "windows": {
        "câmera": "start microsoft.windows.camera:",
        "explorer": "start explorer",
        "arquivos": "start explorer",
        "calculadora": "start calc",
        "cmd": "start cmd",
        "chrome": "start chrome",
        "vscode": "code",
        "teams": "start ms-teams.exe",
        "navegador": "start http://www.google.com",
    },
    "macos": {
        "câmera": "open -a Photo Booth",
        "arquivos": "open .",
        "calculadora": "open -a Calculator",
        "terminal": "open -a Terminal",
        "chrome": "open -a 'Google Chrome'",
        "vscode": "code",
        "teams": "open -a 'Microsoft Teams'",
        "navegador": "open http://www.google.com",
    },
    "linux": {
        "arquivos": "xdg-open .",
        "calculadora": "gnome-calculator", # Varies by distro/DE
        "terminal": "gnome-terminal", # Varies by distro/DE
        "chrome": "google-chrome",
        "vscode": "code",
        "teams": "teams",
        "navegador": "xdg-open http://www.google.com",
    }
}

# Process names per OS
PROCESSOS = {
    "windows": {
        "vscode": "code.exe",
        "teams": "ms-teams.exe",
        "microsoft teams": "ms-teams.exe",
        "chrome": "chrome.exe",
    },
    "macos": {
        "vscode": "Code",
        "teams": "Microsoft Teams",
        "microsoft teams": "Microsoft Teams",
        "chrome": "Google Chrome",
    },
    "linux": {
        "vscode": "code",
        "teams": "teams",
        "microsoft teams": "teams",
        "chrome": "google-chrome",
    }
}

# --- Funções de Comando ---

def speak(text):
    """Função centralizada para falar."""
    engine.say(text)
    engine.runAndWait()

def get_current_location():
    """Obtém a localização atual baseada no IP."""
    try:
        location = geocoder.ip('me')
        if location.ok:
            return location.city, location.country
    except Exception as e:
        print(f"Erro ao obter localização: {e}")
    return None, None

def buscar_temperatura():
    """Abre o navegador na pesquisa de temperatura da localização atual."""
    city, country = get_current_location()
    if city and country:
        search_query = f"temperature in {city}, {country}"
        webbrowser.open(f"https://www.google.com/search?q={search_query}")
    else:
        speak("Não foi possível obter a localização para verificar a temperatura.")

def tocar(query):
    """Toca uma música no YouTube."""
    song = query.replace('tocar', "").strip()
    speak(f"Tocando {song}")
    pywhatkit.playonyt(song)

def horas():
    """Informa a hora atual."""
    now = datetime.now()
    speak(f"Agora são {now.hour} horas e {now.minute} minutos.") 

def pausar():
    """Pausa a mídia (simula a tecla de play/pause)."""
    speak("Pausando a mídia.")
    pyautogui.press("playpause")
    
def play():
    """Continua a mídia (simula a tecla de play/pause)."""
    speak("Continuando a mídia.")
    pyautogui.press("playpause")

def data():
    """Informa a data atual."""
    meses = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", 
           "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
    agora = datetime.now()
    nome_mes = meses[agora.month - 1]
    speak(f"Hoje é dia {agora.day} de {nome_mes} de {agora.year}.")

def get_desktop_path():
    """Retorna o caminho da área de trabalho de forma mais robusta."""
    home = os.path.expanduser("~")

    if IS_WINDOWS:
        try:
            # Tenta obter o caminho do Desktop do registro do Windows (mais confiável)
            import winreg

            key_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                desktop_path = winreg.QueryValueEx(key, "Desktop")[0]
            return os.path.expandvars(desktop_path)
        except Exception:
            # Fallback para caminhos comuns se a leitura do registro falhar
            desktop_en = os.path.join(home, "Desktop")
            if os.path.exists(desktop_en):
                return desktop_en
            desktop_pt = os.path.join(home, "Área de Trabalho")
            if os.path.exists(desktop_pt):
                return desktop_pt
            return desktop_en # Retorna o padrão em inglês como última opção
    else:
        # Para macOS e Linux, o padrão é geralmente 'Desktop'
        return os.path.join(home, "Desktop")


def tirar_print():
    """Tira uma captura de tela e a salva na área de trabalho."""
    try:
        # Cria um nome de arquivo único com data e hora
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        # Obtém o caminho da área de trabalho de forma confiável
        desktop_path = get_desktop_path()
        
        if not os.path.exists(desktop_path):
            os.makedirs(desktop_path) # Cria a pasta Desktop se não existir
            
        file_name = f"captura_{timestamp}.png"
        full_path = os.path.join(desktop_path, file_name)
        
        # Tira a captura de tela e salva diretamente no arquivo
        pyautogui.screenshot(full_path)
                    
        speak(f"Captura de tela salva em sua área de trabalho como {file_name}.")
    except Exception as e:
        print(f"Erro ao tirar print: {e}")
        speak("Desculpe, não consegui tirar a captura de tela.")

def desligar_computador():
    """Desliga o computador após confirmação."""
    speak("Desligando o computador em 10 segundos.")
    if IS_WINDOWS:
        os.system("shutdown /s /t 10")
    elif IS_MACOS:
        os.system("sudo shutdown -h +0") # Requer senha de administrador
    elif IS_LINUX:
        os.system("shutdown now")
                
def reiniciar_computador(confirmado=False):
    """Reinicia o computador após confirmação."""
    speak("Reiniciando o computador em 10 segundos.")
    if IS_WINDOWS:
        os.system("shutdown /r /t 10")
    elif IS_MACOS:
            os.system("sudo shutdown -r +0") # Requer senha de administrador
    elif IS_LINUX:
            os.system("reboot")

def pesquisar(command):
    """Pesquisa um termo no Google."""
    query = command.replace('pesquisar', '').strip()
    webbrowser.open(f"https://www.google.com/search?q={query}")
    speak(f"Pesquisando por {query} no Google.")
        
def set_volume(level):
    """Define o volume para um nível específico (0 a 100)."""
    if IS_WINDOWS and volume:
        volume.SetMasterVolumeLevelScalar(level / 100.0, None)
    elif IS_MACOS:
        subprocess.run(["osascript", "-e", f"set volume output volume {level}"])
    elif IS_LINUX:
        subprocess.run(["amixer", "-D", "pulse", "sset", "Master", f"{level}%"])
    else:
        speak("Desculpe, não consigo controlar o volume neste sistema.")

def aumentar_volume():
    """Aumenta o volume."""
    if IS_WINDOWS and volume:
        current_volume = volume.GetMasterVolumeLevelScalar() * 100
        new_volume = min(current_volume + 10, 100)
        set_volume(new_volume)
        speak(f"Volume aumentado para {int(new_volume)}%.")
    elif IS_MACOS or IS_LINUX:
        # These commands handle their own state
        if IS_MACOS:
            subprocess.run(["osascript", "-e", "set volume output volume (output volume of (get volume settings) + 10)"])
        elif IS_LINUX:
            subprocess.run(["amixer", "-D", "pulse", "sset", "Master", "10%+"])
        speak("Aumentando o volume.")
    else:
        speak("Desculpe, não consigo controlar o volume neste sistema.")

def diminuir_volume():
    """Diminui o volume."""
    if IS_WINDOWS and volume:
        current_volume = volume.GetMasterVolumeLevelScalar() * 100
        new_volume = max(current_volume - 10, 0)
        set_volume(new_volume)
        speak(f"Volume diminuído para {int(new_volume)}%.")
    elif IS_MACOS or IS_LINUX:
        if IS_MACOS:
            subprocess.run(["osascript", "-e", "set volume output volume (output volume of (get volume settings) - 10)"])
        elif IS_LINUX:
            subprocess.run(["amixer", "-D", "pulse", "sset", "Master", "10%-"])
        speak("Diminuindo o volume.")
    else:
        speak("Desculpe, não consigo controlar o volume neste sistema.")
    
def definir_volume(command):
    """Define o volume para um valor numérico informado."""
    try:
        new_volume_str = "".join(filter(str.isdigit, command))
        if new_volume_str:
            new_volume = int(new_volume_str)
            if 0 <= new_volume <= 100:
                set_volume(new_volume)
                speak(f"Volume definido para {new_volume}%.")
            else:
                speak("O volume deve estar entre 0 e 100%.")
        else:
            raise ValueError
    except ValueError:
        speak("Não entendi o valor do volume. Por favor, diga um número entre 0 e 100.")
        
def abrir(query):
    """Abre sites ou aplicativos com base na query."""
    query_lower = query.lower().replace('abrir', '').strip()

    if query_lower in SITES:
        speak(f"Abrindo {query_lower}")
        webbrowser.open(SITES[query_lower])
    

    os_name = platform.system().lower()
    if os_name == 'darwin': os_name = 'macos'
    
    app_dict = APLICATIVOS.get(os_name, {})
    if query_lower in app_dict:
        speak(f"Abrindo {query_lower}")
        command = app_dict[query_lower]
        # Use subprocess for better control and cross-platform compatibility
        subprocess.Popen(command, shell=True)
        # Optionally, you can wait for the process to start
        time.sleep(1)

    speak(f"Desculpe, não sei como abrir {query_lower}.")

def fechar(command):
    """Fecha um aplicativo específico."""
    app_to_close = command.lower().replace('fechar', '').strip()
    
    os_name = platform.system().lower()
    if os_name == 'darwin': os_name = 'macos'

    process_dict = PROCESSOS.get(os_name, {})
    
    if app_to_close in process_dict:
        process_name = process_dict[app_to_close]
        speak(f"Fechando {app_to_close}")
        try:
            if IS_WINDOWS:
                subprocess.run(["taskkill", "/f", "/im", process_name], check=True)
            else: # macOS and Linux
                subprocess.run(["pkill", "-f", process_name], check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            speak(f"Não foi possível fechar {app_to_close}. O processo pode não estar em execução.")
    else:
        speak("Não reconheci o aplicativo para fechar.")

def start_day():
    """Executa a rotina de início de dia."""
    speak("Iniciando o dia...")
    abrir("abrir vscode")
    abrir("abrir github")
    abrir("abrir teams")
    abrir("abrir arquivos")
    speak("Rotina de início de dia concluída!")

def finish_day():
    """Executa a rotina de fim de dia e bloqueia a tela."""
    speak("Finalizando o dia...")
    #fechar("fechar vscode")
    fechar("fechar teams")
    fechar("fechar arc")

    
    lock_command = ""
    if IS_WINDOWS:
        lock_command = "rundll32.exe user32.dll,LockWorkStation"
    elif IS_MACOS:
        lock_command = "/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/CGSession -suspend"
    elif IS_LINUX:
        # This is highly dependent on the desktop environment
        lock_command = "xdg-screensaver lock"

    if lock_command:
        try:
            subprocess.run(lock_command, shell=True, check=True)
            speak("Tela bloqueada.")
        except (subprocess.CalledProcessError, FileNotFoundError):
            speak("Não foi possível bloquear a tela.")
    
    speak("Rotina de fim de dia concluída!")

def verificar_internet():
    """Verifica e informa a velocidade da internet."""
    speak("Calculando a velocidade da internet, isso pode levar um momento.")
    try:
        # Executa o speedtest-cli via subprocess e captura a saída
        result = subprocess.run(["speedtest-cli", "--simple"], capture_output=True, text=True, check=True)
        output = result.stdout
        print(output)
        # Fala os resultados principais
        for line in output.splitlines():
            if "Download:" in line or "Upload:" in line:
                speak(line)
    except Exception as e:
        print(f"Erro ao executar speedtest-cli: {e}")
        speak("Não foi possível conectar para medir a velocidade. Verifique sua conexão com a internet.")
    
def get_system_info():
    """Retorna informações sobre o sistema."""
    cpu_usage = psutil.cpu_percent(interval=1)
    memory_info = psutil.virtual_memory()

    system_info = {
        'Sistema': f"{platform.system()} {platform.release()}",
        'Processador': platform.processor(),
        'Uso de CPU': f'{cpu_usage}%',
        'Memória Usada': f'{round(memory_info.used / (1024 ** 3), 2)} GB ({memory_info.percent}%)',
        'Memória Total': f'{round(memory_info.total / (1024 ** 3), 2)} GB',
    }
    speak(system_info)
    return system_info 

def escreva(command):
    """Digita o texto que segue o comando 'escreva'."""
    texto_para_escrever = command.replace("escreva", "", 1).strip()
    pyautogui.write(texto_para_escrever)



def pesquisar_gemini(command):
    """
    Pesquisa uma pergunta usando o Gemini 1.5 Pro e fala a resposta.
    """
    try:
        
        genai.configure(api_key="AIzaSyBuOScNR-FI818vE_JIZTx3J0X8YVgVpKw")  # Substitua pela sua chave de API do Gemini
    except (ImportError, Exception) as e:
        print(f"Erro ao configurar o Gemini: {e}")
        speak("Desculpe, a função de pesquisa com o Gemini não está disponível no momento.")
      
    # Remove o comando inicial para obter apenas a pergunta
    # Ex: "gemini qual a capital do brasil" -> "qual a capital do brasil"
    
    try:
        # Inicializa o modelo Gemini 2.0 Flash
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Gera o conteúdo com base na pergunta do usuário
        response = model.generate_content(command)
        
        # Extrai e fala a resposta
        answer = response.text
        answer = answer.replace('*','')
        answer = answer.replace('<','')
        answer = answer.replace('>','')
        answer = answer.replace('**','')
        print(f"Resposta do Gemini: {answer}")
        speak(answer)

    except Exception as e:
        error_message = f"Desculpe, ocorreu um erro ao contatar o Gemini: {e}"
        print(error_message)
        speak("Desculpe, ocorreu um erro ao contatar o Gemini.")



# --- Machine Learning / Pattern Recognition ---
COMMAND_LOG_FILE = "command_log.json"
LEARNED_PATTERNS = defaultdict(lambda: defaultdict(int))
MIN_PATTERN_FREQUENCY = 3 # Minimum times a pattern must appear to be learned
PATTERN_TIME_WINDOW_SECONDS = 120 # Max seconds between commands to be considered a sequence

def log_command_for_learning(command_text):
            """Logs a command with a timestamp for background learning."""
            try:
                # Avoid logging the learning command itself
                if "sugerir rotina" in command_text:
                    return
                log_entry = {"timestamp": datetime.now().isoformat(), "command": command_text}
                with open(COMMAND_LOG_FILE, "a", encoding="utf-8") as f:
                    f.write(json.dumps(log_entry) + "\n")
            except IOError as e:
                print(f"Erro ao registrar comando para aprendizado: {e}")

def _analyze_and_learn():
            """Analyzes the command log to find frequent sequential patterns."""
            global LEARNED_PATTERNS
            try:
                with open(COMMAND_LOG_FILE, "r", encoding="utf-8") as f:
                    logs = [json.loads(line) for line in f]
            except (IOError, json.JSONDecodeError):
                return # Log file doesn't exist or is empty/corrupt

            if len(logs) < 2:
                return

            # Sort logs by timestamp just in case
            logs.sort(key=lambda x: x["timestamp"])

            # Use an iterator to create pairs of consecutive commands (cmd1, cmd2)
            a, b = tee(logs)
            next(b, None)
            command_pairs = zip(a, b)

            temp_patterns = defaultdict(lambda: defaultdict(int))

            for cmd1_log, cmd2_log in command_pairs:
                t1 = datetime.fromisoformat(cmd1_log["timestamp"])
                t2 = datetime.fromisoformat(cmd2_log["timestamp"])
                
                # Check if the second command happened within the time window of the first
                if (t2 - t1).total_seconds() <= PATTERN_TIME_WINDOW_SECONDS:
                    first_cmd = cmd1_log["command"]
                    second_cmd = cmd2_log["command"]
                    temp_patterns[first_cmd][second_cmd] += 1
            
            # Update the global learned patterns, keeping only frequent ones
            LEARNED_PATTERNS.clear()
            for first_cmd, next_cmds in temp_patterns.items():
                for second_cmd, count in next_cmds.items():
                    if count >= MIN_PATTERN_FREQUENCY:
                        LEARNED_PATTERNS[first_cmd][second_cmd] = count
            
            if LEARNED_PATTERNS:
                print(f"Aprendizado concluído. Padrões atualizados: {dict(LEARNED_PATTERNS)}")


def suggest_routine(last_command):
            """
            Based on the last command, suggests the next most likely command.
            This function is meant to be called by the main loop.
            """
            _analyze_and_learn() # Update patterns before suggesting

            if last_command in LEARNED_PATTERNS:
                # Find the most likely next command
                potential_next_commands = LEARNED_PATTERNS[last_command]
                if potential_next_commands:
                    # Sort by frequency and get the most common one
                    suggestion = max(potential_next_commands, key=potential_next_commands.get)
                    
                    speak(f"Percebi que você sempre executa '{suggestion}' depois de '{last_command}'.")
                    speak("Gostaria de executar agora?")
                    # The main loop would need to handle the user's "sim" or "não" response
                    # and execute the `suggestion` if confirmed.
                    return suggestion # Return the suggestion for the main loop to handle
            return None