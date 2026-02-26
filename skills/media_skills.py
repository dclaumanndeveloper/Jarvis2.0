import pyautogui
import platform
import subprocess
from typing import Optional, Any
from services.action_controller import registry
from conversation_manager import IntentType, CommandCategory

# --- Platform Detection for Volume ---
IS_WINDOWS = platform.system() == "Windows"
IS_MACOS = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"

volume: Optional[Any] = None

if IS_WINDOWS:
    try: 
        import comtypes
        comtypes.CoInitialize()  # Initialize COM for this thread
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        devices = AudioUtilities.GetSpeakers()
        if devices and hasattr(devices, 'EndpointVolume'):
            volume = devices.EndpointVolume
    except (ImportError, OSError, Exception):
        volume = None

def set_volume(level: int) -> str:
    """Sets system volume (0-100)."""
    if IS_WINDOWS and volume:
        try:
            volume.SetMasterVolumeLevelScalar(level / 100.0, None)
            return "" 
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

# --- MEDIA SKILLS ---

@registry.register(intents=[IntentType.DIRECT_COMMAND], category=CommandCategory.MEDIA, description="Pausa a mídia atual")
def pausar() -> str:
    """Simulates play/pause media key."""
    pyautogui.press("playpause")
    return "Pausando a mídia."
    
@registry.register(intents=[IntentType.DIRECT_COMMAND], category=CommandCategory.MEDIA, description="Continua a mídia pausada")
def play() -> str:
    """Simulates play/pause media key."""
    pyautogui.press("playpause")
    return "Continuando a mídia."

@registry.register(intents=[IntentType.DIRECT_COMMAND], category=CommandCategory.MEDIA, description="Pula para próxima música")
def proxima_musica() -> str:
    """Skip to next track."""
    pyautogui.press("nexttrack")
    return "Próxima música."

@registry.register(intents=[IntentType.DIRECT_COMMAND], category=CommandCategory.MEDIA, description="Volta para música anterior")
def musica_anterior() -> str:
    """Go to previous track."""
    pyautogui.press("prevtrack")
    return "Música anterior."

@registry.register(intents=[IntentType.DIRECT_COMMAND], category=CommandCategory.MEDIA, description="Muta o áudio do sistema")
def mutar() -> str:
    """Mute system audio."""
    pyautogui.press("volumemute")
    return "Áudio mutado."

@registry.register(intents=[IntentType.DIRECT_COMMAND], category=CommandCategory.MEDIA, description="Remove o mudo do áudio")
def desmutar() -> str:
    """Unmute system audio."""
    pyautogui.press("volumemute")
    return "Áudio desmutado."

@registry.register(intents=[IntentType.DIRECT_COMMAND], category=CommandCategory.MEDIA, description="Aumenta o volume do sistema")
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

@registry.register(intents=[IntentType.DIRECT_COMMAND], category=CommandCategory.MEDIA, description="Diminui o volume do sistema")
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
    
@registry.register(intents=[IntentType.DIRECT_COMMAND], category=CommandCategory.MEDIA, description="Definir volume do sistema")
def definir_volume(command: str = None, *, level: int = None) -> str:
    """Sets volume based on voice command."""
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
