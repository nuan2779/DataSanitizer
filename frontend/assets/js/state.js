// Lưu trữ dữ liệu tạm thời (State) & Dữ liệu mẫu (Mock Data)
// Trạng thái chung của ứng dụng trên trình duyệt
export const appState = {
    currentFileId: null,
    filename: "",
    columns: [],       // Danh sách cột lấy từ generate_profile()
    pipelineSteps: []  // Danh sách các bước gửi vào execute_pipeline()
};
