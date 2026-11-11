// Quản lý Trạng thái ứng dụng & Khôi phục phiên làm việc (F5)

export const appState = {
    mode: 'offline', // 'offline' hoặc 'online'
    currentFileId: null,
    filename: "",
    columns: [],
    pipelineSteps: [],
    purpose: 'eda', // 'eda' hoặc 'ml'
    trainSplit: 80,
    user: null,
    authToken: null,
    totalRows: 0
};

export function saveStateToStorage() {
    try {
        const stateToSave = {
            mode: appState.mode,
            currentFileId: appState.currentFileId,
            filename: appState.filename,
            columns: appState.columns,
            pipelineSteps: appState.pipelineSteps,
            purpose: appState.purpose,
            trainSplit: appState.trainSplit,
            totalRows: appState.totalRows,
            user: appState.user,
            authToken: appState.authToken // Đã thêm: Lưu lại token để không bị mất khi F5
        };
        localStorage.setItem('datasanitizer_state', JSON.stringify(stateToSave));

        // Đồng bộ ra các key riêng lẻ để bảo đảm an toàn tuyệt đối cho luồng đăng nhập
        if (appState.user) localStorage.setItem("user", appState.user);
        else localStorage.removeItem("user");
        
        if (appState.authToken) localStorage.setItem("authToken", appState.authToken);
        else localStorage.removeItem("authToken");

    } catch (e) {
        console.warn("Lỗi lưu state vào localStorage:", e);
    }
}

export function loadStateFromStorage() {
    try {
        const saved = localStorage.getItem('datasanitizer_state');
        if (saved) {
            const parsed = JSON.parse(saved);
            Object.assign(appState, parsed);
            
            // CHỈ coi là có "Phiên làm việc khôi phục" nếu thực sự ĐANG CÓ FILE
            if (appState.currentFileId) {
                return true;
            }
        }
    } catch (e) {
        console.warn("Lỗi đọc state từ localStorage:", e);
    }
    return false;
}

export function clearSavedState() {
    // KHÔNG XÓA sạch localStorage nữa! 
    // Chỉ reset thông tin liên quan đến file dữ liệu (pipeline, columns, v.v...)
    appState.currentFileId = null;
    appState.filename = "";
    appState.columns = [];
    appState.pipelineSteps = [];
    appState.purpose = 'eda';
    appState.trainSplit = 80;
    appState.totalRows = 0;
    
    // Ghi đè lại State mới (đã xóa file, nhưng TÀI KHOẢN & TOKEN VẪN ĐƯỢC GIỮ LẠI)
    saveStateToStorage();
}