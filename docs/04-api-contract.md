# CLOUDDS — HỢP ĐỒNG API FRONTEND ↔ BACKEND

**Phiên bản:** v1.0 (bản đề xuất để hai thành viên thống nhất)  
**Phạm vi:** Đặc tả URL, phương thức, dữ liệu yêu cầu, dữ liệu phản hồi, quyền và lỗi. **Chưa triển khai API; chưa thiết kế SQL**.  
**Căn cứ:** `docs/01-requirements.md`, cấu trúc `frontend/`, `backend/app/routes/` hiện có trong repo.

## 1. Quy ước chung — bắt buộc thống nhất

| Mục | Quy định |
|---|---|
| Base URL | `/api/v1` — cùng origin với website qua Apache |
| Dữ liệu thường | `Content-Type: application/json; charset=utf-8` |
| Upload | `multipart/form-data` với field `file` và `parent_id` |
| Download | Trả dữ liệu nhị phân và `Content-Disposition: attachment` |
| Xác thực | Cookie phiên `HttpOnly`, `SameSite=Lax`; `Secure` trên HTTPS; **không lưu JWT/token đăng nhập trong localStorage** |
| Frontend `fetch` | Dùng `credentials: 'same-origin'`; truyền `X-CSRF-Token` ở các thao tác ghi (ngoại trừ callback của VNPay) |
| CSRF | `GET /api/v1/auth/csrf` cấp token; frontend tải lại token sau login khi session được tạo mới |
| ID | Chuỗi UUID, ví dụ `7d356f27-3424-4d9d-9c4e-a2530097a92a` |
| Ngày/giờ | ISO 8601 UTC: `2026-11-13T07:00:00Z` |
| Kích thước | Số nguyên `size_bytes`, `used_bytes`, `quota_bytes` |
| Giá tiền | Số nguyên `price_vnd` hoặc `amount_vnd`; đơn vị đồng Việt Nam, không nhân 100 trong JSON nội bộ |
| Root folder | Dùng literal chuỗi `root` khi gửi `parent_id`; backend đổi thành quan hệ không có cha |
| Phân trang | `page` mặc định 1, `page_size` mặc định 20, giới hạn tối đa do backend quy định (đề xuất 100) |
| Sắp xếp | `sort=name|created_at|size_bytes`, `order=asc|desc` nơi phù hợp |
| Quyền riêng tư | Mọi truy vấn/file ID phải kiểm tra user sở hữu; không tin `user_id` client tự gửi |
| Quản trị | Các endpoint `/admin/*` yêu cầu `role=admin` |
| Phương thức thay đổi | `POST` tạo, `PATCH` sửa một phần, `DELETE` xóa, `GET` chỉ đọc |
| Callback thanh toán | Các GET do VNPay gọi có tham số riêng, KHÔNG theo JSON envelope thông thường |

> Lưu ý: Về thiết kế, Flask sẽ nhận request từ Apache qua `/api/v1`. Chưa cấu hình Apache/Gunicorn tại bước này. Đầu vào API là **hợp đồng giữa hai người**, không phải tên trường/khóa MySQL.

### 1.1. Phản hồi thành công chuẩn

Đối tượng đơn:

```json
{
  "success": true,
  "data": {"id": "...", "name": "..."}
}
```

Danh sách có phân trang:

```json
{
  "success": true,
  "data": [{"id": "...", "name": "..."}],
  "meta": {"page": 1, "page_size": 20, "total": 1}
}
```

### 1.2. Phản hồi lỗi chuẩn

```json
{
  "success": false,
  "error": {
    "code": "QUOTA_EXCEEDED",
    "message": "Dung lượng lưu trữ không đủ.",
    "details": {"available_bytes": 1048576, "required_bytes": 2097152}
  }
}
```

