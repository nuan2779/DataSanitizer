// Xử lý cấu hình Pipeline (Bước 3) & Báo cáo Audit (Bước 4)
import { appState } from "./state.js";
import { updateStepIndicator } from "./ui-profiler.js";
import { escapeHtml } from "./dom-safe.js";

const STEP_NAMES = {
    standardize_nulls: "Chuẩn hóa ký tự rác thành Null",
    clean_numeric: "Lọc ký tự tiền tệ & Ép kiểu số",
    missing_values: "Xử lý giá trị thiếu (Missing Values)",
    outlier: "Xử lý ngoại lai (Outliers)",
    encoding: "Mã hóa phân loại (Encoding)",
    scaling: "Chuẩn hóa thang đo (Scaling)",
    round: "Làm tròn số (Round Feature)"
};

// Regex nhận diện định dạng tiền tệ hoặc số hợp lệ (ví dụ: "$1,200.50", "1500 đ", "2500 VND", "1480000.0")
const MONEY_PATTERN = /^\s*[+-]?\s*\$?\s*(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?\s*(?:đ|₫|vnd|vnđ)?\s*$/i;

// Helper kiểm tra kiểu dữ liệu của cột
export function isNumericType(dtype) {
    if (!dtype) return false;
    const lower = dtype.toLowerCase();
    return lower.includes("int") || lower.includes("float") || lower.includes("number");
}

export function isCategoricalType(dtype) {
    if (!dtype) return false;
    const lower = dtype.toLowerCase();
    return lower.includes("object") || lower.includes("string") || lower.includes("category") || lower.includes("bool");
}

// Kiểm tra xem cột chuỗi (object) có thực sự là cột tiền tệ / số dạng chuỗi hay không
export function isCurrencyOrNumericString(col) {
    if (!col || !col.sample_values || col.sample_values.length === 0) return false;
    const validSamples = col.sample_values.filter(s => {
        const text = String(s).trim();
        return text !== "" && text !== "nan" && text !== "None" && text !== "null" && text !== "N/A" && text !== "?";
    });
    if (validSamples.length === 0) return false;
    return validSamples.every(s => MONEY_PATTERN.test(String(s).trim()));
}

// Cập nhật trạng thái enabled/disabled và nhãn cảnh báo cho từng cột theo công cụ đã chọn
export function updateColumnAvailability() {
    const stepType = document.getElementById("step-type-select")?.value;
    const mvStrategy = document.getElementById("mv-strategy")?.value;

    if (!appState.columns || appState.columns.length === 0) return;

    appState.columns.forEach((col, index) => {
        const checkbox = document.getElementById(`chk-col-${index}`);
        const label = checkbox?.parentElement;
        if (!checkbox || !label) return;

        const isNum = isNumericType(col.dtype);
        const isMoneyOrNum = isNum || isCurrencyOrNumericString(col);

        let isDisabled = false;
        let reason = "";

        if (["scaling", "outlier", "round"].includes(stepType)) {
            if (!isNum) {
                isDisabled = true;
                reason = " (Chỉ áp dụng cột số)";
            }
        } else if (stepType === "missing_values") {
            if (["mean", "median", "interpolate"].includes(mvStrategy)) {
                if (!isNum) {
                    isDisabled = true;
                    reason = " (Chỉ áp dụng cột số)";
                }
            }
        } else if (stepType === "encoding") {
            if (isNum) {
                isDisabled = true;
                reason = " (Chỉ áp dụng cột chữ/danh mục)";
            }
        } else if (stepType === "clean_numeric") {
            if (!isMoneyOrNum) {
                isDisabled = true;
                reason = " (Chứa văn bản, không phải tiền tệ/số)";
            }
        }

        checkbox.disabled = isDisabled;
        if (isDisabled) {
            checkbox.checked = false;
            label.style.opacity = "0.45";
            label.style.cursor = "not-allowed";
        } else {
            label.style.opacity = "1";
            label.style.cursor = "pointer";
        }

        // Cập nhật badge cảnh báo
        let badge = label.querySelector(".col-badge-warning");
        if (isDisabled) {
            if (!badge) {
                badge = document.createElement("span");
                badge.className = "col-badge-warning";
                badge.style.cssText = "color: #ef4444; font-size: 11px; margin-left: 6px; font-weight: 500;";
                label.appendChild(badge);
            }
            badge.textContent = reason;
        } else if (badge) {
            badge.remove();
        }
    });
}

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

    updateColumnAvailability();
}

