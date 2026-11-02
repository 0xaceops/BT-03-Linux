# Tin nhắn mẫu gửi nhóm (copy vào Zalo/Messenger/Discord)

Cả nhà ơi, mình đã dựng sẵn code BT-03. Mỗi bạn làm theo thứ tự:

1. Tạo VM Ubuntu Server (VMware, mạng **Bridged**), 4 vCPU / 8GB RAM / 30GB disk.
2. `git clone <LINK-REPO>` rồi làm theo **README.md** mục 2 → cài Docker + Tailscale (mình sẽ mời vào tailnet chung).
3. Vào thư mục `worker`, copy `.env.example` thành `.env` và điền:
   - GROUP = <số nhóm>
   - MEMBER_ID = <ID của bạn: 1, 2, 3, 4 hoặc 5>
   - API_URL = http://<IP-TAILSCALE-CORE>:8000
   - WORKER_TOKEN = <token mình gửi riêng>
   - NTFY_URL = <link ntfy mình gửi riêng>
   - Danh mục AI của bạn theo bảng phân công trong README mục 1
4. Chạy test: `docker compose up -d --build ai1`, thấy log "xong '...'" thì báo mình, rồi đổi MOCK=0 để chạy AI thật.
5. Cài app **ntfy** trên điện thoại, subscribe topic để xem log.

Hạn: <ngày>. Có lỗi thì gửi ảnh chụp `docker compose logs ai1` vào nhóm.

**Bảng phân công (5 người):**
- ID 1: VM-CORE + AI 1.1 (chuyên phục vụ tìm kiếm, PRIORITY_ONLY=1)
- ID 2: VM-MONITOR + AI 2.1 -> AI1_CATEGORIES=animals,plants
- ID 3: AI 3.1 -> food | AI 3.2 -> tools
- ID 4: AI 4.1 -> vehicles | AI 4.2 -> buildings
- ID 5: AI 5.1 -> space | AI 5.2 -> science,clothing
(AI2 chỉ chạy khi máy >= 12GB RAM: `docker compose --profile two up -d --build`)