| HTTP | Ví dụ mã lỗi | Cách frontend xử lý |
|---|---|---|
| `400` | `VALIDATION_ERROR` | Hiển thị thông báo/đánh dấu input sai |
| `401` | `UNAUTHENTICATED`, `INVALID_CREDENTIALS` | Với API cần đăng nhập, chuyển về trang login |
| `403` | `FORBIDDEN`, `CSRF_INVALID` | Không cho thao tác, hiển thị lỗi |
| `404` | `RESOURCE_NOT_FOUND` | Không thấy đối tượng hoặc không sở hữu đối tượng (tránh lộ tồn tại) |
| `409` | `EMAIL_ALREADY_EXISTS`, `DUPLICATE_NAME`, `INVALID_STATE`, `QUOTA_EXCEEDED` | Hiển thị lỗi nghiệp vụ |
| `413` | `FILE_TOO_LARGE` | Thông báo giới hạn upload |
| `422` | `INVALID_FIELD` | Đánh dấu trường sai hoặc thiếu |
| `429` | `RATE_LIMITED` | Báo thử lại sau |
| `500` | `INTERNAL_ERROR` | Hiển thị lỗi chung; không lộ stack trace |
| `503` | `SERVICE_UNAVAILABLE` | Báo hệ thống tạm không sẵn sàng |

**Quy ước:** Phần `error.message` để người dùng đọc, `error.code` để JS xử lý chính xác. Không dựa vào chuỗi message để xác định loại lỗi.

## 2. Đối tượng JSON chung (frontend và backend phải khớp)

### User (KHÔNG có password/password_hash)

```json
{
  "id": "UUID",
  "full_name": "Nguyen Van A",
  "email": "a@example.com",
  "role": "user",
  "status": "active",
  "created_at": "2026-11-13T07:00:00Z"
}
```

### File metadata

```json
{
  "id": "UUID",
  "name": "baitap.pdf",
  "parent_id": "root",
  "size_bytes": 256000,
  "mime_type": "application/pdf",
  "created_at": "2026-11-13T07:00:00Z",
  "updated_at": "2026-11-13T07:00:00Z"
}
```

**Không trả `object_key`, Garage secret, đường dẫn hệ thống hay user khác** trong dữ liệu file public API.

### Folder

```json
{
  "id": "UUID",
  "name": "Mon Hoc",
  "parent_id": "root",
  "created_at": "2026-11-13T07:00:00Z",
  "updated_at": "2026-11-13T07:00:00Z"
}
```

### Plan

```json
{
  "id": "UUID",
  "code": "basic",
  "name": "Basic",
  "price_vnd": 39000,
  "quota_bytes": 21474836480,
  "duration_days": 30,
  "is_active": true
}
```

`price_vnd: 39000` **chỉ là giá ví dụ để minh họa JSON**, KHÔNG phải giá Basic đã chốt. Khi làm thật, backend phải cài đặt giá phù hợp; chỉ Free mặc định miễn phí. Gói Free có thể để `duration_days: null`.

### Subscription

```json
{
  "plan": {"id": "UUID", "code": "free", "name": "Free"},
  "status": "active",
  "quota_bytes": 5368709120,
  "used_bytes": 102400,
  "started_at": "2026-11-13T07:00:00Z",
  "expires_at": null
}
```

### Order

```json
{
  "id": "UUID",
  "plan_id": "UUID",
  "amount_vnd": 39000,
  "status": "pending",
  "created_at": "2026-11-13T07:00:00Z"
}
```

Trạng thái order: `pending`, `paid`, `failed`, `cancelled`, `expired`. Số tiền chỉ do backend lấy từ gói tương ứng.

## 3. Danh sách API đầy đủ

**Ký hiệu quyền:** `Public` không yêu cầu login, `User` yêu cầu login và quyền trên đối tượng, `Admin` yêu cầu quản trị, `VNPay` callback bên ngoài có xác minh chữ ký. **Mức P0/P1** theo tài liệu yêu cầu chức năng.

### 3.1. Xác thực và hồ sơ — `backend/app/routes/auth.py`, `users.py`

