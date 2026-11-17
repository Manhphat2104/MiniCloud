from flask import Flask, jsonify, request, redirect, send_file, make_response
import time, requests, os, json, datetime
import base64, hashlib, io, re, secrets, socket, uuid
import concurrent.futures
import urllib.request
from urllib.parse import urlencode, quote
from functools import wraps
from jose import jwt
import pymysql
from minio import Minio
from minio.error import S3Error

# ---------------------------------------------------------------------------
# Cau hinh
# ---------------------------------------------------------------------------
ISSUER   = os.getenv("OIDC_ISSUER",   "http://localhost:8081/realms/realm_523H0167")
AUDIENCE = os.getenv("OIDC_AUDIENCE", "account")
JWKS_URL = os.getenv("OIDC_JWKS_URL", f"{ISSUER}/protocol/openid-connect/certs")

# URL noi bo (container-to-container) de doi token
OIDC_INTERNAL   = os.getenv("OIDC_INTERNAL", "http://authentication-identity-server:8080/realms/realm_523H0167")
OIDC_CLIENT_ID  = os.getenv("OIDC_CLIENT_ID", "web-portal")
OIDC_SECRET     = os.getenv("OIDC_CLIENT_SECRET", "web-portal-secret-523H0167")
PUBLIC_URL      = os.getenv("PUBLIC_URL", "http://localhost").rstrip("/")

AUTHORIZE_URL = f"{ISSUER}/protocol/openid-connect/auth"
LOGOUT_URL    = f"{ISSUER}/protocol/openid-connect/logout"
TOKEN_URL     = f"{OIDC_INTERNAL}/protocol/openid-connect/token"
REDIRECT_URI  = f"{PUBLIC_URL}/api/session/callback"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_HOST = os.getenv("DB_HOST", "relational-database-server")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "root")
DB_NAME = os.getenv("DB_NAME", "studentdb")

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://object-storage-server:9000")
MINIO_ACCESS   = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET   = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_PUBLIC_URL = os.getenv("MINIO_PUBLIC_URL", "http://localhost:9000").rstrip("/")

BUCKET_IMAGES = "profile-pics"
BUCKET_DOCS   = "documents"
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "10"))

IMAGE_EXT = {"jpg", "jpeg", "png", "webp", "gif"}
PDF_EXT   = {"pdf"}

app = Flask(__name__)
app.json.ensure_ascii = False
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024 + 1024

_JWKS = None
_TS = 0

# ---------------------------------------------------------------------------
# JWT / Keycloak
# ---------------------------------------------------------------------------
def get_jwks():
    global _JWKS, _TS
    now = time.time()
    if not _JWKS or now - _TS > 600:
        _JWKS = requests.get(JWKS_URL, timeout=5).json()
        _TS = now
    return _JWKS


def decode_token(token):
    return jwt.decode(token, get_jwks(), algorithms=["RS256"], issuer=ISSUER,
                      options={"verify_aud": False})


# Session luu server-side; cookie chi chua sid.
SESSIONS = {}
PENDING  = {}
SESSION_TTL = 8 * 3600


def _now():
    return int(time.time())


def _roles_from(payload):
    return payload.get("realm_access", {}).get("roles", []) or []


def _refresh(s):
    r = requests.post(TOKEN_URL, data={
        "grant_type": "refresh_token",
        "client_id": OIDC_CLIENT_ID,
        "client_secret": OIDC_SECRET,
        "refresh_token": s["refresh_token"],
    }, timeout=8)
    r.raise_for_status()
    data = r.json()
    payload = decode_token(data["access_token"])
    s["access_token"]  = data["access_token"]
    s["refresh_token"] = data.get("refresh_token", s.get("refresh_token"))
    s["token_exp"]     = _now() + int(data.get("expires_in", 300))
    s["roles"]         = _roles_from(payload)
    s["username"]      = payload.get("preferred_username") or s.get("username")
    s["name"]          = payload.get("name") or s.get("name")


