import pyautogui
import pyttsx3
import pywhatkit
from datetime import datetime
import webbrowser
import platform
import os
import subprocess
import speedtest
import psutil
import geocoder

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
        return

    os_name = platform.system().lower()
    if os_name == 'darwin': os_name = 'macos'
    
    app_dict = APLICATIVOS.get(os_name, {})
    if query_lower in app_dict:
        speak(f"Abrindo {query_lower}")
        command = app_dict[query_lower]
        # Use subprocess for better control and cross-platform compatibility
        subprocess.Popen(command, shell=True)
        return
    
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
        st = speedtest.Speedtest()
        st.get_best_server()
        download_speed = round(st.download() / 1_000_000, 2)
        upload_speed = round(st.upload() / 1_000_000, 2)
        
        print(f"Velocidade de Download: {download_speed} Mbps")
        print(f"Velocidade de Upload: {upload_speed} Mbps")
        speak(f"A velocidade de download é de {download_speed} megabits.")
        speak(f"A velocidade de upload é de {upload_speed} megabits.")
    except speedtest.ConfigRetrievalError:
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
    return system_info 

def escreva(command):
    """Digita o texto que segue o comando 'escreva'."""
    texto_para_escrever = command.replace("escreva", "", 1).strip()
    pyautogui.write(texto_para_escrever)