| Method | Endpoint | Quyền | Mức | Chức năng |
|---|---|---|---|---|
| GET | `/api/v1/auth/csrf` | Public | P0 | Lấy CSRF token cho phiên trình duyệt |
| POST | `/api/v1/auth/register` | Public | P0 | Đăng ký, tự cấp Free |
| POST | `/api/v1/auth/login` | Public | P0 | Đăng nhập và cấp cookie phiên |
| POST | `/api/v1/auth/logout` | User | P0 | Kết thúc phiên |
| GET | `/api/v1/auth/me` | User | P0 | Thông tin người đang đăng nhập |
| PATCH | `/api/v1/users/me` | User | P1 | Đổi họ tên hiển thị |
| POST | `/api/v1/users/me/change-password` | User | P1 | Đổi mật khẩu |

**POST `/auth/register`** — JSON:

```json
{"full_name":"Nguyen Van A","email":"a@example.com","password":"StrongPass#123"}
```

Trả `201 Created`, `data.user` theo đối tượng User, không tự đăng nhập. `EMAIL_ALREADY_EXISTS` nếu trùng email. Sau đăng ký điều hướng sang login.

**POST `/auth/login`** — JSON:

```json
{"email":"a@example.com","password":"StrongPass#123"}
```

Trả `200`, `data.user`, đồng thời backend thiết lập cookie phiên. Đăng nhập xong frontend gọi lại `GET /auth/csrf` rồi chuyển Dashboard. Không đưa cookie/token vào JSON.

**GET `/auth/me`** — trả `data.user`. Nếu phiên hết hạn trả `401`.

**PATCH `/users/me`** — `{"full_name":"Ten moi"}`; trả user mới.

**POST `/users/me/change-password`** — `{"current_password":"...","new_password":"..."}`; trả message thành công, không echo mật khẩu.

### 3.2. Dashboard — `backend/app/routes/users.py`

| Method | Endpoint | Quyền | Mức | Chức năng |
|---|---|---|---|---|
| GET | `/api/v1/dashboard/summary` | User | P0 | Tổng quan tài khoản: quota, số tệp, số thư mục và gói hiện tại |

Ví dụ `data`:

```json
{
  "storage": {"used_bytes": 1048576, "quota_bytes": 5368709120, "remaining_bytes": 5367660544},
  "counts": {"files": 8, "folders": 3},
  "subscription": {"plan_code": "free", "plan_name": "Free", "expires_at": null}
}
```

### 3.3. Tệp — `backend/app/routes/files.py`

| Method | Endpoint | Quyền | Mức | Chức năng |
|---|---|---|---|---|
| GET | `/api/v1/files?parent_id=root&page=1&page_size=20` | User | P0 | Danh sách tệp trong thư mục |
| GET | `/api/v1/files?search=bao-cao` | User | P1 | Tìm toàn bộ tệp đang hoạt động thuộc user |
| POST | `/api/v1/files` | User | P0 | Upload tệp qua `multipart/form-data` |
| GET | `/api/v1/files/{file_id}` | User | P0 | Metadata một tệp |
| GET | `/api/v1/files/{file_id}/download` | User | P0 | Download nhị phân (không dùng JSON envelope) |
| PATCH | `/api/v1/files/{file_id}` | User | P1 | Đổi tên/chuyển thư mục |
| DELETE | `/api/v1/files/{file_id}` | User | P1 | Xóa mềm đưa vào Trash |

**GET `/files`** — `data` là mảng File; `meta` chứa phân trang. Khi có `search`, tìm theo tên trong toàn bộ thư mục user (không đồng thời lọc `parent_id`). Có thể thêm `sort`, `order`.

**POST `/files`** — `multipart/form-data`:

```text
file       = (binary bytes of baitap.pdf)
parent_id  = root
```

