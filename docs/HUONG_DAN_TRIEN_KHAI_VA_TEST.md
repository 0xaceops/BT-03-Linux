# HƯỚNG DẪN TRIỂN KHAI VÀ KIỂM THỬ HỆ THỐNG BT-03
## ĐỀ TÀI: KHO ẢNH TRỰC TUYẾN THÔNG MINH (DÀNH CHO CẢ 5 THÀNH VIÊN)

---

### PHẦN 1: TIN NHẮN TỔNG HỢP GỬI NHÓM CHAT (ZALO / MESSENGER / DISCORD)
*(Nhóm trưởng chỉ cần copy đoạn dưới đây gửi vào nhóm chat chung)*

```text
📢 THÔNG BÁO QUAN TRỌNG: TRIỂN KHAI & TEST BÀI TẬP 03 (BT-03) 📢

Cả nhóm ơi, mã nguồn hệ thống Kho ảnh trực tuyến thông minh đã hoàn thiện 100%. 
Tất cả 5 thành viên chúng ta đều phải tham gia chạy máy ảo VMware Ubuntu Server.

👉 BƯỚC 1: Cài đặt môi trường trên máy ảo Ubuntu:
1. Mở máy ảo, vào terminal chạy:
   cd kho-anh && bash scripts/install_docker.sh
2. Đăng xuất SSH rồi đăng nhập lại. Chạy lệnh:
   sudo tailscale up
   (Nhóm trưởng đã gửi link mời vào mạng Tailnet chung, các bạn bấm link xác thực nhé).
3. Lấy IP Tailscale máy mình: tailscale ip -4 (ghi lại IP 100.x.y.z).

👉 BƯỚC 2: Cài ứng dụng ntfy trên điện thoại:
- Cài app "ntfy" từ App Store hoặc Google Play.
- Bấm dấu "+" thêm topic bí mật của nhóm: [ĐIỀN_TÊN_TOPIC_Ở_ĐÂY]

👉 BƯỚC 3: Cấu hình Worker trên máy của từng bạn:
- Vào thư mục: cd kho-anh/worker
- Tạo file cấu hình: cp .env.example .env && nano .env
- Điền các thông tin riêng của bạn theo bảng phân công bên dưới:
  + GROUP = [Số nhóm của chúng ta từ 1-12]
  + MEMBER_ID = [ID của bạn: 1, 2, 3, 4 hoặc 5]
  + API_URL = http://[IP_TAILSCALE_MÁY_CORE]:8000
  + WORKER_TOKEN = [TOKEN_BÍ_MẬT_DO_NHÓM_TRƯỞNG_GỬI]
  + NTFY_URL = https://ntfy.sh/[TÊN_TOPIC_BÍ_MẬT]
  + Danh mục categories theo phân công

👉 BƯỚC 4: Chạy thử nghiệm:
- Bước đầu giữ MOCK=1 để test mạng: docker compose up -d --build ai1
- Xem log: docker compose logs -f ai1 (thấy báo "xong '...' trong 0.1s" là đã thông suốt).
- Đổi MOCK=0 để bật AI vẽ thật: docker compose up -d --build ai1 (chờ 2 phút tải model lần đầu).

Bảng phân công nhiệm vụ chi tiết xem tài liệu đính kèm nhé!
```

---

### PHẦN 2: BẢNG PHÂN CÔNG THÔNG SỐ CẤU HÌNH CHO 5 THÀNH VIÊN

| ID | Thành viên | Máy ảo đảm nhiệm | Tham số cấu hình trong file `worker/.env` | Ghi chú vận hành |
|:---:|---|---|---|---|
| **1** | **Nhóm trưởng** | **VM-CORE**<br>+ **VM-WORKER** | `MEMBER_ID=1`<br>`PRIORITY_ONLY=1`<br>`AI1_CATEGORIES=` *(để trống)* | Chạy Core + AI 1.1 chuyên phục vụ người dùng tìm kiếm |
| **2** | **Thành viên 2** | **VM-MONITOR**<br>+ **VM-WORKER** | `MEMBER_ID=2`<br>`PRIORITY_ONLY=0`<br>`AI1_CATEGORIES=animals,plants` | Chạy Monitor (Beszel, Uptime Kuma) + AI 2.1 |
| **3** | **Thành viên 3** | **VM-WORKER** | `MEMBER_ID=3`<br>`PRIORITY_ONLY=0`<br>`AI1_CATEGORIES=food`<br>`AI2_CATEGORIES=tools` | Chạy 2 AI nếu RAM ≥ 12GB:<br>`docker compose --profile two up -d` |
| **4** | **Thành viên 4** | **VM-WORKER** | `MEMBER_ID=4`<br>`PRIORITY_ONLY=0`<br>`AI1_CATEGORIES=vehicles`<br>`AI2_CATEGORIES=buildings` | Chạy 2 AI nếu RAM ≥ 12GB:<br>`docker compose --profile two up -d` |
| **5** | **Thành viên 5** | **VM-WORKER** | `MEMBER_ID=5`<br>`PRIORITY_ONLY=0`<br>`AI1_CATEGORIES=space`<br>`AI2_CATEGORIES=science,clothing` | Chạy 2 AI nếu RAM ≥ 12GB:<br>`docker compose --profile two up -d` |

