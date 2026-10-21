const API_BASE_URL = "http://localhost:8000/api";

// LUỒNG 1 - BƯỚC A: Gửi file lên server (POST /api/upload) -> Nhận về file_id
export async function uploadDatasetAPI(file) {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${API_BASE_URL}/upload`, {
        method: "POST",
        body: formData
    });

    if (!response.ok) {
        throw new Error(`Lỗi tải file lên server (${response.status}):${response.statusText}`);
    }
    return await response.json(); // Trả về object chứa { file_id: "..." }
}

// LUỒNG 1 - BƯỚC B: Tự động khám bệnh dữ liệu (GET /api/profile/{file_id})
export async function fetchDatasetProfileAPI(fileId) {
    const response = await fetch(`${API_BASE_URL}/profile/${encodeURIComponent(fileId)}`, {
        method: "GET"
    });

    if (!response.ok) {
        throw new Error(`Lỗi khi phân tích dữ liệu (${response.status}):${response.statusText}`);
    }
    return await response.json(); // Trả về kết quả của generate_profile()
}

// LUỒNG 2: Xem chi tiết chuyên sâu 1 cột - Lazy Loading (GET /api/profile/{file_id}/{col_name})
export async function fetchColumnDetailAPI(fileId, colName) {
    const response = await fetch(
        `${API_BASE_URL}/profile/${encodeURIComponent(fileId)}/${encodeURIComponent(colName)}`,
        { method: "GET" }
    );

    if (!response.ok) {
        throw new Error(`Không thể tải chi tiết cột '${colName}' (${response.status})`);
    }
    return await response.json(); // Trả về kết quả của profile_single_column()
}

// LUỒNG 3: Thực thi Pipeline dọn dẹp (POST /api/clean)
export async function executePipelineAPI(fileId, pipeline) {
    const response = await fetch(`${API_BASE_URL}/clean`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            file_id: fileId,
            pipeline: pipeline // Khớp chính xác với key "pipeline" của Backend
        })
    });

    if (!response.ok) {
        throw new Error(`Lỗi khi chạy Pipeline (${response.status}):${response.statusText}`);
    }
    return await response.json();
}

// Xuất dữ liệu sạch (.csv hoặc .json)
export function downloadExportFileAPI(fileId, format = "csv") {
    const downloadUrl = `${API_BASE_URL}/download/${encodeURIComponent(fileId)}?format=${format}`;
    window.open(downloadUrl, "_blank");
}