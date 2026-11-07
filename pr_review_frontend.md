# 📋 BÁO CÁO REVIEW PR — Nhánh `frontend` (Commit `084a3f3`)

**Người commit:** Hoàng Hải Văn | **Ngày:** 06/11/2026  
**Tiêu đề commit:** *"cập nhật frontend theo system plan mới"*  
**Quy mô thay đổi:** 11 file, +1685 dòng thêm / −595 dòng xóa

---

## BẢNG TỔNG KẾT (SCORECARD)

| # | Yêu cầu theo Plan | Kết quả | Ghi chú |
|:---:|:---|:---:|:---|
| 1 | Hệ 3 Màu Chuẩn (60-30-10) | ✅ Đạt | Đã xóa gradient pastel, áp dụng đúng 3 biến CSS |
| 2 | F5 Không Mất Dữ Liệu (State Persistence) | ⚠️ Thiếu | Thiếu hàm `loadStateFromStorage()`, thiếu banner khôi phục, thiếu nút "Bắt đầu phiên mới" |
| 3 | Stepper Cuộn Mượt (Interactive Stepper) | ⚠️ Thiếu | Hoạt động nhưng dùng text **Tiếng Anh** thay vì **Tiếng Việt** theo plan |
| 4 | Tab Mobile Responsive | ⚠️ Thiếu | Cuộn ngang OK, nhưng thiếu rule `sticky` riêng cho thanh tab trên Mobile |
| 5 | Chuyển đổi Offline / Online | ⚠️ Thiếu | Toggle hoạt động nhưng nhãn sai: ghi "Local Environment" thay vì "🛡️ Chế độ Cục bộ: Bảo mật dữ liệu 100%" |
| 6 | Cảnh Báo Data Leakage | ⚠️ Thiếu | Radio EDA/ML OK, slider Train/Test OK, nhưng cảnh báo chỉ hiện theo ngữ cảnh chứ không phải banner cố định |
| 7 | Modal Đăng Nhập / Đăng Ký (Auth) | ⚠️ Thiếu | HTML modal có rồi nhưng **KHÔNG CÓ event handler JS** → Bấm Submit sẽ bị reload trang |
| 8 | Kho Dữ Liệu Mẫu Kaggle (Kaggle Hub) | ⚠️ Thiếu | 4 thẻ dataset đúng tên nhưng **thiếu icon, mô tả, số dòng/cột** |
| 9 | Pipeline Recipes (Lưu Công Thức) | ⚠️ Thiếu | Nút "Save Recipe" và dropdown Recipe Library có rồi nhưng **KHÔNG CÓ event handler JS** → Bấm không có phản hồi |
| 10 | Drawer Lịch Sử Cá Nhân (History) | ⚠️ Thiếu | Drawer UI trượt đúng nhưng **không có logic lấy dữ liệu** → Luôn hiện "No records" |
| — | File `m.text` | ❌ Lỗi | File ghi chú cá nhân học CSS, **KHÔNG NÊN COMMIT** vào repository |

> **Tổng kết: 1/10 hoàn thành, 9/10 chỉ có khung HTML nhưng thiếu logic JavaScript và sai ngôn ngữ.**

---

## CHI TIẾT CÁC LỖI CẦN SỬA

### 🔴 LỖI NGHIÊM TRỌNG (Bugs — Phải sửa ngay)

#### Bug 1: Auth form không có `e.preventDefault()` và không có event handler
- **File:** `script.js`
- **Vấn đề:** Form `#auth-form` trong modal đăng nhập **không gắn sự kiện `submit`**. Khi người dùng bấm nút đăng nhập, trình duyệt sẽ thực hiện hành vi mặc định: **reload toàn bộ trang web**, mất hết dữ liệu đang làm.
- **Cách sửa:** Thêm event listener:
  ```javascript
  document.getElementById('auth-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    // Gọi API /api/auth/login hoặc /api/auth/register
  });
  ```

#### Bug 2: Nút "Save Recipe" và "Apply Recipe" không hoạt động
- **File:** `script.js`
- **Vấn đề:** Nút `#btn-save-recipe` và `#btn-apply-recipe` tồn tại trong HTML nhưng **không có `addEventListener` nào** được gắn. Bấm vào không có phản hồi gì.
- **Cách sửa:** Thêm event handler gọi API `POST /api/recipes` (save) và `GET /api/recipes/{id}` (apply).

#### Bug 3: Nút "Sign Out" và "Toggle Auth Mode" không hoạt động
- **File:** `script.js`
- **Vấn đề:** Nút `#btn-logout` và `#toggle-auth-mode` (chuyển giữa Đăng nhập / Đăng ký) không gắn event nào.

