# Kho ảnh trực tuyến thông minh (BT-03)

Hệ thống gồm các module độc lập, mỗi module một thư mục + một `docker-compose.yml`:

| Module | Thư mục | Chạy ở VM nào | Vai trò |
|---|---|---|---|
| Database (PostgreSQL) | `core/` | VM-CORE | Metadata ảnh + hàng đợi job |
| Web/API + kho ảnh | `core/api` | VM-CORE | Trang chủ, tìm kiếm, nhận ảnh từ AI |
| Planner | `core/planner` | VM-CORE | Tự nghĩ chủ đề theo danh mục, giữ hàng đợi luôn đầy |
| Gateway | `core` (cloudflared) | VM-CORE | Phát hành ra Internet (link `https://xxx.trycloudflare.com`) |
| AI Worker | `worker/` | VM-WORKER (mỗi thành viên 1 VM) | Sinh ảnh bằng SD-Turbo chạy local trên CPU |
| ntfy + Beszel + Uptime Kuma | `monitor/` | VM-MONITOR | Log trên điện thoại + giám sát trực quan |

Luồng: `Planner → (hàng đợi job) → Worker → API → kho ảnh`. Khi người dùng tìm ảnh chưa có, API tạo job **ưu tiên 100**, worker rảnh vẽ ngay, trình duyệt chờ (có hiệu ứng "đang vẽ") rồi hiện ảnh; ảnh được lưu vào kho cho lần sau.

---
## 1. Phân bổ máy (nhóm 5 người)

| ID | Thành viên | VM chạy | AI (tên ảnh sẽ có đuôi) | Danh mục AI nhận |
|---|---|---|---|---|
| 1 | Nhóm trưởng (máy mạnh nhất) | VM-CORE + VM-WORKER | 1.1 (**PRIORITY_ONLY=1**, chuyên phục vụ người dùng tìm kiếm) | (nhận job người dùng) |
| 2 | Thành viên 2 | VM-MONITOR + VM-WORKER | 2.1 | `animals,plants` |
| 3 | Thành viên 3 | VM-WORKER | 3.1 / 3.2 | `food` / `tools` |
| 4 | Thành viên 4 | VM-WORKER | 4.1 / 4.2 | `vehicles` / `buildings` |
| 5 | Thành viên 5 | VM-WORKER | 5.1 / 5.2 | `space` / `science,clothing` |

Tổng 8 AI chạy liên tục, 5 VM-WORKER, 7 AI sinh ảnh nền + 1 AI dành riêng cho người dùng. Nếu máy ai yếu (< 12 GB RAM), chỉ chạy AI số 1 của mình và nhờ người khác nhận danh mục còn lại.

9 danh mục có sẵn: `animals plants food tools vehicles buildings space science clothing`. Ghép sao cho mọi danh mục đều có AI nhận. Muốn thêm danh mục: sửa `core/planner/topics.py`.

Cấu hình VM gợi ý: worker **4 vCPU / 8 GB RAM / 30 GB disk** (SD-Turbo cần ~5 GB RAM); CORE 2 vCPU / 4 GB; MONITOR 1–2 vCPU / 2 GB.

---
## 2. Chuẩn bị chung (mọi thành viên, trên VM Ubuntu Server)
```bash
sudo apt update && sudo apt install -y git
git clone <LINK-REPO-NHOM> kho-anh && cd kho-anh
bash scripts/install_docker.sh      # cài Docker + Tailscale
# đăng xuất rồi đăng nhập lại SSH, sau đó:
sudo tailscale up                   # cả nhóm dùng CHUNG 1 tailnet (nhóm trưởng mời các bạn)
tailscale ip -4                     # ghi lại IP 100.x.y.z của VM
```
Tailscale giúp các VM ở nhà từng người nói chuyện với nhau mà không cần mở port router. Mạng VMware nên đặt **Bridged**.

## 3. Nhóm trưởng: dựng VM-CORE
```bash
cd kho-anh/core
cp .env.example .env && nano .env     # đổi POSTGRES_PASSWORD, WORKER_TOKEN, NTFY_URL
docker compose up -d --build
docker compose logs tunnel | grep trycloudflare     # <- LINK CÔNG KHAI để nộp bài
curl localhost:8000/health
```
- Link `trycloudflare.com` miễn phí nhưng **đổi mỗi lần tunnel khởi động lại**. Muốn cố định: có tên miền → tạo Cloudflare *named tunnel* và thay `command` của service `tunnel` bằng `tunnel run --token <TOKEN>`.
- Gửi cho cả nhóm 3 thứ (qua nhóm chat riêng, không đưa lên repo): **IP Tailscale của VM-CORE**, **WORKER_TOKEN**, **NTFY_URL**.

