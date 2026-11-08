// Xử lý cấu hình Pipeline (Bước 3) & Báo cáo Audit (Bước 4)
import { appState, saveStateToStorage } from "./state.js";
import { updateStepIndicator } from "./ui-profiler.js";
import { escapeHtml } from "./dom-safe.js";

const STEP_NAMES = {
    standardize_nulls: "Standardize Null Signatures",
    clean_numeric: "Currency Formatting & Numeric Cast",
    missing_values: "Missing Value Imputation",
    outlier: "Outlier Handling",
    encoding: "Categorical Encoding",
    scaling: "Feature Scaling",
    round: "Numeric Rounding"
};

const MONEY_PATTERN = /^\s*[+-]?\s*\$?\s*(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?\s*(?:đ|₫|vnd|vnđ)?\s*$/i;

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

export function isCurrencyOrNumericString(col) {
    if (!col || !col.sample_values || col.sample_values.length === 0) return false;
    const validSamples = col.sample_values.filter(s => {
        const text = String(s).trim();
        return text !== "" && text !== "nan" && text !== "None" && text !== "null" && text !== "N/A" && text !== "?";
    });
    if (validSamples.length === 0) return false;
    return validSamples.every(s => MONEY_PATTERN.test(String(s).trim()));
}

export function updateColumnAvailability() {
    const stepType = document.getElementById("step-type-select")?.value;
    const mvStrategy = document.getElementById("mv-strategy")?.value;
    const purpose = document.querySelector('input[name="data-purpose"]:checked')?.value || "eda";

    if (!appState.columns || appState.columns.length === 0) return;

    // Hiển thị hộp cảnh báo Leakage nếu chọn Encoding/Scaling ở chế độ EDA
    const leakageWarning = document.getElementById("leakage-warning");
    if (leakageWarning) {
        if (purpose === "eda" && (stepType === "encoding" || stepType === "scaling")) {
            leakageWarning.classList.remove("hidden");
        } else {
            leakageWarning.classList.add("hidden");
        }
    }

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
                reason = " (Numeric only)";
            }
        } else if (stepType === "missing_values") {
            if (["mean", "median", "interpolate"].includes(mvStrategy) && !isNum) {
                isDisabled = true;
                reason = " (Numeric only)";
            }
        } else if (stepType === "encoding") {
            if (isNum) {
                isDisabled = true;
                reason = " (Categorical only)";
            }
        } else if (stepType === "clean_numeric") {
            if (!isMoneyOrNum) {
                isDisabled = true;
                reason = " (Invalid format)";
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
    });
}

export function handleStepTypeChange() {
    const selectedType = document.getElementById("step-type-select").value;

    document.querySelectorAll(".step-config-panel").forEach(panel => {
        panel.classList.add("hidden");
    });

    const activePanel = document.getElementById(`config-${selectedType}`);
    if (activePanel) activePanel.classList.remove("hidden");

    const colSelectorGroup = document.getElementById("column-selector-group");
    if (selectedType === "standardize_nulls") {
        colSelectorGroup.classList.add("hidden");
    } else {
        colSelectorGroup.classList.remove("hidden");
    }

    updateColumnAvailability();
}

export function addStepToPipeline() {
    const stepType = document.getElementById("step-type-select").value;
    const selectedCols = Array.from(document.querySelectorAll(".col-checkbox:checked")).map(cb => cb.value);

    if (stepType !== "standardize_nulls" && stepType !== "missing_values" && selectedCols.length === 0) {
        alert("Please select at least one feature.");
        return;
    }

    let config = {};
    if (stepType === "missing_values") {
        const strategy = document.getElementById("mv-strategy").value;
        config = { columns: selectedCols.length > 0 ? selectedCols : null, strategy: strategy };
        if (strategy === "constant") config.fill_value = document.getElementById("mv-fill-value").value || "0";
    } else if (stepType === "outlier") {
        config = {
            columns: selectedCols,
            method: document.getElementById("outlier-method").value,
            threshold: parseFloat(document.getElementById("outlier-threshold").value) || 1.5,
            handling: document.getElementById("outlier-handling").value
        };
    } else if (stepType === "encoding") {
        config = { columns: selectedCols, method: document.getElementById("encoding-method").value };
    } else if (stepType === "scaling") {
        config = { columns: selectedCols, method: document.getElementById("scaling-method").value };
    } else if (stepType === "clean_numeric") {
        config = { columns: selectedCols };
    } else if (stepType === "round") {
        config = {
            columns: selectedCols,
            decimals: parseInt(document.getElementById("round-decimals").value, 10) || 0,
            to_integer: document.getElementById("round-to-int").checked
        };
    }

    appState.pipelineSteps.push({ step_type: stepType, config: config });
    renderPipelineQueue();
    saveStateToStorage();
}

