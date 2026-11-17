# Kết quả kiểm thử — MyMiniCloud

Thời điểm chạy: 17/11/2026
Môi trường: Docker Desktop 29.1.5 (Windows), Docker Engine Linux.
Toàn bộ hệ thống chạy đúng cổng của đề: proxy `80`, MariaDB `3306`.

## Trạng thái container

```
api-gateway-proxy-server              Up
application-backend-server            Up
authentication-identity-server        Up
internal-dns-server                   Up
monitoring-grafana-dashboard-server   Up
monitoring-logging-server             Up
monitoring-node-exporter-server       Up
monitoring-prometheus-server          Up
monitoring-promtail                   Up
object-storage-server                 Up
relational-database-server            Up
web-frontend-server                   Up
web-frontend-server2                  Up
```


## 1. Web Frontend Server (Nginx)

| Lệnh | Kết quả |
|---|---|
| `curl -I http://localhost:8080/` | `200` |
| `curl -I http://localhost:8080/blog/` | `200` |
| nội dung trang chủ | `<h1>MyMiniCloud &ndash; Home</h1>` → hiển thị **MyMiniCloud – Home** |
| nội dung trang blog | `<h1>MyMiniCloud Blog</h1>` |

## 2. Application Backend Server (Flask)

| Lệnh | Kết quả |
|---|---|
| `curl http://localhost:8085/hello` | `{"message":"Hello from App Server!"}` |
| `curl http://localhost/api/hello` | `{"message":"Hello from App Server!"}` (qua proxy, đã strip `/api/`) |

## 3. Relational Database Server (MariaDB)

```
$ docker exec relational-database-server mariadb -uroot -proot \
    -e "USE minicloud; SHOW TABLES; SELECT * FROM notes;"

Tables_in_minicloud
notes
id  title                   created_at
1   Hello from MariaDB!     2026-10-29 06:37:28
```

## 4. Authentication Identity Server (Keycloak)

| Lệnh | Kết quả |
|---|---|
| `curl -I http://localhost:8081/` | `302` (redirect trang đăng nhập) |
| `curl http://localhost:8081/realms/master` | `200` |
| Đăng nhập UI | admin / admin |

## 5. Object Storage Server (MinIO)

```
$ docker exec object-storage-server mc alias set local http://127.0.0.1:9000 minioadmin minioadmin
$ docker exec object-storage-server mc mb local/demo local/profile-pics local/documents

$ docker exec object-storage-server mc ls local
demo/  profile-pics/  documents/

$ docker exec object-storage-server mc ls local/profile-pics
avatar.jpg

$ docker exec object-storage-server mc ls local/documents
report.pdf
```

| Kiểm tra | Kết quả |
|---|---|
| `GET :9000/profile-pics/avatar.jpg` | `200` — bucket public |
| `GET :9000/documents/report.pdf` | `403` — bucket private |
| `GET /api/files/documents/report.pdf/download` | `200`, `application/pdf`, 6 132 647 bytes |
| Console `http://localhost:9001` | `200`, đăng nhập minioadmin / minioadmin |

`profile-pics` và `demo` được set policy đọc công khai; `documents` giữ private
và chỉ tải qua Flask (có kiểm soát).


## 6. Internal DNS Server (Bind9)

```
$ docker exec internal-dns-server dig +short @127.0.0.1 web-frontend-server.cloud.local
10.10.10.10
```

## 7. Monitoring (Prometheus + Node Exporter)

```
$ curl -s "http://localhost:9090/api/v1/query?query=up"
job=node up=1
```

`http://localhost:9090/targets` → `monitoring-node-exporter-server:9100` **UP**.

## 8. Logging / Visualization (Grafana + Loki)

| Kiểm tra | Kết quả |
|---|---|
| `curl -I http://localhost:3000/login` | `200` |
| `curl http://localhost:3100/ready` | `ready` |
| Datasource tự nạp | `Prometheus → http://monitoring-prometheus-server:9090` |
| | `Loki → http://monitoring-logging-server:3100` |
| Promtail đẩy log | `GET /loki/api/v1/label/job/values` → `{"status":"success","data":["docker"]}` |
| Truy vấn log | `{job="docker"}` trả về stream log container |