## 4. Mỗi thành viên: dựng VM-WORKER
```bash
cd kho-anh/worker
cp .env.example .env && nano .env
```
Sửa: `GROUP` (số nhóm), `MEMBER_ID` (ID của bạn), `API_URL=http://<IP-Tailscale-CORE>:8000`, `WORKER_TOKEN`, `NTFY_URL`, `AI1_CATEGORIES`/`AI2_CATEGORIES` theo bảng phân công.

**Bước 1 – test đường truyền bằng ảnh giả:** giữ `MOCK=1`
```bash
docker compose up -d --build ai1
docker compose logs -f ai1          # thấy "xong '...'" là thông
```
**Bước 2 – bật AI thật:** đổi `MOCK=0`, chạy lại
```bash
docker compose up -d --build ai1                # 1 AI
docker compose --profile two up -d --build      # 2 AI (cần ≥ 12 GB RAM)
```
Lần đầu sẽ tải model `stabilityai/sd-turbo` (~2–3 GB). Nếu một ảnh mất quá lâu: giảm `GEN_SIZE=384`, `STEPS=1`; tăng vCPU cho VM.

## 5. VM-MONITOR (thành viên 2)
```bash
cd kho-anh/monitor && docker compose up -d
```
- **Beszel** `http://IP:8090`: tạo tài khoản → *Add system* → copy `HUB_URL/TOKEN/KEY` vào `.env` của từng VM worker/core (`BESZEL_HUB_URL`, `BESZEL_TOKEN`, `BESZEL_KEY`) rồi `docker compose --profile monitor up -d beszel-agent`. (Tên biến lấy đúng theo hướng dẫn hub hiển thị, vì Beszel có thể đổi theo phiên bản.)
- **Uptime Kuma** `http://IP:3001`: thêm monitor HTTP cho link công khai của website và cho từng VM.
- Chụp ảnh dashboard cho báo cáo.

## 6. Log trên điện thoại (ntfy và/hoặc Bark)
Hệ thống gửi log lên điện thoại bằng **ntfy** (Android/iPhone) và/hoặc **Bark** (iPhone). Điền trong `.env` của core và của mọi worker:
- ntfy: `NTFY_URL=https://ntfy.sh/ten-bi-mat-cua-nhom` (ntfy.sh công cộng là mã nguồn mở, dùng **topic bí mật**). Cài app **ntfy** → Subscribe đúng tên topic.
- Bark (iPhone): cài app Bark, lấy link dạng `https://api.day.app/KEY` → `BARK_URL=` (để trống nếu không dùng).
- Tự host ntfy: dùng service `ntfy` trong `monitor/`, thêm `--profile tunnel` để có link Internet rồi đặt `NTFY_URL=<link>/ten-topic`.

Thử nhanh khỏi cần chạy hệ thống: `curl -d "thu thong bao" https://ntfy.sh/ten-bi-mat-cua-nhom` → điện thoại phải rung.

Các sự kiện được gửi lên điện thoại:
| Nguồn | Thông báo |
|---|---|
| API | khởi động; **mỗi ảnh tự sinh mới** (đổi `NOTIFY_EVERY` nếu thấy nhiều quá); **người dùng tìm ảnh chưa có**; ảnh trả cho người dùng; lỗi worker |
| Worker | AI online (kèm phong cách + danh mục); model đã tải xong; lỗi khi vẽ; mỗi mốc 50 ảnh |
| Planner | online; mỗi lần thêm chủ đề mới theo danh mục; lỗi |
| Watchdog (trong API) | **AI nào mất kết nối > 5 phút (OFFLINE)** và khi AI hoạt động lại; tổng kết hệ thống mỗi 10 phút (số AI online, job chờ, số ảnh theo từng AI) |

## 7. Kiểm tra trước khi nộp
1. Mở link công khai bằng 4G: thấy ~50 ảnh mới nhất + ô tìm kiếm + bảng thống kê theo AI.
2. Gõ từ chưa có (vd `purple elephant`): hiện "đang vẽ" → ra ảnh → tìm lại thì có sẵn.
3. Tên ảnh đúng dạng `purple elephant 3.1.png`.
4. Điện thoại nhận log (ntfy/Bark): thử tắt 1 worker >5 phút để thấy cảnh báo OFFLINE; Beszel/Kuma hiển thị đủ các VM.
5. Chụp ảnh các bước trên cho báo cáo (dùng `REPORT_TEMPLATE.md`).

## 8. Sự cố thường gặp
| Triệu chứng | Cách xử lý |
|---|---|
| Worker log "khong lien lac duoc API" | Sai `API_URL`/chưa `tailscale up`; thử `curl http://IP-CORE:8000/health` |
| Lỗi 401 | `WORKER_TOKEN` khác với bên core |
| Tìm kiếm quay mãi | Không có worker nào chạy (xem cột "hoạt động gần nhất" ở bảng thống kê) |
| Tìm tiếng Việt ra ảnh lạ | Ô tìm kiếm chỉ hỗ trợ tiếng Anh theo đề bài |
| Hết RAM khi tải model | Tăng RAM VM ≥ 8 GB hoặc chỉ chạy 1 AI |
