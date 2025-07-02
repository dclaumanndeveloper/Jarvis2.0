import speech_recognition as sr
import pyttsx3

import webbrowser
import datetime
from comandos import abrir, aumentar_volume, buscar_temperatura, definir_volume, diminuir_volume, escreva, finish_day, get_system_info, pesquisar, start_day, tocar, verificar_internet
from jarvis_ui import JarvisUI
from PyQt6.QtWidgets import QApplication
import threading

import ctypes

try:
    ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)  # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
except Exception as e:
    print(f"Could not set DPI awareness: {e}")

app = QApplication([])
ui = JarvisUI()
ui.show()
engine = pyttsx3.init('sapi5')
voices = engine.getProperty('voices')
engine.setProperty('voice', voices[0].id)

def speak(audio_text):
    engine.say(audio_text)
    engine.runAndWait()

def greet_user():
    hour = datetime.datetime.now().hour
    if 0 <= hour < 12:
        speak("Bom dia!")
    elif 12 <= hour < 18:
        speak("Boa tarde!")
    else:
        speak("Boa noite!")
    speak("Eu sou Jarvis. Diga 'Jarvis' para me ativar.")

def listen_for_wake_word():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Aguardando palavra de ativação ('Jarvis')...")
        r.pause_threshold = 0.5
        audio = r.listen(source)
    try:
        query = r.recognize_google(audio, language='pt-BR')
        print(f"Ouvi: {query}")
        if 'jarvis' in query.lower():
            return True
    except Exception:
        pass
    return False

def take_query():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        speak("Estou ouvindo seu comando.")
        print("Ouvindo comando...")
        r.pause_threshold = 0.5
        audio = r.listen(source)
    try:
        print("Reconhecendo...")
        query = r.recognize_google(audio, language='pt-BR')
        if query:
            print(f"Usuário disse: {query}\n")
            ui.showMaximized()
            return query.lower()
    except Exception as e:
        print(e)
        return "None"
    return "None"

def process_commands():
    greet_user()
    while True:
        if listen_for_wake_word():
            query = take_query()
            if query == "None":
                continue

            # Lógica para executar tarefas
            if 'abrir google' in query:
                speak("Abrindo o Google...")
                webbrowser.open_new_tab("https://www.google.com")
                ui.showMinimized()
            elif 'que horas são' in query:
                str_time = datetime.datetime.now().strftime("%H:%M:%S")
                speak(f"Senhor, agora são {str_time}")
                ui.showMinimized()
            elif 'tocar' in query:
                tocar(query) 
                ui.showMinimized()
            elif 'aumentar volume' in query:
                aumentar_volume()
                ui.showMinimized()
            elif 'diminuir volume' in query:
                diminuir_volume()
                ui.showMinimized()
            elif 'definir' in query and 'volume' in query:
                definir_volume(query)
                ui.showMinimized()
            elif 'pesquisar' in query:
                pesquisar(query)
                ui.showMinimized()
            elif 'abrir' in query:
                abrir(query)
                ui.showMinimized()
            elif 'verificar' in query and 'internet' in query:
                verificar_internet()
                ui.showMinimized()
            elif 'verificar' in query and 'sistema' in query:
                system_info = get_system_info()
                for key, value in system_info.items():
                    print(f'{key}: {value}')
                    speak(f'{key}: {value}')
                ui.showMinimized()
            elif 'ligar as luzes' in query:
                speak("Ligando as luzes.")
                ui.showMinimized()
            elif 'temperatura' in query:
                buscar_temperatura()
                ui.showMinimized()
            elif 'escreva' in query:
                escreva(query)
                ui.showMinimized()
            elif 'iniciar dia' in query:
                start_day()
                ui.showMinimized()
            elif 'finalizar dia' in query:
                finish_day()
                ui.showMinimized()
            elif 'parar' in query or 'sair' in query:
                speak("Desativando. Até a próxima.")
                ui.showMinimized()
                break

if __name__ == '__main__':
    command_thread = threading.Thread(target=process_commands, daemon=True)
    command_thread.start()
    app.exec()