export function renderPipelineQueue() {
    const listEl = document.getElementById("pipeline-list");
    const countEl = document.getElementById("pipeline-count");
    const executeBtn = document.getElementById("btn-execute-pipeline");

    countEl.textContent = appState.pipelineSteps.length;
    listEl.innerHTML = "";

    if (appState.pipelineSteps.length === 0) {
        listEl.innerHTML = `<li class="empty-state">Queue is empty.</li>`;
        executeBtn.disabled = true;
        return;
    }

    executeBtn.disabled = false;

    appState.pipelineSteps.forEach((step, index) => {
        const li = document.createElement("li");
        li.className = "pipeline-item";

        const colsText = step.config.columns && step.config.columns.length > 0
            ? `Features: ${step.config.columns.join(", ")}`
            : "Scope: Global";

        const details = Object.entries(step.config)
            .filter(([key]) => key !== "columns")
            .map(([key, val]) => `${key}: ${val}`)
            .join(" | ");

        li.innerHTML = `
            <div class="step-info">
                <div class="step-title">Step ${index + 1}: ${escapeHtml(STEP_NAMES[step.step_type] || step.step_type)}</div>
                <div class="step-detail">${escapeHtml(colsText)}${details ? ` — (${escapeHtml(details)})` : ""}</div>
            </div>
            <button type="button" class="btn-remove-step" data-index="${index}" title="Remove step">&times;</button>
        `;
        listEl.appendChild(li);
    });

    listEl.querySelectorAll(".btn-remove-step").forEach(btn => {
        btn.addEventListener("click", () => {
            appState.pipelineSteps.splice(parseInt(btn.dataset.index, 10), 1);
            renderPipelineQueue();
            saveStateToStorage();
        });
    });
}

export function renderAuditResult(auditData) {
    if (!auditData) return;
    
    document.getElementById("audit-rows-compare").textContent = `${auditData.initial_rows} → ${auditData.final_rows}`;
    document.getElementById("audit-cols-compare").textContent = `${auditData.initial_columns} → ${auditData.final_columns}`;
    document.getElementById("audit-total-steps").textContent = auditData.total_steps;

    const historyList = document.getElementById("audit-history-list");
    historyList.innerHTML = "";

    (auditData.history || []).forEach(item => {
        const li = document.createElement("li");
        li.className = "audit-item";
        li.innerHTML = `
            <div class="step-info">
                <div class="step-title">Step ${escapeHtml(item.step)}: [${escapeHtml(item.action)}]</div>
                <div class="step-detail">${escapeHtml(item.description)}</div>
            </div>
        `;
        historyList.appendChild(li);
    });

    // Cập nhật giao diện nút tải về tùy theo chế độ chạy
    const btnCsv = document.getElementById("btn-export-csv");
    const btnJson = document.getElementById("btn-export-json");
    const btnTrain = document.getElementById("btn-export-train");
    const btnTest = document.getElementById("btn-export-test");
    
    if (appState.purpose === "ml") {
        btnCsv.classList.add("hidden");
        btnJson.classList.add("hidden");
        btnTrain.classList.remove("hidden");
        btnTest.classList.remove("hidden");
        
        // Hiện khung đánh giá AI
        if (appState.mode === 'online') {
            document.getElementById("ml-benchmark").classList.remove("hidden");
            document.getElementById("health-score-text").textContent = "Ready to evaluate";
        }
    } else {
        btnCsv.classList.remove("hidden");
        btnJson.classList.remove("hidden");
        btnTrain.classList.add("hidden");
        btnTest.classList.add("hidden");
        document.getElementById("ml-benchmark").classList.add("hidden");
    }

    const resultSection = document.getElementById("result-section");
    resultSection.classList.remove("hidden");
    
    // Tự động mở khóa nút xuất kết quả trên thanh Stepper
    const exportTabBtn = document.querySelector('.step-indicator[data-target="result-section"]');
    if (exportTabBtn) exportTabBtn.disabled = false;
    
    updateStepIndicator("result-section");
    resultSection.scrollIntoView({ behavior: "smooth" });
}