---

### PHẦN 3: HƯỚNG DẪN CHI TIẾT DÀNH RIÊNG CHO TỪNG VAI TRÒ

#### 🧑‍💻 DÀNH CHO NHÓM TRƯỞNG (MÁY ID 1 – DỰNG VM-CORE)
*Nhóm trưởng cần dựng trước để lấy link web và token gửi các bạn.*

1. **Vào thư mục core và cấu hình:**
   ```bash
   cd kho-anh/core
   cp .env.example .env
   nano .env
   ```
   - Đặt `POSTGRES_PASSWORD` (ví dụ: `khoanh_matkhau_2026`)
   - Đặt `WORKER_TOKEN` (ví dụ: `token_nhom_bi_mat_987654`)
   - Đặt `NTFY_URL` (ví dụ: `https://ntfy.sh/kho-anh-nhomX-secret`)
   - Bấm `Ctrl+O` -> `Enter` để lưu, `Ctrl+X` để thoát.

2. **Khởi động toàn bộ cụm Core:**
   ```bash
   docker compose up -d --build
   ```

3. **Kiểm tra trạng thái & lấy link nộp bài:**
   ```bash
   # Kiểm tra API
   curl localhost:8000/health
   # Kết quả: {"ok": true} là thành công!

   # Lấy link công khai truy cập từ Internet
   docker compose logs tunnel | grep trycloudflare
   ```
   *Lưu lại link có đuôi `.trycloudflare.com` gửi vào nhóm chat!*

4. **Chạy thêm Worker AI 1.1 trên máy Nhóm trưởng:**
   ```bash
   cd ../worker
   cp .env.example .env
   nano .env
   ```
   *(Điền `MEMBER_ID=1`, `PRIORITY_ONLY=1`, `API_URL=http://localhost:8000`, rồi chạy `docker compose up -d --build ai1`).*

---

#### 🧑‍💻 DÀNH CHO THÀNH VIÊN 2 (MÁY ID 2 – DỰNG VM-MONITOR + WORKER)

1. **Khởi động cụm giám sát:**
   ```bash
   cd kho-anh/monitor
   docker compose up -d
   ```
2. **Truy cập Dashboard qua trình duyệt:**
   - **Beszel** (theo dõi CPU/RAM 5 máy): `http://<IP-Tailscale-máy-bạn>:8090` -> Tạo tài khoản admin.
   - **Uptime Kuma** (theo dõi website): `http://<IP-Tailscale-máy-bạn>:3001` -> Bấm *Add Monitor* -> Điền link `https://xxx.trycloudflare.com` của nhóm.
3. **Cấu hình Worker AI 2.1 của mình:**
   ```bash
   cd ../worker
   cp .env.example .env
   nano .env
   ```
   - Điền: `MEMBER_ID=2`, `AI1_CATEGORIES=animals,plants`, `API_URL=http://<IP-Tailscale-CORE>:8000`, `WORKER_TOKEN=...`, `MOCK=1`.
   - Chạy: `docker compose up -d --build ai1`.

---

#### 🧑‍💻 DÀNH CHO THÀNH VIÊN 3, 4, 5 (MÁY ID 3, 4, 5 – DỰNG VM-WORKER)

1. **Vào thư mục worker:**
   ```bash
   cd kho-anh/worker
   cp .env.example .env
   nano .env
   ```
2. **Điền thông số (ví dụ Thành viên 3):**
   ```ini
   GROUP=1                 # Đổi theo số nhóm của lớp (1 đến 12)
   MEMBER_ID=3             # Đổi thành ID của bạn (3, 4 hoặc 5)
   API_URL=http://100.x.y.z:8000   # Điền đúng IP Tailscale máy Core do nhóm trưởng gửi
   WORKER_TOKEN=token_nhom_bi_mat_987654
   NTFY_URL=https://ntfy.sh/kho-anh-nhomX-secret
   AI1_CATEGORIES=food
   AI2_CATEGORIES=tools
   PRIORITY_ONLY=0
   MOCK=1                  # Giữ 1 để test trước
   ```
