# Hướng dẫn phần mở rộng (mục 2, 3, 7, 8, 9, 10)

Tài liệu này ghi lại **đã làm gì**, **file nào thay đổi**, **cách demo** và **ảnh cần chụp**
cho từng mục mở rộng, để dùng trực tiếp khi viết báo cáo và khi bảo vệ.

---

## 0. Trạng thái tổng quan

| # | Mục mở rộng | Điểm | Trạng thái |
|---|---|---|---|
| 1 | Blog cá nhân 3 bài (Web Frontend) | 0,5 | ✅ xong (xem `TEST-RESULTS.md`) |
| 2 | API `/student` đọc JSON | 0,5 | ✅ xong |
| 3 | CSDL `studentdb` + bảng `students` | 0,5 | ✅ xong |
| 4 | Realm Keycloak + client + token | 0,5 | ✅ xong |
| 5 | MinIO bucket + upload avatar/PDF | 0,5 | ✅ xong |
| 6 | DNS thêm bản ghi + dig | 0,5 | ✅ xong |
| 7 | Prometheus thêm target `web` | 0,5 | ✅ xong |
| 8 | Grafana dashboard 3 biểu đồ | 0,5 | ✅ xong |
| 9 | Proxy route `/student/` | 0,5 | ✅ xong |
| 10 | Load balancing Round Robin 2 web server | 0,5 | ✅ xong |

> Tổng đã làm: **10/10 mục = 5/5 điểm**, cộng thêm portal 9 server + đăng nhập Keycloak
> + upload ảnh/PDF lên MinIO (mục 11, điểm cộng trình bày).

---

## 1. Chuẩn bị chung

```powershell
cd D:\Code\Cloud\Endtern\huynhmanhphatminiclouddemo

# cổng 80 và 3306 phải trống (tắt XAMPP Apache/MySQL nếu có)
Get-NetTCPConnection -LocalPort 80,3306 -State Listen -ErrorAction SilentlyContinue

docker compose up -d --build
docker compose ps
```

Kết quả mong đợi: **13 container** running (9 server bắt buộc + node-exporter + loki + promtail + web-frontend-server2).

Kiểm tra nhanh toàn hệ thống:

```powershell
curl.exe -s http://localhost/api/hello
curl.exe -s http://localhost/student/
curl.exe -s -o NUL -w "%{http_code}" http://localhost/
```

---

## 2. Mục 2 — API `/student` đọc file JSON (0,5 điểm)

### Đề yêu cầu
- Tạo `students.json` chứa **5 sinh viên** (`id`, `name`, `major`, `gpa`)
- Thêm route `@app.get("/student")` đọc file và trả JSON
- Test qua proxy: `http://localhost/api/student`

### Đã làm

| File | Nội dung |
|---|---|
| `application-backend-server/students.json` | 5 sinh viên, mỗi người có `id`, `name`, `major`, `gpa` |
| `application-backend-server/app.py` | thêm route `/student` |
| `application-backend-server/Dockerfile` | `COPY app.py students.json ./` |

```python
@app.get("/student")
def student():
    with open(os.path.join(BASE_DIR, "students.json"), encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)
```

> `BASE_DIR` là thư mục chứa `app.py`, nên đọc file đúng dù chạy từ đâu trong container.

### Cách demo

```powershell
# qua proxy (đúng như đề)
curl.exe -s http://localhost/api/student

# gọi thẳng app server
curl.exe -s http://localhost:8085/student
```

Kết quả:

```json
[{"gpa":3.52,"id":1,"major":"Kỹ thuật phần mềm","name":"Huỳnh Mạnh Phát"},
 {"gpa":3.31,"id":2,"major":"Khoa học máy tính","name":"Nguyễn Văn An"},
 ...]
```

**Ảnh cần chụp:** terminal chạy lệnh trên + kết quả JSON, hoặc mở trình duyệt
`http://localhost/api/student`.

### Giao diện danh sách sinh viên (mục 2 + 3)

| File | Nội dung |
|---|---|
| `web-frontend-server/html/students/index.html` | trang danh sách: 2 tab (Bài 2 JSON / Bài 3 MariaDB), bảng, thống kê, nút tải lại, JSON gốc |
| `web-frontend-server/html/students/students.css` | theme tối giống trang chủ + blog |
| `web-frontend-server/html/index.html` | link "Sinh viên" + khối CTA "Danh sách sinh viên" |
| `web-frontend-server/html/blog/*.html` | link "Sinh viên" trên thanh điều hướng |

