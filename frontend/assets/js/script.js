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

    // --- 4. UPLOAD & KAGGLE HUB ---
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

    document.querySelectorAll(".btn-sample").forEach(btn => {
        btn.addEventListener("click", async () => {
            const sampleId = btn.dataset.id;
            uploadBtn.textContent = "Đang nạp dữ liệu Kaggle...";
            uploadBtn.disabled = true;
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
                showToast(`Đã nạp bộ dữ liệu ${sampleId}`, "success");
                scrollToSection("profile-section");
            } catch (err) {
                showToast(err.message, "error");
            } finally {
                uploadBtn.textContent = "Bắt đầu phân tích dữ liệu";
                uploadBtn.disabled = false;
            }
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
    
    document.getElementById("btn-apply-recipe").addEventListener("click", () => {
        const selected = document.getElementById("recipe-select").value;
        if (!selected) {
            showToast("Vui lòng chọn 1 Recipe từ thư viện", "error");
            return;
        }
        // Mock data để demo
        appState.pipelineSteps.push({
            step_type: "missing_values", config: { columns: null, strategy: "median" }
        });
        renderPipelineQueue();
        saveStateToStorage();
        showToast("Đã nạp Recipe vào danh sách chờ", "success");
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
        } catch (err) {
            showToast(err.message, "error");
        } finally {
            executeBtn.textContent = "Thực thi Pipeline làm sạch";
            executeBtn.disabled = false;
        }
    });

    document.getElementById("btn-test-ai").addEventListener("click", async (e) => {
        e.preventDefault();
        const btn = e.target;
        btn.disabled = true;
        btn.textContent = "Đang chạy Baseline...";
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
            showToast("Backend chưa có API chấm điểm AI", "error");
        } finally {
            btn.textContent = "Chấm điểm dữ liệu & Test AI";
            btn.disabled = false;
        }
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

    // Xử lý Form Submit (Kiểm tra logic chặt chẽ)
    document.getElementById("auth-form").addEventListener("submit", (e) => {
        e.preventDefault(); 
        
        const username = document.getElementById("auth-username").value;
        const pass = document.getElementById("auth-password").value;
        
        // Nếu đang ở chế độ ĐĂNG KÝ
        if (!isLogin) {
            const confirmPass = document.getElementById("auth-confirm-password").value;
            const termsCheck = document.getElementById("auth-terms").checked;
            
            if (pass !== confirmPass) {
                showToast("Mật khẩu xác nhận không khớp!", "error");
                return;
            }
            if (!termsCheck) {
                showToast("Bạn phải đồng ý với Điều khoản dịch vụ.", "error");
                return;
            }
            
            // Nếu hợp lệ: Giả lập lưu vào DB thành công và ép người dùng quay lại Đăng nhập
            showToast("Đăng ký thành công! Vui lòng đăng nhập.", "success");
            
            // Xóa form và chuyển ngược lại chế độ Đăng nhập
            document.getElementById("auth-password").value = "";
            document.getElementById("auth-confirm-password").value = "";
            document.getElementById("toggle-auth-mode").click(); 
            return; // Dừng lại, bắt người dùng tự bấm đăng nhập
        }
        
        // Nếu đang ở chế độ ĐĂNG NHẬP (Gọi API Login)
        appState.user = username;
        document.getElementById("auth-modal").classList.add("hidden");
        document.getElementById("btn-auth").classList.add("hidden");
        document.getElementById("profile-badge").classList.remove("hidden");
        document.getElementById("username-display").textContent = appState.user;
        
        showToast(`Đăng nhập thành công: ${appState.user}`, "success");
        saveStateToStorage();
    });
    
    // Nút Đăng xuất
    document.getElementById("btn-logout").addEventListener("click", () => {
        appState.user = null;
        document.getElementById("profile-badge").classList.add("hidden");
        document.getElementById("btn-auth").classList.remove("hidden");
        saveStateToStorage();
        showToast("Đã đăng xuất", "success");
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

    // Xử lý Đăng nhập bằng Google (Mock UI)
    document.getElementById("btn-google-login").addEventListener("click", () => {
        // Tự động gán một tên tài khoản Google giả định
        appState.user = "Google User (Dev)";
        
        // Cập nhật giao diện
        document.getElementById("auth-modal").classList.add("hidden");
        document.getElementById("btn-auth").classList.add("hidden");
        document.getElementById("profile-badge").classList.remove("hidden");
        document.getElementById("username-display").textContent = appState.user;
        
        showToast("Đã liên kết tài khoản Google thành công!", "success");
        saveStateToStorage();
    });
});