// Xử lý hiển thị Bảng Profiling (Bước 2) & Modal chi tiết cột
import { appState, saveStateToStorage } from "./state.js";
import { fetchColumnDetailAPI } from "./api.js";
import { escapeHtml } from "./dom-safe.js";

// Cập nhật thanh tiến trình (Step Indicator)
export function updateStepIndicator(stepId) {
    document.querySelectorAll(".step-indicator").forEach(el => {
        el.classList.remove("active");
        if (el.dataset.target === stepId) {
            el.classList.add("active");
            el.disabled = false; // Mở khóa tab nếu nó đã được active
        }
    });
}

// Khởi tạo hiển thị dữ liệu Profiling
export function renderProfileData(profileData) {
    appState.currentFileId = profileData.file_id || appState.currentFileId;
    appState.filename = profileData.filename || appState.filename;
    appState.columns = profileData.columns || [];

    document.getElementById("summary-filename").textContent = appState.filename;
    document.getElementById("summary-fileid").textContent = appState.currentFileId;
    document.getElementById("summary-rows").textContent = profileData.total_rows?.toLocaleString() || "0";
    document.getElementById("summary-cols").textContent = profileData.total_columns || "0";

    renderProfileTableRows(appState.columns);

    const searchInput = document.getElementById("search-col-input");
    if (searchInput) {
        searchInput.oninput = (e) => {
            const keyword = e.target.value.trim().toLowerCase();
            const filteredCols = appState.columns.filter(col => col.name.toLowerCase().includes(keyword));
            renderProfileTableRows(filteredCols);
        };
    }

    renderColumnCheckboxes();

    document.getElementById("profile-section").classList.remove("hidden");
    document.getElementById("pipeline-section").classList.remove("hidden");
    
    // Mở khóa các tab tương ứng
    document.querySelector('.step-indicator[data-target="profile-section"]').disabled = false;
    document.querySelector('.step-indicator[data-target="pipeline-section"]').disabled = false;
    
    // Mở khóa nút Tiếp tục ở bước 1 nếu có
    const uploadNextBtn = document.querySelector("#upload-section .btn-nav.next");
    if (uploadNextBtn) uploadNextBtn.disabled = false;
    
    updateStepIndicator("profile-section");
    saveStateToStorage();
}

function renderProfileTableRows(columnsList) {
    const tbody = document.getElementById("profile-tbody");
    tbody.innerHTML = "";

    if (!columnsList || columnsList.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="empty-state">No matching features found.</td></tr>`;
        return;
    }

    columnsList.forEach(col => {
        const tr = document.createElement("tr");
        const samplesText = (col.sample_values || []).slice(0, 4).join(", ");

        tr.innerHTML = `
            <td><strong>${escapeHtml(col.name)}</strong></td>
            <td><code>${escapeHtml(col.dtype)}</code></td>
            <td>${escapeHtml(col.null_count)}</td>
            <td><strong>${escapeHtml(col.null_percentage)}%</strong></td>
            <td>${escapeHtml(col.unique_count)}</td>
            <td class="text-muted">${escapeHtml(samplesText || "-")}</td>
            <td><button type="button" class="btn-link btn-view-col" data-col="${escapeHtml(col.name)}">Details</button></td>
        `;
        tbody.appendChild(tr);
    });

    tbody.querySelectorAll(".btn-view-col").forEach(btn => {
        btn.addEventListener("click", () => openColumnModal(btn.dataset.col));
    });
}

function renderColumnCheckboxes() {
    const container = document.getElementById("column-checkbox-list");
    container.innerHTML = "";

    appState.columns.forEach((col, index) => {
        const div = document.createElement("div");
        div.className = "checkbox-item";
        div.innerHTML = `
            <input type="checkbox" id="chk-col-${index}" value="${escapeHtml(col.name)}" class="col-checkbox">
            <label for="chk-col-${index}">${escapeHtml(col.name)} <span class="text-muted">(${escapeHtml(col.dtype)})</span></label>
        `;
        container.appendChild(div);
    });
}

export async function openColumnModal(colName) {
    let colDetail = appState.columns.find(c => c.name === colName);

    try {
        const apiDetail = await fetchColumnDetailAPI(appState.currentFileId, colName);
        colDetail = { ...colDetail, ...apiDetail };
    } catch (err) {
        console.warn("Failed to load details:", err);
    }

    if (!colDetail) return;

    document.getElementById("modal-col-title").textContent = `Feature: ${colName}`;
    document.getElementById("modal-dtype").textContent = colDetail.dtype;
    document.getElementById("modal-nulls").textContent = colDetail.null_count;
    document.getElementById("modal-null-pct").textContent = `${colDetail.null_percentage}%`;
    document.getElementById("modal-unique").textContent = colDetail.unique_count;

    const numericSection = document.getElementById("modal-numeric-stats");
    if (colDetail.statistics) {
        numericSection.classList.remove("hidden");
        document.getElementById("modal-mean").textContent = colDetail.statistics.mean ?? "-";
        document.getElementById("modal-median").textContent = colDetail.statistics.median ?? "-";
        document.getElementById("modal-std").textContent = colDetail.statistics.std ?? "-";
        document.getElementById("modal-min").textContent = colDetail.statistics.min ?? "-";
        document.getElementById("modal-max").textContent = colDetail.statistics.max ?? "-";
        document.getElementById("modal-outliers").textContent = colDetail.statistics.outlier_count ?? 0;
    } else {
        numericSection.classList.add("hidden");
    }

    document.getElementById("column-modal").classList.remove("hidden");
}