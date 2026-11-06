"""Module WEB/API: trang chu, tim kiem, hang doi job, nhan anh tu worker."""
import io, math, os, re, time, threading
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import quote

import psycopg2, psycopg2.extras, requests
from psycopg2.pool import ThreadedConnectionPool
from PIL import Image
from fastapi import FastAPI, HTTPException, Header, UploadFile, File, Form, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

DB_URL = os.environ["DATABASE_URL"]
TOKEN = os.environ.get("WORKER_TOKEN", "change-me")
NTFY = os.environ.get("NTFY_URL", "")
NOTIFY_EVERY = int(os.environ.get("NOTIFY_EVERY", "1"))   # 1 = bao moi anh moi
BARK = os.environ.get("BARK_URL", "")                     # vd https://api.day.app/KEY_CUA_BAN
OFFLINE_SEC = int(os.environ.get("OFFLINE_SEC", "300"))
SUMMARY_MIN = float(os.environ.get("SUMMARY_MIN", "10"))
IMG_DIR = Path(os.environ.get("IMG_DIR", "/data/images"))
IMG_DIR.mkdir(parents=True, exist_ok=True)

SCHEMA = """
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE TABLE IF NOT EXISTS images(
  id SERIAL PRIMARY KEY, name TEXT NOT NULL, filename TEXT UNIQUE NOT NULL,
  ai_id TEXT NOT NULL, category TEXT, source TEXT DEFAULT 'auto',
  created_at TIMESTAMPTZ DEFAULT now());
CREATE INDEX IF NOT EXISTS images_created ON images(created_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS images_name_trgm ON images USING gin (name gin_trgm_ops);
CREATE TABLE IF NOT EXISTS jobs(
  id SERIAL PRIMARY KEY, name TEXT NOT NULL, category TEXT DEFAULT 'user',
  priority INT DEFAULT 0, status TEXT DEFAULT 'pending', claimed_by TEXT,
  tries INT DEFAULT 0, image_id INT, created_at TIMESTAMPTZ DEFAULT now(),
  started_at TIMESTAMPTZ);
CREATE INDEX IF NOT EXISTS jobs_status ON jobs(status, priority DESC, id);
CREATE TABLE IF NOT EXISTS workers(ai_id TEXT PRIMARY KEY, last_seen TIMESTAMPTZ DEFAULT now());
"""

pool = None
_counter = {"n": 0}


def notify(title, msg, tags="", prio=3):
    """Gui log len dien thoai qua ntfy va/hoac Bark (khong chan luong chinh)."""
    if not NTFY and not BARK:
        return
    def _send():
        if NTFY:
            try:
                requests.post(NTFY, data=msg.encode("utf-8"), timeout=4,
                              headers={"Title": title, "Tags": tags, "Priority": str(prio)})
            except Exception:
                pass
        if BARK:
            try:
                requests.post(BARK.rstrip("/"), json={"title": title, "body": msg, "group": "kho-anh"}, timeout=4)
            except Exception:
                pass
    threading.Thread(target=_send, daemon=True).start()


def watchdog():
    """Bao khi mot AI offline/online lai + tong ket dinh ky len dien thoai."""
    state, last_sum = {}, time.time()
    while True:
        time.sleep(30)
        try:
            with cur() as c:
                c.execute("SELECT ai_id, extract(epoch from now()-last_seen) age FROM workers")
                for r in c.fetchall():
                    off = r["age"] > OFFLINE_SEC
                    prev = state.get(r["ai_id"])
                    if (prev is None and off) or (prev is not None and prev != off):
                        notify(f"AI {r['ai_id']} " + ("OFFLINE" if off else "online lai"),
                               f"AI {r['ai_id']} " + (f"mat ket noi {int(r['age'])}s" if off else "da hoat dong tro lai"),
                               "rotating_light" if off else "white_check_mark", 5 if off else 3)
                    state[r["ai_id"]] = off
                if time.time() - last_sum > SUMMARY_MIN * 60:
                    last_sum = time.time()
                    c.execute("SELECT ai_id, count(*) n FROM images GROUP BY ai_id ORDER BY ai_id")
                    per = ", ".join(f"{r['ai_id']}:{r['n']}" for r in c.fetchall()) or "chua co"
                    c.execute("SELECT count(*) n FROM jobs WHERE status IN ('pending','running')")
                    pend = c.fetchone()["n"]
                    online = sum(1 for v in state.values() if not v)
                    notify("Tong ket he thong", f"AI online: {online}/{len(state)} | job cho: {pend} | anh theo AI: {per}", "bar_chart")
        except Exception as e:
            print("watchdog loi:", e)


