# MyMiniCloud — Lệnh kiểm thử (Bắt buộc + Mở rộng)

Nhóm: Huỳnh Mạnh Phát (523H0167) – Phạm Nguyễn Thanh Phong (523H0169)

Tài liệu này chỉ gồm **lệnh chạy, kết quả kỳ vọng và ảnh cần chụp** để làm Chương 4 (Demo & kiểm thử) của báo cáo.
Mọi lệnh chạy ở thư mục gốc dự án (nơi có `docker-compose.yml`). Dùng được trên bash, Git Bash, WSL, EC2 Ubuntu.
Người dùng Windows PowerShell: đổi `curl` thành `curl.exe` (xem mục cuối).

> Khi chạy trên **AWS EC2**: thay `localhost` bằng `<PUBLIC_IP>` và mở Security Group cho các cổng 80, 8080, 8081, 8082, 8085, 9000, 9001, 9090, 3000.

---

## 0. Khởi động hệ thống

```bash
# (tuỳ chọn) dọn container cũ
docker rm -f $(docker ps -aq)

docker compose build --no-cache
docker compose up -d
docker compose ps
```

Kỳ vọng: **13 container** trạng thái `Up` (9 server + node-exporter + loki + promtail + web-frontend-server2).
Cổng **80** và **3306** trên máy phải trống (tắt Apache/XAMPP/MySQL nếu có).

Ảnh chụp: kết quả `docker compose ps`.

---

# PHẦN 1 — BẮT BUỘC (5 điểm)

## 1. Web Frontend Server (Nginx)

```bash
curl -I http://localhost:8080/
curl -I http://localhost:8080/blog/
```

Kỳ vọng:
- Cả hai trả `HTTP/1.1 200 OK`.
- Mở trình duyệt `http://localhost:8080/` thấy **MyMiniCloud – Home**; `http://localhost:8080/blog/` thấy **MyMiniCloud Blog**.

Ảnh chụp: terminal 2 lệnh `curl -I` + 2 trang trình duyệt.

## 2. Application Backend Server (Flask)

```bash
curl http://localhost:8085/hello
curl http://localhost/api/hello
```

Kỳ vọng: cả hai trả `{"message":"Hello from App Server!"}` (chứng minh proxy strip `/api/` đúng).

Ảnh chụp: terminal 2 lệnh.

## 3. Relational Database Server (MariaDB)

Cách theo đề (container tạm trong `cloud-net`, dùng alias `db`):

```bash
docker run -it --rm --network cloud-net mysql:8 \
  sh -lc 'mysql -h db -uroot -proot -e "USE minicloud; SHOW TABLES; SELECT * FROM notes;"'
```

Cách ngắn hơn (nếu máy không kéo được image `mysql:8`):

```bash
docker exec relational-database-server mariadb -uroot -proot \
  -e "SHOW DATABASES; USE minicloud; SHOW TABLES; SELECT * FROM notes;"
```

Kỳ vọng: bảng `notes` tồn tại, có dòng `Hello from MariaDB!`.

## 4. Authentication Identity Server (Keycloak)

- Mở `http://localhost:8081` → đăng nhập `admin` / `admin` → thấy trang quản trị (Dashboard).
- Tạo user test `sv01` (Users → Add user) — lưu ý: realm `master` hoặc realm riêng đều được.

Kiểm tra nhanh bằng lệnh:

```bash
curl -I http://localhost:8081/
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8081/realms/master
```

Kỳ vọng: `302` (chuyển sang trang đăng nhập) và `200`.

Ảnh chụp: trang Dashboard + danh sách user.

## 5. Object Storage Server (MinIO)

- Mở `http://localhost:9001` → đăng nhập `minioadmin` / `minioadmin`.
- Create Bucket tên `demo` → Upload file `web-frontend-server/html/index.html`.

Kiểm tra bằng lệnh (dùng `mc` có sẵn trong image):

