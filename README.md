# MyMiniCloud — Cloud Platform thu nhỏ trên Docker

Đồ án cuối kỳ môn Điện toán đám mây: dựng **9 loại máy chủ** của một Cloud Platform
(giống AWS/Azure/GCP) bằng Docker Compose, tất cả chạy chung network `cloud-net`,
deploy được cả trên máy local và AWS EC2.

**Nhóm thực hiện**

| Họ và tên | MSSV |
|---|---|
| Huỳnh Mạnh Phát | 523H0167 |
| Phạm Nguyễn Thanh Phong | 523H0169 |

**Docker Hub (image tự chế, repo public)**

- `phathuynh2104/web:dev` — Nginx + toàn bộ HTML/CSS/JS
- `phathuynh2104/app:dev` — Flask API + OIDC + MinIO client

---

## 1. Kiến trúc

```
Người dùng
   │  http://<host>/
   ▼
┌──────────────────────────┐
│ API Gateway (Nginx :80)  │  round robin 2 web server
└───┬───────────┬──────────┘
    │ /         │ /api/*  /auth/*
    ▼           ▼
┌─────────┐  ┌──────────────┐   ┌──────────────┐
│ Web 1/2 │  │ Flask App    │──▶│ MariaDB      │
│ :8080   │  │ :8085        │   │ :3306        │
│ :8082   │  │              │   └──────────────┘
└─────────┘  │  OIDC login  │──▶ Keycloak :8081
             │  MinIO SDK   │──▶ MinIO :9000/9001
             └──────────────┘
   Prometheus :9090 · Grafana :3000 · Loki :3100 · Bind9 :1053
```

**Trang chủ là một Cloud Portal** gồm:

1. **Hạ tầng đang vận hành** — đúng **9 card** server bắt buộc, đèn xanh/đỏ cập nhật mỗi 15 giây.
   Bấm card có giao diện → mở server đó ở tab mới; Database/DNS hiện hướng dẫn kiểm tra bằng `docker exec`.
2. **Kho tài liệu** — upload/tải **ảnh** (vào `profile-pics`, public) và **PDF**
   (vào `documents`, private) qua MinIO; chỉ **admin** được upload/xoá.
3. **Đăng nhập Keycloak** — hiển thị `username · role`, đăng xuất; phân quyền thao tác sửa.

---

## 2. Chín server bắt buộc

| # | Server | Container | Cổng host | Ghi chú |
|---|---|---|---|---|
| 1 | Web Server | `web-frontend-server` (+ `web-frontend-server2`) | 8080, 8082 | Nginx static, round robin |
| 2 | Application Server | `application-backend-server` | 8085 | Flask, listen nội bộ 8081 |
| 3 | Database Server | `relational-database-server` | 3306 | MariaDB 11, volume dữ liệu |
| 4 | Authentication Server | `authentication-identity-server` | 8081 | Keycloak 26, realm `realm_523H0167` |
| 5 | Object Storage | `object-storage-server` | 9000 / 9001 | MinIO + Console |
| 6 | DNS Server | `internal-dns-server` | 1053/udp + tcp | Bind9, zone `cloud.local` |
| 7 | Monitoring | `monitoring-prometheus-server` (+ node-exporter) | 9090 / 9100 | 3 target: node, web, prometheus |
| 8 | Logging / Dashboard | `monitoring-grafana-dashboard-server` (+ Loki, Promtail) | 3000 / 3100 | Dashboard `System Health of 523H0167` |
| 9 | API Gateway | `api-gateway-proxy-server` | 80 | Nginx reverse proxy |

Tổng cộng **13 container** (9 server + web2 + node-exporter + Loki + Promtail).

---

## 3. Cấu trúc thư mục

