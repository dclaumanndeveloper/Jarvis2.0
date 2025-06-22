import pyautogui
import pyttsx3
import pywhatkit
from datetime import datetime
import webbrowser
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
import pyaudio
import platform
import os
import speedtest
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume 
import psutil
import geocoder
#from distutils.version import LooseVersion
engine = pyttsx3.init()

# Inicialização do controle de volume
devices = AudioUtilities.GetSpeakers()
interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
volume = cast(interface, POINTER(IAudioEndpointVolume))

def say(text):    
    engine.say(text)
    engine.runAndWait()
    return


# Função para falar
def speak(text):
    engine.say(text)
    engine.runAndWait()

def get_current_location():
    # Get your current location based on IP address
    location = geocoder.ip('me')

    # Access city and country information
    city = location.city
    country = location.country

    return city, country
def buscar_temperatura():
    # Get current location
    city, country = get_current_location()
   
    # Construct a Google search query for the current temperature
    search_query = f"temperature in {city}, {country}"

    # Open the default web browser with the Google search query
    webbrowser.open(f"https://www.google.com/search?q={search_query}")    

def tocar(query):
    song = query.replace('tocar', "")
    speak("Tocando " + song)
    pywhatkit.playonyt(song)

def horas():
    now = datetime.now()
    speak(f"Agora são {now.hour} horas e {now.minute} minutos.") 
def pausar():
    pyautogui.press("k")
    
def play():
    pyautogui.press("k")
def pesquisar(command):
        query = command.replace('pesquisar', '')
        webbrowser.open(f"https://www.google.com/search?q={query}")
        speak(f"Pesquisando por {query} no Google.")
        
def set_volume(level):
    """Define o volume para o nível especificado (0 a 100)."""
    volume.SetMasterVolumeLevelScalar(level / 100.0, None)

def aumentar_volume():
    current_volume = volume.GetMasterVolumeLevelScalar() * 100
    new_volume = min(current_volume + 10, 100)  # Aumenta em 10%, mas não ultrapassa 100%
    set_volume(new_volume)
    speak(f"Volume aumentado para {int(new_volume)}%.")   

def diminuir_volume():
    current_volume = volume.GetMasterVolumeLevelScalar() * 100
    new_volume = max(current_volume - 10, 0)  # Diminui em 10%, mas não vai abaixo de 0%
    set_volume(new_volume)
    speak(f"Volume diminuído para {int(new_volume)}%.")    
    
def definir_volume(command):
    try:
        new_volume = int(command.replace('volume', '').replace('definir', '').replace('para', '').strip())
        if 0 <= new_volume <= 100:
            set_volume(new_volume)
            speak(f"Volume definido para {new_volume}%.")
        else:
            speak("O volume deve estar entre 0 e 100%.")
    except ValueError:
        speak("Não entendi o valor do volume. Por favor, diga um número entre 0 e 100.")
        
