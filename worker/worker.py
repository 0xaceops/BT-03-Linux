"""Module AI WORKER: xin job tu API -> AI local ve anh -> gui anh ve API.
Ten AI = <MEMBER_ID>.<AI_NO>, vd 2.1. Chay hoan toan local (khong dung AI API)."""
import hashlib, io, os, random, threading, time, traceback
import requests
from PIL import Image, ImageDraw
from styles import STYLES, prompt_for, postprocess

API = os.environ.get("API_URL", "http://localhost:8000").rstrip("/")
TOKEN = os.environ.get("WORKER_TOKEN", "change-me")
MEMBER = os.environ["MEMBER_ID"]
AI_NO = os.environ.get("AI_NO", "1")
WID = f"{MEMBER}.{AI_NO}"
GROUP = int(os.environ.get("GROUP", "1"))
CATS = [c.strip() for c in os.environ.get("CATEGORIES", "").split(",") if c.strip()]
PRIORITY_ONLY = os.environ.get("PRIORITY_ONLY", "0") == "1"
MOCK = os.environ.get("MOCK", "0") == "1"          # MOCK=1: ve hinh don gian de test he thong
GEN = int(os.environ.get("GEN_SIZE", "512"))        # kich thuoc model sinh
OUT = int(os.environ.get("OUT_SIZE", "256"))        # kich thuoc luu kho (>=128)
STEPS = int(os.environ.get("STEPS", "2"))
MODEL = os.environ.get("MODEL_ID", "stabilityai/sd-turbo")
NTFY = os.environ.get("NTFY_URL", "")
BARK = os.environ.get("BARK_URL", "")
H = {"X-Token": TOKEN}


def notify(title, msg, tags=""):
    def _s():
        if NTFY:
            try: requests.post(NTFY, data=msg.encode(), headers={"Title": title, "Tags": tags}, timeout=4)
            except Exception: pass
        if BARK:
            try: requests.post(BARK.rstrip("/"), json={"title": title, "body": msg, "group": "kho-anh"}, timeout=4)
            except Exception: pass
    threading.Thread(target=_s, daemon=True).start()


def log(*a):
    print(f"[AI {WID}]", *a, flush=True)


_pipe = None


def get_pipe():
    global _pipe
    if _pipe is None:
        import torch
        from diffusers import AutoPipelineForText2Image
        torch.set_num_threads(os.cpu_count() or 4)
        log("tai model", MODEL, "(lan dau se hoi lau)")
        _pipe = AutoPipelineForText2Image.from_pretrained(MODEL, torch_dtype=torch.float32)
        _pipe.set_progress_bar_config(disable=True)
    return _pipe


def mock_image(name):
    rnd = random.Random(int(hashlib.md5(name.encode()).hexdigest(), 16))
    im = Image.new("RGB", (GEN, GEN), tuple(rnd.randint(150, 255) for _ in range(3)))
    d = ImageDraw.Draw(im)
    for _ in range(6):
        x, y = rnd.randint(0, GEN - 120), rnd.randint(0, GEN - 120)
        s = rnd.randint(60, 220)
        box = (x, y, x + s, y + s)
        col = tuple(rnd.randint(0, 255) for _ in range(3))
        d.ellipse(box, fill=col) if rnd.random() < .5 else d.rectangle(box, fill=col)
    d.text((12, GEN - 24), name, fill=(0, 0, 0))
    return im


def generate(name):
    if MOCK:
        raw = mock_image(name)
    else:
        raw = get_pipe()(prompt=prompt_for(GROUP, name), num_inference_steps=STEPS,
                         guidance_scale=0.0, width=GEN, height=GEN).images[0]
    return postprocess(GROUP, raw, OUT)


def main():
    log(f"khoi dong | phong cach: {STYLES[GROUP][0]} | danh muc: {CATS or 'tat ca'} | uu tien-only: {PRIORITY_ONLY} | mock: {MOCK}")
    notify(f"AI {WID} online", f"Style {STYLES[GROUP][0]}, cats={CATS or 'all'}", "robot")
    if not MOCK:
        t = time.time()
        get_pipe()
        notify(f"AI {WID} san sang", f"Da tai model xong sau {time.time()-t:.0f}s, bat dau ve anh", "white_check_mark")
    done = 0
    while True:
        try:
            r = requests.post(API + "/api/worker/claim", headers=H, timeout=15,
                              json={"worker_id": WID, "categories": CATS, "priority_only": PRIORITY_ONLY})
            r.raise_for_status()
            job = r.json()["job"]
        except Exception as e:
            log("khong lien lac duoc API:", e)
            time.sleep(10)
            continue
        if not job:
            time.sleep(3)
            continue
        t0 = time.time()
        try:
            im = generate(job["name"])
            buf = io.BytesIO()
            im.save(buf, "PNG")
            up = requests.post(API + "/api/worker/complete", headers=H, timeout=60,
                               data={"job_id": job["id"], "worker_id": WID},
                               files={"file": ("x.png", buf.getvalue(), "image/png")})
            up.raise_for_status()
            done += 1
            log(f"xong '{job['name']}' trong {time.time()-t0:.1f}s (tong {done})")
            if done % 50 == 0:
                notify(f"AI {WID} moc {done} anh", f"AI {WID} da ve {done} anh, anh gan nhat: {job['name']} ({time.time()-t0:.0f}s/anh)", "tada")
        except Exception as e:
            log("loi:", e)
            traceback.print_exc()
            notify(f"AI {WID} loi", f"job '{job['name']}': {str(e)[:200]}", "warning")
            try:
                requests.post(API + "/api/worker/fail", headers=H, timeout=10,
                              json={"job_id": job["id"], "worker_id": WID, "error": str(e)})
            except Exception:
                pass
            time.sleep(5)


if __name__ == "__main__":
    main()
