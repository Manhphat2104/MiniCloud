# Bảng thay đổi — MyMiniCloud

Danh sách đầy đủ file **mới / sửa / xoá** trong đợt bổ sung Cloud Portal, kèm tác dụng của từng file
và ảnh hưởng khi triển khai (cần build lại image nào, restart container nào).

- **Repo:** `https://github.com/Manhphat2104/MiniCloud.git` — nhánh `main`
- **Thư mục gốc:** `huynhmanhphatminiclouddemo/`
- **Mốc so sánh:** `81be269` (trước khi làm portal) → `5e0f8e3`
- **Tổng hợp:** 19 file thay đổi trong đợt chính + 5 commit, `+2133 / −4232` dòng (phần lớn là xoá dữ liệu Keycloak khỏi Git)

---

## 1. Tổng quan số lượng

| Loại | Số file | Ghi chú |
|---|---|---|
| File mới | 7 | Gồm backend/frontend portal, realm export, 3 tài liệu, `.env.example` |
| File sửa | 10 | Compose, Nginx ×2, app, Dockerfile, HTML/CSS ×3, `.gitignore`, README |
| File xoá khỏi Git | 3 | Dữ liệu runtime của Keycloak (H2 DB + export tạm) |
| File di chuyển | 1 | `realm-export.json` → `import/realm-export.json` |
| Bản thân file này | 1 | `BANG-THAY-DOI.md` |

---

## 2. File mới

| # | Đường dẫn | Dòng | Tác dụng | Ai dùng |
|---|---|---|---|---|
| 1 | `application-backend-server/app.py`* | +474 / −12 | Viết lại backend: OIDC Authorization Code + PKCE, session server-side, `require_admin`, `/services` kiểm tra 9 server, API MinIO (list/upload/download/delete) | API Gateway, web, trình duyệt |
| 2 | `web-frontend-server/html/assets/portal.js` | +267 | Logic Cloud Portal: fetch 9 server, render card, login/logout, upload kéo-thả, danh sách + xoá file, toast lỗi | Trang chủ |
| 3 | `web-frontend-server/html/assets/portal.css` | +125 | Style portal: lưới 3 cột card, đèn xanh/đỏ, vùng upload, danh sách file, header đăng nhập, responsive | Trang chủ |
| 4 | `authentication-identity-server/import/realm-export.json` | +53 / −2 | Realm `realm_523H0167` đầy đủ: 2 user, 2 client, role `admin`/`viewer` + mapping; dùng cho `start-dev --import-realm` | Keycloak (tự import khi data trống) |
| 5 | `.env.example` | +5 | Mẫu biến `PUBLIC_HOST` cho local và EC2 | Người triển khai |
| 6 | `TEST-RESULTS.md` | +302 | Log kết quả kiểm thử thực tế: 13 container, mục bắt buộc, mục 5 MinIO, mục 11 portal, mục 11.5 recreate | Báo cáo / chấm bài |
| 7 | `HUONG-DAN-MO-RONG.md` | +457 | Hướng dẫn demo từng mục mở rộng 1–10 (lệnh chạy + kết quả mong đợi) | Demo / báo cáo |
| 8 | `NHUNG-GI-DA-LAM.md` | +265 | Tổng hợp toàn bộ công việc đã thực hiện | Báo cáo |

\* `app.py` là file cũ nhưng nội dung được thay gần như hoàn toàn nên xếp vào nhóm "mới về nội dung".

---

## 3. File sửa