def abrir(query):
                    sites = [
                        ["google", "https://www.google.com"],
                        ["youtube", "https://www.youtube.com"],
                        ["facebook", "https://www.facebook.com"],
                        ["whatsapp", "https://www.whatsapp.com"],
                        ["instagram", "https://www.instagram.com"],
                        ["cricbuzz", "https://www.cricbuzz.com"],
                        ["gaana", "https://gaana.com"],
                        ["hotstar", "https://www.hotstar.com"],
                        ["bookmyshow", "https://www.bookmyshow.com"],
                        ["makemytrip", "https://www.makemytrip.com"],
                        ["zomato", "https://www.zomato.com"],
                        ["swiggy", "https://www.swiggy.com"],
                        ["phonepe", "https://www.phonepe.com"],
                        ["paytm", "https://paytm.com"],
                        ["chatgpt", "https://www.chatbot.com"],
                        ["stackoverflow", "https://stackoverflow.com"],
                        ["spotify", "https://www.spotify.com"],
                        ["github", "https://www.github.com"],
                        ["google maps", "https://www.google.com/maps"],
                        ["duckduckgo", "https://duckduckgo.com"],
                        ["linkedin", "https://www.linkedin.com"],
                        ["reddit", "https://www.reddit.com"],
                        ["netflix", "https://www.netflix.com"],
                        ["ebay", "https://www.ebay.com"],
                        ["microsoft", "https://www.microsoft.com"],
                        ["apple", "https://www.apple.com"],
                        ["pinterest", "https://www.pinterest.com"],
                        ["yandex", "https://www.yandex.ru"],
                        ["bing", "https://www.bing.com"],
                        ["aliexpress", "https://www.aliexpress.com"],
                        ["zoom", "https://www.zoom.us"],
                        ["wordpress", "https://www.wordpress.com"],
                        ["snapchat", "https://www.snapchat.com"],
                        ["weather", "https://www.weather.com"],
                        ["figma", "https://www.figma.com"],
                        ["canva", "https://www.canva.com"],
                        ["quora", "https://www.quora.com"],
                        ["telegram", "https://web.telegram.org"],
                        ["tiktok", "https://www.tiktok.com"],
                        ["wikipedia", "https://www.wikipedia.org"],
                        ["amazon", "https://www.amazon.com"],
                        ["ebay", "https://www.ebay.com"],
                        ["alibaba", "https://www.alibaba.com"],
                        ["yahoo", "https://www.yahoo.com"],
                        ["tumblr", "https://www.tumblr.com"],
                        ["notion", "https://www.notion.so"],
                        ["craigslist", "https://www.craigslist.org"],
                        ["tribal wars", "https://br128.tribalwars.com.br/game.php?village=13497&screen=overview"],
                    ]
                    for site in sites:
                        if f"Abrir {site[0]}".lower() in query.lower():
                            speak(f"Abrindo {site[0]}")
                            webbrowser.open(site[1])
                    if "abrir câmera".lower() in query.lower():
                        print("Tentando abrir camera")
                        if platform.system() == "Windows":
                            webbrowser.open("microsoft.windows.camera:")
                            print("Camera aberta")
                            speak("Camera opened")

                    elif "abrir explorer".lower() in query.lower() or "abrir arquivos" in query:
                        print("Tentando abrir Explorer")
                        if platform.system() == "Windows":
                            os.system("start explorer")
                            print("Explorer aberto")
                            speak("Explorer aberto")

                    elif "abrir calculadora".lower() in query.lower():
                        print("Tentando abrir Calculadora")
                        if platform.system() == "Windows":
                            os.system("start calc")
                            print("Calculadora aberta")
                            speak("Calculadora aberta")

                    elif "abrir cmd".lower() in query.lower():
                        print("Tentando abrir Cmd")
                        if platform.system() == "Windows":
                            os.system("start cmd")
                            print("cmd aberto")
                            speak("cmd aberto")
                    

                    elif ("abrir anaconda navigator".lower() in query.lower() or "abrir anaconda".lower() in query.lower()) and "open anaconda promt" not in query.lower():

                        print("Tentando abrir o Anaconda Navigator")
                        if platform.system() == "Windows":
                            os.system("start anaconda-navigator")
                            print("Anaconda Navigator aberto")
                            speak("Anaconda Navigator aberto")
                    

                    elif "abrir chrome".lower() in query.lower():
                        print("Tentando abrir o Chrome")
                        if platform.system() == "Windows":
                            os.system("start chrome")
                            print("Chrome aberto")
                            speak("Chrome aberto")
                    

                    elif "abrir vscode".lower() in query.lower():
                        print("Tentando abrir o Visual Studio Code")
                        speak("Abrindo Visual Studio Code")
                        if platform.system() == "Windows":
                            os.system("code")
                            print("Visual Studio Code aberto")
                            speak("Visual Studio Code aberto")

                    elif "abrir navegador".lower() in query.lower():
                        print("Tentando abrir o navegador padrão")
                        if platform.system() == "Windows":
                            webbrowser.open("http://www.google.com")
                            print("Navegador aberto")
                            speak("Navegador aberto")

                    elif "abrir vscode".lower() in query.lower():
                        print("Tentando abrir o Visual Studio Code")
                        if platform.system() == "Windows":
                            os.system("code")
                            print("Visual Studio Code aberto")
                            speak("Visual Studio Code aberto")

                    elif "abrir teams".lower() in query.lower() or "abrir microsoft teams".lower() in query.lower():
                        print("Tentando abrir o Microsoft Teams")
                        speak("Abrindo Microsoft Teams")
                        if platform.system() == "Windows":
                            os.system("start ms-teams.exe")
                            print("Microsoft Teams aberto")
                            speak("Microsoft Teams aberto")

def fechar(command):
    if "fechar" in command:
        if "vscode" in command:
            speak("Fechando Visual Studio Code")
            os.system("taskkill /f /im code.exe")
        elif "notion" in command:
            speak("Fechando Navegador")
            os.system("taskkill /f /im arc.exe")
        elif "teams" in command or "microsoft teams" in command:
            speak("Fechando Microsoft Teams")
            os.system("taskkill /f /im ms-teams.exe")
        else:
            speak("Comando não reconhecido para fechar.")

def start_day():
    speak("Iniciando o dia...")
    print("Iniciando o dia...")
    abrir("abrir vscode")
    abrir("abrir notion")
    abrir("abrir github")
    abrir("abrir teams")
    abrir("abrir explorer")
    speak("Dia iniciado com sucesso!")

def finish_day():
    speak("Finalizando o dia...")
    print("Finalizando o dia...")
    #fechar("fechar vscode")
    fechar("fechar notion")
    fechar("fechar teams")
    if platform.system() == "Windows":
        os.system("rundll32.exe user32.dll,LockWorkStation")
        speak("Tela bloqueada.")
    speak("Dia finalizado com sucesso!")


def verificar_internet():
    speak("Calculando velocidade da internet")
    print("Calculando velocidade da internet ... Aguarde!")
    wifi = speedtest.Speedtest()
    upload_net = round(wifi.upload() / 1048576,2)
    download_net = round(wifi.download() / 1048576,2)
    print("Wifi velocidade de upload", upload_net)
    print("Wifi velocidade de download", download_net)
    speak(f"Velocidade de Upload  {upload_net}")
    speak(f"Velocidade de download {download_net}")
    
# Function to get system information
def get_system_info():
    system_info = {
        'Sistema': platform.system(),
        'Nome da máquina': platform.node(),
        'Release': platform.release(),
        'Versão': platform.version(),
        'Máquina': platform.machine(),
        'Processador': platform.processor()
    }
    cpu_usage = psutil.cpu_percent(interval=1)
    memory_info = psutil.virtual_memory()

    system_info['Uso de CPU'] = f'{cpu_usage}%'
    system_info['Total de Memória'] = f'{round(memory_info.total / (1024 ** 3), 2)} GB'
    system_info['Memória disponivel'] = f'{round(memory_info.available / (1024 ** 3), 2)} GB'
    system_info['Memoria Usada'] = f'{round(memory_info.used / (1024 ** 3), 2)} GB'
    system_info['Uso de Memória'] = f'{memory_info.percent}%'

    return system_info 

def escreva(command):
    
    escreva = command.replace("escreva","")
    
    pyautogui.write(escreva)
    