import os
import sys
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import subprocess
import requests
from io import BytesIO
from PIL import Image, ImageTk

# ─── SerpApi setup ───
from serpapi import GoogleSearch
SERPAPI_KEY = "74b486f05569cca2889a9dde1d7453b0defc1590aa2439604f7cd60b525972b8"

# ─── Offline GPT import ───
os.environ["GGML_NO_CUDA"] = "1"             # silence llama.dll noise
from utils.gpt_chat import ask_gpt

def search_with_image(query: str):
    """Return (snippet, thumbnail_url) from SerpApi."""
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
        first  = data.get("organic_results", [{}])[0]
        snippet = first.get("snippet", "")
        thumb   = first.get("thumbnail") or first.get("rich_snippets", {})\
                          .get("top", {})\
                          .get("thumbnail")\
                          .get("img_with_play_button")\
                          if first.get("rich_snippets") else None
        return snippet, thumb
    except Exception as e:
        return f"Search error: {e}", None

def run_chat():
    root = tk.Tk()
    root.title("Mini Chat Interface")
    root.geometry("800x500")

    # — Top: question entry —
    top_frame = tk.Frame(root)
    top_frame.pack(fill=tk.X, pady=5, padx=5)

    question_var = tk.StringVar()
    entry = tk.Entry(top_frame, textvariable=question_var, font=("Arial", 14))
    entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
    entry.focus()

    send_btn = tk.Button(top_frame, text="Send", font=("Arial", 12), command=lambda: send())
    send_btn.pack(side=tk.RIGHT)

    # — Middle: answer and image panes —
    mid_frame = tk.Frame(root)
    mid_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0,5))

    # Left: text answer
    answer_box = ScrolledText(mid_frame, wrap=tk.WORD, font=("Arial", 12))
    answer_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,5))

    # Right: image pane
    img_label = tk.Label(mid_frame, text="No image", font=("Arial", 12), bd=1, relief=tk.SUNKEN)
    img_label.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    def send():
        query = question_var.get().strip()
        if not query:
            return

        # clear previous
        answer_box.configure(state='normal')
        answer_box.insert(tk.END, f"You: {query}\n")
        answer_box.configure(state='disabled')
        question_var.set("")

        # switch back to voice
        if query.lower() == "connect to voice":
            answer_box.configure(state='normal')
            answer_box.insert(tk.END, "Switching to voice mode...\n")
            answer_box.configure(state='disabled')
            root.destroy()
            subprocess.Popen([sys.executable, "mini.py"])
            return

        # decide whether to do factual Google lookup
        if query.lower().startswith(("who is ", "what is ")):
            snippet, thumb = search_with_image(query)
            response = snippet
        else:
            response = ask_gpt(query)
            thumb = None

        # display text
        answer_box.configure(state='normal')
        answer_box.insert(tk.END, f"Mini: {response}\n\n")
        answer_box.configure(state='disabled')
        answer_box.yview(tk.END)

        # display image if any
        if thumb:
            try:
                resp = requests.get(thumb, timeout=5)
                img = Image.open(BytesIO(resp.content))
                img.thumbnail((300, 300))
                photo = ImageTk.PhotoImage(img)
                img_label.configure(image=photo, text="")
                img_label.image = photo
            except Exception:
                img_label.configure(text="Image load failed", image="")
                img_label.image = None
        else:
            img_label.configure(text="No image", image="")
            img_label.image = None

    root.mainloop()

if __name__ == "__main__":
    run_chat()
