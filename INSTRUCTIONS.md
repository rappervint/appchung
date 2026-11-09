# Refactoring & Coding Standards
1. Zero Logic Loss: Không lược bỏ, đơn giản hóa hay xóa bất kỳ điều kiện biên (if/else, validation, try-catch) nào hiện có.
2. No Placeholders: Không được dùng code tắt dạng "// ... giữ nguyên phần còn lại" hoặc "/* TODO */". Xuất code hoàn chỉnh 100% từ đầu đến cuối.
3. Modular Scope: Tách file theo ES Modules (`import`/`export`). Quản lý state tập trung qua 1 file `state.js`, không tạo biến toàn cục mới.
4. Token Safety: Mỗi module tách ra không quá 200 dòng. Nếu vượt quá, chủ động chia nhỏ tiếp thành sub-module.