| # | Đường dẫn | +/− | Nội dung thay đổi chính | Ảnh hưởng |
|---|---|---|---|---|
| 1 | `docker-compose.yml` | +17 / −3 | Thêm env `OIDC_*`, `MINIO_*`, `PUBLIC_URL`, `MAX_UPLOAD_MB` cho app; `PUBLIC_HOST` cho `KC_HOSTNAME`; volume `relational-database-server/data` và `prometheus-data`; Keycloak `start-dev --import-realm` + mount `import/` | Phải `docker compose up -d` lại để nhận env/volume |
| 2 | `api-gateway-proxy-server/nginx.conf` | +19 / −5 | `client_max_body_size 20m`; `resolver 127.0.0.11 valid=10s`; upstream `resolve`; `/api/`, `/student/`, `/auth/` dùng biến + `rewrite` | Restart proxy (mount file, không cần build) |
| 3 | `web-frontend-server/conf.default` | +25 | Thêm `location /api/` (portal chạy ở `:8080`/`:8082`); resolver; `map $cache_control` (HTML `no-store`, asset 1 giờ); `client_max_body_size 20m` | **Build lại image web** rồi recreate 2 web server |
| 4 | `web-frontend-server/html/index.html` | +46 / −3 | Nav **Hạ tầng / Kho tài liệu**; khu đăng nhập header; section 9 card; section kho tài liệu (upload + 2 bảng file); `#toasts`; nạp `portal.js` | **Build lại image web** |
| 5 | `web-frontend-server/html/students/index.html` | +19 / −3 | Gọi `/api/session/me` → `IS_ADMIN`; ẩn nút Thêm/Sửa/Xoá; banner "chế độ chỉ xem" | **Build lại image web** |
| 6 | `web-frontend-server/html/students/students.css` | +7 / −1 | Style banner `.perm-note` | **Build lại image web** |
| 7 | `application-backend-server/Dockerfile` | +1 / −1 | Thêm package `minio` vào `pip install` | **Build lại image app** |
| 8 | `README.md` | +359 / −277 | Viết lại thành tài liệu chính thức: kiến trúc, 9 server, chạy local/EC2, 8 nhóm test bắt buộc, 10 mục mở rộng, portal, khác biệt so với file Word, lỗi thường gặp | Không ảnh hưởng runtime |
| 9 | `.gitignore` | +3 | Bỏ commit `authentication-identity-server/data/` (H2 runtime) | Không ảnh hưởng runtime |
| 10 | `NHUNG-GI-DA-LAM.md` | +265 | Tạo file tổng hợp công việc (commit `5e0f8e3`) | Không ảnh hưởng runtime |

---

## 4. File xoá / di chuyển

| Đường dẫn | Xử lý | Lý do |
|---|---|---|
| `authentication-identity-server/data/h2/keycloakdb.mv.db` | Xoá khỏi Git (`git rm --cached`) | File nhị phân runtime ~1.8 MB, đổi liên tục |
| `authentication-identity-server/data/h2/keycloakdb.trace.db` | Xoá khỏi Git | Log H2 runtime |
| `authentication-identity-server/data/export/realm_523H0167-realm.json` | Xoá khỏi Git | Bản export tạm, đã thay bằng file trong `import/` |
| `authentication-identity-server/realm-export.json` | **Di chuyển** → `authentication-identity-server/import/realm-export.json` | Đúng thư mục được mount cho `--import-realm` |

> Dữ liệu vẫn còn trên máy (thư mục `authentication-identity-server/data/` bị gitignore),
> chỉ không đưa lên GitHub nữa.

---

## 5. Thay đổi cấu hình (không phải file code)

### 5.1. Biến môi trường mới

| Service | Biến | Giá trị | Tác dụng |
|---|---|---|---|
| `application-backend-server` | `OIDC_ISSUER` | `http://${PUBLIC_HOST}:8081/realms/realm_523H0167` | Địa chỉ công khai để validate token |
| | `OIDC_JWKS_URL` | `http://authentication-identity-server:8080/.../certs` | Lấy public key (gọi nội bộ Docker) |
| | `OIDC_INTERNAL` | `http://authentication-identity-server:8080/...` | Đổi code/refresh token |
| | `OIDC_CLIENT_ID` / `OIDC_CLIENT_SECRET` | `web-portal` / `web-portal-secret-523H0167` | Client dùng cho portal |
| | `PUBLIC_URL` | `http://${PUBLIC_HOST}` | Redirect URI sau đăng nhập |
| | `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY` | `http://object-storage-server:9000`, `minioadmin` | Gọi MinIO |
| | `MINIO_PUBLIC_URL` | `http://${PUBLIC_HOST}:9000` | Link ảnh public |
| | `MAX_UPLOAD_MB` | `10` | Giới hạn upload |
| `authentication-identity-server` | `KC_HOSTNAME` | `http://${PUBLIC_HOST}:8081` | Keycloak sinh URL đúng host |

### 5.2. Volume mới