```bash
docker exec object-storage-server mc alias set local http://127.0.0.1:9000 minioadmin minioadmin
docker exec object-storage-server mc ls local/demo
```

Kỳ vọng: thấy `index.html` trong bucket `demo`.
Ảnh chụp: màn hình Console có bucket `demo` và file.

## 6. Internal DNS Server (Bind9)

```bash
# cách theo đề (máy có cài dig)
dig @127.0.0.1 -p 1053 web-frontend-server.cloud.local +short

# cách không cần cài dig (chạy trong container DNS)
docker exec internal-dns-server dig +short @127.0.0.1 web-frontend-server.cloud.local
```

Kỳ vọng: `10.10.10.10`.
Nếu trống: kiểm tra `internal-dns-server/db.cloud.local` rồi `docker restart internal-dns-server`.

## 7. Monitoring — Node Exporter + Prometheus

- Mở `http://localhost:9090/targets` → target `monitoring-node-exporter-server:9100` phải **UP**.
- Tab Graph: nhập `node_cpu_seconds_total` → Execute.

```bash
curl -s "http://localhost:9090/api/v1/targets" | jq -r '.data.activeTargets[] | "\(.labels.job)\t\(.health)\t\(.scrapeUrl)"'
curl -s "http://localhost:9090/api/v1/query?query=up"
curl -s http://localhost:9100/metrics | head -5
```

Kỳ vọng: job `node` health `up`; query `up` trả giá trị `1`.
Ảnh chụp: trang Targets (UP) + đồ thị `node_cpu_seconds_total`.

## 8. Grafana Dashboard (+ Loki)

- Mở `http://localhost:3000` → `admin` / `admin`.
- Connections → Data sources → Add → Prometheus → URL `http://prometheus:9090` (dự án đã tự nạp sẵn datasource này, chỉ cần mở ra và bấm **Save & test**).
- Dashboards → Import → ID `1860` (Node Exporter Full) → chọn datasource Prometheus.

```bash
curl -s http://localhost:3000/api/health
curl -s -u admin:admin http://localhost:3000/api/datasources | jq -r '.[] | "\(.name)\t\(.url)"'
curl -s http://localhost:3100/ready
```

Kỳ vọng: `database: ok`; có datasource Prometheus và Loki; Loki trả `ready`; dashboard hiển thị CPU/RAM/Network.
Ảnh chụp: dashboard Node Exporter Full có dữ liệu.

## 9. API Gateway / Reverse Proxy (Nginx)

```bash
curl -I http://localhost/
curl -s  http://localhost/api/hello
curl -I http://localhost/auth/
```

Kỳ vọng:
- `/` → `200 OK` (web).
- `/api/hello` → `{"message":"Hello from App Server!"}`.
- `/auth/` → `302` redirect tới Keycloak.

Xem cấu hình upstream: `cat api-gateway-proxy-server/nginx.conf`.

## 10. Kiểm tra thông mạng (ping giữa các server)

Image nginx/flask không có `ping`, nên dùng container tạm `busybox` gắn vào `cloud-net`:

```bash
for h in web app-server db keycloak minio prometheus grafana dns-server; do
  echo "== ping $h"
  docker run --rm --network cloud-net busybox ping -c 3 $h
done
```

Hoặc từng lệnh như đề:

```bash
docker run --rm --network cloud-net busybox ping -c 3 web
docker run --rm --network cloud-net busybox ping -c 3 app-server
docker run --rm --network cloud-net busybox ping -c 3 db
docker run --rm --network cloud-net busybox ping -c 3 keycloak
docker run --rm --network cloud-net busybox ping -c 3 minio
docker run --rm --network cloud-net busybox ping -c 3 prometheus
docker run --rm --network cloud-net busybox ping -c 3 grafana
docker run --rm --network cloud-net busybox ping -c 3 dns-server
```

