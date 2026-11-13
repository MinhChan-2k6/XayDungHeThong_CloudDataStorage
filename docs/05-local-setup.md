# CloudDS — Chạy Flask API với MySQL trên Windows

Phần này triển khai **backend Flask + 9 bảng MySQL theo ERD + API `/api/v1`**. Garage và VNPay Sandbox là các hệ thống ngoài, cần được cấu hình thật trước khi kiểm thử upload/thanh toán.

## 1. Yêu cầu

- Python 3.11 hoặc 3.12, MySQL Server 8.0/8.4, MySQL Workbench; Git nếu nhóm làm chung.
- Chạy lệnh ở **thư mục `backend/`** của CloudDS (VS Code Terminal → PowerShell).
- Không chạy `db.create_all()` từ Flask khi đã dùng migrations. Không tự tạo bảng bằng Workbench.

## 2. Tạo database rỗng và tài khoản ứng dụng trong MySQL Workbench

Đăng nhập vào MySQL Server trong Workbench, mở SQL Editor và chạy bằng tài khoản đủ quyền:

```sql
CREATE DATABASE IF NOT EXISTS cloudds
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'cloudds_app'@'localhost' IDENTIFIED BY 'THAY_MAT_KHAU_MANH';
GRANT ALL PRIVILEGES ON cloudds.* TO 'cloudds_app'@'localhost';
```

Tài khoản `'cloudds_app'@'localhost'` phù hợp khi Flask kết nối MySQL **trên cùng laptop**. Nếu MySQL không khớp tài khoản host này khi kết nối qua TCP `127.0.0.1`, hãy kiểm tra tài khoản/host qua Workbench và điều chỉnh chính xác thay vì mở MySQL ra Internet. Với Docker/2 EC2, cần tạo user cho kết nối từ mạng nội bộ Docker/VPC và hạn chế bằng Security Group.

## 3. Cài thư viện Python

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

Nếu PowerShell chặn `Activate.ps1`, có thể dùng thẳng `.\.venv\Scripts\python.exe` cho các lệnh `python`, `.\.venv\Scripts\flask.exe` cho lệnh `flask`; không cần nới chính sách toàn máy.

## 4. Cấu hình môi trường

```powershell
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
```

Mở `backend/.env`, điền `SECRET_KEY` bằng giá trị random mới tạo và thay `DATABASE_URL` cho đúng MySQL của bạn. URL minh họa:

```dotenv
DATABASE_URL=mysql+pymysql://cloudds_app:THAY_MAT_KHAU_MANH@127.0.0.1:3306/cloudds
COOKIE_SECURE=false
SERVE_FRONTEND=true
```

Nếu mật khẩu có ký tự `@`, `:`, `/`, `%` phải URL-encode trong `DATABASE_URL`. Tuyệt đối không commit `.env`. Khi deploy HTTPS trên EC2, đặt `COOKIE_SECURE=true`; sử dụng kết nối MySQL chỉ qua private network.

## 5. Tạo bảng bằng migrations và cấp 3 gói mặc định

Vẫn đứng trong `backend/` và venv đã kích hoạt:

```powershell
flask --app wsgi db upgrade
flask --app wsgi seed-plans
```

Migrations sẽ tạo các bảng: `users`, `storage_usage`, `folders`, `files`, `plans`, `subscriptions`, `orders`, `payments`, `invoices`, cùng `alembic_version` của hệ thống migrations. Nhấn Refresh trong Workbench để kiểm tra.

Gói mặc định sau lệnh seed: Free 500 MiB (0đ, vĩnh viễn); Basic 2 GiB (10.000đ/30 ngày); VIP 5 GiB (20.000đ/30 ngày). Lệnh seed lặp lại sẽ không ghi đè gói đang có.

Khi đổi models sau này: xem xét thay đổi, chạy `flask --app wsgi db migrate -m "..."` để tạo migration tiếp theo, **đọc lại file migration được sinh ra**, rồi `flask --app wsgi db upgrade`.

## 6. Khởi chạy Flask

```powershell
flask --app wsgi run --debug --host 127.0.0.1 --port 5000
```

