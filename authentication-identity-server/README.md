# Authentication & Identity Server (Keycloak)

Không cần file cấu hình riêng — toàn bộ cấu hình nằm trong `docker-compose.yml`
(service `authentication-identity-server`).

- Image: `quay.io/keycloak/keycloak:latest`
- Chế độ: `start-dev`
- Admin bootstrap: `admin` / `admin`
- Truy cập: http://localhost:8081
