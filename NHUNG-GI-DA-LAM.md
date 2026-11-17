# Những gì đã làm — MyMiniCloud (523H0167 · 523H0169)

Tài liệu tổng hợp toàn bộ công việc đã thực hiện cho đồ án cuối kỳ môn Điện toán đám mây:
từ 9 server bắt buộc, 10 mục mở rộng, đến Cloud Portal có đăng nhập và upload file.

- **Sinh viên:** Huỳnh Mạnh Phát `523H0167` · Phạm Nguyễn Thanh Phong `523H0169`
- **Repo:** `https://github.com/Manhphat2104/MiniCloud.git` (nhánh `main`, thư mục `huynhmanhphatminiclouddemo`)
- **Docker Hub:** `phathuynh2104/web:dev`, `phathuynh2104/app:dev`
- **Cập nhật lần cuối:** 17/11/2026

---

## 1. Kết quả tổng quan

| Hạng mục | Yêu cầu | Kết quả |
|---|---|---|
| Phần bắt buộc | 9 loại server chạy bằng Docker Compose, chung network | ✅ 9/9 server, 13 container |
| Phần mở rộng | Làm các mục 1–10 trong đề | ✅ 10/10 mục |
| Cloud Portal | Trang chủ hiển thị 9 server + đăng nhập + upload ảnh/PDF | ✅ Hoàn thành |
| Phân quyền | Chỉ admin được sửa; ai cũng xem/tải được | ✅ Keycloak role `admin` / `viewer` |
| Docker Hub | Image tự chế, public, `linux/amd64` | ✅ Đã push bản mới nhất |
| Tài liệu | README + log kiểm thử + hướng dẫn demo | ✅ 4 file markdown |
| Deploy EC2 | Chạy bằng public IP | ⏳ Chờ bật instance / IP mới |
| Video demo + báo cáo | Video minh chứng, báo cáo 5 chương | ⏳ Chưa làm |

---

## 2. Hệ thống đang chạy

13 container trên network `cloud-net`:

| # | Server | Container | Cổng host |
|---|---|---|---|
| 1 | Web Server | `web-frontend-server` + `web-frontend-server2` | 8080, 8082 |
| 2 | Application Server | `application-backend-server` | 8085 |
| 3 | Database Server | `relational-database-server` | 3306 |
| 4 | Authentication Server | `authentication-identity-server` | 8081 |
| 5 | Object Storage | `object-storage-server` | 9000, 9001 |
| 6 | DNS Server | `internal-dns-server` | 1053 |
| 7 | Monitoring | `monitoring-prometheus-server` + `monitoring-node-exporter-server` | 9090, 9100 |
| 8 | Logging / Dashboard | `monitoring-grafana-dashboard-server` + `monitoring-logging-server` + `monitoring-promtail` | 3000, 3100 |
| 9 | API Gateway | `api-gateway-proxy-server` | 80 |

Kiểm tra nhanh:

```powershell
docker compose ps --format "{{.Name}}|{{.State}}"
curl.exe -s http://localhost/api/services      # count=9, up=9
```

---

## 3. Phần bắt buộc — đã kiểm thử

| Nhóm | Nội dung | Minh chứng |
|---|---|---|
| 3.1 | 9 server hoạt động, đúng cổng | Tất cả endpoint trả `200` |
| 3.2 | Cùng network, phân giải tên container | `getent hosts` trả `172.20.0.x`, `cloud-net` đủ 13 container |
| 3.3 | MariaDB + dữ liệu + volume | `notes` có dữ liệu, `students` 4 dòng, mount `./relational-database-server/data` |
| 3.4 | MinIO bucket + Console | Bucket `demo`, `profile-pics` (public), `documents` (private) |
| 3.5 | DNS Bind9 + zone `cloud.local` | `dig` trả `10.10.10.10/.20/.30/.40` |
| 3.6 | Prometheus + Grafana + Loki | 3 target `up`, dashboard `System Health of 523H0167` |
| 3.7 | Proxy route + round robin | `/`, `/blog/`, `/auth/`, `/api/`, `/student/` đúng; `X-Served-By` luân phiên |
| 3.8 | Docker Hub + EC2 | Manifest `linux/amd64`; EC2 chạy sau khi có IP |

