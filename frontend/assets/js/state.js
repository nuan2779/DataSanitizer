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

export function getStorageKey(user = appState.user) {
    if (user && typeof user === 'string' && user.trim() !== '') {
        return `datasanitizer_state_${user.trim().toLowerCase()}`;
    }
    return 'datasanitizer_state_offline';
}

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
            authToken: appState.authToken
        };
        const key = getStorageKey(appState.user);
        localStorage.setItem(key, JSON.stringify(stateToSave));

        // Xóa sạch key cũ un-scoped tránh rò rỉ phiên chéo tài khoản
        localStorage.removeItem('datasanitizer_state');

        // Đồng bộ ra các key riêng lẻ để bảo đảm an toàn tuyệt đối cho luồng đăng nhập
        if (appState.user) localStorage.setItem("user", appState.user);
        else localStorage.removeItem("user");
        
        if (appState.authToken) localStorage.setItem("authToken", appState.authToken);
        else localStorage.removeItem("authToken");

        if (appState.mode) localStorage.setItem("datasanitizer_mode", appState.mode);

    } catch (e) {
        console.warn("Lỗi lưu state vào localStorage:", e);
    }
}

export function loadStateFromStorage() {
    try {
        // Dọn dẹp key un-scoped cũ
        localStorage.removeItem('datasanitizer_state');

        const activeUser = appState.user || localStorage.getItem("user");
        const key = getStorageKey(activeUser);
        const saved = localStorage.getItem(key);

        if (saved) {
            const parsed = JSON.parse(saved);
            const currentUser = appState.user || parsed.user || activeUser;
            const currentToken = appState.authToken || parsed.authToken || localStorage.getItem("authToken");

            Object.assign(appState, parsed);
            appState.user = currentUser;
            appState.authToken = currentToken;
            
            // CHỈ coi là có "Phiên làm việc khôi phục" nếu thực sự ĐANG CÓ FILE
            if (appState.currentFileId) {
                return true;
            }
        } else {
            // Không có phiên lưu cho user/mode này -> reset thông tin file trong bộ nhớ
            appState.currentFileId = null;
            appState.filename = "";
            appState.columns = [];
            appState.pipelineSteps = [];
            appState.purpose = 'eda';
            appState.trainSplit = 80;
            appState.totalRows = 0;
        }
    } catch (e) {
        console.warn("Lỗi đọc state từ localStorage:", e);
    }
    return false;
}

export function clearSavedState(deleteFromStorage = false) {
    // Reset thông tin liên quan đến file dữ liệu (pipeline, columns, v.v...)
    appState.currentFileId = null;
    appState.filename = "";
    appState.columns = [];
    appState.pipelineSteps = [];
    appState.purpose = 'eda';
    appState.trainSplit = 80;
    appState.totalRows = 0;
    
    const key = getStorageKey(appState.user);
    if (deleteFromStorage) {
        localStorage.removeItem(key);
    } else {
        saveStateToStorage();
    }
    localStorage.removeItem('datasanitizer_state');
}

export function clearAllUserState() {
    clearSavedState(true);
    appState.user = null;
    appState.authToken = null;
    localStorage.removeItem("user");
    localStorage.removeItem("authToken");
    localStorage.removeItem("datasanitizer_state");
}
