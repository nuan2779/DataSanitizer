import { appState, saveStateToStorage, clearSavedState, loadStateFromStorage } from "./state.js";
import { 
    uploadDatasetAPI, 
    fetchDatasetProfileAPI, 
    executePipelineAPI, 
    downloadExportFileAPI, 
    loadSampleDatasetAPI, 
    benchmarkAIAPI, 
    saveRecipeAPI,
    loginAPI,
    registerAPI,
    logoutAPI,
    getMeAPI,
    fetchHistoryAPI,
    downloadHistoryFileAPI,
    deleteHistoryItemAPI,
    googleLoginAPI
} from "./api.js";
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

    // --- 2. QUẢN LÝ CHẾ ĐỘ OFFLINE / ONLINE & XÁC THỰC BẮT BUỘC TRÊN CLOUD ---
    function applyWorkspaceMode(mode, silent = false) {
        appState.mode = mode;
        saveStateToStorage();
        
        const offlineBadge = document.getElementById("offline-badge");
        const kaggleHub = document.getElementById("kaggle-hub");
        const btnHistory = document.getElementById("btn-history");
        const btnAuth = document.getElementById("btn-auth");
        const profileBadge = document.getElementById("profile-badge");
        const usernameDisplay = document.getElementById("username-display");
        const recipeLib = document.getElementById("recipe-library");
        const btnSaveRecipe = document.getElementById("btn-save-recipe");
        const subNavBar = document.querySelector(".sub-nav-bar");
        const onlineAuthSection = document.getElementById("online-auth-section");
        const uploadSection = document.getElementById("upload-section");
        const profileSection = document.getElementById("profile-section");
        const pipelineSection = document.getElementById("pipeline-section");
        const resultSection = document.getElementById("result-section");

        if (mode === 'online') {
            offlineBadge.classList.add("hidden");
            btnAuth.classList.add("hidden");

            if (!appState.user) {
                // CHƯA ĐĂNG NHẬP: Bỏ hỏi đưa file, chỉ hiển thị màn hình đăng nhập
                if (onlineAuthSection) onlineAuthSection.classList.remove("hidden");
                if (subNavBar) subNavBar.classList.add("hidden");
                if (uploadSection) uploadSection.classList.add("hidden");
                if (profileSection) profileSection.classList.add("hidden");
                if (pipelineSection) pipelineSection.classList.add("hidden");
                if (resultSection) resultSection.classList.add("hidden");
                if (kaggleHub) kaggleHub.classList.add("hidden");
                if (btnHistory) btnHistory.classList.add("hidden");
                if (profileBadge) profileBadge.classList.add("hidden");
                if (recipeLib) recipeLib.classList.add("hidden");
                if (btnSaveRecipe) btnSaveRecipe.classList.add("hidden");
                if (!silent) showToast("Vui lòng đăng nhập để sử dụng Cloud Workspace", "info");
            } else {
                // ĐÃ ĐĂNG NHẬP: Hiển thị đầy đủ giao diện làm việc
                if (onlineAuthSection) onlineAuthSection.classList.add("hidden");
                if (subNavBar) subNavBar.classList.remove("hidden");
                if (uploadSection) uploadSection.classList.remove("hidden");
                if (kaggleHub) kaggleHub.classList.remove("hidden");
                if (btnHistory) btnHistory.classList.remove("hidden");
                if (profileBadge) profileBadge.classList.remove("hidden");
                if (usernameDisplay) usernameDisplay.textContent = appState.user;
                if (recipeLib) recipeLib.classList.remove("hidden");
                if (btnSaveRecipe) btnSaveRecipe.classList.remove("hidden");
                if (!silent) showToast(`Chào mừng trở lại, ${appState.user}`, "success");
            }
        } else {
            // CHẾ ĐỘ OFFLINE: Xử lý cục bộ 100%, không cần đăng nhập
            if (onlineAuthSection) onlineAuthSection.classList.add("hidden");
            if (subNavBar) subNavBar.classList.remove("hidden");
            if (uploadSection) uploadSection.classList.remove("hidden");
            if (offlineBadge) offlineBadge.classList.remove("hidden");
            if (kaggleHub) kaggleHub.classList.add("hidden");
            if (btnHistory) btnHistory.classList.add("hidden");
            if (btnAuth) btnAuth.classList.add("hidden");
            if (profileBadge) profileBadge.classList.add("hidden");
            if (recipeLib) recipeLib.classList.add("hidden");
            if (btnSaveRecipe) btnSaveRecipe.classList.add("hidden");
            const mlBenchmark = document.getElementById("ml-benchmark");
            if (mlBenchmark) mlBenchmark.classList.add("hidden");
            if (!silent) showToast("Đã chuyển sang Chế độ Cục bộ (Offline)", "info");
        }
    }

    const modeToggle = document.getElementById("mode-toggle");
    modeToggle.addEventListener("change", (e) => {
        const selectedMode = e.target.checked ? 'online' : 'offline';
        applyWorkspaceMode(selectedMode);
    });

    // --- TAB CHUYỂN ĐỔI GIỮA ĐĂNG NHẬP VÀ ĐĂNG KÝ TRÊN ONLINE AUTH CARD ---
    const tabLoginBtn = document.getElementById("tab-login-btn");
    const tabRegisterBtn = document.getElementById("tab-register-btn");
    const loginForm = document.getElementById("online-login-form");
    const registerForm = document.getElementById("online-register-form");
    const loginErr = document.getElementById("online-login-error");
    const regErr = document.getElementById("online-reg-error");

    function switchAuthTab(targetTab) {
        if (targetTab === "login") {
            tabLoginBtn?.classList.add("active");
            tabRegisterBtn?.classList.remove("active");
            loginForm?.classList.remove("hidden");
            registerForm?.classList.add("hidden");
            if (loginErr) loginErr.classList.add("hidden");
        } else {
            tabRegisterBtn?.classList.add("active");
            tabLoginBtn?.classList.remove("active");
            registerForm?.classList.remove("hidden");
            loginForm?.classList.add("hidden");
            if (regErr) regErr.classList.add("hidden");
        }
    }

    tabLoginBtn?.addEventListener("click", () => switchAuthTab("login"));
    tabRegisterBtn?.addEventListener("click", () => switchAuthTab("register"));

    // --- XỬ LÝ SUBMIT FORM ĐĂNG NHẬP CLOUD WORKSPACE ---
    loginForm?.addEventListener("submit", async (e) => {
        e.preventDefault();
        const identifier = document.getElementById("online-login-identifier").value.trim();
        const password = document.getElementById("online-login-password").value;
        const submitBtn = document.getElementById("btn-submit-online-login");

        if (loginErr) loginErr.classList.add("hidden");
        submitBtn.disabled = true;
        submitBtn.textContent = "Đang xác thực...";

        try {
            const data = await loginAPI(identifier, password);
            appState.user = data.user.username;
            saveStateToStorage();
            loginForm.reset();
            applyWorkspaceMode("online");
            showToast(`Đăng nhập thành công: ${appState.user}`, "success");
        } catch (err) {
            if (loginErr) {
                loginErr.textContent = err.message || "Tên đăng nhập hoặc mật khẩu không chính xác.";
                loginErr.classList.remove("hidden");
            }
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = "Đăng nhập vào Cloud";
        }
    });

    // --- XỬ LÝ SUBMIT FORM ĐĂNG KÝ CLOUD WORKSPACE ---
    registerForm?.addEventListener("submit", async (e) => {
        e.preventDefault();
        const username = document.getElementById("online-reg-username").value.trim();
        const email = document.getElementById("online-reg-email").value.trim();
        const password = document.getElementById("online-reg-password").value;
        const confirmPass = document.getElementById("online-reg-confirm").value;
        const submitBtn = document.getElementById("btn-submit-online-reg");

        if (regErr) regErr.classList.add("hidden");

        if (password !== confirmPass) {
            if (regErr) {
                regErr.textContent = "Mật khẩu xác nhận không khớp. Vui lòng kiểm tra lại.";
                regErr.classList.remove("hidden");
            }
            return;
        }

        submitBtn.disabled = true;
        submitBtn.textContent = "Đang khởi tạo tài khoản...";

        try {
            const data = await registerAPI(username, email, password);
            appState.user = data.user.username;
            saveStateToStorage();
            registerForm.reset();
            applyWorkspaceMode("online");
            showToast(`Đăng ký tài khoản thành công! Chào mừng ${appState.user}`, "success");
        } catch (err) {
            if (regErr) {
                regErr.textContent = err.message || "Đăng ký không thành công. Vui lòng kiểm tra lại thông tin.";
                regErr.classList.remove("hidden");
            }
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = "Tạo tài khoản";
        }
    });

    // Khởi tạo trạng thái ban đầu theo mode đã lưu
    if (appState.mode === 'online') {
        getMeAPI().then(me => {
            if (me && me.user) {
                appState.user = me.user.username;
                saveStateToStorage();
            } else if (!appState.user) {
                appState.user = null;
                saveStateToStorage();
            }
            applyWorkspaceMode(appState.mode, true);
        }).catch(() => {
            applyWorkspaceMode(appState.mode, true);
        });
    } else {
        applyWorkspaceMode("offline", true);
    }
    modeToggle.checked = (appState.mode === 'online');

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
        
        // 1. Trường hợp bấm nút khi đang ở phiên cũ (không chọn file mới)
        if (fileInput.files.length === 0 && appState.currentFileId) {
            scrollToSection("profile-section");
            showToast("Tiếp tục phiên làm việc hiện tại", "success");
            return; // Dừng luôn ở đây, KHÔNG xóa pipeline, KHÔNG gọi lại API
        }
        
        // Nếu không có file mới và cũng không có phiên cũ -> thoát
        if (fileInput.files.length === 0 && !appState.currentFileId) return;

        // 2. Trường hợp thực sự tải file mới lên
        uploadBtn.disabled = true;
        try {
            clearSavedState(); // Xóa phiên cũ
            uploadBtn.textContent = "Đang tải file lên...";
            const uploadRes = await uploadDatasetAPI(fileInput.files[0]);
            const fileId = uploadRes.file_id;
            appState.filename = uploadRes.filename || fileInput.files[0].name;

            uploadBtn.textContent = "Đang khám bệnh dữ liệu...";
            const profileData = await fetchDatasetProfileAPI(fileId);
            
            // CHỈ KHI TẢI FILE MỚI THÌ MỚI XÓA PIPELINE
            appState.pipelineSteps = [];
            renderPipelineQueue();
            document.getElementById("result-section").classList.add("hidden");
            
            appState.totalRows = profileData.total_rows;
            renderProfileData(profileData);
            updateColumnAvailability();
            
            selectedFileName.textContent = `Hoàn tất: ${appState.filename}`;
            showToast("Tải và phân tích dữ liệu thành công", "success");
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
                fill.style.backgroundColor = "var(--primary)";
            }
            if (txt) txt.textContent = `${overall}/100`;
            if (ratingEl) {
                ratingEl.textContent = result.rating || "Đạt chuẩn";
                if (result.badge_color === "success") ratingEl.style.color = "var(--primary)";
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
    
    let isLogin = true; // Trạng thái mặc định là Đăng nhập

    // Xử lý nút Chuyển đổi Đăng nhập / Đăng ký
    document.getElementById("toggle-auth-mode").addEventListener("click", (e) => {
        e.preventDefault();
        isLogin = !isLogin;
        
        // Cập nhật Giao diện
        document.getElementById("auth-title").textContent = isLogin ? "Đăng nhập hệ thống" : "Tạo tài khoản mới";
        document.getElementById("auth-submit-btn").textContent = isLogin ? "Đăng nhập" : "Đăng ký";
        e.target.textContent = isLogin ? "Đăng ký ngay" : "Đăng nhập";
        
        // Ẩn/Hiện khối Xác nhận mật khẩu & Điều khoản
        const regFields = document.getElementById("register-fields");
        const confirmPass = document.getElementById("auth-confirm-password");
        const termsCheck = document.getElementById("auth-terms");
        
        if (isLogin) {
            regFields.classList.add("hidden");
            confirmPass.removeAttribute("required");
            termsCheck.removeAttribute("required");
        } else {
            regFields.classList.remove("hidden");
            confirmPass.setAttribute("required", "true");
            termsCheck.setAttribute("required", "true");
        }
    });

    const authForm = document.getElementById("auth-form");
    if (authForm) {
        authForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const identifier = document.getElementById("auth-username").value;
            const pass = document.getElementById("auth-password").value;
            const submitBtn = document.getElementById("auth-submit-btn");
            
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = "Đang xử lý...";
            }
            
            try {
                const data = await loginAPI(identifier, pass);
                appState.user = data.user?.username || identifier;
                appState.authToken = data.token;
                saveStateToStorage();
                
                document.getElementById("auth-modal").classList.add("hidden");
                document.getElementById("btn-auth").classList.add("hidden");
                document.getElementById("profile-badge").classList.remove("hidden");
                document.getElementById("username-display").textContent = appState.user;
                
                showToast(`Đăng nhập thành công: ${appState.user}`, "success");
                authForm.reset();
            } catch (err) {
                showToast(err.message || "Đăng nhập thất bại", "error");
            } finally {
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.textContent = "Đăng nhập";
                }
            }
        });
    }
    
    // Sign Out khỏi hệ thống
    document.getElementById("btn-logout").addEventListener("click", async () => {
        try {
            await logoutAPI();
        } catch (e) {
            console.warn("Logout error:", e);
        }
        appState.user = null;
        saveStateToStorage();
        const historyList = document.getElementById("history-list");
        if (historyList) historyList.innerHTML = `<li class="empty-state">Chưa có lịch sử xử lý nào.</li>`;
        applyWorkspaceMode(appState.mode, true);
        showToast("Đã đăng xuất khỏi Cloud Workspace", "info");
    });

    // Drawer Lịch sử (Gọi API thật từ backend, lưu riêng biệt theo từng tài khoản)
    document.getElementById("btn-close-history").addEventListener("click", () => document.getElementById("history-drawer").classList.add("hidden"));
    document.getElementById("btn-history").addEventListener("click", async () => {
        document.getElementById("history-drawer").classList.remove("hidden");
        const list = document.getElementById("history-list");
        list.innerHTML = `<li class="empty-state">Đang tải lịch sử của tài khoản ${appState.user || ""}...</li>`;
        
        try {
            const history = await fetchHistoryAPI();
            if (!history || history.length === 0) {
                list.innerHTML = `<li class="empty-state">Chưa có lịch sử xử lý nào trên tài khoản này.</li>`;
                return;
            }
            list.innerHTML = history.map(item => {
                const rows = item.stats?.processed_data?.rows;
                const purpose = item.stats?.purpose === "ml" ? "Học máy (ML)" : "Khám phá (EDA)";
                const metaInfo = [
                    item.created_at || "Vừa xong",
                    rows !== undefined ? `${rows} dòng` : "Đã xử lý",
                    purpose
                ].join(" • ");

                return `
                    <li class="history-item" id="history-item-${item.id}">
                        <div class="history-title">${item.filename || "Tập dữ liệu"}</div>
                        <div class="history-meta">${metaInfo}</div>
                        <div class="history-actions" style="display: flex; gap: 8px; margin-top: 8px;">
                            <button type="button" class="btn btn-outline btn-dl-history" data-id="${item.id}" style="padding: 3px 8px; font-size: 11px;">Tải lại CSV</button>
                            <button type="button" class="btn-link text-danger btn-del-history" data-id="${item.id}" style="font-size: 11px;">Xóa</button>
                        </div>
                    </li>
                `;
            }).join("");

            // Gán sự kiện Tải lại và Xóa
            list.querySelectorAll(".btn-dl-history").forEach(btn => {
                btn.addEventListener("click", () => downloadHistoryFileAPI(btn.dataset.id));
            });

            list.querySelectorAll(".btn-del-history").forEach(btn => {
                btn.addEventListener("click", async () => {
                    const id = btn.dataset.id;
                    try {
                        await deleteHistoryItemAPI(id);
                        document.getElementById(`history-item-${id}`)?.remove();
                        if (list.children.length === 0) {
                            list.innerHTML = `<li class="empty-state">Chưa có lịch sử xử lý nào trên tài khoản này.</li>`;
                        }
                        showToast("Đã xóa bản ghi lịch sử", "info");
                    } catch (err) {
                        showToast("Lỗi xóa: " + err.message, "error");
                    }
                });
            });
        } catch (err) {
            list.innerHTML = `<li class="empty-state">Không thể tải lịch sử: ${err.message}</li>`;
        }
    });

    // Xử lý Đăng nhập bằng Google
    window.handleCredentialResponse = async function(response) {
        const submitBtn = document.getElementById("btn-submit-online-login");
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = "Đang xác thực Google...";
        }
        try {
            const data = await googleLoginAPI(response.credential);
            appState.user = data.user?.username || data.user?.email || "Google User";
            appState.authToken = data.access_token;

            document.getElementById("auth-modal")?.classList.add("hidden");
            document.getElementById("btn-auth")?.classList.add("hidden");
            document.getElementById("profile-badge")?.classList.remove("hidden");
            document.getElementById("username-display").textContent = appState.user;
            
            saveStateToStorage();
            applyWorkspaceMode(appState.mode, true);
            showToast(`Đăng nhập Google thành công: ${appState.user}`, "success");
        } catch (err) {
            showToast(err.message, "error");
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = "Đăng nhập";
            }
        }
    };
});