```
huynhmanhphatminiclouddemo/
├── docker-compose.yml
├── README.md · TEST-RESULTS.md · HUONG-DAN-MO-RONG.md · NHUNG-GI-DA-LAM.md
├── web-frontend-server/                 # 1. Web (Dockerfile + Nginx + HTML)
│   ├── conf.default                     # có location /api/ để portal chạy cả :8080
│   └── html/
│       ├── index.html                   # portal: 9 service + kho tài liệu + đăng nhập
│       ├── assets/portal.css, portal.js
│       ├── students/                    # CRUD sinh viên (ẩn nút nếu không phải admin)
│       └── blog/                        # 3 bài + 22 ảnh
├── application-backend-server/          # 2. App (Flask)
│   ├── app.py                           # API, OIDC, MinIO, phân quyền
│   └── students.json
├── relational-database-server/          # 3. MariaDB
│   └── init/001_init.sql, 002_studentdb.sql
├── authentication-identity-server/      # 4. Keycloak
│   └── import/realm-export.json         # realm + user + client + role (để import)
├── object-storage-server/               # 5. MinIO
├── internal-dns-server/                 # 6. Bind9 + db.cloud.local
├── monitoring-prometheus-server/        # 7. Prometheus
├── monitoring-grafana-dashboard-server/ # 8. Grafana + Loki + Promtail
└── api-gateway-proxy-server/            # 9. Nginx reverse proxy
```

---

## 4. Chạy dự án

### 4.1. Local

```powershell
cd huynhmanhphatminiclouddemo
copy .env.example .env          # PUBLIC_HOST=localhost
docker compose pull web-frontend-server web-frontend-server2 application-backend-server
docker compose up -d
```

Mở `http://localhost/`.

> Nginx dùng `resolver 127.0.0.11` + `resolve` trong upstream nên **tự cập nhật IP**
> khi container bị recreate — không cần restart proxy nữa.

> Cổng **80** và **3306** phải trống. Nếu máy có Apache/MySQL, tắt trước.

### 4.2. AWS EC2

| Thông số | Giá trị |
|---|---|
| AMI | Ubuntu Server 24.04 LTS, **x86_64** |
| Instance | `t3.medium` (4 GB) trở lên |
| Storage | 30 GB gp3 |
| Security Group | 22 (IP của bạn), 80, 3000, 8080–8085, 9000–9001, 9090 |

```bash
git clone https://github.com/Manhphat2104/MiniCloud.git
cd MiniCloud/huynhmanhphatminiclouddemo

cp .env.example .env
nano .env                       # PUBLIC_HOST=<EC2_PUBLIC_IP>

docker compose pull web-frontend-server web-frontend-server2 application-backend-server
docker compose up -d --no-build
```

`PUBLIC_HOST` được dùng cho:

- `KC_HOSTNAME` → link đăng nhập Keycloak đúng IP
- `OIDC_ISSUER` → token có `iss` đúng, `/secure` không bị 401
- `PUBLIC_URL` → redirect URI sau khi đăng nhập
- `MINIO_PUBLIC_URL` → link ảnh public

> **Bắt buộc:** thêm redirect URI vào Keycloak client `web-portal`:
> `http://<EC2_PUBLIC_IP>/api/session/callback`
> (Keycloak Console → realm `realm_523H0167` → Clients → `web-portal` → Valid redirect URIs).

---

## 5. Tài khoản demo

| User | Mật khẩu | Realm role | Quyền |
|---|---|---|---|
| `sv01` | `sv01` | **admin** | upload/xoá file, thêm/sửa/xoá sinh viên |
| `sv02` | `sv02` | **viewer** | chỉ xem và tải |
| `admin` | `admin` | — | quản trị Keycloak Console |

Khách chưa đăng nhập vẫn xem được portal, blog, sinh viên và tải file.

---

## 6. Kiểm thử PHẦN BẮT BUỘC

Chạy lần lượt, kết quả ghi bên phải là thực tế trên máy.

### 6.1. Chín server hoạt động

```powershell
docker compose ps --format "{{.Name}}|{{.State}}"
```
→ **13/13 running**.