@contextmanager
def cur():
    conn = pool.getconn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            yield c
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


_startup_time = time.time()

MEMBERS = {
    "1": os.environ.get("MEMBER_NAME_1", "Nhóm trưởng"),
    "2": os.environ.get("MEMBER_NAME_2", "Trương Từ Long"),
    "3": os.environ.get("MEMBER_NAME_3", "Thành viên 3"),
    "4": os.environ.get("MEMBER_NAME_4", "Thành viên 4"),
    "5": os.environ.get("MEMBER_NAME_5", "Thành viên 5"),
}

if os.environ.get("MEMBER_NAMES"):
    for pair in os.environ["MEMBER_NAMES"].split(","):
        if ":" in pair:
            mid, mname = pair.split(":", 1)
            MEMBERS[mid.strip()] = mname.strip()


def format_ago(seconds):
    if seconds is None:
        return "-"
    seconds = max(0, int(seconds))
    if seconds < 60:
        return f"{seconds} giây trước"
    if seconds < 3600:
        return f"{seconds // 60} phút trước"
    if seconds < 86400:
        return f"{seconds // 3600} giờ trước"
    return f"{seconds // 86400} ngày trước"


def clean(s):
    s = re.sub(r"[^a-z0-9 ]+", " ", (s or "").lower())
    return " ".join(s.split()[:6])[:60] or "mystery object"


def img_json(r):
    created = r["created_at"]
    return {
        "id": r["id"],
        "name": r["name"],
        "title": r["name"].title(),
        "filename": r["filename"],
        "url": "/images/" + quote(r["filename"]),
        "ai_id": r["ai_id"],
        "created_at": created.isoformat(),
        "created_fmt": created.strftime("%d/%m %H:%M")
    }


def auth(x_token: str = Header(default="")):
    if x_token != TOKEN:
        raise HTTPException(401, "bad token")


app = FastAPI(title="Kho anh bach khoa")


@app.on_event("startup")
def startup():
    global pool
    for i in range(40):
        try:
            pool = ThreadedConnectionPool(1, 10, DB_URL)
            with cur() as c:
                c.execute(SCHEMA)
            break
        except Exception as e:
            print("cho database...", e)
            time.sleep(3)
    else:
        raise RuntimeError("khong ket noi duoc database")
    notify("API started", "Web/API da khoi dong", "rocket")
    threading.Thread(target=watchdog, daemon=True).start()


@app.get("/health")
def health():
    with cur() as c:
        c.execute("SELECT 1")
    return {"ok": True}


@app.get("/api/latest")
def latest(page: int = 1, limit: int = 50):
    """Lấy danh sách ảnh trang chủ có hỗ trợ phân trang (50 ảnh/trang, mới nhất lên đầu)."""
    page = max(1, page)
    limit = min(max(1, limit), 100)
    offset = (page - 1) * limit
    with cur() as c:
        c.execute("SELECT count(*) as total FROM images")
        total = c.fetchone()["total"]
        total_pages = math.ceil(total / limit) if total > 0 else 1

        c.execute("""
            SELECT * FROM images 
            ORDER BY created_at DESC, id DESC 
            LIMIT %s OFFSET %s
        """, (limit, offset))
        rows = c.fetchall()

        return {
            "images": [img_json(r) for r in rows],
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": total_pages
        }