## 9. API Gateway / Reverse Proxy (Nginx)

| Lệnh | Kết quả |
|---|---|
| `curl -I http://localhost/` | `200` (web) |
| `curl -s http://localhost/api/hello` | `{"message":"Hello from App Server!"}` |
| `curl -I http://localhost/auth/` | `302 Found` (Keycloak login) |

## Kiểm tra thông mạng giữa các container

Ping từ container trung gian trong `cloud-net` tới 9 server: **OK 9/9**.

Phân giải alias nội bộ (dùng đúng như lệnh trong đề):

| Alias | IP |
|---|---|
| web | 172.19.0.4 |
| app-server | 172.19.0.6 |
| db | 172.19.0.12 |
| keycloak | 172.19.0.7 |
| minio | 172.19.0.9 |
| dns-server | 172.19.0.10 |
| prometheus | 172.19.0.8 |
| grafana | 172.19.0.3 |
| loki | 172.19.0.2 |

## Phần mở rộng 1 — Blog cá nhân (Web Frontend Server)

| Kiểm thử | Kết quả |
|---|---|
| `GET /blog/` | `200` — danh sách 3 bài, 3 hyperlink tới `blog1/2/3.html` |
| `GET /blog/blog1.html` | `200` — "Đà Nẵng – Hành trình khám phá thành phố biển" |
| `GET /blog/blog2.html` | `200` — "Văn hóa Đài Loan – Giao thoa truyền thống và hiện đại" |
| `GET /blog/blog3.html` | `200` — "Thể thao Nhật Bản – Kỷ luật, đam mê và khát vọng" |
| `GET /blog/blog.css` | `200` — stylesheet dùng chung |
| Ảnh minh hoạ | 22 ảnh JPG/PNG trong `blog/images/` (Đà Nẵng, Đài Loan, Nhật Bản), `200` |
| Qua proxy `http://localhost/blog/...` | `200` cho cả 5 đường dẫn trên |
| Link quay lại | mỗi bài có "← Về trang Blog" + "← Về trang chủ" |
| Trang chủ `GET /` | hero "WELCOME" (tiêu đề `MyMiniCloud – Home`, chip chủ đề, nút "Đọc ngay"), mục "Danh mục" gồm 3 card có ảnh + nhãn chủ đề + tag, link "Xem tất cả" → `/blog/` |
| Đồng bộ giao diện | trang chủ + `/blog/` + 3 bài viết dùng chung bảng màu tối (nền `#0c0916`, panel `#171228`, accent tím `#c39df5`), cùng kiểu header/nav/footer |

Ảnh minh hoạ là ảnh chụp thật (JPG/PNG) theo từng chủ đề, nằm trong
`web-frontend-server/html/blog/images/`.

## Phần mở rộng 2 — API `/student` (Application Backend)

| Kiểm thử | Kết quả |
|---|---|
| `GET /api/student` (qua proxy) | `200`, JSON 5 sinh viên (`id`, `name`, `major`, `gpa`) |
| `GET http://localhost:8085/student` (thẳng app) | `200`, cùng nội dung |
| Dữ liệu | `students.json` 5 phần tử, tiếng Việt hiển thị đúng UTF-8 |

## Phần mở rộng 3 — `studentdb` + bảng `students`

| Kiểm thử | Kết quả |
|---|---|
| `SHOW TABLES` trong `studentdb` | `students` |
| `SELECT * FROM students` | 4 bản ghi (SV001–SV004) đúng `student_id`, `fullname`, `dob`, `major` |
| `GET /api/students-db` | `{"count":4,"students":[...]}` — Flask đọc trực tiếp MariaDB qua `pymysql` |
| Volume dữ liệu | `./relational-database-server/data` giữ dữ liệu khi container bị xoá |
| Sửa `INSERT` trong file SQL | chạy lại script (có `DROP TABLE IF EXISTS`) → DB đúng 4 dòng mới, không trùng |

## Giao diện danh sách sinh viên (mở rộng 2 + 3)