def current_session():
    sid = request.cookies.get("sid")
    if not sid:
        return None
    s = SESSIONS.get(sid)
    if not s:
        return None
    if s["expires"] < _now():
        SESSIONS.pop(sid, None)
        return None
    if s.get("token_exp", 0) - 30 < _now() and s.get("refresh_token"):
        try:
            _refresh(s)
        except Exception:
            pass
    return s


def current_user():
    s = current_session()
    if not s:
        return None
    return {
        "username": s["username"],
        "name": s.get("name") or s["username"],
        "roles": s.get("roles", []),
        "is_admin": "admin" in (s.get("roles") or []),
    }


def require_admin(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        u = current_user()
        if not u:
            return jsonify(error="Cần đăng nhập"), 401
        if not u["is_admin"]:
            return jsonify(error="Chỉ tài khoản admin được phép chỉnh sửa"), 403
        return fn(*a, **kw)
    return wrapper


@app.get("/session/login")
def session_login():
    state    = secrets.token_urlsafe(24)
    verifier = secrets.token_urlsafe(56)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    nxt = request.args.get("next", "/")
    if not nxt.startswith("/") or nxt.startswith("//"):
        nxt = "/"
    PENDING[state] = {"verifier": verifier, "next": nxt, "ts": _now()}
    q = urlencode({
        "client_id": OIDC_CLIENT_ID,
        "response_type": "code",
        "scope": "openid profile email",
        "redirect_uri": REDIRECT_URI,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })
    return redirect(f"{AUTHORIZE_URL}?{q}")


@app.get("/session/callback")
def session_callback():
    if request.args.get("error"):
        return redirect("/?login=error")
    state = request.args.get("state", "")
    code  = request.args.get("code", "")
    p = PENDING.pop(state, None)
    if not p or _now() - p["ts"] > 600 or not code:
        return redirect("/?login=error")

    r = requests.post(TOKEN_URL, data={
        "grant_type": "authorization_code",
        "client_id": OIDC_CLIENT_ID,
        "client_secret": OIDC_SECRET,
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "code_verifier": p["verifier"],
    }, timeout=10)
    if r.status_code != 200:
        return redirect("/?login=error")
    tok = r.json()
    payload = decode_token(tok["access_token"])

    sid = secrets.token_urlsafe(32)
    SESSIONS[sid] = {
        "username": payload.get("preferred_username") or "user",
        "name": payload.get("name") or "",
        "roles": _roles_from(payload),
        "access_token": tok["access_token"],
        "refresh_token": tok.get("refresh_token"),
        "id_token": tok.get("id_token"),
        "token_exp": _now() + int(tok.get("expires_in", 300)),
        "expires": _now() + SESSION_TTL,
    }
    resp = make_response(redirect(p["next"]))
    resp.set_cookie("sid", sid, max_age=SESSION_TTL, httponly=True, samesite="Lax")
    return resp


@app.get("/session/me")
def session_me():
    u = current_user()
    if not u:
        return jsonify(authenticated=False, is_admin=False, roles=[])
    return jsonify(authenticated=True, **u)


@app.post("/session/logout")
def session_logout():
    sid = request.cookies.get("sid")
    s = SESSIONS.pop(sid, None) if sid else None
    url = f"{LOGOUT_URL}?client_id={OIDC_CLIENT_ID}&post_logout_redirect_uri={quote(PUBLIC_URL + '/')}"
    if s and s.get("id_token"):
        url += f"&id_token_hint={s['id_token']}"
    resp = make_response(jsonify(ok=True, logout_url=url))
    resp.delete_cookie("sid")
    return resp


# ---------------------------------------------------------------------------
# 9 server bat buoc (mo rong: trang thai ha tang)
# ---------------------------------------------------------------------------
SERVICES = [
    {"key": "web", "name": "Web Server", "container": "web-frontend-server",
     "port": 8080, "detail": "Nginx · 2 instance round robin",
     "check": ("http", "http://web-frontend-server:80/"),
     "open": (8080, "/"), "has_ui": True},
    {"key": "app", "name": "Application Server", "container": "application-backend-server",
     "port": 8085, "detail": "Flask API",
     "check": ("http", "http://127.0.0.1:8081/hello"),
     "open": (8085, "/hello"), "has_ui": True},
    {"key": "db", "name": "Database Server", "container": "relational-database-server",
     "port": 3306, "detail": "MariaDB · studentdb",
     "check": ("tcp", "relational-database-server", 3306),
     "open": None, "has_ui": False,
     "hint": 'docker exec relational-database-server mariadb -uroot -proot -e "SHOW DATABASES;"'},
    {"key": "auth", "name": "Authentication Server", "container": "authentication-identity-server",
     "port": 8081, "detail": "Keycloak · realm_523H0167",
     "check": ("http", "http://authentication-identity-server:8080/realms/realm_523H0167"),
     "open": (8081, "/"), "has_ui": True},
    {"key": "storage", "name": "Object Storage", "container": "object-storage-server",
     "port": 9000, "detail": "MinIO · Console 9001",
     "check": ("http", "http://object-storage-server:9000/minio/health/live"),
     "open": (9001, "/"), "has_ui": True},
    {"key": "dns", "name": "DNS Server", "container": "internal-dns-server",
     "port": 1053, "detail": "Bind9 · zone cloud.local",
     "check": ("tcp", "internal-dns-server", 53),
     "open": None, "has_ui": False,
     "hint": "docker exec internal-dns-server dig +short @127.0.0.1 web-frontend-server.cloud.local"},
    {"key": "prometheus", "name": "Monitoring", "container": "monitoring-prometheus-server",
     "port": 9090, "detail": "Prometheus + Node Exporter",
     "check": ("http", "http://monitoring-prometheus-server:9090/-/ready"),
     "open": (9090, "/targets"), "has_ui": True},
    {"key": "grafana", "name": "Logging / Dashboard", "container": "monitoring-grafana-dashboard-server",
     "port": 3000, "detail": "Grafana + Loki + Promtail",
     "check": ("http", "http://monitoring-grafana-dashboard-server:3000/api/health"),
     "open": (3000, "/"), "has_ui": True},
    {"key": "gateway", "name": "API Gateway", "container": "api-gateway-proxy-server",
     "port": 80, "detail": "Nginx reverse proxy · round robin",
     "check": ("self",),
     "open": (80, "/"), "has_ui": True},
]

_SVC_CACHE = {"ts": 0, "data": None}


def _http_ok(url, timeout=1.5):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return 200 <= r.status < 500
    except Exception:
        return False


def _tcp_ok(host, port, timeout=1.5):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _check(svc):
    c = svc["check"]
    if c[0] == "self":
        return True
    if c[0] == "http":
        return _http_ok(c[1])
    return _tcp_ok(c[1], c[2])


@app.get("/services")
def services():
    if _SVC_CACHE["data"] and time.time() - _SVC_CACHE["ts"] < 10:
        return jsonify(_SVC_CACHE["data"])

    with concurrent.futures.ThreadPoolExecutor(max_workers=9) as ex:
        states = list(ex.map(_check, SERVICES))

    out = []
    for svc, ok in zip(SERVICES, states):
        out.append({
            "key": svc["key"], "name": svc["name"], "container": svc["container"],
            "port": svc["port"], "detail": svc["detail"],
            "status": "up" if ok else "down",
            "has_ui": svc["has_ui"],
            "open_port": svc["open"][0] if svc["open"] else None,
            "open_path": svc["open"][1] if svc["open"] else None,
            "hint": svc.get("hint"),
        })
    data = {"count": len(out),
            "up": sum(1 for s in out if s["status"] == "up"),
            "checked_at": datetime.datetime.now().strftime("%H:%M:%S"),
            "services": out}
    _SVC_CACHE.update(ts=time.time(), data=data)
    return jsonify(data)


# ---------------------------------------------------------------------------
# MinIO
# ---------------------------------------------------------------------------
_minio = None
_buckets_ready = False


def minio_client():
    global _minio
    if _minio is None:
        host = MINIO_ENDPOINT.replace("http://", "").replace("https://", "")
        _minio = Minio(host, access_key=MINIO_ACCESS, secret_key=MINIO_SECRET,
                       secure=MINIO_ENDPOINT.startswith("https"))
    return _minio


def ensure_buckets():
    global _buckets_ready
    if _buckets_ready:
        return
    c = minio_client()
    for b in (BUCKET_IMAGES, BUCKET_DOCS, "demo"):
        if not c.bucket_exists(b):
            c.make_bucket(b)
    # Anh + demo cho phep doc cong khai; documents giu private.
    public_policy = json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"AWS": ["*"]},
            "Action": ["s3:GetObject"],
            "Resource": [f"arn:aws:s3:::{b}/*" for b in (BUCKET_IMAGES, "demo")],
        }],
    })
    try:
        c.set_bucket_policy(BUCKET_IMAGES, public_policy)
    except Exception:
        pass
    _buckets_ready = True


