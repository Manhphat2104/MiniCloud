from flask import Flask, jsonify, request
import time, requests, os, json
from jose import jwt
import pymysql
import time, requests, os, json, datetime

ISSUER   = os.getenv("OIDC_ISSUER",   "http://authentication-identity-server:8080/realms/master")
AUDIENCE = os.getenv("OIDC_AUDIENCE", "myapp")
JWKS_URL = os.getenv("OIDC_JWKS_URL", f"{ISSUER}/protocol/openid-connect/certs")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_HOST = os.getenv("DB_HOST", "relational-database-server")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "root")
DB_NAME = os.getenv("DB_NAME", "studentdb")

_JWKS = None
_TS = 0

def get_jwks():
    global _JWKS, _TS
    now = time.time()
    if not _JWKS or now - _TS > 600:
        _JWKS = requests.get(JWKS_URL, timeout=5).json()
        _TS = now
    return _JWKS

app = Flask(__name__)
app.json.ensure_ascii = False


@app.get("/hello")
def hello():
    return jsonify(message="Hello from App Server!")

# --- Mo rong 2: API /student doc tu file JSON -------------------------------
@app.get("/student")
def student():
    with open(os.path.join(BASE_DIR, "students.json"), encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)

# --- Mo rong 3: CRUD du lieu trong database studentdb -----------------------
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
    auth = request.headers.get("Authorization","")
    if not auth.startswith("Bearer "):
        return jsonify(error="Missing Bearer token"), 401
    token = auth.split(" ",1)[1]
    try:
        payload = jwt.decode(token, get_jwks(), algorithms=["RS256"], audience=AUDIENCE, issuer=ISSUER)
        return jsonify(message="Secure resource OK", preferred_username=payload.get("preferred_username"))
    except Exception as e:
        return jsonify(error=str(e)), 401
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081)
