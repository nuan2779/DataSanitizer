// Escape untrusted strings before inserting them via innerHTML to prevent XSS.
export function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    })[char]);
}

// Hiển thị thanh thông báo Toast
export function showToast(message, type = "success") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    let displayMsg = message;
    if (typeof message === "string" && message.includes("Failed to fetch")) {
        displayMsg = "Không thể kết nối đến máy chủ Backend (Cổng 8000). Vui lòng kiểm tra và khởi động Backend.";
    }

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.textContent = displayMsg;

    container.appendChild(toast);

    // Tự động xóa sau 4 giây
    setTimeout(() => {
        toast.style.animation = "slideInRight 0.3s ease-in reverse forwards";
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}