Chi tiết từng lệnh: xem `TEST-RESULTS.md` (mục 1–8 của README).

---

## 4. Phần mở rộng — 10/10 mục

| # | Mục | Đã làm |
|---|---|---|
| 1 | Blog cá nhân | 3 bài (Đà Nẵng, Đài Loan, Nhật Bản), 22 ảnh, link về trang chủ/blog |
| 2 | API `/student` đọc JSON | 5 sinh viên với `id, name, major, gpa` |
| 3 | CSDL `studentdb` + CRUD | Bảng `students` (4 seed), CRUD qua API, có phân quyền admin |
| 4 | Keycloak realm + client + token | Realm `realm_523H0167`, client `flask-app`, `/api/secure` 401 → 200 |
| 5 | MinIO bucket avatar/PDF | `profile-pics` public (`avatar.jpg` → 200), `documents` private (403 khi truy cập trực tiếp) |
| 6 | DNS thêm bản ghi + `dig` | 4 bản ghi A giữ đúng `10.10.10.x` như đề |
| 7 | Prometheus target `web` | `/metrics` của web trả 200, job `web` UP |
| 8 | Grafana ≥ 3 biểu đồ | 4 panel: CPU, Memory, Network, Logs (Loki) |
| 9 | Proxy route `/student/` | `proxy_pass` có URI, thay tiền tố `/student/` → `/student` |
| 10 | Load balancing 2 web server | Nginx round robin `web-frontend-server1` ⇄ `web-frontend-server2` |

Hướng dẫn demo từng mục: `HUONG-DAN-MO-RONG.md`.

---

## 5. Cloud Portal (phần làm thêm)

Trang chủ `http://localhost/` gồm 3 khối mới:

### 5.1. Hạ tầng đang vận hành

- Đúng **9 card** server bắt buộc, mỗi card có đèn xanh/đỏ, tên container, cổng, mô tả.
- Dữ liệu từ `GET /api/services` (backend kiểm tra song song 9 server, cache 10 giây).
- Tự refresh mỗi **15 giây**, có nút "↻ Kiểm tra lại".
- Card có giao diện → bấm mở server đó ở **tab mới** (`:8085`, `:8081`, `:9001`, `:9090`, `:3000`, `:8080`...).
- Database và DNS không có UI → hiện toast hướng dẫn lệnh `docker exec`.

### 5.2. Đăng nhập Keycloak

- Authorization Code + **PKCE S256**, state chống CSRF.
- Session lưu server-side (dict), cookie `sid` HttpOnly + SameSite=Lax.
- Tự refresh access token; logout xoá session + gọi end-session của Keycloak.
- Header hiển thị `username · admin/viewer` và nút Đăng xuất.

### 5.3. Kho tài liệu (MinIO)

| Loại | Bucket | Quyền | Cách tải |
|---|---|---|---|
| Ảnh (jpg/jpeg/png/webp/gif) | `profile-pics` | Public | Link trực tiếp `:9000/profile-pics/<file>` |
| PDF | `documents` | Private | Qua Flask `/api/files/documents/<file>/download` |

- Upload kéo-thả hoặc chọn file; giới hạn **10 MB**; kiểm tra cả phần mở rộng và **magic bytes**.
- `client_max_body_size 20m` ở proxy và web để không bị 413.
- Chỉ **admin** thấy vùng upload và nút Xoá.

### 5.4. Bảng phân quyền

| Hành động | Khách | viewer (`sv02`) | admin (`sv01`) |
|---|---|---|---|
| Xem portal / blog / danh sách sinh viên | ✅ | ✅ | ✅ |
| Tải ảnh, PDF | ✅ | ✅ | ✅ |
| Upload / xoá file | 401 | 403 | ✅ |
| Thêm / sửa / xoá sinh viên | 401 | 403 | ✅ |
| Thấy nút Thêm/Sửa/Xoá trên web | ❌ | ❌ | ✅ |

Tài khoản: `sv01 / sv01` (admin), `sv02 / sv02` (viewer), Keycloak Console `admin / admin`.

