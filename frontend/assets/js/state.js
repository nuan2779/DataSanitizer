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
    totalRows: 0 // Thêm trường này để fix lỗi hiện "?"
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
            totalRows: appState.totalRows, // Lưu vào localStorage
            user: appState.user
        };
        localStorage.setItem('datasanitizer_state', JSON.stringify(stateToSave));
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
            return true;
        }
    } catch (e) {
        console.warn("Lỗi đọc state từ localStorage:", e);
    }
    return false;
}

export function clearSavedState() {
    localStorage.removeItem('datasanitizer_state');
    appState.currentFileId = null;
    appState.filename = "";
    appState.columns = [];
    appState.pipelineSteps = [];
    appState.purpose = 'eda';
    appState.trainSplit = 80;
    appState.totalRows = 0;
}