# CLOUDDS — ĐẶC TẢ CHỨC NĂNG & QUY TẮC NGHIỆP VỤ

**Đề tài:** 15 — Xây dựng hệ thống Cloud Data Storage  
**Mục đích tài liệu:** Thống nhất phạm vi công việc giữa 2 thành viên trước khi lập trình  
**Trạng thái:** Bản thiết kế nhóm đề xuất (v1.0), **không phải nguyên văn yêu cầu giảng viên**  
**Nguồn bối cảnh:** Yêu cầu đề tài do giảng viên giao và cấu trúc dự án `XayDungHeThong_CloudDataStorage.rar`.

## 0. Phân biệt yêu cầu thầy và giải pháp nhóm tự chọn

**Thầy đã nêu:** Đề tài Cloud Data Storage; sinh viên tự chọn phần mềm; có frontend, backend, đăng ký, billing, thanh toán; nhóm 2–3 người; nộp slide + source (nếu có) / hướng dẫn cấu hình, không cần báo cáo riêng.

**Nhóm đề xuất:** CloudDS tự phát triển bằng HTML/CSS/JavaScript + Bootstrap 5; Flask + Gunicorn; MySQL + SQLAlchemy; Garage Object Storage qua Boto3; Apache; Docker Compose; VNPay Sandbox; demo triển khai AWS EC2. Những lựa chọn này có thể được điều chỉnh nếu có ràng buộc chi phí hoặc yêu cầu mới của thầy.

**Không làm ở giai đoạn thiết kế này:** chưa vẽ sơ đồ kiến trúc, chưa thiết kế bảng/khóa MySQL, chưa code chức năng.

## 1. Mục tiêu sản phẩm

CloudDS là ứng dụng web cung cấp không gian lưu trữ riêng cho nhiều tài khoản qua Internet. Người dùng đăng ký, đăng nhập, tạo thư mục, tải tệp lên/xuống, quản lý dung lượng, chọn gói lưu trữ và thanh toán thử nghiệm. Nội dung tệp được cất ở Garage; dữ liệu quản lý được lưu tại MySQL; Flask kiểm tra quyền và điều phối thao tác.

**Luồng demo phải chạy được:** Đăng ký → Đăng nhập → Upload → Xem danh sách → Download → Xem quota → Chọn gói → Tạo đơn hàng → Thanh toán sandbox → Gói/quota cập nhật.

## 2. Đối tượng sử dụng và quyền

| Vai trò | Có thể làm | Không được làm |
|---|---|---|
| Khách (Guest) | Xem trang chủ, thông tin các gói, đăng ký, đăng nhập | Xem tệp của user, upload/download, thanh toán, xem dữ liệu quản trị |
| Người dùng (User) | Toàn bộ thao tác đối với tệp/thư mục **thuộc tài khoản mình**; xem/chọn gói, đơn hàng, giao dịch, cập nhật hồ sơ | Truy cập dữ liệu tài khoản khác, tự tăng quota, tự đánh dấu đã thanh toán, dùng chức năng admin |
| Quản trị viên (Admin) | Quản lý người dùng/gói và thống kê cơ bản theo phạm vi được cấp | Xem nội dung tệp riêng tư của người dùng chỉ vì có quyền admin; đổi trạng thái thanh toán không có căn cứ |
| VNPay Sandbox (hệ thống ngoài) | Chuyển người dùng đến bước thanh toán và gọi callback xác nhận giao dịch | Truy cập dữ liệu người dùng hoặc quản trị CloudDS |

**Chính sách dữ liệu:** chỉ người sở hữu truy cập tệp. Chưa có chức năng chia sẻ tệp công khai hoặc cộng tác ở phiên bản đầu tiên.

## 3. Phạm vi chức năng và độ ưu tiên

- **P0 — Bắt buộc cho bản demo của nhóm:** Không có thì chưa xem là CloudDS hoàn chỉnh.
- **P1 — Nên hoàn thành:** Phục vụ trải nghiệm quản lý tệp và vận hành cơ bản.
- **P2 — Sau khi P0/P1 ổn định:** Tính năng mở rộng, không gây trễ đồ án.

### 3.1. Tài khoản, xác thực và hồ sơ