def _safe_name(name):
    base = os.path.basename(name or "file")
    base = re.sub(r"[^A-Za-z0-9._-]", "_", base).strip("._") or "file"
    return f"{uuid.uuid4().hex[:8]}_{base}"


def _magic_ok(head, ext):
    if ext == "pdf":
        return head.startswith(b"%PDF")
    if ext in ("jpg", "jpeg"):
        return head.startswith(b"\xff\xd8\xff")
    if ext == "png":
        return head.startswith(b"\x89PNG\r\n\x1a\n")
    if ext == "gif":
        return head.startswith(b"GIF8")
    if ext == "webp":
        return head[:4] == b"RIFF" and head[8:12] == b"WEBP"
    return False


def _list_bucket(bucket):
    ensure_buckets()
    out = []
    for o in minio_client().list_objects(bucket, recursive=True):
        name = o.object_name
        item = {
            "name": name,
            "size": o.size,
            "last_modified": o.last_modified.strftime("%d/%m/%Y %H:%M") if o.last_modified else "",
        }
        if bucket == BUCKET_IMAGES:
            item["url"] = f"{MINIO_PUBLIC_URL}/{bucket}/{quote(name)}"
        else:
            item["url"] = None
        out.append(item)
    out.sort(key=lambda x: x["last_modified"], reverse=True)
    return out


