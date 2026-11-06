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
    authToken: null
};

// Lưu toàn bộ state hiện tại vào trình duyệt
export function saveStateToStorage() {
    try {
        const stateToSave = {
            mode: appState.mode,
            currentFileId: appState.currentFileId,
            filename: appState.filename,
            columns: appState.columns,
            pipelineSteps: appState.pipelineSteps,
            purpose: appState.purpose,
            trainSplit: appState.trainSplit
        };
        localStorage.setItem('datasanitizer_state', JSON.stringify(stateToSave));
    } catch (e) {
        console.warn("Lỗi lưu state vào localStorage:", e);
    }
}

// Xóa state khi bắt đầu phiên mới
export function clearSavedState() {
    localStorage.removeItem('datasanitizer_state');
    appState.currentFileId = null;
    appState.filename = "";
    appState.columns = [];
    appState.pipelineSteps = [];
    appState.purpose = 'eda';
    appState.trainSplit = 80;
}