| Mã | Chức năng | Mức | Tiêu chí hoàn thành |
|---|---|---|---|
| AUTH-01 | Đăng ký bằng họ tên, email, mật khẩu | P0 | Kiểm tra dữ liệu; từ chối email đã tồn tại; tạo tài khoản mặc định gói Free |
| AUTH-02 | Đăng nhập bằng email/mật khẩu | P0 | Xác thực thành công mới tạo phiên đăng nhập; báo lỗi an toàn nếu sai |
| AUTH-03 | Đăng xuất | P0 | Kết thúc phiên; endpoint cần đăng nhập không còn sử dụng được |
| AUTH-04 | Giữ trạng thái đăng nhập qua tải lại trang | P0 | Giao diện xác định đúng tài khoản hiện tại từ API, không dựa vào localStorage giả lập |
| AUTH-05 | Xem và sửa tên hiển thị | P1 | User chỉ sửa hồ sơ của mình; không tự thay đổi role/quota |
| AUTH-06 | Đổi mật khẩu khi biết mật khẩu hiện tại | P1 | Kiểm tra mật khẩu cũ, lưu hash mật khẩu mới, không trả mật khẩu qua API |
| AUTH-07 | Khóa tài khoản (admin) | P1 | Người bị khóa không thực hiện được yêu cầu đã xác thực |
| AUTH-08 | Quên mật khẩu qua email, MFA | P2 | Chỉ làm nếu nhóm bổ sung được email/hạ tầng xác minh |

### 3.2. Quản lý tệp và thư mục

| Mã | Chức năng | Mức | Tiêu chí hoàn thành |
|---|---|---|---|
| FILE-01 | Upload một tệp | P0 | Lưu byte thật ở Garage; lưu metadata; từ chối nếu quá quota hoặc vượt giới hạn kích thước |
| FILE-02 | Liệt kê tệp trong thư mục | P0 | Chỉ trả tệp user sở hữu; hiện tên, dung lượng, loại, thời gian |
| FILE-03 | Download tệp | P0 | Trả đúng nội dung tệp đã upload; không download được tệp của user khác |
| FILE-04 | Xem thông tin tệp | P0 | Metadata có ID, tên, MIME type, size, đường dẫn cha, thời gian |
| FILE-05 | Tạo và duyệt thư mục | P0 | Thư mục lồng nhau; điều hướng root → thư mục con |
| FILE-06 | Đổi tên tệp/thư mục | P1 | Kiểm tra trùng tên trong cùng thư mục, không đổi tên object gốc công khai |
| FILE-07 | Chuyển tệp/thư mục sang thư mục khác | P1 | Không thể chuyển thư mục vào chính nó hoặc thư mục con của nó |
| FILE-08 | Xóa mềm tệp/thư mục | P1 | Chuyển vào thùng rác, không mất ngay nội dung Garage |
| FILE-09 | Xem thùng rác, khôi phục, xóa vĩnh viễn | P1 | Khôi phục quyền và metadata chính xác; xóa vĩnh viễn mới thu hồi dữ liệu |
| FILE-10 | Tìm kiếm theo tên | P1 | Chỉ tìm trong dữ liệu thuộc user và chưa xóa |
| FILE-11 | Xem trước nội dung phổ biến (ảnh/PDF) | P2 | Có kiểm tra quyền, không mở public bucket |
| FILE-12 | Chia sẻ bằng link, lịch sử phiên bản, upload nhiều tệp | P2 | Chỉ triển khai nếu hoàn thành cốt lõi |

### 3.3. Dung lượng và gói lưu trữ

| Mã | Chức năng | Mức | Tiêu chí hoàn thành |
|---|---|---|---|
| QUOTA-01 | Hiển thị dung lượng đang dùng/tối đa | P0 | Số liệu byte thực tế, xuất hiện ở Dashboard |
| QUOTA-02 | Chặn upload vượt quota | P0 | Kiểm tra ở backend; frontend hiển thị lỗi có mã rõ ràng |
| QUOTA-03 | Cấp gói Free khi đăng ký | P0 | Không cần thanh toán, có quota xác định bằng cấu hình/gói |
| PLAN-01 | Hiển thị các gói Free, Basic, Pro | P0 | Tên, dung lượng, giá VND, thời hạn (nếu là gói trả phí) |
| PLAN-02 | Gói đang sử dụng và ngày hết hạn | P0 | API chỉ trả trạng thái thực tế từ backend |
| PLAN-03 | Sau mua thành công, cập nhật quota | P0 | Chỉ sau xác thực thanh toán hợp lệ |
| PLAN-04 | Xử lý hết hạn gói | P1 | Theo quy tắc ở mục 4, không tự ý xóa file |
| PLAN-05 | Admin thay đổi/tắt gói đối với lượt mua mới | P1 | Không phá quyền lợi của gói đang sử dụng |

### 3.4. Billing và thanh toán

