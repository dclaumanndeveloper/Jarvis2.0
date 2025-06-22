import speech_recognition as sr
import pyttsx3
import webbrowser
import datetime
from comandos import abrir, aumentar_volume, buscar_temperatura, definir_volume, diminuir_volume, escreva, finish_day, get_system_info, pesquisar, start_day, tocar, verificar_internet
from jarvis_ui import JarvisUI
# Inicializa a interface gráfica
from PyQt6.QtWidgets import QApplication
app = QApplication([])
#import simpleaudio as sa
ui = JarvisUI()
ui.show()
engine = pyttsx3.init('sapi5')
voices = engine.getProperty('voices')
#wave_obj = sa.WaveObject.from_wave_file("Voz-do-jarvis.wav")
# Você pode escolher uma voz, por exemplo, a primeira disponível
engine.setProperty('voice', voices[0].id)

def speak(audio_text):
    """Função para o J.A.R.V.I.S. falar."""
    engine.say(audio_text)
    engine.runAndWait()

def greet_user():
    """Saúda o usuário de acordo com a hora do dia."""
    hour = datetime.datetime.now().hour
    if 0 <= hour < 12:
        speak("Bom dia!")
    elif 12 <= hour < 18:
        speak("Boa tarde!")
    else:
        speak("Boa noite!")
    speak("Eu sou Jarvis. Como posso ajudar?")

def take_query():
    """Ouve o comando do usuário e retorna como texto."""
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Ouvindo...")
        r.pause_threshold = 1
        audio = r.listen(source)

    try:
        print("Reconhecendo...")
        query = r.recognize_google(audio, language='pt-BR')
        print(f"Usuário disse: {query}\n")
    except Exception as e:
        print(e)
#        speak("Desculpe, não consegui entender. Pode repetir?")
        return "None"
    return query.lower()

if __name__ == '__main__':
    greet_user()
    while True:
        query = take_query()

        # Lógica para executar tarefas
        if 'abrir google' in query:
            
            speak("Abrindo o Google...")
            webbrowser.open("https://www.google.com")
        
        elif 'que horas são' in query:
            str_time = datetime.datetime.now().strftime("%H:%M:%S")
            speak(f"Senhor, agora são {str_time}")
        elif 'tocar' in query:
            tocar(query) 
         
        elif 'aumentar volume' in query:
            aumentar_volume()
        elif 'diminuir volume' in query:
            diminuir_volume()
        elif 'definir' in query and 'volume' in query:
            definir_volume(query)
        elif 'pesquisar' in query:
            pesquisar(query)
        elif 'abrir' in query:
            abrir(query)
        elif 'verificar' in query and 'internet' in query:
            verificar_internet()
        elif 'verificar' in query and 'sistema' in query:
            system_info = get_system_info()
            for key, value in system_info.items():
                print(f'{key}: {value}')
                speak(f'{key}: {value}')
        elif 'ligar as luzes' in query:
            speak("Ligando as luzes.")
        elif 'temperatura' in query :
            buscar_temperatura()
        elif 'escreva' in query:
            escreva(query)
        elif 'iniciar dia' in query:
            start_day()
        elif 'finalizar dia' in query:
            finish_day()
        elif 'parar' in query or 'sair' in query:
            speak("Desativando. Até a próxima.")
            break

