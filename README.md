# MyMiniCloud — Lệnh kiểm thử trên Windows (Bắt buộc + Mở rộng)

Nhóm: Huỳnh Mạnh Phát (523H0167) – Phạm Nguyễn Thanh Phong (523H0169)

Tài liệu gồm **lệnh chạy, kết quả kỳ vọng và ảnh cần chụp** để làm Chương 4 (Demo & kiểm thử) của báo cáo.

**Môi trường:** Windows 10/11 + Docker Desktop + **PowerShell**. Không cần cài thêm `jq`, `dig`, `grep`.
Quy ước: luôn gõ `curl.exe` (không gõ `curl`, vì trong PowerShell `curl` là bí danh của `Invoke-WebRequest`).
Mọi lệnh chạy ở thư mục gốc dự án (nơi có `docker-compose.yml`), ví dụ:

```powershell
cd D:\Code\Cloud\Endtern\huynhmanhphatminiclouddemo
```

---

## 0. Khởi động hệ thống

```powershell
# cổng 80 và 3306 phải trống (tắt XAMPP/Apache/MySQL nếu có)
Get-NetTCPConnection -LocalPort 80,3306 -State Listen -ErrorAction SilentlyContinue

# (tuỳ chọn) dọn container cũ
docker rm -f $(docker ps -aq)

docker compose build --no-cache
docker compose up -d
docker compose ps
```

Kỳ vọng: **13 container** trạng thái `Up` (9 server + node-exporter + loki + promtail + web-frontend-server2).
Ảnh chụp: kết quả `docker compose ps`.

---

# PHẦN 1 — BẮT BUỘC (5 điểm)

## 1. Web Frontend Server (Nginx)

```powershell
curl.exe -I http://localhost:8080/
curl.exe -I http://localhost:8080/blog/
```

Kỳ vọng: cả hai trả `HTTP/1.1 200 OK`.
Mở trình duyệt: `http://localhost:8080/` thấy **MyMiniCloud – Home**; `http://localhost:8080/blog/` thấy **MyMiniCloud Blog**.
Ảnh chụp: terminal 2 lệnh + 2 trang trình duyệt.

## 2. Application Backend Server (Flask)

```powershell
curl.exe http://localhost:8085/hello
curl.exe http://localhost/api/hello
```

Kỳ vọng: cả hai trả `{"message":"Hello from App Server!"}` (chứng minh proxy bỏ tiền tố `/api/` đúng).

## 3. Relational Database Server (MariaDB)

Cách theo đề (container tạm trong `cloud-net`, dùng alias `db`):

```powershell
docker run -it --rm --network cloud-net mysql:8 mysql -h db -uroot -proot -e "USE minicloud; SHOW TABLES; SELECT * FROM notes;"
```

Cách ngắn hơn:

```powershell
docker exec relational-database-server mariadb -uroot -proot -e "SHOW DATABASES; USE minicloud; SHOW TABLES; SELECT * FROM notes;"
```

Kỳ vọng: bảng `notes` tồn tại, có dòng `Hello from MariaDB!`.

## 4. Authentication Identity Server (Keycloak)

- Mở `http://localhost:8081` → đăng nhập `admin` / `admin` → thấy trang quản trị.
- Tạo user test (Users → Add user), ví dụ `sv01`.

```powershell
curl.exe -I http://localhost:8081/
curl.exe -s -o NUL -w "%{http_code}`n" http://localhost:8081/realms/master
```

Kỳ vọng: `302` (chuyển sang trang đăng nhập) và `200`.
Ảnh chụp: trang quản trị + danh sách user.

## 5. Object Storage Server (MinIO)

- Mở `http://localhost:9001` → đăng nhập `minioadmin` / `minioadmin`.
- Create Bucket `demo` → Upload file `web-frontend-server\html\index.html`.

Kiểm tra bằng lệnh (dùng `mc` có sẵn trong image):

```powershell
docker exec object-storage-server mc alias set local http://127.0.0.1:9000 minioadmin minioadmin
docker exec object-storage-server mc ls local/demo
```

Kỳ vọng: thấy `index.html` trong bucket `demo`.

## 6. Internal DNS Server (Bind9)

Windows thường không có `dig`, nên chạy `dig` bên trong container DNS:

```powershell
docker exec internal-dns-server dig +short "@127.0.0.1" web-frontend-server.cloud.local
```

> Bắt buộc có dấu nháy kép quanh `"@127.0.0.1"`, nếu không PowerShell báo lỗi `splatting operator '@'`.

Hoặc dùng `nslookup` có sẵn của Windows (DNS map cổng 1053):