| Volume | Mount | Tác dụng |
|---|---|---|
| `./relational-database-server/data` | `/var/lib/mysql` | Giữ dữ liệu MariaDB khi xoá container |
| `prometheus-data` (named) | `/prometheus` | Giữ metric Prometheus |
| `./authentication-identity-server/import` | `/opt/keycloak/data/import:ro` | Nguồn realm để tự import |

### 5.3. Thay đổi Nginx

| File | Thay đổi | Lý do |
|---|---|---|
| `api-gateway-proxy-server/nginx.conf` | `client_max_body_size 20m` | Upload 10 MB không bị 413 |
| | `resolver 127.0.0.11 valid=10s ipv6=off` | Docker DNS, resolve lại khi container đổi IP |
| | `upstream web_backend { zone ...; server ... resolve; }` | Round robin vẫn đúng sau khi recreate |
| | `/api/`, `/student/`, `/auth/` dùng `set $var` + `rewrite` | Tránh cache IP cũ → hết 502 |
| `web-frontend-server/conf.default` | `location /api/` proxy sang backend | Portal hoạt động khi mở thẳng `:8080`/`:8082` |
| | `map $uri $cache_control` | HTML `no-store` (F5 thấy round robin), asset `max-age=3600` |
| | `add_header X-Served-By $hostname` (giữ nguyên) | Chứng minh round robin |

### 5.4. Thay đổi trên Keycloak (runtime + export)

| Hạng mục | Giá trị |
|---|---|
| Realm | `realm_523H0167` |
| Realm roles mới | `admin`, `viewer` |
| Client mới | `web-portal` — confidential, secret `web-portal-secret-523H0167`, Standard Flow + PKCE `S256`, Direct Access Grants OFF |
| Client cũ | `flask-app` — public, Direct Access Grants ON (giữ cho mục 4) |
| Role mapping | `sv01` → `admin`, `sv02` → `viewer` |
| Redirect URI | `http://localhost/api/session/callback`, `:8080`, `:8082`, `http://3.0.181.78/...` |

---

## 6. Ảnh hưởng khi triển khai

| Thay đổi | Cần làm gì |
|---|---|
| `app.py`, `Dockerfile` | `docker compose build application-backend-server` → `docker compose up -d application-backend-server` |
| `conf.default`, `html/*` | `docker compose build web-frontend-server` → `docker compose up -d web-frontend-server web-frontend-server2` |
| `api-gateway-proxy-server/nginx.conf` | `docker restart api-gateway-proxy-server` (file được mount) |
| `docker-compose.yml` | `docker compose up -d` |
| `import/realm-export.json` | Chỉ import khi data trống; máy đang có data thì phải xoá `authentication-identity-server/data/` hoặc sửa qua Console |
| Image mới | Push `phathuynh2104/web:dev`, `phathuynh2104/app:dev` (đã push) |
| Đổi `PUBLIC_HOST` | Sửa `.env` → up lại app + Keycloak → thêm redirect URI mới |

---

## 7. Kiểm tra nhanh sau khi thay đổi

```powershell
docker compose ps --format "{{.Name}}|{{.State}}"     # 13 running
curl.exe -s http://localhost/api/services             # count=9 up=9
curl.exe -s http://localhost/api/session/me            # authenticated=false khi chưa login
1..4 | ForEach-Object { (curl.exe -s -D - -o NUL http://localhost/ | Select-String 'X-Served-By').ToString().Trim() }
```

Kết quả mong đợi: `web-frontend-server1` / `web-frontend-server2` luân phiên.

---

## 8. Lịch sử commit của đợt thay đổi

| Commit | Nội dung | File chính |
|---|---|---|
| `a5f665c` | Cloud Portal + Keycloak + MinIO | 19 file (portal, app.py, compose, realm export, docs) |
| `3998440` | Fix 502: Nginx tự resolve IP container | `nginx.conf`, `conf.default`, README, TEST-RESULTS |
| `313e553` | Tắt cache HTML (bước 1) | `conf.default` |
| `8c472eb` | Chỉ tắt cache HTML, giữ cache asset (bước 2) | `conf.default` |
| `5e0f8e3` | Thêm `NHUNG-GI-DA-LAM.md` | `NHUNG-GI-DA-LAM.md`, `README.md` |
| `(file này)` | Thêm `BANG-THAY-DOI.md` | `BANG-THAY-DOI.md`, `README.md` |