---

## 6. Keycloak: client và luồng phân quyền

### 6.1. Hai client

| | `flask-app` | `web-portal` |
|---|---|---|
| Mục đích | Test mục 4 (`/secure`) | Đăng nhập portal |
| Loại | Public (không secret) | Confidential (`web-portal-secret-523H0167`) |
| Flow | Standard + Direct Access Grants | Standard Flow + PKCE S256 |
| Redirect URI | `*` | `http://localhost/api/session/callback` (+ `:8080`, `:8082`, IP EC2) |

### 6.2. Luồng đăng nhập

```
/api/session/login  →  Keycloak /auth (client_id, redirect_uri, state, PKCE)
                    →  user nhập sv01/sv01
                    →  /api/session/callback?code=...
                    →  Flask đổi code (client_secret + code_verifier) lấy token
                    →  token có realm_access.roles = ["admin", ...]
                    →  tạo session + cookie sid
```

### 6.3. Phân quyền ở backend

| Vị trí | Việc làm |
|---|---|
| `app.py:85` `_roles_from()` | Lấy `realm_access.roles` từ token |
| `app.py:125` `current_user()` | `is_admin = "admin" in roles` |
| `app.py:137` `require_admin()` | Chưa login → **401**, không phải admin → **403** |
| `app.py:426, 472, 542, 562, 585` | Gắn cho upload/xoá file và CRUD sinh viên |

Role được gán trong Keycloak (Console → Users → Role mapping), đưa vào token nhờ client scope `roles`
(mapper `realm roles` → claim `realm_access.roles`).

---

## 7. File mới / sửa / xoá và tác dụng

### 7.1. File mới

| File | Tác dụng |
|---|---|
| `application-backend-server/app.py`* | Viết lại backend: OIDC PKCE, session, `require_admin`, `/services` 9 server, API MinIO, bảo vệ CRUD |
| `web-frontend-server/html/assets/portal.js` | Logic portal: 9 card, login/logout, upload, danh sách/xoá file, toast |
| `web-frontend-server/html/assets/portal.css` | Style portal: lưới card, đèn trạng thái, vùng upload, toast, responsive |
| `authentication-identity-server/import/realm-export.json` | Realm + user + client `web-portal` + role `admin`/`viewer` + mapping; dùng cho `--import-realm` |
| `.env.example` | Mẫu `PUBLIC_HOST` cho local/EC2 |
| `TEST-RESULTS.md` | Log kết quả kiểm thử thực tế (gồm mục 11 portal) |
| `HUONG-DAN-MO-RONG.md` | Hướng dẫn demo 10 mục mở rộng |
| `NHUNG-GI-DA-LAM.md` | File này — tổng hợp công việc |

\* file cũ nhưng thay đổi gần như toàn bộ nội dung.

### 7.2. File sửa

| File | Thay đổi chính |
|---|---|
| `docker-compose.yml` | Env OIDC/MinIO/`PUBLIC_HOST`; volume DB + Prometheus; Keycloak `--import-realm` + mount `import/` |
| `api-gateway-proxy-server/nginx.conf` | `client_max_body_size 20m`; `resolver 127.0.0.11` + `resolve` upstream; `/api/`, `/student/`, `/auth/` dùng biến (hết 502 khi recreate) |
| `web-frontend-server/conf.default` | `location /api/` cho `:8080`/`:8082`; resolver; cache HTML `no-store`, asset 1 giờ |
| `web-frontend-server/html/index.html` | Nav Hạ tầng/Kho tài liệu, khu đăng nhập, section 9 card, section kho tài liệu |
| `web-frontend-server/html/students/index.html` | Ẩn nút CRUD + banner "chế độ chỉ xem" nếu không phải admin |
| `web-frontend-server/html/students/students.css` | Style banner `.perm-note` |
| `application-backend-server/Dockerfile` | Thêm `minio` vào `pip install` |
| `README.md` | Viết lại thành tài liệu chính thức (kiến trúc, test, mở rộng, portal, lỗi thường gặp) |
| `.gitignore` | Bỏ commit `authentication-identity-server/data/` (H2 runtime) |