Kỳ vọng: `3 packets transmitted, 3 packets received, 0% packet loss` cho cả 8 tên.
Alias khai báo trong `docker-compose.yml`: `web`, `app-server`, `db`, `keycloak`, `minio`, `dns-server`, `prometheus`, `grafana` (và thêm `proxy`, `loki`, `node-exporter`, `web2`).

---

# PHẦN 2 — MỞ RỘNG (5 điểm)

## MR1. Web — Blog cá nhân 3 bài (0,5đ)

```bash
for p in blog/ blog/blog1.html blog/blog2.html blog/blog3.html blog/blog.css; do
  printf "%s -> " $p; curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/$p
done

# trang chủ blog có hyperlink tới 3 bài
curl -s http://localhost:8080/blog/ | grep -o 'blog[123]\.html' | sort -u

# mỗi bài có ảnh minh hoạ + link quay lại
curl -s http://localhost:8080/blog/blog1.html | grep -c '<img'
curl -s http://localhost:8080/blog/blog1.html | grep -o 'href="/"'

# qua proxy
curl -I http://localhost/blog/blog2.html
```

Kỳ vọng: toàn bộ `200`; thấy `blog1.html blog2.html blog3.html`; số `<img>` > 0; có `href="/"` (về trang chủ).
Ảnh chụp: `http://localhost/blog/` và 1–2 bài viết trên trình duyệt.

## MR2. Backend — API `/student` đọc JSON (0,5đ)

```bash
curl -s http://localhost/api/student
curl -s http://localhost:8085/student | jq length
```

Kỳ vọng: JSON gồm **5 sinh viên** (`id`, `name`, `major`, `gpa`); `jq length` ra `5`.
Giao diện: `http://localhost/students/` (tab Bài 2).

## MR3. Database — `studentdb` + bảng `students` (0,5đ)

```bash
# cấu trúc + dữ liệu
docker exec relational-database-server mariadb -uroot -proot \
  -e "USE studentdb; DESCRIBE students; SELECT * FROM students;"

# CRUD bằng SQL
docker exec relational-database-server mariadb -uroot -proot -e "USE studentdb; INSERT INTO students(student_id,fullname,dob,major) VALUES ('SV005','Ngo Gia Han','2004-09-09','Khoa hoc du lieu'); SELECT * FROM students;"
docker exec relational-database-server mariadb -uroot -proot -e "USE studentdb; UPDATE students SET major='DevOps' WHERE student_id='SV005'; SELECT * FROM students WHERE student_id='SV005';"
docker exec relational-database-server mariadb -uroot -proot -e "USE studentdb; DELETE FROM students WHERE student_id='SV005'; SELECT COUNT(*) AS con_lai FROM students;"

# Flask đọc từ database
curl -s http://localhost/api/students-db
```

Kỳ vọng: bảng có 5 cột (`id`, `student_id`, `fullname`, `dob`, `major`), **≥ 3 bản ghi** (hiện có 4); API trả `{"count":4,"students":[...]}`.

CRUD qua API Flask (tuỳ chọn):

```bash
ID=$(curl -s -X POST -H "Content-Type: application/json" \
  -d '{"student_id":"SV006","fullname":"Test User","dob":"2004-01-01","major":"IT"}' \
  http://localhost/api/students-db | jq -r .id)
curl -s -X PUT -H "Content-Type: application/json" \
  -d '{"student_id":"SV006","fullname":"Test User 2","dob":"2004-01-01","major":"DevOps"}' \
  http://localhost/api/students-db/$ID
curl -s -X DELETE http://localhost/api/students-db/$ID
```

Kỳ vọng: lần lượt `Đã thêm` (201), `Đã cập nhật`, `Đã xóa`.

> Nếu DB đã tồn tại từ trước, file `init/002_studentdb.sql` không tự chạy. Nạp tay:
> `docker exec -i relational-database-server mariadb -uroot -proot --default-character-set=utf8mb4 < relational-database-server/init/002_studentdb.sql`