| Mã | Chức năng | Mức | Tiêu chí hoàn thành |
|---|---|---|---|
| BILL-01 | Tạo đơn hàng theo gói được chọn | P0 | Backend tự lấy giá từ gói; client không gửi số tiền quyết định |
| BILL-02 | Xem đơn hàng và trạng thái | P0 | `pending`, `paid`, `failed`, `cancelled`, `expired` |
| PAY-01 | Khởi tạo URL VNPay Sandbox | P0 | Backend tạo URL có chữ ký từ thông tin đơn hàng |
| PAY-02 | Nhận Return URL để hiện kết quả | P0 | Chỉ dùng để hiển thị; không mặc định kết luận đã thanh toán |
| PAY-03 | Xác minh IPN/callback VNPay và cập nhật đơn | P0 | Kiểm tra chữ ký, số tiền, đơn hàng, trạng thái; xử lý lặp an toàn |
| BILL-03 | Lịch sử thanh toán và biên nhận nội bộ | P0 | Người dùng chỉ thấy dữ liệu của mình; phân biệt biên nhận demo với hóa đơn thuế |
| BILL-04 | Gia hạn, hạ gói, hoàn tiền tự động | P2 | Chưa đưa vào bản đầu nếu không có yêu cầu bổ sung |

### 3.5. Trang quản trị và vận hành

| Mã | Chức năng | Mức | Tiêu chí hoàn thành |
|---|---|---|---|
| ADM-01 | Danh sách người dùng và trạng thái | P1 | Chỉ admin xem, phân trang |
| ADM-02 | Khóa/mở tài khoản | P1 | Không lộ thông tin mật khẩu |
| ADM-03 | Xem, tạo, chỉnh sửa, bật/tắt gói | P1 | Không cho user thường gọi API admin |
| ADM-04 | Thống kê số user, file, tổng dung lượng | P1 | Thống kê từ dữ liệu thực |
| OPS-01 | API health check | P0 | Cho biết ứng dụng sẵn sàng, không lộ mật khẩu/cấu hình |
| OPS-02 | Tệp cấu hình Docker Compose & hướng dẫn chạy | P0 | Có mode local một máy và mode Web + Database hai EC2 |
| OPS-03 | Volume dữ liệu MySQL/Garage và cách backup | P0 | Restart/recreate container không làm mất dữ liệu vì không xóa volumes |
| OPS-04 | HTTPS, private network cho DB, bí mật trong `.env` | P0 | Không public cổng MySQL/Garage management; không commit secret |

## 4. Quy tắc nghiệp vụ phải chốt trước khi code

1. **Một tài khoản — một vùng dữ liệu riêng.** Mọi truy vấn metadata và object phải kiểm tra quyền sở hữu tại backend. Không tin `user_id` do trình duyệt gửi.
2. **Mặc định là Free.** Mức 5 GB Free / 20 GB Basic / 100 GB Pro chỉ là ví dụ; **nhóm chưa chốt giá và dung lượng cụ thể**. Thiết kế lưu quota bằng **bytes**, giá bằng **số nguyên VND**.
3. **Cùng thư mục không có 2 mục trùng tên cùng loại.** Chấp nhận tên tương tự ở các thư mục khác; quy tắc trùng tên sẽ được backend thực thi nhất quán.
4. **Garage lưu byte; MySQL lưu metadata.** Nội dung tệp không được lưu blob trực tiếp trong MySQL. Garage object key dùng ID tạo ngẫu nhiên thay vì lấy nguyên tên tệp.
5. **Upload có kiểm soát.** Backend xác thực, kiểm tra định dạng tên, kích thước request, dung lượng còn lại và tránh lỗi upload đồng thời vượt quota. Nếu lưu tệp thành công nhưng tạo metadata thất bại thì cần cơ chế dọn object mồ côi, và ngược lại.
6. **Quota đang dùng** tính trên các object chưa xóa vĩnh viễn, bao gồm tệp trong thùng rác (vì vẫn chiếm dung lượng). Xóa mềm **không** giải phóng quota; xóa vĩnh viễn mới giải phóng quota.
7. **Thư mục là cấu trúc logic trong database.** Không cần tạo thư mục vật lý trên Garage; mỗi file trỏ tới ID thư mục cha.
8. **Thùng rác:** xóa thư mục đưa cả cây con vào trạng thái đã xóa; khôi phục thư mục kéo theo cây con. Nếu khôi phục tệp mà thư mục cha không tồn tại, đưa về root hoặc từ chối với hướng dẫn chọn thư mục đích (API sẽ chốt hành vi: mặc định root).
9. **Tệp không công khai.** Không dùng bucket policy `public-read` cho tệp cá nhân. Download đi qua backend có kiểm tra quyền; có thể tối ưu bằng presigned URL sau.
10. **Thời gian** được lưu/trả về dưới dạng ISO 8601 theo UTC (có `Z`); frontend hiển thị giờ Việt Nam. Mọi ID là chuỗi UUID, không dùng số tăng dần trong hợp đồng API.
11. **Thanh toán:** Giá do backend quyết định; gói chỉ kích hoạt khi giao dịch hợp lệ được xác minh qua callback IPN. Return URL không đủ để tin đã thanh toán; IPN trùng không được cộng quota/gia hạn hai lần.
12. **Hết hạn gói:** nếu gói trả phí hết hạn và không gia hạn, quay về Free; **không tự xóa file**. Nếu đã sử dụng vượt quota Free, vẫn có thể xem/tải/xóa, nhưng không được upload thêm cho đến khi giảm dung lượng hoặc nâng gói.
13. **Đăng ký Free** là thao tác nội bộ, không tạo đơn hàng thanh toán.
14. **Bảo mật:** mật khẩu được hash an toàn; cookie phiên HttpOnly; cookie Secure khi chạy HTTPS; kiểm soát CSRF, giới hạn số lần đăng nhập, kiểm tra đầu vào; admin có phân quyền riêng.
15. **Bản chạy demo:** một Compose tổng hợp trên máy giảng viên; hoặc hai Compose riêng trên EC2 Web và EC2 Database. Việc tạo VPC/EC2/SG và cài Docker lần đầu được hướng dẫn thủ công, không tự động bởi Compose.

