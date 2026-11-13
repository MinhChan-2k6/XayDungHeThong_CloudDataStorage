# CloudDS Backend (Flask + MySQL + API)

- Tài liệu cài trên Windows: `../docs/05-local-setup.md`.
- Models theo `../docs/03-database-erd.md`.
- API theo `../docs/04-api-contract.md`.
- Tạo bảng: `flask --app wsgi db upgrade`.
- Nạp gói Free/Basic/VIP: `flask --app wsgi seed-plans`.
- Chạy máy local: `flask --app wsgi run --debug --host 127.0.0.1 --port 5000`.
- Trước khi dùng upload và thanh toán, cấu hình Garage và VNPay Sandbox thật.
- Chưa được kiểm thử tích hợp trên MySQL/Garage/VNPay/EC2 thực.
