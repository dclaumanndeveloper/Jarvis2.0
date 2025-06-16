import os
# Ensure Tcl/Tk library paths are set for Windows venv
os.environ['TCL_LIBRARY'] = r"C:\Users\diego\AppData\Local\Programs\Python\Python313\tcl\tcl8.6"
os.environ['TK_LIBRARY'] = r"C:\Users\diego\AppData\Local\Programs\Python\Python313\tcl\tk8.6"

import threading
import tkinter as tk
import speech_recognition as sr
import pyttsx3
import time
from PIL import Image, ImageTk
from PIL import ImageSequence
root = tk.Tk()

bg_img_path = os.path.join(os.path.dirname(__file__), "interface_bg.webp")
bg_img = Image.open(bg_img_path).resize((600, 400))
bg_photo = ImageTk.PhotoImage(bg_img)
bg_label = tk.Label(root, image=bg_photo, borderwidth=0)
bg_label.image = bg_photo
bg_label.place(x=0, y=0, relwidth=1, relheight=1)

root.overrideredirect(False)           # False para manter bordas; True remove bordas
root.attributes('-topmost', True)      # Sempre no topo
root.attributes('-alpha', 0.95)        # Leve transparência

GLOW = "#00FF41"
FONT_BIG = ("OCR A Extended", 14)
FONT_SM = ("OCR A Extended", 12)



engine = pyttsx3.init()
engine.setProperty('rate', 150)  # velocidade da fala
engine.setProperty('voice', 'brazil')  # ou outro id de voz disponível

def speak(text):
    engine.say(text)
    engine.runAndWait()

def listen_and_respond():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
    while True:
        try:
            with mic as source:
                status_label.config(text="Ouvindo...")
                audio = recognizer.listen(source, timeout=5)
            text = recognizer.recognize_google(audio, language='pt-BR')
            append_chat("Você: " + text)
            response = f"Você disse: {text}"
            append_chat("Jarvis: " + response)
            speak(response)
        except sr.WaitTimeoutError:
            continue
        except sr.UnknownValueError:
            append_chat("Jarvis: Desculpe, não entendi.")
            speak("Desculpe, não entendi.")
        except Exception as e:
            append_chat(f"Erro: {e}")
            time.sleep(1)

def append_chat(msg):
    chat_text.config(state='normal')
    chat_text.insert('end', msg + '\n')
    chat_text.config(state='disabled')
    chat_text.see('end')

root.title("Jarvis Voice Assistant")
root.geometry("600x400")
root.configure(bg='black')

status_label = tk.Label(root, text="Inicializando...", font=("Consolas", 12), fg="lime", bg="black")
status_label.pack(pady=5)

chat_frame = tk.Frame(root, bg="black")
chat_frame.pack(expand=True, fill='both', padx=10, pady=10)

chat_text = tk.Text(chat_frame, state='disabled', bg="black", fg=GLOW, font=FONT_SM, wrap='word')



gif_path = os.path.join(os.path.dirname(__file__), "jarvis.gif")
if os.path.exists(gif_path):
    gif = Image.open(gif_path)
    frames = [
        ImageTk.PhotoImage(frame.copy().resize((600, 400)))
        for frame in ImageSequence.Iterator(gif)
    ]
    anim_label = tk.Label(root, bg="black")
    anim_label.place(x=0, y=0, relwidth=1, relheight=1)

    def animate(idx=0):
        anim_label.config(image=frames[idx])
        duration = gif.info.get("duration", 100)
        root.after(duration, lambda: animate((idx + 1) % len(frames)))

    root.after(0, animate)
    root.after(3000, anim_label.destroy)

chat_text.pack(side='left', expand=True, fill='both')

scrollbar = tk.Scrollbar(
    chat_frame,
    command=chat_text.yview,
    bg='black', troughcolor='black', activebackground=GLOW, highlightthickness=0
)
scrollbar.pack(side='right', fill='y')
chat_text['yscrollcommand'] = scrollbar.set

status_label.config(text="Pronto para ouvir...")

# start voice recognition in background thread
threading.Thread(target=listen_and_respond, daemon=True).start()
root.mainloop()