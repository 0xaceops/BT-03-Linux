# BÁO CÁO BT-03 – KHO ẢNH TRỰC TUYẾN THÔNG MINH
Nhóm: …  Phong cách: …  Thành viên: …  Link website: …

## 1. Tổng quan & sơ đồ kiến trúc
(Người dùng → Cloudflare Tunnel → API → DB/Kho ảnh ← Worker ← Planner)
## 2. Module và phân bổ lên máy chủ
(bảng: module – VM – máy của thành viên nào – IP Tailscale – tài nguyên)
## 3. Lựa chọn công nghệ và lý do
| Thành phần | Chọn | Lý do |
|---|---|---|
| Mô hình sinh ảnh | SD-Turbo (diffusers) | Chưng cất, 1–2 bước, chạy được trên CPU, nguồn mở |
| Ép phong cách | Prompt suffix + hậu xử lý Pillow | Không cần GPU/LoRA, đảm bảo đúng phong cách |
| AI lập kế hoạch | Planner theo danh mục (tùy chọn LLM Qwen2.5 qua Ollama) | Chia nhiệm vụ, tránh trùng ảnh |
| Backend | FastAPI | Nhẹ, nhanh |
| CSDL & tìm kiếm | PostgreSQL + pg_trgm | Tìm gần đúng theo tên; hàng đợi `FOR UPDATE SKIP LOCKED` |
| Hàng đợi | Bảng `jobs` có mức ưu tiên | Ít thành phần hơn Redis, đủ cho quy mô bài tập |
| Phát hành | Cloudflare Tunnel | Miễn phí, không cần IP tĩnh/mở port |
| Kết nối VM | Tailscale | VM ở nhà các thành viên nối an toàn |
| Đóng gói | Docker Compose | Mỗi module nâng cấp riêng: `docker compose up -d --build <module>` |
| Log | ntfy | Mã nguồn mở, xem log trên điện thoại |
| Giám sát | Beszel + Uptime Kuma | Nhẹ, trực quan CPU/RAM từng VM và trạng thái website |
## 4. Luồng hoạt động
(tự sinh nền / tìm kiếm có sẵn / tìm kiếm chưa có → sinh mới → lưu lại)
## 5. Quy ước đặt tên ảnh: `<mô tả> <ID thành viên>.<số AI>.png`
## 6. Tính độc lập & khả năng nâng cấp module
## 7. Hình chụp demo
(trang chủ; tìm kiếm sinh ảnh mới; thống kê theo AI; ntfy trên điện thoại; Beszel; Uptime Kuma; docker ps từng VM)
## 8. Khó khăn gặp phải & hướng phát triển
## 9. Phân công thành viên
