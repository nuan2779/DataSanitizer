// Lưu trữ dữ liệu tạm thời (State) & Dữ liệu mẫu (Mock Data)
// Trạng thái chung của ứng dụng trên trình duyệt
export const appState = {
    currentFileId: null,
    filename: "",
    columns: [],       // Danh sách cột lấy từ generate_profile()
    pipelineSteps: []  // Danh sách các bước gửi vào execute_pipeline()
};

// Dữ liệu mẫu (Mock Data) chuẩn theo cấu trúc profiler.py và cleaner.py để Test UI
export const mockProfileData = {
    file_id: "demo_ds66_001",
    filename: "customer_transactions_raw.csv",
    total_rows: 1500,
    total_columns: 5,
    columns: [
        {
            name: "income",
            dtype: "float64",
            null_count: 180,
            null_percentage: 12.0,
            unique_count: 840,
            sample_values: ["45000.0", "52000.5", "120000.0", "38000.0", "61000.0"],
            statistics: { mean: 54200.5, median: 51000.0,std: 18450.2, min: 12000.0, max: 950000.0, outlier_count: 14 }
        },
        {
            name: "age",
            dtype: "float64",
            null_count: 75,
            null_percentage: 5.0,
            unique_count: 58,
            sample_values: ["22.0", "35.0", "41.0", "29.0", "19.0"],
            statistics: { mean: 33.4, median: 32.0, std: 9.8,min: 18.0, max: 125.0, outlier_count: 3 }
        },
        {
            name: "price_str",
            dtype: "object",
            null_count: 30,
            null_percentage: 2.0,
            unique_count: 320,
            sample_values: ["$19.99", "$45.00", "N/A", "$102.50", "?"]
        },
        {
            name: "membership_tier",
            dtype: "object",
            null_count: 15,
            null_percentage: 1.0,
            unique_count: 4,
            sample_values: ["Gold", "Silver", "Bronze", "Platinum"]
        },
        {
            name: "customer_id",
            dtype: "int64",
            null_count: 0,
            null_percentage: 0.0,
            unique_count: 1500,
            sample_values: ["1001", "1002", "1003", "1004", "1005"],
            statistics: { mean: 1750.5, median: 1750.5, std: 433.1,min: 1001, max: 2500, outlier_count: 0 }
        }
    ]
};

export const mockAuditSummary = {
    initial_rows: 1500,
    final_rows: 1483,
    rows_removed: 17,
    initial_columns: 5,
    final_columns: 5,
    columns_added_or_removed: 0,
    total_steps: 0,
    history: []
};