## 5. Trang giao diện và trách nhiệm

| File hiện có trong dự án | Nội dung chính | API sử dụng |
|---|---|---|
| `frontend/index.html` | Trang giới thiệu dịch vụ | `GET /plans` |
| `frontend/pages/register.html` | Form tạo tài khoản | `POST /auth/register` |
| `frontend/pages/login.html` | Form đăng nhập | `POST /auth/login` |
| `frontend/pages/dashboard.html` | Tổng quan, quota, gói hiện tại | `GET /dashboard/summary` |
| `frontend/pages/files.html` | Danh sách, upload, download, tạo thư mục, đổi tên | `/files`, `/folders` |
| `frontend/pages/trash.html` | Thùng rác, khôi phục, xóa hẳn | `/trash` |
| `frontend/pages/plans.html` | So sánh gói | `GET /plans` |
| `frontend/pages/checkout.html` | Tạo đơn, đi tới sandbox | `POST /billing/orders`, `/payments/vnpay/checkout` |
| `frontend/pages/payment-result.html` | Xem trạng thái giao dịch sau redirect | `GET /billing/orders/{id}` |
| `frontend/pages/billing.html` | Gói, đơn hàng, thanh toán, biên nhận | `/billing/*` |
| `frontend/pages/profile.html` | Hồ sơ và đổi mật khẩu | `GET /auth/me`, `/users/me` |
| `frontend/pages/admin.html` | Quản trị viên | `/admin/*` (P1) |

**Đề xuất bổ sung nhẹ (không bắt buộc làm ngay):** `frontend/assets/js/trash.js`, `admin.js`, `payment-result.js` để JS khớp 3 trang còn thiếu file JS riêng. Repo hiện tại chưa có ba file này.

## 6. Kiểm thử nghiệm thu cơ bản

| Test | Kết quả mong đợi |
|---|---|
| Đăng ký 2 email khác nhau | Tạo 2 tài khoản Free riêng |
| Đăng ký email trùng | Trả lỗi trùng email; không tạo dữ liệu rác |
| Đăng nhập sai mật khẩu | Không tạo phiên đăng nhập |
| User A upload `baitap.pdf` rồi download | Nội dung byte đúng nguyên bản |
| User B gọi API với `file_id` của A | Bị chặn, không đọc được metadata/nội dung |
| Upload vượt hạn mức | Lỗi quota; không tạo file/orphan object |
| Xóa mềm file | Hiện trong Trash, quota chưa giảm |
| Khôi phục file | Trở lại Files, nội dung còn nguyên |
| Xóa vĩnh viễn | Không còn thấy file, quota giảm theo byte thực |
| Thanh toán sandbox hợp lệ | Order paid, gói cập nhật đúng **một lần** |
| Gọi lại IPN giống giao dịch cũ | Không cộng thêm quyền lợi |
| Quay về Return URL giả | Không tự ý nâng gói |
| Restart/recreate container không xóa volumes | MySQL và Garage giữ dữ liệu |
| API admin khi đăng nhập user | Bị từ chối |

**Những điều 2 thành viên phải xác nhận trước khi code billing:** 
mức dung lượng và giá 3 gói
CHỐT: 3 GÓI: 
 FREE 500MB (FREE) 
 BASIC 2GB 10.000Đ
 VIP 5GB 20.000Đ

;
thời hạn gói trả phí
3 GÓI: 
 FREE VĨNH VIÊN
 BASIC 10.000Đ/THÁNG
 VIP 20.000Đ/THÁNG

;
Thông số	Đề xuất
Kích thước tối đa mỗi tệp	100 MB
Loại tệp	Hỗ trợ phần lớn định dạng thông dụng
Khi vượt giới hạn	Từ chối upload và thông báo rõ lý do

;
Chức năng quản trị hệ thống sẽ được phát triển sau khi hoàn thiện các chức năng chính.