```powershell
nslookup -port=1053 web-frontend-server.cloud.local 127.0.0.1
```

Kỳ vọng: `10.10.10.10`.
Nếu trống: kiểm tra `internal-dns-server\db.cloud.local` rồi `docker restart internal-dns-server`.

## 7. Monitoring — Node Exporter + Prometheus

- Mở `http://localhost:9090/targets` → target `monitoring-node-exporter-server:9100` phải **UP**.
- Tab Graph: nhập `node_cpu_seconds_total` → Execute.

```powershell
Invoke-RestMethod http://localhost:9090/api/v1/targets |
  Select-Object -ExpandProperty data | Select-Object -ExpandProperty activeTargets |
  Select-Object @{n='job';e={$_.labels.job}}, health, scrapeUrl

curl.exe -s "http://localhost:9090/api/v1/query?query=up"
curl.exe -s http://localhost:9100/metrics | Select-Object -First 5
```

Kỳ vọng: job `node` có `health = up`; query `up` trả giá trị `1`.
Ảnh chụp: trang Targets (UP) + đồ thị `node_cpu_seconds_total`.

## 8. Grafana Dashboard (+ Loki)

- Mở `http://localhost:3000` → `admin` / `admin`.
- Connections → Data sources → Add → Prometheus → URL `http://prometheus:9090` (dự án đã nạp sẵn datasource này; chỉ cần mở ra và bấm **Save & test**).
- Dashboards → Import → ID `1860` (Node Exporter Full) → chọn datasource Prometheus.

```powershell
curl.exe -s http://localhost:3000/api/health
curl.exe -s -u admin:admin http://localhost:3000/api/datasources | ConvertFrom-Json | Select-Object name, url
curl.exe -s http://localhost:3100/ready
```

Kỳ vọng: `database: ok`; có datasource Prometheus và Loki; Loki trả `ready`; dashboard hiển thị CPU/RAM/Network.
Ảnh chụp: dashboard Node Exporter Full có dữ liệu.

## 9. API Gateway / Reverse Proxy (Nginx)

```powershell
curl.exe -I http://localhost/
curl.exe -s http://localhost/api/hello
curl.exe -I http://localhost/auth/
```

Kỳ vọng:
- `/` → `200 OK` (web).
- `/api/hello` → `{"message":"Hello from App Server!"}`.
- `/auth/` → `302` chuyển tới Keycloak.

Xem cấu hình upstream: `Get-Content .\api-gateway-proxy-server\nginx.conf`.

## 10. Kiểm tra thông mạng (ping giữa các server)

Image nginx/flask không có `ping`, nên dùng container tạm `busybox` gắn vào `cloud-net`:

```powershell
"web","app-server","db","keycloak","minio","prometheus","grafana","dns-server" | ForEach-Object {
  Write-Host "== ping $_"
  docker run --rm --network cloud-net busybox ping -c 3 $_
}
```

Hoặc từng lệnh như đề:

```powershell
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

---

# PHẦN 2 — MỞ RỘNG (5 điểm)

## MR1. Web — Blog cá nhân 3 bài (0,5đ)

```powershell
# mã phản hồi từng trang
"blog/","blog/blog1.html","blog/blog2.html","blog/blog3.html","blog/blog.css" | ForEach-Object {
  $code = curl.exe -s -o NUL -w "%{http_code}" "http://localhost:8080/$_"
  "$_ -> $code"
}