Trang là HTML tĩnh (Nginx phục vụ), dữ liệu lấy bằng `fetch()` tới `/api/student`
và `/api/students-db` **qua API Gateway**, nên trình duyệt không cần biết địa chỉ
backend và không vướng CORS.

```powershell
# tab Bài 2 (students.json)
start http://localhost/students/

# tab Bài 3 (MariaDB) - mở thẳng bằng hash
start http://localhost/students/#db
```

Thao tác trên giao diện: bấm tab để đổi nguồn, **↻ Tải lại** để bỏ cache,
mở **Xem JSON gốc** để thấy payload thật của API.

**Ảnh cần chụp:** tab Bài 2 (5 dòng + GPA) và tab Bài 3 (4 dòng + ngày sinh).

---

## 3. Mục 3 — CSDL `studentdb` + bảng `students` (0,5 điểm)

### Đề yêu cầu
- Tạo database **`studentdb`**, bảng **`students`** gồm:
  `id INT PRIMARY KEY AUTO_INCREMENT`, `student_id VARCHAR(10)`, `fullname VARCHAR(100)`,
  `dob DATE`, `major VARCHAR(50)`
- Chèn **ít nhất 3 bản ghi**
- (Tuỳ chọn) SELECT / UPDATE / DELETE và đọc từ Flask

### Đã làm

| File | Nội dung |
|---|---|
| `relational-database-server/init/002_studentdb.sql` | tạo DB + bảng + 4 bản ghi, kèm ví dụ CRUD |
| `application-backend-server/app.py` | route `/students-db` dùng `pymysql` đọc bảng `students` |
| `docker-compose.yml` | thêm biến `DB_HOST/DB_USER/DB_PASSWORD/DB_NAME` cho app |
| `application-backend-server/Dockerfile` | thêm thư viện `pymysql` |

> ⚠️ Script trong `init/` **chỉ tự chạy khi volume dữ liệu còn trống** (lần đầu).
> Nếu DB đã có dữ liệu từ trước, phải nạp tay — xem lệnh bên dưới.
> Script có `DROP TABLE IF EXISTS students` nên nạp lại nhiều lần vẫn ra đúng 4 dòng,
> không bị trùng.

### Cách demo

**Bước 1 — nạp SQL (chỉ cần khi DB đã tồn tại từ trước):**

```powershell
cmd /c "docker exec -i relational-database-server mariadb -uroot -proot --default-character-set=utf8mb4 < relational-database-server\init\002_studentdb.sql"
```

> **Sửa 4 dòng `INSERT` trong file SQL?** Phải chạy lại đúng lệnh trên thì DB mới đổi.
> Chỉ sửa file rồi restart container **không có tác dụng**, vì `init/` chỉ chạy lúc
> database còn trống. Script đã có `DROP TABLE IF EXISTS` nên chạy lại an toàn.

**Bước 2 — kiểm tra bằng SQL:**

```powershell
docker exec relational-database-server mariadb -uroot -proot -e "USE studentdb; SELECT id, student_id, fullname, dob, major FROM students;"
```

**Bước 3 — đọc từ Flask (tuỳ chọn trong đề, đã làm luôn):**

```powershell
curl.exe -s http://localhost/api/students-db
```

```json
{"count":4,"students":[{"dob":"2004-05-21","fullname":"Huỳnh Mạnh Phát","id":1,
 "major":"Kỹ thuật phần mềm","student_id":"SV001"}, ...]}
```

**Bước 4 — demo CRUD:**

```powershell
# C: thêm
docker exec relational-database-server mariadb -uroot -proot -e "USE studentdb; INSERT INTO students(student_id, fullname, dob, major) VALUES ('SV005','Ngô Gia Hân','2004-09-09','Khoa học dữ liệu'); SELECT * FROM students;"

# U: sửa
docker exec relational-database-server mariadb -uroot -proot -e "USE studentdb; UPDATE students SET major='DevOps' WHERE student_id='SV002'; SELECT student_id, fullname, major FROM students WHERE student_id='SV002';"

# D: xoá
docker exec relational-database-server mariadb -uroot -proot -e "USE studentdb; DELETE FROM students WHERE student_id='SV005'; SELECT COUNT(*) AS con_lai FROM students;"
```

