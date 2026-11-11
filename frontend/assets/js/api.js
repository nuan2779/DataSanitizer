// Base URL động theo origin hiện tại (tương thích tuyệt đối cả 127.0.0.1 và localhost)
const API_HOST = (window.location && window.location.hostname && window.location.hostname !== "") ? window.location.hostname : "127.0.0.1";
const API_PROTOCOL = (window.location && window.location.protocol && window.location.protocol.startsWith("http")) ? window.location.protocol : "http:";
const API_BASE_URL = `${API_PROTOCOL}//${API_HOST}:8000/api`;

// Helper: Tự động đính kèm Authorization Bearer token nếu có trong localStorage
export function getAuthHeaders(extraHeaders = {}) {
    const headers = { ...extraHeaders };
    const token = localStorage.getItem("authToken");
    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }
    return headers;
}

// --- LUỒNG CỐT LÕI (CORE PIPELINE) ---

// 1. Gửi file lên server -> Nhận file_id
export async function uploadDatasetAPI(file) {
    const formData = new FormData();
    formData.append("file", file);
    const response = await fetch(`${API_BASE_URL}/upload`, {
        method: "POST",
        headers: getAuthHeaders(),
        credentials: "include",
        body: formData
    });
    if (!response.ok) throw new Error(await getErrorMsg(response, "Upload failed"));
    return await response.json();
}

// 2. Khám bệnh dữ liệu toàn cục
export async function fetchDatasetProfileAPI(fileId) {
    const response = await fetch(`${API_BASE_URL}/profile/${encodeURIComponent(fileId)}`, {
        headers: getAuthHeaders(),
        credentials: "include"
    });
    if (!response.ok) throw new Error(await getErrorMsg(response, "Profiling failed"));
    return await response.json();
}

// 3. Khám bệnh chuyên sâu 1 cột (Lazy Load)
export async function fetchColumnDetailAPI(fileId, colName) {
    const response = await fetch(`${API_BASE_URL}/profile/${encodeURIComponent(fileId)}/${encodeURIComponent(colName)}`, {
        headers: getAuthHeaders(),
        credentials: "include"
    });
    if (!response.ok) throw new Error(await getErrorMsg(response, `Cannot load details for ${colName}`));
    return await response.json();
}

// 4. Thực thi Pipeline dọn dẹp
export async function executePipelineAPI(fileId, pipeline, purpose, trainSplit) {
    const payload = { file_id: fileId, pipeline: pipeline };
    
    // Đính kèm cấu hình ML nếu chọn chế độ Machine Learning
    if (purpose === "ml") {
        payload.purpose = "ml";
        payload.train_ratio = parseFloat(trainSplit) / 100;
    } else {
        payload.purpose = "eda";
    }

    const response = await fetch(`${API_BASE_URL}/clean`, {
        method: "POST",
        headers: getAuthHeaders({ "Content-Type": "application/json" }),
        credentials: "include",
        body: JSON.stringify(payload)
    });
    if (!response.ok) throw new Error(await getErrorMsg(response, "Pipeline execution failed"));
    return await response.json();
}

// 5. Tải file xuất ra (.csv, .json, train.csv, test.csv)
export function downloadExportFileAPI(fileId, format = "csv", suffix = "") {
    let url = `${API_BASE_URL}/download/${encodeURIComponent(fileId)}?file_format=${format}`;
    if (suffix) url += `&suffix=${suffix}`; // Để tải _train hoặc _test
    window.open(url, "_blank");
}

// --- LUỒNG TÍNH NĂNG MỚI (ENTERPRISE EDITION) ---

// Benchmark Data Hub: Nạp dữ liệu mẫu
export async function loadSampleDatasetAPI(sampleId) {
    const response = await fetch(`${API_BASE_URL}/samples/${encodeURIComponent(sampleId)}/load`, {
        method: "POST",
        headers: getAuthHeaders(),
        credentials: "include"
    });
    if (!response.ok) throw new Error(await getErrorMsg(response, "Failed to load sample dataset"));
    return await response.json();
}