3. **Chạy test ban đầu:**
   ```bash
   docker compose up -d --build ai1
   docker compose logs -f ai1
   ```
   *Thấy log báo `xong '...' trong 0.1s` -> Báo nhóm trưởng ngay!*

4. **Chuyển sang bật AI thật:**
   - Mở lại file `.env`: sửa `MOCK=0`.
   - Nếu máy có 8GB RAM (chạy 1 AI):
     ```bash
     docker compose up -d --build ai1
     ```
   - Nếu máy có ≥ 12GB RAM (chạy cả 2 AI):
     ```bash
     docker compose --profile two up -d --build
     ```

---

### PHẦN 4: 5 BƯỚC KIỂM THỬ NGHIỆM THU & CHỤP ẢNH DEMO NỘP BÁO CÁO

Cả nhóm mở link website `https://xxx.trycloudflare.com` và thực hiện:

- [ ] **Test 1 – Truy cập qua mạng di động 4G:** Dùng điện thoại tắt Wi-Fi, bật 4G mở link web. Kiểm tra thấy 50 ảnh mới nhất kèm tên tệp (ví dụ `black cat 2.1.png`).  
  📸 *Chụp ảnh màn hình 1.*

- [ ] **Test 2 – Tìm kiếm ảnh có sẵn:** Nhập từ khóa đã có ảnh trên màn hình (ví dụ: `cat`, `dog`, `apple`) -> Nhấn **Tìm** -> Kết quả trả về ngay lập tức không cần đợi.  
  📸 *Chụp ảnh màn hình 2.*

- [ ] **Test 3 – Tìm kiếm ảnh CHƯA CÓ (Tự vẽ tức thời on-the-fly):**  
  - Nhập từ khóa độc lạ: `purple bicycle` hoặc `golden robot` -> Nhấn **Tìm**.
  - Màn hình lập tức hiện biểu tượng xoay và đếm giây: *"Kho chưa có ảnh này — AI đang vẽ mới cho bạn... 3s, 5s..."*.
  - Điện thoại nảy thông báo ntfy: *"User search: purple bicycle"*.
  - Sau ~10s, ảnh vẽ xong hiện ra với viền đỏ nổi bật.
  - Tìm lại từ này ở tab ẩn danh -> Trả về ngay lập tức (đã lưu vào kho).  
  📸 *Chụp ảnh màn hình 3.*

- [ ] **Test 4 – Thống kê chi tiết theo từng AI:** Cuộn xuống chân trang, kiểm tra bảng thống kê thấy xuất hiện đầy đủ các tiến trình từ `AI 1.1` đến `AI 5.2` với số ảnh tăng đều.  
  📸 *Chụp ảnh màn hình 4.*

- [ ] **Test 5 – Cảnh báo sự cố trên điện thoại & Giám sát:**  
  - Một bạn thử dừng worker: `docker compose stop ai1`.
  - Sau 5 phút, điện thoại của cả 5 bạn sẽ rung chuông cảnh báo: *"AI X.1 OFFLINE - mat ket noi 300s"*.
  - Khi bạn đó bật lại `docker compose start ai1`, điện thoại báo *"AI X.1 online lai"*.
  - Mở dashboard Beszel (`http://IP-MONITOR:8090`) xem biểu đồ CPU/RAM 5 máy.  
  📸 *Chụp ảnh màn hình 5.*

---

### PHẦN 5: CÁC LỖI THƯỜNG GẶP VÀ CÁCH XỬ LÝ NHANH

| Hiện tượng | Nguyên nhân | Cách khắc phục |
|---|---|---|
| **Worker log báo: `khong lien lac duoc API`** | Sai `API_URL` hoặc chưa bật Tailscale | 1. Chạy `sudo tailscale up` trên cả 2 máy.<br>2. Chạy `curl http://IP-CORE:8000/health` để test thông mạng. |
| **Worker log báo: `401 bad token`** | `WORKER_TOKEN` trong worker khác với core | Mở file `.env` của worker, copy lại chính xác token từ file `.env` của core. |
| **Tìm kiếm trên web quay mãi không ra ảnh** | Không có AI worker nào đang online | Nhìn bảng thống kê chân trang xem có AI nào có "Hoạt động gần nhất" trong vòng 1 phút không. Bật lại worker. |
| **Máy bị treo/đơ khi tải model SD-Turbo** | Máy ảo bị thiếu RAM (< 8GB) | Tăng RAM máy ảo lên 8GB, hoặc sửa file `.env`: `GEN_SIZE=384`, `STEPS=1`. |
| **Tìm tiếng Việt ra ảnh lạ** | Đề bài quy định tìm bằng tiếng Anh | Hướng dẫn người dùng chỉ nhập từ khóa tiếng Anh (ví dụ: `blue bird` thay vì `chim xanh`). |
