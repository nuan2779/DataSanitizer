import { appState, saveStateToStorage, clearSavedState, loadStateFromStorage } from "./state.js";
import { uploadDatasetAPI, fetchDatasetProfileAPI, executePipelineAPI, downloadExportFileAPI, loadSampleDatasetAPI, benchmarkAIAPI, saveRecipeAPI } from "./api.js";
import { renderProfileData, updateStepIndicator } from "./ui-profiler.js";
import { handleStepTypeChange, addStepToPipeline, renderPipelineQueue, renderAuditResult, updateColumnAvailability } from "./ui-pipeline.js";
import { showToast } from "./dom-safe.js";

document.addEventListener("DOMContentLoaded", () => {
    
    // --- 1. KIỂM TRA & KHÔI PHỤC PHIÊN LÀM VIỆC (F5 PERSISTENCE) ---
    const restored = loadStateFromStorage();
    if (restored) {
        document.getElementById("selected-file-name").textContent = `Active Session: ${appState.filename}`;
        document.getElementById("btn-upload").textContent = "Tiếp tục phân tích";
        document.getElementById("btn-upload").disabled = false;
        
        // Hiện banner khôi phục thay vì toast
        const sessionBanner = document.createElement("div");
        sessionBanner.className = "alert alert-warning";
        sessionBanner.style.display = "flex";
        sessionBanner.style.justifyContent = "space-between";
        sessionBanner.style.alignItems = "center";
        sessionBanner.innerHTML = `
            <span>Đã khôi phục phiên làm việc: <strong>${appState.filename}</strong></span>
            <button id="btn-new-session" class="btn btn-outline" style="padding: 4px 10px; font-size: 12px;">Bắt đầu phiên mới</button>
        `;
        document.getElementById("upload-section").querySelector(".card-body").prepend(sessionBanner);
        
        document.getElementById("btn-new-session").addEventListener("click", () => {
            clearSavedState();
            location.reload();
        });

        // Khôi phục giao diện
        renderProfileData({
            file_id: appState.currentFileId,
            filename: appState.filename,
            columns: appState.columns,
            total_rows: appState.totalRows || "?", // Lấy từ state
            total_columns: appState.columns.length
        });
        
        renderPipelineQueue();
        
        const purposeRadio = document.querySelector(`input[name="data-purpose"][value="${appState.purpose}"]`);
        if (purposeRadio) purposeRadio.checked = true;
        
        document.getElementById("train-split").value = appState.trainSplit;
        document.getElementById("split-display").textContent = `Train: ${appState.trainSplit}% | Test: ${100 - appState.trainSplit}%`;
        
        // Mở khóa Bước 3 nếu có column
        document.getElementById("pipeline-section").classList.remove("hidden");
    }

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
            showToast("Đã chuyển sang Cloud Workspace", "success");
        } else {
            offlineBadge.classList.remove("hidden");
            kaggleHub.classList.add("hidden");
            btnHistory.classList.add("hidden");
            btnAuth.classList.add("hidden");
            document.getElementById("profile-badge").classList.add("hidden");
            recipeLib.classList.add("hidden");
            btnSaveRecipe.classList.add("hidden");
            document.getElementById("ml-benchmark").classList.add("hidden");
            showToast("Đã chuyển sang Chế độ Cục bộ", "success");
        }
    });
    modeToggle.checked = (appState.mode === 'online');
    modeToggle.dispatchEvent(new Event('change'));

    // --- 3. ĐIỀU HƯỚNG TƯƠNG TÁC ---
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
        btn.addEventListener("click", () => scrollToSection(btn.dataset.target));
    });

    // --- 4. UPLOAD & BENCHMARK DATA HUB ---
    const fileInput = document.getElementById("file-input");
    const uploadBtn = document.getElementById("btn-upload");
    const selectedFileName = document.getElementById("selected-file-name");

    fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) {
            selectedFileName.textContent = `Đã chọn: ${fileInput.files[0].name}`;
            uploadBtn.disabled = false;
        }
    });

    uploadBtn.addEventListener("click", async (e) => {
        e.preventDefault();
        if (fileInput.files.length === 0 && !appState.currentFileId) return;

        uploadBtn.disabled = true;
        try {
            let fileId = appState.currentFileId;
            if (fileInput.files.length > 0) {
                clearSavedState();
                uploadBtn.textContent = "Đang tải file lên...";
                const uploadRes = await uploadDatasetAPI(fileInput.files[0]);
                fileId = uploadRes.file_id;
                appState.filename = uploadRes.filename || fileInput.files[0].name;
            }

            uploadBtn.textContent = "Đang khám bệnh dữ liệu...";
            const profileData = await fetchDatasetProfileAPI(fileId);
            
            appState.pipelineSteps = [];
            renderPipelineQueue();
            document.getElementById("result-section").classList.add("hidden");
            
            appState.totalRows = profileData.total_rows; // Lưu total rows
            renderProfileData(profileData);
            updateColumnAvailability();
            
            selectedFileName.textContent = `Hoàn tất: ${appState.filename}`;
            showToast("Tải và phân tích dữ liệu thành công");
            scrollToSection("profile-section");
        } catch (err) {
            showToast(err.message, "error");
        } finally {
            uploadBtn.textContent = "Bắt đầu phân tích dữ liệu";
            uploadBtn.disabled = false;
        }
    });

    async function handleLoadSample(sampleId, triggerElement) {
        uploadBtn.textContent = "Đang nạp dữ liệu mẫu...";
        uploadBtn.disabled = true;
        if (triggerElement) {
            triggerElement.style.opacity = "0.7";
            triggerElement.style.pointerEvents = "none";
        }

        try {
            clearSavedState();
            const uploadRes = await loadSampleDatasetAPI(sampleId);
            appState.filename = uploadRes.filename;
            
            const profileData = await fetchDatasetProfileAPI(uploadRes.file_id);
            appState.totalRows = profileData.total_rows;
            appState.pipelineSteps = [];
            renderPipelineQueue();
            document.getElementById("result-section").classList.add("hidden");
            
            renderProfileData(profileData);
            updateColumnAvailability();
            
            selectedFileName.textContent = `Dữ liệu mẫu: ${appState.filename}`;
            showToast(`Đã nạp thành công bộ dữ liệu mẫu [${sampleId}]`, "success");
            scrollToSection("profile-section");
        } catch (err) {
            showToast(err.message, "error");
        } finally {
            uploadBtn.textContent = "Bắt đầu phân tích dữ liệu";
            uploadBtn.disabled = false;
            if (triggerElement) {
                triggerElement.style.opacity = "1";
                triggerElement.style.pointerEvents = "auto";
            }
        }
    }

    document.querySelectorAll(".kaggle-card").forEach(card => {
        card.addEventListener("click", (e) => {
            const sampleId = card.dataset.id;
            if (sampleId) handleLoadSample(sampleId, card);
        });
    });

    document.querySelectorAll(".btn-sample").forEach(btn => {
        btn.addEventListener("click", (e) => {
            e.stopPropagation(); // Ngăn double-click từ thẻ cha kaggle-card
            const sampleId = btn.dataset.id;
            if (sampleId) handleLoadSample(sampleId, btn);
        });
    });

    // --- 5. LOGIC PIPELINE & RECIPE ---
    document.getElementById("btn-close-modal").addEventListener("click", () => document.getElementById("column-modal").classList.add("hidden"));
    document.getElementById("step-type-select").addEventListener("change", handleStepTypeChange);
    
    document.getElementById("mv-strategy").addEventListener("change", (e) => {
        const constantGroup = document.getElementById("mv-constant-group");
        if (e.target.value === "constant") constantGroup.classList.remove("hidden");
        else constantGroup.classList.add("hidden");
        updateColumnAvailability();
    });

    document.querySelectorAll('input[name="data-purpose"]').forEach(radio => {
        radio.addEventListener("change", (e) => {
            appState.purpose = e.target.value;
            const splitConfig = document.getElementById("ml-split-config");
            if (appState.purpose === "ml") splitConfig.classList.remove("hidden");
            else splitConfig.classList.add("hidden");
            updateColumnAvailability();
            saveStateToStorage();
        });
    });

    const splitRange = document.getElementById("train-split");
    splitRange.addEventListener("input", (e) => {
        appState.trainSplit = e.target.value;
        document.getElementById("split-display").textContent = `Train: ${appState.trainSplit}% | Test: ${100 - appState.trainSplit}%`;
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
    
    // Sửa lỗi #2: Event listener cho nút Save/Apply Recipe
    document.getElementById("btn-save-recipe").addEventListener("click", async () => {
        if (appState.pipelineSteps.length === 0) {
            showToast("Chưa có bước nào trong pipeline để lưu!", "error");
            return;
        }
        const recipeName = prompt("Nhập tên cho Recipe này:", `Recipe - ${appState.filename}`);
        if (!recipeName) return;
        
        try {
            await saveRecipeAPI(recipeName, appState.pipelineSteps);
            showToast("Đã lưu Recipe thành công!", "success");
        } catch(err) {
            showToast("Lỗi khi lưu Recipe. (Chưa kết nối API Backend)", "error");
        }
    });
    
    // Thư viện các kịch bản chuẩn mẫu (Preset Recipes)
    const PRESET_RECIPES = {
        preset_1: {
            name: "Bộ lọc khuyết thiếu & Chuẩn hóa Null",
            steps: [
                { step_type: "standardize_nulls", config: {} },
                { step_type: "missing_values", config: { columns: null, strategy: "median" } }
            ]
        },
        preset_2: {
            name: "Xử lý nhiễu & Cắt lọc ngoại lai (IQR)",
            steps: [
                { step_type: "standardize_nulls", config: {} },
                { step_type: "outlier", config: { columns: null, method: "iqr", threshold: 1.5, handling: "remove" } }
            ]
        },
        preset_3: {
            name: "Chuẩn hóa dữ liệu số và Categorical",
            steps: [
                { step_type: "clean_numeric", config: { columns: null } },
                { step_type: "encoding", config: { columns: null, method: "one_hot" } },
                { step_type: "scaling", config: { columns: null, method: "min_max" } }
            ]
        }
    };

    document.getElementById("btn-apply-recipe").addEventListener("click", () => {
        const selected = document.getElementById("recipe-select").value;
        if (!selected) {
            showToast("Vui lòng chọn 1 kịch bản mẫu từ danh sách", "error");
            return;
        }

        const preset = PRESET_RECIPES[selected];
        if (!preset) {
            showToast("Kịch bản không tồn tại", "error");
            return;
        }

        // Nạp đúng các bước tương ứng của công thức mẫu
        appState.pipelineSteps = JSON.parse(JSON.stringify(preset.steps));
        renderPipelineQueue();
        saveStateToStorage();
        showToast(`Đã áp dụng mẫu: "${preset.name}" (${preset.steps.length} bước)`, "success");
    });

    const executeBtn = document.getElementById("btn-execute-pipeline");
    executeBtn.addEventListener("click", async () => {
        if (appState.pipelineSteps.length === 0) {
            showToast("Vui lòng thêm ít nhất 1 bước.", "error");
            return;
        }
        executeBtn.textContent = "Đang xử lý...";
        executeBtn.disabled = true;

        try {
            const response = await executePipelineAPI(appState.currentFileId, appState.pipelineSteps, appState.purpose, appState.trainSplit);
            renderAuditResult(response.audit_summary);
            showToast("Làm sạch dữ liệu thành công", "success");
            
            // Tự động đánh giá sức khỏe chất lượng dữ liệu khi ở Cloud/Online mode (cho cả EDA và ML)
            if (appState.mode === 'online') {
                runDataQualityEvaluation(false);
            }
        } catch (err) {
            showToast(err.message, "error");
        } finally {
            executeBtn.textContent = "Thực thi Pipeline làm sạch";
            executeBtn.disabled = false;
        }
    });

    async function runDataQualityEvaluation(showToastFeedback = true) {
        const btn = document.getElementById("btn-test-ai");
        const btnLabel = document.getElementById("btn-test-ai-label");
        if (btn) btn.disabled = true;
        if (btnLabel) btnLabel.textContent = "Đang kiểm tra sức khỏe...";

        try {
            const result = await benchmarkAIAPI(appState.currentFileId);
            const overall = result.overall_score !== undefined ? result.overall_score : (result.ml_readiness_score || 0);

            // 1. Cập nhật thanh & số tổng thể
            const fill = document.getElementById("health-score-fill");
            const txt = document.getElementById("health-score-text");
            const ratingEl = document.getElementById("health-score-rating");

            if (fill) {
                fill.style.width = `${Math.min(100, overall)}%`;
                if (overall >= 80) fill.style.backgroundColor = "var(--success)";
                else if (overall >= 50) fill.style.backgroundColor = "#eab308";
                else fill.style.backgroundColor = "var(--danger)";
            }
            if (txt) txt.textContent = `${overall}/100`;
            if (ratingEl) {
                ratingEl.textContent = result.rating || "Đạt chuẩn";
                if (result.badge_color === "success") ratingEl.style.color = "var(--success)";
                else if (result.badge_color === "danger") ratingEl.style.color = "var(--danger)";
                else if (result.badge_color === "warning") ratingEl.style.color = "#d97706";
                else ratingEl.style.color = "var(--primary)";
            }

            // 2. Cập nhật 4 sub-meters
            const bd = result.breakdown || {};
            
            // Completeness (30đ)
            const compScore = bd.completeness_score !== undefined ? bd.completeness_score : 0;
            const compEl = document.getElementById("sub-score-completeness");
            const compBar = document.getElementById("sub-bar-completeness");
            const compInfo = document.getElementById("sub-detail-completeness");
            if (compEl) compEl.textContent = `${compScore} / 30đ`;
            if (compBar) compBar.style.width = `${Math.min(100, (compScore / 30) * 100)}%`;
            if (compInfo) compInfo.textContent = `Tỷ lệ ô khuyết: ${bd.missing_cell_rate || 0}%`;

            // Deduplication (20đ)
            const dedupScore = bd.deduplication_score !== undefined ? bd.deduplication_score : 0;
            const dedupEl = document.getElementById("sub-score-dedup");
            const dedupBar = document.getElementById("sub-bar-dedup");
            const dedupInfo = document.getElementById("sub-detail-dedup");
            if (dedupEl) dedupEl.textContent = `${dedupScore} / 20đ`;
            if (dedupBar) dedupBar.style.width = `${Math.min(100, (dedupScore / 20) * 100)}%`;
            if (dedupInfo) dedupInfo.textContent = `Tỷ lệ trùng lặp: ${bd.duplicate_rate || 0}%`;

            // Type Uniformity (25đ)
            const typeScore = bd.type_uniformity_score !== undefined ? bd.type_uniformity_score : 0;
            const typeEl = document.getElementById("sub-score-uniformity");
            const typeBar = document.getElementById("sub-bar-uniformity");
            const typeInfo = document.getElementById("sub-detail-uniformity");
            if (typeEl) typeEl.textContent = `${typeScore} / 25đ`;
            if (typeBar) typeBar.style.width = `${Math.min(100, (typeScore / 25) * 100)}%`;
            if (typeInfo) typeInfo.textContent = `${bd.numeric_or_cat_columns || 0}/${bd.total_columns || 0} cột số/phân loại`;

            // Data Retention (25đ)
            const retScore = bd.retention_score !== undefined ? bd.retention_score : 0;
            const retEl = document.getElementById("sub-score-retention");
            const retBar = document.getElementById("sub-bar-retention");
            const retInfo = document.getElementById("sub-detail-retention");
            if (retEl) retEl.textContent = `${retScore} / 25đ`;
            if (retBar) retBar.style.width = `${Math.min(100, (retScore / 25) * 100)}%`;
            if (retInfo) retInfo.textContent = `Bảo toàn: ${bd.retention_rate || 100}% số dòng`;

            // 3. Diagnostics & Warnings
            const diagBox = document.getElementById("dq-diagnostics-box");
            const diagList = document.getElementById("dq-diagnostics-list");
            if (diagBox && diagList) {
                diagList.innerHTML = "";
                const diags = result.diagnostics || {};
                const zeroVars = diags.zero_variance_columns || [];
                const highCards = diags.high_cardinality_text_columns || [];

                if (zeroVars.length > 0 || highCards.length > 0) {
                    diagBox.classList.remove("hidden", "dq-diag-clean");
                    zeroVars.forEach(col => {
                        const li = document.createElement("li");
                        li.className = "dq-diag-item";
                        li.textContent = `Cột "${col}" có phương sai bằng 0 (chỉ chứa 1 giá trị duy nhất, không mang lại thông tin phân tích/ML). Khuyên loại bỏ.`;
                        diagList.appendChild(li);
                    });
                    highCards.forEach(col => {
                        const li = document.createElement("li");
                        li.className = "dq-diag-item";
                        li.textContent = `Cột văn bản "${col}" có quá nhiều giá trị riêng biệt (>50 categories). Cần cân nhắc mã hóa hoặc loại bỏ.`;
                        diagList.appendChild(li);
                    });
                } else {
                    diagBox.classList.remove("hidden");
                    diagBox.classList.add("dq-diag-clean");
                    const li = document.createElement("li");
                    li.className = "dq-diag-item";
                    li.textContent = "Dữ liệu đạt chuẩn: Không phát hiện cột zero-variance hay văn bản rác bất thường.";
                    diagList.appendChild(li);
                }
            }

            if (showToastFeedback) {
                showToast(`Đã đánh giá chất lượng dữ liệu: ${overall}/100 (${result.rating})`, "success");
            }
        } catch (err) {
            showToast("Không thể tải đánh giá chất lượng: " + err.message, "error");
        } finally {
            if (btn) btn.disabled = false;
            if (btnLabel) btnLabel.textContent = "Đánh giá lại sức khỏe dữ liệu";
        }
    }

    document.getElementById("btn-test-ai").addEventListener("click", async (e) => {
        e.preventDefault();
        await runDataQualityEvaluation(true);
    });

    // --- 6. XUẤT DỮ LIỆU TẢI VỀ ---
    document.getElementById("btn-export-csv").addEventListener("click", () => downloadExportFileAPI(appState.currentFileId, "csv"));
    document.getElementById("btn-export-json").addEventListener("click", () => downloadExportFileAPI(appState.currentFileId, "json"));
    document.getElementById("btn-export-train").addEventListener("click", () => downloadExportFileAPI(appState.currentFileId, "csv", "train_cleaned"));
    document.getElementById("btn-export-test").addEventListener("click", () => downloadExportFileAPI(appState.currentFileId, "csv", "test_cleaned"));
    
    // --- 7. MODALS, DRAWER & FORMS ---
    document.getElementById("btn-close-auth").addEventListener("click", () => document.getElementById("auth-modal").classList.add("hidden"));
    document.getElementById("btn-auth").addEventListener("click", () => document.getElementById("auth-modal").classList.remove("hidden"));
    
    // Sửa lỗi #1: PreventDefault cho form đăng nhập
    document.getElementById("auth-form").addEventListener("submit", (e) => {
        e.preventDefault(); 
        appState.user = document.getElementById("auth-username").value;
        document.getElementById("auth-modal").classList.add("hidden");
        document.getElementById("btn-auth").classList.add("hidden");
        document.getElementById("profile-badge").classList.remove("hidden");
        document.getElementById("username-display").textContent = appState.user;
        showToast(`Đăng nhập thành công: ${appState.user}`, "success");
        saveStateToStorage();
    });
    
    // Sửa lỗi #3: Sign Out và Chuyển Đăng ký
    document.getElementById("btn-logout").addEventListener("click", () => {
        appState.user = null;
        document.getElementById("profile-badge").classList.add("hidden");
        document.getElementById("btn-auth").classList.remove("hidden");
        saveStateToStorage();
        showToast("Đã đăng xuất", "success");
    });
    
    let isLogin = true;
    document.getElementById("toggle-auth-mode").addEventListener("click", (e) => {
        e.preventDefault();
        isLogin = !isLogin;
        document.getElementById("auth-title").textContent = isLogin ? "Đăng nhập hệ thống" : "Đăng ký tài khoản";
        document.querySelector("#auth-form button[type='submit']").textContent = isLogin ? "Đăng nhập" : "Đăng ký";
        e.target.textContent = isLogin ? "Đăng ký ngay" : "Đăng nhập";
    });

    // Drawer Lịch sử
    document.getElementById("btn-close-history").addEventListener("click", () => document.getElementById("history-drawer").classList.add("hidden"));
    document.getElementById("btn-history").addEventListener("click", async () => {
        document.getElementById("history-drawer").classList.remove("hidden");
        // Giả lập logic gọi API hiển thị
        const list = document.getElementById("history-list");
        if(appState.filename && appState.pipelineSteps.length > 0) {
            list.innerHTML = `
                <li class="history-item">
                    <div class="history-title">${appState.filename}</div>
                    <div class="history-meta">Vừa xong • ${appState.pipelineSteps.length} bước</div>
                </li>
            `;
        }
    });
});