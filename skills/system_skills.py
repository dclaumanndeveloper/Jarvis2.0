import psutil
import platform
import os
from services.action_controller import registry
from conversation_manager import IntentType, CommandCategory

# --- SYSTEM MONITORING SKILLS ---

@registry.register(intents=[IntentType.INFORMATION_QUERY], category=CommandCategory.INFORMATION, description="Mostra uso de memória RAM")
def uso_memoria() -> str:
    """Returns memory usage information."""
    memory_info = psutil.virtual_memory()
    used_gb = memory_info.used / (1024 ** 3)
    total_gb = memory_info.total / (1024 ** 3)
    return f"Memória em uso: {memory_info.percent}%. Usando {used_gb:.1f} GB de {total_gb:.1f} GB."

@registry.register(intents=[IntentType.INFORMATION_QUERY], category=CommandCategory.INFORMATION, description="Mostra uso do processador")
def uso_cpu() -> str:
    """Returns CPU usage information."""
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_count = psutil.cpu_count()
    return f"Uso do processador: {cpu_percent}%. Você tem {cpu_count} núcleos."

@registry.register(intents=[IntentType.INFORMATION_QUERY], category=CommandCategory.INFORMATION, description="Mostra espaço em disco")
def espaco_disco() -> str:
    """Returns disk space information."""
    IS_WINDOWS = platform.system() == "Windows"
    if IS_WINDOWS:
        disk = psutil.disk_usage('C:\\')
    else:
        disk = psutil.disk_usage('/')
    
    free_gb = disk.free / (1024 ** 3)
    total_gb = disk.total / (1024 ** 3)
    used_percent = disk.percent
    return f"Disco: {used_percent}% usado. {free_gb:.1f} GB livres de {total_gb:.1f} GB."

@registry.register(intents=[IntentType.INFORMATION_QUERY], category=CommandCategory.INFORMATION, description="Mostra informações do sistema")
def get_system_info() -> str:
    """Returns system usage info."""
    cpu_usage = psutil.cpu_percent(interval=1)
    memory_info = psutil.virtual_memory()

    return f"Sistema: {platform.system()} {platform.release()}. CPU: {cpu_usage}%. Memória: {memory_info.percent}%." 