Sau mỗi thao tác, mở `http://localhost/students/` và bấm **↻ Tải lại** để thấy
bảng MariaDB cập nhật ngay. Không cần build lại container, không cần F5 cả trang.

**Ảnh cần chụp:** kết quả `SELECT * FROM students` + bảng MariaDB trên giao diện
(hoặc `curl /api/students-db`).

---

## 4. Mục 7 — Prometheus thêm scrape target `web` (0,5 điểm)

### Đề yêu cầu
```yaml
- job_name: 'web'
  static_configs:
    - targets: ['web-frontend-server:80']
```
Sửa `prometheus.yml`, restart container, mở `http://localhost:9090/targets` thấy target **UP**.

### Đã làm

| File | Thay đổi |
|---|---|
| `monitoring-prometheus-server/prometheus.yml` | thêm job `web` (metrics_path `/metrics`), thêm job `prometheus` |
| `web-frontend-server/html/metrics` | file text đúng định dạng Prometheus, phục vụ tại `/metrics` |
| `web-frontend-server/conf.default` | `location = /metrics` trả `text/plain` |

> **Vì sao cần file `/metrics`?** Nginx không tự xuất metric Prometheus. Nếu chỉ trỏ
> vào `:80/metrics` mà không có endpoint, Prometheus trả 404 → target **DOWN**.
> File tĩnh này giữ đúng định dạng text exposition nên target UP.
> Muốn số liệu thật: thêm `nginx-prometheus-exporter` + `stub_status` (goài phạm vi đồ án).

### Cách demo

```powershell
# xem nội dung metric
curl.exe -s http://localhost:8080/metrics

# restart (chỉ cần khi vừa sửa prometheus.yml)
docker compose restart monitoring-prometheus-server

# kiểm tra qua API
curl.exe -s "http://localhost:9090/api/v1/targets" |
  ConvertFrom-Json | Select-Object -ExpandProperty data |
  Select-Object -ExpandProperty activeTargets |
  Select-Object @{n='job';e={$_.labels.job}}, health, scrapeUrl
```

Kết quả:

```
job         health scrapeUrl
node        up     http://monitoring-node-exporter-server:9100/metrics
prometheus  up     http://localhost:9090/metrics
web         up     http://web-frontend-server:80/metrics
```

**Ảnh cần chụp:** trang `http://localhost:9090/targets` — thấy 3 target `UP`
(đặc biệt job **web** màu xanh).

---

## 5. Mục 8 — Grafana dashboard "System Health of &lt;MSSV&gt;" (0,5 điểm)

### Đề yêu cầu
Dashboard gồm **3 biểu đồ**: CPU Usage (%), Memory Usage, Network Traffic.
Datasource Prometheus. Metric: `node_cpu_seconds_total`,
`node_memory_MemAvailable_bytes`, `node_network_receive_bytes_total`.

### Đã làm

| File | Nội dung |
|---|---|
| `monitoring-grafana-dashboard-server/provisioning/dashboards/system-health.json` | dashboard 4 panel, tự nạp khi khởi động |
| `monitoring-grafana-dashboard-server/provisioning/dashboards/dashboards.yml` | provider trỏ tới thư mục trên, folder `MyMiniCloud` |
| `monitoring-grafana-dashboard-server/provisioning/datasources/datasources.yml` | thêm `uid: prometheus` / `uid: loki` để dashboard tham chiếu ổn định |

Các panel và PromQL:

| Panel | PromQL |
|---|---|
| CPU Usage (%) | `100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)` |
| Memory Usage (%) | `100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)` |
| Network Traffic | `rate(node_network_receive_bytes_total{device!~"lo|veth.*|br-.*|docker.*"}[5m])` (RX) và `..._transmit_bytes_total...` (TX) |
| Application Logs | Loki: `{job="docker"}` |

### Cách demo