Trả `201` + File metadata. Backend phải kiểm tra session, CSRF, folder owner, kích thước upload, quota; rồi lưu file ở Garage và metadata. Nếu lỗi `QUOTA_EXCEEDED`, `FILE_TOO_LARGE`, `RESOURCE_NOT_FOUND`, `SERVICE_UNAVAILABLE` thì frontend hiện thông báo và **không tự thêm tệp vào danh sách**.

**PATCH `/files/{file_id}`** — có thể gửi một hoặc hai trường:

```json
{"name":"baitap_moi.pdf","parent_id":"UUID"}
```

Trả file đã cập nhật; phải kiểm tra trùng tên trong thư mục đích. Đổi tên/chuyển thư mục logic không bắt buộc di chuyển object Garage.

**DELETE `/files/{file_id}`** — trả `200` + `{"id":"UUID","trashed":true}`; file vẫn tính quota đến khi xóa vĩnh viễn.

### 3.4. Thư mục — `backend/app/routes/folders.py`

| Method | Endpoint | Quyền | Mức | Chức năng |
|---|---|---|---|---|
| GET | `/api/v1/folders?parent_id=root` | User | P0 | Liệt kê thư mục con |
| POST | `/api/v1/folders` | User | P0 | Tạo thư mục |
| PATCH | `/api/v1/folders/{folder_id}` | User | P1 | Đổi tên/chuyển thư mục |
| DELETE | `/api/v1/folders/{folder_id}` | User | P1 | Xóa mềm thư mục và cây con |

**POST `/folders`** — `{"name":"Bai tap","parent_id":"root"}` → `201` + Folder.

**PATCH `/folders/{folder_id}`** — `{"name":"Tai lieu","parent_id":"UUID"}` → `200` + Folder. Từ chối vòng lặp cha/con.

**DELETE `/folders/{folder_id}`** — `200` + `{"id":"UUID","trashed":true}`; đồng thời đánh dấu cây con đã xóa, không xóa bytes trong Garage ngay.

### 3.5. Thùng rác — `backend/app/routes/files.py`, `folders.py`

| Method | Endpoint | Quyền | Mức | Chức năng |
|---|---|---|---|---|
| GET | `/api/v1/trash?page=1&page_size=20` | User | P1 | Xem các mục gốc đã xóa mềm |
| POST | `/api/v1/trash/{type}/{id}/restore` | User | P1 | Khôi phục tệp/thư mục |
| DELETE | `/api/v1/trash/{type}/{id}` | User | P1 | Xóa vĩnh viễn |

`type` chỉ nhận `files` hoặc `folders`.

**GET `/trash`** — `data`: `[ {"type":"file","id":"UUID","name":"baitap.pdf","deleted_at":"..."} ]`, danh sách chỉ hiển thị mục bị xóa trực tiếp (không lặp cả cây con của thư mục đã xóa).

**POST `/trash/files/{id}/restore`** — body `{}` (mặc định khôi phục về vị trí cũ nếu còn tồn tại; nếu cha không còn thì về root). Có thể chỉ định `{"parent_id":"UUID"}` để chọn nơi khôi phục. Trả metadata đã khôi phục.

**DELETE `/trash/files/{id}`** — trả `200` + `{"id":"UUID","permanently_deleted":true}`; backend xóa object Garage và metadata theo quy trình nhất quán, giảm quota sau khi bảo đảm xóa thành công. Xóa vĩnh viễn thư mục xử lý tất cả nội dung trong cây.

### 3.6. Gói dịch vụ — `backend/app/routes/plans.py`

| Method | Endpoint | Quyền | Mức | Chức năng |
|---|---|---|---|---|
| GET | `/api/v1/plans` | Public | P0 | Liệt kê các gói đang được bán |
| GET | `/api/v1/plans/{plan_id}` | Public | P0 | Chi tiết một gói |

`GET /plans` → mảng Plan. Chỉ các gói `is_active=true` được giới thiệu cho người dùng.

### 3.7. Billing và đơn hàng — `backend/app/routes/billing.py`