| Kiểm thử | Kết quả |
|---|---|
| `GET /students/` | `200` — giao diện tối giống trang chủ/blog, 2 tab Bài 2 / Bài 3 |
| Tab **Bài 2 · JSON** | bảng 5 sinh viên: STT, họ tên, chuyên ngành, thanh GPA; tổng 5, GPA TB 3.42 |
| Tab **Bài 3 · Database** (`/students/#db`) | bảng 4 sinh viên: mã SV, họ tên, ngày sinh `dd/mm/yyyy`, chuyên ngành; nguồn MariaDB |
| Dữ liệu tải bằng `fetch()` | gọi `/api/student` và `/api/students-db` qua API Gateway (không gọi thẳng backend) |
| Nút **↻ Tải lại** | xoá cache và tải lại tab hiện tại (dùng khi demo CRUD) |
| Tab **Bài 3** tự làm mới | mỗi lần mở tab đều `fetch` lại; có dòng "Cập nhật HH:MM:SS" |
| UPDATE thử trong DB | đổi `SV002` sang `DevOps (demo)` → API và giao diện đổi ngay, không cần build lại |
| JSON gốc | mục "Xem JSON gốc" hiển thị payload thật của API |
| Link điều hướng | trang chủ + 4 trang blog có mục "Sinh viên"; trang chủ có thêm khối CTA "Danh sách sinh viên" |
| Cả 2 web server | `web-frontend-server` và `web-frontend-server2` đều phục vụ `/students/` (round robin) |

## Phần mở rộng 7 — Prometheus target `web`

| Kiểm thử | Kết quả |
|---|---|
| `GET http://localhost:8080/metrics` | `200`, `Content-Type: text/plain; charset=utf-8` |
| `/api/v1/targets` job `web` | `http://web-frontend-server:80/metrics` → **up** |
| Job `node` | `http://monitoring-node-exporter-server:9100/metrics` → **up** |
| Job `prometheus` | `http://localhost:9090/metrics` → **up** |

## Phần mở rộng 8 — Grafana dashboard

| Kiểm thử | Kết quả |
|---|---|
| `GET /api/search?query=System Health` | tìm thấy dashboard `System Health of 523H0167`, uid `system-health`, folder `MyMiniCloud` |
| Datasource | `prometheus` (uid `prometheus`, isDefault) + `loki` (uid `loki`) |
| Panel CPU | query trả `46.46` (%) |
| Panel Memory | query trả `29.27` (%) |
| Panel Network | RX `35.87` Bps (có cả TX) |
| Panel Logs (Loki) | hiển thị stream `{job="docker"}` |

## Phần mở rộng 9 — Proxy route `/student/`

| Kiểm thử | Kết quả |
|---|---|
| `GET http://localhost/student/` | `200`, JSON danh sách sinh viên (đọc từ backend) |
| `GET /api/hello` (không hồi quy) | `{"message":"Hello from App Server!"}` |

## Phần mở rộng 10 — Load balancing Round Robin

| Kiểm thử | Kết quả |
|---|---|
| 6 request liên tiếp `GET /` | `X-Served-By` luân phiên: server1 → server2 → server1 → server2 → server1 → server2 |
| Badge trong HTML | `Served by web-frontend-server1` / `web-frontend-server2` đổi mỗi lần F5 |
| `:8080` và `:8082` | cả hai trả `200` (truy cập trực tiếp từng web server) |
| Tổng container | 13 running (9 server + node-exporter + loki + promtail + web2) |

## Mở rộng 11 — Cloud Portal: 9 server + đăng nhập + upload MinIO

### 11.1. Trạng thái 9 server

`GET /api/services` trả `count=9`, `up=9`:

| Card | Container | Kiểm tra | Kết quả |
|---|---|---|---|
| Web Server | web-frontend-server | HTTP :80 | up |
| Application Server | application-backend-server | HTTP /hello | up |
| Database Server | relational-database-server | TCP 3306 | up |
| Authentication Server | authentication-identity-server | HTTP realm | up |
| Object Storage | object-storage-server | /minio/health/live | up |
| DNS Server | internal-dns-server | TCP 53 | up |
| Monitoring | monitoring-prometheus-server | /-/ready | up |
| Logging / Dashboard | monitoring-grafana-dashboard-server | /api/health | up |
| API Gateway | api-gateway-proxy-server | request hiện tại | up |

