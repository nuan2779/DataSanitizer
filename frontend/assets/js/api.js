const API_BASE_URL = "http://localhost:8000/api";

// --- LUỒNG CỐT LÕI (CORE PIPELINE) ---

// 1. Gửi file lên server -> Nhận file_id
export async function uploadDatasetAPI(file) {
    const formData = new FormData();
    formData.append("file", file);
    const response = await fetch(`${API_BASE_URL}/upload`, {
        method: "POST",
        body: formData
    });
    if (!response.ok) throw new Error(await getErrorMsg(response, "Upload failed"));
    return await response.json();
}

// 2. Khám bệnh dữ liệu toàn cục
export async function fetchDatasetProfileAPI(fileId) {
    const response = await fetch(`${API_BASE_URL}/profile/${encodeURIComponent(fileId)}`);
    if (!response.ok) throw new Error(await getErrorMsg(response, "Profiling failed"));
    return await response.json();
}

// 3. Khám bệnh chuyên sâu 1 cột (Lazy Load)
export async function fetchColumnDetailAPI(fileId, colName) {
    const response = await fetch(`${API_BASE_URL}/profile/${encodeURIComponent(fileId)}/${encodeURIComponent(colName)}`);
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
        headers: { "Content-Type": "application/json" },
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

// Kaggle Hub: Nạp dữ liệu mẫu
export async function loadSampleDatasetAPI(sampleId) {
    const response = await fetch(`${API_BASE_URL}/samples/${encodeURIComponent(sampleId)}/load`, {
        method: "POST"
    });
    if (!response.ok) throw new Error(await getErrorMsg(response, "Failed to load sample dataset"));
    return await response.json();
}

// Lưu Recipe mới
export async function saveRecipeAPI(name, steps) {
    const response = await fetch(`${API_BASE_URL}/recipes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name, steps: steps })
    });
    if (!response.ok) throw new Error(await getErrorMsg(response, "Failed to save recipe"));
    return await response.json();
}

// Chấm điểm ML-Readiness
export async function benchmarkAIAPI(fileId) {
    const response = await fetch(`${API_BASE_URL}/benchmark/${encodeURIComponent(fileId)}`);
    if (!response.ok) throw new Error(await getErrorMsg(response, "AI Benchmark failed"));
    return await response.json();
}

// Helper: Trích xuất lỗi từ FastAPI Pydantic
// Helper: Trích xuất lỗi từ FastAPI Pydantic
async function getErrorMsg(response, fallback) {
    try {
        const errData = await response.json();
        // Kiểm tra xem errData.detail có phải là chuỗi không
        if (typeof errData.detail === 'string') {
            return errData.detail;
        } 
        // Nếu errData.detail là một mảng (thường xảy ra với lỗi validation của FastAPI)
        else if (Array.isArray(errData.detail)) {
            // Lấy thông báo lỗi đầu tiên trong mảng
            return errData.detail[0].msg || fallback;
        }
        return response.statusText || fallback;
    } catch {
        return `${fallback} (${response.status})`;
    }
}

// --- LUỒNG XÁC THỰC (AUTHENTICATION) ---

// Đăng ký tài khoản
export async function registerAPI(username, password) {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // ĐỔI 'username' THÀNH 'identifier'
        body: JSON.stringify({ identifier: username, password: password }) 
    });
    if (!response.ok) throw new Error(await getErrorMsg(response, "Đăng ký thất bại"));
    return await response.json();
}

// Đăng nhập lấy Token
export async function loginAPI(username, password) {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // ĐỔI 'username' THÀNH 'identifier'
        body: JSON.stringify({ identifier: username, password: password })
    });
    if (!response.ok) throw new Error(await getErrorMsg(response, "Sai tên đăng nhập hoặc mật khẩu"));
    return await response.json(); 
}

// Đăng nhập bằng Google
export async function googleLoginAPI(googleToken) {
    const response = await fetch(`${API_BASE_URL}/auth/google`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // Gửi token nhận được từ Google sang cho Backend xác minh
        body: JSON.stringify({ token: googleToken })
    });
    if (!response.ok) throw new Error(await getErrorMsg(response, "Đăng nhập Google thất bại"));
    return await response.json(); 
}

// Đăng xuất
export async function logoutAPI(token) {
    const response = await fetch(`${API_BASE_URL}/auth/logout`, {
        method: "POST",
        headers: { 
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}` 
        }
    });
    if (!response.ok) throw new Error("Lỗi khi đăng xuất");
    return true;
}