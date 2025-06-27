import os, sys, contextlib

# ─── Silence llama.cpp CUDA‐DLL noise ───
os.environ["GGML_NO_CUDA"] = "1"

# ─── Core imports (stderr silenced for gpt4all) ───
import pyttsx3
import speech_recognition as sr
import datetime
import wikipedia
import webbrowser
from serpapi import GoogleSearch
from utils.weather import get_weather
from utils.object_detect import detect_objects

# Wrap GPT4All import to hide its stderr noise
_err = open(os.devnull, "w")
with contextlib.redirect_stderr(_err):
    from gpt4all import GPT4All
_err.close()

# ─── Your SerpApi key (hard-coded) ───
SERPAPI_KEY = "74b486f05569cca2889a9dde1d7453b0defc1590aa2439604f7cd60b525972b8"  # ← replace with your actual key

def search_and_summarize(query: str) -> str:
    if not SERPAPI_KEY or "YOUR_SERPAPI_KEY_HERE" in SERPAPI_KEY:
        return "Error: SerpApi key not set."
    params = {
        "engine":  "google",
        "q":       query,
        "hl":      "en",
        "api_key": SERPAPI_KEY,
        "num":     1
    }
    try:
        client = GoogleSearch(params)
        data   = client.get_dict()
        snippet = data.get("organic_results", [{}])[0].get("snippet", "")
        return snippet or "I found no summary in the top result."
    except Exception as e:
        return f"Search error: {e}"

# ─── TTS setup ───
engine = pyttsx3.init()
voices = engine.getProperty("voices")
if len(voices) > 1:
    engine.setProperty("voice", voices[1].id)

def speak(text: str):
    print(f"Mini: {text}")
    engine.say(text)
    engine.runAndWait()

def take_command() -> str:
    r = sr.Recognizer()
    with sr.Microphone() as mic:
        audio = r.listen(mic)
    try:
        query = r.recognize_google(audio, language="en-US")
        print(f"You asked: {query}")
        return query.lower()
    except sr.UnknownValueError:
        return ""
    except Exception as e:
        print(f"Recognition error: {e}")
        return ""

def greet_user():
    hr = datetime.datetime.now().hour
    if hr < 12:
        gm = "Good morning!"
    elif hr < 18:
        gm = "Good afternoon!"
    else:
        gm = "Good evening!"
    print(f"Mini: {gm} I am Mini. How can I help you today?")
    engine.say(f"{gm} I am Mini. How can I help you today?")
    engine.runAndWait()

def main():
    # Load GPT4All CPU model
    model_path = os.path.abspath("models/gpt4all-13b-snoozy-q4_0.gguf")
    gpt = GPT4All(model_path, allow_download=False, device="cpu")

    greet_user()
    while True:
        query = take_command()
        if not query:
            continue

        # 1) “who is …?” → Wikipedia (2 sentences)
        if query.startswith("who is "):
            term = query.replace("who is ", "").strip()
            try:
                ans = wikipedia.summary(term, sentences=2)
            except Exception:
                ans = search_and_summarize(query)
            speak(ans)

        # 2) Generic Wikipedia lookup
        elif "wikipedia" in query:
            topic = query.replace("wikipedia", "").strip()
            try:
                ans = wikipedia.summary(topic, sentences=2)
            except Exception as e:
                ans = f"Wikipedia error: {e}"
            speak(ans)

        # 3) Open YouTube / Google
        elif "open youtube" in query:
            webbrowser.open("https://youtube.com")
            speak("Opened YouTube.")
        elif "open google" in query:
            webbrowser.open("https://google.com")
            speak("Opened Google.")

        # 4) Weather
        elif "weather" in query:
            speak("Which city?")
            city = take_command()
            if city:
                report = get_weather(city)
                speak(report)

        # 5) Object detection
        elif "identify object" in query:
            speak("Identifying object now.")
            detect_objects()

        # 6) Time
        elif "time" in query:
            now = datetime.datetime.now().strftime("%H:%M:%S")
            speak(f"The time is {now}")

        # 7) GPT chat/jokes/etc.
        elif any(k in query for k in ["joke", "funny", "talk", "chat", "story"]):
            resp = gpt.generate(prompt=query)
            speak(resp)

        # 8) Connect to chat interface
        elif "connect to chat" in query:
            speak("Switching to chat mode")
            import subprocess
            subprocess.Popen([sys.executable, "chat_ui.py"])
            break

        # 9) Exit
        elif query in ("exit", "quit", "stop"):
            speak("Goodbye!")
            break

        # 10) Fallback → Google via SerpApi
        else:
            ans = search_and_summarize(query)
            speak(ans)

if __name__ == "__main__":
    main()