@app.get("/api/search")
def search(q: str):
    name = clean(q)
    pats = [f"%{w}%" for w in name.split()]
    with cur() as c:
        c.execute("""SELECT *, similarity(name,%s) AS sim FROM images
                     WHERE name ILIKE ALL(%s) OR similarity(name,%s) > 0.5
                     ORDER BY (name=%s) DESC, sim DESC, id DESC LIMIT 50""",
                  (name, pats, name, name))
        rows = c.fetchall()
        if rows:
            return {"status": "found", "query": name, "images": [img_json(r) for r in rows]}
        # Khong co anh -> tao job uu tien cao (khong bao gio tra "khong co ket qua")
        c.execute("SELECT id FROM jobs WHERE name=%s AND status IN ('pending','running') ORDER BY id LIMIT 1", (name,))
        j = c.fetchone()
        if j:
            c.execute("UPDATE jobs SET priority=100 WHERE id=%s AND status='pending'", (j["id"],))
            jid = j["id"]
        else:
            c.execute("INSERT INTO jobs(name,category,priority) VALUES(%s,'user',100) RETURNING id", (name,))
            jid = c.fetchone()["id"]
    notify("User search", f"Nguoi dung tim '{name}': kho chua co -> job uu tien #{jid}", "mag", 4)
    return {"status": "generating", "query": name, "job_id": jid}


@app.get("/api/job/{job_id}")
def job(job_id: int):
    with cur() as c:
        c.execute("SELECT * FROM jobs WHERE id=%s", (job_id,))
        j = c.fetchone()
        if not j:
            raise HTTPException(404)
        if j["status"] == "done" and j["image_id"]:
            c.execute("SELECT * FROM images WHERE id=%s", (j["image_id"],))
            return {"status": "done", "image": img_json(c.fetchone())}
        return {"status": j["status"]}


