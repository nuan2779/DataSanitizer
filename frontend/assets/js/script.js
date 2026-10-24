import { appState } from "./state.js";
import { uploadDatasetAPI, fetchDatasetProfileAPI, executePipelineAPI, downloadExportFileAPI } from "./api.js";
import { renderProfileData } from "./ui-profiler.js";
import { handleStepTypeChange, addStepToPipeline, renderPipelineQueue, renderAuditResult } from "./ui-pipeline.js";

document.addEventListener("DOMContentLoaded", () => {
    const fileInput = document.getElementById("file-input");
    const uploadBtn = document.getElementById("btn-upload");
    const selectedFileName = document.getElementById("selected-file-name");

    // Sự kiện chọn file từ máy tính
    fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) {
            selectedFileName.textContent = `Đã chọn: ${fileInput.files[0].name}`;
            uploadBtn.disabled = false;
        }
    });

    // LUỒNG 1: Upload file -> Nhận file_id -> Tự động gọi GET/api/profile/{file_id}
    document.getElementById("upload-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        if (fileInput.files.length === 0) return;

        uploadBtn.disabled = true;

        try {
            // Bước 1: Gửi file lên POST/api/upload
            uploadBtn.textContent = "Đang tải file lên server...";
            const uploadRes = await uploadDatasetAPI(fileInput.files[0]);
            
            const fileId = uploadRes.file_id;
            if (!fileId) {
                throw new Error("Server không trả về file_id sau khi upload!");
            }

            // Bước 2: Có file_id -> Gọi tiếp GET/api/profile/{file_id}
            selectedFileName.textContent = `File đã tải lên thành công (ID: ${fileId}). Đang khám bệnh dữ liệu...`;
            uploadBtn.textContent = "Đang khám bệnh dữ liệu...";
            
            const profileData = await fetchDatasetProfileAPI(fileId);

            // Đảm bảo giữ lại file_id và tên file nếu response profile không kèm sẵn
            profileData.file_id = profileData.file_id || fileId;
            profileData.filename = profileData.filename || fileInput.files[0].name;

            // Đổ dữ liệu vào #summary-rows, #summary-cols và vẽ bảng #profile-tbody
            renderProfileData(profileData);
            selectedFileName.textContent = `Hoàn tất phân tích: ${profileData.filename}`;

        } catch (err) {
            alert(err.message);
        } finally {
            uploadBtn.textContent = "Bắt đầu phân tích dữ liệu";
            uploadBtn.disabled = false;
        }
    });

    // Sự kiện đóng Modal chi tiết cột
    document.getElementById("btn-close-modal").addEventListener("click", () => {
        document.getElementById("column-modal").classList.add("hidden");
    });

    // Sự kiện thay đổi công cụ trong Pipeline
    document.getElementById("step-type-select").addEventListener("change", handleStepTypeChange);

    // Ẩn/hiện ô nhập fill_value khi chọn strategy 'constant' trong Missing Values
    document.getElementById("mv-strategy").addEventListener("change", (e) => {
        const constantGroup = document.getElementById("mv-constant-group");
        if (e.target.value === "constant") {
            constantGroup.classList.remove("hidden");
        } else {
            constantGroup.classList.add("hidden");
        }
    });

    //Nút Chọn tất cả/ Bỏ chọn tất cả cột
    document.getElementById("btn-select-all-cols").addEventListener("click", () => {
        document.querySelectorAll(".col-checkbox").forEach(cb => cb.checked = true);
    });
    document.getElementById("btn-clear-all-cols").addEventListener("click", () => {
        document.querySelectorAll(".col-checkbox").forEach(cb => cb.checked = false);
    });

    // bước xử lý & Xóa toàn bộ danh sách chờ Pipeline
    document.getElementById("btn-add-step").addEventListener("click", addStepToPipeline);
    document.getElementById("btn-clear-pipeline").addEventListener("click", () => {
        appState.pipelineSteps = [];
        renderPipelineQueue();
    });

    // LUỒNG 3: Thực thi Pipeline dọn dẹp (POST /api/clean)
    const executeBtn = document.getElementById("btn-execute-pipeline");
    executeBtn.addEventListener("click", async () => {
        // Kiểm tra an toàn: Nếu chưa thêm công cụ nào thì báo lỗi
        if (appState.pipelineSteps.length === 0) {
            alert("Vui lòng thêm ít nhất 1 bước vào Pipeline trước khi thực thi!");
            return;
        }

        // Chạy với Backend thật qua POST /api/clean
        executeBtn.textContent = "Đang xử lý làm sạch...";
        executeBtn.disabled = true;

        try {
            const response = await executePipelineAPI(appState.currentFileId, appState.pipelineSteps);
            // Hỗ trợ cả trường hợp Backend trả về { audit_summary: {...} } hoặc trả thẳng object audit
            renderAuditResult(response.audit_summary || response.audit || response);
        } catch (err) {
            alert(err.message);
        } finally {
            executeBtn.textContent = "Thực thi Pipeline làm sạch";
            executeBtn.disabled = false;
        }
    });

    // Xuất file CSV / JSON
    document.getElementById("btn-export-csv").addEventListener("click", () => {
        downloadExportFileAPI(appState.currentFileId, "csv");
    });
    document.getElementById("btn-export-json").addEventListener("click", () => {
        downloadExportFileAPI(appState.currentFileId, "json");
    });
});