@app.get("/files/images")
def files_images():
    try:
        return jsonify(bucket=BUCKET_IMAGES, public=True, files=_list_bucket(BUCKET_IMAGES))
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.get("/files/documents")
def files_documents():
    try:
        return jsonify(bucket=BUCKET_DOCS, public=False, files=_list_bucket(BUCKET_DOCS))
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.post("/files/upload")
@require_admin
def files_upload():
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify(error="Không có file"), 400
    raw_name = f.filename
    ext = raw_name.rsplit(".", 1)[-1].lower() if "." in raw_name else ""
    if ext not in IMAGE_EXT and ext not in PDF_EXT:
        return jsonify(error="Chỉ hỗ trợ ảnh (jpg, png, webp, gif) và PDF"), 400

    data = f.read()
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        return jsonify(error=f"File vượt quá {MAX_UPLOAD_MB} MB"), 413
    if not _magic_ok(data[:16], ext):
        return jsonify(error="Nội dung file không khớp định dạng"), 400

    bucket = BUCKET_DOCS if ext in PDF_EXT else BUCKET_IMAGES
    ctype = "application/pdf" if ext == "pdf" else f"image/{'jpeg' if ext in ('jpg', 'jpeg') else ext}"
    name = _safe_name(raw_name)
    ensure_buckets()
    minio_client().put_object(bucket, name, io.BytesIO(data), len(data), content_type=ctype)
    item = {"name": name, "size": len(data), "bucket": bucket, "kind": "pdf" if ext in PDF_EXT else "image"}
    if bucket == BUCKET_IMAGES:
        item["url"] = f"{MINIO_PUBLIC_URL}/{bucket}/{quote(name)}"
    return jsonify(ok=True, file=item), 201