// Đọc dữ liệu từ Form và thêm 1 bước vào mảng pipelineSteps
export function addStepToPipeline() {
    const stepType = document.getElementById("step-type-select").value;
    const selectedCols = Array.from(document.querySelectorAll(".col-checkbox:checked")).map(cb => cb.value);

    // Các bước bắt buộc phải chọn ít nhất 1 cột (trừ standardize_nulls và missing_values)
    if (stepType !== "standardize_nulls" && stepType !== "missing_values" && selectedCols.length === 0) {
        alert("Vui lòng tích chọn ít nhất 1 cột để áp dụng công cụ này!");
        return;
    }

    // Kiểm tra tính hợp lệ của kiểu dữ liệu (Defensive Validation)
    if (["scaling", "outlier", "round"].includes(stepType)) {
        const textCols = selectedCols.filter(colName => {
            const col = appState.columns.find(c => c.name === colName);
            return col && !isNumericType(col.dtype);
        });
        if (textCols.length > 0) {
            alert(`⚠️ Cảnh báo: Công cụ '${STEP_NAMES[stepType]}' chỉ áp dụng cho cột SỐ!\nCác cột không hợp lệ: [ ${textCols.join(", ")} ]\nVui lòng bỏ chọn các cột chữ.`);
            return;
        }
    }

    if (stepType === "missing_values") {
        const strategy = document.getElementById("mv-strategy").value;
        if (["mean", "median", "interpolate"].includes(strategy)) {
            const textCols = selectedCols.filter(colName => {
                const col = appState.columns.find(c => c.name === colName);
                return col && !isNumericType(col.dtype);
            });
            if (textCols.length > 0) {
                alert(`⚠️ Cảnh báo: Không thể tính '${strategy.toUpperCase()}' cho cột chữ!\nCác cột không hợp lệ: [ ${textCols.join(", ")} ]\nGợi ý: Chọn phương pháp 'Mode' hoặc 'Xóa dòng' cho cột chữ.`);
                return;
            }
        }
    }

    if (stepType === "encoding") {
        const numCols = selectedCols.filter(colName => {
            const col = appState.columns.find(c => c.name === colName);
            return col && isNumericType(col.dtype);
        });
        if (numCols.length > 0) {
            alert(`⚠️ Cảnh báo: Mã hóa phân loại (Encoding) chỉ áp dụng cho cột chữ/danh mục!\nCác cột không hợp lệ: [ ${numCols.join(", ")} ]`);
            return;
        }
    }

    if (stepType === "clean_numeric") {
        const invalidCols = selectedCols.filter(colName => {
            const col = appState.columns.find(c => c.name === colName);
            if (!col) return false;
            return !isNumericType(col.dtype) && !isCurrencyOrNumericString(col);
        });
        if (invalidCols.length > 0) {
            alert(`⚠️ Cảnh báo: Công cụ 'Lọc tiền tệ & Ép kiểu số' chỉ áp dụng cho cột số hoặc chuỗi tiền tệ!\nCác cột chứa văn bản (như địa chỉ, ngày tháng, tên quận): [ ${invalidCols.join(", ")} ]\nVui lòng bỏ chọn các cột này.`);
            return;
        }
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
                <div class="step-title">Bước ${index + 1}: ${escapeHtml(STEP_NAMES[step.step_type])}</div>
                <div class="step-detail">${escapeHtml(colsText)}${details ? ` — (${escapeHtml(details)})` : ""}</div>
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

// Hiển thị báo cáo Audit Summary ở Bước 4
export function renderAuditResult(auditData) {
    if (!auditData || !Number.isFinite(Number(auditData.initial_rows)) ||
        !Number.isFinite(Number(auditData.final_rows)) ||
        !Array.isArray(auditData.history)) {
        throw new Error("Audit Summary từ Backend không hợp lệ");
    }
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
                <div class="step-title">Bước ${escapeHtml(item.step)}: [${escapeHtml(item.action)}]</div>
                <div class="step-detail">${escapeHtml(item.description)}</div>
            </div>
        `;
        historyList.appendChild(li);
    });

    const resultSection = document.getElementById("result-section");
    resultSection.classList.remove("hidden");
    updateStepIndicator("result-section");
    resultSection.scrollIntoView({ behavior: "smooth" });
}