Bấm card có giao diện → mở đúng cổng server đó ở tab mới. Database/DNS hiện toast
hướng dẫn lệnh `docker exec` tương ứng.

### 11.2. Đăng nhập Keycloak + phân quyền

| Kiểm thử | Kết quả |
|---|---|
| `GET /api/session/login` | `302` → `http://localhost:8081/realms/realm_523H0167/protocol/openid-connect/auth` (PKCE S256) |
| Đăng nhập `sv01 / sv01` | callback `302` → `/`, set cookie `sid` HttpOnly, SameSite=Lax |
| `GET /api/session/me` (sv01) | `authenticated=true`, `is_admin=true`, roles có `admin` |
| Đăng nhập `sv02 / sv02` | `authenticated=true`, `is_admin=false`, roles có `viewer` |
| `POST /api/files/upload` không login | `401` — "Cần đăng nhập" |
| `POST /api/files/upload` bằng sv02 | `403` — "Chỉ tài khoản admin được phép chỉnh sửa" |
| `POST /api/files/upload` bằng sv01 | `201`, file vào đúng bucket |
| `DELETE /api/files/...` bằng sv02 | `403` |
| `POST /api/students-db` không login / sv02 | `401` / `403` |
| `POST /api/students-db` bằng sv01 | `201`, dữ liệu vào MariaDB |
| `GET /students/` bằng sv02 | `200`, nút Thêm/Sửa/Xoá bị ẩn |

### 11.3. Upload ảnh + PDF

| Kiểm thử | Kết quả |
|---|---|
| Upload `test.png` bằng sv01 | `201` → `profile-pics/<uuid>_test.png`, URL public trả `200` |
| Upload `test.pdf` bằng sv01 | `201` → `documents/<uuid>_test.pdf` |
| Upload file `.exe` | `400` — sai định dạng |
| Upload file > 10 MB | `413` |
| PDF giả mạo (đuôi .pdf, nội dung không phải PDF) | `400` — magic bytes không khớp |
| Tải PDF qua `/api/files/documents/<name>/download` | `200`, `application/pdf` |
| Xoá file bằng sv01 | `200` |
| Ảnh public truy cập trực tiếp MinIO | `200` |

### 11.4. Giao diện

- Trang chủ có 3 khối mới: **Hạ tầng đang vận hành**, **Kho tài liệu**, **đăng nhập ở header**.
- Card xanh/đỏ tự refresh 15 giây, nút "↻ Kiểm tra lại".
- Upload kéo-thả hoặc chọn file, có thông báo lỗi rõ ràng (401/403/413/sai định dạng).
- Trang `/students/` ẩn nút chỉnh sửa với viewer/khách, backend vẫn chặn 401/403.

### 11.5. Chịu được việc recreate container

Trước đây Nginx cache IP container lúc start → recreate backend là `/api/*` trả `502`.
Đã sửa bằng `resolver 127.0.0.11 valid=10s ipv6=off` + `resolve` trong `upstream`.

| Kiểm thử | Kết quả |
|---|---|
| `docker compose up -d --force-recreate application-backend-server` rồi gọi `/api/services` | `200` ngay sau 2s, không restart proxy |
| Gọi cùng lúc `:80`, `:8080`, `:8082` sau khi recreate | cả ba đều `200` |
| Round robin sau khi recreate 2 web server | vẫn luân phiên server1 / server2 |

## Ghi chú khi chụp ảnh minh chứng

Trước khi chạy phải bảo đảm cổng 80 và 3306 còn trống (tắt Apache/MySQL nếu có),
khi đó URL proxy đúng như đề: `http://localhost/`.
Khi deploy EC2 (không bận cổng), dùng `docker compose up -d` và URL là
`http://<public-ip>/` đúng như đề.