# trang blog có hyperlink tới 3 bài
(Invoke-WebRequest -UseBasicParsing http://localhost:8080/blog/).Links.href | Select-String "blog[123]\.html"

# mỗi bài có ảnh minh hoạ + link về trang chủ
(curl.exe -s http://localhost:8080/blog/blog1.html | Select-String "<img").Count
curl.exe -s http://localhost:8080/blog/blog1.html | Select-String 'href="/"'

# qua proxy
curl.exe -I http://localhost/blog/blog2.html
```

Kỳ vọng: toàn bộ `200`; thấy link `blog1/2/3.html`; số dòng `<img` > 0; có `href="/"`.
Ảnh chụp: `http://localhost/blog/` và 1–2 bài viết trên trình duyệt.

## MR2. Backend — API `/student` đọc JSON (0,5đ)

```powershell
curl.exe -s http://localhost/api/student
(Invoke-RestMethod http://localhost:8085/student).Count
```

Kỳ vọng: JSON **5 sinh viên** (`id`, `name`, `major`, `gpa`); lệnh thứ hai ra `5`.
Giao diện: `start http://localhost/students/` (tab Bài 2).

## MR3. Database — `studentdb` + bảng `students` (0,5đ)

```powershell
# cấu trúc + dữ liệu
docker exec relational-database-server mariadb -uroot -proot -e "USE studentdb; DESCRIBE students; SELECT * FROM students;"

# CRUD bằng SQL
docker exec relational-database-server mariadb -uroot -proot -e "USE studentdb; INSERT INTO students(student_id,fullname,dob,major) VALUES ('SV005','Ngo Gia Han','2004-09-09','Khoa hoc du lieu'); SELECT * FROM students;"
docker exec relational-database-server mariadb -uroot -proot -e "USE studentdb; UPDATE students SET major='DevOps' WHERE student_id='SV005'; SELECT * FROM students WHERE student_id='SV005';"
docker exec relational-database-server mariadb -uroot -proot -e "USE studentdb; DELETE FROM students WHERE student_id='SV005'; SELECT COUNT(*) AS con_lai FROM students;"

# Flask đọc từ database
curl.exe -s http://localhost/api/students-db
```

Kỳ vọng: bảng có 5 cột (`id`, `student_id`, `fullname`, `dob`, `major`), **≥ 3 bản ghi** (hiện có 4); API trả `{"count":4,"students":[...]}`.

CRUD qua API Flask (tuỳ chọn):

```powershell
$body = @{ student_id="SV006"; fullname="Test User"; dob="2004-01-01"; major="IT" } | ConvertTo-Json
$r = Invoke-RestMethod -Method Post -Uri http://localhost/api/students-db -ContentType "application/json" -Body $body
$r

$body2 = @{ student_id="SV006"; fullname="Test User 2"; dob="2004-01-01"; major="DevOps" } | ConvertTo-Json
Invoke-RestMethod -Method Put -Uri "http://localhost/api/students-db/$($r.id)" -ContentType "application/json" -Body $body2

Invoke-RestMethod -Method Delete -Uri "http://localhost/api/students-db/$($r.id)"
```

Kỳ vọng: lần lượt `Đã thêm`, `Đã cập nhật`, `Đã xóa`.

> Nếu DB đã tồn tại từ trước, file `init\002_studentdb.sql` không tự chạy. Nạp tay:
> `cmd /c "docker exec -i relational-database-server mariadb -uroot -proot --default-character-set=utf8mb4 < relational-database-server\init\002_studentdb.sql"`

## MR4. Keycloak — Realm + 2 user + client + token (0,5đ)

Realm `realm_523H0167`, user `sv01`, `sv02`, client `flask-app` (public). Thay `<MAT_KHAU_SV01>` bằng mật khẩu đã đặt cho sv01.

```powershell
# token endpoint của realm
(Invoke-RestMethod http://localhost:8081/realms/realm_523H0167/.well-known/openid-configuration).token_endpoint

# lấy access token
$r = Invoke-RestMethod -Method Post -Uri http://localhost:8081/realms/realm_523H0167/protocol/openid-connect/token `
  -Body @{ grant_type="password"; client_id="flask-app"; username="sv01"; password="<MAT_KHAU_SV01>" }
$r.access_token.Substring(0,40)

# /secure: không token -> 401, có token -> 200
curl.exe -s http://localhost/api/secure
Invoke-RestMethod -Uri http://localhost/api/secure -Headers @{ Authorization = "Bearer $($r.access_token)" }
```

Kỳ vọng:
- Không token: `{"error":"Missing Bearer token"}`.
- Có token: `message = Secure resource OK` (`preferred_username` là `sv01` hoặc rỗng tuỳ cấu hình token của Keycloak).

Ảnh chụp: Keycloak Console (realm, 2 user, client `flask-app`) + terminal kết quả `/secure`.

## MR5. MinIO — bucket `profile-pics` và `documents` (0,5đ)

Console `http://localhost:9001` (`minioadmin` / `minioadmin`):
1. Tạo bucket `profile-pics` → upload `avatar.jpg`.
2. Tạo bucket `documents` → upload file PDF báo cáo.
3. Đặt `profile-pics` là **Public** (Anonymous access → readonly) để có URL công khai.

```powershell
docker exec object-storage-server mc alias set local http://127.0.0.1:9000 minioadmin minioadmin
docker exec object-storage-server mc ls local
docker exec object-storage-server mc ls local/profile-pics
docker exec object-storage-server mc ls local/documents

# truy cập URL public (không cần đăng nhập)
curl.exe -I http://localhost:9000/profile-pics/avatar.jpg
```

Kỳ vọng: thấy 2 bucket; `curl.exe -I` trả `200 OK`, `Content-Type: image/jpeg`.
(Nếu bucket còn private sẽ trả `403` — cũng là minh chứng cho policy private/public.)

> Lưu ý: hiện mới có bucket `profile-pics` (gồm `avatar.jpg` và file PDF) và `demo`; cần tạo thêm bucket `documents` và chuyển PDF sang đó cho đúng đề.

## MR6. DNS — thêm bản ghi `app-backend`, `minio`, `keycloak` (0,5đ)

Zone `internal-dns-server\db.cloud.local` đã có:

```
app-backend IN A 10.10.10.20
minio       IN A 10.10.10.30
keycloak    IN A 10.10.10.40
```

```powershell
docker restart internal-dns-server
Start-Sleep -Seconds 5

"web-frontend-server","app-backend","minio","keycloak" | ForEach-Object {
  $ip = docker exec internal-dns-server dig +short "@127.0.0.1" "$_.cloud.local"
  "$_.cloud.local -> $ip"
}
```

Kỳ vọng: `10.10.10.10`, `10.10.10.20`, `10.10.10.30`, `10.10.10.40`.
Nếu sửa zone mà dig không đổi: tăng số serial trong dòng SOA rồi restart container.

## MR7. Prometheus — thêm target `web` (0,5đ)

Job trong `monitoring-prometheus-server\prometheus.yml`: `web` → `web-frontend-server:80` (đường dẫn `/metrics`).

```powershell
curl.exe -s http://localhost:8080/metrics | Select-Object -First 5

docker restart monitoring-prometheus-server
Start-Sleep -Seconds 20

Invoke-RestMethod http://localhost:9090/api/v1/targets |
  Select-Object -ExpandProperty data | Select-Object -ExpandProperty activeTargets |
  Select-Object @{n='job';e={$_.labels.job}}, health, scrapeUrl
```

Kỳ vọng:

```
job         health scrapeUrl
node        up     http://monitoring-node-exporter-server:9100/metrics
prometheus  up     http://localhost:9090/metrics
web         up     http://web-frontend-server:80/metrics
```

Ảnh chụp: `http://localhost:9090/targets` thấy job **web** màu xanh (UP).

## MR8. Grafana — Dashboard "System Health of <MSSV>" (0,5đ)

Dashboard tự nạp (provisioning), nằm trong folder `MyMiniCloud`.

```powershell
curl.exe -s -u admin:admin "http://localhost:3000/api/search?query=System%20Health" | ConvertFrom-Json | Select-Object title, uid, folderTitle

(curl.exe -s -u admin:admin http://localhost:3000/api/dashboards/uid/system-health | ConvertFrom-Json).dashboard.panels | Select-Object title
```

Kỳ vọng: tìm thấy dashboard `uid = system-health`; có các panel CPU Usage (%), Memory Usage, Network Traffic (và Application Logs).
Mở: `start http://localhost:3000/d/system-health` → chụp toàn bộ dashboard có dữ liệu và tiêu đề chứa MSSV.

PromQL dùng:
- CPU: `100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)`
- Memory: `100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)`
- Network: `rate(node_network_receive_bytes_total[5m])`

## MR9. Proxy — route `/student/` (0,5đ)

```powershell
docker restart api-gateway-proxy-server
Start-Sleep -Seconds 3

curl.exe -s http://localhost/student/
curl.exe -s -o NUL -w "%{http_code}`n" http://localhost/student/
```

Kỳ vọng: `200` và JSON danh sách sinh viên (giống `/api/student`).

## MR10. Load Balancer — Round Robin 2 web server (0,5đ)

Cấu hình trong `api-gateway-proxy-server\nginx.conf`:

```nginx
upstream web_backend {
  server web-frontend-server1:80;
  server web-frontend-server2:80;
}
```

```powershell
# 6 request liên tiếp, xem server nào phục vụ
1..6 | ForEach-Object { curl.exe -s -D - -o NUL http://localhost/ | Select-String "X-Served-By" }

# so sánh trực tiếp từng server
curl.exe -s -o NUL -w "server1: %{http_code}`n" http://localhost:8080/
curl.exe -s -o NUL -w "server2: %{http_code}`n" http://localhost:8082/
```

Kỳ vọng: `X-Served-By` luân phiên `web-frontend-server1`, `web-frontend-server2`, `web-frontend-server1`, ...
Trình duyệt: mở `http://localhost/` rồi F5 liên tục, badge góc phải dưới đổi giữa 2 server.
Ảnh chụp: terminal 6 dòng xen kẽ + 2 ảnh trình duyệt (mỗi ảnh một server).

---

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


Link docker hub: 'https://hub.docker.com/r/phathuynh2104/web', 'https://hub.docker.com/r/phathuynh2104/app'