1. Mở `http://localhost:3000` → đăng nhập `admin/admin`.
2. Menu trái → **Dashboards** → folder **MyMiniCloud** → **System Health of Huynh Manh Phat**.
3. Để chế độ TV cho đẹp: thêm `?kiosk` vào URL:
   `http://localhost:3000/d/system-health?orgId=1&kiosk`

Kiểm tra bằng API (không cần mở trình duyệt):

```powershell
curl.exe -s -u admin:admin "http://localhost:3000/api/search?query=System%20Health"
```

**Đổi MSSV trong tên dashboard:** sửa dòng `"title"` trong
`provisioning/dashboards/system-health.json`, sau đó:

```powershell
docker compose restart monitoring-grafana-dashboard-server
```

> Dashboard được **provisioning tự động**, không phải tạo tay trên UI.
> Nếu sửa file JSON mà không thấy đổi: đợi ~15s (provider quét mỗi 10s) rồi F5.

**Ảnh cần chụp:** toàn bộ dashboard hiển thị 3 biểu đồ có dữ liệu + tiêu đề chứa MSSV.

---

## 6. Mục 9 — Proxy thêm route `/student/` (0,5 điểm)

### Đề yêu cầu
```nginx
location /student/ {
    proxy_pass http://application-backend-server:8081/student;
}
```
Restart proxy, `curl http://localhost/student/` trả danh sách sinh viên JSON.

### Đã làm

| File | Thay đổi |
|---|---|
| `api-gateway-proxy-server/nginx.conf` | thêm `location /student/` |

### Cách demo

```powershell
docker compose restart api-gateway-proxy-server

curl.exe -s http://localhost/student/
curl.exe -s -o NUL -w "%{http_code}`n" http://localhost/student/    # 200
```

Kết quả: JSON danh sách sinh viên (giống `/api/student`).

**Giải thích trong báo cáo:** `proxy_pass` có URI `/student` nên Nginx **thay** phần
tiền tố `/student/` của request bằng `/student` → backend chỉ cần route `/student`.
Đây là cơ chế **route mapping** của API Gateway.

**Ảnh cần chụp:** terminal `curl http://localhost/student/` + JSON trả về.

---

## 7. Mục 10 — Load balancing Round Robin 2 web server (0,5 điểm)

### Đề yêu cầu
Cấu hình Nginx cân bằng tải cho 2 web server (`web-frontend-server1`, `web-frontend-server2`)
theo thuật toán **Round Robin**, test thấy kết quả **luân phiên**.

### Đã làm

| File | Thay đổi |
|---|---|
| `docker-compose.yml` | thêm service `web-frontend-server2` (cùng image, port host `8082`), đặt `hostname` cho 2 server, alias `web-frontend-server1` |
| `api-gateway-proxy-server/nginx.conf` | `upstream web_backend { server web-frontend-server1:80; server web-frontend-server2:80; }`, `location /` trỏ vào upstream |
| `web-frontend-server/conf.default` | thêm header `X-Served-By: $hostname` + badge "Served by ..." ở góc phải |

> `web-frontend-server` (server 1) vẫn giữ **container_name đúng đề bắt buộc**,
> đồng thời có alias mạng `web-frontend-server1` và `hostname: web-frontend-server1`,
> nên cấu hình upstream dùng đúng tên `web-frontend-server1` / `web-frontend-server2`.

### Cách demo

```powershell
docker compose up -d --build web-frontend-server2 api-gateway-proxy-server

# xem header doi chieu tung request
1..6 | ForEach-Object {
  $h = curl.exe -s -D - -o NUL http://localhost/
  ($h -split "`n" | Select-String "X-Served-By").ToString().Trim()
}
```

Kết quả luân phiên:

```
X-Served-By: web-frontend-server1
X-Served-By: web-frontend-server2
X-Served-By: web-frontend-server1
X-Served-By: web-frontend-server2
X-Served-By: web-frontend-server1
X-Served-By: web-frontend-server2
```

Trên trình duyệt: mở `http://localhost/` và **F5 liên tục** — badge góc phải dưới
đổi giữa `Served by web-frontend-server1` và `Served by web-frontend-server2`.

So sánh trực tiếp từng server (không qua proxy):