| Method | Endpoint | Quyền | Mức | Chức năng |
|---|---|---|---|---|
| GET | `/api/v1/billing/subscription` | User | P0 | Gói hiện tại, quota, ngày hết hạn |
| POST | `/api/v1/billing/orders` | User | P0 | Tạo đơn hàng theo plan trả phí |
| GET | `/api/v1/billing/orders?page=1&page_size=20` | User | P0 | Lịch sử đơn |
| GET | `/api/v1/billing/orders/{order_id}` | User | P0 | Chi tiết và trạng thái đơn |
| GET | `/api/v1/billing/invoices?page=1&page_size=20` | User | P0 | Lịch sử biên nhận nội bộ |
| GET | `/api/v1/billing/invoices/{invoice_id}` | User | P0 | Chi tiết biên nhận |

**POST `/billing/orders`** — `{"plan_id":"UUID"}` → `201` + Order trạng thái `pending`. Backend lấy `amount_vnd` từ gói hiện hành, **từ chối client truyền giá**. Gói Free được chọn không cần mua đơn.

**GET `/billing/orders/{order_id}`** — trả Order của người đang đăng nhập. Đây là API frontend `payment-result.html` gọi để hiển thị trạng thái thật, kể cả khi IPN đến chậm.

**GET `/billing/invoices/{invoice_id}`** — dữ liệu biên nhận gồm `id`, `order_id`, `amount_vnd`, `status`, `issued_at`. Đây là **biên nhận/giao dịch của demo**, không mặc định là hóa đơn VAT có giá trị pháp lý.

### 3.8. VNPay Sandbox — `backend/app/routes/payments.py`

| Method | Endpoint | Quyền | Mức | Chức năng |
|---|---|---|---|---|
| POST | `/api/v1/payments/vnpay/checkout` | User | P0 | Tạo URL chuyển sang VNPay cho đơn `pending` |
| GET | `/api/v1/payments/vnpay/return` | Public / VNPay redirect | P0 | Xác minh dữ liệu redirect và dẫn tới trang kết quả |
| GET | `/api/v1/payments/vnpay/ipn` | VNPay callback | P0 | Xác minh checksum + đơn + số tiền + trạng thái và cập nhật giao dịch |

**POST `/payments/vnpay/checkout`** — JSON:

```json
{"order_id":"UUID"}
```

Trả JSON:

```json
{
  "success": true,
  "data": {
    "order_id": "UUID",
    "checkout_url": "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html?..."
  }
}
```

Frontend dùng `window.location.assign(data.checkout_url)` để chuyển người dùng. URL không được nối thủ công từ JS, cũng không gửi `vnp_HashSecret` ra frontend.

**GET `/payments/vnpay/return`** — VNPAY redirect trình duyệt kèm query parameters. Backend có thể kiểm tra chữ ký và chuyển hướng (HTTP 302) đến `/pages/payment-result.html?order_id=...`, không lấy `success` từ URL để tăng gói. Trang kết quả gọi API order để đọc trạng thái thực.

**GET `/payments/vnpay/ipn`** — Server VNPay gọi về; backend kiểm tra chữ ký, tìm giao dịch, đối chiếu đơn, số tiền, trạng thái và áp dụng thay đổi một lần. Phản hồi **JSON theo đặc tả `RspCode`/`Message` của VNPay**, không dùng envelope CloudDS ở mục 1.1. Callback không dùng cookie người dùng và không dùng CSRF; bảo vệ bằng kiểm tra chữ ký và dữ liệu đối soát.

**Lưu ý vận hành:** IPN cần URL HTTPS công khai để phía VNPay gọi được; khi chạy trên laptop offline sẽ không có IPN thực nếu không có đường truy cập công khai. Cần tài khoản VNPay Sandbox và bộ thông số kết nối hợp lệ.

### 3.9. Admin (P1) — `backend/app/routes/admin.py`