### 7.3. File xoá / di chuyển

| File | Xử lý | Lý do |
|---|---|---|
| `authentication-identity-server/realm-export.json` | → `authentication-identity-server/import/realm-export.json` | Đúng thư mục mount cho `--import-realm` |
| `authentication-identity-server/data/h2/keycloakdb.mv.db` | Xoá khỏi Git | File nhị phân runtime ~1.8 MB |
| `authentication-identity-server/data/h2/keycloakdb.trace.db` | Xoá khỏi Git | Log runtime |
| `authentication-identity-server/data/export/realm_523H0167-realm.json` | Xoá khỏi Git | Bản export tạm |

---

## 8. Lỗi đã gặp và cách xử lý

| Lỗi | Nguyên nhân | Cách xử lý |
|---|---|---|
| `502 Bad Gateway` ở `/api/*` | Nginx cache IP container lúc start, container recreate đổi IP | Thêm `resolver 127.0.0.11 valid=10s` + `resolve` trong upstream; hết phải restart proxy |
| F5 không thấy round robin đổi | Trình duyệt cache HTML (không có `Cache-Control`) | HTML `no-store`, asset `max-age=3600` (tránh asset ăn lượt round robin) |
| `Cannot parse the JSON` khi tạo role mapping | PowerShell ghi JSON có BOM | Ghi file bằng `UTF8Encoding($false)` |
| Upload 413 | Body lớn hơn giới hạn Nginx | `client_max_body_size 20m` ở proxy và web |
| PDF vào nhầm bucket ảnh | Upload thủ công trước khi có portal | Chuyển sang `documents` bằng SDK MinIO, xoá khỏi `profile-pics` |
| Đăng nhập lỗi `Invalid redirect uri` | Client `web-portal` thiếu URI của host mới | Thêm `http://<host>/api/session/callback` |
| `/secure` 401 `Invalid issuer` | `OIDC_ISSUER` còn `localhost` khi deploy EC2 | Sửa `PUBLIC_HOST` trong `.env` rồi up lại app + Keycloak |
| `manifest unknown` khi pull | Thiếu tag `:dev` | Dùng đúng `phathuynh2104/web:dev` / `app:dev` |
| Container `Exit 137` | Thiếu RAM | Dùng `t3.medium`+ hoặc tăng RAM Docker Desktop ≥ 6 GB |

---

## 9. Lịch sử commit

| Commit | Nội dung |
|---|---|
| `125b12e` | Initial commit |
| `81be269` | add data |
| `a5f665c` | Cloud Portal: 9 server + đăng nhập Keycloak phân quyền + upload ảnh/PDF lên MinIO |
| `3998440` | Fix 502: Nginx tự resolve lại IP container |
| `313e553` | Tắt cache HTML để F5 thấy round robin |
| `8c472eb` | Chỉ tắt cache HTML, giữ cache asset để round robin hiển thị đúng |

Tất cả đã push lên `origin/main`.

---

## 10. Việc còn lại

1. **EC2:** bật instance → lấy Public IP → tạo `.env` với `PUBLIC_HOST=<IP>` →
   `docker compose pull ...` → `up -d --no-build`.
2. Thêm redirect URI `http://<IP>/api/session/callback` cho client `web-portal`.
3. Chụp ảnh minh chứng: 9 card xanh, sv01 upload OK, sv02 bị 403, PDF tải được, nút sửa bị ẩn.
4. Quay video demo (bắt buộc + mở rộng + portal).
5. Hoàn thiện báo cáo 5 chương (dùng README + TEST-RESULTS làm nguồn).

---

## 11. Chạy lại nhanh

```powershell
cd huynhmanhphatminiclouddemo
copy .env.example .env            # PUBLIC_HOST=localhost
docker compose up -d --no-build
curl.exe -s http://localhost/api/services    # count=9 up=9
```

Mở `http://localhost/` → Đăng nhập bằng `sv01 / sv01`.

> Nếu vừa recreate container mà thấy 502 vài giây rồi tự hết: đó là DNS TTL 10 giây,
> không cần restart gì. Nếu kéo dài: `docker restart api-gateway-proxy-server`.
