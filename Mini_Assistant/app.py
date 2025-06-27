import os
import contextlib
import requests
import cv2
import numpy as np
import base64
from flask import Flask, render_template, request, jsonify

# ─── Silence llama.cpp CUDA‐DLL noise ───
os.environ["GGML_NO_CUDA"] = "1"

# ─── Your SerpApi key ───
SERPAPI_KEY = "74b486f05569cca2889a9dde1d7453b0defc1590aa2439604f7cd60b525972b8"

# ─── GPT4All import (hide stderr) ───
_err = open(os.devnull, "w")
with contextlib.redirect_stderr(_err):
    from utils.gpt_chat import ask_gpt
_err.close()

# ─── Object-detect helper ───
from utils.object_detect import detect_image

app = Flask(__name__, static_folder="static", template_folder="templates")


def fetch_first_google_image(query: str) -> str | None:
    try:
        resp = requests.get(
            "https://serpapi.com/search.json",
            params={
                "engine": "google_images",
                "q": query,
                "api_key": SERPAPI_KEY,
                "num": 1
            },
            timeout=10
        ).json()
        imgs = resp.get("images_results", []) or []
        return imgs[0].get("original") if imgs else None
    except:
        return None


def search_with_image(query: str) -> tuple[str, str | None]:
    try:
        resp = requests.get(
            "https://serpapi.com/search.json",
            params={
                "engine": "google",
                "q": query,
                "hl": "en",
                "api_key": SERPAPI_KEY,
                "num": 1
            },
            timeout=10
        ).json()
    except:
        return "Sorry, search failed.", None

    # 1) Knowledge Graph
    kg   = resp.get("knowledge_graph", {}) or {}
    desc = kg.get("description")
    img  = kg.get("thumbnail_url") or kg.get("image")
    if desc:
        return desc, img or fetch_first_google_image(query)

    # 2) Featured snippet
    ab   = resp.get("answer_box", {}) or {}
    ans  = ab.get("answer")
    img2 = ab.get("image")
    if ans:
        return ans, img2 or fetch_first_google_image(query)

    # 3) Organic snippet
    first   = (resp.get("organic_results") or [{}])[0]
    snippet = first.get("snippet","")
    thumb   = first.get("thumbnail")
    if snippet:
        return snippet, thumb or fetch_first_google_image(query)

    # 4) fallback
    return "", fetch_first_google_image(query)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/ask", methods=["POST"])
def ask():
    try:
        q = request.json.get("query","").strip()
        if not q:
            return jsonify(answer="Type something.", image=None, play_music=False)

        lc = q.lower()
        if "play music" in lc:
            return jsonify(
                answer="Playing music now!",
                image=None,
                play_music=True,
                stream_url="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"
            )

        if lc.startswith(("who is ","what is ")):
            answer, image = search_with_image(q)
        else:
            answer, image = ask_gpt(q), None

        return jsonify(answer=answer, image=image, play_music=False)
    except Exception:
        return jsonify(answer="Error occurred.", image=None, play_music=False), 500


@app.route("/detect", methods=["POST"])
def detect():
    file = request.files.get("image")
    if not file:
        return jsonify(error="No image"), 400

    data = file.read()
    nparr = np.frombuffer(data, np.uint8)
    img   = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    annotated = detect_image(img)
    success, jpg = cv2.imencode(".jpg", annotated)
    if not success:
        return jsonify(error="Encode failed"), 500

    b64 = base64.b64encode(jpg.tobytes()).decode("utf-8")
    return jsonify(image="data:image/jpeg;base64," + b64)


if __name__ == "__main__":
    print("→ http://127.0.0.1:8000")
    app.run(host="127.0.0.1", port=8000, debug=True, use_reloader=False)
