// Controller Chính & Điều hướng giao diện
import { appState, saveStateToStorage, clearSavedState } from "./state.js";
import { uploadDatasetAPI, fetchDatasetProfileAPI, executePipelineAPI, downloadExportFileAPI, loadSampleDatasetAPI, benchmarkAIAPI } from "./api.js";
import { renderProfileData, updateStepIndicator } from "./ui-profiler.js";
import { handleStepTypeChange, addStepToPipeline, renderPipelineQueue, renderAuditResult, updateColumnAvailability } from "./ui-pipeline.js";
import { showToast } from "./dom-safe.js";

document.addEventListener("DOMContentLoaded", () => {
    
    // --- 1. KIỂM TRA & KHÔI PHỤC PHIÊN LÀM VIỆC (F5 PERSISTENCE) ---
    try {
        const saved = localStorage.getItem('datasanitizer_state');
        if (saved) {
            const parsed = JSON.parse(saved);
            Object.assign(appState, parsed);
            
            // Nếu có dữ liệu đang làm dở, dựng lại UI
            if (appState.currentFileId && appState.columns.length > 0) {
                document.getElementById("selected-file-name").textContent = `Active Session: ${appState.filename}`;
                document.getElementById("btn-upload").textContent = "Re-initialize";
                document.getElementById("btn-upload").disabled = false;
                
                // Khôi phục giao diện
                renderProfileData({
                    file_id: appState.currentFileId,
                    filename: appState.filename,
                    columns: appState.columns,
                    // Giả lập rows/cols vì không lưu chi tiết trong state.js để nhẹ thẻ
                    total_rows: "?", 
                    total_columns: appState.columns.length
                });
                
                renderPipelineQueue();
                
                // Phục hồi setting mục đích sử dụng
                document.querySelector(`input[name="data-purpose"][value="${appState.purpose}"]`).checked = true;
                document.getElementById("train-split").value = appState.trainSplit;
                document.getElementById("split-display").textContent = `${appState.trainSplit}% / ${100 - appState.trainSplit}%`;
                
                showToast(`Restored previous session: ${appState.filename}`, "success");
            }
        }
    } catch (e) { console.warn("Cannot restore state", e); }

    // --- 2. CHUYỂN ĐỔI CHẾ ĐỘ OFFLINE / ONLINE ---
    const modeToggle = document.getElementById("mode-toggle");
    modeToggle.addEventListener("change", (e) => {
        appState.mode = e.target.checked ? 'online' : 'offline';
        saveStateToStorage();
        
        const offlineBadge = document.getElementById("offline-badge");
        const kaggleHub = document.getElementById("kaggle-hub");
        const btnHistory = document.getElementById("btn-history");
        const btnAuth = document.getElementById("btn-auth");
        const recipeLib = document.getElementById("recipe-library");
        const btnSaveRecipe = document.getElementById("btn-save-recipe");
        
        if (appState.mode === 'online') {
            offlineBadge.classList.add("hidden");
            kaggleHub.classList.remove("hidden");
            btnHistory.classList.remove("hidden");
            if (!appState.user) btnAuth.classList.remove("hidden");
            recipeLib.classList.remove("hidden");
            btnSaveRecipe.classList.remove("hidden");
            showToast("Switched to Cloud Workspace", "success");
        } else {
            offlineBadge.classList.remove("hidden");
            kaggleHub.classList.add("hidden");
            btnHistory.classList.add("hidden");
            btnAuth.classList.add("hidden");
            document.getElementById("profile-badge").classList.add("hidden");
            recipeLib.classList.add("hidden");
            btnSaveRecipe.classList.add("hidden");
            document.getElementById("ml-benchmark").classList.add("hidden");
            showToast("Switched to Local Environment", "success");
        }
    });
    
    // Set trạng thái ban đầu cho công tắc Mode
    modeToggle.checked = (appState.mode === 'online');
    modeToggle.dispatchEvent(new Event('change'));

    // --- 3. ĐIỀU HƯỚNG TƯƠNG TÁC (INTERACTIVE STEPPER & NAV BUTTONS) ---
    function scrollToSection(targetId) {
        document.getElementById(targetId)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        updateStepIndicator(targetId);
    }

    document.querySelectorAll(".step-indicator").forEach(btn => {
        btn.addEventListener("click", () => {
            if (!btn.disabled) scrollToSection(btn.dataset.target);
        });
    });

    document.querySelectorAll(".btn-nav").forEach(btn => {
        btn.addEventListener("click", () => {
            scrollToSection(btn.dataset.target);
        });
    });

    // --- 4. UPLOAD & KAGGLE HUB ---
    const fileInput = document.getElementById("file-input");
    const uploadBtn = document.getElementById("btn-upload");
    const selectedFileName = document.getElementById("selected-file-name");

    fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) {
            selectedFileName.textContent = `Selected: ${fileInput.files[0].name}`;
            uploadBtn.disabled = false;
        }
    });

    uploadBtn.addEventListener("click", async (e) => {
        e.preventDefault();
        if (fileInput.files.length === 0 && !appState.currentFileId) return;

        uploadBtn.disabled = true;
        try {
            let fileId = appState.currentFileId; // Nếu đang restore
            if (fileInput.files.length > 0) {
                clearSavedState(); // Xóa phiên cũ khi nạp file mới
                uploadBtn.textContent = "Uploading...";
                const uploadRes = await uploadDatasetAPI(fileInput.files[0]);
                fileId = uploadRes.file_id;
                appState.filename = uploadRes.filename || fileInput.files[0].name;
            }

            uploadBtn.textContent = "Profiling data...";
            const profileData = await fetchDatasetProfileAPI(fileId);
            
            // Xóa rác Pipeline cũ
            appState.pipelineSteps = [];
            renderPipelineQueue();
            document.getElementById("result-section").classList.add("hidden");

            renderProfileData(profileData);
            updateColumnAvailability();
            
            selectedFileName.textContent = `Initialized: ${appState.filename}`;
            showToast("Dataset loaded and profiled successfully");
            scrollToSection("profile-section");

        } catch (err) {
            showToast(err.message, "error");
        } finally {
            uploadBtn.textContent = "Initialize Dataset";
            uploadBtn.disabled = false;
        }
    });

    // Bấm Nạp dữ liệu mẫu Kaggle 1-Click
    document.querySelectorAll(".btn-sample").forEach(btn => {
        btn.addEventListener("click", async () => {
            const sampleId = btn.dataset.id;
            uploadBtn.textContent = "Loading Kaggle dataset...";
            uploadBtn.disabled = true;
            try {
                clearSavedState();
                const uploadRes = await loadSampleDatasetAPI(sampleId);
                appState.filename = uploadRes.filename;
                
                const profileData = await fetchDatasetProfileAPI(uploadRes.file_id);
                appState.pipelineSteps = [];
                renderPipelineQueue();
                document.getElementById("result-section").classList.add("hidden");
                
                renderProfileData(profileData);
                updateColumnAvailability();
                
                selectedFileName.textContent = `Kaggle Dataset: ${appState.filename}`;
                showToast(`Loaded ${sampleId} dataset`, "success");
                scrollToSection("profile-section");
            } catch (err) {
                showToast(err.message, "error");
            } finally {
                uploadBtn.textContent = "Initialize Dataset";
                uploadBtn.disabled = false;
            }
        });
    });

    // --- 5. LOGIC PIPELINE VÀ ANTI-LEAKAGE ---
    document.getElementById("btn-close-modal").addEventListener("click", () => {
        document.getElementById("column-modal").classList.add("hidden");
    });

    document.getElementById("step-type-select").addEventListener("change", handleStepTypeChange);

    document.getElementById("mv-strategy").addEventListener("change", (e) => {
        const constantGroup = document.getElementById("mv-constant-group");
        if (e.target.value === "constant") {
            constantGroup.classList.remove("hidden");
        } else {
            constantGroup.classList.add("hidden");
        }
        updateColumnAvailability();
    });

    // Chọn tỷ lệ Train/Test & Lưu vào state
    document.querySelectorAll('input[name="data-purpose"]').forEach(radio => {
        radio.addEventListener("change", (e) => {
            appState.purpose = e.target.value;
            const splitConfig = document.getElementById("ml-split-config");
            if (appState.purpose === "ml") {
                splitConfig.classList.remove("hidden");
            } else {
                splitConfig.classList.add("hidden");
            }
            updateColumnAvailability(); // Bật tắt cảnh báo rò rỉ dữ liệu
            saveStateToStorage();
        });
    });

    const splitRange = document.getElementById("train-split");
    splitRange.addEventListener("input", (e) => {
        appState.trainSplit = e.target.value;
        document.getElementById("split-display").textContent = `${appState.trainSplit}% / ${100 - appState.trainSplit}%`;
        saveStateToStorage();
    });

    document.getElementById("btn-select-all-cols").addEventListener("click", () => {
        document.querySelectorAll(".col-checkbox:not(:disabled)").forEach(cb => cb.checked = true);
    });
    
    document.getElementById("btn-clear-all-cols").addEventListener("click", () => {
        document.querySelectorAll(".col-checkbox").forEach(cb => cb.checked = false);
    });

    document.getElementById("btn-add-step").addEventListener("click", addStepToPipeline);
    
    document.getElementById("btn-clear-pipeline").addEventListener("click", () => {
        appState.pipelineSteps = [];
        renderPipelineQueue();
        saveStateToStorage();
    });

    // THỰC THI PIPELINE VÀ CHẤM ĐIỂM
    const executeBtn = document.getElementById("btn-execute-pipeline");
    executeBtn.addEventListener("click", async () => {
        if (appState.pipelineSteps.length === 0) {
            showToast("Add at least one operation to the queue.", "error");
            return;
        }

        executeBtn.textContent = "Processing...";
        executeBtn.disabled = true;

        try {
            const response = await executePipelineAPI(
                appState.currentFileId, 
                appState.pipelineSteps,
                appState.purpose,
                appState.trainSplit
            );
            renderAuditResult(response.audit_summary);
            showToast("Data cleaning pipeline completed", "success");
        } catch (err) {
            showToast(err.message, "error");
        } finally {
            executeBtn.textContent = "Run Pipeline";
            executeBtn.disabled = false;
        }
    });

    // Nút Test AI
    document.getElementById("btn-test-ai").addEventListener("click", async (e) => {
        e.preventDefault();
        const btn = e.target;
        btn.disabled = true;
        btn.textContent = "Running baseline model...";
        
        try {
            const result = await benchmarkAIAPI(appState.currentFileId);
            const fill = document.getElementById("health-score-fill");
            const txt = document.getElementById("health-score-text");
            const score = result.ml_readiness_score || 0;
            
            fill.style.width = `${score}%`;
            txt.textContent = `${score}/100`;
            
            if (score > 80) fill.style.backgroundColor = "var(--success)";
            else if (score > 50) fill.style.backgroundColor = "#eab308";
            else fill.style.backgroundColor = "var(--danger)";
            
        } catch (err) {
            showToast("Benchmark API is not available yet in Backend", "error");
        } finally {
            btn.textContent = "Run Baseline Evaluation";
            btn.disabled = false;
        }
    });

    // --- 6. XUẤT DỮ LIỆU TẢI VỀ ---
    document.getElementById("btn-export-csv").addEventListener("click", () => downloadExportFileAPI(appState.currentFileId, "csv"));
    document.getElementById("btn-export-json").addEventListener("click", () => downloadExportFileAPI(appState.currentFileId, "json"));
    document.getElementById("btn-export-train").addEventListener("click", () => downloadExportFileAPI(appState.currentFileId, "csv", "train_cleaned"));
    document.getElementById("btn-export-test").addEventListener("click", () => downloadExportFileAPI(appState.currentFileId, "csv", "test_cleaned"));
    
    // Đóng Drawer, Auth Modal
    document.getElementById("btn-close-auth").addEventListener("click", () => document.getElementById("auth-modal").classList.add("hidden"));
    document.getElementById("btn-close-history").addEventListener("click", () => document.getElementById("history-drawer").classList.add("hidden"));
    document.getElementById("btn-auth").addEventListener("click", () => document.getElementById("auth-modal").classList.remove("hidden"));
    document.getElementById("btn-history").addEventListener("click", () => document.getElementById("history-drawer").classList.remove("hidden"));
});