## MR4. Keycloak — Realm + 2 user + client + token (0,5đ)

Realm: `realm_523H0167`, user `sv01`, `sv02`, client `flask-app` (public). Thay `<MAT_KHAU_SV01>` bằng mật khẩu đã đặt cho sv01.

```bash
# token endpoint của realm
curl -s http://localhost:8081/realms/realm_523H0167/.well-known/openid-configuration | jq -r .token_endpoint

# lấy access token
TOKEN=$(curl -s -X POST http://localhost:8081/realms/realm_523H0167/protocol/openid-connect/token \
  -d "grant_type=password" -d "client_id=flask-app" \
  -d "username=sv01" -d "password=<MAT_KHAU_SV01>" | jq -r .access_token)
echo ${TOKEN:0:40}...

# /secure: không token -> 401, có token -> 200
curl -s http://localhost/api/secure
curl -s -H "Authorization: Bearer $TOKEN" http://localhost/api/secure
```

Kỳ vọng:
- Không token: `{"error":"Missing Bearer token"}`.
- Có token: `{"message":"Secure resource OK","preferred_username":...}` (`preferred_username` là `sv01` hoặc `null` tuỳ cấu hình token của Keycloak).

Ảnh chụp: Keycloak Console (realm, 2 user, client `flask-app`) + terminal kết quả `/secure`.

## MR5. MinIO — bucket `profile-pics` và `documents` (0,5đ)

Console `http://localhost:9001` (`minioadmin` / `minioadmin`):
1. Tạo bucket `profile-pics` → upload `avatar.jpg`.
2. Tạo bucket `documents` → upload file PDF báo cáo.
3. Đặt policy bucket `profile-pics` là **Public** (Anonymous access → readonly) để lấy URL công khai.

```bash
docker exec object-storage-server mc alias set local http://127.0.0.1:9000 minioadmin minioadmin
docker exec object-storage-server mc ls local
docker exec object-storage-server mc ls local/profile-pics

# truy cập URL public (không cần đăng nhập)
curl -I http://localhost:9000/profile-pics/avatar.jpg
```

Kỳ vọng: thấy 2 bucket; `curl -I` trả `200 OK`, `Content-Type: image/jpeg`.
(Nếu bucket private, `curl -I` trả `403` — đó cũng là minh chứng cho policy private/public.)

> Lưu ý: bản nộp hiện mới thấy bucket `profile-pics` (có `avatar.jpg` và file PDF) và `demo`; cần tạo thêm bucket `documents` và chuyển file PDF sang đó cho đúng đề.

## MR6. DNS — thêm bản ghi `app-backend`, `minio`, `keycloak` (0,5đ)

Zone `internal-dns-server/db.cloud.local` đã có:

```
app-backend IN A 10.10.10.20
minio       IN A 10.10.10.30
keycloak    IN A 10.10.10.40
```

```bash
docker restart internal-dns-server

for n in web-frontend-server app-backend minio keycloak; do
  printf "%s.cloud.local -> " $n
  docker exec internal-dns-server dig +short @127.0.0.1 $n.cloud.local
done
```

Kỳ vọng: `10.10.10.10`, `10.10.10.20`, `10.10.10.30`, `10.10.10.40`.
Nếu đã sửa file zone mà dig không đổi: tăng số serial trong dòng SOA rồi restart container.

## MR7. Prometheus — thêm target `web` (0,5đ)

Job trong `monitoring-prometheus-server/prometheus.yml`: `web` → `web-frontend-server:80` (`/metrics`).

```bash
curl -s http://localhost:8080/metrics | head -5
docker restart monitoring-prometheus-server
sleep 20
curl -s "http://localhost:9090/api/v1/targets" | jq -r '.data.activeTargets[] | "\(.labels.job)\t\(.health)\t\(.scrapeUrl)"'
```

Kỳ vọng:

```
node        up   http://monitoring-node-exporter-server:9100/metrics
prometheus  up   http://localhost:9090/metrics
web         up   http://web-frontend-server:80/metrics
```

Ảnh chụp: `http://localhost:9090/targets` thấy job **web** màu xanh (UP).

## MR8. Grafana — Dashboard "System Health of <MSSV>" (0,5đ)

Dashboard tự nạp (provisioning), thuộc folder `MyMiniCloud`.

```bash
curl -s -u admin:admin "http://localhost:3000/api/search?query=System%20Health" | jq .
curl -s -u admin:admin http://localhost:3000/api/dashboards/uid/system-health | jq -r '.dashboard.panels[] | .title'
```

Kỳ vọng: tìm thấy dashboard `uid=system-health`; có các panel CPU Usage (%), Memory Usage, Network Traffic (và Application Logs).
Mở: `http://localhost:3000/d/system-health` → chụp toàn bộ dashboard có dữ liệu và tiêu đề chứa MSSV.

PromQL dùng:
- CPU: `100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)`
- Memory: `100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)`
- Network: `rate(node_network_receive_bytes_total[5m])`

## MR9. Proxy — route `/student/` (0,5đ)

```bash
docker restart api-gateway-proxy-server
curl -s http://localhost/student/
curl -s -o /dev/null -w "%{http_code}\n" http://localhost/student/
```

Kỳ vọng: `200` và JSON danh sách sinh viên (giống `/api/student`).

## MR10. Load Balancer — Round Robin 2 web server (0,5đ)

Cấu hình (`api-gateway-proxy-server/nginx.conf`):

```nginx
upstream web_backend {
  server web-frontend-server1:80;
  server web-frontend-server2:80;
}
```

```bash
# 6 request liên tiếp, xem server nào phục vụ
for i in 1 2 3 4 5 6; do
  curl -s -D - -o /dev/null http://localhost/ | grep -i x-served-by
done

# so sánh trực tiếp từng server
curl -s -o /dev/null -w "server1: %{http_code}\n" http://localhost:8080/
curl -s -o /dev/null -w "server2: %{http_code}\n" http://localhost:8082/
```

Kỳ vọng: `X-Served-By` luân phiên `web-frontend-server1`, `web-frontend-server2`, `web-frontend-server1`, ...
Trình duyệt: mở `http://localhost/` rồi F5 liên tục, badge góc phải dưới đổi giữa 2 server.
Ảnh chụp: terminal 6 dòng xen kẽ + 2 ảnh trình duyệt (mỗi ảnh một server).

---

## Phụ lục — Ghi chú cho Windows PowerShell

```powershell
# dùng curl.exe thay cho curl
curl.exe -I http://localhost:8080/

# vòng lặp ping
"web","app-server","db","keycloak","minio","prometheus","grafana","dns-server" | ForEach-Object {
  docker run --rm --network cloud-net busybox ping -c 3 $_
}

# vòng lặp round robin
1..6 | ForEach-Object { curl.exe -s -D - -o NUL http://localhost/ | Select-String "X-Served-By" }

# nạp file SQL
cmd /c "docker exec -i relational-database-server mariadb -uroot -proot --default-character-set=utf8mb4 < relational-database-server\init\002_studentdb.sql"
```

Lệnh dùng `jq` (cài bằng `winget install jqlang.jq` hoặc `sudo apt install jq`); nếu không có thì bỏ phần `| jq ...` và đọc JSON thô.

## Phụ lục — Bảng cổng

| Server | Cổng host |
|---|---|
| Web 1 / Web 2 | 8080 / 8082 |
| App | 8085 (nội bộ 8081) |
| Database | 3306 |
| Keycloak | 8081 |
| MinIO API / Console | 9000 / 9001 |
| DNS | 1053 (udp+tcp) |
| Prometheus / Node Exporter | 9090 / 9100 |
| Grafana / Loki | 3000 / 3100 |
| Proxy | 80 |