- Trang chủ: <http://127.0.0.1:5000/>
- Đăng nhập: <http://127.0.0.1:5000/pages/login.html>
- Kiểm tra API + MySQL: <http://127.0.0.1:5000/api/v1/health>
- Danh sách gói: <http://127.0.0.1:5000/api/v1/plans>

`SERVE_FRONTEND=true` chỉ phục vụ HTML/CSS/JS trực tiếp bằng Flask **trong lúc phát triển**. Khi triển khai EC2, Apache phục vụ frontend và proxy `/api/v1` đến Gunicorn/Flask, không dùng Flask development server ngoài Internet.

## 7. Garage và VNPay Sandbox

**Garage:** backend có `garage_service.py` dùng Boto3/S3. Tạo node/layout, bucket riêng tư, API key có quyền với bucket theo hướng dẫn chính thức <https://garagehq.deuxfleurs.fr/documentation/>; sau đó điền `GARAGE_ENDPOINT`, `GARAGE_REGION`, `GARAGE_BUCKET`, `GARAGE_ACCESS_KEY`, `GARAGE_SECRET_KEY` trong `.env`. Nếu chưa thiết lập Garage, `POST /api/v1/files` sẽ trả `503 SERVICE_UNAVAILABLE`, **không báo upload thành công giả**.

**VNPay:** điền `VNPAY_TMN_CODE`, `VNPAY_HASH_SECRET` từ tài khoản Sandbox và `VNPAY_RETURN_URL` **HTTPS có thể truy cập công khai**; cấu hình IPN URL tới `/api/v1/payments/vnpay/ipn` trên máy chủ chạy thật. Nếu thiếu thông số, tạo checkout trả `503` và **không tạo URL thanh toán giả**. Return URL chỉ để hiển thị; chỉ IPN có chữ ký hợp lệ mới nâng gói.

Cần có mạng HTTPS và backend public để VNPay có thể gọi IPN. Đây không phải là khoản thanh toán tiền thật khi dùng Sandbox.

## 8. Kiểm thử tự động

```powershell
pytest -q
```

Tests sử dụng **SQLite riêng biệt + Garage mock trong bộ test**, để kiểm tra logic và response mà không ảnh hưởng MySQL/Garage thật. Các test không thay thế kiểm thử tích hợp với MySQL 8, Garage thực và VNPay Sandbox. **Không chạy tests trên database thật.**

## 9. Khi lên AWS 2 EC2

- EC2 Database: cài MySQL qua Docker, tạo database `cloudds` rỗng từ môi trường container.
- EC2 Web: Flask dùng `DATABASE_URL` với **private IP của EC2 Database**; chạy cùng `flask --app wsgi db upgrade` và `seed-plans` để sinh bảng/gói.
- Bucket/keys Garage, callback VNPay, Security Group, Apache và Docker Compose sẽ cấu hình ở bước triển khai sau; **không tự động sinh EC2** từ source backend này.
- Volume MySQL/Garage phải được giữ khi restart; bảo mật `.env`, backup và phân quyền đầy đủ trước khi demo.

## 10. Giới hạn cần biết trước khi công bố

- Chưa có kết quả thử trực tiếp trên MySQL/EC2/Garage/VNPay trong môi trường tạo bộ mã; cần thực hiện các bước trên máy thật để nghiệm thu.
- Tính nhất quán MySQL–S3 qua hai dịch vụ không thể bảo đảm bằng một transaction DB: upload có giữ chỗ, thất bại giải phóng quota; lỗi hiếm như mất điện khi upload có thể cần script đối soát thủ công. Xóa vĩnh viễn có thể tiếp tục lại an toàn sau lỗi Garage.
- Chưa tích hợp rate limiting liên máy/đa worker (cần Redis hoặc proxy), email xác minh, reset mật khẩu, audit logs, upload chunk lớn; đây không phải chức năng đã hoàn thành.
- Các endpoint Admin có code nhưng chưa có giao diện quản lý đầy đủ; tài khoản mới tạo qua đăng ký luôn là `user`, không tự có quyền `admin`. Để cấp quyền admin thủ công cho tài khoản đã đăng ký (chỉ người có quyền truy cập máy chủ mới chạy): `flask --app wsgi promote-admin email@example.com`. Không chỉnh role qua API công khai.
