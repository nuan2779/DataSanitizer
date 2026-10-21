// Xử lý cấu hình Pipeline (Bước 3) & Báo cáo Audit (Bước 4)
import { appState } from "./state.js";
import { updateStepIndicator } from "./ui-profiler.js";

const STEP_NAMES = {
    standardize_nulls: "Chuẩn hóa ký tự rác thành Null",
    clean_numeric: "Lọc ký tự tiền tệ & Ép kiểu số",
    missing_values: "Xử lý giá trị thiếu (Missing Values)",
    outlier: "Xử lý ngoại lai (Outliers)",
    encoding: "Mã hóa phân loại (Encoding)",
    scaling: "Chuẩn hóa thang đo (Scaling)",
    round: "Làm tròn số (Round Feature)"
};

// Ẩn/hiện khung nhập tham số tùy theo công cụ người dùng chọn
export function handleStepTypeChange() {
    const selectedType = document.getElementById("step-type-select").value;

    // Ẩn toàn bộ các khung cấu hình
    document.querySelectorAll(".step-config-panel").forEach(panel => {
        panel.classList.add("hidden");
    });

    // Hiện khung cấu hình tương ứng
    const activePanel = document.getElementById(`config-${selectedType}`);
    if (activePanel) activePanel.classList.remove("hidden");

    // Ẩn danh sách chọn cột nếu chọn standardize_nulls (vì hàm này chạy toàn bảng)
    const colSelectorGroup = document.getElementById("column-selector-group");
    if (selectedType === "standardize_nulls") {
        colSelectorGroup.classList.add("hidden");
    } else {
        colSelectorGroup.classList.remove("hidden");
    }
}

// Đọc dữ liệu từ Form và thêm 1 bước vào mảng pipelineSteps (chuẩn cấu trúc cleaner.py)
export function addStepToPipeline() {
    const stepType = document.getElementById("step-type-select").value;
    const selectedCols = Array.from(document.querySelectorAll(".col-checkbox:checked")).map(cb => cb.value);

    // Các bước bắt buộc phải chọn ít nhất 1 cột (trừ standardize_nulls và missing_values)
    if (stepType !== "standardize_nulls" && stepType !== "missing_values" && selectedCols.length === 0) {
        alert("Vui lòng tích chọn ít nhất 1 cột để áp dụng công cụ này!");
        return;
    }

    let config = {};

    if (stepType === "missing_values") {
        const strategy = document.getElementById("mv-strategy").value;
        config = {
            columns: selectedCols.length > 0 ? selectedCols : null,
            strategy: strategy
        };
        if (strategy === "constant") {
            config.fill_value = document.getElementById("mv-fill-value").value || "0";
        }
    } else if (stepType === "outlier") {
        config = {
            columns: selectedCols,
            method: document.getElementById("outlier-method").value,
            threshold: parseFloat(document.getElementById("outlier-threshold").value) || 1.5,
            handling: document.getElementById("outlier-handling").value
        };
    } else if (stepType === "encoding") {
        config = {
            columns: selectedCols,
            method: document.getElementById("encoding-method").value
        };
    } else if (stepType === "scaling") {
        config = {
            columns: selectedCols,
            method: document.getElementById("scaling-method").value
        };
    } else if (stepType === "clean_numeric") {
        config = { columns: selectedCols };
    } else if (stepType === "round") {
        config = {
            columns: selectedCols,
            decimals: parseInt(document.getElementById("round-decimals").value, 10) || 0,
            to_integer: document.getElementById("round-to-int").checked
        };
    }

    appState.pipelineSteps.push({
        step_type: stepType,
        config: config
    });

    renderPipelineQueue();
}

// Vẽ lại danh sách chờ thực thi ở cột bên phải
export function renderPipelineQueue() {
    const listEl = document.getElementById("pipeline-list");
    const countEl = document.getElementById("pipeline-count");
    const executeBtn = document.getElementById("btn-execute-pipeline");

    countEl.textContent = appState.pipelineSteps.length;
    listEl.innerHTML = "";

    if (appState.pipelineSteps.length === 0) {
        listEl.innerHTML = `<li class="empty-state">Chưa có bước xử lý nào được thêm.</li>`;
        executeBtn.disabled = true;
        return;
    }

    executeBtn.disabled = false;

    appState.pipelineSteps.forEach((step, index) => {
        const li = document.createElement("li");
        li.className = "pipeline-item";

        const colsText = step.config.columns && step.config.columns.length > 0
            ? `Cột: ${step.config.columns.join(", ")}`
            : "Áp dụng: Toàn bộ bảng";

        // Tóm tắt các tham số phụ
        const details = Object.entries(step.config)
            .filter(([key]) => key !== "columns")
            .map(([key, val]) => `${key}: ${val}`)
            .join(" | ");

        li.innerHTML = `
            <div class="step-info">
                <div class="step-title">Bước ${index + 1}: ${STEP_NAMES[step.step_type]}</div>
                <div class="step-detail">${colsText}${details ? ` — (${details})` : ""}</div>
            </div>
            <button type="button" class="btn-remove-step" data-index="${index}" title="Xóa bước này">&times;</button>
        `;
        listEl.appendChild(li);
    });

    // Gắn sự kiện xóa từng bước
    listEl.querySelectorAll(".btn-remove-step").forEach(btn => {
        btn.addEventListener("click", () => {
            const idx = parseInt(btn.dataset.index, 10);
            appState.pipelineSteps.splice(idx, 1);
            renderPipelineQueue();
        });
    });
}

// Hiển thị báo cáo Audit Summary ở Bước 4 (khớp với get_audit_summary trong cleaner.py)
export function renderAuditResult(auditData) {
    document.getElementById("audit-rows-compare").textContent = `${auditData.initial_rows} ➔ ${auditData.final_rows}`;
    document.getElementById("audit-rows-diff").textContent = `Đã loại bỏ: ${auditData.rows_removed} dòng`;

    document.getElementById("audit-cols-compare").textContent = `${auditData.initial_columns} ➔ ${auditData.final_columns}`;
    const colDiff = auditData.columns_added_or_removed;
    document.getElementById("audit-cols-diff").textContent = colDiff >= 0 ? `Tăng thêm: +${colDiff} cột` : `Giảm: ${colDiff} cột`;

    document.getElementById("audit-total-steps").textContent = auditData.total_steps;

    const historyList = document.getElementById("audit-history-list");
    historyList.innerHTML = "";

    (auditData.history || []).forEach(item => {
        const li = document.createElement("li");
        li.className = "audit-item";
        li.innerHTML = `
            <div class="step-info">
                <div class="step-title">Bước ${item.step}: [${item.action}]</div>
                <div class="step-detail">${item.description}</div>
            </div>
        `;
        historyList.appendChild(li);
    });

    const resultSection = document.getElementById("result-section");
    resultSection.classList.remove("hidden");
    updateStepIndicator("result-section");
    resultSection.scrollIntoView({ behavior: "smooth" });
}