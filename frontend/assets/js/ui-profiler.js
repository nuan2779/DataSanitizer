// Xử lý hiển thị Bảng Profiling (Bước 2) & Modal chi tiết cột
import { appState } from "./state.js";
import { fetchColumnDetailAPI } from "./api.js";
import { escapeHtml } from "./dom-safe.js";

// Cập nhật thanh tiến trình (Step Indicator) trên Header
export function updateStepIndicator(stepId) {
    document.querySelectorAll(".step-indicator").forEach(el => {
        if (el.dataset.target === stepId) {
            el.classList.add("active");
        }
    });
}

// Hiển thị dữ liệu từ generate_profile() lên giao diện Bước 2 & tạo Checkbox Bước 3
export function renderProfileData(profileData) {
    appState.currentFileId = profileData.file_id;
    appState.filename = profileData.filename;
    appState.columns = profileData.columns || [];

    // 1. Điền các thẻ Summary Cards
    document.getElementById("summary-filename").textContent = profileData.filename;
    document.getElementById("summary-fileid").textContent = profileData.file_id;
    document.getElementById("summary-rows").textContent = profileData.total_rows.toLocaleString();
    document.getElementById("summary-cols").textContent = profileData.total_columns;

    // 2. Render toàn bộ các dòng vào bảng ban đầu
    renderProfileTableRows(appState.columns);

    // 3. Lắng nghe sự kiện gõ tìm kiếm cột theo tên
    const searchInput = document.getElementById("search-col-input");
    if (searchInput) {
        searchInput.value = ""; // Reset ô tìm kiếm khi tải file mới
        searchInput.oninput = (e) => {
            const keyword = e.target.value.trim().toLowerCase();
            const filteredCols = appState.columns.filter(col =>
                col.name.toLowerCase().includes(keyword)
            );
            renderProfileTableRows(filteredCols);
        };
    }

    // 4. Tạo danh sách Checkbox chọn cột ở Bước 3 (Pipeline)
    renderColumnCheckboxes();

    // 5. Mở khóa khu vực Bước 2 và Bước 3
    document.getElementById("profile-section").classList.remove("hidden");
    document.getElementById("pipeline-section").classList.remove("hidden");
    updateStepIndicator("profile-section");
    updateStepIndicator("pipeline-section");

    // Cuộn mượt xuống khu vực Khám phá dữ liệu
    document.getElementById("profile-section").scrollIntoView({ behavior: "smooth" });
}

// Hàm phụ: Vẽ các dòng trong bảng #profile-tbody dựa trên danh sách cột truyền vào
function renderProfileTableRows(columnsList) {
    const tbody = document.getElementById("profile-tbody");
    tbody.innerHTML = "";

    if (columnsList.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; color: #64748b; padding: 20px;">
                    Không tìm thấy cột nào khớp với từ khóa.
                </td>
            </tr>
        `;
        return;
    }

    columnsList.forEach(col => {
        const tr = document.createElement("tr");
        const samplesText = (col.sample_values || []).slice(0, 5).join(", ");

        tr.innerHTML = `
            <td><strong>${escapeHtml(col.name)}</strong></td>
            <td><code>${escapeHtml(col.dtype)}</code></td>
            <td>${escapeHtml(col.null_count)}</td>
            <td><strong>${escapeHtml(col.null_percentage)}%</strong></td>
            <td>${escapeHtml(col.unique_count)}</td>
            <td style="color: #64748b; font-size: 12px;">${escapeHtml(samplesText || "-")}</td>
            <td>
                <button type="button" class="btn-link btn-view-col" data-col="${escapeHtml(col.name)}">
                    Xem chi tiết
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });

    // Gắn sự kiện mở Modal cho các nút "Xem chi tiết"
    tbody.querySelectorAll(".btn-view-col").forEach(btn => {
        btn.addEventListener("click", () => openColumnModal(btn.dataset.col));
    });
}

// Tạo các ô Checkbox cột cho phần cấu hình Pipeline
function renderColumnCheckboxes() {
    const container = document.getElementById("column-checkbox-list");
    container.innerHTML = "";

    appState.columns.forEach((col, index) => {
        const div = document.createElement("div");
        div.className = "checkbox-item";
        div.innerHTML = `
            <input type="checkbox" id="chk-col-${index}" value="${escapeHtml(col.name)}" class="col-checkbox">
            <label for="chk-col-${index}">${escapeHtml(col.name)} <small style="color:#64748b">(${escapeHtml(col.dtype)})</small></label>
        `;
        container.appendChild(div);
    });
}

// Mở Modal hiển thị thông tin từ profile_single_column()
export async function openColumnModal(colName) {
    let colDetail = appState.columns.find(c => c.name === colName);

    // Gọi API lấy thống kê chi tiết của cột (Bỏ phần check file Demo)
    try {
        const apiDetail = await fetchColumnDetailAPI(appState.currentFileId, colName);
        colDetail = { ...colDetail, ...apiDetail };
    } catch (err) {
        console.warn("Lỗi tải chi tiết cột từ server:", err);
    }

    if (!colDetail) return;

    document.getElementById("modal-col-title").textContent = `Chi tiết cột: ${colName}`;
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