| Method | Endpoint | Quyền | Mức | Chức năng |
|---|---|---|---|---|
| GET | `/api/v1/admin/users?page=1&page_size=20` | Admin | P1 | Danh sách user |
| PATCH | `/api/v1/admin/users/{user_id}` | Admin | P1 | Đổi `status`: `active` / `disabled` |
| GET | `/api/v1/admin/plans` | Admin | P1 | Xem tất cả gói, kể cả đang tắt |
| POST | `/api/v1/admin/plans` | Admin | P1 | Tạo gói mới |
| PATCH | `/api/v1/admin/plans/{plan_id}` | Admin | P1 | Sửa mô tả, giá, quota cho lượt mua mới / tắt bán |
| GET | `/api/v1/admin/metrics` | Admin | P1 | Thống kê số user, file, dung lượng đang dùng |

Backend phải khóa quyền theo role, không dựa vào việc frontend ẩn menu. Gói đã bán phải giữ quyền lợi phù hợp với giao dịch trước khi sửa giá/quota.

### 3.10. Health check — `backend/app/routes/health.py`

| Method | Endpoint | Quyền | Mức | Chức năng |
|---|---|---|---|---|
| GET | `/api/v1/health` | Public (giới hạn nội dung) | P0 | `200` nếu API sẵn sàng, `503` nếu không |

Không công khai mật khẩu, kết nối DB, access key, tên bucket nội bộ trong health response.

## 4. Luồng gọi API từ những trang quan trọng

### 4.1. Đăng ký/đăng nhập

1. Tải login/register page; gọi `GET /auth/csrf`.
2. Register → `POST /auth/register`; khi thành công chuyển sang login.
3. Login → `POST /auth/login`; backend đặt cookie phiên.
4. Frontend gọi `GET /auth/csrf` mới, `GET /auth/me`, sau đó mở dashboard.
5. Các trang riêng tư gọi `/auth/me` khi tải trang để biết phiên còn hiệu lực.

### 4.2. Upload và xem file

1. Trang Files gọi `/folders?parent_id=root` và `/files?parent_id=root`.
2. Chọn file và folder → `POST /files` (FormData).
3. Sau `201`, gọi lại danh sách và dashboard summary; không tự giả lập đã lưu.
4. Click Download → `GET /files/{id}/download` với cookie phiên.
5. Nếu nhận `401`, yêu cầu đăng nhập lại; `409 QUOTA_EXCEEDED` thì đề xuất nâng gói.

### 4.3. Nâng cấp qua VNPay Sandbox

1. Trang Plans gọi `GET /plans`.
2. Người dùng chọn gói trả phí → `POST /billing/orders`.
3. Checkout gọi `POST /payments/vnpay/checkout` với `order_id`.
4. Browser chuyển đến URL VNPay do backend trả về.
5. VNPay gửi IPN tới backend; backend kiểm chứng, chuyển đơn sang `paid`, nâng quota **một lần**.
6. Browser trở lại trang kết quả; frontend gọi `GET /billing/orders/{id}` và `GET /billing/subscription` để hiển thị sự thật.

## 5. Quy tắc triển khai `frontend/assets/js/api.js`

Mọi file JS gọi **chung** một client API. Không tự `fetch` phân tán với cơ chế bắt lỗi khác nhau. Ví dụ hợp đồng tối thiểu:

```javascript
// MẪU QUY ƯỚC - chưa phải mã chạy hoàn chỉnh
const API_BASE = "/api/v1";
// api.get(path)
// api.post(path, body)
// api.patch(path, body)
// api.delete(path)
// api.upload(path, formData)
// api.download(path, suggestedFilename)
```

- `api.js` tự thêm `credentials: 'same-origin'` và `X-CSRF-Token` khi cần.
- Với JSON: parse `success/data/error`, throw lỗi dạng `{status, code, message}`.
- Với download: đọc `Blob`/stream, **không** gọi `.json()`.
- Với multipart: để browser tự thêm `Content-Type` kèm boundary; **không** tự gán `application/json`.
- HTML không chứa khóa Garage, mật khẩu DB hoặc khóa VNPay.

