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
GROUP = int(os.environ.get("GROUP", "6"))
CATS = [c.strip() for c in os.environ.get("CATEGORIES", "").split(",") if c.strip()]
PRIORITY_ONLY = os.environ.get("PRIORITY_ONLY", "0") == "1"
MOCK = os.environ.get("MOCK", "0") == "1"          # MOCK=1: ve hinh don gian de test he thong
GEN = int(os.environ.get("GEN_SIZE", "512"))        # kich thuoc model sinh
OUT = int(os.environ.get("OUT_SIZE", "256"))        # kich thuoc luu kho (>=128)
STEPS = int(os.environ.get("STEPS", "2"))
MODEL = os.environ.get("MODEL_ID", "stabilityai/sd-turbo")
MODEL_NAME = os.environ.get("MODEL_NAME", "")
if not MODEL_NAME:
    m_low = MODEL.lower()
    if "turbo" in m_low: MODEL_NAME = "SD-Turbo"
    elif "tiny" in m_low: MODEL_NAME = "Tiny-SD"
    elif "lcm" in m_low: MODEL_NAME = "LCM-Dreamshaper"
    elif "bk-sdm" in m_low: MODEL_NAME = "BK-SDM"
    else: MODEL_NAME = MODEL.split("/")[-1][:12]
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
    """Tạo ảnh đồ họa Neon Sign sắc nét trên nền tối sâu thẳm."""
    rnd = random.Random(int(hashlib.md5(name.encode()).hexdigest(), 16))
    
    # Nền tối sâu chuẩn bảng màu Cyber-Neon
    im = Image.new("RGB", (GEN, GEN), (8, 10, 16))
    d = ImageDraw.Draw(im)
    
    # Bảng màu Neon rực rỡ
    NEON_COLORS = [
        (0, 243, 255),   # Neon Cyan
        (255, 0, 128),   # Neon Magenta
        (0, 255, 136),   # Neon Green
        (255, 187, 0),   # Neon Amber
        (170, 70, 255)   # Neon Purple
    ]
    primary_col = rnd.choice(NEON_COLORS)
    secondary_col = rnd.choice(NEON_COLORS)
    
    # Khung viền phát quang đôi
    d.rectangle([16, 16, GEN-16, GEN-16], outline=tuple(c//4 for c in primary_col), width=3)
    d.rectangle([20, 20, GEN-20, GEN-20], outline=primary_col, width=2)
    
    # Vẽ biểu tượng neon trung tâm
    cx, cy = GEN // 2, GEN // 2 - 20
    r = rnd.randint(70, 110)
    
    d.ellipse([cx-r, cy-r, cx+r, cy+r], outline=primary_col, width=5)
    d.ellipse([cx-r+8, cy-r+8, cx+r-8, cy+r-8], outline=(255, 255, 255), width=2)
    
    # Chi tiết phát sáng bên trong
    d.line([(cx-r+30, cy), (cx+r-30, cy)], fill=secondary_col, width=4)
    d.line([(cx, cy-r+30), (cx, cy+r-30)], fill=secondary_col, width=4)
    
    # Tên bách khoa neon
    d.text((32, GEN - 48), name.upper(), fill=primary_col)
    d.text((32, GEN - 28), "ENCYCLOPEDIA NEON PLATE", fill=(120, 140, 170))
    
    return im


def generate(name):
    if MOCK:
        raw = mock_image(name)
    else:
        pipe = get_pipe()
        prompt = prompt_for(GROUP, name)
        m_low = MODEL.lower()
        if "turbo" in m_low:
            raw = pipe(prompt=prompt, num_inference_steps=STEPS, guidance_scale=0.0, width=GEN, height=GEN).images[0]
        elif "lcm" in m_low:
            raw = pipe(prompt=prompt, num_inference_steps=max(2, STEPS), guidance_scale=1.5, width=GEN, height=GEN).images[0]
        else:
            raw = pipe(prompt=prompt, num_inference_steps=max(4, STEPS), guidance_scale=2.0, width=GEN, height=GEN).images[0]
    return postprocess(GROUP, raw, OUT)


def main():
    log(f"khoi dong | model: {MODEL_NAME} ({MODEL}) | phong cach: {STYLES[GROUP][0]} | danh muc: {CATS or 'tat ca'} | uu tien-only: {PRIORITY_ONLY} | mock: {MOCK}")
    notify(f"AI {WID} online", f"Style {STYLES[GROUP][0]}, cats={CATS or 'all'}", "robot")
    if not MOCK:
        t = time.time()
        get_pipe()
        notify(f"AI {WID} san sang", f"Da tai model xong sau {time.time()-t:.0f}s, bat dau ve anh", "white_check_mark")
    done = 0
    while True:
        try:
            r = requests.post(API + "/api/worker/claim", headers=H, timeout=15,
                              json={"worker_id": WID, "model_name": MODEL_NAME, "categories": CATS, "priority_only": PRIORITY_ONLY})
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
