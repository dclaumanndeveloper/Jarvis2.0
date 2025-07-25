import speech_recognition as sr
import pyttsx3

import webbrowser
import datetime
from comandos import abrir, aumentar_volume, buscar_temperatura, data, definir_volume, desligar_computador, diminuir_volume, escreva, finish_day, get_system_info, pausar, pesquisar, pesquisar_gemini, play, reiniciar_computador, start_day, tirar_print, tocar, verificar_internet
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
engine.setProperty('rate', 150)  # Ajuste a taxa de fala conforme necessário
engine.setProperty('input', 'pt-BR')  # Definindo o idioma para português do Brasil

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
        #r.pause_threshold = 0.5
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
        r.pause_threshold = 1
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
            elif 'pausar reprodução' in query:
                pausar()
                ui.showMinimized()
            elif 'continuar reprodução' in query:
                play()
                ui.showMinimized()
            elif 'que dia é hoje' in query:
                data()
                ui.showMinimized()
            elif 'reiniciar computador' in query:
                speak("Reiniciando o computador em 10 segundos.")
                if ctypes.windll.shell32.IsUserAnAdmin():
                    reiniciar_computador()
                else:
                    speak("Você precisa de privilégios de administrador para reiniciar o computador.")
                ui.showMinimized()
            elif 'desligar computador' in query:
                speak("Desligando o computador em 10 segundos.")
                if ctypes.windll.shell32.IsUserAnAdmin():
                    desligar_computador()
            
                else:
                    speak("Você precisa de privilégios de administrador para desligar o computador.")
                ui.showMinimized()
            elif 'tirar print' in query:
                try:
                    tirar_print()
                    ui.showMinimized()
                except Exception as e:
                    print(f"Erro ao tirar print: {e}")
                    speak("Desculpe, não consegui tirar a captura de tela.")
                ui.showMinimized()
            elif 'parar' in query or 'sair' in query:
                speak("Desativando. Até a próxima.")
                ui.showMinimized()
                break
            else:
                pesquisar_gemini(query)
                ui.showMinimized()
            


if __name__ == '__main__':
    command_thread = threading.Thread(target=process_commands, daemon=True)
    command_thread.start()
    app.exec()
