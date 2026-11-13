# CloudDS Frontend – bản đồng bộ theo kiến trúc mới

**Cách tích hợp:** Giải nén ZIP. Copy nguyên thư mục `frontend/` vào **thư mục gốc repository** `XayDungHeThong_CloudDataStorage/`, chọn **Merge / Replace** các file frontend cũ. Không copy đè `backend/`, `database/`, `docs/`, `.git/`, hoặc `deploy/`. ZIP này chỉ chứa frontend.

## Cấu trúc thực tế

```text
frontend/
├── index.html
├── README.md
├── pages/
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── files.html
│   ├── trash.html
│   ├── plans.html
│   ├── checkout.html
│   ├── payment-result.html
│   ├── billing.html
│   ├── profile.html
│   └── admin.html
└── assets/
    ├── css/
    │   ├── main.css
    │   ├── components.css
    │   ├── auth.css
    │   └── dashboard.css
    ├── js/
    │   ├── api.js
    │   ├── ui.js
    │   ├── auth.js
    │   ├── dashboard.js
    │   ├── files.js
    │   ├── folders.js
    │   ├── plans.js
    │   ├── checkout.js
    │   ├── billing.js
    │   ├── profile.js
    │   └── admin.js
    ├── icons/favicon.svg
    ├── images/
    └── vendor/bootstrap/ (Bootstrap CSS và LICENSE)
```

## Những khác biệt quan trọng so với bản cũ

1. **Không còn giả lập đăng nhập/tải tệp:** đã bỏ `js/mocks/`, `js/services/auth-api.js`, `js/services/file.service.js` và dữ liệu session ảo. Các thao tác thành công **chỉ khi backend thực sự trả thành công**.
2. **Đường dẫn mới:** tất cả CSS, JS theo `frontend/assets/css/*` và `frontend/assets/js/*`, phù hợp cấu trúc repository đã tạo.
3. **Đúng hợp đồng `/api/v1`:** đăng ký `{full_name,email,password}`, session HttpOnly, CSRF, list/create/download/rename/move/trash, dashboard, plans, orders, payment và profile.
4. **Giá, tên và dung lượng gói lấy từ Flask API `GET /api/v1/plans`**, không giữ thông số cũ 1 GB / Plus 50 GB / Pro 200 GB hay tự đoán giá. Nếu backend chưa có, hiển thị trạng thái lỗi thay vì giá sai.
5. **Tách trang đúng phạm vi:** `dashboard.html` chỉ tổng quan; `files.html` quản lý tệp/thư mục; các trang trash/plans/checkout/payment-result/billing/profile/admin độc lập.
6. **Không gửi mật khẩu, khóa S3/Garage, khóa VNPay vào JavaScript**. Cookie tự gửi cùng origin với `credentials:'same-origin'`.
7. **Thanh toán không tự đánh dấu thành công từ URL**: `payment-result.html` luôn lấy trạng thái `/billing/orders/{id}` từ server, IPN là trách nhiệm backend.
8. `admin.html` có UI kiểm tra vai trò và một số thao tác cơ bản; **backend bắt buộc kiểm tra quyền admin**, ẩn menu không phải bảo mật.

## Chạy / xem giao diện trước khi có backend

- Chạy static server từ **thư mục gốc repository**, ví dụ:

  ```bash
  python -m http.server 8080
  ```

- Mở `http://localhost:8080/frontend/index.html` xem landing page.
- Có thể xem bố cục trang riêng tư mà **không giả đăng nhập** bằng URL như `http://localhost:8080/frontend/pages/dashboard.html?preview=1` hoặc `.../files.html?preview=1`. Trong preview, thao tác ghi **không dùng được**, dữ liệu không tự tạo.
- Form đăng ký / đăng nhập khi chưa có Flask API sẽ **báo lỗi kết nối**, không báo thành công giả.
- Khi backend hoàn thành, cần dùng Apache reverse proxy `/api/v1` cùng origin với frontend; `file://` không phải môi trường để kiểm thử API thật.

## Các API backend cần hiện thực

- `GET /api/v1/auth/csrf` trả `{success:true,data:{csrf_token:"..."}}`.
- `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`.
- `GET /dashboard/summary`, `/files`, `/folders`, `/trash`, `/plans`, `/billing/*`.
- `POST /files` (`FormData(file,parent_id)`), `/folders` (`name,parent_id`), `/billing/orders` (`plan_id`), `/payments/vnpay/checkout` (`order_id`).
- `PATCH /files/{id}`, `/folders/{id}`, `/users/me`, `POST /users/me/change-password`.
- `DELETE /files/{id}`, `/folders/{id}`, `/trash/{files|folders}/{id}`; `POST /trash/{files|folders}/{id}/restore`.
- `GET /billing/orders/{id}` là nguồn chân lý cho trạng thái thanh toán. Return/IPN là nghiệp vụ backend.

**Định dạng JSON** (theo `docs/04-api-contract.md`): `{success:true,data:...}` và lỗi `{success:false,error:{code,message}}`. List có `meta.total`, `page`, `page_size`. Các endpoint kể trên **chưa được tạo trong backend**, nên không thể có dữ liệu thực cho đến lúc tích hợp Flask + MySQL + Garage + VNPay.

## Những quyết định còn chờ chốt với backend

- Dung lượng Free/Basic/Pro, đơn giá, chu kỳ và kích thước tối đa một tệp: không hardcode vào frontend; được backend áp dụng.
- `GET /folders` đang hỗ trợ liệt kê thư mục theo `parent_id`, nhưng **chưa có API tìm kiếm thư mục trên toàn tài khoản**. Trang Files tìm toàn bộ **tệp** theo `GET /files?search=...`; kết quả **thư mục chỉ lọc trong thư mục đang mở**. Nếu muốn tìm toàn bộ thư mục, cần bổ sung API `/folders?search=` trong hợp đồng và backend.
- Move dialog tải cây thư mục bằng các lệnh GET /folders cho từng cấp (giới hạn 7 cấp / 500 mục cho UI). Backend vẫn quyết định quyền và chống di chuyển vào thư mục con.
- Quản trị nâng cao (tạo/sửa gói và nhiều trang admin) mới chỉ có phần nền; không coi là đã xây dựng đầy đủ.

## Ghi chú kỹ thuật

- Bootstrap CSS 5.3.3 được giữ lại từ bản nguồn, theo giấy phép kèm theo. Không có dependency node/npm.
- `assets/js/api.js` là client chung, có cookie + CSRF + parse JSON + download blob; không đưa token đăng nhập vào localStorage.
- Bảo vệ quyền truy cập, giới hạn upload, quota, kiểm tra tên tệp, CORS, CSRF, idempotent payment... **phải xử lý ở backend**.