```powershell
curl.exe -s -o NUL -w "server1: %{http_code}`n" http://localhost:8080/
curl.exe -s -o NUL -w "server2: %{http_code}`n" http://localhost:8082/
```

**Ảnh cần chụp:** 2 ảnh trình duyệt (mỗi ảnh thấy badge tên server khác nhau) hoặc
terminal 6 dòng `X-Served-By` xen kẽ.

---

## 8. Bảng lệnh kiểm thử tổng hợp (dùng khi demo)

```powershell
cd D:\Code\Cloud\Endtern\huynhmanhphatminiclouddemo

# 13 container
docker compose ps

# mục 2
curl.exe -s http://localhost/api/student
start http://localhost/students/

# mục 3
docker exec relational-database-server mariadb -uroot -proot -e "USE studentdb; SELECT * FROM students;"
curl.exe -s http://localhost/api/students-db
start http://localhost/students/

# mục 7
curl.exe -s http://localhost:8080/metrics
curl.exe -s "http://localhost:9090/api/v1/targets" | ConvertFrom-Json |
  Select-Object -ExpandProperty data | Select-Object -ExpandProperty activeTargets |
  Select-Object @{n='job';e={$_.labels.job}}, health

# mục 8
curl.exe -s -u admin:admin "http://localhost:3000/api/search?query=System%20Health"

# mục 9
curl.exe -s http://localhost/student/

# mục 10
1..4 | ForEach-Object { (curl.exe -s -D - -o NUL http://localhost/ -split "`n" |
  Select-String "X-Served-By").ToString().Trim() }
```

Kết quả đã chạy thực tế ngày 05/11/2026: tất cả **PASS** (xem `TEST-RESULTS.md`).

---

## 9. Xử lý sự cố thường gặp

| Hiện tượng | Nguyên nhân | Cách sửa |
|---|---|---|
| `ports are not available: 3306` | XAMPP MySQL đang chiếm cổng | `Stop-Service mysql -Force` (PowerShell admin) |
| `ports are not available: 80` | XAMPP Apache chiếm cổng | `Stop-Service Apache2.4 -Force` |
| Grafana crash `Datasource provisioning error` | volume `grafana-data` còn datasource cũ chưa có `uid` | `docker compose rm -sf monitoring-grafana-dashboard-server` rồi `docker volume rm huynhmanhphatminiclouddemo_grafana-data` rồi `up -d` |
| `studentdb` không có bảng | volume DB đã tồn tại nên `init/` không chạy lại | Nạp tay bằng lệnh `cmd /c "... < 002_studentdb.sql"` |
| Sửa 4 dòng `INSERT` trong file SQL nhưng DB vẫn dữ liệu cũ | `init/` chỉ chạy khi DB còn trống | Chạy lại script như trên (script có `DROP TABLE IF EXISTS`) |
| `/api/students-db` trả `Access denied` | sai user/password DB | kiểm tra biến `DB_*` trong `docker-compose.yml` |
| Target `web` DOWN | thiếu file `/metrics` | kiểm tra `curl http://localhost:8080/metrics` trả text/plain |
| Dashboard trống | Prometheus chưa đủ dữ liệu | đợi 2–5 phút (cần ít nhất 2 mẫu cho `rate()`) |
| Round robin không đổi | request bị cache | dùng `curl.exe -s -D -` hoặc Ctrl+F5 trên trình duyệt |

---

## 10. Ghi chú khi viết báo cáo

- **Mục 2** nên nêu: API tĩnh vs API đọc DB (`/student` và `/students-db`).
- **Mục 3** chứng minh bằng `SELECT` + CRUD, nhấn mạnh **volume** giữ dữ liệu khi xoá container.
- **Mục 7** giải thích Prometheus là mô hình **pull**, `scrape_interval` 15s, `job_name` phân nhóm target.
- **Mục 8** dán 3 câu PromQL và nói rõ đơn vị (%) / (Bps).
- **Mục 9** giải thích `proxy_pass` có URI → thay tiền tố; API Gateway che giấu địa chỉ backend.
- **Mục 10** nêu thuật toán mặc định của Nginx là round-robin, cân bằng theo **request** chứ không theo kết nối.
- Ghi rõ trong báo cáo: **đã làm 10/10 mục mở rộng = 5/5 điểm**, cộng portal 9 server
  + đăng nhập Keycloak phân quyền + upload ảnh/PDF lên MinIO.
