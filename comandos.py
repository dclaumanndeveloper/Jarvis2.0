import pyautogui
# import pyttsx3 # Removed for architecture refactor
import pywhatkit
import time
from datetime import datetime
import webbrowser
import platform
import os
import subprocess
import psutil
import geocoder
import json
import threading
from collections import defaultdict
from itertools import tee
from typing import Optional, Tuple, Dict, List, Any
from dotenv import load_dotenv

# Import the new registry
from services.action_controller import registry
from services.vision_service import VisionService
from conversation_manager import IntentType

# --- Configuration & Initialization ---
load_dotenv()

# Helper to get env vars with default fallback
def get_env_var(key: str, default: Any = None) -> Any:
    return os.getenv(key, default)
# Gemini removido para execução 100% offline
GEMINI_API_KEY = None

# Initialize Text-to-Speech Engine
# engine = pyttsx3.init()  <-- Disabled to avoid conflict with main.py

# --- Platform Detection ---
IS_WINDOWS = platform.system() == "Windows"
IS_MACOS = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"

# --- Audio/Volume Control Initialization ---
volume: Optional[Any] = None

if IS_WINDOWS:
    try: 
        import comtypes
        comtypes.CoInitialize()  # Initialize COM for this thread
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        # Use the new pycaw API with EndpointVolume property
        devices = AudioUtilities.GetSpeakers()
        if devices and hasattr(devices, 'EndpointVolume'):
            volume = devices.EndpointVolume
            print(f"Volume control initialized: {type(volume)}")
        else:
            print("Volume control: No EndpointVolume available")
    except (ImportError, OSError, Exception) as e:
        print(f"Volume control initialization warning: {e}")
        volume = None

# --- Local AI Model Initialization (Global) ---
# Modelo offline processado via LocalAIProcessor
model = None

# --- Dictionaries ---
SITES: Dict[str, str] = {
    # Social & Communication
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
    # Streaming
    "spotify": "https://www.spotify.com",
    "netflix": "https://www.netflix.com",
    "twitch": "https://www.twitch.tv",
    "prime video": "https://www.primevideo.com",
    "disney plus": "https://www.disneyplus.com",
    # Shopping
    "amazon": "https://www.amazon.com",
    "mercado livre": "https://www.mercadolivre.com.br",
    "ebay": "https://www.ebay.com",
    "aliexpress": "https://www.aliexpress.com",
    # Tools
    "github": "https://www.github.com",
    "chatgpt": "https://chat.openai.com",
    "notion": "https://www.notion.so",
    "gmail": "https://mail.google.com",
    "outlook": "https://outlook.live.com",
    "google drive": "https://drive.google.com",
    "canva": "https://www.canva.com",
    # News
    "g1": "https://g1.globo.com/",
    "uol": "https://www.uol.com.br/",
    "cnn": "https://www.cnnbrasil.com.br/",
    "folha": "https://www.folha.uol.com.br/",
    "estadão": "https://www.estadao.com.br/",
    # Education
    "wikipedia": "https://www.wikipedia.org",
    "stack overflow": "https://stackoverflow.com",
    # Games
    "tribal wars": "https://br128.tribalwars.com.br/game.php?village=13497&screen=overview",
}

APLICATIVOS: Dict[str, Dict[str, str]] = {
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
        "calculadora": "gnome-calculator", 
        "terminal": "gnome-terminal", 
        "chrome": "google-chrome",
        "vscode": "code",
        "teams": "teams",
        "navegador": "xdg-open http://www.google.com",
    }
}