@app.get("/api/stats")
def stats():
    with cur() as c:
        # Total counts by ai_id
        c.execute("""
            SELECT ai_id, 
                   count(*) as n, 
                   count(*) FILTER (WHERE created_at > now() - interval '60 minutes') as n_60m,
                   max(created_at) as last_created,
                   extract(epoch from now() - max(created_at)) as last_created_age
            FROM images GROUP BY ai_id
        """)
        ai_data = {}
        for r in c.fetchall():
            ai_data[r["ai_id"]] = {
                "ai_id": r["ai_id"],
                "count": r["n"],
                "count_60m": r["n_60m"],
                "last_created": r["last_created"].strftime("%d/%m %H:%M") if r["last_created"] else "-",
                "last_created_ago": format_ago(r["last_created_age"]) if r["last_created"] else "-",
                "last_seen_age": None
            }

        # Workers heartbeat
        c.execute("SELECT ai_id, last_seen, extract(epoch from now()-last_seen) age FROM workers")
        for r in c.fetchall():
            d = ai_data.setdefault(r["ai_id"], {
                "ai_id": r["ai_id"], "count": 0, "count_60m": 0,
                "last_created": "-", "last_created_ago": "-", "last_seen_age": None
            })
            d["last_seen_age"] = r["age"]

        # Sort AI by (member_id, ai_no)
        key = lambda a: tuple(int(x) for x in a["ai_id"].split("."))
        sorted_ais = sorted(ai_data.values(), key=key)

        # Build by_ai list
        by_ai = []
        for a in sorted_ais:
            mid = a["ai_id"].split(".")[0]
            is_online = (a["last_seen_age"] is not None and a["last_seen_age"] <= OFFLINE_SEC)
            by_ai.append({
                "ai_code": a["ai_id"],
                "member_name": MEMBERS.get(mid, f"Thành viên {mid}"),
                "model": "SD-Turbo (Neon)",
                "count": a["count"],
                "count_60m": a["count_60m"],
                "last_image": f"{a['last_created']} · {a['last_created_ago']}" if a["last_created"] != "-" else "-",
                "status": "ONLINE" if is_online else "OFFLINE"
            })

        # Build by_member list (aggregated by member)
        member_groups = {}
        for a in sorted_ais:
            mid = a["ai_id"].split(".")[0]
            m = member_groups.setdefault(mid, {
                "member_name": MEMBERS.get(mid, f"Thành viên {mid}"),
                "slots_total": 0,
                "slots_online": 0,
                "count": 0,
                "count_60m": 0,
                "last_created": "-",
                "last_created_ago": "-",
                "min_age": 999999999
            })
            m["slots_total"] += 1
            if a["last_seen_age"] is not None and a["last_seen_age"] <= OFFLINE_SEC:
                m["slots_online"] += 1
            m["count"] += a["count"]
            m["count_60m"] += a["count_60m"]
            if a["last_created"] != "-":
                m["last_created"] = a["last_created"]
                m["last_created_ago"] = a["last_created_ago"]

        by_member = []
        for mid in sorted(member_groups.keys(), key=lambda x: int(x)):
            m = member_groups[mid]
            by_member.append({
                "member_name": m["member_name"],
                "slot_ai": f"{m['slots_total']} ({m['slots_online']} on)",
                "count": m["count"],
                "count_60m": m["count_60m"],
                "last_image": f"{m['last_created']} · {m['last_created_ago']}" if m["last_created"] != "-" else "-"
            })

        # Summary figures
        c.execute("""
            SELECT count(*) as total,
                   count(*) FILTER (WHERE created_at > now() - interval '60 minutes') as total_60m,
                   count(*) FILTER (WHERE created_at > now() - interval '24 hours') as total_24h,
                   min(created_at) as first_created,
                   max(created_at) as last_created,
                   extract(epoch from now() - max(created_at)) as last_age
            FROM images
        """)
        img_stats = c.fetchone()

        c.execute("""
            SELECT count(*) as total_jobs,
                   count(*) FILTER (WHERE status='running') as running_jobs,
                   count(*) FILTER (WHERE status='done') as done_jobs,
                   count(*) FILTER (WHERE status='pending') as pending_jobs
            FROM jobs
        """)
        job_stats = c.fetchone()

        opened_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(_startup_time))
        if img_stats and img_stats["first_created"]:
            opened_time = img_stats["first_created"].strftime("%Y-%m-%d %H:%M:%S")

        summary = {
            "total_images": (img_stats["total"] if img_stats else 0) or 0,
            "total_60m": (img_stats["total_60m"] if img_stats else 0) or 0,
            "total_24h": (img_stats["total_24h"] if img_stats else 0) or 0,
            "running_jobs": (job_stats["running_jobs"] if job_stats else 0) or 0,
            "done_jobs": (job_stats["done_jobs"] if job_stats else 0) or 0,
            "pending_jobs": (job_stats["pending_jobs"] if job_stats else 0) or 0,
            "total_jobs": (job_stats["total_jobs"] if job_stats else 0) or 0,
            "opened_time": opened_time,
            "last_image_ago": format_ago(img_stats["last_age"]) if (img_stats and img_stats["last_created"]) else "chưa có"
        }

    return {"by_ai": by_ai, "by_member": by_member, "summary": summary}


# ---------------- API cho worker / planner ----------------
class Claim(BaseModel):
    worker_id: str
    categories: list[str] = []
    priority_only: bool = False


@app.post("/api/worker/claim", dependencies=[Depends(auth)])
def claim(b: Claim):
    if not re.fullmatch(r"\d+\.\d+", b.worker_id):
        raise HTTPException(400, "worker_id phai dang 2.1")
    with cur() as c:
        c.execute("""INSERT INTO workers(ai_id) VALUES(%s)
                     ON CONFLICT (ai_id) DO UPDATE SET last_seen=now()""", (b.worker_id,))
        c.execute("UPDATE jobs SET status='pending' WHERE status='running' AND started_at < now()-interval '5 minutes'")
        c.execute("""UPDATE jobs SET status='running', claimed_by=%(w)s, started_at=now()
            WHERE id=(SELECT id FROM jobs WHERE status='pending'
                AND (NOT %(po)s OR priority>=10)
                AND (priority>=10 OR cardinality(%(cats)s::text[])=0 OR category=ANY(%(cats)s::text[]))
                ORDER BY priority DESC, id FOR UPDATE SKIP LOCKED LIMIT 1)
            RETURNING id, name, category, priority""",
                  {"w": b.worker_id, "po": b.priority_only, "cats": b.categories})
        j = c.fetchone()
    return {"job": j}