@app.get("/files/documents/<path:name>/download")
def files_download(name):
    try:
        ensure_buckets()
        resp = minio_client().get_object(BUCKET_DOCS, name)
        try:
            data = resp.read()
        finally:
            resp.close()
            resp.release_conn()
        return send_file(io.BytesIO(data), mimetype="application/pdf",
                         as_attachment=True, download_name=name.split("_", 1)[-1])
    except S3Error:
        return jsonify(error="Không tìm thấy file"), 404
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.delete("/files/<kind>/<path:name>")
@require_admin
def files_delete(kind, name):
    bucket = BUCKET_IMAGES if kind == "images" else BUCKET_DOCS if kind == "documents" else None
    if not bucket:
        return jsonify(error="Loại file không hợp lệ"), 400
    try:
        minio_client().remove_object(bucket, name)
        return jsonify(ok=True)
    except Exception as e:
        return jsonify(error=str(e)), 500


# ---------------------------------------------------------------------------
# API co ban
# ---------------------------------------------------------------------------
@app.get("/hello")
def hello():
    return jsonify(message="Hello from App Server!")


@app.get("/student")
def student():
    with open(os.path.join(BASE_DIR, "students.json"), encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)


def get_conn():
    return pymysql.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER,
        password=DB_PASSWORD, database=DB_NAME,
        charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=5,
    )


def clean_student(data):
    sid = (data.get("student_id") or "").strip()
    name = (data.get("fullname") or "").strip()
    major = (data.get("major") or "").strip()
    dob = (data.get("dob") or "").strip() or None
    if not sid or not name:
        raise ValueError("Mã SV và Họ tên không được để trống")
    if len(sid) > 10:
        raise ValueError("Mã SV tối đa 10 ký tự")
    if dob:
        try:
            datetime.date.fromisoformat(dob)
        except ValueError:
            raise ValueError("Ngày sinh phải có dạng YYYY-MM-DD")
    return sid, name, dob, (major or None)


@app.get("/students-db")
def students_db():
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT id, student_id, fullname, dob, major FROM students ORDER BY id")
            rows = cur.fetchall()
        conn.close()
        for r in rows:
            if r.get("dob") is not None:
                r["dob"] = r["dob"].isoformat()
        return jsonify(count=len(rows), students=rows)
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.post("/students-db")
@require_admin
def students_create():
    try:
        sid, name, dob, major = clean_student(request.get_json(silent=True) or {})
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO students (student_id, fullname, dob, major) VALUES (%s,%s,%s,%s)",
                (sid, name, dob, major))
            new_id = cur.lastrowid
        conn.commit()
        conn.close()
        return jsonify(id=new_id, message="Đã thêm"), 201
    except ValueError as e:
        return jsonify(error=str(e)), 400
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.put("/students-db/<int:row_id>")
@require_admin
def students_update(row_id):
    try:
        sid, name, dob, major = clean_student(request.get_json(silent=True) or {})
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM students WHERE id=%s", (row_id,))
            if not cur.fetchone():
                conn.close()
                return jsonify(error="Không tìm thấy sinh viên"), 404
            cur.execute(
                "UPDATE students SET student_id=%s, fullname=%s, dob=%s, major=%s WHERE id=%s",
                (sid, name, dob, major, row_id))
        conn.commit()
        conn.close()
        return jsonify(message="Đã cập nhật")
    except ValueError as e:
        return jsonify(error=str(e)), 400
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.delete("/students-db/<int:row_id>")
@require_admin
def students_delete(row_id):
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM students WHERE id=%s", (row_id,))
            deleted = cur.rowcount
        conn.commit()
        conn.close()
        if not deleted:
            return jsonify(error="Không tìm thấy sinh viên"), 404
        return jsonify(message="Đã xóa")
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.get("/secure")
def secure():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify(error="Missing Bearer token"), 401
    token = auth.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, get_jwks(), algorithms=["RS256"], audience=AUDIENCE, issuer=ISSUER)
        return jsonify(message="Secure resource OK", preferred_username=payload.get("preferred_username"))
    except Exception as e:
        return jsonify(error=str(e)), 401


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081)