PROCESSOS: Dict[str, Dict[str, str]] = {
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

# --- Core Functions ---

# def speak(text: Any) -> None:
#    """Deprecated: Main.py handles all TTS now."""
#    pass

def get_current_location() -> Tuple[Optional[str], Optional[str]]:
    """Retrieves current location based on IP."""
    try:
        location = geocoder.ip('me')
        if location.ok:
            return location.city, location.country
    except Exception as e:
        print(f"Error getting location: {e}")
    return None, None

def buscar_temperatura() -> str:
    """Opens browser searching for current location's temperature."""
    city, country = get_current_location()
    if city and country:
        search_query = f"temperature in {city}, {country}"
        webbrowser.open(f"https://www.google.com/search?q={search_query}")
        return "Buscando informações de temperatura no Google."
    else:
        return "Não foi possível obter a localização para verificar a temperatura."

@registry.register(intents=[IntentType.DIRECT_COMMAND], description="Tocar música no YouTube")
def tocar(query: str = None, *, song: str = None) -> str:
    """Plays a song on YouTube.
    
    Args:
        query: Legacy string command (e.g., "tocar musica")
        song: Direct song name entity
    """
    if song:
        target = song
    elif query:
        target = query.replace('tocar', "").strip()
    else:
        return "O que você gostaria de tocar?"
    
    if target:
        pywhatkit.playonyt(target)
        return f"Tocando {target}"
    else:
        return "O que você gostaria de tocar?"

@registry.register(intents=[IntentType.TIME_QUERY], description="Verificar hora atual")
def horas() -> str:
    """Returns the current time string."""
    now = datetime.now()
    return f"Agora são {now.hour} horas e {now.minute} minutos."

def pausar() -> str:
    """Simulates play/pause media key."""
    pyautogui.press("playpause")
    return "Pausando a mídia."
    
def play() -> str:
    """Simulates play/pause media key."""
    pyautogui.press("playpause")
    return "Continuando a mídia."

@registry.register(intents=[IntentType.DATE_QUERY], description="Verificar data atual")
def data() -> Optional[str]:
    """Announces the current date."""
    meses = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", 
           "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
    agora = datetime.now()
    nome_mes = meses[agora.month - 1]
    return f"Hoje é dia {agora.day} de {nome_mes} de {agora.year}."

def get_desktop_path() -> str:
    """Returns the Desktop path reliably across platforms."""
    home = os.path.expanduser("~")

    if IS_WINDOWS:
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                desktop_path = winreg.QueryValueEx(key, "Desktop")[0]
            return os.path.expandvars(desktop_path)
        except Exception:
            # Fallback checks
            desktop_en = os.path.join(home, "Desktop")
            if os.path.exists(desktop_en): return desktop_en
            desktop_pt = os.path.join(home, "Área de Trabalho")
            if os.path.exists(desktop_pt): return desktop_pt
            return desktop_en 
    else:
        return os.path.join(home, "Desktop")

@registry.register(intents=[IntentType.DIRECT_COMMAND], description="Captura de tela")
def tirar_print() -> str:
    """Takes a screenshot and saves it to the desktop."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        desktop_path = get_desktop_path()
        
        if not os.path.exists(desktop_path):
            os.makedirs(desktop_path)
            
        file_name = f"captura_{timestamp}.png"
        full_path = os.path.join(desktop_path, file_name)
        
        pyautogui.screenshot(full_path)
        return f"Captura de tela salva em sua área de trabalho como {file_name}."
    except Exception as e:
        print(f"Error taking screenshot: {e}")
        return "Desculpe, não consegui tirar a captura de tela."

def desligar_computador() -> str:
    """Shuts down the computer."""
    if IS_WINDOWS:
        os.system("shutdown /s /t 10")
    elif IS_MACOS:
        os.system("sudo shutdown -h +0") # May require sudo
    elif IS_LINUX:
        os.system("shutdown now")
    return "Desligando o computador em 10 segundos."
                
def reiniciar_computador(confirmado: bool = False) -> str:
    """Restarts the computer."""
    if IS_WINDOWS:
        os.system("shutdown /r /t 10")
    elif IS_MACOS:
        os.system("sudo shutdown -r +0") # May require sudo
    elif IS_LINUX:
        os.system("reboot")
    return "Reiniciando o computador em 10 segundos."

@registry.register(intents=[IntentType.DIRECT_COMMAND], description="Pesquisar no Google")
def pesquisar(command: str = None, *, query: str = None) -> str:
    """Searches Google for a term.
    
    Args:
        command: Legacy string command (e.g., "pesquisar python")
        query: Direct search query entity
    """
    if query:
        search_term = query
    elif command:
        search_term = command.replace('pesquisar', '').strip()
    else:
        return "O que você gostaria de pesquisar?"
    
    if search_term:
        webbrowser.open(f"https://www.google.com/search?q={search_term}")
        return f"Pesquisando por {search_term} no Google."
    else:
        return "O que você gostaria de pesquisar?"

def set_volume(level: int) -> str:
    """Sets system volume (0-100)."""
    if IS_WINDOWS and volume:
        try:
            volume.SetMasterVolumeLevelScalar(level / 100.0, None)
            return "" # Internal function, return empty or status
        except Exception:
            pass
    elif IS_MACOS:
        subprocess.run(["osascript", "-e", f"set volume output volume {level}"])
        return ""
    elif IS_LINUX:
        subprocess.run(["amixer", "-D", "pulse", "sset", "Master", f"{level}%"])
        return ""
    else:
        return "Desculpe, não consigo controlar o volume neste sistema."

def aumentar_volume() -> str:
    """Increases system volume."""
    if IS_WINDOWS and volume:
        try:
            current_volume = volume.GetMasterVolumeLevelScalar() * 100
            new_volume = min(current_volume + 10, 100)
            set_volume(int(new_volume))
            return f"Volume aumentado para {int(new_volume)}%."
        except Exception:
            pass
    elif IS_MACOS:
        subprocess.run(["osascript", "-e", "set volume output volume (output volume of (get volume settings) + 10)"])
        return "Aumentando o volume."
    elif IS_LINUX:
        subprocess.run(["amixer", "-D", "pulse", "sset", "Master", "10%+"])
        return "Aumentando o volume."
    else:
        return "Desculpe, não consigo controlar o volume neste sistema."

def diminuir_volume() -> str:
    """Decreases system volume."""
    if IS_WINDOWS and volume:
        try:
            current_volume = volume.GetMasterVolumeLevelScalar() * 100
            new_volume = max(current_volume - 10, 0)
            set_volume(int(new_volume))
            return f"Volume diminuído para {int(new_volume)}%."
        except Exception:
            pass
    elif IS_MACOS:
        subprocess.run(["osascript", "-e", "set volume output volume (output volume of (get volume settings) - 10)"])
        return "Diminuindo o volume."
    elif IS_LINUX:
        subprocess.run(["amixer", "-D", "pulse", "sset", "Master", "10%-"])
        return "Diminuindo o volume."
    else:
        return "Desculpe, não consigo controlar o volume neste sistema."
    
@registry.register(intents=[IntentType.DIRECT_COMMAND], description="Definir volume do sistema")
def definir_volume(command: str = None, *, level: int = None) -> str:
    """Sets volume based on voice command.
    
    Args:
        command: Legacy string command (e.g., "volume 50")
        level: Direct volume level entity (0-100)
    """
    try:
        if level is not None:
            new_volume = level
        elif command:
            new_volume_str = "".join(filter(str.isdigit, command))
            if new_volume_str:
                new_volume = int(new_volume_str)
            else:
                raise ValueError
        else:
            return "Não entendi o valor do volume. Por favor, diga um número entre 0 e 100."
        
        if 0 <= new_volume <= 100:
            set_volume(new_volume)
            return f"Volume definido para {new_volume}%."
        else:
            return "O volume deve estar entre 0 e 100%."
    except ValueError:
        return "Não entendi o valor do volume. Por favor, diga um número entre 0 e 100."

@registry.register(intents=[IntentType.DIRECT_COMMAND], description="Abrir aplicativos ou sites")
def abrir(query: str = None, *, target: str = None) -> Optional[str]:
    """Opens a website or application.
    
    Args:
        query: Legacy string command (e.g., "abrir chrome")
        target: Direct target entity (e.g., "chrome")
    
    Returns:
        Success message or None
    """
    if target:
        query_lower = target.lower()
    elif query:
        query_lower = query.lower().replace('abrir', '').strip()
    else:
        return "O que você gostaria de abrir?"

    if query_lower in SITES:
        webbrowser.open(SITES[query_lower])
        return f"Abrindo {query_lower}"

    os_name = platform.system().lower()
    if os_name == 'darwin': os_name = 'macos'
    
    app_dict = APLICATIVOS.get(os_name, {})
    
    # 1. Try dictionary lookup
    if query_lower in app_dict:
        command_str = app_dict[query_lower]
        try:
            subprocess.Popen(command_str, shell=True)
            time.sleep(0.5) 
            return f"Abrindo {query_lower}"
        except Exception as e:
            print(f"Error opening app from dict: {e}")

    # 2. Try Generic System Open
    try:
        if IS_WINDOWS:
            os.startfile(query_lower)
            return f"Iniciando {query_lower}"
        elif IS_MACOS:
            subprocess.Popen(["open", "-a", query_lower])
            return f"Iniciando {query_lower}"
        elif IS_LINUX:
            subprocess.Popen(["xdg-open", query_lower])
            return f"Iniciando {query_lower}"
            
    except Exception:
        pass

    # 3. Fallback: Windows Start Menu Injection
    if IS_WINDOWS:
        try:
            pyautogui.press('win')
            time.sleep(0.5)
            pyautogui.write(query_lower)
            time.sleep(0.5)
            pyautogui.press('enter')
            return f"Abrindo {query_lower}"
        except Exception as e:
            print(f"Error with pyautogui: {e}")
            return f"Erro ao tentar abrir visualmente: {e}"

    return f"Não consegui encontrar {query_lower}, mas tentei abrir."

@registry.register(intents=[IntentType.DIRECT_COMMAND], description="Fechar aplicativos")
def fechar(command: str = None, *, target: str = None) -> str:
    """Closes an application.
    
    Args:
        command: Legacy string command (e.g., "fechar chrome")
        target: Direct target entity (e.g., "chrome")
    """
    if target:
        app_to_close = target.lower()
    elif command:
        app_to_close = command.lower().replace('fechar', '').strip()
    else:
        return "Qual aplicativo você quer fechar?"
    
    os_name = platform.system().lower()
    if os_name == 'darwin': os_name = 'macos'

    process_dict = PROCESSOS.get(os_name, {})
    
    if app_to_close in process_dict:
        process_name = process_dict[app_to_close]
        try:
            if IS_WINDOWS:
                subprocess.run(["taskkill", "/f", "/im", process_name], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else: # macOS and Linux
                subprocess.run(["pkill", "-f", process_name], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Fechando {app_to_close}"
        except subprocess.CalledProcessError:
            return f"Não foi possível fechar {app_to_close}. O processo pode não estar em execução."
    else:
        return "Não reconheci o aplicativo para fechar."

def start_day() -> str:
    """Starts the daily routine."""
    # Using generic 'abrir' might be safer if the dict keys change
    # But hardcoded keys are fine if they match SITES/APLICATIVOS
    abrir("abrir vscode")
    abrir("abrir github")
    abrir("abrir teams")
    abrir("abrir arquivos")
    return "Rotina de início de dia concluída! Iniciando sistema."

def finish_day() -> str:
    """Ends the daily routine and locks screen."""
    fechar("fechar teams")
    fechar("fechar arc") # Assumed 'arc' exists in processes or system

    lock_command = ""
    if IS_WINDOWS:
        lock_command = "rundll32.exe user32.dll,LockWorkStation"
    elif IS_MACOS:
        lock_command = "/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/CGSession -suspend"
    elif IS_LINUX:
        lock_command = "xdg-screensaver lock"

    msg = "Rotina de fim de dia concluída! "
    if lock_command:
        try:
            subprocess.run(lock_command, shell=True, check=True)
            msg += "Tela bloqueada."
        except Exception:
            msg += "Mas não foi possível bloquear a tela."
    
    return msg

def verificar_internet() -> str:
    """Checks internet speed."""
    try:
        # Run in a separate thread/process in a real UI usage, 
        # but here we are kept synchronous as requested, just wrapped in try/except
        result = subprocess.run(["speedtest-cli", "--simple"], capture_output=True, text=True, check=True)
        output = result.stdout
        print(output)
        
        response = "Velocidade da internet: "
        for line in output.splitlines():
            if "Download:" in line or "Upload:" in line:
               response += f"{line}. "
        return response
    except FileNotFoundError:
        return "O utilitário speedtest-cli não está instalado."
    except Exception as e:
        print(f"Speedtest error: {e}")
        return "Não foi possível conectar para medir a velocidade."

def get_system_info() -> str:
    """Returns system usage info."""
    cpu_usage = psutil.cpu_percent(interval=1)
    memory_info = psutil.virtual_memory()

    return f"Sistema: {platform.system()} {platform.release()}. CPU: {cpu_usage}%. Memória: {memory_info.percent}%." 

# --- NEW COMMANDS: Media Control ---

def proxima_musica() -> str:
    """Skip to next track."""
    pyautogui.press("nexttrack")
    return "Próxima música."

def musica_anterior() -> str:
    """Go to previous track."""
    pyautogui.press("prevtrack")
    return "Música anterior."

def mutar() -> str:
    """Mute system audio."""
    pyautogui.press("volumemute")
    return "Áudio mutado."

def desmutar() -> str:
    """Unmute system audio."""
    pyautogui.press("volumemute")
    return "Áudio desmutado."

# --- NEW COMMANDS: System Monitoring ---

def uso_memoria() -> str:
    """Returns memory usage information."""
    memory_info = psutil.virtual_memory()
    used_gb = memory_info.used / (1024 ** 3)
    total_gb = memory_info.total / (1024 ** 3)
    return f"Memória em uso: {memory_info.percent}%. Usando {used_gb:.1f} GB de {total_gb:.1f} GB."

def uso_cpu() -> str:
    """Returns CPU usage information."""
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_count = psutil.cpu_count()
    return f"Uso do processador: {cpu_percent}%. Você tem {cpu_count} núcleos."

def espaco_disco() -> str:
    """Returns disk space information."""
    if IS_WINDOWS:
        disk = psutil.disk_usage('C:\\')
    else:
        disk = psutil.disk_usage('/')
    
    free_gb = disk.free / (1024 ** 3)
    total_gb = disk.total / (1024 ** 3)
    used_percent = disk.percent
    return f"Disco: {used_percent}% usado. {free_gb:.1f} GB livres de {total_gb:.1f} GB."

def bloquear_tela() -> str:
    """Locks the screen."""
    if IS_WINDOWS:
        os.system("rundll32.exe user32.dll,LockWorkStation")
        return "Bloqueando a tela."
    elif IS_MACOS:
        os.system("pmset displaysleepnow")
        return "Bloqueando a tela."
    elif IS_LINUX:
        os.system("gnome-screensaver-command -l")
        return "Bloqueando a tela."
    return "Não foi possível bloquear a tela neste sistema."

def limpar_lixeira() -> str:
    """Empties the recycle bin/trash."""
    try:
        if IS_WINDOWS:
            import ctypes
            ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 0x0007)
            return "Lixeira esvaziada com sucesso."
        elif IS_MACOS:
            os.system("rm -rf ~/.Trash/*")
            return "Lixeira esvaziada com sucesso."
        elif IS_LINUX:
            os.system("rm -rf ~/.local/share/Trash/*")
            return "Lixeira esvaziada com sucesso."
    except Exception as e:
        return f"Não foi possível esvaziar a lixeira: {e}"
    return "Não foi possível esvaziar a lixeira neste sistema."

# --- NEW COMMANDS: Utilities ---

# Global timer storage
_active_timers: Dict[str, Any] = {}

def criar_timer(command: str = None, *, duration: int = None, unit: str = None) -> str:
    """Creates a timer.
    
    Args:
        command: Legacy string command (e.g., "timer 5 minutos")
        duration: Timer duration as integer
        unit: Time unit (segundo, minuto, hora)
    """
    import re
    import threading
    
    # Use structured entities if available
    if duration is not None and unit:
        amount = duration
        time_unit = unit
    elif command:
        # Extract time from command
        pattern = r'(\d+)\s*(segundo|segundos|minuto|minutos|hora|horas)'
        match = re.search(pattern, command.lower())
        
        if not match:
            return "Por favor, especifique o tempo. Exemplo: criar timer 5 minutos."
        
        amount = int(match.group(1))
        time_unit = match.group(2)
    else:
        return "Por favor, especifique o tempo. Exemplo: criar timer 5 minutos."
    
    # Convert to seconds
    if 'segundo' in time_unit:
        seconds = amount
    elif 'minuto' in time_unit:
        seconds = amount * 60
    elif 'hora' in time_unit:
        seconds = amount * 3600
    else:
        seconds = amount
    
    timer_id = f"timer_{len(_active_timers)}"
    
    def timer_callback():
        print(f"⏰ TIMER: {amount} {time_unit} se passaram!")
        if timer_id in _active_timers:
            del _active_timers[timer_id]
    
    timer = threading.Timer(seconds, timer_callback)
    timer.start()
    _active_timers[timer_id] = timer
    
    return f"Timer de {amount} {time_unit} criado. Vou te avisar quando terminar."

def traduzir(command: str = None, *, text: str = None, target_lang: str = None) -> Optional[str]:
    """Translates text (Offline fallback)."""
    return "Desculpe, o módulo de tradução local avançada ainda não está ativo."

@registry.register(intents=[IntentType.DIRECT_COMMAND], description="Cotação do Dólar")
def cotacao_dolar() -> str:
    """Gets the current USD to BRL exchange rate."""
    try:
        import urllib.request
        import json
        
        url = "https://economia.awesomeapi.com.br/json/last/USD-BRL"
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode())
            rate = float(data['USDBRL']['bid'])
            return f"A cotação do dólar está em {rate:.2f} reais."
    except Exception as e:
        return "Não foi possível obter a cotação do dólar no momento."

def cotacao_bitcoin() -> str:
    """Gets the current Bitcoin price."""
    try:
        import urllib.request
        import json
        
        url = "https://economia.awesomeapi.com.br/json/last/BTC-BRL"
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode())
            rate = float(data['BTCBRL']['bid'])
            return f"O Bitcoin está em {rate:,.2f} reais."
    except Exception as e:
        return "Não foi possível obter a cotação do Bitcoin no momento."

def calcular(command: str = None, *, expression: str = None) -> str:
    """Calculates a mathematical expression.
    
    Args:
        command: Legacy string command (e.g., "calcular 5 mais 3")
        expression: Direct mathematical expression
    """
    import re
    
    # Use structured entity if available
    if expression:
        expr = expression
    elif command:
        expr = command.lower().replace('calcular', '').replace('quanto é', '').strip()
    else:
        return "Por favor, diga a expressão. Exemplo: calcular 5 mais 3."
    
    # Replace Portuguese words with operators
    expr = expr.replace('mais', '+')
    expr = expr.replace('menos', '-')
    expr = expr.replace('vezes', '*')
    expr = expr.replace('dividido por', '/')
    expr = expr.replace('dividido', '/')
    expr = expr.replace('elevado a', '**')
    expr = expr.replace('ao quadrado', '**2')
    expr = expr.replace('ao cubo', '**3')
    
    # Remove any non-math characters for safety
    allowed = set('0123456789+-*/.() ')
    expr = ''.join(c for c in expr if c in allowed)
    
    if not expr:
        return "Por favor, diga a expressão. Exemplo: calcular 5 mais 3."
    
    try:
        result = eval(expr)
        # Format result nicely
        if isinstance(result, float):
            if result.is_integer():
                result = int(result)
            else:
                result = round(result, 4)
        return f"O resultado é {result}."
    except Exception:
        return "Não consegui calcular essa expressão."

# --- NEW COMMANDS: File Management ---

def abrir_pasta(command: str = None, *, folder: str = None) -> str:
    """Opens common user folders.
    
    Args:
        command: Legacy string command (e.g., "abrir pasta downloads")
        folder: Direct folder name entity
    """
    folder_map = {
        'documentos': 'Documents',
        'downloads': 'Downloads',
        'imagens': 'Pictures',
        'músicas': 'Music',
        'vídeos': 'Videos',
        'desktop': 'Desktop',
        'área de trabalho': 'Desktop',
    }
    
    # Determine which folder to open
    target_folder = None
    if folder:
        # Direct entity provided
        folder_lower = folder.lower()
        if folder_lower in folder_map:
            target_folder = folder_map[folder_lower]
            folder_name = folder_lower
        else:
            # Check if folder name is in the entity
            for name, path in folder_map.items():
                if name in folder_lower:
                    target_folder = path
                    folder_name = name
                    break
    elif command:
        command_lower = command.lower()
        for name, path in folder_map.items():
            if name in command_lower:
                target_folder = path
                folder_name = name
                break
    
    if not target_folder:
        return "Qual pasta você gostaria de abrir? Documentos, Downloads, Imagens, Músicas ou Vídeos?"
    
    home = os.path.expanduser("~")
    folder_path = os.path.join(home, target_folder)
    
    if os.path.exists(folder_path):
        if IS_WINDOWS:
            os.startfile(folder_path)
        elif IS_MACOS:
            subprocess.run(['open', folder_path])
        else:
            subprocess.run(['xdg-open', folder_path])
        return f"Abrindo pasta {folder_name}."
    else:
        return f"Pasta {folder_name} não encontrada."

def abrir_ultimo_download() -> str:
    """Opens the most recent file in Downloads folder."""
    home = os.path.expanduser("~")
    downloads_path = os.path.join(home, "Downloads")
    
    if not os.path.exists(downloads_path):
        return "Pasta de downloads não encontrada."
    
    try:
        files = [os.path.join(downloads_path, f) for f in os.listdir(downloads_path)]
        files = [f for f in files if os.path.isfile(f)]
        
        if not files:
            return "Não há arquivos na pasta de downloads."
        
        # Sort by modification time, newest first
        files.sort(key=os.path.getmtime, reverse=True)
        latest_file = files[0]
        
        if IS_WINDOWS:
            os.startfile(latest_file)
        elif IS_MACOS:
            subprocess.run(['open', latest_file])
        else:
            subprocess.run(['xdg-open', latest_file])
        
        filename = os.path.basename(latest_file)
        return f"Abrindo {filename}."
    except Exception as e:
        return f"Erro ao abrir último download: {e}"

def contar_piada() -> Optional[str]:
    """Tells a joke using Gemini AI."""
    if not model:
        piadas = [
            "Por que o programador usa óculos? Porque ele não consegue C#!",
            "O que o café disse para o açúcar? Sem você minha vida é amarga!",
            "Por que o livro de matemática está triste? Porque tem muitos problemas!",
        ]
        import random
        return random.choice(piadas)
    
    try:
        prompt = "Conte uma piada curta e engraçada em português brasileiro. Apenas a piada, sem explicações."
        response = model.generate_content(prompt)
        if response and response.text:
            return response.text.strip()
    except Exception:
        pass
    
    return "O que o pato disse para a pata? Vem quá!"

def escreva(command: str = None, *, text: str = None) -> str:
    """Types the text found in the command.
    
    Args:
        command: Legacy string command (e.g., "escreva olá mundo")
        text: Direct text entity to type
    """
    if text:
        texto_para_escrever = text
    elif command:
        texto_para_escrever = command.replace("escreva", "", 1).replace("digite", "", 1).strip()
    else:
        return "O que você gostaria que eu escrevesse?"
    
    if texto_para_escrever:
        pyautogui.write(texto_para_escrever)
        return "Texto digitado."
    else:
        return "O que você gostaria que eu escrevesse?"

def pesquisar_gemini(command: str) -> Optional[str]:
    """
    Offline fallback for natural language queries.
    """
    return "Módulo de IA em nuvem desativado. Jarvis operando em rede neural local."


# --- NEW COMMANDS: Local AI Vision ---

vision_service_instance = VisionService()

@registry.register(intents=[IntentType.VISION_QUERY], description="Analisar conteúdo da tela ou câmera")
def analisar_visao(command: str = None, **kwargs) -> str:
    """Uses Ollama Vision to see the screen or camera."""
    is_camera = False
    
    if command:
        cmd_lower = command.lower()
        if "câmera" in cmd_lower or "camera" in cmd_lower or "você está vendo" in cmd_lower or "olhe" in cmd_lower:
            is_camera = True
            
    try:
        if is_camera:
            img_b64 = vision_service_instance.capture_camera_base64()
            if not img_b64:
                return "Não consegui acessar a câmera. Ela pode estar em uso ou não conectada."
            return vision_service_instance.analyze_image(img_b64, "Descreva o que você está vendo na imagem capturada pela webcam.")
        else:
            img_b64 = vision_service_instance.capture_screen_base64()
            if not img_b64:
                return "Houve um problema ao capturar a sua tela."
            return vision_service_instance.analyze_image(img_b64, "Me descreva em detalhes o que está aparecendo nesta captura da minha tela de computador.")
    except Exception as e:
        return f"Erro ao processar imagem para o motor de visão: {e}"

# --- Machine Learning / Pattern Recognition ---
COMMAND_LOG_FILE = "command_log.json"
LEARNED_PATTERNS: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
MIN_PATTERN_FREQUENCY = 3 
PATTERN_TIME_WINDOW_SECONDS = 120 

def log_command_for_learning(command_text: str) -> None:
    """Logs a command with a timestamp for background learning."""
    try:
        if "sugerir rotina" in command_text:
            return
        log_entry = {"timestamp": datetime.now().isoformat(), "command": command_text}
        with open(COMMAND_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except IOError as e:
        print(f"Erro ao registrar comando para aprendizado: {e}")

def _analyze_and_learn() -> None:
    """Analyzes the command log to find frequent sequential patterns."""
    global LEARNED_PATTERNS
    try:
        if not os.path.exists(COMMAND_LOG_FILE):
             return

        with open(COMMAND_LOG_FILE, "r", encoding="utf-8") as f:
            logs = [json.loads(line) for line in f]
    except (IOError, json.JSONDecodeError):
        return 

    if len(logs) < 2:
        return

    logs.sort(key=lambda x: x["timestamp"])

    a, b = tee(logs)
    next(b, None)
    command_pairs = zip(a, b)

    temp_patterns: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for cmd1_log, cmd2_log in command_pairs:
        try:
            t1 = datetime.fromisoformat(cmd1_log["timestamp"])
            t2 = datetime.fromisoformat(cmd2_log["timestamp"])
            
            if (t2 - t1).total_seconds() <= PATTERN_TIME_WINDOW_SECONDS:
                first_cmd = cmd1_log["command"]
                second_cmd = cmd2_log["command"]
                temp_patterns[first_cmd][second_cmd] += 1
        except ValueError:
            continue
    
    LEARNED_PATTERNS.clear()
    for first_cmd, next_cmds in temp_patterns.items():
        for second_cmd, count in next_cmds.items():
            if count >= MIN_PATTERN_FREQUENCY:
                LEARNED_PATTERNS[first_cmd][second_cmd] = count
    
    if LEARNED_PATTERNS:
        # Debug print, can be removed in prod
        # print(f"Aprendizado concluído. Padrões atualizados: {dict(LEARNED_PATTERNS)}")
        pass

def suggest_routine(last_command: str) -> Optional[str]:
    """
    Based on the last command, suggests the next most likely command.
    """
    _analyze_and_learn() 

    if last_command in LEARNED_PATTERNS:
        potential_next_commands = LEARNED_PATTERNS[last_command]
        if potential_next_commands:
            suggestion = max(potential_next_commands, key=potential_next_commands.get) # type: ignore
            
            # speak(f"Percebi que você sempre executa '{suggestion}' depois de '{last_command}'.")
            # speak("Gostaria de executar agora?")
            return suggestion 
    return None 
    return None