// Lưu Recipe mới
export async function saveRecipeAPI(name, steps) {
    const response = await fetch(`${API_BASE_URL}/recipes`, {
        method: "POST",
        headers: getAuthHeaders({ "Content-Type": "application/json" }),
        credentials: "include",
        body: JSON.stringify({ name: name, steps: steps })
    });
    if (!response.ok) throw new Error(await getErrorMsg(response, "Failed to save recipe"));
    return await response.json();
}

// Chấm điểm ML-Readiness
export async function benchmarkAIAPI(fileId) {
    const response = await fetch(`${API_BASE_URL}/benchmark/${encodeURIComponent(fileId)}`, {
        headers: getAuthHeaders(),
        credentials: "include"
    });
    if (!response.ok) throw new Error(await getErrorMsg(response, "AI Benchmark failed"));
    return await response.json();
}

// --- XÁC THỰC NGƯỜI DÙNG & PHIÊN LÀM VIỆC (AUTH & SESSION) ---

export async function loginAPI(identifier, password) {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ identifier, password })
    });
    if (!response.ok) throw new Error(await getErrorMsg(response, "Đăng nhập thất bại"));
    return await response.json();
}

export async function registerAPI(username, email, password) {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ username, email, password })
    });
    if (!response.ok) throw new Error(await getErrorMsg(response, "Đăng ký thất bại"));
    return await response.json();
}

export async function logoutAPI() {
    const response = await fetch(`${API_BASE_URL}/auth/logout`, {
        method: "POST",
        headers: getAuthHeaders(),
        credentials: "include"
    });
    if (!response.ok) throw new Error(await getErrorMsg(response, "Đăng xuất thất bại"));
    return await response.json();
}

export async function getMeAPI() {
    try {
        const response = await fetch(`${API_BASE_URL}/auth/me`, {
            method: "GET",
            headers: getAuthHeaders(),
            credentials: "include"
        });
        if (!response.ok) return null;
        return await response.json();
    } catch {
        return null;
    }
}

export async function fetchHistoryAPI() {
    const response = await fetch(`${API_BASE_URL}/history`, {
        method: "GET",
        headers: getAuthHeaders(),
        credentials: "include"
    });
    if (!response.ok) return [];
    const data = await response.json();
    return data.history || [];
}

export function downloadHistoryFileAPI(historyId, format = "csv") {
    const url = `${API_BASE_URL}/history/${encodeURIComponent(historyId)}/download?file_format=${format}`;
    window.open(url, "_blank");
}

export async function deleteHistoryItemAPI(historyId) {
    const response = await fetch(`${API_BASE_URL}/history/${encodeURIComponent(historyId)}`, {
        method: "DELETE",
        headers: getAuthHeaders(),
        credentials: "include"
    });
    if (!response.ok) throw new Error(await getErrorMsg(response, "Không thể xóa lịch sử"));
    return await response.json();
}

// Helper: Trích xuất lỗi từ FastAPI Pydantic
async function getErrorMsg(response, fallback) {
    try {
        const errData = await response.json();
        if (typeof errData.detail === 'string') {
            return errData.detail;
        } else if (Array.isArray(errData.detail)) {
            return errData.detail[0].msg || fallback;
        }
        return response.statusText || fallback;
    } catch {
        return `${fallback} (${response.status})`;
    }
}

// --- LUỒNG XÁC THỰC GOOGLE IDENTITY SERVICES ---

// Đăng nhập bằng Google
export async function googleLoginAPI(googleToken) {
    const response = await fetch(`${API_BASE_URL}/auth/google`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ token: googleToken })
    });
    if (!response.ok) throw new Error(await getErrorMsg(response, "Đăng nhập Google thất bại"));
    return await response.json(); 
}