#### Bug 4: `total_rows` hiện `"?"` khi khôi phục phiên
- **File:** `script.js`
- **Vấn đề:** Khi F5 và khôi phục state từ localStorage, giá trị `total_rows` bị hardcode thành chuỗi `"?"` vì không được lưu vào state. Người dùng sẽ thấy hiển thị rất khó hiểu.
- **Cách sửa:** Lưu `total_rows` và `total_cols` vào `localStorage` cùng với các trường khác.

---

### 🟡 THIẾU SÓT SO VỚI PLAN (Cần bổ sung)

#### Thiếu 1: Banner khôi phục phiên làm việc và nút "Bắt đầu phiên mới"
- **Plan yêu cầu:** Khi F5 và phát hiện state cũ, hiện thanh thông báo: *"Đã khôi phục phiên làm việc trước: [tên file] — [Bắt đầu phiên mới]"*.
- **Thực tế:** Chỉ hiện một toast popup nhỏ rồi biến mất. Không có nút "Bắt đầu phiên mới" để người dùng chọn.

#### Thiếu 2: `loadStateFromStorage()` không tách riêng thành hàm trong `state.js`
- **Plan yêu cầu:** `state.js` phải có 2 hàm rõ ràng: `saveStateToStorage()` và `loadStateFromStorage()`.
- **Thực tế:** Logic load bị viết trực tiếp (inline) trong `script.js` `DOMContentLoaded`, không tách hàm riêng.

#### Thiếu 3: Kaggle Hub — Thiếu icon, mô tả, thông tin dòng/cột
- **Plan yêu cầu:** Mỗi thẻ dataset phải có icon (🏠🚢🌸📊), mô tả bài toán, và số dòng/cột.
- **Thực tế:** Chỉ là 4 nút button thuần text với tên dataset, không có thông tin chi tiết.

#### Thiếu 4: Drawer lịch sử không có logic gọi API
- **Thực tế:** Drawer trượt ra/vào hoạt động đẹp, nhưng danh sách luôn rỗng vì không gọi API `/api/history` để lấy dữ liệu.

---

### 🟠 SAI NGÔN NGỮ (Systematic Language Mismatch)

Toàn bộ giao diện sử dụng **Tiếng Anh**, trong khi plan yêu cầu **Tiếng Việt** ở nhiều vị trí:

| Vị trí | Plan yêu cầu (Tiếng Việt) | Thực tế (Tiếng Anh) |
|:---|:---|:---|
| Nút điều hướng Card | "← Quay lại bước trước" / "Tiếp tục bước sau →" | "Previous" / "Next Step" |
| Badge chế độ Offline | "🛡️ Chế độ Cục bộ: Bảo mật dữ liệu 100%" | "Local Environment" |
| Nút nạp dữ liệu mẫu | "Nạp dữ liệu mẫu này" | *(chỉ là tên dataset)* |
| Nút lịch sử | "Lịch sử xử lý" | "History" |
| Nút lưu công thức | "Lưu thành Recipe" | "Save Recipe" |

---

### ❌ FILE RÁC: `m.text`

File `m.text` (62 dòng) là **ghi chú cá nhân của Văn** giải thích các thuộc tính CSS (`display`, `align-items`, `flex`, `grid`, `padding`...). Đây là tài liệu học tập cá nhân, **KHÔNG PHẢI mã nguồn** và cần:
1. **Xóa khỏi commit.**
2. **Thêm vào `.gitignore`** để không bị commit nhầm lần sau.

---

## ĐÁNH GIÁ CHUNG

Văn đã hoàn thành rất tốt phần **nền tảng cấu trúc HTML và CSS** — tất cả 10 thành phần UI đều đã có khung sườn. Hệ thống 3 màu chuẩn 60-30-10 được áp dụng triệt để và rất đẹp. Tuy nhiên, phần **JavaScript logic (event handlers)** cho các tính năng Online (Auth, Recipes, History) còn thiếu hoàn toàn, và nhãn text bị để tiếng Anh thay vì tiếng Việt theo kế hoạch.

### Ước lượng khối lượng còn lại:
- **Sửa bug nghiêm trọng:** ~1-2 giờ (gắn event handler cho Auth, Recipe, History)
- **Bổ sung thiếu sót:** ~2-3 giờ (banner khôi phục, tách hàm `loadStateFromStorage`, Kaggle Hub metadata)
- **Chỉnh ngôn ngữ Anh → Việt:** ~30 phút
- **Xóa file `m.text`:** ~5 phút