```powershell
curl.exe -s -o NUL -w "web8080   %{http_code}`n" http://localhost:8080/
curl.exe -s -o NUL -w "web2 8082 %{http_code}`n" http://localhost:8082/
curl.exe -s -o NUL -w "app 8085  %{http_code}`n" http://localhost:8085/hello
curl.exe -s -o NUL -w "keycloak  %{http_code}`n" http://localhost:8081/realms/realm_523H0167
curl.exe -s -o NUL -w "minio     %{http_code}`n" http://localhost:9001
curl.exe -s -o NUL -w "prom      %{http_code}`n" http://localhost:9090/-/ready
curl.exe -s -o NUL -w "grafana   %{http_code}`n" http://localhost:3000/api/health
curl.exe -s -o NUL -w "proxy     %{http_code}`n" http://localhost/
```
→ tất cả `200`.

### 6.2. Cùng network + phân giải tên

```powershell
docker exec api-gateway-proxy-server sh -c "getent hosts web-frontend-server application-backend-server relational-database-server"
```
→ cả 3 tên đều trả IP `172.20.0.x`.

```powershell
docker network inspect cloud-net --format "{{range .Containers}}{{.Name}} {{end}}"
```
→ liệt kê đủ 13 container.

### 6.3. Database (MariaDB + volume)

```powershell
docker exec relational-database-server mariadb -uroot -proot -e "USE minicloud; SHOW TABLES; SELECT * FROM notes;"
```
→ bảng `notes`, dòng `Hello from MariaDB!`.

```powershell
docker exec relational-database-server mariadb -uroot -proot -e "USE studentdb; SELECT * FROM students;"
```
→ 4 bản ghi `SV001`–`SV004`.

```powershell
docker inspect relational-database-server --format "{{range .Mounts}}{{.Source}} -> {{.Destination}}{{println}}{{end}}"
```
→ có `...\relational-database-server\data -> /var/lib/mysql`.

### 6.4. Object Storage

```powershell
docker exec object-storage-server sh -c "mc alias set local http://127.0.0.1:9000 minioadmin minioadmin; mc ls local"
docker exec object-storage-server sh -c "mc ls local/profile-pics; mc ls local/documents"
```
→ bucket `demo`, `profile-pics`, `documents`; có `avatar.jpg` và `report.pdf`.

```powershell
curl.exe -s -o NUL -w "avatar public = %{http_code}`n" http://localhost:9000/profile-pics/avatar.jpg
curl.exe -s -o NUL -w "pdf private   = %{http_code}`n" http://localhost:9000/documents/report.pdf
```
→ `200` và `403` (đúng policy public/private).

### 6.5. DNS

```powershell
docker exec internal-dns-server dig +short @127.0.0.1 web-frontend-server.cloud.local
docker exec internal-dns-server dig +short @127.0.0.1 app-backend.cloud.local
docker exec internal-dns-server dig +short @127.0.0.1 minio.cloud.local
docker exec internal-dns-server dig +short @127.0.0.1 keycloak.cloud.local
```
→ `10.10.10.10`, `10.10.10.20`, `10.10.10.30`, `10.10.10.40`.

### 6.6. Monitoring + Logging

```powershell
curl.exe -s "http://localhost:9090/api/v1/targets?state=active"
```
→ 3 target `node`, `web`, `prometheus` đều `"health":"up"`.

```powershell
curl.exe -s -u admin:admin "http://localhost:3000/api/search?query=System"
```
→ dashboard `System Health of 523H0167`.

```powershell
curl.exe -s "http://localhost:3100/loki/api/v1/label/job/values"
```
→ `{"status":"success","data":["docker"]}`.

### 6.7. Proxy route + round robin

```powershell
curl.exe -s -o NUL -w "home     %{http_code}`n" http://localhost/
curl.exe -s -o NUL -w "blog     %{http_code}`n" http://localhost/blog/
curl.exe -s -o NUL -w "auth     %{http_code}`n" http://localhost/auth/
curl.exe -s -o NUL -w "api      %{http_code}`n" http://localhost/api/hello
curl.exe -s -o NUL -w "student  %{http_code}`n" http://localhost/student/
```
→ `200 / 200 / 302 / 200 / 200`.

```powershell
1..6 | ForEach-Object { (curl.exe -s -D - -o NUL http://localhost/ | Select-String 'X-Served-By').ToString().Trim() }
```
→ luân phiên `web-frontend-server1` / `web-frontend-server2`.

### 6.8. Docker Hub + EC2

```powershell
docker manifest inspect phathuynh2104/web:dev
docker manifest inspect phathuynh2104/app:dev
```
→ có `linux/amd64`.

```powershell
curl.exe -s -o NUL -w "%{http_code}`n" http://<EC2_PUBLIC_IP>/
```
→ `200` (public IP, không cần đăng nhập).

---

## 7. Kiểm thử PHẦN MỞ RỘNG (10 mục)

### Mục 1 — Blog ≥ 3 bài + ảnh + link về trang chủ

```powershell
curl.exe -s -o NUL -w "blog index %{http_code}`n" http://localhost/blog/
1..3 | ForEach-Object { curl.exe -s -o NUL -w "blog$_ %{http_code}`n" "http://localhost/blog/blog$_.html" }
(Get-ChildItem web-frontend-server\html\blog\images -File).Count
```
→ 4 đường dẫn `200`, **22 ảnh**. Mỗi bài có link "Về trang Blog" + "Về trang chủ".

### Mục 2 — API `/student` đọc JSON (5 sinh viên)

```powershell
curl.exe -s http://localhost/api/student
( curl.exe -s http://localhost/api/student | ConvertFrom-Json ).Count
```
→ JSON 5 sinh viên (`id, name, major, gpa`), count = **5**.

### Mục 3 — `studentdb.students` + CRUD

```powershell
curl.exe -s http://localhost/api/students-db
docker exec relational-database-server mariadb -uroot -proot -e "USE studentdb; SELECT COUNT(*) FROM students;"
```
→ `count = 4`, DB 4 dòng.

CRUD cần admin (xem mục 11):

```powershell
# chưa đăng nhập -> 401
curl.exe -s -o NUL -w "%{http_code}`n" -X POST http://localhost/api/students-db -H "Content-Type: application/json" -d "{}"
```

### Mục 4 — Keycloak realm + user + client + token

```powershell
curl.exe -s -o NUL -w "realm   %{http_code}`n" http://localhost:8081/realms/realm_523H0167
curl.exe -s -o NUL -w "auth    %{http_code}`n" http://localhost/auth/

$BODY = "grant_type=password&client_id=flask-app&username=sv01&password=sv01&scope=openid"
$TOKEN = (curl.exe -s -X POST "http://localhost:8081/realms/realm_523H0167/protocol/openid-connect/token" -d $BODY | ConvertFrom-Json).access_token

curl.exe -s -o NUL -w "no token  %{http_code}`n" http://localhost/api/secure
curl.exe -s -o NUL -w "with token %{http_code}`n" -H "Authorization: Bearer $TOKEN" http://localhost/api/secure
curl.exe -s -H "Authorization: Bearer $TOKEN" http://localhost/api/secure
```
→ realm `200`, auth `302`, `/secure` lần lượt **401** rồi **200**:

```json
{"message":"Secure resource OK","preferred_username":"sv01"}
```

### Mục 5 — MinIO `profile-pics` + `documents`

```powershell
curl.exe -s http://localhost/api/files/images
curl.exe -s http://localhost/api/files/documents
curl.exe -s -o NUL -w "avatar %{http_code}`n" http://localhost:9000/profile-pics/avatar.jpg
curl.exe -s -o "$env:TEMP\report.pdf" -w "pdf %{http_code}`n" http://localhost/api/files/documents/report.pdf/download
```
→ `profile-pics/avatar.jpg` public `200`; `documents/report.pdf` private (gọi trực tiếp `403`, tải qua API `200`).

### Mục 6 — Thêm bản ghi DNS + `dig`

```powershell
docker exec internal-dns-server cat /etc/bind/db.cloud.local
```
→ 4 bản ghi A: web `10.10.10.10`, app `10.10.10.20`, minio `10.10.10.30`, keycloak `10.10.10.40`.

### Mục 7 — Prometheus job `web`

```powershell
curl.exe -s -o NUL -w "metrics %{http_code}`n" http://localhost:8080/metrics
curl.exe -s "http://localhost:9090/api/v1/targets?state=active"
```
→ `/metrics` `200`; job `web` = `http://web-frontend-server:80/metrics` **UP**.

### Mục 8 — Dashboard Grafana ≥ 3 biểu đồ

```powershell
curl.exe -s -u admin:admin "http://localhost:3000/api/search?query=System"
```
→ `System Health of 523H0167`, **4 panel**: CPU, Memory, Network, Logs (Loki).

### Mục 9 — Proxy route `/student/`

```powershell
curl.exe -s -o NUL -w "student/ %{http_code}`n" http://localhost/student/
curl.exe -s http://localhost/student/
```
→ `200`, JSON danh sách sinh viên (proxy chuyển sang backend `/student`).

### Mục 10 — Load balancing 2 web server

```powershell
1..6 | ForEach-Object { (curl.exe -s -D - -o NUL http://localhost/ | Select-String 'X-Served-By').ToString().Trim() }
```
→ server1 → server2 → server1 → server2 … (Round Robin).

---

## 8. Mở rộng thêm — Cloud Portal (đăng nhập + upload)

### 8.1. Trang chủ hiển thị 9 server

```powershell
curl.exe -s http://localhost/api/services
```
→ `count = 9`, `up = 9`, mỗi service có `status`, `container`, `port`, `has_ui`.

```powershell
docker stop monitoring-logging-server
curl.exe -s http://localhost/api/services      # "grafana": "down"
docker start monitoring-logging-server
```
→ card Logging chuyển đỏ rồi xanh lại.

### 8.2. Đăng nhập + phân quyền

- Mở `http://localhost/` → **Đăng nhập** → `sv01 / sv01` → header hiện `sv01 · admin`.
- Đăng xuất, đăng nhập `sv02 / sv02` → header hiện `sv02 · viewer`.

```powershell
# sv02 upload -> 403
curl.exe -s -b <cookie_sv02> -o NUL -w "%{http_code}`n" -X POST http://localhost/api/files/upload -F "file=@test.pdf"

# sv01 upload -> 201
curl.exe -s -b <cookie_sv01> -w "%{http_code}`n" -X POST http://localhost/api/files/upload -F "file=@test.pdf"
```

Phân quyền:

| Hành động | Khách | viewer | admin |
|---|---|---|---|
| Xem portal / blog / sinh viên | ✅ | ✅ | ✅ |
| Tải ảnh, PDF | ✅ | ✅ | ✅ |
| Upload / xoá file | 401 | 403 | ✅ |
| Thêm / sửa / xoá sinh viên | 401 | 403 | ✅ |

### 8.3. Upload ảnh + PDF

- Ảnh: JPG/JPEG/PNG/WEBP/GIF → bucket `profile-pics` (public, hiện thumbnail).
- PDF → bucket `documents` (private, tải qua Flask).
- Giới hạn 10 MB, kiểm tra cả phần mở rộng lẫn magic bytes.
- Nginx đã set `client_max_body_size 20m` để không lỗi 413.

```powershell
# kiem tra file da len bucket
curl.exe -s http://localhost/api/files/images
curl.exe -s http://localhost/api/files/documents
```

---

## 9. Keycloak: realm, client, role

| Thành phần | Giá trị |
|---|---|
| Realm | `realm_523H0167` |
| Client API (mục 4) | `flask-app` — public, Direct Access Grants ON |
| Client portal | `web-portal` — confidential, Standard Flow + PKCE, secret `web-portal-secret-523H0167` |
| Realm roles | `admin`, `viewer` |
| User | `sv01` → admin, `sv02` → viewer |

File `authentication-identity-server/import/realm-export.json` chứa toàn bộ realm + user + role.
Compose mount thư mục này vào `/opt/keycloak/data/import` và chạy `start-dev --import-realm`,
nên trên EC2 (data trống) realm tự được tạo.

Endpoint:

| Mục đích | URL |
|---|---|
| Token | `http://<host>:8081/realms/realm_523H0167/protocol/openid-connect/token` |
| Authorize | `http://<host>:8081/realms/realm_523H0167/protocol/openid-connect/auth` |
| JWKS | `http://<host>:8081/realms/realm_523H0167/protocol/openid-connect/certs` |
| Console | `http://<host>:8081/` (admin/admin) |

Luồng portal dùng **Authorization Code + PKCE**:

```
/api/session/login → Keycloak → /api/session/callback → session cookie → /api/session/me
```

---

## 10. Khác biệt so với file Word (có lý do)

1. **MinIO**: `minio/minio` bị xoá khỏi Docker Hub, bản mới bỏ Console → dùng
   `bitnamilegacy/minio:2025.3.12` (vẫn là MinIO, còn Console).
2. **Bind9**: image không include `named.conf.local` → thêm `named.conf` riêng để include zone.
3. **`restart: unless-stopped`**: bổ sung cho **tất cả** service (file mẫu chỉ có 2).
4. **Volume dữ liệu**: thêm `relational-database-server/data` và `prometheus-data`
   để không mất dữ liệu khi xoá container.
5. **Loki + provisioning**: thêm Loki/Promtail + datasource Prometheus/Loki tự nạp.
6. **Alias mạng** (`web`, `db`, `keycloak`, `minio`, `dns-server`, `prometheus`, `grafana`,
   `app-server`, `loki`) để các lệnh `ping web`, `ping db`… đúng như đề.
7. **Web server 2 + round robin**: thêm `web-frontend-server2` (:8082) cho mục 10.
8. **Cổng 80 và 3306 phải trống** khi chạy local.

---

## 11. Lỗi thường gặp

| Hiện tượng | Nguyên nhân | Xử lý |
|---|---|---|
| `/api/*` trả 502 | Nginx giữ IP cũ (bản cấu hình cũ) | bản hiện tại tự resolve qua `resolver 127.0.0.11`; nếu vẫn lỗi: `docker restart api-gateway-proxy-server` |
| Upload báo 413 | Body quá lớn | Kiểm tra `client_max_body_size 20m` ở proxy và web |
| `/api/session/login` redirect về `localhost` trên EC2 | `PUBLIC_HOST` chưa đúng | sửa `.env`, `docker compose up -d authentication-identity-server application-backend-server` |
| `/secure` 401 `Invalid issuer` | `OIDC_ISSUER` vẫn `localhost` | như trên |
| Đăng nhập lỗi `Invalid redirect uri` | Client thiếu URI EC2 | thêm `http://<IP>/api/session/callback` vào client `web-portal` |
| `manifest unknown` khi pull | thiếu tag `:dev` | dùng đúng `phathuynh2104/web:dev` |
| Container `Exit 137` | thiếu RAM | dùng `t3.medium`+ hoặc tăng RAM Docker Desktop ≥ 6 GB |
| Dashboard Grafana trống | volume `grafana-data` cũ | `docker compose down` + `docker volume rm huynhmanhphatminiclouddemo_grafana-data` |

---

## 12. Kết quả

- **Bắt buộc:** 9/9 server chạy, 13 container, proxy + round robin, volume DB/Prometheus,
  image public trên Docker Hub, deploy EC2 qua public IP.
- **Mở rộng:** **10/10 mục** (blog, JSON API, MariaDB CRUD, Keycloak OIDC, MinIO public/private,
  DNS, Prometheus target, Grafana dashboard, proxy `/student/`, load balancing)
  **+ portal 9 service + đăng nhập phân quyền + upload ảnh/PDF**.

Log kiểm thử chi tiết: `TEST-RESULTS.md`.
Hướng dẫn demo từng mục: `HUONG-DAN-MO-RONG.md`.
Tổng hợp toàn bộ việc đã làm: `NHUNG-GI-DA-LAM.md`.