@app.post("/api/worker/complete", dependencies=[Depends(auth)])
async def complete(job_id: int = Form(...), worker_id: str = Form(...), file: UploadFile = File(...)):
    if not re.fullmatch(r"\d+\.\d+", worker_id):
        raise HTTPException(400, "worker_id sai")
    data = await file.read()
    try:
        Image.open(io.BytesIO(data)).verify()
    except Exception:
        raise HTTPException(400, "file khong phai anh")
    with cur() as c:
        c.execute("SELECT * FROM jobs WHERE id=%s", (job_id,))
        j = c.fetchone()
        if not j:
            raise HTTPException(404)
        filename = f"{j['name']} {worker_id}.png"       # vd: black dog 2.1.png
        (IMG_DIR / filename).write_bytes(data)
        c.execute("""INSERT INTO images(name,filename,ai_id,category,source) VALUES(%s,%s,%s,%s,%s)
                     ON CONFLICT (filename) DO UPDATE SET created_at=now() RETURNING id""",
                  (j["name"], filename, worker_id, j["category"], "user" if j["priority"] >= 10 else "auto"))
        iid = c.fetchone()["id"]
        c.execute("UPDATE jobs SET status='done', image_id=%s WHERE id=%s", (iid, job_id))
    _counter["n"] += 1
    if j["priority"] >= 10:
        notify("Image for user", f"{filename} (AI {worker_id})", "frame_with_picture", 4)
    elif _counter["n"] % NOTIFY_EVERY == 0:
        notify("Auto image", f"{filename} (AI {worker_id}) | tong {_counter['n']} anh tu luc API chay", "art")
    return {"ok": True, "filename": filename}


class Fail(BaseModel):
    job_id: int
    worker_id: str
    error: str = ""


@app.post("/api/worker/fail", dependencies=[Depends(auth)])
def fail(b: Fail):
    with cur() as c:
        c.execute("""UPDATE jobs SET tries=tries+1,
                     status=CASE WHEN priority>=10 OR tries+1<3 THEN 'pending' ELSE 'failed' END
                     WHERE id=%s""", (b.job_id,))
    notify("Worker error", f"AI {b.worker_id} loi job #{b.job_id}: {b.error[:200]}", "warning", 4)
    return {"ok": True}


class Queue(BaseModel):
    items: list[dict]


@app.post("/api/planner/queue", dependencies=[Depends(auth)])
def planner_queue(b: Queue):
    added = 0
    with cur() as c:
        for it in b.items:
            name, cat = clean(it.get("name", "")), (it.get("category") or "misc")[:30]
            c.execute("""INSERT INTO jobs(name,category,priority)
                         SELECT %s,%s,0 WHERE NOT EXISTS (SELECT 1 FROM jobs WHERE name=%s AND status<>'failed')
                         AND NOT EXISTS (SELECT 1 FROM images WHERE name=%s)""", (name, cat, name, name))
            added += c.rowcount
    return {"added": added}


@app.get("/api/planner/backlog", dependencies=[Depends(auth)])
def backlog():
    with cur() as c:
        c.execute("SELECT category, count(*) n FROM jobs WHERE status='pending' AND priority<10 GROUP BY category")
        return {"pending": {r["category"]: r["n"] for r in c.fetchall()}}


app.mount("/images", StaticFiles(directory=str(IMG_DIR)), name="images")


@app.get("/")
def index():
    return FileResponse("static/index.html")