## 6. Mapping endpoint với file backend

| File route hiện có | Endpoint nên khai báo |
|---|---|
| `auth.py` | `/auth/csrf`, `/auth/register`, `/auth/login`, `/auth/logout`, `/auth/me` |
| `users.py` | `/users/me`, `/users/me/change-password`, `/dashboard/summary` |
| `files.py` | `/files`, `/files/{id}`, `/files/{id}/download`, phần tệp trong `/trash` |
| `folders.py` | `/folders`, `/folders/{id}`, phần thư mục trong `/trash` |
| `plans.py` | `/plans`, `/plans/{id}` |
| `billing.py` | `/billing/subscription`, `/billing/orders`, `/billing/invoices` |
| `payments.py` | `/payments/vnpay/checkout`, `/payments/vnpay/return`, `/payments/vnpay/ipn` |
| `admin.py` | `/admin/users`, `/admin/plans`, `/admin/metrics` |
| `health.py` | `/health` |

Các module `services/` xử lý nghiệp vụ; route chỉ xác thực, kiểm tra đầu vào, gọi service và trả response. Không đặt logic MySQL/Garage/VNPay lặp lại trong nhiều route.

## 7. Các ca kiểm thử API bắt buộc

- Đăng ký trùng email: `409 EMAIL_ALREADY_EXISTS`.
- Không login mà upload: `401 UNAUTHENTICATED`.
- User B yêu cầu metadata/download file A: `404 RESOURCE_NOT_FOUND` hoặc từ chối an toàn, tuyệt đối không trả nội dung.
- Upload lớn hơn giới hạn: `413 FILE_TOO_LARGE`.
- Upload vượt quota: `409 QUOTA_EXCEEDED`; không có dữ liệu mồ côi.
- Đổi tên trùng trong cùng thư mục: `409 DUPLICATE_NAME`.
- Chuyển folder vào chính nó/nhánh con: `409 INVALID_STATE`.
- Soft delete: quota không giảm; hard delete: quota giảm.
- Client sửa `amount_vnd` hoặc `plan_price`: backend không sử dụng số tiền tự gửi.
- Browser tự giả Return URL thành công: không được nâng gói.
- IPN hợp lệ gửi 2 lần: chỉ kích hoạt quyền lợi 1 lần.
- Cookie hết hạn: `401`, frontend về login.
- User gọi admin endpoint: `403 FORBIDDEN`.
- MySQL/Garage lỗi: `503` (hoặc `500` cho lỗi nội bộ), không lộ thông tin bí mật.

## 8. Danh sách công việc cần làm ngay sau khi hai người đồng ý API

- [ ] Thành viên Backend viết mock/route trả JSON đúng mẫu trước khi kết nối MySQL/Garage.
- [ ] Thành viên Frontend viết `api.js` và thử với API mock.
- [ ] Hai người thống nhất `plan_id`, giá, dung lượng, thời hạn, giới hạn file và thông báo lỗi cuối cùng.
- [ ] Khi thiết kế database, giữ nguyên ý nghĩa API này hoặc chỉnh cả hai tài liệu đồng thời.
- [ ] Chỉ sau đó mới làm migration/bảng MySQL và code lưu trữ thật.

## 9. Tài liệu tham chiếu để triển khai thanh toán

- VNPay Sandbox — hướng dẫn PAY: <https://sandbox.vnpayment.vn/apis/docs/thanh-toan-pay/pay.html>
- VNPay — Return URL và IPN khác nhau: <https://sandbox.vnpayment.vn/apis/docs/faqs/>

**Nhắc lại:** `vnp_ReturnUrl` dùng hiển thị cho khách hàng; IPN server-to-server dùng để cập nhật trạng thái thanh toán. Callback cần xác minh checksum, thông tin đơn, số tiền và xử lý idempotent.
