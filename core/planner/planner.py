"""Module PLANNER: giu hang doi job nen luon day, chia chu de theo danh muc cho cac AI.
Neu co OLLAMA_URL thi nho LLM nho de xuat them chu de; khong co thi dung bang tu dien."""
import os, random, time
import threading
import requests
from topics import NOUNS, COLORS

API = os.environ.get("API_URL", "http://api:8000").rstrip("/")
H = {"X-Token": os.environ.get("WORKER_TOKEN", "change-me")}
MIN_BACKLOG = int(os.environ.get("MIN_BACKLOG", "6"))   # moi danh muc
BATCH = int(os.environ.get("BATCH", "8"))
NTFY = os.environ.get("NTFY_URL", "")
BARK = os.environ.get("BARK_URL", "")
OLLAMA = os.environ.get("OLLAMA_URL", "")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:1.5b")


def notify(title, msg, tags=""):
    def _s():
        if NTFY:
            try: requests.post(NTFY, data=msg.encode(), headers={"Title": title, "Tags": tags}, timeout=4)
            except Exception: pass
        if BARK:
            try: requests.post(BARK.rstrip("/"), json={"title": title, "body": msg, "group": "kho-anh"}, timeout=4)
            except Exception: pass
    threading.Thread(target=_s, daemon=True).start()


def llm_nouns(cat):
    if not OLLAMA:
        return []
    try:
        r = requests.post(OLLAMA.rstrip("/") + "/api/generate", timeout=60, json={
            "model": OLLAMA_MODEL, "stream": False,
            "prompt": f"List 15 simple English nouns for an encyclopedia about '{cat}'. One or two words each, one per line, no numbering."})
        return [l.strip().lower() for l in r.json()["response"].splitlines() if 0 < len(l.strip()) < 25]
    except Exception as e:
        print("ollama loi:", e)
        return []


def make_names(cat, n):
    pool = NOUNS[cat] + llm_nouns(cat)
    out = set()
    while len(out) < n:
        noun = random.choice(pool).replace("-", " ")
        out.add(f"{random.choice(COLORS)} {noun}" if random.random() < 0.6 else noun)
    return list(out)


notify("Planner online", "Planner bat dau lap ke hoach chu de", "brain")
while True:
    try:
        pending = requests.get(API + "/api/planner/backlog", headers=H, timeout=10).json()["pending"]
        for cat in NOUNS:
            if pending.get(cat, 0) < MIN_BACKLOG:
                items = [{"name": n, "category": cat} for n in make_names(cat, BATCH)]
                added = requests.post(API + "/api/planner/queue", headers=H, json={"items": items}, timeout=10).json()["added"]
                print(f"[planner] {cat}: +{added} job")
                if added:
                    notify("Planner", f"Them {added} chu de moi cho danh muc '{cat}': " + ", ".join(i["name"] for i in items[:4]) + "...", "memo")
    except Exception as e:
        print("[planner] loi:", e)
        notify("Planner loi", str(e)[:200], "warning")
    time.sleep(15)
