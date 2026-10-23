import { appState, mockProfileData } from "./state.js";
import { uploadDatasetAPI, fetchDatasetProfileAPI, executePipelineAPI, downloadExportFileAPI } from "./api.js";
import { renderProfileData } from "./ui-profiler.js";
import { handleStepTypeChange, addStepToPipeline, renderPipelineQueue, renderAuditResult } from "./ui-pipeline.js";

document.addEventListener("DOMContentLoaded", () => {
    const fileInput = document.getElementById("file-input");
    const uploadBtn = document.getElementById("btn-upload");
    const selectedFileName = document.getElementById("selected-file-name");

    // 1. Sự kiện chọn file từ máy tính
    fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) {
            selectedFileName.textContent = `Đã chọn: ${fileInput.files[0].name}`;
            uploadBtn.disabled = false;
        }
    });

    // 2. LUỒNG 1: Upload file -> Nhận file_id -> Tự động gọi GET /api/profile/{file_id}
    document.getElementById("upload-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        if (fileInput.files.length === 0) return;

        uploadBtn.disabled = true;

        try {
            // Bước 1: Gửi file lên POST /api/upload
            uploadBtn.textContent = "Đang tải file lên server...";
            const uploadRes = await uploadDatasetAPI(fileInput.files[0]);

            const fileId = uploadRes.file_id;
            if (!fileId) {
                throw new Error("Server không trả về file_id sau khi upload!");
            }

            // Bước 2: Có file_id -> Gọi tiếp GET /api/profile/{file_id}
            selectedFileName.textContent = `File đã tải lên thành công (ID: ${fileId}). Đang khám bệnh dữ liệu...`;
            uploadBtn.textContent = "Đang khám bệnh dữ liệu...";

            const profileData = await fetchDatasetProfileAPI(fileId);

            // Đảm bảo giữ lại file_id và tên file nếu response profile không kèm sẵn
            profileData.file_id = profileData.file_id || fileId;
            profileData.filename = uploadRes.filename || fileInput.files[0].name;

            // Clear steps from the previous upload (their column names may be stale).
            appState.pipelineSteps = [];
            renderPipelineQueue();
            document.getElementById("result-section").classList.add("hidden");

            // Đổ dữ liệu vào #summary-rows, #summary-cols và vẽ bảng #profile-tbody
            renderProfileData(profileData);
            selectedFileName.textContent = `Hoàn tất phân tích: ${profileData.filename}`;

        } catch (err) {
            alert(err.message + "\n(Gợi ý: Bạn có thể bấm nút 'Nạp dữ liệu mẫu' ở góc trên nếu chưa bật Backend)");
        } finally {
            uploadBtn.textContent = "Bắt đầu phân tích dữ liệu";
            uploadBtn.disabled = false;
        }
    });

    // 3. Nút "Nạp dữ liệu mẫu (Test UI)"
    const demoBtn = document.getElementById("btn-load-demo");
    if (demoBtn) {
        demoBtn.addEventListener("click", () => {
            selectedFileName.textContent = `Đang dùng dữ liệu mẫu: ${mockProfileData.filename}`;
            appState.pipelineSteps = [];
            renderPipelineQueue();
            document.getElementById("result-section").classList.add("hidden");
            renderProfileData(mockProfileData);
        });
    }

    // 4. Sự kiện đóng Modal chi tiết cột
    document.getElementById("btn-close-modal").addEventListener("click", () => {
        document.getElementById("column-modal").classList.add("hidden");
    });

    // 5. Sự kiện thay đổi công cụ trong Pipeline
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

    // 6. Nút Chọn tất cả / Bỏ chọn tất cả cột
    document.getElementById("btn-select-all-cols").addEventListener("click", () => {
        document.querySelectorAll(".col-checkbox").forEach(cb => cb.checked = true);
    });
    document.getElementById("btn-clear-all-cols").addEventListener("click", () => {
        document.querySelectorAll(".col-checkbox").forEach(cb => cb.checked = false);
    });

    // 7. Thêm bước xử lý & Xóa toàn bộ danh sách chờ Pipeline
    document.getElementById("btn-add-step").addEventListener("click", addStepToPipeline);
    document.getElementById("btn-clear-pipeline").addEventListener("click", () => {
        appState.pipelineSteps = [];
        renderPipelineQueue();
    });

    // 8. LUỒNG 3: Thực thi Pipeline dọn dẹp (POST /api/clean)
    const executeBtn = document.getElementById("btn-execute-pipeline");
    executeBtn.addEventListener("click", async () => {
        // Chế độ Test UI khi chưa bật Backend
        if (appState.currentFileId === "demo_ds66_001") {
            let currentRows = mockProfileData.total_rows;
            let currentCols = mockProfileData.total_columns;
            const history = [];

            appState.pipelineSteps.forEach((s, idx) => {
                const cols = s.config.columns || appState.columns.map(c => c.name);
                let desc = `Đã thực thi '${s.step_type}' cho cột: ${cols.join(", ")}`;

                if (s.step_type === "missing_values") {
                    if (s.config.strategy === "drop_row") {
                        let removed = 0;
                        cols.forEach(colName => {
                            const colObj = appState.columns.find(c => c.name === colName);
                            if (colObj) removed += colObj.null_count;
                        });
                        removed = Math.min(removed, currentRows);
                        currentRows -= removed;
                        desc = `Đã xóa ${removed} dòng có ô trống ở các cột: ${cols.join(", ")}`;
                    } else if (s.config.strategy === "drop_col") {
                        currentCols = Math.max(1, currentCols - cols.length);
                        desc = `Đã xóa ${cols.length} cột: ${cols.join(", ")}`;
                    } else {
                        desc = `Đã điền ô trống theo phương pháp '${s.config.strategy}' cho các cột: ${cols.join(", ")}`;
                    }
                } else if (s.step_type === "outlier") {
                    if (s.config.handling === "remove") {
                        let outRemoved = 0;
                        cols.forEach(colName => {
                            const colObj = appState.columns.find(c => c.name === colName);
                            if (colObj && colObj.statistics) outRemoved += colObj.statistics.outlier_count;
                        });
                        currentRows -= outRemoved;
                        desc = `Đã loại bỏ ${outRemoved} dòng ngoại lai (${s.config.method}) ở các cột: ${cols.join(", ")}`;
                    } else {
                        desc = `Đã cắt ngọn (cap) giá trị ngoại lai ở các cột: ${cols.join(", ")}`;
                    }
                } else if (s.step_type === "encoding") {
                    if (s.config.method === "one_hot") {
                        let addedCols = 0;
                        cols.forEach(colName => {
                            const colObj = appState.columns.find(c => c.name === colName);
                            if (colObj) addedCols += Math.max(0, colObj.unique_count - 2);
                        });
                        currentCols += addedCols;
                    }
                    desc = `Đã mã hóa phân loại (phương pháp '${s.config.method}') cho các cột: ${cols.join(", ")}`;
                }

                history.push({
                    step: idx + 1,
                    action: s.step_type,
                    description: desc
                });
            });

            renderAuditResult({
                initial_rows: mockProfileData.total_rows,
                final_rows: currentRows,
                rows_removed: mockProfileData.total_rows - currentRows,
                initial_columns: mockProfileData.total_columns,
                final_columns: currentCols,
                columns_added_or_removed: currentCols - mockProfileData.total_columns,
                total_steps: appState.pipelineSteps.length,
                history: history
            });
            return;
        }

        // Chạy với Backend thật qua POST /api/clean
        executeBtn.textContent = "Đang xử lý làm sạch...";
        executeBtn.disabled = true;

        try {
            const response = await executePipelineAPI(appState.currentFileId, appState.pipelineSteps);
            // Require a real audit summary. Never display "undefined" as metrics.
            if (!response.audit_summary) {
                throw new Error("Backend không trả về audit_summary. Hãy kiểm tra phiên bản Clean API.");
            }
            renderAuditResult(response.audit_summary);
        } catch (err) {
            alert(err.message);
        } finally {
            executeBtn.textContent = "Thực thi Pipeline làm sạch";
            executeBtn.disabled = false;
        }
    });

    // 9. Xuất file CSV / JSON
    document.getElementById("btn-export-csv").addEventListener("click", () => {
        downloadExportFileAPI(appState.currentFileId, "csv");
    });
    document.getElementById("btn-export-json").addEventListener("click", () => {
        downloadExportFileAPI(appState.currentFileId, "json");
    });
});
